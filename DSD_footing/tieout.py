# -*- coding: utf-8 -*-
"""B1~B10 본표 간 연계 검증 (별도재무제표 기준, 오프라인)"""
import re
import pdfplumber
from core import grid_info, norm
from statements import read_rows, stmt_type, key

SCE_END = re.compile(r"(당기말|전기말)\)?$")
SCE_BEG = re.compile(r"(당기초|전기초)\)?$")

def collect(pdf_path):
    """본표에서 지표 수집 → book[stmt][key][period] = value"""
    book = {}; sce = {}; consolidated = False
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
                d = book.setdefault(st, {})
                for dep,k,raw,vals,ip,it,ri,cof in rows:
                    if k and k not in d: d[k] = vals
                try:
                    _,_,_,_,ncL,_,_ = grid_info(tbs[-1]); carry = (tbs[-1], st, ncL)
                except Exception: carry = None
            elif st == "SCE":
                G,K,V,hdr,ncol,nrow,numcols = grid_info(data)
                hdrs = [norm(G[0][j]) for j in range(ncol)]
                cur = "전기"
                for i in range(hdr, nrow):
                    lab = norm(G[i][0])
                    if "당기초" in lab or "당기말" in lab: cur = "당기"
                    elif "전기초" in lab or "전기말" in lab: cur = "전기"
                    tag = ("END" if SCE_END.search(lab) else
                           "BEG" if SCE_BEG.search(lab) else None)
                    kk = key(lab)
                    for j in numcols:
                        if K[i][j] != "NUM": continue
                        col = key(hdrs[j]) or f"c{j}"
                        if tag: sce[(tag, cur, col)] = V[i][j]
                        else:   sce.setdefault((cur, kk, col), V[i][j])
                carry = None
            else: carry = None
    return book, sce, consolidated

def g(book, st, k, p=0):
    d = book.get(st, {})
    for kk, v in d.items():
        if kk == k or kk.startswith(k): return v.get(p)
    return None

CHK = []
def add(no, name, a, b, note=""):
    if a is None or b is None:
        CHK.append((no, name, None, None, "미검증", note)); return
    CHK.append((no, name, a, b, "OK" if abs(a-b) < 1e-9 else "차이", note))

def run(pdf_path):
    book, sce, cons = collect(pdf_path)
    CHK.clear()
    for p, tag in ((0, "당기"), (1, "전기")):
        s = f"({tag}) "
        add("B1", s+"자산총계 = 부채와자본총계",
            g(book,"BS","자산총계",p), g(book,"BS","부채와자본총계",p))
        add("B2", s+"IS 당기순이익 = 포괄손익 당기순이익",
            g(book,"IS","당기순이익",p), g(book,"CI","당기순이익",p))
        add("B3", s+"포괄손익 총포괄손익 = 자본변동표 총포괄손익",
            g(book,"CI","총포괄손익",p), sce.get((tag,"총포괄손익","총계")))
        add("B4", s+"IS 당기순이익 = 자본변동표 당기순이익",
            g(book,"IS","당기순이익",p), sce.get((tag,"당기순이익","총계")))
        add("B5", s+"IS 당기순이익 = CF 당기순이익",
            g(book,"IS","당기순이익",p), g(book,"CF","당기순이익",p))
        add("B6", s+"자본변동표 기말 총계 = BS 자본총계",
            sce.get(("END", tag, "총계")), g(book,"BS","자본총계",p))
        for nm, bk in (("자본금","자본금"),("주식발행초과금","주식발행초과금"),
                       ("이익잉여금","이익잉여금"),("기타자본항목","기타자본항목")):
            add("B6", s+f"자본변동표 기말 {nm} = BS {nm}",
                sce.get(("END", tag, nm)), g(book,"BS",bk,p))
        add("B7", s+"자본변동표 기초 총계 = 전기말 자본총계",
            sce.get(("BEG", tag, "총계")),
            sce.get(("END","전기","총계")) if tag=="당기" else None)
        add("B8", s+"CF 기말현금 = BS 현금및현금성자산",
            g(book,"CF","기말의현금및현금성자산",p), g(book,"BS","현금및현금성자산",p))
        add("B9", s+"CF 기초현금 = 전기말 BS 현금",
            g(book,"CF","기초의현금및현금성자산",p),
            g(book,"BS","현금및현금성자산",p+1) if p==0 else None)
        b_end = g(book,"CF","기말의현금및현금성자산",p)
        b_beg = g(book,"CF","기초의현금및현금성자산",p)
        add("B10", s+"CF 증감 = 기말 − 기초",
            g(book,"CF","현금및현금성자산의증가",p),
            (b_end - b_beg) if (b_end is not None and b_beg is not None) else None)
    return CHK, cons

if __name__ == "__main__":
    P = "/mnt/user-data/uploads/_삼성전자_감사보고서_2026_03_10_.pdf"
    res, cons = run(P)
    ok = sum(1 for r in res if r[4]=="OK"); ng = sum(1 for r in res if r[4]=="차이")
    sk = sum(1 for r in res if r[4]=="미검증")
    print(f"연결 구조 감지: {cons}")
    print(f"B 검증 {len(res)}건 — OK {ok} / 차이 {ng} / 미검증 {sk}\n" + "-"*74)
    for no,nm,a,b,v,_ in res:
        av = f"{a:,.0f}" if a is not None else "-"; bv = f"{b:,.0f}" if b is not None else "-"
        print(f" {no:4s} {nm[:44]:44s} {av:>16s} {bv:>16s}  {v}")
