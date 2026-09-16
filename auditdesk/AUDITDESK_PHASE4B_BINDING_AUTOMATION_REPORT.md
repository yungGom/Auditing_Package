# AuditDesk Phase 4B Binding Automation Report

최종 확정: 2026-09-16. 전체 Python 491개 고유 테스트의 결과를 대조했으며 491 passed / 0 failed / 0 skipped / 0 errors, 미확인 0개다. 자동 후보/사용자 검토 연결의 완료와 코스맥스 전체 42시트의 실제 검토 완료는 구분한다. Commit/push하지 않았다.

## 1. 범위와 설계 결정

- Current-first / Prior-assisted 유지. 전기 파일은 필수 입력이 아니다.
- Phase 4 `golden.py` writer는 변경하지 않는다. 실제 BIFF8 `.xls`를 생성한다.
- 자동 확정은 제공하지 않는다. 높은 확신도의 후보도 사용자가 선택하고 확정한다.
- 기존 Studio의 계정 매핑 화면 안에 **제출 준비 · Golden binding** 검토 패널을 연결한다. 기존 계정 추천/확정 화면은 유지한다.
- Footing/Prior/V-1/V-2/Guide Check/Mapping Sheet와 제출 준비 파일을 구분한다. 검토 정보는 별도 `review.json`에만 기록한다.
- 제공된 당기 배치의 셀을 검토 대상으로 삼는다. 다른 회사 Golden 좌표를 DSD의 정답 위치로 간주하지 않는다. 후보의 표시값 일치만으로 연결하지 않는다.

## 2. Binding data model

검토 작업은 앱의 SQLite에 독립 ID로 저장된다. 회사, 연결/별도, 당기 기말, 기수, 명시적 비교기말과 DSD/taxonomy/layout SHA256을 보관한다. 선택적 현재 원천 index도 hash에 포함한다.

| 대상 | 저장 내용 |
|---|---|
| DSD 원문 | 원문 문자 구간, 표 시작/끝을 포함한 block ID, 표 번호, 병합을 반영한 행/열, 원문 표시 문자열, 행 레이블, 선행 열 헤더, 본문/주석 구분 |
| taxonomy 출현 | 시트+행 ID, Role URI/Definition, Prefix, Name, KO/EN Label, Label Role, DataType, Balance, Period, 알려진 scope |
| 후보 | 해당 출현 전체, 기존 문자열 유사도 score, evidence, ambiguity reasons, confidence, dimensions(알 수 없으면 null) |
| 대상 배치 | 시트/행/열, 참고 표시값, 행/열축 문구, 기간 블록 후보, 원문 후보와 근거; 불명확한 구성요소/비교기간 위치는 unverified |
| 결정 | 원문 ID, taxonomy 출현 ID, 시점 또는 시작/종료, 회사/scope/단위/차원, 검토 근거, 수동 여부, 검토자/시각, source block ID |
| 동시 수정 | revision 비교; 다른 검토가 먼저 저장되면 409로 거부하고 재조회 요구 |

같은 QName이 BS와 주석, 서로 다른 Role이나 기간에서 반복되어도 전역 dedupe하지 않는다. 저장된 결정은 특정 당기 원천 snapshot과 보고 문맥에 속한다.

## 3. Candidate generation strategy

기존 `dsd_tool.mapping.normalize/similarity`를 재사용한다. 기존 코퍼스의 빈도/추천 알고리즘은 변경하지 않는다. 현재 `.xls`에 실제 존재하는 출현을 대상으로 QName 근거, Role 근거, 알려진 문맥의 불일치, 기존 문자열 유사도, 안정된 시트/행 순서를 사용해 정렬한다. 별도의 임의 회계 가중합을 정답 알고리즘으로 도입하지 않는다.

DSD 표의 grid는 기존 scanner의 ROWSPAN/COLSPAN 처리를 재사용한다. 배치 후보는 원문 행 레이블과 대상 행축 레이블, 열 헤더의 겹침을 사용한다. 금액이 같다는 이유로 셀을 선택하지 않는다. 행/열축 방향, 당기/비교기간, 차원 관계는 사용자가 검토해야 한다.

현재 XBRL/회사 확장 원천을 검토한 index를 선택적으로 제공할 수 있다. 이번 구현은 XBRL/IXD 패키지 자체를 새로 파싱하지 않는다. index는 `dsd_sha256`, `taxonomy_sha256`, `report`, `facts`를 가지며 fact는 `source_id`(시작:끝), `source_evidence`, 선택적 prefix/name/role/data_type/period/dimensions/context를 가진다. 다른 snapshot/report의 index는 거부한다. 이 index는 원천 검토의 기록이지 instance ID 복원 도구가 아니다.

## 4. Confidence / ambiguity

- High: exact current QName과 Role/DataType/Period/dimensions 일치, 알려진 scope와 충돌 없음. 실제 확정은 여전히 사용자 동작이다.
- Medium: 레이블 등 근거는 있으나 하나 이상의 문맥이 미확정이다.
- Low: 확인 가능한 기간/자료형/차원 문맥 등이 불일치한다.
- taxonomy export에 instance의 차원 조합이 없으면 `dimensions=null`이다. 빈 배열로 추정하지 않는다.
- 동일 레이블/복수 Role은 복수 후보로 남기고 화면에 근거와 모호성 사유를 표시한다.
- 회사 확장 Prefix/Name을 그대로 보존한다. namespace/schema ID/contextId/unitRef/calculation 관계를 생성하지 않는다.

## 5. 사용자 검토 workflow

1. **XBRL 작성 지원 → 계정 매핑 확정 → 제출 준비 · Golden binding**에서 시작한다.
2. 당기 DSD, 당기 taxonomy.xls, 현재 회사의 배치.xls, 회사/scope/보고기말/기수/비교기말을 입력한다. 검토한 현재 원천 index와 이전 저장 검토는 선택 입력이다.
3. **자동 후보 생성**을 실행한다. 처리 중 표시와 중복 요청 방지, 오류 메시지 및 같은 화면의 재실행 경로를 제공한다.
4. 미확정 또는 전체 목록에서 대상 셀을 선택한다. 같은 화면에서 DSD 원문, taxonomy Top N 및 근거, Golden 대상 위치를 비교한다.
5. 원문을 검색하거나 배치 후보를 선택한다. taxonomy 후보 또는 현재 taxonomy의 다른 출현을 수동 선택한다. 대상 셀 선택도 변경할 수 있다.
6. 기간/단위/차원을 검토하고 검토 근거를 입력한 뒤 **검토 확정 · 저장**한다. 정적 셀은 실제 DSD 원문 셀을 선택하며, 샘플 표시값 대신 그 원문을 사용한다.
7. **확정 취소 · 미확정으로** 되돌릴 수 있다. 저장된 검토 목록에서 다시 불러온다.
8. coverage gate가 통과하면 새 출력 폴더를 지정하고 **검토 완료 Golden 생성**을 실행한다. taxonomy.xls / Excel.xls / 별도 review.json 경로와 파일 열기를 제공한다. 기존 폴더는 덮어쓰지 않고 새 경로로 재실행한다.

상태는 자동 후보·미확정, 원천 부족·미확정, 사용자 확정, 수동 지정, 충돌, 원천 변경·재검토로 표시한다. 불확실한 결정을 강제로 저장해 성공 상태로 표시하지 않는다. 잘못된 결정은 422로 거부한다.

## 6. Coverage gate

필수 대상은 Phase 4 writer와 동일하게 layout의 저장 STRING 셀 전체다. 제목/빈 문자열도 포함하고 BIFF BLANK는 구분한다.

지표: required, confirmed, unresolved, conflicts, static_without_evidence, taxonomy_unresolved, period_unresolved, dimension_unresolved, stale, ready.

완전 생성 조건은 필수 대상 수 > 0, confirmed = required, conflicts = 0, 현재 원천 hash 일치다. 결정마다 정확한 DSD 원천, taxonomy 출현, 알려진 타입/기간/회사/scope/차원 검토를 다시 검사한다. 미확정 셀은 보수적으로 taxonomy/기간/차원도 미확정으로 계산한다. 따라서 부분 항목 합계는 서로 독립된 지표이며 합산하면 안 된다.

정적 셀도 원문 구간과 검토 근거가 필요하다. 근거 문구만 적고 샘플 제목/금액을 남기는 것은 허용하지 않는다. 생성 직전에 원천 bytes를 다시 읽어 hash를 확인한다. 검증한 bytes를 임시 입력으로 넘겨 검토와 writer 입력 사이 파일 변경을 차단한다.

`ready`/`complete`는 명시된 배치의 사용자 검토 연결이 완료되었다는 뜻이다. XBRL instance의 법정 제출 적합성, 전체 차원 네트워크, 실제 DART 편집기 호환성까지 인증하는 것은 아니다.

## 7. Stale / version handling

- DSD, taxonomy, layout, 선택적 current source index 변경 또는 읽기 불가 → stale.
- stale 상태에서 확정/생성 차단. 새 원천으로 새 후보를 만들고 재검토한다.
- 이전 검토 재사용은 같은 회사/scope에서만 허용한다. 예전 QName/Role/원문 레이블/block ID/보고 문맥/hash를 참고 후보로 보여주고 결정은 빈 상태에서 시작한다.
- 이전 좌표나 context를 당기에 자동 적용하지 않는다. 현재 taxonomy에 없는 요소를 수동 선택할 수도 없다.
- revision 검증과 SQLite 트랜잭션으로 동시 검토 결과의 덮어쓰기를 방지한다.

## 8. Golden writer 연결

`binding.generate`가 검토된 binding과 원문으로 검증한 static cell을 기존 `golden.build_current`에 전달한다. 기존 writer 코드는 수정하지 않는다. 원문으로 갱신한 정적 표시를 포함한 임시 layout을 사용하며, review에는 원본 세 입력의 hash와 사용자 결정을 별도로 보존한다.

금액 문자열, 괄호 음수, 빈 문자열, 병합/서식은 writer 계약을 따른다. 미확정 값은 샘플/0으로 채우지 않는다. 출력 파일에 수식이나 승인 컬럼을 추가하지 않는다.

## 9. 실자료 probe

코스맥스 당기 DSD와 제공된 taxonomy/Excel Golden을 읽기 전용 원천으로 사용했다. Golden 원본은 수정하지 않는다. 일부 현금/차원 표 점검을 전체 42시트 자동화 완료라고 표현하지 않는다.

| 측정 | 결과 |
|---|---:|
| DSD 셀 | 5,732 |
| 현재 taxonomy LINEITEM 출현 | 1,346 |
| 회사 확장 출현 | 67 |
| 필수 출력 STRING 셀 | 5,638 |
| 원문 배치 후보가 제안된 대상 셀 | 3,191 |
| 사용자 확정 | 0 |
| 미확정 | 5,638 |
| 충돌 | 0 |
| 원천 변경 | 없음 |
| 완전 생성 gate | 차단 |
| 전체 후보 생성 시간 | 266.02초 (전체 suite 동시 실행 환경) |

배치 후보 3,191건은 확정 coverage가 아니다. 확정 coverage는 0/5,638다. 실행 시 레이블을 대상 셀마다 반복 정규화하는 병목을 확인했고, 원천 레이블을 한 번만 정규화한 조회 index로 변경했다. 기존 문자열 유사도 계산은 유지했다.

최종 taxonomy 출현은 연결 714개, 별도 632개다. 연결 DSD의 모든 추천 후보에 별도 출현이 없음을 검사했다. 회사 확장 67개는 실제 `entity01009789` Prefix와 Name을 유지한다.

### 현금 본문/주석 및 비교기간

| 위치 | DSD 원문 구간 | 표시값 | 검토 기간 |
|---|---|---|---|
| 재무상태표 (연결) B8 | 14498:14513 | 336,726,180,991 | 2026-06-30 |
| 재무상태표 (연결) C8 | 14578:14593 | 192,279,928,597 | 2025-12-31 |
| 3. 현금및현금성자산 (연결) B8 | 151301:151316 | 336,726,180,991 | 2026-06-30 |
| 3. 현금및현금성자산 (연결) B15 | 151381:151396 | 192,279,928,597 | 2025-12-31 |

당기 및 전기말의 본문/주석 값은 각각 일치했다. 같은 `ifrs-full:CashAndCashEquivalents`를 본문 taxonomy 7행과 주석 11행의 서로 다른 Role 출현으로 선택하는 메모리 내 통합 probe를 통과했다. 이 4개는 시험용 결정이며 사용자 승인이나 DB에 저장하지 않았다. 시험 상태에서도 4/5,638만 연결되어 완전 생성은 차단됐다. 실제 사용자 확정 수는 여전히 0이다.

본문 B8/C8의 첫 배치 후보는 각각 당기/전기말 DSD 금액 셀이었다. 반면 주석 DSD의 일반적인 `합 계` 레이블은 현금 Role을 상위 후보로 올리지 못했고, Golden의 `현금및현금성자산 합계`와도 정확 일치하지 않아 배치 후보가 없었다. 현재 taxonomy에서 수동 선택하는 경로로 검증했으며, 이를 자동 매칭 성공으로 집계하지 않는다.

### 다차원 및 자동 확정하지 않은 사례

CE 원문 `48777:48791`은 전기초 행의 `55,984,447,763`이며 열 헤더는 `지배기업의 소유주에게 귀속되는 자본` / `기타포괄손익 누계액`이다. 행/열 원문은 보존됐지만 taxonomy 후보는 없고 dimensions는 null로 남았다. 축/member를 추정하거나 빈 차원으로 승인하지 않았다. 실제 다차원 표의 완전 연결은 미검증이다.

동일 현금 QName의 본문/주석/금융상품 Role 후보, 일반 합계 레이블, CE 차원 미확정, 현재 원천 없이 판단할 수 없는 기간/단위는 모두 사용자 검토 대상으로 남겼다. Golden 샘플 값으로 coverage를 채우지 않았다.

## 10. 테스트와 수정 전 결과

- 최초 제품 연결 테스트 12개: 모듈/라우터 부재로 12 failed 확인 후 구현.
- 최초 UI 테스트 3개: 검토 패널 부재로 3 failed 확인 후 구현.
- 잘못된 DSD 입력: 실제 500 예외 재현 후 구체적인 422 오류로 수정.
- 알려진 당기 QName와 다른 요소 선택, 다른 scope 배치 선택: 각 실패 재현 후 확정 단계 차단.
- 현재 추가 Python regression은 후보 exact QName/복수 Role/타입·기간·차원 충돌/확장·scope/저장·취소/hash 변경/99% gate/100% 생성/샘플 미복사/정렬 재현/재사용 미승계/동시 수정/API 실파일 생성·재실행을 포함한다.
- 영문 DSD 레이블 후보 누락 및 반복 정규화 테스트 각 1건 실패를 확인한 뒤 수정했다.
- 실자료에서 별도 주석의 영문 `Separated financial statements`를 scope로 인식하지 못한 문제를 확인했다. 영문 연결/별도와 DSD 본문 scope 충돌 테스트 3개 실패를 확인한 뒤 수정했다. 최종 Phase 4B Python 25개가 통과했다.

최종 전체 테스트 ID와 결과를 대조한다. 중복 실행된 Phase 4B는 최종 결과로 대체하고 합산하지 않는다. 실행 로그, JUnit, 임시 파일은 `.pytest_cache/phase4b`에 분리하며 제품 변경에 포함하지 않는다.

| 검증 | 최종 확인 결과 |
|---|---|
| Phase 1 Python regression | 38 passed |
| Phase 2 Python regression | 56 passed |
| Phase 3 Python integration | 15 passed |
| Phase 4 Golden regression | 18 passed |
| Phase 4B binding regression/integration | 25 passed |
| Full Python suite | 491 passed / 0 failed / 0 skipped / 0 errors; 미확인 0 |
| UI regression (Phase 1/2/3/4B) | 19 passed / 0 failed (6+7+3+3) |
| TypeScript | PASS |
| Production build | PASS |
| 실제 브라우저 시각 검증 | NOT TESTED |

UI 검증은 React 컴포넌트를 transpile한 hook/event harness로 요청 실패 후 재시도, 중복 요청 방지, gate, 원문·후보·근거 표시와 확정 취소를 검사한다. 실제 브라우저 화면 및 Excel/DART 확인을 대체하지 않는다. 브라우저 검증은 도구 승인 서비스의 일시적 용량 오류로 완료하지 못했고, 임시 서버는 종료했다.

전체 suite는 최종 수집한 491개 고유 test ID를 기준으로 집계한다. 장시간 그룹 재실행 중 5분 faulthandler 진단 출력에서 주석 테스트 프로세스가 Windows access violation(종료 코드 3221225477)으로 중단됐다. assertion 실패 결과로 해석하지 않으며, 진단 플러그인만 비활성화한 동일 6개 테스트를 다시 실행했다. 재실행은 **6 passed, 종료 코드 0, 1,793.74초**였다. 테스트 코드·기준은 변경하지 않았다. 중단 실행은 최종 passed/failed/skipped 합계에 더하지 않는다.

제품을 import하지 않는 3초 독립 faulthandler probe에서는 접근 위반이 재현되지 않았다. 따라서 진단 출력 시점의 관찰로 기록하며 런타임 문제라고 확정하지 않는다. 원인 미확정의 실행 환경 위험으로 남긴다.

최종 장시간 묶음은 taxonomy **7 passed (2,495.95초)**, 주석 **6 passed (1,793.74초)**, worksheet **2 passed (2,334.24초)**다. 모두 최종 실행 종료 코드 0이다. 나머지 묶음 468개에서 이전 Phase 4B 17개를 제외한 451개에, 최종 Phase 4B 25개와 위 15개를 더해 **451 + 25 + 15 = 491개**로 집계했다. 중복·중단 실행은 더하지 않았다. 최종 소스 hash가 검증 대상과 일치하고 수집한 모든 ID에 정확히 하나의 최종 결과가 있음을 확인했다.

## 11. 남은 미확정 영역 / Case A 전체 자동화

- DSD 레이블/헤더가 Golden 행축과 다른 경우 자동 배치 후보가 없을 수 있다. 사용자 수동 연결 경로는 제공한다.
- 기간 문구의 뜻과 비교기간 위치, 다차원 축 방향은 현재 원천 검토가 필요하다. 상충하거나 원천이 없는 항목은 자동 확정하지 않는다.
- taxonomy export만으로 instance 차원 조합이나 calculation 네트워크를 증명할 수 없다. 현재 원천 index가 없으면 관계의 타당성은 사용자 검토 범위다. 차원 축/member는 같은 Role에서 실제 등장하는 DOMAIN 이름으로 제한한다.
- current XBRL/IXD 원천의 자동 수입, 미매칭 표의 의미 구조 분석, 전체 42시트에 대한 회계사 검토는 이번 자동 후보/검토 연결만으로 완료되지 않는다.
- 현재 검토는 하나의 scope를 대상으로 한다. DSD 본문에 연결/별도가 혼재하거나 선택한 scope와 다르면 원천 분리를 요구한다. 범위가 명시된 영문 Role Definition도 연결/별도 혼입 차단에 사용한다.
- 정적 표시 셀은 선택한 DSD 원문을 그대로 사용한다. 번호/문구/공백을 Golden 표현으로 자동 변환하는 별도 규칙은 추가하지 않았다.
- 실제 Excel/DART 편집기에서 시각·제출 호환성을 검증하지 않았다.
- 실자료 후보 생성은 약 266초의 동기 요청이다. 처리 중/재시도는 제공하지만 비동기 job 진행률이나 대규모 검토 사용성은 이번 범위에서 검증하지 않았다.
- 진단 출력 중 발생한 일회성 접근 위반은 동일 테스트 재실행에서 발생하지 않았으나 근본 원인은 확정하지 못했다.
- 기존 Phase 4의 미커밋 변경과 기존 사용자 변경은 보존한다. 이번 작업도 commit/push하지 않는다.

## 12. 변경 파일

제품: `auditdesk/binding.py`, `auditdesk/routers/binding_api.py`, `auditdesk/app.py`, `webui/src/BindingReview.tsx`, `webui/src/Studio.tsx`.

회귀 테스트: `tests/test_phase4b_binding.py`, `webui/tests/phase4b.test.cjs`.

보고서: `AUDITDESK_PHASE4B_BINDING_AUTOMATION_REPORT.md`.

Phase 4의 writer/CLI/dependency/test/report 변경은 이전 작업에서 이월된 미커밋 변경이다. `CLAUDE.md`, 기존 감사 보고서, `auditlink-v2/.claude/`, `DSD_footing/.claude/`는 이번 변경 대상이 아니다.

기존 사용자 파일 5개는 작업 전 SHA256과 일치했다. Golden taxonomy/Excel 원본도 hash가 유지됐다. `.pytest_cache/phase4b`의 JUnit/log/DSD/Excel/JSON/임시 SQLite와 `webui/dist`는 ignore 대상으로 확인했다. 빌드가 갱신했던 추적 파일 `tsconfig.tsbuildinfo`는 작업 시작 시 깨끗했음을 확인한 뒤 그 생성 변경만 복구했다. 사용자 파일은 삭제하거나 정리하지 않았다. staged 파일은 없다. 신규 파일을 포함한 diff 공백 검사는 통과했다.

## 13. 최종 Git 검토와 검증 근거

- 현재 브랜치: `feat/auditdesk-binding-automation`.
- Phase 4B 제품 5개 + 테스트 2개 + 이 보고서 1개. 제품/테스트 7개만의 변경량은 **+871 / -1**, 보고서는 별도 신규 파일이다.
- 이월된 Phase 4 변경은 writer/CLI/dependency/test/report 5개, **+729 / -0**이며 이번 Phase 4B 구현과 구분한다.
- 일반 `git diff --stat`은 추적 파일만 표시하므로 **5 files, +111 / -23**이다. 이 수치에는 기존 사용자 `CLAUDE.md`(+72/-22)와 Phase 4 CLI/dependency(+25/-0)가 포함되고, 신규 파일은 빠진다. 이를 Phase 4B 변경량으로 보고하지 않는다.
- 사용자 `CLAUDE.md`, `FEATURE_ARCHAEOLOGY_REPORT.md`, `REQUIREMENTS_GAP_AUDIT_20260908.md`, 두 프로젝트의 기존 `.claude/` 변경은 보존했다. 검증 생성물과 기존 사용자 변경은 제품 변경 범위 밖이다.
- 재현/결과 근거는 `.pytest_cache/phase4b/`의 `final-results.json`, `final-nodeids.json`, `final-source-hashes.json`, `remaining.xml`, `final-binding.xml`, `taxonomy.xml`, `notes.xml`, `worksheet.xml`, `cosmax-probe.json`, `cash-review-probe.json`에 분리했다. 이들은 commit 대상이 아니다.
- `git diff --check`: PASS. Commit/push/staging: 없음.

## Phase 4B completion status

- M-37: 구현 및 회귀 PASS; 실자료 연결/별도 후보 분리 확인
- M-38: 보수적 후보 생성 PASS; 전체 배치 자동 확정 아님
- M-39: UI 동작 회귀 PASS; 실제 브라우저 시각 확인 미완료
- M-40: 회귀 PASS; 실자료 0/5,638 확정에서 생성 차단
- M-41: 저장/재조회/재검토/동시 수정 회귀 PASS
- M-42: 실제 BIFF8 생성 및 재실행 통합 회귀 PASS
- Binding coverage: 실자료 사용자 확정 0/5,638; 후보 제안 3,191개와 구분
- Golden generation gate: fixture 100% 생성 / 99% 차단; 실자료 및 시험용 4개 연결 상태에서 차단
- Full Python suite: 491 passed / 0 failed / 0 skipped / 0 errors; 미확인 0
- UI regression: 19 passed / 0 failed
- TypeScript: PASS
- Production build: PASS
- git diff --check: PASS
- Remaining risks: 위 11절; 실제 전체 42시트 검토 완료와 구분
