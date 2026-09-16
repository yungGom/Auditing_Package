"""Golden writers and explicit current-source bindings; no prior input required."""
import copy
import hashlib
import json
import os
from pathlib import Path
import zipfile

import pytest


def api():
    from auditdesk import golden
    return golden


def test_biff_strings_blanks_styles_and_repeated_roles(tmp_path):
    g = api()
    model = g.new_workbook([
        ('본문', [(0, 0, '\u3000자산'), (1, 0, ''), (2, 0, None),
                  (3, 0, '0'), (4, 0, '(1,234)'), (5, 0, '0.2192')]),
        ('주석', [(0, 0, '두 줄\n원문')]),
    ])
    path = tmp_path/'out.xls'
    g.write_xls(model, path)
    assert path.read_bytes().startswith(bytes.fromhex('d0cf11e0a1b11ae1'))
    assert g.semantic_snapshot(g.read_xls(path)) == g.semantic_snapshot(model)
    assert g.formula_count(path) == 0
    with pytest.raises(ValueError, match='존재'):
        g.write_xls(model, path)


def test_xlsx_disguise_is_rejected(tmp_path):
    g = api()
    path = tmp_path/'fake.xls'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('content.xml', '<x/>')
    with pytest.raises(ValueError, match='BIFF'):
        g.read_xls(path)


def test_formula_source_is_rejected(tmp_path):
    g = api()
    import xlwt
    w = xlwt.Workbook(); s = w.add_sheet('s'); s.write(0, 0, xlwt.Formula('1+1'))
    path = tmp_path/'formula.xls'; w.save(str(path))
    with pytest.raises(ValueError, match='수식'):
        g.read_xls(path)


def current_case(tmp_path):
    g = api()
    text = '<DOCUMENT><TABLE><TR><TD>새 회사</TD><TD>1,234</TD><TD>2026.06.30</TD></TR></TABLE></DOCUMENT>'
    dsd = tmp_path/'current.dsd'
    with zipfile.ZipFile(dsd, 'w') as z:
        z.writestr('contents.xml', text)
    tax = g.new_workbook([('재무상태표', [
        (0, 0, 'Role URI'), (0, 1, 'urn:current:bs'),
        (1, 0, 'Role Definition'), (1, 1, '현재 정의'),
        *[(2, c, h) for c, h in enumerate(g.TAXONOMY_HEADER)],
        *[(3, c, v) for c, v in enumerate(['LINEITEM', 'company', 'Cash',
            '   현금', 'Cash', 'urn:label', 'monetaryItemType', 'DEBIT', 'INSTANT', '0', ''])],
    ])])
    layout = g.new_workbook([('재무상태표', [(0, 0, '표 제목'), (1, 0, 'old value')])])
    g.write_xls(tax, tmp_path/'current_taxonomy.xls')
    g.write_xls(layout, tmp_path/'layout.xls')
    report = {'company': 'company', 'scope': 'separate', 'period_end': '2026-06-30', 'fiscal_number': '13'}
    binding = {'sheet': '재무상태표', 'row': 2, 'column': 1,
        'source_start': text.index('1,234'), 'source_end': text.index('1,234')+5,
        'role': 'urn:current:bs', 'prefix': 'company', 'name': 'Cash',
        'taxonomy_sheet': '재무상태표', 'taxonomy_row': 4,
        'context': {'company': 'company', 'scope': 'separate',
                    'instant': '2026-06-30', 'dimensions': [], 'unit': 'KRW'},
        'data_type': 'monetary', 'source_evidence': 'current confirmed mapping'}
    manifest = {'report': report,
        'dsd_sha256': hashlib.sha256(dsd.read_bytes()).hexdigest(),
        'taxonomy_sha256': hashlib.sha256((tmp_path/'current_taxonomy.xls').read_bytes()).hexdigest(),
        'layout_sha256': hashlib.sha256((tmp_path/'layout.xls').read_bytes()).hexdigest(),
        'bindings': [binding],
        'static_cells': [{'sheet': '재무상태표', 'row': 1, 'column': 1,
                          'source_evidence': 'current report title'}]}
    return dsd, manifest


def test_current_first_build_without_prior_and_rerun(tmp_path):
    g = api(); dsd, manifest = current_case(tmp_path)
    results = []
    for name in ('one', 'two'):
        results.append(g.build_current(dsd, tmp_path/'current_taxonomy.xls',
            tmp_path/'layout.xls', manifest, tmp_path/name))
    assert results[0]['complete'] is True
    output = g.read_xls(results[0]['excel'])
    assert output['sheets'][0]['cells'][1][3] == '1,234'
    assert results[0]['bindings'][0]['raw_value'] == '1234'
    assert g.semantic_snapshot(output) == g.semantic_snapshot(g.read_xls(results[1]['excel']))
    assert 'contextId' not in results[0]['bindings'][0]['context']


@pytest.mark.parametrize('failure', ['unbound', 'stale', 'unknown_concept', 'wrong_company', 'wrong_period', 'duplicate'])
def test_current_first_rejects_incomplete_or_stale_bindings(tmp_path, failure):
    g = api(); dsd, manifest = current_case(tmp_path)
    if failure == 'unbound': manifest['static_cells'] = []
    elif failure == 'stale': manifest['dsd_sha256'] = '0'*64
    elif failure == 'unknown_concept': manifest['bindings'][0]['name'] = 'OldConcept'
    elif failure == 'wrong_company': manifest['bindings'][0]['context']['company'] = 'other'
    elif failure == 'wrong_period': manifest['bindings'][0]['context']['instant'] = '2027-06-30'
    elif failure == 'duplicate': manifest['bindings'] *= 2
    with pytest.raises(ValueError):
        g.build_current(dsd, tmp_path/'current_taxonomy.xls', tmp_path/'layout.xls', manifest, tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('kind', ['taxonomy', 'Excel'])
def test_actual_golden_writer_roundtrip(tmp_path, kind):
    folder = os.environ.get('AUDITDESK_GOLDEN_DIR')
    if not folder:
        pytest.skip('External customer Golden files are not distributed with the repository')
    g = api()
    path = Path(folder)/f'코스맥스 2분기 XBRL_최종_연결검토완료_{kind}.xls'
    model = g.read_xls(path)
    assert len(model['sheets']) == (83 if kind == 'taxonomy' else 42)
    result = tmp_path/f'{kind}.xls'
    g.write_xls(model, result)
    assert g.semantic_snapshot(g.read_xls(result)) == g.semantic_snapshot(model)
    assert g.formula_count(result) == 0
    if kind == 'taxonomy':
        from collections import Counter
        rows = [{(r, c): v for r, c, t, v, st in s['cells']} for s in model['sheets']]
        assert sum(v == 'Prefix' for sheet in rows for (r, c), v in sheet.items() if c == 1) == 168
        assert Counter(v for sheet in rows for (r, c), v in sheet.items() if c == 0 and v in
                       ('TABLE', 'DOMAIN', 'LINEITEM')) == {'TABLE': 160, 'DOMAIN': 1088, 'LINEITEM': 1346}
        assert all(not s['merged'] for s in model['sheets'])
    else:
        assert sum((r1-r0)*(c1-c0)>1 for s in model['sheets'] for r0,r1,c0,c1 in s['merged']) == 599
        values = {s['name']: {(r, c): v for r, c, t, v, st in s['cells']} for s in model['sheets']}
        bs = values['재무상태표 (연결)']; note = values['3. 현금및현금성자산 (연결)']
        for col, start in [(1, 5), (2, 12)]:
            assert sum(int(note[(r, 1)].replace(',', '')) for r in (start, start+1)) == int(bs[(7, col)].replace(',', ''))
        assert values['28. 법인세비용 (연결)'][(7, 1)] == '0.2192'


def test_current_dsd_changed_value_requires_reapproval_then_uses_new_value(tmp_path):
    g = api(); dsd, manifest = current_case(tmp_path)
    with zipfile.ZipFile(dsd) as z:
        text = z.read('contents.xml').decode().replace('1,234', '9,876')
    with zipfile.ZipFile(dsd, 'w') as z:
        z.writestr('contents.xml', text)
    with pytest.raises(ValueError, match='재검토'):
        g.build_current(dsd, tmp_path/'current_taxonomy.xls', tmp_path/'layout.xls', manifest, tmp_path/'out')
    manifest['dsd_sha256'] = hashlib.sha256(dsd.read_bytes()).hexdigest()
    result = g.build_current(dsd, tmp_path/'current_taxonomy.xls', tmp_path/'layout.xls', manifest, tmp_path/'out')
    assert result['bindings'][0]['raw_value'] == '9876'
    assert g.read_xls(result['excel'])['sheets'][0]['cells'][1][3] == '9,876'


def test_same_qname_keeps_distinct_role_and_context_occurrences(tmp_path):
    g = api(); dsd, manifest = current_case(tmp_path)
    tax = g.read_xls(tmp_path/'current_taxonomy.xls')
    second = copy.deepcopy(tax['sheets'][0]); second['name'] = '주석'
    next(c for c in second['cells'] if c[:2] == [0, 1])[3] = 'urn:current:note'
    tax['sheets'].append(second)
    tax_path = tmp_path/'two_tax.xls'; g.write_xls(tax, tax_path)
    layout = g.new_workbook([('재무상태표', [(0, 0, '표 제목'), (1, 0, 'old value')]), ('주석', [(0, 0, 'old note')])])
    layout_path = tmp_path/'two_layout.xls'; g.write_xls(layout, layout_path)
    manifest['taxonomy_sha256'] = hashlib.sha256(tax_path.read_bytes()).hexdigest()
    manifest['layout_sha256'] = hashlib.sha256(layout_path.read_bytes()).hexdigest()
    second = copy.deepcopy(manifest['bindings'][0])
    second.update(sheet='주석', row=1, taxonomy_sheet='주석', role='urn:current:note')
    second['context']['dimensions'] = [{'axis': 'current:axis', 'member': 'current:member'}]
    manifest['bindings'].append(second)
    result = g.build_current(dsd, tax_path, layout_path, manifest, tmp_path/'out')
    assert len(result['bindings']) == 2
    assert result['bindings'][0]['context'] != result['bindings'][1]['context']


def test_current_first_cli(tmp_path, capsys):
    from auditdesk.__main__ import main
    dsd, manifest = current_case(tmp_path)
    bindings = tmp_path/'bindings.json'
    bindings.write_text(json.dumps(manifest), encoding='utf-8')
    main(['golden', '--current-dsd', str(dsd), '--taxonomy', str(tmp_path/'current_taxonomy.xls'),
          '--layout', str(tmp_path/'layout.xls'), '--bindings', str(bindings), '--out', str(tmp_path/'result')])
    assert (tmp_path/'result/taxonomy.xls').exists()
    assert (tmp_path/'result/Excel.xls').exists()
    assert 'review.json' in capsys.readouterr().out


def test_current_taxonomy_type_mismatch_is_rejected(tmp_path):
    g = api(); dsd, manifest = current_case(tmp_path)
    manifest['bindings'][0]['data_type'] = 'text'
    with pytest.raises(ValueError, match='유형'):
        g.build_current(dsd, tmp_path/'current_taxonomy.xls', tmp_path/'layout.xls', manifest, tmp_path/'out')


def test_current_taxonomy_period_mismatch_is_rejected(tmp_path):
    g = api(); dsd, manifest = current_case(tmp_path)
    ctx = manifest['bindings'][0]['context']
    del ctx['instant']; ctx.update(start='2026-01-01', end='2026-06-30')
    with pytest.raises(ValueError, match='기간'):
        g.build_current(dsd, tmp_path/'current_taxonomy.xls', tmp_path/'layout.xls', manifest, tmp_path/'out')


def test_taxonomy_fact_column_must_stay_empty(tmp_path):
    g = api(); dsd, manifest = current_case(tmp_path)
    model = g.read_xls(tmp_path/'current_taxonomy.xls')
    next(c for c in model['sheets'][0]['cells'] if c[:2] == [3, 10])[3] = '1234'
    p = tmp_path/'bad_taxonomy.xls'; g.write_xls(model, p)
    manifest['taxonomy_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='Fact'):
        g.build_current(dsd, p, tmp_path/'layout.xls', manifest, tmp_path/'out')
