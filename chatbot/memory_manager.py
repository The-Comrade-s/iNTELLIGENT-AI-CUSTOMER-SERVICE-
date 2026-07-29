"""
chatbot/memory_manager.py

Tracks short-term conversational context: the customer's name (once
mentioned), the current topic, and the last few exchanges, so
response_generator.py can produce context-aware replies instead of
treating every message in isolation.

Memory lives in Streamlit's session_state (keyed per conversation_id)
rather than the database -- it's working memory for the current
session, not an audit record. The full transcript is still persisted
via database.Message for history/analytics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_MAX_RECENT_TURNS = 6


@dataclass
class ConversationMemory:
    conversation_id: int
    customer_name: str | None = None
    current_topic: str | None = None
    recent_turns: list[tuple[str, str]] = field(default_factory=list)  # (role, text)

    def remember_turn(self, role: str, text: str) -> None:
        self.recent_turns.append((role, text))
        if len(self.recent_turns) > _MAX_RECENT_TURNS:
            self.recent_turns = self.recent_turns[-_MAX_RECENT_TURNS:]

    def set_topic(self, topic: str) -> None:
        self.current_topic = topic

    def context_summary(self) -> str:
        """A short human-readable summary of what's been discussed,
        used to prime response generation for context awareness."""

        parts = []
        if self.customer_name:
            parts.append(f"Customer name: {self.customer_name}.")
        if self.current_topic:
            parts.append(f"Current topic: {self.current_topic}.")
        if self.recent_turns:
            last_customer_msgs = [t for r, t in self.recent_turns if r == "customer"][-2:]
            if last_customer_msgs:
                parts.append("Recently asked about: " + "; ".join(last_customer_msgs))
        return " ".join(parts)

    def reset(self) -> None:
        self.customer_name = None
        self.current_topic = None
        self.recent_turns = []


class MemoryStore:
    """In-process registry of ConversationMemory objects, one per
    active conversation_id within this Streamlit session."""

    def __init__(self) -> None:
        self._memories: dict[int, ConversationMemory] = {}

    def get(self, conversation_id: int) -> ConversationMemory:
        if conversation_id not in self._memories:
            self._memories[conversation_id] = ConversationMemory(conversation_id=conversation_id)
        return self._memories[conversation_id]

    def reset(self, conversation_id: int) -> None:
        self._memories.pop(conversation_id, None)
