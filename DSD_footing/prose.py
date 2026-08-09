# -*- coding: utf-8 -*-
"""
줄글(서술문) 표기 검토 — 규칙 기반, 완전 오프라인
표 영역 밖 본문에서 표기 오류 후보를 찾아 위치를 반환. 외부 맞춤법 API 미사용.
정밀도 우선: 확실한 것만 지적하고, 애매하면 지적하지 않는다.
"""
import re

def jong(ch):
    """종성 코드. 0=받침없음, 4=ㄴ, 8=ㄹ"""
    if not ("가" <= ch <= "힣"): return None
    return (ord(ch) - 0xAC00) % 28

# 율/률 · 열/렬 : 모음 또는 ㄴ 받침 뒤 → 율/열, 그 외 → 률/렬
def check_yul(text):
    out = []
    for m in re.finditer(r"([가-힣])(률|율|렬|열)", text):
        prev, suf = m.group(1), m.group(2)
        j = jong(prev)
        if j is None: continue
        soft = j in (0, 4)                       # 받침없음 또는 ㄴ
        if suf == "률" and soft: out.append((m.start(), prev+suf, f"'{prev}율'이 올바른 표기"))
        elif suf == "율" and not soft: out.append((m.start(), prev+suf, f"'{prev}률'이 올바른 표기"))
        elif suf == "렬" and soft: out.append((m.start(), prev+suf, f"'{prev}열'이 올바른 표기"))
    return out

RULES = [
    # ── 감사보고서 특화 오타 ──
    (r"재무재표",                    "'재무제표'의 오기",              "H"),
    (r"손익게산서|손익계산써",        "'손익계산서'의 오기",            "H"),
    (r"현금흐름프|현금흐릅표",        "'현금흐름표'의 오기",            "H"),
    (r"([가-힣]{2,})\1",             "어절 중복 가능",                 "M"),
    (r"주식회사\s*주식회사",          "중복 표기",                     "H"),
    (r"내부회계관리재도",             "'제도'의 오기",                  "H"),
    (r"충당부체|충담금|대손총당금",    "계정과목 오기",                  "H"),
    # ── 표준 표기 ──
    (r"됬|되요(?![가-힣])|됀",       "'됐·돼요'가 올바른 표기",         "H"),
    (r"있읍니다|없읍니다|입니당",     "'-습니다'가 올바른 표기",         "H"),
    (r"몇일",                        "'며칠'이 올바른 표기",            "H"),
    (r"갯수",                        "'개수'가 올바른 표기",            "H"),
    (r"웬지",                        "'왠지'가 올바른 표기",            "H"),
    (r"회계년도|사업년도|당해년도",    "'-연도'가 올바른 표기",           "H"),
    (r"년말|년초(?![가-힣])",         "'연말·연초'가 올바른 표기",       "H"),
    (r"싯가|시가총액액",              "표기 확인",                      "M"),
    # ── 문장부호 ──
    (r"(?<![\.\s])[,\.]{2,}(?![\.\s])", "문장부호 중복",                "H"),
    (r"[가-힣]\s+[,\.]",             "문장부호 앞 불필요한 공백",        "H"),
    (r"\(\s+|\s+\)",                 "괄호 안쪽 불필요한 공백",          "M"),
]
COMPILED = [(re.compile(p), msg, lv) for p, msg, lv in RULES]

KOR  = re.compile(r"[가-힣]")
DOTS = re.compile(r"\.{4,}")
AMT  = re.compile(r"\d{1,3}(,\d{3})+")

def in_tables(w, boxes, pad=2.0):
    for x0, t0, x1, b0 in boxes:
        if w["x0"] >= x0-pad and w["x1"] <= x1+pad and w["top"] >= t0-pad and w["bottom"] <= b0+pad:
            return True
    return False

def lines_outside_tables(page):
    boxes = [t.bbox for t in page.find_tables()]
    ws = [w for w in page.extract_words() if not in_tables(w, boxes)]
    rows = {}
    for w in ws: rows.setdefault(round(w["top"]), []).append(w)
    out = []
    for top in sorted(rows):
        seq = sorted(rows[top], key=lambda w: w["x0"])
        text = ""; spans = []
        for w in seq:
            if text: text += " "
            spans.append((len(text), len(text)+len(w["text"]), w))
            text += w["text"]
        out.append((text, spans))
    return out

FOOTER = re.compile(r"(전자공시시스템|dart\.fss\.or\.kr|^Page\s|^\d+$|\(단위\s*[:：])")

def paragraphs(page, min_kor_line=4, min_kor_para=30):
    """줄글 문단 단위로 묶어 반환 → [dict(bbox_last, nline, text)]
    표·목차·머리말·꼬리말 제외. 검토 완료(/) 마크 대상."""
    lines = []
    for text, spans in lines_outside_tables(page):
        if not spans: continue
        if DOTS.search(text) or FOOTER.search(text.strip()): continue
        if len(KOR.findall(text)) < min_kor_line: continue
        w0 = spans[0][2]; wl = spans[-1][2]
        lines.append(dict(text=text, top=w0["top"], bottom=w0["bottom"],
                          x_end=wl["x1"], spans=spans))
    paras = []; cur = []
    for i, ln in enumerate(lines):
        if cur:
            lh = max(cur[-1]["bottom"] - cur[-1]["top"], 8.0)
            gap = ln["top"] - cur[-1]["bottom"]
            if gap > lh * 1.1:                  # 빈 줄 이상 벌어지면 문단 분리
                paras.append(cur); cur = []
        cur.append(ln)
    if cur: paras.append(cur)
    out = []
    for p in paras:
        body = " ".join(l["text"] for l in p)
        if len(KOR.findall(body)) < min_kor_para: continue
        last = p[-1]
        out.append(dict(bbox=(last["x_end"], last["top"], last["bottom"]),
                        nline=len(p), text=body[:60]))
    return out

def _at(spans, pos):
    return next((w for s, e, w in spans if s <= pos < e), None)

def check_page(page, min_kor=8):
    """→ [dict(text, msg, level, bbox)] · 줄글만 대상, 목차·수치행 제외"""
    res = []
    for text, spans in lines_outside_tables(page):
        if DOTS.search(text): continue                 # 목차 점선
        if len(KOR.findall(text)) < min_kor: continue  # 줄글만
        if AMT.search(text) and len(KOR.findall(text)) < 15: continue
        hits = [(m.start(), m.group()[:20], msg, lv)
                for rx, msg, lv in COMPILED for m in rx.finditer(text)]
        hits += [(p, t, msg, "H") for p, t, msg in check_yul(text)]
        for pos, t, msg, lv in hits:
            w = _at(spans, pos)
            if w: res.append(dict(text=t, msg=msg, level=lv,
                                  bbox=(w["x0"], w["top"], w["x1"], w["bottom"])))
    return res
