"""CLI: python -m dsd_tool extract|repack ..."""
import argparse
import sys


def _println(s: str):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode(sys.stdout.encoding or "utf-8", "replace").decode(
            sys.stdout.encoding or "utf-8"))


def _setup_console():
    """Windows 콘솔 한글 깨짐 방지."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _setup_console()
    parser = argparse.ArgumentParser(
        prog="dsd_tool", description="DSD ↔ Excel 변환 도구 (v3)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ext = sub.add_parser("extract", help="DSD → Excel 추출")
    p_ext.add_argument("dsd", help="원본 .dsd 파일")
    p_ext.add_argument("-o", "--out", help="출력 .xlsx 경로 (기본: 원본명.xlsx)")
    p_ext.add_argument("--report", action="store_true",
                       help="&cr;-only 셀(개행만 있는 셀) 개수 리포트 출력")
    p_ext.add_argument("--keep-note-numbers", action="store_true",
                       help="주석 헤더의 중복 번호(\"1. 1. 제목\")를 정리하지 "
                            "않고 원본 그대로 기록")

    p_rep = sub.add_parser("repack", help="편집된 Excel → DSD 역변환")
    p_rep.add_argument("xlsx", help="편집된 .xlsx 파일")
    p_rep.add_argument("dsd", help="추출에 사용한 원본 .dsd 파일")
    p_rep.add_argument("-o", "--out", help="출력 .dsd 경로 (기본: 원본명_수정.dsd)")
    p_rep.add_argument("--dry-run", action="store_true",
                       help="변경 목록만 출력하고 파일은 만들지 않음")
    p_rep.add_argument("--keep-cr", action="store_true",
                       help="&cr;-only 셀 정리를 끄고 원문 그대로 보존 "
                            "(정리가 기본 동작)")
    p_rep.add_argument("--clean-cr", action="store_true",
                       help=argparse.SUPPRESS)  # 기본 동작이 됨 (하위호환 no-op)

    p_foot = sub.add_parser("foot", help="Footing 검증 (합계검증·주석대사·전기대사)")
    p_foot.add_argument("xlsx", help="검증할 편집용 .xlsx (extract 산출물)")
    p_foot.add_argument("--limit", type=int, default=2,
                        help="단수차 허용 한도 (기본 ±2)")
    p_foot.add_argument("--prior", help="전기 .xlsx — 전기대사 모드")
    p_foot.add_argument("--report", action="store_true",
                        help="관계별 상세 출력")

    p_map = sub.add_parser("map",
                           help="계정과목 → XBRL element 매핑 추천 (완전 로컬)")
    p_map.add_argument("xlsx", nargs="?",
                       help="입력 템플릿 .xlsx (계정과목명|구분|비고)")
    p_map.add_argument("--template", metavar="경로",
                       help="빈 입력 템플릿 생성 후 종료")
    p_map.add_argument("--corpus", default=None,
                       help="mapping_corpus.sqlite 경로 (기본: dart_explorer 산출물)")
    p_map.add_argument("--induty", default=None,
                       help="회사 업종코드 — 동업종 실증 가중치 ×2")
    p_map.add_argument("--threshold", type=float, default=None,
                       help="적합 표준 없음 판정 임계 (기본 0.45)")
    p_map.add_argument("-o", "--out", default=None, help="출력 .xlsx 경로")

    p_me = sub.add_parser("map-eval",
                          help="매핑 추천 홀드아웃 자동 검증 (D-3b 게이트)")
    p_me.add_argument("--corpus", default=None, help="mapping_corpus.sqlite")
    p_me.add_argument("--holdout", type=int, default=30, help="홀드아웃 회사 수")
    p_me.add_argument("--seed", type=int, default=42)
    p_me.add_argument("--caps", default=None,
                      help="구간별 샘플 상한 '쉬움:100,중간:200,함정:60'")
    p_me.add_argument("--json", dest="out_json", default=None,
                      help="리포트 JSON 저장 경로")

    p_his = sub.add_parser("history", help="repack 수정이력 조회 (감사조서 증빙)")
    p_his.add_argument("dsd", nargs="?", default=None,
                       help="원본 .dsd 경로 (생략 시 전체 이력)")
    p_his.add_argument("--limit", type=int, default=20, help="최대 표시 건수")
    p_his.add_argument("--changes", action="store_true",
                       help="셀 단위 변경 내역까지 출력")

    args = parser.parse_args(argv)

    if args.cmd == "extract":
        from .excel_out import extract
        info = extract(args.dsd, args.out,
                       keep_note_numbers=args.keep_note_numbers)
        _println(f"추출 완료: {info['out_path']}")
        _println(f"  DART 편집기 버전: editver={info['editver'] or '(없음)'}"
                 f" / docver={info['docver'] or '(없음)'}")
        if not info["editver_known"]:
            from .version import UNKNOWN_WARNING
            _println("  " + UNKNOWN_WARNING.format(ver=info["editver"]))
        _println(f"  FS 시트: {', '.join(info['fs_sheets']) or '(없음)'}")
        _println(f"  주석: {info['note_count']}개 (감지방식: {info['note_mode']})")
        if info["deduped_notes"]:
            _println(f"  주석 번호 중복 정리: {info['deduped_notes']}개 "
                     f"(repack 시 DSD에 반영, --keep-note-numbers 로 비활성)")
        _println(f"  외부감사 테이블: {info['te_tables']}개")
        _println(f"  매핑 셀: {info['mapped_cells']}개")
        if args.report:
            _println(f"  &cr;-only 셀: {info['cr_only_cells']}개 "
                     f"(repack --clean-cr 로 정리 가능)")
            for sheet, n in sorted(info["cr_only_by_sheet"].items()):
                _println(f"    [{sheet}] {n}개")
        return 0

    if args.cmd == "repack":
        from .repack import diff, repack
        clean_cr = not args.keep_cr

        def _print_summary(changes, stats, limit=50):
            edits = [c for c in changes if c["reason"] == "edit"]
            cleans = [c for c in changes if c["reason"] == "clean-cr"]
            dedups = [c for c in changes if c["reason"] == "note-dedup"]
            _println(f"  수정 셀 {len(edits)} / &cr; 정리 {len(cleans)} / "
                     f"주석번호 정리 {len(dedups)}")
            if not cleans and stats.get("cr_only_total"):
                _println(f"  ⚠ &cr; 셀 {stats['cr_only_total']}개가 보존됨 — "
                         f"의도한 게 아니면 --keep-cr 없이 재실행")
            for ch in edits[:limit]:
                _println(f"  [{ch['sheet']}] R{ch['row']}C{ch['col']}: "
                         f"{ch['old']!r} → {ch['new']!r}")
            if len(edits) > limit:
                _println(f"  ... 외 {len(edits) - limit}개")

        if args.dry_run:
            changes, _, _, stats = diff(args.xlsx, args.dsd, clean_cr=clean_cr)
            _println(f"변경 셀: {len(changes)}개 (dry-run)")
            _print_summary(changes, stats)
            return 0
        info = repack(args.xlsx, args.dsd, args.out, clean_cr=clean_cr)
        _println(f"역변환 완료: {info['out_path']}")
        _print_summary(info["changes"], info["stats"])
        return 0

    if args.cmd == "foot":
        from .foot import FUZZY, MISMATCH, foot
        res = foot(args.xlsx, limit=args.limit, prior_path=args.prior)
        _println(f"Footing 검증 완료 → _FOOT 시트 기록: {args.xlsx}")
        _println(f"  합계검증: 일치 {res['match']} / 단수차 {res['fuzzy']} / "
                 f"불일치 {res['mismatch']}")
        _println(f"  주석대사: 찾음 {res['note_found']} / "
                 f"못찾음 {res['note_missing']}")
        if res["manual_overrides"]:
            _println(f"  수동 레벨 오버라이드 적용: {res['manual_overrides']}건")
        if res["prior"]:
            import collections as _c
            pc = _c.Counter(r["verdict"] for r in res["prior"])
            _println(f"  전기대사: 일치 {pc['일치']} / 단수차 {pc['단수차']} / "
                     f"불일치 {pc['불일치']} / 매칭없음 {pc['매칭없음']}")
        problem = [r for r in res["foot"]
                   if r["verdict"] in (FUZZY, MISMATCH)]
        for r in problem[:30]:
            _println(f"  ⚠ [{r['sheet']}] {r['loc']} {r['label']!r} "
                     f"({r['scope']}/{r['direction']}): Σ자식 {r['expected']:,.0f}"
                     f" vs 기재 {r['actual']:,.0f} (차이 {r['diff']:,.0f}) "
                     f"→ {r['verdict']}")
        if args.report:
            for r in res["foot"]:
                if r["verdict"] not in (FUZZY, MISMATCH):
                    _println(f"  [{r['sheet']}] {r['loc']} {r['label']!r} "
                             f"({r['scope']}) 자식 {r['n_children']}개 → 일치")
        return 0

    if args.cmd == "map":
        from .mapping import DEFAULT_THRESHOLD, map_accounts, write_template
        if args.template:
            path = write_template(args.template)
            _println(f"입력 템플릿 생성: {path}")
            return 0
        if not args.xlsx:
            _println("입력 .xlsx 경로 또는 --template 를 지정하세요.")
            return 1
        res = map_accounts(args.xlsx, out_path=args.out,
                           db_path=args.corpus, induty=args.induty,
                           threshold=args.threshold or DEFAULT_THRESHOLD)
        _println(f"매핑 후보 생성: {res['out_path']}")
        _println(f"  계정과목 {res['items']}건 / 적합 표준 없음 "
                 f"{res['no_match']}건 (선택 열은 회계사 기입 — 자동 확정 없음)")
        return 0

    if args.cmd == "map-eval":
        from .mapping_eval import evaluate
        caps = None
        if args.caps:
            caps = {k: int(v) for k, v in
                    (kv.split(":") for kv in args.caps.split(","))}
        rep = evaluate(db_path=args.corpus, n_holdout=args.holdout,
                       caps=caps, seed=args.seed, progress=_println,
                       out_json=args.out_json)
        _println(f"홀드아웃 {rep['excluded']}사 (누수 방지 제외) / "
                 f"정답쌍 {rep['pairs_total']:,} / 표본 {rep['sampled']}")
        for tier, s in rep["tiers"].items():
            extra = (f", 확장제시 {s['ext_suggested']}/{s['n']}"
                     if "ext_suggested" in s else "")
            _println(f"  [{tier}] n={s['n']}  Top-1 {s['top1']:.1%}  "
                     f"Top-4 {s['top4']:.1%}{extra}")
        g = rep["gate"]
        _println(f"게이트({g['criterion']}): "
                 f"{'통과' if g['passed'] else '미달'}"
                 f" — 실측 {g['value']:.1%}" if g["value"] is not None
                 else "게이트: 중간 구간 표본 없음")
        for m in rep["misses"][:8]:
            _println(f"  ✗ [{m['tier']}] {m['label']!r} 정답 "
                     f"{m['element_id'][:40]} → {m['got'][:2]}")
        return 0

    if args.cmd == "history":
        from .history import default_db_path, query_changes, query_runs
        runs = query_runs(args.dsd, limit=args.limit)
        _println(f"수정이력 {len(runs)}건  (DB: {default_db_path()})")
        for r in runs:
            _println(f"\n#{r['id']}  {r['ts']}  "
                     f"[{'기본' if r['clean_cr'] else 'keep-cr'}]")
            _println(f"  원본: {r['dsd_path']}")
            _println(f"        SHA1={r['dsd_sha1'][:12]}…")
            _println(f"  출력: {r['out_path']}")
            _println(f"  수정 {r['edits']} / &cr; 정리 {r['cleans']} / "
                     f"주석번호 정리 {r['dedups']}")
            if args.changes:
                for ch in query_changes(r["id"]):
                    _println(f"    [{ch['sheet']}] R{ch['row']}C{ch['col']} "
                             f"({ch['reason']}): {ch['old']!r} → {ch['new']!r}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
