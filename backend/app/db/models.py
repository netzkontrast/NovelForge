
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
import sqlalchemy as sa
from typing import Optional, List, Any
from datetime import datetime


class Project(SQLModel, table=True):
    """
    Model representing a Project.

    Attributes:
        id: Unique identifier for the project.
        name: Name of the project.
        description: Description of the project.
        cards: List of cards associated with the project.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None

    cards: List["Card"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})



class LLMConfig(SQLModel, table=True):
    """
    Model representing LLM Configuration.

    Attributes:
        id: Unique identifier.
        provider: Provider name (e.g. openai).
        display_name: Display name.
        model_name: Model name.
        api_base: API base URL.
        api_key: API key.
        base_url: Base URL (optional).
        token_limit: Token limit (-1 for unlimited).
        call_limit: Call limit (-1 for unlimited).
        used_tokens_input: Total input tokens used.
        used_tokens_output: Total output tokens used.
        used_calls: Total calls made.
        rpm_limit: Requests per minute limit.
        tpm_limit: Tokens per minute limit.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(index=True)
    display_name: Optional[str] = None
    model_name: str
    api_base: Optional[str] = None
    api_key: str
    base_url: Optional[str] = None
    # Stats and Quotas (-1 means unlimited) - Also set server_default at DB layer for Alembic automatic inclusion
    token_limit: int = Field(
        default=-1,
        sa_column=Column(sa.Integer, nullable=False, server_default='-1')
    )
    call_limit: int = Field(
        default=-1,
        sa_column=Column(sa.Integer, nullable=False, server_default='-1')
    )
    used_tokens_input: int = Field(
        default=0,
        sa_column=Column(sa.Integer, nullable=False, server_default='0')
    )
    used_tokens_output: int = Field(
        default=0,
        sa_column=Column(sa.Integer, nullable=False, server_default='0')
    )
    used_calls: int = Field(
        default=0,
        sa_column=Column(sa.Integer, nullable=False, server_default='0')
    )
    # RPM/TPM placeholder only, not implemented yet
    rpm_limit: int = Field(
        default=-1,
        sa_column=Column(sa.Integer, nullable=False, server_default='-1')
    )
    tpm_limit: int = Field(
        default=-1,
        sa_column=Column(sa.Integer, nullable=False, server_default='-1')
    )


class Prompt(SQLModel, table=True):
    """
    Model representing a Prompt.

    Attributes:
        id: Unique identifier.
        name: Unique name of the prompt.
        description: Description of the prompt.
        template: The prompt template string.
        version: Version number.
        built_in: Whether the prompt is built-in.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    template: str
    version: int = 1
    built_in: bool = Field(default=False)



class CardType(SQLModel, table=True):
    """
    Model representing a Card Type.

    Attributes:
        id: Unique identifier.
        name: Name of the card type.
        model_name: Model name identifier.
        description: Description.
        json_schema: JSON Schema structure.
        ai_params: Default AI parameters.
        editor_component: Editor component identifier.
        is_ai_enabled: Whether AI is enabled.
        is_singleton: Whether only one instance is allowed per project.
        built_in: Whether the card type is built-in.
        default_ai_context_template: Default AI context template.
        ui_layout: UI layout configuration.
        cards: List of cards of this type.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    # Compatible with old model names (e.g. CharacterCard/SceneCard), if empty defaults to equal name
    model_name: Optional[str] = Field(default=None, index=True)
    description: Optional[str] = None
    # Type built-in structure (JSON Schema)
    json_schema: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    # Type level default AI params (model ID/prompt/sampling etc.)
    ai_params: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    editor_component: Optional[str] = None  # e.g., 'NovelEditor' for custom UI
    is_ai_enabled: bool = Field(default=True)
    is_singleton: bool = Field(default=False)  # e.g., only one 'Synopsis' card per project
    built_in: bool = Field(default=False)
    # Card type level default context injection template
    default_ai_context_template: Optional[str] = Field(default=None)
    # UI Layout (Optional), for frontend SectionedForm use
    ui_layout: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    cards: List["Card"] = Relationship(back_populates="card_type")


class Card(SQLModel, table=True):
    """
    Model representing a Card.

    Attributes:
        id: Unique identifier.
        title: Title of the card.
        model_name: Model name.
        content: Content JSON.
        created_at: Creation timestamp.
        json_schema: Instance-specific JSON Schema.
        ai_params: Instance-specific AI parameters.
        parent_id: Parent card ID.
        parent: Parent card object.
        children: List of child cards.
        project_id: Project ID.
        project: Project object.
        card_type_id: Card Type ID.
        card_type: Card Type object.
        display_order: Display order.
        ai_context_template: Instance-specific AI context template.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    # Compatible with old model names; if empty follows type model_name or type name
    model_name: Optional[str] = Field(default=None, index=True)
    content: Any = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Allow instance custom structure; if empty follows type
    json_schema: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    # Instance level AI params; if empty follows type
    ai_params: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Self-referential relationship, for tree structure
    parent_id: Optional[int] = Field(default=None, foreign_key="card.id")
    parent: Optional["Card"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "[Card.id]"}
    )
    children: List["Card"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "cascade": "all, delete, delete-orphan",
            "single_parent": True,
        },
    )

    # Project foreign key
    project_id: int = Field(foreign_key="project.id")
    project: "Project" = Relationship(back_populates="cards")

    # Card type foreign key
    card_type_id: int = Field(foreign_key="cardtype.id")
    card_type: "CardType" = Relationship(back_populates="cards")

    # For sorting cards, used for sorting under same parent
    display_order: int = Field(default=0)
    ai_context_template: Optional[str] = Field(default=None)


# Foreshadowing Registry
class ForeshadowItem(SQLModel, table=True):
    """
    Model representing a Foreshadowing Item.

    Attributes:
        id: Unique identifier.
        project_id: Project ID.
        chapter_id: Chapter ID (optional).
        title: Title.
        type: Type (goal/item/person/other).
        note: Note.
        status: Status (open/resolved).
        created_at: Creation timestamp.
        resolved_at: Resolution timestamp.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    chapter_id: Optional[int] = Field(default=None)  # Chapter card ID or chapter ID
    title: str
    type: str = Field(default='other', index=True)  # goal | item | person | other
    note: Optional[str] = None
    status: str = Field(default='open', index=True)  # open | resolved
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    resolved_at: Optional[datetime] = None


# Knowledge Base Model
class Knowledge(SQLModel, table=True):
    """
    Model representing a Knowledge Base item.

    Attributes:
        id: Unique identifier.
        name: Unique name.
        description: Description.
        content: Content.
        built_in: Whether it is built-in.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    content: str
    built_in: bool = Field(default=False)


# Workflow System
class Workflow(SQLModel, table=True):
    """
    Model representing a Workflow.

    Attributes:
        id: Unique identifier.
        name: Name.
        description: Description.
        version: Version.
        dsl_version: DSL version.
        is_built_in: Whether it is built-in.
        is_active: Whether it is active.
        definition_json: Definition JSON.
        created_at: Creation timestamp.
        updated_at: Update timestamp.
        triggers: List of associated triggers.
        runs: List of associated runs.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    version: int = Field(default=1)
    dsl_version: int = Field(default=1)
    is_built_in: bool = Field(default=False)
    is_active: bool = Field(default=True)
    definition_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relations
    triggers: List["WorkflowTrigger"] = Relationship(back_populates="workflow", sa_relationship_kwargs={
        "cascade": "all, delete-orphan"
    })
    runs: List["WorkflowRun"] = Relationship(back_populates="workflow", sa_relationship_kwargs={
        "cascade": "all, delete-orphan"
    })


class WorkflowTrigger(SQLModel, table=True):
    """
    Model representing a Workflow Trigger.

    Attributes:
        id: Unique identifier.
        workflow_id: Workflow ID.
        workflow: Workflow object.
        trigger_on: Trigger event.
        card_type_name: Card type name filter.
        filter_json: Filter JSON.
        is_active: Whether it is active.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id")
    workflow: Workflow = Relationship(back_populates="triggers")

    # onsave | ongenfinish | manual
    trigger_on: str = Field(default="manual", index=True)
    # Optional: Limit card type (Store by name, avoid circular dependency)
    card_type_name: Optional[str] = None
    # Filter rules (JSON)
    filter_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    is_active: bool = Field(default=True)


class WorkflowRun(SQLModel, table=True):
    """
    Model representing a Workflow Run.

    Attributes:
        id: Unique identifier.
        workflow_id: Workflow ID.
        workflow: Workflow object.
        definition_version: Definition version.
        status: Status (queued/running/succeeded/failed/cancelled/partial).
        scope_json: Scope JSON.
        params_json: Params JSON.
        idempotency_key: Idempotency key.
        created_at: Creation timestamp.
        started_at: Start timestamp.
        finished_at: Finish timestamp.
        summary_json: Summary JSON.
        error_json: Error JSON.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id")
    workflow: Workflow = Relationship(back_populates="runs")

    definition_version: int = Field(default=1)
    # queued | running | succeeded | failed | cancelled | partial
    status: str = Field(default="queued", index=True)
    scope_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    params_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    idempotency_key: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    summary_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    error_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
