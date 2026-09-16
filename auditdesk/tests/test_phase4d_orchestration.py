"""Orchestration must retain current authority and explicit binding approval."""
import copy
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_phase4_golden import current_case
from test_phase4b_binding import confirm_all


def core():
    from auditdesk import orchestration
    return orchestration


def inputs(tmp_path, mode='first'):
    dsd, manifest = current_case(tmp_path)
    return dict(mode=mode, dsd=str(dsd), taxonomy=str(tmp_path/'current_taxonomy.xls'),
                layout=str(tmp_path/'layout.xls'), report=manifest['report'],
                current_authority='당기 적용 원천을 확인했습니다',corpus=str(tmp_path/'no-corpus.sqlite')), manifest


def test_dsd_analysis_preserves_cells_merges_and_report_candidates(tmp_path):
    body, _ = inputs(tmp_path)
    result = core().analyze(body['dsd'])
    assert result['tables'][0]['cells'][1]['display'] == '1,234'
    assert result['tables'][0]['cells'][1]['colspan'] == 1
    assert '2026-06-30' in result['period_candidates']


def test_first_conversion_requires_no_prior_and_never_confirms(tmp_path):
    body, _ = inputs(tmp_path)
    d = core().prepare(body)
    assert d['decisions'] == {}
    assert d['workflow']['mode'] == 'first'
    assert d['workflow']['coverage']['review_required'] == 2
    assert d['workflow']['analysis']['tables']
    assert d['workflow']['steps']['review']['state'] == 'needs_review'


@pytest.mark.parametrize('missing', ['taxonomy', 'layout', 'current_authority'])
def test_missing_current_source_never_falls_back_to_prior(tmp_path, missing):
    body, _ = inputs(tmp_path, 'rollforward'); body[missing] = ''
    with pytest.raises(ValueError): core().prepare(body)


def concept(**kw):
    return dict(prefix='ifrs-full', name='Cash', role='urn:bs', label_ko='현금',
                data_type='monetary', period='INSTANT', dimensions=[], namespace='urn:ifrs', **kw)


@pytest.mark.parametrize('field,value', [('role','urn:new'),('period','DURATION'),
                                       ('dimensions',['axis']),('data_type','text'),('label_ko','현금성자산')])
def test_prior_changes_require_review(field, value):
    old = concept(); new = {**old,field:value}
    result = core().taxonomy_changes([old], [new])
    assert any(r['status']=='changed' and field in r['reasons'] for r in result)


def test_removed_new_extension_and_unknown_dimensions_are_distinct():
    old = [concept(), {**concept(), 'name':'Removed'}, {**concept(), 'prefix':'company'}]
    new = [concept(), {**concept(), 'name':'New'}, {**concept(), 'prefix':'company'}]
    rows = core().taxonomy_changes(old,new)
    assert {'reusable_candidate','removed','new','extension_review'} <= {r['status'] for r in rows}
    unknown = core().taxonomy_changes([{**concept(),'dimensions':None}], [concept()])
    assert unknown[0]['status'] != 'reusable_candidate'


class Client:
    def resolve_corp_code(self, name): return '12345678'
    def search(self, **kw):
        return [{'corp_code':'12345678','rcept_no':'20250801000001','report_nm':'반기보고서 (2025.06)'},
                {'corp_code':'12345678','rcept_no':'20250801000002','report_nm':'[정정]반기보고서 (2025.06)'},
                {'corp_code':'87654321','rcept_no':'20250801000003','report_nm':'반기보고서 (2025.06)'},
                {'corp_code':'12345678','rcept_no':'20260501000004','report_nm':'분기보고서 (2026.03)'}]


def test_prior_search_preserves_multiple_correct_company_period_candidates():
    result = core().find_prior(Client(), 'company', '2026-06-30', 'half')
    assert result['selection_required'] is True
    assert len(result['documents']) == 2
    assert result['period'] == '2025-06-30'
    assert all(d['corp_code']=='12345678' for d in result['documents'])


def test_no_prior_is_explicit_not_peer_fallback():
    client=Client(); client.search=lambda **kw: []
    result=core().find_prior(client,'company','2026-06-30','half')
    assert result['state']=='needs_review' and result['documents']==[]


def test_reference_frequency_is_evidence_only_current_identity_required(tmp_path):
    body, _ = inputs(tmp_path)
    db=tmp_path/'corpus.sqlite'
    with sqlite3.connect(db) as c:
        c.executescript('CREATE TABLE companies(corp_code,corp_name,induty_code,status); CREATE TABLE usages(corp_code,element_id,label_ko,roles,dims,n_facts,is_ext);')
        for i in range(20):
            c.execute('INSERT INTO companies VALUES(?,?,?,?)',(str(i),'peer','20','ok'))
            c.execute('INSERT INTO usages VALUES(?,?,?,?,?,?,?)',(str(i),'company_Cash','현금','bs','',1,0))
        c.execute('INSERT INTO usages VALUES(?,?,?,?,?,?,?)',('0','old_Removed','현금','bs','',99,0))
    body['corpus']=str(db)
    draft=core().prepare(body)
    assert draft['decisions']=={}
    assert draft['workflow']['references'][0]['issuer_count']==20
    assert all(r['name']!='Removed' for r in draft['workflow']['references'])
    assert draft['workflow']['references'][0]['origin']=='OPENDART_REFERENCE'


def client(tmp_path, monkeypatch):
    from auditdesk import jobs
    from auditdesk.routers import orchestration_api, binding_api
    monkeypatch.setattr(jobs,'_DB',str(tmp_path/'app.sqlite'))
    app=FastAPI(); app.include_router(orchestration_api.router,prefix='/workflows')
    app.include_router(binding_api.router,prefix='/bindings')
    return TestClient(app)


def test_api_input_review_to_real_biff_and_gate(tmp_path, monkeypatch):
    body, manifest=inputs(tmp_path)
    c=client(tmp_path,monkeypatch)
    r=c.post('/workflows',json=body); assert r.status_code==200, r.text
    key=r.json()['id']; draft=c.get('/bindings/'+key).json()
    assert c.post('/bindings/'+key+'/generate',json={'revision':0,'out_dir':str(tmp_path/'blocked')}).status_code==422
    confirmed=confirm_all(draft,manifest)
    for target,decision in confirmed['decisions'].items():
        response=c.put('/bindings/'+key,json={'revision':draft['revision'],'target_id':target,'decision':decision})
        assert response.status_code==200,response.text
        draft=response.json()
    view=c.get('/workflows/'+key).json()
    assert view['workflow']['coverage']['confirmed']==2
    r=c.post('/bindings/'+key+'/generate',json={'revision':draft['revision'],'out_dir':str(tmp_path/'out')})
    assert r.status_code==200,r.text
    assert Path(r.json()['excel']).read_bytes().startswith(bytes.fromhex('d0cf11e0a1b11ae1'))
    review=json.loads((tmp_path/'out'/'review.json').read_text(encoding='utf-8'))
    assert review['workflow']['mode']=='first'
    assert c.get('/workflows/'+key).json()['workflow']['steps']['golden']['state']=='done'


@pytest.mark.parametrize('field,value',[('company','other'),('scope','consolidated'),('period_end','2025-06-30')])
def test_current_source_identity_mismatch_rejected(tmp_path,field,value):
    body,_=inputs(tmp_path)
    body['authority_report']={**body['report'],field:value}
    with pytest.raises(ValueError): core().prepare(body)


def test_deterministic_evidence_and_source_stale(tmp_path):
    body,_=inputs(tmp_path)
    one=core().prepare(body); two=core().prepare(body)
    assert one['workflow']==two['workflow']
    Path(body['dsd']).write_bytes(b'changed')
    from auditdesk import binding
    assert binding.coverage(one)['stale']


def test_change_priority_does_not_mutate_scores_or_confirmations(tmp_path):
    body,_=inputs(tmp_path)
    draft=core().prepare(body)
    original=copy.deepcopy(draft['sources'])
    core().refresh(draft)
    assert draft['sources']==original and not draft['decisions']


def test_missing_key_is_actionable_and_not_500(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    from auditdesk.routers import explorer
    from fastapi import HTTPException
    def absent(): raise HTTPException(409,'OpenDART API 키가 설정되지 않았습니다')
    monkeypatch.setattr(explorer,'_client',absent)
    r=c.post('/workflows/prior-search',json={'company':'company','period_end':'2026-06-30','report_type':'half'})
    assert r.status_code==409 and 'API 키' in r.text


def package(tmp_path, period='2025-06-30', scope='별도'):
    """Tiny actual package, created only inside pytest's temporary directory."""
    folder=tmp_path/'package';folder.mkdir()
    (folder/'company.xsd').write_text('''<schema xmlns="http://www.w3.org/2001/XMLSchema" xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xbrli="http://www.xbrl.org/2003/instance" targetNamespace="urn:company"><annotation><appinfo><link:roleType roleURI="urn:current:bs"><link:definition>재무상태표 - '''+scope+'''</link:definition></link:roleType></appinfo></annotation><element id="company_Cash" name="Cash" type="xbrli:monetaryItemType" xbrli:periodType="instant"/></schema>''',encoding='utf-8')
    (folder/'company_pre.xml').write_text('''<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink"><link:presentationLink xlink:role="urn:current:bs"><link:loc xlink:label="a" xlink:href="company.xsd#company_Cash"/></link:presentationLink></link:linkbase>''',encoding='utf-8')
    (folder/'company.xbrl').write_text('''<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:company="urn:company"><xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="urn:issuer">12345678</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>'''+period+'''</xbrli:instant></xbrli:period></xbrli:context><xbrli:unit id="u"><xbrli:measure>KRW</xbrli:measure></xbrli:unit><company:Cash contextRef="c" unitRef="u" decimals="0">100</company:Cash></xbrli:xbrl>''',encoding='utf-8')
    return folder


def test_package_keeps_actual_namespace_context_unit_and_relationships(tmp_path):
    from auditdesk.orchestration_sources import package_evidence
    result=package_evidence(package(tmp_path),'separate','2025-06-30')
    assert result['concepts'][0]['namespace']=='urn:company'
    assert result['facts'][0]['context_id']=='c'
    assert result['facts'][0]['unit_ref']=='u'
    assert result['facts'][0]['origin']=='PRIOR_COMPANY_XBRL'
    assert result['components']['calculation'] is False


@pytest.mark.parametrize('scope,period',[('consolidated','2025-06-30'),('separate','2024-06-30')])
def test_prior_package_scope_period_mixing_rejected(tmp_path,scope,period):
    from auditdesk.orchestration_sources import package_evidence
    with pytest.raises(ValueError): package_evidence(package(tmp_path),scope,period)


def test_current_package_is_hashed_and_not_replaced_by_prior(tmp_path):
    body,_=inputs(tmp_path)
    body['current_package']=str(package(tmp_path,'2026-06-30'))
    d=core().prepare(body)
    assert d['workflow']['authority']['package_state']=='acquired'
    assert any(k.startswith('current_package_') for k in d['paths'])
    assert d['workflow']['current_instance']['facts'][0]['origin']=='CURRENT_INSTANCE'


def test_acquisition_selection_roundtrip_to_review_and_writer(tmp_path,monkeypatch):
    import zipfile
    body,manifest=inputs(tmp_path,'rollforward')
    folder=package(tmp_path)
    archive=tmp_path/'prior.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for p in folder.iterdir():z.write(p,p.name)
    from auditdesk.routers import explorer
    from dart_explorer.xbrl import pipeline
    monkeypatch.setattr(explorer,'_client',lambda:Client())
    monkeypatch.setattr(pipeline,'download_xbrl',lambda *a:(archive.read_bytes(),str(archive)))
    c=client(tmp_path,monkeypatch)
    assert c.post('/workflows',json=body).status_code==409
    body['prior_receipt']='20250801000002'
    r=c.post('/workflows',json=body); assert r.status_code==200,r.text
    d=r.json();assert d['workflow']['prior']['receipt']==body['prior_receipt']
    assert not d['decisions'] and d['workflow']['changes'][0]['status']=='extension_review'
    confirmed=confirm_all(d,manifest)
    for target,decision in confirmed['decisions'].items():
        r=c.put('/bindings/'+d['id'],json={'revision':d['revision'],'target_id':target,'decision':decision})
        assert r.status_code==200,r.text
        d=r.json()
    r=c.post('/bindings/'+d['id']+'/generate',json={'revision':d['revision'],'out_dir':str(tmp_path/'golden')})
    assert r.status_code==200,r.text
    assert Path(r.json()['excel']).is_file()


def test_reference_alias_suggests_only_current_qname_without_changing_core_scores(tmp_path):
    body,_=inputs(tmp_path)
    db=tmp_path/'aliases.sqlite'
    with sqlite3.connect(db) as c:
        c.executescript('CREATE TABLE companies(corp_code,corp_name,induty_code,status); CREATE TABLE usages(corp_code,element_id,label_ko,roles,dims,n_facts,is_ext);')
        c.execute('INSERT INTO companies VALUES(?,?,?,?)',('other','peer','20','ok'))
        c.execute('INSERT INTO usages VALUES(?,?,?,?,?,?,?)',('other','company_Cash','새 회사','bs','',1,0))
    body['corpus']=str(db)
    draft=core().prepare(body)
    assert any(c.get('reference_label_score') for e in draft['workflow']['evidence'] for c in e['candidates'])
    assert not draft['decisions']


def test_change_filter_prioritizes_exceptions_and_preserves_order(tmp_path):
    body,_=inputs(tmp_path)
    d=core().prepare(body);d['workflow']['mode']='rollforward'
    from auditdesk import binding_review
    result=core().review_projection(d,binding_review.summarize(d))
    assert all(r['workflow_status']=='needs_review' for r in result['rows'])
    assert [r['id'] for r in result['rows']]==[t['id'] for t in d['targets']]


def test_history_is_suggestion_provenance_and_never_a_decision(tmp_path,monkeypatch):
    body,manifest=inputs(tmp_path)
    c=client(tmp_path,monkeypatch)
    first=c.post('/workflows',json=body).json()
    confirmed=confirm_all(first,manifest)
    for key,d in confirmed['decisions'].items():
        first=c.put('/bindings/'+first['id'],json={'revision':first['revision'],'target_id':key,'decision':d}).json()
    body['reuse_id']=first['id']
    next_=c.post('/workflows',json=body).json()
    assert not next_['decisions']
    assert next_['reuse_candidates']
    assert next_['workflow']['history']['origin']=='USER_CONFIRMED_HISTORY'


def test_bad_corpus_is_user_error_not_500(tmp_path,monkeypatch):
    body,_=inputs(tmp_path)
    Path(body['corpus']).write_bytes(b'not sqlite')
    c=client(tmp_path,monkeypatch)
    r=c.post('/workflows',json=body)
    assert r.status_code==422 and 'corpus' in r.text


def test_analysis_and_binding_must_use_same_dsd_snapshot(tmp_path,monkeypatch):
    body,_=inputs(tmp_path);o=core();original=o.analyze
    def changed(path):
        result=original(path)
        with open(path,'ab') as f:f.write(b'changed after analysis')
        return result
    monkeypatch.setattr(o,'analyze',changed)
    with pytest.raises(ValueError,match='변경'):o.prepare(body)


def test_namespace_change_is_not_reusable_despite_same_prefix():
    old={**concept(),'namespace':'urn:old'};new={**concept(),'namespace':'urn:new'}
    rows=core().taxonomy_changes([old],[new])
    assert rows[0]['status']=='changed' and 'namespace' in rows[0]['reasons']


def test_explicit_unavailable_corpus_is_not_silently_defaulted(tmp_path,monkeypatch):
    body,_=inputs(tmp_path);body['corpus']=str(tmp_path/'missing-explicit.sqlite')
    # Absence is allowed but must remain a visible unavailable stage.
    d=core().prepare(body)
    assert d['workflow']['steps']['reference']['state']=='needs_review'
    assert not d['workflow']['references']


def test_empty_company_tag_is_missing_identity_not_a_conflicting_company(tmp_path):
    import zipfile
    body,_=inputs(tmp_path)
    with zipfile.ZipFile(body['dsd']) as z:text=z.read('contents.xml').decode('utf-8')
    with zipfile.ZipFile(body['dsd'],'w') as z:z.writestr('contents.xml',text.replace('<DOCUMENT>','<DOCUMENT><COMPANY-NAME></COMPANY-NAME>'))
    assert core().prepare(body)['workflow']['analysis']['company_candidates']==[]


def test_compact_workflow_save_does_not_resend_immutable_analysis(tmp_path,monkeypatch):
    body,manifest=inputs(tmp_path);c=client(tmp_path,monkeypatch)
    d=c.post('/workflows',json=body).json();confirmed=confirm_all(d,manifest)
    target='재무상태표:1:1'
    r=c.put('/bindings/'+d['id'],json={'revision':0,'target_id':target,'decision':confirmed['decisions'][target],'compact':True})
    assert r.status_code==200,r.text
    assert 'workflow' not in r.json()
    assert r.json()['workflow_update']['coverage']['confirmed']==1
    assert 'evidence' not in r.json()['workflow_update']


def test_package_report_date_uses_explicit_current_document_period_not_first_fact(tmp_path):
    from auditdesk.orchestration_sources import package_evidence
    folder=package(tmp_path)
    path=folder/'company.xbrl';text=path.read_text(encoding='utf-8')
    text=text.replace('xmlns:company="urn:company"','xmlns:company="urn:company" xmlns:dart-gcd="urn:dart"')
    text=text.replace('</xbrli:xbrl>','<dart-gcd:DocumentPeriodEndDate contextRef="c">2023-12-31</dart-gcd:DocumentPeriodEndDate><dart-gcd:DocumentPeriodEndDate contextRef="c">2025-06-30</dart-gcd:DocumentPeriodEndDate></xbrli:xbrl>')
    path.write_text(text,encoding='utf-8')
    assert package_evidence(folder,'separate','2025-06-30')['concepts']
    with pytest.raises(ValueError):package_evidence(folder,'separate','2023-12-31')


def test_workflow_search_failure_is_502_without_secret_exception_text(tmp_path,monkeypatch):
    body,_=inputs(tmp_path,'rollforward');c=client(tmp_path,monkeypatch)
    from auditdesk.routers import explorer
    from dart_explorer.client.opendart import OpenDartError
    cli=Client()
    def fail(*a,**kw):raise OpenDartError('sensitive-key-example')
    cli.resolve_corp_code=fail
    monkeypatch.setattr(explorer,'_client',lambda:cli)
    r=c.post('/workflows',json=body)
    assert r.status_code==502 and 'sensitive-key-example' not in r.text


def test_multi_instance_package_never_chooses_arbitrary_first(tmp_path):
    from auditdesk.orchestration_sources import package_evidence
    folder=package(tmp_path);(folder/'other.xbrl').write_bytes((folder/'company.xbrl').read_bytes())
    with pytest.raises(ValueError,match='instance'):package_evidence(folder,'separate','2025-06-30')


def test_taxonomy_diff_excludes_other_scope_occurrences(tmp_path,monkeypatch):
    body,_=inputs(tmp_path);o=core();draft=o.prepare(body)
    draft['taxonomy'].append({**draft['taxonomy'][0],'name':'OtherScope','scope':'consolidated'})
    monkeypatch.setattr(o.binding,'prepare',lambda *a,**kw:copy.deepcopy(draft))
    prior={'company':body['report']['company'],'scope':'separate','period_end':'2025-06-30',
           'concepts':[{**draft['taxonomy'][0],'scope':'separate'}]}
    result=o.prepare({**body,'mode':'rollforward'},prior)
    assert all(r['name']!='OtherScope' for r in result['workflow']['changes'])


def test_missing_prior_metadata_is_unverified_not_a_proven_change():
    old={**concept(),'data_type':None}
    rows=core().taxonomy_changes([old],[concept()])
    assert rows[0]['status']=='needs_review'
    assert rows[0]['reasons']==['data_type unverified']


def test_invalid_dsd_is_rejected_before_any_prior_network_acquisition(tmp_path,monkeypatch):
    body,_=inputs(tmp_path,'rollforward');Path(body['dsd']).write_bytes(b'invalid dsd')
    c=client(tmp_path,monkeypatch)
    from auditdesk import orchestration_sources
    calls=[]
    monkeypatch.setattr(orchestration_sources,'acquire_prior',lambda *args:(calls.append('network') or None))
    from auditdesk.routers import explorer
    monkeypatch.setattr(explorer,'_client',lambda:Client())
    assert c.post('/workflows',json=body).status_code==422
    assert not calls


def test_background_job_retains_one_review_id_and_stage_progress(tmp_path,monkeypatch):
    import time
    from auditdesk import jobs
    body,_=inputs(tmp_path);c=client(tmp_path,monkeypatch)
    r=c.post('/workflows/start',json=body);assert r.status_code==202,r.text
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        job=jobs.get(r.json()['job_id'])
        if job['state'] in ('done','error','interrupted'):break
        time.sleep(.02)
    assert job['state']=='done',job
    assert job['progress']['current']==4 and job['progress']['total']==6
    review=c.get('/workflows/'+job['result']['id']).json()
    assert review['id']==job['result']['id'] and review['workflow']['analysis']['tables']


def test_prior_acquisition_never_overwrites_an_edited_existing_package(tmp_path,monkeypatch):
    import zipfile
    from auditdesk.orchestration_sources import acquire_prior
    from dart_explorer.xbrl import pipeline
    body,_=inputs(tmp_path,'rollforward');body['prior_receipt']='20250801000001'
    folder=package(tmp_path);archive=tmp_path/'prior.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for p in folder.iterdir():z.write(p,p.name)
    existing=tmp_path/'prior';existing.mkdir()
    edited=existing/'company.xbrl';edited.write_text('user edited package',encoding='utf-8')
    monkeypatch.setattr(pipeline,'download_xbrl',lambda *a:(archive.read_bytes(),str(archive)))
    result=acquire_prior(Client(),body)
    assert result['concepts']
    assert edited.read_text(encoding='utf-8')=='user edited package'


def test_corpus_detail_is_stored_once_not_copied_into_each_candidate(tmp_path):
    body,_=inputs(tmp_path);db=tmp_path/'corpus-large.sqlite'
    with sqlite3.connect(db) as c:
        c.executescript('CREATE TABLE companies(corp_code,corp_name,induty_code,status); CREATE TABLE usages(corp_code,element_id,label_ko,roles,dims,n_facts,is_ext);')
        c.execute('INSERT INTO companies VALUES(?,?,?,?)',('other','peer','20','ok'))
        c.execute('INSERT INTO usages VALUES(?,?,?,?,?,?,?)',('other','company_Cash','새 회사','role-data'*1000,'dimension-data'*1000,1,0))
    body['corpus']=str(db);d=core().prepare(body)
    reference=d['workflow']['references'][0]
    citations=[p for s in d['workflow']['evidence'] for c in s['candidates'] for p in c['provenance'] if p['origin']=='OPENDART_REFERENCE']
    assert len(citations)>1
    assert all('roles' not in p and 'dimensions' not in p for p in citations)
    assert all(p['reference_id']==reference['id'] for p in citations)
    assert reference['roles'] and reference['dimensions']


def test_reference_detail_remains_available_and_rejects_changed_snapshot(tmp_path,monkeypatch):
    body,_=inputs(tmp_path);db=tmp_path/'detail.sqlite'
    with sqlite3.connect(db) as con:
        con.executescript('CREATE TABLE companies(corp_code,corp_name,induty_code,status); CREATE TABLE usages(corp_code,element_id,label_ko,roles,dims,n_facts,is_ext);')
        con.execute('INSERT INTO companies VALUES(?,?,?,?)',('other','peer','20','ok'))
        con.execute('INSERT INTO usages VALUES(?,?,?,?,?,?,?)',('other','company_Cash','새 회사','role','dimension'*1000,1,0))
    body['corpus']=str(db);c=client(tmp_path,monkeypatch)
    draft=c.post('/workflows',json=body).json()
    r=c.get('/workflows/'+draft['id']+'/reference',params={'reference_id':'company:Cash'})
    assert r.status_code==200,r.text
    assert r.json()['rows'][0]['dims']=='dimension'*1000
    assert r.json()['origin']=='OPENDART_REFERENCE'
    with sqlite3.connect(db) as con:con.execute("UPDATE usages SET dims='changed'")
    assert c.get('/workflows/'+draft['id']+'/reference',params={'reference_id':'company:Cash'}).status_code==409
