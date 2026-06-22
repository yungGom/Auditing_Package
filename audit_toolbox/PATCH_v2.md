# PATCH 2 — Phase H1: 헤더 행 자동 탐지

> 목표: 업로드 파일 상단을 스캔해 헤더 행을 자동 추정하고, 회계사가
> `number_input`으로 덮어쓸 수 있도록 그 값을 기본값으로 채운다.
> (자동 추정을 맹신하지 않되 회사당 반복 입력 부담을 줄인다.)

## 변경 내역

| 파일 | 작업 | 비고 |
|---|---|---|
| `mapping_utils.py` | 신규 | `GUESS`·`guess_col`·`detect_header_row` (streamlit 비의존, 테스트 가능) |
| `pages/13_Confirmation_Population.py` | 수정 | ① `GUESS`/`guess_col`을 `mapping_utils`에서 import (중복 제거) ② 업로드 루프에서 상단 21행 probe → `detect_header_row`로 헤더행 추정 → `number_input` 기본값/안내 캡션 |
| `test_mapping_utils.py` | 신규 | H1 회귀 테스트 (pytest/standalone 겸용) |

## 탐지 규칙

- 상단 0~20행을 스캔, 각 행에서 거래처·계정·적요·금액 **4개 카테고리** 중
  키워드(부분일치)가 잡히는 카테고리 수를 센다.
- **2개 카테고리 이상**이 잡히는 **첫 행**을 헤더로 확정(상단 우선).
- 어디서도 2개 미만이면 가장 점수 높은 행, 그래도 없으면 0행(수동 조정 전제).

## 검증 게이트

- **H1 자동탐지**: ✅ `6 passed, 0 failed`
  - **더존식 머리글 3줄 → 4행(인덱스3) 자동 탐지** (게이트 핵심 케이스)
  - 헤더 0행 / 비표준 헤더명(상대처·적요내용·발생액) / 잡음행(키워드 1개) 오인 방지 / fallback 0 / guess_col 동의어
- **PATCH 1 회귀**: ✅ `10 passed, 0 failed` (기능 동등성 유지)
- **구문**: ✅ `py_compile` 통과

## 비고

- 파일을 두 번 읽으므로(probe + 본문) `f.getvalue()` 바이트를 받아
  `io.BytesIO`로 재사용 — 업로드 포인터 소진 문제 없음.
- H2(별칭·시그니처 보조 추정)는 PATCH 4. `mapping_utils`가 그 토대.

## 다음 단계

- PATCH 3: Phase H3 매핑 프로파일 저장·재사용.
  - 7장 열린 결정(저장 위치) 기본값 채택 예정: `~/.audit_toolbox/mapping_profiles.json`
    (앱이 OneDrive/저장소 어디서 실행되든 동일 위치 공유, 데이터 아닌 컬럼 메타만 저장).
