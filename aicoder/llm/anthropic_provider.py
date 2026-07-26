"""Anthropic (Claude) provider implementation."""

import json
from typing import Any, Dict, List, Optional

from anthropic import Anthropic

from ..config import config
from .base import BaseProvider, LLMResponse, Message, ToolCall, ToolResult


class AnthropicProvider(BaseProvider):
    """LLM provider using Anthropic's API (Claude 3.5 Sonnet, etc.)."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model or config.model
        self._client = Anthropic(
            api_key=api_key or config.api_key,
        )

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert our Message objects to Anthropic's format."""
        converted = []
        for msg in messages:
            converted.append({"role": msg.role, "content": msg.content})
        return converted

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[ToolResult]] = None,
    ) -> LLMResponse:
        # Anthropic requires system to be separate from messages
        system_content = ""
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        # Append tool results
        if tool_results:
            for tr in tool_results:
                api_messages.append({
                    "role": "user",
                    "content": f"Tool result for {tr.name}:\n{tr.result}",
                })

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }

        if system_content:
            params["system"] = system_content

        if tools:
            params["tools"] = tools

        response = self._client.messages.create(**params)

        # Extract content
        text_content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                ))

        return LLMResponse(
            content=text_content or None,
            tool_calls=tool_calls,
        )

    def supports_tools(self) -> bool:
        return True
