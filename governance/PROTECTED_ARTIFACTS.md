# Protected artifacts and owner decision

These paths were identified in the repository at v1.1. They are read-only to an AI Implementer. `scripts/check_protected.py` uses `governance/protected_paths.json` to block listed file changes and protected symbol value changes relative to the base branch. The inventory is intentionally conservative where a file itself is a truth record.

| Class | Actual repository paths | Reason |
| --- | --- | --- |
| Gate baselines | `DSD_footing/GATES.json`; `auditdesk/GATES.json` | Recorded PDF metrics and manual AuditDesk gate decisions |
| Public golden samples | `DSD_footing/samples/*.pdf` | Inputs for the four DSD_FOOTING snapshots |
| Approved guide truth | `auditdesk/assets/guide/guide_rules_2026.json`; `auditdesk/assets/guide/build_guide_rules.py` | Accountant-reviewed rules and source generator |
| Domain decision records | `DSD_footing/CLAUDE.md`; `auditdesk/dsd_workbench/KNOWN_VERSIONS.md`; `auditdesk/docs/REQUEST_LEDGER.md`; `auditdesk/docs/IMPL_CHECKLIST.md`; `auditdesk/docs/*SPEC*.md`; `auditdesk/docs/종합_작업계획_2026반기시즌.md`; relevant F-4b approval reports | Confirmed scope, known exceptions, approval history |
| Synthetic reference set | `auditdesk/docs/한빛정밀_검증데이터셋.md`; `auditdesk/dsd_workbench/dsd_tool/tests/{fixture,hanbit_skeleton}.py`; existing fixture directories | Documented synthetic expectations and reference inputs |
| Existing test expectations | Existing `test_*.py` under AuditDesk `dsd_workbench`, `dart_explorer`, and `backend` test directories | Prevent changing expected results to hide a regression; new tests may be added |
| Threshold and exception definitions | Selected assignments/functions in `DSD_footing/{core,refmap,statements,prose}.py` and `auditdesk/dsd_workbench/dsd_tool/{foot,mapping,guide_check,xbrl_recon}.py` | Known tolerances, scoring, skip and whitelist decisions |

There is **no tracked `ERRORS.json`** or standalone accountant-confirmed truth-set file at this baseline. Error/exception truth is distributed across the records above and code such as `guide_check.py`'s approved whitelist. If such a ledger is added later, it joins the protected inventory before agents use it. The checker also blocks conventional `GATES.json`, `ERRORS.json`, golden, baseline, truth, and known-false-positive paths wherever they appear.

On a needed change, STOP and post to the Issue: path or symbol, current value, proposed value, why, expected effect on every gate and known exception, a before/after report, and the Human Owner's explicit decision. Do not commit the protected change as an Implementer. A Human Owner can make or separately authorize the change after review.

Local Git hooks are fast feedback and can be bypassed. CI and protected-branch rules must require the `protected-artifacts` and `regression` checks plus code-owner review to make merge blocking. Until those repository settings are enabled, a successful local hook is not a merge guarantee. The checker uses the base branch's policy when available so a PR cannot edit its own manifest to permit a protected change.
