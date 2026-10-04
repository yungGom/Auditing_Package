# -*- coding: utf-8 -*-
"""
C1~C6 본표↔주석 레퍼런스 대사 (오프라인)
본표 행의 주석번호를 이용해 탐색 범위를 해당 주석으로 한정 → 우연일치 최소화
"""
import re, collections
import pdfplumber
from core import grid_info, norm, parse, UNIT, UNIT_MULT, is_ratio_col
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

PERIOD_SIDE = re.compile(r"(?<![가-힣])(당|전)\s*(반기|분기|기|회계연도)(?:\s*(말|초))?(?!손익|순이익|순손실|이익|비용|수익)|\(\s*(당|전)\s*\)\s*기?")

def _period(text):
    text = norm(text)
    sides = {m.group(1) or m.group(4) for m in PERIOD_SIDE.finditer(text)}
    if len(sides) != 1: return None
    three, cumulative = bool(SPAN_3M.search(text)), bool(SPAN_CUM.search(text))
    half, quarter = "반기" in text, "분기" in text
    if (three and cumulative) or (half and quarter): return None
    dates = re.findall(r"(?:19|20)\d{2}(?:\s*[./년-]\s*\d{1,2}(?:\s*[./월-]\s*\d{1,2}\s*일?)?\s*월?)?", text)
    dates = tuple(dict.fromkeys("-".join(str(int(n)) for n in re.findall(r"\d+", d)) for d in dates))
    return (next(iter(sides)), "3M" if three else ("누적" if cumulative else None),
            "반기" if half else ("분기" if quarter else None), dates)

def _header_texts(data):
    G, K, V, hdr, nc, nr, cols = grid_info(data)
    # Period group starts can be on excluded ratio cells. Walk physical headers,
    # not the first retained monetary cell; text boundaries stop propagation.
    rows = [_fill_merged(G[i], 0, nc) for i in range(hdr)]
    return {j: " ".join(row[j] for row in rows) for j in range(nc)}

def column_periods(data, scope=""):
    """열의 명시 당/전·3개월/누적 표지. 위치만으로 기간을 추정하지 않는다."""
    G, K, V, hdr, ncol, nrow, cols = grid_info(data)
    if not cols: return {}
    texts = _header_texts(data)
    periods = {}
    for j in cols:
        text = texts[j]
        p, s = _period(text), _period(scope)
        if p and s and (p[0] != s[0] or (p[3] and s[3] and p[3] != s[3])): continue
        # A contradictory/ambiguous local header cannot be rescued by a title.
        if PERIOD_SIDE.search(text) and p is None: continue
        combined = _period(text + " " + scope) if scope else p
        if combined: periods[j] = combined
    return periods

def same_period(m, n):
    if m.get("period") is None or m['period'] != n.get('period'): return False
    if 'role' in m or 'role' in n:
        if m.get('role') is None or m['role'] != n.get('role'): return False
        # Equal flows can be different financial meanings. Without an established
        # same item label, retain the proposed relation for human review.
        if m['role'][0]=='거래액' and key(m.get('label','')) != key(n.get('label','')): return False
    return True

def _role(label, header, scope, tag=None):
    text = norm(label).replace(' ', '')
    # Cell role precedes table role: a rollforward contains both endpoints and flows.
    if re.search(r'기말|기초|당기말|전기말|반기말|분기말', text):
        return ('잔액', '초' if '기초' in text else '말')
    if tag == 'BS': return ('잔액', '말')
    # Measurement categories and accrued/prepaid accounts contain words also
    # used for flows. Their bounded account names are not disposal gains.
    if re.fullmatch(r'.*(?:공정가치(?:측정)?금융자산)|(?:미수수익|선급비용|평가충당금)', text):
        if tag in ('CF','IS','CI'): return ('거래액', None)
        if re.search(r'(?:당|전)(?:기|반기|분기)?말', header + scope): return ('잔액','말')
        return None
    if re.search(r'손익|수익|비용|처분이익|처분손실|재측정',text): return ('거래액',None)
    if re.match(r'^(취득|처분|상각|감가상각|평가|증가|감소|배당|조정)', text): return ('거래액', None)
    if tag in ('CF','IS','CI'): return ('거래액', None)
    if tag == 'SCE': return None  # SCE movement/balance relations need Owner review.
    if re.search(r'기초|기말', header): return ('잔액', '초' if '기초' in header else '말')
    if re.search(r'(?:당|전)(?:기|반기|분기)?말', header + scope): return ('잔액', '말')
    if re.search(r'중.*변동|중.*내역', scope): return ('거래액', None)
    if re.search(r'자산|부채|채권|채무|차입금|금융상품|예금|장부금액', text): return ('잔액','말')
    return None

def _source_lines(page, low, high, left=None, right=None):
    lines = collections.defaultdict(list)
    for w in page.extract_words():
        if low <= w['top'] and w['bottom'] <= high and (left is None or w['x0'] >= left-1) and (right is None or w['x1'] <= right+1):
            lines[round(w['top'], 1)].append(w)
    return [(y, ' '.join(w['text'] for w in sorted(ws,key=lambda x:x['x0'])))
            for y,ws in sorted(lines.items())]

DATE_TEXT = re.compile(r'(?:19|20)\d{2}\s*[./년-]\s*\d{1,2}\s*[./월-]\s*\d{1,2}\s*일?')

def _dates(text):
    return tuple('-'.join(str(int(n)) for n in re.findall(r'\d+',d)) for d in DATE_TEXT.findall(text))

def _report_anchors(pdf):
    numbered={}; sides={}
    for page in pdf.pages:
        txt=page.extract_text() if hasattr(page,'extract_text') else ''
        if not stmt_type(txt or ''): continue
        for line in (txt or '').splitlines():
            m=re.search(r'제\s*(\d+)\s*기',line)
            ds=_dates(line)
            if m and ds: numbered.setdefault(m.group(1),set()).update(ds)
        for tb in page.find_tables():
            for text in _header_texts(tb.extract()).values():
                m=re.search(r'제\s*(\d+)\s*\(\s*(당|전)\s*\)',text)
                if m: sides.setdefault(m.group(2),set()).add(m.group(1))
    return {side:tuple(sorted(numbered[next(iter(ns))],key=lambda d:tuple(map(int,d.split('-')))))
            for side,ns in sides.items() if len(ns)==1 and next(iter(ns)) in numbered}

def _grid_layout(tb, nc):
    if not hasattr(tb,'rows'): return None
    layout=[]
    for j in range(nc):
        cells=[r.cells[j] for r in tb.rows if len(r.cells)>j and r.cells[j]]
        if not cells: return None
        bb=min(cells,key=lambda b:b[2]-b[0])
        layout.append((round(bb[0],1),round(bb[2],1)))
    return tuple(layout)

def period_contexts(pdf, units):
    """Geometry-bound table scopes and strict adjacent-page header continuation."""
    out = {}; previous = None; section=None
    anchors=_report_anchors(pdf)
    for pi,page in enumerate(pdf.pages,1):
        scope = ''; owner = None; bottom = 0; date_scope=(); last_box=None
        tables = page.find_tables()
        if not tables: previous = None; continue
        for ti,tb in enumerate(tables,1):
            reset = False
            if last_box and (abs(last_box[0]-tb.bbox[0])>=1 or abs(last_box[2]-tb.bbox[2])>=1 or tb.bbox[1]<bottom):
                scope=''; owner=None; date_scope=(); bottom=0; reset=True
            for y,line in _source_lines(page,bottom,tb.bbox[1],tb.bbox[0],tb.bbox[2]):
                if NOTE_HEAD.match(line.strip()) or re.match(r'^[가-하]\.\s',line):
                    scope = ''; owner = None; date_scope=(); reset = True
                    m=NOTE_HEAD.match(line.strip())
                    if m: section=line.strip()
                ds=_dates(line)
                if ds and (re.fullmatch(r'[\d\s./년월일-]+(?:현재)?',line) or NOTE_HEAD.match(line.strip())):
                    date_scope=ds
                p = _period(line)
                # Only period-bearing standalone/subsection headings own a table;
                # narrative containing both current/prior is not a single-period title.
                if p and (re.match(r'^\s*(?:\(?\d+[).]|\(?당|\(?전)',line) or re.fullmatch(r'\(?\s*(?:당|전)\s*(?:기|반기|분기)(?:말|초)?\s*\)?(?:\s*\(단위.*)?',line)):
                    scope = line; owner = (pi,y,line)
            data = tb.extract()
            if not data: bottom=tb.bbox[3]; previous=None; continue
            _,_,_,hdr,nc,_,_=grid_info(data)
            layout=_grid_layout(tb,nc)
            headers=data; inherited=False
            # Continue only adjacent first/last tables, same grid geometry and
            # declared unit, without a new section or conflicting local scope.
            if ti==1 and hdr==0 and previous and previous['page']==pi-1 and not reset and section and section==previous['section'] and previous['open']:
                if layout is not None and layout==previous['layout'] and previous['nc']==nc and previous['unit'] is not None and previous['unit']==units.get((pi,ti)) and abs(previous['left']-tb.bbox[0]) < 1 and abs(previous['width']-(tb.bbox[2]-tb.bbox[0])) < 1:
                    if not scope or _period(scope)==_period(previous['scope']):
                        headers=previous['headers']; scope=previous['scope']; owner=previous['owner']; date_scope=previous['dates']; inherited=True
            # A completed total or following narrative proves this is not an open
            # continuation. No numeric/amount agreement is used as an anchor.
            last_label=next((norm(c) for c in data[-1] if parse(c)[0]=='TEXT'), '')
            after=[line for y,line in _source_lines(page,tb.bbox[3],10000,tb.bbox[0],tb.bbox[2]) if not re.search(r'전자공시|dart.fss|Page\s*\d+',line)]
            is_open=not re.fullmatch(r'합\s*계|총\s*계|소\s*계|계',last_label) and not after
            out[(pi,ti)] = dict(scope=scope,owner=owner,headers=headers,inherited=inherited,dates=date_scope,anchors=anchors)
            previous=dict(page=pi,nc=nc,layout=layout,left=tb.bbox[0],width=tb.bbox[2]-tb.bbox[0],unit=units.get((pi,ti)),scope=scope,owner=owner,headers=headers,section=section,open=is_open,dates=date_scope)
            bottom=tb.bbox[3]; last_box=tb.bbox
    return out

def _cell_evidence(data, context, tag=None):
    source = context['headers']
    ps = column_periods(source,context['scope'])
    sides={p[0] for p in ps.values()}
    texts = _header_texts(source)
    G, K, V, hdr,nc,nr,cols=grid_info(data)
    out={}
    block=None
    for i in range(hdr,nr):
        label=G[i][0]
        if tag=='SCE' and _period(label): block=_period(label)
        for j in cols:
            role=_role(label,texts.get(j,''),context['scope'],tag)
            p=ps.get(j) or (block if tag=='SCE' else None)
            dates=context.get('dates')
            if p and dates and len(sides)>1 and not _period(context['scope']):
                # An unbound standalone date cannot identify two fiscal sides.
                dates=context.get('anchors',{}).get(p[0],())
                if not dates: p=None
            elif not dates:
                dates=context.get('anchors',{}).get(p[0],()) if p else ()
            if p and dates:
                endpoint=dates[:1] if role and role==('잔액','초') else (dates[-1:] if role and role[0]=='잔액' else dates)
                if p[3] and p[3] != endpoint: p=None
                else: p=(p[0],p[1],p[2],endpoint)
            # Duration is not applicable to an instant, but explicit date/cadence
            # conflicts stay visible. No missing movement span defaults to cumulative.
            if p and role and role[0]=='잔액': p=(p[0],None,p[2],p[3])
            out[(i,j)]=dict(period=p,role=role,period_source=context['owner'],
                            period_text=texts.get(j,'')+' '+context['scope'])
    return out

def collect_main(pdf, units, min_won, contexts=None):
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
            context=(contexts or {}).get((pi,ti),dict(headers=data,scope='',owner=None))
            evidence=_cell_evidence(data,context,STMT_TAG[st])
            for d,k,raw,vals,ip,it,ri,cof in rows:
                refs = set()
                for j in njs:
                    for tok in re.split(r"[,\s]+", norm(G[ri][j])):
                        if tok.isdigit(): refs.add(int(tok))
                for p_, v in vals.items():
                    rec = dict(tag=STMT_TAG[st], label=raw[:24], val=v, mult=mult,
                               refs=refs, page=pi, table=ti, row=ri, col=cof.get(p_),
                               ncol=(njs[0] if njs else None),
                               **evidence.get((ri,cof.get(p_)),dict(period=None,role=None)))
                    if mult is None:
                        if refs: excl.append(rec)       # 복합·판독 불가 단위 → 대사 제외
                        continue
                    if abs(v * mult) < min_won: continue  # 원 환산 소액 제외
                    out.append(rec)
    return out, excl

def collect_notes(pdf, rng, units, min_won, contexts=None):
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
            context=(contexts or {}).get((pi,ti),dict(headers=data,scope='',owner=None))
            evidence=_cell_evidence(data,context)
            HG,_,_,hh,_,_,_=grid_info(context['headers'])
            for i in range(hdr, nrow):
                for j in numcols:
                    if j < len(HG[0]) and is_ratio_col(HG,hh,j): continue
                    if K[i][j] != "NUM": continue
                    v = V[i][j]
                    if abs(v * mult) < min_won: continue
                    out.append(dict(notes=ns, page=pi, table=ti, row=i, col=j,
                                    val=v, mult=mult, label=(G[i][0] or "")[:24],
                                    **evidence.get((i,j),dict(period=None,role=None))))
    return out, excl_tabs

def _pair_tol(ma, mb):
    """단위가 같으면 정확 일치, 다르면 거친 단위의 1스텝(반올림 표시 허용).
    예: 본표 원 vs 주석 천원 → ±1,000원."""
    return 0.0 if ma == mb else float(max(ma, mb))

def build(pdf_path, tol=0.0, min_won=MIN_WON):
    with pdfplumber.open(pdf_path) as pdf:
        rng   = note_ranges(pdf)
        units = table_units(pdf)
        contexts = period_contexts(pdf, units)
        mains, mexcl = collect_main(pdf, units, min_won, contexts)
        nts, nexcl   = collect_notes(pdf, rng, units, min_won, contexts)
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
            equal = [n for ref in m['refs'] for n in bynote.get(ref,[])
                     if abs(n['val']*n['mult']-mwon) <= _pair_tol(m['mult'],n['mult'])+1e-6]
            if equal:
                m['review_reason'] = '검토 필요: 기간 또는 잔액·거래액 의미 확인'
                m['review_candidates'] = [dict(page=n['page'],table=n['table'],row=n['row'],col=n['col'],period=n['period'],role=n['role'],source=n.get('period_source'),text=n.get('period_text')) for n in equal]
            else:
                m['review_reason'] = '동일 금액 미발견; 미검증'
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
