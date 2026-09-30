"""Raw DSD + raw current XLSX to local recommendation JSON; no real input data."""
from dataclasses import asdict
import json
import socket
import pytest
from auditdesk.xbrl_v2.recommendation import analyze
from auditdesk.xbrl_v2.__main__ import main
from test_xbrl_v2_recommendation import inputs, amount


def test_raw_current_only_pipeline_without_network(monkeypatch):
    doc,tax,dsd_bytes,tax_bytes=inputs()
    def forbidden(*args,**kwargs): raise AssertionError('network access')
    monkeypatch.setattr(socket,'socket',forbidden)
    result=analyze(dsd_bytes,tax_bytes,report=doc.metadata.requested,metadata=tax.metadata,namespaces=tax.namespaces)
    actual=next(s for s in result.subjects if s.subject_id==amount(doc).subject_id)
    assert actual.state=='SUGGESTED' and actual.candidates
    assert all(c.role_uri=='urn:role:bs' for c in actual.candidates)
    assert all(c.current_validation=='PARTIAL' for c in actual.candidates)
    assert result.coverage.total==len(doc.subjects)


def test_cli_publishes_local_json_and_preserves_inputs(tmp_path):
    doc,tax,dsd_bytes,tax_bytes=inputs()
    dsd=tmp_path/'current.dsd'; dsd.write_bytes(dsd_bytes)
    workbook=tmp_path/'current.xlsx'; workbook.write_bytes(tax_bytes)
    context=tmp_path/'context.json';context.write_text(json.dumps({'report':asdict(doc.metadata.requested),'taxonomy':asdict(tax.metadata),'namespaces':[asdict(n) for n in tax.namespaces]}),encoding='utf-8')
    out=tmp_path/'recommendations.json'
    args=['--dsd',str(dsd),'--taxonomy',str(workbook),'--context',str(context),'--out',str(out)]
    assert main(args)==0
    result=json.loads(out.read_text(encoding='utf-8'))
    assert result['coverage']['total']==len(doc.subjects)
    assert all(s['state'] not in ('USER_CONFIRMED','DERIVED_FROM_CONFIRMED') for s in result['subjects'])
    assert dsd.read_bytes()==dsd_bytes and workbook.read_bytes()==tax_bytes
    previous=out.read_bytes();dsd.write_bytes(b'corrupt')
    assert main(args)==2 and out.read_bytes()==previous


def test_cli_rejects_output_over_input_and_golden_payload(tmp_path):
    doc,tax,dsd_bytes,tax_bytes=inputs()
    d=tmp_path/'d.dsd';d.write_bytes(dsd_bytes)
    t=tmp_path/'t.xlsx';t.write_bytes(tax_bytes)
    c=tmp_path/'c.json';c.write_text(json.dumps({'report':asdict(doc.metadata.requested),'taxonomy':asdict(tax.metadata),'namespaces':[asdict(n) for n in tax.namespaces],'golden':'forbidden'}),encoding='utf-8')
    assert main(['--dsd',str(d),'--taxonomy',str(t),'--context',str(c),'--out',str(d)])==2
    assert d.read_bytes()==dsd_bytes
    assert main(['--dsd',str(d),'--taxonomy',str(t),'--context',str(c),'--out',str(tmp_path/'out.json')])==2


def test_cli_hardlink_alias_and_failed_atomic_replace_preserve_output(tmp_path, monkeypatch):
    import os
    import auditdesk.xbrl_v2.__main__ as cli
    doc,tax,dsd_bytes,tax_bytes=inputs()
    d=tmp_path/'d.dsd';d.write_bytes(dsd_bytes)
    t=tmp_path/'t.xlsx';t.write_bytes(tax_bytes)
    c=tmp_path/'c.json';c.write_text(json.dumps({'report':asdict(doc.metadata.requested),'taxonomy':asdict(tax.metadata),'namespaces':[asdict(n) for n in tax.namespaces]}),encoding='utf-8')
    out=tmp_path/'alias.json';os.link(d,out)
    args=['--dsd',str(d),'--taxonomy',str(t),'--context',str(c),'--out',str(out)]
    assert main(args)==2 and d.read_bytes()==dsd_bytes
    out.unlink();out.write_bytes(b'previous')
    def fail_replace(*args): raise OSError('synthetic write failure')
    monkeypatch.setattr(cli.os,'replace',fail_replace)
    assert main(args)==2 and out.read_bytes()==b'previous'
    assert not list(tmp_path.glob('.recommendations-*.tmp'))
