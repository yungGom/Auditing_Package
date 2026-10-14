"""Bounded, offline DSD topology. Observations never assert report context or mapping.

Spans are character offsets in raw_xml, including opening/closing tags. Raw ZIP and
XML hashes retain provenance. Supported tables are rectangular row-major grids;
continuation/transposition semantics remain explicitly unknown.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from bisect import bisect_right
import hashlib
import io
import re
import stat
import zipfile
from xml.parsers import expat
from .model import stable_id


class DsdParseError(ValueError):
    pass


@dataclass(frozen=True)
class DsdReportContext:
    entity_scheme: str | None = None
    entity_identifier: str | None = None
    scope: str | None = None
    period_start: str | None = None
    period_end: str | None = None

    def __post_init__(self):
        for value in (self.period_start, self.period_end):
            if value is not None:
                try:
                    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                        raise ValueError('ISO date required')
                    date.fromisoformat(value)
                except (ValueError, TypeError) as e:
                    raise DsdParseError('Invalid report date') from e
        if self.period_start and self.period_end and self.period_start > self.period_end:
            raise DsdParseError('Reversed report period')
        if self.scope not in (None, 'CONNECTED', 'SEPARATE', 'SOURCE_COVERED', 'FULL_COMPANY'):
            raise DsdParseError('Unsupported report scope')


@dataclass(frozen=True)
class DsdMetadata:
    requested: DsdReportContext
    observed: DsdReportContext


@dataclass(frozen=True)
class DsdSubject:
    subject_id: str
    text: str
    kind: str
    source_span: tuple[int, int]
    table_id: str | None = None
    row: int | None = None
    column: int | None = None
    row_headers: tuple[str, ...] = ()
    column_headers: tuple[str, ...] = ()
    period_role: str = 'UNKNOWN'
    value_state: str = 'TEXT'
    unit: str | None = None
    scale: str | None = None
    table_title: str = ''


@dataclass(frozen=True)
class DsdCell:
    subject_id: str
    row: int
    column: int
    rowspan: int
    colspan: int
    text: str
    source_span: tuple[int, int]
    attrs: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class DsdTable:
    table_id: str
    title: str
    source_span: tuple[int, int]
    cells: tuple[DsdCell, ...]
    row_count: int
    column_count: int


@dataclass(frozen=True)
class DsdCoverage:
    element_count: int
    subject_count: int
    unclassified_text_nodes: int


@dataclass(frozen=True)
class DsdDocument:
    source_sha256: str
    snapshot_id: str
    document_id: str
    raw_xml: str
    xml_sha256: str
    metadata: DsdMetadata
    diagnostics: tuple[str, ...]
    subjects: tuple[DsdSubject, ...]
    tables: tuple[DsdTable, ...]
    blocks: tuple[DsdSubject, ...]
    coverage: DsdCoverage
    source_role: str = 'CURRENT_DSD'


@dataclass(eq=False)
class _Node:
    tag: str
    attrs: dict
    start: int
    open_end: int
    end: int = 0
    parent: _Node | None = None
    children: list = field(default_factory=list)
    chunks: list = field(default_factory=list)
    own_text: list = field(default_factory=list)

    @property
    def text(self):
        return ''.join(self.chunks).strip()


def _read_zip(data, limit):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise DsdParseError('Positive integer byte limit required')
    if not isinstance(data, bytes) or len(data) > limit:
        raise DsdParseError('DSD bytes exceed limit or invalid input type')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
            if len(infos) > 2048 or sum(i.file_size for i in infos) > limit:
                raise DsdParseError('ZIP expanded size/member limit exceeded')
            names = set()
            for i in infos:
                name = i.filename.replace('\\', '/')
                if (name.startswith('/') or ':' in name or '..' in name.split('/')
                        or name.casefold() in names or stat.S_ISLNK(i.external_attr >> 16)
                        or i.flag_bits & 1):
                    raise DsdParseError('Unsafe/duplicate/encrypted ZIP member')
                names.add(name.casefold())
                if i.file_size > 0 and i.file_size / max(i.compress_size, 1) > 200:
                    raise DsdParseError('ZIP compression ratio limit exceeded')
            candidates = [i for i in infos if i.filename.lower() == 'contents.xml']
            if len(candidates) != 1:
                raise DsdParseError('Exactly one root contents.xml required')
            return z.read(candidates[0])
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as e:
        raise DsdParseError('Invalid DSD ZIP') from e


def _nodes(raw):
    # Only the observed DART carriage-return entity is explicitly supported.
    # Reject DTD declarations before parsing; never enable entity resolution.
    if re.search(r'<!\s*(DOCTYPE|ENTITY)\b', raw, re.I):
        raise DsdParseError('DTD/entity declarations prohibited')
    replacement_ends = []
    def safe_entity(match):
        if match[0] != '&cr;':
            return match[0]
        replacement_ends.append(match.start() + len(replacement_ends) + 5)
        return '&#13;'
    sanitized = re.sub(r'<!--[\s\S]*?-->|<!\[CDATA\[[\s\S]*?\]\]>|<\?[\s\S]*?\?>|&cr;', safe_entity, raw)
    # Declaration rewriting changes offsets, so parse Unicode with no declaration.
    # Preserve declaration length using spaces.
    # Validate the declaration before preserving its length with spaces. Expat
    # must not lose malformed/unsupported declaration evidence in this rewrite.
    declaration = re.match(r'\ufeff?(<\?xml(?=\s).*?\?>)', raw, flags=re.S)
    if declaration:
        if not re.fullmatch(
                    r'''<\?xml\s+version\s*=\s*(["'])1\.0\1(?:\s+encoding\s*=\s*(["'])[A-Za-z][A-Za-z0-9._-]*\2)?(?:\s+standalone\s*=\s*(["'])(?:yes|no)\3)?\s*\?>''',
                    declaration[1]):
            raise DsdParseError('Malformed or unsupported XML declaration')
        lo, hi = declaration.span(1)
        sanitized = sanitized[:lo] + ' ' * (hi-lo) + sanitized[hi:]
    # Expat validates misplaced/incomplete declarations. Literal declaration
    # text in comments/CDATA and ordinary processing instructions stay intact.
    encoded = sanitized.encode('utf-8')
    parser = expat.ParserCreate()
    nodes, stack = [], []
    last_byte = last_char = 0
    def offset():
        nonlocal last_byte, last_char
        here = parser.CurrentByteIndex
        last_char += len(encoded[last_byte:here].decode('utf-8'))
        last_byte = here
        return last_char
    def start(tag, attrs):
        pos = offset()
        end = re.match(r'<(?:[^>\"\']|\"[^\"]*\"|\'[^\']*\')*>', sanitized[pos:])
        if end is None:
            raise DsdParseError('Malformed opening tag')
        n = _Node(tag.upper(), {k.upper(): v for k, v in attrs.items()}, pos, pos + end.end(), parent=stack[-1] if stack else None)
        if len(stack) >= 64 or len(nodes) >= 20000:
            raise DsdParseError('XML depth/node limit exceeded')
        if stack:
            stack[-1].children.append(n)
        nodes.append(n)
        stack.append(n)
    def finish(tag):
        n = stack.pop()
        n.end = n.open_end if sanitized[n.start:n.open_end].rstrip().endswith('/>') else sanitized.find('>', offset()) + 1
    def chars(value):
        for n in stack:
            n.chunks.append(value)
        if stack:
            stack[-1].own_text.append(value)
    parser.StartElementHandler, parser.EndElementHandler, parser.CharacterDataHandler = start, finish, chars
    try:
        parser.Parse(encoded, True)
    except expat.ExpatError as e:
        raise DsdParseError('Malformed XML') from e
    # Expat offsets refer to the transformed UTF-8 buffer. Convert its character
    # boundaries back to the untouched original, accounting for each 4 -> 5
    # character entity expansion. No element boundary lies inside an entity.
    for n in nodes:
        n.start -= bisect_right(replacement_ends, n.start)
        n.open_end -= bisect_right(replacement_ends, n.open_end)
        n.end -= bisect_right(replacement_ends, n.end)
    return nodes


def parse_dsd(data: bytes, *, report: DsdReportContext | None = None,
              max_uncompressed_bytes: int = 16 * 1024 * 1024) -> DsdDocument:
    xml = _read_zip(data, max_uncompressed_bytes)
    declaration = re.match(br'\s*<\?xml[^>]*encoding=[\"\']([^\"\']+)', xml)
    try:
        encoding = declaration[1].decode('ascii').lower() if declaration else 'utf-8-sig'
    except UnicodeError as e:
        raise DsdParseError('Invalid XML encoding declaration') from e
    if encoding not in ('utf-8', 'utf-8-sig', 'euc-kr', 'cp949'):
        raise DsdParseError('Unsupported XML encoding')
    try:
        raw = xml.decode(encoding)
    except UnicodeError as e:
        raise DsdParseError('Invalid XML encoding') from e
    nodes = _nodes(raw)
    if sum(n.tag == 'TABLE' for n in nodes) > 512:
        raise DsdParseError('Table count limit exceeded')
    digest = hashlib.sha256(data).hexdigest()
    snapshot = stable_id('dsd-source', digest)
    document = stable_id('dsd-document', (snapshot, 'bounded-dsd-v2'))
    diagnostics, subjects, blocks, tables = [], [], [], []
    requested = report or DsdReportContext()
    evidence = {name: set() for name in DsdReportContext.__dataclass_fields__}
    for n in nodes:
        if n.tag == 'COMPANY-NAME' and n.attrs.get('AREGCIK'):
            evidence['entity_identifier'].add(n.attrs['AREGCIK'])
            evidence['entity_scheme'].add('DART:AREGCIK')
        if n.tag in ('PERIODSTART', 'PERIODEND'):
            key = 'period_start' if n.tag == 'PERIODSTART' else 'period_end'
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', n.text):
                    raise ValueError('Invalid date')
                date.fromisoformat(n.text)
            except ValueError as e:
                raise DsdParseError('Invalid observed report date') from e
            evidence[key].add(n.text)
        if n.tag == 'DOCUMENT-NAME':
            if '연결' in n.text:
                evidence['scope'].add('CONNECTED')
            if '별도' in n.text or '개별' in n.text:
                evidence['scope'].add('SEPARATE')
    observed = {}
    for key, values in evidence.items():
        observed[key] = next(iter(values)) if len(values) == 1 else None
        if not values:
            diagnostics.append('UNKNOWN:' + key)
        elif len(values) > 1 or (getattr(requested, key) is not None and getattr(requested, key) != observed[key]):
            diagnostics.append('CONFLICT:' + key)
    metadata = DsdMetadata(requested, DsdReportContext(**observed))
    def ancestors(n):
        p = n.parent
        while p:
            yield p
            p = p.parent
    def subject(n, **kwargs):
        nil = any(k.split(':')[-1] == 'NIL' and v.lower() in ('true', '1') for k, v in n.attrs.items())
        state = 'NIL' if nil else ('BLANK' if not n.text else 'TEXT')
        if nil and n.text:
            diagnostics.append('CONFLICT:nil_with_text:' + str(n.start))
        s = DsdSubject(stable_id('dsd-subject', (document, n.start, n.end, n.tag)), n.text, n.tag, (n.start, n.end), value_state=state, **kwargs)
        subjects.append(s)
        return s
    title = ''
    for n in nodes:
        if n.tag == 'TABLE':
            if any(p.tag == 'TABLE' for p in ancestors(n)):
                raise DsdParseError('Nested tables unsupported')
            tid = stable_id('dsd-table', (document, n.start))
            rows = [r for r in nodes if r.tag == 'TR' and n in list(ancestors(r))]
            owned = [c for c in nodes if c.tag in ('TD', 'TH', 'TE', 'TU') and n in list(ancestors(c))]
            if any(c.parent not in rows for c in owned):
                raise DsdParseError('Unsupported cells outside table rows')
            occupied, cells, placed = {}, [], []
            for r, row in enumerate(rows):
                col = 0
                for c in row.children:
                    if c.tag not in ('TD', 'TH', 'TE', 'TU'):
                        raise DsdParseError('Unsupported row child')
                    while (r, col) in occupied:
                        col += 1
                    try:
                        rs, cs = int(c.attrs.get('ROWSPAN', '1')), int(c.attrs.get('COLSPAN', '1'))
                    except ValueError as e:
                        raise DsdParseError('Malformed cell span') from e
                    if not (1 <= rs <= len(rows) - r and 1 <= cs <= 256) or col + cs > 256:
                        raise DsdParseError('Unsupported/out-of-range merged cell span')
                    if len(occupied) + rs * cs > 100000:
                        raise DsdParseError('Table grid size limit exceeded')
                    for rr in range(r, r + rs):
                        for cc in range(col, col + cs):
                            if (rr, cc) in occupied:
                                raise DsdParseError('Overlapping merged cells')
                            occupied[rr, cc] = c
                    placed.append((c, r, col, rs, cs))
                    col += cs
            for c, r, col, rs, cs in placed:
                rowheads = tuple(p.text for p, pr, pc, prs, _ in placed if pr <= r < pr+prs and pc < col and pc == 0 and p.text)
                def period_label(text):
                    # A period word inside an account name is not a declaration.
                    hit = re.fullmatch(r'(당기|전기)(?:\s*(?:3\s*개월|누적))?', text)
                    return hit[1] if hit else None
                heads = tuple(p.text for p, pr, pc, _, pcs in placed if pr < r and pc <= col < pc + pcs and (p.tag == 'TH' or period_label(p.text)))
                current, prior = any(period_label(h) == '당기' for h in heads), any(period_label(h) == '전기' for h in heads)
                role = 'CURRENT' if current and not prior else ('PRIOR' if prior and not current else 'UNKNOWN')
                s = subject(c, table_id=tid, row=r, column=col, row_headers=rowheads, column_headers=heads, period_role=role, table_title=title)
                cells.append(DsdCell(s.subject_id, r, col, rs, cs, c.text, s.source_span, tuple(sorted(c.attrs.items()))))
            width = max((col + 1 for _, col in occupied), default=0)
            if len(occupied) != len(rows) * width:
                diagnostics.append('UNKNOWN:ragged_table:' + tid)
            diagnostics.append('UNKNOWN:continuation_transposition_semantics:' + tid)
            tables.append(DsdTable(tid, title, (n.start, n.end), tuple(cells), len(rows), width))
        elif n.tag in ('P', 'TITLE') and not any(p.tag in ('TABLE', 'P', 'TITLE') for p in ancestors(n)):
            if n.tag == 'TITLE':
                title = n.text
            blocks.append(subject(n))
    covered = {s.source_span for s in subjects}
    unclassified = 0
    for n in nodes:
        if ''.join(n.own_text).strip() and not any(a <= n.start and n.end <= b for a, b in covered):
            unclassified += 1
            diagnostics.append('UNCLASSIFIED_TEXT:' + str(n.start))
    return DsdDocument(digest, snapshot, document, raw, hashlib.sha256(xml).hexdigest(), metadata,
                       tuple(diagnostics), tuple(subjects), tuple(tables), tuple(blocks),
                       DsdCoverage(len(nodes), len(subjects), unclassified))
