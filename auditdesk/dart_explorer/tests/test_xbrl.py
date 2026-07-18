"""XBRL 파이프라인 게이트 (패치 B-3).

게이트 (지시서 B-3-5):
- 실제 상장사 1곳 XBRL: DART 뷰어 수동 다운로드 파일과 ZIP 바이트 동일
  → tests/fixtures/manual_xbrl/ 에 수동 파일이 있을 때 검증 (없으면 skip)
- extract 결과가 기존 수동 방식(legacy 도구) 산출물과 행 수 일치
- 캐시 히트 시 재다운로드 금지 / 미제출 시 "결과 없음" 명확 처리
"""
import glob
import os

import pytest

from dart_explorer.client.opendart import OpenDartClient
from dart_explorer.xbrl.pipeline import (XbrlNotAvailable, download_xbrl,
                                         find_periodic_rcept, instance_path,
                                         run)

try:
    from dart_explorer.client.config import load_api_key
    _HAS_KEY = bool(load_api_key())
except RuntimeError:
    _HAS_KEY = False

_MANUAL_DIR = os.path.join(os.path.dirname(__file__), "fixtures",
                           "manual_xbrl")
_SAMSUNG = "00126380"


class _Resp:
    def __init__(self, content=b"", json_obj=None, ctype=None):
        self.content = content
        self._json = json_obj
        self.headers = {"content-type": ctype or (
            "application/json" if json_obj is not None else "application/zip")}

    def json(self):
        return self._json


@pytest.fixture()
def client(tmp_path):
    return OpenDartClient(api_key="TESTKEY", cache_dir=str(tmp_path), sleep=0)


# ---------------------------------------------------------------------------
# 오프라인 단위 테스트
# ---------------------------------------------------------------------------

def test_find_periodic_rcept_matches_business_year(client, monkeypatch):
    """사업보고서는 이듬해 접수 — report_nm의 (YYYY.12)로 대상 연도 확정."""
    docs = [{"rcept_no": "1" * 14, "report_nm": "사업보고서 (2024.12)"},
            {"rcept_no": "2" * 14, "report_nm": "사업보고서 (2025.12)"}]
    monkeypatch.setattr(client, "search", lambda **kw: docs)
    hit = find_periodic_rcept(client, _SAMSUNG, 2025)
    assert hit["rcept_no"] == "2" * 14


def test_xbrl_not_available_cleans_cache(client, monkeypatch):
    """미제출(013) 응답: 명확한 예외 + 오류 페이로드를 캐시에 남기지 않음."""
    err_xml = ('<?xml version="1.0"?><result><status>013</status>'
               '<message>조회된 데이타가 없습니다.</message></result>'
               ).encode("utf-8")
    monkeypatch.setattr(
        "dart_explorer.client.opendart.requests.get",
        lambda *a, **k: _Resp(content=err_xml, ctype="application/xml"))
    with pytest.raises(XbrlNotAvailable, match="미제출"):
        download_xbrl(client, "99999999", "3" * 14)
    leftovers = glob.glob(os.path.join(client.cache.root, "xbrl", "**", "*"),
                          recursive=True)
    assert not [p for p in leftovers if os.path.isfile(p)]


def test_download_cache_hit_no_redownload(client, monkeypatch):
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("sample.xbrl", b"<xbrl/>")
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return _Resp(content=buf.getvalue())
    monkeypatch.setattr("dart_explorer.client.opendart.requests.get",
                        fake_get)
    download_xbrl(client, _SAMSUNG, "4" * 14)
    download_xbrl(client, _SAMSUNG, "4" * 14)
    assert len(calls) == 1                    # 영구 캐시 — 재다운로드 금지


# ---------------------------------------------------------------------------
# 라이브 게이트 (API 키 있을 때만) — 실캐시 사용 (재다운로드 없음)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HAS_KEY, reason="OPENDART_API_KEY 없음")
def test_gate_live_pipeline_and_offline_rerun(monkeypatch, tmp_path):
    res = run("삼성전자", 2025, out_dir=str(tmp_path))
    assert res["rows"] > 1000
    assert res["has_ko_labels"]               # lab-ko 동일 폴더 (무수정 입력 조건)
    assert os.path.exists(res["xlsx"])
    assert instance_path(res["folder"]).endswith(".xbrl")

    # 전체 파이프라인 오프라인 재실행 → 캐시만으로 동작 (재다운로드 금지)
    def offline(*a, **k):
        raise ConnectionError("offline")
    monkeypatch.setattr("dart_explorer.client.opendart.requests.get", offline)
    res2 = run("삼성전자", 2025, out_dir=str(tmp_path))
    assert res2["rows"] == res["rows"]
    assert res2["rcept_no"] == res["rcept_no"]


@pytest.mark.skipif(not _HAS_KEY, reason="OPENDART_API_KEY 없음")
def test_gate_rows_match_legacy_tool(tmp_path):
    """extract 결과 행 수가 기존 수동 방식(legacy 도구) 산출물과 일치."""
    import importlib.util
    res = run("삼성전자", 2025, out_dir=str(tmp_path))
    inst = instance_path(res["folder"])

    legacy_path = os.path.join(os.path.dirname(__file__), "..", "legacy",
                               "xbrl_extract.py")
    spec = importlib.util.spec_from_file_location("legacy_xbrl_extract",
                                                  legacy_path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    legacy_rows = legacy.extract(inst)
    assert len(legacy_rows) == res["rows"]

    from dart_explorer.xbrl.xbrl_extract import extract as new_extract
    assert new_extract(inst) == legacy_rows   # 무수정 복사 — 내용까지 동일


# ---------------------------------------------------------------------------
# ZIP 바이트 동일 (DART 뷰어 수동 다운로드 파일 필요 — 없으면 skip)
# ---------------------------------------------------------------------------

_manual_files = (sorted(glob.glob(os.path.join(_MANUAL_DIR, "*.zip")))
                 if os.path.isdir(_MANUAL_DIR) else [])


@pytest.mark.skipif(not (_HAS_KEY and _manual_files),
                    reason="수동 다운로드 파일 없음 "
                           "(tests/fixtures/manual_xbrl/*.zip)")
def test_gate_identity_with_manual_download():
    """API 수신 ZIP == DART 뷰어 수동 다운로드 ZIP.

    실측(2026-07-08): DART 뷰어는 다운로드 시각으로 ZIP 엔트리 타임스탬프를
    재기록하므로 바이트 동일은 원리적으로 불가 — 엔트리 구성·CRC·내용 SHA
    완전 일치(내용 동일성)로 판정한다. 바이트 동일이면 즉시 통과.
    """
    import hashlib
    import io
    import zipfile
    cli = OpenDartClient()
    doc = find_periodic_rcept(cli, _SAMSUNG, 2025)
    api_bytes, _ = download_xbrl(cli, _SAMSUNG, doc["rcept_no"])
    manual_bytes = open(_manual_files[0], "rb").read()
    if api_bytes == manual_bytes:               # 바이트 동일이면 그대로 통과
        return

    def entry_hashes(data):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return {n: (z.getinfo(n).CRC,
                        hashlib.sha1(z.read(n)).hexdigest())
                    for n in z.namelist()}
    ea, em = entry_hashes(api_bytes), entry_hashes(manual_bytes)
    assert ea == em, f"엔트리 내용 불일치: {set(ea) ^ set(em) or 'SHA 상이'}"
    assert len(api_bytes) == len(manual_bytes)  # 압축 결과까지 동일 크기
