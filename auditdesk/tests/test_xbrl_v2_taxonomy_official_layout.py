"""Fresh OOXML for two observed layouts; no official workbook fixture."""
from test_xbrl_v2_taxonomy import edited, parse
import pytest


def compact(w, sections=(0, 1)):
    ws = w['Presentation Link']
    for section in sections:
        start = section * 5 + 1
        role, definition = ws.cell(start, 4).value, ws.cell(start + 1, 4).value
        header = [ws.cell(start + 2, c).value for c in range(1, 13)]
        rows = [[ws.cell(start + n, c).value for c in range(1, 13)] for n in (3, 4)]
        for row in range(start, start + 5):
            for col in range(1, 13):
                ws.cell(row, col).value = None
        ws.cell(start, 1, 'LinkRole'); ws.cell(start, 2, role)
        ws.cell(start + 1, 1, 'Definition'); ws.cell(start + 1, 2, definition)
        # Official table uses explicit named columns, without synthetic #/gap.
        columns = [1, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        for offset, source in enumerate([header, *rows], 2):
            for col, source_col in enumerate(columns, 1):
                ws.cell(start + offset, col).value = source[source_col]


@pytest.mark.parametrize('sections', [(0, 1), (0,), (1,)])
def test_official_and_existing_sections_preserve_roles_paths_and_resources(sections):
    snapshot = parse(edited(lambda w: compact(w, sections)))
    assert snapshot.current_applicable
    assert len(snapshot.occurrences) == 4
    assert {o.role_uri for o in snapshot.occurrences} == {'urn:role:a'}
    assert len({o.occurrence_id for o in snapshot.occurrences}) == 4
    assert snapshot.occurrences[1].path == snapshot.occurrences[3].path
    assert (len(snapshot.concepts), len(snapshot.labels), len(snapshot.references)) == (2, 3, 1)
    assert not snapshot.diagnostics


@pytest.mark.parametrize('row', [3, 8])
def test_official_headerless_section_retains_rejection_locations(row):
    def change(w):
        compact(w)
        w['Presentation Link'].delete_rows(row)
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable and len(snapshot.occurrences) == 2
    assert {o.role_uri for o in snapshot.occurrences} == {'urn:role:a'}
    assert any(d.code == 'MISSING_PRESENTATION_HEADER' for d in snapshot.diagnostics)
    assert [d.source.row for d in snapshot.diagnostics if d.code == 'REJECTED_PRESENTATION_ROW'] == ([3, 4] if row == 3 else [8, 9])


def test_extra_cells_cannot_be_guessed_as_official_role_metadata():
    def change(w):
        compact(w)
        w['Presentation Link']['C1'] = 'unexpected'
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable
    assert any(d.code == 'MALFORMED_PRESENTATION_METADATA' and d.source.row == 1
               for d in snapshot.diagnostics)


def test_extra_cells_cannot_be_dropped_from_existing_role_metadata():
    snapshot = parse(edited(lambda w: setattr(w['Presentation Link']['C1'], 'value', 'unexpected')))
    assert not snapshot.current_applicable
    assert any(d.code == 'MALFORMED_PRESENTATION_METADATA' and d.source.row == 1
               for d in snapshot.diagnostics)


def test_official_definition_extra_cells_remain_rejected():
    def change(w):
        compact(w)
        w['Presentation Link']['C2'] = 'unexpected'
    snapshot = parse(edited(change))
    assert not snapshot.current_applicable and len(snapshot.occurrences) == 4
    assert any(d.code == 'REJECTED_PRESENTATION_ROW' and d.source.row == 2
               for d in snapshot.diagnostics)
