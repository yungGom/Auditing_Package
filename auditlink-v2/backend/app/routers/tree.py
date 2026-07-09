"""GET /api/engagement-tree.

Returns the full hierarchy for ALL fiscal years (bug-prevention rule #4); the
active FY is flagged with is_active=True so the client expands only that one by
default. Node ids are type-prefixed strings ("fy-1", "client-2", "account-9") and
each node carries ref_id (the integer PK) for follow-up API calls.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/api", tags=["tree"])


def _account_node(account: models.Account, client_name: str, phase_name: str) -> dict:
    return {
        "id": f"account-{account.id}",
        "ref_id": account.id,
        "label": account.name,
        "type": "account",
        "parent_label": f"{client_name} · {phase_name}",
        "task_count": len(account.tasks),
        "children": [],
    }


def _phase_node(phase: models.Phase, client_name: str) -> dict:
    children = [_phase_node(c, client_name) for c in phase.children]
    children += [_account_node(a, client_name, phase.name) for a in phase.accounts]
    return {
        "id": f"phase-{phase.id}",
        "ref_id": phase.id,
        "label": phase.name,
        "type": phase.kind,  # "phase" or "folder"
        "kind": phase.kind,
        "children": children,
    }


def _engagement_node(eng: models.Engagement, client_name: str) -> dict:
    top_phases = [p for p in eng.phases if p.parent_id is None]
    return {
        "id": f"eng-{eng.id}",
        "ref_id": eng.id,
        "label": eng.name,
        "type": "engagement",
        "eng_type": eng.eng_type,
        "children": [_phase_node(p, client_name) for p in top_phases],
    }


def _client_node(client: models.Client) -> dict:
    return {
        "id": f"client-{client.id}",
        "ref_id": client.id,
        "label": client.name,
        "type": "client",
        "industry": client.industry,
        "children": [_engagement_node(e, client.name) for e in client.engagements],
    }


def _fy_node(fy: models.FiscalYear) -> dict:
    return {
        "id": f"fy-{fy.id}",
        "ref_id": fy.id,
        "label": fy.label,
        "type": "fy",
        "is_active": fy.is_active,
        "children": [_client_node(c) for c in fy.clients],
    }


@router.get("/engagement-tree")
def engagement_tree(db: Session = Depends(get_db)):
    fys = db.query(models.FiscalYear).order_by(models.FiscalYear.label.desc()).all()
    return [_fy_node(fy) for fy in fys]
