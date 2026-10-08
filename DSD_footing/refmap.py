# -*- coding: utf-8 -*-
"""
C1~C6 본표↔주석 레퍼런스 대사 (오프라인)
본표 행의 주석번호를 이용해 탐색 범위를 해당 주석으로 한정 → 우연일치 최소화
"""
import re, collections, calendar
from datetime import date
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
    if DATE_TEXT.search(text) and not _dates(text): return None
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

def column_periods(data, scope="", columns=None):
    """열의 명시 당/전·3개월/누적 표지. 위치만으로 기간을 추정하지 않는다."""
    G, K, V, hdr, ncol, nrow, cols = grid_info(data)
    if columns is not None: cols=columns
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
        if m['role'][0]=='거래액':
            mi = m.get('item_identity', _item_key(m.get('full_label', m.get('label',''))))
            ni = n.get('item_identity', _item_key(n.get('full_label', n.get('label',''))))
            if not mi or mi != ni: return False
    return True

def _role(label, header, scope, tag=None):
    text = norm(label).replace(' ', '')
    header = norm(header).replace(' ', '')
    scope = norm(scope).replace(' ', '')
    # Explicit movement column belongs to this cell, including borrowing accounts.
    if '재무현금흐름' in header: return ('거래액', None)
    # Cell role precedes table role: a rollforward contains both endpoints and flows.
    if re.search(r'기말|기초|당기말|전기말|반기말|분기말', text):
        return ('잔액', '초' if '기초' in text else '말')
    if tag == 'BS': return ('잔액', '말')
    # Measurement categories and accrued/prepaid accounts contain words also
    # used for flows. Their bounded account names are not disposal gains.
    if re.fullmatch(r'.*(?:공정가치(?:측정)?금융(?:자산|부채)|상각후원가(?:측정)?금융자산)|(?:수익증권|미수수익|선급비용|평가충당금)', text):
        if tag in ('CF','IS','CI'): return ('거래액', None)
        if re.search(r'(?:당|전)(?:기|반기|분기)?말', header + scope): return ('잔액','말')
        return None
    if re.fullmatch(r'매출|매출액|매출원가|매출총이익',text): return ('거래액',None)
    if re.search(r'손익|수익|비용|처분이익|처분손실|재측정|판매비와관리비|영업손실|현금흐름|창출된현금|운전자본|자산부채의변동|순손실|중단영업.*손실|^조정$',text): return ('거래액',None)
    if re.match(r'^(취득|처분|상각|감가상각|평가|증가|감소|배당|조정)', text): return ('거래액', None)
    if tag in ('CF','IS','CI'): return ('거래액', None)
    if tag == 'SCE': return None  # SCE movement/balance relations need Owner review.
    if re.search(r'기초|기말', header): return ('잔액', '초' if '기초' in header else '말')
    if re.search(r'(?:당|전)(?:기|반기|분기)?말', header + scope): return ('잔액', '말')
    if re.search(r'중.*변동|중.*내역', scope): return ('거래액', None)
    if re.search(r'자산|부채|채권|채무|차입금|금융상품|예금|장부금액', text): return ('잔액','말')
    return None


def _item_key(label):
    """Syntactic account identity; never strips valuation/disposal/OCI meaning."""
    text = key(label).rstrip(':：').replace('ㆍ','').replace('ᆞ','').replace('·','')
    text = text.replace('계속영업과관련된','계속영업').replace('법인세비용차감전','법인세차감전')
    text = re.sub(r'(?:합계|총계|계)$', '', text) if not re.fullmatch(r'합계|총계|소계|계', text) else ''
    return {'매출액': '매출', '금융원가': '금융비용',
            '중단영업으로부터의손실': '중단영업손실',
            '영업으로부터창출된현금흐름': '영업으로부터창출된현금'}.get(text, text) or None


def _title_item(title):
    """Identify a single explicitly named total; mixed titles remain ambiguous."""
    text = norm(title).replace(' ', '')
    names = re.findall(r'판매비와관리비|기타영업외수익|기타영업외비용|기타수익|기타비용|금융수익|금융비용|매출원가|매출액|영업수익|영업으로부터창출된현금(?:흐름)?|영업활동으로인한자산부채의변동|순운전자본의변동|운전자본의변동|수익[ㆍᆞ·]?비용의조정|조정(?:내역)?', text)
    cash_adjustment = bool(re.search(r'영업활동|현금흐름',text) or re.fullmatch(r'(?:\(\d+\)|[가-하]\.)?조정(?:내역)?',text))
    names = [x for x in names if not x.startswith('조정') or cash_adjustment]
    items = {_item_key(x.replace('조정내역', '조정')) for x in names}
    return next(iter(items)) if len(items) == 1 else None


def _row_items(data, title, inherited_group=None, tag=None):
    G,K,V,hdr,nc,nr,cols = grid_info(data)
    outer = _title_item(title)
    active = inherited_group or outer
    groups = []; closed = set(); out = {}
    continuing_end = next((i for i in range(nr) if key(G[i][0]) in ('계속영업손실','계속영업이익')), None)
    discontinued = any(key(G[i][0]) in ('중단영업손실','중단영업이익') for i in range(nr))
    for i in range(hdr):
        if _title_item(G[i][0]):
            active = _item_key(G[i][0])
            if active=='조정' and outer and outer.endswith('조정'): active=outer
            groups.append(active)
    for i in range(hdr,nr):
        label = G[i][0]
        k = key(label).rstrip(':：')
        numeric = any(K[i][j] == 'NUM' for j in cols)
        if not numeric and label:
            active = _item_key(label)
            if active=='조정' and outer and outer.endswith('조정'): active=outer
            groups.append(active)
        if re.fullmatch(r'합계|총계|계|소계', k):
            item = active
            # Only already closed subgroups can feed a following grand total.
            # Last-row position alone never proves an enclosing total.
            if k != '소계' and i == nr-1 and outer and len(set(groups)) > 1 and set(groups) <= closed:
                item = outer
            closed.add(active)
        else:
            item = _item_key(label)
            if numeric and re.search(r'총지출액$|총액$',k): closed.add(active)
            # The statement explicitly closes continuing operations before a
            # separately presented discontinued result; bind preceding tax lines.
            if tag in ('IS','CI') and continuing_end is not None and discontinued and i < continuing_end and item in ('법인세비용','법인세차감전순손실','법인세차감전순이익'):
                item='계속영업'+item
        out[i] = item
    return out, active

def _source_lines(page, low, high, left=None, right=None):
    lines = collections.defaultdict(list)
    for w in page.extract_words():
        if low <= w['top'] and w['bottom'] <= high and (left is None or w['x0'] >= left-1) and (right is None or w['x1'] <= right+1):
            lines[round(w['top'], 1)].append(w)
    return [(y, ' '.join(w['text'] for w in sorted(ws,key=lambda x:x['x0'])))
            for y,ws in sorted(lines.items())]

DATE_TEXT = re.compile(r'(?:19|20)\d{2}\s*[./년-]\s*\d{1,2}\s*[./월-]\s*\d{1,2}\s*일?')

def _dates(text):
    dates = tuple('-'.join(str(int(n)) for n in re.findall(r'\d+',d)) for d in DATE_TEXT.findall(text))
    try:
        for d in dates: date(*map(int,d.split('-')))
    except ValueError: return ()
    return dates

def _duration_kind(line, dates):
    """Quarter ordinal is not a duration. Validate the printed calendar range."""
    if len(dates)!=2: return None
    try:
        start,end=(date(*map(int,d.split('-'))) for d in dates)
    except ValueError: return None
    if end < start: return None
    months=(end.year-start.year)*12+end.month-start.month+1
    complete=start.day==1 and end.day==calendar.monthrange(end.year,end.month)[1]
    if not complete: return None
    if '반기' in line and start.month==1 and months==6: return '누적'
    if '분기' in line:
        if months==3 and start.month in (1,4,7,10): return '3M'
        if start.month==1 and months in (6,9,12): return '누적'
        return None
    return 'annual' if start.month==1 and months==12 else None


def _report_anchors(pdf, with_sources=False):
    numbered=collections.defaultdict(set); sides=collections.defaultdict(set)
    sources=collections.defaultdict(list)
    for pi,page in enumerate(pdf.pages,1):
        txt=page.extract_text() if hasattr(page,'extract_text') else ''
        if not stmt_type(txt or ''): continue
        for li,line in enumerate((txt or '').splitlines(),1):
            m=re.search(r'제\s*(\d+)\s*(?:\(\s*(당|전)\s*\))?\s*기',line)
            ds=_dates(line)
            if m and ds:
                kind = 'instant' if len(ds)==1 else _duration_kind(line,ds)
                if kind is None: continue
                if kind=='annual': kind=None
                numbered[(m.group(1),kind)].add(ds)
                sources[(m.group(1),kind)].append(dict(page=pi,line=li,text=line,dates=ds))
                if m.group(2): sides[m.group(2)].add(m.group(1))
        for tb in page.find_tables():
            for text in _header_texts(tb.extract()).values():
                m=re.search(r'제\s*(\d+)\s*\(\s*(당|전)\s*\)',text)
                if m: sides.setdefault(m.group(2),set()).add(m.group(1))
    anchors = {(side,kind):next(iter(values))
            for side,ns in sides.items() if len(ns)==1
            for (number,kind),values in numbered.items()
            if number==next(iter(ns)) and len(values)==1}
    evidence = {(side,kind):sources[(next(iter(sides[side])),kind)] for side,kind in anchors}
    return (anchors,evidence) if with_sources else anchors


def _anchor_dates(anchors, period, role):
    if not period: return ()
    side,span,cadence,_ = period
    if role and role[0]=='잔액':
        if role[1]=='말': return anchors.get((side,'instant'), ())
        span = span or ('누적' if cadence=='반기' else ('3M' if cadence=='분기' else None))
        return anchors.get((side,span), ())[:1]
    span = span or ('누적' if cadence=='반기' else ('3M' if cadence=='분기' else None))
    return anchors.get((side,span), ())

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
    out = {}; previous = None; section=None; title=''
    anchors,anchor_sources=_report_anchors(pdf,with_sources=True)
    for pi,page in enumerate(pdf.pages,1):
        scope = ''; owner = None; bottom = 0; date_scope=(); last_box=None; title=''; invalid_date=False
        tables = page.find_tables()
        if not tables: previous = None; continue
        for ti,tb in enumerate(tables,1):
            reset = False
            if last_box and (abs(last_box[0]-tb.bbox[0])>=1 or abs(last_box[2]-tb.bbox[2])>=1 or tb.bbox[1]<bottom):
                scope=''; owner=None; date_scope=(); bottom=0; title=''; invalid_date=False; reset=True
            for y,line in _source_lines(page,bottom,tb.bbox[1],tb.bbox[0],tb.bbox[2]):
                if NOTE_HEAD.match(line.strip()) or re.match(r'^[가-하]\.\s|^\(\d+\)',line):
                    scope = ''; owner = None; date_scope=(); invalid_date=False; reset = True
                    m=NOTE_HEAD.match(line.strip())
                    if m: section=line.strip(); title=line.strip()
                    elif not re.fullmatch(r'\(\d+\)\s*(?:당|전)\s*(?:기|반기|분기)(?:말|초)?',line):
                        title=line
                if _title_item(line) and not AMT.search(line): title=line
                ds=_dates(line)
                if DATE_TEXT.search(line) and not ds: invalid_date=True
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
                compatible = layout is not None and previous['layout'] is not None and len(layout)==len(previous['layout']) and all(abs(a-b)<=2 for cell,old in zip(layout,previous['layout']) for a,b in zip(cell,old))
                if compatible and previous['nc']==nc and previous['unit'] is not None and previous['unit']==units.get((pi,ti)) and abs(previous['left']-tb.bbox[0]) < 1 and abs(previous['width']-(tb.bbox[2]-tb.bbox[0])) < 1:
                    if not scope or _period(scope)==_period(previous['scope']):
                        headers=previous['headers']; scope=previous['scope']; owner=previous['owner']; date_scope=previous['dates']; title=previous['title']; invalid_date=previous['invalid_date']; inherited=True
            # A completed total or following narrative proves this is not an open
            # continuation. No numeric/amount agreement is used as an anchor.
            last_label=next((norm(c) for c in data[-1] if parse(c)[0]=='TEXT'), '')
            after=[line for y,line in _source_lines(page,tb.bbox[3],10000,tb.bbox[0],tb.bbox[2]) if not re.search(r'전자공시|dart.fss|Page\s*\d+',line)]
            is_open=not re.fullmatch(r'합\s*계|총\s*계|소\s*계|계',last_label) and not after
            donor=(previous['page'],previous['table']) if inherited else None
            group=previous['group'] if inherited else None
            _,active=_row_items(data,title,group)
            out[(pi,ti)] = dict(scope=scope,owner=owner,headers=headers,inherited=inherited,dates=date_scope,anchors=anchors,anchor_sources=anchor_sources,title=title,group=group,donor=donor,invalid_date=invalid_date)
            previous=dict(page=pi,table=ti,nc=nc,layout=layout,left=tb.bbox[0],width=tb.bbox[2]-tb.bbox[0],unit=units.get((pi,ti)),scope=scope,owner=owner,headers=headers,section=section,open=is_open,dates=date_scope,title=title,group=active,invalid_date=invalid_date)
            bottom=tb.bbox[3]; last_box=tb.bbox
    return out

def _cell_evidence(data, context, tag=None):
    source = context['headers']
    ps = column_periods(source,context['scope'],grid_info(data)[-1])
    # A period caption inside a mixed movement table can be placed over its
    # middle columns. Use it only when all physical period headers agree.
    header_periods = {_period(t) for t in _header_texts(source).values() if _period(t)}
    texts = _header_texts(source)
    conflict = any(PERIOD_SIDE.search(t) and not _period(t) for t in texts.values())
    if len(header_periods)==1 and not conflict and not PERIOD_SIDE.search(context['scope']):
        enclosing=next(iter(header_periods))
        for j in grid_info(data)[-1]:
            t=texts.get(j,'')
            if not (PERIOD_SIDE.search(t) or SPAN_3M.search(t) or SPAN_CUM.search(t) or DATE_TEXT.search(t)):
                ps.setdefault(j,enclosing)
    sides={p[0] for p in ps.values()}
    texts = _header_texts(source)
    G, K, V, hdr,nc,nr,cols=grid_info(data)
    items,active = _row_items(data,context.get('title',''),context.get('group'),tag)
    out={}
    block=None
    for i in range(hdr,nr):
        label=G[i][0]
        if tag=='SCE' and _period(label): block=_period(label)
        for j in cols:
            role=_role(label,texts.get(j,''),context['scope'],tag)
            item=items.get(i)
            if key(label) in ('계','합계','총계','소계') and re.search(r'지분법손익$',texts.get(j,'').replace(' ','')):
                item='지분법손익'; role=('거래액',None)
            if role is None and key(label) in ('계','합계','총계','소계') and item and _role(item,'','')==('거래액',None):
                role=('거래액',None)
            if key(label) in ('합계','계') and i==nr-1 and any(key(G[k][0])=='기말' for k in range(hdr,i)) and any(re.search(r'차감.*유동',key(G[k][0])) for k in range(hdr,i)):
                role=('잔액','말')
            p=ps.get(j) or (block if tag=='SCE' else None)
            if context.get('invalid_date'): p=None
            dates=context.get('dates')
            if p and dates and len(sides)>1 and not _period(context['scope']):
                # An unbound standalone date cannot identify two fiscal sides.
                dates=_anchor_dates(context.get('anchors',{}),p,role)
                if not dates: p=None
            elif not dates:
                dates=_anchor_dates(context.get('anchors',{}),p,role)
            if p and dates:
                endpoint=dates[:1] if role and role==('잔액','초') else (dates[-1:] if role and role[0]=='잔액' else dates)
                if p[3] and p[3] != endpoint: p=None
                else: p=(p[0],p[1],p[2],endpoint)
                if p and role and role[0]=='거래액' and not p[1] and p[2]=='반기' and len(endpoint)==2:
                    p=(p[0],'누적',p[2],endpoint)
            # Duration is not applicable to an instant, but explicit date/cadence
            # conflicts stay visible. No missing movement span defaults to cumulative.
            if p and role and role[0]=='잔액': p=(p[0],None,p[2],p[3])
            out[(i,j)]=dict(period=p,role=role,period_source=context['owner'],
                            period_text=texts.get(j,'')+' '+context['scope'],
                            period_anchor_sources=[s for values in context.get('anchor_sources',{}).values() for s in values if p and tuple(s['dates'])==p[3]],
                            item_identity=item,item_source=dict(title=context.get('title',''),row=i,column=texts.get(j,''),donor=context.get('donor')))
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
                    rec = dict(tag=STMT_TAG[st], label=raw[:24], full_label=raw, val=v, mult=mult,
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
                                    val=v, mult=mult, label=(G[i][0] or "")[:24],full_label=G[i][0] or '',
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
                m['review_reason'] = '검토 필요: 기간·잔액/거래액·계정/합계 범위 확인'
                m['review_candidates'] = [dict(page=n['page'],table=n['table'],row=n['row'],col=n['col'],period=n['period'],role=n['role'],source=n.get('period_source'),text=n.get('period_text'),label=n.get('full_label',n['label']),item=n.get('item_identity'),item_source=n.get('item_source'),date_source=n.get('period_anchor_sources')) for n in equal]
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
