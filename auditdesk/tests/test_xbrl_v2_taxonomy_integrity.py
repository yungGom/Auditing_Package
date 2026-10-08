"""Source identity and presentation completeness; fresh OOXML, no truth fixtures."""
from dataclasses import FrozenInstanceError

import pytest

from test_xbrl_v2_taxonomy import edited, parse


def test_original_source_identifiers_survive_graph_projection():
    snapshot = parse()
    assert [c.source_id for c in snapshot.concepts] == ['cash', 'root']
    assert [r.source_id for r in snapshot.roles] == ['r']
    assert snapshot.concepts[0].concept_id != snapshot.concepts[0].source_id
    with pytest.raises(FrozenInstanceError):
        snapshot.roles[0].source_id = 'replacement'


@pytest.mark.parametrize('sheet', ['Concepts', 'RoleTypes'])
def test_source_identifier_collision_preserves_both_records_and_locations(sheet):
    def collide(w):
        if sheet == 'Concepts':
            w[sheet]['D3'] = 'cash'
        else:
            w[sheet].append([2, 'r', 'urn:role:b', 'presentationLink', 'Second role'])
    data = edited(collide)
    snapshot = parse(data)
    assert not snapshot.current_applicable
    records = snapshot.concepts if sheet == 'Concepts' else snapshot.roles
    assert len(records) == 2 and len({r.source_id for r in records}) == 1
    diagnostics = [d for d in snapshot.diagnostics if d.code == 'DUPLICATE_SOURCE_ID']
    assert {d.source.row for d in diagnostics if d.source.sheet == sheet} == {2, 3}
    assert all(d.severity == 'ERROR' for d in diagnostics)
    assert snapshot == parse(data)


def test_source_id_collision_across_namespaces_is_not_guessed_separate():
    from hashlib import sha256
    from dataclasses import replace
    from auditdesk.xbrl_v2.taxonomy import NamespaceBinding, parse_taxonomy_workbook
    data = edited(lambda w: w['Concepts'].append(
        [3, 'other', 'Cash', 'cash', 'xbrli:monetaryItemType', 'instant', 'false']))
    metadata = replace(parse().metadata, content_sha256=sha256(data).hexdigest())
    snapshot = parse_taxonomy_workbook(data, logical_uri='public:taxonomy.xlsx',
        metadata=metadata, namespaces=(NamespaceBinding('ifrs', 'urn:ifrs:2026', 'release'),
                                      NamespaceBinding('other', 'urn:other:2026', 'release')))
    assert snapshot.concepts[0].qname != snapshot.concepts[-1].qname
    assert not snapshot.current_applicable
    assert 'DUPLICATE_SOURCE_ID' in {d.code for d in snapshot.diagnostics}


def test_source_identifiers_are_scoped_by_record_kind_not_cross_sheet_guessing():
    snapshot = parse(edited(lambda w: setattr(w['RoleTypes']['B2'], 'value', 'cash')))
    assert snapshot.current_applicable
    assert snapshot.roles[0].source_id == snapshot.concepts[0].source_id


def test_three_collisions_report_every_conflicting_source_row_once():
    def collide(w):
        w['Concepts']['D3'] = 'cash'
        w['Concepts'].append([3, 'ifrs', 'Third', 'cash', 'xbrli:stringItemType', 'duration', 'false'])
    snapshot = parse(edited(collide))
    errors = [d for d in snapshot.diagnostics if d.code == 'DUPLICATE_SOURCE_ID']
    assert not snapshot.current_applicable and len(snapshot.concepts) == 3
    assert [d.source.row for d in errors] == [2, 3, 4]


@pytest.mark.parametrize('row', [3, 8])
def test_missing_header_in_any_section_is_visible_with_rejected_rows(row):
    snapshot = parse(edited(lambda w: w['Presentation Link'].delete_rows(row, 1)))
    assert not snapshot.current_applicable
    assert len(snapshot.occurrences) == 2
    errors = [d for d in snapshot.diagnostics if d.code == 'MISSING_PRESENTATION_HEADER']
    assert len(errors) == 1 and errors[0].source.sheet == 'Presentation Link'
    rejected = [d.source.row for d in snapshot.diagnostics if d.code == 'REJECTED_PRESENTATION_ROW']
    assert rejected == ([3, 4] if row == 3 else [8, 9])


def test_all_section_headers_missing_keeps_every_rejection_location():
    def remove(w):
        w['Presentation Link'].delete_rows(8, 1)
        w['Presentation Link'].delete_rows(3, 1)
    snapshot = parse(edited(remove))
    assert not snapshot.current_applicable and not snapshot.occurrences
    assert len([d for d in snapshot.diagnostics if d.code == 'MISSING_PRESENTATION_HEADER']) == 2
    assert [d.source.row for d in snapshot.diagnostics if d.code == 'REJECTED_PRESENTATION_ROW'] == [3, 4, 7, 8]


def test_empty_headerless_trailing_section_is_not_hidden_by_earlier_success():
    def append(w):
        w['Presentation Link'].append([None, 'LinkRole', None, 'urn:role:a'])
        w['Presentation Link'].append([None, 'Definition', None, 'Cash role'])
    snapshot = parse(edited(append))
    assert not snapshot.current_applicable and len(snapshot.occurrences) == 4
    assert any(d.code == 'MISSING_PRESENTATION_HEADER' and d.source.row == 11
               for d in snapshot.diagnostics)


def test_malformed_later_header_cannot_drop_its_nonempty_rows():
    snapshot = parse(edited(lambda w: setattr(w['Presentation Link']['F8'], 'value', 'name')))
    assert not snapshot.current_applicable and len(snapshot.occurrences) == 2
    assert {'MALFORMED_PRESENTATION_HEADER', 'REJECTED_PRESENTATION_ROW'} <= {
        d.code for d in snapshot.diagnostics}


def test_headerless_middle_section_does_not_poison_next_valid_section():
    def append(w):
        w['Presentation Link'].delete_rows(8, 1)
        w['Presentation Link'].append([None, 'LinkRole', None, 'urn:role:a'])
        w['Presentation Link'].append([None, 'Definition', None, 'Cash role'])
        w['Presentation Link'].append(['#', 'prefix', None, 'name', 'label', 'depth', 'order',
            'priority', 'parent', 'arcrole', 'preferredLabel', 'systemid'])
        w['Presentation Link'].append([1, 'ifrs', None, 'Root', 'Root', 0, 1, 0, None, 'parent-child', None, 'a.xsd'])
        w['Presentation Link'].append([2, 'ifrs', None, 'Cash', 'Cash', 1, 1, 0, 'ifrs:Root', 'parent-child', 'label', 'a.xsd'])
    snapshot = parse(edited(append))
    assert not snapshot.current_applicable and len(snapshot.occurrences) == 4
    assert snapshot.occurrences[1].path == snapshot.occurrences[3].path
    assert len({o.occurrence_id for o in snapshot.occurrences}) == 4


def test_supported_metadata_and_blank_rows_are_not_rejected():
    snapshot = parse(edited(lambda w: w['Presentation Link'].insert_rows(8)))
    assert snapshot.current_applicable and len(snapshot.occurrences) == 4
    assert not any(d.code in {'REJECTED_PRESENTATION_ROW', 'MISSING_PRESENTATION_HEADER'}
                   for d in snapshot.diagnostics)


def test_integrity_parser_version_changes_snapshot_reuse_boundary():
    snapshot = parse()
    assert snapshot.parser_version == 'dart-workbook-preview/3'
    assert snapshot.capabilities == 'PARTIAL' and snapshot.dimensions_known is False
