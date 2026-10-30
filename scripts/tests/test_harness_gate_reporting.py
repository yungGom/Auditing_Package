"""Structured evidence reaches Orchestrator without hiding compatibility gaps."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]))
import auditdesk_partition as partition
import orchestrator_results as results
import harness_evidence as evidence

NODE='dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct'

class EvidenceTests(unittest.TestCase):
    def report(self):
        manifest=json.loads(partition.MANIFEST.read_text(encoding='utf-8'))
        technical={n:{'status':'PASS'} for n in ['test_new.py::test_new']+manifest['technical_marker_overrides']}
        real={r['selector']:{'status':partition.BLOCKED} for r in manifest['checks']}
        return {'technical_gate':'PASS','technical_checks':{'auditdesk_python':{
            'status':'PASS','counts':{s:len(technical) if s=='PASS' else 0 for s in evidence.STATUSES},
            'checks':technical,'collected':len(technical)+len(real),'collection_errors':0},
            'webui_build':{'status':'PASS'},'dsd_footing':{'status':'PASS'}},
            'real_material_compatibility':{'status':partition.BLOCKED,'checks':real}}

    def summary(self,r):
        return results.summarize('scripts/test_all.py',SimpleNamespace(stdout='HARNESS_REPORT_JSON:'+json.dumps(r),stderr='',returncode=0))
    def test_orchestrator_retains_gap(self):
        r=self.summary(self.report());gaps,regressions,unknown=results.compare([r],[r],set())
        self.assertEqual(len(gaps),1);self.assertFalse(regressions);self.assertFalse(unknown)
    def test_new_compatibility_failure_not_partial_pass(self):
        before=self.summary(self.report());after=json.loads(json.dumps(before));after['real_material_compatibility']['checks'][NODE]['status']='FAIL'
        self.assertTrue(results.compare([before],[after],set())[1])
    def test_missing_marker_fails_even_with_zero_exit(self):
        r=results.summarize('scripts/test_all.py',SimpleNamespace(stdout='225 passed',stderr='',returncode=0))
        self.assertEqual(r['status'],'FAIL')
    def test_invalid_incomplete_or_false_compatibility_pass_fails(self):
        for kind in ('empty','invalid','false_pass','missing_component'):
            r=self.report()
            if kind=='empty':r['real_material_compatibility']['checks']={}
            if kind=='invalid':r['technical_gate']='UNKNOWN'
            if kind=='false_pass':r['real_material_compatibility']['status']='PASS'
            if kind=='missing_component':r['technical_checks'].pop('dsd_footing')
            self.assertEqual(self.summary(r)['status'],'FAIL')
    def test_disappearing_compatibility_row_is_new_regression(self):
        before=self.summary(self.report());after=json.loads(json.dumps(before))
        after['real_material_compatibility']['checks'].pop(NODE)
        self.assertIn('scripts/test_all.py: compatibility evidence disappeared',results.compare([before],[after],set())[1])


class WorkflowEvidenceTests(unittest.TestCase):
    report = EvidenceTests.report
    def test_unscoped_rejects_missing_marker_before_reviewer(self):
        import orchestrator as orch
        from argparse import Namespace
        issue={'number':23,'state':'OPEN','title':'Harness','body':'## Required tests\n`python scripts/test_all.py`\n## Human decision required\nnone'}
        runtime={'ready':True,'selected_executable':'python'}
        with patch.object(orch,'get_issue',return_value=issue),patch.object(orch,'changed_files',return_value=[]),patch.object(orch,'runtime_preflight',return_value=runtime),patch.object(orch,'agent',return_value={'decision':'PASS','summary':'implemented','findings':[]}) as agents,patch.object(orch,'protected_check',return_value=(True,'PASS')),patch.object(orch,'command',return_value=SimpleNamespace(stdout='225 passed',stderr='',returncode=0)):
            args=Namespace(repo='example/repo',issue=23,issue_json=None,dry_run=False,max_attempts=1,agent_timeout=30,test_timeout=30,no_comment=True,report=None,python_candidate=[])
            report=orch.run(args)
        self.assertEqual(report['state'],'FAILED');self.assertEqual(agents.call_count,1)

    def test_unscoped_valid_technical_pass_retains_compatibility_gap(self):
        import orchestrator as orch
        from argparse import Namespace
        issue={'number':23,'state':'OPEN','title':'Harness','body':'## Required tests\n`python scripts/test_all.py`\n## Human decision required\nnone'}
        runtime={'ready':True,'selected_executable':'python'}
        reply={'decision':'PASS','summary':'approved','findings':[]}
        with patch.object(orch,'get_issue',return_value=issue),patch.object(orch,'changed_files',return_value=[]),patch.object(orch,'runtime_preflight',return_value=runtime),patch.object(orch,'agent',return_value=reply) as agents,patch.object(orch,'protected_check',return_value=(True,'PASS')),patch.object(orch,'worktree_fingerprint',return_value=[]),patch.object(orch,'command',return_value=SimpleNamespace(stdout='HARNESS_REPORT_JSON:'+json.dumps(self.report()),stderr='',returncode=0)):
            args=Namespace(repo='example/repo',issue=23,issue_json=None,dry_run=False,max_attempts=1,agent_timeout=30,test_timeout=30,no_comment=True,report=None,python_candidate=[])
            report=orch.run(args)
        self.assertEqual(report['state'],'TASK_PASS_WITH_KNOWN_GAPS');self.assertEqual(agents.call_count,2)
        self.assertEqual(report['attempts'],1);self.assertEqual(report['human_business_acceptance'],'PENDING')
