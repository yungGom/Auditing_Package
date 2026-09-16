"""Binding review must precede publication; real BIFF/DSD and durable API tests."""
import copy
import json
from pathlib import Path

import pytest

from test_phase4_golden import current_case


def service():
    from auditdesk import binding
    return binding


def case(tmp_path):
    dsd, manifest = current_case(tmp_path)
    return service().prepare(str(dsd), str(tmp_path/'current_taxonomy.xls'),
                             str(tmp_path/'layout.xls'), manifest['report']), manifest


def confirm_all(draft, manifest):
    b = service()
    first = manifest['bindings'][0]
    source = next(s for s in draft['sources'] if s['start'] == first['source_start'])
    draft = b.decide(draft, '재무상태표:2:1', {
        'kind': 'binding', 'source_id': source['id'],
        'taxonomy_id': draft['taxonomy'][0]['id'], 'context': first['context'],
        'source_evidence': '당기 DSD 및 차원 없음 확인', 'dimensions_reviewed': True})
    # A sample title is not evidence. Change it only through a reviewed static value.
    draft = b.decide(draft, '재무상태표:1:1', {
        'kind': 'static', 'source_id': draft['sources'][0]['id'],
        'source_evidence': 'DSD 제목 원문', 'use_source_text': True})
    return draft


def test_no_auto_confirmation_and_missing_sample_values_block(tmp_path):
    b = service(); draft, _ = case(tmp_path)
    assert len(draft['sources']) == 3
    assert b.coverage(draft)['required'] == 2
    assert b.coverage(draft)['confirmed'] == 0
    with pytest.raises(ValueError, match='미확정|coverage'):
        b.generate(draft, str(tmp_path/'blocked'))
    assert not (tmp_path/'blocked').exists()


def concept(role='r', **kw):
    return dict(id=role+str(kw), taxonomy_sheet=role, taxonomy_row=4, role=role,
                prefix='company', name='Cash', label_ko='현금', label_en='Cash',
                data_type='monetary', period='INSTANT', dimensions=None,
                balance='DEBIT', label_role='label', scope='separate', **kw)


def test_exact_qname_and_repeated_roles_are_not_deduped():
    b = service(); source = {'label': '현금', 'prefix': 'company', 'name': 'Cash',
        'role': 'r', 'period': 'INSTANT', 'data_type': 'monetary', 'dimensions': [],
        'scope': 'separate'}
    concepts = [concept('r'), concept('note')]
    candidates = b.rank(source, concepts)
    assert len(candidates) == 2
    assert candidates[0]['role'] == 'r'
    assert 'QName exact' in candidates[0]['evidence']
    assert candidates[0]['ambiguity_reasons']  # dimensions not present in taxonomy export
    assert all(not c.get('confirmed') for c in candidates)
    assert b.rank(source, concepts) == candidates


def test_label_alone_ambiguous():
    candidates = service().rank({'label': '현금', 'scope': 'separate'}, [concept('r'), concept('note')])
    assert len(candidates) == 2
    assert all(c['confidence'] != 'high' and c['ambiguity_reasons'] for c in candidates)


def test_english_label_can_propose_current_element():
    cs = service().rank({'label':'Cash','scope':'separate'},[concept()])
    assert cs and cs[0]['name']=='Cash'


def test_layout_lookup_normalizes_source_labels_once(tmp_path,monkeypatch):
    b=service(); calls=[]; original=b.normalize
    monkeypatch.setattr(b,'normalize',lambda s:(calls.append(s),original(s))[1])
    monkeypatch.setattr(b,'rank',lambda *args:[])
    draft,_=case(tmp_path)
    assert len(calls)<=len(draft['sources'])+len(draft['targets'])+2


@pytest.mark.parametrize('field,value', [('period','DURATION'), ('data_type','text'),
                                        ('dimensions',[{'axis':'x:A','member':'x:B'}])])
def test_incompatible_context_is_explained(field, value):
    c = concept(); c['dimensions'] = []
    source = {'label':'현금', 'scope':'separate', 'period':'INSTANT',
              'data_type':'monetary', 'dimensions':[]}; source[field] = value
    candidates = service().rank(source, [c])
    assert field+' mismatch' in candidates[0]['ambiguity_reasons']
    assert candidates[0]['confidence'] == 'low'


def test_scope_and_extension_identity():
    b = service(); wrong = concept('wrong'); wrong['scope'] = 'consolidated'
    cs = b.rank({'label':'현금','scope':'separate'}, [concept(), wrong])
    assert len(cs) == 1 and cs[0]['prefix'] == 'company'


@pytest.mark.parametrize('text,expected',[
    ('[D822415] Cash, Separated financial statements','separate'),
    ('[D822410] Cash, Consolidated financial statements','consolidated')])
def test_explicit_english_role_scope(text,expected):
    assert service()._scope(text)==expected


def test_report_scope_conflicting_with_dsd_body_is_rejected(tmp_path,monkeypatch):
    from types import SimpleNamespace
    b=service(); draft,_=case(tmp_path)
    monkeypatch.setattr(b,'scan',lambda text:SimpleNamespace(fs_blocks=[SimpleNamespace(title_parts=('반기','연결','BS'))]))
    with pytest.raises(ValueError,match='scope'):
        b.prepare(**draft['paths'],report=draft['report'])


def test_confirm_cancel_and_golden_generation(tmp_path):
    b = service(); draft, manifest = case(tmp_path)
    draft = confirm_all(draft, manifest)
    assert b.coverage(draft)['ready']
    result = b.generate(draft, str(tmp_path/'out'))
    from auditdesk import golden
    values = [c[3] for c in golden.read_xls(result['excel'])['sheets'][0]['cells']]
    assert values == ['새 회사', '1,234']
    assert golden.formula_count(result['excel']) == 0
    assert Path(tmp_path/'out/review.json').exists()
    draft = b.decide(draft, '재무상태표:2:1', {'kind':'unresolved'})
    assert not b.coverage(draft)['ready']
    assert b.coverage(draft)['confirmed'] == 1


def test_stale_sources_reject_confirm_and_generation(tmp_path):
    b = service(); draft, manifest = case(tmp_path); draft = confirm_all(draft, manifest)
    with Path(draft['paths']['dsd']).open('ab') as f: f.write(b'changed')
    assert b.coverage(draft)['stale']
    with pytest.raises(ValueError, match='원천|stale'):
        b.generate(draft, str(tmp_path/'out'))
    with pytest.raises(ValueError, match='원천|stale'):
        b.decide(draft, '재무상태표:2:1', {'kind':'unresolved'})


def test_99_percent_gate_and_conflict(tmp_path):
    b = service(); draft, manifest = case(tmp_path); draft = confirm_all(draft, manifest)
    for i in range(98):
        one = copy.deepcopy(draft['targets'][0]); one['id'] = f'extra:{i}:1'
        draft['targets'].append(one)
        if i < 97: draft['decisions'][one['id']] = copy.deepcopy(draft['decisions']['재무상태표:1:1'])
    assert b.coverage(draft)['required'] == 100
    assert b.coverage(draft)['confirmed'] == 99
    assert not b.coverage(draft)['ready']
    draft['targets'] = draft['targets'][:2]
    draft['decisions']['재무상태표:2:1']['context']['scope'] = 'consolidated'
    assert b.coverage(draft)['conflicts'] == 1


def test_static_requires_source_not_claim_only(tmp_path):
    b = service(); draft, _ = case(tmp_path)
    with pytest.raises(ValueError, match='원천'):
        b.decide(draft, '재무상태표:1:1', {'kind':'static','source_evidence':'looks fine'})


def test_durable_api_and_revision_conflict(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from auditdesk import jobs
    from auditdesk.routers import binding_api
    monkeypatch.setattr(jobs, '_DB', str(tmp_path/'app.sqlite'))
    app = FastAPI(); app.include_router(binding_api.router, prefix='/api/studio/bindings')
    client = TestClient(app)
    dsd, manifest = current_case(tmp_path)
    response = client.post('/api/studio/bindings', json={
        'dsd':str(dsd),'taxonomy':str(tmp_path/'current_taxonomy.xls'),
        'layout':str(tmp_path/'layout.xls'),'report':manifest['report']})
    assert response.status_code == 200, response.text
    draft = response.json(); key = draft['id']
    body = {'revision':draft['revision'], 'target_id':'재무상태표:1:1',
            'decision':{'kind':'static','source_id':draft['sources'][0]['id'],
                        'use_source_text':True,'source_evidence':'원문'}}
    assert client.put(f'/api/studio/bindings/{key}', json=body).status_code == 200
    assert client.put(f'/api/studio/bindings/{key}', json=body).status_code == 409
    saved = client.get(f'/api/studio/bindings/{key}').json()
    assert saved['coverage']['confirmed'] == 1
    assert client.post(f'/api/studio/bindings/{key}/generate',json={'revision':saved['revision'],'out_dir':str(tmp_path/'blocked')}).status_code == 422
    assert client.get('/api/studio/bindings').json()['drafts'][0]['id'] == key


def test_current_source_index_hash_and_context_mismatch(tmp_path):
    b = service(); draft, manifest = case(tmp_path)
    s = next(s for s in draft['sources'] if s['text'] == '1,234')
    index = {'dsd_sha256':draft['hashes']['dsd'],'taxonomy_sha256':draft['hashes']['taxonomy'],
        'report':manifest['report'],'facts':[{'source_id':s['id'],'prefix':'company','name':'Cash',
        'role':'urn:current:bs','period':'INSTANT','data_type':'monetary','dimensions':[],
        'context':manifest['bindings'][0]['context'],'source_evidence':'current reviewed source'}]}
    p = tmp_path/'current.json'; p.write_text(json.dumps(index),encoding='utf-8')
    draft = b.prepare(**draft['paths'],report=draft['report'],current_source=str(p))
    s = next(s for s in draft['sources'] if s['text'] == '1,234')
    assert 'QName exact' in s['candidates'][0]['evidence']
    draft = confirm_all(draft,manifest)
    assert b.coverage(draft)['ready']
    p.write_text('{}')
    assert b.coverage(draft)['stale']


@pytest.mark.parametrize('failure',['period','data_type','dimensions','name'])
def test_decisions_reject_known_source_mismatch(tmp_path, failure):
    b = service(); draft, manifest = case(tmp_path)
    draft = confirm_all(draft,manifest)
    source = next(s for s in draft['sources'] if s['text'] == '1,234')
    source[failure] = {'period':'DURATION','data_type':'text','dimensions':[{'axis':'x:A','member':'x:B'}],'name':'OtherConcept'}[failure]
    with pytest.raises(ValueError,match=failure):
        b.decide(draft,'재무상태표:2:1',draft['decisions']['재무상태표:2:1'])


def test_api_reuse_does_not_inherit_approval_and_invalid_file_is_4xx(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from auditdesk import jobs
    from auditdesk.routers import binding_api
    monkeypatch.setattr(jobs,'_DB',str(tmp_path/'reviews.sqlite'))
    app=FastAPI(); app.include_router(binding_api.router,prefix='/bindings')
    client=TestClient(app)
    draft,manifest=case(tmp_path)
    body={**draft['paths'],'report':draft['report']}
    first=client.post('/bindings',json=body).json()
    s=next(s for s in first['sources'] if s['text']=='1,234')
    d={'kind':'binding','source_id':s['id'],'taxonomy_id':first['taxonomy'][0]['id'],
       'context':manifest['bindings'][0]['context'],'dimensions_reviewed':True,'source_evidence':'당기 확인'}
    assert client.put('/bindings/'+first['id'],json={'revision':0,'target_id':'재무상태표:2:1','decision':d}).status_code==200
    second=client.post('/bindings',json={**body,'reuse_id':first['id']}).json()
    assert second['decisions']=={} and len(second['reuse_candidates'])==1
    assert second['coverage']['confirmed']==0
    body['report']['company']='other'
    assert client.post('/bindings',json={**body,'reuse_id':first['id']}).status_code==422
    Path(body['dsd']).write_text('not a zip')
    assert client.post('/bindings',json=body).status_code==422


def test_confirm_cannot_use_other_scope_layout(tmp_path):
    b = service(); draft, manifest = case(tmp_path)
    draft = confirm_all(draft,manifest)
    draft['targets'][1]['sheet'] = '재무상태표 (연결)'
    with pytest.raises(ValueError,match='scope'):
        b.decide(draft,'재무상태표:2:1',draft['decisions']['재무상태표:2:1'])


def test_api_full_review_to_files_and_reexecution(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from auditdesk import jobs
    from auditdesk.routers import binding_api
    monkeypatch.setattr(jobs,'_DB',str(tmp_path/'workflow.sqlite'))
    app=FastAPI(); app.include_router(binding_api.router,prefix='/bindings')
    client=TestClient(app)
    draft,manifest=case(tmp_path)
    saved=client.post('/bindings',json={**draft['paths'],'report':draft['report']}).json()
    reviewed=confirm_all(draft,manifest)
    for target_id,decision in reviewed['decisions'].items():
        response=client.put('/bindings/'+saved['id'],json={'revision':saved['revision'],'target_id':target_id,'decision':decision})
        assert response.status_code==200,response.text
        saved=response.json()
    assert saved['coverage']['ready']
    assert all(s['state']=='confirmed' for s in saved['target_states'].values())
    body={'revision':saved['revision'],'out_dir':str(tmp_path/'result')}
    response=client.post('/bindings/'+saved['id']+'/generate',json=body)
    assert response.status_code==200,response.text
    assert Path(response.json()['excel']).exists()
    assert client.post('/bindings/'+saved['id']+'/generate',json=body).status_code==409
    body['out_dir']=str(tmp_path/'retry')
    assert client.post('/bindings/'+saved['id']+'/generate',json=body).status_code==200
