"""V2-1 offline and legacy-dependency boundary checks."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "auditdesk" / "xbrl_v2"
FORBIDDEN = (
    "requests", "httpx", "aiohttp", "urllib", "socket", "ftplib",
    "smtplib", "websockets", "fastapi", "dart_explorer",
    "auditdesk.binding", "auditdesk.golden", "auditdesk.orchestration",
)


class OfflineBoundary(unittest.TestCase):
    def test_core_imports_have_no_network_or_legacy_dependencies(self):
        files = sorted(ROOT.glob("*.py"))
        self.assertGreaterEqual(len(files), 5)
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported.append(node.module or "")
            for module in imported:
                with self.subTest(file=path.name, module=module):
                    self.assertFalse(any(
                        module == forbidden or module.startswith(forbidden + ".")
                        for forbidden in FORBIDDEN
                    ))


if __name__ == "__main__":
    unittest.main()
