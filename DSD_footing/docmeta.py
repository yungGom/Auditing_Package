# -*- coding: utf-8 -*-
"""docmeta — 문서 메타(제목·목차·표 이름) 추출. 화면(marks.json v2 document)용.

판정에 관여하지 않는다. 여기서 뽑는 값이 틀려도 풋팅 결과는 바뀌지 않는다 —
다만 **조용히 빈 값을 만들지 않는다**: 못 뽑으면 None으로 두고 호출부가
UNRESOLVED_LABEL / 폴백 로그로 표면화한다(2026-08-25 승인 조건 ⑤·H).

탐색 방식은 refmap.unit_texts(표 bbox 위쪽 최근접 '(단위:)' 표기)와 같은 패턴이다 —
새 발상이 아니라 검증된 경로를 재사용한다. 완전 오프라인.
"""
import re
from notes import NOTE_HEAD, AMT
from statements import stmt_type

# 표 제목 후보에서 걷어낼 것들
_UNIT_LINE = re.compile(r"^\(?\s*단\s*위\s*[:：]")
_TAIL = re.compile(r"(는|은)?\s*다음과\s*같습니다\.?\s*$")
_PAGE_FOOT = re.compile(r"전자공시시스템|dart\.fss\.or\.kr")
# 주석 소제목 시작 표지 — '가.' / '(1)' / '1.' 로 시작하는 줄
_CAP_START = re.compile(r"^\s*(?:[(（]\s*\d+\s*[)）]|[가-하]\.|\d+\.)\s*\S")

# 표 위 몇 pt까지를 그 표의 제목으로 볼 것인가. 이보다 멀면 남의 문단이다.
CAPTION_REACH = 140.0


def despace(s):
    """'반 기 연 결 재 무 제 표' → '반기연결재무제표'.
    DSD 표지·본표 제목은 글자 사이에 공백을 넣어 조판한다. 전 토큰이 1글자일 때만
    붙인다 — '제 4 기 반기'처럼 섞인 줄은 건드리지 않는다."""
    toks = (s or "").split()
    if len(toks) >= 3 and all(len(t) == 1 for t in toks):
        return "".join(toks)
    return (s or "").strip()


def title(pdf):
    """→ (제목, 폴백여부). 표지(2면)에서 '회사명 / …재무제표에 대한 / …보고서'를 읽는다.

    4축 실측(2026-08-25) 공통 구조:
        66~88pt   회사명            예) 조선내화 주식회사와 그 종속기업
        146~177pt …재무제표 에 대 한  예) 반 기 연 결 재 무 제 표 에 대 한
        177~207pt …보고서            예) 검 토 보 고 서
    """
    try:
        lines = [despace(l["text"]) for l in pdf.pages[1].extract_text_lines()[:6]]
    except Exception:
        return None, True
    if not lines:
        return None, True
    company = lines[0].strip()
    scope = report = ""
    for t in lines[1:]:
        if t.endswith("에대한") or t.endswith("에 대한"):
            scope = re.sub(r"에\s*대한$", "", t).strip()
        elif t.endswith("보고서") and not report:
            report = t.strip()
    if not company or not report:
        return None, True
    name = f"{company} — {(scope + ' ') if scope else ''}{report}".strip()
    return name, False


def headings(pdf):
    """주석 헤더 위치 → [(page, top, 번호, 라벨)] 페이지·좌표 순 정렬.

    notes.NOTE_HEAD/AMT를 그대로 재사용한다(같은 판정 규칙, 좌표만 추가). 페이지 단위
    구간(refmap.note_ranges)을 쓰지 않는 이유는 l2_extract와 같다 — 한 페이지에서 두
    주석이 시작하면 페이지 범위가 역전돼 표가 남의 주석에 붙는다."""
    out = []
    for pi, page in enumerate(pdf.pages, 1):
        for ln in page.extract_text_lines():
            t = ln["text"].strip()
            if AMT.search(t):
                continue
            m = NOTE_HEAD.match(t)
            if m:
                out.append((pi, ln["top"], int(m.group(1)), t))
    out.sort(key=lambda x: (x[0], x[1]))
    return out


def sections(pdf, heads, stmt_pages):
    """→ [{id, label, page, depth}] · 본표(depth 0) + 주석 항목(depth 1).

    stmt_pages: {page: stmt_type} — final.py가 이미 페이지별로 판정한 것을 넘겨받는다
    (같은 판정을 두 번 하지 않는다)."""
    out = []
    seen_stmt = set()
    for pi, st in sorted(stmt_pages.items()):
        if st in seen_stmt:
            continue                      # 분할된 본표는 첫 페이지만 목차에 올린다
        seen_stmt.add(st)
        label = None
        try:
            for l in pdf.pages[pi - 1].extract_text_lines()[:3]:
                d = despace(l["text"])
                if d.endswith(("표", "계산서", "서")) and len(d) >= 5:
                    label = d
                    break
        except Exception:
            pass
        out.append({"id": st, "label": label or st, "page": pi, "depth": 0,
                    "anchor": (pi, 0.0)})
    for pi, top, no, text in heads:
        out.append({"id": f"n{no}", "label": text, "page": pi, "depth": 1,
                    "anchor": (pi, top)})
    out.sort(key=lambda s: s["anchor"])
    return out


def section_of(secs, page, top):
    """(page, top) 이전(≤)의 마지막 섹션 id. 없으면 None — 억지로 붙이지 않는다."""
    best = None
    for s in secs:
        if s["anchor"] <= (page, top):
            best = s["id"]
        else:
            break
    return best


def table_caption(lines, tbl_bbox):
    """표 bbox 위쪽 제목 줄 → 문자열. 못 찾으면 None(호출부가 UNRESOLVED_LABEL).

    '가장 가까운 줄'을 그대로 쓰면 줄바꿈된 문장의 꼬리("…고 있습니다")를 집는다.
    DSD 주석은 표 앞에 반드시 소제목 문장을 둔다("가. …의 내역은 다음과 같습니다.")
    → 소제목 시작 표지(가./(1)/1.)를 가진 줄을 우선하고, 없으면 '다음과 같습니다'로
    끝나는 줄을 쓴다. 둘 다 없으면 **추측하지 않고 None**을 낸다.

    lines: page.extract_text_lines() 결과 (페이지당 한 번만 뽑아 재사용)."""
    top = tbl_bbox[1]
    cands = []
    for ln in lines:
        b = ln.get("bottom", ln["top"])
        if b > top or top - b > CAPTION_REACH:
            continue                       # 표 아래이거나 너무 멀다(남의 문단)
        t = (ln["text"] or "").strip()
        if not t or len(t) < 4:
            continue
        if _UNIT_LINE.match(t) or _PAGE_FOOT.search(t) or AMT.search(t):
            continue
        cands.append((b, t))
    cands.sort(key=lambda x: -x[0])        # 표에 가까운 줄부터
    for _, t in cands:
        if _CAP_START.match(t):
            return _clean_caption(t)
    for _, t in cands:
        if _TAIL.search(t):
            return _clean_caption(t)
    return None


def _clean_caption(t):
    return _TAIL.sub("", t).strip(" .·:") or None


def with_note(caption, note_no):
    """'주석N {제목}' — 제목이 이미 그 번호로 시작하면(예: '15. 금융수익…') 덧붙이지
    않는다('주석15 15. 금융수익' 같은 중복 방지)."""
    if not caption:
        return caption
    if re.match(rf"^\s*{note_no}\s*[.．)]", caption):
        return f"주석{caption}"
    return f"주석{note_no} {caption}"
