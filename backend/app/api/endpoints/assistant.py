"""
Inspiration Assistant dedicated endpoints
Support conversation with tool calls
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import AsyncGenerator
from loguru import logger
import json

from app.db.session import get_session
from app.services.agent_service import generate_assistant_chat_streaming, generate_assistant_chat_streaming_react
from app.schemas.ai import AssistantChatRequest

router = APIRouter(prefix="/assistant", tags=["assistant"])


async def stream_wrapper(generator):
    """Wrap plain text stream into SSE format"""
    async for item in generator:
        yield f"data: {json.dumps({'content': item}, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def assistant_chat(
    request: AssistantChatRequest,
    session: Session = Depends(get_session)
):
    """
    Inspiration Assistant Chat Interface (Supports Tool Calling)
    
    Features:
    - Dedicated request model (clear semantics)
    - Auto-inject toolset
    - Supports streaming output
    - Supports tool execution result return
    """
    # Load system prompt (select different prompt based on mode)
    from app.services import prompt_service
    
    prompt_name = request.prompt_name
    if request.use_react_mode and request.prompt_name == "灵感对话":
        # ReAct mode uses dedicated prompt
        prompt_name = "灵感对话-React"
    
    p = prompt_service.get_prompt_by_name(session, prompt_name)
    if not p or not p.template:
        raise HTTPException(status_code=400, detail=f"Prompt not found: {prompt_name}")
    
    system_prompt = str(p.template)
    
    # Select generation function based on mode
    async def stream_with_tools() -> AsyncGenerator[str, None]:
        if request.use_react_mode:
            # ReAct Mode: Text format tool calling
            logger.info(f"[Assistant API] Using ReAct Mode")
            async for chunk in generate_assistant_chat_streaming_react(
                session=session,
                request=request,
                system_prompt=system_prompt,
                track_stats=True
            ):
                yield chunk
        else:
            # Standard Mode: Native Function Calling
            logger.info(f"[Assistant API] Using Standard Mode (Function Calling)")
            from app.services.assistant_tools.pydantic_ai_tools import ASSISTANT_TOOLS, AssistantDeps
            
            deps = AssistantDeps(session=session, project_id=request.project_id)
            
            async for chunk in generate_assistant_chat_streaming(
                session=session,
                request=request,
                system_prompt=system_prompt,
                tools=ASSISTANT_TOOLS,
                deps=deps,
                track_stats=True
            ):
                yield chunk
    
    return StreamingResponse(
        stream_wrapper(stream_with_tools()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
