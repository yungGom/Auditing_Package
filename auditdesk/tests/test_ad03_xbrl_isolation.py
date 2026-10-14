"""AD-03: synthetic Workbench session and XBRL ownership checks."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "auditdesk"),
                str(ROOT / "auditdesk" / "dsd_workbench"),
                str(ROOT / "auditdesk" / "dart_explorer")]

from auditdesk import jobs
from auditdesk.routers import studio, workbench


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "_DB", str(tmp_path / "app.sqlite"))
    monkeypatch.setattr(studio, "_WORKDIR", str(tmp_path / "outputs"))
    monkeypatch.setattr(workbench, "_WORKDIR", str(tmp_path / "extracts"))
    queued = []

    def submit(kind, fn):
        queued.append((kind, fn))
        return f"job-{len(queued)}"

    monkeypatch.setattr(jobs, "submit", submit)
    return tmp_path, queued


def seed_session(tmp_path, sid, directory, revision="revision-1"):
    source = tmp_path / directory / "same.dsd"
    source.parent.mkdir()
    source.write_text("synthetic", encoding="utf-8")
    workbook = tmp_path / directory / "same.xlsx"
    workbook.write_text("synthetic", encoding="utf-8")
    with jobs.connect() as con:
        con.execute(
            "INSERT INTO sessions(id, dsd_path, created, meta, state, "
            "xlsx_path, xbrl_revision) VALUES(?,?,?,?,?,?,?)",
            (sid, str(source), "now", "{}", "추출됨", str(workbook), revision))
    return source, workbook


def fake_engine(monkeypatch):
    # The router remains the subject; accounting and XBRL parsing are doubles.
    import dart_explorer.xbrl.corpus as corpus
    import dart_explorer.xbrl.dimension_table as dimension_table
    import dsd_tool.succession as succession
    import dsd_tool.xbrl_recon as recon

    class Instance:
        facts = {}
        doc_period_end = "2026-06-30"

        def __init__(self, package):
            self.package = package

    monkeypatch.setattr(dimension_table, "XbrlInstance", Instance)
    monkeypatch.setattr(corpus, "_element_roles", lambda _: {})
    monkeypatch.setattr(succession, "load_assets", lambda _: {})
    monkeypatch.setattr(studio, "_decided_map", lambda: {})

    def run(xlsx, *args, out_path, **kwargs):
        Path(out_path).write_text("synthetic output", encoding="utf-8")
        return {"counts": {"일치": 1}, "rows": {}, "out_path": out_path,
                "matched": 1, "total": 1, "false": 0}

    monkeypatch.setattr(recon, "xbrl_recon", run)


def start(isolated, monkeypatch, sid, package):
    tmp_path, queued = isolated
    package.mkdir()
    (package / "succession_assets.json").write_text("{}", encoding="utf-8")
    fake_engine(monkeypatch)
    studio.xbrl_recon_route({"session_id": sid, "package_dir": str(package)})
    return queued[-1][1]


def test_migration_and_legacy_result_fail_closed(isolated):
    tmp_path, _ = isolated
    seed_session(tmp_path, "A", "a")
    with jobs.connect() as con:
        con.execute("UPDATE sessions SET xbrl_result=? WHERE id='A'",
                    (json.dumps({"counts": {"일치": 99}}),))
    assert workbench.get_session("A")["xbrl_result"] is None
    assert workbench.get_session("A")["recon"] is None
    with jobs.connect() as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info(sessions)")}
    assert {"xbrl_revision", "xbrl_request", "xbrl_result"} <= cols


def test_malformed_persisted_result_fails_closed(isolated):
    tmp_path, _ = isolated
    seed_session(tmp_path, "A", "a")
    with jobs.connect() as con:
        con.execute("UPDATE sessions SET xbrl_result=?, xbrl_request=? "
                    "WHERE id='A'", ("{invalid-json", "current"))
    assert workbench.get_session("A")["xbrl_result"] is None


def test_sessions_and_identical_basenames_restore_separately(isolated, monkeypatch):
    tmp_path, _ = isolated
    seed_session(tmp_path, "A", "a")
    seed_session(tmp_path, "B", "b")
    a = start(isolated, monkeypatch, "A", tmp_path / "package-a")
    assert workbench.get_session("B")["xbrl_result"] is None
    a(lambda *_: None)
    assert workbench.get_session("B")["xbrl_result"] is None
    b = start(isolated, monkeypatch, "B", tmp_path / "package-b")
    b(lambda *_: None)
    ar = workbench.get_session("A")["xbrl_result"]
    br = workbench.get_session("B")["xbrl_result"]
    assert ar["session_id"] == "A" and br["session_id"] == "B"
    assert ar["dsd_path"] != br["dsd_path"]
    assert ar["out_path"] != br["out_path"]
    assert workbench.get_session("A")["xbrl_result"] == ar
    assert workbench.get_session("A")["recon"] is None


def test_reextract_invalidates_and_old_completion_cannot_persist(isolated, monkeypatch):
    tmp_path, queued = isolated
    seed_session(tmp_path, "A", "a")
    old = start(isolated, monkeypatch, "A", tmp_path / "package-a")
    extract = workbench.extract_session("A")
    assert extract["job_id"] == "job-2"
    assert workbench.get_session("A")["xbrl_result"] is None
    assert workbench.get_session("A")["xlsx_path"] is None
    assert old(lambda *_: None)["stale"] is True
    assert workbench.get_session("A")["xbrl_result"] is None
    assert queued[-1][0] == "extract"


def test_reextract_completes_with_new_workbook_and_no_xbrl(isolated, monkeypatch):
    tmp_path, queued = isolated
    seed_session(tmp_path, "A", "a")
    old = start(isolated, monkeypatch, "A", tmp_path / "package-a")
    import dsd_tool.excel_out as excel_out

    def extract(_, output):
        Path(output).write_text("new synthetic workbook", encoding="utf-8")
        return {"out_path": output, "mapped_cells": 0, "note_count": 0,
                "cr_only_cells": 0, "fs_sheets": [], "viewonly": False,
                "deduped_notes": 0}

    monkeypatch.setattr(excel_out, "extract", extract)
    workbench.extract_session("A")
    queued[-1][1](lambda *_: None)
    current = workbench.get_session("A")
    assert current["xlsx_path"] != old(lambda *_: None)["xlsx_path"]
    assert current["xbrl_result"] is None
    assert current["recon"] is None
    new = start(isolated, monkeypatch, "A", tmp_path / "package-b")
    new(lambda *_: None)
    assert workbench.get_session("A")["xbrl_result"]["xlsx_path"] == (
        current["xlsx_path"])


def test_reverse_extract_completion_keeps_new_revision(isolated, monkeypatch):
    tmp_path, queued = isolated
    seed_session(tmp_path, "A", "a")
    import dsd_tool.excel_out as excel_out

    def extract(_, output):
        Path(output).write_text("synthetic workbook", encoding="utf-8")
        return {"out_path": output, "mapped_cells": 0, "note_count": 0,
                "cr_only_cells": 0, "fs_sheets": [], "viewonly": False,
                "deduped_notes": 0}

    monkeypatch.setattr(excel_out, "extract", extract)
    workbench.extract_session("A")
    old = queued[-1][1]
    workbench.extract_session("A")
    new = queued[-1][1]
    new(lambda *_: None)
    current = workbench.get_session("A")
    old(lambda *_: None)
    assert workbench.get_session("A")["xlsx_path"] == current["xlsx_path"]
    assert workbench.get_session("A")["xbrl_revision"] == current["xbrl_revision"]


def test_mismatched_persisted_identity_is_rejected(isolated):
    tmp_path, _ = isolated
    _, workbook = seed_session(tmp_path, "A", "a")
    source = str(tmp_path / "a" / "same.dsd")
    base = {"session_id": "A", "revision": "revision-1",
            "xlsx_path": str(workbook), "dsd_path": source,
            "request_id": "current"}
    with jobs.connect() as con:
        con.execute("UPDATE sessions SET xbrl_request='current' WHERE id='A'")
    for change in ({"session_id": "B"}, {"revision": "other"},
                   {"request_id": "old"}, {"xlsx_path": "other"},
                   {"dsd_path": "other"}):
        with jobs.connect() as con:
            con.execute("UPDATE sessions SET xbrl_result=? WHERE id='A'",
                        (json.dumps({**base, **change}),))
        assert workbench.get_session("A")["xbrl_result"] is None


def test_reverse_completion_keeps_latest_request(isolated, monkeypatch):
    tmp_path, _ = isolated
    seed_session(tmp_path, "A", "a")
    first = start(isolated, monkeypatch, "A", tmp_path / "package-a")
    second = start(isolated, monkeypatch, "A", tmp_path / "package-b")
    second_result = second(lambda *_: None)
    assert first(lambda *_: None)["stale"] is True
    assert workbench.get_session("A")["xbrl_result"]["request_id"] == (
        second_result["request_id"])


def test_frontend_component_bridge():
    # Missing Node or TypeScript is a failure, never a skip.
    subprocess.run(["node", str(ROOT / "auditdesk" / "webui" / "tests"
                               / "ad03_xbrl_isolation.cjs")],
                   cwd=ROOT / "auditdesk" / "webui", check=True)
