"""
agent/memory.py
In-process conversation memory, keyed by session_id.
For a single-user Streamlit app one session is enough;
for multi-session keep the dict across requests.

Design decisions:
- MAX_TURNS = 5  → 10 messages max injected into the LLM context.
  At ~500 tokens/turn this is ~5k tokens of history — manageable.
- We store the raw LangChain message format (HumanMessage / AIMessage)
  so they can be passed directly to the ReAct agent's message history.
"""

from collections import deque
from langchain_core.messages import HumanMessage, AIMessage

MAX_TURNS = 5   # user+assistant pairs kept in context


class ConversationMemory:
    def __init__(self):
        # deque of (HumanMessage, AIMessage) pairs
        self._turns: deque[tuple] = deque(maxlen=MAX_TURNS)

    def add_turn(self, question: str, answer: str) -> None:
        self._turns.append((HumanMessage(content=question), AIMessage(content=answer)))

    def get_messages(self) -> list:
        """Flat list of HumanMessage / AIMessage ready for LangChain."""
        msgs = []
        for human, ai in self._turns:
            msgs.append(human)
            msgs.append(ai)
        return msgs

    def clear(self) -> None:
        self._turns.clear()


# Global registry keyed by session_id
_sessions: dict[str, ConversationMemory] = {}


def get_memory(session_id: str = "default") -> ConversationMemory:
    if session_id not in _sessions:
        _sessions[session_id] = ConversationMemory()
    return _sessions[session_id]