"""OpenAI-compatible provider — works with any API that speaks the OpenAI chat format.

Supported services (set api_base accordingly):
- DeepSeek:     https://api.deepseek.com/v1
- Groq:         https://api.groq.com/openai/v1
- Together AI:  https://api.together.xyz/v1
- Fireworks:    https://api.fireworks.ai/inference/v1
- Perplexity:   https://api.perplexity.ai
- xAI (Grok):   https://api.x.ai/v1
- Any local proxy (LiteLLM, vLLM, etc.)
"""

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..config import config
from .base import BaseProvider, LLMResponse, Message, ToolCall, ToolResult

# Preset configurations for popular providers
PROVIDER_PRESETS = {
    "deepseek": {
        "name": "DeepSeek",
        "api_base": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "pricing": "~$0.14/M input tokens — extremely cheap",
    },
    "groq": {
        "name": "Groq",
        "api_base": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "pricing": "Free tier available, fast inference",
    },
    "together": {
        "name": "Together AI",
        "api_base": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
        "pricing": "~$0.90/M tokens, free credits for new users",
    },
    "fireworks": {
        "name": "Fireworks AI",
        "api_base": "https://api.fireworks.ai/inference/v1",
        "default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "env_key": "FIREWORKS_API_KEY",
        "pricing": "~$0.90/M tokens",
    },
    "perplexity": {
        "name": "Perplexity",
        "api_base": "https://api.perplexity.ai",
        "default_model": "llama-3.1-sonar-large-128k-online",
        "env_key": "PERPLEXITY_API_KEY",
        "pricing": "~$1.00/M tokens, includes web search",
    },
    "xai": {
        "name": "xAI (Grok)",
        "api_base": "https://api.x.ai/v1",
        "default_model": "grok-2-1212",
        "env_key": "XAI_API_KEY",
        "pricing": "~$2.00/M tokens",
    },
}


class OpenAICompatibleProvider(BaseProvider):
    """Generic provider for any OpenAI-compatible API endpoint.

    Works with DeepSeek, Groq, Together AI, Fireworks, Perplexity, xAI,
    and any self-hosted endpoint (LiteLLM, vLLM, Ollama with OpenAI compat, etc.).
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.model = model or config.model
        self.api_base = api_base or config.api_base
        self._client = OpenAI(
            api_key=api_key or config.api_key,
            base_url=self.api_base,
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

        response = self._client.chat.completions.create(**params)
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
