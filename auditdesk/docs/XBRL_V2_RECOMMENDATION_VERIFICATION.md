# Issue #9 검증 보고서: 지금 어디까지 됐나?

## 한눈에 보기

### 1. 무엇을 만들었나?

당기 공시 문서(DSD)와 당기 XBRL 분류체계를 읽어 공시 항목 후보와 추천 이유를 보여주는 기능을 만들었습니다. 전기 자료는 참고로만 사용합니다. 전기에 썼던 항목이라도 당기 분류체계의 항목 이름, 배치 위치, 유형, 기간과 다시 맞춰 봅니다. 후보가 하나여도 사람의 승인 없이 확정하지 않습니다.

### 2. 실제로 작동하는지 확인했나?

**예. 새 기능 테스트 131개가 통과했습니다.** 시험용 DSD 파일부터 분류체계 읽기, 후보 추천, 결과 저장까지 이어지는 과정도 확인했습니다. 별도 검토자가 코드를 살펴보고 전기 자료가 잘못 승계되지 않는지 등 핵심 조건 10가지를 다시 확인했습니다. 발견된 문제 3건은 수정 후 재검증했습니다.

### 3. 기존 기능은 괜찮았나?

작업 전과 후를 비교했을 때 **새로 생긴 실패는 없었습니다.** 화면 만들기 검사와 화면 동작 테스트 12개는 통과했고, 별도 공개 PDF 검사 5개도 통과했습니다. 다만 저장소 전체 검사는 작업 전부터 실패하던 항목이 남아 여전히 **실패**입니다. 빠진 시험 자료 때문에 기존 검사 5개가 실패했고 76개는 실행되지 않았습니다. 따라서 전체 검증 통과라고 표시하지 않습니다.

### 4. 지금 바로 실제 공시에 써도 되나?

**아직 아닙니다.** 현재 구현은 엑셀 분류체계에서 확인할 수 있는 부분만 추천하는 시험 범위입니다. 실제 공개 분류체계 파일에는 같은 항목이 서로 다르게 정의된 부분과 어느 항목의 설명인지 알 수 없는 행이 있어, 해석기가 임의로 선택하지 않고 사용을 막습니다. 공식 당기 적용 여부, 실제 보고서의 추천 정확도, 최종 제출 파일의 호환성은 확인되지 않았습니다.

### 5. 보호하기로 한 기존 기준은 바뀌었나?

이번 작업은 회계 판단 기준, 정답 자료, 기존 검사 기대값을 바꾸지 않았습니다. 이번 변경만 검사하면 보호 대상 변경은 없습니다. 전체 저장소를 `main`과 비교하면 이전 작업에서 생긴 보호 자료 차이 5개가 그대로 발견됩니다. 이 차이를 이번 작업의 통과로 처리하지 않았습니다.

### 6. 지금 남은 일은 무엇인가?

기능 구현과 독립 검토를 마치고, 사용자의 명시적 승인에 따라 GitHub에 [초안 PR #13](https://github.com/yungGom/Auditing_Package/pull/13)을 열었습니다. 앞선 SQLite 수정 이력을 포함한 검토 기준 브랜치도 게시했습니다. 실제 공시에서 사용할지는 공식 분류체계와 실자료 검증 후 별도로 판단해야 합니다.

## 개발자용 상세 근거

Date: 2026-09-30. Contract: [#9](https://github.com/yungGom/Auditing_Package/issues/9); prerequisites: [#11](https://github.com/yungGom/Auditing_Package/issues/11), [#12](https://github.com/yungGom/Auditing_Package/issues/12).

## Goal and delivered behavior

The missing V2 recommendation path now reads bounded current DSD ZIP and taxonomy XLSX inputs, preserves evidence, generates current structural candidates before label ranking, and separately revalidates prior/corpus evidence. It creates no approval, binding, fact or export. Missing current input cannot be replaced by prior data. Raw synthetic inputs exercise the complete local CLI path; full DTS/DRS and real-report acceptance remain outside this PARTIAL preview.

New modules: `dsd.py`, `taxonomy.py`, `recommendation.py`, `__main__.py` under `auditdesk/auditdesk/xbrl_v2`. Six V2-1 source files and two tests are included as explicitly reviewed dependencies, copied byte-identically from the existing V2 worktree (independent SHA-256 comparison: 8/8). The stateless recommendation path does not instantiate or migrate V2-1 stores. Original dirty worktrees were preserved.

## Baseline and workflow

- Product source: `b0e83b00a3a0a5defe2ee7bea93a9f601519e2c2`.
- Harness source: `6be6f791cd2e9456c24174b90777c6b1f4a88468`.
- Isolated starting merge: `713d4e5a6dad431cf71d3cef48c23e448d894ed6`.
- The published `codex/current-first-foundation` branch at that exact starting merge is the review base. It includes pre-existing product/Harness history and is not a new approval to merge that history into main. The recommendation branch adds only the listed V2 code, tests and documentation above it.
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

The initial automatic approval review rejected publishing the foundation because authorization for the broader inherited payload was not explicit. The Human Owner subsequently authorized that exact scope. The published foundation includes the integration merge `713d4e5` and the existing SQLite/polling fix `b0e83b0` (8 files, 393 insertions and 34 deletions, including its historical verification report). The task branch is published and [draft PR #13](https://github.com/yungGom/Auditing_Package/pull/13) compares the 18 new Issue #9 files against the foundation. No merge was performed.
