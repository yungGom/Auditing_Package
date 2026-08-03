"""B-6-mini 게이트: 주석 텍스트 2차 분할 — 합성 회귀 고정.

바이오인프라 실측 3패턴을 합성 픽스처로 재현:
① 융합형('N. 제목  (1) 본문…' 한 P) 경계 인정
② &cr; 프리픽스 제목 인정
③ 표 셀 안 'N.' 나열(CF 명세류)은 헤더 후보에서 배제 — 유령 시트 0
순차 번호 검증: 건너뜀 허용·역행 불허.
(실파일 게이트는 바이오인프라 FY25 — 고객사 폴더 원칙상 레포 미반입,
로컬 실측으로 수행: 주석 24개 전부 개별 시트·유령 0)
"""
import pytest

from dsd_tool.excel_out import extract
from dsd_tool.foot import FootingContext
from dsd_tool.tests.fixture import CONTENTS_XML, build_dsd

# 주석 SECTION-2를 '뭉텅이 작성' 형태로 교체: USERMARK 헤더 없이
# 융합형·&cr;형 평문 제목 + 표 안 'N.' 나열(오탐 미끼)
_BLOB_NOTES = (
    '<SECTION-2><TITLE>주석</TITLE>\r\n'
    "<P>1. 당사의 개요&amp;cr;주식회사 테스트는 2000년 설립되었습니다."
    "</P>\r\n"
    '<TABLE WIDTH="600">\r\n'
    "<TR><TD><P>1.영업에서 창출된 현금</P></TD>"
    "<TD ALIGN=\"RIGHT\">100</TD></TR>\r\n"
    "<TR><TD><P>2.이자의 수취</P></TD>"
    "<TD ALIGN=\"RIGHT\">200</TD></TR>\r\n"
    "</TABLE>\r\n"
    "<P>2. 중요한 회계정책  (1) 회사는 K-IFRS를 적용합니다. 이하 본문이"
    " 길게 이어집니다.</P>\r\n"
    "<P>&amp;cr;&amp;cr;3. 관계기업투자&amp;cr;&amp;cr;(1) 내역은 다음과"
    " 같습니다.</P>\r\n"
    "<P>9. 우발부채  (1) 약정사항 내용.</P>\r\n"
    "<P>5. 역행하는 가짜 제목입니다.</P>\r\n"
    "</SECTION-2>\r"
)


@pytest.fixture(scope="module")
def blob_extract(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("b6")
    src = CONTENTS_XML
    lo = src.find("<SECTION-2><TITLE>주석</TITLE>")
    hi = src.find("</SECTION-2>") + len("</SECTION-2>\r")
    contents = src[:lo] + _BLOB_NOTES + src[hi:]
    dsd = build_dsd(str(tmp / "blob.dsd"), contents=contents)
    xlsx = str(tmp / "blob.xlsx")
    meta = extract(dsd, xlsx)
    return meta, FootingContext(xlsx)


def test_fused_and_cr_boundaries(blob_extract):
    """융합형·&cr;형 제목이 개별 시트로, 건너뜀(9) 허용."""
    _meta, ctx = blob_extract
    assert "1" in ctx.note_sheets and "2" in ctx.note_sheets
    assert "3" in ctx.note_sheets                # &cr; 프리픽스
    assert "9" in ctx.note_sheets                # 건너뜀 허용
    t2 = str(ctx.wb["2"].cell(1, 1).value or "")
    assert "중요한 회계정책" in t2               # 융합형 제목 인식


def test_table_items_not_headers(blob_extract):
    """표 셀 안 'N.' 나열은 헤더 아님 — 유령 시트 0."""
    _meta, ctx = blob_extract
    ghosts = [s for s in ctx.note_sheets
              if ctx.wb[s].max_row <= 1]
    assert ghosts == []
    # 표 미끼('1.영업에서 창출된 현금')가 주석 1 제목을 밀어내지 않음
    assert "당사의 개요" in str(ctx.wb["1"].cell(1, 1).value or "")


def test_no_backward_numbers(blob_extract):
    """역행 번호(9 뒤 5)는 경계 불인정 — 9번 본문에 잔류."""
    _meta, ctx = blob_extract
    # '5' 시트가 별도로 생기지 않아야 함 (기존 마크업 주석 번호와
    # 충돌 없는 합성 구성 기준)
    assert ctx.note_sheets == ["1", "2", "3", "9"]
    body9 = "\n".join(str(c.value) for row in ctx.wb["9"].iter_rows()
                      for c in row if c.value)
    assert "역행하는 가짜 제목" in body9
