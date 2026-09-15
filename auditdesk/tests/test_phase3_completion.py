"""Phase 3 product entry points: real workbooks, isolated jobs and inputs."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from auditdesk import jobs
from auditdesk.routers import studio, jobs_api
_REAL_SUBMIT = jobs.submit


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, '_DB', str(tmp_path / 'jobs.sqlite'))
    monkeypatch.setattr(studio, '_WORKDIR', str(tmp_path / 'outputs'))
    # Execute the actual submitted function, preserving job result/error contract.
    def submit(kind, fn):
        result = fn(lambda *a: None)
        return result
    monkeypatch.setattr(jobs, 'submit', submit)
    app = FastAPI()
    app.include_router(studio.router, prefix='/api/studio')
    app.include_router(jobs_api.router, prefix='/api/jobs')
    return TestClient(app)


def workbook(path):
    wb = Workbook(); ws = wb.active; ws.title = 'BS'
    ws.append(['자산', 100]); wb.save(path)
    return str(path)


def test_m18_mapping_product_entry_and_repeat(client, tmp_path):
    left = workbook(tmp_path / 'left.xlsx')
    right = workbook(tmp_path / 'right.xlsx')
    body = {'left_xlsx': left, 'right_xlsx': right,
            'pairs': [{'left': 'BS', 'right': 'BS', 'name': 'BS', 'basis': '사용자 확인'}]}
    response = client.post('/api/studio/mapping-workbook', json=body)
    assert response.status_code == 202
    result = response.json()['job_id']
    path = Path(result['out_path']); before = path.read_bytes()
    assert '총괄표' in load_workbook(path).sheetnames
    again = client.post('/api/studio/mapping-workbook', json=body).json()['job_id']
    assert again['out_path'] != str(path) and path.read_bytes() == before


@pytest.mark.parametrize('pairs', [[], [{'left':'missing','right':'BS','name':'BS'}],
                                   [{'left':None,'right':None,'name':'BS'}]])
def test_m18_invalid_assembly_inputs_are_actionable(client, tmp_path, pairs):
    p = workbook(tmp_path / 'left.xlsx')
    response = client.post('/api/studio/mapping-workbook', json={
        'left_xlsx':p, 'right_xlsx':p, 'pairs':pairs})
    assert response.status_code == 422
    assert response.json()['detail']


def test_m19_missing_input_is_actionable(client):
    response = client.post('/api/studio/attr-check', json={})
    assert response.status_code == 422
    assert response.json()['detail']


def test_m20_worksheet_attaches_guide_without_inventing_pass(tmp_path, monkeypatch):
    from dsd_tool import worksheet
    from dsd_tool.tests.fixture import build_dsd
    monkeypatch.setattr(worksheet, 'MappingCorpus', lambda *a, **k: SimpleNamespace(std_labels={}))
    monkeypatch.setattr(worksheet, 'suggest', lambda *a, **k: {'verdict':'없음','similar_extensions':[]})
    result = worksheet.build_worksheet(build_dsd(str(tmp_path/'input.dsd')),
        out_path=str(tmp_path/'worksheet.xlsx'), include_notes=False)
    ws = load_workbook(result['out_path'])['가이드 체크']
    assert '판단필요' in [c.value for row in ws for c in row]
    assert result['guide_check']['need_judge'] > 0


def test_m21_cli_entry_is_discoverable():
    from auditdesk.__main__ import main
    with pytest.raises(SystemExit) as e:
        main(['rollforward', '--help'])
    assert e.value.code == 0


def test_m22_invalid_target_is_rejected(client):
    response = client.post('/api/studio/xbrl-recon', json={'target':'typo'})
    assert response.status_code == 422


@pytest.fixture
def package(tmp_path):
    pkg = tmp_path / 'package'; pkg.mkdir()
    (pkg/'sample.xbrl').write_text('''<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:co="urn:company" xmlns:iso4217="urn:iso">
    <xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="test">company</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
    <xbrli:unit id="krw"><xbrli:measure>iso4217:KRW</xbrli:measure></xbrli:unit>
    <co:Assets contextRef="c" unitRef="krw" decimals="0">100</co:Assets>
    </xbrli:xbrl>''', encoding='utf-8')
    (pkg/'sample_pre.xml').write_text('<linkbase xmlns="http://www.xbrl.org/2003/linkbase"/>', encoding='utf-8')
    (pkg/'sample.xsd').write_text('''<schema xmlns="http://www.w3.org/2001/XMLSchema" xmlns:xbrli="http://www.xbrl.org/2003/instance">
    <element id="co_Assets" name="Assets" type="xbrli:monetaryItemType" xbrli:periodType="instant"/>
    </schema>''', encoding='utf-8')
    (pkg/'succession_assets.json').write_text(json.dumps({'source':str(pkg),'elements':[]}), encoding='utf-8')
    return pkg


def test_m19_real_parser_core_excel_and_reexecution(client, package, tmp_path):
    from dsd_tool.tests.fixture import build_dsd
    from dsd_tool.excel_out import extract
    xlsx = str(tmp_path/'source.xlsx')
    extract(build_dsd(str(tmp_path/'source.dsd')), xlsx)
    body = {'xlsx_path':xlsx, 'package_dir':str(package)}
    response = client.post('/api/studio/attr-check', json=body)
    assert response.status_code == 202
    result = response.json()['job_id']
    assert result['summary']['period'] == {'true':1,'false':0,'na':0,'total':1}
    assert result['summary']['unit']['true'] == 1
    assert result['summary']['name']['false'] > 0
    assert Path(result['out_path']).is_file()
    xml = package/'sample.xsd'
    xml.write_text(xml.read_text().replace('periodType="instant"','periodType="duration"'))
    bad = client.post('/api/studio/attr-check', json=body).json()['job_id']
    assert bad['summary']['period']['false'] == 1
    assert bad['out_path'] != result['out_path']


def test_m21_new_current_cli_workflow_and_guide(package, tmp_path, capsys):
    from auditdesk.__main__ import main
    from dsd_tool.tests.fixture import build_dsd
    source = build_dsd(str(tmp_path/'half.dsd'))
    args = ['rollforward','--half',source,'--package',str(package),'--year-end',source]
    out = tmp_path/'new.xlsx'
    main(args+['--out',str(out)])
    assert '가이드 체크' in load_workbook(out).sheetnames
    assert '판단필요' in capsys.readouterr().out
    update = tmp_path/'update.xlsx'
    main(args+['--current',source,'--out',str(update)])
    assert '가이드 체크' in load_workbook(update).sheetnames
    assert '갱신' in capsys.readouterr().out
    before = out.read_bytes()
    with pytest.raises(SystemExit) as e:
        main(args+['--out',str(out)])
    assert e.value.code == 2 and out.read_bytes() == before


def test_m18_corrupt_excel_is_input_error(client, tmp_path):
    bad = tmp_path/'broken.xlsx'; bad.write_bytes(b'not an Excel file')
    response = client.post('/api/studio/mapping-workbook', json={
        'left_xlsx':str(bad), 'right_xlsx':str(bad),
        'pairs':[{'left':'BS','right':'BS','name':'BS'}]})
    assert response.status_code == 422


def test_m21_update_connects_existing_recommendation(package, tmp_path, monkeypatch):
    from auditdesk.completion import run_rollforward
    from dsd_tool import rollforward, mapping
    calls = []
    monkeypatch.setattr(mapping, 'MappingCorpus', lambda: 'existing corpus')
    monkeypatch.setattr(mapping, 'suggest', lambda corpus, name: calls.append((corpus,name)) or
                        {'candidates':[{'element_id':'ifrs-full_OtherCurrentAssets'}]})
    def core(*args, **kwargs):
        assert kwargs['current_xlsx']
        assert kwargs['recommend']('신규계정') == ['ifrs-full_OtherCurrentAssets']
        return {'out_path':kwargs['out_path']}
    monkeypatch.setattr(rollforward, 'rollforward', core)
    source = workbook(tmp_path/'source.xlsx')
    run_rollforward(source,str(package),source,str(tmp_path/'out.xlsx'),current=source)
    assert calls == [('existing corpus','신규계정')]


def test_product_job_error_then_recovery_and_result_restore(client, tmp_path, package, monkeypatch):
    import time
    from dsd_tool.tests.fixture import build_dsd
    from dsd_tool.excel_out import extract
    monkeypatch.setattr(jobs, 'submit', _REAL_SUBMIT)
    source = str(tmp_path/'source.xlsx')
    extract(build_dsd(str(tmp_path/'source.dsd')), source)
    broken = tmp_path/'broken_package'; broken.mkdir()
    def run(pkg):
        response = client.post('/api/studio/attr-check', json={'xlsx_path':source,'package_dir':str(pkg)})
        assert response.status_code == 202
        jid = response.json()['job_id']
        deadline = time.monotonic()+60
        while time.monotonic() < deadline:
            result = client.get('/api/jobs/'+jid).json()
            if result['state'] in ('done','error'):
                return result
            time.sleep(.02)
        pytest.fail('job did not finish')
    bad = run(broken)
    assert bad['state'] == 'error' and bad['error_detail']['detail']
    good = run(package)
    assert good['state'] == 'done' and Path(good['result']['out_path']).is_file(), good
    restored = client.get('/api/jobs?kind=attr-check').json()['jobs']
    assert any(j['job_id']==good['job_id'] and j['result']==good['result'] for j in restored)


def test_m22_no_prior_context_has_actionable_product_error(client, tmp_path, package):
    from dsd_tool.tests.fixture import build_dsd
    from dsd_tool.excel_out import extract
    dsd = build_dsd(str(tmp_path/'prior.dsd'))
    source = str(tmp_path/'prior.xlsx'); extract(dsd, source)
    with jobs.connect() as con:
        con.execute('INSERT INTO sessions(id,dsd_path,xlsx_path,meta) VALUES(?,?,?,?)',
                    ('prior',dsd,source,'{}'))
    response = client.post('/api/studio/xbrl-recon',json={
        'session_id':'prior','package_dir':str(package),'target':'prior'})
    assert response.status_code == 422
    assert '전기' in response.json()['detail'] and '컨텍스트' in response.json()['detail']


def test_m22_actual_current_prior_result_scope(client, tmp_path, package):
    from dsd_tool.tests.fixture import build_dsd
    from dsd_tool.excel_out import extract
    inst = package/'sample.xbrl'
    xml = inst.read_text()
    start = xml.index('<xbrli:context'); end = xml.index('</xbrli:context>')+len('</xbrli:context>')
    prior = xml[start:end].replace('id="c"','id="p"').replace('2025-12-31','2024-12-31')
    inst.write_text(xml.replace('</xbrli:xbrl>',prior+'<co:Assets contextRef="p" unitRef="krw" decimals="0">90</co:Assets></xbrli:xbrl>'))
    dsd = build_dsd(str(tmp_path/'input.dsd')); xlsx = str(tmp_path/'input.xlsx'); extract(dsd,xlsx)
    with jobs.connect() as con:
        con.execute('INSERT INTO sessions(id,dsd_path,xlsx_path,meta) VALUES(?,?,?,?)',('s',dsd,xlsx,'{}'))
    for target in ['current','prior']:
        response = client.post('/api/studio/xbrl-recon',json={'session_id':'s','package_dir':str(package),'target':target})
        assert response.status_code == 202
        result = response.json()['job_id']
        assert result['target']==target and result['session_id']=='s'
        assert Path(result['out_path']).is_file()
        if target=='prior':
            assert result['target_ends']=={'instant':'2024-12-31','duration':None}
            assert 'PL' in result['skipped_sheets'] and 'CF' in result['skipped_sheets']
        else:
            assert result['target_ends']=={'instant':'2025-12-31','duration':'2025-12-31'}
