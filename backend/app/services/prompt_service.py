from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from app.db.models import Prompt
from app.schemas.prompt import PromptCreate, PromptUpdate
from string import Template

def get_prompt(session: Session, prompt_id: int) -> Optional[Prompt]:
    """
    Get single prompt by ID.

    Args:
        session: Database session.
        prompt_id: Prompt ID.

    Returns:
        Prompt object or None.
    """
    return session.get(Prompt, prompt_id)

def get_prompt_by_name(session: Session, prompt_name: str) -> Optional[Prompt]:
    """
    Get single prompt by name.

    Args:
        session: Database session.
        prompt_name: Prompt name.

    Returns:
        Prompt object or None.
    """
    statement = select(Prompt).where(Prompt.name == prompt_name)
    return session.exec(statement).first()

def get_prompts(session: Session, skip: int = 0, limit: int = 100) -> List[Prompt]:
    """
    Get prompt list.

    Args:
        session: Database session.
        skip: Offset.
        limit: Limit.

    Returns:
        List of Prompt objects.
    """
    statement = select(Prompt).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_prompt(session: Session, prompt_create: PromptCreate) -> Prompt:
    """
    Create new prompt.

    Args:
        session: Database session.
        prompt_create: Prompt creation data.

    Returns:
        Created Prompt object.

    Raises:
        ValueError: If prompt name already exists.
    """
    # Check if name already exists
    existing_prompt = get_prompt_by_name(session, prompt_create.name)
    if existing_prompt:
        raise ValueError(f"Prompt name '{prompt_create.name}' already exists")
    
    db_prompt = Prompt.model_validate(prompt_create)
    session.add(db_prompt)
    session.commit()
    session.refresh(db_prompt)
    return db_prompt

def update_prompt(session: Session, prompt_id: int, prompt_update: PromptUpdate) -> Optional[Prompt]:
    """
    Update prompt.

    Args:
        session: Database session.
        prompt_id: Prompt ID.
        prompt_update: Update data.

    Returns:
        Updated Prompt object or None.
    """
    db_prompt = session.get(Prompt, prompt_id)
    if not db_prompt:
        return None
    prompt_data = prompt_update.model_dump(exclude_unset=True)
    for key, value in prompt_data.items():
        setattr(db_prompt, key, value)
    session.add(db_prompt)
    session.commit()
    session.refresh(db_prompt)
    return db_prompt

def delete_prompt(session: Session, prompt_id: int) -> bool:
    """
    Delete prompt.

    Args:
        session: Database session.
        prompt_id: Prompt ID.

    Returns:
        True if deleted, False if not found.
    """
    db_prompt = session.get(Prompt, prompt_id)
    if not db_prompt:
        return False
    session.delete(db_prompt)
    session.commit()
    return True

def render_prompt(prompt_template: str, context: Dict[str, Any]) -> str:
    """
    Render prompt template using context.
    
    Args:
        prompt_template: String template with placeholders (e.g., "Hello, ${name}").
        context: Dictionary containing values to fill in the template.

    Returns:
        Rendered string.

    Raises:
        ValueError: If rendering fails.
    """
    template = Template(prompt_template)
    try:
        return template.substitute(context)
    except KeyError as e:
        raise ValueError(f"Prompt rendering failed: Missing variable '{e.args[0]}' in context")
    except Exception as e:
        raise ValueError(f"Unknown error occurred during prompt rendering: {e}")
