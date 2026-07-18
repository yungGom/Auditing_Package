"""/api/status — E-0 대시보드 승격 (기존 dashboard 모듈 로직 이식)."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/overview")
def overview():
    from dashboard.app import status
    return status()


@router.get("/gates")
def gates():
    from dashboard.app import GATES, _read_json
    return _read_json(GATES) or {"gates": []}


@router.get("/versions")
def versions():
    from dsd_tool.version import known_versions_table
    return {"versions": known_versions_table()}
