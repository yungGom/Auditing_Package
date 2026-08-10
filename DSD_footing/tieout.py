# -*- coding: utf-8 -*-
"""B1~B10 본표 간 연계 검증 (별도재무제표 기준, 오프라인)"""
import re
import pdfplumber
from core import grid_info, norm
from statements import read_rows, stmt_type, key, period_axis, pick_period

# 자본변동표 시점 라벨. 연차는 '(당기말)', 중간보고는 '(당반기말)'·'(당분기말)'.
SCE_END = re.compile(r"[(（]?\s*(당|전)\s*(반기|분기)?\s*기?\s*말\s*[)）]?$")
SCE_BEG = re.compile(r"[(（]?\s*(당|전)\s*(반기|분기)?\s*기?\s*초\s*[)）]?$")

# ── 계정 별칭 (고정 템플릿) ─────────────────────────────────
# key() 정규화 후 문자열 기준. 자동 추론 대신 명시 목록으로 둔다.
#  · 중간재무보고는 '당기'가 '반기/분기'로 바뀐다 (당기순이익 → 반기순이익)
#  · 결손 회사는 '이익잉여금'이 '결손금'으로 표시된다
#  · 자본변동표 총계 열 이름은 회사마다 '총 계' 또는 '합 계'
# 목록 앞쪽이 우선. 새 표기를 만나면 여기에만 추가한다.
ALIAS = {
 "당기순이익": ("당기순이익","반기순이익","분기순이익","중간순이익",
               "당기순손실","반기순손실","분기순손실"),
 "총포괄손익": ("총포괄손익","총포괄이익","총포괄손실",
               "반기총포괄손익","반기총포괄이익","반기총포괄손실",
               "분기총포괄손익","분기총포괄이익","분기총포괄손실",
               "총포괄손익소계","총포괄이익소계","총포괄손실소계"),
 "부채와자본총계": ("부채와자본총계","부채및자본총계"),
 "기말의현금및현금성자산": ("기말의현금및현금성자산","기말현금및현금성자산",
               "당반기말현금및현금성자산","당분기말현금및현금성자산",
               "반기말현금및현금성자산","분기말현금및현금성자산"),
 "기초의현금및현금성자산": ("기초의현금및현금성자산","기초현금및현금성자산"),
 "현금및현금성자산의증가": ("현금및현금성자산의증가","현금및현금성자산의순증가",
               "현금및현금성자산의증가감소","현금및현금성자산의감소"),
 "환율변동효과": ("현금및현금성자산의환율변동효과","외화환산으로인한현금의변동",
               "외화표시현금및현금성자산의환율변동효과",
               "외화표시현금및현금성자산의환산","환율변동효과"),
 # 자본 구성요소 — 자본변동표 '열 이름'과 재무상태표 '행 이름'을 같은 목록으로 푼다
 "주식발행초과금": ("주식발행초과금","자본잉여금"),
 "이익잉여금": ("이익잉여금","결손금","미처리결손금"),
 "기타자본항목": ("기타자본항목","기타포괄손익누계액","기타자본구성요소"),
 "총계": ("총계","합계"),
}
def _al(k): return ALIAS.get(k, (k,))

def _hit(d, k):
    """별칭을 순서대로 시도해 실제로 존재하는 키를 돌려준다."""
    for a in _al(k):
        for kk in d:
            if kk == a or kk.startswith(a): return kk
    return None

def collect(pdf_path):
    """본표에서 지표 수집 → book[stmt][key][period] = value"""
    book = {}; order = {}; axis = {}; sce = {}; sce_span = {}; consolidated = False
    with pdfplumber.open(pdf_path) as pdf:
        carry = None
        for pi, page in enumerate(pdf.pages, 1):
            txt = page.extract_text() or ""
            if "비지배지분" in txt or "연결재무상태표" in txt: consolidated = True
            st = stmt_type(txt)
            tbs = page.extract_tables()
            if not tbs: carry = None; continue
            data = tbs[0]
            if carry and st is None:
                try:
                    _,_,_,h0,nc0,_,_ = grid_info(data)
                    if h0 == 0 and nc0 == carry[2]: data = carry[0] + data; st = carry[1]
                except Exception: pass
            if st in ("BS","IS","CI","CF"):
                rows, nper = read_rows(data)
                ax, npc = period_axis(data)          # 기간 축(당/전 × 3개월/누적)
                prev = axis.get(st)
                if prev is None or (not prev[0] and ax):   # 판독된 축을 우선 보존
                    axis[st] = (ax, npc)
                d = book.setdefault(st, {}); o = order.setdefault(st, {})
                for dep,k,raw,vals,ip,it,ri,cof in rows:
                    if k and k not in d: d[k] = vals; o[k] = ri
                try:
                    _,_,_,_,ncL,_,_ = grid_info(tbs[-1]); carry = (tbs[-1], st, ncL)
                except Exception: carry = None
            elif st == "SCE":
                G,K,V,hdr,ncol,nrow,numcols = grid_info(data)
                hdrs = [norm(G[0][j]) for j in range(ncol)]
                cur = "전기"
                for i in range(hdr, nrow):
                    lab = norm(G[i][0])
                    me, mb = SCE_END.search(lab), SCE_BEG.search(lab)
                    m = me or mb
                    if m: cur = "당기" if m.group(1) == "당" else "전기"
                    tag = "END" if me else ("BEG" if mb else None)
                    # 반기말/분기말이면 재무상태표 '전기' 열(=직전 연차말)과 시점이 다르다
                    if me: sce_span[("END", cur)] = me.group(2)
                    kk = key(lab)
                    for j in numcols:
                        if K[i][j] != "NUM": continue
                        col = key(hdrs[j]) or f"c{j}"
                        if tag: sce[(tag, cur, col)] = V[i][j]
                        else:   sce.setdefault((cur, kk, col), V[i][j])
                carry = None
            else: carry = None
    return book, order, axis, sce, sce_span, consolidated

def g(book, axis, st, k, side):
    """side='당'|'전'. 기간 인덱스는 헤더에서, 계정명은 별칭표에서 해석한다.
    어느 쪽이든 해석 불가면 None → '미검증'. 추측하지 않는다."""
    ax, npc = axis.get(st, ({}, 0))
    p = pick_period(ax, npc, side)
    if p is None: return None
    d = book.get(st, {})
    kk = _hit(d, k)
    return d[kk].get(p) if kk else None

def sce_pt(sce, kind, tag, comp="총계"):
    """자본변동표 시점 행(END/BEG) 조회. 열 이름을 별칭으로 푼다."""
    for c in _al(comp):
        v = sce.get((kind, tag, c))
        if v is not None: return v
    return None

def sce_row(sce, tag, k, comp="총계"):
    """자본변동표 변동 행 조회. 행 이름·열 이름 모두 별칭으로 푼다."""
    for a in _al(k):
        for c in _al(comp):
            v = sce.get((tag, a, c))
            if v is not None: return v
    return None

CHK = []
def add(no, name, a, b, note=""):
    if a is None or b is None:
        CHK.append((no, name, None, None, "미검증", note)); return
    CHK.append((no, name, a, b, "OK" if abs(a-b) < 1e-9 else "차이", note))

def run(pdf_path):
    book, order, axis, sce, sce_span, cons = collect(pdf_path)
    CHK.clear()
    # 중간재무보고 판정: 손익/포괄손익에 3개월·누적 축이 있으면 중간보고다.
    interim = any(sp in ("3M", "누적")
                  for st in ("IS", "CI") if st in axis
                  for (sd, sp) in axis[st][0])

    def add_g(no, name, a, b, skip=False, why=""):
        """skip이면 값을 버리고 미검증으로 낸다 — 시점이 다른 것끼리 대사해
        가짜 '차이'를 만들지 않기 위함. 사유는 항목명에 남긴다."""
        if skip: CHK.append((no, name + why, None, None, "미검증", why.strip())); return
        add(no, name, a, b)

    # 중간보고에서 자본변동표·현금흐름표의 '전기'는 전년 동기간(전반기말)이고
    # 재무상태표의 '전기' 열은 직전 연차말이다. 교차 대사하면 시점이 어긋난다.
    WHY = " [중간보고: 전반기말 vs 전기말 — 시점 상이]"

    for side, tag in (("당", "당기"), ("전", "전기")):
        s_ = f"({tag}) "
        cross = interim and side == "전"
        add("B1", s_+"자산총계 = 부채와자본총계",
            g(book,axis,"BS","자산총계",side), g(book,axis,"BS","부채와자본총계",side))
        add("B2", s_+"IS 당기순이익 = 포괄손익 당기순이익",
            g(book,axis,"IS","당기순이익",side), g(book,axis,"CI","당기순이익",side))
        add("B3", s_+"포괄손익 총포괄손익 = 자본변동표 총포괄손익",
            g(book,axis,"CI","총포괄손익",side), sce_row(sce, tag, "총포괄손익"))
        add("B4", s_+"IS 당기순이익 = 자본변동표 당기순이익",
            g(book,axis,"IS","당기순이익",side), sce_row(sce, tag, "당기순이익"))
        add("B5", s_+"IS 당기순이익 = CF 당기순이익",
            g(book,axis,"IS","당기순이익",side), g(book,axis,"CF","당기순이익",side))
        add_g("B6", s_+"자본변동표 기말 총계 = BS 자본총계",
            sce_pt(sce,"END",tag,"총계"), g(book,axis,"BS","자본총계",side), cross, WHY)
        for nm, bk in (("자본금","자본금"),("주식발행초과금","주식발행초과금"),
                       ("이익잉여금","이익잉여금"),("기타자본항목","기타자본항목")):
            add_g("B6", s_+f"자본변동표 기말 {nm} = BS {nm}",
                sce_pt(sce,"END",tag,nm), g(book,axis,"BS",bk,side), cross, WHY)
        add("B7", s_+"자본변동표 기초 총계 = 전기말 자본총계",
            sce_pt(sce,"BEG",tag,"총계") if side=="당" else None,
            g(book,axis,"BS","자본총계","전") if side=="당" else None)
        add_g("B8", s_+"CF 기말현금 = BS 현금및현금성자산",
            g(book,axis,"CF","기말의현금및현금성자산",side),
            g(book,axis,"BS","현금및현금성자산",side), cross, WHY)
        add("B9", s_+"CF 기초현금 = 전기말 BS 현금",
            g(book,axis,"CF","기초의현금및현금성자산",side) if side=="당" else None,
            g(book,axis,"BS","현금및현금성자산","전") if side=="당" else None)
        b_end = g(book,axis,"CF","기말의현금및현금성자산",side)
        b_beg = g(book,axis,"CF","기초의현금및현금성자산",side)
        inc   = g(book,axis,"CF","현금및현금성자산의증가",side)
        fx    = g(book,axis,"CF","환율변동효과",side)
        # 환율변동효과가 '증가' 행보다 뒤·'기말' 행보다 앞에 있으면 별도 가산 항목이고,
        # 앞에 있으면 이미 '증가'에 포함된 구성요소다. 규칙을 완화하지 않고 구조로 가른다.
        o = order.get("CF", {})
        ri = lambda k: (o.get(_hit(o, k)) if _hit(o, k) is not None else None)
        r_inc, r_fx, r_end = ri("현금및현금성자산의증가"), ri("환율변동효과"), ri("기말의현금및현금성자산")
        sep = None not in (r_inc, r_fx, r_end) and r_inc < r_fx < r_end
        extra = (fx or 0.0) if sep else 0.0
        # 구조적 안전장치: 증가행~기말행 사이에 값이 있는데 공식의 어느 개념으로도
        # 해석되지 않는 행이 있으면 미검증으로 낸다. 별칭 누락이 조용한 미검증이 아니라
        # 가짜 '차이'를 만드는 것이 결함이다 (휴맥스 B10 사례) — 가짜 차이 금지.
        _ax, _npc = axis.get("CF", ({}, 0))
        _p = pick_period(_ax, _npc, side)
        mid_unres = False
        if None not in (r_inc, r_end, _p):
            known = {kk for c_ in ("현금및현금성자산의증가", "환율변동효과",
                                    "기초의현금및현금성자산", "기말의현금및현금성자산")
                     for kk in [_hit(o, c_)] if kk is not None}
            for kk_, rr_ in o.items():
                if r_inc < rr_ < r_end and kk_ not in known \
                   and book.get("CF", {}).get(kk_, {}).get(_p) is not None:
                    mid_unres = True; break
        if mid_unres:
            CHK.append(("B10", s_+"CF 증감 = 기말 − 기초 [증가~기말 사이 미해석 행 — 별칭 확인 필요]",
                        None, None, "미검증", "미해석 중간 행"))
        else:
            add("B10", s_+"CF 증감 = 기말 − 기초" + (" − 환율변동효과" if sep else ""),
                inc, (b_end - b_beg - extra) if (b_end is not None and b_beg is not None) else None)
    return CHK, cons

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python tieout.py <보고서.pdf>"); sys.exit(2)
    P = sys.argv[1]
    res, cons = run(P)
    ok = sum(1 for r in res if r[4]=="OK"); ng = sum(1 for r in res if r[4]=="차이")
    sk = sum(1 for r in res if r[4]=="미검증")
    print(f"연결 구조 감지: {cons}")
    print(f"B 검증 {len(res)}건 — OK {ok} / 차이 {ng} / 미검증 {sk}\n" + "-"*74)
    for no,nm,a,b,v,_ in res:
        av = f"{a:,.0f}" if a is not None else "-"; bv = f"{b:,.0f}" if b is not None else "-"
        print(f" {no:4s} {nm[:44]:44s} {av:>16s} {bv:>16s}  {v}")
