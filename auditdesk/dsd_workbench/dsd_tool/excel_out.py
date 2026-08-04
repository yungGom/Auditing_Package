"""DSD → Excel 추출 (시트 구성: 스펙 3.2 / 7.5).

사용안내 | 표지 | FS(BS/PL/PL1/CE/CF, 접두사 반영) | 1..N(주석) | 외부감사 | _MAP | _META
"""
import hashlib
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import __version__
from .scanner import honesty_stats, scan
from .textutil import dedup_note_number, is_cr_only_cell, try_number
from .zipsplice import read_contents

MAP_SHEET = "_MAP"
META_SHEET = "_META"
MAP_HEADER = ["sheet", "row", "col", "xml_start", "xml_end", "orig_raw"]
ORIG_RAW_LIMIT = 200  # 스펙 3.3

_GRAY = Font(color="808080")
_BOLD = Font(bold=True)
_TITLE_FONT = Font(bold=True, size=13)
_WRAP = Alignment(wrap_text=True, vertical="top")
_THIN_SIDE = Side(style="thin")
_THIN_BORDER = Border(left=_THIN_SIDE, right=_THIN_SIDE,
                      top=_THIN_SIDE, bottom=_THIN_SIDE)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

GUIDE_LINES = [
    "DSD ↔ Excel 변환 도구 사용안내",
    "",
    "1. 이 파일은 DSD(전자공시 문서)에서 추출된 것입니다.",
    "   값을 수정한 뒤 repack 하면 수정된 셀만 DSD에 반영됩니다.",
    "2. 검은색 셀만 수정 가능합니다. 회색 글씨는 참조용(수정 불가)입니다.",
    "3. 행/열을 추가·삭제하거나 시트명을 바꾸지 마세요. 위치 기반으로 역변환됩니다.",
    "4. 숫자는 원본 표기 스타일(콤마, 괄호 음수)대로 자동 변환됩니다.",
    "   \"3,4,5,6\" 같은 주석 참조는 텍스트로 유지됩니다.",
    "5. 빈 셀에 새 값을 입력하면 해당 위치에 삽입됩니다.",
    "6. 단위 스케일 변환은 하지 않습니다. 표시된 그대로 수정하세요.",
    "7. _MAP / _META 시트(숨김)는 절대 수정하지 마세요.",
    "",
    "역변환: python -m dsd_tool repack <이파일.xlsx> <원본.dsd>",
    "출력: {원본명}_수정.dsd (원본은 덮어쓰지 않습니다)",
]


GUIDE_LINES_VIEWONLY = [
    "DSD 수신문서 열람용 변환본 사용안내",
    "",
    "1. 이 파일은 OpenDART 공시 원본(수신물)에서 변환된 열람·분석용입니다.",
    "2. 이 파일로는 수정·역변환(DSD 반영)을 하지 않습니다 —",
    "   편집·변환은 회사 보유 DSD(편집기 계열)로 하세요.",
    "3. 수신문서는 주석 분할이 부정확할 수 있습니다 — 뭉침·미분할",
    "   안내가 있는 시트는 아래 목록과 각 시트 상단 배너를 확인하세요.",
    "4. 숫자·표는 원본 표기 그대로입니다 (단위 변환 없음).",
]


def _safe(text: str):
    return _CTRL_RE.sub("", text) if isinstance(text, str) else text


class _SheetWriter:
    """시트에 셀을 쓰면서 _MAP 행을 축적한다."""

    def __init__(self, wb: Workbook, title: str, map_rows: list):
        self.ws = wb.create_sheet(title=title)
        self.map_rows = map_rows

    def put_mapped(self, row: int, col: int, cell, display: str = None):
        """스캔된 Cell(오프셋 보유)을 수정 가능 셀로 기록.

        display: 엑셀에 기록할 표시값 오버라이드. _MAP의 orig_raw는 항상
        원본 그대로 유지되므로, 표시값이 원본과 다르면 repack 시 자동으로
        그 차이가 DSD에 반영된다 (주석 번호 중복 정리에 사용).
        """
        text = cell.text if display is None else display
        target = self.ws.cell(row=row, column=col)
        num = try_number(text)
        if num is not None:
            target.value = int(num) if num == int(num) else num
            stripped = text.strip()
            if "," in stripped:
                target.number_format = (
                    "#,##0;(#,##0)" if stripped.startswith("(") else "#,##0")
        else:
            target.value = _safe(text)
            if "\n" in text:
                target.alignment = _WRAP
        self.map_rows.append([
            self.ws.title, row, col,
            cell.start, cell.end, _safe(cell.raw[:ORIG_RAW_LIMIT]),
        ])
        return target

    def put_readonly(self, row: int, col: int, text: str, font=_GRAY):
        target = self.ws.cell(row=row, column=col)
        target.value = _safe(text)
        target.font = font
        if isinstance(text, str) and "\n" in text:
            target.alignment = _WRAP
        return target

    def put_table(self, start_row: int, table, col_offset: int = 0,
                  border: bool = False) -> int:
        """테이블을 grid 좌표대로 배치. 다음 빈 행 번호를 반환.

        border=True 면 테이블 영역 셀 전체에 thin 테두리를 적용한다
        (병합 범위 포함). 서술문/제목 행은 put_table 을 타지 않으므로 제외됨.
        """
        grid = table.grid()
        if not grid:
            return start_row
        max_r = 0
        for (r, c), cell in sorted(grid.items()):
            row, col = start_row + r, 1 + col_offset + c
            self.put_mapped(row, col, cell)
            if cell.colspan > 1 or cell.rowspan > 1:
                self.ws.merge_cells(
                    start_row=row, start_column=col,
                    end_row=row + cell.rowspan - 1,
                    end_column=col + cell.colspan - 1)
            if border:
                for dr in range(cell.rowspan):
                    for dc in range(cell.colspan):
                        self.ws.cell(row=row + dr,
                                     column=col + dc).border = _THIN_BORDER
            max_r = max(max_r, r + cell.rowspan - 1)
        return start_row + max_r + 1


def extract(dsd_path: str, out_path: str = None,
            keep_note_numbers: bool = False) -> dict:
    """DSD → Excel. 결과 요약 dict 반환.

    keep_note_numbers=False(기본): 주석 헤더의 중복 번호("1. 1. 제목")를
    "1. 제목"으로 정리해 엑셀에 기록한다. _MAP은 원본을 유지하므로
    repack 시 DSD 헤더도 자동으로 정리된다. True면 원본 그대로 기록.
    """
    with open(dsd_path, "rb") as f:
        data = f.read()
    contents = read_contents(data)
    text = contents.decode("utf-8")
    doc = scan(text)

    wb = Workbook()
    wb.remove(wb.active)
    map_rows = []

    # --- 사용안내 (B-4: 수신물은 열람용 안내로 분기) ------------------------
    from .version import read_version_info
    ver = read_version_info(data)
    wrapped = not ver["editver"]            # meta.xml 없음 = 수신 래핑본
    hstats = honesty_stats(doc, text)       # B-5: 완전성 통계
    import datetime as _dt
    import os as _os
    src_name = dsd_path.replace("\\", "/").rsplit("/", 1)[-1]
    try:
        src_time = _dt.datetime.fromtimestamp(
            _os.path.getmtime(dsd_path)).strftime("%Y-%m-%d %H:%M")
    except OSError:
        src_time = "(확인 불가)"
    source_line = f"소스 문서: {src_name} · 수신 시각 {src_time}"
    guide_lines = list(GUIDE_LINES_VIEWONLY if wrapped else GUIDE_LINES)
    guide_lines.insert(1, source_line)      # B-5: 소스 식별 명기
    # B-5: 원문 대비 시트화 커버리지 + 미시트화 블록·흡수 의심 목록
    guide_lines.append("")
    guide_lines.append(
        f"시트화 커버리지: {hstats['coverage']:.1%} "
        f"(원문 가시 문자 {hstats['total_chars']:,}자 중 "
        f"{hstats['covered_chars']:,}자)")
    for blk in hstats["uncovered_blocks"]:
        guide_lines.append(
            f"⚠ 미시트화 블록 — 가시 {blk['chars']:,}자: "
            f"“{blk['preview']}…” (열람은 원본 문서로)")
    for name, marks in sorted(hstats["absorbed"].items()):
        guide_lines.append(
            f"⚠ {name} 시트: 성격이 다른 콘텐츠 흡수 의심 — "
            + ", ".join(marks[:4]) + (" 등" if len(marks) > 4 else ""))
    if wrapped:
        for num, extra in sorted((doc.merged_notes or {}).items()):
            guide_lines.append(
                f"⚠ 주석 {num} 시트: 주석 "
                f"{', '.join(str(x) for x in extra[:8])}"
                f"{' 등' if len(extra) > 8 else ''} 미분할 포함")
        if doc.fs_dropped:
            guide_lines.append(
                "⚠ 시트화되지 않은 재무제표 제목 감지 — '미분할 원문' 시트 참조: "
                + " / ".join(t for _p, t in doc.fs_dropped))
    guide = wb.create_sheet("사용안내")
    for i, line in enumerate(guide_lines, start=1):
        c = guide.cell(row=i, column=1, value=line)
        if i == 1:
            c.font = _TITLE_FONT
        if line.startswith("⚠"):
            c.fill = PatternFill("solid", start_color="FFEB9C")
    guide.column_dimensions["A"].width = 70

    # --- 표지 ---------------------------------------------------------------
    cover = _SheetWriter(wb, "표지", map_rows)
    r = 1
    for para in doc.cover_paragraphs:
        if not para.text and not para.is_plain:
            continue
        if para.is_plain:
            cover.put_mapped(r, 1, para)
        else:
            cover.put_readonly(r, 1, para.text)
        r += 1
    if doc.cover_cells:
        r += 1
        for cell in doc.cover_cells:
            cover.put_mapped(r, 1, cell)
            r += 1
    cover.put_readonly(r + 1, 1, source_line)   # B-5: 소스 식별 명기
    cover.ws.column_dimensions["A"].width = 60

    # --- 재무제표 시트 --------------------------------------------------------
    for block in doc.fs_blocks:
        sw = _SheetWriter(wb, block.sheet_name, map_rows)
        t = sw.put_mapped(1, 1, block.title_cell)
        t.font = _TITLE_FONT
        r = 2
        for extra in block.extra_title_cells:
            sw.put_mapped(r, 1, extra)
            r += 1
        r += 1
        for tbl in block.tables:
            r = sw.put_table(r, tbl, border=True)
            r += 1
        if wrapped and block.sheet_name in hstats["absorbed"]:
            # B-5: 이질 콘텐츠 흡수 배너 — 행 삽입 없이 우측 상단 고정
            # (행이 밀리면 위치 기반 역변환이 깨진다)
            bc = sw.put_readonly(
                1, 9, "⚠ 이 시트에 성격이 다른 콘텐츠가 흡수되었을 수 "
                      "있습니다 — 사용안내 목록 확인")
            bc.fill = PatternFill("solid", start_color="FFEB9C")
        sw.ws.column_dimensions["A"].width = 40
        for ci in range(2, 8):
            sw.ws.column_dimensions[get_column_letter(ci)].width = 16
        sw.ws.freeze_panes = "A2"

    # --- 주석 시트 ------------------------------------------------------------
    deduped_notes = 0
    for note in doc.notes:
        sw = _SheetWriter(wb, str(note.number), map_rows)
        if note.header is not None:
            header_text = note.header.text.strip()
        else:
            header_text = f"{note.number}. {note.title}"
        display = header_text if keep_note_numbers \
            else dedup_note_number(header_text)
        if display != header_text:
            deduped_notes += 1
        if note.header is not None and note.header_mappable:
            hc = sw.put_mapped(1, 1, note.header, display=display)
            hc.font = _BOLD
        else:
            sw.put_readonly(1, 1, display, font=_BOLD)
        if wrapped and doc.merged_notes \
                and note.number in doc.merged_notes:
            extra = doc.merged_notes[note.number]
            bc = sw.put_readonly(
                2, 1,
                f"⚠ 주석 {extra[0]}~ 미분할 포함 — 수신본 분할 한계, "
                "열람·분석용 (분할 기준은 회사 보유 DSD)")
            bc.fill = PatternFill("solid", start_color="FFEB9C")
        r = 3
        for _, kind, payload in note.items:
            if kind == "para":
                if payload.is_plain and payload.text:
                    sw.put_mapped(r, 1, payload)
                    r += 2
                elif payload.text:
                    sw.put_readonly(r, 1, payload.text)
                    r += 2
            elif kind == "unit":
                sw.put_mapped(r, 1, payload)  # 단위 행도 _MAP 포함 (스펙 7.5)
                r += 1
            elif kind == "table":
                r = sw.put_table(r, payload, border=True)
                r += 1
        sw.ws.column_dimensions["A"].width = 60
        for ci in range(2, 10):
            sw.ws.column_dimensions[get_column_letter(ci)].width = 15

    # --- 외부감사 --------------------------------------------------------------
    if doc.te_tables:
        sw = _SheetWriter(wb, "외부감사", map_rows)
        sw.put_readonly(1, 1, "외부감사 실시내용 (표준양식, ACODE 기반)", font=_BOLD)
        r = 3
        for tbl in doc.te_tables:
            r = sw.put_table(r, tbl)
            r += 1
        sw.ws.column_dimensions["A"].width = 45
        for ci in range(2, 10):
            sw.ws.column_dimensions[get_column_letter(ci)].width = 14

    # --- B-4: 미분할 원문 (탈락 감지 — 침묵 탈락 금지) --------------------
    if doc.fs_dropped:
        ws_d = wb.create_sheet("미분할 원문")
        ws_d.cell(1, 1, "⚠ 아래 재무제표 제목이 원문에 있으나 시트화되지"
                        " 않았습니다 (수신본 분할 한계). 원문 텍스트를"
                        " 그대로 노출합니다 — 열람용.").font = _BOLD
        ws_d.cell(1, 1).fill = PatternFill("solid", start_color="FFEB9C")
        rr = 3
        first = min(pos for pos, _t in doc.fs_dropped)
        raw = re.sub(r"<[^>]+>", "\n", text[first:])
        raw = raw.replace("&amp;cr;", " ").replace("&amp;", "&")
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        for ln in lines[:3000]:
            ws_d.cell(rr, 1, _safe(ln[:300]))
            rr += 1
        if len(lines) > 3000:
            ws_d.cell(rr, 1, f"… (이하 {len(lines) - 3000}줄 생략)")
        ws_d.column_dimensions["A"].width = 90

    # --- 원문 통합 시트 (스펙 7.5 P3 — ACCIO 장점 흡수) ------------------------
    # 전체 내용을 세로로 이어붙인 참조 전용 뷰. _MAP에는 포함하지 않는다 —
    # 편집·역변환 대상이 아니므로 여기서 값을 고쳐도 repack에 반영되지
    # 않는다(diff는 _MAP 항목만 순회). "사용안내" 다음(index 1)에 배치.
    data_sheet_names = [n for n in wb.sheetnames if n != "사용안내"]
    verbatim = wb.create_sheet("원문", 1)
    out_row = 1
    for name in data_sheet_names:
        src = wb[name]
        verbatim.cell(row=out_row, column=1,
                      value=f"[[ {name} ]]").font = _BOLD
        out_row += 1
        for row in src.iter_rows():
            for cell in row:
                if cell.value is None or cell.column > 12:
                    continue
                tgt = verbatim.cell(row=out_row + cell.row - 1,
                                    column=cell.column)
                tgt.value = cell.value
                tgt.number_format = cell.number_format
        out_row += src.max_row + 2
    verbatim.column_dimensions["A"].width = 45
    for ci in range(2, 10):
        verbatim.column_dimensions[get_column_letter(ci)].width = 16

    # --- _MAP / _META -----------------------------------------------------------
    ms = wb.create_sheet(MAP_SHEET)
    ms.append(MAP_HEADER)
    for row in map_rows:
        ms.append(row)
    ms.sheet_state = "hidden"

    # DART 편집기 버전 (meta.xml GENERATOR) — 패치 A-3
    from .version import is_known

    meta = wb.create_sheet(META_SHEET)
    meta.append(["key", "value"])
    meta.append(["tool_version", __version__])
    meta.append(["source_name", dsd_path.replace("\\", "/").rsplit("/", 1)[-1]])
    meta.append(["contents_len", len(text)])
    meta.append(["contents_sha1", hashlib.sha1(contents).hexdigest()])
    meta.append(["note_mode", doc.note_mode])
    meta.append(["coverage", f"{hstats['coverage']:.4f}"])
    meta.append(["source_time", src_time])
    meta.append(["editver", ver["editver"] or ""])
    meta.append(["docver", ver["docver"] or ""])
    meta.append(["schema", ver["schema"] or ""])
    meta.sheet_state = "hidden"

    if out_path is None:
        out_path = re.sub(r"\.dsd$", "", dsd_path, flags=re.I) + ".xlsx"
    wb.save(out_path)

    # &cr;-only 셀 집계 (repack --clean-cr 대상 미리보기용)
    cr_only_by_sheet = {}
    for row in map_rows:
        s, e = row[3], row[4]
        if is_cr_only_cell(text, s, text[s:e]):
            cr_only_by_sheet[row[0]] = cr_only_by_sheet.get(row[0], 0) + 1

    return {
        "out_path": out_path,
        "fs_sheets": [b.sheet_name for b in doc.fs_blocks],
        # H-1: FS유사 제목인데 미판별 — 침묵 탈락 금지, 그대로 노출
        "fs_unclassified": list(doc.fs_unclassified or []),
        "fs_dropped": [t for _p, t in (doc.fs_dropped or [])],
        "merged_notes": {str(k): v for k, v in
                         (doc.merged_notes or {}).items()} if wrapped
        else {},
        "viewonly": wrapped,
        # B-5: 완전성 통계 — 커버리지·미시트화 블록·흡수 의심
        "coverage": hstats["coverage"],
        "uncovered_blocks": hstats["uncovered_blocks"],
        "absorbed": dict(hstats["absorbed"]),
        "note_count": len(doc.notes),
        "note_mode": doc.note_mode,
        "te_tables": len(doc.te_tables),
        "mapped_cells": len(map_rows),
        "cr_only_cells": sum(cr_only_by_sheet.values()),
        "cr_only_by_sheet": cr_only_by_sheet,
        "deduped_notes": deduped_notes,
        "editver": ver["editver"],
        "docver": ver["docver"],
        "editver_known": is_known(ver["editver"]),
    }
