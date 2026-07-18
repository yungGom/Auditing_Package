# -*- coding: utf-8 -*-
"""
PATCH 3 (H3) — 매핑 프로파일 저장·재사용 회귀 테스트.
- pytest:      pytest test_profile_store.py
- standalone:  python test_profile_store.py   (외부 설치 불필요)
- 실제 ~/.audit_toolbox 를 건드리지 않도록 항상 임시 경로를 사용한다.
"""
import os
import json
import tempfile

import profile_store as P


def _tmp():
    d = tempfile.mkdtemp(prefix="aud_prof_")
    return os.path.join(d, "mapping_profiles.json")


# ── 시그니처: 컬럼 순서·중복과 무관하게 동일 ──
def test_signature_order_and_dup_independent():
    a = P.compute_signature(["거래처명", "계정과목", "적요", "금액"])
    b = P.compute_signature(["금액", "적요", "거래처명", "계정과목"])
    c = P.compute_signature(["거래처명", "거래처명", "계정과목", "적요", "금액"])
    assert a == b == c
    d = P.compute_signature(["거래처명", "계정과목", "적요"])  # 컬럼 빠지면 달라져야
    assert d != a


# ── 저장 → 로드 왕복 ──
def test_save_load_roundtrip():
    path = _tmp()
    sig = P.compute_signature(["상대처", "계정", "적요내용", "발생액"])
    P.save_profile(sig, {"header_row": 3, "vendor": "상대처", "account": "계정",
                         "memo": "적요내용", "amount": "발생액"}, path=path)
    prof = P.get_profile(sig, path=path)
    assert prof["vendor"] == "상대처"
    assert prof["header_row"] == 3
    assert prof["amount"] == "발생액"


# ── 보안: 허용되지 않은(데이터성) 키는 저장되지 않음 ──
def test_security_drops_non_metadata_keys():
    path = _tmp()
    sig = "sig_sec"
    saved = P.save_profile(sig, {
        "vendor": "거래처명", "account": "계정과목", "memo": "적요", "amount": "차변",
        "header_row": 0,
        # 아래는 데이터/민감정보 — 절대 저장되면 안 됨
        "secret_amount": 999999999,
        "거래처값": "신한은행",
        "filename": "삼성전자_분개장_2025.xlsx",
    }, path=path)
    assert set(saved.keys()) <= P._ALLOWED_KEYS
    raw = json.load(open(path, encoding="utf-8"))
    blob = json.dumps(raw, ensure_ascii=False)
    assert "999999999" not in blob
    assert "신한은행" not in blob
    assert "삼성전자" not in blob


# ── 게이트: 같은 파일(동일 헤더) 두 번째 업로드 → 저장 매핑 자동 적용 ──
def test_gate_same_file_second_time_autoapplies():
    path = _tmp()
    headers = ["회계일자", "상대처", "계정", "적요내용", "발생액"]  # 프리셋엔 없는 양식
    # 1회차: 저장본 없음 → None
    m1, src1, sig1 = P.match_mapping(headers, path=path)
    assert m1 is None and src1 is None
    # 회계사가 매핑 확정 후 저장
    P.save_profile(sig1, {"header_row": 0, "vendor": "상대처", "account": "계정",
                          "memo": "적요내용", "amount": "발생액"}, path=path)
    # 2회차: 동일 헤더 → 사용자 저장본 자동 적용
    m2, src2, sig2 = P.match_mapping(headers, path=path)
    assert src2 == "user" and sig2 == sig1
    assert m2["vendor"] == "상대처" and m2["amount"] == "발생액"


# ── ERP 프리셋: 매핑 컬럼명이 모두 존재하면 부분집합 매칭 ──
def test_preset_subset_match():
    path = _tmp()  # 빈 저장소 → 프리셋만 작동
    headers = ["전표일자", "거래처명", "계정과목", "적요", "차변금액", "대변금액", "잔액"]
    m, src, _ = P.match_mapping(headers, path=path)
    assert src == "preset", src
    assert m["vendor"] == "거래처명"
    assert m["account"] == "계정과목"
    assert m["amount"] == "차변금액"


# ── 사용자 저장본이 프리셋보다 우선 ──
def test_user_profile_overrides_preset():
    path = _tmp()
    headers = ["전표일자", "거래처명", "계정과목", "적요", "차변금액"]  # 프리셋 매칭 대상
    sig = P.compute_signature(headers)
    P.save_profile(sig, {"vendor": "거래처명", "account": "계정과목",
                         "memo": "적요", "amount": "대변금액"}, path=path)  # 일부러 다르게
    m, src, _ = P.match_mapping(headers, path=path)
    assert src == "user"
    assert m["amount"] == "대변금액"  # 프리셋(차변금액)이 아니라 저장본


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
