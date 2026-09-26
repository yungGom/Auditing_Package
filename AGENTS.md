# Auditing_Package AI development contract (v1)

This file applies to the whole repository. Read the nearest project `AGENTS.md`, existing `CLAUDE.md`, README, specs, and gates before changing code. The root `CLAUDE.md` describes AuditLink and applies to that app; use each project's own documents for its domain rules. These instructions add a common workflow and do not replace project constraints. If applicable instructions disagree, stop the affected change, report the conflict, and ask the owner to decide. Do not silently weaken a safety rule or quality gate.

## Work contract

1. Inspect the relevant code, current branch and uncommitted work. Preserve unrelated changes and existing behavior.
2. State the observable acceptance criteria, affected project, data boundary, and planned verification. Ask the domain owner when an accounting rule or acceptable exception is undefined.
3. For a bug, first reproduce it with the smallest meaningful failing test or gate case. Implement the smallest fix, then rerun the reproduction and the full applicable regression suite. For a feature, add behavioral tests for its acceptance criteria.
4. Fail closed on source identity, period, unit, sign, missing input, ambiguous mapping, and data export. Never convert unknown or unmatched data to zero or silently mark it as verified. Preserve DSD source integrity checks and offline boundaries.
5. Run `python scripts/test_all.py` for the two primary projects after a shared change; run the relevant project entrypoint for a scoped change. A skipped or unavailable test is **not** a pass. Do not rewrite baselines or gate snapshots merely to make a run pass.
6. Have a reviewer inspect the diff and evidence independently. Fix actionable findings and repeat affected tests and review until no blocking finding remains. The implementer and reviewer may be separate agents or separate review passes; no specific orchestration framework is required.
7. Return the result to a person for **business acceptance**. Technical pass does not approve accounting judgments, client use, deployment, merge, or release.

## Data and reporting

- Use synthetic fixtures or explicitly public DART filings. Never put client data, credentials, local paths to client files, or client numbers in issues, prompts, test logs, or commits.
- AuditDesk's offline `dsd_workbench` and DSD_FOOTING must not acquire network or external upload behavior. Public OpenDART receipt belongs to `dart_explorer` under its existing boundary.
- Report: root cause or goal; changed files; behavior and evidence; exact commands and pass/fail/skip counts; reviewer findings and fixes; remaining risks; decisions needed from the domain owner. Use `docs/harness/review_protocol.md`.

Start with `docs/harness/architecture.md` and `docs/harness/development_workflow.md`. For a new project, add a project `AGENTS.md` and a test entrypoint, then register it in `scripts/test_all.py` after the entrypoint is verified.
