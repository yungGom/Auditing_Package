"""작업(Job) 모델 — 장시간 작업 공통 패턴 (지시서 §1).

프로세스 내 스레드 풀 + SQLite job 테이블. 서버 재시작 시
running → interrupted 처리.
"""
import datetime
import json
import os
import sqlite3
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data",
                   "app.sqlite")
_LOCK = threading.Lock()
_POOL = ThreadPoolExecutor(max_workers=4)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY, kind TEXT, state TEXT,
  progress TEXT, result TEXT, error TEXT,
  created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY, dsd_path TEXT, created TEXT,
  meta TEXT, state TEXT, xlsx_path TEXT,
  diff TEXT, diff_options TEXT, repack TEXT);
"""


def connect():
    os.makedirs(os.path.dirname(_DB), exist_ok=True)
    con = sqlite3.connect(_DB, timeout=30)
    con.executescript(_SCHEMA)
    for col in ("foot", "recon", "xbrl_recon"):
        try:
            con.execute(f"ALTER TABLE sessions ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    for col in ("pinned", "hidden"):           # UI-8: 핀·숨김 (삭제 아님)
        try:
            con.execute(f"ALTER TABLE sessions ADD COLUMN {col} "
                        "INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    return con


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def startup_recover():
    """재시작 시 running → interrupted."""
    with _LOCK, connect() as con:
        con.execute("UPDATE jobs SET state='interrupted', updated=? "
                    "WHERE state IN ('queued','running')", (_now(),))


def submit(kind, fn):
    """fn(progress_cb) → result dict. job_id 즉시 반환 (202 패턴)."""
    job_id = uuid.uuid4().hex[:12]
    with _LOCK, connect() as con:
        con.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)",
                    (job_id, kind, "queued", "{}", None, None,
                     _now(), _now()))

    def _progress(message, current=None, total=None):
        with _LOCK, connect() as con:
            con.execute(
                "UPDATE jobs SET progress=?, updated=? WHERE id=?",
                (json.dumps({"message": message, "current": current,
                             "total": total}, ensure_ascii=False),
                 _now(), job_id))

    def _run():
        with _LOCK, connect() as con:
            con.execute("UPDATE jobs SET state='running', updated=? "
                        "WHERE id=?", (_now(), job_id))
        try:
            result = fn(_progress)
            with _LOCK, connect() as con:
                con.execute(
                    "UPDATE jobs SET state='done', result=?, updated=? "
                    "WHERE id=?",
                    (json.dumps(result, ensure_ascii=False, default=str),
                     _now(), job_id))
        except Exception as e:                     # 에러 표면화 (지시서 §3.4)
            detail = _humanize_error(e)
            with _LOCK, connect() as con:
                con.execute(
                    "UPDATE jobs SET state='error', error=?, updated=? "
                    "WHERE id=?",
                    (json.dumps({"detail": detail,
                                 "trace": traceback.format_exc()[-1500:]},
                                ensure_ascii=False), _now(), job_id))

    _POOL.submit(_run)
    return job_id


def _humanize_error(e):
    """실무자 언어로 번역 (기존 CLI 관례 재사용)."""
    from fastapi import HTTPException
    if isinstance(e, HTTPException) and e.status_code == 409:
        return str(e.detail)
    if isinstance(e, PermissionError):
        return ("파일이 다른 프로그램(엑셀 등)에서 열려 있어 접근할 수 "
                f"없습니다 — 닫고 다시 시도하세요. ({e})")
    if isinstance(e, FileNotFoundError):
        return f"파일을 찾을 수 없습니다: {e}"
    # H-2: 예외 원문을 배너에 그대로 노출하지 않는다 — 요지 + 로그 위치
    # (원문 전체는 작업 기록의 trace로 저장됨)
    return (f"작업 중 오류가 발생했습니다 ({type(e).__name__}) — "
            "상세 내용은 작업 기록(jobs)의 오류 로그에 저장되었습니다")


def get(job_id):
    with connect() as con:
        row = con.execute(
            "SELECT id, kind, state, progress, result, error, created, "
            "updated FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        return None
    return {"job_id": row[0], "kind": row[1], "state": row[2],
            "progress": json.loads(row[3] or "{}"),
            "result": json.loads(row[4]) if row[4] else None,
            "error_detail": json.loads(row[5]) if row[5] else None,
            "created": row[6], "updated": row[7]}


def list_jobs(active=False):
    q = "SELECT id FROM jobs"
    if active:
        q += " WHERE state IN ('queued','running')"
    q += " ORDER BY created DESC LIMIT 50"
    with connect() as con:
        ids = [r[0] for r in con.execute(q)]
    return [get(i) for i in ids]
