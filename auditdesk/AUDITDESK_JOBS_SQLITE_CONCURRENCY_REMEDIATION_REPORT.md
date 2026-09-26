# AuditDesk Jobs SQLite Concurrency Remediation Report

## 범위와 재현

2026-09-24 `test/auditdesk-e2e-uat`에서 기존 사용자 DB와 작업 이력을 삭제하거나 초기화하지 않았다. 수정 전 `jobs.connect()`는 매 호출에서 `CREATE TABLE IF NOT EXISTS` 2건과 기존 `sessions` 컬럼에 대한 `ALTER TABLE` 5건을 시도했다. 따라서 `GET /api/jobs/{id}`와 `GET /api/jobs`도 schema 접근을 수행했다. 기존 `with jobs.connect()`는 Python sqlite3의 commit/rollback만 사용하여 실제 연결을 닫지 않았다. 사용자가 제공한 traceback의 `connect() → executescript(_SCHEMA) → database is locked` 경로와 일치한다.

수정 전에 추가한 회귀 테스트에서 `GET`의 DDL 실행과 연결 미종료가 실패했다(2 failed, 6 passed). 즉시 쓰기 트랜잭션을 잡은 상태에서 조회하는 동시성 테스트, 진행 중 반복 polling, 초기화 경쟁, 기존 DB 마이그레이션·이력 보존 테스트도 작성했다. 단일 테스트 환경의 즉시 쓰기 경합은 기존 구현에서도 통과했으므로, 해당 결과만으로 실제 UAT의 lock 재현이라고 주장하지 않는다. 재현된 결정적 결함은 polling 경로의 반복 schema 실행과 연결 미종료이다.

추가로 임시 SQLite 파일의 기존 기본 rollback journal에서 writer가 `BEGIN EXCLUSIVE`를 유지할 때, 수정 전 polling과 동일한 `reader.executescript(_SCHEMA)`를 실행했다. 0.2초의 재현용 timeout 뒤 `sqlite3.OperationalError: database is locked`가 발생했다. 실제 UAT traceback의 SQL 경로를 같은 잠금 조건에서 확인한 것이다. 이 재현은 사용자 DB를 사용하지 않았다.

## 원인과 수정

`auditdesk/jobs.py`에서 schema 생성·마이그레이션을 `initialize()`로 분리했다. 앱 시작의 `startup_recover()`에서 초기화되고, 독립 사용자는 최초 연결에서 한 번 초기화한다. 프로세스 안에서는 DB 절대 경로별 mutex와 완료 집합으로 중복 초기화를 막는다. 여러 프로세스에서도 SQLite `BEGIN IMMEDIATE`로 schema 변경을 직렬화하며, 실제 누락된 컬럼만 추가한다. 기존 DB의 `jobs`·`sessions`와 결과 이력은 그대로 유지한다. 평상시 `get/list/update` 연결은 schema DDL을 실행하지 않는다.

초기화 때 WAL을 설정했다. 이 DB에서는 장시간 계산은 job update 트랜잭션 밖에서 실행되고, polling read는 동시 writer와 공존해야 하므로 WAL이 적합하다. 초기화와 기본 쓰기 연결의 busy timeout은 30초, 조회 연결은 2초이다. 읽기 경합은 최대 3회만 재시도하며 50/100ms backoff 후에도 실패하면 `Retry-After: 1`이 붙은 HTTP 503과 사용자 메시지를 반환한다. `sqlite3.Connection` 기반 관리 연결은 정상·예외 종료 때 commit/rollback 후 close한다. `list_jobs`는 여러 연결을 열어 각 ID를 다시 읽는 방식에서 한 번의 일관된 SELECT로 변경했다. 이 경로에 전역 read/write 직렬화 lock은 추가하지 않았다.

`jobs`·`sessions` schema에는 외래키가 없으므로 `foreign_keys` 설정은 이 결함의 원인이 아니며 이번 hotfix에서 변경하지 않았다. Python sqlite3의 기본 deferred 트랜잭션은 유지하고, migration에만 `BEGIN IMMEDIATE`를 명시했다.

`jobs.submit()`의 계산은 기존과 같이 쓰기 트랜잭션 밖에서 실행하고, queued/running/progress/done/error 기록만 짧게 쓴다. 다만 별도 binding review 저장 경로의 큰 sidecar 생성·대량 저장은 아직 하나의 쓰기 트랜잭션 안에 있으므로 다른 writer의 지연 가능성은 남는다. 이번 국소 hotfix에서 recommendation 알고리즘·binding 저장 계약은 변경하지 않았다.

`webui/src/api.ts`의 polling은 전송/HTTP 조회 실패를 최대 3회 재시도한다. 실제 job의 `error` 상태는 그대로 반환한다. 지속적인 조회 실패는 별도 `JobPollingError`로 전달하고, `XbrlWorkflow`는 작업 ID를 유지한 채 “상태 다시 확인” 버튼을 보여준다. 이때 추천 생성이 실패했다고 표시하거나 같은 작업을 중복 시작하지 않는다.

## 회귀 검증

Python 회귀 9개는 반복 DDL 금지, 동시 writer와 get/list, background progress polling과 JSON·결과 보존, 동시/반복 초기화, 기존 DB 마이그레이션과 이력, 실제 실패 상태, 503 오류 계약, 연결 종료·rollback, DB 파일 보존을 검증한다. 수정 후 9 passed. UI 신규 테스트 3개는 일시 조회 오류 복구, 실제 job 실패 구분, 영구 조회 오류의 제한 재시도를 검증한다. 기존 Phase 4D UI 테스트에 작업 ID를 유지한 수동 재조회와 중복 시작 방지 테스트를 추가했다.

코스맥스 2026년 반기 연결 DSD를 사용자 DB가 아닌 임시 격리 DB에서 DSD-only로 다시 실행했다. `POST /analyze`는 200과 135개 표, `POST /start`는 202를 반환했다. job `ccd32a3a68ec`를 347회 polling한 결과 200은 347회, 500은 0회였다. 최종 상태는 `done`, workflow ID는 `a76876963a3d44dca9143452ef97992c`이다. `binding_reviews`에 결과 payload 221,203,278 bytes가 실제 저장됐음을 확인했다. 이 검증은 서버 API를 실제 코스맥스 자료로 호출한 것이며 사용자의 기존 DB는 건드리지 않았다.

전체 UI 59 passed, TypeScript `tsc -b` passed. production build는 sandbox의 상위 폴더 접근 제한으로 첫 실행이 중단됐으나, 같은 코드에서 권한 범위를 조정한 재실행이 통과했다(45 modules transformed). `git diff --check` passed. Python `tests/` 하위 실행은 373 passed, 2 skipped였다. 현재 checkout의 전체 repository suite는 750개가 수집됐고 최종 **748 passed, 0 failed, 2 skipped**(29분 58초)였다. 두 skip은 외부 고객 Golden 파일 경로가 기본 suite에 설정되지 않았기 때문이다. 제공된 코스맥스 Golden 폴더를 지정해 그 2건을 별도로 실행해 **2 passed**를 확인했다. 이 별도 실행 수치는 전체 750개 결과에 더하지 않는다.

## 남은 위험

WAL은 동일 DB 파일에 접근하는 프로세스의 동시 읽기에 유효하지만 네트워크 파일시스템 또는 외부 프로그램의 장시간 exclusive lock까지 보장하지 않는다. 지속 lock은 503으로 사용자에게 전달된다. `binding_api._connect()`의 반복 DDL 및 큰 review sidecar 저장의 쓰기 트랜잭션 길이는 별도 범위로 남긴다. 실제 브라우저 화면 클릭 검증은 수행하지 않았고 UI component/API 회귀와 실제 workflow API를 검증했다.

## 최종 상태

- Root cause: polling마다 schema DDL 실행과 연결 미종료; rollback journal의 writer 경합에서 동일 예외 재현
- Schema execution per GET before: 2개 CREATE + 최대 5개 ALTER 시도
- Schema execution per GET after: 0
- SQLite journal mode: WAL
- Busy timeout: 초기화·쓰기 30초, 조회 2초; 최대 3회 제한 재시도
- Concurrent polling test: PASS
- Actual polling 500 count: 0 / 347
- Final job status: done
- Recommendation workflow result: `a76876963a3d44dca9143452ef97992c`, DB payload 확인
- Full Python: 748 passed, 0 failed, 2 skipped / 750 collected; 외부 Golden 2건 별도 실행 2 passed
- UI: 59 passed
- TypeScript: PASS
- Production build: PASS
- git diff --check: PASS
- Remaining risks: 외부 장기 lock은 503, binding review 대량 저장의 쓰기 지연, 실제 브라우저 미검증
