"""Ollama provider for local models."""

import json
import re
from typing import Any, Dict, List, Optional

import requests

from ..config import config
from .base import BaseProvider, LLMResponse, Message, ToolCall, ToolResult


class OllamaProvider(BaseProvider):
    """LLM provider using Ollama for local models (CodeLlama, etc.).

    Since Ollama doesn't natively support function calling, this provider
    uses a prompt-based approach: tools are described in the system prompt,
    and the model responds with a JSON block to invoke a tool.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.model = model or config.model
        self.host = host or config.ollama_host
        self._tools_prompt = ""

    def _build_tools_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """Build a description of available tools for the system prompt."""
        if not tools:
            return ""

        lines = [
            "",
            "## Available Tools",
            "You have access to the following tools. To use a tool, respond with a JSON block:",
            "",
            "```tool",
            "{",
            '  "tool": "tool_name",',
            '  "arguments": { ... }',
            "}",
            "```",
            "",
        ]

        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "No description.")
            params = tool.get("parameters", {})
            lines.append(f"- **{name}**: {desc}")
            if params.get("properties"):
                lines.append("  Parameters:")
                for prop_name, prop_info in params["properties"].items():
                    prop_desc = prop_info.get("description", "")
                    lines.append(f"    - `{prop_name}`: {prop_desc}")

        lines.append("")
        return "\n".join(lines)

    def _parse_tool_calls(self, content: str) -> tuple:
        """Parse tool invocation JSON blocks from the model's response.

        Returns (remaining_text, tool_calls).
        """
        tool_pattern = r"```tool\s*\n(.*?)\n```"
        matches = list(re.finditer(tool_pattern, content, re.DOTALL))

        if not matches:
            return content, []

        tool_calls = []
        remaining = content

        for i, match in enumerate(matches):
            try:
                tool_data = json.loads(match.group(1))
                tool_calls.append(ToolCall(
                    id=f"call_{i}",
                    name=tool_data.get("tool", "unknown"),
                    arguments=tool_data.get("arguments", {}),
                ))
                remaining = remaining.replace(match.group(0), "")
            except json.JSONDecodeError:
                pass

        return remaining.strip(), tool_calls

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[ToolResult]] = None,
    ) -> LLMResponse:
        # Build the system prompt with tool descriptions
        system_prompt = self._build_tools_prompt(tools or [])

        # Convert messages to Ollama format
        api_messages: List[Dict[str, str]] = []

        for msg in messages:
            if msg.role == "system":
                api_messages.append({
                    "role": "system",
                    "content": msg.content + system_prompt,
                })
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        # Append tool results
        if tool_results:
            for tr in tool_results:
                api_messages.append({
                    "role": "user",
                    "content": f"[Tool Result for '{tr.name}']\n{tr.result}\n\nContinue with the task.",
                })

        # Make the request
        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": api_messages,
                    "stream": False,
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")
        except requests.RequestException as e:
            return LLMResponse(content=f"Error calling Ollama: {e}")

        # Parse tool calls from content
        remaining_text, tool_calls = self._parse_tool_calls(content)

        return LLMResponse(
            content=remaining_text or None,
            tool_calls=tool_calls,
        )

    def supports_tools(self) -> bool:
        # Ollama uses prompt-based tool calling, not native
        return True
