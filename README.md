<div align="center">

<img src="aicoder/logo.png" alt="AutoAgent logo" width="140"/>

# AutoAgent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()
[![Providers: 14](https://img.shields.io/badge/LLM_providers-14-8A2BE2.svg)]()

**AutoAgent — a self-improving AI coding agent with a premium desktop dashboard.**
Give it a goal — it audits your project, builds a roadmap, then autonomously
implements, tests, and measures improvements in a continuous loop.

</div>

## The Flow

1. **You provide a high-level goal** — e.g., "Transform this into a AAA-quality driving game"
2. **The AI performs a complete project audit** — analyzing the codebase, architecture, gameplay systems, UI, performance, audio, lighting, animations, physics, AI, and game design to identify weaknesses
3. **The Planner generates a prioritized roadmap** — breaking the project into improvements grouped by category (graphics, physics, AI, vehicles, world design, optimization, UI, audio, etc.)
4. **The Improvement Engine enters an autonomous loop:**
   - Picks the highest-impact improvement
   - Implements it
   - Tests the project (did anything break?)
   - Measures quality and performance
   - Updates the roadmap
   - Repeats
5. **Terminates when:** the target quality threshold is reached, no meaningful improvements remain, the user stops the process, or resource limits are reached.

## Core Concept

Rather than asking "What should I do next?", the AI continually asks:

- **What is the biggest weakness in the current project?**
- **What improvement will most increase quality?**
- **Can I implement it safely?**
- **Did it actually make the project better?**
- **What should I improve next?**

This creates a self-improving development loop.

## Features

- **Self-Improving Engine** — Continuous audit → roadmap → implement → test → measure → repeat loop
- **Premium Desktop App** — Dark neon dashboard with 8 pages: Dashboard, Projects, Agents, Agent Activity, Code Explorer, Metrics, Tools, Settings
- **Live Monitoring** — Real-time quality gauges, CPU/RAM meters, activity feed with search, sparkline charts, toast notifications
- **Comprehensive Auditor** — Analyzes 16 categories (graphics, physics, AI, vehicles, world, optimization, UI, audio, etc.)
- **Prioritized Roadmap** — Impact-scored backlog with dependency tracking and automatic reprioritization
- **Quality Metrics** — Tracks quality over time with category-level scoring, trend analysis, and target thresholds
- **Test Validator** — Verifies improvements don't break the project (custom test functions, file checks, command checks)
- **14 Pluggable LLM Providers** — OpenAI, Anthropic, Gemini, Ollama, DeepSeek, Groq, Together, Fireworks, Perplexity, xAI, OpenRouter, Qwen, Kimi, GLM
- **Built-in Model Catalog** — **100+ models** in a Settings dropdown; free models are labelled **(Free — No API Key needed)** / **(Free)** and the key field disables itself for keyless models
- **Extensible Tools** — File I/O, shell execution, regex/grep search, glob file matching, git operations
- **Safety First** — Shell sandboxing blocks dangerous commands; file writes restricted to workspace
- **pip-Installable** — Single command install with `aicoder` CLI entry point

## Quickstart

### Option A: Download & Double-Click (Windows — easiest)

1. Click the green **Code** button above → **Download ZIP**
2. Extract the ZIP anywhere
3. Double-click **`run.bat`**
   - First run: dependencies install automatically (takes ~1 minute)
   - Every run after: the app opens instantly, no console window
4. Click ⚙ Settings, pick a provider and a model from the dropdown (free ones are labelled), paste your API key if needed, set a goal, press **▶ Run**

> **"Publisher cannot be verified"?** That's standard Windows behavior for files
> downloaded from the internet — click **Run**. You only need Python installed
> ([python.org](https://python.org), tick "Add Python to PATH").

### Option B: Standalone .exe (no Python needed)

1. Go to [Releases](https://github.com/jaydenqiu51/AutoAgent-VersionCode/releases)
2. Download **AICoder.exe**
3. Double-click it — the desktop app opens immediately, no install needed
4. Enter your API key, set a goal, and click **Start Engine**

### Option C: Launch Desktop App from Source

```bash
git clone https://github.com/jaydenqiu51/AutoAgent-VersionCode.git
cd AutoAgent-VersionCode
pip install -e .
aicoder --gui
```

### Option D: CLI from Source

```bash
# 1. Install
git clone https://github.com/jaydenqiu51/AutoAgent-VersionCode.git
cd AutoAgent-VersionCode
pip install -e .

# 2. Configure (Windows PowerShell)
$env:OPENAI_API_KEY = "sk-..."

# 3. Run

# Single task mode
aicoder "Add input validation to src/auth.py"

# Interactive mode
aicoder --interactive

# CONTINUOUS SELF-IMPROVING MODE (the real power)
aicoder --continuous "Transform this into a AAA-quality driving game"

# With quality target and iteration limit
aicoder -c --target 90 --max-iterations 200 "Make this project production-ready"

# With local model
aicoder -c --provider ollama --model codellama "Improve code quality"
```

### Build Your Own .exe

```bash
pip install pyinstaller
python build.py          # Builds AICoder.exe (GUI)
python build.py --cli    # Builds aicoder.exe (CLI)
```

Output goes to `dist/AICoder.exe` — a single file you can share or put on a USB stick.

## Supported LLM Providers

Prices are **per 1 million tokens** (input / output), in **US Dollars (USD $)**.

<!-- PRICING:START -->
| Provider | Model | Price per 1M tokens, USD (in / out) | API Key? | How to Get a Key |
|----------|-------|-------------------------------------|----------|-------------------|
| **Ollama** | codellama, llama3, etc. | **$0 — completely FREE** | ❌ **No key needed** | [ollama.com](https://ollama.com) — just install it |
| **Google Gemini** | gemini-2.5-flash | **FREE tier** (paid: $0.30 / $2.50) | Free key | [aistudio.google.com](https://aistudio.google.com/apikey) |
| **Groq** | llama-3.3-70b-versatile | **FREE tier** (paid: $0.59 / $0.79) | Free key | [console.groq.com](https://console.groq.com) |
| **GLM (Zhipu AI)** | glm-4-flash | **FREE** | Free key | [open.bigmodel.cn](https://open.bigmodel.cn) |
| **OpenRouter** | 100+ models, many `:free` | **FREE** (`:free` models) and up | Free key | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **DeepSeek** | deepseek-chat | $0.27 / $1.10 | Paid key | [platform.deepseek.com](https://platform.deepseek.com) |
| **Qwen (Alibaba)** | qwen-plus | $0.40 / $1.20 | Paid key | [dashscope.aliyun.com](https://dashscope.console.aliyun.com) |
| **Kimi (Moonshot)** | kimi-k2 | $0.60 / $2.50 | Paid key | [platform.moonshot.cn](https://platform.moonshot.cn) |
| **Together AI** | Llama 3.3 70B Turbo | $0.88 / $0.88 (+ free models) | Key (has free models) | [together.ai](https://together.ai) |
| **Fireworks** | Llama 3.3 70B | $0.90 / $0.90 | Paid key | [fireworks.ai](https://fireworks.ai) |
| **OpenAI** | gpt-4o | $2.50 / $10.00 | Paid key | [platform.openai.com](https://platform.openai.com) |
| | gpt-4o-mini | $0.15 / $0.60 | | |
| | gpt-4.1 | $2.00 / $8.00 | | |
| **Anthropic** | claude-sonnet-4 | $3.00 / $15.00 | Paid key | [console.anthropic.com](https://console.anthropic.com) |
| | claude-opus-4 | $15.00 / $75.00 | | |
| | claude-3-5-haiku | $0.80 / $4.00 | | |
| **Perplexity** | sonar-pro | $3.00 / $15.00 (+ search fees) | Paid key | [perplexity.ai](https://docs.perplexity.ai) |
| **xAI (Grok)** | grok-3 | $3.00 / $15.00 | Paid key | [x.ai/api](https://x.ai/api) |

_All prices in USD ($) · Last updated: 2026-07-24 · auto-refreshes every 2 hours_
<!-- PRICING:END -->

<!-- MODELS:START -->
<details>
<summary><b>📋 Full Model Catalog</b> — every model built into the app, with live USD prices (click to expand)</summary>

_This table is populated automatically by the live pricing tracker (refreshes every 2 hours). If it looks empty, check back shortly — 100+ models across all 14 providers are listed here with their current USD prices._

</details>
<!-- MODELS:END -->

### 🆓 Use It Completely Free — No API Key

The **Ollama** provider needs **no API key at all** — models run locally on your PC:

1. Install [Ollama](https://ollama.com) (free)
2. In a terminal: `ollama pull llama3.2` (or `codellama`, `qwen2.5-coder`, `deepseek-r1`…)
3. In AutoAgent Settings, pick provider **ollama** — every model in the dropdown shows
   **(Free — No API Key needed)** and the API key box disables itself
4. Press ▶ Run. Zero cost, zero sign-up, works offline

**Free cloud models** (need only a free account key, no payment): every model marked
**(Free)** in the app's Settings dropdown — including `gemini-2.5-flash`, all Groq models,
`glm-4-flash`, and every OpenRouter model ending in `:free`.
The in-app model catalog covers all 14 providers and is kept updated with each release.

### Environment Variables

Set the right env var for your provider:

```bash
# OpenAI
$env:OPENAI_API_KEY = "sk-..."

# Anthropic
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Google Gemini (FREE tier available!)
$env:GEMINI_API_KEY = "AIza..."

# DeepSeek (cheapest strong coder)
$env:DEEPSEEK_API_KEY = "sk-..."

# Groq (FREE tier available!)
$env:GROQ_API_KEY = "gsk_..."

# OpenRouter (100+ models, some FREE)
$env:OPENROUTER_API_KEY = "sk-or-..."

# Or set once for any provider:
$env:AICODER_API_KEY = "your-key"
```

### CLI Examples with Providers

```bash
# Free: Google Gemini
aicoder -p gemini -m gemini-2.5-flash "Add error handling"

# Free: Groq (fastest inference)
aicoder -p groq -m llama-3.3-70b-versatile "Refactor auth"

# Cheapest strong coder: DeepSeek
aicoder -p deepseek "Optimize the renderer"

# Local: Ollama (no API key, no internet)
aicoder -p ollama -m codellama "Write unit tests"

# OpenRouter: access any model through one API
aicoder -p openrouter -m "google/gemma-3-27b-it:free" "Review code"
```

## Architecture

```mermaid
graph TB
    CLI[CLI / --continuous] --> Engine[Improvement Engine]

    Engine --> Auditor[Project Auditor]
    Engine --> Roadmap[Prioritized Roadmap]
    Engine --> Agent[Single-Task Agent]
    Engine --> Tester[Test Validator]
    Engine --> Metrics[Quality Metrics]

    Auditor --> |"16 categories"| Report[Audit Report]
    Report --> Roadmap

    Roadmap --> |"highest impact"| Agent
    Agent --> |"implemented"| Tester
    Tester --> |"passed"| Metrics
    Tester --> |"failed"| Agent
    Metrics --> |"quality delta"| Roadmap

    Agent --> Provider[LLM Provider]
    Agent --> ToolRegistry[Tool Registry]

    Provider --> OpenAI
    Provider --> Anthropic
    Provider --> Gemini[Google Gemini]
    Provider --> Ollama
    Provider --> DeepSeek
    Provider --> Groq
    Provider --> OpenRouter[OpenRouter 100+]

    ToolRegistry --> FileTools[File I/O]
    ToolRegistry --> ShellTool[Shell]
    ToolRegistry --> SearchTools[Search]
    ToolRegistry --> GitTools[Git]
```

## Usage as a Library

```python
from aicoder.core.engine import ImprovementEngine
from aicoder.core.tester import Tester, make_command_check
from aicoder.core.tool_registry import ToolRegistry
from aicoder.llm.openai_provider import OpenAIProvider
from aicoder.tools.file_tools import ReadFileTool, WriteFileTool

# Set up
provider = OpenAIProvider(model="gpt-4o")
registry = ToolRegistry()
registry.register(ReadFileTool())
registry.register(WriteFileTool())
# ... register more tools

# Custom tester
tester = Tester()
tester.add_check(make_command_check("lint", "flake8 ."))

# Run the engine
engine = ImprovementEngine(
    goal="Transform this into a AAA-quality game",
    provider=provider,
    tool_registry=registry,
    tester=tester,
    target_quality=90.0,
    max_iterations=200,
    on_phase=lambda phase, msg: print(f"[{phase}] {msg}"),
    on_improvement=lambda iid, title, result: print(f"  Done: {title}"),
    on_quality=lambda before, after, trend: print(f"  Quality: {before:.0f} -> {after:.0f}"),
)

report = engine.run()
print(report)
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AICODER_PROVIDER` | `openai` | LLM provider |
| `AICODER_MODEL` | `gpt-4o` | Model name |
| `AICODER_API_KEY` | — | API key |
| `AICODER_WORKSPACE` | `.` (cwd) | Workspace root |
| `AICODER_MAX_TOKENS` | `8000` | Max tokens per request |
| `AICODER_MAX_ITERATIONS` | `25` | Max agent loop iterations (single task) |
| `AICODER_TEMPERATURE` | `0.2` | LLM temperature |

## Project Structure

```
AutoAgent-VersionCode/
├── README.md
├── LICENSE
├── setup.py
├── build.py                    # PyInstaller packaging → standalone .exe
├── run.bat                     # Windows launcher (auto-installs deps on first run)
├── run.pyw                     # Zero-console launcher (double-click)
├── aicoder/
│   ├── cli.py                  # CLI: --gui, --continuous, --interactive
│   ├── gui.py                  # Premium desktop dashboard (tkinter) — 8 pages, live gauges
│   ├── logo.png                # App icon / emblem
│   ├── config.py               # Env-var configuration
│   ├── core/
│   │   ├── agent.py            # Single-task ReAct agent
│   │   ├── engine.py           # Continuous self-improving loop
│   │   ├── auditor.py          # 16-category project audit
│   │   ├── roadmap.py          # Prioritized backlog with dependencies
│   │   ├── metrics.py          # Quality tracking & measurement
│   │   ├── tester.py           # Test validation framework
│   │   ├── memory.py           # Conversation memory
│   │   ├── planner.py          # Task decomposition
│   │   └── tool_registry.py    # Tool registration
│   ├── llm/                    # Pluggable LLM providers
│   ├── tools/                  # 10 built-in tools
│   └── prompts/                # System prompts
└── examples/
    └── basic_usage.py
```

## License

MIT © 2026 Jayden Qiu
