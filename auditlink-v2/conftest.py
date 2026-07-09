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
