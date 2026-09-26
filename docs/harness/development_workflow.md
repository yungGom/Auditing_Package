# Development workflow

1. **Intake.** Fill the issue template. Name the component, source of the business rule, observable examples, expected output, and what remains a human decision. Use synthetic or public data only.
2. **Inspect.** Read root and project instructions, code, tests, `git status`, the current branch, and relevant gates. Preserve unrelated work. State the current baseline before editing.
3. **Implement.** Reproduce a defect first. Add or adjust behavioral tests, make a small change, and record any dependency or data-boundary impact. A changed accounting tolerance or gate baseline is a separate explicit decision.
4. **Verify.** Install dependencies from each project's existing manifests/lockfiles as needed. Run `python scripts/test_auditdesk.py`, `python scripts/test_dsd_footing.py`, or `python scripts/test_all.py` from the root. The scripts return nonzero for a missing input, missing tool, failed test, or gate mismatch. Do not mark an unavailable run as passing.
5. **Review.** Give the reviewer the task contract, diff, test output, and remaining risks. Apply `review_protocol.md`. Fix blocking findings, then rerun affected and full applicable checks.
6. **Handoff.** Fill the PR template. Include exact commands and outcomes, baseline comparison, manual gates, and open risks. The human owner decides whether the behavior is right for audit work and whether to merge or release.

### Commands represented by the entrypoints

| Scope | Actual underlying command or action |
| --- | --- |
| AuditDesk core and DART | From `auditdesk/`: `python -m pytest dsd_workbench/dsd_tool/tests dart_explorer/tests -q` |
| AuditDesk web UI | From `auditdesk/webui/`: `npm run build` (install once with `npm ci`) |
| DSD_FOOTING | For each `GATES.json` sample: from `DSD_footing/`, `python run_gates.py <temporary public PDF copy> <registered tolerance>` |

The AuditDesk README identifies browser E2E gates as manual; record them separately. A DSD_FOOTING gate pass means recorded metrics did not change, including recorded exceptions; it does not mean every accounting result is correct. If a task touches the separate AuditLink v2 under `auditdesk/backend` or `auditdesk/frontend`, run `python -m pytest -q` in `auditdesk/backend`, plus the applicable `npm run lint` and `npm run build` in `auditdesk/frontend`, and record those separately.
