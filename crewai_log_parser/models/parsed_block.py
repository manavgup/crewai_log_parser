from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ParsedBlock(BaseModel):
    """
    Represents a parsed block from a CrewAI log file.
    
    This model contains the raw request and response data, as well as
    extracted information such as thoughts, actions, and token usage.
    """
    task_hint: str
    litellm_request: str
    raw_response: str
    thought: Optional[str] = None
    action: Optional[str] = None
    final_answer: Optional[str] = None
    parsed_usage: Dict[str, Any] = Field(default_factory=dict)
    parsing_error: bool = False
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    model: Optional[str] = None
    api_errors: List[str] = Field(default_factory=list)
