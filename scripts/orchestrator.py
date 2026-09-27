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
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = Path(__file__).with_name("orchestrator_agent.schema.json")
MAX_OUTPUT = 40_000


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


def agent(role: str, issue: dict[str, Any], feedback: str, timeout: int) -> dict[str, Any]:
    if role == "implementer":
        sandbox = "workspace-write"
        instruction = ("Implement this Issue using AGENTS.md and governance/POLICY.md. "
                       "Never edit protected artifacts or accounting/business rules. "
                       "If one is needed, stop and return HUMAN_APPROVAL. "
                       "Do not commit, push, comment, merge, or claim tests passed. ")
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
              f"Current evidence / reviewer feedback:\n{feedback}")
    with tempfile.TemporaryDirectory(prefix="orchestrator_agent_") as tmp:
        output = Path(tmp) / "last.json"
        result = command(["codex", "exec", "--ephemeral", "-C", str(ROOT),
                          "--sandbox", sandbox, "--output-schema", str(SCHEMA),
                          "--output-last-message", str(output), "-"], timeout=timeout,
                         input_text=prompt)
        if result.returncode:
            raise RuntimeError(f"{role} failed ({result.returncode}): " +
                               (result.stderr or result.stdout)[-MAX_OUTPUT:])
        data = json.loads(output.read_text(encoding="utf-8"))
    if data.get("decision") not in {"PASS", "BLOCKER", "HUMAN_APPROVAL"}:
        raise ValueError(f"{role} returned an invalid decision")
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
    report["state"] = "IN_PROGRESS"
    feedback = ""
    for attempt in range(1, args.max_attempts + 1):
        report["attempts"] = attempt
        impl = agent("implementer", issue, feedback, args.agent_timeout)
        report["evidence"].append({"step": f"implementer {attempt}",
                                    "status": impl["decision"],
                                    "detail": impl["summary"] + "\n" + "\n".join(impl["findings"])})
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
        for script in tests:
            result = command([sys.executable, script], timeout=args.test_timeout)
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
        review = agent("reviewer", issue, json.dumps(review_evidence, ensure_ascii=False),
                       args.agent_timeout)
        if worktree_fingerprint() != before_review:
            report.update(state="FAILED", reason="Reviewer changed the worktree")
            break
        report["evidence"].append({"step": f"reviewer {attempt}",
                                    "status": review["decision"],
                                    "detail": review["summary"] + "\n" + "\n".join(review["findings"])})
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
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["state"] in {"READY", "DONE", "HUMAN_APPROVAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
