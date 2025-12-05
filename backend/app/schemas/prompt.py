from typing import Optional

from sqlmodel import SQLModel, Field

class PromptBase(SQLModel):
    """
    Base model for Prompt.

    Attributes:
        name: Name of the prompt.
        description: Description of the prompt.
        template: The prompt template string.
    """
    name: str = Field(index=True)
    description: Optional[str] = None
    template: str

class PromptRead(PromptBase):
    """
    Schema for reading a Prompt.

    Attributes:
        id: Unique identifier for the prompt.
        built_in: Whether the prompt is built-in.
    """
    id: int
    built_in: bool = False

class PromptCreate(PromptBase):
    """
    Schema for creating a new Prompt.
    """
    pass

class PromptUpdate(SQLModel):
    """
    Schema for updating an existing Prompt.

    Attributes:
        name: Name of the prompt.
        description: Description of the prompt.
        template: The prompt template string.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None

# Knowledge Base Schema
class KnowledgeBase(SQLModel):
    """
    Base model for Knowledge Base items.

    Attributes:
        name: Name of the knowledge base item.
        description: Description of the item.
        content: Content of the knowledge base item.
        built_in: Whether the item is built-in.
    """
    name: str
    description: Optional[str] = None
    content: str
    built_in: bool = False

class KnowledgeRead(KnowledgeBase):
    """
    Schema for reading a Knowledge Base item.

    Attributes:
        id: Unique identifier for the item.
    """
    id: int

class KnowledgeCreate(SQLModel):
    """
    Schema for creating a new Knowledge Base item.

    Attributes:
        name: Name of the item.
        description: Description of the item.
        content: Content of the item.
    """
    name: str
    description: Optional[str] = None
    content: str

class KnowledgeUpdate(SQLModel):
    """
    Schema for updating an existing Knowledge Base item.

    Attributes:
        name: Name of the item.
        description: Description of the item.
        content: Content of the item.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
