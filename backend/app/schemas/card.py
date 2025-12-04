from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# --- CardType Schemas ---

class CardTypeBase(BaseModel):
    name: str
    model_name: Optional[str] = None
    description: Optional[str] = None
    # Type built-in structure (JSON Schema)
    json_schema: Optional[Dict[str, Any]] = None
    # Type default AI parameters
    ai_params: Optional[Dict[str, Any]] = None
    editor_component: Optional[str] = None
    is_ai_enabled: bool = Field(default=False)
    is_singleton: bool = Field(default=False)
    # Default AI context injection template (Type level)
    default_ai_context_template: Optional[str] = None
    # UI Layout (Optional)
    ui_layout: Optional[Dict[str, Any]] = None


class CardTypeCreate(CardTypeBase):
    pass


class CardTypeUpdate(BaseModel):
    name: Optional[str] = None
    model_name: Optional[str] = None
    description: Optional[str] = None
    json_schema: Optional[Dict[str, Any]] = None
    ai_params: Optional[Dict[str, Any]] = None
    editor_component: Optional[str] = None
    is_ai_enabled: Optional[bool] = None
    is_singleton: Optional[bool] = None
    default_ai_context_template: Optional[str] = None
    ui_layout: Optional[Dict[str, Any]] = None


class CardTypeRead(CardTypeBase):
    id: int
    built_in: bool = False


# --- Card Schemas ---

class CardBase(BaseModel):
    title: str
    model_name: Optional[str] = None
    content: Optional[Dict[str, Any]] = Field(default_factory=dict)
    parent_id: Optional[int] = None
    card_type_id: int
    # Instance optional custom structure; empty means follow type
    json_schema: Optional[Dict[str, Any]] = None
    # Instance AI parameters; empty means follow type
    ai_params: Optional[Dict[str, Any]] = None


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    title: Optional[str] = None
    model_name: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    parent_id: Optional[int] = None
    display_order: Optional[int] = None
    ai_context_template: Optional[str] = None
    json_schema: Optional[Dict[str, Any]] = None
    ai_params: Optional[Dict[str, Any]] = None


class CardRead(CardBase):
    id: int
    project_id: int
    created_at: datetime
    display_order: int
    card_type: CardTypeRead
    # Specific card can override type default template
    ai_context_template: Optional[str] = None


# --- Operations ---

class CardCopyOrMoveRequest(BaseModel):
    target_project_id: int
    parent_id: Optional[int] = None


class CardOrderItem(BaseModel):
    """Sort information for a single card"""
    card_id: int
    display_order: int
    parent_id: Optional[int] = None


class CardBatchReorderRequest(BaseModel):
    """Batch update card ordering request"""
    updates: List[CardOrderItem] = Field(description="List of card sortings to update")