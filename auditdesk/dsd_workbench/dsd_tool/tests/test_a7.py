"""A-7 게이트: 단위 인지 크로스 검증 — 합성 회귀 고정.

원·천원·백만원·미표기 혼재 픽스처:
G1 표별 단위 리졸버 — 같은 시트 안 표별 상이 배율·미표기 None(보류)
G2 환산 일치 — 백만원 본문 ↔ 원/천원 주석, 허용오차 = 배율 미만,
   "일치(단위환산)" 분리 집계·검증내역 환산 수식·총괄표 별도 열
G3 미표기 보류 — 자릿수 추정 금지, ② 사유(마커 미상 후보)로 정직 노출
G4 변조 — 환산 후에도 배율 초과 차이 → 불일치(미발견 ③) 검출
(실파일: 바이오 기말 — 사유② 68건 중 65건 환산 일치 전환·잔여 8건
③ 재분류, 발견 37→102 / 반기 24→58 — 로컬 실측)
"""
import pytest
from openpyxl import load_workbook

from dsd_tool.excel_out import extract
from dsd_tool.foot import FootingContext, foot
from dsd_tool.foot_excel import DETAIL_SHEET, write_ai_footing
from dsd_tool.tests.fixture import CONTENTS_XML, build_dsd
from dsd_tool.units import region_scales

_lo = CONTENTS_XML.find("<SECTION-2><TITLE>주석</TITLE>")
_hi = CONTENTS_XML.find("</SECTION-2>") + len("</SECTION-2>\r")


def _notes(cash_thousand="500,000,000"):
    return (
        "<SECTION-2><TITLE>주석</TITLE>\r\n"
        '<P><SPAN USERMARK=" B">1. 일반 사항</SPAN>&amp;cr;내용.</P>\r\n'
        '<P><SPAN USERMARK=" B">2. 원단위 내역</SPAN>&amp;cr;내용.</P>\r\n'
        '<TU ALIGN="RIGHT">(단위 : 원)</TU>\r\n'
        '<TABLE WIDTH="600"><TR><TH>구분</TH><TH>금액</TH></TR>\r\n'
        '<TR><TD>총계내역</TD><TD ALIGN="RIGHT">1,234,567,000,000</TD>'
        "</TR>\r\n"
        '<TR><TD>보조</TD><TD ALIGN="RIGHT">5</TD></TR>\r\n'
        '<TR><TD>보조2</TD><TD ALIGN="RIGHT">7</TD></TR></TABLE>\r\n'
        '<TU ALIGN="RIGHT">(단위 : 천원)</TU>\r\n'
        '<TABLE WIDTH="600"><TR><TH>구분</TH><TH>금액</TH></TR>\r\n'
        '<TR><TD>표별상이</TD><TD ALIGN="RIGHT">11</TD></TR>\r\n'
        '<TR><TD>표별상이2</TD><TD ALIGN="RIGHT">13</TD></TR>\r\n'
        '<TR><TD>표별상이3</TD><TD ALIGN="RIGHT">17</TD></TR></TABLE>\r\n'
        '<P><SPAN USERMARK=" B">3. 천원 내역</SPAN>&amp;cr;내용.</P>\r\n'
        '<TU ALIGN="RIGHT">(단위 : 천원)</TU>\r\n'
        '<TABLE WIDTH="600"><TR><TH>구분</TH><TH>금액</TH></TR>\r\n'
        f'<TR><TD>현금내역</TD><TD ALIGN="RIGHT">{cash_thousand}</TD>'
        "</TR>\r\n"
        '<TR><TD>보조</TD><TD ALIGN="RIGHT">3</TD></TR>\r\n'
        '<TR><TD>보조2</TD><TD ALIGN="RIGHT">9</TD></TR></TABLE>\r\n'
        '<P><SPAN USERMARK=" B">4. 단위 미표기 내역</SPAN></P>\r\n'
        '<TABLE WIDTH="600"><TR><TH>구분</TH><TH>금액</TH></TR>\r\n'
        '<TR><TD>미표기값</TD><TD ALIGN="RIGHT">-234,567,000</TD>'
        "</TR>\r\n"
        '<TR><TD>보조</TD><TD ALIGN="RIGHT">21</TD></TR>\r\n'
        '<TR><TD>보조2</TD><TD ALIGN="RIGHT">23</TD></TR></TABLE>\r\n'
        "</SECTION-2>\r")


def _contents(cash="500,000,000"):
    s = CONTENTS_XML[:_lo] + _notes(cash) + CONTENTS_XML[_hi:]
    # BS 주석 참조 재배선: 자산총계→2(원), 현금→3(천원), 부채→4(미표기)
    s = s.replace("<TD>3,4</TD>", "<TD>2</TD>")
    s = s.replace("<TD>4, 28</TD>", "<TD>3</TD>")
    s = s.replace("<TR><TD>부채총계</TD><TD></TD>",
                  "<TR><TD>부채총계</TD><TD>4</TD>")
    return s


def _build(tmp_path, name, cash="500,000,000"):
    dsd = build_dsd(str(tmp_path / f"{name}.dsd"),
                    contents=_contents(cash))
    xlsx = str(tmp_path / f"{name}.xlsx")
    extract(dsd, xlsx)
    res = foot(xlsx, save=False)
    out = write_ai_footing(xlsx, res,
                           out_path=str(tmp_path / f"AI_{name}.xlsx"))
    return xlsx, res, out


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    return _build(tmp_path_factory.mktemp("a7"), "base")


def test_g1_per_table_scales(base):
    """표별 상이 배율 + 미표기 None(보류) — 리졸버 단위 검증."""
    xlsx, _res, _out = base
    ctx = FootingContext(xlsx)
    s2 = region_scales(ctx, "2")
    assert 1 in s2.values() and 1_000 in s2.values()    # 같은 시트 표별 상이
    s4 = region_scales(ctx, "4")
    assert set(s4.values()) == {None}                   # 미표기 → 보류


def test_g2_converted_matches(base):
    """백만원 본문 ↔ 원/천원 주석 — 일치(단위환산) 분리 집계·수식."""
    _xlsx, res, out = base
    conv = [r for r in res["notes"] if r.get("conv")]
    by_label = {r["label"]: r for r in conv}
    assert "자산총계" in by_label            # 백만원 ↔ 원 (배율 1e6:1)
    assert "현금및현금성자산" in by_label    # 백만원 ↔ 천원 (1e6:1e3)
    assert res["note_found_conv"] == len(conv) >= 2
    assert out["checks"]["cross_conv"] >= 2
    wb = load_workbook(out["out_path"])
    ws = wb[DETAIL_SHEET]
    rows = [r for r in range(6, ws.max_row + 1)
            if ws.cell(r, 1).value == "크로스(단위환산)"]
    assert rows
    r0 = rows[0]
    assert "*" in str(ws.cell(r0, 5).value)             # 좌 환산 수식
    assert "*" in str(ws.cell(r0, 8).value)             # 우 환산 수식
    assert "배율" in str(ws.cell(r0, 4).value)
    # 총괄표 별도 열 (원형 5열 뒤 N열)
    w0 = wb["총괄표"]
    assert w0.cell(4, 14).value == "크로스 일치(단위환산)"
    total = sum(w0.cell(r, 14).value or 0
                for r in range(5, w0.max_row + 1))
    assert int(total) == len(conv)


def test_g3_unknown_unit_held(base):
    """단위 미표기 표 — 자릿수 추정 금지, ②(마커 미상 후보) 노출."""
    _xlsx, res, out = base
    row = next(r for r in res["notes"] if r["label"] == "부채총계")
    assert not r_found(row)
    assert not row.get("conv_tried")         # 미상 → 환산 시도 자체 보류
    assert out["checks"]["missing_reasons"]["②단위·집계 상이"] >= 1


def r_found(row):
    return row["found"]


def test_g4_tamper_beyond_tolerance(base, tmp_path):
    """변조: 환산 후 차이 2,000천원(=2,000,000원) > 허용 ±999,999
    → 불일치(미발견 ③) 전환."""
    _x0, res0, _o0 = base
    assert next(r for r in res0["notes"]
                if r["label"] == "현금및현금성자산")["found"]
    _xlsx, res, out = _build(tmp_path, "tam", cash="500,002,000")
    row = next(r for r in res["notes"]
               if r["label"] == "현금및현금성자산" and r["period"] == "당기")
    assert not row["found"] and row["conv_tried"]
    assert out["checks"]["missing_reasons"]["③매칭 불가"] >= 1
