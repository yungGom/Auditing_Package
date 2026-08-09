# -*- coding: utf-8 -*-
"""회귀 스냅샷 게이트 — final.py 실행 지표를 GATES.json과 자동 대조. 완전 오프라인.

검증 로직과 무관한 부가 장치다. 어긋나면 경고만 출력하고 산출물 생성은 막지 않는다.
- GATES.json 없음        → 이번 실행을 기준 스냅샷으로 기록
- 기준과 다른 샘플/허용오차 → 대조 생략 (기준은 기록된 샘플 전용)
- 지표 어긋남            → 경고 출력, 종료코드 1 (의도한 변경이면 --update-gates 로 갱신)
"""
import json, os, sys, datetime

GATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GATES.json")


def check(metrics, pdf, tol):
    """metrics(dict)를 기준 스냅샷과 대조. 일치/생략 True, 어긋남 False."""
    name = os.path.basename(pdf)
    update = "--update-gates" in sys.argv or os.environ.get("GATES_UPDATE") == "1"
    if update or not os.path.exists(GATES):
        _write(metrics, name, tol)
        print(f"[GATES] 기준 스냅샷 기록: {name} (tol={tol:g}, 지표 {len(metrics)}개)")
        return True
    try:
        with open(GATES, encoding="utf-8") as f:
            base = json.load(f)
    except Exception as e:
        print(f"[GATES] 경고: GATES.json 읽기 실패 ({e}) — 대조 생략")
        return True
    if base.get("sample") != name or base.get("tol") != tol:
        print(f"[GATES] 대조 생략: 기준({base.get('sample')}, tol={base.get('tol')})과 다른 입력 — 기준 갱신은 --update-gates")
        return True
    bm = base.get("metrics", {})
    diffs = [(k, v, metrics.get(k, "(지표 없음)")) for k, v in bm.items() if metrics.get(k) != v]
    diffs += [(k, "(기준 없음)", metrics[k]) for k in metrics if k not in bm]
    if not diffs:
        print(f"[GATES] 회귀 대조 통과 — 지표 {len(bm)}개 일치 (기준 {base.get('recorded')})")
        return True
    print("=" * 64)
    print("[GATES] *** 회귀 경고: 기준 스냅샷과 어긋남 ***")
    if base.get("provisional"):
        print("[GATES] 주의: 현 기준은 CLAUDE.md 문서 수치(실측 아님).")
        print("[GATES] 어긋난 지표를 확인한 뒤 실측 기준으로 갱신할 것.")
    for k, v, cur in diffs:
        print(f"[GATES]   {k:16s} 기준 {v} → 현재 {cur}")
    print("[GATES] 의도한 변경이면: python run_gates.py <pdf> <tol> --update-gates")
    print("=" * 64)
    return False


def _write(metrics, name, tol):
    doc = {
        "comment": "final.py 회귀 스냅샷 — 이 샘플·허용오차로 실행 시 자동 대조. 갱신: --update-gates",
        "sample": name,
        "tol": tol,
        "recorded": datetime.date.today().isoformat(),
        "provisional": False,
        "metrics": metrics,
    }
    with open(GATES, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
