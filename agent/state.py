"""
agent/state.py
Minimal state for the ReAct agent.
The LangGraph prebuilt ReAct agent manages its own message list internally —
we only need to track what lives outside that loop.
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