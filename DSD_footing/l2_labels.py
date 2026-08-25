# -*- coding: utf-8 -*-
"""l2_labels — labels/*.json 로드·검증 + 라벨 정규화 + 매칭 엔진.

자동 라벨 매칭 금지(RCM v8 선례) — 고정 매핑 테이블만 읽는다. 완전 오프라인,
표준 라이브러리 json만 사용(YAML·새 의존성 금지).

스키마 확장 메모 (설계안 대비, 구현 중 실물 확인으로 추가됨 — 승인 대기):
  sign_overrides: {alias_text: -1}  — 한 canonical_label 안에서 특정 별칭만 부호가
    반대로 찍히는 경우(예: '지분법손실(이익)'처럼 CF 조정표 관행상 이익을 괄호(-)로
    표기). 값 자체를 바꾸는 게 아니라 "이 별칭은 저장된 부호를 뒤집어 읽는다"는
    선언 — 자동 추정이 아니라 사람이 라벨 텍스트를 보고 등록하는 것이라 '자동
    매칭 금지' 원칙과 배치되지 않는다. 실물: 조선내화 주석17① CF조정표,
    주석9① 순확정급여자산 표.
"""
import json, os, re
from collections import defaultdict
from statements import key as skey

LABELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "labels")

# 범용 라벨 — scope 없이 등록 불가 (강제 검증). core.TOTAL_LAB/tieout.SCE_END 등
# 기존 정규식과 겹치지 않는 최소 집합으로 시작한다(설계안 4-3절).
GENERIC_TERMS = {"합계", "계", "소계", "기초", "기말", "전기초", "당기초", "전기말", "당기말", "총계"}


class LabelLoadError(Exception):
    pass


def _norm_alias(t):
    return skey(t)


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load(company):
    """→ dict(entries, table_aliases, assert_equal, exclude_pairs, alias_index)

    entries: {canonical_label: {aliases, scope, sign_overrides, _note}}
    alias_index: {정규화된 별칭텍스트: [(canonical_label, entry), ...]} — 조회용.
    """
    common_path = os.path.join(LABELS_DIR, "_common.json")
    common = _load_json(common_path) if os.path.isfile(common_path) else {"labels": {}}

    entries = dict(common.get("labels", {}))
    table_aliases = {}
    assert_equal = []
    exclude_pairs = []

    if company:
        path = os.path.join(LABELS_DIR, f"{company}.json")
        if not os.path.isfile(path):
            raise LabelLoadError(f"회사 사전 없음: {path}")
        doc = _load_json(path)
        if doc.get("extends") not in (None, "_common"):
            raise LabelLoadError(f"{path}: extends는 '_common'만 지원")
        for cl, e in (doc.get("overrides") or {}).items():
            entries[cl] = e   # 같은 canonical_label이면 회사 정의가 완전히 덮어씀(설계안 4-2절)
        table_aliases = doc.get("table_aliases") or {}
        assert_equal = doc.get("assert_equal") or []
        exclude_pairs = doc.get("exclude_pairs") or []

    # ── 검증: 범용어는 scope 필수 ──
    for cl, e in entries.items():
        aliases = e.get("aliases") or []
        scope = e.get("scope")
        if any(a in GENERIC_TERMS for a in aliases) and not scope:
            raise LabelLoadError(
                f"'{cl}': 범용 라벨({[a for a in aliases if a in GENERIC_TERMS]})은 "
                f"scope 없이 등록할 수 없습니다 — 강제 검증(설계안 4-3절)")
    for a in assert_equal:
        if a["label"] not in entries:
            raise LabelLoadError(f"assert_equal의 '{a['label']}'가 사전에 없습니다")
    for x in exclude_pairs:
        if x["label"] not in entries:
            raise LabelLoadError(f"exclude_pairs의 '{x['label']}'가 사전에 없습니다")

    alias_index = defaultdict(list)
    for cl, e in entries.items():
        for a in e.get("aliases") or []:
            alias_index[_norm_alias(a)].append((cl, e))

    return dict(entries=entries, table_aliases=table_aliases,
                assert_equal=assert_equal, exclude_pairs=exclude_pairs,
                alias_index=dict(alias_index))


def _scope_ok(scope, table_id):
    """scope(콤마 목록) 중 하나라도 table_id에 맞으면 True. scope=None이면 무제한(전 표 허용)."""
    if not scope:
        return True
    for tok in scope.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if tok == table_id or table_id.startswith(tok + "-") or table_id.startswith(tok + "."):
            return True
    return False


def canonicalize(raw_label, table_id, doc):
    """raw_label(이미 statements.key()로 1차 정규화됨) + table_id → canonical_label|None.

    scope가 있는 후보가 여럿이면 table_id와 맞는 것만 채택. 전부 불일치 또는
    후보가 아예 없으면 None(UNMAPPED) — 억지 매칭 금지."""
    cands = doc["alias_index"].get(_norm_alias(raw_label))
    if not cands:
        return None
    hits = [cl for cl, e in cands if _scope_ok(e.get("scope"), table_id)]
    if len(hits) == 1:
        return hits[0]
    return None  # 0건(scope 불일치) 또는 2건 이상(모호) → 둘 다 안전하게 UNMAPPED


def sign_for(doc, canonical_label, raw_label):
    e = doc["entries"].get(canonical_label) or {}
    return (e.get("sign_overrides") or {}).get(raw_label, 1)


def _resolve_table_alias(doc, name_or_id):
    ta = doc["table_aliases"].get(name_or_id)
    return ta["table_id"] if ta else name_or_id


def _pair_tol(ma, mb):
    """단위가 다르면 거친 쪽 1스텝 허용(refmap._pair_tol과 동일 원리) — 컷이 아니라
    정확도 보정, L2에서도 유지(2026-08-25 확정)."""
    if ma is None or mb is None:
        return None
    return 0.0 if ma == mb else float(max(ma, mb))


def build(pdf_path, company, raw_tuples):
    """원시 튜플(l2_extract.extract 결과) → 매칭 결과.

    → dict(confirmed, undeclared, excluded, unmapped, warnings)
    각 finding: canonical_label, column_key, period_key, table_a, table_b,
                value_a, value_b, diff(원 환산), page_a, page_b, bbox_a, bbox_b
    """
    doc = load(company)
    tuples = []
    unmapped = []
    weak = []
    for t in raw_tuples:
        cl = canonicalize(t["raw_label"], t["table_id"], doc)
        if cl is None:
            unmapped.append(t)
            continue
        sign = sign_for(doc, cl, t["raw_label"])
        t2 = dict(t)
        t2["canonical_label"] = cl
        t2["signed_value"] = t["value"] * sign
        t2["sign"] = sign
        tuples.append(t2)
        if t.get("weak_col"):
            weak.append(t2)

    groups = defaultdict(list)
    for t in tuples:
        groups[(t["canonical_label"], t["column_key"], t["period_key"], t["doc_key"])].append(t)

    assert_labels = {a["label"] for a in doc["assert_equal"]}
    excl_lookup = defaultdict(list)  # canonical_label -> [(table_id_a, table_id_b, reason)]
    for x in doc["exclude_pairs"]:
        ta = _resolve_table_alias(doc, x["table_alias_a"])
        tb = _resolve_table_alias(doc, x["table_alias_b"])
        excl_lookup[x["label"]].append((ta, tb, x.get("reason", "")))

    def is_excluded(label, tid_a, tid_b):
        for ta, tb, reason in excl_lookup.get(label, []):
            if {ta, tb} == {tid_a, tid_b}:
                return reason
        return None

    confirmed, undeclared, excluded = [], [], []
    seen_pairs = set()
    for (cl, ck, pk, dk), items in groups.items():
        # table_id별 대표값 하나만 남긴다 — 같은 table_id 안에 같은 키로 여러 값이
        # 있는 경우는 label 정규화가 더 필요하다는 신호라 첫 값만 쓰고 넘어간다
        # (침묵 손실이 아니라 UNMAPPED이 아닌 다른 문제이므로 별도 정밀화는 후속 과제).
        by_table = {}
        for it in items:
            by_table.setdefault(it["table_id"], it)
        if len(by_table) < 2:
            continue
        tids = sorted(by_table)
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                a, b = by_table[tids[i]], by_table[tids[j]]
                tol = _pair_tol(a["mult"], b["mult"])
                won_a = a["signed_value"] * (a["mult"] or 1)
                won_b = b["signed_value"] * (b["mult"] or 1)
                if tol is None or abs(won_a - won_b) <= tol + 1e-6:
                    continue  # 일치(또는 단위 미상으로 비교 불가) — finding 아님
                key = (cl, ck, pk, dk, tids[i], tids[j])
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                rec = dict(canonical_label=cl, column_key=ck, period_key=pk, doc_key=dk,
                           table_a=tids[i], table_b=tids[j],
                           value_a=a["signed_value"], value_b=b["signed_value"],
                           won_a=won_a, won_b=won_b, diff=won_b - won_a,
                           page_a=a["page"], page_b=b["page"],
                           bbox_a=a["bbox"], bbox_b=b["bbox"],
                           sign_a=a["sign"], sign_b=b["sign"])
                reason = is_excluded(cl, tids[i], tids[j])
                if reason is not None:
                    rec["reason"] = reason
                    excluded.append(rec)
                elif cl in assert_labels:
                    confirmed.append(rec)
                else:
                    undeclared.append(rec)

    confirmed.sort(key=lambda r: -abs(r["diff"]))
    undeclared.sort(key=lambda r: -abs(r["diff"]))
    return dict(confirmed=confirmed, undeclared=undeclared, excluded=excluded,
                unmapped=unmapped, weak_col=weak)
