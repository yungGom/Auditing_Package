# -*- coding: utf-8 -*-
"""파일 반입 무결성 가드 — 외부 사본이 저장소 수정을 덮어썼는지 확인한다.

배경: claude.ai 사본(files.zip 등)을 풀다가 core.py가 구버전으로 덮여
소계 3경로·콜론 경계·A2 완화가 유실된 사고가 있었다 (2026-08-09).
파일 반입은 diff만 받아 변경 지점만 얹고, 반입 직후 이 스크립트를 실행할 것.

사용:
  python intake_check.py          # 시그니처 가드 (1초) — pre-commit 훅에서도 실행
  python intake_check.py --full   # + 삼성 회귀 게이트 실행 (수 분)
"""
import inspect, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

fails = []

def need(cond, msg):
    if not cond: fails.append(msg)

try:
    import core
    sig = inspect.signature(core.check_table)
    need({"x0s", "sublog", "ctx"} <= set(sig.parameters),
         "core.check_table에 x0s/sublog/ctx 없음 — 소계 구조 인식 유실 (구버전으로 덮임)")
    need(hasattr(core, "EXCL_TABLE"), "core.EXCL_TABLE 없음 — 적용 부적합 제외 유실")
    src = open(os.path.join(HERE, "core.py"), encoding="utf-8").read()
    need("a2cols" in src, "core.py에 a2cols 없음 — A2 가로합 성분열 완화 유실")
    need("open_cols" in src, "core.py에 open_cols 없음 — 열린 콜론 구간 경계 유실")
except Exception as e:
    fails.append(f"core import 실패: {e}")

try:
    import statements
    need(hasattr(statements, "period_axis") and hasattr(statements, "pick_period"),
         "statements.period_axis/pick_period 없음 — 기간축 2차원 해석 유실 (패치 #3)")
    need(hasattr(statements, "_PFX"), "statements._PFX 없음 — 중간보고 표제 접두 유실 (패치 #1)")
except Exception as e:
    fails.append(f"statements import 실패: {e}")

try:
    import tieout
    need(hasattr(tieout, "ALIAS") and hasattr(tieout, "sce_pt"),
         "tieout.ALIAS/sce_pt 없음 — 계정 별칭·중간보고 가드 유실 (패치 #4)")
except Exception as e:
    fails.append(f"tieout import 실패: {e}")

if fails:
    print("[INTAKE] *** 반입 사고 의심 — 저장소 수정 유실 ***")
    for m in fails: print("[INTAKE]   " + m)
    print("[INTAKE] git 이력에서 유실 파일을 복원할 것 (전체 파일 반입 금지, diff만).")
    sys.exit(1)

print("[INTAKE] 시그니처 가드 통과")
if "--full" in sys.argv:
    r = subprocess.run([sys.executable, os.path.join(HERE, "run_gates.py"),
                        os.path.join(HERE, "samples", "삼성전자_감사보고서.pdf"), "0"])
    sys.exit(r.returncode)
