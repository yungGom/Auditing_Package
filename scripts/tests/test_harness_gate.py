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
import time
import os
import harness_evidence as evidence
import harness_process as process_helper

NODE='dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct'

class GateTests(unittest.TestCase):
    def fake_run(self, argv,cwd,timeout):
        if 'auditdesk_partition.py' in ' '.join(argv):
            target=Path(argv[argv.index('--report')+1])
            manifest=json.loads(partition.MANIFEST.read_text(encoding='utf-8'))
            technical={n:{'status':'PASS'} for n in ['test_fake']+manifest['technical_marker_overrides']}
            compatibility={r['selector']:{'status':partition.BLOCKED} for r in manifest['checks']}
            target.write_text(json.dumps({'status':'PASS','counts':{s:len(technical) if s=='PASS' else 0 for s in evidence.STATUSES},'technical_checks':technical,'compatibility_checks':compatibility,'collected':len(technical)+len(compatibility),'collection_errors':0}))
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
        mark=SimpleNamespace(args=(missing,),name="skipif")
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
        for timeout in (0, -1, float('inf'), float('nan')):
            with self.assertRaises(ValueError): run_check(['fake'],Path.cwd(),timeout)



class MoreGateTests(unittest.TestCase):
    fake_run = GateTests.fake_run
    def test_empty_or_inconsistent_or_missing_catalog_evidence_fails(self):
        for corruption in ('empty', 'count', 'catalog', 'status', 'json'):
            with self.subTest(corruption=corruption):
                def run(argv, cwd, timeout):
                    result=self.fake_run(argv,cwd,timeout)
                    if 'auditdesk_partition.py' in ' '.join(argv):
                        target=Path(argv[argv.index('--report')+1]);r=json.loads(target.read_text())
                        if corruption=='empty': r['technical_checks']={}
                        if corruption=='count': r['counts']['PASS']+=1
                        if corruption=='catalog': r['compatibility_checks']={}
                        if corruption=='status': r['technical_checks']['test_fake']['status']='UNKNOWN'
                        target.write_text('broken' if corruption=='json' else json.dumps(r))
                    return result
                with patch.object(gate,'run_check',side_effect=run),patch.object(gate.shutil,'which',return_value=None):
                    r=gate.run_all('auditdesk')
                self.assertEqual(r['technical_gate'],'FAIL')
                self.assertEqual(r['technical_checks']['auditdesk_python']['reason'],'INVALID_EVIDENCE')

class MorePartitionTests(unittest.TestCase):
    plugin = PartitionTests.plugin
    item = PartitionTests.item
    collect = PartitionTests.collect
    def test_parameter_labels_do_not_leak(self):
        p=self.plugin(); self.collect(p,[self.item(NODE+'[C:\\private\\client.dsd]')])
        encoded=json.dumps(p.result(5))
        self.assertNotIn('private',encoded);self.assertNotIn('client',encoded)
        self.assertIn(NODE+'[case:1]',p.compatibility)

    def test_compatibility_mode_is_assessment_only_even_when_present(self):
        p=partition.Partition('compatibility',{'checks':[{'selector':NODE,'material':'DSD'}]})
        items=[self.item(missing=False)];self.collect(p,items)
        self.assertEqual(items,[]);self.assertEqual(p.result(5)['status'],'NOT RUN')

    def test_runtime_fixture_missing_prerequisite_is_blocked_without_execution(self):
        p=partition.Partition('technical',{'checks':[{'selector':NODE,'material':'public cache','required_paths':['cache/public.dsd']}]})
        with patch.object(Path,'exists',return_value=False):
            self.collect(p,[self.item(missing=False)])
        self.assertEqual(p.compatibility[NODE]['status'],partition.BLOCKED)

    def test_material_prerequisite_cannot_escape_repository(self):
        with self.assertRaises(ValueError):
            partition.Partition('technical',{'checks':[{'selector':NODE,'material':'cache','required_paths':['../outside.dsd']}]})

    def test_pure_numeric_test_kept_without_inherited_material_mark(self):
        p=partition.Partition('technical',{'checks':[], 'technical_marker_overrides':['test_pure']})
        inherited=SimpleNamespace(name='skipif',args=(True,))
        own=SimpleNamespace(name='skipif',args=(False,))
        item=SimpleNamespace(nodeid='test_pure',module=SimpleNamespace(pytestmark=inherited),iter_markers=lambda name=None:[own,inherited])
        self.collect(p,[item])
        self.assertEqual(list(item.iter_markers('skipif')),[own])
        self.assertEqual(p.technical['test_pure']['status'],'NOT RUN')

class MoreProcessTests(unittest.TestCase):
    def test_cleanup_failure_is_not_timeout_success(self):
        fake=SimpleNamespace(pid=123,returncode=None,wait=lambda timeout: (_ for _ in ()).throw(subprocess.TimeoutExpired('fake',timeout)))
        with patch.object(process_helper.subprocess,'Popen',return_value=fake),patch.object(process_helper,'stop',return_value=False),patch.object(sys,'stdout',io.StringIO()),patch('os.name','posix'):
            r=run_check(['fake'],'.',0.1)
        self.assertEqual(r['status'],'FAIL');self.assertEqual(r['reason'],'CLEANUP_FAILED')

    def test_timeout_stops_descendant(self):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile=Path(tmp)/'pid'
            child=f"import os,time;open({str(pidfile)!r},'w').write(str(os.getpid()));time.sleep(30)"
            parent=f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}]);time.sleep(30)"
            with patch.object(sys,'stdout',io.StringIO()):
                result=run_check([sys.executable,'-c',parent],Path.cwd(),2)
            self.assertEqual(result['reason'],'TIMEOUT')
            self.assertTrue(pidfile.exists())
            pid=int(pidfile.read_text())
            if os.name=='nt':
                import ctypes
                from ctypes import wintypes
                api=ctypes.WinDLL('kernel32',use_last_error=True)
                api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];api.OpenProcess.restype=wintypes.HANDLE
                api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];api.WaitForSingleObject.restype=wintypes.DWORD
                api.CloseHandle.argtypes=[wintypes.HANDLE]
                handle=api.OpenProcess(0x100000,False,pid)
                if handle:
                    try:self.assertEqual(api.WaitForSingleObject(handle,5000),0)
                    finally:api.CloseHandle(handle)
            else:
                stat=Path(f'/proc/{pid}/stat')
                if stat.exists(): self.assertEqual(stat.read_text().split()[2],'Z')

    def test_cp949_preserves_unencodable_output_by_escape(self):
        raw=io.BytesIO();out=io.TextIOWrapper(raw,encoding='cp949',write_through=True)
        with patch.object(sys,'stdout',out):
            r=run_check([sys.executable,'-c',"print('한글 \\u2014')"],Path.cwd(),5)
        self.assertEqual(r['status'],'PASS')
        text=raw.getvalue().decode('cp949')
        self.assertIn('한글',text);self.assertIn('\\u2014',text)


class ConsoleTests(unittest.TestCase):
    def test_cp949_report_file_and_console_are_equal(self):
        raw=io.BytesIO();out=io.TextIOWrapper(raw,encoding='cp949',write_through=True)
        report={'technical_gate':'PASS','technical_checks':{},'real_material_compatibility':{'status':partition.BLOCKED},'note':'한글 —'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'result.json'
            with patch.object(gate,'run_all',return_value=report),patch.object(sys,'argv',['gate','--report',str(path)]),patch.object(sys,'stdout',out):
                self.assertEqual(gate.main(),0)
            console=json.loads(raw.getvalue().decode('cp949').split('HARNESS_REPORT_JSON:')[1].splitlines()[0])
            self.assertEqual(console,json.loads(path.read_text(encoding='utf-8')))


if __name__=="__main__": unittest.main()
