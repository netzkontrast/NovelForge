
from sqlmodel import SQLModel
from typing import Optional

# 1. Define base model (Base Model)
class ProjectBase(SQLModel):
    """
    Base model for Project.

    Attributes:
        name: Name of the project.
        description: Description of the project.
    """
    name: str
    description: Optional[str] = None

# 2. Model for creating a project (Create Schema)
class ProjectCreate(ProjectBase):
    """
    Schema for creating a new Project.

    Attributes:
        workflow_id: Optional ID of an initialization workflow to run.
    """
    # Optional project initialization workflow (usually onprojectcreate type)
    workflow_id: Optional[int] = None

# 3. Model for reading a project from database (Read Schema)
class ProjectRead(ProjectBase):
    """
    Schema for reading a Project.

    Attributes:
        id: Unique identifier for the project.
    """
    id: int

# 4. Model for updating a project (Update Schema)
class ProjectUpdate(SQLModel):
    """
    Schema for updating an existing Project.

    Attributes:
        name: Name of the project.
        description: Description of the project.
    """
    name: Optional[str] = None
    description: Optional[str] = None
