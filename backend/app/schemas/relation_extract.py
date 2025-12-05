from __future__ import annotations

from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field



# Extended relation types (English enumeration)
RelationKind = Literal[
    # Character relations
    'ally', 'team', 'fellow', 'enemy', 'family', 'mentor', 'rival', 'partner', 'superior', 'subordinate', 'guide',
    # Character <-> Organization
    'member_of', 'member', 'lead', 'found',
    # Organization <-> Scene
    'control', 'locate_in',
    # Generic and Fallback
    'influence', 'counter', 'about', 'other'
]


class RecentEventSummary(BaseModel):
    """
    Model for summarizing a recent event.

    Attributes:
        summary: One sentence summary of recent event between A and B.
        volume_number: Volume number occurred (Optional).
        chapter_number: Chapter number occurred (Optional).
    """
    summary: str = Field(description="One sentence summary of recent event between A and B (Suggest merging into one for this extraction)")
    volume_number: Optional[int] = Field(default=None, description="Volume number occurred (Leave empty, system can auto-fill)")
    chapter_number: Optional[int] = Field(default=None, description="Chapter number occurred (Leave empty, system can auto-fill)")


class RelationItem(BaseModel):
    """
    Model for a single relation item between two entities.

    Attributes:
        a: Entity A name.
        b: Entity B name.
        kind: Type of relation.
        description: Brief text description of this relation.
        a_to_b_addressing: A's addressing term for B.
        b_to_a_addressing: B's addressing term for A.
        recent_dialogues: List of recent dialogue fragments.
        recent_event_summaries: List of recent event summaries.
        stance: A's overall stance towards B (Friendly/Neutral/Hostile).
    """
    a: str = Field(description="Entity A name (one of participants)")
    b: str = Field(description="Entity B name (one of participants)")
    kind: RelationKind = Field(description="Relation type (English)")
    description: Optional[str] = Field(default=None, description="Brief text description of this relation (Optional)")
    # Mutual addressing (Optional, need not appear in recent dialogue)
    a_to_b_addressing: Optional[str] = Field(default=None, description="A's addressing term for B, e.g.: Senior Brother, Mister. Extract only if A, B are both characters.")
    b_to_a_addressing: Optional[str] = Field(default=None, description="B's addressing term for A. Extract only if A, B are both characters.")
    # Recent evidence (For tone consistency and fact backtracking) - Suggest <= 3 each
    recent_dialogues: List[str] = Field(default_factory=list, description="Recent dialogue fragments (Suggest including at least one sentence from each side, can use A: '...', B: '...' merged fragment; length >= 20 chars). Extract only if A, B are both characters.")
    recent_event_summaries: List[RecentEventSummary] = Field(default_factory=list, description="Recent events directly occurred between A and B; if same fact involves three parties or more, record only once on the most direct pair. Prioritize Character-Character pairing; record Character-Organization/Organization-Organization relation only when event subject is indeed A and B, avoid mistaking organization background as bilateral event.")
    # Stance (Optional): Friendly/Neutral/Hostile
    stance: Optional[Literal['Friendly','Neutral','Hostile']] = Field(default=None, description="A's overall stance towards B (Optional)")


class RelationExtraction(BaseModel):
    """
    Model for extracted relations.

    Attributes:
        relations: List of extracted relation items.
    """
    relations: List[RelationItem] = Field(default_factory=list)
