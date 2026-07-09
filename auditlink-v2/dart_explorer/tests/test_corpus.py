"""D-3a 게이트: 매핑 코퍼스 구축.

- 패키지 → usage 추출 (element/라벨/Role/차원문맥/확장 분리)
- DB 적재·재개·통계 (오프라인: 신원 패키지 + 가짜 클라이언트)
- 100사 파일럿은 CLI 배치로 수행 (본 테스트는 파일럿 DB가 있으면 검증)
"""
import os
import sqlite3

import pytest

from dart_explorer.xbrl import corpus

_SHINWON = os.path.join(
    r"C:\Users\moonyong\OneDrive - 서현회계법인\바탕 화면\XBRL",
    "신원종합개발", "[신원종합개발]반기보고서_IFRS(원문XBRL)(2025.08.14)")


@pytest.mark.skipif(not os.path.isdir(_SHINWON), reason="신원 패키지 없음")
def test_extract_package_fields():
    rows = corpus.extract_package(_SHINWON)
    assert len(rows) > 100
    by_id = {r["element_id"]: r for r in rows}
    ce = by_id["dart_EquityAtBeginningOfPeriod"]
    assert ce["label_ko"] == "기초자본"
    assert "D610005" in ce["roles"]
    assert "ComponentsOfEquityAxis" in ce["dims"]      # 차원 문맥
    assert ce["n_facts"] >= 8
    # 확장 element 플래그 + 별도 집계 대상
    exts = [r for r in rows if r["is_ext"]]
    assert len(exts) == 3
    assert all(r["element_id"].startswith("entity00136925") for r in exts)


@pytest.mark.skipif(not os.path.isdir(_SHINWON), reason="신원 패키지 없음")
def test_build_with_fake_client(tmp_path, monkeypatch):
    """빌드 흐름: 적재 → 재개(스킵) → 통계. 네트워크 없이 검증."""
    db = str(tmp_path / "corpus.sqlite")

    class FakeCli:
        def corp_codes(self):
            return [{"corp_code": "00136925", "corp_name": "신원종합개발",
                     "stock_code": "017000"},
                    {"corp_code": "99999999", "corp_name": "미제출사",
                     "stock_code": "999999"}]

        def company(self, code):
            return {"induty_code": "41"}

    monkeypatch.setattr(corpus, "find_periodic_rcept",
                        lambda cli, code, year: (
                            {"rcept_no": "1" * 14, "report_nm": "사업보고서"}
                            if code == "00136925" else None))
    monkeypatch.setattr(corpus, "download_xbrl",
                        lambda cli, code, rcept, rc: (b"", "(캐시경로)"))
    monkeypatch.setattr(corpus, "unpack_xbrl", lambda z: _SHINWON)

    counts = corpus.build(2025, db_path=db, cli=FakeCli(),
                          progress=lambda *_: None)
    assert counts == {"ok": 1, "no_annual": 1, "no_xbrl": 0, "error": 0}

    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM usages").fetchone()[0] > 100
    assert con.execute("SELECT COUNT(*) FROM extensions").fetchone()[0] == 3
    ind = con.execute("SELECT induty_code FROM companies WHERE corp_code "
                      "= '00136925'").fetchone()[0]
    assert ind == "41"                              # 업종코드 결합
    con.close()

    # 재개: 이미 처리된 회사는 건너뜀
    counts2 = corpus.build(2025, db_path=db, cli=FakeCli(),
                           progress=lambda *_: None)
    assert counts2 == {"ok": 0, "no_annual": 0, "no_xbrl": 0, "error": 0}

    s = corpus.stats(db)
    assert s["companies"]["ok"] == 1
    assert s["distinct_elements"] > 100


# ---------------------------------------------------------------------------
# 파일럿 DB 검증 (100사 빌드 후)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.path.exists(corpus.DEFAULT_DB),
                    reason="파일럿 코퍼스 없음")
def test_gate_pilot_corpus():
    s = corpus.stats()
    total = sum(s["companies"].values())
    assert total >= 100                             # 100사 파일럿
    assert s["companies"].get("ok", 0) >= 50        # 절반 이상 정상 적재
    assert s["distinct_elements"] > 500
    assert s["standard_labels"] > 5000
    # 실증 빈도 신호: BS 기본 계정은 대다수 회사가 사용
    top = {eid: n for eid, n, _ in s["top_elements"]}
    assert max(top.values()) >= s["companies"].get("ok", 0) * 0.8
