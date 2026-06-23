# PATCH 9 — 명세서 검토 스텝 (멀티시트 인벤토리 + 시트별 매핑 + 시트 드릴다운)

> 배경: 명세서는 통합문서(한 엑셀) 안에 예금·차입금·유가증권 등 계정별 시트가
> 나뉘고 헤더가 시트마다 다르다. 분개장과 동일한 검토를 하되 슬라이서 축이
> '계정'이 아니라 '시트'다. PATCH 8 드릴다운 컴포넌트를 재사용한다.

## 변경 내역

| 파일 | 작업 | 비고 |
|---|---|---|
| `fi_detector.py` | 추가 | `guess_sheet`(시트명→추정계정/금융여부) |
| `pages/13_Confirmation_Population.py` | 재구성 | 멀티시트 인벤토리·시트별 매핑·시트 드릴다운, 검토 컴포넌트 공용화 |
| `test_journal_review.py` | 추가 | PATCH 9 게이트(유가증권 적요기반·시트출처 보존·시트분류) |

## 화면 흐름

1. **시트 인벤토리**: `pd.ExcelFile(...).sheet_names` 로 전 시트 인식.
   `guess_sheet` 로 시트명→추정계정·금융여부. 표로 검토대상(기본)·시트·추정계정·
   행수·헤더행·거래처컬럼유무 노출. **비금융 추정 시트(매출처/재고/받을어음 등) 기본 체크 해제.**
   거래처 컬럼이 없고 적요만 있는 시트는 "없음(적요만)" + 경고 표시.
2. **시트별 컬럼 매핑**: 시트마다 거래처(복수)·적요·금액 매핑(계정은 시트힌트로 자동).
   매핑 프로파일/프리셋(H3) 재사용. (`mapping_widget` 공용 함수)
3. **시트 드릴다운**: PATCH 8 과 동일한 `render_drilldown`(행 포함 체크 + 일괄동작)을 시트 단위로 재사용.

## 일괄동작 (2층위)

- **시트 단위**: 시트 드릴다운의 "전체 포함 / 전체 제외" (예: 차입금명세서 8행 일괄).
- **행 단위**: data_editor 행별 포함 체크.

## 산출 (집계 연동)

- 시트 출처를 `source = "파일명 ▸ 시트명"` 으로 보존 → `_hits`·서면 검토 패널·산출물에서
  "어느 명세서 어느 시트" 원본 그대로 표시. **분개장 출처(파일명)와 명세서 시트 출처가 구분됨.**
- 검토 포함분(분개장 계정 + 명세서 시트)을 `REVIEW_GROUPS` 로 통합 → `hits_from_included` →
  `aggregate`. 검토 대상 아닌 기타 자료만 기존 `scan` 자동 탐지.
- row_no는 파일·시트 통합 후 일괄 부여(유니크 보장).

## 검증 게이트 (모두 통과)

- ✅ 통합문서 전 시트 읽힘 + 비금융 시트 자동 제외 (`test_guess_sheet_classification` + E2E)
- ✅ 시트마다 다른 헤더(거래처명/거래처) 각각 매핑되어 거래처 추출 (E2E)
- ✅ 거래처 없는 시트(유가증권)에서 적요 기반 검토 (`test_statement_securities_memo_based`)
- ✅ 시트 전체 일괄 포함 (`render_drilldown` 전체 포함; backend는 PATCH8 gate3)
- ✅ 병합 결과에서 분개장 출처(파일) vs 명세서 시트 출처(파일 ▸ 시트) 구분 (`test_hits_preserve_sheet_source` + E2E)
- ✅ 기존 회귀 전부 통과 (6개 suite)
- **PATCH 8+9 backend**: `test_journal_review.py 9 passed`
- E2E 스모크: 예금/차입 자동 + 유가증권 적요 수기 + 매출처 제외, 출처 시트별 구분 정상
- 구문: `py_compile` 통과

## 커밋

`feat(confirmation): statement review step with multi-sheet inventory`
