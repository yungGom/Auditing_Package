"""Fail if a proposed diff changes protected truth, expectations, or rule values.

CI: python scripts/check_protected.py --base origin/main
Pre-commit: python scripts/check_protected.py --staged
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
from pathlib import Path
import subprocess
import sys


def git(repo: Path, *args: str, allow_missing: bool = False) -> bytes | None:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True)
    if result.returncode:
        if allow_missing:
            return None
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip() or "git failed")
    return result.stdout


def changed_paths(repo: Path, base: str, staged: bool) -> list[tuple[str, list[str]]]:
    args = ["diff", "--name-status", "-z", "-M"]
    args += ["--cached", base] if staged else [base]
    fields = (git(repo, *args) or b"").split(b"\0")
    result = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i].decode("ascii")
        i += 1
        count = 2 if status[0] in "RC" else 1
        paths = [fields[i + j].decode("utf-8") for j in range(count)]
        i += count
        result.append((status, paths))
    return result


def matches(path: str, patterns: list[str]) -> bool:
    name = path.replace("\\", "/").lower()
    return any(fnmatch.fnmatchcase(name, pattern.lower()) for pattern in patterns)


def base_content(repo: Path, base: str, path: str) -> bytes | None:
    return git(repo, "show", f"{base}:{path}", allow_missing=True)


def current_content(repo: Path, path: str, staged: bool) -> bytes | None:
    if staged:
        return git(repo, "show", f":{path}", allow_missing=True)
    file = repo / path
    return file.read_bytes() if file.is_file() else None


def symbol_map(source: bytes, symbols: list[str]) -> dict[str, str]:
    tree = ast.parse(source.decode("utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in symbols:
            found[node.name] = ast.dump(node, include_attributes=False)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in symbols:
                    found[target.id] = ast.dump(node.value, include_attributes=False)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in symbols:
                found[node.target.id] = ast.dump(node.value, include_attributes=False)
    return found


def keyword_values(source: bytes, names: list[str]) -> dict[str, list[str]]:
    tree = ast.parse(source.decode("utf-8"))
    found = {name: [] for name in names}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg in found:
                    found[keyword.arg].append(ast.dump(keyword.value, include_attributes=False))
    return found


def check(repo: Path, base: str, staged: bool) -> list[str]:
    if git(repo, "rev-parse", "--verify", base, allow_missing=True) is None:
        raise RuntimeError(f"base ref is unavailable: {base}")
    manifest_path = "governance/protected_paths.json"
    trusted = base_content(repo, base, manifest_path)
    manifest_data = trusted or current_content(repo, manifest_path, staged)
    if not manifest_data:
        raise RuntimeError("protected path manifest is missing")
    manifest = json.loads(manifest_data.decode("utf-8"))
    findings = []
    for status, paths in changed_paths(repo, base, staged):
        for path in paths:
            existed = base_content(repo, base, path) is not None
            if matches(path, manifest["exact"] + manifest["globs"]):
                findings.append(f"protected artifact changed: {path} ({status})")
            elif existed and matches(path, manifest["existing_test_globs"]):
                findings.append(f"existing test expectation changed: {path} ({status})")
            elif trusted and matches(path, manifest["self_globs"]):
                findings.append(f"enforcement control changed: {path} ({status})")
            if (path in manifest["symbols"] or path in manifest.get("call_keywords", {})) and existed:
                before = base_content(repo, base, path)
                after = current_content(repo, path, staged)
                if after is None:
                    findings.append(f"rule source removed: {path}")
                    continue
                names = manifest["symbols"].get(path, [])
                old = symbol_map(before, names)
                new = symbol_map(after, names)
                for name in names:
                    if old.get(name) != new.get(name):
                        findings.append(f"protected rule value changed: {path}:{name}")
                names = manifest.get("call_keywords", {}).get(path, [])
                old_calls = keyword_values(before, names)
                new_calls = keyword_values(after, names)
                for name in names:
                    if old_calls[name] != new_calls[name]:
                        findings.append(f"protected threshold call changed: {path}:{name}")
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args()
    try:
        findings = check(args.repo.resolve(), args.base, args.staged)
    except (OSError, RuntimeError, ValueError, KeyError, SyntaxError, UnicodeError) as exc:
        print(f"PROTECTED CHECK ERROR: {exc}", file=sys.stderr)
        return 2
    if findings:
        print("PROTECTED CHECK FAILED. Stop and report before/after to the Human Owner:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("PROTECTED CHECK PASS: no protected artifact or rule definition changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
