from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# --- CardType Schemas ---

class CardTypeBase(BaseModel):
    """
    Base schema for CardType.

    Attributes:
        name: The name of the card type.
        model_name: Optional model name.
        description: Description of the card type.
        json_schema: JSON Schema definition for the card type structure.
        ai_params: Default AI parameters for this card type.
        editor_component: Editor component identifier.
        is_ai_enabled: Whether AI is enabled for this card type.
        is_singleton: Whether this card type is a singleton.
        default_ai_context_template: Default template for AI context injection.
        ui_layout: Optional UI layout configuration.
    """
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
    """
    Schema for creating a new CardType.
    """
    pass


class CardTypeUpdate(BaseModel):
    """
    Schema for updating an existing CardType.

    Attributes:
        name: The name of the card type.
        model_name: Optional model name.
        description: Description of the card type.
        json_schema: JSON Schema definition.
        ai_params: Default AI parameters.
        editor_component: Editor component identifier.
        is_ai_enabled: Whether AI is enabled.
        is_singleton: Whether this card type is a singleton.
        default_ai_context_template: Default template for AI context injection.
        ui_layout: Optional UI layout configuration.
    """
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
    """
    Schema for reading a CardType.

    Attributes:
        id: Unique identifier for the card type.
        built_in: Whether the card type is built-in.
    """
    id: int
    built_in: bool = False


# --- Card Schemas ---

class CardBase(BaseModel):
    """
    Base schema for Card.

    Attributes:
        title: The title of the card.
        model_name: Optional model name.
        content: The content of the card.
        parent_id: The ID of the parent card (optional).
        card_type_id: The ID of the card type.
        json_schema: Custom JSON schema for this card instance (overrides type schema).
        ai_params: Custom AI parameters for this card instance (overrides type parameters).
    """
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
    """
    Schema for creating a new Card.
    """
    pass


class CardUpdate(BaseModel):
    """
    Schema for updating an existing Card.

    Attributes:
        title: The title of the card.
        model_name: Optional model name.
        content: The content of the card.
        parent_id: The ID of the parent card.
        display_order: The display order of the card.
        ai_context_template: Custom AI context template for this card.
        json_schema: Custom JSON schema for this card instance.
        ai_params: Custom AI parameters for this card instance.
    """
    title: Optional[str] = None
    model_name: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    parent_id: Optional[int] = None
    display_order: Optional[int] = None
    ai_context_template: Optional[str] = None
    json_schema: Optional[Dict[str, Any]] = None
    ai_params: Optional[Dict[str, Any]] = None


class CardRead(CardBase):
    """
    Schema for reading a Card.

    Attributes:
        id: Unique identifier for the card.
        project_id: The ID of the project the card belongs to.
        created_at: The creation timestamp.
        display_order: The display order of the card.
        card_type: The detailed CardType information.
        ai_context_template: Custom AI context template for this card.
    """
    id: int
    project_id: int
    created_at: datetime
    display_order: int
    card_type: CardTypeRead
    # Specific card can override type default template
    ai_context_template: Optional[str] = None


# --- Operations ---

class CardCopyOrMoveRequest(BaseModel):
    """
    Request model for copying or moving a card.

    Attributes:
        target_project_id: The ID of the target project.
        parent_id: The ID of the new parent card (optional).
    """
    target_project_id: int
    parent_id: Optional[int] = None


class CardOrderItem(BaseModel):
    """
    Sort information for a single card.

    Attributes:
        card_id: The ID of the card.
        display_order: The new display order.
        parent_id: The ID of the parent card (optional).
    """
    card_id: int
    display_order: int
    parent_id: Optional[int] = None


class CardBatchReorderRequest(BaseModel):
    """
    Batch update card ordering request.

    Attributes:
        updates: List of card sortings to update.
    """
    updates: List[CardOrderItem] = Field(description="List of card sortings to update")
