# One-Issue Orchestrator MVP

`scripts/orchestrator.py` runs one open GitHub Issue through Harness v1.1. It uses
the existing Python gate scripts and two separate `codex exec` sessions. The
Implementer gets a workspace-write sandbox; the Reviewer gets a read-only
sandbox and sees the Issue, diff, and test evidence. Neither session merges or
changes GitHub state. The orchestrator can post concise status evidence to the
Issue when `gh` is authenticated.

## Requirements and commands

- Start from a **clean branch containing PR #4** with `gh`, `codex`, and Python
  available. Authenticate `gh` and `codex` first. Install each project's
  declared test dependencies. The Issue must be OPEN and contain `Required
  tests` and `Human decision required` sections.
- Preview: `python scripts/orchestrator.py 5 --dry-run`
- Run one ready Issue: `python scripts/orchestrator.py NUMBER --report ../orchestrator-report.json`
- Keep GitHub unchanged while testing: add `--no-comment`.
- Offline preview from `gh issue view NUMBER --json number,title,body,state,url,author,comments`
  output: `python scripts/orchestrator.py NUMBER --issue-json issue.json --dry-run`.

The script runs only allowlisted `scripts/test_auditdesk.py`,
`scripts/test_dsd_footing.py`, and `scripts/test_all.py` named in the Issue. It
never executes a command supplied by the Issue. The protected check stages a
snapshot in a temporary Git index, including untracked files, and leaves the
real index alone. Its comparison base is the starting `HEAD`, so PR #4's
governance files are trusted and the new Implementer changes are checked.

## States and stops

| State | Meaning |
| --- | --- |
| READY | Intake valid; dry-run stops here before any agent or test. |
| IN_PROGRESS | Implementer, checks, tests, or Reviewer running. |
| HUMAN_APPROVAL | Issue names a pending owner decision, an agent requests one, or protected check fails. No further agent/test runs. |
| DONE | Required scripts returned zero and a separate read-only Reviewer returned PASS. Human business acceptance is still pending. |
| FAILED | Invalid input, unavailable CLI, failed command, dirty worktree, or blocker remains after two attempts. |

A named Human Owner decision in the Issue stops intake even in dry-run. The
owner must update the Issue contract after deciding. Protected artifacts and
accounting rules remain read-only to the Implementer; the Human Owner handles
any such change separately. A failed or skipped required check cannot produce
DONE. Review blockers and ordinary test failures can prompt one rework; the
attempt limit is configurable from 1 to 3. Agent and test timeouts also stop
the run as FAILED. The report shows exact status and local test output. Issue
comments include status names only, because raw test logs may contain paths or
data unsuitable for GitHub.

Issue #5 currently stops at HUMAN_APPROVAL before Implementer launch because
the public fixture source and handling decision remains with the Human Owner.
The current PR #4 regression remains red; this script does not reinterpret that
failure or any skip as a pass. No automatic PR creation, merge, parallel queue,
model routing, or business approval is included.
