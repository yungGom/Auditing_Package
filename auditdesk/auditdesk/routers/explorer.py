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
           type: str = None):
    """공시 검색 — 정기보고서. cached = XBRL zip 캐시 존재 여부."""
    if not corp:
        raise HTTPException(400, "corp(회사명 또는 corp_code) 필요")
    from dart_explorer.xbrl.pipeline import DETAIL
    cli = _client()
    corp_code = corp if (corp.isdigit() and len(corp) == 8) \
        else cli.resolve_corp_code(corp)
    year = datetime.date.today().year
    docs = cli.search(
        corp_code=corp_code,
        bgn_de=(frm or f"{year - 2}0101").replace("-", ""),
        end_de=(to or f"{year}1231").replace("-", ""),
        pblntf_detail_ty=DETAIL.get(type) if type else None)
    try:
        induty = cli.company(corp_code).get("induty_code")
    except Exception:
        induty = None
    return {"corp_code": corp_code, "induty": induty, "docs": [
        {"corp_name": d.get("corp_name"), "report_nm": d.get("report_nm"),
         "rcept_dt": d.get("rcept_dt"), "rcept_no": d.get("rcept_no"),
         "cached": _is_cached(corp_code, d.get("rcept_no", ""))}
        for d in docs]}


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
