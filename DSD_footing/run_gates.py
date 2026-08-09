# -*- coding: utf-8 -*-
"""회귀 게이트 진입점 — final.py를 runpy로 실행해 전역 지표를 수집, GATES.json과 대조.

final.py 본문에는 게이트 코드를 두지 않는다: final.py가 외부 세션 원본으로 통째로
교체되어도 이 진입점과 gates.py가 살아남는다. 지표는 final.py의 전역 변수명
(stat·B·RLINKS·RUN·RDIFF·gap·miss·unref·npara·pros·cons·nounit·FCON)에 의존하므로
변수명이 바뀌면 여기만 고치면 된다.

실행: python run_gates.py <보고서.pdf> <허용오차> [--update-gates]
"""
import os, sys, runpy
import gates

HERE = os.path.dirname(os.path.abspath(__file__))

args = [a for a in sys.argv[1:] if not a.startswith("--")]
pdf = args[0] if args else os.path.join("samples", "삼성전자_감사보고서.pdf")
tol = float(args[1]) if len(args) > 1 else 0.0

_argv = sys.argv
sys.argv = [os.path.join(HERE, "final.py"), pdf, str(tol)]   # final.py 인자 규약에 맞춤
try:
    g = runpy.run_path(sys.argv[0], run_name="__main__")
finally:
    sys.argv = _argv                                          # --update-gates 플래그 복원

stat = g["stat"]; B = g["B"]; FCON = g["FCON"]
metrics = {
    "A_total": sum(stat.values()), "A_OK": stat["OK"], "A_ROUND": stat["ROUND"],
    "A_DIFF": stat["DIFF"], "A_SKIP": stat["SKIP"], "A_SIGN": stat["SIGN"],
    "B_total": len(B), "B_OK": sum(1 for r in B if r[4] == "OK"),
    "B_DIFF": sum(1 for r in B if r[4] == "차이"),
    "B_SKIP": sum(1 for r in B if r[4] == "미검증"),
    "C_ok": len(g["RLINKS"]), "C_unmatched": len(g["RUN"]), "C_diff": len(g["RDIFF"]),
    "C7_gap": len(g["gap"]), "C7_missing": len(g["miss"]), "C7_unref": len(g["unref"]),
    "D_paragraphs": g["npara"], "D_flags": len(g["pros"]),
    "consolidated": bool(g["cons"]), "pages_no_unit": len(g["nounit"]),
    "F1_unit_missing": len(FCON["F1_단위누락"]),
    "F2_term_groups": len(FCON["F2_표현불일치"]),
    "F3_label_groups": len(FCON["F3_라벨불일치"]),
    "F4_multi_space": len(FCON["F4_다중공백"]),
}
sys.exit(0 if gates.check(metrics, pdf, tol) else 1)
