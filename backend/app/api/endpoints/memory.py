from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Optional, List, Dict
from sqlmodel import Session, select
from loguru import logger

from app.db.session import get_session
from app.db.models import Card
from app.services.memory_service import MemoryService
from app.services.card_service import CardService
from app.schemas.entity import UpdateDynamicInfo
from app.schemas.relation_extract import RelationExtraction
from app.schemas.memory import (
    QueryRequest,
    QueryResponse,
    IngestRelationsLLMRequest,
    IngestRelationsLLMResponse,
    ExtractRelationsRequest,
    IngestRelationsFromPreviewRequest,
    IngestRelationsFromPreviewResponse,
    ExtractOnlyRequest,
    UpdateDynamicInfoRequest,
    UpdateDynamicInfoResponse,
)


router = APIRouter()



@router.post("/query", response_model=QueryResponse, summary="Retrieve subgraph/snapshot")
def query(req: QueryRequest, session: Session = Depends(get_session)):
    svc = MemoryService(session)
    data = svc.graph.query_subgraph(project_id=req.project_id, participants=req.participants, radius=req.radius)
    return QueryResponse(**data)


@router.post("/ingest-relations-llm", response_model=IngestRelationsLLMResponse, summary="Extract entity relations using LLM and ingest (strict)")
async def ingest_relations_llm(req: IngestRelationsLLMRequest, session: Session = Depends(get_session)):
    svc = MemoryService(session)
    try:
        data = await svc.extract_relations_llm(req.text, req.participants, req.llm_config_id, req.timeout)
        # Pass typed participants to ingest method
        res = svc.ingest_relations_from_llm(
            req.project_id, 
            data, 
            volume_number=req.volume_number, 
            chapter_number=req.chapter_number,
            participants_with_type=req.participants
        )
        return IngestRelationsLLMResponse(written=res.get("written", 0))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM relation extraction or ingestion failed: {e}")


# === Extract relations only (for preview) ===
@router.post("/extract-relations-llm", response_model=RelationExtraction, summary="Extract entity relations only (no ingestion)")
async def extract_relations_only(req: ExtractRelationsRequest, session: Session = Depends(get_session)):
    svc = MemoryService(session)
    try:
        # Pass participants list (including type)
        data = await svc.extract_relations_llm(req.text, req.participants, req.llm_config_id, req.timeout)
        
        # Can also optionally perform backend filtering here if needed
        # (Logic similar to filtering in ingest_relations_from_llm)

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM relation extraction failed: {e}")

# === Extract dynamic info only (no update) ===
@router.post("/extract-dynamic-info", response_model=UpdateDynamicInfo, summary="Extract dynamic info only (no update)")
async def extract_dynamic_info_only(req: ExtractOnlyRequest, session: Session = Depends(get_session)):
    svc = MemoryService(session)
    try:
        data = await svc.extract_dynamic_info_from_text(
            text=req.text,
            participants=req.participants,
            llm_config_id=req.llm_config_id,
            timeout=req.timeout,
            project_id=req.project_id,
            extra_context=req.extra_context,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dynamic info extraction failed: {e}")

# === Ingest based on preview result ===
@router.post("/ingest-relations", response_model=IngestRelationsFromPreviewResponse, summary="Ingest based on RelationExtraction result")
def ingest_relations_from_preview(req: IngestRelationsFromPreviewRequest, session: Session = Depends(get_session)):
    svc = MemoryService(session)
    try:
        res = svc.ingest_relations_from_llm(req.project_id, req.data, volume_number=req.volume_number, chapter_number=req.chapter_number)
        return IngestRelationsFromPreviewResponse(written=res.get("written", 0))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Relation ingestion failed: {e}")


@router.post("/update-dynamic-info", response_model=UpdateDynamicInfoResponse)
def update_dynamic_info(req: UpdateDynamicInfoRequest, session: Session = Depends(get_session)):
    """
    Receive dynamic info previewed and confirmed by frontend, and execute update.
    Now calls the new, more complete service function.
    """
    svc = MemoryService(session)
    try:
        # Call new service function, handling deletion, modification, and addition
        result = svc.update_dynamic_character_info(
            project_id=req.project_id,
            data=req.data,
            queue_size=req.queue_size or 3
        )
        return UpdateDynamicInfoResponse(
            success=result.get("success", False),
            updated_card_count=result.get("updated_card_count", 0)
        )
    except Exception as e:
        logger.error(f"Failed to update dynamic info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 