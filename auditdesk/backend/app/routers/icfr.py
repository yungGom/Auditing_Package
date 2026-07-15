"""ICFR control CRUD. RCM detail is stored flat on the row but exposed nested
(`rcm: {...}`) to match the RCM detail panel in the design."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/icfr", tags=["icfr"])

RCM_FIELDS = [
    "risk", "objective", "org", "nature", "frequency", "residual_risk",
    "mrc", "ipe", "accounts", "assertions", "test_types",
    "eval_result", "sample_size", "exception_note",
]


def _serialize(ctrl: models.IcfrControl) -> dict:
    return {
        "id": ctrl.id,
        "client_id": ctrl.client_id,
        "code": ctrl.code,
        "process": ctrl.process,
        "description": ctrl.description,
        "ctrl_type": ctrl.ctrl_type,
        "owner": ctrl.owner,
        "due": ctrl.due,
        "status": ctrl.status,
        "rcm": {f: getattr(ctrl, f) for f in RCM_FIELDS},
    }


@router.get("", response_model=list[schemas.IcfrOut])
def list_icfr(client_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.IcfrControl)
    if client_id is not None:
        q = q.filter(models.IcfrControl.client_id == client_id)
    return [_serialize(c) for c in q.order_by(models.IcfrControl.id).all()]


@router.post("", response_model=schemas.IcfrOut, status_code=201)
def create_icfr(payload: schemas.IcfrCreate, db: Session = Depends(get_db)):
    if not db.get(models.Client, payload.client_id):
        raise HTTPException(404, "Client not found")
    data = payload.model_dump(exclude={"rcm"})
    data.update(payload.rcm.model_dump())
    ctrl = models.IcfrControl(**data)
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return _serialize(ctrl)


@router.put("/{ctrl_id}", response_model=schemas.IcfrOut)
def update_icfr(ctrl_id: int, payload: schemas.IcfrUpdate, db: Session = Depends(get_db)):
    ctrl = db.get(models.IcfrControl, ctrl_id)
    if not ctrl:
        raise HTTPException(404, "ICFR control not found")
    data = payload.model_dump(exclude_unset=True, exclude={"rcm"})
    for k, v in data.items():
        setattr(ctrl, k, v)
    if payload.rcm is not None:
        for k, v in payload.rcm.model_dump().items():
            setattr(ctrl, k, v)
    db.commit()
    db.refresh(ctrl)
    return _serialize(ctrl)


@router.delete("/{ctrl_id}", status_code=204)
def delete_icfr(ctrl_id: int, db: Session = Depends(get_db)):
    ctrl = db.get(models.IcfrControl, ctrl_id)
    if not ctrl:
        raise HTTPException(404, "ICFR control not found")
    db.delete(ctrl)
    db.commit()
