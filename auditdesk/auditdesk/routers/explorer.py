"""/api/explorer — dart_explorer (OpenDART 수신 허용 모듈).

라우터는 얇은 래퍼 — 검색/수신/파이프라인/코퍼스/설정 전부 기존 함수.
"""
import datetime
import glob
import os
import uuid

from fastapi import APIRouter, HTTPException

from .. import jobs

router = APIRouter()

_EXPLORER_DIR = None


def _client():
    from dart_explorer.client.opendart import OpenDartClient
    return OpenDartClient()


def _cache_root():
    from dart_explorer.client.opendart import OpenDartClient
    import inspect
    mod_dir = os.path.dirname(os.path.dirname(
        inspect.getfile(OpenDartClient)))
    return os.path.join(mod_dir, "cache")


def _is_cached(corp_code, rcept_no):
    return bool(glob.glob(os.path.join(
        _cache_root(), "xbrl", corp_code, f"{rcept_no}_*.zip")))


@router.get("/corps")
def corps(q: str = "", limit: int = 10):
    """회사명 자동완성 — corpCode 캐시 프리픽스 검색 (상장사 우선)."""
    if len(q.strip()) < 2:
        return {"corps": []}
    cli = _client()
    hits = []
    for c in cli.corp_codes():
        if q in c["corp_name"]:
            hits.append({"corp_code": c["corp_code"],
                         "corp_name": c["corp_name"],
                         "stock_code": c["stock_code"] or None})
    hits.sort(key=lambda c: (c["stock_code"] is None,
                             len(c["corp_name"])))
    return {"corps": hits[:limit]}


@router.get("/search")
def search(corp: str = "", frm: str = None, to: str = None,
           type: str = None, induty: str = None):
    """공시 검색 — 정기보고서. cached = XBRL zip 캐시 존재 여부.

    induty 지정 + corp 생략 = 동종업계 스캔 (기존 클라이언트의
    induty_code 필터 — 회사개황 조회 기반이라 최근 3페이지로 제한).
    """
    if not corp and not induty:
        raise HTTPException(400, "corp(회사명·corp_code) 또는 induty 필요")
    from dart_explorer.xbrl.pipeline import DETAIL
    cli = _client()
    year = datetime.date.today().year
    common = dict(
        bgn_de=(frm or f"{year - 2}0101").replace("-", ""),
        end_de=(to or f"{year}1231").replace("-", ""),
        pblntf_detail_ty=DETAIL.get(type) if type else None)
    if corp:
        corp_code = corp if (corp.isdigit() and len(corp) == 8) \
            else cli.resolve_corp_code(corp)
        docs = cli.search(corp_code=corp_code,
                          induty_code=induty or None, **common)
        try:
            corp_induty = cli.company(corp_code).get("induty_code")
        except Exception:
            corp_induty = None
    else:                                   # 동종업계 보기 (벤치마크 동선)
        corp_code = None
        corp_induty = induty
        docs = cli.search(induty_code=induty, max_pages=3, **common)
    return {"corp_code": corp_code, "induty": corp_induty, "docs": [
        {"corp_code": d.get("corp_code"),
         "corp_name": d.get("corp_name"), "report_nm": d.get("report_nm"),
         "rcept_dt": d.get("rcept_dt"), "rcept_no": d.get("rcept_no"),
         "cached": _is_cached(d.get("corp_code") or corp_code or "",
                              d.get("rcept_no", ""))}
        for d in docs]}


@router.get("/peer-induty")
def peer_induty():
    """동종업계 프리셋 — 최근 Workbench 세션 회사의 업종코드."""
    with jobs.connect() as con:
        row = con.execute("SELECT meta FROM sessions "
                          "ORDER BY created DESC LIMIT 1").fetchone()
    if row is None:
        return {"induty": None}
    import json as _json
    company = (_json.loads(row[0] or "{}") or {}).get("company")
    if not company:
        return {"induty": None}
    try:
        cli = _client()
        code = cli.resolve_corp_code(company)
        return {"induty": cli.company(code).get("induty_code"),
                "company": company}
    except Exception as e:
        return {"induty": None, "company": company, "error": str(e)[:120]}


# --------------------------------------------------------------------------
# UI-5 동선 통합 — 수신(explorer)과 변환(dsd_tool/dart_explorer 기존 함수)을
# 원클릭으로 연결. 기능 신규 0 — 캐시 경로를 내부 전달만 한다.
# --------------------------------------------------------------------------

@router.post("/dsd", status_code=202)
def dsd_save(body: dict):
    """[DSD 저장] — 공시원본 수신(캐시) → DSD 래핑 → 지정 위치 복사.

    래핑본은 읽기 전용 수신물(meta.xml 없음 — B-2 원칙 그대로).
    """
    corp_code = body.get("corp_code") or ""
    rcept_no = body.get("rcept_no") or ""
    save_to = body.get("save_to")
    if not corp_code or not rcept_no:
        raise HTTPException(400, "corp_code/rcept_no 필요")

    def _run(progress):
        import shutil
        progress("공시원본 수신 중… (캐시 히트 시 재다운로드 없음)")
        from dart_explorer.converters.document_wrap import fetch_and_wrap
        path = fetch_and_wrap(_client(), corp_code, rcept_no)
        if save_to:
            shutil.copyfile(path, save_to)
            path = save_to
        return {"dsd_path": path}

    return {"job_id": jobs.submit("dsd-save", _run)}


@router.post("/to-excel", status_code=202)
def to_excel(body: dict):
    """[엑셀로 변환] — 원본 수신(캐시) → dsd_tool extract → 편집용 xlsx.

    ACCIO 대응 동선: 검색에서 클릭 2번 안에 엑셀.
    """
    corp_code = body.get("corp_code") or ""
    rcept_no = body.get("rcept_no") or ""
    if not corp_code or not rcept_no:
        raise HTTPException(400, "corp_code/rcept_no 필요")

    def _run(progress):
        progress("공시원본 수신 중…")
        from dart_explorer.converters.document_wrap import fetch_and_wrap
        dsd = fetch_and_wrap(_client(), corp_code, rcept_no)
        progress("DSD → Excel 추출 중…")
        from dsd_tool.excel_out import extract
        xlsx = os.path.splitext(dsd)[0] + ".xlsx"
        info = extract(dsd, xlsx)
        return {"xlsx_path": info["out_path"], "dsd_path": dsd,
                "cells": info["mapped_cells"], "notes": info["note_count"]}

    return {"job_id": jobs.submit("to-excel", _run)}


@router.post("/dimtable-from-search", status_code=202)
def dimtable_from_search(body: dict):
    """[차원표 엑셀] — XBRL 수신(캐시) → D-2 렌더 → BS/PL/1..N 시트 xlsx.

    '주석 번호별 택사노미+숫자' 산출물 — 검색에서 직행.
    """
    corp_code = body.get("corp_code") or ""
    rcept_no = body.get("rcept_no") or ""
    report = body.get("report") or "annual"
    if not corp_code or not rcept_no:
        raise HTTPException(400, "corp_code/rcept_no 필요")

    def _run(progress):
        from dart_explorer.xbrl.pipeline import (REPRT, download_xbrl,
                                                 unpack_xbrl)
        progress("1/2 XBRL 수신 중… (캐시 히트 시 재다운로드 없음)", 1, 2)
        _, zpath = download_xbrl(_client(), corp_code, rcept_no,
                                 REPRT[report])
        folder = unpack_xbrl(zpath)
        progress("2/2 차원 표 렌더링 중…", 2, 2)
        from dart_explorer.xbrl.dimension_table import \
            render_dimension_tables
        out = os.path.join(folder, "차원표.xlsx")
        res = render_dimension_tables(folder, out_path=out)
        return {"xlsx_path": res["out_path"], "package": folder,
                "sheets": [r["sheet"] for r in res["roles"]]}

    return {"job_id": jobs.submit("dimtable-from-search", _run)}


@router.get("/packages")
def packages(limit: int = 15):
    """최근 수신 XBRL 패키지 목록 — Studio 경로 드롭다운용."""
    root = os.path.join(_cache_root(), "xbrl")
    out = []
    if os.path.isdir(root):
        for corp in os.listdir(root):
            cdir = os.path.join(root, corp)
            if not os.path.isdir(cdir):
                continue
            for entry in os.listdir(cdir):
                p = os.path.join(cdir, entry)
                if os.path.isdir(p) and glob.glob(
                        os.path.join(p, "*.xbrl")):
                    out.append({"path": p, "corp_code": corp,
                                "name": f"{corp} / {entry}",
                                "mtime": os.path.getmtime(p)})
    out.sort(key=lambda x: -x["mtime"])
    return {"packages": out[:limit]}


@router.post("/fetch", status_code=202)
def fetch(body: dict):
    corp_code = body.get("corp_code") or ""
    rcept_no = body.get("rcept_no") or ""
    report = body.get("report") or "annual"
    if not corp_code or not rcept_no:
        raise HTTPException(400, "corp_code/rcept_no 필요")

    def _run(progress):
        from dart_explorer.xbrl.pipeline import (REPRT, download_xbrl,
                                                 unpack_xbrl)
        progress("XBRL ZIP 수신 중… (캐시 히트 시 재다운로드 없음)")
        _, zpath = download_xbrl(_client(), corp_code, rcept_no,
                                 REPRT[report])
        progress("압축 해제 중…")
        folder = unpack_xbrl(zpath)
        return {"folder": folder, "zip": zpath}

    return {"job_id": jobs.submit("fetch", _run)}


@router.post("/xbrl", status_code=202)
def xbrl(body: dict):
    """원클릭 파이프라인 — 검색→수신→해제→추출 (스텝을 progress로 중계)."""
    corp = body.get("corp") or ""
    year = int(body.get("year") or 0)
    report = body.get("report") or "annual"
    if not corp or not year:
        raise HTTPException(400, "corp/year 필요")

    def _run(progress):
        from dart_explorer.xbrl.pipeline import (REPRT, XbrlNotAvailable,
                                                 download_xbrl,
                                                 extract_to_excel,
                                                 find_periodic_rcept,
                                                 unpack_xbrl)
        cli = _client()
        corp_code = corp if (corp.isdigit() and len(corp) == 8) \
            else cli.resolve_corp_code(corp)
        progress(f"1/4 접수번호 검색 — {year}년 {report}", 1, 4)
        doc = find_periodic_rcept(cli, corp_code, year, report)
        if doc is None:
            raise XbrlNotAvailable(
                f"{year}년 {report} 정기보고서를 찾을 수 없습니다")
        progress(f"2/4 XBRL 수신 — {doc['rcept_no']} "
                 f"({doc.get('report_nm', '')})", 2, 4)
        _, zpath = download_xbrl(cli, corp_code, doc["rcept_no"],
                                 REPRT[report])
        progress("3/4 압축 해제", 3, 4)
        folder = unpack_xbrl(zpath)
        progress("4/4 팩트 추출 → 엑셀", 4, 4)
        out_xlsx = os.path.join(folder, "추출.xlsx")
        n = extract_to_excel(folder, out_xlsx)
        return {"corp_code": corp_code, "rcept_no": doc["rcept_no"],
                "report_nm": doc.get("report_nm"), "folder": folder,
                "xlsx_path": out_xlsx, "facts": n}

    return {"job_id": jobs.submit("xbrl", _run)}


@router.get("/corpus/stats")
def corpus_stats():
    from dashboard.app import _corpus_status
    return _corpus_status()


@router.post("/corpus/build", status_code=202)
def corpus_build(body: dict = None):
    body = body or {}
    year = int(body.get("year") or datetime.date.today().year - 1)
    limit = body.get("limit")

    def _run(progress):
        from dart_explorer.xbrl.corpus import build
        res = build(year, limit=int(limit) if limit else None,
                    progress=lambda m: progress(str(m)))
        return res

    return {"job_id": jobs.submit("corpus-build", _run)}


@router.get("/settings")
def settings():
    api_key_set = True
    try:
        from dart_explorer.client.config import load_api_key
        load_api_key()
    except Exception:
        api_key_set = False
    root = _cache_root()
    size = 0
    files = 0
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            try:
                size += os.path.getsize(os.path.join(dirpath, n))
                files += 1
            except OSError:
                pass
    from dashboard.app import _corpus_status
    cs = _corpus_status()
    return {"api_key_set": api_key_set,
            "cache_path": root, "cache_files": files,
            "cache_size_mb": round(size / 1048576, 1),
            "today_usage": cs.get("today_requests_est"),
            "daily_limit": cs.get("daily_limit"),
            "corpus": {"processed": cs.get("processed"),
                       "ok": (cs.get("by_status") or {}).get("ok")}}


@router.delete("/cache")
def clear_cache(confirm: str = ""):
    """공시 캐시 비우기 — 파괴적: confirm=DELETE 필수 (재다운로드 가능
    자료지만 요청 한도를 소모하므로 이중 확인)."""
    if confirm != "DELETE":
        raise HTTPException(400, "확인 필요 — ?confirm=DELETE 로 호출")
    import shutil
    root = _cache_root()
    n = 0
    for entry in os.listdir(root) if os.path.isdir(root) else []:
        p = os.path.join(root, entry)
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            n += 1
        except OSError:
            pass
    return {"cleared": n}
