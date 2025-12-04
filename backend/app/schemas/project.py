
from sqlmodel import SQLModel
from typing import Optional

# 1. Define base model (Base Model)
class ProjectBase(SQLModel):
    name: str
    description: Optional[str] = None

# 2. Model for creating a project (Create Schema)
class ProjectCreate(ProjectBase):
    # Optional project initialization workflow (usually onprojectcreate type)
    workflow_id: Optional[int] = None

# 3. Model for reading a project from database (Read Schema)
class ProjectRead(ProjectBase):
    id: int

# 4. Model for updating a project (Update Schema)
class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None 