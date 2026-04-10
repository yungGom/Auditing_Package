# AuditLink 버그 리포트

코드 분석 일자: 2026-04-10
분석 대상: auditlink/src/**/*.jsx, auditlink/backend/*.py

---

## Critical (즉시 수정 필요)

### ✅ C-1. 목업 데이터가 API 실패 시 실제 데이터처럼 표시됨 — 수정 완료

**영향**: 사용자가 가짜 데이터를 실제로 오인할 수 있음

| 파일 | 위치 | 내용 |
|------|------|------|
| `Engagements.jsx` | L35-91, L384-385 | `fallbackTree`, `fallbackTasks`가 초기값으로 사용됨. API 실패 시 한빛제조/서현테크 등 목업 데이터가 그대로 표시 |
| `Templates.jsx` | L8-96, L275 | `MOCK_TEMPLATES` (제조업/IT서비스/유통업)가 초기값. API 실패 시 목업 템플릿이 실제처럼 표시 |
| `ICFR.jsx` | L15-29, L123 | `MOCK_DATA` (11건 ICFR 테스트)가 초기값. API 실패 시 구분 불가 |

**해결 방안**: 초기값을 빈 배열로 설정하고, API 실패 시 에러 상태 표시 또는 "데이터를 불러올 수 없습니다" 안내

---

## High (가능한 빨리 수정)

### ✅ H-1. onClick 핸들러 없는 버튼 (기능 미작동) — 수정 완료

| 파일 | 위치 | 버튼 | 상태 |
|------|------|------|------|
| `Templates.jsx` | L299-302 | "새 템플릿" 버튼 | 클릭해도 아무 동작 없음 |
| `Templates.jsx` | L261 | "이 템플릿 적용" 버튼 (상세 모달) | 클릭해도 아무 동작 없음 |
| `Settings.jsx` | L284-296 | "데이터 백업" 버튼 | 클릭해도 아무 동작 없음 |
| `Settings.jsx` | L299-311 | "데이터 복원" 버튼 | 클릭해도 아무 동작 없음 |
| `Settings.jsx` | L314-323 | "데이터 초기화" 버튼 | 클릭해도 아무 동작 없음 |

### H-2. API 에러를 사용자에게 알리지 않는 곳 (silent `.catch(() => {})`)

데이터 로딩 실패 시 사용자에게 아무 피드백 없이 조용히 실패:

| 파일 | 함수/위치 | 설명 |
|------|-----------|------|
| `Templates.jsx` | L280 | 템플릿 목록 로딩 실패 → 목업 데이터 유지, 에러 표시 없음 |
| `ICFR.jsx` | L128 | ICFR 테스트 로딩 실패 → 목업 데이터 유지, 에러 표시 없음 |
| `Settings.jsx` | L80-88 | 설정 로딩 실패 → 기본값 유지, 에러 표시 없음 |
| `Header.jsx` | L506 | 알림 로딩 실패 → 알림 아이콘 뱃지 없이 표시 |
| `Header.jsx` | L374 | FY 목록 로딩 실패 → 빈 드롭다운, 에러 표시 없음 |

### H-3. ICFR 페이지 CRUD UI 미구현

백엔드에 CRUD API가 모두 존재하지만 프론트에서 호출하지 않음:
- ICFR 테스트 추가 불가
- ICFR 테스트 수정 불가 (행 클릭해도 아무 동작 없음)
- ICFR 테스트 삭제 불가

---

## Medium (계획적으로 수정)

### M-1. 낙관적 업데이트 (Optimistic Update) 실패 시 롤백 없음

API 호출이 실패해도 로컬 state가 이미 변경된 상태로 남음:

| 파일 | 함수 | 설명 |
|------|------|------|
| `Engagements.jsx` | `doRenameClient` | API 실패해도 트리에서 이름이 변경된 상태 유지 |
| `Engagements.jsx` | `doDeleteClient` | API 실패해도 트리에서 삭제된 상태 유지 |
| `Engagements.jsx` | `doDeletePhase` | API 실패해도 트리에서 삭제된 상태 유지 |
| `Engagements.jsx` | `doDeleteAccount` | API 실패해도 트리에서 삭제된 상태 유지 |
| `Engagements.jsx` | `doEditTask` | API 실패해도 제목이 변경된 상태 유지 |
| `Engagements.jsx` | `doDeleteTask` | API 실패해도 삭제된 상태 유지 |
| `Engagements.jsx` | `doChangeTaskStatus` | API 실패해도 상태가 변경된 상태 유지 |
| `Templates.jsx` | `handleDelete` | API 실패해도 카드가 삭제된 상태 유지 |
| `PBCPanel.jsx` | `handleDelete` | API 실패해도 항목이 삭제된 상태 유지 |

**영향**: 오프라인/네트워크 불안정 환경에서 UI와 서버 데이터 불일치 가능
**해결 방안**: API 실패 시 이전 state로 롤백하거나 에러 토스트 표시

### M-2. 검색 디바운스 타이머 메모리 누수 가능성

`Header.jsx`에서 컴포넌트 언마운트 시 `debounceRef.current` 타이머가 정리되지 않음:

```
// 현재: cleanup 없음
debounceRef.current = setTimeout(() => {...}, 300);
```

**해결 방안**: useEffect cleanup에서 `clearTimeout(debounceRef.current)` 추가

### M-3. 캘린더 빠른 추가 모달에서 클라이언트/계정 없을 때 처리 미흡

`Dashboard.jsx` `QuickAddModal`: 클라이언트가 없거나 계정과목이 없는 경우 드롭다운이 비어있지만 안내 메시지 없음

---

## Low (개선 권장)

### L-1. 도움말 버튼 미구현

`Header.jsx`: 도움말(help) 아이콘 버튼에 onClick 핸들러 없음. 클릭해도 아무 동작 없음.

### L-2. 설정 변경 시 사이드바 FY 표시가 갱신되지 않음

`Sidebar.jsx` L24: FY 표시가 `FY 2025`로 하드코딩되어 있음. 설정에서 활성 FY를 변경해도 사이드바에 반영 안 됨.

### L-3. PBC 엑셀 추적에서 개별 저장 에러 무시

`PBCExcelUpload.jsx`: 체크박스 변경 시 `api.upsertPBCExcelItem(...).catch(() => {})` — 저장 실패 시 사용자 피드백 없음.

### L-4. 엑셀 체크리스트 저장 에러 무시

`ExcelChecklist.jsx`: `api.upsertChecklist(...).catch(() => {})` — 저장 실패 시 사용자 피드백 없음.

### L-5. 알림 데이터 주기적 갱신 없음

`Header.jsx`: 알림 데이터를 최초 마운트 시 1회만 로딩. 앱 사용 중 새 마감이 지나도 갱신되지 않음. 주기적 폴링 또는 포커스 시 새로고침 필요.

### L-6. 타임존 처리 없음

D-day 계산(`calcDDay`)이 로컬 타임존 기반. UTC 자정 근처에서 1일 오차 가능성 있음.

---

## 요약 통계

| 심각도 | 건수 | 주요 내용 |
|--------|------|-----------|
| **Critical** | 1 | 목업 데이터 표시 문제 (3개 페이지) |
| **High** | 3 | 버튼 미구현 5개 + 에러 무시 5곳 + ICFR CRUD 없음 |
| **Medium** | 3 | 낙관적 업데이트 롤백 없음 9곳 + 타이머 누수 + 모달 예외처리 |
| **Low** | 6 | 도움말 버튼, 사이드바 FY, 에러 무시 2곳, 알림 갱신, 타임존 |

---

## 참고: 정상 동작 확인된 항목

다음 항목들은 코드 분석 결과 정상 동작:

- ✅ React Hook 순서: 모든 컴포넌트에서 훅이 조건문/early return 이전에 선언됨
- ✅ PBC 상세 모달 저장: `await` API 응답 → state 갱신 (수정 완료)
- ✅ 할일 상세 모달 저장: `await` API 응답 → state 갱신 (수정 완료)
- ✅ 설정 저장: `await` + 에러 알림 (수정 완료)
- ✅ 일괄 추가 (계정/할일): `await` API → 응답 데이터로 state 갱신
- ✅ 일괄 수정/삭제 (PBC): `await` API → 성공 후 state 갱신
- ✅ `useState(load)` (Settings.jsx): React lazy initializer로 정상 동작
