# -*- coding: utf-8 -*-
"""
PATCH 4 (H2) — 별칭 확장 + 데이터 시그니처 보조 추정 회귀 테스트.
- pytest:      pytest test_h2_signature.py
- standalone:  python test_h2_signature.py
"""
from mapping_utils import resolve_mapping, suggest_by_data, guess_col, GUESS


# ── H2 게이트: 헤더명을 비표준(상대처/적요내용/발생액)으로 바꿔도 4필드 추정 ──
def test_h2_nonstandard_header_names():
    cols = ["회계일자", "상대처", "계정", "적요내용", "발생액"]
    data = {c: [] for c in cols}  # 헤더명만으로 충분
    m = resolve_mapping(cols, data)
    assert m["vendor"] == "상대처"
    assert m["account"] == "계정"
    assert m["memo"] == "적요내용"
    assert m["amount"] == "발생액"


# ── H2 핵심: 헤더명이 의미 없을 때 데이터 성질로 위치 추정 ──
def test_h2_data_signature_when_headers_useless():
    cols = ["A", "B", "C", "D", "E", "F"]
    data = {
        "A": ["2025-01-05", "2025-03-11", "2025-04-01", "2025-07-10", "2025-10-21"],
        "B": ["신한은행", "㈜하나은행", "대구은행", "글로벌인베스트", "행복식당"],
        "C": ["보통예금", "단기차입금", "정기예금", "선급금", "복리후생비"],
        "D": ["이자입금", "차입금 상환", "정기예금 예치", "투자 선급금", "부서 회식"],
        "E": ["1,200,000", "", "5,000,000", "700,000,000", "300,000"],
        "F": ["", "30,000,000", "", "", ""],
    }
    m = resolve_mapping(cols, data)
    assert m["account"] == "C", m          # 계정명 사전 매칭률
    assert m["amount"] in ("E", "F"), m    # 숫자 변환 성공률
    assert m["memo"] == "D", m             # 서술형 비율
    assert m["vendor"] == "B", m           # 날짜·숫자 아닌 고유명사형


# ── 날짜 컬럼은 금액/거래처로 오인하지 않음 ──
def test_h2_date_column_excluded():
    cols = ["일자", "값"]
    data = {"일자": ["2025-01-01", "2025-02-02"], "값": ["100", "200"]}
    s = suggest_by_data(data)
    assert s["amount"] == "값"
    assert s["vendor"] != "일자"


# ── 헤더명이 명확하면 데이터보다 헤더명을 우선 ──
def test_h2_header_name_takes_precedence():
    cols = ["거래처명", "계정과목", "적요", "금액"]
    data = {"거래처명": ["신한은행"], "계정과목": ["보통예금"],
            "적요": ["이자"], "금액": ["1000"]}
    m = resolve_mapping(cols, data)
    assert m == {"vendor": "거래처명", "account": "계정과목",
                 "memo": "적요", "amount": "금액"}


# ── 확장된 동의어(공급처/계정과목명/적요내용/차변금액)도 잡힘 ──
def test_h2_expanded_synonyms():
    cols = ["전표일자", "공급처", "계정과목명", "적요내용", "차변금액", "대변금액"]
    assert guess_col(cols, GUESS["vendor"]) == "공급처"
    assert guess_col(cols, GUESS["account"]) == "계정과목명"
    assert guess_col(cols, GUESS["memo"]) == "적요내용"
    assert guess_col(cols, GUESS["amount"]) == "차변금액"


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
