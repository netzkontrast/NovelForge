
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db.session import get_session
from app.schemas.llm_config import LLMConfigCreate, LLMConfigRead, LLMConfigUpdate, LLMConnectionTest
from app.schemas.response import ApiResponse
from app.services import llm_config_service
from typing import List
from app.services.agent_service import _get_agent
from pydantic import BaseModel

router = APIRouter()

@router.post("/", response_model=ApiResponse[LLMConfigRead])
def create_llm_config_endpoint(config_in: LLMConfigCreate, session: Session = Depends(get_session)):
    """Create a new LLM configuration."""
    if config_in.display_name is None or config_in.display_name == "":
        config_in.display_name = config_in.model_name
    config = llm_config_service.create_llm_config(session=session, config_in=config_in)
    return ApiResponse(data=config)

@router.get("/", response_model=ApiResponse[List[LLMConfigRead]])
def get_llm_configs_endpoint(session: Session = Depends(get_session)):
    """Get all LLM configurations."""
    configs = llm_config_service.get_llm_configs(session=session)
    return ApiResponse(data=configs)

@router.put("/{config_id}", response_model=ApiResponse[LLMConfigRead])
def update_llm_config_endpoint(config_id: int, config_in: LLMConfigUpdate, session: Session = Depends(get_session)):
    """Update an existing LLM configuration."""
    config = llm_config_service.update_llm_config(session=session, config_id=config_id, config_in=config_in)
    if not config:
        raise HTTPException(status_code=404, detail="LLM Config not found")
    return ApiResponse(data=config)

@router.delete("/{config_id}", response_model=ApiResponse)
def delete_llm_config_endpoint(config_id: int, session: Session = Depends(get_session)):
    """Delete an LLM configuration."""
    success = llm_config_service.delete_llm_config(session=session, config_id=config_id)
    if not success:
        raise HTTPException(status_code=404, detail="LLM Config not found")
    return ApiResponse(message="LLM Config deleted successfully")

@router.post("/test", response_model=ApiResponse, summary="Test LLM connection")
async def test_llm_connection_endpoint(connection_data: LLMConnectionTest, session: Session = Depends(get_session)):
    """Temporarily construct an Agent using passed parameters and initiate a minimal call to verify connectivity."""
    try:
        # Reuse pydantic-ai Provider/Model, minimal connectivity test by provider branch
        from pydantic_ai import Agent
        from pydantic_ai.settings import ModelSettings

        provider = None
        model = None
        if connection_data.provider == 'google':
            # Google Generative Language API (API Key)
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider
            provider = GoogleProvider(api_key=connection_data.api_key)
            model = GoogleModel(connection_data.model_name, provider=provider)
        else:
            # Default to OpenAI compatible path (including custom/base_url)
            from pydantic_ai.models.openai import OpenAIModel
            from pydantic_ai.providers.openai import OpenAIProvider
            provider_cfg = {"api_key": connection_data.api_key}
            if connection_data.api_base:
                provider_cfg["base_url"] = connection_data.api_base
            provider = OpenAIProvider(**provider_cfg)
            model = OpenAIModel(connection_data.model_name, provider=provider)

        agent = Agent(model, system_prompt="You are a helpful assistant.", model_settings=ModelSettings(timeout=15))
        await agent.run("ping")
        return ApiResponse(message="Connection successful")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection test failed: {e}")


@router.post("/{config_id}/reset-usage", response_model=ApiResponse, summary="Reset usage statistics (clear input/output tokens and call count)")
def reset_llm_usage(config_id: int, session: Session = Depends(get_session)):
    """Reset usage statistics for an LLM configuration."""
    ok = llm_config_service.reset_usage(session, config_id)
    if not ok:
        raise HTTPException(status_code=404, detail="LLM Config not found")
    return ApiResponse(message="Usage reset")
