"""Interview CRUD. Questions are nested; on update, passing `questions` replaces
the whole list (keeps reorder/add/remove from the UI a single round-trip)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def _set_questions(db: Session, interview: models.Interview, questions) -> None:
    interview.questions.clear()
    db.flush()
    for i, q in enumerate(questions):
        interview.questions.append(
            models.InterviewQuestion(order_index=i, **q.model_dump())
        )


@router.get("", response_model=list[schemas.InterviewOut])
def list_interviews(account_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Interview)
    if account_id is not None:
        q = q.filter(models.Interview.account_id == account_id)
    return q.order_by(models.Interview.date.desc(), models.Interview.id.desc()).all()


@router.post("", response_model=schemas.InterviewOut, status_code=201)
def create_interview(payload: schemas.InterviewCreate, db: Session = Depends(get_db)):
    if not db.get(models.Account, payload.account_id):
        raise HTTPException(404, "Account not found")
    data = payload.model_dump(exclude={"questions"})
    interview = models.Interview(**data)
    db.add(interview)
    db.flush()
    if payload.questions:
        _set_questions(db, interview, payload.questions)
    db.commit()
    db.refresh(interview)
    return interview


@router.put("/{interview_id}", response_model=schemas.InterviewOut)
def update_interview(interview_id: int, payload: schemas.InterviewUpdate, db: Session = Depends(get_db)):
    interview = db.get(models.Interview, interview_id)
    if not interview:
        raise HTTPException(404, "Interview not found")
    data = payload.model_dump(exclude_unset=True, exclude={"questions"})
    for k, v in data.items():
        setattr(interview, k, v)
    if payload.questions is not None:
        _set_questions(db, interview, payload.questions)
    db.commit()
    db.refresh(interview)
    return interview


@router.delete("/{interview_id}", status_code=204)
def delete_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.get(models.Interview, interview_id)
    if not interview:
        raise HTTPException(404, "Interview not found")
    db.delete(interview)
    db.commit()
