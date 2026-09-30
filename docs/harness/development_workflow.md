# Development workflow

1. **Intake.** Open a GitHub Issue using `development_task.md` and use its number as the task identifier. Write the Korean `한눈에 보기` first so the Human Owner can understand the problem, business impact, solution direction, their decision, observable success criteria, and current status in about 30 seconds without reading Developer Details. Start with the business consequence, use short sentences, and replace technical terms with plain Korean. Keep code and workflow terms in Developer Details by default. Define only terms actually used in that Issue, below the summary. Keep the Developer Details contract complete: component, rule owner, observable examples, expected output, protected artifacts, required tests, and human decisions. Use synthetic or public data only. Update both layers when acceptance criteria change; chat is not the durable contract.
2. **Inspect.** Read root and project instructions, code, tests, `git status`, the current branch, and relevant gates. Preserve unrelated work. State the current baseline before editing.
3. **Implement.** Reproduce a defect first. Add or adjust behavioral tests, make a small change, and record any dependency or data-boundary impact. A changed accounting tolerance or gate baseline is a separate explicit decision.
4. **Verify.** Run `python scripts/check_protected.py --base origin/main` before tests. Install dependencies from the existing manifests/lockfiles as needed. Run `python scripts/test_auditdesk.py`, `python scripts/test_dsd_footing.py`, or `python scripts/test_all.py` from the root. The scripts return nonzero for a missing input, missing tool, failed test, skipped required test, or gate mismatch. Do not mark an unavailable run as passing.
5. **Review.** Give the reviewer the task contract, diff, test output, and remaining risks. Apply `review_protocol.md`. Fix blocking findings, then rerun affected and full applicable checks.
6. **Handoff.** Open a PR linked to the Issue. Put a plain-Korean Human Owner Result Summary first, explaining the change, business effect, tests, remaining problems, and requested approval. Keep exact commands and outcomes, protected-artifact result, baseline comparison, manual gates, and open risks below it. The human owner decides whether the behavior is right for audit work and whether to merge or release. Close the Issue only after that decision is recorded.

Use `report_template.md` for every intermediate or final implementation, verification, root-cause, UAT, review, and approval report. Put its six-question Korean summary first, then the exact technical evidence below Developer Details. Apply the same order to PR and Orchestrator final results. Historical reports are not rewritten; new reports and updates use this format.

### Commands represented by the entrypoints

| Scope | Actual underlying command or action |
| --- | --- |
| AuditDesk core and DART | From `auditdesk/`: `python -m pytest dsd_workbench/dsd_tool/tests dart_explorer/tests -q` |
| AuditDesk web UI | From `auditdesk/webui/`: `npm run build` (install once with `npm ci`) |
| DSD_FOOTING | For each `GATES.json` sample: from `DSD_footing/`, `python run_gates.py <temporary public PDF copy> <registered tolerance>` |

The AuditDesk README identifies browser E2E gates as manual; record them separately. A DSD_FOOTING gate pass means recorded metrics did not change, including recorded exceptions; it does not mean every accounting result is correct. If a task touches the separate AuditLink v2 under `auditdesk/backend` or `auditdesk/frontend`, run `python -m pytest -q` in `auditdesk/backend`, plus the applicable `npm run lint` and `npm run build` in `auditdesk/frontend`, and record those separately.
