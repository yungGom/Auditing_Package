"""F-3b: 롤포워드 세팅 — 전기 반기 DSD × 기말 인스턴스 → 당기 스캐폴드.

조립 패치 (신규 매칭 코드 금지):
- 범위 = ① 전기 반기 DSD extract의 시트·표 구성 (FootingContext)
- 태깅 = F-3 SuccessionAssets (element·확장·role 승계, D-4c 병기)
- 전기말 시점 값 = ② 기말 인스턴스 팩트 직결 — V-1 `_current_fact`
  컨텍스트 선별 재사용, 폴백은 ③ 기말 DSD의 A-5b 매칭 역방향
  (match_note_titles·_pair_regions·행 라벨)
- 동반기 흐름 값 = ①의 당기(제N기) 열 그대로
- 기간 롤포워드 = 당기 위치 라벨만 제N기·연도 +1 (비교 열은 유지)
- 미매칭 = 빈칸 + '수동 확인' (미매칭≠0)

경계: 팩트는 호출자(조립층)가 dict로 전달 — 이 모듈은 dart_explorer를
모른다 (V-1과 동일). LLM 불사용.
"""
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from .foot import FootingContext, _label, _regions
from .recon import _norm_label, _pair_regions, match_note_titles
from .xbrl_recon import _MEMBER, _current_fact

_BOLD = Font(bold=True)
_HDR_FILL = PatternFill("solid", start_color="D9E1F2")
_WARN_FILL = PatternFill("solid", start_color="FFEB9C")
_PRE_FILL = PatternFill("solid", start_color="E2EFDA")
_NUMFMT = "#,##0;(#,##0)"
_WRAP = Alignment(wrap_text=True, vertical="top")

S_YE = "프리필-기말"            # ② 인스턴스 팩트 직결
S_YE_DSD = "프리필-기말(DSD)"   # ③ 기말 DSD 매칭 폴백
S_HALF = "프리필-반기"          # ① 동반기 흐름 값
S_MANUAL = "수동 확인"          # 미매칭≠0 — 빈칸으로 노출
S_NEW = "신규추천"              # 갱신 모드 신규 계정

# '제 43 기' 외에 '제43(당)기말' 표기(OpenDART 기말 원본 실측)도 수용
_GISU_RE = re.compile(r"제\s*(\d+)\s*(\([당전]\))?\s*기")
_YEAR_RE = re.compile(r"(19|20)\d{2}")


def _roll_text(txt):
    """당기 위치 라벨의 기수·연도 +1 (기간 롤포워드)."""
    txt = _GISU_RE.sub(
        lambda m: f"제 {int(m.group(1)) + 1} {m.group(2) or ''}기"
        .replace("  ", " "), txt)
    return _YEAR_RE.sub(lambda m: str(int(m.group(0)) + 1), txt)


def _fs_layout(ctx, sheet):
    """본문 시트의 헤더·데이터 구조 분석.

    반환: {titles, cur_title, gisu_cur, hdr_rows, data_rows,
           cur_cols: [(col, sub_label)], pri_cols}
    기수(제N기)가 큰 열 = 당기. 서브라벨(3개월/누적)은 2단 헤더에서.
    """
    ws = ctx.wb[sheet]
    rm = ctx.rowmaps[sheet]
    regions = _regions(rm)
    if not regions:
        return None
    region = max(regions, key=len)
    # 헤더 행: 금액 열이 전부 비수치이고, (col1 공란 또는 기수 표기 존재)
    # — '과  목' 라벨이 붙는 기말 원본 헤더(실측)도 수용
    def _is_hdr(r):
        vals = [str(ws.cell(r, c).value or "") for c in rm[r] if c > 1]
        if any(_num(v) is not None and len(v) > 6 for v in vals):
            return False
        has_gisu = any(_GISU_RE.search(v) for v in vals)
        return has_gisu or not str(ws.cell(r, 1).value or "").strip()

    hdr_rows = [r for r in region[:3] if _is_hdr(r)]
    data_rows = [r for r in region if r not in hdr_rows
                 and str(_label(ws, r) or "").strip()]
    cols = sorted({c for r in data_rows for c in rm[r] if c > 1})

    # 열별 기수: 자기 헤더 → 없으면 왼쪽 열에서 승계 (2단 헤더 병합 대응)
    gisu, sub = {}, {}
    for c in cols:
        g = None
        for r in hdr_rows:
            m = _GISU_RE.search(str(ws.cell(r, c).value or ""))
            if m:
                g = int(m.group(1))
        gisu[c] = g
        s = ""
        for r in hdr_rows[1:]:
            v = str(ws.cell(r, c).value or "").strip()
            if v and not _GISU_RE.search(v):
                s = v
        sub[c] = s
    carry = None
    for c in cols:
        if gisu[c] is not None:
            carry = gisu[c]
        elif carry is not None:
            gisu[c] = carry
    known = [g for g in gisu.values() if g is not None]
    g_cur = max(known) if known else None
    cur_cols = [(c, sub[c]) for c in cols if gisu[c] == g_cur] \
        if g_cur is not None else []
    pri_cols = [(c, sub[c]) for c in cols
                if gisu[c] is not None and gisu[c] != g_cur]

    # 시트 상단 제목 행 (region 위): 당기(기수 최대) 제목줄 탐지
    titles, cur_title = [], None
    for r in range(1, region[0]):
        v = str(ws.cell(r, 1).value or "").strip()
        if not v:
            continue
        titles.append(v)
        m = _GISU_RE.search(v)
        if m and g_cur is not None and int(m.group(1)) == g_cur:
            cur_title = v
    return {"titles": titles, "cur_title": cur_title, "gisu_cur": g_cur,
            "hdr_rows": hdr_rows, "data_rows": data_rows,
            "cur_cols": cur_cols, "pri_cols": pri_cols, "region": region}


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _resolver3(resolver, eid):
    """D-2c 리졸버 → [한글 표준레이블, 영문명, ID] (자산 없으면 빈칸)."""
    if not resolver or not eid:
        return "", "", (eid or "").replace("_", ":", 1)
    r = resolver.resolve(eid)
    return (r["ko"] if r["standard"] else "(확장)", r["en"], r["qname"])


def _ye_dsd_note_index(ctx_ye):
    """③ 기말 DSD 주석: 제목 정규화 → (시트, 표별 행라벨→당기값)."""
    out = {}
    for s in ctx_ye.note_sheets:
        ws = ctx_ye.wb[s]
        t = _norm_label(re.sub(r"^\d+\.\s*", "",
                               str(ws.cell(1, 1).value or "")))
        out[t] = s
    return out


def _table_cur_values(ctx, sheet, region):
    """표 하나의 행라벨→당기 열 값 dict (기수 최대 열 기준)."""
    ws = ctx.wb[sheet]
    rm = ctx.rowmaps[sheet]
    hdr = region[:2]
    gisu = {}
    for r in hdr:
        for c in rm.get(r, []):
            m = _GISU_RE.search(str(ws.cell(r, c).value or ""))
            if m:
                gisu[c] = int(m.group(1))
    if not gisu:
        # 기수 미표기 표 — '당기' 문구 탐지 폴백
        for r in hdr:
            for c in rm.get(r, []):
                if "당" in str(ws.cell(r, c).value or "").replace(" ", ""):
                    gisu[c] = 1
    if not gisu:
        return {}
    g_max = max(gisu.values())
    cur_cols = [c for c, g in gisu.items() if g == g_max]
    vals = {}
    for r in region:
        if r in hdr:
            continue
        lab = _norm_label(_label(ws, r) or "")
        if not lab:
            continue
        for c in cur_cols:
            n = _num(ws.cell(r, c).value)
            if n is not None:
                vals.setdefault(lab, n)
                break
    return vals


def rollforward(half_xlsx, facts_ye, doc_end_ye, succession,
                ye_xlsx=None, resolver=None, member="별도",
                out_path=None, current_xlsx=None, recommend=None,
                source_warning=None, progress=None):
    """① 전기 반기 extract ×② 기말 팩트(+승계 자산) → 당기 스캐폴드.

    facts_ye: {element_id: [{value, decimals, type, start, end, dims}]}
    succession: SuccessionAssets (F-3)
    ye_xlsx: ③ 기말 DSD extract 경로 — 주석 폴백
    current_xlsx: 갱신 모드 — 당기 DSD extract (①과 diff)
    recommend: callable(label)->[element_id...] — 신규 계정 D-3b 추천
    """
    doc_end_ye = str(doc_end_ye)
    ctx = FootingContext(half_xlsx)
    ctx_ye = FootingContext(ye_xlsx) if ye_xlsx else None
    # 연결/별도: 시트명 우선(V-1과 동일), 기본은 ① 문서 구성을 따름
    if any("연결" in s for s in ctx.fs_sheets):
        member = "연결"
    mem = _MEMBER.get(member, _MEMBER["별도"])
    cur_ctx = FootingContext(current_xlsx) if current_xlsx else None

    counts = {S_YE: 0, S_YE_DSD: 0, S_HALF: 0, S_MANUAL: 0}
    tag = {"승계": 0, "유사": 0, "미매칭": 0}
    g3_texts = []                       # 당기 위치 라벨 전수 (G3 검사 대상)
    update = {"new": [], "changed": []}
    sheets_out = {}

    # ③ 기말 DSD: 본문 BS 행라벨→당기값 / 주석 제목 인덱스
    ye_bs_vals, ye_note_idx = {}, {}
    if ctx_ye is not None:
        for s in ctx_ye.fs_sheets:
            if s.endswith("BS"):
                lay = _fs_layout(ctx_ye, s)
                if lay and lay["cur_cols"]:
                    ws3 = ctx_ye.wb[s]
                    c0 = lay["cur_cols"][0][0]
                    for r in lay["data_rows"]:
                        n = _num(ws3.cell(r, c0).value)
                        if n is not None:
                            ye_bs_vals.setdefault(
                                _norm_label(_label(ws3, r)), n)
        ye_note_idx = _ye_dsd_note_index(ctx_ye)

    def _inherit(label):
        """태깅 제안(0.55) + 값 프리필용 고신뢰 element(0.85) 분리."""
        inh = succession.inherit(label) if succession else None
        eid_tag = inh["element_id"] if inh else None
        sim = inh.get("sim", 1.0) if inh else None
        basis = ("승계" if inh and sim >= 1.0
                 else f"승계(유사 {sim:.2f})" if inh else "")
        hi = succession.inherit(label, min_sim=0.85) if succession else None
        eid_val = hi["element_id"] if hi else None
        if inh:
            tag["승계" if sim >= 1.0 else "유사"] += 1
        else:
            tag["미매칭"] += 1
        return eid_tag, basis, eid_val

    def _ye_prefill(label, eid_val, note_title_norm=None):
        """전기말 시점 값: ② 팩트 → ③ DSD → None."""
        if eid_val:
            for kind in ("instant", "duration"):
                f = _current_fact(facts_ye, eid_val, doc_end_ye, mem, kind)
                if f is not None:
                    return float(f["value"]), S_YE
        lab = _norm_label(label)
        if note_title_norm is None and lab in ye_bs_vals:
            return ye_bs_vals[lab], S_YE_DSD
        if note_title_norm is not None:
            vals = ye_note_vals.get(note_title_norm) or {}
            if lab in vals:
                return vals[lab], S_YE_DSD
        return None, None

    # ── 본문 FS ──────────────────────────────────────────────
    for sheet in ctx.fs_sheets:
        lay = _fs_layout(ctx, sheet)
        if lay is None:
            continue
        ws = ctx.wb[sheet]
        mem = _MEMBER["연결" if "연결" in sheet else member]
        is_bs = sheet.endswith("BS")
        is_ce = sheet.endswith("CE")
        cur_cols = lay["cur_cols"]
        # 당기 열 라벨(롤) — G3 대상
        cur_hdr = _roll_text(lay["cur_title"] or f"제 {lay['gisu_cur']} 기") \
            if lay["gisu_cur"] else "당기"
        g3_texts.append(cur_hdr)
        sub_labels = [s or "금액" for _, s in cur_cols] or ["금액"]
        if is_bs:
            cmp_labels = [f"전기말 {doc_end_ye}"]
        elif is_ce:
            cmp_labels = []
        else:
            cmp_labels = [f"전반기 {s}".strip() for s in sub_labels]

        rows = []
        for r in lay["data_rows"]:
            label = _label(ws, r)
            eid, basis, eid_val = _inherit(label)
            d4c = ""
            if succession and eid:
                tc = succession.taxcheck_of(eid)
                if isinstance(tc, dict):
                    d4c = tc.get("status") or ""
                    if d4c and d4c != "녹색":
                        d4c += f" — {tc.get('detail', '')}"
                else:
                    d4c = tc or ""
            ko, en, qn = _resolver3(resolver, eid)
            cmp_vals, src = [], None
            if is_ce:
                src = S_MANUAL
            elif is_bs:
                v, src = _ye_prefill(label, eid_val)
                cmp_vals = [v]
                src = src or S_MANUAL
            else:
                cmp_vals = [_num(ws.cell(r, c).value) for c, _ in cur_cols]
                src = S_HALF if any(v is not None for v in cmp_vals) \
                    else S_MANUAL
            counts[src] += 1
            rows.append({
                "label": label, "indent": ws.cell(r, 1).alignment.indent
                if ws.cell(r, 1).alignment else 0,
                "cmp": cmp_vals, "src": src, "element": eid,
                "basis": basis, "ko": ko, "en": en, "qname": qn,
                "d4c": d4c or "",
            })
        sheets_out[sheet] = {
            "kind": "fs", "titles": lay["titles"], "cur_hdr": cur_hdr,
            "sub_labels": sub_labels, "cmp_labels": cmp_labels,
            "rows": rows,
        }
        if progress:
            progress(f"  [{sheet}] {len(rows)}행 스캐폴드")

    # ── 주석 ────────────────────────────────────────────────
    mem = _MEMBER.get(member, _MEMBER["별도"])   # 문서 유형 기준으로 복원
    ye_note_vals = {}
    note_pairs = {}
    if ctx_ye is not None:
        for cur_s, ye_s, _t in match_note_titles(ctx, ctx_ye):
            if ye_s:
                note_pairs[cur_s] = ye_s
    for s in ctx.note_sheets:
        ws = ctx.wb[s]
        title = str(ws.cell(1, 1).value or "")
        t_norm = _norm_label(re.sub(r"^\d+\.\s*", "", title))
        role = succession.find_role(title) if succession else None
        # ③ 매칭 주석의 표별 당기값 인덱스 (표 자카드 페어링)
        if t_norm not in ye_note_vals and ctx_ye is not None \
                and s in note_pairs:
            ye_s = note_pairs[s]
            vals = {}
            ws3 = ctx_ye.wb[ye_s]
            regs_c = _regions(ctx.rowmaps[s])
            regs_p = _regions(ctx_ye.rowmaps[ye_s])
            pairs, _un = _pair_regions(ws, regs_c, ws3, regs_p)
            for _i, _rc, rp in pairs:
                vals.update(_table_cur_values(ctx_ye, ye_s, rp))
            ye_note_vals[t_norm] = vals

        rows = []
        rm = ctx.rowmaps[s]
        for region in _regions(rm):
            cur_vals = _table_cur_values(ctx, s, region)
            hdr = region[:2]
            for r in region:
                if r in hdr:
                    continue
                label = _label(ws, r)
                if not str(label or "").strip():
                    continue
                lab = _norm_label(label)
                eid, basis, eid_val = _inherit(label)
                ko, en, qn = _resolver3(resolver, eid)
                half_v = cur_vals.get(lab)
                ye_v, ye_src = _ye_prefill(label, eid_val,
                                           note_title_norm=t_norm)
                if ye_src:
                    src = ye_src
                elif half_v is not None:
                    src = S_HALF
                else:
                    src = S_MANUAL
                counts[src] += 1
                rows.append({"label": label, "half": half_v, "ye": ye_v,
                             "src": src, "element": eid, "basis": basis,
                             "ko": ko, "qname": qn})
        rolled_title = _roll_text(title)
        g3_texts.append(rolled_title)
        sheets_out[s] = {"kind": "note", "title": rolled_title,
                         "role": role or "수동", "rows": rows}

    # ── 갱신 모드: 당기 DSD diff (신규만 추천, 변경 감지) ──
    if cur_ctx is not None:
        for sheet in cur_ctx.fs_sheets:
            lay_c = _fs_layout(cur_ctx, sheet)
            if lay_c is None or sheet not in sheets_out:
                continue
            base = {_norm_label(r["label"]): r
                    for r in sheets_out[sheet]["rows"]}
            lay_b = _fs_layout(ctx, sheet)
            base_vals = {}
            if lay_b:
                wsb = ctx.wb[sheet]
                for r in lay_b["data_rows"]:
                    n = _num(wsb.cell(r, lay_b["cur_cols"][0][0]).value) \
                        if lay_b["cur_cols"] else None
                    base_vals[_norm_label(_label(wsb, r))] = n
            wsc = cur_ctx.wb[sheet]
            for r in lay_c["data_rows"]:
                label = _label(wsc, r)
                lab = _norm_label(label)
                v = _num(wsc.cell(r, lay_c["cur_cols"][0][0]).value) \
                    if lay_c["cur_cols"] else None
                if lab not in base:
                    cands = list(recommend(label)) if recommend else []
                    update["new"].append({"sheet": sheet, "label": label,
                                          "candidates": cands[:4]})
                elif lab in base_vals and base_vals[lab] is not None \
                        and v is not None and v != base_vals[lab]:
                    update["changed"].append({"sheet": sheet,
                                              "label": label,
                                              "old": base_vals[lab],
                                              "new": v})

    prefilled = counts[S_YE] + counts[S_YE_DSD] + counts[S_HALF]
    total = prefilled + counts[S_MANUAL]
    # G3: 당기 위치 라벨에 전기 연도·기수 잔존 검사
    pri_years = set()
    for s in ctx.fs_sheets:
        lay = _fs_layout(ctx, s)
        if lay and lay["cur_title"]:
            pri_years.update(m.group(0)
                             for m in _YEAR_RE.finditer(lay["cur_title"]))
            pri_years.add(f"제 {lay['gisu_cur']} 기")
    g3_violations = [t for t in g3_texts
                     if any(y in t for y in pri_years)]

    summary = {
        "counts": dict(counts), "prefilled": prefilled, "total": total,
        "fill_rate": round(prefilled / total, 4) if total else None,
        "tagging": dict(tag), "doc_end_ye": doc_end_ye,
        "g3_violations": g3_violations,
        "update": update if cur_ctx is not None else None,
        "source_warning": source_warning,
        "sheets": {s: len(d["rows"]) for s, d in sheets_out.items()},
    }
    if out_path:
        _write_excel(out_path, sheets_out, summary)
        summary["out_path"] = out_path
    summary["rows"] = {s: d["rows"] for s, d in sheets_out.items()}
    return summary


def _write_excel(out_path, sheets_out, summary):
    wb = Workbook()
    ws0 = wb.active
    ws0.title = "요약"
    ws0.append(["롤포워드 스캐폴드 (F-3b) — 당기 확정 후 입력"])
    ws0.cell(1, 1).font = Font(bold=True, size=14)
    if summary.get("source_warning"):
        ws0.append([summary["source_warning"]])
        ws0.cell(ws0.max_row, 1).fill = _WARN_FILL
    ws0.append(["확정 ☐ 미기입 시 완성 아님 — 자동은 추천, 확정은 회계사"])
    ws0.cell(ws0.max_row, 1).fill = _WARN_FILL
    ws0.cell(ws0.max_row, 1).font = _BOLD
    ws0.append([])
    c = summary["counts"]
    ws0.append([f"프리필 충전율: {summary['prefilled']}/{summary['total']} "
                f"({(summary['fill_rate'] or 0):.1%})"])
    ws0.cell(ws0.max_row, 1).font = _BOLD
    ws0.append([f"출처 분해: {S_YE} {c[S_YE]} / {S_YE_DSD} {c[S_YE_DSD]} / "
                f"{S_HALF} {c[S_HALF]} / {S_MANUAL} {c[S_MANUAL]}"])
    t = summary["tagging"]
    ws0.append([f"태깅(F-3 승계): 승계 {t['승계']} / 유사 {t['유사']} / "
                f"미매칭 {t['미매칭']} — 기준 기말 보고기간말 "
                f"{summary['doc_end_ye']}"])
    if summary.get("update"):
        u = summary["update"]
        ws0.append([f"갱신 모드: 신규 {len(u['new'])}건(추천 부착) / "
                    f"값 변경 감지 {len(u['changed'])}건"])
    ws0.append([])
    ws0.append(["시트", "행", "링크"])
    for cell in ws0[ws0.max_row]:
        cell.font = _BOLD
        cell.fill = _HDR_FILL
    for s, n in summary["sheets"].items():
        ws0.append([s, n, f'=HYPERLINK("#\'{s}\'!A1","바로가기")'])
    ws0.column_dimensions["A"].width = 60

    for name, d in sheets_out.items():
        ws = wb.create_sheet(name[:31])
        if d["kind"] == "fs":
            for t in d["titles"][:1]:
                ws.append([t])
                ws.cell(ws.max_row, 1).font = _BOLD
            ws.append([f"당기: {d['cur_hdr']}"])
            ws.cell(ws.max_row, 1).font = _BOLD
            ncur = len(d["sub_labels"])
            ncmp = len(d["cmp_labels"])
            hdr = (["행 라벨"]
                   + [f"당기 {s}(당기 확정 후 입력)" for s in d["sub_labels"]]
                   + d["cmp_labels"]
                   + ["값 출처", "element ID", "한글 표준레이블", "영문명",
                      "근거", "D-4c", "확정 ☐"])
            ws.append(hdr)
            hr = ws.max_row
            for cell in ws[hr]:
                cell.font = _BOLD
                cell.fill = _HDR_FILL
                cell.alignment = _WRAP
            for r in d["rows"]:
                cmp_cells = list(r["cmp"]) + [None] * (ncmp - len(r["cmp"]))
                ws.append([r["label"]] + [None] * ncur + cmp_cells[:ncmp]
                          + [r["src"], r["qname"], r["ko"], r["en"],
                             r["basis"], r["d4c"], "☐"])
            for row in ws.iter_rows(min_row=hr + 1):
                for i in range(1, ncur + ncmp + 1):
                    row[i].number_format = _NUMFMT
                for i in range(ncur + 1, ncur + ncmp + 1):
                    if row[i].value is not None:
                        row[i].fill = _PRE_FILL
                if row[ncur + ncmp + 1].value == S_MANUAL:
                    row[ncur + ncmp + 1].fill = _WARN_FILL
            ws.column_dimensions["A"].width = 38
            ws.freeze_panes = f"A{hr + 1}"
        else:
            ws.append([d["title"]])
            ws.cell(1, 1).font = _BOLD
            ws.append([f"role: {d['role']} (F-3 승계)"])
            ws.append(["행 라벨", "당기값(당기 확정 후 입력)",
                       "전반기 프리필", "기말 프리필", "값 출처",
                       "element ID", "한글 표준레이블", "확정 ☐"])
            hr = ws.max_row
            for cell in ws[hr]:
                cell.font = _BOLD
                cell.fill = _HDR_FILL
            for r in d["rows"]:
                ws.append([r["label"], None, r["half"], r["ye"], r["src"],
                           r["qname"], r["ko"], "☐"])
                for i in (2, 3, 4):
                    ws.cell(ws.max_row, i).number_format = _NUMFMT
                if r["src"] == S_MANUAL:
                    ws.cell(ws.max_row, 5).fill = _WARN_FILL
            ws.column_dimensions["A"].width = 38
            ws.freeze_panes = f"A{hr + 1}"
    wb.save(out_path)
