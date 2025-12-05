
from sqlmodel import Session, select
from app.db.models import LLMConfig
from app.schemas.llm_config import LLMConfigCreate, LLMConfigUpdate

def create_llm_config(session: Session, config_in: LLMConfigCreate) -> LLMConfig:
    """
    Create a new LLM configuration.

    Args:
        session: Database session.
        config_in: Configuration creation data.

    Returns:
        Created LLMConfig object.
    """
    # Now use config_in directly to create model, it includes api_key
    db_config = LLMConfig.model_validate(config_in)
    
    session.add(db_config)
    session.commit()
    session.refresh(db_config)
    return db_config

def get_llm_configs(session: Session) -> list[LLMConfig]:
    """
    Get all LLM configurations.

    Args:
        session: Database session.

    Returns:
        List of LLMConfig objects.
    """
    return session.exec(select(LLMConfig)).all()

def get_llm_config(session: Session, config_id: int) -> LLMConfig | None:
    """
    Get an LLM configuration by ID.

    Args:
        session: Database session.
        config_id: Configuration ID.

    Returns:
        LLMConfig object or None.
    """
    return session.get(LLMConfig, config_id)

def update_llm_config(session: Session, config_id: int, config_in: LLMConfigUpdate) -> LLMConfig | None:
    """
    Update an existing LLM configuration.

    Args:
        session: Database session.
        config_id: Configuration ID.
        config_in: Update data.

    Returns:
        Updated LLMConfig object or None if not found.
    """
    db_config = session.get(LLMConfig, config_id)
    if not db_config:
        return None
    
    # Update data directly, no longer exclude api_key
    update_data = config_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_config, key, value)
    
    session.add(db_config)
    session.commit()
    session.refresh(db_config)
    return db_config

def delete_llm_config(session: Session, config_id: int) -> bool:
    """
    Delete an LLM configuration.

    Args:
        session: Database session.
        config_id: Configuration ID.

    Returns:
        True if deleted, False if not found.
    """
    db_config = session.get(LLMConfig, config_id)
    if not db_config:
        return False
    
    session.delete(db_config)
    session.commit()
    return True 


def can_consume(session: Session, config_id: int, need_input_tokens: int, need_output_tokens: int = 0, need_calls: int = 1) -> tuple[bool, str]:
    """
    Check if the LLM configuration has enough quota.

    Args:
        session: Database session.
        config_id: Configuration ID.
        need_input_tokens: Required input tokens.
        need_output_tokens: Required output tokens (estimated).
        need_calls: Required calls.

    Returns:
        Tuple (success, reason).
    """
    cfg = session.get(LLMConfig, config_id)
    if not cfg:
        return False, "LLM Config not found"
    # Token limit (-1 unlimited)
    total_need = max(0, need_input_tokens) + max(0, need_output_tokens)
    if cfg.token_limit is not None and cfg.token_limit >= 0:
        if (cfg.used_tokens_input + cfg.used_tokens_output + total_need) > cfg.token_limit:
            return False, "Token limit exceeded"
    # Call count
    if cfg.call_limit is not None and cfg.call_limit >= 0:
        if (cfg.used_calls + need_calls) > cfg.call_limit:
            return False, "Call limit exceeded"
    return True, "OK"


def accumulate_usage(session: Session, config_id: int, add_input_tokens: int, add_output_tokens: int, add_calls: int, aborted: bool = False) -> None:
    """
    Accumulate usage statistics for an LLM configuration.

    Args:
        session: Database session.
        config_id: Configuration ID.
        add_input_tokens: Input tokens used.
        add_output_tokens: Output tokens used.
        add_calls: Calls made.
        aborted: Whether the task was aborted (unused).
    """
    cfg = session.get(LLMConfig, config_id)
    if not cfg:
        return
    # Increment call count regardless of normal or aborted task (distinguish if needed)
    cfg.used_calls = (cfg.used_calls or 0) + max(0, add_calls)
    cfg.used_tokens_input = (cfg.used_tokens_input or 0) + max(0, add_input_tokens)
    cfg.used_tokens_output = (cfg.used_tokens_output or 0) + max(0, add_output_tokens)
    session.add(cfg)
    session.commit()


def reset_usage(session: Session, config_id: int) -> bool:
    """
    Reset usage statistics for an LLM configuration.

    Args:
        session: Database session.
        config_id: Configuration ID.

    Returns:
        True if reset, False if not found.
    """
    cfg = session.get(LLMConfig, config_id)
    if not cfg:
        return False
    cfg.used_tokens_input = 0
    cfg.used_tokens_output = 0
    cfg.used_calls = 0
    session.add(cfg)
    session.commit()
    return True