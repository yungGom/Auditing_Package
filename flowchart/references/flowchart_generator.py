"""
Flowchart 자동 생성기 — 핵심 로직
RCM + 매핑 + 헤더정보 시트가 들어있는 엑셀 파일을 읽어 PPT를 생성한다.

작성자: 회계법인 (감사인용)
실행 환경: 완전 오프라인 (외부 API/네트워크 호출 없음)

사용 라이브러리:
- openpyxl: 엑셀 읽기
- python-pptx: PPT 생성

설치:
    pip install openpyxl python-pptx
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from pptx import Presentation
from pptx.util import Cm, Pt
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn


# ─────────────────────────────────────────────────────────────
# 데이터 모델
# ─────────────────────────────────────────────────────────────

@dataclass
class HeaderInfo:
    """헤더 박스 정보 (회사명, 분류, 날짜 등)"""
    company: str = ""
    process_name: str = ""        # 대분류
    middle_category: str = ""     # 중분류
    sub_process_name: str = ""    # 소분류
    flowchart_code: str = ""
    last_change_date: str = ""
    author: str = ""


@dataclass
class RcmRow:
    """RCM 시트의 한 행 (Process Narrative 단락 단위)"""
    row_num: int                       # 엑셀 행 번호 (4부터)
    process: str = ""
    process_name: str = ""
    sub_process_no: str = ""
    sub_process_name: str = ""
    narrative: str = ""
    risk_no: str = ""
    risk_desc: str = ""
    control_no: str = ""
    control_name: str = ""
    control_desc: str = ""
    it_system: str = ""
    control_owner: str = ""
    control_org: str = ""
    key_ca: str = ""                   # Y/N
    control_type: str = ""             # Manual/Preventive 등
    raw: dict[str, Any] = field(default_factory=dict)  # 기타 모든 컬럼

    @property
    def has_control(self) -> bool:
        return bool(self.control_no.strip())

    @property
    def has_risk(self) -> bool:
        return bool(self.risk_no.strip())

    @property
    def is_key_control(self) -> bool:
        return self.key_ca.strip().upper() in ("Y", "YES", "KEY")

    @property
    def control_type_symbol(self) -> str:
        """통제유형을 M/A/I 한 글자로 변환"""
        t = (self.control_type or "").upper()
        if "AUTO" in t or t.startswith("A"):
            return "A"
        if "ITDM" in t or "ITGC" in t or "IT D" in t:
            return "I"
        return "M"  # 기본값: Manual


@dataclass
class Activity:
    """매핑 시트의 한 행 = 활동 1개"""
    act_no: int
    rcm_row: int                  # 참조할 RCM 행 번호
    act_name: str
    team_override: str = ""
    sub_steps: str = ""
    doc_names: str = ""
    branch_info: str = ""
    note: str = ""
    # JOIN 후 채워짐
    rcm: RcmRow | None = None

    @property
    def team(self) -> str:
        """수행팀: TEAM_OVERRIDE가 있으면 우선, 없으면 RCM의 Control Organization"""
        if self.team_override.strip():
            return self.team_override.strip()
        if self.rcm and self.rcm.control_org.strip():
            return self.rcm.control_org.strip()
        return ""

    @property
    def location(self) -> str:
        return (self.rcm.it_system if self.rcm else "") or "Manual"

    @property
    def display_body(self) -> str:
        """활동 박스에 들어갈 본문: SUB_STEPS 우선, 없으면 narrative"""
        if self.sub_steps.strip():
            return self.sub_steps.strip()
        if self.rcm and self.rcm.narrative.strip():
            return self.rcm.narrative.strip()
        return ""

    @property
    def doc_list(self) -> list[str]:
        return [d.strip() for d in self.doc_names.split(",") if d.strip()]


# ─────────────────────────────────────────────────────────────
# 엑셀 읽기
# ─────────────────────────────────────────────────────────────

def _cell(ws, row: int, col: int) -> str:
    v = ws.cell(row=row, column=col).value
    return "" if v is None else str(v).strip()


def _find_header_row_and_cols(ws, required_keys: list[str], max_scan_rows: int = 10) -> tuple[int, dict[str, int]]:
    """
    헤더 행을 자동 탐색.
    여러 행에 헤더가 분산된 경우(2단 헤더 등)도 대응:
    required_keys가 가장 많이 매칭되는 행을 헤더로 본다.
    반환: (헤더행번호, {정규화키: 컬럼번호})
    """
    best_row = -1
    best_count = 0
    best_cols: dict[str, int] = {}

    for r in range(1, max_scan_rows + 1):
        cols_found = {}
        for c in range(1, ws.max_column + 1):
            val = _cell(ws, r, c)
            norm = _normalize_header(val)
            if norm:
                cols_found[norm] = c
        match_count = sum(1 for k in required_keys if k in cols_found)
        if match_count > best_count:
            best_count = match_count
            best_row = r
            best_cols = cols_found

    if best_count == 0:
        raise ValueError(f"헤더 행을 찾을 수 없습니다. 필수 키: {required_keys}")
    return best_row, best_cols


def _normalize_header(s: str) -> str:
    """헤더 문자열 정규화: 공백·줄바꿈·괄호 제거 후 소문자"""
    if not s:
        return ""
    s = str(s)
    for ch in [" ", "\n", "\t", "\r", "(", ")", ".", "/", "-", "_"]:
        s = s.replace(ch, "")
    return s.lower()


# RCM 컬럼명 후보 (정규화된 키 → 표시명)
RCM_COL_ALIASES = {
    # 프로세스 그룹
    "프로세스": ["프로세스", "process"],
    "프로세스이름": ["프로세스이름", "processname"],
    "하위프로세스번호": ["하위프로세스번호", "subprocessno", "subprocesscode"],
    "하위프로세스이름": ["하위프로세스이름", "subprocessname"],
    "narrative": ["processnarrative", "narrative", "프로세스내러티브"],
    # 리스크
    "위험번호": ["리스크no", "risk번호", "위험번호", "riskno", "리스크번호"],
    "위험내용": ["리스크", "위험내용", "risk", "위험"],
    # 통제활동
    "통제번호": ["통제활동번호", "통제번호", "controlno", "controlid", "ca번호"],
    "통제이름": ["통제활동이름", "통제이름", "controlname"],
    "통제설명": ["통제활동설명", "통제설명", "controldesc", "controldescription"],
    "it시스템": ["it시스템", "itsystem", "system"],
    "controlowner": ["controlowner", "통제수행자", "통제소유자"],
    "controlorg": ["controlorganization", "controlorg", "통제조직"],
    "keyca": ["keyca", "keycontrol", "핵심통제", "keyyn"],
    "통제유형": ["통제유형8가지", "통제유형", "controltype", "통제유형8"],
}


def _resolve_col(cols_found: dict[str, int], key: str) -> int | None:
    """RCM_COL_ALIASES에 따라 컬럼 번호를 찾는다."""
    for alias in RCM_COL_ALIASES.get(key, [key]):
        norm = _normalize_header(alias)
        if norm in cols_found:
            return cols_found[norm]
    return None


def read_header_info(xlsx_path: Path) -> HeaderInfo:
    """헤더정보 시트 읽기"""
    wb = load_workbook(xlsx_path, data_only=True)
    if "헤더정보" not in wb.sheetnames:
        return HeaderInfo()
    ws = wb["헤더정보"]

    info = HeaderInfo()
    key_map = {
        "회사명": "company",
        "대분류": "process_name",
        "중분류": "middle_category",
        "소분류": "sub_process_name",
        "flowchartcode": "flowchart_code",
        "lastchangedate": "last_change_date",
        "작성자": "author",
    }
    for r in range(1, ws.max_row + 1):
        k = _normalize_header(_cell(ws, r, 1))
        v = _cell(ws, r, 2)
        if k in key_map and v:
            setattr(info, key_map[k], v)
    return info


def read_rcm(xlsx_path: Path) -> dict[int, RcmRow]:
    """
    RCM 시트 읽기. {엑셀행번호: RcmRow} 반환.
    헤더는 자동 탐색 (1~10행 안에서 '프로세스' 또는 'Process Narrative' 찾기)
    """
    wb = load_workbook(xlsx_path, data_only=True)
    if "RCM" not in wb.sheetnames:
        raise ValueError("RCM 시트가 없습니다.")
    ws = wb["RCM"]

    hdr_row, cols = _find_header_row_and_cols(
        ws,
        required_keys=[
            _normalize_header("Process Narrative"),
            _normalize_header("하위 프로세스 번호"),
            _normalize_header("리스크 No."),
            _normalize_header("통제활동 번호"),
            _normalize_header("IT시스템"),
        ],
        max_scan_rows=10,
    )

    col_map = {
        "process": _resolve_col(cols, "프로세스"),
        "process_name": _resolve_col(cols, "프로세스이름"),
        "sub_process_no": _resolve_col(cols, "하위프로세스번호"),
        "sub_process_name": _resolve_col(cols, "하위프로세스이름"),
        "narrative": _resolve_col(cols, "narrative"),
        "risk_no": _resolve_col(cols, "위험번호"),
        "risk_desc": _resolve_col(cols, "위험내용"),
        "control_no": _resolve_col(cols, "통제번호"),
        "control_name": _resolve_col(cols, "통제이름"),
        "control_desc": _resolve_col(cols, "통제설명"),
        "it_system": _resolve_col(cols, "it시스템"),
        "control_owner": _resolve_col(cols, "controlowner"),
        "control_org": _resolve_col(cols, "controlorg"),
        "key_ca": _resolve_col(cols, "keyca"),
        "control_type": _resolve_col(cols, "통제유형"),
    }

    # narrative는 필수
    if col_map["narrative"] is None:
        raise ValueError("RCM 시트에서 'Process Narrative' 컬럼을 찾지 못했습니다.")

    rows: dict[int, RcmRow] = {}
    for r in range(hdr_row + 1, ws.max_row + 1):
        narr = _cell(ws, r, col_map["narrative"])
        if not narr:
            continue
        row = RcmRow(row_num=r)
        for attr, col in col_map.items():
            if col is not None:
                setattr(row, attr, _cell(ws, r, col))
        rows[r] = row
    return rows


def read_mapping(xlsx_path: Path) -> list[Activity]:
    """매핑 시트 읽기. 헤더는 자동 탐색."""
    wb = load_workbook(xlsx_path, data_only=True)
    if "매핑" not in wb.sheetnames:
        raise ValueError("매핑 시트가 없습니다.")
    ws = wb["매핑"]

    hdr_row, cols = _find_header_row_and_cols(
        ws, required_keys=[_normalize_header("ACT_NO"), _normalize_header("RCM_ROW")]
    )

    def get_col(*aliases) -> int | None:
        for a in aliases:
            n = _normalize_header(a)
            if n in cols:
                return cols[n]
        return None

    c_act_no = get_col("ACT_NO", "활동번호")
    c_rcm_row = get_col("RCM_ROW", "RCMROW", "RCM행")
    c_act_name = get_col("ACT_NAME", "활동명")
    c_team = get_col("TEAM_OVERRIDE", "TEAM", "수행팀")
    c_substeps = get_col("SUB_STEPS", "서브스텝")
    c_docs = get_col("DOC_NAMES", "문서")
    c_branch = get_col("BRANCH_INFO", "분기")
    c_note = get_col("NOTE", "비고")

    if c_act_no is None or c_rcm_row is None or c_act_name is None:
        raise ValueError("매핑 시트에 ACT_NO, RCM_ROW, ACT_NAME 컬럼이 모두 필요합니다.")

    activities: list[Activity] = []
    for r in range(hdr_row + 1, ws.max_row + 1):
        act_no_str = _cell(ws, r, c_act_no)
        if not act_no_str:
            continue
        try:
            act_no = int(float(act_no_str))
            rcm_row = int(float(_cell(ws, r, c_rcm_row)))
        except ValueError:
            continue  # 헤더 설명 행 등 스킵

        act = Activity(
            act_no=act_no,
            rcm_row=rcm_row,
            act_name=_cell(ws, r, c_act_name),
            team_override=_cell(ws, r, c_team) if c_team else "",
            sub_steps=_cell(ws, r, c_substeps) if c_substeps else "",
            doc_names=_cell(ws, r, c_docs) if c_docs else "",
            branch_info=_cell(ws, r, c_branch) if c_branch else "",
            note=_cell(ws, r, c_note) if c_note else "",
        )
        activities.append(act)

    activities.sort(key=lambda a: a.act_no)
    return activities


def load_all(xlsx_path: Path) -> tuple[HeaderInfo, list[Activity]]:
    """엑셀에서 모든 정보를 읽고 매핑 ↔ RCM JOIN까지 수행"""
    header = read_header_info(xlsx_path)
    rcm = read_rcm(xlsx_path)
    activities = read_mapping(xlsx_path)

    warnings: list[str] = []
    for act in activities:
        if act.rcm_row in rcm:
            act.rcm = rcm[act.rcm_row]
        else:
            warnings.append(f"⚠ 활동 {act.act_no} ({act.act_name}): RCM_ROW={act.rcm_row} 에 해당하는 RCM 행이 없습니다.")

    # 헤더 정보가 비어있으면 첫 활동의 RCM 행에서 자동 채움
    if activities and activities[0].rcm:
        first_rcm = activities[0].rcm
        if not header.process_name:
            header.process_name = first_rcm.process_name
        if not header.sub_process_name:
            header.sub_process_name = first_rcm.sub_process_name
        if not header.flowchart_code:
            header.flowchart_code = first_rcm.sub_process_no

    if warnings:
        print("\n".join(warnings))

    return header, activities


# ─────────────────────────────────────────────────────────────
# PPT 생성
# ─────────────────────────────────────────────────────────────

# 색상 정의
C = {
    "header_bg":  RGBColor(0xB4, 0x18, 0x5C),   # 진분홍 (회사 제공 양식 참고)
    "header_fg":  RGBColor(0xFF, 0xFF, 0xFF),
    "header_cell_bg": RGBColor(0xFA, 0xE4, 0xEC),  # 연분홍 (라벨 셀)
    "title_bg":   RGBColor(0x1F, 0x3A, 0x5F),
    "border":     RGBColor(0x40, 0x40, 0x40),
    "act_hdr":    RGBColor(0xEA, 0xEA, 0xEA),
    "act_body":   RGBColor(0xFF, 0xFF, 0xFF),
    "risk":       RGBColor(0xFF, 0xC0, 0x00),
    "key_ctrl":   RGBColor(0xB4, 0x18, 0x5C),
    "nonkey_ctrl":RGBColor(0xE2, 0x7D, 0x9E),
    "ctrl_M":     RGBColor(0xE2, 0x7D, 0x9E),
    "ctrl_A":     RGBColor(0xB4, 0x18, 0x5C),
    "ctrl_I":     RGBColor(0xFF, 0xC0, 0x00),
    "doc_fill":   RGBColor(0xD9, 0xD9, 0xD9),
    "db_fill":    RGBColor(0xE0, 0x35, 0x6A),
    "arrow":      RGBColor(0x60, 0x60, 0x60),
    "white":      RGBColor(0xFF, 0xFF, 0xFF),
    "black":      RGBColor(0x00, 0x00, 0x00),
}


def _set_text(shape, lines: list[str], sizes: list[int],
              bolds: list[bool] | None = None,
              color: RGBColor = C["black"],
              anchor=MSO_ANCHOR.MIDDLE,
              align=PP_ALIGN.CENTER):
    tf = shape.text_frame
    tf.margin_left = Cm(0.08); tf.margin_right = Cm(0.08)
    tf.margin_top = Cm(0.04); tf.margin_bottom = Cm(0.04)
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    if bolds is None:
        bolds = [False] * len(lines)
    for i, (txt, sz, bd) in enumerate(zip(lines, sizes, bolds)):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        run = p.add_run()
        run.text = txt
        run.font.size = Pt(sz)
        run.font.bold = bd
        run.font.name = "맑은 고딕"
        run.font.color.rgb = color


def _draw_header(slide, h: HeaderInfo, slide_w_cm: float):
    """상단 헤더 표 (실제 산출물과 유사한 형태)"""
    y = 0.3
    row_h = 0.9
    # 회사명 | 값 | 대분류 | 값 | 중/소분류 | 값 | Flowchart Code | 값 | Last Change Date | 값
    cells = [
        ("회사명", h.company, 1.4, 2.5),
        ("대분류", h.process_name, 1.4, 2.2),
        ("중/소분류", f"{h.middle_category} / {h.sub_process_name}".strip(" /"), 1.8, 2.8),
        ("Flowchart\nCode", h.flowchart_code, 1.6, 1.6),
        ("Last Change\nDate", h.last_change_date, 1.8, 2.0),
    ]
    x = 0.3
    for label, value, lw, vw in cells:
        # 라벨 (분홍)
        lbl = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x), Cm(y), Cm(lw), Cm(row_h))
        lbl.fill.solid(); lbl.fill.fore_color.rgb = C["header_bg"]
        lbl.line.color.rgb = C["header_bg"]
        lbl.shadow.inherit = False
        _set_text(lbl, [label], [9], [True], color=C["white"])
        # 값
        val = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x + lw), Cm(y), Cm(vw), Cm(row_h))
        val.fill.solid(); val.fill.fore_color.rgb = C["white"]
        val.line.color.rgb = C["border"]; val.line.width = Pt(0.5)
        val.shadow.inherit = False
        _set_text(val, [value], [9])
        x += lw + vw
    return y + row_h + 0.3  # 다음 y 좌표


def _draw_activity(slide, x: float, y: float, w: float, h: float, act: Activity):
    """활동 박스: A(번호)/B(팀) // C(이름) // D(위치) + 통제구분 원형"""
    a_w = w * 0.35
    hdr_h = h * 0.25
    body_h = h * 0.55
    foot_h = h - hdr_h - body_h

    # A: 활동번호
    a = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x), Cm(y), Cm(a_w), Cm(hdr_h))
    a.fill.solid(); a.fill.fore_color.rgb = C["act_hdr"]
    a.line.color.rgb = C["border"]; a.line.width = Pt(0.5); a.shadow.inherit = False
    _set_text(a, [str(act.act_no)], [10], [True])

    # B: 팀
    b = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x + a_w), Cm(y), Cm(w - a_w), Cm(hdr_h))
    b.fill.solid(); b.fill.fore_color.rgb = C["act_hdr"]
    b.line.color.rgb = C["border"]; b.line.width = Pt(0.5); b.shadow.inherit = False
    _set_text(b, [act.team], [8])

    # C: 활동명 + 서브스텝
    body_lines = [act.act_name]
    sizes = [10]
    bolds = [True]
    if act.display_body and act.display_body != act.act_name:
        body_lines.append(act.display_body)
        sizes.append(7)
        bolds.append(False)
    c = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x), Cm(y + hdr_h), Cm(w), Cm(body_h))
    c.fill.solid(); c.fill.fore_color.rgb = C["act_body"]
    c.line.color.rgb = C["border"]; c.line.width = Pt(0.5); c.shadow.inherit = False
    _set_text(c, body_lines, sizes, bolds, anchor=MSO_ANCHOR.TOP)

    # D: 위치
    d = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x), Cm(y + hdr_h + body_h), Cm(w), Cm(foot_h))
    d.fill.solid(); d.fill.fore_color.rgb = C["act_hdr"]
    d.line.color.rgb = C["border"]; d.line.width = Pt(0.5); d.shadow.inherit = False
    _set_text(d, [act.location], [8])

    # 통제구분 원형 (통제 있는 활동만)
    if act.rcm and act.rcm.has_control:
        sym = act.rcm.control_type_symbol
        cw = 0.55
        cs = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                                     Cm(x + w - cw - 0.08), Cm(y + 0.08),
                                     Cm(cw), Cm(cw))
        cs.fill.solid(); cs.fill.fore_color.rgb = C[f"ctrl_{sym}"]
        cs.line.fill.background()
        cs.shadow.inherit = False
        _set_text(cs, [sym], [8], [True], color=C["white"])

    return {"x": x, "y": y, "w": w, "h": h,
            "cx": x + w/2, "cy": y + h/2,
            "left": x, "right": x + w, "top": y, "bottom": y + h}


def _draw_risk_control(slide, x: float, y_top: float, act: Activity, w: float):
    """활동 박스 위에 위험·통제 박스를 그린다. 반환: 사용된 높이"""
    if not act.rcm or not (act.rcm.has_risk or act.rcm.has_control):
        return 0.0

    GAP_TO_ACT = 0.15  # 활동 박스와의 간격
    used_h = GAP_TO_ACT
    # 통제 (위 — 활동에 더 가까이)
    if act.rcm.has_control:
        ch = 1.1
        is_key = act.rcm.is_key_control
        color = C["key_ctrl"] if is_key else C["nonkey_ctrl"]
        cb = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                    Cm(x), Cm(y_top - used_h - ch), Cm(w), Cm(ch))
        cb.fill.solid(); cb.fill.fore_color.rgb = color
        cb.line.color.rgb = color; cb.shadow.inherit = False
        cb.name = f"CTRL_{act.rcm.control_no}"
        # 박스 안 텍스트
        desc = act.rcm.control_name or act.rcm.control_desc[:40]
        _set_text(cb, [act.rcm.control_no, desc], [9, 7], [True, False], color=C["white"])
        used_h += ch + 0.1

    # 위험 (통제 위)
    if act.rcm.has_risk:
        rh = 0.9
        rb = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                    Cm(x), Cm(y_top - used_h - rh), Cm(w), Cm(rh))
        rb.fill.solid(); rb.fill.fore_color.rgb = C["risk"]
        rb.line.color.rgb = C["risk"]; rb.shadow.inherit = False
        rb.name = f"RISK_{act.rcm.risk_no}"
        risk_short = act.rcm.risk_desc[:35] + ("…" if len(act.rcm.risk_desc) > 35 else "")
        _set_text(rb, [act.rcm.risk_no, risk_short], [9, 7], [True, False])
        used_h += rh + 0.1

    return used_h


def _draw_document(slide, x: float, y: float, name: str):
    w, h = 2.2, 1.0
    d = slide.shapes.add_shape(MSO_SHAPE.FLOWCHART_DOCUMENT, Cm(x), Cm(y), Cm(w), Cm(h))
    d.fill.solid(); d.fill.fore_color.rgb = C["doc_fill"]
    d.line.color.rgb = C["border"]; d.line.width = Pt(0.5)
    d.shadow.inherit = False
    _set_text(d, [name], [8])
    return {"x": x, "y": y, "w": w, "h": h, "cx": x + w/2, "cy": y + h/2}


def _draw_db(slide, x: float, y: float, name: str):
    w, h = 2.2, 1.3
    d = slide.shapes.add_shape(MSO_SHAPE.CAN, Cm(x), Cm(y), Cm(w), Cm(h))
    d.fill.solid(); d.fill.fore_color.rgb = C["db_fill"]
    d.line.color.rgb = C["db_fill"]
    d.shadow.inherit = False
    _set_text(d, [name], [9], [True], color=C["white"])
    return {"x": x, "y": y, "w": w, "h": h, "cx": x + w/2, "cy": y + h/2}


def _draw_terminal(slide, x: float, y: float, label: str):
    w, h = 1.8, 0.9
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(x), Cm(y), Cm(w), Cm(h))
    s.adjustments[0] = 0.5
    s.fill.solid(); s.fill.fore_color.rgb = C["title_bg"]
    s.line.color.rgb = C["title_bg"]
    s.shadow.inherit = False
    _set_text(s, [label], [11], [True], color=C["white"])
    return {"x": x, "y": y, "w": w, "h": h, "cx": x + w/2, "cy": y + h/2,
            "left": x, "right": x + w, "top": y, "bottom": y + h}


def _draw_arrow(slide, x1: float, y1: float, x2: float, y2: float, dashed: bool = False):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Cm(x1), Cm(y1), Cm(x2), Cm(y2))
    conn.line.color.rgb = C["arrow"]; conn.line.width = Pt(1.2)
    ln = conn.line._get_or_add_ln()
    if dashed:
        prst = ln.makeelement(qn("a:prstDash"), {"val": "dash"})
        ln.append(prst)
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)


def generate_ppt(header: HeaderInfo, activities: list[Activity], output_path: Path):
    """전체 PPT 생성"""
    if not activities:
        raise ValueError("매핑 시트에 활동이 없습니다.")

    prs = Presentation()
    prs.slide_width = Cm(33.87)
    prs.slide_height = Cm(19.05)
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

    slide_w = 33.87
    slide_h = 19.05

    # 1) 헤더
    content_top = _draw_header(slide, header, slide_w)

    # 2) 활동 배치
    n = len(activities)
    margin = 0.5
    term_w = 1.8  # START/END 폭
    avail_w = slide_w - margin * 2 - (term_w + 0.5) * 2  # 양 끝 START/END 자리 빼기

    # 활동 박스 폭: 최소 3.5, 최대 5.0
    if n <= 1:
        act_w = 5.0
        gap = 0
    else:
        # n개 박스 + (n-1)개 gap이 avail_w에 들어가야 함
        target_w = min(5.0, max(3.8, avail_w / n - 0.5))
        act_w = target_w
        gap = (avail_w - act_w * n) / (n - 1) if n > 1 else 0
        gap = max(0.3, gap)
    act_h = 2.4

    # 위험·통제 박스가 차지할 공간 예약
    has_any_risk_or_ctrl = any(
        a.rcm and (a.rcm.has_risk or a.rcm.has_control) for a in activities
    )
    risk_ctrl_reserve = 2.6 if has_any_risk_or_ctrl else 0.3
    act_y = content_top + risk_ctrl_reserve

    # START
    start_x = margin
    start_y = act_y + act_h/2 - 0.45
    start = _draw_terminal(slide, start_x, start_y, "START")

    # 활동들
    act_boxes = []
    cur_x = start_x + term_w + 0.5
    for act in activities:
        # 위험·통제 (활동 위)
        _draw_risk_control(slide, cur_x, act_y, act, act_w)
        # 활동
        box = _draw_activity(slide, cur_x, act_y, act_w, act_h, act)
        act_boxes.append((act, box))
        # 문서 (활동 아래)
        if act.doc_list:
            doc_y = act_y + act_h + 0.3
            for i, doc in enumerate(act.doc_list[:2]):  # 최대 2개
                _draw_document(slide, cur_x + i * (act_w/2), doc_y, doc)
        # DB (문서 아래)
        if act.rcm and act.rcm.it_system and act.rcm.it_system.lower() not in ("manual", ""):
            db_y = act_y + act_h + 1.6
            _draw_db(slide, cur_x + act_w/2 - 1.1, db_y, act.rcm.it_system)
        cur_x += act_w + gap

    # END
    end_x = slide_w - margin - term_w
    end = _draw_terminal(slide, end_x, start_y, "END")

    # 3) 화살표 (직선, 가로 연결)
    if act_boxes:
        first_act = act_boxes[0][1]
        last_act = act_boxes[-1][1]
        _draw_arrow(slide, start["right"], start["cy"], first_act["left"], first_act["cy"])
        for i in range(len(act_boxes) - 1):
            a = act_boxes[i][1]
            b = act_boxes[i + 1][1]
            _draw_arrow(slide, a["right"], a["cy"], b["left"], b["cy"])
        _draw_arrow(slide, last_act["right"], last_act["cy"], end["left"], end["cy"])

    # 4) 분기점·BRANCH_INFO 표시 (간단히 텍스트 박스로)
    for act, box in act_boxes:
        if act.branch_info:
            # 활동 박스 위 또는 아래 작은 라벨
            tb = slide.shapes.add_textbox(Cm(box["x"]), Cm(box["y"] + box["h"] + 0.05),
                                          Cm(box["w"]), Cm(0.5))
            tf = tb.text_frame
            tf.margin_left = Cm(0.05); tf.margin_right = Cm(0.05)
            p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = f"⤳ {act.branch_info}"
            run.font.size = Pt(7); run.font.italic = True; run.font.color.rgb = C["title_bg"]
            run.font.name = "맑은 고딕"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    return output_path


# ─────────────────────────────────────────────────────────────
# 검증 리포트
# ─────────────────────────────────────────────────────────────

def validate(header: HeaderInfo, activities: list[Activity]) -> list[dict]:
    """매핑 ↔ RCM 정합성 검사. 경고·오류 목록 반환"""
    issues = []
    for act in activities:
        if act.rcm is None:
            issues.append({"level": "ERROR", "act": act.act_no,
                           "msg": f"RCM_ROW={act.rcm_row} 에 해당하는 RCM 행 없음"})
            continue
        if not act.act_name:
            issues.append({"level": "ERROR", "act": act.act_no, "msg": "ACT_NAME 비어 있음"})
        if not act.team:
            issues.append({"level": "WARN", "act": act.act_no,
                           "msg": "수행팀이 비어 있음 (RCM Control Organization도 없음, TEAM_OVERRIDE 입력 필요)"})
        if act.rcm.has_risk and not act.rcm.has_control:
            issues.append({"level": "WARN", "act": act.act_no,
                           "msg": f"RCM 행에 위험({act.rcm.risk_no})은 있으나 통제가 없음"})
        if act.rcm.has_control and not act.rcm.has_risk:
            issues.append({"level": "WARN", "act": act.act_no,
                           "msg": f"RCM 행에 통제({act.rcm.control_no})는 있으나 위험이 없음"})
    if not header.flowchart_code:
        issues.append({"level": "WARN", "act": 0, "msg": "Flowchart Code가 비어 있음"})
    return issues
