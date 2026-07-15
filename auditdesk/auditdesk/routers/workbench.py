"""/api/workbench — dsd_workbench 함수만 import (네트워크 금지 경계).

라우터는 얇은 래퍼 — 로직은 전부 dsd_tool 기존 함수.
repack의 승인 게이트(★)는 서버가 강제: diff 미실행 → 409.
부분 승인은 백엔드(repack)가 전체 일괄 적용만 지원하므로 422로 안내
(백엔드 수정 금지 원칙 — 변경을 빼려면 엑셀에서 되돌린 뒤 재-diff).
"""
import datetime
import hashlib
import json
import os
import uuid

from fastapi import APIRouter, HTTPException

from .. import jobs

router = APIRouter()

_WORKDIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "sessions")

_CHECKLIST = [
    "DART 편집기에서 파일이 정상적으로 열리는지 확인",
    "수정한 셀의 표시가 의도대로인지 확인 (표·주석)",
    "편집기 자체 검증(오류 검사) 통과 확인",
]


def _sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _session(sid):
    with jobs.connect() as con:
        row = con.execute(
            "SELECT id, dsd_path, created, meta, state, xlsx_path, diff, "
            "diff_options, repack FROM sessions WHERE id=?",
            (sid,)).fetchone()
    if row is None:
        raise HTTPException(404, "세션 없음")
    meta = json.loads(row[3] or "{}")
    # editver 검증 여부는 저장 스냅샷이 아니라 현재 KNOWN_VERSIONS 표
    # 기준으로 재판정 (batch_validate로 등재가 갱신되면 즉시 반영)
    if meta.get("editver"):
        from dsd_tool.version import is_known
        meta["editver_known"] = bool(is_known(meta["editver"]))
    return {"session_id": row[0], "dsd_path": row[1], "created": row[2],
            "meta": meta, "state": row[4],
            "xlsx_path": row[5],
            "diff": json.loads(row[6]) if row[6] else None,
            "diff_options": json.loads(row[7]) if row[7] else None,
            "repack": json.loads(row[8]) if row[8] else None}


def _update(sid, **cols):
    sets = ", ".join(f"{k}=?" for k in cols)
    with jobs.connect() as con:
        con.execute(f"UPDATE sessions SET {sets} WHERE id=?",
                    (*cols.values(), sid))


@router.post("/sessions", status_code=201)
def create_session(body: dict):
    dsd_path = body.get("dsd_path") or ""
    if not os.path.isfile(dsd_path):
        raise HTTPException(400, f"DSD 파일이 없습니다: {dsd_path}")
    from dsd_tool.version import is_known, read_version_info
    with open(dsd_path, "rb") as f:
        data = f.read()
    v = read_version_info(data)
    meta = {
        "file": os.path.basename(dsd_path),
        "sha1": _sha1(dsd_path),
        "size": os.path.getsize(dsd_path),
        "editver": v.get("editver"), "docver": v.get("docver"),
        "editver_known": bool(is_known(v.get("editver"))),
        "company": os.path.basename(dsd_path).split("_")[0].strip("[]"),
        "cells": None, "notes": None, "cr_only": None,   # extract 후 채움
    }
    sid = uuid.uuid4().hex[:10]
    with jobs.connect() as con:
        con.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
            (sid, os.path.abspath(dsd_path),
             datetime.datetime.now().isoformat(timespec="seconds"),
             json.dumps(meta, ensure_ascii=False), "생성됨",
             None, None, None, None))
    return {"session_id": sid, "meta": meta}


@router.get("/sessions")
def list_sessions():
    with jobs.connect() as con:
        rows = con.execute(
            "SELECT id FROM sessions ORDER BY created DESC LIMIT 50")
        ids = [r[0] for r in rows]
    return [
        {k: s[k] for k in ("session_id", "dsd_path", "created", "meta",
                           "state", "xlsx_path")}
        for s in (_session(i) for i in ids)]


@router.get("/sessions/{sid}")
def get_session(sid: str):
    s = _session(sid)
    # 파이프라인 단계 상태 (추출 → 엑셀 편집(외부) → 변경검토 → repack → DART 확인)
    s["pipeline"] = [
        {"key": "extract", "label": "추출", "done": bool(s["xlsx_path"])},
        {"key": "edit", "label": "엑셀 편집 (외부)",
         "done": bool(s["diff"] or s["repack"])},
        {"key": "diff", "label": "변경검토", "done": bool(s["diff"])},
        {"key": "repack", "label": "repack", "done": bool(s["repack"])},
        {"key": "confirm", "label": "DART 확인", "done": False},
    ]
    return s


@router.post("/sessions/{sid}/extract", status_code=202)
def extract_session(sid: str):
    s = _session(sid)
    dsd = s["dsd_path"]
    os.makedirs(_WORKDIR, exist_ok=True)
    out = os.path.join(_WORKDIR, f"{sid}_{os.path.splitext(
        os.path.basename(dsd))[0]}.xlsx")

    def _run(progress):
        progress("DSD → Excel 추출 중…")
        from dsd_tool.excel_out import extract
        info = extract(dsd, out)
        meta = s["meta"]
        meta.update(cells=info["mapped_cells"], notes=info["note_count"],
                    cr_only=info["cr_only_cells"],
                    fs_sheets=info["fs_sheets"],
                    deduped_notes=info["deduped_notes"])
        _update(sid, xlsx_path=info["out_path"], state="추출됨",
                meta=json.dumps(meta, ensure_ascii=False))
        return {"xlsx_path": info["out_path"], "meta": meta}

    return {"job_id": jobs.submit("extract", _run)}


@router.get("/sessions/{sid}/sheets")
def list_sheets(sid: str):
    s = _session(sid)
    if not s["xlsx_path"] or not os.path.exists(s["xlsx_path"]):
        raise HTTPException(409, "extract 미실행 — 먼저 추출하세요")
    from openpyxl import load_workbook
    wb = load_workbook(s["xlsx_path"], read_only=True)
    names = [n for n in wb.sheetnames if not n.startswith("_")]
    wb.close()
    return {"sheets": names}


@router.get("/sessions/{sid}/sheets/{name}")
def sheet_grid(sid: str, name: str, max_rows: int = 400,
               max_cols: int = 12):
    s = _session(sid)
    if not s["xlsx_path"]:
        raise HTTPException(409, "extract 미실행")
    from openpyxl import load_workbook
    wb = load_workbook(s["xlsx_path"], read_only=True)
    if name not in wb.sheetnames:
        wb.close()
        raise HTTPException(404, "시트 없음")
    ws = wb[name]
    grid = []
    for r, row in enumerate(ws.iter_rows(max_row=max_rows,
                                         max_col=max_cols), 1):
        vals = [(c.value if c.value is not None else None) for c in row]
        if any(v is not None for v in vals):
            grid.append({"row": r, "cells": vals})
    wb.close()
    return {"name": name, "rows": grid, "truncated": len(grid) >= max_rows}


@router.post("/sessions/{sid}/diff")
def diff_session(sid: str, body: dict = None):
    """dry-run — 변경 목록. repack 승인 게이트의 입력."""
    s = _session(sid)
    if not s["xlsx_path"] or not os.path.exists(s["xlsx_path"]):
        raise HTTPException(409, "extract 미실행 — 변경검토 대상 엑셀이 없습니다")
    options = (body or {}).get("options") or {}
    clean_cr = bool(options.get("clean_cr", True))
    from dsd_tool.repack import diff
    changes, _text, _data, stats = diff(s["xlsx_path"], s["dsd_path"],
                                        clean_cr=clean_cr)
    items = [{"id": i, "sheet": c["sheet"], "row": c["row"], "col": c["col"],
              "cell": f"R{c['row']}C{c['col']}",
              "before": c["old"], "after": c["new"], "reason": c["reason"]}
             for i, c in enumerate(changes)]
    counts = {
        "edit": sum(1 for c in items if c["reason"] == "edit"),
        "clean_cr": sum(1 for c in items if c["reason"] == "clean-cr"),
        "note_dedup": sum(1 for c in items if c["reason"] == "note-dedup"),
        "total": len(items),
    }
    payload = {"changes": items, "counts": counts, "stats": stats,
               "options": {"clean_cr": clean_cr},
               "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    _update(sid, diff=json.dumps(payload, ensure_ascii=False),
            diff_options=json.dumps({"clean_cr": clean_cr}),
            state="수정중" if items else "추출됨")
    return payload


@router.post("/sessions/{sid}/repack", status_code=202)
def repack_session(sid: str, body: dict = None):
    s = _session(sid)
    body = body or {}
    if s["diff"] is None:
        # ★ 변경검토가 승인 게이트 — 서버가 강제
        raise HTTPException(
            409, "변경검토(diff) 미실행 — repack 전에 변경 내용을 검토·"
                 "승인해야 합니다")
    options = body.get("options") or {}
    clean_cr = bool(options.get("clean_cr",
                                s["diff"]["options"]["clean_cr"]))
    if clean_cr != s["diff"]["options"]["clean_cr"]:
        raise HTTPException(409, "옵션이 변경검토 시점과 다릅니다 — "
                                 "동일 옵션으로 diff를 다시 실행하세요")
    approved = body.get("approved_change_ids", "all")
    all_ids = [c["id"] for c in s["diff"]["changes"]]
    if approved != "all":
        if sorted(approved) != sorted(all_ids):
            raise HTTPException(
                422, "부분 승인 미지원 — repack은 편집본 기준 전체 일괄 "
                     "적용입니다. 제외할 변경은 엑셀에서 되돌린 뒤 다시 "
                     "변경검토를 실행하세요 (백엔드 수정 금지 원칙)")
    dsd, xlsx = s["dsd_path"], s["xlsx_path"]

    def _run(progress):
        progress("repack 실행 중…")
        from dsd_tool.repack import repack
        info = repack(xlsx, dsd, clean_cr=clean_cr)
        result = {"output_path": info["out_path"],
                  "sha1": _sha1(info["out_path"]),
                  "n_changes": len(info["changes"]),
                  "checklist": _CHECKLIST}
        _update(sid, repack=json.dumps(result, ensure_ascii=False),
                state="repack완료")
        return result

    return {"job_id": jobs.submit("repack", _run)}


@router.get("/sessions/{sid}/history")
def session_history(sid: str, limit: int = 20, changes: bool = False):
    s = _session(sid)
    from dsd_tool.history import query_changes, query_runs
    runs = query_runs(s["dsd_path"], limit=limit)
    if changes:
        for r in runs:
            r["changes"] = query_changes(r["id"])
    return {"runs": runs}


@router.get("/version-check")
def version_check(dsd_path: str):
    if not os.path.isfile(dsd_path):
        raise HTTPException(400, f"파일 없음: {dsd_path}")
    from dsd_tool.version import g2_smoke, is_known, read_version_info
    with open(dsd_path, "rb") as f:
        v = read_version_info(f.read())
    smoke = g2_smoke(dsd_path)
    return {"editver": v.get("editver"), "known": bool(is_known(
        v.get("editver"))),
        "g2_smoke": "pass" if (smoke["changes"] == 0 and
                               smoke["byte_identical"]) else "fail"}
