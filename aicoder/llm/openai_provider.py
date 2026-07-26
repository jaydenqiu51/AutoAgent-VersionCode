"""OpenAI provider implementation."""

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..config import config
from .base import BaseProvider, LLMResponse, Message, ToolCall, ToolResult


class OpenAIProvider(BaseProvider):
    """LLM provider using OpenAI's API (GPT-4o, GPT-4, etc.)."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.model = model or config.model
        self._client = OpenAI(
            api_key=api_key or config.api_key,
            base_url=api_base or config.api_base,
        )

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[ToolResult]] = None,
    ) -> LLMResponse:
        # Build message list
        api_messages: List[Dict[str, Any]] = []

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        # Append tool results as tool-role messages
        if tool_results:
            for tr in tool_results:
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": tr.tool_call_id,
                    "content": tr.result,
                })

        # Prepare API params
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }

        if tools:
            params["tools"] = [
                {"type": "function", "function": t} for t in tools
            ]

        response = self._client.chat.completions.create(**params)
        choice = response.choices[0].message

        # Extract tool calls
        tool_calls = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))

        return LLMResponse(
            content=choice.content,
            tool_calls=tool_calls,
        )

    def supports_tools(self) -> bool:
        return True
