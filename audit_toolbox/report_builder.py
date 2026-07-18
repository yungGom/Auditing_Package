# -*- coding: utf-8 -*-
"""조회 대상 명세 Excel 빌더 — CLI/Streamlit 공용. 외부통신 없음."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FONT = "맑은 고딕"
_T = Font(name=FONT, size=13, bold=True, color="FFFFFF")
_H = Font(name=FONT, size=10, bold=True, color="FFFFFF")
_HG = Font(name=FONT, size=9, bold=True, color="7F7F7F")
_B = Font(name=FONT, size=10)
_NUM = Font(name=FONT, size=10, bold=True, color="0000CC")
_W = Font(name=FONT, size=10, bold=True, color="C00000")
_G = Font(name=FONT, size=9, color="808080")
_TF = PatternFill("solid", fgColor="1F3864")
_HF = PatternFill("solid", fgColor="305496")
_HGF = PatternFill("solid", fgColor="F2F2F2")
_WF = PatternFill("solid", fgColor="FFE699")
_thin = Side(style="thin", color="BFBFBF")
_BD = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
_C = Alignment(horizontal="center", vertical="center", wrap_text=True)
_L = Alignment(horizontal="left", vertical="center", wrap_text=True)
_R = Alignment(horizontal="right", vertical="center")

FORM_ORDER = {"은행": 0, "증권사": 1, "보험회사": 2, "보증기관": 3, "여신전문": 4,
              "저축은행": 5, "기타(검토필요)": 8, "미분류(검토필요)": 9}


def sort_candidates(candidates):
    return sorted(candidates, key=lambda c: (FORM_ORDER.get(c["조회서양식"], 7),
                  c["조회방법"].startswith("서면"), c["기관(정규화)"]))


def _hdr(ws, row, headers, widths, gray_from=None):
    for i, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=row, column=i, value=h)
        if gray_from and i >= gray_from:
            cell.font = _HG; cell.fill = _HGF
        else:
            cell.font = _H; cell.fill = _HF
        cell.alignment = _C; cell.border = _BD
        ws.column_dimensions[get_column_letter(i)].width = w


def build_workbook(candidates, hits, unmatched):
    candidates = sort_candidates(candidates)
    wb = Workbook()

    # Sheet 1: 조회 대상 명세 (제출 양식)
    ws = wb.active; ws.title = "조회 대상 명세"
    ws.merge_cells("A1:L1")
    t = ws["A1"]; t.value = "금융기관 조회 대상 명세 (모집단 완전성 검토 결과)"
    t.font = _T; t.fill = _TF; t.alignment = _C; ws.row_dimensions[1].height = 28
    ws.merge_cells("A2:L2")
    g = ws["A2"]
    g.value = ("(*1) 조회방법: 온라인 조회 가능 기관은 자동 표기, '서면 조회(확인필요)'는 직접 확인  ·  "
               "(*2) 회신형태 기본값 '원본'  |  노란색 = 사전 미등록 또는 온라인 미참가 → 직접 확인  |  "
               "회색 컬럼(I~K)은 검토용, 제출 전 삭제 가능")
    g.font = _G; g.alignment = _L; g.fill = _HGF; ws.row_dimensions[2].height = 32
    headers = ["조회서번호", "금융기관", "조회(*1)", "주소", "담당자", "전화번호",
               "회신/스캔(*2)", "조회서 양식", "포함근거", "발견건수", "근거", "원천행"]
    widths = [11, 22, 16, 22, 12, 14, 12, 16, 18, 9, 16, 14]
    _hdr(ws, 3, headers, widths, gray_from=9)
    for i, c in enumerate(candidates, 4):
        flag = c["조회방법"].startswith("서면") or c["조회서양식"].endswith("(검토필요)")
        # 온라인 조회는 전화번호 생략(전자조회), 서면 조회처만 참고용 표기 가능
        tel = "" if c["조회방법"] == "온라인 조회" else c.get("전화번호", "")
        vals = [f"BC{i-3}", c.get("온라인정식명") or c["기관(정규화)"], c["조회방법"],
                "", "", tel, "원본", c["조회서양식"],
                c.get("포함근거", "당기 탐지"), c["발견건수"], c["근거"], c["원천행"]]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=i, column=j, value=v); cell.border = _BD
            if j == 1:
                cell.font = _NUM; cell.alignment = _C
            elif j >= 9:
                cell.font = _G; cell.alignment = _L if j == 11 else _C
            else:
                cell.font = _B; cell.alignment = _L if j in (2, 4) else _C
            if flag and j <= 8:
                cell.fill = _WF
        if flag:
            ws.cell(row=i, column=3).font = _W
    ws.freeze_panes = "A4"

    # Sheet 2: 검토 근거
    ws2 = wb.create_sheet("검토 근거")
    ws2.merge_cells("A1:J1")
    t = ws2["A1"]; t.value = "검토 근거 — 원천 추적 & 미매칭 안전망"
    t.font = _T; t.fill = _TF; t.alignment = _C; ws2.row_dimensions[1].height = 26
    ws2.merge_cells("A2:J2")
    g = ws2["A2"]
    g.value = ("위: 후보 기관이 나온 원천행 (노란색=사전 미등록)  ·  "
               "아래: 어디에도 안 걸렸지만 금액 큰 거래 (비정형 명칭 금융기관 점검용)")
    g.font = _G; g.alignment = _L; g.fill = _HGF; ws2.row_dimensions[2].height = 26
    h2 = ["구분", "기관(정규화)", "원천행", "출처", "일자", "전표번호", "계정과목", "거래처명", "적요", "금액"]
    w2 = [14, 18, 8, 12, 12, 12, 24, 18, 30, 16]
    _hdr(ws2, 3, h2, w2)
    hits_sorted = sorted(hits, key=lambda x: (x["norm_vendor"], x["row_no"]))
    r = 4
    for h in hits_sorted:
        review = h["basis"] != "사전매칭"
        vals = ["매칭", h["norm_vendor"], h["row_no"], h["source"], h["date"], h["slip_no"],
                h["account"], h.get("vendor") or "(공란)", h["memo"], h["amount"]]
        for j, v in enumerate(vals, 1):
            cell = ws2.cell(row=r, column=j, value=v); cell.font = _B; cell.border = _BD
            cell.alignment = _R if j == 10 else (_L if j in (7, 8, 9) else _C)
            if j == 10:
                cell.number_format = "#,##0"
            if review:
                cell.fill = _WF
        r += 1
    r += 1
    ws2.cell(row=r, column=1, value="── 미매칭 잔여 (안전망) ──").font = _W
    r += 1
    for u in sorted(unmatched, key=lambda x: -float(x["amount"])):
        vals = ["미매칭(안전망)", "-", u["row_no"], u["source"], u["date"], u["slip_no"],
                u["account"], u.get("vendor") or "(공란)", u["memo"], u["amount"]]
        for j, v in enumerate(vals, 1):
            cell = ws2.cell(row=r, column=j, value=v); cell.font = _B; cell.border = _BD
            cell.alignment = _R if j == 10 else (_L if j in (7, 8, 9) else _C)
            if j == 10:
                cell.number_format = "#,##0"
        r += 1
    ws2.freeze_panes = "A4"
    return wb
