from typing import List, Dict
from sqlmodel import Session, select
from time import monotonic

from app.db.models import WorkflowTrigger, Card, Workflow, WorkflowRun
from app.services.workflow_engine import engine as wf_engine


def _match_triggers_for_card(session: Session, event: str, card: Card) -> List[WorkflowTrigger]:
    q = select(WorkflowTrigger).where(
        WorkflowTrigger.trigger_on == event,
        WorkflowTrigger.is_active == True,  # noqa: E712
    )
    triggers = session.exec(q).all()
    matched: List[WorkflowTrigger] = []
    for t in triggers:
        # Filter card_type
        if t.card_type_name and card.card_type and card.card_type.name != t.card_type_name:
            continue
        # filter_json reserved: Complex matching not implemented yet
        matched.append(t)
    return matched


_recent_keys: Dict[str, float] = {}
_DEBOUNCE_MS = 1500  # Same key won't trigger again within this window


def _make_idempotency_key(event: str, workflow_id: int, card: Card | None, project_id: int | None) -> str:
    card_id = getattr(card, "id", None) or 0
    proj_id = project_id or getattr(card, "project_id", None) or 0
    return f"evt:{event}|wf:{workflow_id}|card:{card_id}|proj:{proj_id}"


def _should_suppress(session: Session, key: str, workflow_id: int) -> bool:
    # 1) In-process debounce
    now = monotonic()
    last = _recent_keys.get(key)
    if last is not None and (now - last) * 1000 < _DEBOUNCE_MS:
        return True
    # Clean up expired items to avoid leaks
    try:
        for k, v in list(_recent_keys.items()):
            if (now - v) * 1000 > 60000:
                _recent_keys.pop(k, None)
    except Exception:
        pass
    # 2) Persistence layer "No secondary trigger in same run cycle": Check for running task with same idempotency key
    existing = session.exec(
        select(WorkflowRun).where(
            WorkflowRun.workflow_id == workflow_id,
            WorkflowRun.idempotency_key == key,
            WorkflowRun.status.in_(["queued", "running"]),  # type: ignore[arg-type]
        )
    ).first()
    if existing:
        return True
    # Mark current
    _recent_keys[key] = now
    return False


def trigger_on_card_save(session: Session, card: Card) -> List[int]:
    """Trigger OnSave workflows after card save/update, return run_id list."""
    run_ids: List[int] = []
    triggers = _match_triggers_for_card(session, "onsave", card)
    for t in triggers:
        wf = session.get(Workflow, t.workflow_id)
        if not wf or not wf.is_active:
            continue
        idem_key = _make_idempotency_key("onsave", int(t.workflow_id), card, card.project_id)
        if _should_suppress(session, idem_key, int(t.workflow_id)):
            continue
        run = wf_engine.create_run(
            session=session,
            workflow=wf,
            scope_json={"card_id": card.id, "project_id": card.project_id},
            params_json={},
            idempotency_key=idem_key,
        )
        wf_engine.run(session, run)
        if run.id:
            run_ids.append(int(run.id))
    return run_ids


def trigger_on_generate_finish(session: Session, card: Card | None, project_id: int | None) -> List[int]:
    """Trigger OnGenerateFinish workflows after generation/continuation, return run_id list."""
    run_ids: List[int] = []
    q = select(WorkflowTrigger).where(
        WorkflowTrigger.trigger_on == "ongenfinish",
        WorkflowTrigger.is_active == True,  # noqa: E712
    )
    triggers = session.exec(q).all()
    for t in triggers:
        if card and t.card_type_name and card.card_type and card.card_type.name != t.card_type_name:
            continue
        wf = session.get(Workflow, t.workflow_id)
        if not wf or not wf.is_active:
            continue
        scope = {"project_id": project_id}
        if card and card.id:
            scope["card_id"] = card.id
        idem_key = _make_idempotency_key("ongenfinish", int(t.workflow_id), card, project_id)
        if _should_suppress(session, idem_key, int(t.workflow_id)):
            continue
        run = wf_engine.create_run(session, wf, scope_json=scope, params_json={}, idempotency_key=idem_key)
        wf_engine.run(session, run)
        if run.id:
            run_ids.append(int(run.id))
    return run_ids



def trigger_on_project_create(session: Session, project_id: int) -> List[int]:
    """Trigger onprojectcreate workflows after project creation, return run_id list.
    Scope contains only project_id, no card_id.
    """
    run_ids: List[int] = []
    triggers = session.exec(
        select(WorkflowTrigger).where(
            WorkflowTrigger.trigger_on == "onprojectcreate",
            WorkflowTrigger.is_active == True,
        )
    ).all()
    for t in triggers:
        wf = session.get(Workflow, t.workflow_id)
        if not wf or not wf.is_active:
            continue
        idem_key = _make_idempotency_key("onprojectcreate", int(t.workflow_id), None, project_id)
        if _should_suppress(session, idem_key, int(t.workflow_id)):
            continue
        run = wf_engine.create_run(
            session=session,
            workflow=wf,
            scope_json={"project_id": project_id},
            params_json={},
            idempotency_key=idem_key,
        )
        wf_engine.run(session, run)
        if run.id:
            run_ids.append(int(run.id))
    return run_ids
