from typing import Optional, Dict, Any, AsyncGenerator
from pydantic import BaseModel, Field
from sqlmodel import Session
from app.schemas.response_registry import RESPONSE_MODEL_MAP
from app.services import agent_service, prompt_service
import json
from loguru import logger

class ContinuationResponse(BaseModel):
    """AI Continuation Response Model"""
    continuation: str = Field(description="AI generated continuation content")

class ContinuationRequest(BaseModel):
    """Request model for AI continuation"""
    llm_config_id: int
    prompt_id: int
    context: Dict[str, Any]  # Used to fill prompt template
    max_tokens: Optional[int] = 5000
    temperature: Optional[float] = 0.7
    stream: bool = False

def extract_text_content(tiptap_content: Dict[Any, Any]) -> str:
    """Extract plain text from Tiptap editor JSON content"""
    if not tiptap_content:
        return ""
    
    try:
        # Attempt to get text from content field
        if "content" in tiptap_content:
            text_parts = []
            for item in tiptap_content["content"]:
                if item.get("type") == "paragraph" and "content" in item:
                    for content_item in item["content"]:
                        if content_item.get("type") == "text":
                            text_parts.append(content_item.get("text", ""))
            return " ".join(text_parts)
        else:
            # If structured content not found, try converting whole content to string
            return json.dumps(tiptap_content, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error extracting text content: {e}")
        return json.dumps(tiptap_content, ensure_ascii=False)

async def generate_continuation(session: Session, request: ContinuationRequest) -> ContinuationResponse:
    """Generate AI continuation content"""
    # 1. Get prompt template
    db_prompt = prompt_service.get_prompt(session, request.prompt_id)
    if not db_prompt:
        raise ValueError(f"Prompt not found, ID: {request.prompt_id}")

    # 2. Render prompt
    final_prompt = prompt_service.render_prompt(db_prompt.template, request.context)
    
    # 3. Call encapsulated LLM Agent service
    try:
        result = await agent_service.run_llm_agent(
            session=session,
            llm_config_id=request.llm_config_id,
            user_prompt=final_prompt,
            output_type=ContinuationResponse,
            system_prompt="You are a professional novel writing assistant, skilled at continuing stories based on existing content.",
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        return result
    except ValueError as e:
        logger.error(f"Error generating continuation content: {e}")
        raise e

async def generate_continuation_streaming(
    session: Session, request: ContinuationRequest
) -> AsyncGenerator[str, None]:
    """Generate AI continuation content in streaming mode"""
    # 1. Get prompt template
    db_prompt = prompt_service.get_prompt(session, request.prompt_id)
    if not db_prompt:
        raise ValueError(f"Prompt not found, ID: {request.prompt_id}")

    # 2. Render prompt
    final_prompt = prompt_service.render_prompt(db_prompt.template, request.context)

    try:
        async for text_chunk in agent_service.run_llm_agent_streaming(
            session=session,
            llm_config_id=request.llm_config_id,
            prompt=final_prompt,
            system_prompt="You are a professional novel writing assistant, skilled at continuing stories based on existing content.",
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        ):
            yield text_chunk
    except ValueError as e:
        logger.error(f"Error generating streaming continuation content: {e}")
        raise e 