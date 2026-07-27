"""Auto-update the README pricing table with live per-1M-token prices.

Runs on a GitHub Actions schedule (every 2 hours). Fetches live model
pricing from OpenRouter's public catalog API (no key needed) and rewrites
the table between <!-- PRICING:START --> and <!-- PRICING:END -->.

If the API is unreachable or a model is missing, the previous (fallback)
price is kept so the table never breaks.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"
API = "https://openrouter.ai/api/v1/models"

# Each row: (provider, model shown, price spec, key info, link)
# price spec: ("live", openrouter_id, fallback) or ("static", text)
ROWS = [
    ("**Ollama**", "codellama, llama3, etc.",
     ("static", "**$0 — completely FREE**"),
     "❌ **No key needed**", "[ollama.com](https://ollama.com) — just install it"),
    ("**Google Gemini**", "gemini-2.5-flash",
     ("live_prefix", "google/gemini-2.5-flash", "**FREE tier** (paid: $0.30 / $2.50)", "**FREE tier** (paid: {})"),
     "Free key", "[aistudio.google.com](https://aistudio.google.com/apikey)"),
    ("**Groq**", "llama-3.3-70b-versatile",
     ("static", "**FREE tier** (paid: $0.59 / $0.79)"),
     "Free key", "[console.groq.com](https://console.groq.com)"),
    ("**GLM (Zhipu AI)**", "glm-4-flash",
     ("static", "**FREE**"),
     "Free key", "[open.bigmodel.cn](https://open.bigmodel.cn)"),
    ("**OpenRouter**", "100+ models, many `:free`",
     ("static", "**FREE** (`:free` models) and up"),
     "Free key", "[openrouter.ai/keys](https://openrouter.ai/keys)"),
    ("**DeepSeek**", "deepseek-chat",
     ("live", "deepseek/deepseek-chat-v3-0324", "$0.27 / $1.10"),
     "Paid key", "[platform.deepseek.com](https://platform.deepseek.com)"),
    ("**Qwen (Alibaba)**", "qwen-plus",
     ("live", "qwen/qwen-plus", "$0.40 / $1.20"),
     "Paid key", "[dashscope.aliyun.com](https://dashscope.console.aliyun.com)"),
    ("**Kimi (Moonshot)**", "kimi-k3",
     ("live", "moonshotai/kimi-k3", "$3.00 / $15.00"),
     "Paid key", "[platform.moonshot.cn](https://platform.moonshot.cn)"),
    ("", "kimi-k2.7-code",
     ("live", "moonshotai/kimi-k2.7-code", "$0.73 / $3.50"), "", ""),
    ("**Together AI**", "Llama 3.3 70B Turbo",
     ("static", "$0.88 / $0.88 (+ free models)"),
     "Key (has free models)", "[together.ai](https://together.ai)"),
    ("**Fireworks**", "Llama 3.3 70B",
     ("static", "$0.90 / $0.90"),
     "Paid key", "[fireworks.ai](https://fireworks.ai)"),
    ("**OpenAI**", "gpt-4o",
     ("live", "openai/gpt-4o", "$2.50 / $10.00"),
     "Paid key", "[platform.openai.com](https://platform.openai.com)"),
    ("", "gpt-4o-mini",
     ("live", "openai/gpt-4o-mini", "$0.15 / $0.60"), "", ""),
    ("", "gpt-4.1",
     ("live", "openai/gpt-4.1", "$2.00 / $8.00"), "", ""),
    ("**Anthropic**", "claude-sonnet-4",
     ("live", "anthropic/claude-sonnet-4", "$3.00 / $15.00"),
     "Paid key", "[console.anthropic.com](https://console.anthropic.com)"),
    ("", "claude-opus-4",
     ("live", "anthropic/claude-opus-4", "$15.00 / $75.00"), "", ""),
    ("", "claude-3-5-haiku",
     ("live", "anthropic/claude-3.5-haiku", "$0.80 / $4.00"), "", ""),
    ("**Perplexity**", "sonar-pro",
     ("live_suffix", "perplexity/sonar-pro", "$3.00 / $15.00 (+ search fees)", "{} (+ search fees)"),
     "Paid key", "[perplexity.ai](https://docs.perplexity.ai)"),
    ("**xAI (Grok)**", "grok-3",
     ("live", "x-ai/grok-3", "$3.00 / $15.00"),
     "Paid key", "[x.ai/api](https://x.ai/api)"),
]

# ── FULL MODEL CATALOG ── mirrors MODEL_CATALOG in aicoder/gui.py.
# (provider, model shown, openrouter id for live price or None, tag)
# tag: "free" = no key needed · "freetier" = free with free key · None = paid
FULL_CATALOG = [
    ("OpenAI", "gpt-4o", "openai/gpt-4o", None),
    ("OpenAI", "gpt-4o-mini", "openai/gpt-4o-mini", None),
    ("OpenAI", "chatgpt-4o-latest", "openai/chatgpt-4o-latest", None),
    ("OpenAI", "gpt-4.1", "openai/gpt-4.1", None),
    ("OpenAI", "gpt-4.1-mini", "openai/gpt-4.1-mini", None),
    ("OpenAI", "gpt-4.1-nano", "openai/gpt-4.1-nano", None),
    ("OpenAI", "gpt-4.5-preview", "openai/gpt-4.5-preview", None),
    ("OpenAI", "gpt-4-turbo", "openai/gpt-4-turbo", None),
    ("OpenAI", "gpt-4", "openai/gpt-4", None),
    ("OpenAI", "gpt-3.5-turbo", "openai/gpt-3.5-turbo", None),
    ("OpenAI", "o1", "openai/o1", None),
    ("OpenAI", "o1-mini", "openai/o1-mini", None),
    ("OpenAI", "o1-pro", "openai/o1-pro", None),
    ("OpenAI", "o3", "openai/o3", None),
    ("OpenAI", "o3-pro", "openai/o3-pro", None),
    ("OpenAI", "o3-mini", "openai/o3-mini", None),
    ("OpenAI", "o4-mini", "openai/o4-mini", None),
    ("Anthropic", "claude-opus-4", "anthropic/claude-opus-4", None),
    ("Anthropic", "claude-sonnet-4", "anthropic/claude-sonnet-4", None),
    ("Anthropic", "claude-3-7-sonnet", "anthropic/claude-3.7-sonnet", None),
    ("Anthropic", "claude-3-5-sonnet", "anthropic/claude-3.5-sonnet", None),
    ("Anthropic", "claude-3-5-sonnet-20240620", "anthropic/claude-3.5-sonnet-20240620", None),
    ("Anthropic", "claude-3-5-haiku", "anthropic/claude-3.5-haiku", None),
    ("Anthropic", "claude-3-opus", "anthropic/claude-3-opus", None),
    ("Anthropic", "claude-3-sonnet", "anthropic/claude-3-sonnet", None),
    ("Anthropic", "claude-3-haiku", "anthropic/claude-3-haiku", None),
    ("Google Gemini", "gemini-2.5-flash", "google/gemini-2.5-flash", "freetier"),
    ("Google Gemini", "gemini-2.5-flash-lite", "google/gemini-2.5-flash-lite", "freetier"),
    ("Google Gemini", "gemini-2.0-flash", "google/gemini-2.0-flash-001", "freetier"),
    ("Google Gemini", "gemini-2.0-flash-lite", "google/gemini-2.0-flash-lite-001", "freetier"),
    ("Google Gemini", "gemini-2.0-flash-thinking-exp", None, "freetier"),
    ("Google Gemini", "gemini-1.5-flash", "google/gemini-flash-1.5", "freetier"),
    ("Google Gemini", "gemini-1.5-flash-8b", "google/gemini-flash-1.5-8b", "freetier"),
    ("Google Gemini", "gemma-3-27b-it", "google/gemma-3-27b-it", "freetier"),
    ("Google Gemini", "gemini-2.5-pro", "google/gemini-2.5-pro", None),
    ("Google Gemini", "gemini-1.5-pro", "google/gemini-pro-1.5", None),
    ("Ollama (local)", "llama3.3", None, "free"),
    ("Ollama (local)", "llama3.2", None, "free"),
    ("Ollama (local)", "llama3.2-vision", None, "free"),
    ("Ollama (local)", "llama3.1", None, "free"),
    ("Ollama (local)", "llama3", None, "free"),
    ("Ollama (local)", "llama2", None, "free"),
    ("Ollama (local)", "codellama", None, "free"),
    ("Ollama (local)", "qwen3", None, "free"),
    ("Ollama (local)", "qwen2.5", None, "free"),
    ("Ollama (local)", "qwen2.5-coder", None, "free"),
    ("Ollama (local)", "qwq", None, "free"),
    ("Ollama (local)", "deepseek-r1", None, "free"),
    ("Ollama (local)", "deepseek-coder-v2", None, "free"),
    ("Ollama (local)", "deepseek-v3", None, "free"),
    ("Ollama (local)", "mistral", None, "free"),
    ("Ollama (local)", "mistral-nemo", None, "free"),
    ("Ollama (local)", "mistral-small", None, "free"),
    ("Ollama (local)", "mixtral", None, "free"),
    ("Ollama (local)", "codestral", None, "free"),
    ("Ollama (local)", "phi4", None, "free"),
    ("Ollama (local)", "phi4-mini", None, "free"),
    ("Ollama (local)", "phi3", None, "free"),
    ("Ollama (local)", "gemma3", None, "free"),
    ("Ollama (local)", "gemma2", None, "free"),
    ("Ollama (local)", "codegemma", None, "free"),
    ("Ollama (local)", "starcoder2", None, "free"),
    ("Ollama (local)", "granite3.3", None, "free"),
    ("Ollama (local)", "command-r", None, "free"),
    ("Ollama (local)", "command-r-plus", None, "free"),
    ("Ollama (local)", "llava", None, "free"),
    ("Ollama (local)", "tinyllama", None, "free"),
    ("Ollama (local)", "smollm2", None, "free"),
    ("Ollama (local)", "dolphin3", None, "free"),
    ("Ollama (local)", "olmo2", None, "free"),
    ("Ollama (local)", "openthinker", None, "free"),
    ("DeepSeek", "deepseek-chat", "deepseek/deepseek-chat-v3-0324", None),
    ("DeepSeek", "deepseek-reasoner", "deepseek/deepseek-r1", None),
    ("Groq", "llama-3.3-70b-versatile", None, "freetier"),
    ("Groq", "llama-3.1-8b-instant", None, "freetier"),
    ("Groq", "llama3-70b-8192", None, "freetier"),
    ("Groq", "llama3-8b-8192", None, "freetier"),
    ("Groq", "llama-4-scout-17b-16e-instruct", None, "freetier"),
    ("Groq", "llama-4-maverick-17b-128e-instruct", None, "freetier"),
    ("Groq", "deepseek-r1-distill-llama-70b", None, "freetier"),
    ("Groq", "qwen-qwq-32b", None, "freetier"),
    ("Groq", "qwen-2.5-coder-32b", None, "freetier"),
    ("Groq", "qwen-2.5-32b", None, "freetier"),
    ("Groq", "gemma2-9b-it", None, "freetier"),
    ("Groq", "mistral-saba-24b", None, "freetier"),
    ("Groq", "allam-2-7b", None, "freetier"),
    ("Together AI", "Llama-3.3-70B-Instruct-Turbo-Free", None, "freetier"),
    ("Together AI", "DeepSeek-R1-Distill-Llama-70B-free", None, "freetier"),
    ("Together AI", "Llama-3.3-70B-Instruct-Turbo", "meta-llama/llama-3.3-70b-instruct", None),
    ("Together AI", "Llama-3.1-405B-Instruct-Turbo", "meta-llama/llama-3.1-405b-instruct", None),
    ("Together AI", "Llama-3.1-70B-Instruct-Turbo", "meta-llama/llama-3.1-70b-instruct", None),
    ("Together AI", "Llama-3.1-8B-Instruct-Turbo", "meta-llama/llama-3.1-8b-instruct", None),
    ("Together AI", "Llama-4-Maverick-17B-128E", "meta-llama/llama-4-maverick", None),
    ("Together AI", "Llama-4-Scout-17B-16E", "meta-llama/llama-4-scout", None),
    ("Together AI", "Qwen2.5-72B-Instruct-Turbo", "qwen/qwen-2.5-72b-instruct", None),
    ("Together AI", "Qwen2.5-Coder-32B-Instruct", "qwen/qwen-2.5-coder-32b-instruct", None),
    ("Together AI", "Qwen3-235B-A22B", "qwen/qwen3-235b-a22b", None),
    ("Together AI", "QwQ-32B", "qwen/qwq-32b", None),
    ("Together AI", "DeepSeek-V3", "deepseek/deepseek-chat-v3-0324", None),
    ("Together AI", "DeepSeek-R1", "deepseek/deepseek-r1", None),
    ("Together AI", "Mixtral-8x7B-Instruct", "mistralai/mixtral-8x7b-instruct", None),
    ("Together AI", "Mixtral-8x22B-Instruct", "mistralai/mixtral-8x22b-instruct", None),
    ("Together AI", "Mistral-Small-24B-Instruct", "mistralai/mistral-small-24b-instruct-2501", None),
    ("Together AI", "gemma-2-27b-it", "google/gemma-2-27b-it", None),
    ("Fireworks", "llama-v3p3-70b-instruct", "meta-llama/llama-3.3-70b-instruct", None),
    ("Fireworks", "llama-v3p1-405b-instruct", "meta-llama/llama-3.1-405b-instruct", None),
    ("Fireworks", "llama-v3p1-70b-instruct", "meta-llama/llama-3.1-70b-instruct", None),
    ("Fireworks", "llama-v3p1-8b-instruct", "meta-llama/llama-3.1-8b-instruct", None),
    ("Fireworks", "llama4-maverick-instruct-basic", "meta-llama/llama-4-maverick", None),
    ("Fireworks", "llama4-scout-instruct-basic", "meta-llama/llama-4-scout", None),
    ("Fireworks", "qwen2p5-coder-32b-instruct", "qwen/qwen-2.5-coder-32b-instruct", None),
    ("Fireworks", "qwen2p5-72b-instruct", "qwen/qwen-2.5-72b-instruct", None),
    ("Fireworks", "qwen3-235b-a22b", "qwen/qwen3-235b-a22b", None),
    ("Fireworks", "qwq-32b", "qwen/qwq-32b", None),
    ("Fireworks", "deepseek-v3", "deepseek/deepseek-chat-v3-0324", None),
    ("Fireworks", "deepseek-r1", "deepseek/deepseek-r1", None),
    ("Fireworks", "mixtral-8x22b-instruct", "mistralai/mixtral-8x22b-instruct", None),
    ("Fireworks", "mistral-small-24b-instruct", "mistralai/mistral-small-24b-instruct-2501", None),
    ("Perplexity", "sonar", "perplexity/sonar", None),
    ("Perplexity", "sonar-pro", "perplexity/sonar-pro", None),
    ("Perplexity", "sonar-reasoning", "perplexity/sonar-reasoning", None),
    ("Perplexity", "sonar-reasoning-pro", "perplexity/sonar-reasoning-pro", None),
    ("Perplexity", "sonar-deep-research", "perplexity/sonar-deep-research", None),
    ("Perplexity", "r1-1776", "perplexity/r1-1776", None),
    ("xAI (Grok)", "grok-4", "x-ai/grok-4", None),
    ("xAI (Grok)", "grok-3", "x-ai/grok-3", None),
    ("xAI (Grok)", "grok-3-mini", "x-ai/grok-3-mini", None),
    ("xAI (Grok)", "grok-3-fast", None, None),
    ("xAI (Grok)", "grok-3-mini-fast", None, None),
    ("xAI (Grok)", "grok-2", "x-ai/grok-2-1212", None),
    ("xAI (Grok)", "grok-2-vision", "x-ai/grok-2-vision-1212", None),
    ("OpenRouter", "llama-3.3-70b-instruct:free", "meta-llama/llama-3.3-70b-instruct:free", "freetier"),
    ("OpenRouter", "llama-4-scout:free", "meta-llama/llama-4-scout:free", "freetier"),
    ("OpenRouter", "deepseek-chat-v3-0324:free", "deepseek/deepseek-chat-v3-0324:free", "freetier"),
    ("OpenRouter", "deepseek-r1:free", "deepseek/deepseek-r1:free", "freetier"),
    ("OpenRouter", "deepseek-r1-0528:free", "deepseek/deepseek-r1-0528:free", "freetier"),
    ("OpenRouter", "gemma-3-27b-it:free", "google/gemma-3-27b-it:free", "freetier"),
    ("OpenRouter", "gemini-2.0-flash-exp:free", "google/gemini-2.0-flash-exp:free", "freetier"),
    ("OpenRouter", "qwen-2.5-coder-32b-instruct:free", "qwen/qwen-2.5-coder-32b-instruct:free", "freetier"),
    ("OpenRouter", "qwen3-235b-a22b:free", "qwen/qwen3-235b-a22b:free", "freetier"),
    ("OpenRouter", "qwq-32b:free", "qwen/qwq-32b:free", "freetier"),
    ("OpenRouter", "mistral-small-3.1-24b-instruct:free", "mistralai/mistral-small-3.1-24b-instruct:free", "freetier"),
    ("OpenRouter", "mistral-7b-instruct:free", "mistralai/mistral-7b-instruct:free", "freetier"),
    ("OpenRouter", "kimi-k2:free", "moonshotai/kimi-k2:free", "freetier"),
    ("OpenRouter", "glm-4.5-air:free", "z-ai/glm-4.5-air:free", "freetier"),
    ("OpenRouter", "openai/gpt-4o", "openai/gpt-4o", None),
    ("OpenRouter", "openai/gpt-4.1", "openai/gpt-4.1", None),
    ("OpenRouter", "anthropic/claude-sonnet-4", "anthropic/claude-sonnet-4", None),
    ("OpenRouter", "anthropic/claude-opus-4", "anthropic/claude-opus-4", None),
    ("OpenRouter", "google/gemini-2.5-pro", "google/gemini-2.5-pro", None),
    ("OpenRouter", "google/gemini-2.5-flash", "google/gemini-2.5-flash", None),
    ("OpenRouter", "x-ai/grok-4", "x-ai/grok-4", None),
    ("OpenRouter", "deepseek/deepseek-chat-v3-0324", "deepseek/deepseek-chat-v3-0324", None),
    ("OpenRouter", "moonshotai/kimi-k3", "moonshotai/kimi-k3", None),
    ("OpenRouter", "moonshotai/kimi-k2.7-code", "moonshotai/kimi-k2.7-code", None),
    ("OpenRouter", "meta-llama/llama-3.3-70b-instruct", "meta-llama/llama-3.3-70b-instruct", None),
    ("OpenRouter", "mistralai/mistral-large-2411", "mistralai/mistral-large-2411", None),
    ("Qwen (Alibaba)", "qwen-max", "qwen/qwen-max", None),
    ("Qwen (Alibaba)", "qwen-plus", "qwen/qwen-plus", None),
    ("Qwen (Alibaba)", "qwen-turbo", "qwen/qwen-turbo", None),
    ("Qwen (Alibaba)", "qwen-long", None, None),
    ("Qwen (Alibaba)", "qwen3-coder-plus", "qwen/qwen3-coder", None),
    ("Qwen (Alibaba)", "qwen3-coder-flash", None, None),
    ("Qwen (Alibaba)", "qwen-vl-max", "qwen/qwen-vl-max", None),
    ("Qwen (Alibaba)", "qwen-vl-plus", "qwen/qwen-vl-plus", None),
    ("Qwen (Alibaba)", "qwen-math-plus", None, None),
    ("Qwen (Alibaba)", "qwq-plus", "qwen/qwq-plus", None),
    ("Kimi (Moonshot)", "kimi-k3", "moonshotai/kimi-k3", None),
    ("Kimi (Moonshot)", "kimi-k2.7-code", "moonshotai/kimi-k2.7-code", None),
    ("Kimi (Moonshot)", "kimi-k2.7-code-highspeed", None, None),
    ("Kimi (Moonshot)", "kimi-k2.6", "moonshotai/kimi-k2.6", None),
    ("Kimi (Moonshot)", "kimi-k2.5", "moonshotai/kimi-k2.5", None),
    ("GLM (Zhipu AI)", "glm-4-flash", None, "freetier"),
    ("GLM (Zhipu AI)", "glm-4-flashx", None, "freetier"),
    ("GLM (Zhipu AI)", "glm-4.5-flash", None, "freetier"),
    ("GLM (Zhipu AI)", "glm-4.5", "z-ai/glm-4.5", None),
    ("GLM (Zhipu AI)", "glm-4.5-air", "z-ai/glm-4.5-air", None),
    ("GLM (Zhipu AI)", "glm-4.5-x", None, None),
    ("GLM (Zhipu AI)", "glm-4.5-airx", None, None),
    ("GLM (Zhipu AI)", "glm-4-plus", None, None),
    ("GLM (Zhipu AI)", "glm-4-air", None, None),
    ("GLM (Zhipu AI)", "glm-4-airx", None, None),
    ("GLM (Zhipu AI)", "glm-4-long", None, None),
    ("GLM (Zhipu AI)", "glm-4v-plus", None, None),
    ("GLM (Zhipu AI)", "glm-z1-air", None, None),
]


def fetch_prices():
    """Return {openrouter_id: '$X.XX / $Y.YY'} from the public catalog."""
    req = urllib.request.Request(API, headers={"User-Agent": "AutoAgent-pricing-bot"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except urllib.error.URLError as e:
        # Local networks with SSL inspection break cert verification.
        # This is a public, read-only price feed (no credentials), so
        # falling back to an unverified fetch is acceptable here.
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        import ssl
        print("Cert verification failed; retrying without verification "
              "(public read-only feed)")
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            data = json.loads(r.read().decode())
    out = {}
    for m in data.get("data", []):
        p = m.get("pricing") or {}
        try:
            inp = float(p.get("prompt", 0)) * 1_000_000
            outp = float(p.get("completion", 0)) * 1_000_000
        except (TypeError, ValueError):
            continue
        if inp <= 0 and outp <= 0:
            continue
        out[m["id"]] = f"${inp:.2f} / ${outp:.2f}"
    return out


def build_table(prices):
    lines = [
        "| Provider | Model | Price per 1M tokens, USD (in / out) | API Key? | How to Get a Key |",
        "|----------|-------|-------------------------------------|----------|-------------------|",
    ]
    for prov, model, spec, key, link in ROWS:
        kind = spec[0]
        if kind == "static":
            price = spec[1]
        elif kind == "live":
            price = prices.get(spec[1], spec[2])
        else:  # live_prefix / live_suffix: wrap the live price in a template
            live = prices.get(spec[1])
            price = spec[3].format(live) if live else spec[2]
        lines.append(f"| {prov} | {model} | {price} | {key} | {link} |")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines += ["", f"_All prices in USD ($) · Last updated: {stamp} · auto-refreshes every 2 hours_"]
    return "\n".join(lines)


def build_catalog(prices):
    """Collapsible full-catalog table with live prices where available."""
    lines = [
        "<details>",
        "<summary><b>\U0001f4cb Full Model Catalog</b> — every model built into the app, "
        "with live USD prices (click to expand)</summary>",
        "",
        "| Provider | Model(s) | Price per 1M tokens, USD (in / out) |",
        "|----------|----------|--------------------------------------|",
    ]
    for prov, model, or_id, tag in FULL_CATALOG:
        if tag == "free":
            price = "**FREE — No API Key needed**"
        elif tag == "freetier":
            live = prices.get(or_id) if or_id else None
            price = "**FREE** (with free key)" if not live or live == "$0.00 / $0.00" \
                else f"**FREE tier** (paid: {live})"
        else:
            price = (prices.get(or_id) if or_id else None) or "see provider site"
        lines.append(f"| {prov} | `{model}` | {price} |")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines += ["", f"_All prices in USD ($) · Last updated: {stamp} · auto-refreshes every 2 hours_",
              "", "</details>"]
    return "\n".join(lines)


def main():
    text = README.read_text(encoding="utf-8")
    try:
        prices = fetch_prices()
        print(f"Fetched {len(prices)} live model prices")
    except Exception as e:
        print(f"Price fetch failed ({e}); keeping fallback prices")
        prices = {}
    new = re.sub(
        r"<!-- PRICING:START -->.*?<!-- PRICING:END -->",
        "<!-- PRICING:START -->\n" + build_table(prices) + "\n<!-- PRICING:END -->",
        text, flags=re.DOTALL)
    new = re.sub(
        r"<!-- MODELS:START -->.*?<!-- MODELS:END -->",
        "<!-- MODELS:START -->\n" + build_catalog(prices) + "\n<!-- MODELS:END -->",
        new, flags=re.DOTALL)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README pricing tables updated")
    else:
        print("No changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
