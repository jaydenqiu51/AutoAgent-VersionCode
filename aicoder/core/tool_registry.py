"""Tool registry for discovering and managing available tools."""

from typing import Any, Dict, List, Optional

from ..tools.base import BaseTool


class ToolRegistry:
    """Manages the set of tools available to the agent."""

    def __init__(self, tools: Optional[List[BaseTool]] = None):
        self._tools: Dict[str, BaseTool] = {}
        if tools:
            for tool in tools:
                self.register(tool)

    def register(self, tool: BaseTool) -> None:
        """Register a tool with the registry."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return the OpenAI-compatible function schemas for all tools."""
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name with the given arguments.

        Returns the tool's result string, or an error message.
        """
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: Unknown tool '{name}'. Available tools: {list(self._tools.keys())}"

        try:
            return tool.execute(**arguments)
        except Exception as e:
            return f"Error executing tool '{name}': {e}"
