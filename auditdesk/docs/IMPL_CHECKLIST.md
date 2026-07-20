# AuditDesk 구현 추적 체크리스트 (IMPL_CHECKLIST)

> 원천: docs/REQUEST_LEDGER.md (요청 이력 대장). 대장의 각 행을 구현
> 파일·스펙·게이트·테스트로 잇는 **순방향 매트릭스**와, 코드·스펙에는
> 있으나 대장에 없는 기능을 찾는 **역방향 대조**로 구성.
> 기준일: 2026-07-18 (커밋 cd600c4, GATES 29). 공란 금지 — 미구현이면
> 상태(보류/백로그)와 사유를 적는다.
>
> 경로 약칭: `wb/` = dsd_workbench/dsd_tool, `ex/` = dart_explorer,
> `rt/` = auditdesk/routers, `ui/` = webui/src, `tests/` = wb/tests

---

## 1. 순방향 — 대장 행 → 구현·검증

### A. 변환기 코어

| 항목 | 발원 | 구현 위치 | 검증 | 상태 |
|---|---|---|---|---|
| DSD↔Excel 양방향 변환 (위치 기반 교체 v2) | 요청 (5월) | `wb/excel_out.py`(extract, `_MAP` 오프셋 기록) · `wb/repack.py`(diff/repack, 뒤→앞 교체) · `wb/zipsplice.py`(ZIP 바이트 재조립) — 스펙 DSD_PIPELINE_SPEC.md | 게이트 2셀→2건·바이트 일치 — `tests/test_pipeline.py`, `batch_validate.py` 12/12 | ✅ |
| 신뢰성 문제(중복값 오교체·빈 셀) 해결 | 요청 | 위와 동일 (찾아치환 폐기 = 위치 기반 교체의 설계 목적) | `tests/test_pipeline.py` false positive 0 | ✅ |
| 주석 참조 `3,4,5,6` 버그 / `&cr;` 가짜 변경 | 버그 수정 | `wb/repack.py` try_number 천단위 검증 · `wb/textutil.py` 디코딩 비교 | 회귀 `tests/test_pipeline.py` | ✅ |
| 서식 지원 | 요청→운영결정 | **미지원 확정** (USERMARK 비문서화 — H절) | — | 제외 |
| 회귀 테스트 체계 | 제안승인 (6/10 ①) | `tests/` 17개 모듈 + `batch_validate.py` + `ex/tests` | 상시 (V-1 시점 59 passed 스코프, UI-4 시점 전체 202) | ✅ |
| dart4.xsd 로컬 사전검증 (lxml) | 제안승인 (6/10 ②) | **없음** — repack 파이프라인에 스키마 검증 부재 (V-1a 부록 a 실사). 현행 안전장치: 바이트 보존+위치 교체+바이트 일치 게이트 | — | ⏸ 백로그 |
| 변경 로그 (셀 주소·전→후·타임스탬프) | 제안승인 (6/10 ③) | `wb/history.py`(SQLite: runs ts·SHA1·옵션 / changes 시트·행·열·old·new·reason) · CLI `dsd_tool history` · `rt/workbench.py` `/sessions/{sid}/history` · UI-1 이력 화면 — 형태는 시트가 아닌 DB+화면. A-5와 연계 없음(별개 산출물, 부록 b) | A-2 게이트 · `tests/test_history.py` | ✅ (A-2) |
| 표 행 추가/삭제 | 제안승인 (6/10 ④) | **없음** — repack은 `_MAP` 값 교체만 (부록 c 실사) | — | ⏸ 보류 (H절) |
| 수정이력 SQLite + history CLI | 요청 (지시서 A-2) | 위 변경 로그 행과 동일 구현 | A-2 게이트 | ✅ |
| 편집기 버전 관리 (editver) | 요청 (로드맵 1) | `wb/version.py` · KNOWN_VERSIONS.md · version-check CLI(A-3b) | A-3/A-3b 게이트 · `tests/test_version.py`, `test_version_check.py` | ✅ |

### B. 수신·검색

| 항목 | 발원 | 구현 위치 | 검증 | 상태 |
|---|---|---|---|---|
| 공시 검색 | 요청 (로드맵 2·5) | `ex/client/opendart.py`(corpCode·list 검색) · `cache.py`(7일/1일/영구) · `config.py`(.env 키) · `rt/explorer.py` · `ui/Explorer.tsx` | B-1 게이트 · UI-4 E2E | ✅ |
| 업종코드 필터 | 요청 (로드맵 5) | `ex/client/opendart.py` induty_code · UI-5 검색 필터 | UI-5 게이트 | ✅ |
| 동종업계 벤치마크 탐색 | 요청 (dart_benchmark_finder 승계) | UI-5 동종업계 토글 (`ui/Explorer.tsx` + `rt/explorer.py`) — 원 스크립트는 `ex/legacy/` | UI-5 게이트 | ✅ |
| 공시 원본 수신 (읽기 전용) | 요청 (ACCIO 전제) | `ex/client/opendart.py` document.xml · `ex/converters/`(DSD 래핑) — B-2 구조대조 REPORT_B2_구조대조.md | B-2 게이트 (형식 대조·주석 분할 한계 실측) | ✅ |
| XBRL 파이프라인 + 코퍼스 | 요청 (로드맵 3) | `ex/xbrl/pipeline.py`(원클릭) · `xbrl_extract.py`·`xbrl_diff.py`(승계 도구) · `corpus.py`(D-3a 3,976사) · `ex/corpus/` | B-3 게이트(SHA 동일) · D-3a 전량 빌드 | ✅ |

### C. 분석 산출물

| 항목 | 발원 | 구현 위치 | 검증 | 상태 |
|---|---|---|---|---|
| 차원표 렌더 (본문+주석 시트) | 요청 (로드맵 3) | `ex/xbrl/dimension_table.py`(XbrlInstance·렌더, D-2/D-2b/오매칭 수정 c636a10) | D-2/D-2b 게이트(육안 포함) · UI-5 게이트 B(34시트) | ✅ |
| 차원표 편집기 입력 3열 | 요청 (7/18) | `wb/taxonomy_labels.py`(LabelResolver — 배포 엑셀 조인) · `dimension_table.py` `_enrich_sheet` · assets/taxonomy(gitignore, KNOWN_VERSIONS 등재) | D-2c G1~G3 · `tests(ex)/test_dimension_table_d2c.py` · F 회귀 2/2 | ✅ |
| ACCIO식 엑셀 즉시 다운 | 요청 (로드맵 2) | UI-5 [엑셀로 변환] (`rt/explorer.py` → `wb/excel_out.py` extract) | UI-5 게이트 A (5,554셀) | ✅ |
| '원문' 통합 시트 | 요청 (§7.5 P3) | `wb/excel_out.py` — `[[시트명]]` 세로 연결, `_MAP` 미포함 | `tests/test_foot_excel.py` 3/3 | ✅ |
| 태깅 추천 (인벡터 ①) | 요청 (6/10) | `wb/mapping.py`(Top-4, 동업종 ×2) ← `ex/xbrl/corpus.py` 실증 | D-3b 홀드아웃 99.0% · `tests/test_mapping.py` | ✅ |
| 신버전 호환성 점검 (D-4c) | 요청 (로드맵 7 C4) | `ex/xbrl/taxonomy.py`·`taxonomy_diff.py`(taxdiff·taxcheck·승격 감지) — UPDATE_MANAGEMENT_SPEC.md | D-4 게이트(1,334/156 정확) | ✅ |

### D. 검증 3종

| 항목 | 발원 | 구현 위치 | 검증 | 상태 |
|---|---|---|---|---|
| 합계검증·주석대사 | 요청 (지시서 A-4 — DSDbreaker 역분석) | `wb/foot.py`(FootingContext·`_FOOT`·정규화) — FOOTING_SPEC_A4.md | A-4 게이트(한빛·삼성) · `tests/test_foot.py`, `test_hanbit.py` | ✅ |
| AI_Footing 형식 엑셀 | 요청 (예시 10종) | `wb/foot_excel.py`(총괄표·하이퍼링크·오류 서식) — PATCH_A5_SPEC.md | A-5a 게이트 · `tests/test_foot_excel.py` | ✅ |
| 전기대사 | 요청 | `wb/recon.py`(모드 3종·TRUE/FALSE·제목 정규화 매칭·셀 참조 수식) — PATCH_A5_SPEC.md | A-5b 게이트(삼성 전수+변조) · `tests/test_recon.py` | ✅ |
| XBRL 인스턴스 대사 (인벡터 ②) | 요청 (6/10→V-1) | `wb/xbrl_recon.py`(5분류·허용오차·표준레이블 열·무차원/차원 분리) + `rt/studio.py` `/xbrl-recon`(조립층) — V1_XBRL_RECON_SPEC.md | V-1 G1~G3 + V-1a 재실행 67/99 유지 · `tests/test_xbrl_recon.py` | ✅ |

### E. 작성 지원

| 항목 | 발원 | 구현 위치 | 검증 | 상태 |
|---|---|---|---|---|
| 분반기 첫 공시·완전 신규 워크시트 | 요청 (7/18) | `wb/worksheet.py`(F-1 본문) · `wb/note_worksheet.py`(F-2/F-2b 주석 role·축 배정) · `wb/succession.py`(F-3 승계) + `ex/xbrl/corpus.py` export_succession_assets — PHASE_F_XBRL_AUTHORING_SPEC.md | F-1 92.4% / F-2b member 100%·분류 95.3% / F-3 정확도 100% · `tests/test_worksheet.py`, `test_note_worksheet.py`, `test_succession.py` | ✅ |
| 산출물=전사 가이드 (확정☐) | 운영결정 | 워크시트 확정☐ 열 + "완성 아님" 명시 · Studio 매핑 확정 기록(`rt/studio.py` mapping_decisions) | UI-3 E2E(확정 20건 기록) | ✅ |
| 워크시트 원클릭 진입 | 요청 (UI-5) | `ui/Explorer.tsx` [워크시트] → Studio 경로 프리셋 | UI-5 | ✅ |

### F. UI·동선

| 항목 | 발원 | 구현 위치 | 검증 | 상태 |
|---|---|---|---|---|
| 4개 영역 화면 | 요청 (로드맵 4 + Design Brief 2종 + 라우터 계약 지시서) | `ui/App.tsx`(셸·해시 라우팅) · `Session.tsx`(Workbench+Footing 탭) · `Studio.tsx`+`RecCard.tsx` · `Explorer.tsx` · `rt/`(workbench·studio·explorer·jobs_api — 기존 함수 얇은 래퍼) | UI-1~4 브라우저 E2E (CLI 정합·SHA1 동일) | ✅ |
| 원클릭 동선 통합 | 요청 (7/16) | UI-5 검색 행 4버튼 (`ui/Explorer.tsx` + `rt/explorer.py`) | UI-5 게이트 (2클릭 ×2) | ✅ |
| 최근 수신 패키지 드롭다운 | 요청 | `/api/explorer/packages` + Studio·세션 드롭다운 | UI-5 ③ | ✅ |
| XBRL 대사 화면 | V-1 지시 ⑤ | `ui/Session.tsx` XbrlReconSub (서브탭·배너·필터·딥링크) | V-1 게이트 + 브라우저 확인 | ✅ |

### H. 의식적 보류·제외 (구현 없음이 정상)

| 항목 | 상태 | 근거 |
|---|---|---|
| IXD 직접 생성 | 제외 | 편집기 유일 경로 — 대응 코드 없음이 준수 상태 |
| 바닥부터 DSD 생성 | 폐기 | dart4.xsd — 동상 |
| USERMARK 서식 | 제외 | 동상 |
| OpenDART 원본 왕복 | 한정 | 수신물 meta.xml 없음→editver 미검출→경고 노출로 구현됨 (`rt/studio.py`·V-1 배너) |
| 표 행 추가/삭제 | 보류 | 부록 c 실사로 미착수 확정 — 코드 부재가 기록과 일치 |
| dart4.xsd 사전검증 | 백로그 | 부록 a 실사 — 코드 부재가 기록과 일치 |

**G1 판정: 대장 전 행 기재 완료 — 미매칭 0** (미구현 3건은 전부
보류/백로그/제외 상태와 사유 명기, H절과 정합).

---

## 2. 역방향 — 코드·스펙에 있으나 대장에 없던 기능

대장 갱신(2026-07-18) 전 기준으로 대조한 결과. **발원 불명 = 0건** —
아래 5건이 대장에 행이 없었으나, 전부 발원이 문서로 추적되어 대장에
반영했거나(A-2·A-3) 성격상 대장 스코프 밖(인프라·소품)으로 판단했다.

| 발견 항목 | 구현 | 발원 추적 결과 | 처리 |
|---|---|---|---|
| 수정이력 SQLite (A-2) | `wb/history.py` | 지시서 [패치 A-2] "감사조서 증빙용" — 발원 확인 | 대장 A절에 행 추가 (6/10 권고③ 행과 동일 구현임을 병기) |
| editver 버전 관리 (A-3/A-3b) | `wb/version.py`·KNOWN_VERSIONS.md | 초기 로드맵 항목 1 — 발원 확인 | 대장 A절에 행 추가 |
| 택소노미 트리 뷰 (D-1) | `ex/xbrl/taxonomy.py` + `ui/Studio.tsx` 트리 뷰 | 지시서(XBRL 지도) — D-2 차원표의 전신·보조 화면. 대장 C절 차원표 행의 하위 구성으로 간주 | 대장 별도 행 없이 유지 (F절 UI-3 구성에 포함) |
| 상태 대시보드 (E-0) + 홈·작업 목록 | `ui/StatusPage.tsx`·`Home.tsx`·`rt/status.py` | 지시서(E-0 읽기 전용 대시보드) — 인프라성 화면 | 대장 F절 "4개 영역 화면"에 포섭 (별도 행 불요) |
| RUN.bat 원클릭 실행기 | 레포 루트 RUN.bat (커밋 28ae843) | git log 외 지시 근거 없음 — 실행 편의 소품 | 성격상 대장 스코프 밖 (배포 시점 PyInstaller 로드맵의 임시 대체) |

**G2 판정: 발원 불명 0건.** 대장 추가 후보 2건(A-2·A-3)은 이번
갱신에서 A절에 반영 완료, 나머지 3건은 기존 행의 하위 구성이거나
스코프 밖으로 정리.
