"""contents.xml 스캐너.

정규 XML 파서 대신 정규식으로 문자 오프셋을 직접 기록한다
(위치 기반 값 교체의 전제). 스펙 2장 구조 불변식 기반.
"""
import re
from dataclasses import dataclass, field

from .textutil import clean_text, fs_title_unclassified, match_fs_title

# ---------------------------------------------------------------------------
# 저수준 요소
# ---------------------------------------------------------------------------

_ATTR_RE = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
_TABLE_RE = re.compile(r"<TABLE\b[^>]*>.*?</TABLE>", re.DOTALL)
_TR_RE = re.compile(r"<TR\b[^>]*>.*?</TR>", re.DOTALL)
_CELL_OPEN_RE = re.compile(r"<(TD|TH|TE|TU)\b([^>]*)>")
_P_RE = re.compile(r"<P\b[^>]*>(.*?)</P>", re.DOTALL)
_TU_RE = re.compile(r"<TU\b([^>]*)>(.*?)</TU>", re.DOTALL)
_SECTION1_CLOSE_RE = re.compile(r"</SECTION-1>")
_COVER_RE = re.compile(r"<COVER\b[^>]*>.*?</COVER>", re.DOTALL)
_TOC_RE = re.compile(r"<TOC\b[^>]*>.*?</TOC>", re.DOTALL)
_TITLE_RE = re.compile(r"<TITLE\b[^>]*>(.*?)</TITLE>", re.DOTALL)

# 주석 헤더 (스펙 2.5) — 폴백 체인
# group(1) = 헤더 내부 콘텐츠(번호부터, 교체 가능 구간), group(2) = 주석 번호
_NOTE_USERMARK_RE = re.compile(
    r'<SPAN\b[^>]*USERMARK="\s*B\s*"[^>]*>\s*((\d+)\s*\.\s*.*?)</SPAN>', re.DOTALL
)
_NOTE_SPANID_RE = re.compile(
    r'<SPAN\b[^>]*ID="[^"]*"[^>]*>\s*((\d+)\s*\.\s*.*?)</SPAN>', re.DOTALL
)
_NOTE_PLAIN_RE = re.compile(r"<P\b[^>]*>\s*((\d+)\s*\.\s*[^<&]{1,60})", re.DOTALL)
# B-6-mini: 융합형 평문 주석 경계 — 제목+본문이 한 P에 이어져도
# 경계로 인정 (2차 분할 전용 — 1차 헤더 체인은 기존 규칙 유지)
_NOTE_FUSED_RE = re.compile(
    r"<P\b[^>]*>\s*(?:&amp;cr;|\s|<SPAN\b[^>]*>)*"
    r"((\d{1,2})\s*[.．]\s*[가-힣][^<]{0,60})")
# B-6c: 문단 중간 &cr; 경계 헤더 — '…합니다.&cr;&cr;2. 제목' 형태.
# 공시본 실측(바이오인프라 FY25 감사보고서): 일부 헤더가 P 시작이 아닌
# 본문 중간에만 존재해 평문 체인이 붕괴한다. TITLE로 확정된 주석
# 범위 안에서만 후보로 쓴다 (폴백 전용).
_NOTE_CR_RE = re.compile(
    r"(?:&amp;cr;\s*)+((\d{1,2})\s*[.．]\s*[가-힣][^<&]{0,60})")
# B-6c: 주석 범위 단일 산정 — '주석' TITLE ~ 다음 TITLE
_NOTES_TITLE_RE = re.compile(r"<TITLE\b[^>]*>\s*주\s*석\s*</TITLE>")


@dataclass
class Cell:
    tag: str            # TD | TH | TE | TU
    attrs: dict
    start: int          # 내용 시작 오프셋 (여는 태그 '>' 다음)
    end: int            # 내용 끝 오프셋 ('</' 위치)
    raw: str            # 내용 원본 XML

    @property
    def text(self) -> str:
        return clean_text(self.raw)

    @property
    def colspan(self) -> int:
        try:
            return max(1, int(self.attrs.get("COLSPAN", 1)))
        except ValueError:
            return 1

    @property
    def rowspan(self) -> int:
        try:
            return max(1, int(self.attrs.get("ROWSPAN", 1)))
        except ValueError:
            return 1


@dataclass
class Table:
    start: int
    end: int
    rows: list = field(default_factory=list)  # list[list[Cell]]

    def all_cells(self):
        for row in self.rows:
            yield from row

    def grid(self):
        """ROWSPAN/COLSPAN을 반영한 (r, c) -> Cell 배치."""
        placed = {}
        occupied = set()
        for r, row in enumerate(self.rows):
            c = 0
            for cell in row:
                while (r, c) in occupied:
                    c += 1
                placed[(r, c)] = cell
                for dr in range(cell.rowspan):
                    for dc in range(cell.colspan):
                        occupied.add((r + dr, c + dc))
                c += cell.colspan
        return placed


@dataclass
class Paragraph:
    start: int
    end: int          # 내용 구간 (P 내부)
    raw: str

    @property
    def text(self) -> str:
        return clean_text(self.raw)

    @property
    def is_plain(self) -> bool:
        """내부 마크업이 없어 통째 교체가 안전한 문단."""
        return "<" not in self.raw


@dataclass
class FSBlock:
    title_cell: Cell            # 제목 TD
    title_parts: tuple          # (반기/분기, 연결, 기본명)
    extra_title_cells: list     # 제목 테이블의 나머지 셀(기수 등)
    tables: list                # 헤더/데이터 테이블들
    sheet_name: str = ""

    @property
    def title_text(self) -> str:
        return self.title_cell.text


@dataclass
class Note:
    number: int
    title: str
    start: int
    end: int
    items: list = field(default_factory=list)  # (offset, kind, payload)
    header: Paragraph = None        # 헤더 내부 콘텐츠 구간 (번호부터)
    header_mappable: bool = False   # 통째 교체가 안전한 헤더인지


@dataclass
class Document:
    text: str
    tables: list
    cover_paragraphs: list
    cover_cells: list
    fs_blocks: list
    notes: list
    note_mode: str              # usermark | span-id | plain | none
    te_tables: list             # 외부감사 (TE 셀 포함 테이블)
    standalone_tus: list        # 테이블 밖 단위 표기 셀
    fs_unclassified: list = None   # H-1: 미분류 FS유사 제목 (침묵 탈락 금지)
    fs_dropped: list = None        # B-4: 유효 FS 제목이나 주석 이후라 탈락
    merged_notes: dict = None      # B-4: 주석 묶침 {번호: [포함 추정 번호]}


# ---------------------------------------------------------------------------
# 파싱
# ---------------------------------------------------------------------------

def _parse_attrs(s: str) -> dict:
    return {k.upper(): v for k, v in _ATTR_RE.findall(s)}


def _parse_table(text: str, m) -> Table:
    tbl = Table(start=m.start(), end=m.end())
    for tr in _TR_RE.finditer(text, m.start(), m.end()):
        row = []
        pos = tr.start()
        while True:
            om = _CELL_OPEN_RE.search(text, pos, tr.end())
            if not om:
                break
            tag = om.group(1)
            close = text.find(f"</{tag}>", om.end(), tr.end())
            if close < 0:
                break
            row.append(Cell(
                tag=tag,
                attrs=_parse_attrs(om.group(2)),
                start=om.end(),
                end=close,
                raw=text[om.end():close],
            ))
            pos = close + len(tag) + 3
        if row:
            tbl.rows.append(row)
    return tbl


def _is_title_table(tbl: Table):
    """FS 제목 테이블 판정 (스펙 2.3 패턴, 실제 공시 DSD 검증 반영).

    실제 구조: 1행 제목 + 기수(당/전기) + 회사명·단위 행 → 최대 4~5행.
    첫 행에 비어있지 않은 셀이 정확히 1개이고 그 텍스트가 FS 제목이면 채택.
    반환: (제목 셀, 제목 파트, 나머지 셀들) 또는 None
    """
    if not tbl.rows or len(tbl.rows) > 6:
        return None
    cells = list(tbl.all_cells())
    if len(cells) > 8:
        return None
    first_nonempty = [c for c in tbl.rows[0] if c.text]
    if len(first_nonempty) != 1:
        return None
    cell = first_nonempty[0]
    parts = match_fs_title(cell.text)
    if not parts:
        return None
    rest = [c for c in cells if c is not cell]
    return cell, parts, rest


def _note_title(header_text: str) -> str:
    """헤더 텍스트에서 번호 접두("1." 또는 중복 "1. 1.")를 뗀 제목."""
    first = header_text.splitlines()[0].strip() if header_text else ""
    return re.sub(r"^(\d+)\s*\.\s*(?:\1\s*\.\s*)?", "", first).strip()


def _find_note_headers(text: str, lo: int, hi: int, skip=None,
                       cr_boundaries=False, allow_skip=False):
    """주석 헤더 탐지 폴백 체인: USERMARK → SPAN ID → 평문 P.

    반환 항목: dict(num, pos, start, end, raw, mappable)
    mappable: 헤더 내부에 마크업이 없어 통째 교체가 안전한 경우.
    평문 P 모드는 헤더 경계가 불확실하므로 매핑하지 않는다.
    """
    for mode, pattern in (("usermark", _NOTE_USERMARK_RE),
                          ("span-id", _NOTE_SPANID_RE),
                          ("plain", _NOTE_PLAIN_RE)):
        matches = []
        seen_pos = set()
        for m in pattern.finditer(text, lo, hi):
            if skip and skip(m.start()):
                continue                # B-6-mini: 표 셀 안 P는 헤더 아님
            inner = m.group(1)
            seen_pos.add(m.start())
            matches.append({
                "num": int(m.group(2)), "pos": m.start(),
                "start": m.start(1), "end": m.end(1), "raw": inner,
                "mappable": mode != "plain" and "<" not in inner,
            })
        if mode == "plain":
            # B-6-mini: 융합형(제목+본문 한 P·SPAN 래핑 포함) 후보도
            # 합집합으로 — 최장 순차 체인 검증(_longest_chain)이 본문
            # 명세항('1.영업에서 창출된 현금흐름' 등) 오탐을 방어한다
            for m in _NOTE_FUSED_RE.finditer(text, lo, hi):
                if m.start() in seen_pos or (skip and skip(m.start())):
                    continue
                matches.append({
                    "num": int(m.group(2)), "pos": m.start(),
                    "start": m.start(1), "end": m.end(1),
                    "raw": m.group(1), "mappable": False,
                })
            if cr_boundaries:
                # B-6c: 문단 중간 &cr; 경계 후보 합집합 (콘텐츠 시작
                # 오프셋으로 중복 제거 — P 프리픽스형과 위치가 같다)
                seen_c1 = {x["start"] for x in matches}
                for m in _NOTE_CR_RE.finditer(text, lo, hi):
                    if m.start(1) in seen_c1 or \
                            (skip and skip(m.start())):
                        continue
                    matches.append({
                        "num": int(m.group(2)), "pos": m.start(),
                        "start": m.start(1), "end": m.end(1),
                        "raw": m.group(1), "mappable": False,
                    })
            matches.sort(key=lambda x: x["pos"])
        chained = _longest_chain(matches, allow_skip=allow_skip)
        if len(chained) >= 2 or (len(chained) == 1 and mode == "usermark"):
            return mode, chained
    return "none", []


def _longest_chain(matches, allow_skip=False):
    """1부터 시작해 +1씩 이어지는 가장 자연스러운 연속열만 채택.

    본문 안의 "1." 볼드 등 오탐을 걸러낸다. 1이 없으면 전체를 그대로 쓴다.
    allow_skip(B-6c 폴백 전용): TITLE로 확정된 주석 범위 안에서는
    오름차순(건너뜀 허용) 체인 — 결번이 있어도 붕괴하지 않는다.
    """
    if not matches:
        return []
    starts = [i for i, item in enumerate(matches) if item["num"] == 1]
    if not starts:
        return matches
    def _min_gap(chain):
        # B-6-mini: 동률 타이브레이크 — 헤더 간 최소 간격.
        # 본문 명세 나열 오탐('1.영업에서 창출된 현금흐름' 등)은
        # 항목이 다닥닥 붙어 간격이 작다 — 진짜 주석 체인이 이긴다.
        if len(chain) < 2:
            return 0
        return min(b["pos"] - a["pos"]
                   for a, b in zip(chain, chain[1:]))

    best = []
    for s in starts:
        chain = [matches[s]]
        expect = 2
        last = matches[s]["num"]
        for item in matches[s + 1:]:
            if allow_skip:
                if item["num"] > last:
                    chain.append(item)
                    last = item["num"]
            elif item["num"] == expect:
                chain.append(item)
                expect += 1
        if len(chain) > len(best) or \
                (len(chain) == len(best) and best and
                 _min_gap(chain) > _min_gap(best)):
            best = chain
    return best


def scan(text: str) -> Document:
    """contents.xml 전체 스캔 → 구조화된 Document."""
    tables = [_parse_table(text, m) for m in _TABLE_RE.finditer(text)]
    table_spans = [(t.start, t.end) for t in tables]

    def inside_table(pos: int) -> bool:
        return any(s <= pos < e for s, e in table_spans)

    # --- 표지 -------------------------------------------------------------
    cover_paragraphs, cover_cells = [], []
    cm = _COVER_RE.search(text)
    if cm:
        lo, hi = cm.start(), cm.end()
        for pm in _P_RE.finditer(text, lo, hi):
            if not inside_table(pm.start()):
                cover_paragraphs.append(
                    Paragraph(start=pm.start(1), end=pm.end(1), raw=pm.group(1)))
        for tm in _TITLE_RE.finditer(text, lo, hi):
            cover_paragraphs.append(
                Paragraph(start=tm.start(1), end=tm.end(1), raw=tm.group(1)))
        for t in tables:
            if lo <= t.start < hi:
                cover_cells.extend(t.all_cells())
        cover_paragraphs.sort(key=lambda p: p.start)

    # --- 재무제표 블록 ------------------------------------------------------
    fs_blocks = []
    fs_table_idx = set()
    fs_unclassified_raw = []       # H-1: FS유사지만 미판별 제목 (start, raw)
    for i, tbl in enumerate(tables):
        hit = _is_title_table(tbl)
        if hit:
            cell, parts, rest = hit
            fs_blocks.append(FSBlock(
                title_cell=cell, title_parts=parts,
                extra_title_cells=rest, tables=[]))
            fs_table_idx.add(i)
        elif tbl.rows and len(tbl.rows) <= 6                 and len(list(tbl.all_cells())) <= 8:
            fne = [c for c in tbl.rows[0] if c.text]
            if len(fne) == 1 and fs_title_unclassified(fne[0].text):
                fs_unclassified_raw.append(
                    (fne[0].start, fne[0].text.strip()))

    # --- 주석 헤더 ----------------------------------------------------------
    notes_lo = fs_blocks[0].title_cell.start if fs_blocks else 0
    # 첨부 재무제표 SECTION-1의 끝을 주석 상한으로 사용
    notes_hi = len(text)
    if fs_blocks:
        cm2 = _SECTION1_CLOSE_RE.search(text, notes_lo)
        if cm2:
            notes_hi = cm2.start()

    # B-6c: '주석' TITLE이 있으면 범위를 TITLE ~ 다음 TITLE로 한정 —
    # 후반 '외부감사 실시내용'의 번호 TITLE(1.~4.)·본문과 격리
    # (주석 범위 산정 단일 소스)
    ntm = _NOTES_TITLE_RE.search(text, notes_lo, notes_hi)
    titled = ntm is not None
    if titled:
        notes_lo = ntm.end()
        nxt = _TITLE_RE.search(text, ntm.end())
        if nxt and nxt.start() < notes_hi:
            notes_hi = nxt.start()

    note_mode, headers = _find_note_headers(text, notes_lo, notes_hi,
                                            skip=inside_table)
    if note_mode == "none" and titled:
        # B-6c 폴백: 헤더 일부가 문단 중간 &cr; 경계로만 존재해(공시본
        # 실측 — 결번으로 연속 체인 붕괴) 미검출인 경우, TITLE로 확정된
        # 주석 범위 안에서만 &cr; 후보 합집합 + 건너뜀 허용 체인 재시도
        note_mode, headers = _find_note_headers(
            text, notes_lo, notes_hi, skip=inside_table,
            cr_boundaries=True, allow_skip=True)
        if headers:
            note_mode = "plain-cr"
    notes = []
    for k, h in enumerate(headers):
        end = headers[k + 1]["pos"] if k + 1 < len(headers) else notes_hi
        header = Paragraph(start=h["start"], end=h["end"], raw=h["raw"])
        notes.append(Note(
            number=h["num"], title=_note_title(header.text),
            start=h["pos"], end=end,
            header=header, header_mappable=h["mappable"]))

    notes_start = headers[0]["pos"] if headers else notes_hi

    # B-6-mini: 주석 텍스트 2차 분할 — 마크업 경계 소진 후 잔여 블록의
    # 평문 'N. 제목' 경계 (융합형 허용). 편집기·수신물 공통.
    # 순차 번호 검증: 직전+1 우선이되 건너뜀 허용·역행 불허 —
    # 표 내부 숫자 오탐 억제. repack(_MAP)·FS 분할 불가침 —
    # 분할 실패 잔여는 기존 뭉침 배너(B-4) 체계로 노출된다.
    if notes:
        expanded = []
        for n in notes:
            search_from = n.header.end if n.header is not None else n.start
            cuts = []
            last = n.number
            for m in _NOTE_FUSED_RE.finditer(text, search_from, n.end):
                if inside_table(m.start()):
                    continue
                num = int(m.group(2))
                if num > last:          # 오름차순(건너뜀 허용)·역행 불허
                    cuts.append((num, m))
                    last = num
            if not cuts:
                expanded.append(n)
                continue
            bounds = [(n.number, n.start, n.header, n.title,
                       n.header_mappable)]
            for num, m in cuts:
                hdr = Paragraph(start=m.start(1), end=m.end(1),
                                raw=m.group(1))
                bounds.append((num, m.start(), hdr,
                               _note_title(hdr.text), False))
            for i, (num, pos, hdr, title, mp) in enumerate(bounds):
                end = bounds[i + 1][1] if i + 1 < len(bounds) else n.end
                expanded.append(Note(
                    number=num, title=title, start=pos, end=end,
                    header=hdr, header_mappable=mp))
        notes = expanded

    # 주석 본문 안의 소형 표(첫 셀이 "재무상태표" 등)로 인한 FS 오탐 제거
    # B-4: 단, 유효한 FS 제목이 주석 이후에 오는 경우(수신본 본문의
    # 별도 재무제표 섩션 등)는 침묵 탈락 금지 — 미분할 원문으로 노출
    fs_dropped = [(b.title_cell.start,
                   " ".join(b.title_parts[i] for i in (0, 1, 2) if
                            b.title_parts[i]))
                  for b in fs_blocks if b.title_cell.start >= notes_start]
    fs_blocks = [b for b in fs_blocks if b.title_cell.start < notes_start]
    fs_table_idx = {i for i in fs_table_idx if tables[i].start < notes_start}
    # H-1: 미분류 제목도 같은 상한 적용 (주석 속 셀 오탐 배제) 후 노출
    fs_unclassified = [t for pos, t in fs_unclassified_raw
                       if pos < notes_start]

    # --- FS 블록에 테이블 배정 (제목 테이블 이후 ~ 다음 제목/주석 시작 전) ----
    title_positions = sorted(
        [(b.title_cell.start, b) for b in fs_blocks], key=lambda x: x[0])
    for i, tbl in enumerate(tables):
        if i in fs_table_idx or tbl.start >= notes_start:
            continue
        owner = None
        for pos, block in title_positions:
            if pos < tbl.start:
                owner = block
            else:
                break
        if owner:
            owner.tables.append(tbl)

    # --- 표지 부속 테이블 (COVER/TOC 밖, 첫 FS 제목 이전 프런트매터) ---------
    if fs_blocks:
        first_title = min(b.title_cell.start for b in fs_blocks)
        skip_spans = []
        if cm:
            skip_spans.append((cm.start(), cm.end()))
        tm2 = _TOC_RE.search(text)
        if tm2:
            skip_spans.append((tm2.start(), tm2.end()))
        for i, t in enumerate(tables):
            if t.start < first_title and i not in fs_table_idx and \
                    not any(s <= t.start < e for s, e in skip_spans) and \
                    not (cm and cm.start() <= t.start < cm.end()):
                cover_cells.extend(t.all_cells())

    # --- 주석에 요소 배정 ----------------------------------------------------
    for note in notes:
        for tbl in tables:
            if note.start <= tbl.start < note.end:
                note.items.append((tbl.start, "table", tbl))
        # 헤더 P의 <P>는 주석 시작(SPAN 위치)보다 앞이므로 역탐색으로 찾는다.
        # SPAN 뒤 본문이 마크업 없으면 편집 가능한 첫 문단으로 매핑.
        if note.header is not None:
            p_open = text.rfind("<P", 0, note.header.start)
            if p_open >= 0:
                pm0 = _P_RE.match(text, p_open)
                if pm0 and pm0.end() <= note.end and \
                        pm0.start(1) <= note.header.start < pm0.end(1):
                    close = text.find("</SPAN>", note.header.end, pm0.end(1))
                    if close >= 0:
                        body_start = close + len("</SPAN>")
                        raw_body = text[body_start:pm0.end(1)]
                        if "<" not in raw_body:
                            note.items.append((
                                note.start, "para",
                                Paragraph(start=body_start, end=pm0.end(1),
                                          raw=raw_body)))
        for pm in _P_RE.finditer(text, note.start, note.end):
            if inside_table(pm.start()):
                continue
            note.items.append((
                pm.start(), "para",
                Paragraph(start=pm.start(1), end=pm.end(1), raw=pm.group(1))))
        for um in _TU_RE.finditer(text, note.start, note.end):
            if not inside_table(um.start()):
                note.items.append((
                    um.start(),
                    "unit",
                    Cell(tag="TU", attrs=_parse_attrs(um.group(1)),
                         start=um.start(2), end=um.end(2), raw=um.group(2)),
                ))
        note.items.sort(key=lambda x: x[0])

    # --- 외부감사 (TE 셀 포함 테이블, 스펙 2.8) ------------------------------
    te_tables = [t for t in tables
                 if any(c.tag == "TE" for c in t.all_cells())]

    # --- 테이블 밖 단독 TU (주석 범위 밖 포함) --------------------------------
    standalone_tus = []
    for um in _TU_RE.finditer(text):
        if inside_table(um.start()):
            continue
        if any(n.start <= um.start() < n.end for n in notes):
            continue  # 주석 items 에 이미 포함
        standalone_tus.append(
            Cell(tag="TU", attrs=_parse_attrs(um.group(1)),
                 start=um.start(2), end=um.end(2), raw=um.group(2)))

    _assign_sheet_names(fs_blocks)

    # B-4: 주석 묶침 감지 — 본문 안에 다른 번호의 주석 헤더가
    # 평문으로 남아 있으면(분할 실패) 해당 번호들을 기록
    merged_notes = {}
    note_num_re = re.compile(r"[>\n\r]\s*(\d{1,2})\s*[.．]\s*[가-힣]")
    for n in notes:
        body = text[n.start:n.end]
        extra = sorted({int(m.group(1))
                        for m in note_num_re.finditer(body)
                        if int(m.group(1)) != n.number and
                        int(m.group(1)) > n.number})
        if extra:
            merged_notes[n.number] = extra

    return Document(
        text=text,
        tables=tables,
        cover_paragraphs=cover_paragraphs,
        cover_cells=cover_cells,
        fs_blocks=fs_blocks,
        notes=notes,
        note_mode=note_mode,
        te_tables=te_tables,
        standalone_tus=standalone_tus,
        fs_unclassified=fs_unclassified,
        fs_dropped=fs_dropped,
        merged_notes=merged_notes,
    )


def _visible_text(seg: str) -> str:
    """마크업·개행 표기를 걷어낸 가시 문자만 (커버리지 문자량 기준)."""
    s = re.sub(r"<[^>]+>", "", seg)
    s = s.replace("&amp;cr;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", "", s)


def honesty_stats(doc: Document, text: str) -> dict:
    """B-5: 산출물 완전성 통계 — 시트화 커버리지·미시트화 블록·이질 흡수.

    - coverage: 시트로 옮겨진 원문 구간의 가시 문자량 / 전체 가시 문자량
    - uncovered: 어떤 시트에도 배정되지 않은 원문 블록 (가시 200자 이상)
    - absorbed: FS 시트 구간 안의 이질 마커(TITLE·주석형 헤더 무리) —
      다른 성격의 콘텐츠가 그 시트로 흡수되었다는 신호 (침묵 흡수 0)
    """
    spans = []
    for p in doc.cover_paragraphs:
        spans.append((p.start, p.end))
    for c in doc.cover_cells:
        spans.append((c.start, c.end))
    fs_spans = {}
    for b in doc.fs_blocks:
        lo = b.title_cell.start
        hi = max([t.end for t in b.tables] + [b.title_cell.end])
        fs_spans[b.sheet_name] = (lo, hi)
        spans.append((lo, hi))
    for n in doc.notes:
        spans.append((n.start, n.end))
    for t in doc.te_tables:
        spans.append((t.start, t.end))
    if doc.fs_dropped:
        spans.append((min(p for p, _t in doc.fs_dropped), len(text)))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    total_vis = len(_visible_text(text))
    covered_vis = sum(len(_visible_text(text[s:e])) for s, e in merged)
    uncovered = []
    prev = 0
    for s, e in merged + [[len(text), len(text)]]:
        gap = _visible_text(text[prev:s])
        if len(gap) >= 200:
            uncovered.append({"pos": prev, "chars": len(gap),
                              "preview": gap[:40]})
        prev = max(prev, e)

    table_spans = [(t.start, t.end) for t in doc.tables]

    def _outside(pos):
        return not any(s <= pos < e for s, e in table_spans)

    absorbed = {}
    for name, (lo, hi) in fs_spans.items():
        marks = []
        for m in _TITLE_RE.finditer(text, lo, hi):
            t_ = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if not t_:
                continue
            if doc.notes and t_.replace(" ", "") == "주석":
                # 주석 분할이 성공한 문서의 구획 제목 자체는 흡수 아님
                continue
            marks.append(f"제목 '{t_[:20]}'")
        heads = [m for m in _NOTE_FUSED_RE.finditer(text, lo, hi)
                 if _outside(m.start())]
        if len(heads) >= 2:
            marks.append(f"주석형 헤더 {len(heads)}개")
        if marks:
            absorbed[name] = marks

    return {
        "coverage": (covered_vis / total_vis) if total_vis else 1.0,
        "covered_chars": covered_vis, "total_chars": total_vis,
        "uncovered_blocks": uncovered,
        "absorbed": absorbed,
    }


def _assign_sheet_names(fs_blocks):
    """시트명 약칭 부여 (스펙 7.5 + P1 접두사 반영).

    포괄손익계산서: 손익계산서가 따로 있으면 PL1, 없으면 PL (4종/5종 동적).
    연결/반기 접두사는 시트명 앞에 붙인다 (예: 연결BS, 반기PL).
    """
    from .textutil import FS_ABBREV

    bases = [b.title_parts[2] for b in fs_blocks]
    has_separate_pl = "손익계산서" in bases

    used = set()
    for b in fs_blocks:
        period, consol, base = b.title_parts
        abbrev = FS_ABBREV[base]
        if base == "포괄손익계산서":
            abbrev = "PL1" if has_separate_pl else "PL"
        name = f"{period}{consol}{abbrev}" if (period or consol) else abbrev
        n, i = name, 2
        while n in used:
            n = f"{name}_{i}"
            i += 1
        used.add(n)
        b.sheet_name = n
