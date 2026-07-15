"""DSD(ZIP) 바이너리 스플라이스.

원본 ZIP의 다른 엔트리는 바이트 그대로 보존하고 contents.xml 엔트리만
교체한다. LFH/CD/EOCD 오프셋을 수동 패치한다 (스펙 3.5).
"""
import struct
import zlib

CONTENTS_NAME = "contents.xml"

_EOCD_SIG = b"PK\x05\x06"
_CD_SIG = b"PK\x01\x02"
_LFH_SIG = b"PK\x03\x04"


class ZipFormatError(Exception):
    pass


def _parse_central_directory(data: bytes):
    eocd_off = data.rfind(_EOCD_SIG)
    if eocd_off < 0:
        raise ZipFormatError("EOCD를 찾을 수 없습니다 (ZIP 형식이 아님)")
    (_, _, _, _, n_total, cd_size, cd_off, _) = struct.unpack_from(
        "<IHHHHIIH", data, eocd_off)
    if cd_off == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:
        raise ZipFormatError("ZIP64 형식은 지원하지 않습니다")

    entries = []
    p = cd_off
    for _ in range(n_total):
        if data[p:p + 4] != _CD_SIG:
            raise ZipFormatError("중앙 디렉터리 레코드 손상")
        flags, method = struct.unpack_from("<HH", data, p + 8)
        crc, csize, usize = struct.unpack_from("<III", data, p + 16)
        nlen, elen, clen = struct.unpack_from("<HHH", data, p + 28)
        lfh_off, = struct.unpack_from("<I", data, p + 42)
        name = data[p + 46:p + 46 + nlen]
        entries.append({
            "cd_pos": p, "cd_len": 46 + nlen + elen + clen,
            "name": name, "flags": flags, "method": method,
            "crc": crc, "csize": csize, "usize": usize,
            "lfh_off": lfh_off, "new": None,
        })
        p += 46 + nlen + elen + clen
    return eocd_off, cd_off, entries


def _find_contents_entry(entries):
    for e in entries:
        name = e["name"].decode("utf-8", "replace")
        if name.lower().endswith(CONTENTS_NAME):
            return e
    raise ZipFormatError("contents.xml 엔트리를 찾을 수 없습니다")


def read_contents(data: bytes) -> bytes:
    """contents.xml 압축 해제 (원본 바이트)."""
    _, _, entries = _parse_central_directory(data)
    return _decompress_entry(data, _find_contents_entry(entries))


def read_entry(data: bytes, name: str):
    """이름이 name으로 끝나는 엔트리 압축 해제. 없으면 None."""
    _, _, entries = _parse_central_directory(data)
    for e in entries:
        if e["name"].decode("utf-8", "replace").lower().endswith(name.lower()):
            return _decompress_entry(data, e)
    return None


def _decompress_entry(data: bytes, e: dict) -> bytes:
    off = e["lfh_off"]
    if data[off:off + 4] != _LFH_SIG:
        raise ZipFormatError("로컬 파일 헤더 손상")
    nlen, elen = struct.unpack_from("<HH", data, off + 26)
    body = data[off + 30 + nlen + elen: off + 30 + nlen + elen + e["csize"]]
    if e["method"] == 0:
        raw = body
    elif e["method"] == 8:
        raw = zlib.decompress(body, -15)
    else:
        raise ZipFormatError(f"지원하지 않는 압축 방식: {e['method']}")
    if len(raw) != e["usize"]:
        raise ZipFormatError("압축 해제 크기 불일치")
    return raw


def replace_contents(data: bytes, new_raw: bytes) -> bytes:
    """contents.xml만 교체한 새 ZIP 바이트 생성. 다른 엔트리는 그대로 복사."""
    eocd_off, cd_off, entries = _parse_central_directory(data)
    target = _find_contents_entry(entries)

    by_offset = sorted(entries, key=lambda e: e["lfh_off"])
    prefix_end = by_offset[0]["lfh_off"] if by_offset else 0
    out = bytearray(data[:prefix_end])
    new_offsets = {}

    for i, e in enumerate(by_offset):
        start = e["lfh_off"]
        end = by_offset[i + 1]["lfh_off"] if i + 1 < len(by_offset) else cd_off
        new_offsets[id(e)] = len(out)

        if e is not target:
            out += data[start:end]
            continue

        # 새 로컬 레코드: 원본 LFH를 복사한 뒤 CRC/크기/플래그만 패치
        if data[start:start + 4] != _LFH_SIG:
            raise ZipFormatError("로컬 파일 헤더 손상")
        nlen, elen = struct.unpack_from("<HH", data, start + 26)
        lfh = bytearray(data[start:start + 30 + nlen + elen])

        crc = zlib.crc32(new_raw) & 0xFFFFFFFF
        method = e["method"] if e["method"] in (0, 8) else 8
        if method == 8:
            co = zlib.compressobj(9, zlib.DEFLATED, -15)
            comp = co.compress(new_raw) + co.flush()
        else:
            comp = new_raw

        flags, = struct.unpack_from("<H", lfh, 6)
        flags &= ~0x08  # 데이터 디스크립터 제거 (크기를 LFH에 직접 기록)
        struct.pack_into("<H", lfh, 6, flags)
        struct.pack_into("<H", lfh, 8, method)
        struct.pack_into("<III", lfh, 14, crc, len(comp), len(new_raw))
        out += lfh + comp
        e["new"] = (flags, method, crc, len(comp), len(new_raw))

    # 중앙 디렉터리 재작성 (원본 CD 순서 유지, 오프셋 패치)
    new_cd_off = len(out)
    for e in entries:
        rec = bytearray(data[e["cd_pos"]:e["cd_pos"] + e["cd_len"]])
        if e["new"]:
            flags, method, crc, csize, usize = e["new"]
            struct.pack_into("<HH", rec, 8, flags, method)
            struct.pack_into("<III", rec, 16, crc, csize, usize)
        struct.pack_into("<I", rec, 42, new_offsets[id(e)])
        out += rec
    new_cd_size = len(out) - new_cd_off

    eocd = bytearray(data[eocd_off:])
    struct.pack_into("<II", eocd, 12, new_cd_size, new_cd_off)
    out += eocd
    return bytes(out)
