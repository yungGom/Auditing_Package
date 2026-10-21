"""Issue #12: raw synthetic ZIP contracts, with no taxonomy dependency."""
from dataclasses import FrozenInstanceError
import io
import zipfile
import pytest
from auditdesk.xbrl_v2.dsd import parse_dsd, DsdParseError, DsdReportContext
from auditdesk.xbrl_v2.dsd_structure import parse_dsd_structure


def archive(xml):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('contents.xml', xml.encode('utf-8'))
    return out.getvalue()


def test_explicit_sections_notes_rows_columns_and_empty_notes():
    xml = ('<DOCUMENT><TABLE><TR><TD>표지</TD></TR></TABLE>'
           '<SECTION-1><TITLE>재무제표</TITLE><SECTION-2><TITLE>주석</TITLE>'
           '<P><SPAN USERMARK=" B">1. 현금</SPAN>본문</P><P>단위: 천원</P>'
           '<TABLE><TR><TH ROWSPAN="2">과목</TH><TH COLSPAN="2">금액</TH></TR>'
           '<TR><TH>당기 3개월</TH><TH>전기 누적</TH></TR>'
           '<TR><TD>현금</TD><TD>(1,000)</TD><TD/></TR></TABLE>'
           '<P><SPAN USERMARK=" B">2. 빈 주석</SPAN></P>'
           '</SECTION-2></SECTION-1><P>끝</P></DOCUMENT>')
    raw = archive(xml)
    d = parse_dsd_structure(raw, logical_uri='a/current.dsd')
    assert len(d.sections) == 2 and len(d.notes) == 2
    assert d.notes[1].text == '2. 빈 주석'
    table = next(x for x in d.structures if x.kind == 'TABLE' and x.parent_id == d.notes[0].subject_id)
    rows = [x for x in d.structures if x.kind == 'ROW' and x.parent_id == table.subject_id]
    cols = [x for x in d.structures if x.kind == 'COLUMN' and x.parent_id == table.subject_id]
    assert len(rows) == len(cols) == 3
    assert all(x.cell_ids for x in rows + cols)
    first = next(t for t in d.document.tables if t.table_id == table.subject_id).cells[0]
    assert first.subject_id in rows[0].cell_ids and first.subject_id in rows[1].cell_ids
    assert d.coverage.physical_cell_count == sum(len(t.cells) for t in d.document.tables)
    assert d.coverage.linked_cell_count == d.coverage.physical_cell_count
    assert len(d.cell_owners) == d.coverage.physical_cell_count
    assert any(c.kind == 'UNIT' and c.text == '단위: 천원' for c in d.clues)
    assert any(c.kind == 'PERIOD' and c.text == '당기 3개월' for c in d.clues)
    amount = next(s for s in d.document.subjects if s.text == '(1,000)')
    assert amount.unit is None and amount.scale is None
    assert any('period_extent' in v for v in d.diagnostics)
    relocated = parse_dsd_structure(raw, logical_uri='b/renamed.dsd')
    assert relocated.structures == d.structures
    assert relocated.document.snapshot_id == d.document.snapshot_id
    assert parse_dsd_structure(archive(xml.replace('(1,000)', '(1,001)'))).document.snapshot_id != d.document.snapshot_id
    with pytest.raises(FrozenInstanceError):
        d.logical_uri = 'changed'
    assert d.document.raw_xml == xml


def test_note_scope_does_not_leak_to_next_section_and_numeric_paragraph_not_note():
    xml = ('<DOCUMENT><SECTION-1><TITLE>주석</TITLE><P>1. 설명</P>'
           '<P><SPAN USERMARK="B">1. 명시 주석</SPAN></P></SECTION-1>'
           '<SECTION-1><TITLE>외부감사</TITLE><TABLE><TR><TD>1</TD></TR></TABLE></SECTION-1></DOCUMENT>')
    d = parse_dsd_structure(archive(xml))
    assert len(d.notes) == 1
    t = next(x for x in d.structures if x.kind == 'TABLE')
    assert t.parent_id == d.sections[1].subject_id
    assert 'UNKNOWN:unmarked_note_heading' in d.diagnostics


def test_unclassified_text_blank_rows_ragged_and_outside_table_are_retained():
    xml = '<DOCUMENT>outside<ODD>kept</ODD><TITLE/><TABLE><TR/><TR><TD>x</TD><TD/></TR></TABLE><TU>단위: 원</TU></DOCUMENT>'
    d = parse_dsd_structure(archive(xml))
    assert d.document.coverage.unclassified_text_nodes == 3
    assert len(d.unclassified) == 3
    assert {x.text for x in d.unclassified} == {'outside', 'kept', '단위: 원'}
    assert d.coverage.unclassified_count == 3
    assert any(x.kind == 'ROW' and not x.cell_ids for x in d.structures)
    assert any('ragged_table' in x for x in d.diagnostics)
    assert any(c.kind == 'UNIT' for c in d.clues)


def test_spans_and_clues_preserve_escaped_literal_and_multibyte():
    xml = '<DOCUMENT><SECTION-1><TITLE>주석</TITLE><P>A&cr;한글</P><P><SPAN USERMARK="B">1. 현금</SPAN></P><P>&amp;cr; 단위: 천원, USD</P></SECTION-1></DOCUMENT>'
    d = parse_dsd_structure(archive(xml))
    for item in d.structures + d.unclassified:
        for lo, hi in item.source_spans:
            assert 0 <= lo <= hi <= len(xml)
    note = d.notes[0]
    assert xml[slice(*note.source_spans[0])].startswith('<P><SPAN')
    clue = next(c for c in d.clues if c.kind == 'UNIT')
    assert '&amp;cr;' in xml[slice(*clue.source_span)]
    assert clue.text.startswith('&cr;')
    assert 'UNKNOWN:unit_interpretation' in d.diagnostics


@pytest.mark.parametrize('version', ['2.0', '1.1'])
def test_unsupported_xml_version_is_rejected(version):
    with pytest.raises(DsdParseError):
        parse_dsd(archive('<?xml version="'+version+'"?><DOCUMENT/>'))


@pytest.mark.parametrize('declaration', ['<?xml nonsense?>', '<?xml encoding="utf-8"?>', '<?xml version="1.0" junk="yes"?>'])
def test_malformed_xml_declaration_is_not_silently_removed(declaration):
    with pytest.raises(DsdParseError):
        parse_dsd(archive(declaration+'<DOCUMENT/>'))


@pytest.mark.parametrize('literal', ['<![CDATA[<?xml version="2.0"?>]]>', '<!--<?xml version="2.0"?>-->literal'])
def test_xml_declaration_literal_is_preserved_in_comment_or_cdata(literal):
    xml = '<DOCUMENT><P>'+literal+'</P></DOCUMENT>'
    d = parse_dsd(archive(xml))
    assert d.raw_xml == xml
    assert d.raw_xml[slice(*d.blocks[0].source_span)] == '<P>'+literal+'</P>'


def test_scope_evidence_conflict_is_visible_even_if_requested_matches_one():
    d = parse_dsd(archive('<DOCUMENT><DOCUMENT-NAME>연결 및 별도 보고서</DOCUMENT-NAME></DOCUMENT>'), report=DsdReportContext(scope='CONNECTED'))
    assert d.metadata.observed.scope is None
    assert 'CONFLICT:scope' in d.diagnostics


@pytest.mark.parametrize('header', ['전기오류수정', '당기손익인식금융자산', '전기 및 당기', '당기말 전기말'])
def test_substring_is_not_period_authority(header):
    d = parse_dsd(archive('<DOCUMENT><TABLE><TR><TH>'+header+'</TH></TR><TR><TD>7</TD></TR></TABLE></DOCUMENT>'))
    assert next(s for s in d.subjects if s.text == '7').period_role == 'UNKNOWN'


def test_rowspan_header_and_repeat_table_locality():
    d = parse_dsd_structure(archive('<DOCUMENT><TABLE><TR><TH ROWSPAN="2">현금</TH><TD>1</TD></TR><TR><TD>2</TD></TR></TABLE><TABLE><TR><TD>3</TD></TR></TABLE></DOCUMENT>'))
    s = next(s for s in d.document.subjects if s.text == '2')
    assert s.row_headers == ('현금',)
    assert next(s for s in d.document.subjects if s.text == '3').row_headers == ()


def test_missing_declarations_stay_unknown_and_no_taxonomy_loaded():
    import sys
    d = parse_dsd_structure(archive('<DOCUMENT><P>2026-12-31 연결</P></DOCUMENT>'), logical_uri='2026_connected.dsd')
    assert d.document.metadata.observed == DsdReportContext()
    assert not any(n.endswith('xbrl_v2.taxonomy') for n in sys.modules)
    assert 'UNKNOWN:note_topology' in d.diagnostics


def test_merged_only_columns_have_distinct_source_bound_identities():
    d = parse_dsd_structure(archive('<DOCUMENT><TABLE><TR><TD COLSPAN="2">merged</TD></TR></TABLE></DOCUMENT>'))
    columns = [s for s in d.structures if s.kind == 'COLUMN']
    assert len(columns) == 2
    assert columns[0].source_spans == columns[1].source_spans
    assert columns[0].cell_ids == columns[1].cell_ids
    assert columns[0].subject_id != columns[1].subject_id
    assert len({s.subject_id for s in d.structures}) == len(d.structures)


def test_nested_notes_scopes_are_unknown_without_duplicate_semantic_notes():
    xml = '<DOCUMENT><SECTION-1><TITLE>주석</TITLE><SECTION-2><TITLE>주석</TITLE><P><SPAN USERMARK="B">1. 현금</SPAN></P></SECTION-2></SECTION-1></DOCUMENT>'
    d = parse_dsd_structure(archive(xml))
    assert len(d.sections) == 2
    assert not d.notes
    assert 'UNKNOWN:nested_note_scopes' in d.diagnostics
    assert any(x.text == '1. 현금' for x in d.document.blocks)


@pytest.mark.parametrize('xml', ['<DOCUMENT><TABLE><TR><TD COLSPAN="0"/></TR></TABLE></DOCUMENT>', '<DOCUMENT><TABLE><TR><TD ROWSPAN="2"/><TD/></TR><TR><TD COLSPAN="2"/></TR></TABLE></DOCUMENT>'])
def test_invalid_or_ragged_grids_have_explicit_outcome(xml):
    try:
        d = parse_dsd_structure(archive(xml))
    except DsdParseError:
        return
    assert any('ragged_table' in v for v in d.diagnostics)
