"""
agent/memory.py
Simple in-process conversation memory.
Stored in st.session_state — no external DB needed for a single-user app.
"""

from dataclasses import dataclass, field
from typing import Optional


MAX_HISTORY = 20   # max messages kept in context


@dataclass
class ConversationMemory:
    messages: list[dict] = field(default_factory=list)

    # Public API
    def add_user(self, content: str) -> None:
        self._append("user", content)

    def add_assistant(self, content: str, cypher: Optional[str] = None) -> None:
        self._append("assistant", content, cypher=cypher)

    def get_history(self) -> list[dict]:
        """Return the last MAX_HISTORY messages for the LLM context window."""
        return self.messages[-MAX_HISTORY:]

    def clear(self) -> None:
        self.messages.clear()

    # Internal
    def _append(self, role: str, content: str, **meta) -> None:
        entry = {"role": role, "content": content}
        entry.update(meta)
        self.messages.append(entry)