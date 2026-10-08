"""Issue #12-only topology projection. No taxonomy or recommendation imports.

The legacy-compatible DsdDocument remains intact inside this separate contract.
Locators are character offsets into document.raw_xml. Column locators can be
disjoint; merged coordinates refer to their original physical cell anchor.
Clues are observations, never resolved accounting units, dates or scope.
"""
from dataclasses import dataclass
import re
from .dsd import DsdDocument, DsdReportContext, _nodes, parse_dsd
from .model import stable_id

PARSER_VERSION = 'issue12-structure-v1'


@dataclass(frozen=True)
class DsdStructure:
    subject_id: str
    kind: str
    parent_id: str
    text: str
    source_spans: tuple[tuple[int, int], ...]
    cell_ids: tuple[str, ...] = ()
    index: int | None = None


@dataclass(frozen=True)
class DsdClue:
    clue_id: str
    kind: str
    text: str
    source_span: tuple[int, int]
    source_subject_id: str | None
    interpretation: str = 'UNKNOWN'


@dataclass(frozen=True)
class StructureCoverage:
    physical_cell_count: int
    linked_cell_count: int
    unclassified_count: int


@dataclass(frozen=True)
class DsdStructuredDocument:
    document: DsdDocument
    logical_uri: str
    projection_id: str
    structures: tuple[DsdStructure, ...]
    sections: tuple[DsdStructure, ...]
    notes: tuple[DsdStructure, ...]
    unclassified: tuple[DsdStructure, ...]
    clues: tuple[DsdClue, ...]
    cell_owners: tuple[tuple[str, str], ...]
    coverage: StructureCoverage
    diagnostics: tuple[str, ...]
    parser_version: str = PARSER_VERSION


def parse_dsd_structure(data: bytes, *, report: DsdReportContext | None = None,
                        logical_uri: str = '', max_uncompressed_bytes: int = 16*1024*1024):
    doc = parse_dsd(data, report=report, max_uncompressed_bytes=max_uncompressed_bytes)
    nodes = _nodes(doc.raw_xml)
    diagnostics = list(doc.diagnostics)
    structures, sections, notes, unclassified, clues, cell_owners = [], [], [], [], [], []
    projection = stable_id('dsd-projection', (doc.document_id, PARSER_VERSION))

    def ancestry(n):
        p = n.parent
        while p:
            yield p
            p = p.parent

    def sid(kind, span):
        return stable_id('dsd-' + kind.lower(), (doc.document_id, span, PARSER_VERSION))

    def make(kind, parent, text, spans, cells=(), index=None, identity=None):
        item = DsdStructure(identity or sid(kind, (parent, index, spans)), kind, parent, text, tuple(spans), tuple(cells), index)
        structures.append(item)
        return item

    # Only literal section elements are authoritative physical sections.
    for n in nodes:
        if re.fullmatch(r'SECTION-\d+', n.tag):
            parent = next((s.subject_id for s in reversed(sections)
                           if s.source_spans[0][0] <= n.start and n.end <= s.source_spans[0][1]), doc.document_id)
            title = next((c.text for c in n.children if c.tag == 'TITLE'), '')
            sections.append(make('SECTION', parent, title, ((n.start, n.end),)))

    def owner(start, end):
        for item in tuple(reversed(notes)) + tuple(reversed(sections)):
            # Prefer notes explicitly, then innermost sections.
            if item.source_spans[0][0] <= start and end <= item.source_spans[0][1]:
                return item.subject_id
        return doc.document_id

    # A note requires a marked numbered heading within an explicit notes section.
    # Unmarked numbering is retained as a block and diagnostic, not guessed.
    note_scopes = [s for s in sections if re.sub(r'\s+', '', s.text) == '주석']
    for scope in note_scopes:
        lo, hi = scope.source_spans[0]
        if any(other is not scope and
               (lo <= other.source_spans[0][0] < other.source_spans[0][1] <= hi or
                other.source_spans[0][0] <= lo < hi <= other.source_spans[0][1])
               for other in note_scopes):
            diagnostics.append('UNKNOWN:nested_note_scopes')
            continue
        candidates = []
        for n in nodes:
            if not (lo < n.start and n.end < hi) or any(p.tag == 'TABLE' for p in ancestry(n)):
                continue
            if n.tag == 'SPAN' and n.attrs.get('USERMARK', '').strip() == 'B' and re.match(r'^\d+\s*[.．]', n.text):
                # Keep the heading paragraph together, including a fused body.
                p = n.parent if n.parent and n.parent.tag == 'P' else n
                candidates.append((p.start, n.text))
            elif n.tag == 'P' and re.match(r'^\d+\s*[.．]', n.text) and not any(c.tag == 'SPAN' and c.attrs.get('USERMARK', '').strip() == 'B' for c in n.children):
                diagnostics.append('UNKNOWN:unmarked_note_heading')
        # Multiple marked headings in a fused paragraph have no safe split here.
        starts = [p for p, _ in candidates]
        for i, (start, text) in enumerate(candidates):
            if starts.count(start) != 1:
                diagnostics.append('UNKNOWN:fused_note_headings')
                continue
            end = candidates[i+1][0] if i+1 < len(candidates) else hi
            notes.append(make('NOTE', scope.subject_id, text, ((start, end),)))
    if not notes:
        diagnostics.append('UNKNOWN:note_topology')

    # Physical tables and blocks use the underlying DsdDocument identifiers;
    # its parser profile is versioned independently from this projection.
    for table in doc.tables:
        diagnostics.append('UNKNOWN:table_title_semantics:' + table.table_id)
        make('TABLE', owner(*table.source_span), table.title, (table.source_span,), identity=table.table_id)
        table_node = next(n for n in nodes if n.tag == 'TABLE' and n.start == table.source_span[0])
        rows = [n for n in nodes if n.tag == 'TR' and table_node in ancestry(n)]
        for r, n in enumerate(rows):
            cells = tuple(c.subject_id for c in table.cells if c.row <= r < c.row+c.rowspan)
            make('ROW', table.table_id, n.text, ((n.start, n.end),), cells, r)
        for col in range(table.column_count):
            cells = tuple(c for c in table.cells if c.column <= col < c.column+c.colspan)
            make('COLUMN', table.table_id, '', tuple(c.source_span for c in cells),
                 tuple(c.subject_id for c in cells), col)
        cell_owners.extend((c.subject_id, table.table_id) for c in table.cells)
    for block in doc.blocks:
        make('BLOCK', owner(*block.source_span), block.text, (block.source_span,), identity=block.subject_id)

    # Every unclassified text owner is explicitly projected; raw_xml preserves
    # exact mixed-content order even when its own text is discontiguous.
    covered = [s.source_span for s in doc.subjects]
    for n in nodes:
        if ''.join(n.own_text).strip() and not any(a <= n.start and n.end <= b for a, b in covered):
            unclassified.append(make('UNCLASSIFIED', owner(n.start, n.end),
                                     ''.join(n.own_text).strip(), ((n.start, n.end),)))

    # Smallest relevant textual element avoids duplicating whole document text.
    source_ids = {s.source_span: s.subject_id for s in doc.subjects}
    for n in nodes:
        if n.tag not in ('P', 'TD', 'TH', 'TE', 'TU', 'PERIODSTART', 'PERIODEND', 'DOCUMENT-NAME', 'COMPANY-NAME'):
            continue
        kinds = []
        if '단위' in n.text:
            kinds.append('UNIT')
            diagnostics.append('UNKNOWN:unit_interpretation')
        if n.tag in ('PERIODSTART', 'PERIODEND') or re.search(r'당기|전기|3\s*개월|누적|\d{4}[-./]\d{1,2}', n.text):
            kinds.append('PERIOD')
            diagnostics.append('UNKNOWN:period_extent')
        if n.tag == 'DOCUMENT-NAME':
            kinds.append('SCOPE')
        if n.tag == 'COMPANY-NAME':
            kinds.append('IDENTITY')
        for kind in kinds:
            span = (n.start, n.end)
            clues.append(DsdClue(sid('clue', (kind, span)), kind, n.text, span, source_ids.get(span)))
    count = sum(len(t.cells) for t in doc.tables)
    return DsdStructuredDocument(doc, logical_uri, projection, tuple(structures), tuple(sections),
                                 tuple(notes), tuple(unclassified), tuple(clues), tuple(cell_owners),
                                 StructureCoverage(count, len(cell_owners), len(unclassified)),
                                 tuple(dict.fromkeys(diagnostics)))
