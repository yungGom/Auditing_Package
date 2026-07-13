"""A-5b: 전기대사 — 당기 보고서의 전기값 ↔ 전기 보고서의 당기값.

판정 규칙 (확정, 법인 실무 표준):
- 판정 열은 TRUE / FALSE 2값만
- FALSE 사유는 비고 열: "값 상이 (차이 ±N)" / "전기 보고서에 항목 없음"
- 값 비교는 절대값 ±0 엄격 일치 (--tolerance 로만 완화)
- 해석은 회계사: 요약 상단 안내 1줄 (전기 재작성·계정 재분류 확인)

입력 모드:
① 계속감사: 당기 DSD + 전기 DSD (로컬 파일)
② 초도감사: dart_explorer가 미리 수신해 둔 캐시 파일 경로를 --prior로 지정
   (dsd_workbench는 직접 네트워크 금지 — 경계 유지. 호환성 판정은
   RECON_모드2_호환성.md 참조: 공시원본은 래핑 후 extract로 본문 대사 가능,
   주석 분할 부정확 → 주석은 수동 확인 필요 목록화)
③ 파일 직접 지정: --prior <전기.dsd 또는 전기_편집용.xlsx>

대사 로직:
- 본문(BS/PL/PL1/CF): 당기 파일 "전기 열" ↔ 전기 파일 "당기 열",
  계정 매칭은 A-4 계정명 정규화 재사용
- CE: 행(변동내역, 블록 라벨의 날짜 제거) × 열(자본항목) 2차원 매칭 —
  당기 파일의 전기 블록(전기초~전기말) ↔ 전기 파일의 당기 블록
- 주석: 번호가 아니라 제목 정규화로 매칭 (연도 간 번호 이동 대응).
  표 내부는 헤더의 당기/전기 열 식별 후 행 라벨 매칭 → 셀 대조.
  서술문 내 숫자는 스코프 제외 (오탐 과다).
"""
import os
import re
import tempfile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .excel_out import extract
from .foot import FootingContext, _label, _regions
from .foot import _norm_label as _norm1
from .mapping import normalize as _norm2

# 라벨 정규화 2단계 (실측 근거):
# 1차: foot._norm_label — 괄호 기호만 제거, 안의 한글 유지
#      ('기타금융자산(유동)' vs '(비유동)' 구분 보존 — 병합하면 오탐)
# 2차 폴백: mapping.normalize — 괄호 내용까지 제거
#      (FY24 '영업이익 (손실)' vs FY25 '영업이익' 같은 표기 변형 흡수)


def _norm_label(label):
    return _norm1(label)

_BOLD = Font(bold=True)
_HDR_FILL = PatternFill("solid", start_color="D9E1F2")
_FALSE_FILL = PatternFill("solid", start_color="FFC7CE")
_LINK_FONT = Font(color="FF0563C1", underline="single")
_NUMFMT = "#,##0;[RED](#,##0)"

GUIDE = ("FALSE 존재 시 전기 재작성·계정 재분류 여부를 확인하십시오 "
         "(판정은 기계, 해석은 회계사)")

_DATE_PREFIX_RE = re.compile(r"^\d{4}[.\-/]\s*\d{1,2}[.\-/]\s*\d{1,2}")
_BLOCK_TAG_RE = re.compile(r"\((당|전)기\s*(초|말)\)")


def _to_xlsx(path, workdir):
    """입력이 .dsd면 extract, .xlsx면 그대로."""
    if path.lower().endswith(".dsd"):
        out = os.path.join(workdir,
                           re.sub(r"\.dsd$", ".xlsx",
                                  os.path.basename(path), flags=re.I))
        extract(path, out)
        return out
    return path


def _fmt_num(v):
    return f"{v:,.0f}" if isinstance(v, (int, float)) else str(v)


def _verdict(cur_val, pri_val, tolerance):
    """(TRUE/FALSE, 비고)."""
    if pri_val is None:
        return False, "전기 보고서에 항목 없음"
    if cur_val is None:
        return False, "당기 보고서에 값 없음"
    diff = abs(float(cur_val) - float(pri_val))
    if diff <= tolerance:
        return True, ""
    return False, f"값 상이 (차이 ±{diff:,.0f})"


# ---------------------------------------------------------------------------
# 본문 대사 (BS/PL/PL1/CF — 1차원 라벨 매칭)
# ---------------------------------------------------------------------------

def _period_seq(ctx, sheet, want):
    """fs_sequences에서 '당기'/'전기' 시퀀스를 dict{row: val}로."""
    periods, rows = ctx.fs_sequences(sheet)
    seq = next((s for n, s in periods if n == want), [])
    return dict(seq), rows


def recon_statement(cur_ctx, pri_ctx, sheet, tolerance=0):
    cur_prior, cur_rows = _period_seq(cur_ctx, sheet, "전기")
    pri_current, pri_rows = _period_seq(pri_ctx, sheet, "당기")
    ws_c, ws_p = cur_ctx.wb[sheet], pri_ctx.wb[sheet]

    pri_by_label, pri_by_label2 = {}, {}
    for r in pri_rows:
        raw = _label(ws_p, r)
        if pri_current.get(r) is None:
            continue
        lab1, lab2 = _norm1(raw), _norm2(raw)
        if lab1:
            pri_by_label.setdefault(lab1, pri_current[r])
        if lab2:
            pri_by_label2.setdefault(lab2, pri_current[r])

    rows = []
    for r in cur_rows:
        label = _label(ws_c, r)
        lab1, lab2 = _norm1(label), _norm2(label)
        v = cur_prior.get(r)
        if not lab1 or v is None:
            continue
        pv = pri_by_label.get(lab1)
        if pv is None and lab2:                 # 2차 폴백 (표기 변형 흡수)
            pv = pri_by_label2.get(lab2)
        ok, note = _verdict(v, pv, tolerance)
        rows.append({"label": label, "cur_prior": v, "pri_current": pv,
                     "true": ok, "note": note})
    return rows


# ---------------------------------------------------------------------------
# CE 대사 (행 변동내역 × 열 자본항목 — 2차원)
# ---------------------------------------------------------------------------

def _ce_grid(ctx, sheet, want_block):
    """CE 시트에서 (행라벨정규화, 열라벨정규화) → 값 grid.

    want_block: '전기'(전기초~전기말 구간) 또는 '당기'.
    """
    rowmap = ctx.rowmaps[sheet]
    regions = _regions(rowmap)
    if not regions:
        return {}, []
    region = max(regions, key=len)
    ws = ctx.wb[sheet]
    header = region[0]
    cols = {c: _norm_label(str(ws.cell(row=header, column=c).value or "")
                           .replace("\n", ""))
            for c in rowmap[header][2:]}

    # 블록 구간 탐지: '(전기초)' 행 ~ '(전기말)' 행
    start = end = None
    for r in region[1:]:
        label = _label(ws, r)
        m = _BLOCK_TAG_RE.search(label)
        if m and m.group(1) + "기" == want_block + "기"[1:]:
            pass
        if m:
            tag = m.group(1)                    # 당 or 전
            if (want_block == "전기") == (tag == "전"):
                if m.group(2) == "초":
                    start = r
                else:
                    end = r
    if start is None or end is None:
        return {}, sorted(cols.values())

    grid = {}
    for r in region[1:]:
        if not (start <= r <= end):
            continue
        raw = _label(ws, r)
        # 날짜 접두 제거 후 정규화 ('2024.1.1(전기초)' → '기초')
        lab = _DATE_PREFIX_RE.sub("", raw)
        lab = _BLOCK_TAG_RE.sub(lambda m: m.group(2), lab)   # 초/말 유지
        lab = _norm_label(lab)
        if not lab:
            continue
        for c, col_lab in cols.items():
            from .textutil import try_number
            v = try_number(ws.cell(row=r, column=c).value)
            if v is not None:
                grid[(lab, col_lab)] = v
    return grid, sorted(set(cols.values()))


def recon_ce(cur_ctx, pri_ctx, sheet, tolerance=0):
    cur_grid, _ = _ce_grid(cur_ctx, sheet, "전기")
    pri_grid, _ = _ce_grid(pri_ctx, sheet, "당기")
    rows = []
    for (rl, cl), v in sorted(cur_grid.items()):
        pv = pri_grid.get((rl, cl))
        ok, note = _verdict(v, pv, tolerance)
        rows.append({"label": f"{rl} × {cl}", "cur_prior": v,
                     "pri_current": pv, "true": ok, "note": note})
    return rows


# ---------------------------------------------------------------------------
# 주석 대사 (제목 매칭 → 표 셀 대조)
# ---------------------------------------------------------------------------

def _note_title_norm(ws):
    v = str(ws.cell(1, 1).value or "")
    return _norm_label(re.sub(r"^\d+\.\s*", "", v))


def match_note_titles(cur_ctx, pri_ctx):
    """제목 정규화 매칭 (번호 무시). [(당기시트, 전기시트|None, 제목)]"""
    pri_titles = {}
    for s in pri_ctx.note_sheets:
        pri_titles.setdefault(_note_title_norm(pri_ctx.wb[s]), s)
    out = []
    for s in cur_ctx.note_sheets:
        t = _note_title_norm(cur_ctx.wb[s])
        out.append((s, pri_titles.get(t),
                    str(cur_ctx.wb[s].cell(1, 1).value or "")))
    return out


def _period_cols(ws, rowmap, region, want):
    """표 헤더에서 '당기'/'전기' 표기 열 탐지 (라벨 없는 표는 빈 목록)."""
    header_rows = region[:2]
    cols = []
    for r in header_rows:
        for c in rowmap.get(r, []):
            txt = str(ws.cell(row=r, column=c).value or "")
            if want in txt.replace(" ", ""):
                cols.append(c)
    return sorted(set(cols))


def _row_label_set(ws, region):
    return {_norm_label(_label(ws, r)) for r in region[1:]
            if _norm_label(_label(ws, r))}


def _pair_regions(ws_c, regs_c, ws_p, regs_p):
    """표 쌍 매칭: 순서 zip이 아니라 행 라벨 집합 자카드 최적 매칭.

    (연도 간 표 삽입·삭제·순서 이동에 강건 — 실측: 순서 zip은 대량
    '항목 없음' 오탐)
    반환: (pairs, unpaired) — unpaired는 [(당기 region 번호, 원인, 최고자카드)]
    """
    sets_c = [_row_label_set(ws_c, r) for r in regs_c]
    sets_p = [_row_label_set(ws_p, r) for r in regs_p]
    pairs, unpaired = [], []
    used_p = set()
    for i, sc in enumerate(sets_c):
        best, best_j = 0.0, None
        for j, sp in enumerate(sets_p):
            if j in used_p or not sc or not sp:
                continue
            jac = len(sc & sp) / len(sc | sp)
            if jac > best:
                best, best_j = jac, j
        if best_j is not None and best >= 0.3:
            used_p.add(best_j)
            pairs.append((i, regs_c[i], regs_p[best_j]))
        else:
            if not sc:
                reason = "행 라벨 없는 표(헤더만/수치 그리드)"
            elif len(regs_p) == len(used_p):
                reason = "전기 쪽 잔여 표 없음(신규 표 추정)"
            elif best > 0:
                reason = f"행 라벨 자카드 {best:.2f} < 0.30 (구조 상이)"
            else:
                reason = "행 라벨 공통분모 없음(신규 표 추정)"
            unpaired.append((i + 1, reason, round(best, 2)))
    return pairs, unpaired


def recon_note_tables(cur_ctx, pri_ctx, cur_sheet, pri_sheet, tolerance=0):
    """매칭된 주석 쌍의 표들: 당기표 '전기' 열 ↔ 전기표 '당기' 열."""
    ws_c, ws_p = cur_ctx.wb[cur_sheet], pri_ctx.wb[pri_sheet]
    rm_c, rm_p = cur_ctx.rowmaps[cur_sheet], pri_ctx.rowmaps[pri_sheet]
    regs_c, regs_p = _regions(rm_c), _regions(rm_p)
    from .textutil import try_number

    results, skipped = [], 0
    unpaired_out = []
    paired, unpaired = _pair_regions(ws_c, regs_c, ws_p, regs_p)
    for idx, reason, jac in unpaired:
        unpaired_out.append({"table": idx, "reason": reason, "jaccard": jac})
    def _col_header(ws, rowmap, region, c):
        parts = []
        for r in region[:2]:
            v = ws.cell(row=r, column=c).value
            if v:
                parts.append(str(v).replace("\n", ""))
        return " / ".join(parts)

    for ti, (ci, reg_c, reg_p) in enumerate(paired, 1):
        cols_c = _period_cols(ws_c, rm_c, reg_c, "전기")
        cols_p = _period_cols(ws_p, rm_p, reg_p, "당기")
        if not cols_c or not cols_p:
            skipped += 1
            continue
        hdr_c = {c: _col_header(ws_c, rm_c, reg_c, c) for c in cols_c}
        hdr_p = {c: _col_header(ws_p, rm_p, reg_p, c) for c in cols_p}
        addr_to_hdr_p = {f"{get_column_letter(c)}": hdr_p[c] for c in cols_p}

        # 열 대응: 기간(당기/전기) 외 헤더 시맨틱 매칭 — j-순서 대응은
        # '장부금액↔보유주식수' 류 오탐 실측(38건 전원)으로 폐기.
        # 시맨틱이 비어있는 단순 표(헤더가 기간뿐)만 순서 대응 유지.
        def _sem(hdr):
            return _norm2(re.sub(r"당\s*기|전\s*기|말|초", "", hdr))

        col_pair = {}                          # cols_c → cols_p | None
        used = set()
        for c in cols_c:
            sc = _sem(hdr_c[c])
            hit = None
            for p in cols_p:
                if p in used:
                    continue
                if _sem(hdr_p[p]) == sc:
                    hit = p
                    break
            if hit is None and not sc:
                hit = next((p for p in cols_p
                            if p not in used and not _sem(hdr_p[p])), None)
            if hit is not None:
                used.add(hit)
            else:
                unpaired_out.append({
                    "table": ti,
                    "reason": f"열 시맨틱 불일치 — 당기 열 "
                              f"'{hdr_c[c][:30]}'에 대응하는 전기 열 없음",
                    "jaccard": ""})
            col_pair[c] = hit                  # None = 열 시맨틱 불일치
        pri_vals = {}                       # (라벨, 전기열) → (값, 셀주소)
        pri_pool = []                       # 전기표 당기열 전체 (오탐 스캔 풀)
        for r in reg_p[1:]:
            lab = _norm_label(_label(ws_p, r))
            for c in cols_p:
                v = try_number(ws_p.cell(row=r, column=c).value)
                if v is None:
                    continue
                addr = f"{get_column_letter(c)}{r}"
                pri_pool.append((v, addr, _label(ws_p, r)))
                if lab:
                    pri_vals.setdefault((lab, c), (v, addr))
        for r in reg_c[1:]:
            lab = _norm_label(_label(ws_c, r))
            if not lab:
                continue
            for j, c in enumerate(cols_c):
                v = try_number(ws_c.cell(row=r, column=c).value)
                if v is None:
                    continue
                pc = col_pair.get(c)
                if pc is None:                 # 열 시맨틱 불일치 — 대사 불가
                    continue
                hitp = pri_vals.get((lab, pc))
                pv, paddr = hitp if hitp else (None, None)
                ok, note = _verdict(v, pv, tolerance)
                # 오탐 스캔: 같은 값이 전기표 당기열의 "다른 셀"에 존재하면
                # 행 매칭 오류(오탐) 후보 — 사용자 육안 판정용 표시
                mism = None
                if not ok and pv is not None:
                    cand = [(pw, aw, lw) for pw, aw, lw in pri_pool
                            if pw == v and aw != paddr]
                    if cand:
                        mism = (f"오탐 후보 — 같은 값이 전기표 "
                                f"{cand[0][1]}('{cand[0][2].strip()[:16]}')에 존재")
                paddr_col = re.match(r"([A-Z]+)", paddr).group(1) \
                    if paddr else None
                results.append({
                    "table": ti, "label": _label(ws_c, r), "col": j + 1,
                    "cur_prior": v, "pri_current": pv, "true": ok,
                    "note": note, "cur_addr": f"{get_column_letter(c)}{r}",
                    "pri_addr": paddr, "cur_sheet": cur_sheet,
                    "pri_sheet": pri_sheet, "mismatch_flag": mism,
                    "cur_col_hdr": hdr_c.get(c, ""),
                    "pri_col_hdr": addr_to_hdr_p.get(paddr_col, "")
                    if paddr_col else ""})
    return results, skipped, unpaired_out


# ---------------------------------------------------------------------------
# 실무 양식 병렬 시트 (한진칼_전기대사_문용.xlsb 실측 재현)
# 좌측 = 당기 원문 | 판정(셀 참조 수식 =좌전기셀=우당기셀) | 우측 = 전기 원문
# ---------------------------------------------------------------------------

def _copy_block(dst_ws, src_ws, rows, cols, dst_row0, dst_col0, row_map):
    """원문 블록 복사 (값만). row_map: 원본행 → 출력행."""
    for r in rows:
        out_r = row_map(r)
        if out_r is None:
            continue
        for i, c in enumerate(cols):
            v = src_ws.cell(row=r, column=c).value
            if v is None:
                continue
            cell = dst_ws.cell(row=dst_row0 + out_r, column=dst_col0 + i)
            cell.value = v
            if isinstance(v, (int, float)):
                cell.number_format = _NUMFMT


def _side_statement(dst, cur_ctx, pri_ctx, sheet):
    """본문 시트: 당기 원문 | 판정열(전기값 열별) | 전기 원문 (행 라벨 정렬)."""
    ws_c, ws_p = cur_ctx.wb[sheet], pri_ctx.wb[sheet]
    rm_c, rm_p = cur_ctx.rowmaps[sheet], pri_ctx.rowmaps[sheet]
    periods_c, rows_c = cur_ctx.fs_sequences(sheet)
    periods_p, rows_p = pri_ctx.fs_sequences(sheet)

    all_cols_c = sorted({c for r in rm_c for c in rm_c[r]})
    all_cols_p = sorted({c for r in rm_p for c in rm_p[r]})
    width_c = max(all_cols_c) if all_cols_c else 6
    amount_c = [c for c in all_cols_c if c >= 3]
    prior_cols_c = amount_c[len(amount_c) // 2:] if len(amount_c) >= 4 \
        else amount_c[-1:]                     # 당기파일 '전기' 값 열들
    amount_p = [c for c in all_cols_p if c >= 3]
    cur_cols_p = amount_p[:len(amount_p) // 2] if len(amount_p) >= 4 \
        else amount_p[:1]                      # 전기파일 '당기' 값 열들

    verdict_col0 = width_c + 1                 # 판정열 시작
    n_verdict = len(prior_cols_c)
    right0 = verdict_col0 + n_verdict + 1      # 우측 전기 원문 시작

    # 전기 행 매핑 (2단 정규화 라벨)
    pri_by_label = {}
    for r in rows_p:
        raw = _label(ws_p, r)
        for key in (_norm1(raw), _norm2(raw)):
            if key:
                pri_by_label.setdefault(key, r)

    # 좌측: 당기 원문 전 행 그대로 (제목~표)
    max_row_c = max(rm_c) if rm_c else 1
    for r in range(1, max_row_c + 1):
        for c in range(1, width_c + 1):
            v = ws_c.cell(row=r, column=c).value
            if v is None:
                continue
            cell = dst.cell(row=r, column=c)
            cell.value = v
            if isinstance(v, (int, float)):
                cell.number_format = _NUMFMT

    from .textutil import try_number
    for r in rows_c:
        raw = _label(ws_c, r)
        pr = pri_by_label.get(_norm1(raw)) or pri_by_label.get(_norm2(raw))
        if pr is not None:
            # 우측: 전기 원문 행을 당기 행 옆에 정렬 배치
            for i, c in enumerate(all_cols_p):
                v = ws_p.cell(row=pr, column=c).value
                if v is None:
                    continue
                cell = dst.cell(row=r, column=right0 + i)
                cell.value = v
                if isinstance(v, (int, float)):
                    cell.number_format = _NUMFMT
        # 판정 수식: 당기파일 전기셀 = 전기파일 당기셀 (실무 양식 그대로)
        for k, pc in enumerate(prior_cols_c):
            if try_number(ws_c.cell(row=r, column=pc).value) is None:
                continue
            vcell = dst.cell(row=r, column=verdict_col0 + k)
            if pr is not None and k < len(cur_cols_p):
                right_col = right0 + all_cols_p.index(cur_cols_p[k])
                vcell.value = (f"={get_column_letter(pc)}{r}="
                               f"{get_column_letter(right_col)}{r}")
            else:
                vcell.value = "FALSE"          # 전기 보고서에 항목 없음
                vcell.fill = _FALSE_FILL
    hdr = dst.cell(row=max(1, min(rm_c) - 1), column=verdict_col0)
    hdr.value = "판정"
    hdr.font = _BOLD


def _side_note(dst, cur_ctx, pri_ctx, cur_sheet, pri_sheet):
    """주석 시트: 표 쌍·행 라벨 매칭으로 좌우 병렬 + 판정 수식."""
    ws_c = cur_ctx.wb[cur_sheet]
    rm_c = cur_ctx.rowmaps[cur_sheet]
    from .textutil import try_number

    # 좌측: 당기 원문 전체
    all_cols_c = sorted({c for r in rm_c for c in rm_c[r]})
    width_c = max(all_cols_c) if all_cols_c else 3
    for r in sorted(rm_c):
        for c in rm_c[r]:
            v = ws_c.cell(row=r, column=c).value
            if v is None:
                continue
            cell = dst.cell(row=r, column=c)
            cell.value = v
            if isinstance(v, (int, float)):
                cell.number_format = _NUMFMT

    if pri_sheet is None:
        dst.cell(row=1, column=width_c + 2,
                 value="전기 보고서에 대응 주석 없음 — 수동 확인").font = _BOLD
        return

    ws_p = pri_ctx.wb[pri_sheet]
    rm_p = pri_ctx.rowmaps[pri_sheet]
    regs_c, regs_p = _regions(rm_c), _regions(rm_p)
    paired, _ = _pair_regions(ws_c, regs_c, ws_p, regs_p)
    verdict_col = width_c + 1
    right0 = width_c + 3

    for ci, reg_c, reg_p in paired:
        cols_c = _period_cols(ws_c, rm_c, reg_c, "전기")
        cols_p = _period_cols(ws_p, rm_p, reg_p, "당기")
        all_cols_p = sorted({c for r in reg_p for c in rm_p.get(r, [])})
        pri_rows = {}
        for r in reg_p[1:]:
            for key in (_norm1(_label(ws_p, r)), _norm2(_label(ws_p, r))):
                if key:
                    pri_rows.setdefault(key, r)
        for r in reg_c[1:]:
            raw = _label(ws_c, r)
            pr = pri_rows.get(_norm1(raw)) or pri_rows.get(_norm2(raw))
            if pr is None:
                continue
            for i, c in enumerate(all_cols_p):
                v = ws_p.cell(row=pr, column=c).value
                if v is None:
                    continue
                cell = dst.cell(row=r, column=right0 + i)
                cell.value = v
                if isinstance(v, (int, float)):
                    cell.number_format = _NUMFMT
            if cols_c and cols_p and \
                    try_number(ws_c.cell(row=r, column=cols_c[0]).value) \
                    is not None:
                right_col = right0 + all_cols_p.index(cols_p[0]) \
                    if cols_p[0] in all_cols_p else None
                if right_col:
                    dst.cell(row=r, column=verdict_col).value = (
                        f"={get_column_letter(cols_c[0])}{r}="
                        f"{get_column_letter(right_col)}{r}")


def write_side_by_side(cur_ctx, pri_ctx, note_map, wb):
    """실무 양식 상세 시트들을 wb에 추가 (요약/FALSE분해는 별도 유지)."""
    for sheet in cur_ctx.fs_sheets:
        if sheet not in pri_ctx.fs_sheets:
            continue
        dst = wb.create_sheet(sheet)
        _side_statement(dst, cur_ctx, pri_ctx, sheet)
        dst.column_dimensions["A"].width = 34
    for cur_s, pri_s, _title in note_map:
        dst = wb.create_sheet(cur_s)
        _side_note(dst, cur_ctx, pri_ctx, cur_s, pri_s)
        dst.column_dimensions["A"].width = 30


# ---------------------------------------------------------------------------
# 실행 + 엑셀 출력
# ---------------------------------------------------------------------------

def recon(cur_path, prior_path, out_path=None, tolerance=0, progress=None):
    with tempfile.TemporaryDirectory(prefix="recon_") as tmp:
        cur_x = _to_xlsx(cur_path, tmp)
        pri_x = _to_xlsx(prior_path, tmp)
        cur_ctx = FootingContext(cur_x)
        pri_ctx = FootingContext(pri_x)

        stmt_results = {}
        for sheet in cur_ctx.fs_sheets:
            if sheet not in pri_ctx.fs_sheets:
                continue
            if sheet.endswith("CE"):
                stmt_results[sheet] = recon_ce(cur_ctx, pri_ctx, sheet,
                                               tolerance)
            else:
                stmt_results[sheet] = recon_statement(cur_ctx, pri_ctx,
                                                      sheet, tolerance)
            if progress:
                progress(f"  [{sheet}] {len(stmt_results[sheet])}건 대사")

        note_map = match_note_titles(cur_ctx, pri_ctx)
        note_results = {}
        note_skipped = {}
        note_unpaired = {}
        for cur_s, pri_s, title in note_map:
            if pri_s is None:
                continue
            res, skipped, unpaired = recon_note_tables(
                cur_ctx, pri_ctx, cur_s, pri_s, tolerance)
            if res or skipped or unpaired:
                note_results[cur_s] = res
                note_skipped[cur_s] = skipped
                note_unpaired[cur_s] = unpaired

        # 제목 매칭 실패 원인 진단 (양쪽 제목을 병기해 육안 확인 가능하게)
        title_misses = []
        pri_titles_all = [
            (s, str(pri_ctx.wb[s].cell(1, 1).value or ""))
            for s in pri_ctx.note_sheets]
        for cur_s, pri_s, title in note_map:
            if pri_s is not None:
                continue
            qn = _norm_label(re.sub(r"^\d+\.\s*", "", title))
            near = sorted(
                pri_titles_all,
                key=lambda t: -len(set(qn) & set(_norm_label(
                    re.sub(r"^\d+\.\s*", "", t[1])))))[:2]
            title_misses.append({"cur_sheet": cur_s, "title": title,
                                 "nearest": near})

        if out_path is None:
            base = re.sub(r"\.(dsd|xlsx)$", "", os.path.basename(cur_path),
                          flags=re.I)
            out_path = os.path.join(
                os.path.dirname(os.path.abspath(cur_path)),
                f"전기대사_{base}.xlsx")
        summary = _write_recon_excel(stmt_results, note_map, note_results,
                                     note_skipped, out_path, cur_path,
                                     prior_path, tolerance,
                                     note_unpaired=note_unpaired,
                                     title_misses=title_misses,
                                     cur_ctx=cur_ctx, pri_ctx=pri_ctx)
    return summary


def _write_recon_excel(stmt_results, note_map, note_results, note_skipped,
                       out_path, cur_path, prior_path, tolerance,
                       note_unpaired=None, title_misses=None,
                       cur_ctx=None, pri_ctx=None):
    note_unpaired = note_unpaired or {}
    title_misses = title_misses or []
    wb = Workbook()
    ws0 = wb.active
    ws0.title = "요약"

    def _counts(rows):
        n = len(rows)
        t = sum(1 for r in rows if r["true"])
        return n, t, n - t

    stmt_n = stmt_t = note_n = note_t = 0
    lines = []
    for sheet, rows in stmt_results.items():
        n, t, f = _counts(rows)
        stmt_n += n
        stmt_t += t
        lines.append(("본문", sheet, n, t, f))
    for sheet, rows in note_results.items():
        n, t, f = _counts(rows)
        note_n += n
        note_t += t
        lines.append(("주석", sheet, n, t, f))

    ws0.append(["전기대사 결과"])
    ws0.cell(1, 1).font = Font(bold=True, size=14)
    ws0.append([f"당기: {os.path.basename(cur_path)}  ↔  전기: "
                f"{os.path.basename(prior_path)}  (허용오차 ±{tolerance})"])
    ws0.append([GUIDE])
    ws0.cell(3, 1).fill = PatternFill("solid", start_color="FFEB9C")
    ws0.cell(3, 1).font = _BOLD
    ws0.append([])
    total_false = (stmt_n - stmt_t) + (note_n - note_t)
    ws0.append([f"전체 판정: {'TRUE' if total_false == 0 else 'FALSE'} "
                f"(본문 대사 {stmt_n} · TRUE {stmt_t} · FALSE "
                f"{stmt_n - stmt_t} / 주석 대사 {note_n} · TRUE {note_t} · "
                f"FALSE {note_n - note_t})"])
    ws0.cell(5, 1).font = _BOLD
    ws0.append([])
    ws0.append(["구분", "시트", "대사", "TRUE", "FALSE", "시트 링크"])
    for c in ws0[7]:
        c.font = _BOLD
        c.fill = _HDR_FILL
    for kind, sheet, n, t, f in lines:
        ws0.append([kind, sheet, n, t, f,
                    f'=HYPERLINK("#\'{sheet}\'!A1","시트 바로가기")'])
        ws0.cell(ws0.max_row, 6).font = _LINK_FONT
        if f:
            ws0.cell(ws0.max_row, 5).fill = _FALSE_FILL
    # 주석 제목 매핑표
    ws0.append([])
    ws0.append(["주석 제목 매핑 (번호가 아니라 제목 기준)"])
    ws0.cell(ws0.max_row, 1).font = _BOLD
    ws0.append(["당기 주석", "전기 주석", "제목", "표 대사"])
    for c in ws0[ws0.max_row]:
        c.font = _BOLD
        c.fill = _HDR_FILL
    matched = 0
    for cur_s, pri_s, title in note_map:
        matched += int(pri_s is not None)
        skipped = note_skipped.get(cur_s, 0)
        state = ("미매칭 — 수동 확인" if pri_s is None else
                 f"대사 {len(note_results.get(cur_s, []))}건"
                 + (f" (기간열 없는 표 {skipped}개 스킵" ")" if skipped
                    else ""))
        ws0.append([cur_s, pri_s or "-", title[:60], state])
        if pri_s is None:
            ws0.cell(ws0.max_row, 4).fill = _FALSE_FILL
    ws0.column_dimensions["A"].width = 14
    ws0.column_dimensions["C"].width = 50
    for col in ("B", "D", "E", "F"):
        ws0.column_dimensions[col].width = 16

    # 상세 시트 — 실무 양식(문용.xlsb) 병렬 배치: 당기 원문 | 판정 수식 |
    # 전기 원문. 판정 근거는 셀 참조 수식이라 엑셀에서 추적 가능.
    if cur_ctx is not None and pri_ctx is not None:
        write_side_by_side(cur_ctx, pri_ctx, note_map, wb)

    breakdown = _write_false_breakdown(wb, note_results, note_unpaired,
                                       title_misses)

    wb.save(out_path)
    return {"out_path": out_path,
            "stmt": {"n": stmt_n, "true": stmt_t, "false": stmt_n - stmt_t},
            "notes": {"n": note_n, "true": note_t,
                      "false": note_n - note_t},
            "note_matched": matched, "note_total": len(note_map),
            "stmt_results": stmt_results, "note_results": note_results,
            "breakdown": breakdown}


def _write_false_breakdown(wb, note_results, note_unpaired, title_misses):
    """[FALSE분해] 시트 — 주석 FALSE 전수 사유 분해 (벤치마크 기준 확정판).

    ① 항목 없음(신규/소멸 행): 목록
    ② 값 상이: 당기/전기 셀 주소·값 병기 + 오탐 후보(같은 값이 전기표
       당기열의 다른 셀에 존재 = 행 매칭 오류 의심) 표시 — 게이트: 오탐 0건
    ③ 표 쌍 매칭 실패: 원인별
    ④ 제목 매칭 실패: 원인(최근접 전기 제목 병기)
    """
    ws = wb.create_sheet("FALSE분해")
    warn = PatternFill("solid", start_color="FFEB9C")

    def _hdr_row(cells):
        ws.append(cells)
        for c in ws[ws.max_row]:
            c.font = _BOLD
            c.fill = _HDR_FILL

    missing, differs = [], []
    for sheet, rows in note_results.items():
        for r in rows:
            if r["true"]:
                continue
            if "항목 없음" in r["note"]:
                missing.append(r)
            else:
                differs.append(r)

    ws.append(["① 항목 없음 (신규/소멸 행) — 정당한 FALSE 후보 목록"])
    ws.cell(ws.max_row, 1).font = _BOLD
    _hdr_row(["주석", "표", "행 라벨", "당기 셀", "당기보고서 전기값"])
    for r in missing:
        ws.append([r["cur_sheet"], r["table"], r["label"],
                   f"'{r['cur_sheet']}'!{r['cur_addr']}", r["cur_prior"]])
        ws.cell(ws.max_row, 5).number_format = _NUMFMT
    ws.append([])

    ws.append(["② 값 상이 — 셀 주소·값·열 헤더 병기 (오탐 후보는 육안 확인 대상)"])
    ws.cell(ws.max_row, 1).font = _BOLD
    _hdr_row(["주석", "표", "행 라벨", "당기 셀", "당기보고서 전기값",
              "당기 열 헤더", "전기 셀", "전기보고서 당기값", "전기 열 헤더",
              "차이", "오탐 후보"])
    n_mismatch_flag = 0
    for r in differs:
        diff = abs(float(r["cur_prior"]) - float(r["pri_current"])) \
            if r["pri_current"] is not None else None
        flag = r.get("mismatch_flag") or ""
        if flag:
            n_mismatch_flag += 1
        ws.append([r["cur_sheet"], r["table"], r["label"],
                   f"'{r['cur_sheet']}'!{r['cur_addr']}", r["cur_prior"],
                   r.get("cur_col_hdr", ""),
                   f"'{r['pri_sheet']}'!{r['pri_addr']}", r["pri_current"],
                   r.get("pri_col_hdr", ""), diff, flag])
        for col in (5, 8, 10):
            ws.cell(ws.max_row, col).number_format = _NUMFMT
        if flag:
            for c in ws[ws.max_row]:
                c.fill = warn
    ws.append([])

    ws.append(["③ 표 쌍 매칭 실패 — 원인별"])
    ws.cell(ws.max_row, 1).font = _BOLD
    _hdr_row(["주석", "당기 표 번호", "원인", "최고 자카드"])
    n_unpaired = 0
    for sheet, items in note_unpaired.items():
        for u in items:
            n_unpaired += 1
            ws.append([sheet, u["table"], u["reason"], u["jaccard"]])
    ws.append([])

    ws.append(["④ 제목 매칭 실패 — 원인 (최근접 전기 제목 병기)"])
    ws.cell(ws.max_row, 1).font = _BOLD
    _hdr_row(["당기 주석", "당기 제목", "최근접 전기 제목 1", "최근접 전기 제목 2"])
    for t in title_misses:
        near = [f"[{s}] {ttl[:40]}" for s, ttl in t["nearest"]]
        ws.append([t["cur_sheet"], t["title"][:60],
                   near[0] if near else "", near[1] if len(near) > 1 else ""])

    for col, w in (("A", 8), ("B", 8), ("C", 34), ("D", 20), ("E", 18),
                   ("F", 20), ("G", 18), ("H", 14), ("I", 44)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    return {"missing": len(missing), "differs": len(differs),
            "mismatch_flags": n_mismatch_flag, "unpaired": n_unpaired,
            "title_misses": len(title_misses)}
