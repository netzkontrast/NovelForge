from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ContinuationRequest(BaseModel):
    previous_content: str = Field(default="", description="Written chapter content")
    llm_config_id: int
    stream: bool = False
    # Optional context fields (backward compatibility)
    project_id: Optional[int] = None
    volume_number: Optional[int] = None
    chapter_number: Optional[int] = None
    participants: Optional[List[str]] = None
    # Sampling and timeout (optional)
    temperature: Optional[float] = Field(default=None, description="Sampling temperature 0-2, use model default if empty")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens generated, use default if empty")
    timeout: Optional[float] = Field(default=None, description="Generation timeout (seconds), use default if empty")
    # Context info (Cited context + Fact subgraph)
    context_info: Optional[str] = Field(default=None, description="Context information, including cited content and fact subgraph")
    # Existing content word count (Used to guide continuation length)
    existing_word_count: Optional[int] = Field(default=None, description="Word count of existing chapter text")
    # Prompt name selected in parameter card (Prioritize using this prompt as system prompt)
    prompt_name: Optional[str] = Field(default=None, description="Prompt name selected in parameter card")
    # Whether to append "Directly output continuous novel text" suffix (Default True compatible with original continuation)
    append_continuous_novel_directive: bool = Field(default=True, description="Whether to append continuous novel text directive")

class ContinuationResponse(BaseModel):
    content: str


class AssistantChatRequest(BaseModel):
    """Inspiration Assistant Chat Request (New Format)"""
    # New format: Frontend sends unified context info and user input
    context_info: str = Field(description="Complete project context info (including project structure, operation history, cited cards, etc.)")
    user_prompt: str = Field(default="", description="User current input (can be empty)")
    
    # Required fields
    project_id: int = Field(description="Project ID (for tool calling scope)")
    llm_config_id: int = Field(description="LLM Config ID")
    prompt_name: str = Field(default="Inspiration Chat", description="System prompt name")
    
    # Optional parameters
    temperature: Optional[float] = Field(default=None, description="Sampling temperature 0-2")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens")
    timeout: Optional[float] = Field(default=None, description="Timeout seconds")
    stream: bool = Field(default=True, description="Whether streaming output")
    use_react_mode: bool = Field(default=False, description="Whether to use ReAct mode (Text format tool calling)")


class GeneralAIRequest(BaseModel):
    input: Dict[str, Any]
    llm_config_id: Optional[int] = None
    prompt_name: Optional[str] = None
    response_model_name: Optional[Dict[str, Any]] | Optional[str] = None
    response_model_schema: Optional[Dict[str, Any]] = None  # Used for dynamic model creation
    # Sampling and timeout (optional)
    temperature: Optional[float] = Field(default=None, description="Sampling temperature 0-2, use model default if empty")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens generated, use default if empty")
    timeout: Optional[float] = Field(default=None, description="Generation timeout (seconds), use default if empty")
    # Frontend directly passed dependencies (JSON string, e.g. {\"all_entity_names\":[...]}")
    deps: Optional[str] = Field(default=None, description="Dependency injection data (JSON string), e.g. entity name list etc.")

    class Config:
        extra = 'ignore'