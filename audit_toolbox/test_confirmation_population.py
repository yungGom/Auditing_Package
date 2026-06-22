# -*- coding: utf-8 -*-
"""
조회 모집단 완전성 검토 — 회귀 테스트 (HANDOFF 5장 9개 케이스 고정)

- pytest로 실행 가능:   pytest test_confirmation_population.py
- pytest 없이도 실행 가능: python test_confirmation_population.py
  (외부 패키지 추가 설치 없이 pandas/openpyxl만으로 동작 — 완전 오프라인)
"""
import fi_detector as D
from report_builder import build_workbook


def make_rec(row_no, vendor="", account="", memo="", amount=0.0,
             source="분개장.xlsx", kind="분개장"):
    """scan/aggregate/report가 기대하는 형태의 행 1건 생성."""
    return {
        "row_no": row_no, "source": source, "kind": kind,
        "date": "2026-06-22", "slip_no": f"S{row_no:04d}",
        "account": account, "vendor": vendor, "memo": memo, "amount": amount,
        "raw": {"거래처": vendor, "계정과목": account, "적요": memo, "금액": amount},
        "raw_cols": ["거래처", "계정과목", "적요", "금액"],
    }


# ── 케이스 1: 지점·법인격 롤업 → 1개 기관 ─────────────────────────
def test_case1_branch_legalform_rollup():
    recs = [
        make_rec(1, "신한은행", "보통예금"),
        make_rec(2, "신한은행 강남지점", "보통예금"),
        make_rec(3, "㈜신한은행", "이자비용"),
    ]
    hits = D.scan(recs)
    cands = D.aggregate(hits)
    keys = {c["기관(정규화)"] for c in cands}
    assert keys == {"신한은행"}, keys
    assert len(cands) == 1
    assert cands[0]["발견건수"] == 3


# ── 케이스 2: 계정추적 후보 (거래처 공란 + '사채') → 미분류(검토필요) ──
def test_case2_account_trace_candidate():
    recs = [make_rec(1, "", "사채", amount=500000000)]
    hits = D.scan(recs)
    assert len(hits) == 1
    assert hits[0]["basis"] == "계정추적"
    cands = D.aggregate(hits)
    assert len(cands) == 1
    assert cands[0]["조회서양식"] == "미분류(검토필요)"


# ── 케이스 3: 노이즈 제외 (사전·계정·적요 어디에도 안 걸림) ──────────
def test_case3_noise_excluded():
    recs = [
        make_rec(1, "한국철강공업(매출원가)", "매출원가"),
        make_rec(2, "행복식당(복리후생비)", "복리후생비"),
    ]
    hits = D.scan(recs)
    assert hits == [], hits


# ── 케이스 4: 미매칭 안전망 (고액인데 미탐지) → unmatched 노출 ──────
def test_case4_unmatched_safety_net():
    recs = [make_rec(1, "글로벌인베스트", "선급금", memo="선급금 지급", amount=700000000)]
    hits = D.scan(recs)
    hit_rows = {h["row_no"] for h in hits}
    unmatched = [r for r in recs if r["row_no"] not in hit_rows]
    assert len(unmatched) == 1
    assert unmatched[0]["row_no"] == 1


# ── 케이스 5: 온라인 유형 충돌 방지 (생명 vs 화재 분리) ─────────────
def test_case5_online_type_no_collision():
    a = D.lookup_online("삼성생명", "보험회사")
    b = D.lookup_online("삼성화재", "보험회사")
    assert a["online"] and a["정식명"] == "삼성생명보험", a
    assert b["online"] and b["정식명"] == "삼성화재해상보험", b


# ── 케이스 6: 명칭 변형 매칭 ──────────────────────────────────────
def test_case6_name_variant_matching():
    cases = [
        ("KB국민은행", "은행", "국민은행"),
        ("중소기업은행", "은행", "기업은행"),
        ("iM뱅크", "은행", "아이엠뱅크"),
        ("하나은행", "은행", "KEB하나은행"),
    ]
    for raw, form, expect in cases:
        o = D.lookup_online(raw, form)
        assert o["online"], f"{raw} 매칭 실패"
        assert expect in o["정식명"], f"{raw} → {o['정식명']} (기대: {expect})"


# ── 케이스 7: 전기 병합 + 변형 흡수 ──────────────────────────────
def test_case7a_prior_merge_into_current():
    """전기 'KEB하나은행' 이 당기 '하나은행' 과 병합."""
    recs = [make_rec(1, "하나은행", "보통예금")]
    cands = D.aggregate(D.scan(recs))
    cands, added = D.merge_prior(cands, ["KEB하나은행"])
    assert added == 0, "당기에 이미 있으므로 신규 추가 0이어야 함"
    target = next(c for c in cands if "하나" in (c.get("온라인정식명") or c["기관(정규화)"]))
    assert "당기 탐지" in target["포함근거"]
    assert "전기" in target["포함근거"], target["포함근거"]


def test_case7b_prior_only_added():
    """당기 미탐지 전기 조회처(NH농협은행, 한국씨티은행)가 전기보유분으로 추가."""
    recs = [make_rec(1, "신한은행", "보통예금")]
    cands = D.aggregate(D.scan(recs))
    before = len(cands)
    cands, added = D.merge_prior(cands, ["NH농협은행", "한국씨티은행"])
    assert added == 2, added
    assert len(cands) == before + 2
    names = {c.get("온라인정식명") or c["기관(정규화)"] for c in cands}
    assert "농협은행" in names, names
    assert "씨티은행" in names, names
    for nm in ("농협은행", "씨티은행"):
        c = next(x for x in cands if (x.get("온라인정식명") or x["기관(정규화)"]) == nm)
        assert c["포함근거"] == "전기 조회처(당기 미탐지)", c["포함근거"]
        assert c["발견건수"] == 0


# ── 케이스 8: 온라인 조회 행 전화번호 칸 비움 (산출물) ──────────────
def test_case8_online_phone_blank_in_report():
    recs = [make_rec(1, "신한은행", "보통예금")]
    cands = D.aggregate(D.scan(recs))
    # 신한은행은 온라인 참가기관 → 산출물 전화번호 칸이 비어야 함
    assert cands[0]["조회방법"] == "온라인 조회"
    wb = build_workbook(cands, D.scan(recs), [])
    ws = wb["조회 대상 명세"]
    # 데이터 첫 행 = 4행, 전화번호 = 6열
    tel = ws.cell(row=4, column=6).value
    assert tel in (None, ""), f"온라인 행 전화번호가 비어있지 않음: {tel!r}"


# ── 케이스 9: 원본 컬럼 구조 보존 (_hits 의 raw/raw_cols) ───────────
def test_case9_raw_preserved():
    recs = [make_rec(1, "", "사채", amount=100)]  # 서면/미분류로 검토 대상
    cands = D.aggregate(D.scan(recs))
    c = cands[0]
    assert c["_hits"], "_hits 비어있음"
    h = c["_hits"][0]
    assert "raw" in h and "raw_cols" in h
    assert h["raw_cols"] == ["거래처", "계정과목", "적요", "금액"]
    assert h["raw"]["계정과목"] == "사채"


if __name__ == "__main__":
    import traceback
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception:
            print(f"  FAIL  {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed (총 {len(tests)}개)")
    raise SystemExit(1 if failed else 0)
