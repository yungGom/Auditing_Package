# -*- coding: utf-8 -*-
"""스크리너 — 정밀 축 승격 후보 선별 (축 붕괴 자동 탐지, 완전 오프라인).

목적: DIFF 분류에 회계사 시간을 쓰지 않고, 도구가 이 샘플에서 붕괴하는지만
기계 판정한다. 빨간 신호가 뜬 샘플만 정밀 축 후보로 올린다 (정밀 축 6개 이하 유지).

사용: python screen.py <PDF...>          (파일 여러 개)
      python screen.py samples          (폴더 전체)

신호 (전부 기계 판정):
  CRASH   실행 중 예외
  본표미인식  stmt_type=None인데 제목 줄에 본표 표제가 있는 표 페이지 수 (> 0 = 빨강)
  B미검증   B 미검증 비율 >= 90%
  C붕괴    C 성립 0 또는 성립률 < 20%
  A밀도    A_total/페이지 비율이 등록 4축 대역(2.0~7.0) 밖 (침묵 소실 탐지)
  단위     환산 불가(복합·미등재) 단위 표 비율 > 20%
  기간축   period_axis nper >= 5 (미지의 기간 구조)
  참고     복합 단위 표 수 · SIGN 건수 (SIGN > 5 = 빨강)
"""
import io, os, re, sys, glob, runpy, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pdfplumber
import core, refmap
from statements import stmt_type, period_axis, STMT

A_DENSITY = (2.0, 7.0)      # 등록 4축 실측 2.88~5.72 (삼성·LGES·조선내화·휴맥스) ± 여유
# 표제 판정 — 줄(공백 제거)이 표제로 '끝나고' 전체가 짧을 것(접두 포함 <=14자).
# contains 판정은 주석 문장('...재무상태표에 인식된 금액은...')에 전량 오발화한다(4축 보정 실측)
TITLE_END = re.compile(r".{0,6}(재무상태표|손익계산서|포괄손익계산서|현금흐름표|자본변동표)$")
SUBHEAD = re.compile(r"^(\d{1,3}|[가-하])[\.\)]")   # '나.'·'30.' 류 주석 소제목·표제 제외


def run_pipeline(pdf_path):
    """final.py를 모듈로 실행해 지표 수집 (run_gates와 동일 방식)"""
    argv = sys.argv
    sys.argv = [os.path.join(HERE, "final.py"), pdf_path, "0"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            g = runpy.run_path(sys.argv[0], run_name="__main__")
    finally:
        sys.argv = argv
    stat = g["stat"]; B = g["B"]
    return dict(A_total=sum(stat.values()), A_SIGN=stat["SIGN"],
                B_total=len(B), B_unv=sum(1 for r in B if r[4] == "미검증"),
                C_ok=len(g["RLINKS"]), C_un=len(g["RUN"]))


def scan(pdf_path):
    """보조 스캔 — 본표 미인식·기간축·단위 구조"""
    miss = []; nper_max = 0
    with pdfplumber.open(pdf_path) as pdf:
        npages = len(pdf.pages)
        for pi, page in enumerate(pdf.pages, 1):
            txt = page.extract_text() or ""
            st = stmt_type(txt)
            tbs = page.find_tables()
            if st in ("BS", "IS", "CI", "CF") and tbs:   # SCE는 열 구조상 nper가 원래 5~8
                try:
                    _, npc = period_axis(tbs[0].extract())
                    nper_max = max(nper_max, npc)
                except Exception:
                    pass
            if st is None and tbs:
                lines = [l.strip() for l in txt.split("\n") if l.strip()][:3]
                for l in lines:
                    c = l.replace(" ", "")
                    if SUBHEAD.match(c): continue
                    if len(c) <= 14 and TITLE_END.fullmatch(c): miss.append(pi); break
    units = refmap.unit_texts(pdf_path)
    kinds = set(); nofit = 0
    for u in units.values():
        m = refmap._mult_of(u)
        if u is not None: kinds.add(core.norm(u).replace(" ", ""))
        if m is None: nofit += 1
    ratio_nofit = nofit / max(len(units), 1)
    return dict(pages=npages, stmt_miss=miss, nper_max=nper_max,
                unit_kinds=len(kinds), unit_nofit_ratio=ratio_nofit)


def screen_one(pdf_path):
    name = os.path.basename(pdf_path)
    row = dict(sample=name, flags=[], info={})
    try:
        m = run_pipeline(pdf_path)
        s = scan(pdf_path)
    except Exception as e:
        row["flags"].append(f"CRASH({type(e).__name__})")
        return row
    dens = m["A_total"] / max(s["pages"], 1)
    b_ratio = m["B_unv"] / max(m["B_total"], 1)
    c_tot = m["C_ok"] + m["C_un"]
    c_rate = m["C_ok"] / c_tot if c_tot else None
    if s["stmt_miss"]: row["flags"].append(f"본표미인식 p{s['stmt_miss']}")
    if b_ratio >= 0.9: row["flags"].append(f"B미검증 {b_ratio:.0%}")
    if m["C_ok"] == 0 or (c_rate is not None and c_rate < 0.2):
        row["flags"].append(f"C붕괴 {m['C_ok']}/{c_tot}")
    if not (A_DENSITY[0] <= dens <= A_DENSITY[1]):
        row["flags"].append(f"A밀도 {dens:.2f}")
    if s["unit_nofit_ratio"] > 0.2:
        row["flags"].append(f"단위 환산불가 {s['unit_nofit_ratio']:.0%}")
    if s["nper_max"] >= 5: row["flags"].append(f"기간축 nper={s['nper_max']}")
    if m["A_SIGN"] > 5: row["flags"].append(f"SIGN {m['A_SIGN']}")
    row["info"] = dict(A=m["A_total"], 밀도=round(dens, 2), B미검증율=f"{b_ratio:.0%}",
                       C=f"{m['C_ok']}/{c_tot}", 단위종류=s["unit_kinds"],
                       환산불가=f"{s['unit_nofit_ratio']:.0%}", nper=s["nper_max"],
                       SIGN=m["A_SIGN"])
    return row


if __name__ == "__main__":
    args = sys.argv[1:] or ["samples"]
    paths = []
    for a in args:
        if os.path.isdir(a): paths += sorted(glob.glob(os.path.join(a, "*.pdf")))
        else: paths.append(a)
    rows = [screen_one(p) for p in paths]
    print(f"\n{'샘플':44s} {'판정':10s} 신호/참고")
    print("-" * 110)
    for r in rows:
        verdict = "정밀후보" if r["flags"] else "정상"
        detail = " · ".join(r["flags"]) if r["flags"] else \
                 " ".join(f"{k}={v}" for k, v in r["info"].items())
        print(f"{r['sample'][:42]:44s} {verdict:10s} {detail}")
    n_red = sum(1 for r in rows if r["flags"])
    print(f"\n샘플 {len(rows)}개 중 정밀 축 후보 {n_red}개")
