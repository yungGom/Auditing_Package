"""Behavioral checks for the protected-artifact diff gate."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from check_protected import check  # noqa: E402


class ProtectedDiffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="protected_gate_test_")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.write("DSD_footing/GATES.json", '{"samples": {}}\n')
        self.write("auditdesk/dsd_workbench/dsd_tool/mapping.py", "DEFAULT_THRESHOLD = 0.45\n")
        self.write("auditdesk/dsd_workbench/dsd_tool/xbrl_recon.py", "result = foo(min_sim=0.85)\n")
        self.write("auditdesk/dsd_workbench/dsd_tool/tests/test_existing.py", "assert 2 == 2\n")
        self.write("unrelated.py", "VALUE = 1\n")
        manifest = SCRIPTS.parent / "governance" / "protected_paths.json"
        dest = self.repo / "governance" / "protected_paths.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest, dest)
        self.git("init", "-q")
        self.git("config", "user.name", "Harness Test")
        self.git("config", "user.email", "harness@example.invalid")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def write(self, path, content):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def findings(self, staged=False):
        return check(self.repo, "HEAD", staged)

    def test_gate_snapshot_change_blocked(self):
        self.write("DSD_footing/GATES.json", '{"samples": {"changed": true}}\n')
        self.assertTrue(any("GATES.json" in item for item in self.findings()))

    def test_staged_gate_snapshot_change_blocked(self):
        self.write("DSD_footing/GATES.json", '{"samples": {"changed": true}}\n')
        self.git("add", "DSD_footing/GATES.json")
        self.assertTrue(any("GATES.json" in item for item in self.findings(staged=True)))

    def test_threshold_value_change_blocked(self):
        self.write("auditdesk/dsd_workbench/dsd_tool/mapping.py", "DEFAULT_THRESHOLD = 0.01\n")
        self.assertTrue(any("DEFAULT_THRESHOLD" in item for item in self.findings()))

    def test_keyword_threshold_change_blocked(self):
        self.write("auditdesk/dsd_workbench/dsd_tool/xbrl_recon.py", "result = foo(min_sim=0.01)\n")
        self.assertTrue(any("min_sim" in item for item in self.findings()))

    def test_existing_expectation_change_blocked(self):
        self.write("auditdesk/dsd_workbench/dsd_tool/tests/test_existing.py", "assert 2 == 3\n")
        self.assertTrue(any("existing test" in item for item in self.findings()))

    def test_new_test_allowed(self):
        self.write("auditdesk/dsd_workbench/dsd_tool/tests/test_new.py", "assert 3 == 3\n")
        self.git("add", "auditdesk/dsd_workbench/dsd_tool/tests/test_new.py")
        self.assertEqual([], self.findings(staged=True))

    def test_new_error_ledger_blocked(self):
        self.write("auditdesk/ERRORS.json", "{}\n")
        self.git("add", "auditdesk/ERRORS.json")
        self.assertTrue(any("ERRORS.json" in item for item in self.findings(staged=True)))

    def test_policy_manifest_change_blocked_after_bootstrap(self):
        path = self.repo / "governance/protected_paths.json"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assertTrue(any("enforcement control" in item for item in self.findings()))

    def test_unrelated_code_change_allowed(self):
        self.write("unrelated.py", "VALUE = 2\n")
        self.assertEqual([], self.findings())


if __name__ == "__main__":
    unittest.main()
