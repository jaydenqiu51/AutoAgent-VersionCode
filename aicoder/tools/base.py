"""Abstract base class for tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """A tool that the AI agent can invoke.

    Each tool must define:
    - name: unique identifier used in function calling
    - description: what the tool does
    - parameters: JSON Schema for the tool's arguments
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema for the tool's parameters."""
        ...

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with the given arguments.

        Returns a string result to feed back to the LLM.
        """
        ...

    def to_schema(self) -> Dict[str, Any]:
        """Return the OpenAI-compatible function schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
