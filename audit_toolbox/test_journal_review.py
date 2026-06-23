# -*- coding: utf-8 -*-
"""
PATCH 8 — 분개장 검토 스텝(계정 슬라이서 + 드릴다운 + 일괄동작) 회귀 테스트.
- pytest:      pytest test_journal_review.py
- standalone:  python test_journal_review.py
"""
import fi_detector as D


def jrec(row_no, account, cand_vals, cand_cols=None, memo="", amount=0.0):
    return {
        "row_no": row_no, "source": "더존분개장.xlsx", "kind": "분개장",
        "date": "2026-01-02", "slip_no": f"S{row_no}",
        "account": account, "memo": memo, "amount": amount,
        "vendor": next((x for x in cand_vals if x), ""),
        "vendor_candidates": list(cand_vals),
        "vendor_cand_cols": cand_cols or [f"관리항목{i+1}" for i in range(len(cand_vals))],
        "raw": {"계정과목": account}, "raw_cols": ["계정과목"],
    }


# ── 게이트1: 관리항목에 숨은 은행이 거래처로 잡혀 드릴다운에 뜬다 ──
def test_gate1_hidden_bank_in_mgmt_item():
    recs = [jrec(1, "보통예금", ["", "신한은행"], ["관리항목1", "관리항목2"], memo="이자")]
    rev = D.review_journal(recs)
    assert len(rev) == 1
    row = rev[0]
    assert row["vendor_display"] == "신한은행"
    assert row["vendor_col"] == "관리항목2"
    assert row["auto_include"] is True
    assert row["tag"] == "자동추천"


# ── 게이트2: 거래처 공란 + 적요에 은행명 → 노란색(적요확인필요), 체크 시 후보 반영 ──
def test_gate2_memo_bank_blank_vendor():
    recs = [jrec(1, "잡비", ["", ""], ["관리항목1", "관리항목2"], memo="신한은행 계좌이체")]
    rev = D.review_journal(recs)
    row = rev[0]
    assert row["tag"] == "적요확인필요"
    assert row["highlight"] is True
    assert row["auto_include"] is False
    assert row["vendor_display"] == "신한은행"

    # 기본(미체크) → 후보 없음
    assert D.hits_from_included(rev) == []

    # 회계사가 체크 → 후보 반영
    hits = D.hits_from_included(rev, include_map={1: True})
    assert len(hits) == 1
    cands = D.aggregate(hits)
    c = next(c for c in cands if c["기관(정규화)"] == "신한은행")
    assert c["조회방법"] == "온라인 조회"


# ── 게이트3: 계정 전체 포함/제외 일괄동작 ──
def test_gate3_account_bulk_include_exclude():
    recs = [
        jrec(1, "비품", ["신한은행"], ["관리항목1"]),       # 자동추천(ON)
        jrec(2, "비품", ["행복상사"], ["관리항목1"]),       # 비금융(OFF)
    ]
    rev = D.review_journal(recs, selected_accounts={"비품"})
    # 기본: 자동추천 1건만
    assert len(D.hits_from_included(rev)) == 1
    # 전체 포함: 비금융까지 수기포함
    inc_all = {1: True, 2: True}
    hits = D.hits_from_included(rev, include_map=inc_all)
    assert len(hits) == 2
    cands = D.aggregate(hits)
    names = {c["기관(정규화)"] for c in cands}
    assert "신한은행" in names and "행복상사" in names
    # 전체 제외
    assert D.hits_from_included(rev, include_map={1: False, 2: False}) == []


# ── account_summary: 금융계정 기본 체크 + 정렬(금융 먼저) ──
def test_account_summary_fi_default():
    recs = [
        jrec(1, "매출원가", ["행복상사"]), jrec(2, "매출원가", ["가나상사"]),
        jrec(3, "매출원가", ["다라상사"]),
        jrec(4, "보통예금", ["신한은행"]),
        jrec(5, "단기차입금", ["국민은행"]),
    ]
    s = D.account_summary(recs)
    by = {x["account"]: x for x in s}
    assert by["보통예금"]["is_fi"] is True
    assert by["단기차입금"]["is_fi"] is True
    assert by["매출원가"]["is_fi"] is False
    assert by["매출원가"]["count"] == 3
    # 금융계정이 앞쪽으로 정렬
    assert s[0]["is_fi"] and s[1]["is_fi"]


# ── _hits 에 계정·행 기록(5단계 병합·근거 표시용) ──
def test_hits_record_account_and_row():
    recs = [jrec(7, "단기차입금", ["국민은행"], ["관리항목1"])]
    rev = D.review_journal(recs)
    hits = D.hits_from_included(rev)              # 자동추천 ON
    cands = D.aggregate(hits)
    c = next(c for c in cands if c["기관(정규화)"] == "국민은행")
    h = c["_hits"][0]
    assert h["review_account"] == "단기차입금"
    assert h["row_no"] == 7
    assert h["included_via"] == "자동추천"


# ── 선택 계정 필터: 선택 안 한 계정 행은 검토 목록에서 빠진다 ──
def test_selected_accounts_filter():
    recs = [jrec(1, "보통예금", ["신한은행"]), jrec(2, "매출원가", ["행복상사"])]
    rev = D.review_journal(recs, selected_accounts={"보통예금"})
    assert len(rev) == 1 and rev[0]["account"] == "보통예금"


# ── PATCH 9: 시트명 → 추정계정/금융여부 ──
def test_guess_sheet_classification():
    assert D.guess_sheet("예금명세서") == {"account": "보통예금", "is_fi": True}
    assert D.guess_sheet("차입금명세서") == {"account": "단기차입금", "is_fi": True}
    g = D.guess_sheet("유가증권명세서")
    assert g["is_fi"] is True and g["account"] == ""
    assert D.guess_sheet("매출처원장")["is_fi"] is False
    assert D.guess_sheet("재고자산명세")["is_fi"] is False


# ── PATCH 9 게이트: 거래처 없는 유가증권 시트 — 적요 기반 검토 ──
def test_statement_securities_memo_based():
    rec = jrec(1, "", ["", ""], ["관리항목1", "관리항목2"], memo="삼성증권 매수")
    rec.update({"source": "명세서.xlsx ▸ 유가증권명세서", "kind": "명세서",
                "sheet": "유가증권명세서"})
    rev = D.review_journal([rec])
    row = rev[0]
    assert row["tag"] == "적요확인필요"
    assert row["vendor_display"] == "삼성증권"
    cands = D.aggregate(D.hits_from_included(rev, include_map={1: True}))
    c = next(c for c in cands if c["기관(정규화)"] == "삼성증권")
    assert c["조회서양식"] == "증권사"


# ── PATCH 9 게이트: 시트 출처(파일 ▸ 시트)가 _hits 에 보존 ──
def test_hits_preserve_sheet_source():
    rec = jrec(1, "보통예금", ["신한은행"], ["거래처"])
    rec.update({"source": "통합명세서.xlsx ▸ 예금명세서", "kind": "명세서",
                "sheet": "예금명세서"})
    rev = D.review_journal([rec])
    hits = D.hits_from_included(rev)  # 자동추천 ON
    assert hits[0]["source"] == "통합명세서.xlsx ▸ 예금명세서"
    cands = D.aggregate(hits)
    c = next(c for c in cands if c["기관(정규화)"] == "신한은행")
    assert c["_hits"][0]["source"] == "통합명세서.xlsx ▸ 예금명세서"


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
