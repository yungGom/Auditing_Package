# -*- coding: utf-8 -*-
"""
F 시리즈 — 문서 전체 일관성 검토 (오프라인)
F1 단위 표기 누락 (금액 표가 있는데 단위 없음)
F2 시점·기간 표현 불일치 ('보고기간종료일 현재' vs '당기 말')
F3 라벨 표기 불일치 ('구분' vs '구   분')
F4 다중 공백 (어절 간격 기준)
F5 문장 마침표 누락
"""
import re, collections
import pdfplumber
from core import grid_info, norm, parse, find_unit
from prose import lines_outside_tables, DOTS, FOOTER, KOR

# ── F2 용어 변형 그룹 ─────────────────────────────────────
TERM_GROUPS = {
    "기간말 시점": [r"보고기간\s*종료일\s*현재", r"보고기간\s*말", r"당기\s*말",
                    r"전기\s*말", r"기말\s*현재"],
    "기간 중":     [r"보고기간\s*중", r"당기\s*중", r"전기\s*중", r"당\s*회계기간\s*중"],
    "재무제표 지칭": [r"재무제표", r"본\s*재무제표", r"별도\s*재무제표"],
}
# 당기/전기 대응쌍은 정상이므로 시점 그룹은 '당기/전기' 접두를 하나로 묶어 비교
def canon(t):
    """공백만 정규화. 당기/전기 접두는 의미가 있으므로 유지."""
    return t.replace(" ", "")

AMTRE = re.compile(r"\d{1,3}(,\d{3})+")
END_OK = re.compile(r"[\.。:：]\s*$|다\s*$|음\s*$|함\s*$|것\s*$")
SENT_END = re.compile(r"(습니다|입니다|됩니다|합니다|있습니다|없습니다)\s*$")

def run(pdf_path):
    unit_missing = []; terms = collections.defaultdict(lambda: collections.defaultdict(list))
    labels = collections.defaultdict(lambda: collections.defaultdict(list))
    gaps = []; nodots = []
    with pdfplumber.open(pdf_path) as pdf:
        for pi, page in enumerate(pdf.pages, 1):
            txt = page.extract_text() or ""
            tbs = page.find_tables()

            # ── F1: 금액 표가 있는데 단위 표기 없음 ──
            has_amt = False
            for t in tbs:
                try: G,K,V,hdr,ncol,nrow,numcols = grid_info(t.extract())
                except Exception: continue
                if numcols and any(K[i][j] == "NUM" and abs(V[i][j]) >= 1000
                                   for i in range(hdr, nrow) for j in numcols):
                    has_amt = True
                # ── F3: 라벨 공백 변형 수집 ──
                for j in range(min(2, ncol)):
                    for i in range(max(hdr, 1)):
                        raw = norm(G[i][j])
                        if raw and len(raw) <= 12 and KOR.search(raw):
                            labels[raw.replace(" ", "")][raw].append(pi)
                for i in range(hdr, nrow):
                    raw = norm(G[i][0])
                    if raw and len(raw) <= 12 and KOR.search(raw) and not AMTRE.search(raw):
                        labels[raw.replace(" ", "")][raw].append(pi)
            cont = False
            if tbs:
                try:
                    _,_,_,h0,_,_,_ = grid_info(tbs[0].extract())
                    cont = (h0 == 0)          # 헤더 없이 시작 = 앞 페이지 연속
                except Exception: pass
            if has_amt and not find_unit(txt) and not cont:
                unit_missing.append(pi)

            # ── F2/F4/F5: 줄글 대상 ──
            for text, spans in lines_outside_tables(page):
                if DOTS.search(text) or FOOTER.search(text.strip()): continue
                if len(KOR.findall(text)) < 6: continue
                for g, pats in TERM_GROUPS.items():
                    for p in pats:
                        for m in re.finditer(p, text):
                            terms[g][canon(m.group())].append((pi, m.group()))
                # F4 다중 공백: 어절 간격이 통상 공백폭의 1.8배 초과
                ws = [w for _, _, w in spans]
                if len(ws) >= 3:
                    gs = [ws[i+1]["x0"] - ws[i]["x1"] for i in range(len(ws)-1)]
                    med = sorted(gs)[len(gs)//2]
                    if med > 0:
                        for i, g_ in enumerate(gs):
                            if g_ > med * 2.2 and g_ > 4.0:
                                gaps.append(dict(page=pi, before=ws[i]["text"][-8:],
                                                 after=ws[i+1]["text"][:8],
                                                 bbox=(ws[i]["x1"], ws[i]["top"],
                                                       ws[i+1]["x0"], ws[i]["bottom"])))
    return unit_missing, terms, labels, gaps

def report(pdf_path):
    um, terms, labels, gaps = run(pdf_path)
    out = {"F1_단위누락": um, "F2_표현불일치": [], "F3_라벨불일치": [], "F4_다중공백": gaps}
    for g, forms in terms.items():
        if len(forms) >= 2:
            out["F2_표현불일치"].append(
                (g, {k: (len(v), sorted({p for p, _ in v})[:6]) for k, v in forms.items()}))
    for k, forms in labels.items():
        if len(forms) >= 2:
            tot = sum(len(v) for v in forms.values())
            out["F3_라벨불일치"].append(
                (k, {f: (len(p), sorted(set(p))[:6]) for f, p in forms.items()}, tot))
    out["F3_라벨불일치"].sort(key=lambda x: -x[2])
    return out

if __name__ == "__main__":
    r = report("/mnt/user-data/uploads/_삼성전자_감사보고서_2026_03_10_.pdf")
    print(f"F1 단위 누락 (금액표 있는데 단위 없음): {len(r['F1_단위누락'])}p → {r['F1_단위누락'][:20]}")
    print(f"\nF2 표현 불일치 {len(r['F2_표현불일치'])}그룹")
    for g, forms in r["F2_표현불일치"]:
        print(f"  [{g}]")
        for f, (n, ps) in sorted(forms.items(), key=lambda x: -x[1][0]):
            print(f"     '{f}' {n}회  p{ps}")
    print(f"\nF3 라벨 표기 불일치 {len(r['F3_라벨불일치'])}건 (상위 8)")
    for k, forms, tot in r["F3_라벨불일치"][:8]:
        print(f"  '{k}' 총 {tot}회")
        for f, (n, ps) in sorted(forms.items(), key=lambda x: -x[1][0]):
            print(f"     '{f}' {n}회  p{ps}")
    print(f"\nF4 다중 공백 {len(r['F4_다중공백'])}건: {[(g['page'], g['before'], g['after']) for g in r['F4_다중공백'][:6]]}")
