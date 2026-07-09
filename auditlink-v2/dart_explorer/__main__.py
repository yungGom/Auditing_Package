"""CLI: python -m dart_explorer search ... (fetch/xbrl은 패치 B-2/B-3)."""
import argparse
import sys


def _setup_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _setup_console()
    parser = argparse.ArgumentParser(
        prog="dart_explorer", description="공개 공시 검색·수집 (OpenDART 수신 전용)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_s = sub.add_parser("search", help="공시검색 (list.json)")
    p_s.add_argument("corp", help="회사명 또는 8자리 corp_code")
    p_s.add_argument("--start", required=True, help="시작일 YYYYMMDD")
    p_s.add_argument("--end", required=True, help="종료일 YYYYMMDD")
    p_s.add_argument("--kind", default="A",
                     help="공시유형 pblntf_ty (기본 A=정기공시)")
    p_s.add_argument("--detail", default=None,
                     help="상세유형 pblntf_detail_ty (예: A001=사업보고서)")
    p_s.add_argument("--induty", default=None,
                     help="업종코드 필터 (회사개황 기준 클라이언트측)")
    p_s.add_argument("--force", action="store_true", help="캐시 무시 재조회")

    p_x = sub.add_parser("xbrl", help="XBRL 수신→추출[→버전대사] 원클릭 (B-3)")
    p_x.add_argument("corp", help="회사명 또는 8자리 corp_code")
    p_x.add_argument("year", type=int, help="사업연도 (예: 2025)")
    p_x.add_argument("--diff", type=int, default=None,
                     help="비교할 전기 사업연도 (예: 2024)")
    p_x.add_argument("--report", default="annual",
                     choices=["annual", "half", "q1", "q3"],
                     help="정기보고서 종류 (기본 annual=사업보고서)")
    p_x.add_argument("--out", default=None, help="산출 폴더 (기본 cache/xbrl)")

    p_t = sub.add_parser("taxtree",
                         help="택사노미 트리 뷰 엑셀 (D-1, 이미지2 형식)")
    p_t.add_argument("source", help="XBRL 패키지 폴더 또는 금감원 택사노미 xlsm")
    p_t.add_argument("-o", "--out", default=None, help="출력 .xlsx 경로")
    p_t.add_argument("--role", default=None,
                     help="Role 필터 (예: D210000 — 정의 문자열 부분일치)")

    p_d = sub.add_parser("dimtable",
                         help="차원 표 렌더러 (D-2, DART 뷰어식 배치)")
    p_d.add_argument("source", help="XBRL 패키지 폴더")
    p_d.add_argument("-o", "--out", default=None, help="출력 .xlsx 경로")
    p_d.add_argument("--role", default=None,
                     help="Role 필터 (예: D610005 — 부분일치, 기본 전체)")

    p_c = sub.add_parser("corpus", help="매핑 코퍼스 구축·통계 (D-3a)")
    c_sub = p_c.add_subparsers(dest="corpus_cmd", required=True)
    c_b = c_sub.add_parser("build", help="XBRL 일괄 수신·적재 (재개 가능)")
    c_b.add_argument("--year", type=int, required=True, help="사업연도")
    c_b.add_argument("--limit", type=int, default=None,
                     help="목표 총 회사 수 (기존 처리분 포함)")
    c_sub.add_parser("stats", help="코퍼스 통계")
    c_l = c_sub.add_parser("load-standard", help="금감원 xlsm 표준 라벨 적재")
    c_l.add_argument("xlsm", help="금감원 택사노미 xlsm 경로")

    args = parser.parse_args(argv)

    if args.cmd == "search":
        from .client import OpenDartClient
        cli = OpenDartClient()
        kw = dict(bgn_de=args.start, end_de=args.end, pblntf_ty=args.kind,
                  pblntf_detail_ty=args.detail, induty_code=args.induty,
                  force=args.force)
        if args.corp.isdigit() and len(args.corp) == 8:
            kw["corp_code"] = args.corp
        else:
            kw["corp_name"] = args.corp
        docs = cli.search(**kw)
        print(f"공시 {len(docs)}건")
        for d in docs:
            print(f"  {d['rcept_no']}  {d['rcept_dt']}  [{d['corp_name']}] "
                  f"{d['report_nm']}")
        return 0

    if args.cmd == "xbrl":
        from .xbrl.pipeline import XbrlNotAvailable, run
        try:
            res = run(args.corp, args.year, diff_year=args.diff,
                      report=args.report, out_dir=args.out)
        except XbrlNotAvailable as e:
            print(f"결과 없음: {e}")
            return 1
        print(f"XBRL 수신: {res['report_nm']} (rcept {res['rcept_no']})")
        print(f"  해제 폴더: {res['folder']}"
              f"  (lab-ko: {'있음' if res['has_ko_labels'] else '없음'})")
        print(f"  추출 완료: {res['rows']:,}건 → {res['xlsx']}")
        if args.diff is not None:
            print(f"  버전대사: {res['diff_rows']:,}개 계정 → "
                  f"{res['diff_xlsx']}")
        return 0

    if args.cmd == "dimtable":
        from .xbrl.dimension_table import render_dimension_tables
        res = render_dimension_tables(args.source, args.out,
                                      role_filter=args.role)
        print(f"차원 표 생성: {res['out_path']}")
        for r in res["roles"]:
            print(f"  [{r['axes']}축/{r['sections']}표/{r['rows']}행] "
                  f"{r['definition'][:70]}")
        return 0

    if args.cmd == "corpus":
        from .xbrl import corpus
        if args.corpus_cmd == "build":
            counts = corpus.build(args.year, limit=args.limit,
                                  progress=print)
            print(f"빌드 결과: {counts}")
        elif args.corpus_cmd == "load-standard":
            n = corpus.load_standard_labels(args.xlsm)
            print(f"표준 라벨 적재: {n:,}건")
        else:
            s = corpus.stats()
            print(f"회사: {s['companies']}")
            print(f"usages {s['usages']:,}행 / 고유 element "
                  f"{s['distinct_elements']:,} / 확장 {s['extensions']:,} "
                  f"/ 표준라벨 {s['standard_labels']:,}")
            print("사용 회사수 상위 element:")
            for eid, n, label in s["top_elements"]:
                print(f"  {n:>4}사  {eid}  ({label})")
        return 0

    if args.cmd == "taxtree":
        from .xbrl.taxonomy import build_tree_view
        res = build_tree_view(args.source, args.out, role_filter=args.role)
        print(f"트리 뷰 생성: {res['out_path']}")
        arcs = f", 아크 {res['arcs']}개" if res["arcs"] is not None else ""
        print(f"  Role {res['roles']}개 / 행 {res['rows']:,}개{arcs}"
              f" / 확장 element {res['extensions']}개(빨간 표시)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
