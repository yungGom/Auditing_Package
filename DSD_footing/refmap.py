# -*- coding: utf-8 -*-
"""
C1~C6 본표↔주석 레퍼런스 대사 (오프라인)
본표 행의 주석번호를 이용해 탐색 범위를 해당 주석으로 한정 → 우연일치 최소화
"""
import re, collections
import pdfplumber
from core import grid_info, norm, parse
from statements import read_rows, stmt_type, key
from notes import NOTE_HEAD, AMT

STMT_TAG = {"BS":"BS", "IS":"IS", "CI":"CI", "CF":"CF", "SCE":"SCE"}

def note_ranges(pdf):
    """주석번호 → 페이지 구간"""
    starts = {}
    for pi, page in enumerate(pdf.pages, 1):
        for ln in (page.extract_text() or "").split("\n"):
            t = ln.strip()
            if AMT.search(t): continue
            m = NOTE_HEAD.match(t)
            if m: starts.setdefault(int(m.group(1)), pi)
    seq = sorted(starts.items(), key=lambda x: x[1])
    rng = {}
    for i, (n, p) in enumerate(seq):
        end = (seq[i+1][1] - 1) if i+1 < len(seq) else len(pdf.pages)
        rng[n] = (p, end)
    return rng

def collect_main(pdf):
    """본표 항목 → [dict(tag,label,val,refs,page,table,row,col)]"""
    out = []
    for pi, page in enumerate(pdf.pages, 1):
        st = stmt_type(page.extract_text() or "")
        if st not in STMT_TAG: continue
        for ti, tb in enumerate(page.find_tables(), 1):
            data = tb.extract()
            try: G,K,V,hdr,ncol,nrow,numcols = grid_info(data)
            except Exception: continue
            # 주석열 위치 찾기
            njs = [j for j in range(min(3,ncol))
                   if any(re.fullmatch(r"주\s*석", norm(G[i][j])) for i in range(max(hdr,1)))]
            rows, nper = read_rows(data)
            for d,k,raw,vals,ip,it,ri,cof in rows:
                refs = set()
                for j in njs:
                    for tok in re.split(r"[,\s]+", norm(G[ri][j])):
                        if tok.isdigit(): refs.add(int(tok))
                for p_, v in vals.items():
                    if abs(v) < 1000: continue          # 소액·비율은 우연일치 위험
                    out.append(dict(tag=STMT_TAG[st], label=raw[:24], val=v, refs=refs,
                                    page=pi, table=ti, row=ri, col=cof.get(p_), period=p_,
                                    ncol=(njs[0] if njs else None)))
    return out

def collect_notes(pdf, rng):
    """주석 내 금액 → [dict(note,page,table,row,col,val,label)]"""
    inv = {}
    for n,(a,b) in rng.items():
        for p in range(a, b+1): inv.setdefault(p, set()).add(n)
    out = []
    for pi, page in enumerate(pdf.pages, 1):
        ns = inv.get(pi)
        if not ns: continue
        if stmt_type(page.extract_text() or ""): continue      # 본표 페이지 제외
        for ti, tb in enumerate(page.find_tables(), 1):
            data = tb.extract()
            try: G,K,V,hdr,ncol,nrow,numcols = grid_info(data)
            except Exception: continue
            for i in range(hdr, nrow):
                for j in numcols:
                    if K[i][j] != "NUM": continue
                    v = V[i][j]
                    if abs(v) < 1000: continue
                    out.append(dict(notes=ns, page=pi, table=ti, row=i, col=j,
                                    val=v, label=(G[i][0] or "")[:24]))
    return out

def build(pdf_path, tol=0.0):
    with pdfplumber.open(pdf_path) as pdf:
        rng   = note_ranges(pdf)
        mains = collect_main(pdf)
        nts   = collect_notes(pdf, rng)
    byval = collections.defaultdict(list)
    for n in nts: byval[round(n["val"], 2)].append(n)

    links = []      # (본표항목, 주석항목) 매칭
    unmatched = []
    for m in mains:
        if not m["refs"]: continue
        cands = [n for n in byval.get(round(m["val"],2), []) if n["notes"] & m["refs"]]
        if cands:
            links.append((m, cands))
        else:
            near = [n for v,lst in byval.items() if abs(v-m["val"]) <= tol and tol > 0
                    for n in lst if n["notes"] & m["refs"]]
            unmatched.append((m, near))
    # 주석간 레퍼: 같은 값이 다른 주석에도 등장하면 태그 누적
    for m, cs in links:
        for c in cs:
            others = {n for x in byval.get(round(c["val"],2), []) for n in x["notes"]
                      if n not in (c["notes"] & m["refs"])}
            c["also"] = sorted(others)[:2]
    return rng, mains, nts, links, unmatched

def marks(pdf_path, tol=0.0):
    """→ (본표 동그라미 목록, 주석 태그 목록, 차이 목록)"""
    rng, mains, nts, links, un = build(pdf_path, tol)
    circles = {}; tags = collections.defaultdict(list); diffs = []
    for m, cs in links:
        if m["ncol"] is None: continue
        k = (m["page"], m["table"], m["row"], m["ncol"])
        hit = set().union(*[c["notes"] & m["refs"] for c in cs]) if cs else set()
        circles.setdefault(k, set()).update(hit)
        for c in cs:
            lbl = "/" + m["tag"]
            for a in c.get("also", []):
                if f"FN{a}" not in lbl: lbl += f", FN{a}"
            tags[(c["page"], c["table"], c["row"], c["col"])].append(lbl)
    for m, near in un:
        if near:
            n0 = min(near, key=lambda n: abs(n["val"]-m["val"]))
            diffs.append(dict(page=m["page"], table=m["table"], row=m["row"], col=m["col"],
                              label=m["label"], val=m["val"], other=n0["val"],
                              diff=n0["val"]-m["val"], where=f"p{n0['page']}"))
    circles = [dict(page=p_, table=t_, row=r_, ncol=n_, notes=sorted(v))
               for (p_,t_,r_,n_), v in circles.items()]
    return circles, tags, diffs, links, un, mains

if __name__ == "__main__":
    P = "/mnt/user-data/uploads/_삼성전자_감사보고서_2026_03_10_.pdf"
    rng, mains, nts, links, un = build(P)
    withref = [m for m in mains if m["refs"]]
    print(f"주석 구간 {len(rng)}개 · 본표 금액 {len(mains)}건(주석참조 {len(withref)}건) · 주석 금액 {len(nts)}건")
    print(f"레퍼 성립 {len(links)}건 ({len(links)/max(len(withref),1)*100:.1f}%) · 미성립 {len(un)}건")
    print("\n[성립 샘플]")
    for m, cs in links[:10]:
        tgt = ", ".join(sorted({f"FN{min(c['notes'] & m['refs'])}" for c in cs}))
        print(f"  {m['tag']} p{m['page']} {m['label'][:20]:20s} {m['val']:>15,.0f} → {tgt} (후보 {len(cs)})")
    print("\n[미성립 샘플]")
    for m, near in un[:10]:
        print(f"  {m['tag']} p{m['page']} {m['label'][:20]:20s} {m['val']:>15,.0f} refs={sorted(m['refs'])}")
