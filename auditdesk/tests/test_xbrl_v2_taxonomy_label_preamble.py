"""Label preamble preservation from fresh OOXML, without accounting truth."""
import pytest
from test_xbrl_v2_taxonomy import edited, parse


@pytest.mark.parametrize('value', ['orphan source value', '  original\t\n', ' \t '])
def test_data_before_label_header_is_preserved_without_identity_guess(value):
    def change(workbook):
        sheet = workbook['Label Link']
        sheet.insert_rows(3)
        for column, cell in enumerate([99, 'ifrs', 'Cash', value], 1):
            sheet.cell(3, column, cell)
    data = edited(change)
    snapshot = parse(data)
    assert not snapshot.current_applicable
    assert len(snapshot.labels) == 3
    fields = [field for field in snapshot.label_source_fields if field.source.row == 3]
    assert [(field.source.column, field.value) for field in fields] == [
        (1, '99'), (2, 'ifrs'), (3, 'Cash'), (4, value)]
    assert all(field.qname is None and field.prefix == field.name == field.field_name == ''
               and field.classification == 'UNRESOLVED' for field in fields)
    assert all(field.source.sheet == 'Label Link' and field.source.snapshot_id == snapshot.snapshot_id
               for field in fields)
    assert any(item.code == 'REJECTED_LABEL_ROW' and item.severity == 'ERROR'
               and item.source.row == 3 for item in snapshot.diagnostics)
    assert snapshot == parse(data)


def test_whitespace_only_orphan_cell_before_language_row_is_not_empty():
    def change(workbook):
        sheet = workbook['Label Link']
        sheet.insert_rows(3)
        sheet.cell(3, 7, ' \t ')
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable and len(snapshot.labels) == 3
    assert [(field.source.row, field.source.column, field.value)
            for field in snapshot.label_source_fields] == [(3, 7, ' \t ')]


def test_missing_label_header_retains_uninterpreted_physical_values():
    snapshot = parse(edited(lambda workbook: workbook['Label Link'].delete_rows(4)))
    assert not snapshot.current_applicable and not snapshot.labels
    assert any(item.code == 'MISSING_LABEL_HEADER' for item in snapshot.diagnostics)
    fields = {(field.source.row, field.source.column): field for field in snapshot.label_source_fields}
    assert fields[(4, 4)].value == '\ud604\uae08'
    assert fields[(4, 4)].classification == 'UNRESOLVED' and fields[(4, 4)].qname is None


@pytest.mark.parametrize('value', ['unexpected value', ' \t '])
def test_extra_metadata_cell_is_retained_instead_of_accepted_as_preamble(value):
    snapshot = parse(edited(lambda workbook: workbook['Label Link'].cell(1, 7, value)))
    assert not snapshot.current_applicable and len(snapshot.labels) == 3
    field = next(field for field in snapshot.label_source_fields
                 if (field.source.row, field.source.column) == (1, 7))
    assert field.value == value and field.classification == 'UNRESOLVED'


def test_invalid_language_preamble_is_not_resource_authority():
    def change(workbook):
        workbook['Label Link'].cell(3, 4, 'not a language declaration')
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable and not snapshot.labels
    fields = {(field.source.row, field.source.column): field for field in snapshot.label_source_fields}
    assert fields[(3, 4)].value == 'not a language declaration'
    assert fields[(5, 4)].value == '\ud604\uae08' and fields[(5, 4)].classification == 'UNRESOLVED'


@pytest.mark.parametrize('metadata_layout', ['B_D', 'A_B'])
def test_explicit_metadata_and_language_preamble_remain_valid(metadata_layout):
    def change(workbook):
        if metadata_layout == 'A_B':
            sheet = workbook['Label Link']
            for cell in sheet[1]:
                cell.value = None
            sheet.cell(1, 1, 'LinkRole')
            sheet.cell(1, 2, 'urn:label')
    snapshot = parse(edited(change))
    assert snapshot.current_applicable and len(snapshot.labels) == 3
    assert not snapshot.label_source_fields


@pytest.mark.parametrize('language', ['fr', 'en-US'])
def test_explicit_language_markers_are_not_limited_to_korean_and_english(language):
    snapshot = parse(edited(lambda workbook: workbook['Label Link'].cell(3, 4, language)))
    assert snapshot.current_applicable and len(snapshot.labels) == 3
    assert {item.language for item in snapshot.labels} == {language, 'en'}
    assert not snapshot.label_source_fields
