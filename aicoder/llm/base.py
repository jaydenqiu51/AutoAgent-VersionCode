"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Message:
    """Represents a chat message."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class ToolCall:
    """Represents a tool call requested by the LLM."""

    def __init__(self, id: str, name: str, arguments: Dict[str, Any]):
        self.id = id
        self.name = name
        self.arguments = arguments


class ToolResult:
    """Represents the result of executing a tool."""

    def __init__(self, tool_call_id: str, name: str, result: str):
        self.tool_call_id = tool_call_id
        self.name = name
        self.result = result


class LLMResponse:
    """Response from an LLM provider."""

    def __init__(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
    ):
        self.content = content
        self.tool_calls = tool_calls or []

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[ToolResult]] = None,
    ) -> LLMResponse:
        """Send a chat request and return the response.

        Args:
            messages: Conversation history.
            tools: JSON schema definitions for available tools.
            tool_results: Results from previously executed tool calls.

        Returns:
            LLMResponse with optional text content and/or tool calls.
        """
        ...

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports native function/tool calling."""
        ...
