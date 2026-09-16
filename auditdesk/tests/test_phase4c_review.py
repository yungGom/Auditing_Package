"""Review efficiency cannot weaken source, approval, or publication gates."""
import copy
import json
from pathlib import Path

import pytest
from test_phase4b_binding import case, confirm_all


def review():
    from auditdesk import binding_review
    return binding_review


def ready(tmp_path):
    d, m = case(tmp_path)
    s = next(s for s in d['sources'] if s['text'] == '1,234')
    c = d['taxonomy'][0]
    c['prefix'] = 'ifrs-full'
    c['scope'] = d['report']['scope']
    s.update({k: c[k] for k in ('prefix','name','role','data_type','period')})
    s.update(dimensions=[],context=m['bindings'][0]['context'],source_evidence='reviewed current source',
             review_target_ids=['재무상태표:2:1'])
    s['candidates'] = [{**c,'confidence':'medium','ambiguity_reasons':['dimensions unverified']}]
    d['targets'][1]['source_candidates'] = [{'source_id':s['id']}]
    return d, m


def test_queue_confidence_metrics_and_order(tmp_path):
    d,_=ready(tmp_path); r=review().summarize(d)
    assert r['metrics']['required']==2 and r['metrics']['confirmed']==0
    assert r['metrics']['candidate_available']==1 and r['metrics']['high_confidence']==1
    assert r['metrics']['candidate_coverage_pct']==50 and r['metrics']['confirmation_pct']==0
    assert r==review().summarize(d)
    s=next(s for s in d['sources'] if s['text']=='1,234')
    del s['review_target_ids']
    assert review().summarize(d)['rows'][1]['state']=='medium'
    s['candidates'][0]['confidence']='low'
    s['candidates'][0]['ambiguity_reasons']=['period mismatch']
    r=review().summarize(d)
    assert r['rows'][1]['state']=='low' and 'period_mismatch' in r['rows'][1]['exceptions']


def test_group_evidence_and_explicit_batch(tmp_path):
    from auditdesk import binding
    d,_=ready(tmp_path); r=review().summarize(d)
    assert len(r['groups'])==1 and d['decisions']=={}
    ids=r['groups'][0]['target_ids']; p=review().preview(d,ids)
    assert p['hashes']==d['hashes'] and p['conflicts']==0 and p['stale']==0
    assert p['count']==1 and p['roles'] and p['sheets'] and p['evidence']
    updated=review().confirm_batch(d,ids,p['token'],'원천 및 대상 목록 검토')
    assert d['decisions']=={} and updated['revision']==1
    assert binding.coverage(updated)['confirmed']==1
    assert review().summarize(updated)['metrics']['batch_confirmed']==1


@pytest.mark.parametrize('kind',['ambiguous','stale','conflict','multi_role','dimension','extension'])
def test_unsafe_entries_never_batch(tmp_path,kind):
    d,m=ready(tmp_path); s=next(s for s in d['sources'] if s['text']=='1,234')
    if kind=='ambiguous': s['candidates'].append({**s['candidates'][0],'id':'another'})
    elif kind=='stale': Path(d['paths']['dsd']).write_bytes(b'changed')
    elif kind=='conflict':
        d=confirm_all(d,m); d['decisions']['재무상태표:2:1']['context']['scope']='consolidated'
    elif kind=='multi_role': d['taxonomy'].append({**d['taxonomy'][0],'id':'other','role':'other'})
    elif kind=='dimension': s['dimensions']=None
    elif kind=='extension':
        # Extension review is explicit even when otherwise high-confidence.
        d['taxonomy'][0]['prefix']='entity123'; s['prefix']='entity123'; s['candidates'][0]['prefix']='entity123'
    assert not review().summarize(d)['groups']
    with pytest.raises(ValueError): review().preview(d,['재무상태표:2:1'])


def client_case(tmp_path,monkeypatch,d):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from auditdesk import jobs
    from auditdesk.routers import binding_api
    monkeypatch.setattr(jobs,'_DB',str(tmp_path/'review.sqlite'))
    d['id']='test'
    with binding_api._connect() as con: con.execute('INSERT INTO binding_reviews VALUES(?,?)',('test',json.dumps(d)))
    app=FastAPI(); app.include_router(binding_api.router,prefix='/bindings')
    return TestClient(app)


def test_api_transaction_revision_and_preview_token(tmp_path,monkeypatch):
    d,_=ready(tmp_path); client=client_case(tmp_path,monkeypatch,d)
    ids=['재무상태표:2:1']
    p=client.post('/bindings/test/batch-preview',json={'revision':0,'target_ids':ids})
    assert p.status_code==200,p.text
    body={'revision':0,'target_ids':ids,'token':p.json()['token'],'evidence':'검토 완료','compact':True}
    r=client.post('/bindings/test/batch-confirm',json=body)
    assert r.status_code==200,r.text
    assert r.json()['review']['metrics']['batch_confirmed']==1
    assert r.json().get('partial') is True and 'sources' not in r.json() and 'taxonomy' not in r.json()
    assert r.json()['decision_updates']['재무상태표:2:1']['batch_id']
    cancel=client.put('/bindings/test',json={'revision':1,'target_id':'재무상태표:2:1','decision':{'kind':'unresolved'},'compact':True})
    assert cancel.status_code==200 and cancel.json()['decision_updates']['재무상태표:2:1'] is None
    assert client.post('/bindings/test/batch-confirm',json=body).status_code==409


def test_batch_failure_rolls_back_every_decision(tmp_path,monkeypatch):
    d,_=ready(tmp_path); second=copy.deepcopy(d['targets'][1]); second['id']='second'; d['targets'].append(second)
    s=next(s for s in d['sources'] if s['text']=='1,234'); s['review_target_ids'].append('second')
    client=client_case(tmp_path,monkeypatch,d); ids=['재무상태표:2:1','second']
    p=client.post('/bindings/test/batch-preview',json={'revision':0,'target_ids':ids}).json()
    from auditdesk import binding
    validate=binding._validate
    def fail(draft,target,decision):
        if target['id']=='second': raise ValueError('injected invalid item')
        return validate(draft,target,decision)
    monkeypatch.setattr(binding,'_validate',fail)
    r=client.post('/bindings/test/batch-confirm',json={'revision':0,'target_ids':ids,'token':p['token'],'evidence':'검토'})
    assert r.status_code==422
    saved=client.get('/bindings/test').json()
    assert saved['decisions']=={} and saved['revision']==0


def test_batch_gate_99_then_100_and_cancel(tmp_path):
    from auditdesk import binding
    d,m=ready(tmp_path)
    for i in range(98):
        target=copy.deepcopy(d['targets'][1]);target['id']=f'extra:{i}';d['targets'].append(target)
        next(s for s in d['sources'] if s['text']=='1,234')['review_target_ids'].append(target['id'])
    ids=review().summarize(d)['groups'][0]['target_ids'];p=review().preview(d,ids)
    d=review().confirm_batch(d,ids,p['token'],'명시적 그룹 검토')
    assert binding.coverage(d)['confirmed']==99 and not binding.coverage(d)['ready']
    with pytest.raises(ValueError): binding.generate(d,tmp_path/'blocked')
    d=binding.decide(d,'재무상태표:1:1',{'kind':'static','source_id':d['sources'][0]['id'],'use_source_text':True,'source_evidence':'원문 확인'})
    assert binding.coverage(d)['ready']
    d=binding.decide(d,ids[0],{'kind':'unresolved'})
    assert not binding.coverage(d)['ready']


def test_prior_is_only_current_valid_contextual_suggestion(tmp_path):
    d,_=ready(tmp_path);s=next(s for s in d['sources'] if s['text']=='1,234')
    d['reuse_candidates']=[{'taxonomy':d['taxonomy'][0],'report':d['report'],
        'source_block_id':s['block_id'],'source_label':s['label']}]
    r=review().summarize(d)
    assert r['rows'][1]['prior_suggestions'] and not d['decisions']
    d['reuse_candidates'][0]['taxonomy']={**d['taxonomy'][0],'name':'Deleted'}
    assert not review().summarize(d)['rows'][1]['prior_suggestions']


def test_preview_invalidated_by_revision_and_source(tmp_path):
    d,_=ready(tmp_path); ids=['재무상태표:2:1'];p=review().preview(d,ids)
    d['revision']+=1
    with pytest.raises(ValueError): review().confirm_batch(d,ids,p['token'],'reviewed')
    d['revision']-=1
    Path(d['paths']['dsd']).write_bytes(b'changed')
    with pytest.raises(ValueError): review().confirm_batch(d,ids,p['token'],'reviewed')


def test_current_index_to_real_api_batch_and_files(tmp_path,monkeypatch):
    from auditdesk import binding, golden
    d,m=case(tmp_path)
    tax=golden.read_xls(d['paths']['taxonomy'])
    for cell in tax['sheets'][0]['cells']:
        if cell[:2]==[1,1]: cell[3]='Separate financial statements'
        if cell[:2]==[3,1]: cell[3]='ifrs-full'
    taxpath=tmp_path/'review-tax.xls';golden.write_xls(tax,taxpath)
    d=binding.prepare(d['paths']['dsd'],taxpath,d['paths']['layout'],d['report'])
    s=next(s for s in d['sources'] if s['text']=='1,234');c=d['taxonomy'][0]
    index={'dsd_sha256':d['hashes']['dsd'],'taxonomy_sha256':d['hashes']['taxonomy'],
           'layout_sha256':d['hashes']['layout'],'report':d['report'],
           'facts':[{'source_id':s['id'],'source_evidence':'current source + target checked',
           **{k:c[k] for k in ('prefix','name','role','data_type','period')},
           'dimensions':[],'context':m['bindings'][0]['context'],'review_target_ids':['재무상태표:2:1']}]}
    path=tmp_path/'source.json';path.write_text(json.dumps(index),encoding='utf-8')
    client=client_case(tmp_path,monkeypatch,d)
    body={**d['paths'],'report':d['report'],'current_source':str(path)}
    r=client.post('/bindings',json=body);assert r.status_code==200,r.text
    saved=r.json();assert saved['review']['metrics']['batch_reviewable']==1 and saved['decisions']=={}
    key=saved['id'];ids=['재무상태표:2:1']
    p=client.post(f'/bindings/{key}/batch-preview',json={'revision':0,'target_ids':ids}).json()
    saved=client.post(f'/bindings/{key}/batch-confirm',json={'revision':0,'target_ids':ids,'token':p['token'],'evidence':'검토 확인'}).json()
    assert not saved['coverage']['ready']
    saved=client.put(f'/bindings/{key}',json={'revision':1,'target_id':'재무상태표:1:1',
        'decision':{'kind':'static','source_id':d['sources'][0]['id'],'use_source_text':True,'source_evidence':'제목 원문'}}).json()
    assert saved['coverage']['ready']
    r=client.post(f'/bindings/{key}/generate',json={'revision':2,'out_dir':str(tmp_path/'output')})
    assert r.status_code==200,r.text
    assert golden.formula_count(r.json()['excel'])==0
    assert [v[3] for v in golden.read_xls(r.json()['excel'])['sheets'][0]['cells']]==['새 회사','1,234']
    index['layout_sha256']='wrong';path.write_text(json.dumps(index),encoding='utf-8')
    assert client.post('/bindings',json=body).status_code==422


def test_sql_update_failure_does_not_save_batch(tmp_path,monkeypatch):
    import sqlite3
    from auditdesk.routers import binding_api
    d,_=ready(tmp_path);client=client_case(tmp_path,monkeypatch,d);ids=['재무상태표:2:1']
    p=client.post('/bindings/test/batch-preview',json={'revision':0,'target_ids':ids}).json()
    with binding_api._connect() as con:
        con.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON binding_reviews BEGIN SELECT RAISE(ABORT,'test storage failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        client.post('/bindings/test/batch-confirm',json={'revision':0,'target_ids':ids,'token':p['token'],'evidence':'검토'})
    saved=client.get('/bindings/test').json()
    assert saved['decisions']=={} and saved['revision']==0


def test_any_conflict_removes_batch_reviewable_metric(tmp_path):
    d,m=ready(tmp_path)
    confirmed=confirm_all(d,m)
    d['decisions']['재무상태표:1:1']=confirmed['decisions']['재무상태표:1:1']
    d['decisions']['재무상태표:1:1']['source_id']='missing'
    r=review().summarize(d)
    assert r['metrics']['conflict']==1
    assert r['metrics']['batch_reviewable']==0 and not r['groups']
