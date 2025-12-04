
from typing import List, Optional
from sqlmodel import Session, select

from app.db.models import Project, Workflow
from app.services import workflow_triggers
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.card_service import CardService
from app.services.kg_provider import get_provider


FREE_PROJECT_NAME = "__free__"

# Get or create reserved project (__free__)
def get_or_create_free_project(session: Session) -> Project:
    proj = session.exec(select(Project).where(Project.name == FREE_PROJECT_NAME)).first()
    if proj:
        return proj
    proj = Project(name=FREE_PROJECT_NAME, description="System reserved project: store free cards")
    session.add(proj)
    session.commit()
    session.refresh(proj)
    return proj


def get_projects(session: Session) -> List[Project]:
    statement = select(Project).order_by(Project.id.desc())
    return session.exec(statement).all()


def get_project(session: Session, project_id: int) -> Optional[Project]:
    statement = (
        select(Project)
        .where(Project.id == project_id)
    )
    return session.exec(statement).first()




def create_project(session: Session, project_in: ProjectCreate) -> Project:
    db_project = Project.model_validate(project_in)
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    
    # If workflow_id passed, run that workflow directly
    workflow_id = getattr(project_in, 'workflow_id', None)
    if isinstance(workflow_id, int) and workflow_id > 0:
        wf = session.get(Workflow, workflow_id)
        if wf:
            # Create a run directly, scope only carries project_id
            from app.services.workflow_engine import engine as wf_engine
            run = wf_engine.create_run(session, wf, scope_json={"project_id": db_project.id}, params_json={}, idempotency_key=f"proj-init:{db_project.id}:{workflow_id}")
            wf_engine.run(session, run)
    else:
        # Trigger all onprojectcreate workflows
        try:
            workflow_triggers.trigger_on_project_create(session, db_project.id)
        except Exception:
            # Do not block project creation
            pass
    
    # Refresh to load newly created cards into project relationships
    session.refresh(db_project)
    
    return db_project


def update_project(session: Session, project_id: int, project_in: ProjectUpdate) -> Optional[Project]:
    db_project = session.get(Project, project_id)
    if not db_project:
        return None
    project_data = project_in.model_dump(exclude_unset=True)
    for key, value in project_data.items():
        setattr(db_project, key, value)
    session.add(db_project)
    session.flush()
    session.refresh(db_project)
    return db_project


def delete_project(session: Session, project_id: int) -> bool:
    project = session.get(Project, project_id)
    if not project:
        return False
    # Reserved project cannot be deleted
    if getattr(project, 'name', None) == FREE_PROJECT_NAME:
        return False
    # Delete project record from DB first
    session.delete(project)
    session.commit()
    # Then clean up all entities and relations of this project in Graph DB
    try:
        kg = get_provider()
        kg.delete_project_graph(project_id)
    except Exception:
        # Avoid affecting main flow when Graph DB is unavailable
        pass
    return True 