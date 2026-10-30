"""Opt in to the repository's local Git hooks (reversible with git config --unset)."""

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if not (ROOT / ".githooks" / "pre-commit").is_file():
        print("FAIL: .githooks/pre-commit missing")
        return 1
    result = subprocess.run(
        ["git", "config", "--local", "core.hooksPath", ".githooks"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode == 0:
        print("Local hooks installed. Undo: git config --local --unset core.hooksPath")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
