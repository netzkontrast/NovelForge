from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from app.db.models import Prompt
from app.schemas.prompt import PromptCreate, PromptUpdate
from string import Template

def get_prompt(session: Session, prompt_id: int) -> Optional[Prompt]:
    """Get single prompt by ID"""
    return session.get(Prompt, prompt_id)

def get_prompt_by_name(session: Session, prompt_name: str) -> Optional[Prompt]:
    """Get single prompt by name"""
    statement = select(Prompt).where(Prompt.name == prompt_name)
    return session.exec(statement).first()

def get_prompts(session: Session, skip: int = 0, limit: int = 100) -> List[Prompt]:
    """Get prompt list"""
    statement = select(Prompt).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_prompt(session: Session, prompt_create: PromptCreate) -> Prompt:
    """Create new prompt"""
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
    """Update prompt"""
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
    """Delete prompt"""
    db_prompt = session.get(Prompt, prompt_id)
    if not db_prompt:
        return False
    session.delete(db_prompt)
    session.commit()
    return True

def render_prompt(prompt_template: str, context: Dict[str, Any]) -> str:
    """
    Render prompt template using context.
    
    :param prompt_template: String template with placeholders (e.g., "Hello, ${name}")
    :param context: Dictionary containing values to fill in the template (e.g., {"name": "World"})
    :return: Rendered string ("Hello, World")
    """
    template = Template(prompt_template)
    try:
        return template.substitute(context)
    except KeyError as e:
        raise ValueError(f"Prompt rendering failed: Missing variable '{e.args[0]}' in context")
    except Exception as e:
        raise ValueError(f"Unknown error occurred during prompt rendering: {e}")