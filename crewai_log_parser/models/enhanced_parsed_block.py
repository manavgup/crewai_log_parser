from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class TokenUsage(BaseModel):
    """Model for token usage statistics"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

class EnhancedParsedBlock(BaseModel):
    """Enhanced parsed block with task awareness"""
    # Original fields
    task_hint: str
    litellm_request: str
    raw_response: str
    thought: Optional[str] = None
    action: Optional[str] = None
    final_answer: Optional[str] = None
    parsed_usage: Optional[TokenUsage] = None
    parsing_error: bool = False
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    model: Optional[str] = None
    api_errors: List[str] = Field(default_factory=list)

    # New fields for task awareness
    task_id: Optional[str] = None  # Mapped from tasks.yaml
    agent_id: Optional[str] = None  # Mapped from agents.yaml
    expected_output_format: Optional[str] = None  # From task definition
    dependencies: List[str] = Field(default_factory=list)  # Task dependencies

    # Enhanced tool tracking
    tool_used: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    tool_success: Optional[bool] = None
