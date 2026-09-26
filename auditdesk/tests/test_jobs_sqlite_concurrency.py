"""A polling reader must not run schema migrations or fail behind a writer."""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auditdesk import jobs
from auditdesk.routers import jobs_api


@pytest.fixture
def isolated_jobs(tmp_path, monkeypatch):
    path = tmp_path / "jobs.sqlite"
    monkeypatch.setattr(jobs, "_DB", str(path))
    with jobs.connect() as con:
        con.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)",
                    ("existing", "xbrl-orchestration", "running", "{}", None, None,
                     "2026-09-24", "2026-09-24"))
    app = FastAPI()
    app.include_router(jobs_api.router, prefix="/api/jobs")
    return path, TestClient(app, raise_server_exceptions=False)


def test_get_is_read_only_after_initialization(isolated_jobs, monkeypatch):
    _, client = isolated_jobs
    original_connect = sqlite3.connect
    statements = []

    def traced(*args, **kwargs):
        con = original_connect(*args, **kwargs)
        con.set_trace_callback(statements.append)
        return con

    monkeypatch.setattr(sqlite3, "connect", traced)
    for _ in range(3):
        assert client.get("/api/jobs/existing").status_code == 200
    assert not [sql for sql in statements if sql.lstrip().upper().startswith(
        ("CREATE ", "ALTER ", "PRAGMA JOURNAL_MODE", "BEGIN IMMEDIATE"))]


def test_polling_reads_while_writer_holds_transaction(isolated_jobs):
    path, client = isolated_jobs
    writer = sqlite3.connect(path)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("UPDATE jobs SET progress=? WHERE id='existing'",
                   (json.dumps({"message": "still working"}),))
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = [pool.submit(client.get, "/api/jobs/existing") for _ in range(6)]
            listed = pool.submit(client.get, "/api/jobs")
            for result in responses + [listed]:
                response = result.result(timeout=5)
                assert response.status_code == 200, response.text
                if "job_id" in response.json():
                    assert response.json()["progress"] == {}
    finally:
        writer.rollback()
        writer.close()


def test_repeated_polling_through_background_progress_preserves_json(isolated_jobs):
    _, client = isolated_jobs
    proceed = threading.Event()

    def work(progress):
        for index in range(8):
            progress(f"stage {index}", index, 8)
            if index == 2:
                proceed.wait(timeout=5)
        return {"id": "workflow-result"}

    job_id = jobs.submit("xbrl-orchestration", work)
    counts = []
    for _ in range(30):
        response = client.get("/api/jobs/" + job_id)
        counts.append(response.status_code)
        assert response.status_code == 200, response.text
        assert isinstance(response.json()["progress"], dict)
        if response.json()["state"] == "done":
            break
        proceed.set()
        time.sleep(.01)
    assert counts and set(counts) == {200}
    final = client.get("/api/jobs/" + job_id).json()
    assert final["state"] == "done" and final["result"] == {"id": "workflow-result"}
    assert client.get("/api/jobs/existing").json()["state"] == "running"


def test_schema_init_is_idempotent_and_parallel_safe(tmp_path, monkeypatch):
    path = tmp_path / "parallel.sqlite"
    monkeypatch.setattr(jobs, "_DB", str(path))
    barrier = threading.Barrier(10)

    def open_and_read(_):
        barrier.wait(timeout=5)
        with jobs.connect() as con:
            return con.execute("SELECT count(*) FROM jobs").fetchone()[0]

    with ThreadPoolExecutor(max_workers=10) as pool:
        assert list(pool.map(open_and_read, range(10))) == [0] * 10
    jobs.startup_recover()
    with jobs.connect() as con:
        assert con.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_existing_db_migrates_and_retains_history(tmp_path, monkeypatch):
    path = tmp_path / "legacy.sqlite"
    con = sqlite3.connect(path)
    con.executescript(jobs._SCHEMA)
    con.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)",
                ("old", "mapping", "done", "{}", '{"id":"kept"}', None,
                 "2025", "2025"))
    con.commit()
    con.close()
    monkeypatch.setattr(jobs, "_DB", str(path))
    with jobs.connect() as current:
        cols = {row[1] for row in current.execute("PRAGMA table_info(sessions)")}
        assert {"foot", "recon", "xbrl_recon", "pinned", "hidden"} <= cols
    assert jobs.get("old")["result"] == {"id": "kept"}
    assert [row["job_id"] for row in jobs.list_jobs(kind="mapping")] == ["old"]


def test_failed_job_is_distinct_from_poll_transport_failure(isolated_jobs):
    _, client = isolated_jobs
    with jobs.connect() as con:
        con.execute("UPDATE jobs SET state='error', error=? WHERE id='existing'",
                    ('{"detail":"actual job failure"}',))
    response = client.get("/api/jobs/existing")
    assert response.status_code == 200
    assert response.json()["state"] == "error"
    assert response.json()["error_detail"]["detail"] == "actual job failure"


def test_unavailable_job_store_returns_retryable_error(isolated_jobs, monkeypatch):
    _, client = isolated_jobs
    def busy(*_args, **_kwargs):
        raise jobs.JobStoreBusy("작업 상태 저장소가 사용 중입니다.")
    monkeypatch.setattr(jobs, "_read", busy)
    for route in ("/api/jobs/existing", "/api/jobs"):
        response = client.get(route)
        assert response.status_code == 503
        assert response.headers["retry-after"] == "1"
        assert "사용 중" in response.json()["detail"]


def test_connection_context_closes_on_success_and_rollback(isolated_jobs):
    with jobs.connect() as con:
        assert con.execute("SELECT 1").fetchone() == (1,)
    with pytest.raises(sqlite3.ProgrammingError):
        con.execute("SELECT 1")
    with pytest.raises(RuntimeError):
        with jobs.connect() as broken:
            broken.execute("UPDATE jobs SET state='done' WHERE id='existing'")
            raise RuntimeError("abort")
    with pytest.raises(sqlite3.ProgrammingError):
        broken.execute("SELECT 1")
    assert jobs.get("existing")["state"] == "running"


def test_database_file_is_preserved_after_polling(isolated_jobs):
    path, client = isolated_jobs
    before = path.stat().st_ino
    for _ in range(10):
        assert client.get("/api/jobs/existing").status_code == 200
    assert path.exists() and path.stat().st_ino == before
    assert jobs.get("existing") is not None
