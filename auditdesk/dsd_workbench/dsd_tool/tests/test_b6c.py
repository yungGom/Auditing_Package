"""B-6c 게이트: 주석 분할 단일 소스화 — 합성 회귀 고정.

바이오인프라 FY25 감사보고서 공시본 실측 재현:
① 헤더 일부가 문단 중간 &cr; 경계로만 존재(결번) → 연속 체인 붕괴
   → '주석' TITLE 확정 범위 안에서 &cr; 후보 + 건너뜀 체인 폴백
② 주석 범위 = '주석' TITLE ~ 다음 TITLE — 후반 '외부감사 실시내용'의
   번호 TITLE(1.~4.)과 격리
③ 컨테이너 무결 — 내장 바이너리 엔트리 포함 수정 0건 repack 왕복
   바이트 보존
(실파일 게이트는 로컬 실측: 주석 35개 개별 시트·CF 918→37행·크로스
모수 110 / 반기 24 불변 / 공시본 jpg 내장 repack 바이트 동일)
"""
import pytest

from dsd_tool.excel_out import extract
from dsd_tool.foot import FootingContext
from dsd_tool.tests.fixture import CONTENTS_XML, build_dsd

# 주석 SECTION-2 교체: USERMARK 없는 평문 + 주석 2가 문단 중간
# &cr; 경계로만 존재 (공시본 실측 형태) — 1차 연속 체인은 결번 2에서
# 붕괴하고, B-6c 폴백이 살려야 한다
_CR_NOTES = (
    "<SECTION-2><TITLE>주석</TITLE>\r\n"
    "<P>1. 당사의 개요&amp;cr;회사는 2000년에 설립되었으며 서울에"
    " 본사를 두고 있습니다.&amp;cr;&amp;cr;2. 재무제표 작성기준"
    "&amp;cr;&amp;cr;회사는 K-IFRS를 적용하고 있습니다.</P>\r\n"
    "<P>3. 현금및현금성자산  (1) 내역은 다음과 같습니다.</P>\r\n"
    "<P>4. 재고자산  평가 내역입니다.</P>\r\n"
    "</SECTION-2>\r"
)


@pytest.fixture(scope="module")
def cr_extract(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("b6c")
    src = CONTENTS_XML
    lo = src.find("<SECTION-2><TITLE>주석</TITLE>")
    hi = src.find("</SECTION-2>") + len("</SECTION-2>\r")
    contents = src[:lo] + _CR_NOTES + src[hi:]
    dsd = build_dsd(str(tmp / "cr.dsd"), contents=contents)
    xlsx = str(tmp / "cr.xlsx")
    meta = extract(dsd, xlsx)
    return meta, FootingContext(xlsx), dsd, xlsx


def test_cr_fallback_splits_all(cr_extract):
    """문단 중간 &cr; 경계(결번 2) — 폴백으로 전 주석 분할."""
    meta, ctx, _dsd, _xlsx = cr_extract
    assert meta["note_mode"] == "plain-cr"
    assert ctx.note_sheets == ["1", "2", "3", "4"]
    assert "재무제표 작성기준" in str(ctx.wb["2"].cell(1, 1).value or "")


def test_audit_section_titles_isolated(cr_extract):
    """'외부감사 실시내용'의 번호 TITLE은 주석 범위 밖 — 오탐 0."""
    meta, ctx, _dsd, _xlsx = cr_extract
    # 픽스처의 외부감사 TITLE '1. 감사참여자…'가 주석으로 새지 않음
    body = "\n".join(
        str(c.value) for s in ctx.note_sheets
        for row in ctx.wb[s].iter_rows() for c in row if c.value)
    assert "감사참여자" not in body
    assert "외부감사" in ctx.wb.sheetnames      # TE 시트는 그대로


def test_container_roundtrip_bytes(cr_extract, tmp_path):
    """내장 바이너리 엔트리 포함 — 수정 0건 repack 왕복 바이트 보존."""
    import zipfile

    from dsd_tool.repack import repack
    _meta, _ctx, dsd, xlsx = cr_extract
    out = str(tmp_path / "roundtrip.dsd")
    # clean_cr=False: 픽스처의 &cr;-only 셀 정리를 끄고 순수 무변경
    # 왕복만 검증 (컨테이너 보존이 검증 대상)
    r = repack(xlsx, dsd, out_path=out, record_history=False,
               clean_cr=False)
    assert r["changes"] == []
    assert open(dsd, "rb").read() == open(out, "rb").read()
    with zipfile.ZipFile(out) as z:
        assert "images/logo.bin" in z.namelist()
