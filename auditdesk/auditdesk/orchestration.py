"""Current-first orchestration. Evidence never writes binding decisions."""
import calendar
import copy
from datetime import date
import io
import re
import sqlite3
from pathlib import Path
import zipfile

from . import binding, binding_review, golden
from dsd_tool.scanner import scan


def analyze(path):
    blob = Path(path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        text = z.read('contents.xml').decode('utf-8-sig')
    doc = scan(text)
    tables = []
    for table in doc.tables:
        fs = next((f.sheet_name for f in doc.fs_blocks if table in f.tables), None)
        note = next((n for n in doc.notes if n.start <= table.start < n.end), None)
        tables.append({'id': f'table:{table.start}:{table.end}',
            'section': fs or (f'주석 {note.number} {note.title}' if note else '기타 표'),
            'kind': 'body' if fs else 'notes' if note else 'other',
            'cells': [{'source_id': f'{c.start}:{c.end}', 'row':r+1, 'column':col+1,
                'rowspan':c.rowspan,'colspan':c.colspan,'display':golden._text(c.raw),
                'data_type_candidate':'numeric' if re.fullmatch(r'[\d,().+\-\s]+',c.text) else 'text'}
                for (r,col),c in sorted(table.grid().items())]})
    periods = set()
    for y,m,d in re.findall(r'(20\d{2})[.년/\-]\s*(\d{1,2})[.월/\-]\s*(\d{1,2})', text):
        try: periods.add(date(int(y),int(m),int(d)).isoformat())
        except ValueError: pass
    companies = sorted(set(golden._text(v).strip() for v in re.findall(
        r'<(?:COMPANY-NAME|CORPORATION-NAME)\b[^>]*>(.*?)</(?:COMPANY-NAME|CORPORATION-NAME)>',text,re.S)))
    companies=[value for value in companies if value]
    return {'sha256':binding.digest(blob),'tables':tables,
        'statements':[f.sheet_name for f in doc.fs_blocks],
        'notes':[{'number':n.number,'title':n.title} for n in doc.notes],
        'period_candidates':sorted(periods),'company_candidates':companies,
        'scope_candidates':sorted({'consolidated' if f.title_parts[1] else 'separate' for f in doc.fs_blocks}),
        'identity_state':'needs_review'}


def find_prior(cli, company, period_end, report_type):
    current=date.fromisoformat(period_end)
    if report_type not in ('annual','half','q1','q3'): raise ValueError('보고서 종류를 선택하세요')
    prior=date(current.year-1,current.month,min(current.day,calendar.monthrange(current.year-1,current.month)[1]))
    match=re.fullmatch(r'(?:entity)?(\d{8})',company or '')
    code=match.group(1) if match else cli.resolve_corp_code(company)
    from dart_explorer.xbrl.pipeline import DETAIL
    docs=cli.search(corp_code=code,bgn_de=f'{prior.year}0101',end_de=f'{current.year}1231',
                    pblntf_detail_ty=DETAIL[report_type],last_reprt_at='N')
    expected={'annual':'사업보고서','half':'반기보고서','q1':'분기보고서','q3':'분기보고서'}[report_type]
    found={}
    for doc in docs:
        name=doc.get('report_nm','')
        if (doc.get('corp_code')==code and expected in name
                and re.search(r'\('+str(prior.year)+r'\.0?'+str(prior.month)+r'\)',name)):
            found[doc['rcept_no']]={**doc,'report_type':report_type,'period_end':prior.isoformat()}
    documents=[found[k] for k in sorted(found,reverse=True)]
    return {'corp_code':code,'period':prior.isoformat(),'documents':documents,
            'selection_required':len(documents)>1,'state':'done' if documents else 'needs_review',
            'message':'전기 동기 공시 후보를 확인하세요' if documents else '해당 회사 전기 동기 보고서 없음 — 당기 원천으로 계속하거나 검색 조건을 확인하세요'}


def taxonomy_changes(prior, current):
    # QName identity is preserved per Role occurrence; never a label-only join.
    fields=('role','label_ko','data_type','period','dimensions','namespace')
    rows=[]; used=set()
    for old in prior:
        same=[(i,c) for i,c in enumerate(current) if (c['prefix'],c['name'])==(old['prefix'],old['name'])]
        exact=[(i,c) for i,c in same if c['role']==old['role']]
        candidates=exact or same
        if not candidates:
            rows.append({'prefix':old['prefix'],'name':old['name'],'role':old['role'],
                         'status':'removed','reasons':['현재 제공 원천에 없음; 폐지 확정 아님']}); continue
        for i,new in candidates:
            used.add(i)
            reasons=[f for f in fields if old.get(f) is not None and new.get(f) is not None and old[f]!=new[f]]
            unknown=[f+' unverified' for f in fields if old.get(f) is None or new.get(f) is None]
            extension=old['prefix'] not in ('ifrs-full','dart-gcd','dart')
            state='extension_review' if extension else 'changed' if reasons else 'needs_review' if unknown else 'reusable_candidate'
            rows.append({'prefix':new['prefix'],'name':new['name'],'role':new['role'],
                'prior_role':old['role'],'status':state,'reasons':reasons+unknown})
    rows.extend({**{k:c[k] for k in ('prefix','name','role')},'status':'new',
                 'reasons':['전기 제공 원천에 없음; 신규 제정 확정 아님']}
                for i,c in enumerate(current) if i not in used)
    return sorted(rows,key=lambda r:(r['prefix'],r['name'],r['role'],r['status']))


def references(path, concepts, company, industry=''):
    if not path or not Path(path).is_file(): return []
    current={(c['prefix'],c['name']) for c in concepts}
    grouped={}
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as con:
        if not industry:
            row=con.execute('SELECT induty_code FROM companies WHERE corp_code=? OR corp_name=? LIMIT 1',
                            (company.removeprefix('entity'),company)).fetchone()
            if row and row[0]: industry=str(row[0])
        columns={r[1] for r in con.execute('PRAGMA table_info(companies)')}
        extra=','.join('c.'+k if k in columns else 'NULL' for k in ('rcept_no','year','report_nm'))
        data=con.execute('SELECT u.element_id,u.label_ko,u.roles,u.dims,c.corp_code,c.corp_name,c.induty_code '
                         +','+extra+' FROM usages u JOIN companies c ON c.corp_code=u.corp_code WHERE c.status=? ORDER BY u.element_id,c.corp_code',('ok',)).fetchall()
    for eid,label,roles,dims,code,name,induty,receipt,year,report_name in data:
        prefix,sep,local=eid.partition('_')
        if not sep or (prefix,local) not in current or name==company or code==company.removeprefix('entity'): continue
        row=grouped.setdefault((prefix,local),{'prefix':prefix,'name':local,'issuers':set(),
            'labels':set(),'roles':set(),'dimensions':set(),'same_industry':set(),'filings':[]})
        row['issuers'].add(code)
        if label: row['labels'].add(label)
        if roles: row['roles'].add(roles)
        if dims: row['dimensions'].add(dims)
        if industry and str(induty)==industry: row['same_industry'].add(code)
        row['filings'].append({'corp_code':code,'company':name,'receipt':receipt,'year':year,'report_name':report_name})
    out=[]
    for key,row in sorted(grouped.items()):
        out.append({**{k:sorted(v) if isinstance(v,set) else v for k,v in row.items()},'id':row['prefix']+':'+row['name'],
                    'issuer_count':len(row['issuers']),'origin':'OPENDART_REFERENCE',
                    'message':f'타사 {len(row["issuers"])}개에서 확인 (동일 업종 {len(row["same_industry"])}개); 현재 회사 확정 근거 아님'})
    return out


def prepare(body, prior=None, progress=lambda message:None, prior_loader=None):
    if body.get('mode') not in ('first','rollforward'): raise ValueError('전환 모드를 선택하세요')
    for key in ('dsd','taxonomy','layout','current_authority'):
        if not isinstance(body.get(key),str) or not body[key].strip():
            raise ValueError('당기 DSD, 적용 taxonomy.xls, 검토된 배치.xls 및 당기 적용 확인 근거가 필요합니다')
    report=body.get('report',{})
    if body.get('authority_report',report)!=report: raise ValueError('현재 원천의 회사/범위/기간이 다릅니다')
    progress('당기 DSD 분석')
    analysis=analyze(body['dsd'])
    if analysis['company_candidates'] and report.get('company') not in analysis['company_candidates']:
        raise ValueError('DSD 회사와 지정 회사가 다릅니다')
    if prior_loader:
        progress('회사 전기 공시 검색·수신')
        prior=prior_loader()
    progress('현재 taxonomy 및 배치 후보 생성')
    draft=binding.prepare(body['dsd'],body['taxonomy'],body['layout'],report,body.get('current_source'))
    if analysis['sha256']!=draft['hashes']['dsd']:
        raise ValueError('분석 중 DSD가 변경되었습니다. 같은 원천으로 다시 실행하세요')
    binding_review.enrich(draft)
    from dart_explorer.xbrl.corpus import DEFAULT_DB
    corpus=body.get('corpus') or DEFAULT_DB
    progress('공시 corpus 근거 연결')
    corpus_hash=binding.digest(Path(corpus).read_bytes()) if Path(corpus).is_file() else None
    try:
        refs=references(corpus,draft['taxonomy'],report['company'],body.get('industry',''))
    except sqlite3.DatabaseError:
        raise ValueError('corpus DB의 형식/테이블을 확인하세요. Explorer에서 구축한 corpus를 선택하세요') from None
    if Path(corpus).is_file():
        draft['paths']['reference_corpus']=str(Path(corpus).resolve())
        draft['hashes']['reference_corpus']=binding.digest(Path(corpus).read_bytes())
        if draft['hashes']['reference_corpus']!=corpus_hash: raise ValueError('분석 중 corpus 원천이 변경되었습니다. 다시 실행하세요')
    if prior and (prior['company']!=report['company'] or prior['scope']!=report['scope']
                  or prior['period_end']>=report['period_end']):
        raise ValueError('전기 원천의 회사/범위/기간이 다릅니다')
    current_package=None
    if body.get('current_package'):
        from .orchestration_sources import package_evidence
        current_package=package_evidence(body['current_package'],report['scope'],report['period_end'],'CURRENT_INSTANCE')
        for key,path in current_package['paths'].items():
            draft['paths']['current_package_'+key]=path
            draft['hashes']['current_package_'+key]=current_package['hashes'][key]
    comparison_concepts=copy.deepcopy([c for c in draft['taxonomy'] if c.get('scope') in (None,report['scope'])])
    if current_package:
        for c in comparison_concepts:
            matches=[p for p in current_package['concepts'] if all(p[k]==c[k] for k in ('prefix','name','role'))]
            if len(matches)==1:
                p=matches[0]
                for k in ('namespace','schema_id','dimensions'):
                    c[k]=p.get(k)
    changes=taxonomy_changes(prior['concepts'],comparison_concepts) if prior else []
    if prior:
        for key,path in prior.get('paths',{}).items():
            draft['paths']['prior_'+key]=path
            draft['hashes']['prior_'+key]=prior['hashes'][key]
    progress('추천 근거 정리')
    evidence=[]
    by_ref={(r['prefix'],r['name']):r for r in refs}
    aliases={}
    for ref in refs:
        for label in ref['labels']:
            aliases.setdefault(binding.normalize(label),set()).add((ref['prefix'],ref['name']))
    by_change={}
    for row in changes: by_change.setdefault((row['prefix'],row['name'],row['role']),[]).append(row)
    for source in draft['sources']:
        candidates=[]
        # Existing scores and candidate arrays are untouched. Corpus alias
        # evidence is a separate recommendation, resolved to current occurrences.
        additional=[]
        identities=aliases.get(binding.normalize(source['label']),set())
        if identities:
            matched=[{**c,'label_ko':source['label']} for c in draft['taxonomy'] if (c['prefix'],c['name']) in identities]
            additional=binding.rank(source,matched)
        reference_scores={c['id']:c['score'] for c in additional}
        suggestions=list(source['candidates'])
        existing={c['id'] for c in suggestions}
        suggestions.extend(c for c in additional if c['id'] not in existing)
        for c in suggestions:
            provenance=[{'origin':'CURRENT_DSD','message':'원문 label/표; 기간·차원은 별도 검토'},
                        {'origin':'CURRENT_TAXONOMY','message':'현재 제공 taxonomy의 QName/Role 출현','taxonomy_id':c['id']}]
            ref=by_ref.get((c['prefix'],c['name']))
            if ref: provenance.append({'origin':'OPENDART_REFERENCE','message':ref['message'],
                'issuer_count':ref['issuer_count'],'reference_id':ref['id']})
            diff=by_change.get((c['prefix'],c['name'],c['role']),[])
            if diff: provenance.append({'origin':'PRIOR_COMPANY_XBRL','message':'전기 공시와 당기 제공 정의 비교','changes':diff})
            if source.get('source_evidence'):
                provenance.append({'origin':'CURRENT_DSD','message':'사용자 검토 current source index; 원시 instance 자동 연결 아님'})
            if current_package and any((f['prefix'],f['name'])==(c['prefix'],c['name']) for f in current_package['facts']):
                provenance.append({'origin':'CURRENT_INSTANCE','message':'현재 제공 instance QName 출현; DSD 셀/context 연결은 별도 검토'})
            candidates.append({'taxonomy_id':c['id'],'score':c['score'] if c['id'] in existing else None,
                'reference_label_score':reference_scores.get(c['id']),'provenance':provenance,
                'changes':diff,'needs_review':True})
        if body['mode']=='rollforward':
            candidates.sort(key=lambda c:not any(r['status']=='reusable_candidate' for r in c['changes']))
        evidence.append({'source_id':source['id'],'candidates':candidates,
                         'extension_review':not candidates or any(c['prefix'] not in ('ifrs-full','dart','dart-gcd') for c in source['candidates'])})
    # The source DB and its hash remain the authority for full case details.
    # Do not duplicate long corpus dimension strings in every binding payload.
    compact_refs=[]
    for ref in refs:
        compact={**ref}
        for field in ('labels','roles','dimensions'):
            compact[field]=[value[:240] for value in ref[field][:3]]
            compact[field+'_variants']=len(ref[field])
            compact[field+'_truncated']=len(ref[field])>3 or any(len(v)>240 for v in ref[field][:3])
        compact['filings']=ref['filings'][:3]
        compact['detail_available']=True
        compact_refs.append(compact)
    draft['workflow']={'mode':body['mode'],'analysis':analysis,'references':compact_refs,'changes':changes,
        'current_instance':{k:v for k,v in current_package.items() if k not in ('concepts','paths','hashes')} if current_package else None,
        'evidence':evidence,'authority':{'report':copy.deepcopy(report),'evidence':body['current_authority'],
            'state':'user_identified','package_state':'acquired' if current_package else 'not_provided'},
        'prior':{k:v for k,v in prior.items() if k not in ('concepts','paths','hashes')} if prior else None,
        'steps':{'analysis':{'state':'done'},'taxonomy':{'state':'done','message':'사용자 지정 당기 export; schema/linkbase 확보는 별도'},
            'reference':{'state':'done' if refs else 'needs_review','message':f'현재 QName reference {len(refs)}개'},
            'prior':{'state':'done' if prior else 'needs_review' if body['mode']=='rollforward' else 'waiting',
                     'message':'전기 패키지 참고 근거' if prior else '전기 없음; 당기 기준 검토 가능'},
            'recommendation':{'state':'done'},'review':{'state':'needs_review'},'golden':{'state':'waiting'}}}
    refresh(draft)
    return draft


def refresh(draft):
    w=draft.get('workflow')
    if not w: return
    cov=binding.coverage(draft); required=cov['required']; confirmed=0 if cov['stale'] else cov['confirmed']
    counts={s:sum(r['status']==s for r in w['changes']) for s in ('reusable_candidate','changed','new','removed','extension_review','needs_review')}
    candidate=sum(bool(t['source_candidates']) for t in draft['targets'])
    enriched={s['source_id'] for s in w['evidence'] if any(
        p['origin'] in ('CURRENT_INSTANCE','PRIOR_COMPANY_XBRL','OPENDART_REFERENCE')
        for c in s['candidates'] for p in c['provenance'])}
    evidence_count=sum(any(s['source_id'] in enriched for s in t['source_candidates']) for t in draft['targets'])
    w['coverage']={'required':required,'mapping_candidate':candidate,'confirmed':confirmed,
        'unresolved':required-confirmed,'review_required':required-confirmed,
        'candidate_coverage_pct':round(100*candidate/required,2) if required else 0,
        'automatic_evidence_available':evidence_count,
        'automatic_evidence_coverage_pct':round(100*evidence_count/required,2) if required else 0,
        'prior_reusable':counts['reusable_candidate'],
        'taxonomy_valid_reusable':counts['reusable_candidate'],'changes':counts,'stale':cov['stale']}
    w['steps']['review']['state']='done' if cov['ready'] else 'needs_review'
    w['steps']['golden']['state']='waiting' if cov['ready'] else 'needs_review'
    w['steps']['golden']['message']='100% 확정 후 생성 가능' if cov['ready'] else '미확정/conflict/stale로 생성 차단'
    if cov['ready'] and w.get('output_revision')==draft['revision']:
        if all(Path(p).is_file() for p in w.get('output',{}).values()):
            w['steps']['golden']={'state':'done','message':'확정 당시 산출 완료; 편집기 호환성은 별도 검증'}


def review_projection(draft, review):
    w=draft.get('workflow')
    if not w or w['mode']!='rollforward': return review
    evidence={s['source_id']:s for s in w['evidence']}
    targets={t['id']:t for t in draft['targets']}
    for row in review['rows']:
        source_candidates=targets[row['id']]['source_candidates']
        candidates=[c for source in source_candidates
                    for c in evidence.get(source['source_id'],{}).get('candidates',[])]
        reusable=(len(source_candidates)==1 and len(candidates)==1 and candidates[0]['changes']
                  and all(c['status']=='reusable_candidate' for c in candidates[0]['changes']))
        # Prior structure equality alone does not prove the current DSD layout.
        row['workflow_status']='reusable_candidate' if reusable and row['state']=='high' else 'needs_review'
    review['rows'].sort(key=lambda row:row['workflow_status']=='reusable_candidate')
    return review
