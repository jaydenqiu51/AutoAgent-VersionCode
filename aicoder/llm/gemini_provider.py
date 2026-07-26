"""Google Gemini provider — free tier available (15 RPM, 1500 RPD).

Models: gemini-2.5-flash (fast+free), gemini-2.5-pro (best quality)
Free tier: https://aistudio.google.com/apikey
"""

import json
from typing import Any, Dict, List, Optional

from ..config import config
from .base import BaseProvider, LLMResponse, Message, ToolCall, ToolResult


class GeminiProvider(BaseProvider):
    """LLM provider using Google's Gemini API.

    Free tier: 15 requests/minute, 1500 requests/day on gemini-2.5-flash.
    Get an API key at https://aistudio.google.com/apikey
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model or config.model or self.DEFAULT_MODEL
        self._api_key = api_key or config.api_key

    def _get_client(self):
        """Lazy import so the package is optional."""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "Google Gemini requires: pip install google-generativeai"
            )
        genai.configure(api_key=self._api_key)
        return genai

    def _convert_tools_for_gemini(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-style tool schemas to Gemini's format."""
        gemini_tools = []
        for tool in tools:
            declarations = {}
            if "function" in tool:
                func = tool["function"]
            else:
                func = tool

            declarations["name"] = func.get("name", "")
            declarations["description"] = func.get("description", "")
            declarations["parameters"] = func.get("parameters", {})

            gemini_tools.append(declarations)
        return gemini_tools

    def _convert_messages_for_gemini(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert our messages to Gemini's format."""
        contents = []
        system_parts = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            elif msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})

        return contents, "\n".join(system_parts) if system_parts else None

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[ToolResult]] = None,
    ) -> LLMResponse:
        genai = self._get_client()

        # Convert messages
        contents, system_instruction = self._convert_messages_for_gemini(messages)

        # Append tool results as user messages
        if tool_results:
            for tr in tool_results:
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"[Tool Result for '{tr.name}']\n{tr.result}"}],
                })

        # Build generation config
        generation_config = {
            "temperature": config.temperature,
            "max_output_tokens": config.max_tokens,
        }

        # Convert tools
        tool_config = None
        if tools:
            gemini_tools = self._convert_tools_for_gemini(tools)
            tool_config = {"function_calling_config": {"mode": "AUTO"}}

        # Create model
        model_kwargs = {
            "model_name": self.model,
            "generation_config": generation_config,
        }
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction
        if tool_config:
            model_kwargs["tools"] = [{"function_declarations": gemini_tools}] if gemini_tools else None

        model = genai.GenerativeModel(**{k: v for k, v in model_kwargs.items() if v is not None})

        # Generate
        try:
            response = model.generate_content(
                contents=contents,
                tools=[{"function_declarations": gemini_tools}] if tools and gemini_tools else None,
            )
        except Exception as e:
            return LLMResponse(content=f"Gemini API error: {e}")

        # Extract text and function calls
        text_content = ""
        tool_calls = []

        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.text:
                        text_content += part.text
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        args = {}
                        if fc.args:
                            args = dict(fc.args) if isinstance(fc.args, dict) else {}
                        tool_calls.append(ToolCall(
                            id=f"gemini_{len(tool_calls)}",
                            name=fc.name,
                            arguments=args,
                        ))

        return LLMResponse(
            content=text_content or None,
            tool_calls=tool_calls,
        )

    def supports_tools(self) -> bool:
        return True
