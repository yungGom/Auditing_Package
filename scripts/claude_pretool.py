"""Claude Code fast feedback for direct writes; CI handles all edit methods."""

import json
from pathlib import Path
import subprocess
import sys

from check_protected import matches


def main() -> int:
    try:
        data = json.load(sys.stdin)
        raw = data.get("tool_input", {}).get("file_path")
        if not raw:
            return 0
        cwd = Path(data.get("cwd") or Path.cwd())
        repo = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd,
            stderr=subprocess.DEVNULL, text=True).strip()).resolve()
        target = Path(raw)
        target = (target if target.is_absolute() else cwd / target).resolve()
        path = target.relative_to(repo).as_posix()
        manifest = json.loads((repo / "governance/protected_paths.json").read_text(encoding="utf-8"))
        protected = matches(path, manifest["exact"] + manifest["globs"])
        tracked_before = subprocess.run(
            ["git", "cat-file", "-e", f"HEAD:{path}"], cwd=repo,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False).returncode == 0
        protected |= tracked_before and matches(path, manifest["existing_test_globs"])
        if protected:
            print(f"Protected artifact: {path}. Stop and report to Human Owner.", file=sys.stderr)
            return 2
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Protected hook could not check path: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
