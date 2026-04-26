"""
Shared state — passed through every LangGraph node.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class AgentState(BaseModel):
    # Input
    question: str
    chat_history: List[Dict] = Field(default_factory=list)
    
    # Intent
    intent: Optional[str] = None
    entities: List[str] = Field(default_factory=list)
    
    # Cypher generation
    cypher_query: Optional[str] = None
    generation_prompt: Optional[str] = None
    
    # Validation
    validation_ok: bool = True
    validation_error: Optional[str] = None
    
    # Execution
    raw_results: List[Dict] = Field(default_factory=list)
    execution_error: Optional[str] = None
    
    # Retry loop
    retry_count: int = 0
    retry_feedback: Optional[str] = None
    
    #Final answer
    answer: Optional[str] = None