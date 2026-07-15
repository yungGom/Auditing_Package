# [Claude Code 작업 지시서] AuditDesk 웹 앱 — 라우터 계약 + React UI 구현

> 입력물: AuditDesk_v2__standalone_.html (승인된 디자인 — **참조 구현**, 이 화면 그대로 이식)
> 스택: FastAPI(백엔드 래퍼) + React/TypeScript/Tailwind/Vite (AuditLink v2 표준 토큰 유지)
> 대원칙: **백엔드 로직 신규 작성 금지** — 라우터는 기존 dsd_tool/dart_explorer 함수의 얇은 래퍼.
>          로직이 부족하면 라우터에서 채우지 말고 중간 보고 후 정지.
> 순서: UI-1 → UI-2 → UI-3 → UI-4, 패치별 게이트 통과 → 커밋 → 다음.

---

## 0. 실행 구조와 보안 경계

- 단일 로컬 서버: `python -m auditdesk` → FastAPI(:8710) + 정적 React 빌드 서빙. localhost 전용, 인증 없음
- 라우터 3분할, **import 방향 강제**:
  - `/api/workbench/*` → dsd_workbench 함수만 import (네트워크 라이브러리 import 금지 — 기존 가드 테스트 확장)
  - `/api/explorer/*` → dart_explorer (OpenDART 수신 허용)
  - `/api/studio/*` → dart_explorer의 xbrl 모듈 + dsd_tool 매핑 (수신은 캐시 경유만)
- 파일 접근: 로컬 앱이므로 경로 문자열로 직접 (업로드 스트림 아님).
  프론트 파일 선택은 OS 대화상자 호출 API(`POST /api/fs/pick`) 또는 경로 입력 — v2 디자인의 드래그&드롭 존은 경로 drop으로 처리
- E-0 대시보드는 `/api/status/*`로 승격 (기존 dashboard 모듈 라우터 이식, 별도 서버 폐지)

## 1. 작업(Job) 모델 — 장시간 작업 공통 패턴

extract/foot/recon/repack/worksheet/corpus 등 수 초~수 시간 작업은 전부:
```
POST /api/{module}/{action}          → 202 { job_id }
GET  /api/jobs/{job_id}              → { state: queued|running|done|error,
                                         progress: {current, total, message},
                                         result_ref | error_detail }
GET  /api/jobs?active=true           → 진행 중 목록 (홈 상태 카드용)
```
- 구현: 프로세스 내 스레드 풀 + SQLite job 테이블 (재시작 시 running→interrupted)
- 코퍼스 빌드처럼 기존 백그라운드 실행이 있는 작업은 그 상태 파일을 job으로 노출만

## 2. 라우터 계약

### /api/workbench
```
POST /sessions                    {dsd_path} → {session_id, meta{sha1, editver, company, cells, notes, cr_only}}
GET  /sessions                    → 세션 목록 (최근순, 상태칩용 state 포함)
GET  /sessions/{id}               → 상세 (파이프라인 단계 상태 포함)
POST /sessions/{id}/extract       → job (완료 시 xlsx_path)
GET  /sessions/{id}/sheets        → 시트 목록 / GET /sheets/{name} → 셀 그리드 JSON (읽기 전용 뷰)
POST /sessions/{id}/foot          {excel?: bool} → job → {summary{match,rounding,mismatch,cross}, findings[], levels[]}
PUT  /sessions/{id}/foot/levels   {overrides:[{sheet,row,level}]} → 재검증 job
POST /sessions/{id}/recon         {prior_path | prior_cache_ref, tolerance?} → job
                                  → {verdict: bool, body[], notes[], excel_path}
POST /sessions/{id}/diff          {options{clean_cr, note_dedup}} → dry-run: {changes:[{sheet,cell,before,after,reason}], counts}
POST /sessions/{id}/repack        {approved_change_ids[] | all, options} → job → {output_path, checklist[]}
                                  ★ diff 미실행 상태로 호출 시 409 — 변경검토가 승인 게이트임을 서버가 강제
GET  /sessions/{id}/history       → history.sqlite 항목 / POST /history/export → xlsx
GET  /workbench/version-check     {dsd_path} → {editver, known: bool, g2_smoke: pass|fail}
```

### /api/studio
```
POST /taxtree      {package_path | taxonomy_version, role?} → job → 트리 JSON(들여쓰기 렌더용) + xlsx_path
POST /dimtable     {package_path, role?} → job → 표 JSON(중첩 헤더 스키마) + xlsx_path
POST /mapping      {accounts:[{name, category}] | template_path} → job
                   → {items:[{account, candidates:[{element, label, score, evidence{firms, similarity, industry_boost}, state: normal|extension_needed|standard_recommended}], decided?}]}
PUT  /mapping/{job}/decide  {account_idx, element | extension} → 확정 기록 (누가/언제)
POST /taxcheck     {prior_package, against_version} → job → {green[], yellow[{element, candidates[]}], blue[]} + xlsx
POST /worksheet    {dsd_path, report: annual|half|q1|q3, mode: new|inherit, inherit_package?} → job
                   → xlsx_path + {summary{mapped, unmapped, extension_candidates, decided_pct}}
                   ※ notes 부분은 F-2 게이트 전이면 501 + "F-2 미완" 메시지 (자리만 — 허위 구현 금지)
GET  /taxonomies   → 보유 버전 목록 (D-4a)
POST /taxdiff      {old, new} → job → diff 요약 + xlsx
```

### /api/explorer
```
GET  /search       ?corp=&from=&to=&type=&industry= → 공시 목록 (+cached: bool)
POST /fetch        {rcept_no} → job → 캐시 경로
POST /xbrl         {corp, year, diff_year?} → job (파이프라인 스텝 progress.message로 중계) → 결과 카드 데이터
GET  /corpus/stats → E-0 카드 데이터 / POST /corpus/build → job (재개 로직 그대로)
GET  /settings     → {api_key_set: bool, cache_size, today_usage} / DELETE /cache
```

### /api/status
```
GET /overview      → E-0 5패널 통합 JSON (홈 상태 카드 + 상태 페이지 공용)
GET /gates         → GATES.json / GET /versions → KNOWN_VERSIONS
```

## 3. React 이식 지시

1. **v2 HTML이 정답지** — 레이아웃·컴포넌트·문구·토큰을 그대로 컴포넌트화. 재디자인 금지.
   디자인시스템 zip(_ds: colors_and_type.css, fonts)을 Tailwind 토큰으로 변환해 사용
2. 컴포넌트 우선순위: **추천 카드**(상태 4종 — mapping/taxcheck/worksheet/foot 공용),
   숫자 그리드(고정폭·우측정렬·음수 빨간 괄호 — sheets/dimtable/recon 공용),
   findings 리스트, job 진행 스텝퍼, 신뢰 뱃지(모듈별 상단 고정)
3. 상태 관리: 서버가 진실 원천 — 화면은 job 폴링(2~5s)과 재조회로만 갱신. 낙관적 업데이트 금지
   (감사 도구 — 화면과 파일이 다르면 사고)
4. 에러 표면화: error_detail을 실무자 언어로 (기존 CLI의 PermissionError 번역 등 재사용)

## 4. 패치 분할과 게이트

| 패치 | 범위 | 게이트 (전부 실파일 E2E) |
|------|------|--------------------------|
| UI-1 | 셸(3모듈 네비+신뢰뱃지) + 시즌 홈 + 상태 페이지 + Workbench 세션 흐름 (열기→extract→시트뷰→**변경검토→repack**) | 삼성 FY2025 DSD로 브라우저 E2E: 변경 2건 승인 repack → 산출 DSD가 CLI 산출과 SHA 동일 / diff 미실행 repack 409 확인 |
| UI-2 | Footing 탭(findings·레벨 오버라이드·AI_Footing 내보내기) + 전기대사 서브탭 | 삼성 페어 recon → 화면 113 TRUE = CLI 결과 정합 / 레벨 수정→재검증 반영 |
| UI-3 | XBRL Studio 5화면 (worksheet notes는 F-2 상태에 따라 501 처리) | 매핑 확정 E2E: 계정 20건 → 추천 카드 확정 → 확정 기록 조회 / 차원표 화면 = xlsx 산출과 값 동일 |
| UI-4 | Explorer (검색·fetch·xbrl 파이프라인·코퍼스 카드·설정) | 실검색→캐시 뱃지→xbrl 실행 스텝퍼 완주 |

각 게이트에 **스크린샷 필수** (E-0 때처럼 캡처 실패 시 대체 증빙 허용하되 사유 명기).
백엔드 함수 수정이 필요해 보이면 수정하지 말고 보고 후 정지.

## 5. 스코프 제외
- 인증/멀티유저/배포 패키징(PyInstaller는 후속) / 시트 셀 편집 / F-2·F-3 미완 기능의 선구현
