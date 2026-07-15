"""D-3b 게이트: 홀드아웃 자동 검증 (수동 블라인드 대체).

1. 업종 분산으로 홀드아웃 30개사 선정 (결정적 — seed 기반)
2. 각 사의 (한글라벨, 실제 element) 쌍 = 정답지
3. 해당 회사를 코퍼스 집계에서 제외하고 추천 실행 (누수 방지)
4. Top-1/Top-4 적중률을 난이도 구간별 리포트
   - 쉬움: 라벨 = 표준 라벨 정확 일치 (참고치 — 100% 근처가 정상)
   - 중간: 라벨이 표준과 다름 (표기 변형) ← 게이트: Top-4 80%+
   - 함정: 정답이 확장 element → "적합 표준 없음"+유사 확장 제시가 정답
"""
import collections
import json
import random
import sqlite3

from .mapping import (DEFAULT_CORPUS, MappingCorpus, normalize, suggest)

# Role 코드 → 입력 구분 (정답지의 구분 유추)
_ROLE_TO_CAT = [("D2", "BS"), ("D3", "PL"), ("D4", "PL"), ("D5", "CF"),
                ("D6", "CE"), ("D8", "주석")]

TIER_EASY, TIER_MID, TIER_TRAP = "쉬움", "중간", "함정"
DEFAULT_CAPS = {TIER_EASY: 100, TIER_MID: 200, TIER_TRAP: 60}
GATE_TIER, GATE_RATE = TIER_MID, 0.80


def _category_of(roles: str):
    for code in (roles or "").split(","):
        for prefix, cat in _ROLE_TO_CAT:
            if code.startswith(prefix):
                return cat
    return None


def select_holdout(db_path=None, n=30, seed=42):
    """업종 분산 홀드아웃: 업종별 그룹 → 라운드로빈 추출 (결정적)."""
    con = sqlite3.connect(f"file:{db_path or DEFAULT_CORPUS}?mode=ro",
                          uri=True, timeout=30)
    rows = con.execute(
        "SELECT corp_code, corp_name, induty_code FROM companies "
        "WHERE status = 'ok'").fetchall()
    con.close()
    by_induty = collections.defaultdict(list)
    for code, name, ind in rows:
        by_induty[ind or "?"].append((code, name))
    rng = random.Random(seed)
    for group in by_induty.values():
        group.sort()
        rng.shuffle(group)
    picked = []
    industries = sorted(by_induty, key=lambda k: -len(by_induty[k]))
    while len(picked) < min(n, len(rows)):
        progressed = False
        for ind in industries:
            if by_induty[ind]:
                picked.append(by_induty[ind].pop(0) + (ind,))
                progressed = True
                if len(picked) >= n:
                    break
        if not progressed:
            break
    return picked                       # [(corp_code, corp_name, induty)]


def build_answer_key(db_path, holdout, std_labels):
    """홀드아웃사들의 (라벨, element) 정답 쌍 + 난이도 구간."""
    con = sqlite3.connect(f"file:{db_path or DEFAULT_CORPUS}?mode=ro",
                          uri=True, timeout=30)
    pairs = []
    for corp_code, corp_name, induty in holdout:
        for eid, is_ext, label, roles in con.execute(
                "SELECT element_id, is_ext, label_ko, roles FROM usages "
                "WHERE corp_code = ? AND element_id NOT LIKE 'dart-gcd%'",
                (corp_code,)):
            label = (label or "").strip()
            if len(normalize(label)) < 2:       # 빈/기호 라벨 제외
                continue
            if is_ext:
                tier = TIER_TRAP
            elif std_labels.get(eid, "").strip() == label:
                tier = TIER_EASY
            else:
                tier = TIER_MID
            pairs.append({
                "corp_code": corp_code, "corp_name": corp_name,
                "induty": induty, "label": label, "element_id": eid,
                "tier": tier, "category": _category_of(roles),
            })
    con.close()
    return pairs


def evaluate(db_path=None, n_holdout=30, caps=None, seed=42,
             threshold=None, progress=None, out_json=None):
    """홀드아웃 평가 실행. 구간별 Top-1/Top-4 리포트 dict 반환."""
    from .mapping import DEFAULT_THRESHOLD
    caps = caps or DEFAULT_CAPS
    threshold = threshold or DEFAULT_THRESHOLD
    holdout = select_holdout(db_path, n=n_holdout, seed=seed)
    excl = {h[0] for h in holdout}
    corpus = MappingCorpus(db_path, exclude_corps=excl)   # 누수 방지

    pairs = build_answer_key(db_path, holdout, corpus.std_labels)
    rng = random.Random(seed)
    sampled = []
    for tier, cap in caps.items():
        tier_pairs = [p for p in pairs if p["tier"] == tier]
        rng.shuffle(tier_pairs)
        sampled += tier_pairs[:cap]

    stats = {t: {"n": 0, "top1": 0, "top4": 0} for t in caps}
    misses = []
    for i, p in enumerate(sampled, 1):
        r = suggest(corpus, p["label"], p["category"], induty=p["induty"],
                    threshold=threshold)
        ids = [c["element_id"] for c in r["candidates"]]
        if p["tier"] == TIER_TRAP:
            # 정답 = "적합 표준 없음" 판정 (+유사 확장 제시 여부는 별도 집계)
            hit1 = hit4 = r["verdict"] == "적합 표준 없음"
            stats[p["tier"]].setdefault("ext_suggested", 0)
            if hit4 and r["similar_extensions"]:
                stats[p["tier"]]["ext_suggested"] += 1
        else:
            hit1 = ids[:1] == [p["element_id"]]
            hit4 = p["element_id"] in ids[:4]
        s = stats[p["tier"]]
        s["n"] += 1
        s["top1"] += int(hit1)
        s["top4"] += int(hit4)
        if not hit4 and len(misses) < 40:
            misses.append({**p, "got": ids[:4], "verdict": r["verdict"]})
        if progress and i % 25 == 0:
            progress(f"  [{i}/{len(sampled)}] 평가 중…")

    report = {"holdout": [{"corp": h[1], "induty": h[2]} for h in holdout],
              "excluded": len(excl), "pairs_total": len(pairs),
              "sampled": len(sampled), "tiers": {}, "misses": misses}
    for tier, s in stats.items():
        if s["n"]:
            report["tiers"][tier] = {
                "n": s["n"],
                "top1": round(s["top1"] / s["n"], 4),
                "top4": round(s["top4"] / s["n"], 4),
                **({"ext_suggested": s["ext_suggested"]}
                   if "ext_suggested" in s else {}),
            }
    mid = report["tiers"].get(GATE_TIER, {})
    report["gate"] = {
        "criterion": f"{GATE_TIER} Top-4 ≥ {GATE_RATE:.0%}",
        "value": mid.get("top4"),
        "passed": (mid.get("top4") or 0) >= GATE_RATE,
    }
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    return report
