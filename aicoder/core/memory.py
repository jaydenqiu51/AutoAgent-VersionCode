"""Conversation memory with sliding window management."""

from typing import List, Optional

from ..llm.base import Message, ToolCall, ToolResult


class Memory:
    """Manages conversation history for the agent.

    Uses a sliding window approach: keeps the most recent N messages
    in full, with older messages summarized to conserve tokens.
    """

    def __init__(self, max_messages: int = 50):
        self._messages: List[Message] = []
        self._max_messages = max_messages

    @property
    def messages(self) -> List[Message]:
        return self._messages

    def add_system(self, content: str) -> None:
        """Add or replace the system message."""
        # Remove existing system message
        self._messages = [m for m in self._messages if m.role != "system"]
        # Insert at beginning
        self._messages.insert(0, Message(role="system", content=content))

    def add_user(self, content: str) -> None:
        self._messages.append(Message(role="user", content=content))
        self._trim()

    def add_assistant(self, content: str, tool_calls: Optional[List[ToolCall]] = None) -> None:
        text = content or ""
        if tool_calls:
            text += "\n[Tool calls: " + ", ".join(tc.name for tc in tool_calls) + "]"
        self._messages.append(Message(role="assistant", content=text))
        self._trim()

    def add_tool_results(self, results: List[ToolResult]) -> None:
        parts = []
        for tr in results:
            parts.append(f"[Result from {tr.name}]\n{tr.result}")
        self._messages.append(Message(role="user", content="\n\n".join(parts)))
        self._trim()

    def get_history(self) -> List[Message]:
        return list(self._messages)

    def clear(self) -> None:
        """Clear all messages except the system prompt."""
        system_msgs = [m for m in self._messages if m.role == "system"]
        self._messages = system_msgs

    def _trim(self) -> None:
        """Trim old messages if exceeding max, preserving system prompt."""
        system_msgs = [m for m in self._messages if m.role == "system"]
        non_system = [m for m in self._messages if m.role != "system"]

        if len(non_system) > self._max_messages:
            # Keep the most recent messages
            non_system = non_system[-self._max_messages:]

        self._messages = system_msgs + non_system
