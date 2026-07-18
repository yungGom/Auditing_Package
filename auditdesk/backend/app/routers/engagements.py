"""Engagement CRUD with type-based phase templates.

Creating an engagement seeds default phases based on its type (bug-prevention:
the structure starts consistent for each work type):
  - audit  -> 기중감사, 기말감사
  - review -> 검토절차
  - etc    -> empty (user adds folders freely)
Pass apply_template=false to skip seeding.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/engagements", tags=["engagements"])

TYPE_TEMPLATES = {
    "audit": ["기중감사", "기말감사"],
    "review": ["검토절차"],
    "etc": [],
}


@router.get("", response_model=list[schemas.EngagementOut])
def list_engagements(client_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Engagement)
    if client_id is not None:
        q = q.filter(models.Engagement.client_id == client_id)
    return q.order_by(models.Engagement.id).all()


@router.post("", response_model=schemas.EngagementOut, status_code=201)
def create_engagement(payload: schemas.EngagementCreate, db: Session = Depends(get_db)):
    if not db.get(models.Client, payload.client_id):
        raise HTTPException(404, "Client not found")
    eng = models.Engagement(
        client_id=payload.client_id, name=payload.name, eng_type=payload.eng_type
    )
    db.add(eng)
    db.flush()
    if payload.apply_template:
        for i, phase_name in enumerate(TYPE_TEMPLATES.get(payload.eng_type, [])):
            db.add(models.Phase(engagement_id=eng.id, name=phase_name, kind="phase", order_index=i))
    db.commit()
    db.refresh(eng)
    return eng


@router.put("/{eng_id}", response_model=schemas.EngagementOut)
def update_engagement(eng_id: int, payload: schemas.EngagementUpdate, db: Session = Depends(get_db)):
    eng = db.get(models.Engagement, eng_id)
    if not eng:
        raise HTTPException(404, "Engagement not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(eng, k, v)
    db.commit()
    db.refresh(eng)
    return eng


@router.delete("/{eng_id}", status_code=204)
def delete_engagement(eng_id: int, db: Session = Depends(get_db)):
    eng = db.get(models.Engagement, eng_id)
    if not eng:
        raise HTTPException(404, "Engagement not found")
    db.delete(eng)
    db.commit()
