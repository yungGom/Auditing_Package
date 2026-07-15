"""D-4: 택사노미 버전 관리 — 감지·대조·리포트만 담당 (변환·배포는 금감원 몫).

D-4a: 버전 저장소(dart_explorer/taxonomies/{버전}/) + 버전 자동 감지
D-4b: 두 세대 Presentation Link 대조 → 신설/폐지/변경 리포트
D-4c: 인스턴스 호환성 점검 (전기 XBRL이 신버전에서 그대로/폐지/변경인지)
D-4d: 확장→표준 승격 감지 (D-3b 스코어러 재사용)

핵심 실측 함정 (구현 근거):
- 열 배치가 세대별로 다르다(2025판: prefix|name|label(en)|label(ko)|depth,
  2026판: prefix|목차|name|label(ko)|depth). 헤더 행에서 열 역할을 탐지하고
  열 위치는 절대 하드코딩하지 않는다.
- "label" 헤더가 한 세대에는 2번(영문/한글) 나온다 — 값의 한글 포함 여부로
  구분한다. 열 위치로 임의 배정하면 영문↔한글 비교가 되어 가짜 변경 신호가
  대량 발생한다(실측: 7,652건 = 유지 전체가 오탐).
"""
import glob
import os
import re
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

_HANGUL_RE = re.compile(r"[가-힣]")
_SYSTEMID_RE = re.compile(r"dart_all_(\d{4}-\d{2}-\d{2})_pre")
_MARKERS = ("LinkRole", "Definition", "prefix")

_BOLD = Font(bold=True)
_HDR_FILL = PatternFill("solid", start_color="D9E1F2")
_RED = Font(color="FFCC0000")

_EXPLORER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAXONOMY_DIR = os.path.join(_EXPLORER_DIR, "taxonomies")

# D-4d: dsd_workbench의 D-3b 스코어러 재사용 (explorer→workbench 단방향 import)
_WORKBENCH = os.path.join(os.path.dirname(_EXPLORER_DIR), "dsd_workbench")
if _WORKBENCH not in sys.path:
    sys.path.insert(0, _WORKBENCH)


def _has_hangul(s):
    return bool(_HANGUL_RE.search(str(s or "")))


def resolve_version_dir(version_or_path):
    """버전명('2026-01-31')이면 taxonomies/ 하위 파일을, 경로면 그대로 반환."""
    if os.path.exists(version_or_path):
        return version_or_path
    folder = os.path.join(TAXONOMY_DIR, version_or_path)
    if os.path.isdir(folder):
        cands = [p for p in glob.glob(os.path.join(folder, "*"))
                 if p.lower().endswith((".xlsx", ".xlsm"))]
        if cands:
            return cands[0]
    raise FileNotFoundError(
        f"택사노미 파일을 찾을 수 없습니다: {version_or_path} "
        f"(taxonomies/{{버전}}/ 아래 배치했는지 확인)")


def detect_version(path):
    """systemid 열(pre.xml 참조)에서 'dart_all_YYYY-MM-DD_pre' 기준일 추출."""
    wb = load_workbook(path, read_only=True)
    try:
        ws = wb["Presentation Link"]
        sysid_col = None
        for row in ws.iter_rows(values_only=True):
            if sysid_col is None:
                if "systemid" in row:
                    sysid_col = row.index("systemid")
                continue
            if row[sysid_col]:
                m = _SYSTEMID_RE.search(str(row[sysid_col]))
                if m:
                    return m.group(1)
    finally:
        wb.close()
    return None


# ---------------------------------------------------------------------------
# D-4b: 헤더 역할 탐지 기반 Presentation Link 파서 (열 위치 하드코딩 금지)
# ---------------------------------------------------------------------------

def parse_presentation_concepts(path, progress=None):
    """Presentation Link 시트 → {element_id: {label_ko, label_en, roles:set}}.

    블록 구조(LinkRole/Definition/prefix 마커 행 → 데이터 행 반복)는 두 세대
    공통이나, 마커·데이터 열 위치는 세대마다 다르다. 헤더 행에서 매 블록마다
    prefix/name/label*/systemid 열 인덱스를 다시 탐지한다.
    """
    wb = load_workbook(path, read_only=True)
    concepts = {}
    try:
        ws = wb["Presentation Link"]
        prefix_col = name_col = None
        label_cols = []
        cur_def = None
        n = 0
        for row in ws.iter_rows(values_only=True):
            if "LinkRole" in row:
                cur_def = None
                prefix_col = name_col = None
                label_cols = []
                continue
            if "Definition" in row:
                idx = row.index("Definition")
                texts = [v for v in row[idx + 1:] if v]
                cur_def = texts[0] if texts else None
                continue
            if "prefix" in row and "name" in row:
                prefix_col = row.index("prefix")
                name_col = row.index("name")
                label_cols = [i for i, v in enumerate(row) if v == "label"]
                continue
            if prefix_col is None or name_col is None:
                continue
            if len(row) <= name_col or not row[name_col]:
                continue
            local = row[name_col]
            prefix = row[prefix_col] if prefix_col < len(row) else None
            eid = f"{prefix}_{local}" if prefix else local
            labels = [row[c] for c in label_cols
                     if c < len(row) and row[c]]
            ko = next((lb for lb in labels if _has_hangul(lb)), None)
            en = next((lb for lb in labels if not _has_hangul(lb)), None)
            c = concepts.setdefault(
                eid, {"label_ko": None, "label_en": None, "roles": set()})
            if ko:
                c["label_ko"] = ko
            if en:
                c["label_en"] = en
            if cur_def:
                c["roles"].add(cur_def)
            n += 1
            if progress and n % 20000 == 0:
                progress(f"  파싱 중… {n:,}행")
    finally:
        wb.close()
    return concepts


# ---------------------------------------------------------------------------
# D-4b: 버전 diff
# ---------------------------------------------------------------------------

# 대용량 파싱·매칭 결과 캐시 (taxcheck·게이트 테스트가 같은 diff를 여러 번
# 요구 — 파일 파싱 ~1분, 승격 감지 ~12분이라 재계산 방지가 필수)
_DIFF_CACHE = {}
_PROMO_CACHE = {}


def diff_versions(old_path, new_path, progress=None):
    old_path = resolve_version_dir(old_path)
    new_path = resolve_version_dir(new_path)
    cache_key = (os.path.abspath(old_path), os.path.abspath(new_path))
    if cache_key in _DIFF_CACHE:
        return _DIFF_CACHE[cache_key]
    if progress:
        progress(f"구버전 파싱: {os.path.basename(old_path)}")
    old = parse_presentation_concepts(old_path, progress)
    if progress:
        progress(f"신버전 파싱: {os.path.basename(new_path)}")
    new = parse_presentation_concepts(new_path, progress)

    old_ids, new_ids = set(old), set(new)
    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)
    changed = []
    for eid in sorted(new_ids & old_ids):
        o, n = old[eid], new[eid]
        if (o["label_ko"] or "") != (n["label_ko"] or ""):
            changed.append({
                "element_id": eid,
                "old_label": o["label_ko"], "new_label": n["label_ko"],
                "roles": "; ".join(sorted(n["roles"]))[:200],
            })

    def _rows(ids, table, deprecated=False):
        out = []
        for eid in ids:
            out.append({
                "element_id": eid, "label_ko": table[eid]["label_ko"],
                "roles": "; ".join(sorted(table[eid]["roles"]))[:200],
                "deprecated": deprecated,
            })
        return out

    result = {
        "old_path": old_path, "new_path": new_path,
        "old_version": detect_version(old_path),
        "new_version": detect_version(new_path),
        "added": _rows(added, new), "removed": _rows(removed, old, True),
        "changed": changed, "kept": len(new_ids & old_ids),
    }
    _DIFF_CACHE[cache_key] = result
    return result


def get_promotions(old, new, corpus, min_similarity=0.55, progress=None):
    """diff + 승격 감지 (모듈 캐시) — run_taxcheck·테스트 공용 진입점."""
    d = diff_versions(old, new, progress)
    key = (os.path.abspath(d["old_path"]), os.path.abspath(d["new_path"]),
           min_similarity)
    if key not in _PROMO_CACHE:
        _PROMO_CACHE[key] = detect_promotions(
            d["added"], corpus, min_similarity=min_similarity,
            progress=progress)
    return _PROMO_CACHE[key]


def write_diff_excel(result, out_path):
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "신설"
    ws1.append(["element ID", "한글 라벨", "소속 Role"])
    for r in result["added"]:
        ws1.append([r["element_id"], r["label_ko"], r["roles"]])

    ws2 = wb.create_sheet("폐지")
    ws2.append(["element ID", "한글 라벨(구버전)", "소속 Role(구버전)", "비고"])
    for r in result["removed"]:
        ws2.append([r["element_id"], r["label_ko"], r["roles"], "deprecated"])

    ws3 = wb.create_sheet("변경")
    ws3.append(["element ID", "구 한글 라벨", "신 한글 라벨", "소속 Role(신)"])
    for r in result["changed"]:
        ws3.append([r["element_id"], r["old_label"], r["new_label"],
                   r["roles"]])

    for ws in (ws1, ws2, ws3):
        for c in ws[1]:
            c.font = _BOLD
            c.fill = _HDR_FILL
        ws.freeze_panes = "A2"
        widths = [46, 34, 50, 12]
        for i, w in enumerate(widths[:ws.max_column], 1):
            ws.column_dimensions[get_column_letter(i)].width = w
    wb.save(out_path)
    return out_path


def taxdiff(old, new, out_path=None, progress=None):
    result = diff_versions(old, new, progress)
    if out_path is None:
        out_path = os.path.join(
            TAXONOMY_DIR,
            f"taxdiff_{result['old_version']}_to_{result['new_version']}.xlsx")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    write_diff_excel(result, out_path)
    result["out_path"] = out_path
    return result


# ---------------------------------------------------------------------------
# D-4c: 인스턴스 호환성 점검 (당기 XBRL 착수 전 체크리스트)
# ---------------------------------------------------------------------------

def _auto_old_baseline(new_path):
    """taxonomies/ 에 신버전 외 세대가 정확히 1개면 D-4d 승격탐지용으로 자동 채택."""
    if not os.path.isdir(TAXONOMY_DIR):
        return None
    versions = [d for d in os.listdir(TAXONOMY_DIR)
               if os.path.isdir(os.path.join(TAXONOMY_DIR, d))]
    others = []
    for v in versions:
        try:
            if os.path.abspath(resolve_version_dir(v)) != \
                    os.path.abspath(new_path):
                others.append(v)
        except FileNotFoundError:
            continue
    return others[0] if len(others) == 1 else None


def _load_mapping_corpus(mapping_db):
    try:
        from dsd_tool.mapping import MappingCorpus
        return MappingCorpus(mapping_db)
    except (ImportError, FileNotFoundError):
        return None


def run_taxcheck(xbrl_folder, against, mapping_db=None, out_path=None,
                 progress=None):
    """전기 XBRL 사용 element 전수 ↔ 신버전 대조. "당기 착수 전 체크리스트"."""
    from .dimension_table import XbrlInstance
    from .taxonomy import TaxonomyPackage

    new_path = resolve_version_dir(against)
    if progress:
        progress(f"신버전 파싱: {os.path.basename(new_path)}")
    new_concepts = parse_presentation_concepts(new_path, progress)

    pkg = TaxonomyPackage(xbrl_folder)
    inst = XbrlInstance(xbrl_folder)
    used = sorted(e for e in inst.facts if not e.startswith("dart-gcd"))

    corpus = _load_mapping_corpus(mapping_db)
    rows = []
    for eid in used:
        label = pkg._label(pkg.labels_ko, eid)
        if eid in pkg.extensions:
            rows.append({"element_id": eid, "label_ko": label,
                        "status": "확장(회사고유)", "detail": "당사 확장 element"})
            continue
        if eid in new_concepts:
            new_label = new_concepts[eid]["label_ko"]
            if (new_label or "").strip() == (label or "").strip():
                rows.append({"element_id": eid, "label_ko": label,
                            "status": "녹색", "detail": "그대로 사용 가능"})
            else:
                rows.append({"element_id": eid, "label_ko": label,
                            "status": "파랑",
                            "detail": f"라벨 변경: '{label}' → '{new_label}'"})
        else:
            cands = []
            if corpus is not None:
                from dsd_tool.mapping import suggest
                cands = suggest(corpus, label or eid, top=4)["candidates"]
            rows.append({"element_id": eid, "label_ko": label,
                        "status": "노랑", "detail": "폐지됨 — 대체 후보 참고",
                        "candidates": cands})

    counts = {"green": sum(1 for r in rows if r["status"] == "녹색"),
             "yellow": sum(1 for r in rows if r["status"] == "노랑"),
             "blue": sum(1 for r in rows if r["status"] == "파랑")}

    promotions = []
    old_baseline = _auto_old_baseline(new_path)
    if old_baseline and corpus is not None:
        if progress:
            progress(f"승격 감지용 구버전 자동 채택: {old_baseline}")
        promotions = list(get_promotions(old_baseline, new_path, corpus,
                                         progress=progress))
        own_ext_labels = {pkg._label(pkg.labels_ko, e) for e in pkg.extensions}
        for p in promotions:
            p["own_extension"] = p["ext_label"] in own_ext_labels

    if out_path is None:
        out_path = os.path.join(xbrl_folder, "taxcheck_체크리스트.xlsx")
    write_taxcheck_excel(rows, promotions, out_path)
    return {"out_path": out_path, "rows": rows, "promotions": promotions,
            **counts}


def write_taxcheck_excel(rows, promotions, out_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "체크리스트"
    ws.append(["element ID", "한글 라벨", "상태", "상세"])
    fills = {
        "녹색": PatternFill("solid", start_color="C6EFCE"),
        "노랑": PatternFill("solid", start_color="FFEB9C"),
        "파랑": PatternFill("solid", start_color="BDD7EE"),
        "확장(회사고유)": PatternFill("solid", start_color="E4DFEC"),
    }
    for r in rows:
        ws.append([r["element_id"], r["label_ko"], r["status"], r["detail"]])
        fill = fills.get(r["status"])
        if fill:
            for c in ws[ws.max_row]:
                c.fill = fill
        for i, cand in enumerate(r.get("candidates") or [], 1):
            ws.append(["", f"  대체후보{i}: {cand['element_id']}",
                       cand.get("std_label", ""),
                       f"score={cand['score']} — {cand.get('evidence', '')}"])
    for c in ws[1]:
        c.font = _BOLD
        c.fill = _HDR_FILL
    ws.freeze_panes = "A2"
    for i, w in enumerate((46, 34, 16, 60), 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    if promotions:
        ws2 = wb.create_sheet("확장→표준 승격후보")
        ws2.append(["작년 확장 라벨", "코퍼스 사용 회사수", "올해 신설 표준 element",
                   "신설 표준 라벨", "유사도", "당사 확장과 일치"])
        for p in promotions:
            ws2.append([p["ext_label"], p["n_companies"],
                       p["new_element_id"], p["new_label"], p["similarity"],
                       "예" if p.get("own_extension") else ""])
        for c in ws2[1]:
            c.font = _BOLD
            c.fill = _HDR_FILL
        ws2.freeze_panes = "A2"
        for i, w in enumerate((34, 14, 46, 34, 8, 14), 1):
            ws2.column_dimensions[get_column_letter(i)].width = w
    wb.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# D-4d: 확장→표준 승격 감지 (D-3b 스코어러 재사용)
# ---------------------------------------------------------------------------

def detect_promotions(added, corpus, min_similarity=0.55, progress=None):
    """diff의 신설 element 라벨 ↔ 코퍼스 확장 라벨 고유사도 매칭.

    D-3b 스코어러(자모편집거리 0.7 + 토큰자카드 0.3, 반의어 페널티)의
    구성요소를 재사용하되, 신설 1,300+ × 확장 라벨 9만+ 규모라 배치 전용
    최적화를 얹는다:
    - 확장 라벨의 정규화·자모·토큰을 1회 사전계산 (similarity()는 호출마다
      normalize를 다시 돌려 이 규모에선 병목)
    - 토큰 공유 후보만 비교 + 자모 길이차 상한으로 편집거리 DP 사전 차단
      (jamo_sim ≤ 1 - len차/max이므로 상한이 임계 미달이면 계산 불필요)
    """
    import collections as _c

    from dsd_tool.mapping import (SIM_MIX, _antonym_penalty, _levenshtein,
                                  _query_variants, _tokens, jamo, normalize)

    # 확장 라벨 사전계산(정규화·자모·토큰 집합) + 토큰 역색인
    ext_pre = {}
    token_index = _c.defaultdict(set)
    for label in corpus.extensions:
        ln = normalize(label)
        if not ln:
            continue
        toks = _tokens(label)
        ext_pre[label] = (ln, jamo(ln), toks)
        for t in toks:
            token_index[t].add(label)

    results = []
    for i, item in enumerate(added):
        label = item.get("label_ko")
        if not label:
            continue
        qn = normalize(label)
        q_tokens = _tokens(label)
        variants = [(v, jamo(v)) for v in _query_variants(qn)]
        cand_labels = set()
        for t in q_tokens:
            cand_labels |= token_index.get(t, set())
        best = None
        for ext_label in cand_labels:
            ln, lj, l_tokens = ext_pre[ext_label]
            jacc = (len(q_tokens & l_tokens) / len(q_tokens | l_tokens)
                    if q_tokens and l_tokens else 0.0)
            best_jamo = 0.0
            for _, vj in variants:
                gap = abs(len(vj) - len(lj))
                mx = max(len(vj), len(lj))
                if not mx:
                    continue
                upper = 1 - gap / mx
                # 상한 기준 임계 미달이면 DP 생략
                if SIM_MIX["jamo"] * upper + SIM_MIX["jaccard"] * jacc \
                        < min_similarity:
                    continue
                if upper > best_jamo:
                    s = 1 - _levenshtein(vj, lj) / mx
                    if s > best_jamo:
                        best_jamo = s
            sim = (SIM_MIX["jamo"] * best_jamo
                   + SIM_MIX["jaccard"] * jacc) * _antonym_penalty(qn, ln)
            if sim >= min_similarity and (best is None or sim > best[1]):
                best = (ext_label, sim)
        if best:
            results.append({
                "new_element_id": item["element_id"], "new_label": label,
                "ext_label": best[0], "similarity": round(best[1], 3),
                "n_companies": len(corpus.extensions[best[0]]),
            })
        if progress and i and i % 300 == 0:
            progress(f"  승격 감지… {i}/{len(added)}")
    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results
