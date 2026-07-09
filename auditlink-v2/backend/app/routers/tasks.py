"""Task CRUD. A status change appends a TaskHistory row (server-stamped date),
so the detail panel's status-change history stays authoritative on the backend.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _today() -> str:
    return date.today().isoformat()


@router.get("", response_model=list[schemas.TaskOut])
def list_tasks(account_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Task)
    if account_id is not None:
        q = q.filter(models.Task.account_id == account_id)
    return q.order_by(models.Task.id).all()


@router.post("", response_model=schemas.TaskOut, status_code=201)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    if not db.get(models.Account, payload.account_id):
        raise HTTPException(404, "Account not found")
    task = models.Task(**payload.model_dump())
    db.add(task)
    db.flush()
    db.add(models.TaskHistory(task_id=task.id, status=task.status, at=_today()))
    db.commit()
    db.refresh(task)
    return task


@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    data = payload.model_dump(exclude_unset=True)
    new_status = data.get("status")
    status_changed = new_status is not None and new_status != task.status
    for k, v in data.items():
        setattr(task, k, v)
    if status_changed:
        db.add(models.TaskHistory(task_id=task.id, status=new_status, at=_today()))
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    db.delete(task)
    db.commit()
