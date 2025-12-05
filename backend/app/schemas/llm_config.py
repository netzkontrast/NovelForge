
from sqlmodel import SQLModel
from typing import Optional

class LLMConfigBase(SQLModel):
    """
    Base model for LLM Configuration.

    Attributes:
        provider: The provider name (e.g., openai, anthropic).
        display_name: Optional display name for the configuration.
        model_name: The model name (e.g., gpt-4, claude-2).
        api_base: Optional base URL for the API.
        api_key: Optional API key.
        token_limit: Token limit (-1 for unlimited).
        call_limit: Call limit (-1 for unlimited).
        rpm_limit: Requests per minute limit (-1 for unlimited).
        tpm_limit: Tokens per minute limit (-1 for unlimited).
        used_tokens_input: Total input tokens used.
        used_tokens_output: Total output tokens used.
        used_calls: Total calls made.
    """
    provider: str
    display_name: Optional[str] = None
    model_name: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    # Quota (-1 means unlimited) and statistics (visible externally in read-only scenarios)
    token_limit: Optional[int] = -1
    call_limit: Optional[int] = -1
    rpm_limit: Optional[int] = -1
    tpm_limit: Optional[int] = -1
    used_tokens_input: Optional[int] = 0
    used_tokens_output: Optional[int] = 0
    used_calls: Optional[int] = 0

class LLMConfigCreate(LLMConfigBase):
    """
    Schema for creating a new LLM Configuration.
    """
    pass

class LLMConfigRead(LLMConfigBase):
    """
    Schema for reading an LLM Configuration.

    Attributes:
        id: Unique identifier for the configuration.
    """
    id: int

class LLMConfigUpdate(SQLModel):
    """
    Schema for updating an existing LLM Configuration.

    Attributes:
        provider: The provider name.
        display_name: Display name.
        model_name: The model name.
        api_base: Base URL for the API.
        api_key: API key.
        token_limit: Token limit.
        call_limit: Call limit.
        rpm_limit: Requests per minute limit.
        tpm_limit: Tokens per minute limit.
        used_tokens_input: Total input tokens used.
        used_tokens_output: Total output tokens used.
        used_calls: Total calls made.
    """
    provider: Optional[str] = None
    display_name: Optional[str] = None
    model_name: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    token_limit: Optional[int] = None
    call_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    tpm_limit: Optional[int] = None
    used_tokens_input: Optional[int] = None
    used_tokens_output: Optional[int] = None
    used_calls: Optional[int] = None

class LLMConnectionTest(SQLModel):
    """
    Schema for testing an LLM connection.

    Attributes:
        provider: The provider name.
        model_name: The model name.
        api_base: Optional base URL for the API.
        api_key: API key.
    """
    provider: str
    model_name: str
    api_base: Optional[str] = None
    api_key: str
