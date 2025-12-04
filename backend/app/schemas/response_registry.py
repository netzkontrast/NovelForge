from __future__ import annotations

from typing import Dict, Any

# Unified centralized export of all response/nested models that need to be exposed in OpenAPI
from app.schemas.wizard import (
	WorldBuilding, Blueprint,
	VolumeOutline, ChapterOutline,
	SpecialAbilityResponse, OneSentence, ParagraphOverview,
	CharacterCard, SceneCard, StoryLine, StageLine, 
	Tags, WorldviewTemplate, Chapter,
 WritingGuide
)
from app.schemas.entity import OrganizationCard


RESPONSE_MODEL_MAP: Dict[str, Any] = {
	'Tags': Tags,
	'SpecialAbilityResponse': SpecialAbilityResponse,
	'OneSentence': OneSentence,
	'ParagraphOverview': ParagraphOverview,
	'WorldBuilding': WorldBuilding,
	'WorldviewTemplate': WorldviewTemplate,
	'Blueprint': Blueprint,
	# Use unwrapped model
	'VolumeOutline': VolumeOutline,
 	'WritingGuide': WritingGuide,
	'ChapterOutline': ChapterOutline,
	'Chapter': Chapter,
	# Base schema, automatically included in OpenAPI
	'CharacterCard': CharacterCard,
	'SceneCard': SceneCard,
	'OrganizationCard': OrganizationCard,
	# Explicitly export nested types for frontend field tree parsing
	'StageLine': StageLine,
	'StoryLine': StoryLine,
} 