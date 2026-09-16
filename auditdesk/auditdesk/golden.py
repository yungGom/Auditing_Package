"""Current-first Golden output. Explicit source bindings; no inferred XBRL IDs.

The workbook model preserves stored text and layout. Reading an exported Golden
workbook is useful for writer verification, not proof of DSD-to-XBRL mapping.
"""
import copy
from decimal import Decimal, InvalidOperation
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import zipfile

import xlrd
import xlwt

TAXONOMY_HEADER = ['구분', 'Prefix', 'Name', 'Label(KO)', 'Label(EN)',
                   'Label Role', 'DataType', 'Balance', 'Period', 'Decimal', 'Fact']
OLE = bytes.fromhex('d0cf11e0a1b11ae1')


def formula_count(path):
    data = path if isinstance(path, bytes) else Path(path).read_bytes()
    if not data.startswith(OLE):
        raise ValueError('실제 OLE/BIFF .xls 파일이 필요합니다')
    from xlrd.compdoc import CompDoc
    doc = CompDoc(data, logfile=io.StringIO())
    stream = doc.get_named_stream('Workbook') or doc.get_named_stream('Book')
    if stream is None:
        raise ValueError('BIFF Workbook 스트림이 없습니다')
    offset = count = 0
    while offset + 4 <= len(stream):
        opcode, length = struct.unpack_from('<HH', stream, offset)
        count += opcode == 0x0006
        offset += 4 + length
    return count


def _style(book, xf):
    f, a, b, p = book.font_list[xf.font_index], xf.alignment, xf.border, xf.background
    return {
        'font': {k: getattr(f, k) for k in ('name', 'height', 'bold', 'italic',
                 'struck_out', 'outline', 'shadow', 'colour_index', 'escapement',
                 'underline_type', 'family', 'character_set')},
        'alignment': {'horz': a.hor_align, 'vert': a.vert_align, 'dire': a.text_direction,
                      'rota': a.rotation, 'wrap': a.text_wrapped, 'shri': a.shrink_to_fit, 'inde': a.indent_level},
        'borders': {**{side: getattr(b, side+'_line_style') for side in ('left', 'right', 'top', 'bottom', 'diag')},
                    **{side+'_colour': getattr(b, side+'_colour_index') for side in ('left', 'right', 'top', 'bottom', 'diag')},
                    'need_diag1': b.diag_down, 'need_diag2': b.diag_up},
        'pattern': {'pattern': p.fill_pattern, 'pattern_fore_colour': p.pattern_colour_index,
                    'pattern_back_colour': p.background_colour_index},
        'protection': {'cell_locked': xf.protection.cell_locked, 'formula_hidden': xf.protection.formula_hidden},
        'number_format': book.format_map[xf.format_key].format_str,
    }


def read_xls(path):
    data = path if isinstance(path, bytes) else Path(path).read_bytes()
    if formula_count(data):
        raise ValueError('Golden 입력에 수식이 있습니다; 저장 결과값 원천이 필요합니다')
    w = xlrd.open_workbook(file_contents=data, formatting_info=True, logfile=io.StringIO())
    if w.biff_version != 80:
        raise ValueError('BIFF8 .xls만 지원합니다')
    out = {'styles': [_style(w, x) for x in w.xf_list],
           'palette': {k: v for k, v in w.colour_map.items() if v is not None}, 'sheets': []}
    for s in w.sheets():
        cells = []
        for r in range(s.nrows):
            for c in range(s.ncols):
                v = s.cell(r, c)
                if v.ctype == 0:
                    continue
                if v.ctype not in (1, 6):
                    raise ValueError(f'{s.name}!R{r+1}C{c+1}: 문자열/BLANK 외 유형은 Golden 입력에서 지원하지 않습니다')
                cells.append([r, c, v.ctype, None if v.ctype == 6 else v.value, v.xf_index])
        rows, columns = [], []
        for r in range(s.nrows):
            info = s.rowinfo_map.get(r)
            rows.append({'height': info.height if info else s.default_row_height,
                         'hidden': info.hidden if info else 0,
                         'level': info.outline_level if info else 0})
        for c in range(s.ncols):
            info = s.colinfo_map.get(c)
            columns.append({'width': info.width if info else (s.defcolwidth or 8)*256,
                            'hidden': info.hidden if info else 0,
                            'level': info.outline_level if info else 0})
        if s.panes_are_frozen:
            raise ValueError('Golden 입력의 틀 고정은 지원하지 않습니다')
        out['sheets'].append({'name': s.name, 'nrows': s.nrows, 'ncols': s.ncols,
            'cells': cells, 'rows': rows, 'columns': columns,
            'merged': [list(m) for m in s.merged_cells],
            'visible': s.visibility, 'grid': s.show_grid_lines})
    w.release_resources()
    return out


def _xlstyle(data):
    result = xlwt.XFStyle()
    aliases = {'underline_type': 'underline', 'character_set': 'charset'}
    for section in ('font', 'alignment', 'borders', 'pattern', 'protection'):
        for key, value in data[section].items():
            setattr(getattr(result, section), aliases.get(key, key), value)
    result.num_format_str = data['number_format']
    return result


def _encode(model):
    w = xlwt.Workbook(encoding='utf-8', style_compression=2)
    for index, rgb in model['palette'].items():
        if 8 <= int(index) <= 63:
            w.set_colour_RGB(int(index), *rgb)
    styles = [_xlstyle(s) for s in model['styles']]
    for data in model['sheets']:
        s = w.add_sheet(data['name'])
        s.visibility, s.show_grid = data['visible'], data['grid']
        for r, row in enumerate(data['rows']):
            for k, v in row.items():
                setattr(s.row(r), k, v)
        for c, col in enumerate(data['columns']):
            for k, v in col.items():
                setattr(s.col(c), k, v)
        for r, c, typ, value, style in data['cells']:
            if typ == 1 and isinstance(value, str):
                # Row.set_cell_text preserves empty STRING, unlike write('').
                s.row(r).set_cell_text(c, value, styles[style])
            elif typ == 6 and value is None:
                s.row(r).set_cell_blank(c, styles[style])
            else:
                raise ValueError('Golden 셀은 문자열 또는 명시적 BLANK여야 합니다')
        # Append records without write_merge replacing covered blank-cell styles.
        for r0, r1, c0, c1 in data['merged']:
            for r, c, typ, value, _ in data['cells']:
                if r0 <= r < r1 and c0 <= c < c1 and (r, c) != (r0, c0) and value not in (None, ''):
                    raise ValueError('병합의 비앵커 셀에 값이 있습니다')
            s.merged_ranges.append((r0, r1-1, c0, c1-1))
    stream = io.BytesIO(); w.save(stream)
    return stream.getvalue()


def write_xls(model, path):
    path = Path(path)
    if path.suffix.lower() != '.xls':
        raise ValueError('출력 확장자는 .xls여야 합니다')
    data = _encode(model)
    try:
        with path.open('xb') as f:
            f.write(data)
    except FileExistsError:
        raise ValueError('출력 파일이 존재합니다; 새 경로를 사용하세요') from None


def semantic_snapshot(model):
    """Meaningful stored styles, not palette/style index identity."""
    palette = {int(k): tuple(v) for k, v in model['palette'].items()}
    styles = copy.deepcopy(model['styles'])
    for s in styles:
        f = s['font']; f['colour_index'] = palette.get(f['colour_index'], (0, 0, 0))
        b = s['borders']
        for edge in ('left', 'right', 'top', 'bottom', 'diag'):
            b[edge+'_colour'] = palette.get(b[edge+'_colour'], (0, 0, 0)) if b[edge] else None
        p = s['pattern']
        for k in ('pattern_fore_colour', 'pattern_back_colour'):
            p[k] = palette.get(p[k]) if p['pattern'] else None
    sheets = copy.deepcopy(model['sheets'])
    for s in sheets:
        s['merged'] = sorted(s['merged'])
        s['cells'] = [[r, c, typ, val, styles[sty]] for r, c, typ, val, sty in s['cells']]
    return sheets


def new_workbook(sheets):
    """Small explicit layout constructor, also useful for integration fixtures."""
    style = {'font': {'name': '굴림', 'height': 180, 'bold': 0, 'italic': 0,
        'struck_out': 0, 'outline': 0, 'shadow': 0, 'colour_index': 0,
        'escapement': 0, 'underline_type': 0, 'family': 0, 'character_set': 129},
        'alignment': {'horz': 0, 'vert': 2, 'dire': 0, 'rota': 0, 'wrap': 1, 'shri': 0, 'inde': 0},
        'borders': {**{s: 0 for s in ('left', 'right', 'top', 'bottom', 'diag')},
            **{s+'_colour': 0 for s in ('left', 'right', 'top', 'bottom', 'diag')}, 'need_diag1': 0, 'need_diag2': 0},
        'pattern': {'pattern': 0, 'pattern_fore_colour': 64, 'pattern_back_colour': 65},
        'protection': {'cell_locked': 1, 'formula_hidden': 0}, 'number_format': 'General'}
    model = {'styles': [style], 'palette': {0: (0, 0, 0)}, 'sheets': []}
    for name, cells in sheets:
        nr, nc = max(r for r, c, v in cells)+1, max(c for r, c, v in cells)+1
        model['sheets'].append({'name': name, 'nrows': nr, 'ncols': nc,
            'cells': [[r, c, 6 if v is None else 1, v, 0] for r, c, v in sorted(cells)],
            'rows': [{'height': 255, 'hidden': 0, 'level': 0} for _ in range(nr)],
            'columns': [{'width': 5674, 'hidden': 0, 'level': 0} for _ in range(nc)],
            'merged': [], 'visible': 0, 'grid': 1})
    return model


def _text(raw):
    from dsd_tool.textutil import unescape_entities
    return unescape_entities(re.sub('<[^>]*>', '', raw)).replace('&cr;', '\n')


def build_current(dsd, taxonomy, layout, manifest, out_dir):
    """Bind explicit current DSD cells to current taxonomy occurrences/layout.

    Static cells must be individually declared, never silently inherited. The
    manifest is a reviewed current mapping, not an automatic label-based join.
    It supplies semantic context, never reconstructed XML contextId/unitRef.
    """
    blobs = {key: Path(path).read_bytes() for key, path in
             [('dsd', dsd), ('taxonomy', taxonomy), ('layout', layout)]}
    for key, blob in blobs.items():
        if hashlib.sha256(blob).hexdigest() != manifest.get(key+'_sha256'):
            raise ValueError(f'{key} 원천이 변경되었습니다; 당기 연결을 재검토하세요')
    report = manifest['report']
    if not all(report.get(k) for k in ('company', 'scope', 'period_end', 'fiscal_number')):
        raise ValueError('당기 회사/연결·별도/기간/기수 정보가 필요합니다')
    date.fromisoformat(report['period_end'])
    if report['scope'] not in ('separate', 'consolidated'):
        raise ValueError('보고 범위는 separate 또는 consolidated여야 합니다')
    tax, excel = read_xls(blobs['taxonomy']), read_xls(blobs['layout'])
    for sheet in tax['sheets']:
        if sheet['merged']:
            raise ValueError('taxonomy에는 병합이 없어야 합니다')
    ts = {s['name']: {(r+1, c+1): v for r, c, t, v, st in s['cells']} for s in tax['sheets']}
    for sheet, cells in ts.items():
        if cells.get((1, 1)) != 'Role URI' or cells.get((2, 1)) != 'Role Definition':
            raise ValueError(f'{sheet}: taxonomy Role 원문이 필요합니다')
        for (r, c), value in cells.items():
            if c == 1 and value in ('TABLE', 'DOMAIN', 'LINEITEM') and cells.get((r, 11)) not in (None, ''):
                raise ValueError(f'{sheet}: taxonomy Fact 열은 비어 있어야 합니다')
    targets = {(s['name'], r+1, c+1): cell for s in excel['sheets']
               for cell in s['cells'] for r, c, t, v, st in [cell] if t == 1}
    with zipfile.ZipFile(io.BytesIO(blobs['dsd'])) as z:
        contents = z.read('contents.xml').decode('utf-8-sig')
    from dsd_tool.scanner import scan
    doc = scan(contents)
    source_cells = {(c.start, c.end): c.raw for t in doc.tables for c in t.all_cells()}
    assigned = set(); result_bindings = []
    for b in manifest.get('bindings', []):
        key = (b['sheet'], b['row'], b['column'])
        if key not in targets or key in assigned:
            raise ValueError('중복 또는 없는 출력 셀 연결입니다')
        occurrence = ts.get(b['taxonomy_sheet'], {}); row = b['taxonomy_row']
        if (occurrence.get((1, 2)) != b['role'] or occurrence.get((row, 2)) != b['prefix']
                or occurrence.get((row, 3)) != b['name']):
            raise ValueError('현재 taxonomy의 Role/Prefix/Name 출현과 연결이 다릅니다')
        if occurrence.get((row, 1)) != 'LINEITEM':
            raise ValueError('값 연결 대상은 확인된 LINEITEM 출현이어야 합니다')
        declared_type = str(occurrence.get((row, 7), '')).split(':')[-1]
        expected_type = {'text': ('stringItemType', 'textBlockItemType'),
                         'date': ('dateItemType',), 'duration': ('durationItemType',)}.get(
                             b['data_type'], (b['data_type']+'ItemType',))
        if declared_type not in expected_type:
            raise ValueError('현재 taxonomy의 자료형과 연결 유형이 다릅니다')
        ctx = b['context']
        instant = occurrence.get((row, 9)) == 'INSTANT'
        if occurrence.get((row, 9)) not in ('INSTANT', 'DURATION') or instant != bool(ctx.get('instant')):
            raise ValueError('현재 taxonomy의 기간 속성과 문맥이 다릅니다')
        if (ctx.get('company') != report['company'] or ctx.get('scope') != report['scope']
                or not ctx.get('unit') or not isinstance(ctx.get('dimensions'), list)
                or not b.get('source_evidence')):
            raise ValueError('현재 회사/범위/단위/차원 및 연결 근거가 필요합니다')
        period_end = ctx.get('instant') or ctx.get('end')
        allowed = {report['period_end'], *report.get('comparison_ends', [])}
        if period_end not in allowed or (not ctx.get('instant') and not ctx.get('start')):
            raise ValueError('현재 보고기간 또는 명시한 비교기간이 아닙니다')
        if date.fromisoformat(period_end) > date.fromisoformat(report['period_end']):
            raise ValueError('비교기간이 현재 보고기간보다 미래입니다')
        if not instant and date.fromisoformat(ctx['start']) > date.fromisoformat(ctx['end']):
            raise ValueError('기간 시작일이 종료일보다 늦습니다')
        raw = source_cells.get((b['source_start'], b['source_end']))
        if raw is None:
            raise ValueError('현재 DSD에 정확히 대응하는 셀 위치가 없습니다')
        display = _text(raw)
        raw_value = display
        if b['data_type'] in ('monetary', 'shares', 'perShare', 'percent', 'pure'):
            literal = display.strip()
            if not re.fullmatch(r'(?:-?\d+(?:,\d{3})*(?:\.\d+)?|\(\d+(?:,\d{3})*(?:\.\d+)?\))', literal):
                raise ValueError('숫자 유형과 DSD 표시값이 다릅니다')
            numeric = literal.replace(',', '')
            if numeric.startswith('(') and numeric.endswith(')'):
                numeric = '-'+numeric[1:-1]
            try:
                number = Decimal(numeric)
                if not number.is_finite():
                    raise InvalidOperation
                raw_value = str(number)
            except InvalidOperation:
                raise ValueError('숫자 유형과 DSD 표시값이 다릅니다') from None
        elif b['data_type'] not in ('text', 'date', 'duration'):
            raise ValueError('지원하지 않는 값 유형입니다')
        targets[key][3] = display
        result_bindings.append({**b, 'raw_value': raw_value, 'display_text': display})
        assigned.add(key)
    for b in manifest.get('static_cells', []):
        key = (b['sheet'], b['row'], b['column'])
        if key not in targets or key in assigned or not b.get('source_evidence'):
            raise ValueError('중복/누락된 정적 셀 또는 근거입니다')
        assigned.add(key)
    missing = sorted(set(targets)-assigned)
    if missing:
        raise ValueError(f'현재 값/정적 표시 근거가 연결되지 않은 셀 {len(missing)}개: {missing[:3]}')
    # Validate/encode both before publishing either; a new directory is required.
    payloads = {'taxonomy.xls': _encode(tax), 'Excel.xls': _encode(excel)}
    out = Path(out_dir)
    result = {'complete': True, 'report': report, 'bindings': result_bindings,
              'taxonomy': str(out/'taxonomy.xls'), 'excel': str(out/'Excel.xls'),
              'validation_scope': 'explicit current bindings; editor compatibility not tested'}
    out.mkdir(parents=False, exist_ok=False)
    for name, payload in payloads.items():
        (out/name).write_bytes(payload)
    (out/'review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
