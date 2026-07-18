"""Phase/folder and account CRUD — the flexible middle of the tree.

Phases and folders share one table (kind = phase|folder) and nest via parent_id.
Accounts attach to a phase/folder and own tasks/PBC/interviews. Includes bulk add
and reorder for accounts (drag-and-drop ordering in the UI).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api", tags=["structure"])


# ---- Phases / folders ----
@router.post("/phases", response_model=schemas.PhaseOut, status_code=201)
def create_phase(payload: schemas.PhaseCreate, db: Session = Depends(get_db)):
    if not db.get(models.Engagement, payload.engagement_id):
        raise HTTPException(404, "Engagement not found")
    if payload.parent_id is not None and not db.get(models.Phase, payload.parent_id):
        raise HTTPException(404, "Parent phase not found")
    phase = models.Phase(**payload.model_dump())
    db.add(phase)
    db.commit()
    db.refresh(phase)
    return phase


@router.put("/phases/{phase_id}", response_model=schemas.PhaseOut)
def update_phase(phase_id: int, payload: schemas.PhaseUpdate, db: Session = Depends(get_db)):
    phase = db.get(models.Phase, phase_id)
    if not phase:
        raise HTTPException(404, "Phase not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(phase, k, v)
    db.commit()
    db.refresh(phase)
    return phase


@router.delete("/phases/{phase_id}", status_code=204)
def delete_phase(phase_id: int, db: Session = Depends(get_db)):
    phase = db.get(models.Phase, phase_id)
    if not phase:
        raise HTTPException(404, "Phase not found")
    db.delete(phase)
    db.commit()


# ---- Accounts ----
@router.get("/accounts", response_model=list[schemas.AccountOut])
def list_accounts(phase_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Account)
    if phase_id is not None:
        q = q.filter(models.Account.phase_id == phase_id)
    return q.order_by(models.Account.order_index, models.Account.id).all()


@router.post("/accounts", response_model=schemas.AccountOut, status_code=201)
def create_account(payload: schemas.AccountCreate, db: Session = Depends(get_db)):
    if not db.get(models.Phase, payload.phase_id):
        raise HTTPException(404, "Phase not found")
    account = models.Account(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.post("/accounts/bulk", response_model=list[schemas.AccountOut], status_code=201)
def bulk_create_accounts(payload: schemas.AccountBulkCreate, db: Session = Depends(get_db)):
    if not db.get(models.Phase, payload.phase_id):
        raise HTTPException(404, "Phase not found")
    base = (
        db.query(models.Account)
        .filter(models.Account.phase_id == payload.phase_id)
        .count()
    )
    created = []
    for i, name in enumerate(n.strip() for n in payload.names if n.strip()):
        acc = models.Account(phase_id=payload.phase_id, name=name, order_index=base + i)
        db.add(acc)
        created.append(acc)
    db.commit()
    for acc in created:
        db.refresh(acc)
    return created


@router.put("/accounts/reorder", response_model=list[schemas.AccountOut])
def reorder_accounts(payload: schemas.AccountReorder, db: Session = Depends(get_db)):
    accounts = (
        db.query(models.Account)
        .filter(models.Account.phase_id == payload.phase_id)
        .all()
    )
    by_id = {a.id: a for a in accounts}
    for idx, aid in enumerate(payload.ordered_ids):
        if aid in by_id:
            by_id[aid].order_index = idx
    db.commit()
    return (
        db.query(models.Account)
        .filter(models.Account.phase_id == payload.phase_id)
        .order_by(models.Account.order_index, models.Account.id)
        .all()
    )


@router.put("/accounts/{account_id}", response_model=schemas.AccountOut)
def update_account(account_id: int, payload: schemas.AccountUpdate, db: Session = Depends(get_db)):
    account = db.get(models.Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(account, k, v)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(models.Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    db.delete(account)
    db.commit()
