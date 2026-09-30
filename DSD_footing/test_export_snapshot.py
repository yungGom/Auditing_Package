"""TC-020: runtime-only synthetic export regression tests (no golden updates)."""
import copy
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest
from pypdf import PdfReader
from reportlab.pdfgen import canvas

# These bridge tests do not open a GUI or require the optional native runtime.
try:
    import webview
except ModuleNotFoundError:
    sys.modules.setdefault("webview", types.ModuleType("webview"))

sys.path.insert(0, str(Path(__file__).parent))
from ui import api as bridge
import render
import summary


@pytest.fixture
def report(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "CONFIG", str(tmp_path / "config.json"))
    source = tmp_path / "report.pdf"
    c = canvas.Canvas(str(source), invariant=1)
    c.drawString(50, 700, "ORIGINAL SOURCE")
    c.save()
    tick = tmp_path / "report_틱마크.pdf"
    tick.write_bytes(source.read_bytes())
    marks = tmp_path / "report_marks.json"
    marks.write_text(json.dumps({
        "source": {"pdf": str(source), "sha256": bridge.sha256_of(str(source))},
        "run": {"commit": "TEST", "at": "2026-01-01", "params": {"tol": 0, "round_steps": 1}},
        "document": {"title": "Synthetic report", "counts": {"diff": 1}},
        "marks": [{"id": "m1", "page": 1, "kind": "cross", "type": "diff",
                   "status": "pending", "box": {"x0": 50, "top": 50, "x1": 100, "bottom": 70}, "seq": 1,
                   "account": "TEST ACCOUNT"}],
        "annotations": [], "page_notes": []}), encoding="utf-8")
    app = bridge.Api(str(tick), str(marks), str(tmp_path / "report_판단.json"))
    assert "error" not in app.get_marks()
    assert app.set_reviewer("OLD REVIEWER")["ok"]
    assert app.save_judgment("m1", "approved", "OLD COMMENT")["ok"]
    return app, tmp_path, source


def test_change_between_body_and_summary_uses_one_snapshot(report):
    app, folder, source = report
    captured = {}
    original = render.render_all
    append = summary.append_to

    def render_then_change(src, doc, output, **kwargs):
        captured["body"] = copy.deepcopy(doc)
        original(src, doc, output, **kwargs)
        assert app.save_judgment("m1", "removed", "NEW COMMENT")["ok"]
        assert app.set_reviewer("NEW REVIEWER")["ok"]

    def observe_summary(tick, doc, judgments, reviewer, output, **kwargs):
        captured["judgments"] = copy.deepcopy(judgments)
        captured["reviewer"] = reviewer
        return append(tick, doc, judgments, reviewer, output, **kwargs)

    with patch.object(render, "render_all", side_effect=render_then_change), \
         patch.object(summary, "append_to", side_effect=observe_summary):
        result = app.export_final()
    assert result.get("ok"), result
    assert captured["body"]["marks"][0]["status"] == "approved"
    assert captured["judgments"]["m1"]["status"] == "approved"
    assert captured["judgments"]["m1"]["comment"] == "OLD COMMENT"
    assert captured["reviewer"] == "OLD REVIEWER"
    assert result["approved"] == 1 and result["removed"] == 0
    pages = PdfReader(result["path"]).pages
    assert len(pages) == 2
    assert "ORIGINAL SOURCE" in pages[0].extract_text()
    assert "OLD COMMENT" in pages[1].extract_text()
    assert "OLD REVIEWER" in pages[1].extract_text()


def test_failed_save_cannot_change_export(report):
    app, folder, source = report
    before = copy.deepcopy(app._judgments)
    with patch.object(bridge, "_atomic_write", side_effect=OSError("disk full")):
        assert "error" in app.save_judgment("m1", "removed", "UNSAVED")
    assert app._judgments == before
    result = app.export_final()
    assert result.get("ok"), result
    assert result["approved"] == 1 and result["removed"] == 0


@pytest.mark.parametrize("status", ["pending", "approved", "removed"])
def test_status_mapping_and_inputs_unchanged(report, status):
    app, folder, source = report
    assert app.save_judgment("m1", status, "DECISION")["ok"]
    paths = [source, Path(app._pdf_path), Path(app._marks_path), Path(app._review_path)]
    before = {p: p.read_bytes() for p in paths}
    result = app.export_final()
    assert result.get("ok"), result
    assert result[status] == result["total"] == 1
    assert sum(result[k] for k in ("pending", "approved", "removed")) == 1
    assert {p: p.read_bytes() for p in paths} == before
    assert not list(folder.glob(".dsd-export-*"))


def test_nested_state_and_document_switch_do_not_leak(report):
    app, folder, source = report
    app._judgments["m1"]["metadata"] = {"nested": ["OLD"]}
    app._doc["document"]["nested"] = ["OLD"]
    original = render.render_all
    append = summary.append_to
    captured = {}
    other_tick = folder / "other_틱마크.pdf"
    other_tick.write_bytes(source.read_bytes())
    other_source = folder / "other.pdf"
    other_source.write_bytes(source.read_bytes())
    other_doc = copy.deepcopy(app._doc)
    other_doc["document"]["title"] = "OTHER REPORT"
    (folder / "other_marks.json").write_text(json.dumps(other_doc), encoding="utf-8")

    def change_document(src, doc, out, **kwargs):
        with app._state_lock:
            app._judgments["m1"]["metadata"]["nested"][0] = "NEW"
            app._doc["document"]["nested"][0] = "NEW"
        assert app._open_tick_directly(str(other_tick))["status"] == "opened"
        assert "error" not in app.get_marks()
        assert app.save_judgment("m1", "removed", "OTHER COMMENT")["ok"]
        original(src, doc, out, **kwargs)

    def observe(tick, doc, judgments, reviewer, out, **kwargs):
        captured["doc"] = copy.deepcopy(doc)
        captured["judgments"] = copy.deepcopy(judgments)
        return append(tick, doc, judgments, reviewer, out, **kwargs)

    with patch.object(render, "render_all", side_effect=change_document), \
         patch.object(summary, "append_to", side_effect=observe):
        result = app.export_final()
    assert result.get("ok"), result
    assert Path(result["path"]).name == "report_검토완료.pdf"
    assert result["approved"] == 1
    assert captured["doc"]["document"]["nested"] == ["OLD"]
    assert captured["judgments"]["m1"]["metadata"]["nested"] == ["OLD"]
    assert not (folder / "other_검토완료.pdf").exists()
    assert app._judgments["m1"]["status"] == "removed"


def test_source_replaced_after_capture_uses_original_bytes(report):
    app, folder, source = report
    original = render.render_all

    def replace_source(src, doc, out, **kwargs):
        replacement = folder / "replacement.pdf"
        c = canvas.Canvas(str(replacement), invariant=1)
        c.drawString(50, 700, "NEW SOURCE")
        c.save()
        replacement.replace(source)
        original(src, doc, out, **kwargs)

    with patch.object(render, "render_all", side_effect=replace_source):
        result = app.export_final()
    assert result.get("ok"), result
    assert "ORIGINAL SOURCE" in PdfReader(result["path"]).pages[0].extract_text()
    assert "NEW SOURCE" in PdfReader(source).pages[0].extract_text()
    # A later export must not combine old analysis with a replaced source.
    before = Path(result["path"]).read_bytes()
    assert "error" in app.export_final()
    assert Path(result["path"]).read_bytes() == before


def test_same_instance_busy_and_retry(report):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    app, folder, source = report
    entered, release = Event(), Event()
    original = render.render_all

    def pause(src, doc, out, **kwargs):
        entered.set()
        assert release.wait(10), "test did not release renderer"
        original(src, doc, out, **kwargs)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with patch.object(render, "render_all", side_effect=pause):
            first = pool.submit(app.export_final)
            try:
                assert entered.wait(10)
                second = app.export_final()
                assert "error" in second and not second.get("ok")
                assert app.save_judgment("m1", "removed", "NEXT EXPORT")["ok"]
            finally:
                release.set()
            result = first.result(timeout=10)
    assert result.get("ok"), result
    assert result["approved"] == 1
    retry = app.export_final()
    assert retry.get("ok"), retry
    assert retry["removed"] == 1
    assert not list(folder.glob(".dsd-export-*"))


def test_two_instances_have_independent_staging(report):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock
    app, folder, source = report
    other = bridge.Api(app._pdf_path, app._marks_path, app._review_path)
    assert "error" not in other.get_marks()
    barrier, lock = Barrier(2), Lock()
    paths = []
    original = render.render_all

    def overlap(src, doc, out, **kwargs):
        with lock:
            paths.append((src, out))
        barrier.wait(timeout=10)
        original(src, doc, out, **kwargs)

    # Warm up reportlab's shared font registration before simultaneous rendering.
    summary._font()
    with ThreadPoolExecutor(max_workers=2) as pool:
        with patch.object(render, "render_all", side_effect=overlap):
            futures = [pool.submit(a.export_final) for a in (app, other)]
            results = [f.result(timeout=15) for f in futures]
    assert all(r.get("ok") for r in results), results
    assert len(set(paths)) == 2
    assert len(PdfReader(results[0]["path"]).pages) == 2
    assert not list(folder.glob(".dsd-export-*"))


@pytest.mark.parametrize("failure", ["render", "summary", "validation", "corrupt", "publish"])
def test_failures_preserve_previous_pdf_clean_temps_and_retry(report, failure):
    app, folder, source = report
    completed = folder / "report_검토완료.pdf"
    completed.write_bytes(source.read_bytes())
    before = completed.read_bytes()
    sentinel = folder / ".dsd-export-unrelated"
    sentinel.mkdir()
    (sentinel / "keep").write_text("not ours")
    append = summary.append_to
    replace = bridge.os.replace

    def fail_render(src, doc, out, **kwargs):
        Path(out).write_bytes(b"partial render")
        raise OSError("render injected")

    def fail_summary(tick, doc, judgments, reviewer, out, **kwargs):
        Path(out + ".tmp").write_bytes(b"partial summary")
        raise OSError("summary injected")

    def corrupt(tick, doc, judgments, reviewer, out, **kwargs):
        tally = append(tick, doc, judgments, reviewer, out, **kwargs)
        Path(out).write_bytes(b"not a PDF")
        return tally

    def fail_publish(src, dst):
        if Path(dst) == completed:
            raise OSError("publish injected")
        return replace(src, dst)

    patches = {
        "render": patch.object(render, "render_all", side_effect=fail_render),
        "summary": patch.object(summary, "append_to", side_effect=fail_summary),
        "validation": patch.object(bridge, "_validate_export", side_effect=ValueError("validation injected")),
        "corrupt": patch.object(summary, "append_to", side_effect=corrupt),
        "publish": patch.object(bridge.os, "replace", side_effect=fail_publish),
    }
    with patches[failure]:
        result = app.export_final()
    assert "error" in result and not result.get("ok"), result
    assert completed.read_bytes() == before
    assert sorted(folder.glob(".dsd-export-*")) == [sentinel]
    assert (sentinel / "keep").read_text() == "not ours"
    retry = app.export_final()
    assert retry.get("ok"), retry
    assert len(PdfReader(completed).pages) == 2
    assert sorted(folder.glob(".dsd-export-*")) == [sentinel]


def test_returned_marks_cannot_mutate_cached_document(report):
    app, folder, source = report
    res = app.get_marks()
    res["marks"][0]["box"]["x0"] = 999
    res["marks"][0]["status"] = "removed"
    assert app._doc["marks"][0]["box"]["x0"] == 50
    assert app._doc["marks"][0]["status"] == "pending"
    assert app.export_final()["approved"] == 1


@pytest.mark.parametrize("permanent", [False, True])
def test_cleanup_failure_after_publish_reports_commit_truthfully(report, permanent):
    app, folder, source = report
    cleanup = bridge.shutil.rmtree
    attempts = []

    def denied(path, *args, **kwargs):
        attempts.append(path)
        if permanent or len(attempts) == 1:
            raise PermissionError("cleanup injected")
        return cleanup(path, *args, **kwargs)

    with patch.object(bridge.shutil, "rmtree", side_effect=denied):
        result = app.export_final()
    try:
        assert result.get("ok"), result
        assert len(PdfReader(result["path"]).pages) == 2
        assert ("warning" in result) is permanent
        assert len(attempts) == (3 if permanent else 2)
        if not permanent:
            assert not list(folder.glob(".dsd-export-*"))
    finally:
        for path in set(attempts):
            if Path(path).exists():
                cleanup(path)


def test_summary_without_content_is_not_published(report):
    from pypdf import PdfWriter
    app, folder, source = report
    completed = folder / "report_검토완료.pdf"
    completed.write_bytes(source.read_bytes())
    before = completed.read_bytes()

    def empty_summary(tick, doc, judgments, reviewer, out, **kwargs):
        writer = PdfWriter()
        for page in PdfReader(tick).pages:
            writer.add_page(page)
        writer.add_blank_page(width=595, height=842)
        with open(out, "wb") as stream:
            writer.write(stream)
        return summary.tally(doc["marks"], judgments)

    with patch.object(summary, "append_to", side_effect=empty_summary):
        result = app.export_final()
    assert "error" in result
    assert completed.read_bytes() == before
    assert not list(folder.glob(".dsd-export-*"))


@pytest.mark.parametrize("save_fails", [False, True])
def test_snapshot_waits_for_inflight_save_result(report, save_fails):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    app, folder, source = report
    writing, export_started, finish_write = Event(), Event(), Event()
    write = bridge._atomic_write

    def paused_write(path, text):
        writing.set()
        assert finish_write.wait(10)
        if save_fails:
            raise OSError("save injected")
        return write(path, text)

    def start_export():
        export_started.set()
        return app.export_final()

    with ThreadPoolExecutor(max_workers=2) as pool:
        with patch.object(bridge, "_atomic_write", side_effect=paused_write):
            save = pool.submit(app.save_judgment, "m1", "removed", "NEW COMMENT")
            try:
                assert writing.wait(10)
                export = pool.submit(start_export)
                assert export_started.wait(10)
            finally:
                finish_write.set()
            saved = save.result(timeout=10)
            result = export.result(timeout=10)
    assert ("error" in saved) is save_fails
    assert result.get("ok"), result
    assert result["approved" if save_fails else "removed"] == 1
    text = PdfReader(result["path"]).pages[-1].extract_text()
    assert ("OLD COMMENT" if save_fails else "NEW COMMENT") in text


def test_publication_occurs_only_after_complete_validation(report):
    app, folder, source = report
    completed = folder / "report_검토완료.pdf"
    completed.write_bytes(source.read_bytes())
    before = completed.read_bytes()
    replace = bridge.os.replace
    commits = []

    def observe(src, dst):
        if Path(dst) == completed:
            assert completed.read_bytes() == before
            pages = PdfReader(src, strict=True).pages
            assert len(pages) == 2
            assert "ORIGINAL SOURCE" in pages[0].extract_text()
            assert "OLD COMMENT" in pages[-1].extract_text()
            commits.append((src, dst))
        return replace(src, dst)

    with patch.object(bridge.os, "replace", side_effect=observe):
        result = app.export_final()
    assert result.get("ok"), result
    assert len(commits) == 1
    assert completed.read_bytes() != before


def test_malformed_content_stream_is_not_published(report):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject
    app, folder, source = report
    completed = folder / "report_검토완료.pdf"
    completed.write_bytes(source.read_bytes())
    before = completed.read_bytes()

    def broken_summary(tick, doc, judgments, reviewer, out, **kwargs):
        writer = PdfWriter()
        writer.add_page(PdfReader(tick).pages[0])
        page = writer.add_blank_page(width=595, height=842)
        stream = DecodedStreamObject()
        stream.set_data(b"[ (unterminated")
        page[NameObject("/Contents")] = writer._add_object(stream)
        with open(out, "wb") as handle:
            writer.write(handle)
        return summary.tally(doc["marks"], judgments)

    with patch.object(summary, "append_to", side_effect=broken_summary):
        result = app.export_final()
    assert "error" in result
    assert completed.read_bytes() == before
    assert not list(folder.glob(".dsd-export-*"))
