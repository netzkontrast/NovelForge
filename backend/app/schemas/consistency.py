from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CheckRequest(BaseModel):
    """
    Request model for consistency checking.

    Attributes:
        text: Text to verify.
        facts_structured: Structured fact subgraph (relation_summaries etc.).
    """
    text: str = Field(..., description="Text to verify")
    facts_structured: Optional[Dict[str, Any]] = Field(default=None, description="Structured fact subgraph (relation_summaries etc.)")


class Issue(BaseModel):
    """
    Model representing a consistency issue found in the text.

    Attributes:
        type: The type of the issue.
        message: Description of the issue.
        position: Optional position of the issue in the text (e.g., [start, end]).
    """
    type: str
    message: str
    position: List[int] | None = None


class FixSuggestion(BaseModel):
    """
    Model representing a suggested fix for an issue.

    Attributes:
        range: Optional range in the text to replace (e.g., [start, end]).
        replacement: The suggested replacement text.
    """
    range: List[int] | None = None
    replacement: str


class CheckResponse(BaseModel):
    """
    Response model for consistency checking.

    Attributes:
        issues: List of issues found.
        suggested_fixes: List of suggested fixes for the issues.
    """
    issues: List[Issue]
    suggested_fixes: List[FixSuggestion]
