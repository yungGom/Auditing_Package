# -*- coding: utf-8 -*-
"""C7 주석번호 참조 정합성 (오프라인)"""
import re, pdfplumber
from core import grid_info, norm
NOTE_HEAD = re.compile(r"^\s*(\d{1,2})\.(?!\d)\s*(?![\d,]+$)\S[^:：]{0,40}[:：]?\s*$")
AMT = re.compile(r"\d{1,3}(,\d{3})+")
REF_SPLIT = re.compile(r"[,\s]+")

def run(pdf_path):
    declared = {}; refs = {}
    with pdfplumber.open(pdf_path) as pdf:
        for pi, page in enumerate(pdf.pages, 1):
            for ln in (page.extract_text() or "").split("\n"):
                t = ln.strip()
                if AMT.search(t): continue
                m = NOTE_HEAD.match(t)
                if m: declared.setdefault(int(m.group(1)), pi)
            for tb in page.extract_tables():
                try: G,K,V,hdr,ncol,nrow,numcols = grid_info(tb)
                except Exception: continue
                for j in range(min(3, ncol)):
                    if not any(re.fullmatch(r"주\s*석", norm(G[i][j])) for i in range(max(hdr,1))):
                        continue
                    for i in range(hdr, nrow):
                        for tok in REF_SPLIT.split(norm(G[i][j])):
                            if tok.isdigit(): refs.setdefault(int(tok), set()).add(pi)
    missing = sorted(n for n in refs if n not in declared)
    unref   = sorted(n for n in declared if n not in refs)
    seq_gap = [n for n in range(1, max(declared or [0]) + 1) if n not in declared]
    return declared, refs, missing, unref, seq_gap

if __name__ == "__main__":
    d,r,m,u,g = run("/mnt/user-data/uploads/_삼성전자_감사보고서_2026_03_10_.pdf")
    print(f"선언된 주석 {len(d)}개: {sorted(d)[:40]}")
    print(f"본표 참조 {len(r)}개: {sorted(r)}")
    print(f"참조됐으나 주석 없음: {m or '없음'}")
    print(f"주석 있으나 본표 미참조: {u or '없음'}")
    print(f"주석 번호 결번: {g or '없음'}")
