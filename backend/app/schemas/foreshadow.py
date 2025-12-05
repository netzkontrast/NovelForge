from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field
from app.db.models import ForeshadowItem as ForeshadowItemModel


class SuggestRequest(BaseModel):
    """
    Request model for foreshadowing suggestions.

    Attributes:
        text: Text to analyze.
    """
    text: str = Field(..., description="Text to analyze")

class SuggestResponse(BaseModel):
    """
    Response model for foreshadowing suggestions.

    Attributes:
        goals: List of suggested goals.
        items: List of suggested items.
        persons: List of suggested persons.
    """
    goals: List[str]
    items: List[str]
    persons: List[str]


class ForeshadowRegisterItem(BaseModel):
    """
    Model for registering a foreshadowing item.

    Attributes:
        title: Title of the foreshadowing item.
        type: Type of the item (goal|item|person|other).
        note: Optional note.
        chapter_id: Optional chapter ID where it appears.
    """
    title: str
    type: str = Field('other', description='goal|item|person|other')
    note: Optional[str] = None
    chapter_id: Optional[int] = None

class ForeshadowRegisterRequest(BaseModel):
    """
    Request model for registering multiple foreshadowing items.

    Attributes:
        project_id: Project ID.
        items: List of items to register.
    """
    project_id: int
    items: List[ForeshadowRegisterItem]

class ForeshadowListResponse(BaseModel):
    """
    Response model for listing foreshadowing items.

    Attributes:
        items: List of foreshadowing items.
    """
    items: List[ForeshadowItemModel]

class ForeshadowResolveRequest(BaseModel):
    """
    Request model for resolving foreshadowing (unused/placeholder).

    Attributes:
        project_id: Project ID.
    """
    project_id: int

class ForeshadowDeleteRequest(BaseModel):
    """
    Request model for deleting foreshadowing (unused/placeholder).

    Attributes:
        project_id: Project ID.
    """
    project_id: int
