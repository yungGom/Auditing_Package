"""E-0 대시보드 FastAPI 앱 — 전부 기존 데이터 소스의 읽기 전용 조회.

- 코퍼스: dart_explorer/corpus/mapping_corpus.sqlite (mode=ro)
- 수정이력: dsd_workbench/history/history.sqlite (mode=ro, 파일 읽기)
- 테스트: .test_results.json (pytest 후크 기록)
- 게이트: GATES.json (수동 기록)
- 편집기 버전: dsd_workbench/KNOWN_VERSIONS.md (표 파싱, 파일 읽기 —
  dsd_workbench는 코드 import 없이 파일로만 접근해 네트워크 경계를 유지한다)
"""
import datetime
import json
import os
import re
import sqlite3

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DB = os.path.join(_ROOT, "dart_explorer", "corpus",
                         "mapping_corpus.sqlite")
HISTORY_DB = os.path.join(_ROOT, "dsd_workbench", "history",
                          "history.sqlite")
CORP_CODES = os.path.join(_ROOT, "dart_explorer", "cache", "corp",
                          "corp_codes.json")
TEST_RESULTS = os.path.join(_ROOT, ".test_results.json")
GATES = os.path.join(_ROOT, "GATES.json")
KNOWN_VERSIONS = os.path.join(_ROOT, "dsd_workbench", "KNOWN_VERSIONS.md")

_KV_ROW_RE = re.compile(
    r"^\|\s*(\d+(?:\.\d+)+)\s*\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|")
DAILY_LIMIT = 20000
# 회사 1곳 처리 ≈ 요청 3건 (list 검색 + fnlttXbrl + company) — 추정치 표기용
_REQ_PER_COMPANY = 3

app = FastAPI(title="AuditLink 관제탑 (읽기 전용)")


def _ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)


def _corpus_status():
    out = {"available": os.path.exists(CORPUS_DB)}
    if not out["available"]:
        return out
    try:
        con = _ro(CORPUS_DB)
        out["by_status"] = dict(con.execute(
            "SELECT status, COUNT(*) FROM companies GROUP BY status"))
        out["processed"] = sum(out["by_status"].values())
        today = datetime.date.today().isoformat()
        out["today_companies"] = con.execute(
            "SELECT COUNT(*) FROM companies WHERE fetched_at LIKE ?",
            (today + "%",)).fetchone()[0]
        out["today_requests_est"] = out["today_companies"] * _REQ_PER_COMPANY
        out["daily_limit"] = DAILY_LIMIT
        out["usages"] = con.execute(
            "SELECT COUNT(*) FROM usages").fetchone()[0]
        out["distinct_elements"] = con.execute(
            "SELECT COUNT(DISTINCT element_id) FROM usages").fetchone()[0]
        out["extensions"] = con.execute(
            "SELECT COUNT(*) FROM extensions").fetchone()[0]
        out["last"] = con.execute(
            "SELECT corp_name, status, fetched_at FROM companies "
            "ORDER BY fetched_at DESC LIMIT 1").fetchone()
        con.close()
    except sqlite3.Error as e:
        out["error"] = str(e)
    total = None
    if os.path.exists(CORP_CODES):
        try:
            with open(CORP_CODES, encoding="utf-8") as f:
                total = sum(1 for c in json.load(f) if c.get("stock_code"))
        except (OSError, ValueError):
            pass
    out["target_total"] = total
    return out


def _recent_runs(limit=10):
    if not os.path.exists(CORPUS_DB):
        return []
    try:
        con = _ro(CORPUS_DB)
        rows = con.execute(
            "SELECT corp_name, status, error, rcept_no, fetched_at "
            "FROM companies ORDER BY fetched_at DESC LIMIT ?",
            (limit,)).fetchall()
        con.close()
        return [{"corp": r[0], "status": r[1], "error": r[2] or "",
                 "rcept_no": r[3] or "", "at": r[4]} for r in rows]
    except sqlite3.Error:
        return []


def _recent_history(limit=10):
    if not os.path.exists(HISTORY_DB):
        return []
    try:
        con = _ro(HISTORY_DB)
        rows = con.execute(
            "SELECT ts, dsd_path, out_path, clean_cr, edits, cleans, dedups "
            "FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        con.close()
        return [{"ts": r[0], "dsd": os.path.basename(r[1]),
                 "out": os.path.basename(r[2]),
                 "mode": "기본" if r[3] else "keep-cr",
                 "edits": r[4], "cleans": r[5], "dedups": r[6]}
                for r in rows]
    except sqlite3.Error:
        return []


def _known_versions():
    if not os.path.exists(KNOWN_VERSIONS):
        return []
    rows = []
    with open(KNOWN_VERSIONS, encoding="utf-8") as f:
        for line in f:
            m = _KV_ROW_RE.match(line)
            if m:
                rows.append({"editver": m.group(1), "files": int(m.group(2)),
                            "g2": m.group(3), "date": m.group(4)})
    return rows


def _read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


@app.get("/api/status")
def status():
    return {
        "now": datetime.datetime.now().isoformat(timespec="seconds"),
        "corpus": _corpus_status(),
        "recent_runs": _recent_runs(),
        "history": _recent_history(),
        "tests": _read_json(TEST_RESULTS),
        "gates": (_read_json(GATES) or {}).get("gates", []),
        "known_versions": _known_versions(),
    }


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__), "index.html"),
              encoding="utf-8") as f:
        return f.read()
