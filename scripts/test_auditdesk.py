"""Run AuditDesk's existing automated core and web UI checks."""

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "auditdesk"
WEBUI = PROJECT / "webui"


def main() -> int:
    required = [
        PROJECT / "dsd_workbench" / "dsd_tool" / "tests",
        PROJECT / "dart_explorer" / "tests",
        WEBUI / "package.json",
        WEBUI / "package-lock.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        print(f"FAIL: required AuditDesk inputs missing: {', '.join(missing)}", flush=True)
        return 1

    print("[AuditDesk] Python core and DART tests", flush=True)
    py = subprocess.run(
        [sys.executable, "-m", "pytest", "dsd_workbench/dsd_tool/tests", "dart_explorer/tests", "-q"],
        cwd=PROJECT,
        check=False,
    ).returncode

    npm = shutil.which("npm")
    if npm is None or not (WEBUI / "node_modules").is_dir():
        print("FAIL: npm or webui/node_modules missing. Run npm ci in auditdesk/webui.", flush=True)
        return 1
    print("[AuditDesk] Web UI TypeScript and build", flush=True)
    web = subprocess.run([npm, "run", "build"], cwd=WEBUI, check=False).returncode
    print(f"[AuditDesk] pytest={py}, webui build={web}", flush=True)
    return 0 if py == 0 and web == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
