# Issue #9 verification and handoff

Date: 2026-09-30. Contract: [#9](https://github.com/yungGom/Auditing_Package/issues/9); prerequisites: [#11](https://github.com/yungGom/Auditing_Package/issues/11), [#12](https://github.com/yungGom/Auditing_Package/issues/12).

## Goal and delivered behavior

The missing V2 recommendation path now reads bounded current DSD ZIP and taxonomy XLSX inputs, preserves evidence, generates current structural candidates before label ranking, and separately revalidates prior/corpus evidence. It creates no approval, binding, fact or export. Missing current input cannot be replaced by prior data. Raw synthetic inputs exercise the complete local CLI path; full DTS/DRS and real-report acceptance remain outside this PARTIAL preview.

New modules: `dsd.py`, `taxonomy.py`, `recommendation.py`, `__main__.py` under `auditdesk/auditdesk/xbrl_v2`. Six V2-1 source files and two tests are included as explicitly reviewed dependencies, copied byte-identically from the existing V2 worktree (independent SHA-256 comparison: 8/8). The stateless recommendation path does not instantiate or migrate V2-1 stores. Original dirty worktrees were preserved.

## Baseline and workflow

- Product source: `b0e83b00a3a0a5defe2ee7bea93a9f601519e2c2`.
- Harness source: `6be6f791cd2e9456c24174b90777c6b1f4a88468`.
- Isolated starting merge: `713d4e5a6dad431cf71d3cef48c23e448d894ed6`.
- The proposed foundation branch at that exact starting merge is the review base. It includes pre-existing product/Harness history and is not a new approval to merge that history into main. The recommendation branch adds only the listed V2 code, tests and documentation above it. Publication is pending approval; neither foundation nor recommendation branch has been pushed.
- Parent Orchestrator managed separate Implementer agents, official checks, and a read-only independent Reviewer. The MVP CLI does not allow these `auditdesk/tests` task commands. Its enforcement was unchanged; this report does not claim automatic `scripts/orchestrator.py` DONE.

## Acceptance and independent review

Before implementation, recommendation tests failed collection because the module did not exist. After implementation, the same tests pass with additional behavioral cases; no original assertion or legacy expectation was weakened.

The prerequisite reviewer found three blockers: DSD source offsets after DART carriage-return entities, double-decoding escaped literal text, and partial taxonomy identities being skipped. Each was reproduced, fixed, and independently rechecked. Taxonomy fix evidence: 8 failed / 27 passed before, 35 passed after. Final prerequisite suites: 35 taxonomy + 22 DSD = 57 passed.

Recommendation hardening added self-contained source/resource evidence, role-indexed evaluation, explicit candidate/rejection truncation totals, prior date validation against current period start, and safe atomic CLI failures. Implementer reproduction: 3 failed / 27 passed before fixes, 33 passed after. The independent Reviewer found no remaining blocking finding and separately reproduced 10 invariants: five incompatible prior identities leave current candidates unchanged, three input/rule changes invalidate freshness, and two missing/conflicting current-source cases block candidates.

Nonblocking boundaries: `recommend()` trusts parser-produced snapshots and is not an external arbitrary snapshot validation API. The raw CLI reparses input bytes. Current evaluation budgets bound occurrence/reference work; Role lookup and label-comparison budgets should be extended before claiming large-scale production capacity.

## Commands and measured results

Commands below use the existing bundled Python plus the existing pytest dependencies and project paths, UTF-8 output, and a unique writable `--basetemp` per run. No dependencies, fixtures, baselines or skip rules were changed to turn failures green. Scoped pytest commands use `--noconftest -p no:cacheprovider -q -rfEs`.

| Check | Fresh baseline | Final implementation |
|---|---|---|
| V2 core/offline/taxonomy/DSD/recommendation/integration | Recommendation module absent | **131 passed**, 69 subtests passed, 0 failed/skipped (28.26s) |
| Core/DART, official AuditDesk entrypoint | 267 passed, 1 failed, 76 skipped | **267 passed, 1 failed, 76 skipped** (98.25s) |
| Official web UI build | PASS | PASS |
| Direct legacy Phase 3/4B/4D | 81 passed, 4 failed | **81 passed, 4 failed**, 0 skipped (20.58s) |
| Node Phase 3/4B/4D behavior | 12 passed | **12 passed**, 0 failed/skipped |
| DSD_FOOTING registered public samples | 5/5 PASS | **5/5 PASS**, unchanged metric/exception comparisons |
| Full Harness | FAIL: AuditDesk fixture gap; DSD_FOOTING PASS | **FAIL**: AuditDesk fixture gap; DSD_FOOTING PASS |
| Protected artifacts, task staged diff | PASS before task | **PASS**, including new files |
| Protected artifacts, `origin/main` | FAIL, 5 inherited paths | **FAIL**, same 5 inherited paths |

Exact project commands from the repository root:

```text
python -B -m pytest --noconftest -p no:cacheprovider --basetemp=<unique> auditdesk/tests/test_xbrl_v2_core.py auditdesk/tests/test_xbrl_v2_offline.py auditdesk/tests/test_xbrl_v2_taxonomy.py auditdesk/tests/test_xbrl_v2_dsd.py auditdesk/tests/test_xbrl_v2_recommendation.py auditdesk/tests/test_xbrl_v2_recommendation_integration.py -q -rfEs
python -B -m pytest --noconftest -p no:cacheprovider --basetemp=<unique> auditdesk/tests/test_phase3_completion.py auditdesk/tests/test_phase4b_binding.py auditdesk/tests/test_phase4d_orchestration.py -q -rfEs
python -B scripts/test_auditdesk.py
python -B scripts/test_all.py
python -B scripts/check_protected.py --staged
python -B scripts/check_protected.py --base origin/main
git diff --cached --check
```

`test_all.py` invokes the same `test_auditdesk.py` entrypoint; the standalone command was also executed for the fresh baseline. From `auditdesk/webui`: `node --test tests/phase3.test.cjs tests/phase4b.test.cjs tests/phase4d.test.cjs`.

The full core failure ID and all 76 skip entries were compared before/after and are unchanged. The four direct legacy failure IDs are also unchanged:

- `dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct`: external known-generation DSD files absent.
- `auditdesk/tests/test_phase3_completion.py::test_m19_real_parser_core_excel_and_reexecution`
- `auditdesk/tests/test_phase3_completion.py::test_m21_new_current_cli_workflow_and_guide`
- `auditdesk/tests/test_phase3_completion.py::test_m21_update_connects_existing_recommendation`
- `auditdesk/tests/test_phase3_completion.py::test_product_job_error_then_recovery_and_result_restore`

The latter four require an ignored taxonomy workbook absent from the isolated checkout. Skips include unavailable taxonomy/source fixtures and OpenDART credentials; no new skips were added. These are measured repository gaps, not waived requirements.

Initial local verification attempts encountered unavailable pytest import paths and shared temporary-directory ACL failures. They were rerun with the existing runtime and unique temporary directories. One direct legacy attempt used incorrect paths and collected no tests; the corrected run is reported above. No erroneous attempt was counted as PASS.

## Protected baseline and remaining limits

The five inherited `origin/main` differences are `DSD_footing/CLAUDE.md`, `ERRORS.json`, `GATES.json`, and the two public Chosun Refractories interim PDF samples already present in the product source. The task changes none of these. No accounting rule, threshold, expected result, exception, Golden data, or legacy implementation was modified. Full comparison failure remains visible even though the task staged comparison passes.

A read-only public-workbook probe used synthetic namespace/applicability declarations solely to inspect parser behavior. It did not establish official applicability. One duplicate concept has two lexical type prefixes; sixteen label rows lack concept identity; six parent diagnostics cascade from the unresolved duplicate. The parser refuses this ambiguous workbook. No actual company source or public workbook is included as a new fixture, and no implicit identity inheritance was added to make that file pass.

Manual real-report accuracy, official namespace/applicability confirmation, full DTS/DRS, DART editor compatibility, UI rollout and final export were **not performed** and are not claimed. No UI was changed. Business acceptance, production enablement and merge remain Human Owner decisions. No additional business choice is needed to review this bounded implementation; accepting actual reporting treatment would require separate evidence.

**Overall status: scoped implementation and independent review complete; repository Technical PASS unavailable.** This is a draft review handoff, not a release or approval of accounting treatment.

## Publication status

Automatic approval review rejected pushing the proposed foundation to the public repository because authorization for the broader inherited payload was not explicit. The push was not executed and no workaround was attempted. Comparing the starting merge against all known origin refs identifies two unpublished commits: the integration merge `713d4e5` and the existing SQLite/polling fix `b0e83b0` (8 files, 393 insertions and 34 deletions, including its historical verification report). Publishing this ancestry requires an explicit Human Owner decision separate from reviewing the new V2 files. A draft PR body is prepared locally; no PR or merge was created.
