"""Fiscal-year CRUD.

Bug-prevention rule #1: only one fiscal year may be active at a time. Whenever a
FY is created or updated with is_active=True, every other FY is deactivated in the
same transaction. The mutated resource is always returned so the client can update
its state without a reload.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/fiscal-years", tags=["fiscal-years"])


def _deactivate_others(db: Session, keep_id: int) -> None:
    db.query(models.FiscalYear).filter(models.FiscalYear.id != keep_id).update(
        {models.FiscalYear.is_active: False}
    )


@router.get("", response_model=list[schemas.FiscalYearOut])
def list_fiscal_years(db: Session = Depends(get_db)):
    return db.query(models.FiscalYear).order_by(models.FiscalYear.label.desc()).all()


@router.post("", response_model=schemas.FiscalYearOut, status_code=201)
def create_fiscal_year(payload: schemas.FiscalYearCreate, db: Session = Depends(get_db)):
    fy = models.FiscalYear(**payload.model_dump())
    db.add(fy)
    db.flush()
    if fy.is_active:
        _deactivate_others(db, fy.id)
    db.commit()
    db.refresh(fy)
    return fy


@router.get("/{fy_id}", response_model=schemas.FiscalYearOut)
def get_fiscal_year(fy_id: int, db: Session = Depends(get_db)):
    fy = db.get(models.FiscalYear, fy_id)
    if not fy:
        raise HTTPException(404, "Fiscal year not found")
    return fy


@router.put("/{fy_id}", response_model=schemas.FiscalYearOut)
def update_fiscal_year(fy_id: int, payload: schemas.FiscalYearUpdate, db: Session = Depends(get_db)):
    fy = db.get(models.FiscalYear, fy_id)
    if not fy:
        raise HTTPException(404, "Fiscal year not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(fy, k, v)
    db.flush()
    if fy.is_active:
        _deactivate_others(db, fy.id)
    db.commit()
    db.refresh(fy)
    return fy


@router.delete("/{fy_id}", status_code=204)
def delete_fiscal_year(fy_id: int, db: Session = Depends(get_db)):
    fy = db.get(models.FiscalYear, fy_id)
    if not fy:
        raise HTTPException(404, "Fiscal year not found")
    db.delete(fy)
    db.commit()
