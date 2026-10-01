"""Owner-approved partition, fail-closed outcomes, timeout and no false compatibility PASS."""
from pathlib import Path
import io
import json
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]))
import test_all as gate
import auditdesk_partition as partition
from harness_process import run_check
import orchestrator_results as results

NODE='dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct'

class GateTests(unittest.TestCase):
    def fake_run(self, argv,cwd,timeout):
        if 'auditdesk_partition.py' in ' '.join(argv):
            target=Path(argv[argv.index('--report')+1])
            target.write_text(json.dumps({'status':'PASS','counts':{'PASS':3,'FAIL':0,'SKIP':0,'NOT RUN':0},'technical_checks':{'test_fake':{'status':'PASS'}},'compatibility_checks':{NODE:{'status':partition.BLOCKED}}}))
        return {'status':'PASS','reason':'COMPLETED','exit_code':0}

    def test_technical_pass_with_material_blocker(self):
        with patch.object(gate,'run_check',side_effect=self.fake_run), patch.object(gate.shutil,'which',return_value='npm.CMD'),patch.object(Path,'is_dir',return_value=True):
            report=gate.run_all()
        self.assertEqual(report['technical_gate'],'PASS')
        self.assertEqual(report['real_material_compatibility']['status'],partition.BLOCKED)
        self.assertEqual(report['human_business_acceptance'],'PENDING')

    def test_missing_npm_is_not_run_and_gate_fails(self):
        with patch.object(gate,'run_check',side_effect=self.fake_run),patch.object(gate.shutil,'which',return_value=None):
            report=gate.run_all()
        self.assertEqual(report['technical_gate'],'FAIL')
        self.assertEqual(report['technical_checks']['webui_build']['status'],'NOT RUN')

    def test_timeout_does_not_stop_other_checks(self):
        def run(argv,cwd,timeout):
            if 'auditdesk_partition.py' in ' '.join(argv): return {'status':'FAIL','reason':'TIMEOUT','exit_code':-1}
            return self.fake_run(argv,cwd,timeout)
        with patch.object(gate,'run_check',side_effect=run),patch.object(gate.shutil,'which',return_value='npm.CMD'),patch.object(Path,'is_dir',return_value=True):
            r=gate.run_all()
        self.assertEqual(r['technical_gate'],'FAIL')
        self.assertEqual(r['technical_checks']['dsd_footing']['status'],'PASS')
        self.assertEqual(r['real_material_compatibility']['status'],'NOT RUN')

    def test_invalid_or_missing_evidence_fails(self):
        with patch.object(gate,'run_check',return_value={'status':'PASS','reason':'COMPLETED','exit_code':0}),patch.object(gate.shutil,'which',return_value=None):
            r=gate.run_all('auditdesk')
        self.assertEqual(r['technical_checks']['auditdesk_python']['reason'],'MISSING_EVIDENCE')
        self.assertEqual(r['technical_gate'],'FAIL')

    def test_unselected_project_not_run(self):
        with patch.object(gate,'run_check',return_value={'status':'PASS','reason':'COMPLETED','exit_code':0}):
            r=gate.run_all('dsd_footing')
        self.assertEqual(r['technical_gate'],'PASS')
        self.assertEqual(r['technical_checks']['auditdesk_python']['status'],'NOT RUN')

class PartitionTests(unittest.TestCase):
    def plugin(self): return partition.Partition('technical',{'checks':[{'selector':NODE,'material':'DSD generation'}]})
    def item(self,node=NODE,missing=True):
        mark=SimpleNamespace(args=(missing,))
        return SimpleNamespace(nodeid=node,module=SimpleNamespace(_KNOWN_GENERATIONS=[] if missing else ['public']),iter_markers=lambda name:[mark])
    def collect(self,p,items):
        hook=SimpleNamespace(pytest_deselected=lambda **kw:None)
        with patch.dict(sys.modules, {"pytest":SimpleNamespace(UsageError=RuntimeError)}):
            p.pytest_collection_modifyitems(None,SimpleNamespace(hook=hook),items)

    def test_missing_real_material_not_pass(self):
        p=self.plugin();items=[self.item(),self.item('test_new.py::test_new',False)]
        self.collect(p,items)
        self.assertEqual(len(items),1)
        self.assertEqual(p.compatibility[NODE]['status'],partition.BLOCKED)
        self.assertEqual(p.technical['test_new.py::test_new']['status'],'NOT RUN')

    def test_available_real_material_not_run_by_default(self):
        p=self.plugin(); self.collect(p,[self.item(missing=False)])
        self.assertEqual(p.compatibility[NODE]['status'],'NOT RUN')

    def test_unknown_new_skip_fails_technical(self):
        p=self.plugin();p.technical['test_new']={'status':'NOT RUN'}
        p.pytest_runtest_logreport(SimpleNamespace(nodeid='test_new',failed=False,skipped=True,when='setup',passed=False))
        self.assertEqual(p.result(0)['status'],'FAIL')

    def test_deleted_catalog_item_not_silently_dropped(self):
        with self.assertRaises(RuntimeError): self.collect(self.plugin(),[])

    def test_failed_call_cannot_be_replaced_by_passed_teardown(self):
        p=self.plugin();p.technical['test_new']={'status':'NOT RUN'}
        for failed,when in [(True,'call'),(False,'teardown')]:
            p.pytest_runtest_logreport(SimpleNamespace(nodeid='test_new',failed=failed,skipped=False,when=when,passed=not failed))
        self.assertEqual(p.result(1)['status'],'FAIL')

class ProcessTests(unittest.TestCase):
    def test_launch_failure_is_not_run(self):
        with patch('harness_process.subprocess.Popen',side_effect=PermissionError):
            self.assertEqual(run_check(['fake'],Path.cwd(),1)['status'],'NOT RUN')
    def test_real_timeout_terminates_process(self):
        with patch('sys.stdout',io.StringIO()):
            r=run_check([sys.executable,'-c','import time; time.sleep(30)'],Path.cwd(),0.2)
        self.assertEqual(r['reason'],'TIMEOUT')
        self.assertEqual(r['status'],'FAIL')
    def test_invalid_timeout(self):
        with self.assertRaises(ValueError): run_check(['fake'],Path.cwd(),0)

class EvidenceTests(unittest.TestCase):
    def report(self):
        return {'technical_gate':'PASS','technical_checks':{'auditdesk_python':{'status':'PASS','counts':{'PASS':221},'checks':{}},'webui_build':{'status':'PASS'},'dsd_footing':{'status':'PASS'}},'real_material_compatibility':{'status':partition.BLOCKED,'checks':{NODE:{'status':partition.BLOCKED}}}}
    def test_orchestrator_retains_gap(self):
        r=results.summarize('scripts/test_all.py',SimpleNamespace(stdout='HARNESS_REPORT_JSON:'+json.dumps(self.report()),stderr='',returncode=0))
        gaps,regressions,unknown=results.compare([r],[r],set())
        self.assertEqual(len(gaps),1);self.assertFalse(regressions);self.assertFalse(unknown)
    def test_new_compatibility_failure_not_partial_pass(self):
        before=results.summarize('scripts/test_all.py',SimpleNamespace(stdout='HARNESS_REPORT_JSON:'+json.dumps(self.report()),stderr='',returncode=0))
        after=json.loads(json.dumps(before));after['real_material_compatibility']['checks'][NODE]['status']='FAIL'
        self.assertTrue(results.compare([before],[after],set())[1])

if __name__=='__main__': unittest.main()
