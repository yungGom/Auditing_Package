"""Phase 2 API regressions, isolated from user files and network."""
import importlib
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from auditdesk import jobs
from auditdesk.routers import explorer, fs, jobs_api, studio, workbench as w
from dsd_tool.tests.fixture import build_dsd


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, '_DB', str(tmp_path / 'jobs.sqlite'))
    monkeypatch.setattr(w, '_WORKDIR', str(tmp_path / 'sessions'))
    app = FastAPI()
    for module, prefix in [(explorer, 'explorer'), (fs, 'fs'),
                           (jobs_api, 'jobs'), (w, 'workbench'), (studio, 'studio')]:
        app.include_router(module.router, prefix='/api/' + prefix)
    return TestClient(app, raise_server_exceptions=False)


def test_m08_receipts_and_retries_preserve_existing_output(client, tmp_path, monkeypatch):
    wrap = importlib.import_module('dart_explorer.converters.document_wrap')
    monkeypatch.setattr(explorer, '_client', lambda: object())
    monkeypatch.setattr(wrap, 'fetch_and_wrap', lambda cli, corp, receipt:
                        build_dsd(str(tmp_path / (receipt + '.dsd'))))
    monkeypatch.setattr(wrap, 'friendly_name', lambda path: 'Company_Report_2025')
    monkeypatch.setattr(jobs, 'submit', lambda kind, fn: fn(lambda *a: None))
    results = []
    for receipt in ['20260101000001', '20260101000002', '20260101000001']:
        response = client.post('/api/explorer/to-excel', json={'corp_code':'00123456', 'rcept_no':receipt})
        assert response.status_code == 202
        result = response.json()['job_id']
        assert result['display_name'] == 'Company_Report_2025'
        for path, content in results:
            assert path.read_bytes() == content, 'earlier user output overwritten'
        path = Path(result['xlsx_path'])
        assert path not in [p for p, _ in results]
        assert receipt in str(path)
        path.write_bytes(b'user edited workbook')
        results.append((path, path.read_bytes()))


def test_m14_kind_is_filtered_before_limit(client):
    with jobs.connect() as con:
        con.execute("INSERT INTO jobs(id,kind,state,created) VALUES('old','mapping','done','2025')")
        con.executemany("INSERT INTO jobs(id,kind,state,created) VALUES(?,?,?,?)",
                        [(str(i), 'foot', 'done', f'2026-{i:03d}') for i in range(60)])
    assert [j['job_id'] for j in client.get('/api/jobs?kind=mapping').json()['jobs']] == ['old']
    assert len(client.get('/api/jobs').json()['jobs']) == 50
    assert client.get('/api/jobs?kind=mapping&active=true').json()['jobs'] == []


@pytest.mark.parametrize('failure', ['missing', 'os'])
def test_m15_open_errors_are_http_errors(client, tmp_path, monkeypatch, failure):
    path = tmp_path / 'output.xlsx'
    if failure == 'os':
        path.write_bytes(b'fixture')
        def fail(p):
            raise OSError('sensitive internal launch information')
        monkeypatch.setattr('os.startfile', fail)
    response = client.post('/api/fs/open', json={'path':str(path)})
    assert response.status_code == (404 if failure == 'missing' else 409)
    assert response.json()['detail']
    assert 'sensitive internal' not in response.text


def test_m16_missing_api_key_is_actionable(client, monkeypatch):
    def missing():
        raise RuntimeError('secret diagnostic must not be returned')
    monkeypatch.setattr(importlib.import_module('dart_explorer.client.opendart'), 'load_api_key', missing)
    response = client.get('/api/explorer/corps?q=test')
    assert 400 <= response.status_code < 500
    assert 'API' in response.json()['detail']
    assert 'secret diagnostic' not in response.text


@pytest.mark.parametrize('endpoint,payload', [
    ('/api/explorer/xbrl', {'corp':'test','year':'not-a-number'}),
    ('/api/explorer/corpus/build', {'year':'not-a-number'}),
    ('/api/explorer/corpus/build', {'year':2025,'limit':'not-a-number'}),
])
def test_m16_numeric_input_rejected_before_job(client, monkeypatch, endpoint, payload):
    submitted = []
    monkeypatch.setattr(jobs, 'submit', lambda *a: submitted.append(a) or 'queued')
    response = client.post(endpoint, json=payload)
    assert response.status_code == 422
    assert response.json()['detail']
    assert not submitted


def test_m15_open_success_preserves_contract(client, monkeypatch, tmp_path):
    path = tmp_path / 'output.xlsx'; path.touch()
    opened = []
    monkeypatch.setattr('os.startfile', lambda p: opened.append(p))
    response = client.post('/api/fs/open', json={'path':str(path)})
    assert response.status_code == 200 and response.json() == {'ok':True}
    assert opened == [str(path)]


def test_m16_internal_client_failure_remains_server_error(client, monkeypatch):
    module = importlib.import_module('dart_explorer.client.opendart')
    monkeypatch.setattr(module, 'load_api_key', lambda: 'test-key')
    def broken(**kwargs):
        raise RuntimeError('internal secret diagnostic')
    monkeypatch.setattr(module, 'OpenDartClient', broken)
    response = client.get('/api/explorer/corps?q=test')
    assert response.status_code == 500
    assert 'internal secret' not in response.text


def test_m13_selected_alternative_is_persisted_and_restored(client):
    import json
    payload = {'items':[{'account':'Cash','candidates':[
        {'element':'ifrs-full_First'}, {'element':'ifrs-full_Second'}]}]}
    with studio._con() as con:
        con.execute('INSERT INTO mappings VALUES(?,?,?)', ('m', 'today', json.dumps(payload)))
    response = client.put('/api/studio/mapping/m/decide', json={
        'account_idx':0,'element':'ifrs-full_Second'})
    assert response.status_code == 200
    item = client.get('/api/studio/mapping/m').json()['items'][0]
    assert item['decided']['element'] == 'ifrs-full_Second'
    assert item['decided_by'] and item['decided_at']
    assert item['candidates'] == payload['items'][0]['candidates']


@pytest.mark.parametrize('limit', ['bad', -1, 1.5])
def test_m16_foot_limit_validation(client, monkeypatch, tmp_path, limit):
    path = tmp_path / 'input.xlsx'
    path.touch()
    monkeypatch.setattr(w, '_session', lambda sid: {'xlsx_path':str(path)})
    monkeypatch.setattr(jobs, 'submit', lambda *a: 'queued')
    response = client.post('/api/workbench/sessions/s/foot', json={'limit':limit})
    assert response.status_code == 422


def test_m10_zero_limit_survives_route(client, monkeypatch, tmp_path):
    path = tmp_path / 'input.xlsx'
    path.touch()
    monkeypatch.setattr(w, '_session', lambda sid: {'xlsx_path':str(path)})
    monkeypatch.setattr(jobs, 'submit', lambda kind, fn: fn(None))
    monkeypatch.setattr(w, '_run_foot', lambda sid, xlsx, excel, limit, progress: limit)
    response = client.post('/api/workbench/sessions/s/foot', json={'limit':0})
    assert response.json()['job_id'] == 0


@pytest.mark.parametrize('limit', [0, 5])
def test_m10_level_recheck_keeps_previous_limit(client, monkeypatch, tmp_path, limit):
    from openpyxl import Workbook
    from dsd_tool.foot import FOOT_SHEET
    path = tmp_path / 'input.xlsx'
    wb = Workbook(); ws = wb.active; ws.title = FOOT_SHEET
    ws.append(['[레벨]']); ws.append(['BS', 4, None, None, None]); wb.save(path)
    monkeypatch.setattr(w, '_session', lambda sid: {'xlsx_path':str(path), 'foot':{'limit':limit}})
    monkeypatch.setattr(jobs, 'submit', lambda kind, fn: fn(lambda *a: None))
    monkeypatch.setattr(w, '_run_foot', lambda sid, xlsx, excel, limit, progress: {'limit':limit})
    response = client.put('/api/workbench/sessions/s/foot/levels', json={
        'overrides':[{'sheet':'BS','row':4,'level':1}]})
    assert response.status_code == 202
    assert response.json()['job_id']['limit'] == limit


@pytest.mark.parametrize('endpoint', ['to-excel', 'dsd', 'fetch', 'dimtable-from-search', 'xbrl', 'corpus/build'])
def test_m16_missing_key_rejected_before_queue(client, monkeypatch, endpoint):
    def missing():
        raise RuntimeError('secret diagnostic')
    monkeypatch.setattr(importlib.import_module('dart_explorer.client.opendart'), 'load_api_key', missing)
    submitted = []
    monkeypatch.setattr(jobs, 'submit', lambda *a: submitted.append(a) or 'queued')
    response = client.post('/api/explorer/' + endpoint, json={
        'corp_code':'00123456','rcept_no':'20260101000001','corp':'test','year':2025})
    assert response.status_code == 409
    assert 'API' in response.json()['detail']
    assert 'secret' not in response.text
    assert not submitted


@pytest.mark.parametrize('value', ['bad', 'NaN', 'Infinity', -1])
@pytest.mark.parametrize('kind', ['prior', 'xbrl', 'level', 'decision'])
def test_m16_numeric_boundaries(client, monkeypatch, tmp_path, value, kind):
    path = tmp_path / 'input.xlsx'; path.touch()
    monkeypatch.setattr(w, '_session', lambda sid: {'xlsx_path':str(path), 'dsd_path':'input.dsd', 'foot':{'limit':5}})
    with jobs.connect() as con:
        con.execute('INSERT INTO sessions(id, dsd_path, xlsx_path, meta) VALUES(?,?,?,?)',
                    ('s', 'input.dsd', str(path), '{}'))
    with studio._con() as con:
        con.execute('INSERT INTO mappings VALUES(?,?,?)', ('m', 'today', '{"items":[{}]}'))
    submitted = []
    monkeypatch.setattr(jobs, 'submit', lambda *a: submitted.append(a) or 'queued')
    if kind == 'prior':
        response = client.post('/api/workbench/sessions/s/recon', json={'prior_path':str(path),'tolerance':value})
    elif kind == 'xbrl':
        response = client.post('/api/studio/xbrl-recon', json={'session_id':'s','package_dir':str(tmp_path),'tolerance':value})
    elif kind == 'level':
        response = client.put('/api/workbench/sessions/s/foot/levels', json={'overrides':[{'sheet':'BS','row':4,'level':value}]})
    else:
        response = client.put('/api/studio/mapping/m/decide', json={'account_idx':value,'element':'ifrs-full_Second'})
    assert response.status_code == 422
    assert response.json()['detail']
    assert not submitted
