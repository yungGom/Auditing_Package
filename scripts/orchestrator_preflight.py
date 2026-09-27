"""Machine-readable runtime probe run by a candidate Python inside Codex's sandbox.

Only capability flags and interpreter identity leave this process. Never print
command output, environment variables, exception text, or repository data.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def _module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except (ImportError, OSError):
        return False


def _command_available(argv: list[str]) -> bool:
    try:
        return subprocess.run(
            argv, capture_output=True, timeout=15, check=False,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def probe(nonce: str, temp_base: Path, require_npm: bool) -> dict:
    temp_write = False
    try:
        with tempfile.TemporaryDirectory(prefix="orchestrator_probe_", dir=temp_base) as tmp:
            marker = Path(tmp) / "write-check"
            marker.write_bytes(b"ok")
            temp_write = marker.read_bytes() == b"ok"
    except OSError:
        pass

    pytest = _module_available("pytest")
    openpyxl = _module_available("openpyxl")
    git = _command_available(["git", "--version"])
    npm = _command_available(["npm", "--version"]) if require_npm else True
    pytest_command = _command_available([sys.executable, "-m", "pytest", "--version"]) if pytest else False
    return {
        "nonce": nonce,
        "executable": sys.executable,
        "version": ".".join(map(str, sys.version_info[:3])),
        "pytest": pytest and pytest_command,
        "openpyxl": openpyxl,
        "temp_write": temp_write,
        "git": git,
        "npm": npm,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--temp-base", type=Path, required=True)
    parser.add_argument("--require-npm", action="store_true")
    args = parser.parse_args()
    print(json.dumps(probe(args.nonce, args.temp_base, args.require_npm), ensure_ascii=True))


if __name__ == "__main__":
    main()
