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
    ("**Kimi (Moonshot)**", "kimi-k2",
     ("live", "moonshotai/kimi-k2", "$0.60 / $2.50"),
     "Paid key", "[platform.moonshot.cn](https://platform.moonshot.cn)"),
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
    ("OpenAI", "gpt-4.1", "openai/gpt-4.1", None),
    ("OpenAI", "gpt-4.1-mini", "openai/gpt-4.1-mini", None),
    ("OpenAI", "gpt-4.1-nano", "openai/gpt-4.1-nano", None),
    ("OpenAI", "o3", "openai/o3", None),
    ("OpenAI", "o3-mini", "openai/o3-mini", None),
    ("OpenAI", "o4-mini", "openai/o4-mini", None),
    ("OpenAI", "gpt-4-turbo", "openai/gpt-4-turbo", None),
    ("OpenAI", "gpt-3.5-turbo", "openai/gpt-3.5-turbo", None),
    ("Anthropic", "claude-sonnet-4", "anthropic/claude-sonnet-4", None),
    ("Anthropic", "claude-opus-4", "anthropic/claude-opus-4", None),
    ("Anthropic", "claude-3-7-sonnet", "anthropic/claude-3.7-sonnet", None),
    ("Anthropic", "claude-3-5-sonnet", "anthropic/claude-3.5-sonnet", None),
    ("Anthropic", "claude-3-5-haiku", "anthropic/claude-3.5-haiku", None),
    ("Anthropic", "claude-3-haiku", "anthropic/claude-3-haiku", None),
    ("Google Gemini", "gemini-2.5-flash", "google/gemini-2.5-flash", "freetier"),
    ("Google Gemini", "gemini-2.5-flash-lite", "google/gemini-2.5-flash-lite", "freetier"),
    ("Google Gemini", "gemini-2.0-flash", "google/gemini-2.0-flash-001", "freetier"),
    ("Google Gemini", "gemini-2.0-flash-lite", "google/gemini-2.0-flash-lite-001", "freetier"),
    ("Google Gemini", "gemini-1.5-flash", "google/gemini-flash-1.5", "freetier"),
    ("Google Gemini", "gemini-2.5-pro", "google/gemini-2.5-pro", None),
    ("Google Gemini", "gemini-1.5-pro", "google/gemini-pro-1.5", None),
    ("Ollama (local)", "llama3.3 / llama3.2 / llama3.1 / llama3.2-vision", None, "free"),
    ("Ollama (local)", "codellama / qwen2.5-coder / qwen3", None, "free"),
    ("Ollama (local)", "deepseek-coder-v2 / deepseek-r1", None, "free"),
    ("Ollama (local)", "mistral / mistral-nemo / mixtral / codestral", None, "free"),
    ("Ollama (local)", "phi4 / phi4-mini / gemma3 / gemma2 / codegemma", None, "free"),
    ("Ollama (local)", "starcoder2 / granite3.3", None, "free"),
    ("DeepSeek", "deepseek-chat", "deepseek/deepseek-chat-v3-0324", None),
    ("DeepSeek", "deepseek-reasoner", "deepseek/deepseek-r1", None),
    ("Groq", "llama-3.3-70b-versatile", None, "freetier"),
    ("Groq", "llama-3.1-8b-instant", None, "freetier"),
    ("Groq", "deepseek-r1-distill-llama-70b", None, "freetier"),
    ("Groq", "qwen-2.5-coder-32b / qwen-qwq-32b", None, "freetier"),
    ("Groq", "gemma2-9b-it / mixtral-8x7b-32768", None, "freetier"),
    ("Groq", "llama-4-scout / llama-4-maverick", None, "freetier"),
    ("Together AI", "Llama-3.3-70B-Instruct-Turbo-Free", None, "freetier"),
    ("Together AI", "DeepSeek-R1-Distill-Llama-70B-free", None, "freetier"),
    ("Together AI", "Llama-3.3-70B-Instruct-Turbo", "meta-llama/llama-3.3-70b-instruct", None),
    ("Together AI", "Llama-4-Maverick-17B-128E", "meta-llama/llama-4-maverick", None),
    ("Together AI", "Qwen2.5-Coder-32B / Qwen3-235B", None, None),
    ("Together AI", "DeepSeek-V3 / DeepSeek-R1", None, None),
    ("Together AI", "Mixtral-8x7B-Instruct", "mistralai/mixtral-8x7b-instruct", None),
    ("Fireworks", "llama-v3p3-70b / llama4-maverick", None, None),
    ("Fireworks", "qwen2p5-coder-32b / deepseek-v3 / deepseek-r1", None, None),
    ("Fireworks", "mixtral-8x22b-instruct", None, None),
    ("Perplexity", "sonar", "perplexity/sonar", None),
    ("Perplexity", "sonar-pro", "perplexity/sonar-pro", None),
    ("Perplexity", "sonar-reasoning", "perplexity/sonar-reasoning", None),
    ("Perplexity", "sonar-reasoning-pro", "perplexity/sonar-reasoning-pro", None),
    ("Perplexity", "sonar-deep-research", "perplexity/sonar-deep-research", None),
    ("xAI (Grok)", "grok-4", "x-ai/grok-4", None),
    ("xAI (Grok)", "grok-3", "x-ai/grok-3", None),
    ("xAI (Grok)", "grok-3-mini", "x-ai/grok-3-mini", None),
    ("xAI (Grok)", "grok-3-fast / grok-2", None, None),
    ("OpenRouter", "llama-3.3-70b-instruct:free", "meta-llama/llama-3.3-70b-instruct:free", "freetier"),
    ("OpenRouter", "deepseek-chat-v3-0324:free", "deepseek/deepseek-chat-v3-0324:free", "freetier"),
    ("OpenRouter", "deepseek-r1:free / deepseek-r1-0528:free", "deepseek/deepseek-r1:free", "freetier"),
    ("OpenRouter", "gemma-3-27b-it:free", "google/gemma-3-27b-it:free", "freetier"),
    ("OpenRouter", "qwen-2.5-coder-32b:free / qwen3-235b:free", "qwen/qwen-2.5-coder-32b-instruct:free", "freetier"),
    ("OpenRouter", "mistral-small-3.1-24b:free", "mistralai/mistral-small-3.1-24b-instruct:free", "freetier"),
    ("OpenRouter", "kimi-k2:free", "moonshotai/kimi-k2:free", "freetier"),
    ("OpenRouter", "glm-4.5-air:free", "z-ai/glm-4.5-air:free", "freetier"),
    ("OpenRouter", "gpt-4o / claude-sonnet-4 / gemini-2.5-pro / grok-4", None, None),
    ("Qwen (Alibaba)", "qwen-max", "qwen/qwen-max", None),
    ("Qwen (Alibaba)", "qwen-plus", "qwen/qwen-plus", None),
    ("Qwen (Alibaba)", "qwen-turbo", "qwen/qwen-turbo", None),
    ("Qwen (Alibaba)", "qwen3-coder-plus / qwen3-coder-flash", "qwen/qwen3-coder", None),
    ("Qwen (Alibaba)", "qwen-long", None, None),
    ("Kimi (Moonshot)", "kimi-k2 / kimi-k2-turbo / kimi-latest", "moonshotai/kimi-k2", None),
    ("Kimi (Moonshot)", "moonshot-v1-8k / 32k / 128k", None, None),
    ("GLM (Zhipu AI)", "glm-4-flash / glm-4.5-flash", None, "freetier"),
    ("GLM (Zhipu AI)", "glm-4.5", "z-ai/glm-4.5", None),
    ("GLM (Zhipu AI)", "glm-4.5-air", "z-ai/glm-4.5-air", None),
    ("GLM (Zhipu AI)", "glm-4.5-x / glm-4-plus / glm-4-air / glm-4-long", None, None),
]


def fetch_prices():
    """Return {openrouter_id: '$X.XX / $Y.YY'} from the public catalog."""
    req = urllib.request.Request(API, headers={"User-Agent": "AutoAgent-pricing-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
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
