
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
import sqlalchemy as sa
from typing import Optional, List, Any
from datetime import datetime


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None

    cards: List["Card"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})



class LLMConfig(SQLModel, table=True):
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
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    template: str
    version: int = 1
    built_in: bool = Field(default=False)



class CardType(SQLModel, table=True):
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
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    content: str
    built_in: bool = Field(default=False)


# Workflow System
class Workflow(SQLModel, table=True):
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