# -*- coding: utf-8 -*-
"""
C1~C6 본표↔주석 레퍼런스 대사 (오프라인)
본표 행의 주석번호를 이용해 탐색 범위를 해당 주석으로 한정 → 우연일치 최소화
"""
import re, collections
import pdfplumber
from core import grid_info, norm, parse, UNIT, UNIT_MULT
from statements import (read_rows, stmt_type, key, SIDE_CUR, SIDE_PRV,
                        SPAN_3M, SPAN_CUM, _fill_merged)
from notes import NOTE_HEAD, AMT

STMT_TAG = {"BS":"BS", "IS":"IS", "CI":"CI", "CF":"CF", "SCE":"SCE"}

# 소액 제외 기준 — '표시 숫자'가 아니라 원 환산 절대금액. 단위가 다른 회사 간에
# 같은 강도로 작동하게 한다 (표시 1000 기준은 백만원 회사 10억 / 원 회사 1천원으로
# 100만 배 다르게 작동했다). 기본값 1억원 — 4축 측정에서 삼성 C 51/56 불변 확인.
# 최종 확정은 회계사 판단 사항 (A7 허용오차처럼 파라미터).
MIN_WON = 100_000_000

def _mult_of(unit_text):
    """(단위: X) 표기 → 원 환산 배수. 복합 단위·미등재·환산 불가면 None."""
    if unit_text is None: return None
    u = norm(unit_text).replace(" ", "")
    if not u or "," in u: return None
    return UNIT_MULT.get(u)

def unit_texts(pdf_path):
    """(page, table) → 표 귀속 단위 원문 문자열 (table_units와 같은 귀속 규칙).
    복합 통화 판정(core.mixed_currency) 등 원문이 필요한 소비자용."""
    out = {}
    with pdfplumber.open(pdf_path) as pdf:
        carry = None
        for pi, page in enumerate(pdf.pages, 1):
            try:
                found = page.search(UNIT.pattern, regex=True)
            except Exception:
                found = []
            ms = sorted((f["top"], (f.get("groups") or ("",))[0]) for f in found)
            for ti, tb in enumerate(page.find_tables(), 1):
                above = [u_ for t_, u_ in ms if t_ < tb.bbox[1]]
                if above: carry = above[-1]
                out[(pi, ti)] = carry
            if ms: carry = ms[-1][1]
    return out

def table_units(pdf):
    """(page, table) → 원 환산 배수. 단위는 페이지가 아니라 표에 귀속:
    표 bbox 위쪽 최근접 (단위:) 표기. 같은 페이지 위쪽에 없으면 직전 표기를
    승계한다(연속 표 — 단위 표기는 표 시작에 한 번만 찍히는 관행).
    배수 탐색은 하지 않는다 — 표에 선언된 단위로만 환산한다."""
    units = {}
    carry = None
    for pi, page in enumerate(pdf.pages, 1):
        try:
            found = page.search(UNIT.pattern, regex=True)
        except Exception:
            found = []
        ms = sorted((f["top"], (f.get("groups") or ("",))[0]) for f in found)
        for ti, tb in enumerate(page.find_tables(), 1):
            above = [u_ for t_, u_ in ms if t_ < tb.bbox[1]]
            if above: carry = above[-1]
            units[(pi, ti)] = _mult_of(carry)
        if ms: carry = ms[-1][1]
    return units

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

def column_periods(data):
    """열의 명시 당/전·3개월/누적 표지. 위치만으로 기간을 추정하지 않는다."""
    G, K, V, hdr, ncol, nrow, cols = grid_info(data)
    if not cols: return {}
    rows = [_fill_merged(G[i], min(cols), ncol) for i in range(hdr)]
    periods = {}
    for j in cols:
        text = " ".join(row[j] for row in rows)
        cur, prv = bool(SIDE_CUR.search(text)), bool(SIDE_PRV.search(text))
        if cur == prv: continue
        three, cumulative = bool(SPAN_3M.search(text)), bool(SPAN_CUM.search(text))
        if three and cumulative: continue
        span = "3M" if three else ("누적" if cumulative else None)
        half, quarter = "반기" in text, "분기" in text
        if half and quarter: continue
        cadence = "반기" if half else ("분기" if quarter else None)
        dates = re.findall(r"(?:19|20)\d{2}(?:\s*[./년-]\s*\d{1,2}(?:\s*[./월-]\s*\d{1,2}\s*일?)?\s*월?)?", text)
        dates = tuple("-".join(re.findall(r"\d+", d)) for d in dates)
        periods[j] = ("당" if cur else "전", span, cadence, dates)
    return periods

def same_period(m, n):
    return m.get("period") is not None and m["period"] == n.get("period")

def collect_main(pdf, units, min_won):
    """본표 항목 → ([dict(tag,label,val,mult,refs,...)], 단위 제외 목록)"""
    out = []; excl = []
    for pi, page in enumerate(pdf.pages, 1):
        st = stmt_type(page.extract_text() or "")
        if st not in STMT_TAG: continue
        for ti, tb in enumerate(page.find_tables(), 1):
            data = tb.extract()
            try: G,K,V,hdr,ncol,nrow,numcols = grid_info(data)
            except Exception: continue
            mult = units.get((pi, ti))
            # 주석열 위치 찾기
            njs = [j for j in range(min(3,ncol))
                   if any(re.fullmatch(r"주\s*석", norm(G[i][j])) for i in range(max(hdr,1)))]
            rows, nper = read_rows(data)
            periods = column_periods(data)
            for d,k,raw,vals,ip,it,ri,cof in rows:
                refs = set()
                for j in njs:
                    for tok in re.split(r"[,\s]+", norm(G[ri][j])):
                        if tok.isdigit(): refs.add(int(tok))
                for p_, v in vals.items():
                    rec = dict(tag=STMT_TAG[st], label=raw[:24], val=v, mult=mult,
                               refs=refs, page=pi, table=ti, row=ri, col=cof.get(p_),
                               period=periods.get(cof.get(p_)), ncol=(njs[0] if njs else None))
                    if mult is None:
                        if refs: excl.append(rec)       # 복합·판독 불가 단위 → 대사 제외
                        continue
                    if abs(v * mult) < min_won: continue  # 원 환산 소액 제외
                    out.append(rec)
    return out, excl

def collect_notes(pdf, rng, units, min_won):
    """주석 내 금액 → ([dict(notes,page,table,row,col,val,mult,label)], 단위제외 표 수)"""
    inv = {}
    for n,(a,b) in rng.items():
        for p in range(a, b+1): inv.setdefault(p, set()).add(n)
    out = []; excl_tabs = set()
    for pi, page in enumerate(pdf.pages, 1):
        ns = inv.get(pi)
        if not ns: continue
        if stmt_type(page.extract_text() or ""): continue      # 본표 페이지 제외
        for ti, tb in enumerate(page.find_tables(), 1):
            data = tb.extract()
            try: G,K,V,hdr,ncol,nrow,numcols = grid_info(data)
            except Exception: continue
            mult = units.get((pi, ti))
            if mult is None:
                excl_tabs.add((pi, ti)); continue              # 복합·판독 불가 단위
            periods = column_periods(data)
            for i in range(hdr, nrow):
                for j in numcols:
                    if K[i][j] != "NUM": continue
                    v = V[i][j]
                    if abs(v * mult) < min_won: continue
                    out.append(dict(notes=ns, page=pi, table=ti, row=i, col=j,
                                    val=v, mult=mult, label=(G[i][0] or "")[:24],
                                    period=periods.get(j)))
    return out, excl_tabs

def _pair_tol(ma, mb):
    """단위가 같으면 정확 일치, 다르면 거친 단위의 1스텝(반올림 표시 허용).
    예: 본표 원 vs 주석 천원 → ±1,000원."""
    return 0.0 if ma == mb else float(max(ma, mb))

def build(pdf_path, tol=0.0, min_won=MIN_WON):
    with pdfplumber.open(pdf_path) as pdf:
        rng   = note_ranges(pdf)
        units = table_units(pdf)
        mains, mexcl = collect_main(pdf, units, min_won)
        nts, nexcl   = collect_notes(pdf, rng, units, min_won)
    bynote = collections.defaultdict(list)
    for n in nts:
        for nn in n["notes"]: bynote[nn].append(n)
    bywon = collections.defaultdict(list)
    for n in nts: bywon[round(n["val"] * n["mult"])].append(n)

    def match(m, n):
        if not same_period(m, n): return False
        a, b = m["val"] * m["mult"], n["val"] * n["mult"]
        return abs(a - b) <= _pair_tol(m["mult"], n["mult"]) + 1e-6

    links = []      # (본표항목, 주석항목) 매칭 — 원 환산 절대금액 기준
    unmatched = []
    for m in mains:
        if not m["refs"]: continue
        seen = set(); cands = []
        for ref in sorted(m["refs"]):
            for n in bynote.get(ref, []):
                if id(n) in seen: continue
                seen.add(id(n))
                if match(m, n): cands.append(n)
        if cands:
            links.append((m, cands))
        else:
            mwon = m["val"] * m["mult"]
            near = [n for n in {id(x): x for ref in m["refs"]
                                for x in bynote.get(ref, [])}.values()
                    if same_period(m, n) and tol > 0 and abs(n["val"]*n["mult"] - mwon) <= tol]
            unmatched.append((m, near))
    # 주석간 레퍼: 같은 원 환산 금액이 다른 주석에도 등장하면 태그 누적
    for m, cs in links:
        for c in cs:
            others = {n for x in bywon.get(round(c["val"]*c["mult"]), []) for n in x["notes"]
                      if same_period(c, x) and n not in (c["notes"] & m["refs"])}
            c["also"] = sorted(others)[:2]
    return rng, mains, nts, links, unmatched, mexcl, nexcl

def marks(pdf_path, tol=0.0, min_won=MIN_WON):
    """→ (본표 동그라미, 주석 태그, 차이, 성립, 미성립, 본표 전체, 단위제외)"""
    rng, mains, nts, links, un, mexcl, _nx = build(pdf_path, tol, min_won)
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
            n0 = min(near, key=lambda n: abs(n["val"]*n["mult"] - m["val"]*m["mult"]))
            diffs.append(dict(page=m["page"], table=m["table"], row=m["row"], col=m["col"],
                              label=m["label"], val=m["val"], other=n0["val"],
                              diff=n0["val"]*n0["mult"]/m["mult"] - m["val"], where=f"p{n0['page']}"))
    circles = [dict(page=p_, table=t_, row=r_, ncol=n_, notes=sorted(v))
               for (p_,t_,r_,n_), v in circles.items()]
    return circles, tags, diffs, links, un, mains, mexcl

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python refmap.py <보고서.pdf>"); sys.exit(2)
    P = sys.argv[1]
    rng, mains, nts, links, un, mexcl, nexcl = build(P)
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
