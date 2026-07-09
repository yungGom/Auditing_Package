"""PBC (요청자료) CRUD plus bulk import (excel-paste mapping happens client-side)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/pbc", tags=["pbc"])


@router.get("", response_model=list[schemas.PBCOut])
def list_pbc(account_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.PBCItem)
    if account_id is not None:
        q = q.filter(models.PBCItem.account_id == account_id)
    return q.order_by(models.PBCItem.id).all()


@router.post("", response_model=schemas.PBCOut, status_code=201)
def create_pbc(payload: schemas.PBCCreate, db: Session = Depends(get_db)):
    if not db.get(models.Account, payload.account_id):
        raise HTTPException(404, "Account not found")
    item = models.PBCItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/bulk", response_model=list[schemas.PBCOut], status_code=201)
def bulk_create_pbc(payload: schemas.PBCBulkCreate, db: Session = Depends(get_db)):
    created = []
    for it in payload.items:
        if not db.get(models.Account, it.account_id):
            raise HTTPException(404, f"Account {it.account_id} not found")
        obj = models.PBCItem(**it.model_dump())
        db.add(obj)
        created.append(obj)
    db.commit()
    for obj in created:
        db.refresh(obj)
    return created


@router.put("/{pbc_id}", response_model=schemas.PBCOut)
def update_pbc(pbc_id: int, payload: schemas.PBCUpdate, db: Session = Depends(get_db)):
    item = db.get(models.PBCItem, pbc_id)
    if not item:
        raise HTTPException(404, "PBC item not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{pbc_id}", status_code=204)
def delete_pbc(pbc_id: int, db: Session = Depends(get_db)):
    item = db.get(models.PBCItem, pbc_id)
    if not item:
        raise HTTPException(404, "PBC item not found")
    db.delete(item)
    db.commit()
