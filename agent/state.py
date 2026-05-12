"""
Agent State Module

Defines the input and output state structures for the ReAct agent.
LangGraph manages internal message history, so only external interaction state is tracked.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AgentInput(BaseModel):
    """What the caller passes in on every turn."""
    question: str
    session_id: str = "default"


class AgentOutput(BaseModel):
    """What the agent returns after each turn."""
    answer: str
    cypher_queries: list[str] = Field(default_factory=list)
    iterations_used: int = 0