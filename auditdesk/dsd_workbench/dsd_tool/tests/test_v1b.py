"""V-1b 게이트: V-1 대상 기간 선택 — 전기 컨텍스트 대사 (합성 회귀).

당기 인스턴스의 전기 비교표시(전기말 instant·전반기 duration) ↔ 전기
공시 DSD의 당기 열 대사. 선별 파라미터만 다르고 판정 로직은 V-1 재사용.
G1 전기 컨텍스트 일치 (BS↔전기말, PL/CF↔전반기 — kind별 종료일 분리)
G2 당기(current) 선별과의 분리 — 미끼 당기 팩트가 prior에 유입되지 않음
G3 변조 1건 → 해당 행만 FALSE 전환
(실파일 게이트는 바이오인프라 FY25 공시 DSD ↔ FY26 모의 인스턴스 —
로컬 실측)
"""
import pytest

from dsd_tool.excel_out import extract
from dsd_tool.mapping import normalize as _norm
from dsd_tool.tests.fixture import CONTENTS_XML, build_dsd
from dsd_tool.xbrl_recon import V_DIFF, V_MATCH, V_NOFACT, xbrl_recon

_DOC_END = "2026-06-30"          # 당기(FY26 반기) 보고기간말
_PRIOR_BS = "2025-12-31"         # 전기말 (instant)
_PRIOR_HALF = "2025-06-30"       # 전반기 (duration)

# 전기 공시 DSD(합성)의 당기 열 값 — 단위 백만원
_BS_VALUES = {"자산총계": 1_234_567, "현금및현금성자산": 500_000,
              "부채총계": -234_567}
_DUR_VALUES = {"매출액": 999_999, "당기순이익": 77_777,
               "영업활동현금흐름": 123_456}
_SCALE = 1_000_000
_BIG = 5_000_000_000             # 허용오차(±0.5백만원)보다 큰 교란값


def _mock():
    decided, facts = {}, {}
    for i, (label, v) in enumerate(_BS_VALUES.items()):
        eid = f"mock_BS{i}"
        decided[_norm(label)] = eid
        facts[eid] = [
            {"value": v * _SCALE, "decimals": None, "type": "instant",
             "start": None, "end": _PRIOR_BS, "dims": {}},
            # 미끼: 당기 컨텍스트 (값이 크게 다름 — 유입 시 검출)
            {"value": v * _SCALE + _BIG, "decimals": None,
             "type": "instant", "start": None, "end": _DOC_END,
             "dims": {}},
        ]
    for i, (label, v) in enumerate(_DUR_VALUES.items()):
        eid = f"mock_D{i}"
        decided[_norm(label)] = eid
        facts[eid] = [
            {"value": v * _SCALE, "decimals": None, "type": "duration",
             "start": "2025-01-01", "end": _PRIOR_HALF, "dims": {}},
            {"value": v * _SCALE + _BIG, "decimals": None,
             "type": "duration", "start": "2026-01-01", "end": _DOC_END,
             "dims": {}},
        ]
    return decided, facts


# 합성 픽스처의 PL·CF는 단일 열 헤더라 기간 열 인식이 안 된다(실제
# 공시 DSD는 2단 헤더) — 실측 구조(주석·금액1/금액2 2단 + 단위 행)로
# 교체해 duration 경로까지 검증
_HDR2 = ('<TR><TH ROWSPAN="2">과목</TH><TH ROWSPAN="2">주석</TH>'
         '<TH COLSPAN="2">당기</TH><TH COLSPAN="2">전기</TH></TR>\r\n'
         "<TR><TH>금액1</TH><TH>금액2</TH><TH>금액1</TH><TH>금액2</TH>"
         "</TR>\r\n")
_UNIT_TBL = ('<TABLE WIDTH="600"><TR><TD>제 57 기</TD>'
             '<TD ALIGN="RIGHT">(단위 : 백만원)</TD></TR></TABLE>\r\n')
_PL_TBL = (
    _UNIT_TBL + '<TABLE WIDTH="600">\r\n' + _HDR2 +
    "<TR><TD>매출액</TD><TD></TD><TD></TD>"
    '<TD ALIGN="RIGHT">999,999</TD><TD></TD>'
    '<TD ALIGN="RIGHT">888,888</TD></TR>\r\n'
    "<TR><TD>당기순이익</TD><TD></TD><TD></TD>"
    '<TD ALIGN="RIGHT">77,777</TD><TD></TD>'
    '<TD ALIGN="RIGHT">66,666</TD></TR>\r\n'
    "</TABLE>\r")
_CF_TBL = (
    _UNIT_TBL + '<TABLE WIDTH="600">\r\n' + _HDR2 +
    "<TR><TD>영업활동현금흐름</TD><TD></TD><TD></TD>"
    '<TD ALIGN="RIGHT">123,456</TD><TD></TD>'
    '<TD ALIGN="RIGHT">120,000</TD></TR>\r\n'
    "</TABLE>\r")


def _contents():
    src = CONTENTS_XML
    for title, tbl in (("포괄손익계산서", _PL_TBL),
                       ("현 금 흐 름 표", _CF_TBL)):
        anchor = f'<TABLE WIDTH="600"><TR><TD ALIGN="CENTER">{title}</TD></TR></TABLE>\r'
        lo = src.find(anchor)
        assert lo >= 0, title
        body_lo = lo + len(anchor)
        body_hi = src.find("</TABLE>\r", body_lo) + len("</TABLE>\r")
        src = src[:body_hi].replace(
            src[body_lo:body_hi], "\n" + tbl, 1) + src[body_hi:]
    return src


@pytest.fixture(scope="module")
def prior_xlsx(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("v1b")
    dsd = build_dsd(str(tmp / "prior.dsd"), contents=_contents())
    xlsx = str(tmp / "prior.xlsx")
    extract(dsd, xlsx)
    return xlsx


def test_prior_target_matches(prior_xlsx):
    """G1: 전기 컨텍스트 대상 — kind별 종료일 자동 도출·전 행 일치."""
    decided, facts = _mock()
    res = xbrl_recon(prior_xlsx, facts, _DOC_END, decided=decided,
                     target="prior")
    assert res["target_ends"] == {"instant": _PRIOR_BS,
                                  "duration": _PRIOR_HALF}
    assert res["counts"][V_MATCH] == 6          # BS 3 + PL 2 + CF 1
    assert res["counts"][V_DIFF] == 0
    assert res["counts"][V_NOFACT] == 0


def test_current_target_separation(prior_xlsx):
    """G2: 같은 팩트로 current 선별 시 미끼 당기 값이 잡혀 전부 상이 —
    prior 선별이 당기 컨텍스트와 분리되어 있음을 증명."""
    decided, facts = _mock()
    res = xbrl_recon(prior_xlsx, facts, _DOC_END, decided=decided,
                     target="current")
    assert res["counts"][V_MATCH] == 0
    assert res["counts"][V_DIFF] == 6


def test_tamper_one_fact(prior_xlsx):
    """G3: 전기 컨텍스트 팩트 1건 변조 → 해당 행만 FALSE 전환."""
    decided, facts = _mock()
    facts["mock_BS0"][0]["value"] += _BIG
    res = xbrl_recon(prior_xlsx, facts, _DOC_END, decided=decided,
                     target="prior")
    assert res["counts"][V_DIFF] == 1
    bad = [r for rows in res["rows"].values() for r in rows
           if r["verdict"] == V_DIFF]
    assert len(bad) == 1 and bad[0]["element"] == "mock_BS0"


def test_no_prior_context_raises(prior_xlsx):
    """전기 비교표시가 전혀 없으면 정직하게 판정 불가 (침묵 0건 금지)."""
    decided, facts = _mock()
    for fl in facts.values():
        fl[:] = [f for f in fl if f["end"] == _DOC_END]
    with pytest.raises(ValueError):
        xbrl_recon(prior_xlsx, facts, _DOC_END, decided=decided,
                   target="prior")
