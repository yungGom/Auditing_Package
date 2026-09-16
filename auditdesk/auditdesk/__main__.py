import argparse

import uvicorn


def main(argv=None):
    p = argparse.ArgumentParser(prog="auditdesk",
                                description="AuditDesk 로컬 웹 앱")
    p.add_argument("--port", type=int, default=8710)
    sub = p.add_subparsers(dest="command")
    roll = sub.add_parser("rollforward", help="F-3b 전기 자료로 작성 준비 / 당기 갱신")
    roll.add_argument("--half", required=True, help="① 전기 반기 DSD 또는 extract Excel")
    roll.add_argument("--package", required=True, help="② 전기 기말 제출용 XBRL 패키지 폴더")
    roll.add_argument("--year-end", required=True, help="③ 전기 기말 DSD 또는 extract Excel")
    roll.add_argument("--current", help="갱신 모드: 당기 DSD 또는 extract Excel")
    roll.add_argument("--out", required=True, help="새 산출 Excel 경로 (기존 파일 덮어쓰기 금지)")
    golden = sub.add_parser("golden", help="당기 DSD와 확인된 당기 정의/배치로 Golden .xls 두 파일 생성")
    golden.add_argument("--current-dsd", required=True)
    golden.add_argument("--taxonomy", required=True, help="당기 정의를 담은 taxonomy .xls")
    golden.add_argument("--layout", required=True, help="확인된 당기 Excel 배치 .xls")
    golden.add_argument("--bindings", required=True, help="당기 원천 해시·보고 문맥·명시적 셀 연결 JSON")
    golden.add_argument("--out", required=True, help="존재하지 않는 새 산출 폴더")
    args = p.parse_args(argv)
    if args.command == "golden":
        import json
        import os
        import sys
        from pathlib import Path
        from zipfile import BadZipFile
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "dsd_workbench"))
        from .golden import build_current
        try:
            manifest = json.loads(Path(args.bindings).read_text(encoding="utf-8-sig"))
            print("당기 원천·정의·셀 연결 검사 중…")
            result = build_current(args.current_dsd, args.taxonomy, args.layout, manifest, args.out)
        except (ValueError, OSError, KeyError, TypeError, BadZipFile) as e:
            p.error(f"Golden 생성 입력을 확인하세요: {e}")
        print(f"생성 완료: {result['taxonomy']} / {result['excel']}")
        print(f"검토 근거: {Path(args.out) / 'review.json'} (실제 편집기 호환성은 별도 확인)")
        return
    if args.command == "rollforward":
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "dsd_workbench"))
        from .completion import run_rollforward
        try:
            result = run_rollforward(args.half, args.package, args.year_end,
                os.path.abspath(args.out), current=args.current)
        except (ValueError, FileNotFoundError, PermissionError) as e:
            p.error(str(e))
        print(f"완료: {result['out_path']}")
        print(f"입력 ① {args.half} / ② {args.package} / ③ {args.year_end}")
        print(f"모드: {'갱신 ' + args.current if args.current else '신규'}")
        print(f"프리필: {result['prefilled']}/{result['total']} · 가이드 판단필요: {result['guide_check']['need_judge']}")
        return
    uvicorn.run("auditdesk.app:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
