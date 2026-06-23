# PATCH 6 — 거래처 복수 컬럼 스캔 (더존 관리항목 대응)

> 배경: `scan`이 거래처를 단일 vendor 컬럼만 봐서, 거래처가 관리항목2 등
> 다른 컬럼에 들어간 더존 분개장에서 금융기관을 놓쳤다(모집단 완전성 위반).

## 변경 내역

| 파일 | 작업 | 비고 |
|---|---|---|
| `fi_detector.py` | 수정 | `_pick_vendor` 추가 + `scan`이 `vendor_candidates` 다중 컬럼 스캔 |
| `pages/13_Confirmation_Population.py` | 수정 | 거래처 매핑을 selectbox→multiselect, record에 후보 컬럼/값 |
| `profile_store.py` | 수정 | `vendor_cols`(다중 컬럼) 저장 허용 키 추가 |
| `test_confirmation_population.py` | 추가 | 관리항목 분산 케이스 3건(+기존 9케이스 유지) |

## 동작

- **UI**: "거래처명 후보 컬럼 *"을 multiselect로. 컬럼명에
  `관리항목/거래처/상대처/거래상대` 포함 컬럼을 기본 선택 후보로 자동 채움
  (+ H2/H3 추정 거래처 컬럼). 회계사 확인·수정 게이트 유지.
- **record**: `vendor_candidates`(선택 컬럼 값 리스트) + `vendor_cand_cols`(컬럼명).
  `vendor`는 첫 비공란 후보(대표값)로 유지 → 하위호환.
- **scan(`_pick_vendor`)**: 후보를 순회하며 레이어1 매칭. 채택 우선순위
  **사전매칭 > 접미어매칭**, 둘 다 없으면 첫 비공란 후보를 거래처로.
  채택된 거래처와 **매칭 컬럼(`vendor_col`)** 을 hit에 기록(검토 패널 표시용).
- 정규화·집계·온라인매칭은 채택된 거래처 기준으로 기존과 동일하게 동작.
- 하위호환: `vendor_candidates`가 없으면 기존처럼 단일 `vendor` 사용.

## 검증 게이트 (모두 통과)

- ✅ 관리항목2에만 "신한은행" → 탐지 (`test_case10_multi_vendor_columns`)
- ✅ 관리항목1=프로젝트명 + 관리항목2=은행명 → 은행 채택 (`test_case10b_...`)
- ✅ 기존 단일 vendor 케이스 회귀 (`test_case10c_...` + 기존 9케이스)
- **confirmation 회귀**: `13 passed, 0 failed`
- **H1/H2/H3/PATCH5 회귀**: 모두 유지
- **구문**: `py_compile` 통과

## 커밋

`feat(confirmation): scan multiple vendor columns for 더존 관리항목`
