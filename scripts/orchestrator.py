"""Run one GitHub Issue through the bounded Harness v1.1 workflow.

Requires authenticated ``gh`` and ``codex`` CLIs for a live run. Dry runs can
read a saved ``gh issue view --json`` response without invoking either agent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = Path(__file__).with_name("orchestrator_agent.schema.json")
PREFLIGHT_SCHEMA = Path(__file__).with_name("orchestrator_preflight.schema.json")
PREFLIGHT_SCRIPT = Path(__file__).with_name("orchestrator_preflight.py")
MAX_OUTPUT = 40_000


class AgentExecutionError(RuntimeError):
    def __init__(self, diagnostic: dict[str, Any]):
        super().__init__("Agent CLI execution failed")
        self.diagnostic = diagnostic


def command(argv: list[str], *, env: dict[str, str] | None = None,
            timeout: int = 3600, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=ROOT, env=env, text=True, encoding="utf-8",
                          errors="replace", capture_output=True, timeout=timeout,
                          input=input_text,
                          check=False)


def issue_section(body: str, title: str) -> str:
    match = re.search(rf"(?im)^##\s+{re.escape(title)}\s*$", body)
    if not match:
        return ""
    tail = body[match.end():]
    next_heading = re.search(r"(?m)^##\s+", tail)
    return tail[:next_heading.start() if next_heading else None].strip()


def get_issue(repo: str, number: int, fixture: Path | None) -> dict[str, Any]:
    if fixture:
        data = json.loads(fixture.read_text(encoding="utf-8"))
    else:
        result = command(["gh", "issue", "view", str(number), "--repo", repo,
                          "--json", "number,title,body,state,url,author,comments"])
        if result.returncode:
            raise RuntimeError("GitHub Issue fetch failed: " + result.stderr.strip())
        data = json.loads(result.stdout)
    if data.get("number") != number or not data.get("body") or data.get("state") != "OPEN":
        raise ValueError("Issue number, body, or OPEN state is invalid")
    return data


def approval_pending(issue: dict[str, Any]) -> str | None:
    body = issue["body"]
    section = issue_section(body, "Human decision required")
    if not section:
        return "Issue has no explicit Human decision required section"
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    lines = [line for line in lines if not line.startswith("Definition of done:")]
    value = "\n".join(lines)
    value = re.sub(r"(?i)^Accounting judgment or protected-artifact decision \(or `none`\):\s*",
                   "", value)
    if re.fullmatch(r"(?is)(none|not applicable|n/a)[.\s]*", value):
        return None
    # A named human decision is never inferred from an agent's text. The owner
    # updates the Issue contract after deciding, with protected edits handled
    # separately under POLICY.md.
    return section


def test_scripts(issue: dict[str, Any]) -> list[str]:
    section = issue_section(issue["body"], "Required tests")
    if not section:
        raise ValueError("Issue has no Required tests section")
    allowed = ["scripts/test_auditdesk.py", "scripts/test_dsd_footing.py",
               "scripts/test_all.py"]
    selected = [path for path in allowed if path in section.replace("\\", "/")]
    if not selected:
        raise ValueError("No supported required test entrypoint is specified")
    return selected


def changed_files() -> list[str]:
    result = command(["git", "status", "--porcelain=v1", "--untracked-files=all"])
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return [line[3:] for line in result.stdout.splitlines() if line]


def worktree_fingerprint() -> list[tuple[str, str]]:
    snapshot = []
    for name in changed_files():
        path = ROOT / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "absent"
        snapshot.append((name, digest))
    return snapshot


def protected_check(base: str) -> tuple[bool, str]:
    # A temporary index includes untracked files, which the normal worktree
    # diff in check_protected.py does not see. The real index is untouched.
    with tempfile.TemporaryDirectory(prefix="orchestrator_index_") as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        for args in (["git", "read-tree", "HEAD"], ["git", "add", "-A"]):
            result = command(args, env=env)
            if result.returncode:
                return False, result.stderr.strip()
        result = command([sys.executable, "scripts/check_protected.py", "--base",
                          base, "--staged"], env=env)
        return result.returncode == 0, (result.stdout + result.stderr).strip()


def runtime_candidates(extra: list[str] | None = None) -> list[str]:
    bundled = (Path.home() / ".cache" / "codex-runtimes" /
               "codex-primary-runtime" / "dependencies" / "python" / "python.exe")
    return list(dict.fromkeys([sys.executable, "python", "py", "python3",
                               str(bundled), *(extra or [])]))


def diagnostic_kind(stderr: str) -> str:
    """Whitelist a failure class; never copy raw CLI output into the report."""
    tail = stderr[-2000:].lower()
    if any(token in tail for token in ("access denied", "permission denied", "winerror 5")):
        return "ACCESS_DENIED"
    if any(token in tail for token in ("not found", "not recognized", "no such file")):
        return "NOT_FOUND"
    if any(token in tail for token in ("auth", "credential", "login")):
        return "AUTH_FAILURE"
    if "timed out" in tail or "timeout" in tail:
        return "TIMEOUT"
    return "OTHER_REDACTED" if stderr else "NONE"


def runtime_preflight(timeout: int, tests: list[str],
                      extra_candidates: list[str] | None = None) -> dict[str, Any]:
    """Probe inside a fresh workspace-write Codex session before Implementer.

    The helper produces capability flags from executed commands. A random nonce
    binds the structured reply to this probe; arbitrary CLI logs are discarded.
    """
    candidates = runtime_candidates(extra_candidates)
    nonce = secrets.token_hex(16)
    require_npm = any(path in tests for path in
                      ("scripts/test_auditdesk.py", "scripts/test_all.py"))
    prompt = (
        "You are a runtime capability probe. Make no persistent repository "
        "changes; the helper may create and remove only its temporary probe "
        "file. For each Python candidate in "
        "the listed order, actually run it with -B and the probe script. Do not infer "
        "success from PATH or a file existing. The probe imports pytest/openpyxl, "
        "runs python -m pytest --version and git/npm --version as applicable, and "
        "writes/reads/deletes a temporary file inside the repository. "
        "Choose the first candidate whose probe reports every required flag true. "
        "Copy the probe's nonce, executable, version, flags, and npm_version "
        "exactly into your "
        "structured JSON reply, adding the candidate and error_code=NONE. "
        "If no candidate passes but at least one probe executed, copy the first "
        "executed probe's real identity and flags; set error_code to "
        "TEMP_NOT_WRITABLE, MISSING_DEPENDENCY, or COMMAND_FAILED as appropriate. "
        "Only when no candidate can execute the probe, return empty "
        "candidate/executable/version/npm_version and all flags false, with ACCESS_DENIED, "
        "NOT_FOUND, or UNKNOWN. Do not include raw "
        "stdout, stderr, environment variables, credentials, or repository content.\n"
        f"Candidates: {json.dumps(candidates, ensure_ascii=True)}\n"
        f"Probe script: {PREFLIGHT_SCRIPT}\n"
        f"Command arguments: --nonce {nonce} --temp-base {ROOT}"
        + (" --require-npm" if require_npm else "") + "\n"
    )
    with tempfile.TemporaryDirectory(prefix="orchestrator_preflight_") as tmp:
        output = Path(tmp) / "last.json"
        argv = ["codex", "exec", "--ephemeral", "-C", str(ROOT),
                "--sandbox", "workspace-write", "--output-schema",
                str(PREFLIGHT_SCHEMA), "--output-last-message", str(output), "-"]
        try:
            result = command(argv, timeout=timeout, input_text=prompt)
        except (OSError, subprocess.TimeoutExpired) as exc:
            code = "TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired) else "NOT_FOUND"
            return {"ready": False, "error_code": code,
                    "diagnostic": {"command_class": "codex exec preflight",
                                   "exit_code": None, "stderr_tail": code}}
        diagnostic = {"command_class": "codex exec preflight",
                      "exit_code": result.returncode,
                      "stderr_tail": (diagnostic_kind(result.stderr)
                                      if result.returncode else
                                      "REDACTED" if result.stderr else "NONE")}
        if result.returncode or not output.is_file():
            return {"ready": False, "error_code": diagnostic["stderr_tail"],
                    "diagnostic": diagnostic}
        try:
            data = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"ready": False, "error_code": "INVALID_PROBE",
                    "diagnostic": diagnostic}

    safe_codes = {"NONE", "ACCESS_DENIED", "NOT_FOUND", "MISSING_DEPENDENCY",
                  "TEMP_NOT_WRITABLE", "COMMAND_FAILED", "UNKNOWN"}
    if not isinstance(data, dict):
        return {"ready": False, "error_code": "INVALID_PROBE",
                "diagnostic": diagnostic}
    candidate = data.get("candidate", "")
    executable = data.get("executable", "")
    version = data.get("version", "")
    flags = {name: data.get(name) is True
             for name in ("pytest", "openpyxl", "temp_write", "git", "npm")}
    npm_version = data.get("npm_version", "")
    valid = (data.get("nonce") == nonce and candidate in candidates and
             isinstance(executable, str) and Path(executable).is_absolute() and
             isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version) and
             data.get("error_code") in safe_codes and
             isinstance(npm_version, str) and
             (not npm_version or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", npm_version)) and
             (not require_npm or not flags["npm"] or bool(npm_version)))
    valid_failure = (data.get("nonce") == nonce and candidate == "" and
                     executable == "" and version == "" and npm_version == "" and
                     data.get("error_code") in safe_codes - {"NONE"})
    ready = bool(valid and all(flags.values()) and data["error_code"] == "NONE")
    code = ("NONE" if ready else
            data["error_code"] if valid_failure else
            "INVALID_PROBE" if not valid else
            "TEMP_NOT_WRITABLE" if not flags["temp_write"] else
            "MISSING_DEPENDENCY" if not (flags["pytest"] and flags["openpyxl"]) else
            "COMMAND_FAILED" if not (flags["git"] and flags["npm"]) else
            "INVALID_PROBE")
    return {"ready": ready, "error_code": code,
            "selected_executable": executable if ready else None,
            "probe_executable": executable if valid else None,
            "candidate": candidate if valid else None,
            "version": version if valid else None,
            "dependencies": {"pytest": flags["pytest"], "openpyxl": flags["openpyxl"]},
            "temp_write": flags["temp_write"], "commands": {
                "git": flags["git"], "npm": flags["npm"]},
            "npm_version": npm_version if valid and npm_version else None,
            "diagnostic": diagnostic}


def agent(role: str, issue: dict[str, Any], feedback: str, timeout: int,
          runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    if role == "implementer":
        sandbox = "workspace-write"
        instruction = ("Implement this Issue using AGENTS.md and governance/POLICY.md. "
                       "Never edit protected artifacts or accounting/business rules. "
                       "If one is needed, stop and return HUMAN_APPROVAL. "
                       "Do not commit, push, comment, merge, or claim tests passed. "
                       "Run Python only with the verified executable below. ")
    else:
        sandbox = "read-only"
        instruction = ("Independently review the Issue contract, git diff against HEAD, "
                       "changed files, protected check and exact test evidence. "
                       "Do not edit files or run mutating commands. Report blockers, "
                       "including FAIL, SKIP or NOT RUN required checks. ")
    prompt = (instruction + "Return the required JSON decision. "
              "Use PASS only when this role's work is complete; use BLOCKER for "
              "fixable defects and HUMAN_APPROVAL for owner decisions.\n\n"
              f"Issue #{issue['number']}: {issue['title']}\n{issue['body']}\n\n"
              f"Current evidence / reviewer feedback:\n{feedback}\n"
              f"Verified Python executable: {(runtime or {}).get('selected_executable', 'unverified')}\n"
              f"Verified Python version: {(runtime or {}).get('version', 'unverified')}\n"
              f"Verified Python command prefix: {json.dumps((runtime or {}).get('selected_executable', 'unverified'))} -B\n"
              "Use -B for Python invocations. A probe checked pytest, openpyxl, "
              "git/npm commands and repository temporary-file writes in a fresh "
              "workspace-write session. Recheck if your sandbox differs.")
    with tempfile.TemporaryDirectory(prefix="orchestrator_agent_") as tmp:
        output = Path(tmp) / "last.json"
        try:
            result = command(["codex", "exec", "--ephemeral", "-C", str(ROOT),
                              "--sandbox", sandbox, "--output-schema", str(SCHEMA),
                              "--output-last-message", str(output), "-"], timeout=timeout,
                             input_text=prompt)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AgentExecutionError({
                "command_class": f"codex exec {role}", "exit_code": None,
                "selected_runtime": (runtime or {}).get("selected_executable"),
                "stderr_tail": "TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired)
                               else "NOT_FOUND"}) from None
        diagnostic = {"command_class": f"codex exec {role}",
                      "exit_code": result.returncode,
                      "selected_runtime": (runtime or {}).get("selected_executable"),
                      "stderr_tail": (diagnostic_kind(result.stderr)
                                      if result.returncode else
                                      "REDACTED" if result.stderr else "NONE")}
        if result.returncode:
            raise AgentExecutionError(diagnostic)
        data = json.loads(output.read_text(encoding="utf-8"))
    if data.get("decision") not in {"PASS", "BLOCKER", "HUMAN_APPROVAL"}:
        raise ValueError(f"{role} returned an invalid decision")
    data["_diagnostic"] = diagnostic
    return data


def comment(repo: str, issue_number: int, report: dict[str, Any]) -> str | None:
    lines = [f"Orchestrator MVP: **{report['state']}**", report["reason"],
             f"Attempts: {report['attempts']}"]
    for step in report["evidence"]:
        # Full logs remain in the local JSON report; a comment only carries
        # command/status evidence to avoid copying arbitrary test output.
        lines.append(f"- {step['step']}: {step['status']}")
    with tempfile.TemporaryDirectory(prefix="orchestrator_comment_") as tmp:
        body = Path(tmp) / "comment.md"
        body.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = command(["gh", "issue", "comment", str(issue_number), "--repo",
                          repo, "--body-file", str(body)])
    return None if result.returncode == 0 else result.stderr.strip()


def run(args: argparse.Namespace) -> dict[str, Any]:
    issue = get_issue(args.repo, args.issue, args.issue_json)
    report: dict[str, Any] = {"issue": issue.get("url"), "state": "READY",
                              "reason": "Issue accepted", "attempts": 0, "evidence": []}
    pending = approval_pending(issue)
    if pending:
        report.update(state="HUMAN_APPROVAL", reason="Human Owner decision required: " + pending)
        return report
    tests = test_scripts(issue)
    report["evidence"].append({"step": "required tests", "status": "READY",
                                "detail": ", ".join(tests)})
    if args.dry_run:
        report["reason"] = "Dry run: ready for Implementer; no work executed"
        return report
    if changed_files():
        report.update(state="FAILED", reason="Worktree is not clean; preserve existing work")
        return report
    runtime = runtime_preflight(args.agent_timeout, tests,
                                getattr(args, "python_candidate", None))
    report["evidence"].append({"step": "runtime preflight",
                                "status": "PASS" if runtime["ready"] else "FAIL",
                                "detail": runtime})
    if not runtime["ready"]:
        report.update(state="FAILED",
                      reason="ENVIRONMENT_BLOCKER: " + runtime["error_code"])
        return report
    report["state"] = "IN_PROGRESS"
    feedback = ""
    for attempt in range(1, args.max_attempts + 1):
        report["attempts"] = attempt
        try:
            impl = agent("implementer", issue, feedback, args.agent_timeout, runtime)
        except AgentExecutionError as exc:
            report["evidence"].append({"step": f"implementer {attempt}",
                                       "status": "FAIL", "diagnostic": exc.diagnostic})
            report.update(state="FAILED", reason="Implementer CLI execution failed")
            break
        report["evidence"].append({"step": f"implementer {attempt}",
                                    "status": impl["decision"],
                                    "detail": impl["summary"] + "\n" + "\n".join(impl["findings"]),
                                    "diagnostic": impl.get("_diagnostic")})
        ok, detail = protected_check("HEAD")
        report["evidence"].append({"step": "protected check", "status": "PASS" if ok else "FAIL",
                                    "detail": detail})
        if not ok:
            report.update(state="HUMAN_APPROVAL", reason="Protected check failed; Human Owner review required")
            break
        if impl["decision"] == "HUMAN_APPROVAL":
            report.update(state="HUMAN_APPROVAL", reason=impl["summary"])
            break
        if impl["decision"] == "BLOCKER":
            feedback = impl["summary"] + "\n" + "\n".join(impl["findings"])
            continue
        failures = []
        # A fresh base avoids an inaccessible pre-existing pytest-of-user folder.
        with tempfile.TemporaryDirectory(prefix="orchestrator_tests_") as test_tmp:
            test_env = dict(os.environ, TEMP=test_tmp, TMP=test_tmp, TMPDIR=test_tmp)
            for script in tests:
                result = command([sys.executable, script], env=test_env,
                                 timeout=args.test_timeout)
                status = "PASS" if result.returncode == 0 else "FAIL"
                detail = (result.stdout + result.stderr)[-MAX_OUTPUT:]
                report["evidence"].append({"step": script, "status": status, "detail": detail})
                if result.returncode:
                    failures.append(script)
        if failures:
            feedback = "Required tests failed: " + ", ".join(failures)
            continue
        before_review = worktree_fingerprint()
        review_evidence = {"steps": report["evidence"],
                           "changed_files": [name for name, _ in before_review]}
        try:
            review = agent("reviewer", issue, json.dumps(review_evidence, ensure_ascii=False),
                           args.agent_timeout, runtime)
        except AgentExecutionError as exc:
            report["evidence"].append({"step": f"reviewer {attempt}",
                                       "status": "FAIL", "diagnostic": exc.diagnostic})
            report.update(state="FAILED", reason="Reviewer CLI execution failed")
            break
        if worktree_fingerprint() != before_review:
            report.update(state="FAILED", reason="Reviewer changed the worktree")
            break
        report["evidence"].append({"step": f"reviewer {attempt}",
                                    "status": review["decision"],
                                    "detail": review["summary"] + "\n" + "\n".join(review["findings"]),
                                    "diagnostic": review.get("_diagnostic")})
        if review["decision"] == "HUMAN_APPROVAL":
            report.update(state="HUMAN_APPROVAL", reason=review["summary"])
            break
        if review["decision"] == "BLOCKER" or review["findings"]:
            feedback = review["summary"] + "\n" + "\n".join(review["findings"])
            continue
        report.update(state="DONE", reason="Technical checks and independent review passed; business acceptance remains with Human Owner")
        break
    else:
        report.update(state="FAILED", reason=f"Retry limit reached ({args.max_attempts}); last blocker: {feedback}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue", type=int)
    parser.add_argument("--repo", default="yungGom/Auditing_Package")
    parser.add_argument("--issue-json", type=Path, help="Saved gh issue JSON for offline dry-run")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--agent-timeout", type=int, default=3600)
    parser.add_argument("--test-timeout", type=int, default=3600)
    parser.add_argument("--no-comment", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--python-candidate", action="append", default=[],
                        help="Additional Python executable candidate (repeatable)")
    args = parser.parse_args()
    if not 1 <= args.max_attempts <= 3:
        parser.error("--max-attempts must be between 1 and 3")
    if args.issue_json and not args.dry_run:
        parser.error("--issue-json is only available with --dry-run")
    try:
        report = run(args)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        report = {"issue": args.issue, "state": "FAILED", "reason": str(exc),
                  "attempts": 0, "evidence": []}
    if not args.dry_run and not args.no_comment and not args.issue_json:
        error = comment(args.repo, args.issue, report)
        if error:
            report["comment_error"] = error
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["state"] in {"READY", "DONE", "HUMAN_APPROVAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
