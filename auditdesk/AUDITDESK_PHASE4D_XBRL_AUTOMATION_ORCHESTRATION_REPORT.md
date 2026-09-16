# AuditDesk Phase 4D XBRL Automation Orchestration Report

작성일: 2026-09-16. 브랜치: `feat/auditdesk-xbrl-orchestration`.

**이번 구현은 기존 분석·후보·검토·출력을 두 전환 모드로 연결한다. 요청한 전체 자동화 목표의 완전 달성으로 판정하지 않는다.** 당기 taxonomy export와 검토된 현재 회사 배치가 있는 입력에서는 실제 두 BIFF8 `.xls` 생성까지 연결했지만, 당기 DSD와 표준 taxonomy만으로 회사별 Golden 배치 및 모든 확장 정의를 완성하는 경로는 아직 없다. 실자료에서 사용자 확정 없이 검토 건수가 줄었다고 표현하지 않는다.

당기 회사 패키지는 사용자가 추가로 찾아볼 예정이라고 답변했다. 이번 검증에서 당기 schema/instance/전체 차원망의 확보·최신성 검증을 완료했다고 간주하지 않는다. 전기 자료는 선택적 참고자료이며 당기 정답으로 복사하지 않는다. Commit/push하지 않았다.

## 1. 최초 전환 workflow

시작: **XBRL 작성 지원 → 계정 매핑 확정 → XBRL 전환 · 작성 준비 → 최초 XBRL 전환**.

1. 로컬 DSD를 선택하거나 경로를 입력하고 `DSD 분석`을 실행한다.
2. 본문/주석/표와 원문 셀·병합·날짜 후보를 확인한다. 회사·보고기말·기수·연결/별도·비교기말은 사용자가 확인한다. 빈 회사명 태그를 다른 회사로 오인하지 않는다.
3. 당기 `taxonomy.xls`, 현재 회사의 검토된 `배치.xls`, 당기 적용 확인 근거를 입력한다. 선택적으로 당기 원천 index, 실제 XBRL 패키지, corpus 및 이전 확정 작업 ID를 제공한다.
4. `분석·추천 실행`은 기존 scanner/binding 후보 생성과 로컬 corpus 참고 근거를 연결한다. 전기 회사 XBRL은 필요하지 않다.
5. 같은 binding 작업 ID의 기존 검토 화면에서 원문·Top N·provenance를 확인하고 명시적으로 확정한다. 저장된 전환 작업을 선택해 재개할 수 있다.
6. 기존 100% + conflict 0 + stale 0 조건을 충족한 뒤 새 산출 폴더에 두 `.xls` 및 별도 `review.json`을 생성한다.

실제 headless Chrome의 독립 프로필과 임시 DB에서 DSD 분석 → 후보 작업 → 미확정 생성 차단 → 정적 제목/금액 2개 명시적 확정 → 두 파일 생성 → 생성 상태 재조회까지 확인했다. 실제 코스맥스 5,638개를 대신 확정하지 않았다.

**남은 간격:** 최초 도입 회사에 당기 taxonomy export와 검토된 배치가 없는 경우 DSD만 넣고 완성 파일을 받을 수 없다. 원천 부족을 분명히 알리고 중단한다. 표준 파일이나 타사 사례를 현재 회사의 확정 배치로 바꾸지 않는다.

## 2. 전기→당기 workflow

같은 화면에서 `반기/전기→당기 전환`을 선택한다. DSD 유효성을 먼저 검사한 뒤 회사·보고기간·보고서 종류로 전기 **동기** 공시를 찾는다. 정확한 회사코드 또는 정확한 회사명을 사용한다. 보고서 기간 및 종류가 다른 공시, 다른 회사 공시는 후보에서 제외한다.

- 후보 1건: 실행 시 회사·기간을 재검증하고 수신한다.
- 후보 여러 건: 보고서명·기간·접수번호를 보여주며 사용자가 선택해야 한다. 첫 결과를 임의 선택하지 않는다.
- 공시/키가 없거나 수신에 실패: 구체적인 오류와 재시도 경로를 제공한다. 사용자가 `전기 공시 수신`을 해제하면 전기 없음 상태를 유지하면서 당기 원천 검토를 진행할 수 있다.
- 전기 package는 참고 근거로만 저장한다. 전기 값·기간·차원을 현재 셀에 자동 대입하지 않는다.

실제 package fixture에서 다중 접수 선택 → 수신 → 당기 비교 → 명시적 binding 결정 → 두 BIFF 파일 생성까지 API 통합 검증했다. 전기말과 전반기말은 당기 보고 문맥의 별도 비교기말 입력으로 유지한다. 전반기·전기말 패키지 여러 개를 한꺼번에 자동 최적 선택/조립하는 기능은 이번 연결에 없다.

## 3. OpenDART / corpus integration

기존 OpenDART 클라이언트, 검색·다운로드·해제 및 기존 corpus DB를 재사용한다. 신규 외부 AI 서비스나 별도 회계 매칭 알고리즘을 추가하지 않았다.

현재 taxonomy에 존재하는 Prefix+Name을 대상으로 타사 사용 회사 수, 라벨, Role, dimension 사용 문자열, 동일 업종 여부, 접수/연도 등 DB에 있는 근거를 연결한다. 동일 회사 자체 사용은 타사 빈도에서 제외한다. DB에 없는 정보는 추정하지 않는다. Corpus는 회사별 사용 기록이므로 `타사 N개`로 표현하며 이를 N개 독립 공시 수와 혼동하지 않는다.

기존 문자열 점수와 `sources[].candidates` 순위를 변경하지 않는다. 타사 label 별칭이 현재 DSD label과 연결되는 경우 기존 `binding.rank`를 사용해 **별도 통합 근거 후보**를 만든다. 그 점수는 `reference_label_score`로 구분한다. Role/기간/차원 동등성은 빈도나 별칭 일치로 확정하지 않는다. 현재 QName이 없는 타사 요소를 확정 후보로 삽입하지 않는다.

로컬 corpus가 없으면 해당 단계는 사용자 확인 필요로 표시한다. 새 타사 공시 대량 수집·업종 corpus 구축은 기존 공시 조회 경로를 사용한다. 이번 전환 버튼이 전 업종 자료를 무제한 자동 수집하지 않는다.

## 4. Prior XBRL acquisition

코스맥스 회사코드 `01009789`, 당기 `2026-06-30`, 반기 모드에서 **반기보고서 (2025.06), 접수번호 `20250814000437`, 접수일 2025-08-14**를 실제 탐색했다. 실제 instance, schema, label, presentation, definition, calculation 파일을 수신·읽었다. fixture 결과를 실수신 결과로 대체하지 않았다.

실자료에 `DocumentPeriodEndDate`가 2023-12-31, 2024-06-30, 2024-12-31, 2025-06-30 순서로 존재했다. 기존 parser가 첫 값을 대표일자로 사용하는 경우가 있어, 연결부에서 명시된 문서기말의 최종값과 요청 보고기간을 대조했다. 기존 XBRL parser·V-1/V-2 코어는 수정하지 않았다. 비교기간 하나가 존재한다는 이유만으로 다른 보고기간 패키지를 승인하지 않는다.

여러 instance가 들어 있는 패키지는 임의로 첫 파일을 선택하지 않고 지원 범위 오류로 처리한다. 단일 instance/기존 parser가 읽을 수 있는 package가 현재 지원 범위다. 기존 해제 폴더가 ZIP과 다르면 새 위치에 해제하여 사용자가 편집한 패키지를 덮어쓰지 않는다. 원천 hash를 저장하고 이후 변경 시 재검토를 요구한다.

## 5. Taxonomy 비교

비교의 기준은 당기 원천이며 Prefix+Name 및 Role 출현을 유지한다. 연결/별도 중 선택한 범위만 비교한다. 같은 QName의 다른 Role을 전역 dedupe하지 않는다.

| 상태 | 실제 의미 |
|---|---|
| reusable_candidate | 제공된 비교 필드가 알려져 있고 같은 경우의 후보. 확정 아님 |
| changed | 양쪽에서 확인 가능한 Role/Label/DataType/Period/dimension/namespace 값의 차이 |
| new | 현재 제공 원천에만 있는 출현. 신규 표준 제정 확정 아님 |
| removed | 전기 출현이 현재 제공 비교 원천에 없음. 표준 폐지 확정 아님 |
| extension_review | 회사 확장 항목의 현재 유효성 재검토 필요 |
| needs_review | 비교 메타데이터가 없거나 불확실함 |

모르는 DataType/namespace/dimension은 실제 변경으로 확정하지 않는다. 다른 prefix에서 같은 라벨을 찾았다는 이유로 QName을 동일하게 취급하지 않는다. 회사 확장은 자동 유지 승인하지 않는다.

**범위 한계:** 현재 Golden export에서는 LINEITEM 출현을 읽는다. 전기 presentation에는 abstract/구조 노드도 존재하므로 위 숫자는 완전한 표준 taxonomy 변화나 고유 회계 항목 수가 아니다. 여러 Role 대응은 여러 비교 행이 될 수 있다. 현재 원시 schema/definition이 없으면 표준 폐지·전체 축/구성요소 네트워크의 동등성을 판정할 수 없다. 해당 범위는 PARTIAL이다.

## 6. Recommendation evidence

현재 DSD label/표/표시값 및 현재 taxonomy 후보가 기본이다. 선택적 current source index의 정확한 QName/문맥은 기존 Phase 4B/C 검증을 그대로 따른다. Corpus는 보조 근거, 전기 회사 자료는 현재 QName/Role과 대조한 보조 근거로 사용한다. 같은 라벨의 다른 Role은 별도 후보로 남긴다.

통합 근거 후보 선택은 화면 선택 상태만 바꾼다. 사용자가 단건/기존 batch 확정을 명시적으로 실행하기 전에는 decisions에 저장하지 않는다. 확장 필요 가능성 또는 현재 후보 부족은 `회사 확장 필요 검토`로 표시하며 요소를 생성하지 않는다. 신규 추천 점수나 업무 임계값을 발명하지 않았다.

## 7. Change-focused review

전기 모드의 검토 큐는 `변경 / 재검토 필요`와 `변경 없음 · 재사용 후보 (미확정)`를 구분한다. 변경/불확실 항목을 먼저 보여주며 같은 구분 안에서는 기존 순서를 유지한다. 기존 시트/Role/본문·주석/자료형/예외 필터와 다음 미확정·단축키·확정 취소를 유지한다.

재사용 후보 표시는 현재 source 근거와 기존 High 조건까지 충족한 경우에만 허용한다. taxonomy 비교에서 같다는 사실만으로 현재 DSD의 배치·문맥이 확정되지 않는다. 현재 실자료에서는 이 조건을 만족한 안전 재사용 그룹이 없다.

## 8. Unified provenance

| 출처 | 기록/표시 |
|---|---|
| CURRENT_DSD | 원문 offset/셀/표, 표시값, label 및 검토된 index 근거 |
| CURRENT_TAXONOMY | 현재 제공 export의 QName/Role/출현 ID |
| CURRENT_INSTANCE | 선택적으로 제공한 실제 당기 패키지의 namespace, contextId, unitRef, 값, 기간 및 관계. DSD 셀과 자동 연결하지 않음 |
| PRIOR_COMPANY_XBRL | 검색된 회사/접수/보고기간, 원시 패키지 hash·fact/context/unit·관계 및 현재 비교 |
| OPENDART_REFERENCE | 타사 사용 빈도/출처와 reference ID, 원천 corpus hash |
| USER_CONFIRMED_HISTORY | 동일 회사/범위의 이전 확정 ID/revision 및 기존 재검토 후보. 새 작업은 미확정 |

namespace URI, schema ID, contextId, unitRef와 calculation 관계는 실제 package에 있을 때만 읽는다. 누락값은 생성하지 않는다. 원천을 읽기 전후 hash가 달라지면 중단한다. DSD 분석과 binding 준비가 다른 snapshot을 사용하면 재실행을 요구한다.

실자료 최초 구현에서 같은 corpus Role/dimension 문자열을 후보마다 복제해 first draft가 546,869,738 bytes까지 증가했다. 이를 실패 테스트로 재현하고 reference ID로 연결하도록 수정했다. 큰 원문은 원천 DB에 유지하며 화면의 `타사 근거 원문 보기`에서 20개 사례 단위로 조회한다. 표시용 미리보기는 잘린 여부를 기록한다. 원천이 변경됐으면 상세 조회도 거절한다. 저장 응답은 변경된 결정과 coverage/단계만 반환하고 불변 분석/근거는 다시 전송하지 않는다.

## 9. Workflow coverage

- required / mapping candidate / confirmed / unresolved / review required는 출력 셀 기준이다.
- candidate coverage는 기존 배치 원문 후보가 하나 이상 있는 셀 비율이다.
- automatic evidence coverage는 해당 배치 후보의 taxonomy 추천에 corpus/prior/current instance 보조 근거가 연결된 셀 비율이다. 회계 의미나 차원이 확정됐다는 비율이 아니다.
- prior reusable / taxonomy-valid reusable 및 changed/new/removed 등은 taxonomy 비교 출현 기준이다. 출력 셀 수와 합산하지 않는다.
- stale이면 현재 유효한 confirmed는 0으로 표시한다.

회계 자동화율이나 검토 시간 절감률을 위 후보/보조 근거 coverage로 대체하지 않는다. 사람이 실제 검토하는 데 걸리는 시간/오류율은 측정하지 않았다.

## 10. Golden generation

두 모드가 같은 기존 `binding.generate` → `golden.build_current`를 사용한다. `binding.py`, `golden.py`, 기존 Footing/Prior reconciliation/V-1/V-2/Guide check/Mapping Sheet/AuditLink 코어는 변경하지 않았다.

산출: `[회사]_taxonomy.xls`, `[회사]_Excel.xls`, 별도 `review.json`. 실제 BIFF8 파일이며 확장자만 변경한 xlsx가 아니다. 검토 상태·provenance·workflow 정보는 별도 JSON에만 기록한다. 기존 writer 의미·수식 0개·사용자 확정 조건을 유지한다. 99% 생성 차단은 기존 Phase 4C 회귀로 다시 확인한다.

생성 결과와 당시 revision을 작업에 남겨 다시 열 수 있다. 결정이 바뀌거나 원천이 stale이면 이전 결과를 현재 완료 상태로 표시하지 않는다. 생성 실패 시 같은 화면에서 경로/오류를 수정하여 다시 실행할 수 있다. 기존 출력 폴더를 덮어쓰지 않는다.

## 11. 코스맥스 실자료 결과

당기 연결 DSD + 제공된 Golden taxonomy/Excel export + 기존 로컬 corpus를 사용했다. DSD source 5,732개, 표 135개, taxonomy 출현 1,346개, 필수 출력 셀 5,638개다. 입력 DSD/두 Golden 원본 hash는 검증 전후 동일했다.

| 지표 | 최초 전환 | 전기→당기 |
|---|---:|---:|
| Required | 5,638 | 5,638 |
| Mapping candidate | 3,191 | 3,191 |
| Candidate coverage | 56.60% | 56.60% |
| 보조 근거가 연결된 출력 셀 | 2,962 | 3,151 |
| Automatic evidence coverage | 52.54% | 55.89% |
| Confirmed | 0 | 0 |
| Unresolved / review required | 5,638 | 5,638 |
| 안전 재사용 / 현재 검증 재사용 후보 | 해당 없음 | 0 / 0 |
| 완전 Golden 생성 | 차단 | 차단 |

현재 QName에 해당하는 corpus reference 집계 426개를 연결했다. 전기 연결 presentation 출현 1,729개를 읽었다. 현재 선택 범위와 비교한 행은 changed 587, current-only 239, prior-only 1,282, extension review 9, metadata-unverified 21이다. 비교 행 중복/구조 노드 및 원천 범위 한계가 있으므로 이 합계를 고유 변경 계정 수라고 해석하지 않는다.

## 12. 최초 전환 자동화율

보조 근거 연결 52.54%, 후보 coverage 56.60%를 측정했다. **확정 자동화율은 0%이며 자동 확정 자체를 구현하지 않았다.** 현재 원천만으로 5,638개를 무검토 산출할 수 있다는 주장을 하지 않는다. 다른 최초 도입 회사의 DSD + 표준 taxonomy만으로 Golden 배치가 자동 완성되는 실자료 검증도 없다.

## 13. 전기→당기 자동화율

실제 전기 공시의 자동 탐색·수신은 성공했다. 보조 근거 coverage는 55.89%지만 현재 기준의 안전 재사용은 0이다. 당기 원시 패키지 부재와 비교 메타데이터 불확실성을 남겼다. 날짜만 바꾸거나 전기 taxonomy/회사 확장 요소를 정답으로 복제하지 않았다.

## 14. 실제 사용자 검토 필요 건수

두 모드 모두 **5,638개**다. baseline 대비 확정 대상 셀 수의 감소는 **0개**다. 추가 근거·변경 필터·빠른 검토 도구를 제공하지만 실자료의 사용자 검토를 완료하지 않았다. 과거 사용자 확정 이력의 실자료 비교는 별도 이력이 제공되지 않아 fixture 검증 범위다.

## 15. Phase 1~4C 회귀

기존 Phase 1: 38개, Phase 2: 56개, Phase 3: 15개, Phase 4: 18개, Phase 4B: 25개, Phase 4C: 16개를 포함한다. 테스트 삭제/기대값 완화/기능 기준 하향은 없었다.

기존 일반 묶음 최초 실행에서 UI 금지 용어 `Explorer`가 노출돼 1건 실패했다. 사용자 화면을 `공시 조회`로 수정했고 기존 용어 검사 4개를 그대로 통과했다. 실제 Golden roundtrip 2건은 파일 경로 환경설정 누락으로 skip되어, 제공된 실제 파일 경로를 지정하고 기존 Phase 4 18개와 함께 재검증했다. 해당 22개는 모두 통과했다. 최종 집계에서 이전 실패/skip을 최신 동일 ID 결과로 대체한다.

## 16. 전체 테스트

최초 구현 전 Python 21개가 새 연결 모듈/API 부재로 실패했고 UI 3개가 새 화면 부재로 실패했다. 테스트 임시 폴더 준비 오류는 기능 실패 재현 수에 넣지 않고 디렉터리를 준비한 뒤 재실행했다.

추가 실패 재현: 원천 식별자 누락, current package 미연결, corpus 별칭 추천 누락, sidecar/생성 상태 미보존, 과거 확정 이력 누락, 잘못된 corpus 오류, 분석 중 DSD 변경, namespace 변경, 빈 회사명 태그, compact 응답 중복, 여러 문서기말, 외부 검색 오류/비밀 문자열, 다중 instance 임의 선택, 반대 scope 비교, 미확인 속성의 변경 오인, 분석 전 불필요한 다운로드, 편집한 package 덮어쓰기, 후보별 대형 근거 중복이다.

### 요구 테스트 대응

| 요구 범위 | 검증 근거 |
|---|---|
| 최초 전환 1~3 | DSD 구조 분석, 사용자 지정 current export/선택적 package, corpus alias API/통합 테스트 |
| 4~6 | 기존 동일 label/다른 Role 회귀, 빈도 20개여도 decisions 0, 회사 확장 review 분류 |
| 7~9 | 실제 API 결정 저장 → BIFF 출력, 미확정 생성 차단, 독립 브라우저 workflow |
| 전기 10~12 | 회사/종류/기간 필터, 다중 접수 선택, 실제 코스맥스 조회 |
| 13~18 | QName 존재/부재/신규, Role/Period/DataType/dimension/namespace 변경 및 확장 검토 |
| 19~22 | 예외 우선 projection/필터, 전기 없음 상태, current 원천 필수, 기준/점수/decisions 불변 |
| 공통 23~27 | provenance, raw context/unit/namespace, snapshot stale, 회사·scope·기간 혼입 거절 |
| 28~29 | 기존 99/100 gate 회귀 + 두 전환 fixture의 100% 실제 파일 생성 |
| 30 | 동일 입력 evidence/queue 결정성 및 기존 Golden semantic 재실행 회귀 |

검증 산출물은 `.pytest_cache/phase4d/`의 ignored 로그/JUnit/고유 ID/소스 hash에 기록한다. 중복 실행 횟수를 passed에 더하지 않는다. 장시간 구간 taxonomy 7개, note worksheet 6개, worksheet 2개와 나머지 492개는 서로 겹치지 않는다. 관련 소스 변경 이후 재검증 결과는 같은 테스트 ID를 대체한다. 기존 faulthandler 진단 플러그인만 끄며 테스트 내용은 변경하지 않았다.

최종 수집 552개 고유 테스트 ID와 JUnit 결과를 대조한 결과 **552 passed / 0 failed / 0 skipped / 0 errors**다. 누락 및 미등록 ID는 0개다. Phase 4D Python 45개와 기존 Phase 1~4C Python 회귀 168개가 포함된다. UI는 전체 31개(Phase 4D 5개 포함)가 통과했다. 마지막 TypeScript 검사에서 원문 조회 버튼의 disabled 속성 지원 오류를 발견해 기존 PrimaryBtn으로 연결하고 재검증했다. TypeScript, production build, git diff --check 모두 통과했다.

최종 빌드의 격리 Chrome에서 시작 → DSD 분석 → 미확정 생성 차단 → 두 셀 명시적 확정 → 실제 두 BIFF 파일 및 review.json 생성 → 새로고침 후 완료 상태 복원을 확인했다. JavaScript page error는 0개다. 기존 개인 Chrome 접근은 자동 승인 검토에서 거절되어 사용하지 않았으며, 별도 임시 프로필과 로컬 fixture/DB만 사용했다.

실자료 draft 저장 크기는 최초 전환 48,443,016 bytes, 전기 전환 91,748,277 bytes다. 후보마다 동일 corpus 원문을 복제하던 문제를 원문 참조 방식으로 수정했다. 여전히 큰 draft이므로 코스맥스 전체 화면의 실사용 성능은 검증 완료로 간주하지 않는다.

## 17. 미구현/미검증 부분

| Master | 상태 | 범위와 한계 |
|---|---|---|
| M-51 | PASS | 두 사용자 모드, 입력/수집 안내, 진행·오류·복원·재실행 |
| M-52 | PARTIAL | scanner 구조/값/병합/후보 연결 완료. 회사·기수·보고기간 완전 자동 판정 아님 |
| M-53 | PARTIAL | 지정 export/로컬 자산/선택적 package 수용. 현재 적용 표준과 회사 확장의 공식 최신성 자동 확정·수신 미완성 |
| M-54 | PARTIAL | 기존 local corpus와 후보 근거 연결. 신규 peer 자료의 전환 내 자동 대량 구축 및 완전한 dimension 구조 대응 없음 |
| M-55 | PASS (지원 package 범위) | 실제 회사 전기 동기 검색/수신 및 선택·오류 처리. 다중 instance/다중 전기기간 조립 제외 |
| M-56 | PARTIAL | QName/Role 출현 및 알려진 속성 대조. 완전한 표준 폐지·차원망 diff로 간주하지 않음 |
| M-57 | PARTIAL | current 후보/alias/corpus 근거 조합. 당기 회사 taxonomy/배치 자체의 자동 완성 없음 |
| M-58 | PARTIAL | 전기 공시/확정 이력의 재검토 후보 연결. 실자료 안전 승계 0 |
| M-59 | PASS (검토 도구) | 변경/재검토 큐와 재사용 후보 분리. 실자료 검토 셀 감소 0 |
| M-60 | PASS (지원 원천) | 출처·식별자·hash·원문 조회 연결. 실제 current package 미제공 |
| M-61 | PASS | 후보/근거/확정/미해결 지표 분리; taxonomy 행과 출력 셀 분모 구분 |
| M-62 | PASS (명시 입력+확정 범위) | 기존 writer로 두 실제 BIFF 파일 생성. 실자료 미확정 상태의 생성은 차단 |

실제 Excel/DART 편집기에서 생성 파일을 열고 제출 호환성을 확인하지 않았다. 독립 Chrome fixture 검증은 회계사 실사용 시간이나 코스맥스 전체 화면 성능 시험을 대신하지 않는다. 당기 source index/배치의 정확성은 사용자가 확인해야 한다. 원천 부족 상태에서 확장 QName/차원/namespace를 만들어 채우지 않았다.

현재 단계의 사례 원문 조회에는 hash가 일치하는 로컬 corpus DB가 필요하다. 별도 `review.json`의 요약과 source hashes만 이동한 경우 모든 타사 원문이 함께 포함되는 것은 아니다. 원시 XBRL schema import를 완전히 해석하지 않으며 typed dimension의 의미 검증도 제공하지 않는다.

## 18. 다음 단계 및 변경 범위

사용자가 확보할 당기 회사 패키지와 적용 기준의 출처를 확인하고, 현재 회사 배치/문맥을 명시적으로 검토해야 한다. 이후에야 현재 QName/Role/차원의 재사용 가능성을 더 강하게 검증할 수 있다. 최초 도입 회사의 실제 DSD + 당기 표준 원천으로 회사별 Golden 배치를 구성하는 요구는 별도 남은 구현 항목이다. 이를 이번 결과에서 완료 처리하지 않는다.

제품 변경:

- `auditdesk/orchestration.py`: 분석·corpus 근거·현재 기준 비교·workflow coverage/projection.
- `auditdesk/orchestration_sources.py`: 기존 OpenDART 수신/패키지 adapter 및 원시 근거.
- `auditdesk/routers/orchestration_api.py`: 전환 실행/복원/검색/원문 조회.
- `auditdesk/routers/binding_api.py`: 기존 검토와 전환 상태/작은 저장 응답/별도 review 산출 연결.
- `auditdesk/app.py`: 전환 router 등록.
- `webui/src/XbrlWorkflow.tsx`: 두 모드의 공식 진입 화면.
- `webui/src/Studio.tsx`: 기존 매핑 화면의 진입 버튼.
- `webui/src/BindingReview.tsx`: 기존 검토에 단계·provenance·원문 조회 연결.
- `webui/src/ReviewQueue.tsx`, `webui/src/bindingReviewQueue.ts`: 변경 필터와 작은 workflow 상태 병합.

테스트: `tests/test_phase4d_orchestration.py`, `webui/tests/phase4d.test.cjs`. 보고서: 이 파일.

기존 사용자 `CLAUDE.md`, 기존 감사 보고서, `auditlink-v2/.claude/`, `DSD_footing/.claude/`는 보존한다. 테스트 DSD/Excel/XML/JSON/SQLite, 브라우저 프로필/서버 DB, 공시 수신 cache, build 산출물은 제품 변경 파일에 포함하지 않는다.

최종 Git 범위는 제품 코드 10개 + regression/UI test 2개 + 보고서 1개, 총 13개다. 기존 추적 파일의 Phase 4D diff는 6개 파일 +65 / -15이며, 신규 코드·테스트 6개는 1,111행이다. 신규 보고서는 Git diff --stat 기본 출력에 포함되지 않으므로 별도로 집계한다. 기존 사용자 CLAUDE.md 변경(+72 / -22)과 감사 보고서/.claude 파일은 이 범위에서 제외하며 기존 SHA-256 일치를 확인했다. api.ts는 내용 diff가 없는 줄바꿈/작업 트리 표시만 있으므로 제품 변경 목록에서 제외한다. staged 파일은 없으며 commit/push하지 않았다.

### Phase 4D completion status

- First conversion workflow: PARTIAL — 명시적인 current export/배치 입력부터 확정·파일 생성까지 연결; DSD+표준만으로 완성은 미구현.
- Rollforward workflow: PARTIAL — 실수신/비교/검토/공통 writer 연결; 실제 재사용·완전 Golden 미달성.
- OpenDART acquisition: PASS — 코스맥스 실제 전기 동기 공시 수신.
- Reference corpus: PARTIAL — local corpus 근거/원문 조회 연결.
- Taxonomy diff: PARTIAL — 현재 제공 범위와 전기 출현 비교; 전체 표준/차원망 검증 아님.
- Change-focused review: PASS — 도구 연결; 실자료 검토량 감소 0.
- Golden generation: PASS (검토 완료 fixture); 코스맥스는 차단.
- First conversion review required: 5,638.
- Rollforward review required: 5,638.
- Full Python suite: PASS — 552 passed / 0 failed / 0 skipped / 0 errors (고유 ID 기준).
- UI: PASS — 31 passed / 0 failed.
- TypeScript: PASS.
- Production build: PASS.
- git diff --check: PASS.
- Remaining risks: 당기 package/공식 적용성, 최초 도입 배치 자동 구성, 차원 의미, 실제 편집기 호환성 및 대규모 실사용 검증.
