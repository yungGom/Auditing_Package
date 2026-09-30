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
| TASK_PASS_WITH_KNOWN_GAPS | Issue-declared task checks and independent review passed, with no new regression against a measured pre-change baseline. Declared repository failures or skips remain; this is not Technical PASS and exits with code 2. Human business acceptance is pending. |
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

Issue #5's fixture-policy decision is recorded in its Issue contract.
Its Pilot subsequently stopped at a separate protected-fixture decision.
The current PR #4 regression remains red; this script does not reinterpret that
failure or any skip as a pass. No automatic PR creation, merge, parallel queue,
model routing, or business approval is included.

## Runtime preflight and diagnostics

Before launching an Implementer, the orchestrator starts a separate
codex exec session with the same workspace-write sandbox and checkout. It tries
the parent interpreter, python, py, python3, the Codex bundled interpreter,
and repeatable --python-candidate entries in that order. Each candidate must
execute scripts/orchestrator_preflight.py inside the sandbox. The helper
imports pytest and openpyxl, runs pytest and Git version commands (plus npm
when AuditDesk tests require it), and writes/reads/deletes a temporary file
inside the repository. PATH presence alone never counts as success.

A failed sandbox probe in the original unscoped flow returns FAILED with an
ENVIRONMENT_BLOCKER reason, attempts zero, and no Implementer call. Scoped task
completion uses the separate parent probe described below. The report keeps
only capability flags, the selected executable/version, command class, exit
code, and a whitelisted stderr failure category. Raw CLI output and environment
variables are not retained. A fresh temporary directory is used for parent
test scripts to avoid a stale pytest shared temp folder.

The UTF-8 JSON report remains human-readable. Console JSON uses ASCII escapes
so CP949 terminals and redirected pipes can print every status without changing
the exit code. A JSON parser recovers the same strings. This change does not
reinterpret failed or skipped regressions as a pass.

## Scoped task completion for known repository gaps

An Issue may add a `## Task required checks` section listing backtick-quoted
repository `test_*.py` paths. Only checked-in tests under the AuditDesk test
directories or `scripts/tests` are accepted; Issue-supplied shell commands are
never run. Its existing `## Required tests` section remains the repository
regression set. For the existing Issue #5 contract, the fallback reads test
paths only from the acceptance-criterion line beginning `Add only`; it ignores
the generator path and does not execute any Issue-supplied command. The optional
`## Known unavailable gates` section lists backtick-quoted pytest node IDs for
pre-existing failures. If absent, the `## Reproduction` section provides that
declaration. Issue #5 thus scopes the synthetic G2 test while retaining the
AuditDesk and full Harness scripts as regression checks and the unavailable
real-file smoke node as a known gate.

The scoped run records the regression result before implementation, then
runs the Implementer, protected check, task checks, and the same regression
scripts again. Pytest reports failed, error, and skipped node summaries with
`-rfEs`; the comparison requires the expected AuditDesk and Harness component
results in both runs. It compares failing node IDs, skips, and component status.

The Implementer owns investigation and edits and may run focused development
tests. The Orchestrator owns the protected check, required task tests, repository
regressions, baseline comparison, and official test evidence. A repository-wide
Harness or Web UI build inside the workspace-write Implementer sandbox is not
a prerequisite for task review. If such a sandbox command is denied, the
Implementer reports `IMPLEMENTER_ENVIRONMENT`; the scoped run retains it as a
warning and continues to the Orchestrator checks without using another retry.
Legacy agent `ENVIRONMENT` replies are treated the same way in this scoped
flow. If the sandbox runtime probe fails, the parent runner is probed separately
before attempting official checks. An unusable parent runtime or an official
check that cannot execute stops as `VERIFICATION_ENVIRONMENT` / FAILED with an
`ENVIRONMENT_BLOCKER` reason. An official test that executes and fails remains
a task failure or repository regression, never an environment warning.

New failures, increased or newly located skips, or a component changing from
PASS to FAIL are implementation regressions and can trigger rework. Unchanged
failures without a declared identity or comparable skip evidence are reported
as unclassified baseline gaps; they cannot yield partial completion or spend
an Implementer retry. The read-only Reviewer still examines the task diff,
Issue acceptance criteria, and check evidence before a final decision.

The Reviewer returns a verdict separately from structured findings. Each
finding has `severity` (`blocking`, `nonblocking`, `known_gap`, `question`, or
`informational`), `summary`, and `evidence`. A PASS verdict with only
nonblocking findings does not consume a retry; known gaps remain visible in
the report and never become repository Technical PASS. `BLOCKING` and
`REQUEST_CHANGES` (plus legacy `BLOCKER`) request rework only for an actionable
implementation defect. PASS with an explicit blocking finding is a protocol
contradiction and fails closed without rework. For older string-only findings,
an explicit `[severity]:` prefix is honored; otherwise PASS strings migrate
to nonblocking and blocking-verdict strings migrate to blocking, with the
inference recorded in finding evidence.

The local report separates `task_required_checks`, `regression_checks`,
`known_unavailable_gates`, `known_gaps`, `new_regressions`,
`unclassified_baseline`, `implementer_environment_warnings`,
`task_result`, `repository_result`, `reviewer_findings`,
`reviewer_result`, and `human_business_acceptance`. A fully green scoped run
still ends as DONE. A scoped run with only declared, unchanged baseline gaps
ends as TASK_PASS_WITH_KNOWN_GAPS. The old Issue contract without a task-check
section retains the original DONE/HUMAN_APPROVAL/FAILED behavior.

Every final JSON report starts with a `human_owner_summary` field containing
the six-question Korean `## 한눈에 보기` section. The existing machine-readable
state, evidence, task/repository results, Reviewer findings, and decision
fields remain at the top level as Developer Details for compatibility. Issue
status comments use the same summary, followed by `## Developer Details` and
bounded status evidence. They omit freeform reason and agent text; the full
reason remains in the local JSON. The summary never converts FAIL, SKIP,
NOT RUN, or an observed known gap into a pass. It uses only structured state
and check outcomes, not arbitrary Issue or agent prose, so it cannot supply
specific business change descriptions or approval options. A separate reviewed
Human Approval request must state those options in its own top summary before
the owner decides. See `report_template.md` for other Harness reports,
including UAT and Human Approval requests.
