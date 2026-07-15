"""FastAPI 앱 — 라우터 3분할 + 정적 React 빌드 서빙 (localhost 전용)."""
import os
import sys

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# dsd_tool / dashboard import 경로 (레포 배치 그대로)
for p in (os.path.join(_ROOT, "dsd_workbench"), _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from . import jobs                              # noqa: E402
from .routers import fs, jobs_api, status, workbench  # noqa: E402

app = FastAPI(title="AuditDesk", docs_url="/api/docs")
jobs.startup_recover()

app.include_router(workbench.router, prefix="/api/workbench",
                   tags=["workbench"])
app.include_router(jobs_api.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(status.router, prefix="/api/status", tags=["status"])
app.include_router(fs.router, prefix="/api/fs", tags=["fs"])

_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_STATIC):
    app.mount("/assets", StaticFiles(
        directory=os.path.join(_STATIC, "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        full = os.path.join(_STATIC, path)
        if path and os.path.isfile(full):
            return FileResponse(full)
        return FileResponse(os.path.join(_STATIC, "index.html"))
