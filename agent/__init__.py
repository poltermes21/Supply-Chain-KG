"""
agent/__init__.py
Public API for the supply chain ReAct agent.

Usage
-----
    from agent import run

    result = run("quines rutes tenen més retard?", session_id="user-123")
    print(result.answer)
    print(result.cypher_queries)   # for audit / debug
    print(result.iterations_used)
"""

from .graph import run
from .state import AgentInput, AgentOutput
from .memory import get_memory

__all__ = ["run", "AgentInput", "AgentOutput", "get_memory"]