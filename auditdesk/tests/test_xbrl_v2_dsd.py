import io
import zipfile
from dataclasses import FrozenInstanceError
import pytest
from auditdesk.xbrl_v2.dsd import parse_dsd, DsdReportContext, DsdParseError


def archive(xml, extra=()):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('contents.xml', xml.encode('utf-8'))
        for name, value in extra:
            z.writestr(name, value)
    return out.getvalue()


def test_topology_raw_values_and_stable_subjects():
    xml = '<DOCUMENT><TITLE>주석</TITLE><P></P><P>단위: 천원</P><TABLE><TR><TH ROWSPAN="2">계정</TH><TH COLSPAN="2">금액</TH></TR><TR><TH>당기</TH><TH>전기</TH></TR><TR><TD>현금</TD><TD>(1,000)</TD><TD></TD></TR><TR><TD>기타</TD><TD NIL="true"/><TD>-</TD></TR></TABLE><P>끝&cr;문단 &amp;cr;</P></DOCUMENT>'
    d = parse_dsd(archive(xml))
    assert d.raw_xml == xml
    assert len(d.tables) == 1
    assert d.tables[0].cells[0].rowspan == 2
    assert d.tables[0].cells[1].colspan == 2
    amount = next(s for s in d.subjects if s.text == '(1,000)')
    assert amount.row_headers == ('현금',)
    assert amount.column_headers == ('금액', '당기')
    assert amount.period_role == 'CURRENT'
    assert amount.scale is None and amount.unit is None
    assert d.raw_xml[slice(*amount.source_span)] == '<TD>(1,000)</TD>'
    assert any(s.value_state == 'NIL' for s in d.subjects)
    assert any(s.kind == 'P' and s.value_state == 'BLANK' for s in d.subjects)
    assert d.subjects == parse_dsd(archive(xml)).subjects
    with pytest.raises(FrozenInstanceError):
        d.raw_xml = ''


@pytest.mark.parametrize('xml', ['<!DOCTYPE x [<!ENTITY a SYSTEM "file:///secret">]><x>&a;</x>', '<x><TABLE><TR><TD><TABLE/></TD></TR></TABLE></x>', '<x><TABLE><TD>x</TD></TABLE></x>', '<x><P></x>'])
def test_unsafe_or_unsupported_xml_rejected(xml):
    with pytest.raises(DsdParseError):
        parse_dsd(archive(xml))


@pytest.mark.parametrize('path', ['../bad', '/bad', 'a/../bad', 'C:/bad'])
def test_zip_paths_rejected(path):
    with pytest.raises(DsdParseError):
        parse_dsd(archive('<DOCUMENT/>', [(path, b'x')]))


def test_duplicate_contents_rejected():
    with pytest.warns(UserWarning):
        data = archive('<DOCUMENT/>', [('contents.xml', b'<DOCUMENT/>')])
    with pytest.raises(DsdParseError):
        parse_dsd(data)


def test_identity_conflicts_and_missing_evidence():
    report = DsdReportContext(entity_identifier='requested', scope='SEPARATE', period_end='2026-12-31')
    xml = '<DOCUMENT><COMPANY-NAME AREGCIK="observed">샘플</COMPANY-NAME><DOCUMENT-NAME>연결감사보고서</DOCUMENT-NAME><PERIODEND>2025-12-31</PERIODEND><P>2024-01-01</P></DOCUMENT>'
    d = parse_dsd(archive(xml), report=report)
    assert any(x.startswith('CONFLICT:entity_identifier') for x in d.diagnostics)
    assert any(x.startswith('CONFLICT:scope') for x in d.diagnostics)
    assert any(x.startswith('CONFLICT:period_end') for x in d.diagnostics)
    unknown = parse_dsd(archive('<DOCUMENT><P>2025-12-31</P></DOCUMENT>'), report=report)
    assert unknown.metadata.observed.period_end is None
    assert 'UNKNOWN:period_end' in unknown.diagnostics


def test_unsupported_text_visible_and_resource_limit():
    d = parse_dsd(archive('<DOCUMENT>outside<ODD>kept</ODD><TITLE>빈 주석</TITLE></DOCUMENT>'))
    assert any('UNCLASSIFIED_TEXT' in x for x in d.diagnostics)
    assert d.coverage.unclassified_text_nodes == 2
    with pytest.raises(DsdParseError):
        parse_dsd(archive('<DOCUMENT/>'), max_uncompressed_bytes=2)


def test_cp949_and_xml_declaration_spans():
    xml = '<?xml version="1.0" encoding="euc-kr"?><DOCUMENT><P>한글</P></DOCUMENT>'
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('contents.xml', xml.encode('euc-kr'))
    d = parse_dsd(out.getvalue())
    assert d.raw_xml[slice(*d.blocks[0].source_span)] == '<P>한글</P>'
    assert d.source_role == 'CURRENT_DSD'


@pytest.mark.parametrize('date', ['2026-02-30', '2026-1-1', 'garbage'])
def test_invalid_dates_fail_closed(date):
    with pytest.raises(DsdParseError):
        DsdReportContext(period_end=date)
    with pytest.raises(DsdParseError):
        parse_dsd(archive('<DOCUMENT><PERIODEND>' + date + '</PERIODEND></DOCUMENT>'))


def test_invalid_spans_and_comparison_ambiguity():
    with pytest.raises(DsdParseError):
        parse_dsd(archive('<DOCUMENT><TABLE><TR><TD ROWSPAN="9">x</TD></TR></TABLE></DOCUMENT>'))
    xml = '<DOCUMENT><TABLE><TR><TH>당기 전기</TH></TR><TR><TD>7</TD></TR></TABLE></DOCUMENT>'
    d = parse_dsd(archive(xml))
    assert next(s for s in d.subjects if s.text == '7').period_role == 'UNKNOWN'


def test_symlink_and_compression_bomb_rejected():
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('contents.xml', '<DOCUMENT/>')
        info = zipfile.ZipInfo('link')
        info.external_attr = 0o120777 << 16
        z.writestr(info, 'outside')
    with pytest.raises(DsdParseError):
        parse_dsd(out.getvalue())
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('contents.xml', '<DOCUMENT>' + ' ' * 100000 + '</DOCUMENT>')
    with pytest.raises(DsdParseError):
        parse_dsd(out.getvalue())


def test_depth_and_table_count_limits():
    with pytest.raises(DsdParseError):
        parse_dsd(archive('<X>' * 65 + '</X>' * 65))
    with pytest.raises(DsdParseError):
        parse_dsd(archive('<DOCUMENT>' + '<TABLE/>' * 513 + '</DOCUMENT>'))


def test_entity_offsets_and_single_decode_preserve_literal_text():
    xml = '<DOCUMENT><P>A&cr;B</P><P>C</P><P>&amp;cr;</P><TABLE><TR><TD>한글&cr;끝</TD></TR></TABLE></DOCUMENT>'
    d = parse_dsd(archive(xml))
    assert [d.raw_xml[slice(*s.source_span)] for s in d.blocks] == ['<P>A&cr;B</P>', '<P>C</P>', '<P>&amp;cr;</P>']
    assert d.blocks[2].text == '&cr;'
    cell = d.tables[0].cells[0]
    assert d.raw_xml[slice(*cell.source_span)] == '<TD>한글&cr;끝</TD>'


@pytest.mark.parametrize('encoding', ['utf-8', 'euc-kr'])
def test_multiple_entity_spans_with_declaration_and_multibyte(encoding):
    xml = '<?xml version="1.0" encoding="' + encoding + '"?><DOCUMENT><!--&cr;--><P>한&cr;&cr;글</P><P><![CDATA[&cr;]]></P><P>&amp;cr;</P><TABLE><TR><TD>&cr;끝</TD></TR></TABLE></DOCUMENT>'
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('contents.xml', xml.encode(encoding))
    d = parse_dsd(out.getvalue())
    assert [d.raw_xml[slice(*s.source_span)] for s in d.blocks] == ['<P>한&cr;&cr;글</P>', '<P><![CDATA[&cr;]]></P>', '<P>&amp;cr;</P>']
    assert d.blocks[1].text == d.blocks[2].text == '&cr;'
    assert d.raw_xml[slice(*d.tables[0].source_span)] == '<TABLE><TR><TD>&cr;끝</TD></TR></TABLE>'
    assert d.raw_xml[slice(*d.tables[0].cells[0].source_span)] == '<TD>&cr;끝</TD>'
