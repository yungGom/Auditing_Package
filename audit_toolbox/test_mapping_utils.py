# -*- coding: utf-8 -*-
"""
PATCH 2 (H1) — 헤더행 자동 탐지 회귀 테스트.
- pytest:        pytest test_mapping_utils.py
- standalone:    python test_mapping_utils.py   (외부 설치 불필요)
"""
from mapping_utils import detect_header_row, guess_col, GUESS


# ── H1 검증 게이트: 더존식 머리글 3줄 → 4행(인덱스3)이 헤더로 자동 탐지 ──
def test_h1_donzu_three_title_lines():
    rows = [
        ["㈜한국제조 분개장", "", "", "", ""],
        ["출력일시: 2026-06-22 10:00", "", "", "", ""],
        ["단위: 원", "", "", "", ""],
        ["전표일자", "거래처명", "계정과목", "적요", "차변금액"],
        ["2026-01-05", "신한은행", "보통예금", "이자입금", "12,000"],
    ]
    assert detect_header_row(rows) == 3


# ── 헤더가 첫 행(인덱스0)인 평범한 케이스 ──
def test_h1_header_at_row0():
    rows = [
        ["거래처", "계정과목", "적요", "금액"],
        ["신한은행", "보통예금", "이자", 100],
    ]
    assert detect_header_row(rows) == 0


# ── 비표준 헤더명(상대처/적요내용/발생액)도 키워드 부분일치로 탐지 ──
def test_h1_nonstandard_headers():
    rows = [
        ["회사: 테스트", "", "", ""],
        ["상대처", "계정", "적요내용", "발생액"],
        ["국민은행", "보통예금", "이자수취", 500],
    ]
    assert detect_header_row(rows) == 1


# ── 잡음 행에 키워드 1개만 있으면(=2개 미만) 헤더로 오인하지 않음 ──
def test_h1_single_keyword_row_not_header():
    rows = [
        ["합계", "", "금액합계", ""],          # amount 1개 카테고리뿐 → 헤더 아님
        ["거래처명", "계정과목", "적요", "금액"],  # 진짜 헤더
        ["하나은행", "정기예금", "예치", 999],
    ]
    assert detect_header_row(rows) == 1


# ── 헤더를 못 찾으면 0 반환(회계사 수동 조정 전제) ──
def test_h1_fallback_zero():
    rows = [
        ["설명만 있는 표", ""],
        ["값1", "값2"],
    ]
    assert detect_header_row(rows) == 0


# ── guess_col: 동의어 부분일치로 실제 컬럼명을 찾아냄 ──
def test_guess_col_synonym():
    cols = ["전표일자", "거래처명", "계정과목", "적요", "차변금액"]
    assert guess_col(cols, GUESS["vendor"]) == "거래처명"
    assert guess_col(cols, GUESS["amount"]) == "차변금액"
    assert guess_col(cols, GUESS["memo"]) == "적요"
    assert guess_col(["a", "b"], GUESS["vendor"]) == "(없음)"


if __name__ == "__main__":
    import traceback
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn(); print(f"  PASS  {name}"); passed += 1
        except Exception:
            print(f"  FAIL  {name}"); traceback.print_exc(); failed += 1
    print(f"\n{passed} passed, {failed} failed (총 {len(tests)}개)")
    raise SystemExit(1 if failed else 0)
