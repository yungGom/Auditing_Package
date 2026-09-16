"""Current-source candidate review. Suggestions are never decisions.

Offsets and occurrence IDs are scoped by immutable source hashes. A taxonomy
export cannot establish instance dimensions; those require explicit review.
"""
import copy
from datetime import date, datetime, timezone
import getpass
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile

from . import golden
from dsd_tool.mapping import normalize, similarity
from dsd_tool.scanner import scan


def digest(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=100000)
def label_score(label, candidate):
    return similarity(normalize(label), label, candidate)


def rank(source, concepts, limit=4):
    """Lexicographic evidence ranking, existing label similarity as tie breaker.

    Score is label similarity, not a probability or accounting correctness.
    Role/QName and context disagreements remain visible, including below Top N.
    """
    result = []
    for c in concepts:
        if c.get('scope') and c['scope'] != source.get('scope'):
            continue
        exact = bool(source.get('prefix') and source.get('name') and
                     (source['prefix'], source['name']) == (c['prefix'], c['name']))
        score = max(label_score(source.get('label', ''), c['label_ko']),
                    label_score(source.get('label_en') or source.get('label', ''), c['label_en']))
        if not exact and score <= 0:
            continue
        evidence, ambiguity = [], []
        if exact: evidence.append('QName exact')
        if normalize(source.get('label')) == normalize(c['label_ko']): evidence.append('Label exact')
        for field in ('role', 'period', 'data_type', 'dimensions'):
            if source.get(field) is None or c.get(field) is None:
                ambiguity.append(field+' unverified')
            elif source[field] == c[field]:
                evidence.append(field+' exact')
            else:
                ambiguity.append(field+' mismatch')
        if not c.get('scope'): ambiguity.append('taxonomy scope requires review')
        strong = exact and not ambiguity
        result.append({**c, 'score':round(score, 6), 'evidence':evidence,
            'ambiguity_reasons':ambiguity or ([] if strong else ['identity requires review']),
            'confidence':'high' if strong else 'low' if any('mismatch' in a for a in ambiguity) else 'medium',
            'auto_confirm_eligible':strong})
    result.sort(key=lambda c: ('QName exact' not in c['evidence'], 'role exact' not in c['evidence'],
        any('mismatch' in a for a in c['ambiguity_reasons']), -c['score'], c['taxonomy_sheet'], c['taxonomy_row']))
    if len(result) > 1:
        for c in result:
            if c['confidence'] != 'high': c['ambiguity_reasons'].append('multiple occurrences')
    return result[:limit]


def _type(value):
    name = str(value or '').split(':')[-1].removesuffix('ItemType')
    return 'text' if name in ('string','textBlock') else name


def _scope(name):
    lower = name.casefold()
    consolidated = '연결' in name or 'consolidated financial statements' in lower
    separate = '별도' in name or any(s in lower for s in ('separated financial statements','separate financial statements'))
    if consolidated and separate: raise ValueError('명시된 taxonomy scope가 서로 충돌합니다')
    if consolidated: return 'consolidated'
    if separate: return 'separate'
    return None


def prepare(dsd, taxonomy, layout, report, current_source=None):
    for key in ('company','scope','period_end','fiscal_number'):
        if not report.get(key): raise ValueError('당기 회사/범위/보고기간/기수가 필요합니다')
    if report['scope'] not in ('separate','consolidated'): raise ValueError('보고 범위 오류')
    date.fromisoformat(report['period_end'])
    paths = {'dsd':str(Path(dsd).resolve()), 'taxonomy':str(Path(taxonomy).resolve()),
             'layout':str(Path(layout).resolve())}
    if current_source: paths['current_source'] = str(Path(current_source).resolve())
    blobs = {k:Path(p).read_bytes() for k,p in paths.items()}
    hashes = {k:digest(v) for k,v in blobs.items()}
    with zipfile.ZipFile(io.BytesIO(blobs['dsd'])) as z:
        doc = scan(z.read('contents.xml').decode('utf-8-sig'))
    scopes = {'consolidated' if f.title_parts[1] else 'separate' for f in doc.fs_blocks}
    if scopes and scopes != {report['scope']}:
        raise ValueError('DSD 본문 scope와 보고 범위가 다릅니다. 한 범위의 원천을 선택하세요')
    sources = []
    for ti, table in enumerate(doc.tables):
        grid = table.grid()
        fs = next((f.sheet_name for f in doc.fs_blocks if table in f.tables), None)
        note = next((n for n in doc.notes if n.start <= table.start < n.end), None)
        for (r,c), cell in sorted(grid.items()):
            row = [v.text for (rr,cc),v in sorted(grid.items()) if rr == r and cc < c]
            headers = [v.text for (rr,cc),v in sorted(grid.items()) if rr < r and cc <= c < cc+v.colspan][-6:]
            sources.append({'id':f'{cell.start}:{cell.end}', 'start':cell.start, 'end':cell.end,
                'text':golden._text(cell.raw), 'label':next((v for v in row if v.strip()), cell.text),
                'block_id':f'table:{table.start}:{table.end}', 'table':ti+1,'row':r+1,'column':c+1,
                'headers':headers,'row_axis':row, 'column_axis':headers, 'members':None,
                'section':fs or (f'주석 {note.number} {note.title}' if note else '기타 표'),
                'scope':report['scope'], 'dimensions':None, 'period':None,
                'data_type':'text' if not re.fullmatch(r'[\d,().+\-\s]+',cell.text) else None})
    # Optional reviewed current-source index: exact offsets, not a prior mapping.
    if current_source:
        index = json.loads(blobs['current_source'])
        if (index.get('dsd_sha256') != hashes['dsd'] or index.get('taxonomy_sha256') != hashes['taxonomy']
                or index.get('report') != report):
            raise ValueError('현재 원천 index의 hash/회사/보고기간이 다릅니다')
        by_id = {s['id']:s for s in sources}
        for fact in index.get('facts', []):
            if fact.get('source_id') not in by_id or not fact.get('source_evidence'):
                raise ValueError('현재 원천 index에 DSD 셀/근거가 없습니다')
            s = by_id[fact['source_id']]
            for k in ('prefix','name','role','period','data_type','dimensions','context','source_evidence'):
                if k in fact: s[k] = fact[k]
    concepts, members = [], []
    for sheet in golden.read_xls(blobs['taxonomy'])['sheets']:
        cells = {(r+1,c+1):v for r,c,t,v,st in sheet['cells']}
        role = cells.get((1,2)); definition = cells.get((2,2), '')
        if cells.get((1,1)) != 'Role URI' or not role: raise ValueError('taxonomy Role 원천이 없습니다')
        for r in range(1,sheet['nrows']+1):
            if cells.get((r,1)) == 'DOMAIN':
                members.append({'role':role,'prefix':cells.get((r,2)),'name':cells.get((r,3))})
            if cells.get((r,1)) != 'LINEITEM': continue
            concepts.append({'id':f'{sheet["name"]}:{r}', 'taxonomy_sheet':sheet['name'], 'taxonomy_row':r,
                'role':role, 'role_definition':definition,'prefix':cells.get((r,2)), 'name':cells.get((r,3)),
                'label_ko':cells.get((r,4),''),'label_en':cells.get((r,5),''),
                'label_role':cells.get((r,6)), 'data_type':_type(cells.get((r,7))),
                'balance':cells.get((r,8)), 'period':cells.get((r,9)), 'dimensions':None,
                'scope':_scope(sheet['name']+' '+str(definition))})
    by_label = {}
    for s in sources:
        key = normalize(s['label'])
        if key: by_label.setdefault(key, []).append(s)
    targets = []
    for sheet in golden.read_xls(blobs['layout'])['sheets']:
        cells = {(r,c):v for r,c,t,v,st in sheet['cells'] if t == 1}
        for (r,c), value in sorted(cells.items()):
            label = next((cells[(r,col)] for col in range(c) if (r,col) in cells and cells[(r,col)].strip()), value)
            headers = [cells[(rr,c)] for rr in range(max(0,r-6),r) if (rr,c) in cells]
            possible = list(by_label.get(normalize(label), []))
            possible.sort(key=lambda s: (-len(set(map(normalize,s['headers'])) & set(map(normalize,headers))),s['start']))
            targets.append({'id':f'{sheet["name"]}:{r+1}:{c+1}', 'sheet':sheet['name'],'row':r+1,'column':c+1,
                'sample_text':value, 'row_axis':label,'column_axis':headers, 'period_block':headers,
                'members':None, 'section':sheet['name'], 'comparison_position':'unverified',
                'source_candidates':[{'source_id':s['id'],'evidence':['row label exact'],
                    'ambiguity_reasons':['period/axes require review; sample value is not evidence']} for s in possible[:4]]})
    # Cache recommendations once per row identity; DSD values never participate in ranking.
    cache = {}
    for s in sources:
        key = json.dumps({k:s.get(k) for k in ('label','prefix','name','role','period','data_type','dimensions','scope')},sort_keys=True)
        if key not in cache: cache[key] = rank(s,concepts)
        s['candidates'] = cache[key]
    return {'version':1,'report':copy.deepcopy(report),'paths':paths,'hashes':hashes,
            'sources':sources,'taxonomy':concepts,'members':members,'targets':targets,'decisions':{},'revision':0}


def stale(draft):
    for k,p in draft['paths'].items():
        try:
            if digest(Path(p).read_bytes()) != draft['hashes'][k]: return True
        except OSError: return True
    return False


def _validate(draft, target, decision):
    if _scope(target['sheet']) and _scope(target['sheet']) != draft['report']['scope']:
        raise ValueError('배치 scope 충돌')
    sources = {s['id']:s for s in draft['sources']}
    s = sources.get(decision.get('source_id'))
    if not s or not str(decision.get('source_evidence','')).strip(): raise ValueError('DSD 셀 원천과 검토 근거가 필요합니다')
    if decision['kind'] == 'static':
        if not decision.get('use_source_text') and s['text'] != target['sample_text']:
            raise ValueError('정적 표시값과 DSD 원천이 다릅니다; 원문 사용을 선택하세요')
        return
    c = next((c for c in draft['taxonomy'] if c['id'] == decision.get('taxonomy_id')), None)
    if not c: raise ValueError('현재 taxonomy 요소를 선택하세요')
    ctx = decision.get('context', {})
    if c.get('scope') and c['scope'] != draft['report']['scope']: raise ValueError('taxonomy scope 충돌')
    if ctx.get('company') != draft['report']['company'] or ctx.get('scope') != draft['report']['scope']:
        raise ValueError('company/scope 충돌')
    instant = bool(ctx.get('instant'))
    if c['period'] not in ('INSTANT','DURATION') or instant != (c['period'] == 'INSTANT'):
        raise ValueError('period 미확정 또는 충돌')
    end = ctx.get('instant') if instant else ctx.get('end')
    if end not in [draft['report']['period_end'],*draft['report'].get('comparison_ends',[])]: raise ValueError('period 미확정')
    if date.fromisoformat(end) > date.fromisoformat(draft['report']['period_end']): raise ValueError('period 미래 비교기간')
    if not instant and (not ctx.get('start') or date.fromisoformat(ctx['start']) > date.fromisoformat(end)):
        raise ValueError('period 시작일 오류')
    dims = ctx.get('dimensions')
    if not decision.get('dimensions_reviewed') or not isinstance(dims,list): raise ValueError('dimension 검토 필요')
    known = {m['prefix']+':'+m['name'] for m in draft['members'] if m['role'] == c['role'] and m['prefix'] and m['name']}
    axes = set()
    for d in dims:
        if not isinstance(d,dict) or d.get('axis') not in known or d.get('member') not in known or d['axis'] in axes:
            raise ValueError('dimension 축/구성요소를 현재 Role에서 확인할 수 없습니다')
        axes.add(d['axis'])
    for field in ('prefix','name','role','period','data_type','dimensions'):
        chosen = dims if field == 'dimensions' else c[field]
        if s.get(field) is not None and s[field] != chosen: raise ValueError(field+' mismatch: 당기 원천과 다릅니다')
    if s.get('context') and s['context'] != ctx: raise ValueError('period/dimension context 원천 불일치')
    if not ctx.get('unit'): raise ValueError('단위 검토 필요')
    if c['data_type'] in ('monetary','shares','perShare','percent','pure'):
        if not re.fullmatch(r'(?:-?\d+(?:,\d{3})*(?:\.\d+)?|\(\d+(?:,\d{3})*(?:\.\d+)?\))',s['text'].strip()):
            raise ValueError('data_type 숫자 원천 불일치')
    elif c['data_type'] not in ('text','date','duration'): raise ValueError('지원하지 않는 data_type')


def decide(draft, target_id, decision):
    if stale(draft): raise ValueError('원천 변경(stale): 새 후보를 생성하고 재검토하세요')
    target = next((t for t in draft['targets'] if t['id'] == target_id),None)
    if not target: raise ValueError('배치 셀이 없습니다')
    out = copy.deepcopy(draft)
    if decision.get('kind') == 'unresolved': out['decisions'].pop(target_id,None)
    else:
        if decision.get('kind') not in ('binding','static'): raise ValueError('확정 종류 오류')
        _validate(draft,target,decision)
        out['decisions'][target_id] = {**copy.deepcopy(decision),'state':'manual' if decision.get('manual') else 'confirmed',
            'reviewed_by':getpass.getuser(),'reviewed_at':datetime.now(timezone.utc).isoformat(),
            'source_block_id':next(s['block_id'] for s in draft['sources'] if s['id'] == decision['source_id'])}
    out['revision'] += 1
    return out


def coverage(draft):
    out = dict(required=len(draft['targets']),confirmed=0,unresolved=0,conflicts=0,
               static_without_evidence=0,taxonomy_unresolved=0,period_unresolved=0,dimension_unresolved=0,
               stale=stale(draft),ready=False)
    for t in draft['targets']:
        d = draft['decisions'].get(t['id'])
        if not d:
            out['unresolved'] += 1
            for k in ('taxonomy_unresolved','period_unresolved','dimension_unresolved'): out[k] += 1
            continue
        try: _validate(draft,t,d)
        except (ValueError,TypeError,KeyError) as e:
            out['conflicts'] += 1
            for field in ('taxonomy','period','dimension'):
                if field in str(e): out[field+'_unresolved'] += 1
            if d.get('kind') == 'static': out['static_without_evidence'] += 1
        else: out['confirmed'] += 1
    out['ready'] = bool(out['required'] and out['confirmed'] == out['required'] and not out['conflicts'] and not out['stale'])
    return out


def review_states(draft):
    """Display status is derived, never a second source of approval truth."""
    changed = stale(draft)
    states = {}
    for t in draft['targets']:
        d = draft['decisions'].get(t['id'])
        if changed: state, reason = 'stale', '원천 변경 · 재검토 필요'
        elif not d:
            state = 'automatic_candidate' if t['source_candidates'] else 'source_missing'
            reason = '미확정 · 사용자 검토 필요'
        else:
            try: _validate(draft,t,d)
            except (ValueError,KeyError,TypeError) as e: state, reason = 'conflict', str(e)
            else: state, reason = d['state'], '사용자 검토 저장됨'
        states[t['id']] = {'state':state,'reason':reason}
    return states


def generate(draft, out_dir):
    gate = coverage(draft)
    if gate['stale']: raise ValueError('원천 변경(stale): 재검토 필요')
    if not gate['ready']: raise ValueError('coverage 미확정 또는 충돌: 완전 생성 불가')
    manifest = {'report':draft['report'], **{k+'_sha256':v for k,v in draft['hashes'].items()},'bindings':[],'static_cells':[]}
    # Static display replacements are sourced too. Pass the validated temporary
    # layout to the unchanged writer; never fill missing cells with sample values.
    blobs = {k:Path(p).read_bytes() for k,p in draft['paths'].items()}
    if any(digest(v) != draft['hashes'][k] for k,v in blobs.items()): raise ValueError('원천 변경: 재검토 필요')
    layout = golden.read_xls(blobs['layout'])
    for t in draft['targets']:
        d = draft['decisions'][t['id']]; s = next(s for s in draft['sources'] if s['id'] == d['source_id'])
        b = {k:t[k] for k in ('sheet','row','column')}; b['source_evidence'] = d['source_evidence']
        if d['kind'] == 'static':
            for sheet in layout['sheets']:
                if sheet['name'] == t['sheet']:
                    for cell in sheet['cells']:
                        if cell[:2] == [t['row']-1,t['column']-1]: cell[3] = s['text']
            manifest['static_cells'].append(b)
        else:
            c = next(c for c in draft['taxonomy'] if c['id'] == d['taxonomy_id'])
            b.update({k:c[k] for k in ('taxonomy_sheet','taxonomy_row','role','prefix','name','data_type')})
            b.update(source_start=s['start'],source_end=s['end'],context=d['context'])
            manifest['bindings'].append(b)
    with tempfile.TemporaryDirectory(prefix='auditdesk_binding_', dir=Path(out_dir).resolve().parent) as temp:
        paths = {}
        for k in ('dsd','taxonomy','layout'):
            data = golden._encode(layout) if k == 'layout' else blobs[k]
            paths[k] = Path(temp)/(k+'.xls' if k != 'dsd' else 'input.dsd')
            paths[k].write_bytes(data); manifest[k+'_sha256'] = digest(data)
        result = golden.build_current(paths['dsd'],paths['taxonomy'],paths['layout'],manifest,out_dir)
    result['binding_review'] = {'source_hashes':draft['hashes'],'revision':draft['revision'],'coverage':gate,
                                'decisions':draft['decisions'],
                                'scope':'user-reviewed explicit bindings; editor compatibility not tested'}
    (Path(out_dir)/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
