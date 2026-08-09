# -*- coding: utf-8 -*-
"""회귀 스냅샷 게이트 — final.py 실행 지표를 GATES.json과 자동 대조. 완전 오프라인.

검증 로직과 무관한 부가 장치다. 어긋나면 경고만 출력하고 산출물 생성은 막지 않는다.
GATES.json은 다중 샘플(회귀 축)을 지원한다: samples[파일명] = {tol, recorded, metrics}.
- 미등록 샘플            → 대조 생략, --update-gates 로 축 등록 안내
- 기준과 다른 허용오차    → 대조 생략 (기준은 기록된 tol 전용)
- 지표 어긋남            → 경고 출력, 종료코드 1 (의도한 변경이면 --update-gates 로 갱신)
"""
import json, os, sys, datetime

GATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GATES.json")


def _load():
    try:
        with open(GATES, encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        return {"samples": {}}
    except Exception as e:
        print(f"[GATES] 경고: GATES.json 읽기 실패 ({e}) — 대조 생략")
        return None
    if "samples" not in doc:                      # 구 단일 샘플 스키마 → 이행
        doc = {"comment": doc.get("comment", ""),
               "samples": {doc["sample"]: {"tol": doc.get("tol", 0.0),
                                           "recorded": doc.get("recorded", ""),
                                           "metrics": doc.get("metrics", {})}}}
    return doc


def check(metrics, pdf, tol):
    """metrics(dict)를 해당 샘플 축과 대조. 일치/생략 True, 어긋남 False."""
    name = os.path.basename(pdf)
    update = "--update-gates" in sys.argv or os.environ.get("GATES_UPDATE") == "1"
    doc = _load()
    if doc is None: return True
    if update:
        doc.setdefault("comment",
            "final.py 회귀 스냅샷 — 등록된 샘플·허용오차로 실행 시 자동 대조. 갱신: --update-gates")
        ent = doc["samples"].get(name, {})           # _메모 필드는 보존하고 지표만 갱신
        ent.update({"tol": tol, "recorded": datetime.date.today().isoformat(),
                    "metrics": metrics})
        doc["samples"][name] = ent
        with open(GATES, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2); f.write("\n")
        print(f"[GATES] 기준 스냅샷 기록: {name} (tol={tol:g}, 지표 {len(metrics)}개, 축 {len(doc['samples'])}개)")
        return True
    ent = doc["samples"].get(name)
    if ent is None:
        print(f"[GATES] 대조 생략: 미등록 샘플 '{name}' — 축 등록은 --update-gates")
        return True
    if ent.get("tol") != tol:
        print(f"[GATES] 대조 생략: 기준 tol={ent.get('tol')}과 다른 입력(tol={tol:g})")
        return True
    bm = ent.get("metrics", {})
    diffs = [(k, v, metrics.get(k, "(지표 없음)")) for k, v in bm.items() if metrics.get(k) != v]
    diffs += [(k, "(기준 없음)", metrics[k]) for k in metrics if k not in bm]
    if not diffs:
        print(f"[GATES] 회귀 대조 통과 [{name}] — 지표 {len(bm)}개 일치 (기준 {ent.get('recorded')})")
        return True
    print("=" * 64)
    print(f"[GATES] *** 회귀 경고 [{name}]: 기준 스냅샷과 어긋남 ***")
    for k, v, cur in diffs:
        print(f"[GATES]   {k:16s} 기준 {v} → 현재 {cur}")
    print("[GATES] 의도한 변경이면: python run_gates.py <pdf> <tol> --update-gates")
    print("=" * 64)
    return False
