# PATCH 8 — 분개장 검토 스텝 (계정 슬라이서 + 드릴다운 + 일괄동작)

> 배경: 실무는 자동 탐지 결과만 보는 게 아니라, 분개장을 계정으로 좁힌 뒤
> 그 계정의 거래처·적요를 사람이 훑어 조회처 포함을 판단한다. 자동 탐지는
> 1차 추천(체크 기본값)으로만 쓰고 최종 판단은 회계사가 한다. (PATCH 6 선행)

## 변경 내역

| 파일 | 작업 | 비고 |
|---|---|---|
| `fi_detector.py` | 추가 | `_detect_row`·`account_summary`·`review_journal`·`hits_from_included` |
| `pages/13_Confirmation_Population.py` | 수정 | 3️⃣ 분개장 검토(슬라이서+드릴다운+일괄동작), 탐지 로직을 검토 포함분 기반으로 |
| `test_journal_review.py` | 신규 | PATCH 8 회귀(게이트 포함) |

## 화면 흐름 (분개장 단일 시트 전제)

1. **컬럼 매핑**: 거래처(복수, 관리항목 포함)·적요·계정·금액 (기존 PATCH 6).
2. **관련 계정 선택(슬라이서)**: 분개장 실제 계정 distinct + 건수. `FI_ACCOUNTS`
   매칭 계정(🏦)은 기본 선택, 나머지는 multiselect 드롭다운(고른 것만 칩 노출).
3. **계정 드릴다운**: 선택 계정을 expander로 펼쳐 거래행 표(일자·거래처·적요·금액·포함 체크).
   - 자동 탐지(레이어1 거래처 / 레이어2 계정)가 잡은 행 → 포함 ✅ 기본 ON + "자동추천".
   - 거래처 공란/비금융 + 적요에 단서 → 🟡 "적요확인필요", 기본 OFF, 회계사가 적요 읽고 결정.
   - 비금융 추정 → 미체크.

## 일괄동작

- **계정 단위**: "이 계정 전체 포함 / 전체 제외" 버튼(차입금처럼 거의 다 대상인 계정).
- **행 단위(보이는 행 전체)**: 계정 expander가 곧 현재 보이는 행 집합 → 위 버튼이 전체 토글.
- 상태는 `st.session_state["incmap::<계정>"]`(row_no→bool)로 관리, 버튼은 에디터 키를
  리셋 후 `st.rerun()` 으로 즉시 반영.

## 산출 (집계 연동)

- 포함 확정 행 → `hits_from_included` → `aggregate` → 후보 반영.
  비탐지 행을 사람이 포함하면 `basis="수기포함"`으로 후보화.
- `_hits`에 `review_account`(어느 계정)·`row_no`(어느 행)·`included_via`(추천/적요확인/수기) 기록
  → 5단계 병합·근거 표시용.
- 명세서 등 비분개장은 기존 `scan` 자동 탐지 유지. 최종 hits = 분개장 포함분 + 명세서 자동.

## 검증 게이트 (모두 통과)

- ✅ 관리항목에 숨은 은행이 거래처로 잡혀 드릴다운에 뜸 (`test_gate1_...`)
- ✅ 거래처 공란 + 적요 은행명 → 🟡 적요확인필요, 체크 시 후보 반영 (`test_gate2_...`)
- ✅ 계정 전체 포함/제외 일괄동작 (`test_gate3_...`)
- ✅ 기존 회귀 전부 통과 (confirmation 13 / mapping / profile / h2 / external / journal_review)
- **PATCH 8**: `6 passed, 0 failed`
- E2E 스모크: 자동추천 포함·적요확인 수기포함·미선택 계정 안전망·전기 병합 정상
- 구문: `py_compile` 통과

## 커밋

`feat(confirmation): journal review step with account slicer and drilldown`
