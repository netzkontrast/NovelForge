from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.relation_extract import RelationItem


class AssembleContextRequest(BaseModel):
	project_id: Optional[int] = Field(default=None, description="Project ID")
	volume_number: Optional[int] = Field(default=None, description="Volume Number")
	chapter_number: Optional[int] = Field(default=None, description="Chapter Number")
	chapter_id: Optional[int] = Field(default=None, description="Chapter Card ID (Optional)")
	participants: Optional[List[str]] = Field(default=None, description="List of participant entity names")
	current_draft_tail: Optional[str] = Field(default=None, description="Context template (draft tail)")
	recent_chapters_window: Optional[int] = Field(default=None, description="Recent window N (Reserved for future extension)")


class FactsStructured(BaseModel):
	# Only keep fields currently used
	fact_summaries: List[str] = Field(default_factory=list, description="Key fact summaries")
	relation_summaries: List[RelationItem] = Field(default_factory=list, description="Relation summaries (including recent dialogues/events)")


class AssembleContextResponse(BaseModel):
	# Only keep fact subgraph and budget info
	facts_subgraph: str = Field(default="", description="Fact subgraph text echo (Optional, echo only)")
	budget_stats: Dict[str, Any] = Field(default_factory=dict, description="Context word count budget stats (may include nested parts dict)")
	facts_structured: Optional[FactsStructured] = Field(default=None, description="Structured fact subgraph")


class ContextSettingsModel(BaseModel):
	recent_chapters_window: int
	total_context_budget_chars: int
	soft_budget_chars: int
	quota_recent: int
	quota_older_summary: int
	quota_facts: int


class UpdateContextSettingsRequest(BaseModel):
	recent_chapters_window: Optional[int] = None
	total_context_budget_chars: Optional[int] = None
	soft_budget_chars: Optional[int] = None
	quota_recent: Optional[int] = None
	quota_older_summary: Optional[int] = None
	quota_facts: Optional[int] = None 