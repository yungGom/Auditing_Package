"""pytest 루트 설정: dsd_workbench를 sys.path에 추가.

dsd_tool 패키지는 dsd_workbench/ 아래에 있지만 패키지명(import dsd_tool)과
CLI(python -m dsd_tool)는 그대로 유지한다.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "dsd_workbench"))

# 테스트 중 repack 이력이 실제 history.sqlite를 오염시키지 않도록 임시 경로로
os.environ.setdefault(
    "DSD_TOOL_HISTORY",
    os.path.join(tempfile.mkdtemp(prefix="dsd_hist_test_"), "history.sqlite"))


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """마지막 pytest 결과를 .test_results.json에 기록 (E-0 대시보드가 읽음)."""
    import datetime
    import json
    stats = terminalreporter.stats
    out = {
        "when": datetime.datetime.now().isoformat(timespec="seconds"),
        "passed": len(stats.get("passed", [])),
        "failed": len(stats.get("failed", [])),
        "skipped": len(stats.get("skipped", [])),
        "errors": len(stats.get("error", [])),
        "exitstatus": int(getattr(exitstatus, "value", exitstatus)),
    }
    start = getattr(terminalreporter, "_sessionstarttime",
                    getattr(terminalreporter, "_session_start", None))
    if start is not None:
        try:
            out["duration_s"] = round(
                __import__("time").time() - float(start), 1)
        except (TypeError, ValueError):
            pass
    try:
        with open(os.path.join(os.path.dirname(__file__),
                               ".test_results.json"), "w",
                  encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
    except OSError:
        pass
