"""Aggregate primary project test entrypoints; return failure if any fails."""

from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = {
    "auditdesk": ROOT / "scripts" / "test_auditdesk.py",
    "dsd_footing": ROOT / "scripts" / "test_dsd_footing.py",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=["all", *ENTRYPOINTS], default="all")
    args = parser.parse_args()
    selected = list(ENTRYPOINTS) if args.project == "all" else [args.project]
    results = {}
    for name in selected:
        script = ENTRYPOINTS[name]
        if not script.is_file():
            print(f"FAIL: missing entrypoint {script}", flush=True)
            results[name] = 1
            continue
        print(f"\n=== {name} ===", flush=True)
        results[name] = subprocess.run([sys.executable, str(script)], cwd=ROOT, check=False).returncode
    print("\nHarness result: " + ", ".join(f"{name}={'PASS' if code == 0 else 'FAIL'}" for name, code in results.items()), flush=True)
    return 0 if results and all(code == 0 for code in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
