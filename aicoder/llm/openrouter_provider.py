"""OpenRouter provider — unified API accessing 100+ models.

OpenRouter gives you a single API key that works with models from:
OpenAI, Anthropic, Google, Meta, DeepSeek, Mistral, Qwen, and many more.

Includes free models: google/gemma-3-27b-it:free, meta-llama/llama-3.2-3b-instruct:free
Pricing: pay-per-token, many models under $0.50/M tokens.
"""

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..config import config
from .base import BaseProvider, LLMResponse, Message, ToolCall, ToolResult

# Curated list of recommended models on OpenRouter with their strengths
OPENROUTER_MODELS = {
    "openai/gpt-4o": {"strength": "Best overall coding", "cost": "$5.00/M input"},
    "anthropic/claude-3.5-sonnet": {"strength": "Strong coding, large context", "cost": "$3.00/M input"},
    "google/gemini-2.5-flash": {"strength": "Fast, free tier available", "cost": "$0.15/M input"},
    "deepseek/deepseek-chat": {"strength": "Cheapest strong coder", "cost": "$0.14/M input"},
    "meta-llama/llama-3.3-70b-instruct": {"strength": "Open model, solid coding", "cost": "$0.23/M input"},
    "qwen/qwen-2.5-72b-instruct": {"strength": "Top open coding model", "cost": "$0.40/M input"},
    "mistralai/mistral-large": {"strength": "European, strong multilingual", "cost": "$2.00/M input"},
    "google/gemma-3-27b-it:free": {"strength": "Completely free, decent quality", "cost": "FREE"},
}

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


class OpenRouterProvider(BaseProvider):
    """LLM provider using OpenRouter's unified API.

    One API key for 100+ models from all major providers.
    Free models available without any payment.

    Get a key at https://openrouter.ai/keys
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model or config.model or "openai/gpt-4o"
        self._client = OpenAI(
            api_key=api_key or config.api_key,
            base_url=OPENROUTER_BASE,
        )

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[ToolResult]] = None,
    ) -> LLMResponse:
        api_messages: List[Dict[str, Any]] = []

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        if tool_results:
            for tr in tool_results:
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": tr.tool_call_id,
                    "content": tr.result,
                })

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

        # OpenRouter-specific headers for optional features
        extra_headers = {
            "HTTP-Referer": "https://github.com/jaydenqiu51/Ai-Coding-Agent-Framework",
            "X-Title": "AICoder Framework",
        }

        response = self._client.chat.completions.create(
            **params,
            extra_headers=extra_headers,
        )
        choice = response.choices[0].message

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
