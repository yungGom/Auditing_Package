# AuditDesk Phase 1 Remediation Report

작업 브랜치: `fix/auditdesk-integrity`
범위: M-01–M-07. 커밋하지 않음. 최초 재현: 2026-09-08, 후속 검증: 2026-09-14.

## 변경 범위와 검증 방법

각 Master 항목의 회귀 테스트를 먼저 작성하고 기존 코드에서 실패를 확인한 뒤 수정했다. 최초 Python 재현은 **11 failed / 7 passed**, 실제 React 컴포넌트를 실행한 UI 재현은 **2 failed / 1 passed**였다. 실패를 무시하거나 기존 테스트를 삭제·완화하지 않았다. API 이름, 기본 추출·검토·반영 순서, 셀 참조 수식, 기존 UI 배치와 스타일 값을 유지했다. 판정 조건에 따라 기존 성공/오류 표시를 선택하는 조건과 안내 문구만 변경했다.

새 테스트는 임시 DSD·Excel·SQLite DB를 사용한다. UI 테스트는 `Session.tsx`의 실제 XBRL 컴포넌트를 TypeScript로 변환해 최소 React hook/JSX harness에서 실행한다. 브라우저 전체 E2E나 Microsoft Excel 엔진에서의 직접 재계산을 수행했다는 의미는 아니다. Excel 검증은 생성 수식 자체의 주소·연산자·허용오차 확인, 저장 후 재독, 코어·수식 평가·요약의 일치 확인으로 구성했다.

기존 작업자의 `CLAUDE.md`, 두 감사 보고서, `DSD_footing/.claude/`, `auditlink-v2/` 변경은 이번 수정에 포함하지 않았다. 다음 Phase의 기능, 택사노미 추천·승계·추론, UI 재설계는 수정하지 않았다.

## M-01 — 승인 diff와 repack 입력의 결합

- **기존 재현:** 합성 DSD를 추출해 같은 셀을 1,234,577로 수정·검토한 뒤 1,234,587로 다시 수정했다. 기존 change ID 승인으로 후자의 값이 반영됐다. 큐 등록 후 실행 전 수정도 통과했다.
- **Root cause:** 세션의 diff 존재·옵션·change ID만 확인하고 repack에서 사용자 Excel 경로를 다시 읽었다. 검토된 파일 내용의 증빙과 비동기 입력 고정이 없었다.
- **변경 파일:** `auditdesk/routers/workbench.py`, `auditdesk/jobs.py`, `webui/src/Session.tsx`; 테스트 `tests/test_phase1_integrity.py`.
- **변경 내용:** diff가 실제로 읽는 snapshot의 SHA-256을 저장한다. 반영 접수 및 실행 시 동일성을 확인하고, repack은 해시를 확인한 별도 복사본을 읽는다. 이전 형식의 해시 없는 diff는 재검토를 요구한다. UI는 보고 있는 diff의 해시를 승인 요청에 보내며 다른 검토로 바뀌면 409로 거절한다. 반영 결과에도 입력 해시를 기록한다. 이력에는 임시 경로 대신 원래 작업 Excel 경로를 유지한다. 비동기 409 오류는 재검토 안내를 표시한다.
- **추가 regression test:** `test_m01_changed_value_same_ids_requires_review`, `test_m01_queued_repack_rechecks_input`, `test_m01_unchanged_input_repack_works`, `test_m01_repack_consumes_reviewed_snapshot_during_concurrent_edit`, `test_m01_history_keeps_source_workbook_path`, `test_m01_background_conflict_explains_rereview`, `test_m01_old_review_token_rejected_after_another_review`, `test_m01_non_diff_workbook_change_also_requires_review`.
- **수정 전 결과:** 내용 변경·큐 대기 변경 모두 거절되지 않아 2개 실패. 후속 테스트에서 이력 임시 경로, 비동기 안내 누락, 이전 화면 토큰 미검증도 각각 실패로 확인했다.
- **수정 후 결과:** 검토 후 저장된 파일이 달라지면 409 및 재검토 안내. 실행 snapshot 확정 이후 사용자가 원본을 바꾸더라도 반영되는 값은 검토했던 값이다. diff에 나타나지 않는 새 시트 변경도 해시 검증 대상이다.
- **관련 기존 테스트 결과:** 전체 검증 결과 절 참조. 기존 무변경 repack의 바이트 동일성·이력·원본 보존 테스트를 유지했다.
- **인접 기능 회귀 테스트:** 무변경 승인 왕복, snapshot 생성 이후 동시 편집, 원래 Excel 이력 경로, 다른 검토 화면 승인, 재추출과 diff 완료 경합.
- **남은 위험:** 외부 Excel에서 아직 저장하지 않은 내용은 검증할 수 없다. 호환성을 위해 승인 해시를 생략한 기존 API 호출은 서버에 저장된 최신 diff를 승인한다는 기존 의미를 유지한다. UI는 항상 검토 해시를 전송한다. snapshot을 확정한 이후의 외부 편집은 해당 반영 입력에 포함되지 않는다.

## M-02 — CE 미대응 자본항목 판정 보존

- **기존 재현:** 현재 CE에는 Capital·Retained, 전기 CE에는 Capital·Other를 배치했다. Capital은 같지만 Retained 대응 열이 없다. `recon_ce`는 두 행 모두 FALSE, 출력·요약은 두 행 모두 TRUE였다.
- **Root cause:** `_side_ce`가 미대응 자본 열을 `continue`로 버린 뒤 남은 대응 쌍만 비교했다.
- **변경 파일:** `dsd_workbench/dsd_tool/recon.py`; 테스트 `dsd_workbench/dsd_tool/tests/test_phase1_recon.py`.
- **변경 내용:** 미대응 자본항목을 명시적으로 기록해 수식에 FALSE 조건을 포함한다. 대응되는 항목의 셀 참조는 남긴다. 상대 값이 비어 있거나 비교 가능한 쌍이 없는 경우도 통과하지 않는다.
- **추가 regression test:** `test_m02_missing_ce_column_never_passes[0]`, `[2]`; 정상·불일치 CE는 M-03의 매개변수 테스트로 함께 검증한다.
- **수정 전 결과:** tolerance=0과 2 모두 코어 FALSE 2건이 출력 TRUE 2건으로 바뀌어 2개 실패.
- **수정 후 결과:** 두 허용오차 모두 코어·출력·요약 `(n=2, true=0, false=2)`로 일치한다.
- **관련 기존 테스트 결과:** 전체 검증 결과 절의 전기대사 테스트 참조. 기존 정상 CE·판정 수식·병렬 원문 형식 검사를 유지했다.
- **인접 기능 회귀 테스트:** 완전 대응 CE의 일치·불일치, tolerance 경계 및 초과, 생성 수식의 셀 참조 확인.
- **남은 위험:** 기존에 잘못 TRUE로 생성된 Excel 파일 자체를 자동 수정하지 않는다. 재검증해야 수정된 판정이 적용된다.

## M-03 — tolerance의 코어·Excel·요약 일치

- **기존 재현:** BS와 CE에서 차이 1·2, tolerance=2를 사용했다. 코어는 TRUE인데 최종 Excel 등식과 요약은 FALSE였다.
- **Root cause:** 출력 함수와 수식 평가 함수에 tolerance가 전달되지 않았다. 코어 결과 이후 출력에서 엄격한 등식으로 다시 판정했다.
- **변경 파일:** `dsd_workbench/dsd_tool/recon.py`; 테스트 `dsd_workbench/dsd_tool/tests/test_phase1_recon.py`.
- **변경 내용:** 본문·CE·주석 renderer에 tolerance를 전달한다. ±0의 정상 숫자 비교는 기존 등식을 유지하고 허용오차가 있으면 `ABS(좌측셀-우측셀)<=tolerance`를 생성한다. 복수 조건은 AND로 결합한다. 요약 평가기는 생성된 수식을 같은 허용오차로 평가한다. 기존 행별 FALSE 강조도 이 평가 결과를 따른다. 본문 금액이 두 칸으로 나뉜 양식에서도 임의 열 쌍 대신 기존 코어의 `fs_value_col`로 선택한 금액 셀을 참조한다.
- **추가 regression test:** `test_m03_core_excel_summary_agree` 10개(BS/CE × 일치·엄격 불일치·오차 내·경계·초과), `test_m03_note_formula_matches_core` 5개, `test_m03_four_amount_columns_use_core_selected_cells` 2개. 음수 금액도 포함했다.
- **수정 전 결과:** 초기 BS/CE 테스트에서 tolerance=2의 차이 1·2 사례 4개 실패. tolerance=0·허용범위 초과 등 대조군 6개는 통과했다. 후속 네 금액 열 양식에서 좌/우 위치가 달라 코어 TRUE가 출력 FALSE로 바뀌는 2개 사례를 추가로 재현했다.
- **수정 후 결과:** 생성 Excel 재독 후 판정 건수와 코어·요약이 일치한다. `=ABS(D3-I3)<=2` 및 CE의 복수 셀 AND 수식을 정확한 문자열로 검사한다. 주석의 허용오차도 동일하게 연결된다.
- **관련 기존 테스트 결과:** 실제 삼성 전기대사 `test_recon.py` 6개 통과. 출력 형식·실제 조서 요약 일치·변조 검출 기준은 변경하지 않았다.
- **인접 기능 회귀 테스트:** 정상 BS/CE, 음수, tolerance=0·2, 오차 경계·초과, 주석 표 대사, 미대응 CE와 허용오차의 결합.
- **남은 위험:** Excel 엔진을 직접 실행한 재계산 E2E는 미실시다. 출력 후 사용자가 수식·입력값을 수정하면 서버에 저장된 이전 검증 결과는 자동 재계산되지 않으므로 검증을 다시 실행해야 한다.

## M-04 — XBRL 결과의 세션 귀속

- **기존 재현:** 세션 B 컴포넌트에 전역 작업 목록의 세션 A 완료 결과를 반환하면 A 결과가 복원됐다. 서버는 XBRL 결과를 세션에 저장하지 않았다.
- **Root cause:** UI는 `/api/jobs?kind=xbrl-recon`의 최신 완료 결과를 사용했고 서버 SQL은 `SET recon=recon`이었다.
- **변경 파일:** `auditdesk/jobs.py`, `auditdesk/routers/workbench.py`, `auditdesk/routers/studio.py`, `webui/src/Session.tsx`; 테스트 `tests/test_phase1_integrity.py`, `webui/tests/phase1.test.cjs`.
- **변경 내용:** 별도 `sessions.xbrl_recon` 필드를 추가하고 session ID·DSD·Excel·패키지 경로를 결과와 함께 저장한다. 일반 전기대사 `recon`은 보존한다. UI는 해당 세션 API만 읽고 session ID가 일치하는 결과만 표시한다. 세션 전환은 상태 초기화·늦은 응답 취소로 처리한다. 전역 job fallback은 제거했다.
- **추가 regression test:** `test_m04_result_is_persisted_only_to_own_session`; UI의 타 세션 복원 차단, 자기 세션 복원, 세션 전환 후 늦은 응답 차단.
- **수정 전 결과:** 세션 저장 API 테스트 1개와 타 세션 복원 UI 테스트 1개 실패.
- **수정 후 결과:** A 결과는 A에만 저장되고 B는 결과 없음으로 유지된다. 정상 A 복원은 동작하며 일반 전기대사 결과를 덮어쓰지 않는다.
- **관련 기존 테스트 결과:** 전체 검증 결과 절의 XBRL 대사·속성·인스턴스 테스트 참조.
- **인접 기능 회귀 테스트:** 정상 복원, 일반 전기대사 공존, 빠른 세션 전환, 재추출 시 XBRL 결과 무효화.
- **남은 위험:** 기존 전역 job만 있고 세션 귀속이 저장되지 않은 과거 결과는 추정해 복원하지 않는다. 해당 세션에서 재실행해야 한다.

## M-05 — FALSE 0건과 검증 완료의 구분

- **기존 재현:** TRUE 1행·미매핑/미판정 1행·FALSE 0건에서 FALSE 필터가 빈 목록이 되며 “태깅·본문 전수 일치”를 표시했다.
- **Root cause:** 실패 행이 없다는 조건을 전체 행의 검증 완료로 사용했다.
- **변경 파일:** `webui/src/Session.tsx`; 테스트 `webui/tests/phase1.test.cjs`.
- **변경 내용:** 미매핑 건수·미판정 행·전체/대조 건수 차이를 확인한다. 대상 행이 있고 모든 행이 TRUE이며 건수가 맞을 때만 기존 성공 문구와 성공 표시를 사용한다. 미완료이면 “검증 미완료”와 미매핑/미판정 건수를 표시한다. 기존 FALSE 필터는 유지한다.
- **추가 regression test:** 미매핑 포함 FALSE 0건, 전체 TRUE의 정상 성공 문구, 빈 결과·판정 미정 행의 성공 오표시 차단.
- **수정 전 결과:** 미매핑 사례 1개 실패, 전체 TRUE 대조군 1개 통과.
- **수정 후 결과:** 미판정이 있으면 전수 일치를 표시하지 않는다. 정상 전체 TRUE의 성공 문구는 유지한다.
- **관련 기존 테스트 결과:** 프런트 타입 검사·프로덕션 빌드 및 기존 사용자 용어 검사 통과 여부는 전체 검증 결과 절 참조.
- **인접 기능 회귀 테스트:** 빈 결과, undefined 판정, 정상 완료, FALSE 필터의 빈 화면 안내.
- **남은 위험:** 전수라는 문구는 기존에 화면에 명시된 본문 BS/PL/CF 범위에 대한 것이며 CE 등의 범위를 새로 추가하지 않았다.

## M-06 — 재추출 시 편집본 보존과 종속 상태 무효화

- **기존 재현:** 추출 Excel을 편집하고 diff·repack·foot·recon 결과를 저장한 뒤 같은 세션을 재추출하면 동일 경로에 새 Excel을 써 편집 내용이 사라졌다. 이전 결과 상태도 남았다.
- **Root cause:** 출력 경로가 세션별 고정 이름이며 추출 완료 UPDATE가 이전 종속 결과를 초기화하지 않았다.
- **변경 파일:** `auditdesk/routers/workbench.py`, `auditdesk/routers/studio.py`, `auditdesk/jobs.py`; 테스트 `tests/test_phase1_integrity.py`.
- **변경 내용:** 추출마다 새로운 파일 경로를 생성하고 성공 후에만 세션 입력 경로를 교체한다. diff·diff_options·repack·foot·recon·xbrl_recon을 같은 UPDATE에서 비운다. 이전 입력으로 시작한 diff·검증·반영 작업은 입력 경로가 여전히 동일할 때만 결과를 저장할 수 있다. 추출 이전 NULL 입력 상태도 비교한다.
- **추가 regression test:** 편집본 바이트 보존·새 경로·종속 결과 초기화, 실패한 추출의 이전 상태 보존, 재추출 후 이전 foot 완료 차단, 추출 전 작업 차단, XBRL 결과 초기화, 재추출과 diff 완료 경합.
- **수정 전 결과:** 편집본 바이트 보존 테스트 실패. 후속 NULL 입력 경합 테스트도 수정 전 실패를 확인했다.
- **수정 후 결과:** 이전 편집본은 그대로 존재한다. 새 추출이 성공하면 종속 결과가 비워지고, 늦게 완료된 이전 작업이 이를 복원하지 못한다. 추출 실패 시 이전 파일·세션 상태가 유지된다.
- **관련 기존 테스트 결과:** 전체 검증 결과 절의 추출·왕복 변환·footing·recon·XBRL 검증 참조.
- **인접 기능 회귀 테스트:** 추출 실패, 이전 작업 완료 순서 역전, diff 완료 경합, NULL 입력 경합, 일반 대사·XBRL 결과 초기화.
- **남은 위험:** 보존된 이전 추출 파일은 자동 정리하지 않으므로 디스크 사용량이 늘 수 있다. 경합으로 세션 저장이 거절된 작업이 이미 만든 별도 출력 파일은 남을 수 있지만 현재 세션의 유효 결과로 등록하지 않는다.

## M-07 — 캐시와 작업 자산의 구분

- **기존 재현:** 캐시 아래 세션 DSD·편집 Excel·관련 ZIP과 검색 JSON을 배치한 뒤 삭제하면 모두 제거됐다.
- **Root cause:** 캐시 최상위 항목을 디렉터리 단위 `rmtree`로 삭제해 재다운로드 파일과 사용자 작업물을 구분하지 않았다.
- **변경 파일:** `auditdesk/routers/explorer.py`, `webui/src/Explorer.tsx`; 테스트 `tests/test_phase1_integrity.py`.
- **변경 내용:** 디렉터리 재귀 삭제를 없애고 검색/회사 JSON 및 기존 다운로드 명명 규칙의 원본 ZIP만 파일 단위 후보로 삼는다. DSD·Excel이 있는 작업 폴더, 세션 입력·결과가 참조하는 캐시 경로, 풀린 XBRL 패키지와 미분류 파일은 보존한다. 심볼릭 링크·junction을 따라가지 않는다. 실행 중 작업이 있으면 409로 삭제를 보류한다. UI는 삭제·보존·실패 건수를 표시한다.
- **추가 regression test:** 세션 DSD·편집 Excel·관련 ZIP 보존, 독립된 검색 캐시 및 미참조 다운로드 ZIP 삭제, 풀린 패키지·사용자 문서 보존, 실행 중 작업의 삭제 거절, 사용자 백업 ZIP 보존.
- **수정 전 결과:** 세션 입력·편집본 보존 테스트 실패. 후속 검사에서 캐시 외부 경로의 과도한 보호와 사용자 백업 ZIP의 오삭제도 확인한 뒤 수정했다.
- **수정 후 결과:** 작업 파일은 남고 삭제 가능한 캐시만 삭제된다. 삭제 실패를 숨기지 않고 건수로 반환한다.
- **관련 기존 테스트 결과:** 전체 검증 결과 절의 클라이언트 캐시·공시 래핑·XBRL 패키지 테스트 참조.
- **인접 기능 회귀 테스트:** 캐시 밖 세션 입력이 불필요하게 모든 캐시를 보호하지 않는지, 알 수 없는 ZIP 보존, 활성 job 보호, 실제 다운로드 이름의 정상 삭제.
- **남은 위험:** 안전하게 분류할 수 없는 자료는 삭제하지 않아 캐시가 완전히 비워지지 않을 수 있다. 다운로드 원본과 동일한 경로·이름의 ZIP 자체를 사용자가 직접 덮어쓴 경우에는 파일 생성 이력만으로 이를 구분하는 기능을 추가하지 않았다. 세션에서 참조 중이거나 DSD/Excel 작업물과 함께 있는 파일은 보존한다.

## 전체 테스트 결과

확정된 최종 코드 검증:

| 검증 | 결과 |
|---|---|
| 전체 Python (고유 테스트 ID 376개) | **376 passed / 0 failed / 0 skipped / 0 errors**, 미확인 0 |
| 기존 Python 테스트 | 338 passed (전체 376개에 포함) |
| Phase 1 Python regression | 38 passed |
| 기존 실제 삼성 전기대사 `test_recon.py` | 6 passed |
| 위 두 그룹 합동 실행 | 44 passed, 59.29초 |
| 실제 React 컴포넌트 regression | 6 passed |
| 기존 backend API | 29 passed |
| TypeScript 및 Vite 프로덕션 빌드 | 통과 |
| `git diff --check` | 통과 |

Phase 1 회귀 테스트는 Python **38개**와 UI **6개**로 별도 관리한다. Python 38개는 전체 376개 안에 이미 포함되며 다시 더하지 않는다. M-01 8개, M-02 2개, M-03 17개, M-04 Python 1개/UI 3개, M-05 UI 3개, M-06 6개, M-07 4개다.

관련 기존 테스트 및 인접 workflow의 확인된 결과(아래 수치 역시 전체 집계의 부분집합):

| 관련 Master | 기존 테스트 (`dsd_workbench/dsd_tool/tests/`, 별도 명시 제외) | 결과 / 확인 범위 |
|---|---|---|
| M-01, M-06 | `test_pipeline.py`, `test_offline.py` | 57 + 65 passed; 추출·변경 검출·repack·오프라인 왕복 |
| M-01 | `test_history.py` | 4 passed; 이력 기록·조회 |
| M-02, M-03 | `test_recon.py` | 6 passed; 실제 삼성 전기대사·Excel 출력 |
| M-06 | `test_foot.py`, `test_foot_excel.py` | 10 + 3 passed; 풋팅 코어·Excel 출력 |
| 인접 주석 workflow | `test_note_worksheet.py` | 6 passed; 전수 라우팅·member 정밀도/매칭률·미확정 경고·차원 매핑 |
| 인접 워크시트 workflow | `test_worksheet.py` | 2 passed; 삼성 홀드아웃 본문 매핑률·한빛 워크시트 구조/추적 정보/미완성 경고 |
| M-04, M-06 | `test_succession.py`, `test_v1b.py`, `test_attr_check.py` | 3 + 4 + 3 passed; 승계 입력·대사 인접 속성 검사 |
| M-04, M-05, M-06 | `test_xbrl_recon.py` | 2 passed; 실제 공시 왕복 리포트·단일 팩트 변조 검출 |
| M-05 | `test_glossary_ban.py` | 4 passed; 기존 사용자 용어 기준 |
| M-07 | `dart_explorer/tests/test_client.py`, `test_document_structure.py` | 7 + 4 passed; 캐시·공시 원본 래핑/바이트 동일성 |
| M-07 및 공시 입력 | `dart_explorer/tests/test_xbrl.py` | 6 passed; 실제 파이프라인·오프라인 재실행·캐시 재사용·수동 다운로드 원본 동일성 |
| 인접 택사노미 workflow | `dart_explorer/tests/test_taxonomy_diff.py` | 7 passed; 세대 탐지·실파일 diff·폐지/대체 검출·승격 후보·리포트 통합·CLI |
| 전체 인접 API | `backend/tests/` | 29 passed; 기존 계정·업무·연도·내부통제·PBC API |

마감 시작 시 미확인 **17개를 모두 실행하여 17 passed / 0 failed / 0 skipped**로 확정했다. 새로 발견된 기능 실패가 없어 이번 마감에서는 제품 코드나 테스트를 추가 수정하지 않았다.

전체 수집 목록의 **376개 고유 node ID**를 기준으로 기존 완료 로그와 마감 실행 결과를 연결했다. 중단된 실행의 미완료 테스트를 통과로 간주하지 않았으며, 중복 실행된 ID는 한 번만 집계했다. 전체 테스트를 단일 프로세스에서 한 번 실행했다는 의미가 아니다. 장시간 검증을 파일/독립 그룹별로 분할했고, 필요한 결과가 기록된 프로세스는 별도 실행과 겹치는 구간에서 종료했다. 이때 프로세스 종료 코드 `-1`은 테스트 assertion 실패가 아니며, 기록된 개별 테스트 판정과 구분했다.

| 전체 수집 그룹 | Passed | Failed | Skipped | Errors |
|---|---:|---:|---:|---:|
| `backend/tests/` | 29 | 0 | 0 | 0 |
| `dsd_workbench/dsd_tool/tests/` (Phase 1 대사 19개 포함) | 281 | 0 | 0 | 0 |
| `dart_explorer/tests/` | 47 | 0 | 0 | 0 |
| `tests/test_phase1_integrity.py` | 19 | 0 | 0 | 0 |
| **합계** | **376** | **0** | **0** | **0** |

검증 근거는 [전체 수집 목록](C:/Users/moonyong/Auditing_Package/auditdesk/.pytest_cache/phase1-final-collection.log), [376개 ID별 판정과 출처](C:/Users/moonyong/Auditing_Package/auditdesk/.pytest_cache/phase1-final-node-results.json), [최종 집계](C:/Users/moonyong/Auditing_Package/auditdesk/.pytest_cache/phase1-aggregate.json)에 보존했다. 이 파일과 실행 로그는 기존 ignore 경로 안의 감사 증거이며 제품 변경에 포함하지 않는다. 최종 제품 코드·테스트 10개 파일의 SHA-256이 마감 검증 중 유지된 것도 확인했다.

환경 오류는 기능 실패와 분리했다. 최초 pytest 기본 임시 디렉터리 접근 실패는 저장소 안의 새 `--basetemp`로 해결했다. 기본 샌드박스에서 Python 실행 및 esbuild의 상위 디렉터리 읽기가 제한되어 허용된 실행 방식으로 동일 명령을 재실행했다. 테스트 조건·검증 기준은 낮추지 않았다. 주석 허용오차 테스트에서 첫 데이터 행을 둘째 헤더 행으로 잘못 구성한 픽스처는 기존 두 줄 헤더 구조에 맞게 수정하고 원래 기대 판정을 그대로 검증했다.

마감 실행에는 `-o faulthandler_timeout=180`을 사용해 장시간 계산의 스택만 기록했다. 로그의 `Timeout (0:03:00)!`는 테스트를 종료하거나 실패 처리한 timeout이 아니다. 확인된 스택은 기존 택사노미 승격 탐지 및 주석/본문 추천의 `_levenshtein` 계산이었다. 성능 개선은 이번 범위 밖이므로 코드를 바꾸거나 벤치마크 기준을 낮추지 않았다.

재실행 명령(각 `--basetemp`는 기존 작업 파일이 없는 새 테스트 전용 경로를 사용):

```powershell
# cwd: auditdesk
python -m pytest --collect-only -q
python -m pytest -vv --tb=short --basetemp=.pytest_cache/phase1-all-new
python -m pytest tests/test_phase1_integrity.py dsd_workbench/dsd_tool/tests/test_phase1_recon.py dsd_workbench/dsd_tool/tests/test_recon.py -q --tb=short --basetemp=.pytest_cache/phase1-verify-new
# cwd: auditdesk/backend
python -m pytest -q --tb=short --basetemp=../.pytest_cache/phase1-backend-new
# cwd: auditdesk/webui
node --test tests/phase1.test.cjs
npm run build
```

## Git diff 요약

제품 파일 7개에서 **228줄 추가 / 96줄 삭제**. 신규 테스트는 Python 2개(369줄), Node 1개(84줄)이며 이 보고서가 추가된다. 기존 테스트 파일은 수정하지 않았다.

최종 A/B 변경량은 **11개 파일, +956 / -96**이다. 신규 테스트 453줄과 본 보고서 275줄을 포함한 수치이며, 기존 사용자 변경과 기존 42개 커밋은 제외했다.

| 파일 (`auditdesk/` 기준) | 추가 | 삭제 | Master |
|---|---:|---:|---|
| `auditdesk/jobs.py` | 4 | 1 | M-01, M-04 |
| `auditdesk/routers/explorer.py` | 51 | 13 | M-07 |
| `auditdesk/routers/studio.py` | 6 | 3 | M-04, M-06 |
| `auditdesk/routers/workbench.py` | 70 | 13 | M-01, M-04, M-06 |
| `dsd_workbench/dsd_tool/recon.py` | 65 | 50 | M-02, M-03 |
| `webui/src/Explorer.tsx` | 2 | 2 | M-07 |
| `webui/src/Session.tsx` | 30 | 14 | M-01, M-04, M-05 |

신규 파일: `tests/test_phase1_integrity.py`, `dsd_workbench/dsd_tool/tests/test_phase1_recon.py`, `webui/tests/phase1.test.cjs`, `AUDITDESK_PHASE1_REMEDIATION_REPORT.md`.

### A. Phase 1 제품 코드 수정

위 표의 7개 제품 파일만 해당한다. 합계 **+228 / -96**이며 이번 최종 마감에서는 제품 코드를 추가 수정하지 않았다.

### B. Phase 1 regression test / 보고서

| 신규 파일 (`auditdesk/` 기준) | 용도 |
|---|---|
| `tests/test_phase1_integrity.py` | M-01 8개, M-04 1개, M-06 6개, M-07 4개: Python 19개 |
| `dsd_workbench/dsd_tool/tests/test_phase1_recon.py` | M-02 2개, M-03 17개: Python 19개 |
| `webui/tests/phase1.test.cjs` | M-04 3개, M-05 3개: UI 6개 |
| `AUDITDESK_PHASE1_REMEDIATION_REPORT.md` | 본 보고서 |

세 테스트 파일은 총 453줄이다. 모두 신규 미추적 파일이므로 일반 `git diff --stat`에는 아직 표시되지 않는다. stage하지 않고 변경 목록과 파일 내용을 별도로 검토했다.

### C. Phase 1과 무관하거나 임시 생성된 변경

기존 사용자 변경은 삭제·복원·이동하지 않았다. 아래 파일은 A/B의 변경량에 포함하지 않는다.

| 파일 (저장소 루트 기준) | 분류와 발생 경위 | 처리 |
|---|---|---|
| `CLAUDE.md` | 작업 시작 전부터 있던 추적 파일 변경, +72 / -22 | 원상 보존 |
| `auditdesk/FEATURE_ARCHAEOLOGY_REPORT.md` | 작업 시작 전부터 있던 감사 보고서, 미추적 519줄 | 원상 보존 |
| `auditdesk/REQUIREMENTS_GAP_AUDIT_20260908.md` | 작업 시작 전부터 있던 감사 보고서, 미추적 275줄 | 원상 보존 |
| `auditlink-v2/.claude/launch.json` | 기존 별도 프로젝트 실행 설정, 미추적 19줄 | 원상 보존 |
| `DSD_footing/.claude/settings.local.json` | 기존 개인 설정. 전역 ignore를 읽지 못하는 제한 실행에서는 미추적으로 보이나 정상 Git 실행에서는 제외됨 | 원상 보존, 내용 미출력 |

생성 파일과 기존 로컬 자산은 다음과 같이 별도 점검했다. 대용량 자료가 있다는 이유로 사용자 자산을 삭제하지 않았다. 이번 작업이 만든 과거 pytest 전용 디렉터리 **15개 / 파일 700개 / 48,538,610 bytes**만 정리했다. 각 삭제 대상의 절대 경로가 `auditdesk/.pytest_cache/` 안에 있는지, reparse point가 없는지 확인했다. 결과 로그·집계 파일은 해당 디렉터리 밖에 그대로 보존했으며 실행 중 테스트 디렉터리는 건드리지 않았다. 정리 이력은 ignored 경로 `.pytest_cache/phase1-cleanup.json`에 남겼다.

| 점검 대상 (`auditdesk/` 기준) | 발생 경위 / Git 상태 | 처리 |
|---|---|---|
| `.pytest_cache/phase1-*` | 회귀 재현·전체 검증의 임시 Excel, DSD, DB, JSON/XML, 로그 및 집계 자료. 기존 `.pytest_cache/` 규칙으로 제외 | 검증 증거 로그와 집계는 로컬에 보존; 코드 변경에서 제외 |
| `.test_results.json` | 기존 pytest summary hook의 최근 실행 결과. 기존 ignore 대상 | 코드 변경에서 제외 |
| `dsd_workbench/dsd_tool/fixtures/_work/`, `fixtures/verify_g3/`, `dsd_workbench/history/` | 기존 테스트/벤치마크 및 이력 산출 위치. 기존 ignore 대상 | 사용자 자료 혼재 가능성이 있어 일괄 삭제하지 않음 |
| `dart_explorer/cache/`, `dart_explorer/corpus/`, `dart_explorer/taxonomies/` | 기존 공시 입력·코퍼스·택사노미와 테스트가 사용하는 로컬 데이터. 기존 ignore 대상 | 보존; 제품 변경에서 제외 |
| `auditdesk/data/` | 앱의 세션 DB·사용자 작업 산출물. 기존 ignore 대상 | 보존; 제품 변경에서 제외 |
| `auditdesk/static/` | Vite production build가 생성한 HTML/CSS/JS. 기존 ignore 대상 | 빌드 확인용으로 보존; 제품 변경에서 제외 |
| `webui/node_modules/`, `frontend/node_modules/`, `backend/.venv/`, `__pycache__/` | 설치 의존성·런타임 바이트코드. 기존 ignore 대상 | 보존; 제품 변경에서 제외 |
| `webui/tsconfig.tsbuildinfo` | 기존부터 추적하는 TypeScript 빌드 정보 파일 | 최종 빌드 후 Git diff 없음; 삭제하지 않음 |
| visualization / scratch / 감사용 임시 산출물 | A/B 외 신규 Git 변경 목록에서 이번 작업이 만든 해당 파일 없음 | 추가 제품 변경 없음 |

`git status --porcelain=v1 --untracked-files=all`, `git diff --stat`, `git diff --numstat`, 미추적 파일 전수 목록, `git check-ignore -v`, staged diff를 확인했다. **작업 트리의 추적 파일 변경은 8개, +300 / -118**이며 A의 +228 / -96과 기존 사용자 `CLAUDE.md`의 +72 / -22로 정확히 분리된다. 신규 파일은 위 B 4개와 기존 사용자 C 3개다. ignored 파일은 일반 Git 변경량에 합산하지 않았다.

### +104,512 / -272의 정확한 구성

브랜치의 시작 커밋은 `62762e5`이며 로컬 `main`, `test/astra-history-audit`와 같다. 로컬에 저장된 `origin/main`은 `7cd756b`이므로 이미 **42개 기존 커밋**의 차이가 있다. 네트워크 fetch나 기존 커밋 변경은 하지 않았다.

| 비교 구성 | 추가 | 삭제 | Phase 1 귀속 |
|---|---:|---:|---|
| `git diff origin/main...HEAD`: 기존 42개 커밋, 257개 파일 | 102,795 | 154 | C: 작업 이전 이력 |
| 현재 작업 트리의 추적 파일 8개 | 300 | 118 | A + 기존 사용자 `CLAUDE.md` |
| 마감 시작 시 미추적 7개 파일의 전체 줄 수 | 1,417 | 0 | B + 기존 사용자 C |
| 합계 | **104,512** | **272** | 사용자 표시 수치와 정확히 일치 |

마감 시작 시 미추적 줄 수는 보고서 151 + Python 테스트 273/96 + UI 테스트 84 + 기존 감사 보고서 519/275 + 기존 실행 설정 19 = **1,417**이다. 이후 본 보고서의 보강만큼 신규 줄 수는 증가한다. 이는 테스트 생성 파일이 추가되는 현상이 아니다.

기존 커밋에 포함된 아래 **PDF.js vendor 빌드 2개만 92,845줄**이다. 작업 트리에서 새로 생성·수정된 파일이 아니므로 삭제하지 않았다.

| 기존 추적 파일 (저장소 루트 기준) | 기존 커밋의 추가 줄 수 | 처리 |
|---|---:|---|
| `DSD_footing/ui/web/vendor/pdfjs/build/pdf.worker.mjs` | 64,857 | C: 기존 다른 프로젝트의 vendor, 보존 |
| `DSD_footing/ui/web/vendor/pdfjs/build/pdf.mjs` | 27,988 | C: 기존 다른 프로젝트의 vendor, 보존 |

동일한 기존 커밋 범위의 `.bcmap` 168개, `.pfb` 10개, `.ttf` 4개, `.woff2` 2개와 PDF 2개도 기존 추적 자산이다. JSON 6개는 `DSD_footing/ERRORS.json`, `GATES.json`, `RENDER_GATES.json`, `labels/_common.json`, `labels/조선내화.json`, `ui/glyph_offsets.json`이다. 기존 검증/렌더링 데이터와 설정을 이번 테스트가 생성한 JSON으로 오인해 삭제하지 않았다. 이 257개 이력 차이에는 `.xlsx`, `.xml`, `.db`, `.sqlite` 또는 `.log` 확장자의 파일은 없다.

257개 기존 변경 파일의 전수 목록·추가/삭제 수와 위 산식은 [브랜치 비교 조사 원본](C:/Users/moonyong/Auditing_Package/auditdesk/.pytest_cache/phase1-branch-comparison-audit.json)에 보존했다. 따라서 Phase 1 검토 기준은 시작 커밋 `62762e5` 대비 A/B이며, 원격 기준의 기존 42개 커밋을 Phase 1 변경으로 합산하면 안 된다. 기존 이력을 reset·rebase하거나 vendor/사용자 파일을 삭제해 화면 수치만 줄이는 작업은 하지 않았다.

빌드 산출물·테스트 임시 파일을 추적 대상으로 추가하지 않았다. 기존 테스트 및 ignore 규칙도 변경하지 않았다. stage·commit·push는 수행하지 않았다.

## Phase 1 completion status

- M-01: PASS
- M-02: PASS
- M-03: PASS
- M-04: PASS
- M-05: PASS
- M-06: PASS
- M-07: PASS
- Full Python suite: **376 passed / 0 failed / 0 skipped / 0 errors**; 고유 테스트 기준, 미확인 0.
- UI regression: **6 passed / 0 failed / 0 skipped**.
- Production build: **PASS**, `tsc -b && vite build`.
- Unexpected files: Phase 1 제품 변경에 예상 밖 생성 파일 없음. 기존 C 변경/42개 커밋은 보존하고 과거 테스트 임시 파일 700개만 정리. +104,512/-272의 구성을 위에서 전수 분리했다.
- Remaining risks: Excel 엔진 직접 재계산 E2E 미실시, 승인 해시를 생략한 기존 API의 최신 서버 diff 승인 의미 유지, 이전 작업 파일 보존에 따른 디스크 사용량 증가, 안전하게 분류할 수 없는 캐시의 보존. Master별 상세 위험 참조.

Phase 1 검증 및 보고를 완료했으며 사용자 검토를 위해 커밋·push 없이 중단한다.
