"""A-5a: Footing 결과 엑셀 — AI_Footing 형식 재현.

예시 파일 실측 (AI_Footing 5종):
- 시트 구성: 총괄표 | 원문 | BS/PL/CE/CF | 1..N (주석)
- 총괄표: 좌측 [시트|제목] (하이퍼링크+원문 제목), 우측
  [시트|시트 링크|푸팅 오류|크로스 오류|총합(=I{r}+J{r} 수식)]
- 각 시트 M2에 총괄표 복귀 하이퍼링크
- 오류 셀 표시: 노란 채우기 (예시 5종 중 2종에서 실측 — 비일관하므로
  노랑 컨벤션만 계승, 위치는 A-4 검증 결과의 정확 좌표 사용, 상세는 메모)

용어 매핑: 푸팅 오류 = A-4 합계검증(단수차+불일치),
크로스 오류 = 주석대사 미매칭(못찾음).
"""
import os
import re

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .cellsafe import put as safe_put
from .excel_out import MAP_SHEET, META_SHEET
from .foot import (DEFAULT_LIMIT, FOOT_SHEET, FUZZY, MISMATCH,
                   FootingContext)

_BOLD = Font(bold=True)
_HDR_FILL = PatternFill("solid", start_color="D9E1F2")
_YELLOW = PatternFill("solid", start_color="FFFFFF00")   # 예시 실측 색
_LINK_FONT = Font(color="FF0563C1", underline="single")

_SUMMARY_LEFT_HDR = ["시트", "제목"]
_SUMMARY_RIGHT_HDR = ["시트", "시트 링크", "푸팅 오류", "크로스 오류", "총합"]


DETAIL_SHEET = "검증내역"          # A-6: 전수 목록·수식 판정
_REASONS = ("①분해 공시", "②단위·집계 상이", "③매칭 불가")


def _ref(sheet, row, col):
    """엑셀 셀 참조 — 시트명은 항상 인용(숫자 시트명 '12' 등 안전)."""
    return f"'{sheet}'!{get_column_letter(col)}{row}"


def _foot_cells(ctx, fr):
    """푸팅 결과 행 → (부모 (row,col), 자식 [(row,col)]) 실좌표."""
    sheet = fr["sheet"]
    if fr["axis"] == "행":
        m = re.match(r"표\d+:C(\d+)", str(fr["scope"] or ""))
        if m:                                    # 주석 표 — 열 고정
            col = int(m.group(1))
            return ((fr["parent_key"], col),
                    [(k, col) for k in fr["child_keys"]])
        # FS — 행별 실제 값 열 (당기 좌/우 쌍 대응)
        pc = ctx.fs_value_col(sheet, fr["parent_key"], fr["scope"])
        if pc is None:
            return None
        children = []
        for k in fr["child_keys"]:
            c = ctx.fs_value_col(sheet, k, fr["scope"])
            if c is None:
                return None
            children.append((k, c))
        return (fr["parent_key"], pc), children
    m = re.search(r"R(\d+)", str(fr["scope"] or ""))
    if not m:
        return None
    row = int(m.group(1))                        # 열 방향 — 행 고정
    return ((row, fr["parent_key"]),
            [(row, k) for k in fr["child_keys"]])


def _classify_missing(ctx, pools, refs, value):
    """크로스 미발견 사유 분류 (A-6 보완 — 사유 없는 미발견 금지).

    기계 분류는 후보 제시일 뿐 판정 변경 없음 (통제 4호 — 확정은
    회계사). ② 스케일 후보 → ① 구성 합 일치 → ③ 기타 순.
    """
    limit = ctx.limit
    for ref in refs:
        for _ti, _axis, _key, seq in ctx.table_sequences(ref):
            vals = [x for _k, x in seq if x is not None]
            for i in range(len(vals)):
                s = 0.0
                for j in range(i, len(vals)):
                    s += vals[j]
                    if j > i and abs(abs(s) - abs(value)) <= limit:
                        return "①분해 공시(구성 합 일치 구간 존재)"
    # 스케일 후보는 미세값 우연 일치 방지 가드: 양변 모두 유의미한 크기
    for ref in refs:
        for _r, _c, nv in pools.get(ref, []):
            if abs(nv) <= limit * 10 or abs(value) < 1000:
                continue
            if abs(abs(nv) - abs(value) / 1000) <= limit or \
                    abs(abs(nv) - abs(value) * 1000) <= limit:
                # A-7 이후: 배율 확정 쌍은 환산까지 시도되므로, 여기
                # 도달 = 단위 마커 미상 상태의 자릿수 후보 (참고용)
                return "②단위·집계 상이(천배 후보 — 단위 마커 미상)"
    return "③매칭 불가(기타)"


def _sheet_title(ws):
    """시트 원문 제목: FS는 A1 제목행, 주석은 'N. 제목'의 제목부."""
    v = str(ws.cell(1, 1).value or "").strip()
    m = re.match(r"^\d+\.\s*(.+)$", v)
    return m.group(1).strip() if m else v


def _quote(name):
    return f"'{name}'" if not name.isalnum() else name


def write_ai_footing(xlsx_path, foot_result, out_path=None,
                     company_name=None):
    """foot() 결과 → AI_Footing_{회사명}.xlsx 독립 파일. 요약 dict 반환."""
    wb = load_workbook(xlsx_path)
    # extract()가 이미 참조용 "원문" 시트를 만들어 두지만(스펙 7.5 P3),
    # 여기서 만드는 원문은 오류 하이라이트까지 포함한 상위 호환판이라
    # 소스 목록에서 제외하고 아래에서 새로 만들어 교체한다.
    data_sheets = [s for s in wb.sheetnames
                   if s not in (MAP_SHEET, META_SHEET, FOOT_SHEET, "원문")]

    # --- 오류 집계 (시트별) -------------------------------------------------
    foot_err = {}
    for r in foot_result["foot"]:
        if r["verdict"] in (FUZZY, MISMATCH):
            foot_err.setdefault(r["sheet"], []).append(r)
    cross_err = {}
    for r in foot_result["notes"]:
        if not r["found"]:
            cross_err.setdefault(r["sheet"], []).append(r)

    # --- 오류 셀 표시 (노란 채우기 + 메모 — A-4 정확 좌표) ------------------
    # H-2: 추출 시트에는 원문 표의 병합이 그대로 있어 병합 내부 좌표
    # 기입이 터진다 — 안전 헬퍼(앵커 리다이렉트·메모 이어붙임·실패
    # 축적)로 기입. 한 셀 실패로 전체 생성을 중단하지 않는다.
    write_failures = []
    for sheet, errs in foot_err.items():
        if sheet not in wb.sheetnames:
            continue
        ws = wb[sheet]
        for e in errs:
            m = re.match(r"R(\d+)", str(e["loc"]))
            if not m:
                continue
            note = (f"[푸팅 {e['verdict']}] Σ자식 {e['expected']:,.0f} vs "
                    f"기재 {e['actual']:,.0f} (차이 {e['diff']:,.0f}) — "
                    f"{e['scope']}/{e['direction']}")
            safe_put(ws, int(m.group(1)), 1, fill=_YELLOW,
                     comment=(note, "dsd_tool foot"),
                     failures=write_failures, what="푸팅 오류 표시")
    for sheet, errs in cross_err.items():
        if sheet not in wb.sheetnames:
            continue
        ws = wb[sheet]
        for e in errs:
            safe_put(ws, e["row"], 1, fill=_YELLOW,
                     comment=(f"[크로스 미매칭] 주석 {e['refs']} 에서 값 "
                              f"{e['value']:,.0f} ({e['period']}) 미발견",
                              "dsd_tool foot"),
                     failures=write_failures, what="크로스 오류 표시")

    # --- 각 시트 복귀 링크 (M2 — 예시 위치 그대로) ---------------------------
    for sheet in data_sheets:
        safe_put(wb[sheet], 2, 13,
                 value='=HYPERLINK("#총괄표!A1","총괄표로 이동")',
                 font=_LINK_FONT, failures=write_failures,
                 what="총괄표 복귀 링크", preserve_value=True)

    # --- 원문 시트 (전체 통합 뷰 — 시트 내용 세로 연결) ----------------------
    src_order = list(data_sheets)
    if "원문" in wb.sheetnames:                     # extract판 → 교체
        wb.remove(wb["원문"])
    ws_all = wb.create_sheet("원문", 0)
    out_row = 1
    for sheet in src_order:
        ws = wb[sheet]
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None or cell.column > 12:
                    continue
                tgt = ws_all.cell(row=out_row + cell.row - 1,
                                  column=cell.column)
                tgt.value = cell.value
                if cell.fill and cell.fill.patternType:
                    tgt.fill = PatternFill(
                        cell.fill.patternType,
                        start_color=cell.fill.start_color,
                        end_color=cell.fill.end_color)
        out_row += ws.max_row + 2

    # --- 총괄표 -------------------------------------------------------------
    ws0 = wb.create_sheet("총괄표", 0)
    ws0.cell(row=2, column=2, value="시트정보").font = _BOLD
    ws0.cell(row=2, column=7, value="푸팅/크로스 에러 사항").font = _BOLD
    for j, h in enumerate(_SUMMARY_LEFT_HDR):
        c = ws0.cell(row=4, column=2 + j, value=h)
        c.font = _BOLD
        c.fill = _HDR_FILL
    for j, h in enumerate(_SUMMARY_RIGHT_HDR):
        c = ws0.cell(row=4, column=7 + j, value=h)
        c.font = _BOLD
        c.fill = _HDR_FILL
    # A-6: 수행 건수 병기 — 원형 5열(G~K)은 불가침, 우측에 추가
    # ("0/0 검증불능"과 "0/N 전부 일치" 구분 — 침묵 무결 금지)
    # A-7: 일치(단위환산) 별도 열 — 기존 일치와 분리 집계
    for j, h in enumerate(("푸팅 수행", "크로스 수행",
                           "크로스 일치(단위환산)")):
        c = ws0.cell(row=4, column=12 + j, value=h)
        c.font = _BOLD
        c.fill = _HDR_FILL

    left = [("원문", _sheet_title(wb[src_order[0]]) if src_order else "")]
    left += [(s, _sheet_title(wb[s])) for s in src_order]
    for i, (name, title) in enumerate(left):
        r = 5 + i
        c = ws0.cell(row=r, column=2,
                     value=f'=HYPERLINK("#{_quote(name)}!A1","{name}")')
        c.font = _LINK_FONT
        ws0.cell(row=r, column=3, value=title)

    ctx = FootingContext(xlsx_path, limit=foot_result.get("limit", DEFAULT_LIMIT))
    verify_targets = set(ctx.fs_sheets) | set(ctx.note_sheets)
    foot_all, cross_all = {}, {}                # A-6: 시트별 수행(모수)
    for fr in foot_result["foot"]:
        foot_all.setdefault(fr["sheet"], []).append(fr)
    for nr in foot_result["notes"]:
        cross_all.setdefault(nr["sheet"], []).append(nr)

    _WARN = PatternFill("solid", start_color="FFFFC000")   # 모수 0 경고색
    total_foot = total_cross = 0
    for i, name in enumerate(src_order):
        r = 5 + i
        nf = len(foot_err.get(name, []))
        nc = len(cross_err.get(name, []))
        total_foot += nf
        total_cross += nc
        ws0.cell(row=r, column=7, value=name)
        c = ws0.cell(row=r, column=8,
                     value=f'=HYPERLINK("#{_quote(name)}!$A$1",'
                           f'"시트 바로가기")')
        c.font = _LINK_FONT
        ws0.cell(row=r, column=9, value=float(nf))
        ws0.cell(row=r, column=10, value=float(nc))
        ws0.cell(row=r, column=11, value=f"=총괄표!I{r}+총괄표!J{r}")
        # A-6: 수행 건수 — 모수 0이면 경고색 (검증불능 ≠ 무결)
        nfa, nca = len(foot_all.get(name, [])), len(cross_all.get(name, []))
        cf = ws0.cell(row=r, column=12, value=float(nfa))
        cc = ws0.cell(row=r, column=13, value=float(nca))
        ws0.cell(row=r, column=14, value=float(
            sum(1 for x in cross_all.get(name, []) if x.get("conv"))))
        if name in verify_targets:              # 검증 대상인데 모수 0
            if nfa == 0:
                cf.fill = _WARN
            if nca == 0 and name in ctx.fs_sheets:   # 크로스는 FS발 검증
                cc.fill = _WARN
    ws0.column_dimensions["C"].width = 40
    for col in ("B", "G", "H"):
        ws0.column_dimensions[col].width = 16

    # --- 검증내역 (A-6) — 수행된 모든 검증 전수 목록·수식 판정 --------------
    # 판정·차이는 엑셀 수식으로 기입 — 셀 클릭 시 근거 추적 (조서 증적)
    from .foot import _numeric_cells
    pools = {s: _numeric_cells(ctx, s) for s in ctx.note_sheets}
    limit = ctx.limit
    wsd = wb.create_sheet(DETAIL_SHEET, 2)      # 총괄표|원문 다음 (원형 보존)
    reason_counts = {k: 0 for k in _REASONS}
    n_foot = len(foot_result["foot"])
    n_cross = len(foot_result["notes"])
    n_found = sum(1 for x in foot_result["notes"] if x["found"])
    foot_bad = sum(1 for x in foot_result["foot"]
                   if x["verdict"] in (FUZZY, MISMATCH))
    wsd.append([f"검증내역 — 수행된 모든 검증 전수 목록 "
                f"(판정·차이 = 엑셀 수식, 허용 한도 ±{limit})"])
    wsd.cell(1, 1).font = Font(bold=True, size=12)
    wsd.append([f"푸팅: 수행 {n_foot} — 통과 {n_foot - foot_bad} / "
                f"오류 {foot_bad}"])
    wsd.append([])                              # 크로스 집계 — 사유 확정 후
    wsd.append([])
    wsd.append(["유형", "시트", "좌변 참조", "좌변 내용", "좌변 값",
                "우변 참조", "우변 계정명", "우변 값", "판정", "차이액",
                "미발견 사유", "이동"])
    hdr_r = wsd.max_row
    for c in wsd[hdr_r]:
        c.font = _BOLD
        c.fill = _HDR_FILL
    detail_of = {}                              # (시트, 행) → 검증내역 행

    for fr in foot_result["foot"]:
        cells = _foot_cells(ctx, fr)
        r = wsd.max_row + 1
        if cells is None:                       # 좌표 재구성 불가 — 값 기입
            wsd.append(["푸팅", fr["sheet"], fr["scope"], "Σ자식",
                        fr["expected"], fr["loc"], fr["label"],
                        fr["actual"], (FUZZY if fr["verdict"] == FUZZY
                                       else fr["verdict"] != MISMATCH),
                        fr["diff"], "", ""])
        else:
            (pr, pc), children = cells
            refs = [_ref(fr["sheet"], cr, cc) for cr, cc in children]
            wsd.append([
                "푸팅", fr["sheet"], "+".join(refs),
                f"Σ자식 {fr['n_children']}개 ({fr['direction']})",
                "=" + "+".join(refs),
                _ref(fr["sheet"], pr, pc), fr["label"],
                "=" + _ref(fr["sheet"], pr, pc),
                f'=IF(E{r}=H{r},TRUE,IF(ABS(E{r}-H{r})<={limit},"{FUZZY}",FALSE))',
                f"=E{r}-H{r}", "",
                f'=HYPERLINK("#{_quote(fr["sheet"])}!'
                f'{get_column_letter(pc)}{pr}","이동")'])
        wsd.cell(r, 12).font = _LINK_FONT
        if fr["verdict"] in (FUZZY, MISMATCH):
            wsd.cell(r, 9).fill = _YELLOW
            if fr["axis"] == "행":
                br = fr["parent_key"]
            else:
                m2 = re.search(r"R(\d+)", str(fr["scope"] or ""))
                br = int(m2.group(1)) if m2 else None
            if br:
                detail_of.setdefault((fr["sheet"], br), r)

    for nr in foot_result["notes"]:
        r = wsd.max_row + 1
        lc = ctx.fs_value_col(nr["sheet"], nr["row"], nr["period"])
        lref = _ref(nr["sheet"], nr["row"], lc) if lc else ""
        left_val = "=" + lref if lref else nr["value"]
        kind = "크로스" if nr["refs"] != "(폴백)" else "크로스(폴백)"
        conv = nr.get("conv")
        if conv:
            kind = "크로스(단위환산)"           # A-7: 분리 집계·표기
        if nr["found"]:
            m = re.match(r"(?:주석)?(.+?) R(\d+)C(\d+)$",
                         str(nr["where"] or ""))
            if m and m.group(1) in wb.sheetnames:
                tref = _ref(m.group(1), int(m.group(2)), int(m.group(3)))
                if conv:
                    # A-7: 좌·우를 원 단위로 환산하는 수식 — 배율·허용
                    # 오차까지 셀에서 추적 가능 (증적)
                    sf, sn, tol = (conv["fs_scale"], conv["note_scale"],
                                   conv["tol"])
                    wsd.append([
                        kind, nr["sheet"], lref,
                        f"{nr['label']} ({nr['period']} · 주석 "
                        f"{nr['refs']}) · 배율 좌×{sf:,}/우×{sn:,}"
                        f" (허용 ±{tol:,})",
                        (f"={lref}*{sf}" if lref else nr["value"] * sf),
                        tref, nr["where"] + " 표시값",
                        f"={tref}*{sn}",
                        f"=ABS(ABS(E{r})-ABS(H{r}))<={tol}",
                        f"=ABS(E{r})-ABS(H{r})", "",
                        f'=HYPERLINK("#{_quote(nr["sheet"])}!'
                        f'A{nr["row"]}","이동")'])
                else:
                    wsd.append([
                        kind, nr["sheet"], lref,
                        f"{nr['label']} ({nr['period']} · 주석 "
                        f"{nr['refs']})",
                        left_val, tref, nr["where"], "=" + tref,
                        f"=ABS(ABS(E{r})-ABS(H{r}))<={limit}",
                        f"=ABS(E{r})-ABS(H{r})", "",
                        f'=HYPERLINK("#{_quote(nr["sheet"])}!'
                        f'A{nr["row"]}","이동")'])
            else:
                wsd.append([kind, nr["sheet"], lref,
                            f"{nr['label']} ({nr['period']})", left_val,
                            nr["where"], "", "", True, "", "",
                            f'=HYPERLINK("#{_quote(nr["sheet"])}!'
                            f'A{nr["row"]}","이동")'])
        else:
            refs = [t for t in re.findall(r"\d+", str(nr["refs"]))
                    if t in ctx.note_sheets]
            if nr.get("conv_tried"):
                # A-7: 배율이 확정된 상이 쌍은 환산까지 시도한 결과 —
                # 스케일 후보(②)가 아니라 환산 후에도 미발견(③)
                reason = "③매칭 불가(단위환산 시도 후 미발견)"
            else:
                reason = _classify_missing(ctx, pools, refs, nr["value"])
            reason_counts[reason.split("(")[0]] += 1
            wsd.append([kind, nr["sheet"], lref,
                        f"{nr['label']} ({nr['period']} · 주석 "
                        f"{nr['refs']})", left_val,
                        "(미발견)", "", "", False, "", reason,
                        f'=HYPERLINK("#{_quote(nr["sheet"])}!A{nr["row"]}",'
                        f'"이동")'])
            wsd.cell(r, 9).fill = _YELLOW
            detail_of.setdefault((nr["sheet"], nr["row"]), r)
        wsd.cell(r, 12).font = _LINK_FONT

    rc = " · ".join(f"{k} {v}" for k, v in reason_counts.items())
    n_conv = sum(1 for x in foot_result["notes"] if x.get("conv"))
    wsd.cell(3, 1).value = (
        f"크로스: 수행 {n_cross} — 발견 {n_found}"
        f" (단위환산 일치 {n_conv} 분리 집계) / 미발견 "
        f"{n_cross - n_found} (사유별: {rc}) — 사유 없는 미발견 없음")
    for col, w in (("C", 28), ("D", 34), ("F", 18), ("G", 22), ("K", 26)):
        wsd.column_dimensions[col].width = w

    # 개별 시트 → 검증내역 왕복 링크 (오류 행 N열) — H-2 안전 기입
    for (sheet, row), dr in detail_of.items():
        if sheet in wb.sheetnames:
            safe_put(wb[sheet], row, 14,
                     value=f'=HYPERLINK("#{DETAIL_SHEET}!A{dr}","검증내역")',
                     font=_LINK_FONT, failures=write_failures,
                     what="검증내역 왕복 링크", preserve_value=True)

    # H-2: 기입 불가 항목 노출 — 침묵 금지, 생성은 계속
    if write_failures:
        wsd.append([])
        wsd.append([f"⚠ 표시 기입 불가 {len(write_failures)}건 — 아래"
                    " 항목은 시트에 표시하지 못했습니다 (검증 결과"
                    " 자체는 이 목록과 총괄표에 반영됨)"])
        wsd.cell(wsd.max_row, 1).fill = _YELLOW
        for f in write_failures:
            wsd.append(["기입 불가", f["sheet"], f["cell"], f["what"],
                        "", "", "", "", "", "", f["reason"], ""])

    # --- 저장 ---------------------------------------------------------------
    if MAP_SHEET in wb.sheetnames:
        del wb[MAP_SHEET]
    if META_SHEET in wb.sheetnames:
        del wb[META_SHEET]
    if FOOT_SHEET in wb.sheetnames:
        del wb[FOOT_SHEET]
    if company_name is None:
        company_name = re.sub(r"\.xlsx$", "", os.path.basename(xlsx_path))
    if out_path is None:
        out_path = os.path.join(os.path.dirname(os.path.abspath(xlsx_path)),
                                f"AI_Footing_{company_name}.xlsx")
    wb.save(out_path)
    return {"out_path": out_path, "limit": limit, "foot_errors": total_foot,
            "cross_errors": total_cross,
            "sheets": ["총괄표", "원문", DETAIL_SHEET] + src_order,
            # A-6: 수행 모수·사유별 집계 — "오류/수행"이 해석 가능하게
            "checks": {"foot_total": n_foot, "cross_total": n_cross,
                       "cross_found": n_found,
                       "cross_conv": n_conv,   # A-7: 일치(단위환산)
                       "missing_reasons": dict(reason_counts)},
            # H-2: 기입 불가 항목 (0이 정상 — 침묵 금지 노출용)
            "write_failures": list(write_failures)}
