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
        "| Provider | Model | Price per 1M tokens (in / out) | API Key? | How to Get a Key |",
        "|----------|-------|-------------------------------|----------|-------------------|",
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
    lines += ["", f"_Last updated: {stamp} · prices auto-refresh every 2 hours_"]
    return "\n".join(lines)


def main():
    text = README.read_text(encoding="utf-8")
    try:
        prices = fetch_prices()
        print(f"Fetched {len(prices)} live model prices")
    except Exception as e:
        print(f"Price fetch failed ({e}); keeping fallback prices")
        prices = {}
    table = build_table(prices)
    new = re.sub(
        r"<!-- PRICING:START -->.*?<!-- PRICING:END -->",
        "<!-- PRICING:START -->\n" + table + "\n<!-- PRICING:END -->",
        text, flags=re.DOTALL)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README pricing table updated")
    else:
        print("No changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
