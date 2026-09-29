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
REVIEWER_SCHEMA = Path(__file__).with_name("orchestrator_reviewer.schema.json")
PREFLIGHT_SCHEMA = Path(__file__).with_name("orchestrator_preflight.schema.json")
PREFLIGHT_SCRIPT = Path(__file__).with_name("orchestrator_preflight.py")
MAX_OUTPUT = 40_000


class AgentExecutionError(RuntimeError):
    def __init__(self, diagnostic: dict[str, Any]):
        super().__init__("Agent CLI execution failed")
        self.diagnostic = diagnostic


class VerificationEnvironmentError(OSError):
    """An official check could not start or complete in the parent runner."""

    def __init__(self, code: str, path: str, completed: list[dict[str, Any]],
                 exit_code: int | None = None):
        super().__init__(code)
        self.code = code
        self.path = path
        self.completed = completed
        self.exit_code = exit_code


def verification_diagnostic(exc: BaseException) -> dict[str, Any]:
    """Keep only bounded command and status evidence, never raw test output."""
    if isinstance(exc, VerificationEnvironmentError):
        return {"code": exc.code, "command_class": exc.path,
                "exit_code": exc.exit_code, "completed_checks": exc.completed}
    return {"code": "TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired)
            else "COMMAND_UNAVAILABLE", "command_class": "official check",
            "exit_code": None, "completed_checks": []}


REVIEWER_SEVERITIES = {"blocking", "nonblocking", "known_gap",
                       "question", "informational"}
REWORK_VERDICTS = {"BLOCKER", "BLOCKING", "REQUEST_CHANGES"}


def reviewer_findings(review: dict[str, Any]) -> list[dict[str, str]]:
    """Normalize typed findings and legacy strings without using text as a retry signal."""
    items = review.get("findings", [])
    if not isinstance(items, list):
        raise ValueError("Reviewer findings must be an array")
    normalized = []
    for item in items:
        if isinstance(item, str):
            # Old Reviewer responses had no severity. Their explicit verdict
            # remains authoritative unless the string has an explicit severity
            # prefix. Keep the migration visible in evidence.
            explicit = re.match(
                r"^\s*\[?(blocking|nonblocking|known_gap|question|informational)\]?\s*:\s*(.+)$",
                item, re.I | re.S)
            severity = (explicit.group(1).lower() if explicit else
                        "blocking" if review["decision"] in REWORK_VERDICTS
                        else "nonblocking")
            normalized.append({
                "severity": severity,
                "summary": explicit.group(2).strip() if explicit else item,
                "evidence": "Legacy severity prefix" if explicit else
                "Legacy untyped finding; severity inferred from reviewer verdict"})
        elif (isinstance(item, dict) and item.get("severity") in REVIEWER_SEVERITIES
              and isinstance(item.get("summary"), str) and item["summary"].strip()
              and isinstance(item.get("evidence"), str) and item["evidence"].strip()):
            normalized.append({name: item[name] for name in
                               ("severity", "summary", "evidence")})
        else:
            raise ValueError("Reviewer finding is missing severity, summary or evidence")
    return normalized


def reviewer_feedback(summary: str, findings: list[dict[str, str]]) -> str:
    return summary + "\n" + "\n".join(
        f"[{item['severity']}] {item['summary']}: {item['evidence']}" for item in findings)


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


def verification_preflight(tests: list[str]) -> dict[str, Any]:
    """Verify the parent runner when the Implementer sandbox has no usable runtime."""
    from orchestrator_preflight import probe

    require_npm = any(path in tests for path in
                      ("scripts/test_auditdesk.py", "scripts/test_all.py"))
    data = probe(secrets.token_hex(16), ROOT, require_npm)
    ready = all(data[name] is True for name in
                ("pytest", "openpyxl", "temp_write", "git", "npm"))
    return {"ready": ready,
            "selected_executable": data["executable"] if ready else None,
            "version": data["version"],
            "dependencies": {name: data[name] for name in ("pytest", "openpyxl")},
            "temp_write": data["temp_write"],
            "commands": {name: data[name] for name in ("git", "npm")},
            "npm_version": data["npm_version"] or None,
            "sandbox_verified": False,
            "error_code": "NONE" if ready else "MISSING_VERIFICATION_CAPABILITY"}


def agent(role: str, issue: dict[str, Any], feedback: str, timeout: int,
          runtime: dict[str, Any] | None = None, scoped: bool = False) -> dict[str, Any]:
    if role == "implementer":
        sandbox = "workspace-write"
        instruction = ("Implement this Issue using AGENTS.md and governance/POLICY.md. "
                       "Never edit protected artifacts or accounting/business rules. "
                       "If one is needed, stop and return HUMAN_APPROVAL. "
                       "Do not commit, push, comment, merge, or claim tests passed. "
                       "Run Python only with the verified executable below when it works "
                       "in your sandbox. The Orchestrator owns protected checks, task "
                       "required checks, repository regressions and final test evidence. "
                       "Run only focused development tests when useful; a repository-wide "
                       "Harness or Web UI build is not a prerequisite for your PASS. "
                       "If a sandbox-only command cannot run, report "
                       "IMPLEMENTER_ENVIRONMENT as a warning with the implementation "
                       "status. Do not change product behavior, expected results, baselines "
                       "or protected artifacts to work around that environment. ")
    else:
        sandbox = "read-only"
        instruction = ("Independently review the Issue contract, git diff against HEAD, "
                       "changed files, protected check and exact test evidence. "
                       "Do not edit files or run mutating commands. Report blockers, "
                       "including FAIL, SKIP or NOT RUN required checks. "
                       "Give every finding a severity, summary and evidence. "
                       "Use blocking only for an actionable task defect; use known_gap "
                       "for unchanged repository failures or skips, and nonblocking, "
                       "question or informational for observations that do not prevent "
                       "task completion. A PASS verdict must have zero blocking findings. "
                       "Use BLOCKING or REQUEST_CHANGES for fixable blocking findings. ")
    verdict_instruction = (
        "Use PASS only when implementation is complete; use BLOCKER for fixable "
        "defects and HUMAN_APPROVAL for owner decisions. "
        "PASS may carry an IMPLEMENTER_ENVIRONMENT warning. "
        if role == "implementer" else
        "Use PASS only when task review is complete with zero blocking findings; "
        "use BLOCKING or REQUEST_CHANGES for fixable defects and HUMAN_APPROVAL "
        "for owner decisions. PASS must have null blocker_class. ")
    prompt = (instruction + "Return the required JSON decision. "
              + verdict_instruction + "\n\n"
              f"Issue #{issue['number']}: {issue['title']}\n{issue['body']}\n\n"
              f"Current evidence / reviewer feedback:\n{feedback}\n"
              f"Verified Python executable: {(runtime or {}).get('selected_executable', 'unverified')}\n"
              f"Verified Python version: {(runtime or {}).get('version', 'unverified')}\n"
              f"Implementer sandbox runtime verified: {(runtime or {}).get('sandbox_verified', True)}\n"
              f"Verified Python command prefix: {json.dumps((runtime or {}).get('selected_executable', 'unverified'))} -B\n"
              "Use -B for Python invocations. A probe checked pytest, openpyxl, "
              "git/npm commands and repository temporary-file writes in a fresh "
              "workspace-write session. Recheck if your sandbox differs."
              + ("\nScoped task: classify BLOCKER with blocker_class as IMPLEMENTATION, "
                 "IMPLEMENTER_ENVIRONMENT, EXISTING_BASELINE, or HUMAN_DECISION. "
                 "Only the Orchestrator may classify VERIFICATION_ENVIRONMENT. Do not spend a "
                 "retry on an existing measured baseline. Reviewer: assess the task diff "
                 "and acceptance criteria even if the repository remains red; PASS means "
                 "task implementation approved, never repository Technical PASS. "
                 "Keep existing FAIL/SKIP/UNAVAILABLE visible." if scoped else ""))
    with tempfile.TemporaryDirectory(prefix="orchestrator_agent_") as tmp:
        output = Path(tmp) / "last.json"
        try:
            result = command(["codex", "exec", "--ephemeral", "-C", str(ROOT),
                              "--sandbox", sandbox, "--output-schema",
                              str(REVIEWER_SCHEMA if role == "reviewer" else SCHEMA),
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
    allowed_decisions = ({"PASS", "BLOCKER", "HUMAN_APPROVAL"}
                         if role == "implementer" else
                         {"PASS", "BLOCKER", "BLOCKING", "REQUEST_CHANGES",
                          "HUMAN_APPROVAL"})
    if data.get("decision") not in allowed_decisions:
        raise ValueError(f"{role} returned an invalid decision")
    if data.get("blocker_class") is not None and data["blocker_class"] not in {
            "IMPLEMENTATION", "ENVIRONMENT", "IMPLEMENTER_ENVIRONMENT",
            "VERIFICATION_ENVIRONMENT", "EXISTING_BASELINE", "HUMAN_DECISION"}:
        raise ValueError(f"{role} returned an invalid blocker class")
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


def _scoped_checks(paths: list[str], runtime: dict[str, Any], timeout: int,
                   *, task: bool) -> list[dict[str, Any]]:
    """Run checked-in tests with the verified runtime and a private temp base."""
    from orchestrator_results import summarize

    summaries = []
    with tempfile.TemporaryDirectory(prefix="orchestrator_scoped_") as tmp:
        env = dict(os.environ, TEMP=tmp, TMP=tmp, TMPDIR=tmp,
                   PYTEST_ADDOPTS="-rfEs -p no:cacheprovider")
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, (str(ROOT / "auditdesk"), env.get("PYTHONPATH", ""))))
        for index, path in enumerate(paths):
            if task:
                if not (ROOT / path).is_file():
                    raise ValueError(f"Task test is missing: {path}")
                argv = [runtime["selected_executable"], "-B", "-m", "pytest",
                        path, "-q", "-p", "no:cacheprovider",
                        "--basetemp", str(Path(tmp) / f"task_{index}")]
            else:
                argv = [runtime["selected_executable"], "-B", path]
            try:
                result = command(argv, env=env, timeout=timeout)
            except (OSError, subprocess.TimeoutExpired) as exc:
                code = "TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired) else "COMMAND_UNAVAILABLE"
                raise VerificationEnvironmentError(code, path, summaries) from exc
            if result.returncode:
                output = (result.stdout + result.stderr).lower()
                if (re.search(r"(?m)^[^\r\n]*python(?:\.exe)?: no module named pytest\s*$",
                              output) or
                        re.search(r"(?m)^fail: npm or webui/node_modules missing\.",
                                  output)):
                    raise VerificationEnvironmentError(
                        "MISSING_DEPENDENCY", path, summaries, result.returncode)
                # Recognize a launcher error, not an assertion that happens to
                # mention esbuild or access denial in its test output.
                if ("[auditdesk] web ui typescript and build" in output and
                        (("traceback (most recent call last)" in output and
                          "permissionerror:" in output and
                          "subprocess.run" in output) or
                         re.search(r"(?m)^error: spawn .*esbuild.*\b(?:eacces|eperm)\b", output))):
                    raise VerificationEnvironmentError(
                        "ACCESS_DENIED", path, summaries, result.returncode)
            summaries.append(summarize(path, result))
    return summaries


def _run_scoped(args: argparse.Namespace, issue: dict[str, Any],
                regression: list[str], task: list[str]) -> dict[str, Any]:
    """Task completion with measured baseline gaps, never a Technical PASS."""
    from orchestrator_results import compare, known_gate_ids

    declared = known_gate_ids(issue["body"])
    report: dict[str, Any] = {
        "issue": issue.get("url"), "state": "READY", "reason": "Issue accepted",
        "attempts": 0, "evidence": [],
        "task_required_checks": [{"path": path, "status": "READY"} for path in task],
        "regression_checks": [{"path": path, "status": "READY"} for path in regression],
        "known_unavailable_gates": sorted(declared), "task_result": "NOT_RUN",
        "repository_result": "NOT_RUN", "known_gaps": [], "new_regressions": [],
        "unclassified_baseline": [],
        "implementer_environment_warnings": [],
        "reviewer_result": "NOT_RUN", "reviewer_findings": [],
        "human_business_acceptance": "PENDING",
        "blocker_class": None,
    }
    if args.dry_run:
        report["reason"] = "Dry run: scoped task and regression checks identified"
        return report
    if changed_files():
        report.update(state="FAILED", reason="Worktree is not clean; preserve existing work",
                      blocker_class="ENVIRONMENT")
        return report
    runtime = runtime_preflight(args.agent_timeout, regression,
                                getattr(args, "python_candidate", None))
    report["evidence"].append({"step": "runtime preflight",
                               "status": "PASS" if runtime["ready"] else "WARNING",
                               "detail": runtime})
    if not runtime["ready"]:
        report["implementer_environment_warnings"].append(
            {"phase": "sandbox runtime preflight", "code": runtime["error_code"]})
        runtime = verification_preflight(regression)
        report["evidence"].append({"step": "verification runtime preflight",
                                   "status": "PASS" if runtime["ready"] else "FAIL",
                                   "detail": runtime})
        if not runtime["ready"]:
            report.update(state="FAILED",
                          reason="ENVIRONMENT_BLOCKER: verification runtime unavailable",
                          blocker_class="VERIFICATION_ENVIRONMENT")
            return report
    try:
        baseline = _scoped_checks(regression, runtime, args.test_timeout, task=False)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        report["evidence"].append({"step": "regression baseline", "status": "NOT_RUN",
                                   "diagnostic": verification_diagnostic(exc)})
        report.update(state="FAILED",
                      reason=f"ENVIRONMENT_BLOCKER: baseline checks could not run ({type(exc).__name__})",
                      blocker_class="VERIFICATION_ENVIRONMENT")
        return report
    report["evidence"].append({"step": "regression baseline", "status": "RECORDED",
                               "detail": baseline})
    report["state"] = "IN_PROGRESS"
    feedback = ("Review the Issue's task checks independently of the measured "
                "repository baseline. Existing declared failures/skips are not "
                "implementation defects; do not change protected tests or fixtures. "
                "Do not call the repository Technical PASS.\n"
                + json.dumps({"baseline": baseline,
                              "declared_known_gates": sorted(declared)}, ensure_ascii=True))
    for attempt in range(1, args.max_attempts + 1):
        report["attempts"] = attempt
        try:
            impl = agent("implementer", issue, feedback, args.agent_timeout, runtime,
                         scoped=True)
        except AgentExecutionError as exc:
            report["evidence"].append({"step": f"implementer {attempt}", "status": "FAIL",
                                       "diagnostic": exc.diagnostic})
            report.update(state="FAILED", reason="Implementer CLI execution failed",
                          blocker_class="IMPLEMENTER_ENVIRONMENT")
            break
        category = impl.get("blocker_class") or "IMPLEMENTATION"
        sandbox_warning = category in {"IMPLEMENTER_ENVIRONMENT", "ENVIRONMENT",
                                       "VERIFICATION_ENVIRONMENT"}
        if sandbox_warning:
            report["implementer_environment_warnings"].append(
                {"attempt": attempt, "code": "IMPLEMENTER_ENVIRONMENT",
                 "summary": impl["summary"]})
        report["evidence"].append({"step": f"implementer {attempt}",
                                   "status": "WARNING" if sandbox_warning else impl["decision"],
                                   "decision": impl["decision"],
                                   "blocker_class": "IMPLEMENTER_ENVIRONMENT"
                                   if sandbox_warning else category
                                   if impl["decision"] != "PASS" else None,
                                   "detail": impl["summary"] + "\n" + "\n".join(impl["findings"]),
                                   "diagnostic": impl.get("_diagnostic")})
        ok, detail = protected_check("HEAD")
        report["evidence"].append({"step": "protected check",
                                   "status": "PASS" if ok else "FAIL", "detail": detail})
        if not ok or impl["decision"] == "HUMAN_APPROVAL" or category == "HUMAN_DECISION":
            report.update(state="HUMAN_APPROVAL", blocker_class="HUMAN_DECISION",
                          reason="Protected or Human Owner decision required"
                          if not ok else impl["summary"])
            break
        if impl["decision"] == "BLOCKER":
            if category == "IMPLEMENTATION":
                feedback = impl["summary"] + "\n" + "\n".join(impl["findings"])
                report["blocker_class"] = "IMPLEMENTATION"
                continue
            # Existing baseline and Implementer-only environment warnings do
            # not consume a retry. Official checks decide whether work passes.
        try:
            task_results = _scoped_checks(task, runtime, args.test_timeout, task=True)
        except ValueError as exc:
            report.update(state="FAILED", reason=str(exc), blocker_class="IMPLEMENTATION")
            break
        except (OSError, subprocess.TimeoutExpired) as exc:
            report["evidence"].append({"step": f"task checks {attempt}",
                                       "status": "NOT_RUN",
                                       "diagnostic": verification_diagnostic(exc)})
            report.update(state="FAILED",
                          reason=f"ENVIRONMENT_BLOCKER: official checks could not run ({type(exc).__name__})",
                          blocker_class="VERIFICATION_ENVIRONMENT")
            break
        report["task_required_checks"] = task_results
        task_ok = all(x["status"] == "PASS" and x["passed"] > 0 and not x["skipped"]
                      for x in task_results)
        report["task_result"] = "PASS" if task_ok else "FAIL"
        report["evidence"].append({"step": f"task checks {attempt}",
                                   "status": report["task_result"], "detail": task_results})
        try:
            current = _scoped_checks(regression, runtime, args.test_timeout, task=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            report["evidence"].append({"step": f"regression checks {attempt}",
                                       "status": "NOT_RUN",
                                       "diagnostic": verification_diagnostic(exc)})
            report.update(state="FAILED",
                          reason=f"ENVIRONMENT_BLOCKER: official regression could not run ({type(exc).__name__})",
                          blocker_class="VERIFICATION_ENVIRONMENT")
            break
        report["regression_checks"] = current
        gaps, regressions, unclassified = compare(baseline, current, declared)
        report["known_gaps"] = gaps
        report["new_regressions"] = regressions
        report["unclassified_baseline"] = unclassified
        report["repository_result"] = ("PASS" if all(x["status"] == "PASS" and
                                                      not x["skipped"] for x in current)
                                       else "FAIL")
        report["evidence"].append({"step": f"regression checks {attempt}",
                                   "status": report["repository_result"],
                                   "detail": {"results": current, "known_gaps": gaps,
                                              "comparison_status": ("NEW_REGRESSIONS" if regressions
                                                                    else "NO_NEW_REGRESSIONS"),
                                              "new_regressions": regressions,
                                              "unclassified_baseline": unclassified}})
        if not task_ok or regressions:
            feedback = json.dumps({"task_checks": task_results,
                                   "new_regressions": regressions}, ensure_ascii=True)
            report["blocker_class"] = "IMPLEMENTATION"
            continue
        before_review = worktree_fingerprint()
        review_evidence = {"task_required_checks": task_results,
                           "protected_check": {"status": "PASS", "detail": detail},
                           "regression_baseline": baseline,
                           "regression_checks": current, "known_gaps": gaps,
                           "new_regressions": [],
                           "unclassified_baseline": unclassified,
                           "implementer_environment_warnings":
                           report["implementer_environment_warnings"],
                           "changed_files": [name for name, _ in before_review]}
        try:
            review = agent("reviewer", issue,
                           json.dumps(review_evidence, ensure_ascii=True),
                           args.agent_timeout, runtime, scoped=True)
        except AgentExecutionError as exc:
            report["evidence"].append({"step": f"reviewer {attempt}",
                                       "status": "FAIL", "diagnostic": exc.diagnostic})
            report.update(state="FAILED", blocker_class="VERIFICATION_ENVIRONMENT",
                          reason="Reviewer CLI execution failed")
            break
        if worktree_fingerprint() != before_review:
            report.update(state="FAILED", blocker_class="VERIFICATION_ENVIRONMENT",
                          reason="Reviewer changed the worktree")
            break
        try:
            findings = reviewer_findings(review)
        except ValueError as exc:
            report.update(state="FAILED", reviewer_result="INVALID",
                          blocker_class="VERIFICATION_ENVIRONMENT",
                          reason=f"Reviewer response invalid: {exc}")
            break
        report["reviewer_result"] = review["decision"]
        report["reviewer_findings"] = findings
        report["evidence"].append({"step": f"reviewer {attempt}",
                                   "status": review["decision"],
                                    "detail": reviewer_feedback(review["summary"], findings),
                                    "findings": findings,
                                   "diagnostic": review.get("_diagnostic")})
        if review["decision"] == "PASS" and (review.get("blocker_class") is not None or
                any(item["severity"] == "blocking" for item in findings)):
            report.update(state="FAILED", reviewer_result="INVALID",
                          blocker_class="VERIFICATION_ENVIRONMENT",
                          reason="Reviewer response contradictory: PASS with blocking signal")
            break
        if review["decision"] == "HUMAN_APPROVAL":
            report.update(state="HUMAN_APPROVAL", blocker_class="HUMAN_DECISION",
                          reason=review["summary"])
            break
        if review["decision"] in REWORK_VERDICTS:
            category = review.get("blocker_class") or "IMPLEMENTATION"
            if category == "HUMAN_DECISION":
                report.update(state="HUMAN_APPROVAL", blocker_class="HUMAN_DECISION",
                              reason=review["summary"])
                break
            if category in {"ENVIRONMENT", "VERIFICATION_ENVIRONMENT",
                            "IMPLEMENTER_ENVIRONMENT"}:
                report.update(state="FAILED", blocker_class="VERIFICATION_ENVIRONMENT",
                              reason=review["summary"])
                break
            if category == "EXISTING_BASELINE":
                report.update(state="FAILED", blocker_class="EXISTING_BASELINE",
                              reason="Reviewer did not approve task implementation")
                break
            feedback = reviewer_feedback(review["summary"], findings)
            report["blocker_class"] = "IMPLEMENTATION"
            continue
        if unclassified:
            incomplete = any("result unavailable" in item or
                             "identity unavailable" in item or
                             "identities unavailable" in item for item in unclassified)
            report.update(state="FAILED",
                          blocker_class="VERIFICATION_ENVIRONMENT" if incomplete else "EXISTING_BASELINE",
                          reason=("Baseline evidence is incomplete" if incomplete else
                                  "Baseline gaps could not be matched to declared known gates"))
        elif report["repository_result"] == "PASS":
            report.update(state="DONE", blocker_class=None,
                          reason="Task, regression checks and independent review passed")
        else:
            report.update(state="TASK_PASS_WITH_KNOWN_GAPS",
                          blocker_class="EXISTING_BASELINE",
                          reason="Task checks and independent review passed; repository gaps remain")
        break
    else:
        report.update(state="FAILED", blocker_class="IMPLEMENTATION",
                      reason=f"Retry limit reached ({args.max_attempts}); last blocker: {feedback}")
    return report


def run(args: argparse.Namespace) -> dict[str, Any]:
    issue = get_issue(args.repo, args.issue, args.issue_json)
    report: dict[str, Any] = {"issue": issue.get("url"), "state": "READY",
                              "reason": "Issue accepted", "attempts": 0, "evidence": []}
    pending = approval_pending(issue)
    if pending:
        report.update(state="HUMAN_APPROVAL", reason="Human Owner decision required: " + pending)
        return report
    tests = test_scripts(issue)
    from orchestrator_results import task_paths
    task = task_paths(issue["body"])
    if task:
        return _run_scoped(args, issue, tests, task)
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
        try:
            findings = reviewer_findings(review)
        except ValueError as exc:
            report.update(state="FAILED", reviewer_result="INVALID",
                          reason=f"Reviewer response invalid: {exc}")
            break
        report["reviewer_result"] = review["decision"]
        report["reviewer_findings"] = findings
        report["evidence"].append({"step": f"reviewer {attempt}",
                                    "status": review["decision"],
                                    "detail": reviewer_feedback(review["summary"], findings),
                                    "findings": findings,
                                    "diagnostic": review.get("_diagnostic")})
        if review["decision"] == "PASS" and (review.get("blocker_class") is not None or
                any(item["severity"] == "blocking" for item in findings)):
            report.update(state="FAILED", reviewer_result="INVALID",
                          reason="Reviewer response contradictory: PASS with blocking signal")
            break
        if review["decision"] == "HUMAN_APPROVAL":
            report.update(state="HUMAN_APPROVAL", reason=review["summary"])
            break
        if review["decision"] in REWORK_VERDICTS:
            feedback = reviewer_feedback(review["summary"], findings)
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
    if report["state"] == "TASK_PASS_WITH_KNOWN_GAPS":
        return 2  # task accepted; repository is not a Technical PASS
    return 0 if report["state"] in {"READY", "DONE", "HUMAN_APPROVAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
