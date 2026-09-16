# AuditDesk Phase 4 Golden Output Report

## 1. 설계 결정과 인수 범위

브랜치: `feat/auditdesk-golden-output`. 기준: AuditDesk Target Output Specification v1 및 사용자의 Current-first 수정 지시.

**Current-first / Prior-assisted:** 당기 DSD, 당기 정의·레이블·배치 및 현재 보고 문맥을 기준으로 생성한다. 전기 XBRL/taxonomy/편집 프로젝트는 필수 입력이 아니다. 전기 자료는 참고 후보이며 현재 유효성을 재검증하지 않고 자동 승계하지 않는다. 기존 Phase 3 rollforward 동작은 바꾸지 않았다.

이번 구현은 실제 BIFF8 writer, 명시적 당기 DSD 연결, CLI 실행 경로다. **Golden 원본을 모델로 읽고 다시 쓰는 writer 검증과 DSD에서 새 값을 생성하는 workflow 검증을 구분한다.** 코스맥스 전체 42개 시트의 셀별 의미 연결이 완성된 것은 아니다. 원본을 재출력한 사실로 M-31 전체 완료를 선언하지 않는다.

### 필수 원천 / 선택적 원천 / 추정 금지 Matrix

| 정보 | 확보 원천 | 조건 |
|---|---|---|
| 본문·주석 순서, 표·문단, 셀 원문, ROWSPAN/COLSPAN | 당기 DSD | 직접 확보. scanner의 원문/위치 유지, 양끝 공백을 자동 제거하지 않음 |
| 금액·비율·날짜·서술 표시 문자열 | 당기 DSD | 직접 확보. 계산값과 표시 문자열을 분리하며 모든 숫자를 통화로 보지 않음 |
| 보고기간·비교기간·기수·연결/별도 표시 | 당기 DSD 및 현재 보고정보 | 명시된 문맥 필요. 전기말과 전반기, 3개월과 누적은 별도 |
| 표준 QName·DataType·Balance·Period·표준 레이블 | 현재 적용 taxonomy/schema/label | 당기 원천 필요. Prefix+Name에서 namespace URI나 schema ID를 만들지 않음 |
| 회사 확장·Role·Label Role·관계 | 당기 회사 schema/label/presentation 또는 편집 원천 | 확장 최신성은 해당 당기 원천에서 확인. 전기 요소를 현행이라고 간주하지 않음 |
| contextId·unitRef·회사·기간·차원·nil | 당기 instance/context 또는 명시적 현재 연결 원천 | 원래 XML ID는 DSD/Golden만으로 복원 불가. 이번 경로는 의미 문맥을 받으며 XML ID를 발명하지 않음 |
| 행/열축 방향·요소별 대상 셀 | 현재 편집 프로젝트 또는 검토된 명시적 배치 연결 | 한글 레이블로 자동 조인하지 않음. 미확정 연결은 생성 전에 거부 |
| 원래 시트명·반복 헤더·서식·빈 셀·표시 문자열 | 제공된 당기 Golden 파일 | 동일 샘플 writer 기준. 정답 샘플을 읽은 것과 DSD 연결 성공은 별도 |
| 과거 Role/회사 정의/배치/비교값 | 전기 산출물 | 선택적 참고만 가능 |
| namespace URI/schema ID/contextId/unitRef/calculation 관계/확장 최신성 | 해당 당기 원천 없으면 확보 불가 | 추정 금지 |

DSD 단독으로 공시 표/값은 읽을 수 있으나 XBRL 의미를 전부 확정할 수 없다. **당기 정의와 확인된 배치 연결을 함께 받으면 전기 없이 생성된다.** 코스맥스비티아이 당기 IXD에는 namespace·ContextKey·차원·값·배치 정보가 있으나, 다른 회사의 정보를 코스맥스에 대입하지 않았다.

코스맥스 DSD 직접 조사: 현 scanner가 표 135개·본문 4개·주석 구획 33개를 읽었다. 셀 속성에는 COLSPAN/ROWSPAN, ALIGN/VALIGN, WIDTH/HEIGHT, AUNIT/AUNITVALUE 등이 있다. 원문에서 contextRef, unitRef, schemaRef, xbrli:context, link:calculationLink는 발견되지 않았다. 이 결과는 완전한 XBRL 문맥을 DSD만으로 만들어내지 않는 근거이며 주석 33개가 Golden 주석 38개와 일대일이라는 뜻은 아니다.

## 2. GOLD-01~14 Matrix

최초 상태는 구현 전 기존 AuditDesk 출력 기준이다. 현재 판정은 원본 충실도 검증과 실제 DSD 연결의 한계를 함께 반영한다.

| ID | 최초 | 현재 | 근거와 한계 |
|---|---|---|---|
| GOLD-01 | FAIL | PASS | 신규 writer가 실제 OLE/BIFF8 `.xls` 생성. ZIP `.xlsx` 위장 입력 거부. CLI가 두 `.xls` 생성 |
| GOLD-02 | FAIL | PARTIAL | writer 재출력에서 Excel 42 / taxonomy 83 이름·순서·범위 전수 일치. DSD 전체 42시트 생성 연결은 미완성 |
| GOLD-03 | FAIL | PASS (writer) | 168회 헤더, TABLE 160 / DOMAIN 1,088 / LINEITEM 1,346 출현 보존. 헤더 위치 고정/전역 dedupe 없음. taxonomy Fact 값이 있으면 생성 거부 |
| GOLD-04 | FAIL | PARTIAL | 재출력에서 문자열/빈 문자열/BLANK/공백/괄호/줄바꿈 전수 동일. 실제 DSD 연결은 대표 현금 두 값과 통합 fixture에서 검증 |
| GOLD-05 | FAIL | PARTIAL | 현재 taxonomy 입력의 Role/Prefix/Name/Label Role/속성 전수 보존. 연결은 특정 Role·행 출현의 QName·자료형·기간과 비교. namespace/최신 schema의 전수 검증은 아님 |
| GOLD-06 | PARTIAL | PARTIAL | Golden 원본의 BS/PL/CE/CF 블록 위치 전수 보존. 명시된 현재/비교 종료일 및 INSTANT/DURATION 검사. 모든 실제 표의 기간 연결은 미완성 |
| GOLD-07 | FAIL | PASS (stored writer) | 전체 셀 글꼴·색·정렬·줄바꿈·테두리·숫자서식·병합·행높이·열너비·표시/틀고정 의미값 비교 통과. 실제 화면/인쇄는 제외 |
| GOLD-08 | PARTIAL | PARTIAL | 재출력에서 빈 주석과 별도 taxonomy 41시트 보존. 별도 금액 시트를 자동 생성하지 않음. 새 회사의 빈 주석 처리는 자동 추정하지 않음 |
| GOLD-09 | PARTIAL | PASS | BIFF FORMULA 레코드 검사: 입력 Golden 및 생성물 모두 0. 수식 입력은 거부. 기존 rollforward 조서의 수식은 변경하지 않음 |
| GOLD-10 | PARTIAL | PARTIAL | Golden 현금 본문/주석 양 시점 대사 통과. 실제 DSD에서 336,726,180,991 / 192,279,928,597 생성 확인. 전체 DSD 본문/주석 연결은 미완성 |
| GOLD-11 | PARTIAL | PARTIAL | 특수관계자·투자부동산·CE·법인세 등 원본 전 셀 재출력 일치, 법인세 B8 `0.2192` 별도 확인. 해당 표의 DSD 의미 연결은 미완성 |
| GOLD-12 | NOT TESTED | PARTIAL | 명시적 current-first fixture의 두 번 실행에서 의미값 동일. 원본 모델→writer 전수 동일. 전체 실제 DSD 문맥 생성 재실행은 미완성 |
| GOLD-13 | NOT TESTED | NOT TESTED | 실제 Excel 화면 및 인쇄 전체 비교 미수행 |
| GOLD-14 | NOT TESTED | NOT TESTED | DART 편집기 실제 지원 경로 미수행. IXD 내부 구조 읽기를 호환성 PASS로 보지 않음 |

## 3. 수정 전 재현 및 실제 구현

현재 코스맥스 DSD의 기존 extract도 42시트였으나 `사용안내/원문/표지/_MAP/_META`와 숫자 주석명이 포함됐다. BS 52×4 / PL 41×6 / CE 31×9 / CF 225×5로 Golden 48×3 / 37×5 / 29×9 / 93×3과 다르다. 숫자형 셀 29,407개가 있고, taxonomy tree writer는 6열만 출력했다. 기존 조서는 편집/repack 목적이므로 제거하지 않았다.

실패 테스트 먼저 작성: 새 경로 부재로 10개 실패(외부 파일 경로 미설정 2개 skip는 실패 재현 수에 포함하지 않음). 구현 후 실제 Golden 경로를 설정해 전부 실행했다. 추가 경계 검증으로 taxonomy 자료형/기간 불일치 2개와 Fact 비어 있음 계약 1개가 실패하는 것을 확인한 뒤 수정했다. 기존 테스트를 삭제하거나 기대값을 낮추지 않았다.

변경 파일:

- `auditdesk/golden.py`: BIFF8 읽기/쓰기, 의미값 비교, 명시적 current-first 생성.
- `auditdesk/__main__.py`: `golden` CLI. 기존 서버/rollforward 진입점 유지.
- `backend/requirements.txt`: xlrd 2.0.2 / xlwt 1.3.0 의존성.
- `tests/test_phase4_golden.py`: 18개 회귀/통합 테스트(실제 Golden 2개 포함).
- 이 Phase 4 보고서.

writer는 문자열과 BLANK를 별도 저장하며 `write('')`가 BLANK로 바뀌는 경로를 피한다. 병합 레코드를 추가할 때 비앵커 서식 셀을 덮어쓰지 않는다. 스타일 인덱스 대신 팔레트를 해석한 색·글꼴·배치 의미값을 비교한다. 파일 덮어쓰기는 거부하고 새 폴더에 산출한다.

## 4. 사용자 workflow와 Current-first 계약

AuditDesk 디렉터리에서:

```powershell
python -m auditdesk golden --current-dsd "현재.dsd" --taxonomy "당기_taxonomy.xls" --layout "당기_배치.xls" --bindings "확인된_당기연결.json" --out "새_산출폴더"
```

입력→현재 원천/연결 검사 메시지→`taxonomy.xls`, `Excel.xls`, 별도 `review.json` 경로 확인. 실패 시 구체적 입력 오류가 나오며 입력 수정 후 재실행한다. 새 출력 폴더가 필요하다. review 정보는 Golden workbook 안에 삽입하지 않는다.

연결 JSON은 자동 생성된 추천 결과가 아니라 **검토된 당기 연결 입력**이다. 최소 계약:

- `report`: company, scope(consolidated/separate), period_end, fiscal_number, 선택적 comparison_ends.
- `dsd_sha256`, `taxonomy_sha256`, `layout_sha256`: 검토한 현재 파일 해시. 읽은 동일 bytes로 검증·생성하여 중간 파일 변경을 섞지 않는다.
- `bindings`: 대상 sheet/row/column(1부터), DSD contents.xml source_start/source_end(문자 offset), taxonomy_sheet/taxonomy_row, role/prefix/name, data_type, context, source_evidence.
- `context`: company/scope, instant 또는 start/end, dimensions, 의미 단위 unit. XML contextId/unitRef를 자동 생성하지 않는다.
- `static_cells`: 원문 제목 등 유지할 셀의 sheet/row/column과 source_evidence. 문자열 셀 하나라도 binding/static 선언이 없으면 거부한다.

이 선언을 이용해 원천이 없는 값을 조용히 샘플에서 복사하지 않게 한다. 다만 정적 셀 및 차원·단위의 근거 자체는 입력자의 검토에 의존한다. 이 버전은 instance/schema를 모두 읽어 연결을 자동 확정하는 제품이 아니다. `complete`는 제공된 명시적 연결의 커버리지 검사 완료이며 전체 Golden 인수·업무 승인·편집기 호환성 승인이 아니다.

## 5. Case A 결과 — 전기 없이 실행

M-31은 **PARTIAL**로 재평가한다. 전기 부재가 이유가 아니다.

1. 통합 fixture: 현재 DSD+당기 taxonomy+배치+명시적 연결만으로 두 `.xls` 생성. layout의 `old value` 대신 현재 DSD의 `1,234`를 사용한다.
2. DSD가 `9,876`으로 바뀌면 기존 해시로 실행을 거부하고, 재검토한 새 해시로 실행하면 새 값을 출력한다.
3. 코스맥스 실자료: 기존 extract의 `_MAP`에서 BS C10/D10에 해당하는 정확한 DSD 셀 위치를 확인하고 기준 문서 6.1의 taxonomy BS 7행 QName/Role과 명시적으로 연결했다. current=2026-06-30 / comparison=2025-12-31, KRW 의미 단위로 실행했다.
4. 실제 출력 문자열 `336,726,180,991` / `192,279,928,597`, 내부 Decimal 문자열 `336726180991` / `192279928597`을 확인했다. 전기 파일은 사용하지 않았다.

실자료 실행은 **현금 두 값만 포함한 별도 probe**다. 전체 42시트 연결 JSON은 만들지 않았으며 이 probe를 완성된 코스맥스 Golden Excel이라고 제공하지 않는다. 남은 공백은 다른 값·차원·표의 당기 연결 확정이다. namespace나 계산관계를 추정하여 채우지 않았다.

전체 Golden layout에 현금 두 binding만 제공하는 실자료 실패 시나리오도 확인했다. 남은 문자열 셀 5,636개에 현재 값/정적 표시 근거가 없다는 오류를 반환하고 출력 폴더를 만들지 않았다. 이 수는 미매핑 금액 개수가 아니라 제목·빈 문자열 등을 포함한 미분류 출력 셀 수다.

## 6. Case B 결과

보류. 최초 도입 회사 입력이 아직 지정되지 않았다. 코스맥스비티아이 IXD의 FirstSubmitReport_YN은 N이므로 최초 도입 사례로 가장하지 않았다. 신규 회사 정의/영문 레이블/ID를 발명하지 않았다.

## 7. Rollforward 결과

별도 현재/비교 시나리오가 확보되면 추가 검증한다. 새 Golden 경로는 현재 taxonomy와 보고정보를 입력으로 받으며 전기 자동 승계·날짜 일괄 치환을 하지 않는다. 이번 테스트의 비교 종료일 검증은 전체 이월 검증을 대신하지 않는다. 기존 Phase 3 F-3b 코어는 그대로 유지한다.

## 8. taxonomy ↔ Excel 대응

Role + taxonomy 시트/행 + Prefix + Name 출현을 검사한다. QName만으로 전역 dedupe하지 않으며, 같은 QName의 다른 Role·차원 문맥을 별도 bindings로 유지하는 테스트가 통과했다. 현재 taxonomy와 자료형 또는 INSTANT/DURATION이 다르면 거부한다. Balance나 negatedLabel로 표시부호를 다시 뒤집지 않는다.

단위/차원 연결의 명시적 근거, namespace/schema ID, 계산관계 및 회사 확장 최신성은 Golden만으로 완전히 복원할 수 없다. 현재 구현이 그것들을 자동 검증했다고 주장하지 않는다.

## 9. 서식/배치 검증

원본 SHA-256:

- Excel: `6222728cfcd1b409895765a8d0e988462b33028e0b41632010a8c8c21ee5c0e4`
- taxonomy: `9c6330bd7fe2450b589224a2f1f87616228deb5bc4858c5b6847e565b2a91166`

전수 재출력 비교: taxonomy 83시트/3,262행/문자열 25,073/BLANK 5,881; Excel 42시트/2,135행/문자열 5,638/BLANK 2,974. taxonomy 병합 0, Excel 병합 레코드 1,361(2셀 이상 599). 원문 공백·행열 좌표·굴림 9pt·색·정렬·줄바꿈·테두리·General/숫자표시 서식이 보존된다. 사용 범위와 모든 셀을 비교하므로 CE 전기→당기, PL 3개월/누적, 빈 주석도 재출력에서 유지된다.

## 10. deterministic 결과

동일 명시적 현재 입력으로 두 번 생성한 결과의 시트·값·유형·서식 의미값이 동일하다. 재출력 전수 비교도 통과했다. ZIP/BIFF 바이트나 스타일 인덱스 자체를 동일성 기준으로 삼지 않는다. 전체 실자료 DSD의 미확정 문맥까지 생성한 재실행 검증은 남아 있다.

## 11. 기존 Phase 회귀 및 전체 검증

- Phase 4 대상 테스트: 18 passed (실제 Golden 파일 2개 포함).
- Phase 1/2/3: 38/56/15, 총 109 passed. 현재 전체 suite의 일반 그룹에서도 다시 통과했다.
- UI regression: 16 passed / 0 failed / 0 skipped.
- TypeScript: PASS.
- Production build: PASS.
- Full Python suite: **466 passed / 0 failed / 0 skipped / 0 errors**. 고유 수집 466개와 결과 466개가 일치하며 누락/중복 합산은 0개다. 제품·의존성·테스트 파일 4개의 실행 전후 해시도 동일하다.

| 최종 그룹 | Passed | Failed | Skipped | JUnit 실행 시간 |
|---|---:|---:|---:|---:|
| taxonomy | 7 | 0 | 0 | 3,257.870초 |
| 주석 worksheet | 6 | 0 | 0 | 2,226.549초 |
| worksheet | 2 | 0 | 0 | 2,963.869초 |
| 나머지 전체 | 451 | 0 | 0 | 1,223.939초 |
| 합계 | 466 | 0 | 0 | 병렬 실행, 시간 합산하지 않음 |

근거: ignored `.pytest_cache/phase4/full-nodeids.json`, `full-groups.json`, 그룹별 JUnit XML, `final-results.json`, `verified-source-hashes.json`. 선택한 node ID 목록과 XML의 테스트 이름·순서·건수를 전수 대조했다. pytest rootdir 밖 테스트의 classname이 비는 경우가 있어 classname 유무를 테스트 누락으로 해석하지 않았다. 반복 대상 실행 18개와 별도 실자료 probe는 전체 466개에 더하지 않았다.

기존 경고 3개(클래스 fixture 인스턴스 메서드 deprecation 2개, 기본 스타일 없는 기존 Excel 1개)는 유지된다. 기존 테스트의 기준과 기대값은 변경하지 않았다.

## 12. 실제 응용프로그램 미검증 범위

Excel 전체 시트 화면·인쇄와 DART 편집기 실제 활용은 NOT TESTED. 코스맥스비티아이 최종 `.xls` 읽기에서 OLE 구조 경고가 있었으며 해당 파일을 고치거나 Golden 기준으로 바꾸지 않았다. IXD는 읽기만 했고 수정하지 않았다.

## 13. 남은 결정사항과 Git 범위

- 실제 전 표의 당기 연결을 제공/확정하는 경로: 이번에는 명시적 연결 JSON으로 제한했다. 자동 label 매칭/IXD 전체 역공학은 추가하지 않았다.
- 최초 도입 Case B 및 이월 비교 시나리오 지정.
- 실제 Excel/DART 편집기 확인 환경.
- xlwt는 BIFF8의 제한을 따른다. 임의 새 회사/초대형 표에 대한 지원을 보장하지 않는다.

고객 Golden/DSD는 원래 경로에서 읽기만 했다. 생성 Excel, JSON 근거, 테스트 로그, 초기 의존성 임시 설치는 ignored `.pytest_cache/phase4`에 두었으며 Git에 넣지 않는다. CLI 실행을 위해 작업 Python 환경에도 xlwt 1.3.0을 설치했다. 기존 CLAUDE.md, 감사 보고서, 다른 제품 .claude 파일은 보존한다. commit/push하지 않았다.

Git 범위(저장소 루트 기준): A는 `auditdesk/auditdesk/golden.py`, `auditdesk/auditdesk/__main__.py`, `auditdesk/backend/requirements.txt`; B는 `auditdesk/tests/test_phase4_golden.py`와 이 보고서다.
C인 기존 `CLAUDE.md`, `auditdesk/FEATURE_ARCHAEOLOGY_REPORT.md`, `auditdesk/REQUIREMENTS_GAP_AUDIT_20260908.md`, `auditlink-v2/.claude/launch.json`, `DSD_footing/.claude/settings.local.json`은 해시를 확인하여 보존한다. 이 파일들은 Phase 4 변경에 포함하지 않는다. cache/Excel/XML/JSON/DB/build 파일을 stage하지 않았다. 추가로 확인된 예상 밖 비-ignored 생성 파일은 없다.

최종 Phase 4 A/B diff: **5개 파일, +729/-0**. 제품·의존성 3개 +336/-0, 테스트·보고서 2개 +393/-0. tracked-only diff의 기존 CLAUDE 변경 +72/-22는 제외했다. stage는 비어 있으며 commit/push하지 않았다.

## Phase 4 completion status

- M-28: PARTIAL — taxonomy writer 충실도 PASS, 당기 원천 자동 조립은 미완성
- M-29: PARTIAL — Excel writer 충실도 PASS, 전체 DSD 배치 연결은 미완성
- M-30: PARTIAL — 명시적 QName/Role/유형/기간 연결 검증, 전수 문맥 검증은 미완성
- M-31: PARTIAL — 전기 없이 CLI 및 실제 현금 probe PASS, 코스맥스 42시트 전수 연결은 미완성
- M-32: DEFERRED — 최초 도입 입력 필요
- M-33: DEFERRED — 현재/비교 이월 시나리오 필요
- M-34: PASS (stored writer) — 실제 화면/인쇄 제외
- M-35: PARTIAL — 명시적 모델 재실행 PASS, 전체 실자료 연결은 미완성
- M-36: NOT TESTED
- GOLD-01~14: 위 Matrix의 검증 범위별 판정; Phase 전체 PASS 선언 아님
- Full Python suite: 466 passed / 0 failed / 0 skipped / 0 errors
- UI regression: 16 PASS
- TypeScript: PASS
- Production build: PASS
- git diff --check: PASS
- Remaining risks: 미확정 당기 연결/차원/원천 최신성, Case B/이월 시나리오, Excel/편집기 시각 검증
