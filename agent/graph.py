"""
ReAct Agent Module

Main entry point of the ReAct agent. Orchestrates the full reasoning pipeline:
chitchat fast-path, history-based answering, and tool-augmented Cypher reasoning
via a LangGraph ReAct loop.
"""

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from .llm import get_interface_llm, get_reasoning_llm
from .memory import get_memory
from .prompts import CHITCHAT_CLASSIFIER_SYSTEM, CHITCHAT_SYSTEM, REACT_SYSTEM
from .state import AgentInput, AgentOutput
from .tools import query_graph, answer_from_context

# ─────────────────────────────────────────────────────────────────────────────
# Build the ReAct agent (singleton — compiled once at import time)
# ─────────────────────────────────────────────────────────────────────────────

_TOOLS = [query_graph, answer_from_context]

_react_agent = create_react_agent(
    model=get_reasoning_llm(temperature=0),
    tools=_TOOLS,
    # LangGraph's prebuilt ReAct respects this as the agent's system prompt
    prompt=SystemMessage(content=REACT_SYSTEM)
)

# ─────────────────────────────────────────────────────────────────────────────
# Chitchat fast-path helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_chitchat(question: str) -> bool:
    """Single cheap LLM call — returns True if the message is small talk."""
    llm = get_interface_llm(temperature=0)
    reply = llm.invoke([
        SystemMessage(content=CHITCHAT_CLASSIFIER_SYSTEM),
        HumanMessage(content=question),
    ])
    return reply.content.strip().lower().startswith("chitchat")


def _chitchat_response(question: str) -> str:
    """Generate a warm, structured chitchat reply (no tools, no Neo4j)."""
    llm = get_interface_llm(temperature=0.7)
    reply = llm.invoke([
        SystemMessage(content=CHITCHAT_SYSTEM),
        HumanMessage(content=question),
    ])
    return reply.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Answer from history helpers
# ─────────────────────────────────────────────────────────────────────────────

def _can_answer_from_history(question: str, history: str) -> bool:
    """Flash decideix si l'historial conté la resposta. Cost: ~100 tokens."""
    llm = get_interface_llm(temperature=0)
    reply = llm.invoke([
        SystemMessage(content=(
            "Does the conversation history contain enough data to answer "
            "the question directly, without querying a database?\n"
            "Reply ONLY with 'yes' or 'no'."
        )),
        HumanMessage(content=f"History:\n{history}\n\nQuestion: {question}"),
    ])
    return reply.content.strip().lower().startswith("yes")

def _answer_with_flash(question: str, history: str) -> str:
    """Flash respon usant l'historial. Cost: ~200-300 tokens, ~1s."""
    llm = get_interface_llm(temperature=0.3)
    reply = llm.invoke([
        SystemMessage(content=(
            "Answer the question using ONLY the data in the conversation history. "
            "Respond in the SAME LANGUAGE as the question. "
            "Do not invent any data not present in the history."
        )),
        HumanMessage(content=f"History:\n{history}\n\nQuestion: {question}"),
    ])
    return reply.content.strip()

# ─────────────────────────────────────────────────────────────────────────────
# Agent ReAct helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_final_answer(messages: list, question: str) -> str:
    """Return the content of the last AIMessage that is a plain text response."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            # Skip messages that are purely tool-call requests (content = "")
            if isinstance(msg.content, str) and msg.content.strip():
                return msg.content.strip()
            if isinstance(msg.content, list):
                # Gemini sometimes returns content as a list of parts
                text_parts = [p["text"] for p in msg.content if p.get("type") == "text"]
                if text_parts:
                    return " ".join(text_parts).strip()

    llm = get_interface_llm(temperature=0)
    reply = llm.invoke([
        SystemMessage(content="The agent could not retrieve data. Inform the user briefly in the SAME LANGUAGE as their question. Be concise."),
        HumanMessage(content=question),
    ])
    return reply.content.strip()


def _extract_cypher_queries(messages: list) -> list[str]:
    """
    Extract all Cypher strings passed to query_graph and get_entity_details.
    """
    import json
    from langchain_core.messages import AIMessage

    queries = []
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        tool_calls = getattr(msg, "tool_calls", []) or []
        for tc in tool_calls:
            if tc.get("name") in ("query_graph", "get_entity_details"):
                args = tc.get("args", {})
                cypher = args.get("cypher") or args.get("entity_id", "")
                if cypher:
                    queries.append(cypher)
    return queries


def _count_tool_calls(messages: list) -> int:
    """Count how many tool calls were made in this turn."""
    from langchain_core.messages import AIMessage
    count = 0
    for msg in messages:
        if isinstance(msg, AIMessage):
            count += len(getattr(msg, "tool_calls", []) or [])
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Public run() function
# ─────────────────────────────────────────────────────────────────────────────

def run(question: str, session_id: str = "default") -> AgentOutput:
    """
    Process one conversational turn and return an AgentOutput.

    Parameters
    ----------
    question   : the user's natural-language question.
    session_id : conversation identifier (use st.session_state key in Streamlit).

    Returns
    -------
    AgentOutput with .answer (str) and .cypher_queries (list[str]).
    """
    memory = get_memory(session_id)

    # 1. Chitchat fast-path
    if _is_chitchat(question):
        answer = _chitchat_response(question)
        memory.add_turn(question, answer)
        return AgentOutput(answer=answer)

    # 2. Build message list: history as explicit text + current question
    history_str = ""
    history_msgs = memory.get_messages()
    if history_msgs:
        lines = []
        for msg in history_msgs:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            lines.append(f"{role}: {msg.content}")
        history_str = "\n".join(lines)
        
    # 3. Answer from context fast-path
    if history_str and _can_answer_from_history(question, history_str):
        answer = _answer_with_flash(question, history_str)
        memory.add_turn(question, answer)
        return AgentOutput(answer=answer)

    # Inject history inside  HumanMessage
    if history_str:
        full_question = (
            f"## Conversation history\n{history_str}\n\n"
            f"## Current question\n{question}"
        )
    else:
        full_question = question

    # 4. Run ReAct loop
    result = _react_agent.invoke(
        {"messages": [HumanMessage(content=full_question)]},
        config={"recursion_limit": 13},
    )

    # 4. Extract final answer and any Cypher queries used
    # The last AIMessage in the result that is NOT a tool call is the final answer.
    final_answer = _extract_final_answer(result["messages"], question)
    cypher_queries = _extract_cypher_queries(result["messages"])
    iterations = _count_tool_calls(result["messages"])

    # ── 5. Persist turn to memory ─────────────────────────────────────────────
    memory.add_turn(question, final_answer)

    return AgentOutput(
        answer=final_answer,
        cypher_queries=cypher_queries,
        iterations_used=iterations,
    )