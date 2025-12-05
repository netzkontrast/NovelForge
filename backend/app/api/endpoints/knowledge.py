from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app.db.session import get_session
from app.schemas.prompt import KnowledgeRead, KnowledgeCreate, KnowledgeUpdate
from app.schemas.response import ApiResponse
from app.services.knowledge_service import KnowledgeService

router = APIRouter()

@router.get('/', response_model=ApiResponse[List[KnowledgeRead]], summary='Get knowledge base list')
def list_knowledge(session: Session = Depends(get_session)):
    """Get list of knowledge bases."""
    svc = KnowledgeService(session)
    items = svc.list()
    return ApiResponse(data=items)

@router.post('/', response_model=ApiResponse[KnowledgeRead], summary='Create knowledge base')
def create_knowledge(body: KnowledgeCreate, session: Session = Depends(get_session)):
    """Create a new knowledge base."""
    svc = KnowledgeService(session)
    if svc.get_by_name(body.name):
        raise HTTPException(status_code=400, detail='Knowledge base with same name already exists')
    item = svc.create(name=body.name, description=body.description, content=body.content)
    return ApiResponse(data=item)

@router.get('/{kid}', response_model=ApiResponse[KnowledgeRead], summary='Get single knowledge base')
def get_knowledge(kid: int, session: Session = Depends(get_session)):
    """Get a knowledge base by ID."""
    svc = KnowledgeService(session)
    item = svc.get_by_id(kid)
    if not item:
        raise HTTPException(status_code=404, detail='Knowledge base not found')
    return ApiResponse(data=item)

@router.put('/{kid}', response_model=ApiResponse[KnowledgeRead], summary='Update knowledge base')
def update_knowledge(kid: int, body: KnowledgeUpdate, session: Session = Depends(get_session)):
    """Update a knowledge base."""
    svc = KnowledgeService(session)
    item = svc.update(kid, name=body.name, description=body.description, content=body.content)
    if not item:
        raise HTTPException(status_code=404, detail='Knowledge base not found')
    return ApiResponse(data=item)

@router.delete('/{kid}', response_model=ApiResponse, summary='Delete knowledge base')
def delete_knowledge(kid: int, session: Session = Depends(get_session)):
    """Delete a knowledge base."""
    svc = KnowledgeService(session)
    item = svc.get_by_id(kid)
    if not item:
        raise HTTPException(status_code=404, detail='Knowledge base not found')
    if getattr(item, 'built_in', False):
        raise HTTPException(status_code=400, detail='System built-in knowledge base cannot be deleted')
    ok = svc.delete(kid)
    if not ok:
        raise HTTPException(status_code=404, detail='Knowledge base not found')
    return ApiResponse(message='Delete successful')
