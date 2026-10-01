# Development workflow

1. **Intake.** Open a GitHub Issue using `development_task.md` and use its number as the task identifier. Record the component, rule owner, observable examples, expected output, protected artifacts, required tests, and human decisions. Use synthetic or public data only. Update the Issue when acceptance criteria change; chat is not the durable contract.
2. **Inspect.** Read root and project instructions, code, tests, `git status`, the current branch, and relevant gates. Preserve unrelated work. State the current baseline before editing.
3. **Implement.** Reproduce a defect first. Add or adjust behavioral tests, make a small change, and record any dependency or data-boundary impact. A changed accounting tolerance or gate baseline is a separate explicit decision.
4. **Verify.** Run `python scripts/check_protected.py --base origin/main` before tests. Install dependencies from the existing manifests/lockfiles as needed. Run `python scripts/test_auditdesk.py`, `python scripts/test_dsd_footing.py`, or `python scripts/test_all.py` from the root. The strict project entrypoints return nonzero for missing input, missing tool, failed/skipped required tests or gate mismatch. Under Issue #23, test_all.py separately reports the selected Technical scope: failed/skipped/unrun Technical checks return nonzero, while real-material BLOCKED/NOT RUN remains separately incomplete even when the Technical exit is zero. Do not mark unavailable actual-material verification as passing.
5. **Review.** Give the reviewer the task contract, diff, test output, and remaining risks. Apply `review_protocol.md`. Fix blocking findings, then rerun affected and full applicable checks.
6. **Handoff.** Open a PR linked to the Issue. Include exact commands and outcomes, protected-artifact result, baseline comparison, manual gates, and open risks. The human owner decides whether the behavior is right for audit work and whether to merge or release. Close the Issue only after that decision is recorded.

### Commands represented by the entrypoints

| Scope | Actual underlying command or action |
| --- | --- |
| AuditDesk core and DART | From `auditdesk/`: `python -m pytest dsd_workbench/dsd_tool/tests dart_explorer/tests -q` |
| AuditDesk web UI | From `auditdesk/webui/`: `npm run build` (install once with `npm ci`) |
| DSD_FOOTING | For each `GATES.json` sample: from `DSD_footing/`, `python run_gates.py <temporary public PDF copy> <registered tolerance>` |

The AuditDesk README identifies browser E2E gates as manual; record them separately. A DSD_FOOTING gate pass means recorded metrics did not change, including recorded exceptions; it does not mean every accounting result is correct. If a task touches the separate AuditLink v2 under `auditdesk/backend` or `auditdesk/frontend`, run `python -m pytest -q` in `auditdesk/backend`, plus the applicable `npm run lint` and `npm run build` in `auditdesk/frontend`, and record those separately.

## Issue #23 approved gate scope

Under the [Owner Decision](https://github.com/yungGom/Auditing_Package/issues/23#issuecomment-5923919699), default `python scripts/test_all.py` executes the reproducible public/synthetic Technical Gate, bounded by `--timeout` (600 seconds per check by default), with optional UTF-8 `--report` evidence. Exit 0 applies only to the selected executed Technical scope. Real-material compatibility is separately BLOCKED: REQUIRED MATERIAL UNAVAILABLE or NOT RUN; it is not executed by this aggregate and never promoted to PASS. The existing strict `scripts/test_auditdesk.py` remains for separately authorized public-material verification. Missing/failed/skipped/unrun Technical checks or invalid evidence block the Technical Gate. Actual-material compatibility and Human Business Acceptance remain separate; no required real-material acceptance without its evidence. Future catalogue scope changes require an explicit Owner Decision and independent review. No automatic protected-check registration is claimed.
