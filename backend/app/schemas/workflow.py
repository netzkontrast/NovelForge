from typing import Optional, Any, List
from pydantic import BaseModel


class WorkflowBase(BaseModel):
    """
    Base model for Workflow.

    Attributes:
        name: Name of the workflow.
        description: Description of the workflow.
        is_active: Whether the workflow is active.
        is_built_in: Whether the workflow is built-in.
        version: Version number.
        dsl_version: DSL version number.
        definition_json: JSON definition of the workflow.
    """
    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True
    is_built_in: Optional[bool] = False
    version: Optional[int] = 1
    dsl_version: Optional[int] = 1
    definition_json: Optional[dict] = None


class WorkflowCreate(WorkflowBase):
    """
    Schema for creating a new Workflow.
    """
    pass


class WorkflowUpdate(BaseModel):
    """
    Schema for updating an existing Workflow.

    Attributes:
        name: Name of the workflow.
        description: Description of the workflow.
        is_active: Whether the workflow is active.
        version: Version number.
        dsl_version: DSL version number.
        definition_json: JSON definition of the workflow.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    version: Optional[int] = None
    dsl_version: Optional[int] = None
    definition_json: Optional[dict] = None


class WorkflowRead(WorkflowBase):
    """
    Schema for reading a Workflow.

    Attributes:
        id: Unique identifier for the workflow.
    """
    id: int

    class Config:
        from_attributes = True


class WorkflowRunRead(BaseModel):
    """
    Schema for reading a Workflow Run.

    Attributes:
        id: Unique identifier for the run.
        workflow_id: ID of the workflow.
        definition_version: Version of the workflow definition used.
        status: Status of the run.
        scope_json: Scope data.
        params_json: Parameters data.
        idempotency_key: Idempotency key.
        summary_json: Summary data.
        error_json: Error data.
    """
    id: int
    workflow_id: int
    definition_version: int
    status: str
    scope_json: Optional[dict] = None
    params_json: Optional[dict] = None
    idempotency_key: Optional[str] = None
    summary_json: Optional[dict] = None
    error_json: Optional[dict] = None

    class Config:
        from_attributes = True


class RunRequest(BaseModel):
    """
    Request model for running a workflow.

    Attributes:
        scope_json: Scope data.
        params_json: Parameters data.
        idempotency_key: Idempotency key.
    """
    scope_json: Optional[dict] = None
    params_json: Optional[dict] = None
    idempotency_key: Optional[str] = None


class CancelResponse(BaseModel):
    """
    Response model for cancelling a workflow run.

    Attributes:
        ok: Whether the cancellation was successful.
        message: Optional message.
    """
    ok: bool
    message: Optional[str] = None




# ---- Triggers ----

class WorkflowTriggerBase(BaseModel):
    """
    Base model for Workflow Trigger.

    Attributes:
        workflow_id: ID of the workflow to trigger.
        trigger_on: Trigger event (onsave | ongenfinish | manual).
        card_type_name: Optional card type name filter.
        filter_json: Optional filter JSON.
        is_active: Whether the trigger is active.
    """
    workflow_id: int
    trigger_on: str  # onsave | ongenfinish | manual
    card_type_name: Optional[str] = None
    filter_json: Optional[dict] = None
    is_active: Optional[bool] = True


class WorkflowTriggerCreate(WorkflowTriggerBase):
    """
    Schema for creating a new Workflow Trigger.
    """
    pass


class WorkflowTriggerUpdate(BaseModel):
    """
    Schema for updating an existing Workflow Trigger.

    Attributes:
        trigger_on: Trigger event.
        card_type_name: Card type name filter.
        filter_json: Filter JSON.
        is_active: Whether the trigger is active.
    """
    trigger_on: Optional[str] = None
    card_type_name: Optional[str] = None
    filter_json: Optional[dict] = None
    is_active: Optional[bool] = None


class WorkflowTriggerRead(WorkflowTriggerBase):
    """
    Schema for reading a Workflow Trigger.

    Attributes:
        id: Unique identifier for the trigger.
    """
    id: int

    class Config:
        from_attributes = True
