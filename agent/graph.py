"""
agent/graph.py
LangGraph pipeline: NL → Cypher → Validate → Execute → Format
"""

from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    detect_intent,
    generate_query,
    validate_query,
    execute_query,
    regenerate_query,
    format_answer,
)

# ─────────────────────────────────────────────
# Routing logic
# ─────────────────────────────────────────────

def route_after_intent(state: AgentState) -> str:
    if state.intent == "chitchat":
        return "format"
    if state.is_followup:
        return "format"
    return "generate"

def route_after_validation(state: AgentState) -> str:
    if state.validation_ok:
        return "execute"
    if state.retry_count < 3:
        return "regenerate"
    return "format"


def route_after_execution(state: AgentState) -> str:
    if state.execution_error and state.retry_count < 3:
        return "regenerate"
    return "format"

# ─────────────────────────────────────────────
# Graph assembly
# ─────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("detect_intent",    detect_intent)
    g.add_node("generate_query",   generate_query)
    g.add_node("validate_query",   validate_query)
    g.add_node("execute_query",    execute_query)
    g.add_node("regenerate_query", regenerate_query)
    g.add_node("format_answer",    format_answer)

    g.set_entry_point("detect_intent")

    g.add_conditional_edges(
        "detect_intent",
        route_after_intent,
        {"format": "format_answer","generate": "generate_query"},
    )
    
    g.add_edge("generate_query", "validate_query")

    g.add_conditional_edges(
        "validate_query",
        route_after_validation,
        {"execute": "execute_query", "regenerate": "regenerate_query", "format": "format_answer"},
    )

    g.add_conditional_edges(
        "execute_query",
        route_after_execution,
        {"regenerate": "regenerate_query", "format": "format_answer"},
    )

    g.add_edge("regenerate_query", "validate_query")
    g.add_edge("format_answer", END)

    return g.compile()


# Singleton
kg_agent = build_graph()