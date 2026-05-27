"""
Agent State Module

Defines the input and output state structures for the ReAct agent.
LangGraph manages internal message history, so only external interaction state is tracked.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional


class AgentInput(BaseModel):
    """What the caller passes in on every turn."""
    question: str
    session_id: str = "default"


class AgentOutput(BaseModel):
    """What the agent returns after each turn."""
    answer: str
    cypher_queries: list[str] = Field(default_factory=list)
    iterations_used: int = 0
    # Raw tool-call results parsed back into DataFrames (kept for downstream
    # visualisations). Stored as Any so this model stays Pydantic-friendly
    # without enabling arbitrary_types_allowed.
    tool_dataframes: list[Any] = Field(default_factory=list)
    # Pre-computed flag: True when at least one tool result is tabular enough
    # (≥2 rows AND ≥2 columns) to be worth offering a chart on.
    chartable: bool = False