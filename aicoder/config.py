"""Configuration management for the AI Coding Agent Framework.

Loads settings from environment variables and .env files.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv


def _find_dotenv() -> Optional[Path]:
    """Search upward from cwd for a .env file."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        dotenv_path = parent / ".env"
        if dotenv_path.exists():
            return dotenv_path
    return None


# Load .env at import time
_dotenv_path = _find_dotenv()
if _dotenv_path:
    load_dotenv(_dotenv_path)


@dataclass
class Config:
    """Framework configuration loaded from environment variables."""

    # LLM provider: openai, anthropic, ollama, gemini, deepseek, groq, together,
    #              fireworks, perplexity, xai, openrouter, openai_compatible
    provider: str = field(
        default_factory=lambda: os.getenv("AICODER_PROVIDER", "openai")
    )

    # Model name
    model: str = field(
        default_factory=lambda: os.getenv("AICODER_MODEL", "gpt-4o")
    )

    # API key — tries AICODER_API_KEY first, then provider-specific env vars
    api_key: Optional[str] = field(
        default_factory=lambda: (
            os.getenv("AICODER_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or os.getenv("TOGETHER_API_KEY")
            or os.getenv("FIREWORKS_API_KEY")
            or os.getenv("PERPLEXITY_API_KEY")
            or os.getenv("XAI_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("MOONSHOT_API_KEY")
            or os.getenv("ZHIPUAI_API_KEY")
        )
    )

    # API base URL (for custom endpoints / proxies / openai-compatible providers)
    api_base: Optional[str] = field(
        default_factory=lambda: os.getenv("AICODER_API_BASE")
    )

    # Ollama host (default: http://localhost:11434)
    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434")
    )

    # Workspace root directory
    workspace: Path = field(
        default_factory=lambda: Path(os.getenv("AICODER_WORKSPACE", str(Path.cwd())))
    )

    # Max tokens per LLM request
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("AICODER_MAX_TOKENS", "8000"))
    )

    # Maximum agent loop iterations
    max_iterations: int = field(
        default_factory=lambda: int(os.getenv("AICODER_MAX_ITERATIONS", "25"))
    )

    # Temperature for LLM calls
    temperature: float = field(
        default_factory=lambda: float(os.getenv("AICODER_TEMPERATURE", "0.2"))
    )

    @property
    def is_configured(self) -> bool:
        """Check if the config has the minimum required settings."""
        # Free / no-key providers
        no_key_providers = {"ollama", "openrouter"}  # OpenRouter free models don't need key
        if self.provider in no_key_providers:
            return True
        return self.api_key is not None


# Provider presets with default models and API bases
PROVIDER_INFO = {
    "openai": {"default_model": "gpt-4o", "api_base": None, "requires_key": True},
    "anthropic": {"default_model": "claude-3-5-sonnet-20241022", "api_base": None, "requires_key": True},
    "gemini": {"default_model": "gemini-2.5-flash", "api_base": None, "requires_key": True},
    "ollama": {"default_model": "codellama", "api_base": None, "requires_key": False},
    "deepseek": {"default_model": "deepseek-chat", "api_base": "https://api.deepseek.com/v1", "requires_key": True},
    "groq": {"default_model": "llama-3.3-70b-versatile", "api_base": "https://api.groq.com/openai/v1", "requires_key": True},
    "together": {"default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "api_base": "https://api.together.xyz/v1", "requires_key": True},
    "fireworks": {"default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct", "api_base": "https://api.fireworks.ai/inference/v1", "requires_key": True},
    "perplexity": {"default_model": "llama-3.1-sonar-large-128k-online", "api_base": "https://api.perplexity.ai", "requires_key": True},
    "xai": {"default_model": "grok-2-1212", "api_base": "https://api.x.ai/v1", "requires_key": True},
    "openrouter": {"default_model": "openai/gpt-4o", "api_base": "https://openrouter.ai/api/v1", "requires_key": False},
    "qwen": {"default_model": "qwen-plus", "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "requires_key": True},
    "kimi": {"default_model": "moonshot-v1-8k", "api_base": "https://api.moonshot.cn/v1", "requires_key": True},
    "glm": {"default_model": "glm-4-flash", "api_base": "https://open.bigmodel.cn/api/paas/v4", "requires_key": True},
    "openai_compatible": {"default_model": "gpt-4o", "api_base": None, "requires_key": True},
}


# Global config instance
config = Config()
