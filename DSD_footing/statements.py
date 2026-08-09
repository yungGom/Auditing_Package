# -*- coding: utf-8 -*-
"""본표 전용 검증 — A5 가감구조 · B 본표간 연계 · C7 주석번호 (오프라인)"""
import re
from core import norm, parse, grid_info

# ── 라벨 계층 (한국 재무제표 관행) ─────────────────────────
ROMAN = re.compile(r"^\s*(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[IVX]{1,4})\s*[\.\)]")
ARABIC= re.compile(r"^\s*\d+\s*[\.\)]")
HANGUL= re.compile(r"^\s*[가나다라마바사아자차카타파하]\s*[\.\)]")

def label_depth(t):
    t = norm(t)
    if ROMAN.match(t):  return 3
    if ARABIC.match(t): return 2
    if HANGUL.match(t): return 1
    return 0

def key(t):
    """라벨 정규화 — 공백·괄호주석 제거"""
    t = norm(t)
    t = re.sub(r"^\s*(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[IVX]{1,4}|\d+|[가-하])\s*[\.\)]\s*", "", t)
    t = re.sub(r"\(.*?\)", "", t)
    return t.replace(" ", "")

# ── 기간 열 그룹핑: numcols를 (세부, 합계) 쌍으로 ──────────
TOTAL_KEY = re.compile(r"^(자산총계|부채총계|자본총계|부채와자본총계|합계|계|총계)$")

STMT = [("BS", re.compile(r"(연결|별도)?재무상태표")),
        ("CI", re.compile(r"(연결|별도)?포괄손익계산서")),
        ("IS", re.compile(r"(연결|별도)?손익계산서")),
        ("CF", re.compile(r"(연결|별도)?현금흐름표")),
        ("SCE",re.compile(r"(연결|별도)?자본변동표"))]

def stmt_type(page_text):
    """본표 페이지만 인식: 제목이 첫 3줄 안(공백 제거 후 완전일치) + '과목/구분' 헤더"""
    txt = page_text or ""
    lines = [l.strip() for l in txt.split("\n") if l.strip()][:3]
    if not lines: return None
    flat = txt.replace(" ", "")
    if "과목" not in flat and "구분" not in flat: return None
    for l in lines:
        c = l.replace(" ", "")
        if re.match(r"^[\d가-하][\.\)]", c): continue    # '나. 연결손익계산서' 등 주석 소제목 제외
        for name, rx in STMT:
            if rx.fullmatch(c): return name
    return None

# 재무제표 유형별 적용 규칙 (고정 템플릿)
APPLY = {"BS": ("A3","A5"), "CF": ("A3","A5"), "IS": ("A5",),
         "CI": ("A5",), "SCE": (), None: ()}

def period_cols(numcols, K=None, hdr=0, nrow=0):
    """열 구조 판정: 동시 출현하면 별개 기간, 배타적이면 (세부,합계) 계층쌍.
    삼성식(합계 별도열)과 일반식(단일열)을 모두 지원한다."""
    if K is None or len(numcols) < 2:
        return [(c,) for c in numcols]
    def co(a, b):
        both = sum(1 for i in range(hdr, nrow) if K[i][a]=="NUM" and K[i][b]=="NUM")
        any_ = sum(1 for i in range(hdr, nrow) if K[i][a]=="NUM" or  K[i][b]=="NUM")
        return both / any_ if any_ else 0.0
    out = []; i = 0
    while i < len(numcols):
        a = numcols[i]
        if i+1 < len(numcols) and co(a, numcols[i+1]) < 0.15:
            out.append((a, numcols[i+1])); i += 2      # 배타적 = 계층쌍
        else:
            out.append((a,)); i += 1                    # 동시출현 = 독립 기간
    return out

def read_rows(tb):
    """→ [(depth, key, raw, {periodIdx: value})]  본표형(세부/합계 2열) 전용"""
    G,K,V,hdr,ncol,nrow,numcols = grid_info(tb)
    if len(numcols) < 2: return [], 0
    pcs = period_cols(numcols, K, hdr, nrow)
    out = []
    for i in range(hdr, nrow):
        lab = G[i][0]
        if not lab: continue
        vals = {}; coldep = 0; colof = {}
        for pi, cols in enumerate(pcs):
            for ci, j in enumerate(cols):
                if K[i][j] == "NUM":
                    vals[pi] = V[i][j]; colof[pi] = j
                    coldep = max(coldep, ci + 1)   # 합계열이면 2
        if not vals: continue
        d = (coldep - 1) * 10 + label_depth(lab)   # 열 위치 우선, 라벨계층 보조
        out.append([d, key(lab), lab, vals, False, bool(TOTAL_KEY.match(key(lab))), i, colof])
    # 부모 판정: 다음 항목의 depth가 더 얕으면 부모, 아니면 말단
    for i in range(len(out)):
        nxt = out[i+1][0] if i+1 < len(out) else -1
        out[i][4] = nxt < out[i][0]
    return out, len(pcs)

# ── A3v2: 라벨계층 기반 누적 풋팅 ─────────────────────────
def foot_hier(tb):
    rows, nper = read_rows(tb)
    res = []
    for p in range(nper):
        stack = []
        for d, k, raw, vals, is_parent, is_tot, ri, colof in rows:
            if p not in vals or is_tot: continue
            while stack and stack[-1][0] <= d:
                dd, kk, rr, dv, acc, rri, rcj = stack.pop()
                res.append(dict(kind="A3", period=p, label=rr[:26], row=rri, col=rcj,
                                disp=dv, calc=sum(acc), n=(len(acc) if len(acc)>=2 else 0)))
                if stack: stack[-1][4].append(dv)
            if not is_parent:
                if stack: stack[-1][4].append(vals[p])
            else:
                stack.append((d, k, raw, vals[p], [], ri, colof.get(p)))
        while stack:
            dd, kk, rr, dv, acc, rri, rcj = stack.pop()
            res.append(dict(kind="A3", period=p, label=rr[:26], row=rri, col=rcj,
                            disp=dv, calc=sum(acc), n=(len(acc) if len(acc)>=2 else 0)))
            if stack: stack[-1][4].append(dv)
    return res

# ── A5: 가감 관계식 (고정 템플릿) ─────────────────────────
A5_RULES = [
 ("매출총이익",              [("+","매출액"),("-","매출원가")]),
 ("영업이익",                [("+","매출총이익"),("-","판매비와관리비")]),
 ("법인세비용차감전순이익",   [("+","영업이익"),("+","기타수익"),("-","기타비용"),
                              ("+","금융수익"),("-","금융비용")]),
 ("당기순이익",              [("+","법인세비용차감전순이익"),("-","법인세비용")]),
 ("총포괄손익",              [("+","당기순이익"),("+","기타포괄손익")]),
 ("현금및현금성자산의증가",   [("+","영업활동현금흐름"),("+","투자활동현금흐름"),
                              ("+","재무활동현금흐름"),("+","외화환산으로인한현금의")]),
 ("기말의현금및현금성자산",   [("+","기초의현금및현금성자산"),("+","현금및현금성자산의증가")]),
 ("부채와자본총계",          [("+","부채총계"),("+","자본총계")]),
 ("자산총계",                [("+","유동자산"),("+","비유동자산")]),
 ("부채총계",                [("+","유동부채"),("+","비유동부채")]),
]

def foot_a5(tb):
    rows, nper = read_rows(tb)
    res = []
    for p in range(nper):
        book = {}; rowof = {}; colof2 = {}
        for d,k,raw,vals,_ip,_it,ri,cof in rows:
            if p in vals and k not in book:
                book[k] = vals[p]; rowof[k] = ri; colof2[k] = cof.get(p)
        for tgt, terms in A5_RULES:
            if tgt not in book: continue
            if not all(any(t.startswith(nm) or nm.startswith(t) for t in book) for _,nm in terms):
                pass
            s = 0.0; got = 0
            for sg, nm in terms:
                hit = next((v for kk,v in book.items() if kk == nm), None)
                if hit is None:
                    hit = next((v for kk,v in book.items() if kk.startswith(nm)), None)
                if hit is None: continue
                s += hit if sg == "+" else -hit
                got += 1
            if got < len(terms): continue
            res.append(dict(kind="A5", period=p, label=tgt, row=rowof.get(tgt), col=colof2.get(tgt),
                            disp=book[tgt], calc=s, n=got))
    return res
