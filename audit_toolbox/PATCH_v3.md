# PATCH 3 — Phase H3: 매핑 프로파일 저장·재사용

> 목표: 컬럼 헤더 시그니처를 키로 확정 매핑을 로컬 JSON에 저장하고,
> 동일 양식 파일 재업로드 시 자동 적용 → 회사당 매핑 반복을 없앤다.

## 7장 열린 결정 — 채택값

- **매핑 프로파일 저장 위치: 사용자 홈 `~/.audit_toolbox/mapping_profiles.json`**
  - 앱이 OneDrive/저장소 어디서 실행되든 동일 위치를 공유.
  - 저장소 밖이라 git에 데이터가 섞일 일 없음(.gitignore의 `profiles/`도 불필요).
  - 변경 원하면 `profile_store.default_path()` 한 곳만 수정.

## 변경 내역

| 파일 | 작업 | 비고 |
|---|---|---|
| `profile_store.py` | 신규 | 시그니처·저장/로드·프리셋·매칭 (streamlit 비의존) |
| `pages/13_Confirmation_Population.py` | 수정 | 매핑 단계에 `match_mapping` 자동적용 + "💾 매핑 저장/갱신" 버튼 |
| `test_profile_store.py` | 신규 | H3 회귀 테스트 (임시 경로 사용, 사용자 홈 비오염) |

## 동작

- `compute_signature(headers)`: 정렬·중복제거 후 SHA1 → 컬럼 순서/중복 무관 안정 키.
- `match_mapping(headers)`: ① 사용자 저장본(`user`) → ② ERP 프리셋(`preset`) → ③ None.
  - 사용자 저장본이 프리셋보다 항상 우선.
- 화면: 저장본 적용 시 "📌 저장된 매핑 자동 적용", 프리셋 시 "🧩 프리셋 추정" 안내.
  버튼으로 현재 매핑을 시그니처에 저장(다음부터 우선 적용).
- ERP 프리셋: 더존 분개장 2종 동봉(매핑 컬럼명이 헤더에 모두 존재할 때만 매칭, 보수적).

## 보안 (절대 준수)

- 저장 JSON에는 **컬럼명 매핑 메타데이터만** 기록.
  `_ALLOWED_KEYS = {vendor, account, memo, amount, header_row, label, headers}` 외 키는
  `_sanitize`에서 전부 폐기. 재무수치·기관명·거래처값·**파일명/클라이언트명 저장 안 함**
  (`label`은 파일종류='분개장/명세서'만).
- 회귀 테스트 `test_security_drops_non_metadata_keys`로 고정: 금액·기관명·파일명이
  JSON에 절대 남지 않음을 검증.

## 검증 게이트

- **H3**: ✅ `6 passed, 0 failed`
  - **같은 양식 2회차 업로드 → 저장 매핑 자동 적용** (게이트 핵심)
  - 시그니처 순서/중복 무관 / 저장·로드 왕복 / 보안 키 폐기 / 프리셋 부분집합 / 저장본>프리셋
- **회귀(PATCH1)·H1(PATCH2)**: ✅ 유지
- **구문**: ✅ `py_compile` 통과

## 다음 단계

- PATCH 4: Phase H2 별칭·데이터 시그니처 보조 추정.
- PATCH 5: 사전·온라인목록 외부 엑셀 분리.
