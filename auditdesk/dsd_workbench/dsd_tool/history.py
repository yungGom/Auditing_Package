"""repack 수정이력 관리 (감사조서 증빙용, 패치 A-2).

repack 실행마다 dsd_workbench/history/history.sqlite에 기록한다.
- runs: 실행시각, 원본 경로+SHA1, 출력 경로, 옵션, 변경 요약
- changes: 셀 단위 변경 내역 (시트/행/열/변경전/변경후/reason)

DB 경로는 환경변수 DSD_TOOL_HISTORY 로 재지정 가능 (테스트용).
--dry-run(diff)은 기록하지 않는다.
"""
import datetime
import hashlib
import os
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  dsd_path TEXT NOT NULL,
  dsd_sha1 TEXT NOT NULL,
  xlsx_path TEXT NOT NULL,
  out_path TEXT NOT NULL,
  clean_cr INTEGER NOT NULL,
  edits INTEGER NOT NULL,
  cleans INTEGER NOT NULL,
  dedups INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS changes(
  run_id INTEGER NOT NULL REFERENCES runs(id),
  sheet TEXT, row INTEGER, col INTEGER,
  old TEXT, new TEXT, reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_changes_run ON changes(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_dsd ON runs(dsd_path);
"""


def default_db_path() -> str:
    env = os.environ.get("DSD_TOOL_HISTORY")
    if env:
        return env
    workbench = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(workbench, "history", "history.sqlite")


def _connect(db_path=None):
    path = db_path or default_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(_SCHEMA)
    return con


def file_sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_run(dsd_path, xlsx_path, out_path, clean_cr, changes,
               db_path=None) -> int:
    """repack 1회 실행 기록. run_id 반환."""
    counts = {"edit": 0, "clean-cr": 0, "note-dedup": 0}
    for ch in changes:
        counts[ch["reason"]] = counts.get(ch["reason"], 0) + 1
    con = _connect(db_path)
    try:
        cur = con.execute(
            "INSERT INTO runs(ts, dsd_path, dsd_sha1, xlsx_path, out_path,"
            " clean_cr, edits, cleans, dedups) VALUES(?,?,?,?,?,?,?,?,?)",
            (datetime.datetime.now().isoformat(timespec="seconds"),
             os.path.abspath(dsd_path), file_sha1(dsd_path),
             os.path.abspath(xlsx_path), os.path.abspath(out_path),
             int(clean_cr), counts["edit"], counts["clean-cr"],
             counts["note-dedup"]))
        run_id = cur.lastrowid
        con.executemany(
            "INSERT INTO changes(run_id, sheet, row, col, old, new, reason)"
            " VALUES(?,?,?,?,?,?,?)",
            [(run_id, ch["sheet"], ch["row"], ch["col"],
              str(ch["old"]), str(ch["new"]), ch["reason"])
             for ch in changes])
        con.commit()
        return run_id
    finally:
        con.close()


def query_runs(dsd_path=None, limit=20, db_path=None):
    """실행 이력 조회 (최신순). dsd_path 지정 시 해당 원본 것만."""
    con = _connect(db_path)
    try:
        con.row_factory = sqlite3.Row
        if dsd_path:
            rows = con.execute(
                "SELECT * FROM runs WHERE dsd_path = ? OR dsd_path LIKE ?"
                " ORDER BY id DESC LIMIT ?",
                (os.path.abspath(dsd_path), f"%{os.path.basename(dsd_path)}",
                 limit)).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def query_changes(run_id, db_path=None):
    con = _connect(db_path)
    try:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT sheet, row, col, old, new, reason FROM changes"
            " WHERE run_id = ? ORDER BY rowid", (run_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
