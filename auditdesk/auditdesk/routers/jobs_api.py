"""/api/jobs — 작업 상태 조회 (지시서 §1)."""
from fastapi import APIRouter, HTTPException

from .. import jobs

router = APIRouter()


@router.get("/{job_id}")
def get_job(job_id: str):
    j = jobs.get(job_id)
    if j is None:
        raise HTTPException(404, "job 없음")
    return j


@router.get("")
def list_jobs(active: bool = False, kind: str = None):
    out = jobs.list_jobs(active=active, kind=kind)
    return {"jobs": out}
