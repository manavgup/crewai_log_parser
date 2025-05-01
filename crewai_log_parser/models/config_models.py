from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class CrewAITask(BaseModel):
    """Model representing a CrewAI task definition"""
    task_id: str
    description: str
    expected_output: str
    agent: str
    dependencies: List[str] = Field(default_factory=list)

class CrewAIAgent(BaseModel):
    """Model representing a CrewAI agent definition"""
    role: str
    goal: str
    backstory: str
    allow_delegation: bool
    verbose: bool
