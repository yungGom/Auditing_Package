# Issue #12 검증 보고서 — 당기 DSD 원문 해석

## 한눈에 보기

### 1. 이번에 무엇을 했나?
기존 공시 원문 해석기를 조사하고, 별도 작업 공간에서 필요한 보완과 검증을 마쳤습니다. 기존에 구현된 코드를 재사용했습니다.

기본 코드에는 DSD 추출·표 인식 기능이 있었습니다. 새 XBRL 원문 해석기는 이전 변경 제안에만 있었고 기본 코드에는 없었습니다. 그 해석기는 원문 위치, 병합 셀, 당기·전기 열, 빈칸·nil 보존과 안전한 입력 거절까지 구현되어 있었습니다.

### 2. 실제로 무엇이 달라졌나?
구역·주석·표·행·열·셀을 연결하고 원문 근거를 찾을 수 있게 보강했습니다. 기간 단어를 계정명에서 잘못 읽는 경우와 병합 행 제목 연결을 고쳤습니다. 잘못된 문서 선언은 거절하고, 인용 속 같은 모양의 글자는 보존합니다.

독립 검토에서 찾은 병합 열의 식별자 중복과 중첩 주석의 중복 해석도 고쳤습니다. 불확실한 단위·기간·표 제목·이어진 표의 의미는 임의로 확정하지 않습니다. 다른 동시 작업이나 보호 자료, 회계 기준, 원본 파일은 수정하지 않았습니다.

### 3. 확인 결과는 어땠나?
전용 검사 85건과 추가 세부 검사 45건이 통과했습니다. 독립 검토자는 같은 검사와 별도 행동 검사 13건을 통과시켰고 미해결 차단 의견이 없습니다. 보호 자료 검사도 통과했습니다.

기존 엄격 검사에는 통과 229건, 자료 부족 실패 1건, 건너뜀 76건이 남습니다. 전체 검사의 공개·합성 Python 225건과 화면 빌드는 통과했으나 PDF 풋팅 검사가 제한 시간을 넘겼습니다. 변경 없는 기본 코드에서도 같은 결과를 확인했습니다. 전체 검사 통과로 표시하지 않습니다. 실제 자료 확인 81건도 자료 부족으로 미완료입니다.

### 4. 아직 남은 문제는?
표준 XML 구역, 명시적으로 표시된 주석 제목, 일반 표와 병합 셀, 빈칸·빈 주석·표 밖 문단을 합성자료로 확인했습니다. 중첩 표와 잘못된 입력은 거절합니다. 주석 표시가 없거나 구역이 겹치는 경우, 이어진 표·전치 표의 의미는 미확인입니다.

실제 DSD 세대별 호환성, 대용량 성능, 회계적 수치 해석, 편집기 호환성은 확인하지 않았습니다. 숫자는 부호·쉼표·괄호를 포함한 원문 문자열로 보존하며, 단위 환산이나 기간 확정은 하지 않습니다.

상위 추천 기능에 연결하려면 새 구조 관계·근거·미확인 상태를 전달하는 연결부를 만들고, 별도로 검증된 당기 분류체계와 통합 검사해야 합니다. 이번 구현은 동시 진행 중인 분류체계 작업의 미병합 코드 없이 실행됩니다.

### 5. 내가 결정해야 할 게 있나?
제한된 원문 해석 범위와 미확인 처리 방식, 기존 검사 실패·시간 초과를 검토해 주세요. 다음 실제 공시자료 확인과 상위 추천 기능 연결의 진행 범위를 결정해야 합니다. 보호 자료나 회계 기준 변경 승인을 요청하는 내용은 없습니다.

업무 수용, 기본 코드 병합, 배포는 승인되지 않았고 수행하지 않았습니다.

### 6. 지금 상태는?
**사람 확인 필요 — Owner Review.** 전용 범위 구현·독립 검토는 마쳤으나 전체 검사·실제 자료 호환성·업무 수용 완료는 아닙니다.

## Developer Details

### 조사와 격리

- Source of Truth: [Issue #12](https://github.com/yungGom/Auditing_Package/issues/12), Request ID XBRL-003. 본문·댓글·AC·승인 범위를 확인했습니다. #9/#11/#18와 PR #13의 범위·상태·댓글도 조사했습니다.
- 현재 remote main: `6373a333414f51015f9d1068e32ec2ef7702cbe4`. local main은 `62762e5`로 뒤처져 있었고 primary checkout은 `test/auditdesk-e2e-uat` at `b0e83b0`였습니다. 기존 미커밋 자료는 stage/stash/수정하지 않았습니다. 원래 폴더의 일부 무시된 의존성 디렉터리는 접근 제한이 있어 전체 untracked inventory 확인이 제한되었으나 작업 파일은 독립 Worktree에만 작성했습니다.
- 전용 linked Worktree `work/issue12`, branch `codex/issue12-dsd-semantic`는 origin/main에서 시작했습니다. 비교용 `work/main-baseline`은 동일 main의 별도 detached Worktree이며 제품 변경이 없습니다.
- root/project AGENTS.md, POLICY/PROTECTED_ARTIFACTS, CLAUDE.md, README, DSD_PIPELINE_SPEC, 기존 GATES와 Harness review/orchestrator/report 절차를 읽었습니다. Issue의 기존 scope와 protected 기준을 유지했습니다.
- 현재 main은 Issue #23의 승인된 공개·합성 Technical Gate와 실제 자료 호환성 분리 정책을 포함합니다. 기존 Issue #12의 strict 명령도 그대로 실행했습니다. allowlist·catalog·test expected·gate threshold를 수정하지 않았습니다.

### 재사용과 구현

PR #13은 draft/open/unmerged이며 base `713d4e5`, head `ec256e52`입니다. 전체 foundation history를 이식하거나 의존하지 않았습니다. 게시된 head에서 V2-1 6개 모듈과 core/offline 2개 검사를 byte-identical로 재사용했습니다. 기존 DSD 검사도 동일하므로 independent hash 비교 대상은 총 9개입니다. `dsd.py`는 기존 bounded parser를 재사용 후 DSD 전용 문제만 고쳤습니다.

기존 `dsd_workbench/dsd_tool/scanner.py`의 표·병합 grid와 주석 분할, `zipsplice.py`의 원문 처리, 기존 extract/repack/표 인식 검사를 조사했습니다. 기존 scanner는 레거시 추출용 휴리스틱이며 이번의 안전한 XML 해석 계약을 그대로 대체하지 않으므로 수정·직접 import하지 않았습니다. 기존 원본 수정 경로와 DB를 연결하지 않았습니다.

새 `dsd_structure.py`는 기존 DsdDocument를 감싸는 독립 계약입니다. SECTION/NOTE/TABLE/ROW/COLUMN/BLOCK/UNCLASSIFIED 관계, 원문 locator, cell anchor 참조, unit/period clues와 coverage ledger를 제공합니다. `model.py`/`ports.py` 등 공통 구조는 원본과 동일합니다. taxonomy/recommendation, #11 미병합 구현, #18 변경은 포함하지 않았습니다.

원문 parser profile은 `bounded-dsd-v2`, 구조 profile은 `issue12-structure-v1`입니다. 경로 변경은 ID를 바꾸지 않습니다. 입력 내용 또는 parser profile 변경은 과거 결과를 재사용하지 못하게 합니다. locator는 디코딩된 raw_xml의 문자 오프셋이며 byte 오프셋이 아닙니다. 원문 ZIP/XML 해시는 별도 보존합니다.

### 실패 우선 검증과 독립 리뷰

- main에 parser가 없는 상태에서 기존 DSD 검사는 import collection error였고, 새 구조 계약도 구현 전 import error를 기록했습니다.
- raw behavior 보완 전 새 검사: 10 FAIL / 8 PASS. XML 선언, scope conflict, period substring, merged row label 등 실제 행동 실패를 재현했습니다.
- Reviewer B1: colspan 하나가 덮는 서로 다른 열 ID 충돌. 새 테스트에서 1 FAIL 재현 후 parent+column index를 identity에 추가했습니다.
- Reviewer B2: 중첩된 명시적 주석 구역에서 같은 heading을 의미 주석 둘로 확정. 새 테스트에서 1 FAIL 재현 후 해당 의미 해석을 UNKNOWN으로 남겼습니다. 물리 구조·원문은 보존합니다.
- N1: table.title/table_title은 최근 TITLE 문맥이며 확정 표 제목이 아닙니다. `UNKNOWN:table_title_semantics:*`와 문서를 추가했습니다.
- 후속 구현자 경계 검사에서 comment/CDATA의 선언 literal 거절 2 FAIL을 재현했습니다. 실제 초기 prolog만 검증하도록 수정했고 Reviewer가 invalid actual declarations 9개 하위 사례와 literal/multibyte/raw spans를 독립 확인했습니다.
- Reviewer `/root/issue12_reviewer`: 최종 85 PASS +45 subtests, custom13 PASS, staged protected/diff check PASS. 미해결 blocking 0. 별도 리뷰 보고서에 재현과 수정 근거를 기록했습니다.

### 실행 결과

Python 3.14, 기존 package-lock으로 npm ci 수행. 공용 pytest 임시 폴더 권한 오류가 있어 최종 strict/비교 실행은 이 작업 전용 TEMP/TMP를 사용했습니다. 제품 코드나 검사 기준을 바꾸지 않았습니다. 초기 sandbox strict 오류와 npm 설치 실패는 성공으로 바꾸지 않고 환경 시도 기록에 남겼습니다. bundled Python에는 pytest가 없어 기존 system Python을 사용했습니다.

| 검사 | 작업 결과 | 변경 없는 main 비교 |
|---|---|---|
| `python scripts/check_protected.py --base origin/main` | PASS | PASS |
| 시작 HEAD staged 보호 검사 | PASS | 해당 없음 |
| AuditDesk에서 `python -m pytest tests/test_xbrl_v2_dsd.py tests/test_xbrl_v2_dsd_structure.py tests/test_xbrl_v2_core.py tests/test_xbrl_v2_offline.py -q` | 85 PASS +45 subtests, 0 FAIL/SKIP | V2 package 없음; 신규 범위 |
| `python scripts/test_auditdesk.py` | FAIL: 229 PASS /1 FAIL /76 SKIP; Web build PASS | 같은 수치·실패 ID; Web build PASS |
| `python scripts/test_all.py --report <local-evidence>` | overall FAIL; Python225 PASS, Web PASS, DSD_FOOTING TIMEOUT 600초 | 같은 selected statuses/counts; DSD_FOOTING TIMEOUT 600초 |
| 상세 기존 core/DART `pytest -q -ra --junitxml=<local-evidence> --basetemp=<task-temp>` | 229 PASS /1 FAIL /76 SKIP, 정확한 node ID 별첨 | 기존 파일·입력 가용성 동일; strict 집계·실패 ID 비교 |
| Real-material compatibility catalog | 81 BLOCKED, 0 PASS | 81 BLOCKED, 항목별 상태 동일 |
| 독립 Reviewer | 85 PASS +45 subtests, custom13 PASS, protected PASS | 별도 합성 범위 검토 |
| 실제 DSD / DART 편집기 / GUI / #9 taxonomy-recommendation integration | NOT RUN | 통과 주장 없음 |

Strict failure: `dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct` — `_KNOWN_GENERATIONS` empty. 누락된 실제 DSD 세대 자료를 임의로 만들거나 기존 검사 기대값을 고치지 않았습니다.

Aggregate Python의 225개 항목, 81 compatibility 항목의 상태는 clean main과 동일합니다. DSD_FOOTING 시간 초과는 양쪽에서 재현되었습니다. 부분 PDF 표본의 지표 일치가 있어도 전체 registered gate PASS로 간주하지 않습니다. `TIMEOUT` 결과에 자식 정리 후 exit_code 0이 함께 기록되어도 status FAIL을 그대로 보존합니다. #18 코드는 수정하지 않았고, 타 세션 프로세스를 중단하지 않았습니다.

전체 명령은 기존 core/DART·web·PDF 범위만 수집하며 새 auditdesk/tests를 수집하지 않습니다. 따라서 최종 새 코드에는 별도의 전용·독립 검사를 적용했습니다. aggregate 실행 중 나중에 이뤄진 원문 전용 보완은 기존 aggregate 수집 파일을 변경하지 않았습니다. 마지막 소스 변경 뒤 전용 85개 검사를 다시 수행했습니다. 기존 selected 파일은 main 대비 변경 0입니다.

### 지원·한계와 #9 연결

UTF-8/EUC-KR/CP949 XML 1.0 contents.xml, SECTION-N, 명시적 주석 USERMARK B, P/TITLE, 일반 TABLE/TR/TD/TH/TE/TU, rowspan/colspan 앵커, 빈 주석·문단·셀, 표 밖 원문을 합성 ZIP으로 확인했습니다. rowspan 행 제목, merged-column ID, 반복 표의 locality, relocation/content identity, CR/entity 뒤 원문 위치도 검증했습니다.

중첩 표/잘못된 구조·선언·ZIP·경로 이탈·암호화·symlink·크기/압축률 위반은 명시적 오류입니다. 불균일 표·불명확한 주석 경계·중첩 주석 scope·이어진/전치 표·표 제목 의미는 UNKNOWN/diagnostic입니다. 일반 숫자 문단을 주석으로 임의 확정하지 않습니다. 실자료 전체지원 또는 성능 보증은 없습니다.

`result.document`를 기존 #9 계약에 전달할 수 있는 형태는 유지하지만 #9 코드를 이 브랜치에 포함하거나 통합 테스트하지 않았습니다. 새로운 구조·단서·coverage와 UNKNOWN/CONFLICT를 추천기에 전달하는 adapter를 별도 검증해야 합니다. BLOCK/COLUMN은 원문에 대한 구조 연결이므로 수치 fact로 중복 집계하면 안 됩니다. #11과 공통 인터페이스 조정이 필요하면 이 Issue에 의존관계를 기록한 뒤 Owner Decision을 받아야 합니다.

### 보호 및 인계

기존 보호 파일·fixtures·tests·GATES·thresholds·회계 기준·legacy DB·repack 변경 0. 고객 자료·정답 manifest·외부 전송 없음. 소스 bytes를 읽기만 하고 파일 추출·네트워크 호출하지 않습니다.

Issue #12 Progress/Verification Report 및 Master Dashboard Status/Current Summary/Next Action/Owner Action/Last Evidence를 결과와 연결해 갱신합니다. Status는 `Awaiting Final Approval`, Owner Action은 `Verification Review`입니다. Done/Issue close/merge/release/business acceptance 완료로 표시하지 않습니다.

Implementation commit: `62cbd13298200e8df6f5c9342e022954c2086ce1`.

### 실행 시간

| 검사 | 작업(초) | clean main(초) |
|---|---:|---:|
| auditdesk_python | 119.64 | 109.37 |
| webui_build | 26.56 | 42.56 |
| dsd_footing | 600.72 | 602.0 |

전용 검사 실행 로그: 58.52초; independent 최종 41.15초. strict 최종 208.30초, clean main strict 92.77초; 상세 strict 93.59초. 병렬 작업과 환경에 따라 소요 시간은 달랐고 시간 초과를 통과로 바꾸지 않았습니다.

### Strict FAIL / SKIP 정확한 항목

- SKIP: `dsd_workbench/dsd_tool/tests/test_attr_check.py::test_g1_three_companies`
- SKIP: `dsd_workbench/dsd_tool/tests/test_attr_check.py::test_g2_tamper_three_kinds`
- SKIP: `dsd_workbench/dsd_tool/tests/test_attr_check.py::test_g3_guide_sheet_in_v2_report`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_infer_bottom_sum`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_infer_top_subtotal_and_multilevel`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_infer_fuzzy_within_limit`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_relations_from_levels_mismatch`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_gf1_all_match`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_gf2_single_corruption`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_gf4_note_matching`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_level_override_detects_mismatch`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_foot_cli`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot.py::test_gf3_samsung_real`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot_excel.py::test_gate1_sheet_and_summary_structure`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot_excel.py::test_gate2_counts_match_foot`
- SKIP: `dsd_workbench/dsd_tool/tests/test_foot_excel.py::test_gate3_hyperlink_roundtrip_and_marks`
- SKIP: `dsd_workbench/dsd_tool/tests/test_guide_check.py::test_scaffold_guide_check_attached`
- SKIP: `dsd_workbench/dsd_tool/tests/test_hanbit.py::test_build_report`
- SKIP: `dsd_workbench/dsd_tool/tests/test_hanbit.py::test_v_points`
- SKIP: `dsd_workbench/dsd_tool/tests/test_hanbit.py::test_s1_extract_dirty`
- SKIP: `dsd_workbench/dsd_tool/tests/test_hanbit.py::test_s2_v1_positional_replace`
- SKIP: `dsd_workbench/dsd_tool/tests/test_hanbit.py::test_s3_clean_output`
- SKIP: `dsd_workbench/dsd_tool/tests/test_hanbit.py::test_s4_keep_modes_byte_identity[dirty]`
- SKIP: `dsd_workbench/dsd_tool/tests/test_hanbit.py::test_s4_keep_modes_byte_identity[clean]`
- SKIP: `dsd_workbench/dsd_tool/tests/test_note_worksheet.py::test_gate1_role_assignment`
- SKIP: `dsd_workbench/dsd_tool/tests/test_note_worksheet.py::test_gate3_routing_and_benchmark`
- SKIP: `dsd_workbench/dsd_tool/tests/test_note_worksheet.py::test_gate4_unassigned_table_warning`
- SKIP: `dsd_workbench/dsd_tool/tests/test_note_worksheet.py::test_gate2_dimension_mapping_spotcheck`
- SKIP: `dsd_workbench/dsd_tool/tests/test_pipeline.py::test_note_dedup_real_samsung`
- SKIP: `dsd_workbench/dsd_tool/tests/test_pipeline.py::test_clean_cr_real_samsung`
- SKIP: `dsd_workbench/dsd_tool/tests/test_recon.py::test_gate1_statements_all_true`
- SKIP: `dsd_workbench/dsd_tool/tests/test_recon.py::test_gate2_note_false_breakdown`
- SKIP: `dsd_workbench/dsd_tool/tests/test_recon.py::test_gate3_tamper_detection`
- SKIP: `dsd_workbench/dsd_tool/tests/test_recon.py::test_output_format`
- SKIP: `dsd_workbench/dsd_tool/tests/test_recon.py::test_verdicts_are_formulas_all_sheets`
- SKIP: `dsd_workbench/dsd_tool/tests/test_recon.py::test_summary_equals_rendered_verdicts`
- SKIP: `dsd_workbench/dsd_tool/tests/test_rollforward.py::test_g1_scaffold_fill_rate`
- SKIP: `dsd_workbench/dsd_tool/tests/test_rollforward.py::test_g2_prefill_sample_crosscheck`
- SKIP: `dsd_workbench/dsd_tool/tests/test_rollforward.py::test_g3_period_labels_rolled`
- SKIP: `dsd_workbench/dsd_tool/tests/test_rollforward.py::test_g4_update_mode`
- SKIP: `dsd_workbench/dsd_tool/tests/test_succession.py::test_gate1_succession_roundtrip`
- SKIP: `dsd_workbench/dsd_tool/tests/test_succession.py::test_gate2_period_conversion`
- SKIP: `dsd_workbench/dsd_tool/tests/test_succession.py::test_gate3_succession_worksheet`
- SKIP: `dsd_workbench/dsd_tool/tests/test_version.py::test_editver_extraction_all_real_files`
- SKIP: `dsd_workbench/dsd_tool/tests/test_version.py::test_editver_in_extract_info_and_meta_sheet`
- FAIL: `dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct`
- SKIP: `dsd_workbench/dsd_tool/tests/test_version_check.py::test_gate_known_generations_pass[NOTSET]`
- SKIP: `dsd_workbench/dsd_tool/tests/test_version_check.py::test_gate_known_generations_cli`
- SKIP: `dsd_workbench/dsd_tool/tests/test_worksheet.py::test_gate_f1_samsung_holdout`
- SKIP: `dsd_workbench/dsd_tool/tests/test_worksheet.py::test_worksheet_structure`
- SKIP: `dsd_workbench/dsd_tool/tests/test_xbrl_recon.py::test_g1_roundtrip_report`
- SKIP: `dsd_workbench/dsd_tool/tests/test_xbrl_recon.py::test_g2_tamper_detection`
- SKIP: `dart_explorer/tests/test_client.py::test_gate_live_search_and_offline_cache`
- SKIP: `dart_explorer/tests/test_corpus.py::test_gate_pilot_corpus`
- SKIP: `dart_explorer/tests/test_dimension_table.py::TestSamsung::test_consolidated_filter`
- SKIP: `dart_explorer/tests/test_dimension_table.py::TestSamsung::test_gate3_two_axis_nested`
- SKIP: `dart_explorer/tests/test_dimension_table.py::TestSamsung::test_subrole_merge`
- SKIP: `dart_explorer/tests/test_dimension_table_d2b.py::test_gate_samsung_sheet_naming`
- SKIP: `dart_explorer/tests/test_dimension_table_d2b.py::test_gate_samsung_annual_pl_duration_no_suffix`
- SKIP: `dart_explorer/tests/test_dimension_table_d2c.py::test_g2_sample_matches_distribution_xlsx`
- SKIP: `dart_explorer/tests/test_dimension_table_d2c.py::test_extension_marked_not_blank`
- SKIP: `dart_explorer/tests/test_dimension_table_d2c.py::test_fill_rate_line_and_summary`
- SKIP: `dart_explorer/tests/test_document_structure.py::test_unwrap_document`
- SKIP: `dart_explorer/tests/test_document_structure.py::test_extract_and_note_dedup_noop`
- SKIP: `dart_explorer/tests/test_document_structure.py::test_wrapped_roundtrip_byte_identity`
- SKIP: `dart_explorer/tests/test_document_structure.py::test_contamination_is_dartdb_artifact`
- SKIP: `dart_explorer/tests/test_taxonomy.py::test_gate_samsung_extensions`
- SKIP: `dart_explorer/tests/test_taxonomy_diff.py::test_detect_version`
- SKIP: `dart_explorer/tests/test_taxonomy_diff.py::test_parse_concepts_ko_label_not_english`
- SKIP: `dart_explorer/tests/test_taxonomy_diff.py::test_gate1_taxdiff_expected_counts`
- SKIP: `dart_explorer/tests/test_taxonomy_diff.py::test_gate2_taxcheck_deprecation_and_replacement`
- SKIP: `dart_explorer/tests/test_taxonomy_diff.py::test_gate3_promotion_detection`
- SKIP: `dart_explorer/tests/test_taxonomy_diff.py::test_taxcheck_integrates_promotions`
- SKIP: `dart_explorer/tests/test_taxonomy_diff.py::test_taxdiff_cli`
- SKIP: `dart_explorer/tests/test_xbrl.py::test_gate_live_pipeline_and_offline_rerun`
- SKIP: `dart_explorer/tests/test_xbrl.py::test_gate_rows_match_legacy_tool`
- SKIP: `dart_explorer/tests/test_xbrl.py::test_gate_identity_with_manual_download`

### 재사용 SHA-256

| 파일 | SHA-256 |
|---|---|
| `auditdesk/auditdesk/xbrl_v2/__init__.py` | `188fe642c1b53f63a94ce1b0d237c9b307148f728018d6bd9a2af19e4c2b4b3c` |
| `auditdesk/auditdesk/xbrl_v2/model.py` | `b5ab8681c438f083fa6dc6d58f1d3f9f8f06bbe089d54cc81470e33f9b120fae` |
| `auditdesk/auditdesk/xbrl_v2/ports.py` | `77291790411eb9e44b12ae0b964a74845daed38efa473ae538c5db029b57bcfc` |
| `auditdesk/auditdesk/xbrl_v2/provenance.py` | `f55611c6f77ed4bf3f9b6626e88d679097c85b5ecb2b3ca25d3df9f53e730699` |
| `auditdesk/auditdesk/xbrl_v2/rules.py` | `204bb5f5835b41f33de6218b2930f32f9a76c883461d4f35e6442cbfb8d3c66c` |
| `auditdesk/auditdesk/xbrl_v2/storage.py` | `4886309e0c0958d59c8ce0490a0ba06af46a9c1b2aa04db406ee120bbb90bd12` |
| `auditdesk/tests/test_xbrl_v2_core.py` | `8928d2036713d41981fe030bc643c48ead932976b1c9ee0e36b3194d48dda39f` |
| `auditdesk/tests/test_xbrl_v2_offline.py` | `12bdff9ffcfa17315c0707cb2da4e8ffb8000bf3f41890e4c055d0a4b944ec1d` |
| `auditdesk/tests/test_xbrl_v2_dsd.py` | `15948c37f8cd16f9349a76d1afd0ca7f7c78ae13aa931b95c5b0da2abbf12ac0` |
