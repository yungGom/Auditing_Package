# -*- coding: utf-8 -*-
"""DIFF 판정용 목록 — 회계사가 진성/오탐을 판정할 수 있는 형태로 xlsx 한 시트를 낸다.

C안(진성오류 선언 게이트)의 짝이다. 새 축을 등록하려면 그 문서의 DIFF 전건을 회계사가
판정해야 하는데, marks.json 원문으로는 판정할 수 없다. 이 목록이 그 입력이다.
**ERRORS.json에 그대로 붙여넣을 키**를 함께 내므로 선언 작성이 손으로 옮겨 적는 일이
되지 않는다.

★ 자체 검증(결정 25): 성분 합이 재계산금액을 재현하는지 매 행 확인하고, 재현되지 않으면
  조용히 내보내지 않고 경고를 띄운다. 재현되지 않는 근거로는 판정할 수 없다 —
  조선내화 p62에서 성분 21개 중 7개만 실려 나가 판정이 막혔던 사고(2026-08-28)가 계기다.

사용:  python diff_list.py <보고서.pdf> [<보고서.pdf> ...] [--out <폴더>]
       (먼저 `python foot.py <보고서.pdf>`로 marks.json이 생성되어 있어야 한다)
산출:  DIFF_판정목록.xlsx  — 실제 재무 수치가 들어가므로 .gitignore 대상이다
"""
import sys, json, os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import errors as errmod

# 코드 → 회계사가 읽는 말. 내부 코드값을 그대로 내보내지 않는다.
CHECK_NAME = {
    "A1": "세로합 — 계·합계 행이 위 항목들의 합과 같은가",
    "A2": "가로합 — 계 열이 나머지 열의 합과 같은가",
    "A3": "계층합 — 상위 항목이 하위 항목들의 합과 같은가",
    "A5": "산식 — 손익·현금흐름 가감 관계식",
    "L2": "표간 대사 — 같은 항목이 다른 표에서 다른 금액",
    "B":  "본표 간 연계 — 대차일치·순이익 일관·현금 tie",
    "C":  "본표↔주석 레퍼 — 주석에 같은 금액이 있는가",
}
HEAD = ["문서", "면", "표 이름", "계정과목", "공시금액", "재계산금액 / 상대 표 금액",
        "차이", "검증 종류", "계산에 쓴 항목 / 상대 금액", "도구가 차이로 본 근거",
        "자체 검증", "판정 (진성/오탐)", "판정 사유", "ERRORS.json 키"]
WID = [22, 6, 26, 26, 16, 18, 14, 34, 44, 38, 30, 14, 30, 34]
WRAP = {3, 4, 8, 9, 10, 11, 13, 14}
ANSW = {12, 13}


def check_of(m):
    c = (m.get("source") or {}).get("check") or ""
    if c.startswith("B"): return "B"
    if c.startswith("C"): return "C"
    return c


def num(s):
    """표시 금액 문자열 → 수치. 괄호는 음수, '-'는 0. 못 읽으면 None."""
    t = (s or "").strip().replace(",", "").replace(" ", "")
    if t in ("", "-", "–", "—"): return 0.0
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try: v = float(t)
    except ValueError: return None
    return -v if neg else v


def operand_text(m):
    ops = m.get("operands") or []
    out = []
    for o in ops:
        sg = o.get("sign") or "+"
        # bbox=null = 분할 병합 표에서 앞 페이지에 있는 성분. 계산에는 들어갔다.
        tail = "  (앞 면)" if o.get("bbox") is None else ""
        out.append(f"{sg} {o.get('label') or '?'} {o.get('value') or ''}{tail}".strip())
    return "\n".join(out)


def counterpart_text(m):
    out = []
    for c in (m.get("counterparts") or []):
        flag = " [부호 반전 적용]" if c.get("sign_flipped") else ""
        out.append(f"{c.get('tag','')} {c.get('label','')} = {c.get('amount','')} "
                   f"(p{c.get('page')}){flag}")
    return "\n".join(out)


def blank_operands(m):
    ops = m.get("operands") or []
    return sum(1 for o in ops if not (o.get("value") or "").strip()), len(ops)


def basis(m):
    """도구가 왜 차이라고 봤는지 한 줄."""
    ck = check_of(m)
    n = len(m.get("operands") or [])
    nb, nt = blank_operands(m)
    if nt and nb == nt:
        return f"성분 셀 {nt}개를 모두 빈 칸으로 읽어 합계를 0으로 계산했습니다 — 표를 못 읽은 것으로 보입니다"
    if nb:
        return f"성분 셀 {nt}개 중 {nb}개를 빈 칸으로 읽었습니다 — 표를 덜 읽었을 수 있습니다"
    if ck == "L2":
        cps = m.get("counterparts") or []
        return f"본표 금액과 {cps[0].get('label') if cps else '상대 표'}의 금액이 다릅니다"
    if ck == "A5":
        return f"가감 관계식 구성 항목 {n}개로 계산한 값이 공시 금액과 다릅니다"
    if ck == "A1":
        return f"바로 위 {n}개 항목의 합이 이 합계 행과 다릅니다" if n else "위 항목들의 합이 이 합계 행과 다릅니다"
    if ck == "A2":
        return "같은 행 나머지 열의 합이 계 열과 다릅니다"
    if ck == "A3":
        return f"하위 항목 {n}개의 합이 이 상위 항목과 다릅니다" if n else "하위 항목들의 합이 이 상위 항목과 다릅니다"
    return m.get("formula") or ""


def selfcheck(m):
    """성분 합이 재계산금액을 재현하는가. 재현 실패는 판정 불가다 — 조용히 내보내지 않는다."""
    if check_of(m) == "L2":
        cps = m.get("counterparts") or []
        return f"표간 1:1 대사 — 성분 합산 구조 아님 (상대 {len(cps)}건)"
    ev = m.get("evidence") or {}
    n = ev.get("n"); ops = m.get("operands") or []
    if isinstance(n, int) and n > 0 and len(ops) != n:
        return f"⚠ 성분 {n}개 중 {len(ops)}개만 실림 — 판정 불가, 도구 확인 필요"
    if not ops:
        return "⚠ 계산에 쓴 항목이 실리지 않음 — 판정 불가, 도구 확인 필요"
    tot = 0.0
    for o in ops:
        v = num(o.get("value"))
        if v is None:
            return f"⚠ 성분 금액을 숫자로 읽지 못함({o.get('value')!r}) — 판정 불가"
        tot += v if (o.get("sign") or "+") == "+" else -v
    calc = ev.get("calc")
    if calc is None:
        return ""
    if abs(tot - float(calc)) > 0.5:
        return (f"⚠ 성분 합 {tot:,.0f} ≠ 재계산 {float(calc):,.0f} "
                f"(차이 {tot-float(calc):,.0f}) — 판정 불가, 도구 확인 필요")
    return "성분 합 = 재계산금액 (재현 확인)"


def erid(m):
    """ERRORS.json에 붙여넣을 키. L1은 errors.l1_key, L2는 errors.l2_key와 같은 규약."""
    ev = m.get("evidence") or {}
    if check_of(m) == "L2":
        return "(L2 — l2_confirmed_pairs 참고, l2_probe.py로 확인)"
    if ev.get("disp") is None or ev.get("diff") is None:
        return ""
    return errmod.l1_key(m["page"], check_of(m), ev["disp"], ev["diff"])


def rows_of(marks_path, title):
    doc = json.load(open(marks_path, encoding="utf-8"))
    out = []
    for m in doc["marks"]:
        if m.get("verdict") != "DIFF":
            continue
        other = m.get("computed_value") or ""
        if check_of(m) == "L2":
            cps = m.get("counterparts") or []
            other = cps[0].get("amount", "") if cps else ""
        out.append([title, m["page"], m.get("table_label") or "표 이름 미확인",
                    m.get("account") or "", m.get("shown_value") or "", other,
                    m.get("delta") or "", CHECK_NAME.get(check_of(m), check_of(m)),
                    operand_text(m) or counterpart_text(m), basis(m), selfcheck(m),
                    "", "", erid(m)])
    return out


def main(argv):
    pdfs = [a for a in argv if not a.startswith("--")]
    outdir = "."
    if "--out" in argv:
        outdir = argv[argv.index("--out") + 1]
    if not pdfs:
        print(__doc__); return 2

    rows = []
    for p in pdfs:
        base = os.path.splitext(p)[0]
        mj = base + "_marks.json"
        if not os.path.isfile(mj):
            print(f"[오류] marks.json이 없습니다: {mj}")
            print(f"       먼저 실행하십시오: python foot.py \"{p}\"")
            return 2
        rows += rows_of(mj, os.path.basename(base))
    rows.sort(key=lambda r: (r[0], r[1]))

    wb = Workbook(); ws = wb.active; ws.title = "DIFF 판정"
    ws.append(HEAD)
    for r in rows: ws.append(r)

    thin = Side(style="thin", color="BFBFBF")
    for c in range(1, len(HEAD) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="1F3864")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 34
    for i, w in enumerate(WID, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ans_fill = PatternFill("solid", fgColor="FFF2CC")
    warn_fill = PatternFill("solid", fgColor="FCE4E4")
    warned = 0
    for r in range(2, ws.max_row + 1):
        for c in range(1, len(HEAD) + 1):
            cell = ws.cell(row=r, column=c)
            cell.alignment = Alignment(vertical="top", wrap_text=(c in WRAP))
            cell.font = Font(size=10)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            if c in ANSW: cell.fill = ans_fill
        for c in (5, 6, 7):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="right", vertical="top")
        sc = ws.cell(row=r, column=11)
        if str(sc.value or "").startswith("⚠"):
            warned += 1
            for c in range(1, len(HEAD) + 1):
                ws.cell(row=r, column=c).fill = warn_fill
            sc.font = Font(size=10, bold=True, color="C00000")

    dv = DataValidation(type="list", formula1='"진성,오탐,보류"', allow_blank=True)
    ws.add_data_validation(dv); dv.add(f"L2:L{ws.max_row}")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEAD))}{ws.max_row}"

    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "DIFF_판정목록.xlsx")
    wb.save(out)
    print(f"DIFF {len(rows)}건 → {out}")
    if warned:
        print(f"⚠ 자체 검증 실패 {warned}건 — 성분 합이 재계산금액을 재현하지 못합니다. "
              "그 행은 판정하지 마시고 도구 확인이 필요합니다.")
    else:
        print("자체 검증: 전건 통과 (성분 합 = 재계산금액)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
