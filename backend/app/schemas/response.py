
from pydantic import BaseModel
from typing import TypeVar, Generic, Optional

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """
    Generic API Response wrapper.

    Attributes:
        status: The status of the response (default: "success").
        data: The payload data (optional).
        message: Optional message (e.g., error message or success details).
    """
    status: str = "success"
    data: Optional[T] = None
    message: Optional[str] = None
