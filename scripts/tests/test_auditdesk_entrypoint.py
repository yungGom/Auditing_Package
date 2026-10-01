"""Harness temp isolation and strict skip behavior; no product expectations changed."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("auditdesk_entrypoint", Path(__file__).parents[1] / "test_auditdesk.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)

class AuditDeskEntrypointTests(unittest.TestCase):
    def run_case(self, skipped=0, code=0):
        commands = []
        def fake_run(argv, **kwargs):
            commands.append(argv)
            if "pytest" in argv:
                report = Path(next(x.split("=", 1)[1] for x in argv if x.startswith("--junitxml=")))
                base = Path(next(x.split("=", 1)[1] for x in argv if x.startswith("--basetemp=")))
                self.assertEqual(base.parent, report.parent)
                self.assertEqual(base.name, "pytest")
                self.assertFalse(base.exists())
                report.write_text(f'<testsuites><testsuite skipped="{skipped}"/></testsuites>', encoding="utf-8")
                return SimpleNamespace(returncode=code)
            return SimpleNamespace(returncode=0)
        with patch.object(entry.subprocess, "run", side_effect=fake_run), patch.object(entry.shutil, "which", return_value="npm.CMD"), patch.object(Path, "is_dir", return_value=True):
            result = entry.main()
        self.assertEqual(commands[1], ["npm.CMD", "run", "build"])
        return result

    def test_temp_isolation(self):
        self.assertEqual(self.run_case(), 0)
    def test_skipped_required_test_still_fails(self):
        self.assertEqual(self.run_case(skipped=1), 1)
    def test_failed_test_still_fails(self):
        self.assertEqual(self.run_case(code=1), 1)

if __name__ == "__main__":
    unittest.main()
