"""App settings / user profile — a single row (id=1), auto-created on first read."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_or_create(db: Session) -> models.Settings:
    settings = db.get(models.Settings, 1)
    if not settings:
        settings = models.Settings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=schemas.SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.put("", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsUpdate, db: Session = Depends(get_db)):
    settings = _get_or_create(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(settings, k, v)
    db.commit()
    db.refresh(settings)
    return settings
