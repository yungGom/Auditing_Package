# AuditDesk Phase 3 Feature Completion Report

검증일: 2026-09-15. 브랜치: `feat/auditdesk-feature-completion`.
기준 커밋: `45e036b05fea9e75f51e9892e6d01621813a1797`.
범위: M-18~M-22. M-23 작성 지원, M-24 이후 문서화/제품 정렬, 추천 알고리즘 변경은 제외한다.
이 보고서는 Phase 3 자체 검증 기록이며 기존 감사 보고서는 수정하지 않는다.

**최종 확정: M-18~M-22 PASS. 전체 Python 448 passed / 0 failed / 0 skipped / 0 errors. UI 16 passed, TypeScript 및 production build PASS. commit/push하지 않았다.**

## 검증 기준

기존 `mapping_sheet`, `attr_check`, `guide_check`, `rollforward`, `xbrl_recon`의 입력/결과 계약과 기존 게이트 테스트를 먼저 확인했다.
제품 연결 전 신규 Python 통합 8개가 실패했다. M-18/M-19는 404, F-2는 가이드 시트 없음, CLI는 인자 진입점 없음, V-1 잘못된 target은 422 계약 없음이었다.
최초 기본 Temp 폴더 권한 오류는 결함 재현으로 세지 않고, 전용 `.pytest_cache/phase3-red-temp-01`에서 다시 실행했다.
UI 연결 전 2개 테스트가 실패했다: current 값이 전송되지 않음, M-1 입력/실행 경로 없음.
추가로 손상 Excel과 갱신 추천 연결의 실패 2개를 확인한 후 연결층만 수정했다.
전기 context가 전혀 없는 경우 코어의 구체적 설명이 일반 오류로 가려지는 실패도 추가 재현한 뒤, 해당 오류만 422 및 재실행 안내로 변환했다.

기존 Phase 1/2 테스트 파일과 기대값은 수정하지 않았다. 신규 테스트에서 확인된 오류 필드명은 기존 `error_detail` 계약에 맞췄다. V-2 UI는 실제 코어의 `summary` 아래 집계를 읽도록 테스트를 강화한 뒤 수정했다.
전체 고유 node ID **448개**를 기준으로 집계하며 반복 회귀 실행을 합산하지 않는다. 장시간 단일 실행과 중간 회귀 실행은 최종 집계에서 제외했다. 최종 구성은 taxonomy 7개, note worksheet 6개, worksheet 2개, 나머지 433개의 서로 겹치지 않는 그룹이다. 나머지 그룹은 용어 수정과 추가 current/prior 통합 테스트를 반영해 다시 실행했다. Windows 명령행 길이 제한 때문에 시작되지 않은 최초 그룹 실행은 테스트 결과로 세지 않고, pytest 인자 파일로 대체했다. 최종 JUnit의 건수·테스트 이름·실행 순서를 선택한 node ID 목록과 전수 대조한다.
신규 비동기 복구 테스트의 성공 입력은 일반 Excel 대신 실제 extract 산출물로 수정했다. 일반 Excel의 `_MAP` 부재는 제품이 올바르게 거부한 입력 오류였으며, 복구 기준을 낮추지 않았다.

## M-18 — M-1 대사 조서 자동 조립

- **최초 요구:** 원문 Excel과 XBRL 공시화면 Excel을 기존 pairs 구조대로 조립하여 사용자가 M-1 조서를 받는다.
- **기존 코어 상태:** `build_mapping_workbook`에 좌우 블록 복사, 값 대조, 단위 환산, 미대응 시트, 총괄표 생성 로직과 기존 테스트가 있다. 해당 로직은 수정하지 않았다.
- **제품에서 사용 불가능했던 이유:** 입력 준비/검증 및 실행 라우터와 UI가 없었다.
- **변경 파일:** `auditdesk/completion.py`, `auditdesk/routers/studio.py`, `webui/src/Session.tsx`, 두 Phase 3 테스트 파일.
- **사용자 진입점:** 세션 → 검증 → XBRL 대사 → `제출파일 속성 검증 · 대사 조서` 펼침.
- **사용자 workflow:** 세션에서 DSD 추출 → 우측 공시화면 Excel 경로 입력 → 확인한 pairs JSON 입력 → `대사 조서 생성` → 기존 job 진행/오류 확인 → 출력 경로와 `대사 조서 Excel 열기`로 결과 확인. 실패 후 입력을 수정해 같은 화면에서 다시 실행할 수 있다.
- **입력 계약:** 좌측은 현재 세션의 추출 Excel이다. 예: `[{"left":"별도BS","right":"BS","name":"BS","basis":"확인한 짝 근거"}]`. 실제 시트명으로 바꿔야 한다. 미대응은 한쪽을 `null`로 지정한다. 빈 pairs, 양쪽 미지정, 없는 시트, 중복/잘못된 조서 시트명, 손상 Excel은 명확한 오류다.
- **추가 regression/integration:** 실제 Excel API 생성·반복 실행 보존, 잘못된 pairs 3종, 손상 Excel, UI 입력→실행→결과, JSON 오류 수정 및 중복 실행 방지.
- **수정 전 결과:** FAIL — API 404, UI 실행 경로 없음.
- **수정 후 결과:** 실제 조서와 총괄표 생성, 반복 실행은 UUID별 새 파일을 사용한다. 전체 검증 최종 집계는 아래에 기록한다.
- **Phase 1/2 회귀:** 별도 전체 회귀 실행에서 기존 94개 Python 회귀와 UI 13개 통과.
- **남은 위험:** pairs의 업무 적합성은 사용자가 확인한다. 자동 매칭을 추가하지 않았다. 기존 코어의 복사 범위/판정 의미는 그대로다.
- **사용자 확인이 필요한 설계사항:** 이번 Phase는 직접 확인한 pairs를 JSON으로 입력하는 최소 UI다. 일반 사용자용 시트 짝 편집기나 새로운 매칭 로직은 만들지 않았다. 별도 승인 때문에 현재 실행을 막지는 않는다.

## M-19 — V-2 제출파일 속성 검증

- **최초 요구:** 제출 직전 기간, unit, decimals, 주석명을 기존 코어 의미로 검증하고 Excel 산출물을 제공한다.
- **기존 코어 상태:** `attr_check`가 속성 TRUE/FALSE/판정 불가, 비교 쌍·주석명 결과와 Excel을 만든다. 표준 속성은 `LabelResolver`, 확장 속성은 `TaxonomyPackage.ext_attrs`, 팩트는 `XbrlInstance`에서 읽을 수 있다.
- **제품에서 사용 불가능했던 이유:** 기존 파서와 검증 코어를 조립하는 제품 경로가 없었다.
- **변경 파일:** `auditdesk/completion.py`, `auditdesk/routers/studio.py`, `webui/src/Session.tsx`, 두 Phase 3 테스트 파일.
- **사용자 진입점:** 세션 → 검증 → XBRL 대사 → 동일 펼침 영역의 `속성 검증 실행`.
- **사용자 workflow:** 세션 DSD 추출 → 위쪽 제출용 XBRL 패키지 경로 입력 → V-2 실행 → job 진행/오류 → 기간/unit/주석명별 FALSE·판정 불가 수 확인 → 출력 경로 및 `속성 검증 Excel 열기`. 수정 후 재실행 가능하다.
- **검증 범위 표시:** V-1 본문 값 대사와 별도의 속성 검사라고 화면에 명시했다. `target` 선택은 V-1에만 적용하며 V-2는 코어의 제출파일 전체 속성 검증 계약을 따른다.
- **추가 regression/integration:** 누락 입력 422, 실제 XBRL/XML 파서→확장 속성→코어→Excel, 정상 instant→변조 duration 검출, 반복 파일 분리, 비동기 오류/복구/조회, 실제 summary 계약 UI 집계.
- **수정 전 결과:** FAIL — API/UI 없음.
- **수정 후 결과:** 실제 확장 monetary 팩트의 period/unit 정상과 변조 periodType 위반을 구분하고 미대응 주석명을 표시한다.
- **Phase 1/2 회귀:** 기존 94개 Python 회귀와 UI 13개 통과.
- **남은 위험:** 배포 택소노미 Excel 및 제출파일 자산이 필요하다. 원천 속성이 없으면 코어의 판정 불가를 유지한다. API가 있다는 이유만으로 완료 처리하지 않고 사용자 실행·Excel 확인 경로까지 연결했다.
- **사용자 확인이 필요한 설계사항:** V-2의 전체 제출파일 범위와 V-1 current/prior 범위를 분리했다. 별도 검증 결과를 합쳐 종합 승인 판정을 새로 만들지 않았다.

## M-20 — F-4b-lite 가이드 체크 자동 부착

- **최초 요구:** F-2 worksheet와 F-3b rollforward의 실제 Excel 산출에 `[가이드 체크]`를 자동 부착한다.
- **기존 코어 상태:** `attach_guide_check`와 활성 규칙/기계 판정 4종이 있으며, 입력이 없는 기계 항목은 `판단필요`다. 판정 로직/규칙 파일은 수정하지 않았다.
- **제품에서 사용 불가능했던 이유:** 해당 함수가 테스트에서만 후처리로 호출됐다.
- **변경 파일:** `dsd_workbench/dsd_tool/worksheet.py`, `dsd_workbench/dsd_tool/rollforward.py`, `auditdesk/routers/studio.py`, Phase 3 Python 테스트.
- **사용자 진입점:** 기존 Studio 작성 worksheet 생성 또는 공식 F-3b CLI. 별도의 수동 부착 명령은 필요 없다.
- **사용자 workflow:** 기존 입력으로 산출 실행 → 자동 가이드 부착 → 동일 Excel의 `가이드 체크` 시트 확인. worksheet의 기존 화면 재독 경로에도 시트가 포함된다. 가이드 생성 오류는 완료로 숨기지 않는다.
- **입력 부족 처리:** 원문에서 기존 `collect_note_titles`로 주석 적용 범위를 전달한다. 스캐폴드의 임시 표를 완성된 제출파일 검증 입력인 것처럼 추정하지 않는다. 제공하지 못한 기계 검증 입력은 기존 코어의 `판단필요`로 표시한다.
- **추가 regression/integration:** 실제 DSD→worksheet 가이드 시트/판단필요, CLI 신규·current 갱신 산출의 가이드 시트 존재.
- **수정 전 결과:** FAIL — 실제 F-2 산출에 시트 없음.
- **수정 후 결과:** F-2와 F-3b 양쪽에 자동 부착. worksheet 결과 및 CLI 완료 요약에 가이드 상태 전달.
- **Phase 1/2 회귀:** 기존 94개 Python 회귀와 UI 13개 통과.
- **남은 위험:** 기계 검증 입력이 아직 없는 준비 자료를 정상 제출파일로 인증하지 않는다. 체크리스트의 판단필요 항목은 사용자 검토 대상이다.
- **사용자 확인이 필요한 설계사항:** 자동 부착은 기존 검증 체크리스트 연결에 한정한다. M-23 가이드 기반 작성 지원/권고 생성은 포함하지 않는다.

## M-21 — F-3b rollforward 및 current 갱신

- **최초 요구:** ① 전기 반기 DSD, ② 기말 XBRL 팩트·승계 자산, ③ 기말 DSD로 작성 준비 자료를 만들고 당기 DSD 수령 후 갱신한다.
- **기존 코어 상태:** `rollforward`는 기말 팩트 프리필, 기말 DSD 폴백, 반기 흐름값, 기간 롤포워드, 신규/변경 감지를 구현했다. 신규 계정 추천 콜백은 기존 `MappingCorpus/suggest`에 연결한다.
- **제품에서 사용 불가능했던 이유:** 입력 조립과 공식 CLI/UI가 없고 테스트가 직접 호출했다.
- **변경 파일:** `auditdesk/__main__.py`, `auditdesk/completion.py`, 가이드 부착용 `dsd_workbench/dsd_tool/rollforward.py`, Phase 3 Python 테스트.
- **사용자 진입점:** AuditDesk 디렉터리에서 `python -m auditdesk rollforward --help`.
- **사용자 workflow:** 아래 명령에 실제 경로 3종과 새 출력 경로 입력 → 콘솔 진행/오류 → 완료 경로와 프리필·가이드 요약 → Excel 확인. 당기 DSD가 오면 `--current`와 별도 `--out`으로 재실행한다.

```powershell
python -m auditdesk rollforward --half "C:\자료\전기반기.dsd" --package "C:\자료\기말XBRL" --year-end "C:\자료\전기기말.dsd" --out "C:\자료\당기준비.xlsx"
python -m auditdesk rollforward --half "C:\자료\전기반기.dsd" --package "C:\자료\기말XBRL" --year-end "C:\자료\전기기말.dsd" --current "C:\자료\당기.dsd" --out "C:\자료\당기갱신.xlsx"
```

- **입력/출력 보호:** DSD는 임시 디렉터리에서 extract한다. 기존 입력/출력 파일을 덮어쓰지 않는다. 승계 JSON이 없으면 별도 임시 위치에 기존 exporter로 준비한다. 기존 웹 서버 실행 `python -m auditdesk --port ...`는 유지한다.
- **추가 regression/integration:** help 진입, 실제 DSD 신규→current 갱신→Excel, 기존 출력 덮어쓰기 거부, 신규 계정 콜백의 기존 추천기 연결.
- **수정 전 결과:** FAIL — CLI 진입 없음; 연결 중 추천 콜백 누락도 추가 테스트로 확인 후 수정.
- **수정 후 결과:** 사용자 명령으로 두 모드 실행 가능, 가이드 시트와 콘솔 완료 경로 제공.
- **Phase 1/2 회귀:** 기존 94개 Python 회귀와 UI 13개 통과.
- **남은 위험:** 입력 자료의 회사/기간/연결·별도 일치는 사용자가 확인해야 한다. 기존 코어의 미매칭/수동 확인 및 신규 계정 판단 의미를 유지한다.
- **사용자 확인이 필요한 설계사항:** 다중 입력과 갱신 옵션을 명확히 받고 기존 Studio 화면의 구조 변경을 피하기 위해 허용된 CLI를 공식 진입점으로 선택했다. 향후 별도 GUI가 필요하더라도 이번 Phase에는 추가하지 않았다.

## M-22 — V-1 current/prior 선택

- **최초 요구:** 기존 API/core의 `target=prior`를 UI에서 선택할 수 있어야 한다.
- **기존 코어 상태:** current/prior 선별, `target_ends`, `skipped_sheets` 결과가 있다. 해당 선별 알고리즘은 수정하지 않았다.
- **제품에서 사용 불가능했던 이유:** UI가 target을 전달하지 않아 항상 기본 current였다.
- **변경 파일:** `webui/src/Session.tsx`, 잘못된 target 입력 검증용 `auditdesk/routers/studio.py`, 두 Phase 3 테스트 파일.
- **사용자 진입점:** 세션 → 검증 → XBRL 대사의 `당기/current` 또는 `전기/prior` 선택.
- **사용자 workflow:** 자료 경로 입력 → context 선택 → 실행/재실행 → 실행 결과 context·비교 기간·제외 시트 확인 → 기존 Excel 다운로드. 선택만 바꾼 경우 이전 결과임을 표시한다.
- **추가 regression/integration:** current 기본 전송, prior 선택 전송, 비교 기간 부재/제외 PL 표시, 잘못된 target 422, 전기 context 부재의 구체적 오류. 실제 XBRL 팩트로 current=2025-12-31, prior instant=2024-12-31/duration 없음 및 PL·CF 제외를 확인했다. 기존 session 소속 결과/미판정 표시 테스트 유지.
- **수정 전 결과:** FAIL — current도 명시적으로 전송되지 않았고 prior 선택 불가.
- **수정 후 결과:** current/prior 전환과 범위 표시가 사용자 화면에서 작동한다.
- **Phase 1/2 회귀:** 기존 94개 Python 회귀와 UI 13개 통과.
- **남은 위험:** 제출파일에 비교표시 자체가 없으면 선택만으로 생성할 수 없다. 기존 코어가 제외한 시트를 명시적으로 표시한다.
- **사용자 확인이 필요한 설계사항:** prior는 전기 DSD를 당기 제출파일의 전기 context와 대조하는 용도다. 기본 current는 유지한다.

## 최종 검증 및 Git 범위

신규 Python 테스트는 `tests/test_phase3_completion.py`에 있고, UI 테스트는 `webui/tests/phase3.test.cjs`에 있다.

| 항목 | Python regression/integration 함수 | 건수 |
|---|---|---:|
| M-18 | `test_m18_mapping_product_entry_and_repeat`, `test_m18_invalid_assembly_inputs_are_actionable`(3종), `test_m18_corrupt_excel_is_input_error` | 5 |
| M-19 | `test_m19_missing_input_is_actionable`, `test_m19_real_parser_core_excel_and_reexecution`, `test_product_job_error_then_recovery_and_result_restore` | 3 |
| M-20 | `test_m20_worksheet_attaches_guide_without_inventing_pass` (rollforward 부착은 아래 CLI 테스트에서도 확인) | 1 |
| M-21 | `test_m21_cli_entry_is_discoverable`, `test_m21_new_current_cli_workflow_and_guide`, `test_m21_update_connects_existing_recommendation` | 3 |
| M-22 | `test_m22_invalid_target_is_rejected`, `test_m22_no_prior_context_has_actionable_product_error`, `test_m22_actual_current_prior_result_scope` | 3 |

기존 인접 게이트는 `test_m1.py`, `test_attr_check.py`, `test_guide_check.py`, `test_rollforward.py`, `test_v1b.py`, `test_xbrl_recon.py`, `test_worksheet.py`, `test_note_worksheet.py`를 전체 suite에 포함한다.

전체 Python 최종 결과: **448 passed / 0 failed / 0 skipped / 0 errors**. 수집 448개와 결과 448개가 정확히 일치하며 누락과 중복 합산은 0개다. 최종 소스 8개(제품 6개+테스트 2개)의 검증 후 해시가 모두 동일하다.

| 최종 그룹 | Passed | Failed | Skipped | 실행 시간 |
|---|---:|---:|---:|---:|
| Taxonomy | 7 | 0 | 0 | 1,910.24초 |
| Note worksheet | 6 | 0 | 0 | 1,413.58초 |
| Worksheet | 2 | 0 | 0 | 1,773.91초 |
| 나머지 전체(수정 후 재실행) | 433 | 0 | 0 | 554.61초 |
| 합계(고유 테스트) | 448 | 0 | 0 | 병렬 실행 — 시간 합산하지 않음 |

근거: `.pytest_cache/phase3-final-nodeids.json`, `phase3-final-groups-v2.json`, `phase3-suite-taxonomy.xml`, `phase3-suite-notes.xml`, `phase3-suite-worksheet.xml`, `phase3-suite-remaining-v2.xml`, `phase3-final-results-final.json`. 이 검증용 생성 파일들은 Git 변경에 포함하지 않는다.
기존 경고 3개(클래스 fixture 인스턴스 메서드 deprecation 2개, 기본 스타일 없는 기존 Excel 1개)는 남아 있으며 이번 범위에서 테스트나 자산을 바꾸지 않았다.
UI regression: 16 passed / 0 failed. TypeScript: PASS. Production build: PASS.
최종 Phase 3 진입점 통합은 15 passed. 전체 suite에서 기존 용어 검사 2개가 내부 ID의 화면/진행 메시지 노출을 검출했다. 기존 테스트를 그대로 유지하고 사용자 문구를 대사 조서/제출파일 속성 검증으로 수정한 뒤 용어 검사 4개와 진입점 15개 모두 통과했다(19 passed). 직전 Phase 1/2/3 합동 회귀는 108 passed이며 이후 추가한 current/prior 실제 통합 1개도 별도로 통과했다. 이 반복 결과를 전체 suite 개수에 더하지 않는다.
브라우저 확인: 사용자 DB와 분리한 임시 DB에서 홈의 DSD 열기→실제 extract→검증→XBRL 태깅 대사→M-1 입력/생성→V-2 입력/실행을 실제 UI로 완주했다. M-1 `총괄표/BS`, V-2 `요약/기간속성/단위속성/주석명칭` Excel 파일을 다시 읽어 확인했다. 화면의 V-2 FALSE는 기간 0/단위 0/주석명 3으로 실제 코어 결과와 일치했다. 확인 후 임시 브라우저와 서버를 종료했다. 사용자의 Excel 앱이나 기존 DB를 열거나 변경하지 않았다.
초기 빌드는 샌드박스 상위 폴더 읽기 제한으로 실패했고, 동일 명령을 접근 가능한 환경에서 재실행해 통과했다. 제품 코드/빌드 기준을 낮추지 않았다.

Phase 3 제품 코드: `auditdesk/__main__.py`, `auditdesk/completion.py`, `auditdesk/routers/studio.py`, `dsd_workbench/dsd_tool/worksheet.py`, `dsd_workbench/dsd_tool/rollforward.py`, `webui/src/Session.tsx`.
Phase 3 테스트: `tests/test_phase3_completion.py`, `webui/tests/phase3.test.cjs`.
Phase 3 보고서: 이 파일.
기존 사용자 변경(C)은 다음 5개이며 작업 전후 해시가 모두 동일하다.

- `CLAUDE.md`
- `auditdesk/FEATURE_ARCHAEOLOGY_REPORT.md`
- `auditdesk/REQUIREMENTS_GAP_AUDIT_20260908.md`
- `auditlink-v2/.claude/launch.json`
- `DSD_footing/.claude/settings.local.json`

테스트 로그/임시 Excel/XML/SQLite, 브라우저 검증용 서버/DB, build 산출물은 ignored 위치에만 두며 제품 변경에 포함하지 않는다. 사용자 파일이나 기존 미커밋 변경을 삭제하지 않았다.
최종 Phase 3 A/B diff: **9개 파일, +745/-9** (제품 코드 6개 +295/-9, 테스트·보고서 3개 +450/-0). tracked-only `git diff --stat`에는 신규 파일 4개가 빠지고 기존 CLAUDE 변경(+72/-22)이 들어가므로 이를 별도 분리해 계산했다.
`git diff --check`: PASS. staged 파일: 0개.
commit/push하지 않았다.

## Phase 3 completion status

- M-18: PASS
- M-19: PASS
- M-20: PASS
- M-21: PASS
- M-22: PASS
- Phase 1 regression: Python 38 / UI 6 PASS
- Phase 2 regression: Python 56 / UI 7 PASS
- Full Python suite: 448 passed / 0 failed / 0 skipped / 0 errors
- UI regression: 16 passed
- TypeScript: PASS
- Production build: PASS
- Remaining risks: pairs 업무 판단은 사용자 확인, 기계 입력이 없는 가이드 항목은 판단필요 유지, rollforward는 공식 CLI 제공. 기존 코어의 지원 범위 및 경고 3개 유지. 기능별 상세 제약은 각 절에 기재.
