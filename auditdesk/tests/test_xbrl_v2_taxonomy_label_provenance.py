"""Fresh source-column regressions; no workbook fixture or accounting truth."""
from dataclasses import FrozenInstanceError
import pytest
from test_xbrl_v2_taxonomy import edited, parse

HEADERS = ('base schema', 'systemid', 'prohibit', 'comment')


def metadata(w):
    ws = w['Label Link']
    ws.merge_cells('D3:E3')
    for col, name in enumerate(HEADERS, 7):
        ws.cell(4, col, name)
        ws.cell(5, col, 'source:' + name)


@pytest.mark.parametrize('field', HEADERS)
def test_known_source_columns_are_preserved_separately_from_labels(field):
    snapshot = parse(edited(metadata))
    assert snapshot.current_applicable
    assert {(l.language, l.role, l.text) for l in snapshot.labels} == {
        ('ko', 'label', '현금'), ('ko', 'verboseLabel', '현금 설명'), ('en', 'label', 'Cash')}
    fields = snapshot.label_source_fields
    assert len(fields) == 4
    item = next(f for f in fields if f.field_name == field)
    assert (item.prefix, item.name, item.value, item.classification) == ('ifrs', 'Cash', 'source:' + field, 'PROVENANCE')
    assert item.qname == snapshot.concepts[0].qname
    assert (item.source.sheet, item.source.row, item.source.column) == ('Label Link', 5, 7 + HEADERS.index(field))
    assert item.source.snapshot_id == snapshot.snapshot_id


@pytest.mark.parametrize('header', ['future metadata', ''])
def test_unknown_after_provenance_is_located_and_preserved_without_language_guess(header):
    def change(w):
        metadata(w)
        w['Label Link'].cell(4, 11, header)
        w['Label Link'].cell(5, 11, 'unresolved value')
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable and len(snapshot.labels) == 3
    item = snapshot.label_source_fields[-1]
    assert (item.field_name, item.value, item.classification, item.source.column) == (header, 'unresolved value', 'UNRESOLVED', 11)
    assert any(d.code == 'UNSUPPORTED_LABEL_COLUMN' and d.source.column == 11 for d in snapshot.diagnostics)


def test_explicit_language_after_provenance_does_not_reopen_resource_group():
    def change(w):
        metadata(w)
        ws = w['Label Link']
        ws.cell(3, 11, 'fr'); ws.cell(4, 11, 'label'); ws.cell(5, 11, 'unresolved french')
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable and len(snapshot.labels) == 3
    assert snapshot.label_source_fields[-1].classification == 'UNRESOLVED'
    assert snapshot.label_source_fields[-1].value == 'unresolved french'


def test_duplicate_provenance_headers_preserve_both_physical_columns():
    def change(w):
        metadata(w)
        w['Label Link'].cell(4, 11, 'base schema'); w['Label Link'].cell(5, 11, 'different schema')
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable
    items = [f for f in snapshot.label_source_fields if f.field_name == 'base schema']
    assert [(f.source.column, f.value) for f in items] == [(7, 'source:base schema'), (11, 'different schema')]
    assert len({f.field_id for f in items}) == 2
    assert any(d.code == 'AMBIGUOUS_LABEL_HEADER' for d in snapshot.diagnostics)


def test_language_on_provenance_is_an_error_but_values_survive():
    def change(w):
        metadata(w); w['Label Link'].cell(3, 7, 'en')
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable and len(snapshot.label_source_fields) == 4
    assert any(d.code == 'AMBIGUOUS_LABEL_HEADER' and d.source.column == 7 for d in snapshot.diagnostics)


def test_missing_identity_keeps_lexical_source_fields_without_qname_guess():
    def change(w):
        metadata(w); w['Label Link']['B5'] = None
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable
    assert all((f.prefix, f.name, f.qname) == ('', 'Cash', None) for f in snapshot.label_source_fields)
    assert len(snapshot.label_source_fields) == 4


def test_malformed_resource_header_keeps_values_unresolved_and_provenance_separate():
    def change(w):
        metadata(w); w['Label Link']['E4'] = 'label'
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable and not snapshot.labels
    assert len(snapshot.label_source_fields) == 7
    assert [f.classification for f in snapshot.label_source_fields] == ['UNRESOLVED'] * 3 + ['PROVENANCE'] * 4
    assert any(d.code == 'AMBIGUOUS_LABEL_HEADER' for d in snapshot.diagnostics)


def test_provenance_only_row_is_not_dropped_and_does_not_create_labels():
    def change(w):
        metadata(w)
        w['Label Link'].append([2, 'ifrs', 'Root', None, None, None, 'root-schema'])
    snapshot = parse(edited(change))
    assert snapshot.current_applicable and len(snapshot.labels) == 3
    field = snapshot.label_source_fields[-1]
    assert (field.name, field.value, field.source.row, field.source.column) == ('Root', 'root-schema', 6, 7)


def test_blank_provenance_has_no_invented_values_and_legacy_layout_stays_valid():
    def change(w):
        metadata(w)
        for col in range(7, 11): w['Label Link'].cell(5, col).value = None
    snapshot = parse(edited(change))
    assert snapshot.current_applicable and len(snapshot.labels) == 3
    assert snapshot.label_source_fields == ()
    assert parse().current_applicable and parse().label_source_fields == ()


def test_source_fields_are_immutable_deterministic_and_version_bound():
    data = edited(metadata)
    snapshot = parse(data)
    assert snapshot == parse(data)
    assert snapshot.parser_version == 'dart-workbook-preview/4'
    assert len({f.field_id for f in snapshot.label_source_fields}) == 4
    with pytest.raises(FrozenInstanceError): snapshot.label_source_fields[0].value = 'changed'


@pytest.mark.parametrize('value', ['  original source\t\n', ' \t '])
def test_provenance_preserves_original_whitespace_instead_of_normalizing(value):
    def change(w):
        metadata(w); w['Label Link'].cell(5, 7, value)
    snapshot = parse(edited(change))
    field = next(f for f in snapshot.label_source_fields if f.source.column == 7)
    assert field.value == value


def test_malformed_identity_header_still_retains_source_values_and_locations():
    def change(w):
        metadata(w); w['Label Link']['C4'] = 'unrecognized identity'
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable and not snapshot.labels
    assert len(snapshot.label_source_fields) == 7
    assert all(f.name == '' and f.qname is None for f in snapshot.label_source_fields)
    assert [f.source.column for f in snapshot.label_source_fields] == list(range(4, 11))
