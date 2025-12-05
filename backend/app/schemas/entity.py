from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union, Tuple
from pydantic import BaseModel, Field, field_validator

# Use Literal to express optional collection, and provide constant array for traversal/Schema construction
DynamicInfoType = Literal[
    "System/Simulator/Cheat Info",
    "Level/Cultivation Realm",
    "Equipment/Artifact",
    "Knowledge/Intel",
    "Asset/Territory",
    "Technique/Skill",
    "Bloodline/Physique",
    "Connection/Favor",
    "Thought/Goal Snapshot",
]
DYNAMIC_INFO_TYPES: List[str] = [
    "System/Simulator/Cheat Info",
    "Level/Cultivation Realm",
    "Equipment/Artifact",
    "Knowledge/Intel",
    "Asset/Territory",
    "Technique/Skill",
    "Bloodline/Physique",
    "Connection/Favor",
    "Thought/Goal Snapshot",
]

# Entity type identifier (unified main type)
EntityType = Literal['character', 'scene', 'organization']


class DynamicInfoItem(BaseModel):
    """
    Model for a single item of dynamic information.

    Attributes:
        id: Unique identifier for the item (-1 means unassigned/auto-assign).
        info: Brief description of the specific dynamic info.
    """
    id:int=Field(-1,description="Manually set, no generation needed; if -1 upon merging, will be automatically assigned sequential ID (starting from 1)")
    info:str=Field(description="Briefly describe specific dynamic info.")
    # weight:float=Field(description="Weight, between 0-1")
    
class DynamicInfo(BaseModel):
    """
    Model for dynamic information associated with an entity.

    Attributes:
        name: Character name.
        dynamic_info: Dictionary of dynamic info, categorized by type.
    """
    name: str = Field(description="Character name.")
    # Keys use English literal types directly, consistent between frontend and backend
    dynamic_info: Dict[DynamicInfoType, List[DynamicInfoItem]] = Field(default_factory=dict, description="Dynamic info dictionary, keys are English categories; values are lists of info items.")

    @field_validator('dynamic_info', mode='before')
    @classmethod
    def _normalize_keys(cls, v: Any) -> Dict[str, Any]:
        """
        Normalizes keys in the dynamic_info dictionary, keeping only allowed types.

        Args:
            v: The input value for dynamic_info.

        Returns:
            A normalized dictionary.
        """
        if not isinstance(v, dict):
            return {}
        normalized: Dict[str, Any] = {}
        allowed = set(DYNAMIC_INFO_TYPES)
        for k, arr in v.items():
            key = k if isinstance(k, str) else str(k)
            # Keep only allowed English keys, ignore others
            if key in allowed:
                normalized[key] = arr
        return normalized

class DeletionInfo(BaseModel):
    """
    Model for specifying dynamic info to be deleted.

    Attributes:
        name: Character name.
        dynamic_type: The type of dynamic info.
        id: ID of the dynamic info item to delete.
    """
    name: str = Field(description="Character name.")
    dynamic_type: DynamicInfoType = Field(description="Dynamic info type.")
    id: int = Field(gt=0, description="ID of dynamic info to delete (cannot be -1)")

class UpdateDynamicInfo(BaseModel):
    """
    Model for updating dynamic information.

    Attributes:
        info_list: List of dynamic info to update.
        delete_info_list: Optional list of old info to delete.
    """
    info_list:List[DynamicInfo]=Field(description="List of dynamic info to update, try to extract only important enough info")
    delete_info_list: Optional[List[DeletionInfo]] = Field(default=None, description="(Optional) List of old info to delete to make room for new info")


class Entity(BaseModel):
    """
    Base model for an Entity.

    Attributes:
        name: Entity name (Unique identifier).
        entity_type: Entity type marker.
        life_span: Entity lifespan in story (Long-term/Short-term).
        last_appearance: Last appearance time as [volume number, chapter number].
    """
    name: str = Field(..., min_length=1, description="Entity name (Unique identifier), excludes any alias, nickname, title, etc., just the name.")
    entity_type: EntityType = Field(..., description="Entity type marker.")
    life_span: Literal['Long-term','Short-term'] = Field(description="Entity lifespan in story. 'Long-term' means existing across volumes, 'Short-term' means influencing only within single volume")
    # Last appearance time (2D: volume number, chapter number)
    last_appearance: Optional[Tuple[int, int]] = Field(default=None, description="Last appearance time: [volume number, chapter number]")



class CharacterCardCore(Entity):
    """
    Core attributes for a Character Card.

    Attributes:
        role_type: Role type (Protagonist/Sidekick/NPC/Villain).
        born_scene: Appearance/Resident scene.
        description: One-sentence intro/background and relationship overview.
    """
    role_type: Literal['Protagonist','Sidekick','NPC','Villain'] = Field("Sidekick", description="Role type.")
    born_scene: str = Field(description="Appearance/Resident scene.")
    description: str = Field(description="One-sentence intro/background and relationship overview.")


class CharacterCard(CharacterCardCore):
    """
    Complete Character Card model.

    Attributes:
        entity_type: Fixed to 'character'.
        personality: Personality keywords.
        core_drive: Core drive/Goal.
        character_arc: Brief description of character arc/stage changes.
        dynamic_info: Dynamic info dictionary.
    """
    # Fixed entity type marker
    entity_type: EntityType = Field('character', description="Entity type marker.")
    personality: str = Field(description="Personality keywords, e.g., 'Cautious', 'Humorous'.")
    core_drive: str = Field(description="Core drive/Goal.")
    character_arc: str = Field(description="Brief description of character arc/stage changes throughout the book.")

    # Dynamic info (New design: centralized as source of truth)
    dynamic_info: Dict[DynamicInfoType, List[DynamicInfoItem]] = Field(default_factory=dict, description="Dynamic info dictionary, leave empty, do not generate info, system maintains automatically.")


class SceneCard(Entity):
    """
    Model for a Scene Card.

    Attributes:
        entity_type: Fixed to 'scene'.
        description: Scene/Map one-sentence intro.
        function_in_story: Function in story.
    """
    # Fixed entity type marker
    entity_type: EntityType = Field('scene', description="Entity type marker.")
    description: str = Field(description="Scene/Map one-sentence intro")
    function_in_story: str = Field(description="Function in story")

# Organization Entity
class OrganizationCard(Entity):
    """
    Model for an Organization Card.

    Attributes:
        entity_type: Fixed to 'organization'.
        description: Info description of this organization/faction camp.
        influence: Influence scope/power of this organization on the novel world.
        relationship: Relationship of this organization with others.
    """
    entity_type: EntityType = Field('organization', description="Entity type marker.")
    description: str = Field(description="Info description of this organization/faction camp")
    influence: Optional[str] = Field(default=None, description="Influence scope/power of this organization on the novel world")
    relationship:Optional[List[str]]=Field(description="Relationship of this organization with others, e.g., Hostile, Cooperative, Neutral etc.")
