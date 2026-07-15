"""실제 공시 DSD 배치 검증: G1(전수 추출) + G2(무변경 바이트 동일).

기획서 §1 표의 파일별 FS 종수/주석 수와 대조해 리포트를 출력한다.

실행: python -m dsd_tool.tests.batch_validate [fixtures_dir] [work_dir]
"""
import glob
import os
import sys
import time
import traceback

from ..excel_out import extract
from ..repack import repack

# 기획서 §1 표 (None = 스펙에 명시 없음)
SPEC = [
    # (파일명 키워드, 연결여부구분, FS 종수, 주석 수, 비고)
    ("연결감사보고서", "삼성전자", 5, 34, "연결 접두사·비지배지분"),
    ("삼성전자", None, 5, 32, "손익+포괄 분리"),
    ("LG화학", None, 5, 37, "복합단위"),
    ("에코프로비엠", None, 4, 18, "포괄손익 통합"),
    ("삼천당제약", None, 4, 41, "제목 무공백"),
    ("KB금융지주", None, 4, 33, "신탁계정 INSERTION"),
    ("삼성화재", None, 4, 43, "XML 1.6MB·TD 18,039"),
    ("노무라", None, 4, 39, "3월 결산·단일컬럼 제목"),
    ("홈플러스", None, None, 41, "계속기업 이슈"),
    ("티에스넥스젠", None, None, 40, "반기 접두사 FS"),
]


def match_spec(filename):
    for kw, kw2, fs, notes, memo in SPEC:
        if kw in filename and (kw2 is None or kw2 in filename):
            return fs, notes, memo
    return None, None, "(스펙 대조 없음)"


def validate_one(dsd_path, work_dir):
    name = os.path.basename(dsd_path)
    r = {"file": name, "g1": None, "g2": None, "fs_sheets": [],
         "note_count": None, "note_mode": None, "mapped": None,
         "te_tables": None, "sec_extract": None, "sec_repack": None,
         "error": None, "issues": []}
    exp_fs, exp_notes, memo = match_spec(name)
    r["memo"] = memo

    stem = os.path.join(work_dir, os.path.splitext(name)[0])

    # --- G1: 추출 ---
    # G2(무변경 바이트 동일)는 기계적 충실도 검증이므로
    # 주석 번호 정리를 끄고 원본 그대로 추출한다.
    try:
        t0 = time.perf_counter()
        info = extract(dsd_path, stem + ".xlsx", keep_note_numbers=True)
        r["sec_extract"] = time.perf_counter() - t0
        r["g1"] = True
        r["fs_sheets"] = info["fs_sheets"]
        r["note_count"] = info["note_count"]
        r["note_mode"] = info["note_mode"]
        r["mapped"] = info["mapped_cells"]
        r["te_tables"] = info["te_tables"]
        r["editver"] = info["editver"]
    except Exception as e:
        r["g1"] = False
        r["error"] = f"{type(e).__name__}: {e}"
        r["trace"] = traceback.format_exc()
        r["issues"].append(("G1 추출 실패", r["error"]))
        return r

    # --- G2: 무변경 역변환 → 바이트 동일 ---
    # 기계적 충실도 검증이므로 &cr;-only 정리를 끈다 (--keep-cr 모드)
    try:
        t0 = time.perf_counter()
        out = repack(stem + ".xlsx", dsd_path, stem + "_G2.dsd", clean_cr=False)
        r["sec_repack"] = time.perf_counter() - t0
        if out["changes"]:
            r["g2"] = False
            sample = [(c["sheet"], c["row"], c["col"], c["old"], c["new"])
                      for c in out["changes"][:5]]
            r["issues"].append(
                ("G2 거짓변경", f"{len(out['changes'])}건, 예: {sample}"))
        else:
            with open(out["out_path"], "rb") as f1, open(dsd_path, "rb") as f2:
                r["g2"] = f1.read() == f2.read()
            if not r["g2"]:
                r["issues"].append(("G2 바이트 불일치", "변경 0건인데 파일 상이"))
    except Exception as e:
        r["g2"] = False
        r["error"] = f"{type(e).__name__}: {e}"
        r["trace"] = traceback.format_exc()
        r["issues"].append(("G2 역변환 실패", r["error"]))

    # --- 스펙 §1 대조 ---
    if exp_fs is not None and len(r["fs_sheets"]) != exp_fs:
        r["issues"].append(
            ("FS 종수 불일치",
             f"스펙 {exp_fs}종 vs 감지 {len(r['fs_sheets'])}종 {r['fs_sheets']}"))
    if exp_notes is not None and r["note_count"] != exp_notes:
        r["issues"].append(
            ("주석 수 불일치", f"스펙 {exp_notes}개 vs 감지 {r['note_count']}개"))
    if "티에스넥스젠" in name and r["fs_sheets"] and \
            not all(s.startswith("반기") for s in r["fs_sheets"]):
        r["issues"].append(("반기 접두사 누락", str(r["fs_sheets"])))
    if "연결감사보고서" in name and r["fs_sheets"] and \
            not all(s.startswith("연결") for s in r["fs_sheets"]):
        r["issues"].append(("연결 접두사 누락", str(r["fs_sheets"])))
    return r


def main(fixtures_dir, work_dir):
    os.makedirs(work_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(fixtures_dir, "*.dsd")))
    if not files:
        print(f"DSD 파일 없음: {fixtures_dir}")
        return 1

    results = [validate_one(f, work_dir) for f in files]

    # --- 리포트 ---
    print("=" * 100)
    print(f"실제 공시 DSD 배치 검증 리포트  ({len(files)}개 파일)")
    print("=" * 100)
    for r in results:
        g1 = "PASS" if r["g1"] else "FAIL"
        g2 = "PASS" if r["g2"] else "FAIL"
        print(f"\n▶ {r['file']}")
        print(f"   G1 추출: {g1}   G2 무변경: {g2}   [{r['memo']}]")
        if r["g1"]:
            print(f"   FS {len(r['fs_sheets'])}종 {r['fs_sheets']} | "
                  f"주석 {r['note_count']}개({r['note_mode']}) | "
                  f"매핑 {r['mapped']:,}셀 | TE테이블 {r['te_tables']}개 | "
                  f"editver {r.get('editver') or '?'} | "
                  f"추출 {r['sec_extract']:.1f}s"
                  + (f" / 역변환 {r['sec_repack']:.1f}s" if r["sec_repack"] else ""))
        for kind, detail in r["issues"]:
            print(f"   ⚠ {kind}: {detail}")

    # --- 실패 원인별 분류 ---
    print("\n" + "=" * 100)
    by_cause = {}
    for r in results:
        for kind, detail in r["issues"]:
            by_cause.setdefault(kind, []).append((r["file"], detail))
    if not by_cause:
        print("전 파일 이상 없음: G1/G2 및 스펙 §1 대조 전부 일치")
    else:
        print("실패/불일치 원인별 분류")
        for kind, items in sorted(by_cause.items()):
            print(f"\n[{kind}] {len(items)}건")
            for fname, detail in items:
                print(f"  - {fname}\n      {detail}")

    ok = sum(1 for r in results if r["g1"] and r["g2"] and not r["issues"])
    print(f"\n요약: {ok}/{len(results)} 파일 완전 통과 "
          f"(G1 {sum(1 for r in results if r['g1'])}/{len(results)}, "
          f"G2 {sum(1 for r in results if r['g2'])}/{len(results)})")

    # --- KNOWN_VERSIONS.md 자동 갱신 (패치 A-3) ---
    from ..version import update_known_versions
    by_ver = {}
    for r in results:
        ver = r.get("editver")
        if not ver:
            continue
        agg = by_ver.setdefault(ver, {"files": 0, "g2_pass": True})
        agg["files"] += 1
        agg["g2_pass"] = agg["g2_pass"] and bool(r["g2"])
    if by_ver:
        path = update_known_versions(by_ver)
        print(f"KNOWN_VERSIONS.md 갱신: {path} "
              f"({', '.join(sorted(by_ver))})")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    fixtures = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(__file__), "..", "fixtures", "real")
    work = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(__file__), "..", "fixtures", "_work")
    sys.exit(main(fixtures, work))
