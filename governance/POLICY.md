# Shared AI development policy (v1.1)

This is the common governance source for Codex, Claude Code, and human contributors. Project-specific domain rules in existing `CLAUDE.md`, specs, and gate ledgers still apply. Do not weaken them to satisfy a check. If instructions conflict, stop the affected change and ask the Human Owner.

## Work contract

1. Start from a GitHub Issue. Record the problem, business rule and owner, acceptance criteria, reproduction, affected protected artifacts, required tests, and human decision. The Issue is the task source of truth; chat can clarify it but must not silently replace it.
2. Inspect relevant code, current branch, uncommitted work, existing instructions, and gate baselines. Preserve unrelated work and product behavior.
3. For a bug, first reproduce it with the smallest meaningful failing test or gate case. For a feature, add behavioral tests for its acceptance criteria. Implement the smallest change that meets the contract.
4. Fail closed on source identity, period, unit, sign, missing input, ambiguous mapping, and data export. Never convert unknown or unmatched data to zero or silently mark it verified.
5. Treat the inventory in `governance/PROTECTED_ARTIFACTS.md` as read-only. If a protected artifact or accounting rule must change, STOP before editing. Report the reason, expected impact, exact before/after, and evidence to the Human Owner. Approval is a separate decision; an Implementer does not update the baseline to turn a failure green.
6. Run the applicable project tests and full regression via `python scripts/test_all.py` for shared changes. Run `python scripts/check_protected.py --base origin/main`. A missing dependency, missing fixture, failed gate, skipped required test, or unrun check is not a Technical PASS.
7. Have a reviewer inspect the diff and evidence independently. Resolve blocking findings, rerun affected and full applicable checks, and repeat review. Return the result to the Human Owner for business acceptance. Technical results do not approve accounting treatment, merge, deployment, or release.

## Data and result reporting

- Use synthetic fixtures or explicitly public DART filings. Never place client data, credentials, client numbers, or client file paths in prompts, issues, logs, or commits.
- AuditDesk's `dsd_workbench` and DSD_FOOTING remain offline. Public OpenDART receipt belongs only to `dart_explorer` under its existing boundary.
- Report: goal/root cause; files and behavior; before/after reproduction; exact commands and PASS/FAIL/SKIP/NOT RUN counts; protected-artifact check; reviewer findings and fixes; manual checks; remaining risks; and the Human Owner decision needed. Use `docs/harness/review_protocol.md`.
