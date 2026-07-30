"""스펙 2장의 공시 DSD 구조 불변식을 따르는 합성 DSD 픽스처.

실제 공시 DSD의 특징 재현:
- INSERTION placeholder (감사보고서 본문 없음)
- FS 제목이 TD 테이블 (공백 포함 "재 무 상 태 표")
- 4종 FS (포괄손익 통합)
- 주석 헤더 SPAN USERMARK=" B" + &amp;cr; 줄바꿈
- 빈 셀 <TD></TD>
- &cr;-only 셀(<TD>&amp;cr;</TD>)과 값+&cr; 혼합 셀 (--clean-cr 검증용)
- TE 셀 + ACODE (외부감사 표준양식)
- UTF-8 / CRLF
"""
import io
import zipfile

CONTENTS_XML = """<?xml version="1.0" encoding="utf-8"?>\r
<DART>\r
<BODY>\r
<INSERTION>◆click◆『정오표』삽입</INSERTION>\r
<COVER><COVER-TITLE>감 사 보 고 서</COVER-TITLE>\r
<P>제 57 기</P>\r
<P>2026년 01월 01일 부터 2026년 12월 31일 까지</P>\r
<P>테스트주식회사</P>\r
<P>&amp;cr;</P>\r
</COVER>\r
<TOC><P>목차입니다</P></TOC>\r
<INSERTION>◆click◆『감사인의 감사보고서』삽입</INSERTION>\r
<SECTION-1><TITLE>(첨부)재무제표</TITLE>\r
<WARNING>이 재무제표는 K-IFRS에 따라 작성되었습니다</WARNING>\r
<INSERTION>◆재무상태표 삽입◆</INSERTION>\r
<TABLE WIDTH="600"><TR><TD ALIGN="CENTER" COLSPAN="2">재 무 상 태 표</TD></TR></TABLE>\r
<TABLE WIDTH="600"><TR><TD>제 57 기  2026년 12월 31일 현재</TD><TD ALIGN="RIGHT">(단위 : 백만원)</TD></TR></TABLE>\r
<TABLE WIDTH="600">\r
<TR><TH ROWSPAN="2">과목</TH><TH ROWSPAN="2">주석</TH><TH COLSPAN="2">당기</TH><TH COLSPAN="2">전기</TH></TR>\r
<TR><TH>금액1</TH><TH>금액2</TH><TH>금액1</TH><TH>금액2</TH></TR>\r
<TR><TD>자산총계</TD><TD>3,4</TD><TD></TD><TD ALIGN="RIGHT">1,234,567</TD><TD></TD><TD ALIGN="RIGHT">1,111,111</TD></TR>\r
<TR><TD>현금및현금성자산</TD><TD>4, 28</TD><TD ALIGN="RIGHT">500,000</TD><TD></TD><TD ALIGN="RIGHT">450,000</TD><TD></TD></TR>\r
<TR><TD>부채총계</TD><TD></TD><TD></TD><TD ALIGN="RIGHT">(234,567)</TD><TD></TD><TD ALIGN="RIGHT">(211,111)</TD></TR>\r
<TR><TD>기타참고</TD><TD>&amp;cr;</TD><TD>&amp;cr;&amp;cr;</TD><TD ALIGN="RIGHT">777</TD><TD>주석&amp;cr;참조</TD><TD></TD></TR>\r
</TABLE>\r
<INSERTION>◆포괄손익계산서 삽입◆</INSERTION>\r
<TABLE WIDTH="600"><TR><TD ALIGN="CENTER">포괄손익계산서</TD></TR></TABLE>\r
<TABLE WIDTH="600">\r
<TR><TH>과목</TH><TH>당기</TH><TH>전기</TH></TR>\r
<TR><TD>매출액</TD><TD ALIGN="RIGHT">999,999</TD><TD ALIGN="RIGHT">888,888</TD></TR>\r
<TR><TD>당기순이익</TD><TD ALIGN="RIGHT">77,777</TD><TD ALIGN="RIGHT">66,666</TD></TR>\r
</TABLE>\r
<INSERTION>◆자본변동표 삽입◆</INSERTION>\r
<TABLE WIDTH="600"><TR><TD ALIGN="CENTER">자 본 변 동 표</TD></TR></TABLE>\r
<TABLE WIDTH="600">\r
<TR><TH>과목</TH><TH>자본금</TH><TH>이익잉여금</TH></TR>\r
<TR><TD>기초잔액</TD><TD ALIGN="RIGHT">100,000</TD><TD ALIGN="RIGHT">200,000</TD></TR>\r
</TABLE>\r
<INSERTION>◆현금흐름표 삽입◆</INSERTION>\r
<TABLE WIDTH="600"><TR><TD ALIGN="CENTER">현 금 흐 름 표</TD></TR></TABLE>\r
<TABLE WIDTH="600">\r
<TR><TH>과목</TH><TH>당기</TH><TH>전기</TH></TR>\r
<TR><TD>영업활동현금흐름</TD><TD ALIGN="RIGHT">123,456</TD><TD ALIGN="RIGHT">120,000</TD></TR>\r
</TABLE>\r
<SECTION-2><TITLE>주석</TITLE>\r
<P><SPAN USERMARK=" B">1. 일반적 사항</SPAN>&amp;cr;&amp;cr;테스트주식회사(이하 "회사")는 2000년에 설립되었습니다.</P>\r
<P>회사의 본사는 서울특별시에 위치하고 있습니다.</P>\r
<P><SPAN USERMARK=" B">2. 재무제표 작성기준</SPAN>&amp;cr;&amp;cr;회사는 K-IFRS를 적용하고 있습니다.</P>\r
<TU ALIGN="RIGHT">(단위 : 백만원)</TU>\r
<TABLE WIDTH="600">\r
<TR><TH>구분</TH><TH>당기</TH><TH>전기</TH></TR>\r
<TR><TD>금융자산</TD><TD ALIGN="RIGHT">12,581,632</TD><TD ALIGN="RIGHT">11,000,000</TD></TR>\r
<TR><TD>금융부채</TD><TD ALIGN="RIGHT">3,456</TD><TD></TD></TR>\r
</TABLE>\r
<P><SPAN USERMARK=" B">3. 현금및현금성자산</SPAN>&amp;cr;&amp;cr;당기말 현금 내역은 다음과 같습니다.</P>\r
<TABLE WIDTH="600">\r
<TR><TH>구분</TH><TH>금액</TH></TR>\r
<TR><TD>보통예금</TD><TD ALIGN="RIGHT">500,000</TD></TR>\r
</TABLE>\r
</SECTION-2>\r
</SECTION-1>\r
<INSERTION>◆부속명세서 삽입◆</INSERTION>\r
<INSERTION>◆내부회계관리제도 검토의견 삽입◆</INSERTION>\r
<SECTION-1><TITLE>외부감사 실시내용</TITLE>\r
<SECTION-2><TITLE>1. 감사참여자 구분별 인원수 및 감사시간</TITLE>\r
<TABLE WIDTH="600">\r
<TR><TH>구분</TH><TH>품질관리검토자</TH><TH>담당이사</TH></TR>\r
<TR><TD>인원수</TD><TE ACODE="A001">1</TE><TE ACODE="A002">2</TE></TR>\r
<TR><TD>감사시간</TD><TE ACODE="A003">10</TE><TE ACODE="A004"></TE></TR>\r
</TABLE>\r
</SECTION-2>\r
</SECTION-1>\r
</BODY>\r
</DART>\r
"""


META_XML_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    "<METAINFO>\r\n"
    '\t<GENERATOR schema="dart4.xsd" editver="{editver}"/>\r\n'
    '\t<DOCUMENT-HEADER regcik="" regname=""/>\r\n'
    '\t<DOCUMENT-INFO docver="4.1" bsn-id="00760" rpt-id="00760" '
    'doc-id="00760" iscorrection="N"/>\r\n'
    "</METAINFO>\r\n")



# H-1 회귀 픽스처: 반기/분기·중간·요약·제N기·연결 접두 변형 제목
# + FS유사 미분류 제목 1건 (침묵 탈락 금지 검증용)
CONTENTS_XML_HALF = (
    CONTENTS_XML
    .replace("재 무 상 태 표", "연결 반기 재무상태표")
    .replace("포괄손익계산서</TD>", "중간요약포괄손익계산서</TD>")
    .replace("자 본 변 동 표", "자본변동표(제57기 반기)")
    .replace("현 금 흐 름 표", "제 57 기 분기 현금흐름표")
    .replace(
        "<SECTION-2><TITLE>주석</TITLE>",
        '<TABLE WIDTH="600"><TR><TD ALIGN="CENTER">'
        "재무상태표 부속명세"
        "</TD></TR></TABLE>\r\n"
        "<SECTION-2><TITLE>주석</TITLE>")
)


def build_dsd(path: str, contents: str = CONTENTS_XML,
              editver: str = "5.049", no_meta: bool = False):
    """contents.xml + meta.xml(실제 형식) 부속 엔트리를 가진 .dsd(ZIP) 생성."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("contents.xml", contents.encode("utf-8"))
        if not no_meta:                 # B-4: 수신 래핑본 모의
            z.writestr(
                "meta.xml",
                META_XML_TEMPLATE.format(editver=editver).encode("utf-8"))
        z.writestr("images/logo.bin", bytes(range(256)) * 4)
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return path
