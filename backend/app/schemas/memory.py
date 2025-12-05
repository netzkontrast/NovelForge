from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.relation_extract import RelationExtraction
from app.schemas.entity import UpdateDynamicInfo

class ParticipantTyped(BaseModel):
    """
    Model representing a participant with name and type.

    Attributes:
        name: Name of the participant.
        type: Type of the participant.
    """
    name: str
    type: str


class QueryRequest(BaseModel):
    """
    Request model for querying the knowledge graph.

    Attributes:
        project_id: Project ID.
        participants: Optional list of participant names.
        radius: Radius for graph traversal.
    """
    project_id: int
    participants: Optional[List[str]] = None
    radius: int = 2

class QueryResponse(BaseModel):
    """
    Response model for knowledge graph query.

    Attributes:
        nodes: List of nodes in the subgraph.
        edges: List of edges in the subgraph.
        fact_summaries: List of fact summaries.
        relation_summaries: List of relation summaries.
    """
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    # Only keep fields actually used
    fact_summaries: List[str]
    relation_summaries: List[Dict[str, Any]]


class IngestRelationsLLMRequest(BaseModel):
    """
    Request model for ingesting relations using LLM.

    Attributes:
        project_id: Project ID.
        text: Text to analyze.
        participants: Optional list of participants.
        llm_config_id: LLM Config ID.
        timeout: Optional timeout.
        volume_number: Optional volume number.
        chapter_number: Optional chapter number.
    """
    project_id: int
    text: str
    participants: Optional[List[ParticipantTyped]] = None
    llm_config_id: int = 1
    timeout: Optional[float] = None
    volume_number: Optional[int] = None
    chapter_number: Optional[int] = None

class IngestRelationsLLMResponse(BaseModel):
    """
    Response model for LLM relation ingestion.

    Attributes:
        written: Number of relations written/updated.
    """
    written: int


class ExtractRelationsRequest(BaseModel):
    """
    Request model for extracting relations without ingestion.

    Attributes:
        text: Text to analyze.
        participants: Optional list of participants.
        llm_config_id: LLM Config ID.
        timeout: Optional timeout.
        volume_number: Optional volume number.
        chapter_number: Optional chapter number.
    """
    text: str
    participants: Optional[List[ParticipantTyped]] = None
    llm_config_id: int = 1
    timeout: Optional[float] = None
    volume_number: Optional[int] = None
    chapter_number: Optional[int] = None


class IngestRelationsFromPreviewRequest(BaseModel):
    """
    Request model for ingesting relations from a preview.

    Attributes:
        project_id: Project ID.
        data: Extracted relation data.
        volume_number: Optional volume number.
        chapter_number: Optional chapter number.
    """
    project_id: int
    data: RelationExtraction
    volume_number: Optional[int] = None
    chapter_number: Optional[int] = None

class IngestRelationsFromPreviewResponse(BaseModel):
    """
    Response model for ingesting relations from preview.

    Attributes:
        written: Number of relations written/updated.
    """
    written: int


class ExtractDynamicInfoRequest(BaseModel):
    """
    Request model for extracting dynamic information.

    Attributes:
        project_id: Project ID.
        text: Text to analyze.
        participants: Optional list of participants.
        llm_config_id: LLM Config ID.
        timeout: Optional timeout.
        extra_context: Optional extra context.
    """
    project_id: int
    text: str
    participants: Optional[List[ParticipantTyped]] = None
    llm_config_id: int = 1
    timeout: Optional[float] = None
    extra_context: Optional[str] = None

class ExtractOnlyRequest(BaseModel):
    """
    Request model for extraction only (generic).

    Attributes:
        project_id: Optional Project ID.
        text: Text to analyze.
        participants: Optional list of participants.
        llm_config_id: LLM Config ID.
        timeout: Optional timeout.
        extra_context: Optional extra context.
    """
    project_id: Optional[int] = None
    text: str
    participants: Optional[List[ParticipantTyped]] = None
    llm_config_id: int = 1
    timeout: Optional[float] = None
    extra_context: Optional[str] = None


class UpdateDynamicInfoRequest(BaseModel):
    """
    Request model for updating dynamic information.

    Attributes:
        project_id: Project ID.
        data: Dynamic info data to update.
        queue_size: Optional queue size limit.
    """
    project_id: int
    data: UpdateDynamicInfo
    queue_size: Optional[int] = 5

class UpdateDynamicInfoResponse(BaseModel):
    """
    Response model for updating dynamic information.

    Attributes:
        success: Whether the update was successful.
        updated_card_count: Number of cards updated.
    """
    success: bool
    updated_card_count: int
