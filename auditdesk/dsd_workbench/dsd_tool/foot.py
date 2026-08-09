"""Footing 검증 (패치 A-4) — DSDbreaker CB1_Footing 알고리즘 기반.

검증 3종:
1. 합계검증: 값 기반 계층 역추론(키워드 불사용) → 부모 = Σ자식 재검산
   - DSDbreaker 원전은 하단 합계 전제. 한국 FS의 2열 계층은 소계가 개별항목
     위에 오므로(상단 소계) 양방향 스캔으로 확장했다.
   - 패스마다 (하단/상단) 스캔 → 확정된 자식을 축약 → 반복 = 다단 계층
2. 주석대사: FS 셀의 주석참조("5", "6, 23") → 해당 주석 시트에서 같은 값(±2)
   탐색. 참조 없으면 전 시트 값 탐색 폴백(정보성).
3. 전기대사: 당기 파일의 "전기 열" ↔ 전기 파일의 "당기 열" 계정명 매칭

결과는 _FOOT 리포트 시트에 기록 (원본 시트 오염 없음).
레벨 오버라이드: _FOOT [레벨] 섹션의 '수동' 열을 채우면 재실행 시 우선.
"""
import collections
import re

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill

from .excel_out import MAP_SHEET
from .textutil import try_number

FOOT_SHEET = "_FOOT"
DEFAULT_LIMIT = 2          # DSDbreaker 단수차 한도 ±2

# H-1: 시트명 인식 정규식은 textutil과 단일 소스
from .textutil import FS_SHEET_RE as _FS_SHEET_RE  # noqa: E402
_YELLOW = PatternFill("solid", start_color="FFF2CC")
_RED = PatternFill("solid", start_color="FFC7CE")
_BOLD = Font(bold=True)

MATCH, FUZZY, MISMATCH = "일치", "단수차", "불일치"


# ---------------------------------------------------------------------------
# 계층 역추론 (DSDbreaker §1.1 확장)
# ---------------------------------------------------------------------------

def _scan_once(avail, limit):
    """단방향 1회 스윕: 인접 누적합 == 다음 노드 → 부모 관계.

    시작 노드를 하나씩 뒤로 밀며 재시도 (targetNode+1).
    반환: [(parent, [children])], 스윕 내 중복 없음.
    """
    rels = []
    n = len(avail)
    start = 0
    while start < n - 2:
        found = False
        acc, sub = [], 0.0
        for i in range(start, n - 1):
            acc.append(avail[i])
            sub += avail[i]["val"]
            nxt = avail[i + 1]
            if len(acc) >= 2 and abs(sub - nxt["val"]) <= limit:
                rels.append((nxt, list(acc)))
                start = i + 2
                found = True
                break
        if not found:
            start += 1
    return rels


def infer_relations(seq, limit=DEFAULT_LIMIT):
    """seq: [(key, value)] 위→아래. 다단 계층 관계 추론.

    반환: [{parent, children, direction, diff}] (node = {key, val})
    """
    nodes = [{"key": k, "val": float(v), "pos": i}
             for i, (k, v) in enumerate(seq) if v is not None]
    relations = []
    avail = list(nodes)
    while len(avail) >= 3:
        claimed = set()
        found = []
        for direction, lst in (("하단합계", avail), ("상단소계", avail[::-1])):
            for parent, children in _scan_once(lst, limit):
                child_ids = {id(c) for c in children}
                if (child_ids & claimed) or id(parent) in claimed:
                    continue
                claimed |= child_ids
                found.append({
                    "parent": parent,
                    "children": sorted(children, key=lambda c: c["pos"]),
                    "direction": direction,
                    "diff": abs(sum(c["val"] for c in children)
                                - parent["val"]),
                })
        if not found:
            break
        relations.extend(found)
        removed = {id(c) for r in found for c in r["children"]}
        avail = [nd for nd in avail if id(nd) not in removed]
    return relations


def relations_from_levels(nodes, limit=DEFAULT_LIMIT):
    """수동 레벨 기반 트리 (DSDbreaker getNodeTreeByLevel, 하단 합계).

    nodes: [{key, val, level}] 위→아래, level>=1.
    레벨 p 노드는 직전의 미소속 하위레벨(<p) 노드들을 자식으로 갖는다.
    """
    rels = []
    buf = []
    for nd in nodes:
        if nd["val"] is None:
            continue
        if nd["level"] <= 1:
            buf.append(nd)
            continue
        children = []
        while buf and buf[-1]["level"] < nd["level"]:
            children.insert(0, buf.pop())
        if children:
            rels.append({
                "parent": nd, "children": children, "direction": "수동",
                "diff": abs(sum(c["val"] for c in children) - nd["val"]),
            })
        buf.append(nd)
    return rels


def _verdict(diff, limit):
    if diff == 0:
        return MATCH
    if diff <= limit:
        return FUZZY
    return MISMATCH


# ---------------------------------------------------------------------------
# 워크북 구조 해석 (_MAP 기반 — 테이블 탐지 휴리스틱 불필요)
# ---------------------------------------------------------------------------

def _rowmaps(wb):
    m = collections.defaultdict(dict)
    for row in wb[MAP_SHEET].iter_rows(min_row=2, values_only=True):
        if row and row[0] is not None:
            m[str(row[0])].setdefault(int(row[1]), []).append(int(row[2]))
    for sheet in m:
        for r in m[sheet]:
            m[sheet][r].sort()
    return m


def _regions(rowmap):
    rows = [r for r in sorted(rowmap) if rowmap[r] != [1]]
    regions, cur = [], []
    for r in rows:
        if cur and r - cur[-1] > 1:
            regions.append(cur)
            cur = []
        cur.append(r)
    if cur:
        regions.append(cur)
    return regions


def _num(ws, r, c):
    return try_number(ws.cell(row=r, column=c).value)


def _label(ws, r):
    v = ws.cell(row=r, column=1).value
    return str(v).strip() if v is not None else ""


class FootingContext:
    def __init__(self, xlsx_path, limit=DEFAULT_LIMIT):
        self.path = xlsx_path
        self.limit = limit
        self.wb = load_workbook(xlsx_path)
        if MAP_SHEET not in self.wb.sheetnames:
            raise ValueError("_MAP 시트가 없습니다. 이 도구로 추출한 파일이 "
                             "아닙니다.")
        self.rowmaps = _rowmaps(self.wb)
        self.fs_sheets = [s for s in self.wb.sheetnames
                          if _FS_SHEET_RE.match(s)]
        self.note_sheets = [s for s in self.wb.sheetnames if s.isdigit()]
        self.manual_levels = self._read_manual_levels()

    # --- 수동 레벨 (기존 _FOOT [레벨] 섹션) ------------------------------
    def _read_manual_levels(self):
        levels = {}
        if FOOT_SHEET not in self.wb.sheetnames:
            return levels
        ws = self.wb[FOOT_SHEET]
        in_section = False
        for row in ws.iter_rows(values_only=True):
            if row and row[0] == "[레벨]":
                in_section = True
                continue
            if in_section:
                if row and isinstance(row[0], str) and \
                        row[0].startswith("["):
                    break
                if row and row[0] and row[1] is not None:
                    manual = try_number(row[4]) if len(row) > 4 else None
                    if manual:
                        levels[(str(row[0]), int(row[1]))] = int(manual)
        return levels

    # --- FS 시트: 2열 계층 병합 시퀀스 -----------------------------------
    def fs_sequences(self, sheet):
        """[(period_name, [(row, value)]), ...] + 데이터행 목록."""
        rowmap = self.rowmaps[sheet]
        regions = _regions(rowmap)
        if not regions:
            return [], []
        region = max(regions, key=len)
        ws = self.wb[sheet]
        header, data_rows = region[0], region[1:]
        amount_cols = [c for c in
                       sorted({c for r in data_rows for c in rowmap[r]})
                       if c >= 3]
        periods = []
        if len(amount_cols) == 4:
            pairs = [("당기", amount_cols[0], amount_cols[1]),
                     ("전기", amount_cols[2], amount_cols[3])]
            for name, left, right in pairs:
                seq = []
                for r in data_rows:
                    v = _num(ws, r, left)
                    if v is None:
                        v = _num(ws, r, right)
                    seq.append((r, v))
                periods.append((name, seq))
        elif len(amount_cols) == 2:
            # 단층 2열 (OpenDART 원본 등 — '제43(당)기말'/'제42(전)기말').
            # 헤더 표기로 당/전 판별, 미표기면 좌=당기 관례.
            def _period_of(c):
                h = str(ws.cell(row=header, column=c).value or "")
                h = h.replace(" ", "")
                if "당" in h and "전" not in h:
                    return "당기"
                if "전" in h and "당" not in h:
                    return "전기"
                return None
            names = [_period_of(c) for c in amount_cols]
            if names[0] is None and names[1] is None:
                names = ["당기", "전기"]
            if sorted(n for n in names if n) == \
                    sorted(set(n for n in names if n)) and all(names):
                for name, c in zip(names, amount_cols):
                    periods.append(
                        (name, [(r, _num(ws, r, c)) for r in data_rows]))
            else:                               # 판별 불가 → colN 폴백
                for c in amount_cols:
                    seq = [(r, _num(ws, r, c)) for r in data_rows]
                    if sum(1 for _, v in seq if v is not None) >= 3:
                        periods.append((f"col{c}", seq))
        else:
            for c in amount_cols:
                seq = [(r, _num(ws, r, c)) for r in data_rows]
                if sum(1 for _, v in seq if v is not None) >= 3:
                    periods.append((f"col{c}", seq))
        return periods, data_rows

    def fs_value_col(self, sheet, row, period):
        """해당 행·기간 값이 실제로 놓인 열 (A-6 검증내역 수식 참조용).

        fs_sequences의 열 선택 규칙과 동일: 4열=쌍(좌 우선, 없으면 우),
        2열=당/전 순, colN=해당 열.
        """
        rowmap = self.rowmaps[sheet]
        regions = _regions(rowmap)
        if not regions:
            return None
        region = max(regions, key=len)
        data_rows = region[1:]
        ws = self.wb[sheet]
        amount_cols = [c for c in
                       sorted({c for r in data_rows for c in rowmap[r]})
                       if c >= 3]
        if str(period).startswith("col"):
            try:
                cand = [int(str(period)[3:])]
            except ValueError:
                cand = []
        elif len(amount_cols) == 4:
            cand = amount_cols[:2] if period == "당기" else amount_cols[2:]
        elif len(amount_cols) == 2:
            cand = ([amount_cols[0]] if period == "당기"
                    else [amount_cols[1]])
        else:
            cand = amount_cols
        for c in cand:
            if _num(ws, row, c) is not None:
                return c
        return cand[0] if cand else None

    # --- 일반 테이블 (주석/CE 등): 열별·행별 시퀀스 -----------------------
    def table_sequences(self, sheet):
        """[(테이블번호, axis, key이름, [(key, value)])]"""
        rowmap = self.rowmaps[sheet]
        ws = self.wb[sheet]
        out = []
        for ti, region in enumerate(_regions(rowmap)):
            cols = sorted({c for r in region for c in rowmap[r]})
            for c in cols[1:]:
                seq = [(r, _num(ws, r, c)) for r in region]
                if sum(1 for _, v in seq if v is not None) >= 3:
                    out.append((ti, "행", f"C{c}", seq))
            for r in region:
                seq = [(c, _num(ws, r, c)) for c in rowmap[r][1:]]
                if sum(1 for _, v in seq if v is not None) >= 4:
                    out.append((ti, "열", f"R{r}", seq))
        return out


# ---------------------------------------------------------------------------
# 검증 실행
# ---------------------------------------------------------------------------

def _relation_row(ctx, sheet, axis, scope, rel, limit):
    parent, children = rel["parent"], rel["children"]
    ws = ctx.wb[sheet]
    if axis == "행":
        plabel = _label(ws, parent["key"])
        ploc = f"R{parent['key']}"
    else:
        m = re.search(r"R(\d+)", scope)
        plabel = str(ws.cell(row=int(m.group(1)),
                             column=parent["key"]).value or "") if m else ""
        ploc = f"C{parent['key']}"
    total = sum(c["val"] for c in children)
    return {
        "sheet": sheet, "axis": axis, "scope": scope,
        "direction": rel["direction"], "loc": ploc, "label": plabel,
        "n_children": len(children), "child_keys": [c["key"] for c in children],
        "parent_key": parent["key"],
        "expected": total, "actual": parent["val"],
        "diff": rel["diff"], "verdict": _verdict(rel["diff"], limit),
    }


def run_footing(ctx):
    """합계검증. (결과 목록, 레벨 목록) 반환."""
    results, level_rows = [], []
    limit = ctx.limit

    for sheet in ctx.fs_sheets:
        periods, data_rows = ctx.fs_sequences(sheet)
        base_relations = None
        for name, seq in periods:
            manual = [(r, ctx.manual_levels.get((sheet, r))) for r, _ in seq]
            has_manual = any(lv for _, lv in manual)
            if has_manual and name == "당기":
                # 수동 레벨 우선 (자동 레벨은 미기입 행 보완)
                auto = infer_relations(seq, limit)
                auto_levels = _levels_from_relations(auto)
                nodes = [{"key": r, "val": v,
                          "level": ctx.manual_levels.get(
                              (sheet, r), auto_levels.get(r, 1))}
                         for r, v in seq if v is not None]
                rels = relations_from_levels(nodes, limit)
            else:
                rels = infer_relations(seq, limit)
            for rel in rels:
                results.append(
                    _relation_row(ctx, sheet, "행", name, rel, limit))
            if name == "당기" or base_relations is None:
                base_relations = rels
        # 레벨 기록 (당기 기준)
        if base_relations is not None:
            levels = _levels_from_relations(base_relations)
            ws = ctx.wb[sheet]
            for r in data_rows:
                if _label(ws, r):
                    level_rows.append({
                        "sheet": sheet, "row": r, "label": _label(ws, r),
                        "auto": levels.get(r, 0),
                        "manual": ctx.manual_levels.get((sheet, r), ""),
                    })

    for sheet in ctx.note_sheets:
        for ti, axis, scope, seq in ctx.table_sequences(sheet):
            for rel in infer_relations(seq, ctx.limit):
                results.append(
                    _relation_row(ctx, sheet, axis, f"표{ti + 1}:{scope}",
                                  rel, ctx.limit))
    return results, level_rows


def _levels_from_relations(relations):
    levels = {}
    for rel in relations:
        for c in rel["children"]:
            levels.setdefault(c["key"], 1)
    changed = True
    while changed:
        changed = False
        for rel in relations:
            want = max((levels.get(c["key"], 1)
                        for c in rel["children"]), default=0) + 1
            if levels.get(rel["parent"]["key"], 0) < want:
                levels[rel["parent"]["key"]] = want
                changed = True
    return levels


# ---------------------------------------------------------------------------
# 주석대사 (DSDbreaker getSameValueCell + 주석참조 결합)
# ---------------------------------------------------------------------------

def _numeric_cells(ctx, sheet):
    ws = ctx.wb[sheet]
    out = []
    for r, cols in ctx.rowmaps[sheet].items():
        for c in cols:
            v = _num(ws, r, c)
            if v is not None:
                out.append((r, c, v))
    return out


def run_note_matching(ctx):
    results = []
    pools = {s: _numeric_cells(ctx, s) for s in ctx.note_sheets}
    fs_pools = {s: _numeric_cells(ctx, s) for s in ctx.fs_sheets}
    # A-7: 단위 인지 — FS 시트 배율·주석 표별 배율 (미감지 None=보류)
    from .units import region_scales, sheet_scale
    fs_scales = {s: sheet_scale(ctx, s) for s in ctx.fs_sheets}
    note_scales = {s: region_scales(ctx, s) for s in ctx.note_sheets}
    for sheet in ctx.fs_sheets:
        periods, data_rows = ctx.fs_sequences(sheet)
        values_by_row = collections.defaultdict(list)
        for name, seq in periods:
            for r, v in seq:
                if v is not None:
                    values_by_row[r].append((name, v))
        ws = ctx.wb[sheet]
        for r in data_rows:
            ref_raw = ws.cell(row=r, column=2).value
            refs = [t for t in re.findall(r"\d+", str(ref_raw or ""))
                    if t in ctx.note_sheets]
            if not values_by_row.get(r):
                continue
            if refs:
                s_fs = fs_scales.get(sheet)
                for name, v in values_by_row[r]:
                    hit, conv, conv_tried = None, None, False
                    for ref in refs:
                        for (nr, nc, nv) in pools[ref]:
                            if abs(abs(nv) - abs(v)) <= ctx.limit:
                                hit = (ref, nr, nc, nv)
                                break
                        if hit:
                            break
                    if hit is None and s_fs is not None:
                        # A-7: 배율 상이 쌍 — 원 단위 환산 후 비교.
                        # 허용오차 = 굵은 쪽 배율 미만(천원 ±999).
                        # 단위 미상(None)은 환산 보류 — 추정 금지.
                        for ref in refs:
                            scales = note_scales.get(ref, {})
                            for (nr, nc, nv) in pools[ref]:
                                s_n = scales.get(nr)
                                if s_n is None or s_n == s_fs:
                                    continue
                                conv_tried = True
                                tol = max(s_fs, s_n) - 1
                                if abs(abs(nv) * s_n - abs(v) * s_fs) <= tol:
                                    hit = (ref, nr, nc, nv)
                                    conv = {"fs_scale": s_fs,
                                            "note_scale": s_n, "tol": tol}
                                    break
                            if hit:
                                break
                    results.append({
                        "sheet": sheet, "row": r, "label": _label(ws, r),
                        "refs": ", ".join(refs), "period": name, "value": v,
                        "found": hit is not None,
                        "where": (f"주석{hit[0]} R{hit[1]}C{hit[2]}"
                                  if hit else ""),
                        # A-7: 단위환산 발견은 분리 집계 (기존 일치 불변)
                        "conv": conv, "conv_tried": conv_tried,
                    })
            else:
                # 폴백: 전 시트 값 탐색 (정보성 — 발견 시에만 기록)
                for name, v in values_by_row[r]:
                    if abs(v) <= ctx.limit:
                        continue
                    for pool_sheet, pool in list(pools.items()) + \
                            [(s, p) for s, p in fs_pools.items()
                             if s != sheet]:
                        hit = next(((nr, nc) for nr, nc, nv in pool
                                    if abs(abs(nv) - abs(v)) <= ctx.limit),
                                   None)
                        if hit:
                            results.append({
                                "sheet": sheet, "row": r,
                                "label": _label(ws, r), "refs": "(폴백)",
                                "period": name, "value": v, "found": True,
                                "where": f"{pool_sheet} R{hit[0]}C{hit[1]}",
                            })
                            break
    return results


# ---------------------------------------------------------------------------
# 전기대사 (--prior)
# ---------------------------------------------------------------------------

_LABEL_NORM_RE = re.compile(r"[\sⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ.()0-9]+")


def _norm_label(label):
    return _LABEL_NORM_RE.sub("", label or "")


def run_prior_matching(ctx, prior_ctx):
    """당기 파일 '전기 열' ↔ 전기 파일 '당기 열' 계정명 매칭 비교."""
    results = []
    for sheet in ctx.fs_sheets:
        if sheet not in prior_ctx.fs_sheets:
            continue
        cur_periods, cur_rows = ctx.fs_sequences(sheet)
        pri_periods, pri_rows = prior_ctx.fs_sequences(sheet)
        cur_prior_col = dict(next((s for n, s in cur_periods if n == "전기"),
                                  []))
        pri_current_col = dict(next((s for n, s in pri_periods
                                     if n == "당기"), []))
        ws_c, ws_p = ctx.wb[sheet], prior_ctx.wb[sheet]
        pri_by_label = {}
        for r in pri_rows:
            lab = _norm_label(_label(ws_p, r))
            if lab and pri_current_col.get(r) is not None:
                pri_by_label.setdefault(lab, pri_current_col[r])
        for r in cur_rows:
            lab = _norm_label(_label(ws_c, r))
            v = cur_prior_col.get(r)
            if not lab or v is None:
                continue
            pv = pri_by_label.get(lab)
            if pv is None:
                verdict = "매칭없음"
                diff = None
            else:
                diff = abs(v - pv)
                verdict = _verdict(diff, ctx.limit)
            results.append({
                "sheet": sheet, "row": r, "label": _label(ws_c, r),
                "current_file_prior": v, "prior_file_current": pv,
                "diff": diff, "verdict": verdict,
            })
    return results


# ---------------------------------------------------------------------------
# _FOOT 리포트 시트
# ---------------------------------------------------------------------------

def _write_foot_sheet(ctx, foot_results, level_rows, note_results,
                      prior_results):
    wb = ctx.wb
    if FOOT_SHEET in wb.sheetnames:
        del wb[FOOT_SHEET]
    ws = wb.create_sheet(FOOT_SHEET)

    counts = collections.Counter(r["verdict"] for r in foot_results)
    nf = sum(1 for r in note_results if r["found"])
    nu = sum(1 for r in note_results if not r["found"])
    ws.append(["[요약]"])
    ws.cell(row=1, column=1).font = _BOLD
    ws.append([f"합계검증: 일치 {counts[MATCH]} / 단수차 {counts[FUZZY]} / "
               f"불일치 {counts[MISMATCH]}"])
    ws.append([f"주석대사: 찾음 {nf} / 못찾음 {nu}"])
    if prior_results:
        pc = collections.Counter(r["verdict"] for r in prior_results)
        ws.append([f"전기대사: 일치 {pc[MATCH]} / 단수차 {pc[FUZZY]} / "
                   f"불일치 {pc[MISMATCH]} / 매칭없음 {pc['매칭없음']}"])
    ws.append([])

    ws.append(["[합계검증]"])
    ws.cell(row=ws.max_row, column=1).font = _BOLD
    ws.append(["시트", "축", "구간", "방식", "부모위치", "부모라벨",
               "자식수", "Σ자식", "기재값", "차이", "판정"])
    for r in sorted(foot_results,
                    key=lambda x: (x["verdict"] == MATCH, x["sheet"])):
        ws.append([r["sheet"], r["axis"], r["scope"], r["direction"],
                   r["loc"], r["label"], r["n_children"], r["expected"],
                   r["actual"], r["diff"], r["verdict"]])
        cell = ws.cell(row=ws.max_row, column=11)
        if r["verdict"] == FUZZY:
            cell.fill = _YELLOW
        elif r["verdict"] == MISMATCH:
            cell.fill = _RED
    ws.append([])

    ws.append(["[레벨]"])
    ws.cell(row=ws.max_row, column=1).font = _BOLD
    ws.append(["시트", "행", "라벨", "자동", "수동(수정 후 재실행)"])
    for lv in level_rows:
        ws.append([lv["sheet"], lv["row"], lv["label"], lv["auto"],
                   lv["manual"]])
    ws.append([])

    ws.append(["[주석대사]"])
    ws.cell(row=ws.max_row, column=1).font = _BOLD
    ws.append(["시트", "행", "라벨", "참조", "기간", "값", "결과", "위치"])
    for r in note_results:
        ws.append([r["sheet"], r["row"], r["label"], r["refs"], r["period"],
                   r["value"], "찾음" if r["found"] else "못찾음",
                   r["where"]])
        if not r["found"]:
            ws.cell(row=ws.max_row, column=7).fill = _YELLOW

    if prior_results:
        ws.append([])
        ws.append(["[전기대사]"])
        ws.cell(row=ws.max_row, column=1).font = _BOLD
        ws.append(["시트", "행", "라벨", "당기파일 전기값", "전기파일 당기값",
                   "차이", "판정"])
        for r in prior_results:
            ws.append([r["sheet"], r["row"], r["label"],
                       r["current_file_prior"], r["prior_file_current"],
                       r["diff"], r["verdict"]])
            if r["verdict"] in (MISMATCH, "매칭없음"):
                ws.cell(row=ws.max_row, column=7).fill = _RED

    ws.column_dimensions["A"].width = 10
    for col, w in (("E", 10), ("F", 30), ("C", 12)):
        ws.column_dimensions[col].width = w


def foot(xlsx_path, limit=DEFAULT_LIMIT, prior_path=None, save=True):
    """Footing 검증 실행. 요약 dict 반환 (+ _FOOT 시트 기록)."""
    ctx = FootingContext(xlsx_path, limit=limit)
    foot_results, level_rows = run_footing(ctx)
    note_results = run_note_matching(ctx)
    prior_results = []
    if prior_path:
        prior_results = run_prior_matching(ctx, FootingContext(prior_path,
                                                               limit=limit))
    _write_foot_sheet(ctx, foot_results, level_rows, note_results,
                      prior_results)
    if save:
        ctx.wb.save(xlsx_path)
    counts = collections.Counter(r["verdict"] for r in foot_results)
    return {
        "foot": foot_results,
        "levels": level_rows,
        "notes": note_results,
        "prior": prior_results,
        "match": counts[MATCH], "fuzzy": counts[FUZZY],
        "mismatch": counts[MISMATCH],
        "note_found": sum(1 for r in note_results if r["found"]),
        "note_missing": sum(1 for r in note_results if not r["found"]),
        # A-7: 일치(단위환산) 분리 집계
        "note_found_conv": sum(1 for r in note_results if r.get("conv")),
        "manual_overrides": len(ctx.manual_levels),
    }
