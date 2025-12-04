from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.db.session import get_session
from app.db.models import Workflow, WorkflowRun, WorkflowTrigger
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowRead,
    WorkflowRunRead,
    RunRequest,
    CancelResponse,
    WorkflowTriggerCreate,
    WorkflowTriggerUpdate,
    WorkflowTriggerRead,
)
from app.services.workflow_engine import engine as wf_engine
from app.services.nodes import get_node_types


router = APIRouter()


@router.get("/workflow-node-types")
def get_workflow_node_types():
    """Get all registered workflow node types"""
    node_types = get_node_types()
    
    # Return node types, categories, and descriptions
    node_info = []
    for node_type in sorted(node_types):
        category = node_type.split('.')[0] if '.' in node_type else 'Other'
        node_name = node_type.split('.')[-1] if '.' in node_type else node_type
        
        # Simple description mapping
        descriptions = {
            'Card.Read': 'Read Card',
            'Card.ModifyContent': 'Modify Content',
            'Card.UpsertChildByTitle': 'Create/Update Child Card',
            'Card.ClearFields': 'Clear Fields',
            'Card.ReplaceFieldText': 'Replace Text',
            'List.ForEach': 'Iterate Collection',
            'List.ForEachRange': 'Iterate Range',
        }
        
        node_info.append({
            'type': node_type,
            'name': node_name,
            'category': category,
            'description': descriptions.get(node_type, node_name)
        })
    
    return {'node_types': node_info}


@router.get("/workflows", response_model=List[WorkflowRead])
def list_workflows(session: Session = Depends(get_session)):
    return session.exec(select(Workflow)).all()


@router.get("/workflow-triggers", response_model=List[WorkflowTriggerRead])
def list_triggers(session: Session = Depends(get_session)):
    """Return all workflow triggers (independent resource path, avoids conflict with /workflows/{workflow_id})."""
    items = session.exec(select(WorkflowTrigger)).all()
    return items

@router.post("/workflow-triggers", response_model=WorkflowTriggerRead)
def create_trigger(payload: WorkflowTriggerCreate, session: Session = Depends(get_session)):
    t = WorkflowTrigger(**payload.model_dump())
    session.add(t)
    session.commit()
    session.refresh(t)
    return t

@router.put("/workflow-triggers/{trigger_id}", response_model=WorkflowTriggerRead)
def update_trigger(trigger_id: int, payload: WorkflowTriggerUpdate, session: Session = Depends(get_session)):
    t = session.get(WorkflowTrigger, trigger_id)
    if not t:
        raise HTTPException(status_code=404, detail="Trigger not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t

@router.delete("/workflow-triggers/{trigger_id}")
def delete_trigger(trigger_id: int, session: Session = Depends(get_session)):
    t = session.get(WorkflowTrigger, trigger_id)
    if not t:
        raise HTTPException(status_code=404, detail="Trigger not found")
    session.delete(t)
    session.commit()
    return {"ok": True}


@router.post("/workflows", response_model=WorkflowRead)
def create_workflow(payload: WorkflowCreate, session: Session = Depends(get_session)):
    wf = Workflow(**payload.model_dump())
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


@router.get("/workflows/{workflow_id}", response_model=WorkflowRead)
def get_workflow(workflow_id: int, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/workflows/{workflow_id}", response_model=WorkflowRead)
def update_workflow(workflow_id: int, payload: WorkflowUpdate, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(wf, k, v)
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    session.delete(wf)
    session.commit()
    return {"ok": True}


@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRunRead)
def run_workflow(workflow_id: int, req: RunRequest, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    run = wf_engine.create_run(session, wf, req.scope_json, req.params_json, req.idempotency_key)
    wf_engine.run(session, run)
    session.refresh(run)
    return run


@router.get("/workflows/runs/{run_id}", response_model=WorkflowRunRead)
def get_run(run_id: int, session: Session = Depends(get_session)):
    run = session.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/workflows/{workflow_id}/validate")
def validate_workflow(workflow_id: int, session: Session = Depends(get_session)):
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    dsl = wf.definition_json or {}
    raw_nodes = list((dsl.get("nodes") or []))

    # Automatically get allowed node types from node registry
    allowed_types = set(get_node_types())

    # 1) Normalization: Complete/Uniquify id; fold next node for ForEach missing body
    canonical = wf_engine._canonicalize(raw_nodes)  # type: ignore[attr-defined]

    # Complete stable id for main line nodes and body nodes; also check for duplicate id
    used_ids = set()
    auto_fixes: List[str] = []
    def _ensure_id(prefix: str, idx: int) -> str:
        base = f"{prefix}{idx}"
        if base not in used_ids:
            used_ids.add(base)
            return base
        # Backoff on conflict
        k = 1
        while f"{base}_{k}" in used_ids:
            k += 1
        nid = f"{base}_{k}"
        used_ids.add(nid)
        return nid

    # Record existing ids first, then complete missing ids
    for n in canonical:
        nid = n.get("id")
        if isinstance(nid, str) and nid:
            if nid in used_ids:
                auto_fixes.append(f"Duplicate id={nid} detected, will be renamed automatically")
            used_ids.add(nid)
        for bn in (n.get("body") or []):
            bid = bn.get("id")
            if isinstance(bid, str) and bid:
                if bid in used_ids:
                    auto_fixes.append(f"Duplicate id={bid} (body) detected, will be renamed automatically")
                used_ids.add(bid)

    for i, n in enumerate(canonical):
        if not n.get("id"):
            n["id"] = _ensure_id("n", i)
            auto_fixes.append(f"Main node #{i} missing id, auto-completed as {n['id']}")
        body = list((n.get("body") or []))
        for k, bn in enumerate(body):
            if not bn.get("id"):
                bn_id = _ensure_id(f"{n['id']}-b", k)
                bn["id"] = bn_id
                auto_fixes.append(f"Body node {n['id']}[{k}] missing id, auto-completed as {bn_id}")
        if body:
            n["body"] = body

    # 2) Rule validation
    errors: List[str] = []
    warnings: List[str] = []
    for i, n in enumerate(canonical):
        t = n.get("type")
        if t not in allowed_types:
            errors.append(f"Node#{i} uses unsupported type: {t}")
        # ForEach series requires body (canonicalize has attempted fold repair)
        if t in ("List.ForEach", "List.ForEachRange"):
            if not n.get("body"):
                errors.append(f"Node#{i}({t}) missing body")
            # Basic parameter check
            p = n.get("params") or {}
            if t == "List.ForEach" and not p.get("listPath") and not p.get("list"):
                warnings.append(f"Node#{i}(List.ForEach) suggests providing listPath or list parameter")
            if t == "List.ForEachRange":
                start = p.get("start")
                end = p.get("end")
                if not isinstance(start, int) or not isinstance(end, int):
                    warnings.append(f"Node#{i}(List.ForEachRange) suggests providing integer start/end parameters")

    fixed_dsl = {**dsl, "nodes": canonical}
    return {
        "canonical_nodes": canonical,
        "errors": errors,
        "warnings": warnings,
        "auto_fixes": auto_fixes,
        "fixed_dsl": fixed_dsl,
    }


@router.post("/workflows/runs/{run_id}/cancel", response_model=CancelResponse)
def cancel_run(run_id: int):
    ok = wf_engine.cancel(run_id)
    return CancelResponse(ok=ok, message="cancelled" if ok else "not running")


@router.get("/workflows/runs/{run_id}/events")
async def stream_events(run_id: int):
    async def event_publisher():
        async for evt in wf_engine.subscribe_events(run_id):
            yield evt

    return StreamingResponse(event_publisher(), media_type="text/event-stream")


