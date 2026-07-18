"""Template CRUD. Accounts are nested; update replaces the account list."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _set_accounts(template: models.Template, accounts) -> None:
    template.accounts.clear()
    for a in accounts:
        template.accounts.append(models.TemplateAccount(**a.model_dump()))


@router.get("", response_model=list[schemas.TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.query(models.Template).order_by(models.Template.id).all()


@router.post("", response_model=schemas.TemplateOut, status_code=201)
def create_template(payload: schemas.TemplateCreate, db: Session = Depends(get_db)):
    template = models.Template(name=payload.name, industry=payload.industry)
    _set_accounts(template, payload.accounts)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{template_id}", response_model=schemas.TemplateOut)
def update_template(template_id: int, payload: schemas.TemplateUpdate, db: Session = Depends(get_db)):
    template = db.get(models.Template, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    data = payload.model_dump(exclude_unset=True, exclude={"accounts"})
    for k, v in data.items():
        setattr(template, k, v)
    if payload.accounts is not None:
        _set_accounts(template, payload.accounts)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.get(models.Template, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    db.delete(template)
    db.commit()
