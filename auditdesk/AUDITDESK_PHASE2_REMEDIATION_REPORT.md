# AuditDesk Phase 2 Remediation Report

검증일: 2026-09-14. 브랜치: `fix/auditdesk-regression-reliability`.
기준 커밋: `372c9cf15a4a957d121ec731c8cad72d2e5cf33f` (Phase 1).
범위: M-08~M-16의 기존 기능 회귀·경계조건·복구 경로만 수정. UI 스타일, 추천 알고리즘, M-18 이후 기능, 기존 테스트와 기대값은 변경하지 않았다. commit/push하지 않았다.

**최종 확정: M-08~M-16 PASS. 전체 Python 433 passed / 0 failed / 0 skipped / 0 errors. 사용자 검토를 위해 미커밋 상태로 마감한다.**

## 검증 방법과 수정 전 증거

제품 수정 전에 신규 회귀를 작성하고 실패를 확인했다. 최초 Python 재현은 **19 failed**, UI 재현은 **3 failed / 1 passed**였다. 추가 경로(수동 레벨 재검증의 limit 초기화, 비동기 작업의 API 키 누락, 숫자 경계)는 **20 failed / 4 passed**였다. 4개 통과 항목은 먼저 수정한 전기대사 tolerance의 추가 경계 검사다. 지원 불가능한 CE 구조의 설명 가능한 오류는 별도로 **1 failed**를 확인했다.

수정 전 로그: `.pytest_cache/phase2-red-01.log`, `phase2-red-02.log`, `phase2-red-03.log`, `phase2-red-04.log`. 테스트는 임시 DSD/Excel/SQLite와 격리된 FastAPI 앱을 사용했다. UI는 실제 TSX 함수와 API 모듈을 TypeScript로 변환해 실행하는 Node hook/JSX harness다. OS 파일 실행과 외부 수신은 제어 가능한 대역으로 검증했으며 사용자의 Excel 파일을 열거나 편집하지 않았다.

넓은 실제 공시의 `주 석` 헤더를 확인하면서 공백/줄바꿈 포함 주석 열이 금액 열로 포함되는 경계를 추가 재현했다(**2 failed / 1 passed**). 공백을 정규화하여 주석 열을 제외했고, 영향을 받는 기존 본문 작성·승계·표 분류와 Phase 2 회귀를 최종 코드로 다시 실행했다. 중단한 이전 worksheet 실행은 최종 결과에 사용하지 않는다.

추가 한도 경계 테스트의 첫 실행에서 새 테스트가 총괄표 H열(링크)을 I열(오류 건수)로 오인했고, 코어가 당기에만 수동 레벨을 적용한다는 조건을 놓쳤다. 실제 조서의 I열을 검사하고 전기는 일치하는 대조군으로 구성했다. 당기의 0/한도 이내/경계/초과 기대값은 유지했다. 기존 테스트를 수정하거나 코어 업무 기준을 낮추지 않았다.

## M-08 — 공시 접수별 Excel 저장 identity

- **수정 전 재현:** 같은 친화명을 반환하는 서로 다른 접수번호 및 같은 접수 재변환을 실제 extract에 전달했다. `Company_Report_2025.xlsx` 경로가 재사용되어 기존 편집 파일을 덮어쓸 수 있었다.
- **Root cause:** Explorer `to_excel`이 표시용 친화명을 저장 identity로 사용했다.
- **변경 파일:** `auditdesk/routers/explorer.py`, `tests/test_phase2_reliability.py`.
- **변경 내용:** 접수번호를 접두사로 갖는 독립 디렉터리를 `mkdtemp`로 생성하고 그 안에 친화명 Excel을 저장한다. 디렉터리 생성 자체가 배타적이므로 같은 접수의 반복 실행도 기존 경로를 재사용하지 않는다. `display_name`, `xlsx_path`, `dsd_path` 응답 키는 유지했다.
- **추가 regression:** `test_m08_receipts_and_retries_preserve_existing_output` (1개). 서로 다른 2개 접수와 첫 접수 재실행, 친화명 유지, 이전 파일 byte 보존, 경로 분리를 확인한다.
- **수정 전 결과:** FAIL — 접수 identity가 없는 공통 경로.
- **수정 후 결과:** PASS — 3회 결과 경로가 다르고 앞선 편집 내용 유지. 마감 단계에서 HEAD의 기존 `to_excel` 함수만 격리 실행한 비교에서도 실제 Excel 셀 편집이 기존 구현에서는 덮어써지고 현재 구현에서는 보존됨을 확인했다(`.pytest_cache/phase2-m08-baseline-proof.json`). 제품 파일을 과거 버전으로 되돌리지 않았다.
- **관련 기존 테스트:** `test_n1.py`, `test_document_structure.py`, `test_pipeline.py`.
- **Phase 1 회귀:** M-01/M-06/M-07의 파일 동일성·재추출 보존·캐시 보호 회귀 포함, 전체 38개 재검증.
- **인접 workflow:** Explorer 공시→Excel, 기존 DSD extract→diff→repack 및 래핑 roundtrip.
- **남은 위험:** 반복 변환 파일은 누적된다. 파일 정리 기능을 새로 추가하지 않았으며 기존 작업 파일을 자동 삭제하지 않는다.

## M-09 — 복귀 링크의 원문 보존

- **수정 전 재현:** BS `A2:M2` 및 주석 `C8:N8`을 병합하고 원문 제목/숫자를 넣은 뒤 AI Footing을 생성했다. 링크가 병합 anchor로 이동하며 원문을 덮어썼다.
- **Root cause:** `cellsafe.put`은 병합 anchor 쓰기에는 안전했지만 기존 값 충돌을 구분하지 않았다.
- **변경 파일:** `dsd_workbench/dsd_tool/cellsafe.py`, `foot_excel.py`, `tests/test_phase2_excel.py` (이 절의 테스트 파일은 `dsd_workbench/dsd_tool/tests/` 기준).
- **변경 내용:** 링크 호출에만 `preserve_value=True`를 적용한다. 원문과 충돌하면 기존 표의 마지막 열 오른쪽 빈 셀을 사용한다. Excel 최대 열까지 사용 중이면 원문을 보존하고 기존 기입 실패 목록으로 사유를 노출한다. 메모 추가·강조색의 기존 병합 anchor 처리는 유지했다.
- **추가 regression:** `test_m09_merged_return_link_keeps_source` (문자열/숫자 2개), `test_m09_occupied_unmerged_cell_and_full_sheet_fallback` (1개).
- **수정 전 결과:** FAIL — 병합 anchor의 원문 값이 링크 수식으로 바뀜.
- **수정 후 결과:** PASS — 제목·숫자·0 보존, 안전한 링크 위치, 공간 부족 시 명시적 실패 기록.
- **관련 기존 테스트:** `test_h2.py`, `test_foot_excel.py`, `test_a6.py`.
- **Phase 1 회귀:** 38개 재검증; 기존 전기대사 수식 추적성과 추출 파일 보존 포함.
- **인접 workflow:** 추출된 병합 표→footing→AI Footing 총괄표/검증내역 왕복 링크.
- **남은 위험:** 충돌 시 링크가 표 오른쪽으로 이동한다. 빈 열이 전혀 없으면 링크는 생성하지 않으며 사유를 검증내역에 표시한다.

## M-10 — 실행 limit 및 단수차 의미 일치

- **수정 전 재현:** limit=0 요청이 2로 바뀌고, limit=5 코어 결과에 limit가 없어 Excel writer가 2로 재구성했다. FUZZY는 오류 건수와 노란색에 포함되지만 판정 수식은 TRUE였다. 수동 레벨 재검증도 2를 고정 사용했다.
- **Root cause:** truthy 기본값 처리, 결과/세션의 limit 미저장, writer의 기본 Context 재생성, FUZZY를 bool로 축약한 수식.
- **변경 파일:** `auditdesk/routers/workbench.py`, `auditdesk/validation.py`, `dsd_workbench/dsd_tool/foot.py`, `foot_excel.py`, 두 Phase 2 Python 테스트 파일.
- **변경 내용:** 입력→코어 결과→세션/작업 응답→Excel Context까지 limit를 전달한다. 수동 레벨 재검증은 저장된 limit를 사용한다. 추적 가능한 셀 참조를 유지하며 판정은 차이=0이면 TRUE, 0<차이≤limit이면 `단수차`, 초과이면 FALSE다. FUZZY의 기존 코어 의미와 오류 집계/노란색 표시를 유지한다.
- **추가 regression:** `test_m10_zero_limit_survives_route`, `test_m10_level_recheck_keeps_previous_limit` (2개), `test_m10_core_result_retains_limit` (3개), `test_m10_excel_preserves_fuzzy_semantics_and_limit`, `test_m10_limit_boundary_core_excel_and_session_agree` (5개): **12개**.
- **수정 전 결과:** FAIL — limit 누락/초기화, FUZZY가 TRUE로 표현됨.
- **수정 후 결과:** PASS — limit=0/2/5, 차이=0/1/5/6, 코어·수식·요약·초기 색상 일치. 전기는 정상 대조군으로 유지된다.
- **관련 기존 테스트:** `test_foot.py`, `test_foot_excel.py`, `test_a6.py`, `test_a7.py`.
- **Phase 1 회귀:** M-02/M-03의 19개 전기대사 테스트 및 나머지 19개 무결성 테스트 재검증.
- **인접 workflow:** 합계검증→AI Footing, 수동 레벨 수정→재검증, prior reconciliation.
- **남은 위험:** 이전 저장 기록에 limit가 없으면 기존 기본값 2를 사용한다. 과거 실행 한도를 추정하지 않는다. 실제 Excel 엔진에서 격리된 테스트 조서 5개를 읽기 전용으로 재계산해 TRUE/단수차/FALSE와 정상 전기 대조군의 일치를 확인했다. 생성 후 사용자가 조서 숫자를 다시 편집했을 때 정적 요약/색상의 자동 갱신은 기존 범위 그대로다.

## M-11 — 최초 diff 실패 후 재시도

- **수정 전 재현:** 최초 자동 diff 요청을 실패시키면 오류만 남고 diff가 없는 화면에는 클릭 가능한 재실행 동작이 없었다.
- **Root cause:** 재비교 버튼은 diff가 있을 때만 렌더링되고 자동 effect는 최초 1회만 실행됐다.
- **변경 파일:** `webui/src/Session.tsx`, `webui/tests/phase2.test.cjs`.
- **변경 내용:** 최초 자동 실행은 유지하고 실패 화면에 기존 GhostBtn의 `다시 비교`를 연결했다. ref로 요청 중 재진입을 막으며 자동 무한 재시도는 없다.
- **추가 regression:** 실패→같은 화면 재시도·연속 클릭 중복 방지, 정상 최초 성공 1회 실행: UI **2개**.
- **수정 전 결과:** FAIL — 실패 후 재시도 버튼 0개.
- **수정 후 결과:** PASS — 명시적 재시도 1회, 진행 중 중복 요청 없음, 정상 최초 동작 유지.
- **관련 기존 테스트:** `test_phase1_integrity.py`의 diff/repack 승인·해시 검사, `test_pipeline.py`.
- **Phase 1 회귀:** Python 38개와 UI 6개 재검증.
- **인접 workflow:** extract→자동 diff→오류→재시도→승인→repack.
- **남은 위험:** 기존 서버 오류가 지속되면 사용자 재시도가 다시 실패할 수 있다. 재시도는 원인 자체를 숨기거나 자동으로 승인하지 않는다.

## M-12 — 좁은 CE 작성 워크시트

- **수정 전 재현:** extract가 정상 수용한 `과목/자본금/이익잉여금` 3열 CE로 worksheet 생성 시 `min() arg is an empty sequence`가 발생했다.
- **Root cause:** CE 헤더와 member 블록이 모두 5열 이상인 행을 전제로 했다. 공통 FS 기간 추론만 재사용하면 B열 자본금도 누락될 수 있었다.
- **변경 파일:** `dsd_workbench/dsd_tool/worksheet.py`, `auditdesk/routers/studio.py`, `auditdesk/jobs.py`, `dsd_workbench/dsd_tool/tests/test_phase2_excel.py`.
- **변경 내용:** 동일 표 region의 헤더와 실제 자본 열을 사용한다. 자본 열은 기간 쌍으로 합치지 않고 각각 보존하며 공백/줄바꿈을 정규화한 명시적 주석 열을 제외한다. 자본 금액 열이 없는 구조는 `WorksheetStructureError`로 표 이름과 원인을 전달한다. Studio 작업 함수는 이를 422 오류로 분류하고 job의 `error` 상태와 구체적 메시지로 전달한다. 비동기 제출의 HTTP 202 계약은 유지한다.
- **추가 regression:** `test_m12_extracted_narrow_ce_builds`, `test_m12_unsupported_ce_has_table_specific_error`, `test_m12_ce_note_references_are_not_capital` (헤더 3종): **5개**. 추천만 작은 corpus 대역으로 대체하며 extract와 worksheet 생성은 실제 구현을 실행한다.
- **수정 전 결과:** FAIL — 3열 CE 내부 예외. 지원 불가능한 구조에 대한 별도 오류 계약도 수정 전 FAIL.
- **수정 후 결과:** PASS — CE 시트, 자본금 헤더/100000 값 보존, 지원 불가능한 CE의 구체적 오류. 실제 비동기 worksheet→job 조회에서도 정상 CE 값 보존과 오류 안내 전달을 확인했다(`.pytest_cache/phase2-worksheet-job-workflow.json`). 추천을 대역으로 격리한 실제 자료 구조 검사에서 삼성 CE의 자본 5열/숫자 46개, 한빛 CE의 자본 5열/숫자 28개도 전부 보존됐다(`.pytest_cache/phase2-wide-ce-workflow.json`). 기존 추천 정확도 테스트는 별도로 원래 기준으로 실행했다.
- **관련 기존 테스트:** `test_worksheet.py`의 삼성/한빛 본문 작성, `test_note_worksheet.py`, `test_fs_titles.py`.
- **Phase 1 회귀:** CE 미대응 자본항목 및 tolerance 회귀 19개 포함, 전체 38개 재검증.
- **인접 workflow:** extract→worksheet, 본문+주석 worksheet, 기존 CE member 추천.
- **남은 위험:** header/region 선택과 member 추천의 기존 한계는 유지한다. 모든 비정형 공시 표의 새 지원을 선언하지 않는다.

## M-13 — 대안 매핑 후보 선택/확정

- **수정 전 재현:** 대안 후보가 표시돼도 선택 콜백이 없었고 확정은 항상 최초 top candidate를 전달했다.
- **Root cause:** RecCard의 대안 행은 읽기 전용이며 MappingCard가 top 후보를 고정 참조했다.
- **변경 파일:** `webui/src/Studio.tsx`, `webui/src/RecCard.tsx`, `webui/tests/phase2.test.cjs`, `tests/test_phase2_reliability.py`.
- **변경 내용:** 대안 행의 마우스/키보드 선택을 현재 후보에 연결하고 기존 decide callback/API로 원래 element ID를 전달한다. 계정 전환 시 선택 상태를 분리한다. 자동 top 추천과 후보 순위는 유지하고 대안 선택은 `선택한 대안`으로 표시한다. 확정 카드는 계속 잠긴다.
- **추가 regression:** UI 선택→확정 및 실제 RecCard 마우스/Enter/Space/잠금 **2개**, decide 저장→조회 복원 Python **1개**.
- **수정 전 결과:** FAIL — 선택 콜백 없음, top 이외 확정 불가.
- **수정 후 결과:** PASS — 선택한 raw element ID 저장/복원, 추천 순서 유지, 확정 사용자/시각 유지.
- **관련 기존 테스트:** `test_mapping.py`, `test_note_worksheet.py`의 추천 상태, 기존 매핑 결과/decide workflow.
- **Phase 1 회귀:** Python 38개 및 UI 6개 재검증.
- **인접 workflow:** mapping 추천→대안 선택→decide→조회/확정 결과 복원.
- **남은 위험:** 대안의 적합성은 기존 추천 품질과 사용자 판단에 따른다. 알고리즘 점수·자동 확정 정책을 바꾸지 않았다.

## M-14 — kind 필터를 LIMIT 전에 적용

- **수정 전 재현:** 오래된 mapping 완료 작업 뒤에 다른 kind 작업 60개를 넣으면 `/api/jobs?kind=mapping`이 빈 목록을 반환했다.
- **Root cause:** SQL 전체 최근 50개를 읽은 뒤 라우터에서 kind를 필터링했다.
- **변경 파일:** `auditdesk/jobs.py`, `auditdesk/routers/jobs_api.py`, `tests/test_phase2_reliability.py`.
- **변경 내용:** 선택적 kind 조건을 parameterized SQL WHERE에 넣고 이후 ORDER BY/LIMIT 50을 적용한다. 기본 조회와 active 필터 의미는 유지한다.
- **추가 regression:** `test_m14_kind_is_filtered_before_limit`: **1개**, 과거 완료 작업 복원·기본 50개·active+kind 확인.
- **수정 전 결과:** FAIL — 해당 kind의 완료 작업 복원 불가.
- **수정 후 결과:** PASS — 전체 최근 50개 밖의 mapping 작업 복원.
- **관련 기존 테스트:** job submit/get/list 및 Studio 결과 복원 경로.
- **Phase 1 회귀:** M-04 session 소속 XBRL 복원 Python/UI 포함, 전체 재검증.
- **인접 workflow:** job 완료→kind별 조회→결과 복원. XBRL 결과의 타 세션 fallback은 다시 도입하지 않았다.
- **남은 위험:** kind별 최근 50개 한도는 유지한다. pagination은 추가하지 않았다.

## M-15 — 파일 열기 실패의 오류 계약

- **수정 전 재현:** 없는 파일은 HTTP 200 `{ok:false}`, OS 실행 실패는 내부 예외였다. 프런트의 파일 열기 호출은 실패를 사용자에게 표시하지 않았다.
- **Root cause:** 파일 API의 성공/실패 HTTP 계약 불일치와 각 버튼의 catch 누락.
- **변경 파일:** `auditdesk/routers/fs.py`, `webui/src/api.ts`, `Session.tsx`, `Studio.tsx`, `Explorer.tsx`, 두 Phase 2 API/UI 테스트 파일.
- **변경 내용:** 빈 경로 422, 파일 없음 404, OS 실행 실패 409 및 구체적 안내를 반환한다. OS 예외 원문은 노출하지 않는다. 정상 `{ok:true}`는 유지한다. 모든 기존 파일 열기 버튼을 공통 `openFile`에 연결해 실패 메시지를 표시한다.
- **추가 regression:** Python 없음/OS 실패/성공 **3개**, UI API 오류·오류 표시·정상 열기 및 호출 연결 **3개**.
- **수정 전 결과:** FAIL — 잘못된 성공 응답 및 오류 표시 처리 없음.
- **수정 후 결과:** PASS — 404/409 처리, 사용자 메시지, 정상 경로 전달과 성공 계약 유지.
- **관련 기존 테스트:** API 공통 오류 처리, 기존 Excel 산출물 경로 계약.
- **Phase 1 회귀:** UI 6개 및 Python 38개 재검증.
- **인접 workflow:** Session/Explorer/Studio의 Excel 파일 열기, footing 완료 후 파일 열기.
- **남은 위험:** 실제 Windows 기본 앱 연결과 Excel 실행은 수동 확인 영역이다. `os.startfile`의 호출 성공 이후 외부 앱 자체의 실패까지 감지하는 새 기능은 추가하지 않았다.

## M-16 — 예상 가능한 설정/숫자 오류의 4xx 분리

- **수정 전 재현:** API 키 없음, year/limit/account_idx/level 숫자 형식 오류는 500 또는 실패 예정 작업의 202였다. NaN/Infinity/음수도 일부 경로에서 큐나 DB에 도달했다.
- **Root cause:** raw `int`/`float` 변환과 검증 없는 dict 입력, 작업 함수 내부의 API 키 로딩.
- **변경 파일:** `auditdesk/validation.py`, `auditdesk/routers/explorer.py`, `workbench.py`, `studio.py`, `auditdesk/jobs.py`, `tests/test_phase2_reliability.py`.
- **변경 내용:** 공통 숫자 검증으로 유한성·최솟값·정수 여부를 확인하고 422 및 항목별 메시지를 반환한다. 누락 API 키는 고정된 안전한 안내와 409로 반환한다. Explorer 비동기 수신 경로도 제출 전에 설정을 확인한다. 실제 client 내부 오류는 500으로 유지하고 예외/키 원문을 설정 오류 메시지에 넣지 않는다.
- **추가 regression:** API 키 누락, 비동기 경로 6개, year/corpus limit, foot limit, prior/XBRL tolerance·level·decision 숫자 경계, 실제 내부 오류 대조군: **30개**.
- **수정 전 결과:** FAIL — 500 또는 잘못된 202/200, 오류 구분 실패.
- **수정 후 결과:** PASS — 해당 예상 입력/설정 오류는 4xx, 작업 제출 차단, 내부 오류는 500, 비밀 진단값 미노출.
- **관련 기존 테스트:** `test_client.py`, 기존 Explorer 수신/캐시, mapping decide, prior/XBRL reconciliation.
- **Phase 1 회귀:** 전기대사 tolerance=0/>0 및 XBRL 세션 소속 포함, 전체 38개와 UI 6개 재검증.
- **인접 workflow:** API 키 미설정 검색/수신, numeric 입력 오류, 정상 0 한도, mapping 확정, prior/XBRL 대사.
- **남은 위험:** OpenDART 서비스 가용성·요청 한도·유효하지 않은 발급 키에 대한 외부 서비스 응답은 기존 수신 계층의 범위다. 실제 서버 내부 오류를 임의로 4xx로 낮추지 않는다.

## 최종 검증 집계

실제 Excel 재계산: limit=0에서 차이 0→TRUE / 1→FALSE, limit=5에서 차이 1→단수차 / 5→단수차 / 6→FALSE, 전기 대조군은 모두 TRUE. 별도 숨김 인스턴스에서 테스트 파일만 읽기 전용으로 열었고 저장하지 않았다. 근거: `.pytest_cache/phase2-excel-recalculation.json`. 이 5건은 Python 테스트 수에 합산하지 않는다.

최종 전체 Python 결과는 **433 passed / 0 failed / 0 skipped / 0 errors**, 미확인 0개다. Phase 2 전용 결과는 **Python 56 passed / 0 failed / 0 skipped / 0 errors**, UI 전용 **7 passed**다. Phase 1 UI 6개를 합친 UI 전체는 **13 passed / 0 failed / 0 skipped**다. TypeScript 및 production build는 PASS다.

| Phase 2 항목 | Python 회귀 | UI 회귀 | 결과 |
|---|---:|---:|---|
| M-08 | 1 | 0 | PASS |
| M-09 | 3 | 0 | PASS |
| M-10 | 12 | 0 | PASS |
| M-11 | 0 | 2 | PASS |
| M-12 | 5 | 0 | PASS |
| M-13 | 1 | 2 | PASS |
| M-14 | 1 | 0 | PASS |
| M-15 | 3 | 3 | PASS |
| M-16 | 30 | 0 | PASS |
| 합계 | **56** | **7** | PASS |

Phase 1 회귀는 **Python 38 passed / 0 failed / 0 skipped**, **UI 6 passed / 0 failed / 0 skipped**다. M-01 8개, M-02 2개, M-03 17개, M-04 1개, M-06 6개, M-07 4개의 Python 테스트와 M-04/M-05 각 3개의 UI 테스트를 모두 유지했다. 이 숫자는 전체 Python/UI 집계에 포함되는 부분집합이며 별도로 더하지 않는다.

전체 수집은 **433개 고유 Python ID**다. Phase 1의 376개 + 신규 Phase 2 56개 + 새 테스트 파일을 자동 포함한 기존 오프라인 import 검사 1개다. 기존 테스트 삭제/누락은 없다. 독립 실행의 JUnit 결과를 전체 ID에 대응시키고 중복 실행 횟수는 합산하지 않는다. 기존 `.test_results.json` hook은 마지막 단일 실행만 기록하므로 전체 집계 근거로 사용하지 않았다. 전용 Phase 2 실행 결과를 해당 56개 ID의 최종 판정으로 사용한다.

### 전체 Python 최종 결과 및 인접 workflow

| 전체 수집 범위 | Passed | Failed | Skipped | Errors |
|---|---:|---:|---:|---:|
| `backend/tests/` | 29 | 0 | 0 | 0 |
| `dart_explorer/tests/` | 47 | 0 | 0 | 0 |
| `dsd_workbench/dsd_tool/tests/` | 299 | 0 | 0 | 0 |
| `tests/` (AuditDesk API/무결성) | 58 | 0 | 0 | 0 |
| **고유 테스트 합계** | **433** | **0** | **0** | **0** |

JUnit 8개 결과 파일의 테스트 ID를 최종 수집 목록에 대응시켰다. 중복 결과 67개는 합산하지 않았다. 동일 ID의 판정 충돌은 없었으며, 최종 Phase 2/영향 범위 재실행 결과를 우선 사용했다. Phase 1의 기존 376개 ID가 모두 포함되는 것도 확인했다. 중단한 이전 코드의 worksheet 실행과 수정 전 red 결과는 최종 집계에서 제외했다.

| 인접 workflow | 검증 근거 | 결과 |
|---|---|---|
| extract → diff → repack | `test_pipeline.py`, Phase 1 승인 해시·재추출 상태 회귀 | PASS |
| footing | `test_foot.py`, `test_foot_excel.py`, `test_a6.py`, `test_a7.py`, Phase 2 limit 12개 | PASS |
| prior reconciliation | `test_recon.py`, Phase 1 CE/tolerance 19개 | PASS |
| XBRL reconciliation | `test_xbrl_recon.py`, `test_v1b.py`, Phase 1 session 복원 | PASS |
| worksheet 생성 | 실제 삼성/한빛 `test_worksheet.py` 2개, 주석 6개, 승계 3개, CE 구조 회귀 5개 | PASS |
| mapping 후보 결정 | `test_mapping.py` 8개, 대안 선택 UI 및 decide 저장/조회 | PASS |
| job result 복원 | kind 필터 전 LIMIT 회귀, session별 XBRL 복원 | PASS |
| Explorer 공시 → Excel | 접수/재변환 보존, 실제 편집 파일 baseline 비교, document roundtrip | PASS |
| 파일 열기 | HTTP 오류/성공 3개, UI 오류 처리/호출 연결 3개 | PASS |
| API key 미설정 | 검색 및 비동기 수신 6개 경로의 제출 전 409 | PASS |

검증 환경은 Windows / Python 3.14.0 / pytest 9.1.0이다. 기존 클래스 fixture deprecation 경고 2개와 openpyxl 기본 스타일 경고 1개가 있었으며 실패·skip·error는 없었다. 관련 없는 기존 테스트나 스타일 파일을 변경하여 경고를 숨기지 않았다.

- 전체 ID: `.pytest_cache/phase2-final-collection-v3.log`.
- ID별 최종 판정·원본 JUnit·중복 처리: `.pytest_cache/phase2-final-node-results.json`.
- JUnit/로그: `phase2-final-{backend,api,dsd,notes,taxonomy,worksheet-v2,affected,regression-v2}.{xml,log}` (모두 `.pytest_cache/`).
- Phase 2 전용 최종 실행: **56 passed**. 영향 범위 재실행: **20 passed**. 주석 gate **6 passed**, 택사노미 gate **7 passed**, 최종 본문 작성 gate **2 passed**.
- UI: `node --test tests/phase1.test.cjs tests/phase2.test.cjs` → **13 passed / 0 failed / 0 skipped** (cwd `webui/`). 실제 TSX/API 모듈 실행 harness이며 브라우저 전체 E2E 결과로 표현하지 않는다.
- TypeScript: `npx tsc -b --pretty false` → **PASS**.
- Production: `npm run build` (`tsc -b && vite build`) → **PASS**, 40 modules transformed. 로그: `.pytest_cache/phase2-production-build.log`.
- 실제 Excel 엔진의 limit 경계 5건 및 별도 구조/비동기 workflow 검사는 위 433개에 더하지 않았다.

재현 실행은 각 그룹에 독립 `--basetemp`와 `--junitxml`을 지정했다. 주요 실행 범위는 다음과 같다.

```text
python -m pytest tests dart_explorer/tests --ignore=dart_explorer/tests/test_taxonomy_diff.py -v
python -m pytest dsd_workbench/dsd_tool/tests --ignore=dsd_workbench/dsd_tool/tests/test_worksheet.py --ignore=dsd_workbench/dsd_tool/tests/test_note_worksheet.py -v
python -m pytest dart_explorer/tests/test_taxonomy_diff.py -v
python -m pytest dsd_workbench/dsd_tool/tests/test_note_worksheet.py -v
python -m pytest dsd_workbench/dsd_tool/tests/test_worksheet.py -v
python -m pytest dsd_workbench/dsd_tool/tests/test_succession.py dsd_workbench/dsd_tool/tests/test_fs_titles.py -v
python -m pytest tests/test_phase2_reliability.py dsd_workbench/dsd_tool/tests/test_phase2_excel.py -v
# cwd: backend
python -m pytest -q
```

## Git 변경 범위

기준은 현재 HEAD(Phase 1 커밋) 대비 작업 트리다. 아래 경로는 저장소 루트 기준이다. stage/commit/push하지 않았다.

### A. Phase 2 제품 코드 — 16개, +193 / -105

| 변경 파일 | 추가 | 삭제 |
|---|---:|---:|
| `auditdesk/auditdesk/jobs.py` | 10 | 4 |
| `auditdesk/auditdesk/routers/explorer.py` | 42 | 17 |
| `auditdesk/auditdesk/routers/fs.py` | 8 | 3 |
| `auditdesk/auditdesk/routers/jobs_api.py` | 1 | 3 |
| `auditdesk/auditdesk/routers/studio.py` | 12 | 6 |
| `auditdesk/auditdesk/routers/workbench.py` | 8 | 6 |
| `auditdesk/dsd_workbench/dsd_tool/cellsafe.py` | 7 | 1 |
| `auditdesk/dsd_workbench/dsd_tool/foot.py` | 1 | 0 |
| `auditdesk/dsd_workbench/dsd_tool/foot_excel.py` | 8 | 6 |
| `auditdesk/dsd_workbench/dsd_tool/worksheet.py` | 16 | 8 |
| `auditdesk/webui/src/Explorer.tsx` | 2 | 9 |
| `auditdesk/webui/src/RecCard.tsx` | 17 | 5 |
| `auditdesk/webui/src/Session.tsx` | 17 | 20 |
| `auditdesk/webui/src/Studio.tsx` | 13 | 17 |
| `auditdesk/webui/src/api.ts` | 10 | 0 |
| `auditdesk/auditdesk/validation.py` | 21 | 0 |

### B. Phase 2 regression / 보고서 — 4개

- `auditdesk/tests/test_phase2_reliability.py`: API 회귀 39개.
- `auditdesk/dsd_workbench/dsd_tool/tests/test_phase2_excel.py`: Excel 회귀 17개.
- `auditdesk/webui/tests/phase2.test.cjs`: UI 회귀 7개.
- `auditdesk/AUDITDESK_PHASE2_REMEDIATION_REPORT.md`: 본 보고서.

신규 B 파일은 테스트 462줄 + 보고서 288줄 = **+750/-0**이다. A/B 전체는 **20개 파일, +943/-105**이며 기존 사용자 C 변경은 제외했다. 일반 `git diff --stat`에는 신규 파일이 포함되지 않으므로 이 수치를 별도로 집계했다.

### C. 보존한 기존 사용자 변경 / 제외한 생성 파일

| 항목 | 분류·처리 |
|---|---|
| `CLAUDE.md` | 기존 추적 사용자 변경 +72/-22, 보존 |
| `auditdesk/FEATURE_ARCHAEOLOGY_REPORT.md` | 기존 미추적 감사 보고서, 보존 |
| `auditdesk/REQUIREMENTS_GAP_AUDIT_20260908.md` | 기존 미추적 감사 보고서, 보존 |
| `auditlink-v2/.claude/launch.json` | 기존 실행 설정, 보존 |
| `DSD_footing/.claude/settings.local.json` | 기존 개인 설정, 보존. 제한 실행의 전역 ignore 접근 여부에 따라 status 표시가 달라질 수 있음 |
| `auditdesk/.pytest_cache/phase2-*` | 이번 테스트의 DSD/Excel/JSON/XML/SQLite, JUnit, 로그, 집계·해시·조사 스크립트. 기존 ignore 대상, 제품 변경에서 제외 |
| `auditdesk/.test_results.json` | 기존 pytest hook 생성 결과, 기존 ignore 대상 |
| `auditdesk/auditdesk/static/` | Vite production HTML/CSS/JS, 기존 ignore 대상 |
| `auditdesk/auditdesk/data/`, 공시 cache/corpus/taxonomies | 기존 로컬 세션·작업·다운로드 자료, 기존 ignore 대상, 보존 |
| `node_modules/`, `__pycache__/`, 기존 fixtures 작업 폴더 | 의존성/생성 캐시, 기존 ignore 대상 |

기존 사용자 파일 5개의 내용 해시를 유지했다. 기존 Phase 1 보고서와 테스트는 변경하지 않았다. 제품·테스트 19개 파일의 최종 소스 해시도 확인했다. 검증 도중 CE 주석 헤더 1줄 보완과 그 회귀 추가 이후에는 영향을 받는 worksheet/승계/표 분류/Phase 2 테스트를 재실행해 최종 결과를 사용한다. C 파일을 삭제·복원·정리하지 않았다. 새로운 cache/build/DB/감사용 scratch 파일이 Git 제품 변경에 포함되지 않았음을 `git status --untracked-files=all`, `git diff --stat/--numstat`, `git check-ignore -v`, staged diff로 확인했다.

일반 작업 트리 diff는 **추적 16개 파일, +244/-127**이다. 이는 A의 추적 15개 +172/-105와 기존 `CLAUDE.md` +72/-22의 합계다. A의 신규 숫자 검증 모듈 +21줄과 B의 신규 4개 파일은 이 수치에 별도로 더해야 한다.

## Phase 2 completion status

- M-08: PASS
- M-09: PASS
- M-10: PASS
- M-11: PASS
- M-12: PASS
- M-13: PASS
- M-14: PASS
- M-15: PASS
- M-16: PASS
- Phase 1 regression: Python 38 passed / UI 6 passed; failed 0, skipped 0
- Full Python suite: **433 passed / 0 failed / 0 skipped / 0 errors**; 고유 ID 기준, 미확인 0
- UI regression: 13 passed / 0 failed / 0 skipped
- TypeScript: PASS
- Production build: PASS
- git diff --check: PASS
- Remaining risks: 기본 앱 연결을 통한 실제 Windows 파일 열기 미실시, 보존 파일 누적, 과거 limit 미기록의 기본값, 기존 비정형 표/추천 품질의 한계. 항목별 상세 참조.
