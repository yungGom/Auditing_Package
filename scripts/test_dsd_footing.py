"""Compare every registered DSD_FOOTING public sample without overwriting outputs."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "DSD_footing"


def main() -> int:
    gates = PROJECT / "GATES.json"
    runner = PROJECT / "run_gates.py"
    if not gates.is_file() or not runner.is_file():
        print("FAIL: GATES.json or run_gates.py missing", flush=True)
        return 1
    try:
        samples = json.loads(gates.read_text(encoding="utf-8"))["samples"]
        if not isinstance(samples, dict) or not samples:
            raise ValueError("no registered samples")
        for name, entry in samples.items():
            if Path(name).name != name or not name.lower().endswith(".pdf"):
                raise ValueError(f"invalid sample name: {name}")
            if not isinstance(entry["tol"], (int, float)) or not entry.get("metrics"):
                raise ValueError(f"invalid gate baseline: {name}")
            if not (PROJECT / "samples" / name).is_file():
                raise FileNotFoundError(PROJECT / "samples" / name)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: unusable registered gate input: {exc}", flush=True)
        return 1

    env = os.environ.copy()
    env.pop("GATES_UPDATE", None)
    failures = []
    with tempfile.TemporaryDirectory(prefix="dsd_footing_gates_") as tmp:
        for name, entry in samples.items():
            sample = Path(tmp) / name
            shutil.copy2(PROJECT / "samples" / name, sample)
            print(f"[DSD_FOOTING] {name}, tol={entry['tol']}", flush=True)
            code = subprocess.run(
                [sys.executable, str(runner), str(sample), str(entry["tol"])],
                cwd=PROJECT,
                env=env,
                check=False,
            ).returncode
            if code:
                failures.append((name, code))
    print(f"[DSD_FOOTING] {len(samples) - len(failures)}/{len(samples)} registered samples passed", flush=True)
    for name, code in failures:
        print(f"FAIL: {name} (exit {code})", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
