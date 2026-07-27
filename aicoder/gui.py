"""Desktop GUI for AutoAgent — the self-improving AI coding agent.

Ultra-premium dark dashboard with neon accents, glass-morphism cards,
glow gauges, toast notifications, tooltips, and smooth hover animations.
Built with pure tk widgets + Canvas (no ttk themes, no place geometry).
"""

import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

# Give the app its own Windows taskbar identity *before* any window is
# created — otherwise the taskbar keeps grouping us under pythonw.exe
# and shows the Python icon no matter what the window icon is.
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "AutoAgent.Desktop.App")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# ── PREMIUM DARK PALETTE ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
BG       = "#06080e"    # ultra-deep background
BG2      = "#0a0d16"    # layer 1
BG3      = "#0e1220"    # layer 2
SIDEBAR  = "#080c16"    # sidebar
TOPBAR   = "#090d17"    # top bar
CARD     = "#0f1525"    # card surface
CARD2    = "#141c2e"    # hover / elevated
CARD3    = "#1a2438"    # active card
BORDER   = "#162036"    # card borders (subtle blue tint)
BORDER2  = "#1e2d4a"    # highlighted borders
GLOW_BRD = "#253a60"    # glow borders
FG       = "#f0f4ff"    # primary text (slight blue-white)
FG2      = "#c0c8e0"    # secondary text
FG_DIM   = "#7888a8"    # muted
FG_FAINT = "#3d4e6e"    # very muted

# Neon accents
BLUE     = "#4f8fff"    # primary action
BLUE_HL  = "#6fa8ff"    # hover blue
CYAN     = "#00e5ff"    # electric cyan
GREEN    = "#00e676"    # neon green
TEAL     = "#1de9b6"    # teal
PURPLE   = "#b388ff"    # soft purple
VIOLET   = "#7c4dff"    # deep violet
ORANGE   = "#ff9100"    # warm orange
RED      = "#ff5252"    # error red
YELLOW   = "#ffd740"    # gold
PINK     = "#ff80ab"    # pink

# Canvas drawing
TRACK    = "#101828"    # gauge/bar track
TRACK2   = "#182038"    # lighter track

# Toast backgrounds
TOAST_INFO_BG = "#0d1e3a"
TOAST_OK_BG   = "#0d2a1a"
TOAST_ERR_BG  = "#2a0d0d"
TOAST_WARN_BG = "#2a1f0d"
STOP_HOVER    = "#3a1818"   # stop-button hover

# ── THEMES ── every color above, per theme.  The module-level names
# stay authoritative: apply_palette() rewrites them in place, and all
# widgets are rebuilt afterwards so the change takes effect everywhere.
PALETTES = {
    "dark": dict(
        BG="#06080e", BG2="#0a0d16", BG3="#0e1220",
        SIDEBAR="#080c16", TOPBAR="#090d17",
        CARD="#0f1525", CARD2="#141c2e", CARD3="#1a2438",
        BORDER="#162036", BORDER2="#1e2d4a", GLOW_BRD="#253a60",
        FG="#f0f4ff", FG2="#c0c8e0", FG_DIM="#7888a8", FG_FAINT="#3d4e6e",
        BLUE="#4f8fff", BLUE_HL="#6fa8ff", CYAN="#00e5ff", GREEN="#00e676",
        TEAL="#1de9b6", PURPLE="#b388ff", VIOLET="#7c4dff", ORANGE="#ff9100",
        RED="#ff5252", YELLOW="#ffd740", PINK="#ff80ab",
        TRACK="#101828", TRACK2="#182038",
        TOAST_INFO_BG="#0d1e3a", TOAST_OK_BG="#0d2a1a",
        TOAST_ERR_BG="#2a0d0d", TOAST_WARN_BG="#2a1f0d",
        STOP_HOVER="#3a1818",
    ),
    "light": dict(
        BG="#f2f4fa", BG2="#eaeef6", BG3="#e2e8f2",
        SIDEBAR="#e8ecf5", TOPBAR="#edf0f8",
        CARD="#ffffff", CARD2="#f0f3fa", CARD3="#e3e9f4",
        BORDER="#d7deeb", BORDER2="#c2cde0", GLOW_BRD="#9fb4d8",
        FG="#141b2e", FG2="#3a4560", FG_DIM="#68748f", FG_FAINT="#9aa6bd",
        BLUE="#2f6fe4", BLUE_HL="#1d5dd2", CYAN="#0092b8", GREEN="#0a9d58",
        TEAL="#00897b", PURPLE="#7e57c2", VIOLET="#5e35b1", ORANGE="#e8710a",
        RED="#d93030", YELLOW="#c99700", PINK="#d81b60",
        TRACK="#dde3ef", TRACK2="#d0d8e8",
        TOAST_INFO_BG="#e1ebff", TOAST_OK_BG="#dff3e6",
        TOAST_ERR_BG="#fce3e3", TOAST_WARN_BG="#fcefdc",
        STOP_HOVER="#f3d3d3",
    ),
}


def apply_palette(name):
    """Swap every module-level color to the chosen theme's values."""
    globals().update(PALETTES.get(name, PALETTES["dark"]))

UI_FONT   = "Segoe UI"
MONO_FONT = "Consolas"
TITLE_FONT = "Segoe UI Semibold"


# ═══════════════════════════════════════════════════════════════════
# ── PROVIDER PRESETS ──────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
PROVIDER_DEFAULTS = {
    "openai":       {"model": "gpt-4o", "key_env": "OPENAI_API_KEY", "hint": "sk-..."},
    "anthropic":    {"model": "claude-sonnet-4-20250514", "key_env": "ANTHROPIC_API_KEY", "hint": "sk-ant-..."},
    "gemini":       {"model": "gemini-2.5-flash", "key_env": "GEMINI_API_KEY", "hint": "AIza..."},
    "ollama":       {"model": "llama3.2", "key_env": "", "hint": "(no key needed)"},
    "deepseek":     {"model": "deepseek-chat", "key_env": "DEEPSEEK_API_KEY", "hint": "sk-..."},
    "groq":         {"model": "llama-3.3-70b-versatile", "key_env": "GROQ_API_KEY", "hint": "gsk_..."},
    "together":     {"model": "mistralai/Mixtral-8x7B-Instruct-v0.1", "key_env": "TOGETHER_API_KEY", "hint": "..."},
    "fireworks":    {"model": "accounts/fireworks/models/llama-v3p1-70b-instruct", "key_env": "FIREWORKS_API_KEY", "hint": "..."},
    "perplexity":   {"model": "sonar-pro", "key_env": "PERPLEXITY_API_KEY", "hint": "pplx-..."},
    "xai":          {"model": "grok-2", "key_env": "XAI_API_KEY", "hint": "xai-..."},
    "openrouter":   {"model": "openai/gpt-4o", "key_env": "OPENROUTER_API_KEY", "hint": "sk-or-..."},
    "qwen":         {"model": "qwen-plus", "key_env": "DASHSCOPE_API_KEY", "hint": "sk-..."},
    "kimi":         {"model": "moonshot-v1-8k", "key_env": "MOONSHOT_API_KEY", "hint": "sk-..."},
    "glm":          {"model": "glm-4-flash", "key_env": "ZHIPUAI_API_KEY", "hint": "..."},
}
PROVIDER_LIST = list(PROVIDER_DEFAULTS.keys())

# ── FULL MODEL CATALOG ── every model per provider, tagged:
#   "free"     → 100% free, NO API key needed (runs locally)
#   "freetier" → free to use, just needs a free account key
#   None       → paid
MODEL_CATALOG = {
    "openai": [
        ("gpt-4o", None), ("gpt-4o-mini", None), ("chatgpt-4o-latest", None),
        ("gpt-4.1", None), ("gpt-4.1-mini", None), ("gpt-4.1-nano", None),
        ("gpt-4.5-preview", None), ("gpt-4-turbo", None), ("gpt-4", None),
        ("gpt-3.5-turbo", None), ("o1", None), ("o1-mini", None),
        ("o1-pro", None), ("o3", None), ("o3-pro", None), ("o3-mini", None),
        ("o4-mini", None),
    ],
    "anthropic": [
        ("claude-opus-4-20250514", None), ("claude-sonnet-4-20250514", None),
        ("claude-3-7-sonnet-20250219", None), ("claude-3-5-sonnet-20241022", None),
        ("claude-3-5-sonnet-20240620", None), ("claude-3-5-haiku-20241022", None),
        ("claude-3-opus-20240229", None), ("claude-3-sonnet-20240229", None),
        ("claude-3-haiku-20240307", None),
    ],
    "gemini": [
        ("gemini-2.5-flash", "freetier"), ("gemini-2.5-flash-lite", "freetier"),
        ("gemini-2.0-flash", "freetier"), ("gemini-2.0-flash-lite", "freetier"),
        ("gemini-2.0-flash-thinking-exp", "freetier"),
        ("gemini-1.5-flash", "freetier"), ("gemini-1.5-flash-8b", "freetier"),
        ("gemma-3-27b-it", "freetier"),
        ("gemini-2.5-pro", None), ("gemini-1.5-pro", None),
    ],
    "ollama": [
        ("llama3.3", "free"), ("llama3.2", "free"), ("llama3.2-vision", "free"),
        ("llama3.1", "free"), ("llama3", "free"), ("llama2", "free"),
        ("codellama", "free"), ("qwen3", "free"), ("qwen2.5", "free"),
        ("qwen2.5-coder", "free"), ("qwq", "free"), ("deepseek-r1", "free"),
        ("deepseek-coder-v2", "free"), ("deepseek-v3", "free"),
        ("mistral", "free"), ("mistral-nemo", "free"), ("mistral-small", "free"),
        ("mixtral", "free"), ("codestral", "free"), ("phi4", "free"),
        ("phi4-mini", "free"), ("phi3", "free"), ("gemma3", "free"),
        ("gemma2", "free"), ("codegemma", "free"), ("starcoder2", "free"),
        ("granite3.3", "free"), ("command-r", "free"), ("command-r-plus", "free"),
        ("llava", "free"), ("tinyllama", "free"), ("smollm2", "free"),
        ("dolphin3", "free"), ("olmo2", "free"), ("openthinker", "free"),
    ],
    "deepseek": [("deepseek-chat", None), ("deepseek-reasoner", None)],
    "groq": [
        ("llama-3.3-70b-versatile", "freetier"), ("llama-3.1-8b-instant", "freetier"),
        ("llama3-70b-8192", "freetier"), ("llama3-8b-8192", "freetier"),
        ("meta-llama/llama-4-scout-17b-16e-instruct", "freetier"),
        ("meta-llama/llama-4-maverick-17b-128e-instruct", "freetier"),
        ("deepseek-r1-distill-llama-70b", "freetier"),
        ("qwen-qwq-32b", "freetier"), ("qwen-2.5-coder-32b", "freetier"),
        ("qwen-2.5-32b", "freetier"), ("gemma2-9b-it", "freetier"),
        ("mistral-saba-24b", "freetier"), ("allam-2-7b", "freetier"),
    ],
    "together": [
        ("meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "freetier"),
        ("deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free", "freetier"),
        ("meta-llama/Llama-3.3-70B-Instruct-Turbo", None),
        ("meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", None),
        ("meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", None),
        ("meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", None),
        ("meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8", None),
        ("meta-llama/Llama-4-Scout-17B-16E-Instruct", None),
        ("Qwen/Qwen2.5-72B-Instruct-Turbo", None),
        ("Qwen/Qwen2.5-Coder-32B-Instruct", None),
        ("Qwen/Qwen3-235B-A22B-fp8-tput", None),
        ("Qwen/QwQ-32B", None),
        ("deepseek-ai/DeepSeek-V3", None), ("deepseek-ai/DeepSeek-R1", None),
        ("mistralai/Mixtral-8x7B-Instruct-v0.1", None),
        ("mistralai/Mixtral-8x22B-Instruct-v0.1", None),
        ("mistralai/Mistral-Small-24B-Instruct-2501", None),
        ("google/gemma-2-27b-it", None),
    ],
    "fireworks": [
        ("accounts/fireworks/models/llama-v3p3-70b-instruct", None),
        ("accounts/fireworks/models/llama-v3p1-405b-instruct", None),
        ("accounts/fireworks/models/llama-v3p1-70b-instruct", None),
        ("accounts/fireworks/models/llama-v3p1-8b-instruct", None),
        ("accounts/fireworks/models/llama4-maverick-instruct-basic", None),
        ("accounts/fireworks/models/llama4-scout-instruct-basic", None),
        ("accounts/fireworks/models/qwen2p5-coder-32b-instruct", None),
        ("accounts/fireworks/models/qwen2p5-72b-instruct", None),
        ("accounts/fireworks/models/qwen3-235b-a22b", None),
        ("accounts/fireworks/models/qwq-32b", None),
        ("accounts/fireworks/models/deepseek-v3", None),
        ("accounts/fireworks/models/deepseek-r1", None),
        ("accounts/fireworks/models/mixtral-8x22b-instruct", None),
        ("accounts/fireworks/models/mistral-small-24b-instruct-2501", None),
    ],
    "perplexity": [
        ("sonar", None), ("sonar-pro", None), ("sonar-reasoning", None),
        ("sonar-reasoning-pro", None), ("sonar-deep-research", None),
        ("r1-1776", None),
    ],
    "xai": [
        ("grok-4", None), ("grok-3", None), ("grok-3-mini", None),
        ("grok-3-fast", None), ("grok-3-mini-fast", None),
        ("grok-2", None), ("grok-2-vision", None),
    ],
    "openrouter": [
        ("meta-llama/llama-3.3-70b-instruct:free", "freetier"),
        ("meta-llama/llama-4-scout:free", "freetier"),
        ("deepseek/deepseek-chat-v3-0324:free", "freetier"),
        ("deepseek/deepseek-r1:free", "freetier"),
        ("deepseek/deepseek-r1-0528:free", "freetier"),
        ("google/gemma-3-27b-it:free", "freetier"),
        ("google/gemini-2.0-flash-exp:free", "freetier"),
        ("qwen/qwen-2.5-coder-32b-instruct:free", "freetier"),
        ("qwen/qwen3-235b-a22b:free", "freetier"),
        ("qwen/qwq-32b:free", "freetier"),
        ("mistralai/mistral-small-3.1-24b-instruct:free", "freetier"),
        ("mistralai/mistral-7b-instruct:free", "freetier"),
        ("moonshotai/kimi-k2:free", "freetier"),
        ("z-ai/glm-4.5-air:free", "freetier"),
        ("openai/gpt-4o", None), ("openai/gpt-4.1", None),
        ("anthropic/claude-sonnet-4", None), ("anthropic/claude-opus-4", None),
        ("google/gemini-2.5-pro", None), ("google/gemini-2.5-flash", None),
        ("x-ai/grok-4", None), ("deepseek/deepseek-chat-v3-0324", None),
        ("meta-llama/llama-3.3-70b-instruct", None),
        ("mistralai/mistral-large-2411", None),
    ],
    "qwen": [
        ("qwen-max", None), ("qwen-plus", None), ("qwen-turbo", None),
        ("qwen-long", None), ("qwen3-coder-plus", None), ("qwen3-coder-flash", None),
        ("qwen-vl-max", None), ("qwen-vl-plus", None),
        ("qwen-math-plus", None), ("qwq-plus", None),
    ],
    "kimi": [
        ("kimi-k2-0711-preview", None), ("kimi-k2-turbo-preview", None),
        ("kimi-latest", None), ("kimi-thinking-preview", None),
        ("moonshot-v1-8k", None), ("moonshot-v1-32k", None),
        ("moonshot-v1-128k", None), ("moonshot-v1-auto", None),
    ],
    "glm": [
        ("glm-4-flash", "freetier"), ("glm-4-flashx", "freetier"),
        ("glm-4.5-flash", "freetier"),
        ("glm-4.5", None), ("glm-4.5-air", None), ("glm-4.5-x", None),
        ("glm-4.5-airx", None), ("glm-4-plus", None), ("glm-4-air", None),
        ("glm-4-airx", None), ("glm-4-long", None), ("glm-4v-plus", None),
        ("glm-z1-air", None),
    ],
}

FREE_SUFFIX = "  (Free — No API Key needed)"
FREETIER_SUFFIX = "  (Free)"


def model_display(model_id, tag):
    """Display string for the model dropdown."""
    if tag == "free":
        return model_id + FREE_SUFFIX
    if tag == "freetier":
        return model_id + FREETIER_SUFFIX
    return model_id


def strip_model_suffix(name):
    """Turn a display string back into the raw model id."""
    for suf in (FREE_SUFFIX, FREETIER_SUFFIX):
        if name.endswith(suf):
            return name[: -len(suf)].strip()
    return name.strip()


def model_tag(provider, model_id):
    """Return 'free' / 'freetier' / None for a provider+model pair."""
    mid = strip_model_suffix(model_id)
    for m, tag in MODEL_CATALOG.get(provider, []):
        if m == mid:
            return tag
    return "free" if provider == "ollama" else None

AGENTS = [
    ("Planner Agent",       "Strategic roadmap & audit",  PURPLE, ("audit", "plan", "roadmap", "analy", "scan")),
    ("Coding Agent",        "Implementing improvements",  BLUE,   ("implement", "improv", "code", "edit", "write", "apply", "patch")),
    ("Testing Agent",       "Running validations",        GREEN,  ("test", "valid", "check", "run")),
    ("Review Agent",        "Measuring quality",          TEAL,   ("measur", "qualit", "evaluat", "review", "score")),
    ("Optimization Agent",  "Tuning performance",         ORANGE, ("optim", "perf", "refactor", "tune")),
    ("Documentation Agent", "Updating documentation",     YELLOW, ("doc", "readme", "comment", "changelog")),
]


def _try_env_key(provider: str) -> str:
    info = PROVIDER_DEFAULTS.get(provider, {})
    env_name = info.get("key_env", "")
    if env_name:
        val = os.environ.get(env_name, "")
        if val:
            return val[:4] + "····" + val[-4:] if len(val) > 8 else "····"
    return ""


# ═══════════════════════════════════════════════════════════════════
# ── TOAST NOTIFICATION ────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
class Toast:
    """Non-blocking notification that auto-dismisses."""

    def __init__(self, root):
        self._root = root
        self._queue = []
        self._showing = False

    def show(self, message, kind="info", duration=3200):
        colors = {"info": (BLUE, TOAST_INFO_BG), "success": (GREEN, TOAST_OK_BG),
                  "error": (RED, TOAST_ERR_BG), "warn": (ORANGE, TOAST_WARN_BG)}
        accent, bg = colors.get(kind, colors["info"])
        self._queue.append((message, accent, bg, duration))
        if not self._showing:
            self._pop()

    def _pop(self):
        if not self._queue:
            self._showing = False
            return
        self._showing = True
        msg, accent, bg, dur = self._queue.pop(0)
        frame = tk.Frame(self._root, bg=accent, highlightthickness=0)
        frame.place(relx=1.0, rely=0.0, anchor="ne", x=-24, y=74)
        inner = tk.Frame(frame, bg=bg)
        inner.pack(padx=2, pady=2)
        tk.Label(inner, text=f"  ● {msg}  ", bg=bg, fg=FG,
                 font=(UI_FONT, 9, "bold"), padx=14, pady=8).pack()
        self._root.after(dur, lambda: self._dismiss(frame))

    def _dismiss(self, frame):
        try:
            frame.destroy()
        except Exception:
            pass
        self._root.after(200, self._pop)


# ═══════════════════════════════════════════════════════════════════
# ── TOOLTIP ───────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
class ToolTip:
    def __init__(self, widget, text, delay=350):
        self._widget = widget
        self._text = text
        self._delay = delay
        self._tip = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._cancel)

    def _schedule(self, event):
        self._after_id = self._widget.after(self._delay, self._show)

    def _cancel(self, event=None):
        if self._after_id:
            self._widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        x = self._widget.winfo_rootx() + 16
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 6
        self._tip = tk.Toplevel(self._widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self._tip, text=self._text, bg=CARD3, fg=FG2,
                 font=(UI_FONT, 8), padx=10, pady=5, relief=tk.SOLID, bd=0,
                 highlightbackground=BORDER2, highlightthickness=1).pack()

    def _hide(self):
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


# ═══════════════════════════════════════════════════════════════════
# ── HOVER BUTTON ──────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
class HBtn(tk.Button):
    """Button with hover color change."""

    def __init__(self, parent, bg_n, bg_h, fg_n="white", fg_h=None, **kw):
        self._bg_n, self._bg_h = bg_n, bg_h
        self._fg_n, self._fg_h = fg_n, fg_h or fg_n
        super().__init__(parent, bg=bg_n, fg=fg_n,
                         activebackground=bg_h, activeforeground=self._fg_h,
                         relief=tk.FLAT, bd=0, cursor="hand2",
                         highlightthickness=0, **kw)
        self.bind("<Enter>", lambda e: self.configure(bg=self._bg_h, fg=self._fg_h))
        self.bind("<Leave>", lambda e: self.configure(bg=self._bg_n, fg=self._fg_n))


# ═══════════════════════════════════════════════════════════════════
# ── MAIN APPLICATION ──────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
class AICoderApp:
    CONFIG_FILE = Path.home() / ".aicoder_config.json"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AutoAgent")
        self._load_config()
        self._theme = self._saved_config.get("theme", "dark")
        apply_palette(self._theme)
        self.root.geometry(self._saved_config.get("geometry", "1380x880"))
        self.root.minsize(1100, 720)
        try:
            self.root.state("zoomed" if self._saved_config.get("zoomed", True)
                            else "normal")
        except Exception:
            pass
        self.root.configure(bg=BG)
        self._style_ttk()
        self._set_taskbar_icon(root)
        root.report_callback_exception = self._on_error
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._engine_thread = None
        self._engine = None
        self._running = False
        self._update_queue = queue.Queue()
        self._iteration = 0
        self._max_iter = 100
        self._current_quality = 0.0
        self._quality_history = []
        self._start_time = 0.0
        self._active_agent = None
        self._agent_widgets = {}
        self._nav_items = {}
        self._activity_log = []
        self._explorer_cwd = None
        self._toasts = Toast(root)

        self._make_vars()
        try:
            self._build_ui()
        except Exception as e:
            import traceback; traceback.print_exc()
            messagebox.showerror("UI Error", str(e)); raise
        self._bind_keys()
        self._poll_queue()
        self._tick_resources()
        self._animate_pulse()

    def _on_error(self, exc, val, tb):
        import traceback; traceback.print_exception(exc, val, tb)
        try:
            self._toasts.show(str(val)[:100], "error", 5000)
        except Exception:
            pass

    def _style_ttk(self):
        """Dark ttk theme — keeps comboboxes and scrollbars from
        rendering in the default light Windows style."""
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("TCombobox", fieldbackground=CARD, background=CARD2,
                     foreground=FG, arrowcolor=FG_DIM, bordercolor=BORDER2,
                     lightcolor=CARD, darkcolor=CARD, insertcolor=FG,
                     selectbackground=CARD3, selectforeground=FG, padding=4)
        st.map("TCombobox",
               fieldbackground=[("readonly", CARD), ("disabled", BG2)],
               foreground=[("disabled", FG_FAINT)],
               background=[("active", CARD3)])
        st.configure("Vertical.TScrollbar", background=CARD2, troughcolor=BG2,
                     bordercolor=BG2, arrowcolor=FG_DIM,
                     lightcolor=CARD2, darkcolor=CARD2)
        st.map("Vertical.TScrollbar", background=[("active", CARD3)])
        # The combobox dropdown is a plain Tk listbox — style it globally
        self.root.option_add("*TCombobox*Listbox.background", CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", BLUE)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")
        self.root.option_add("*TCombobox*Listbox.borderWidth", 0)

    def _on_close(self):
        """Persist everything (settings + window state) on exit."""
        try:
            if getattr(self, "_autosave_job", None):
                self.root.after_cancel(self._autosave_job)
        except Exception:
            pass
        self._save_config()
        self.root.destroy()

    # ── Theme switching ──────────────────────────────────
    def _set_theme(self, name, reopen_settings=False):
        if name not in PALETTES or name == self._theme:
            return
        self._theme = name
        apply_palette(name)
        self._save_config()
        self._rebuild_ui()
        if reopen_settings:
            self._open_settings()
        self._toasts.show(f"{name.capitalize()} theme applied", "success", 2000)

    def _toggle_theme(self):
        self._set_theme("light" if self._theme == "dark" else "dark")

    def _rebuild_ui(self):
        """Re-skin everything in place after a palette change."""
        # The goal placeholder must not survive the rebuild as real text
        if getattr(self, "_goal_ph_on", False):
            self._goal_var.set("")
        for w in self.root.winfo_children():
            w.destroy()
        self._agent_widgets = {}
        self._nav_items = {}
        self.root.configure(bg=BG)
        self._style_ttk()
        self._build_ui()
        # Replay the session log into the fresh widgets
        try:
            for ts, text, tag in self._activity_log[-400:]:
                self._output_text.insert(tk.END, f"{ts}  ", "time")
                self._output_text.insert(tk.END, text + "\n", tag)
                self._activity_text.insert(tk.END, f"{ts}  ", "time")
                self._activity_text.insert(tk.END, text + "\n", tag)
            self._output_text.see(tk.END)
            self._activity_text.see(tk.END)
        except Exception:
            pass
        # Restore run-state visuals
        if self._running:
            self._run_btn.configure(state=tk.DISABLED)
            self._stop_btn.configure(state=tk.NORMAL)
            self._engine_state_lbl.config(text="Running", fg=GREEN)
            self._engine_dot.config(fg=GREEN)
            self._status_lbl.config(text="Engine running")
            self._status_dot.config(fg=GREEN)

    @staticmethod
    def _set_taskbar_icon(root):
        """Set the taskbar/titlebar icon from logo.png.

        Tk's Windows icon loader only understands classic BMP-format
        .ico files (PNG-compressed entries are rejected), so we build
        one pixel-by-pixel and hand it to every toplevel.
        """
        import math
        logo_path = Path(__file__).resolve().parent / "logo.png"
        if logo_path.exists():
            try:
                img = tk.PhotoImage(file=str(logo_path))
                # Subsample to ~32px for the titlebar photo icon
                w = img.width()
                factor = max(1, w // 32)
                icon = img.subsample(factor, factor)
                root._icon_img = icon
                root._icon_src = img  # keep reference
                root.iconphoto(True, icon)
                # Real BMP-format .ico for the Windows taskbar
                if os.name == "nt":
                    try:
                        AICoderApp._apply_windows_ico(root, img, logo_path)
                    except Exception:
                        pass
                return
            except Exception:
                pass
        # Fallback: programmatic hex
        size = 32
        img = tk.PhotoImage(width=size, height=size)
        cx, cy, r = size//2, size//2, 13
        for y in range(size):
            for x in range(size):
                dx, dy = x - cx, y - cy
                dist = math.sqrt(dx*dx + dy*dy)
                angle = math.atan2(dy, dx)
                sector = (angle + math.pi/6) % (math.pi/3)
                hex_r = r * math.cos(math.pi/6) / max(math.cos(sector - math.pi/6), 0.001)
                if dist <= hex_r:
                    if dist >= hex_r - 2:
                        img.put("#4f8fff", (x, y))
                    elif dist <= 3:
                        img.put("#00e5ff", (x, y))
                    else:
                        img.put("#0a1628", (x, y))
                elif dist <= hex_r + 2:
                    img.put("#1a3060", (x, y))
        for i in range(6):
            nx = int(cx + (r-2)*math.cos(math.radians(60*i - 30)))
            ny = int(cy + (r-2)*math.sin(math.radians(60*i - 30)))
            for dy2 in range(-1, 2):
                for dx2 in range(-1, 2):
                    if 0 <= nx+dx2 < size and 0 <= ny+dy2 < size:
                        img.put("#00e5ff", (nx+dx2, ny+dy2))
        root._icon_img = img
        root.iconphoto(True, img)

    @staticmethod
    def _apply_windows_ico(root, img, logo_path):
        """Build a classic BMP-format .ico from the logo and apply it.

        Each frame is written as a 32-bit BGRA bitmap with an AND mask
        — the only encoding Tk's iconbitmap accepts on Windows.
        """
        import struct
        ico_path = Path.home() / ".autoagent.ico"
        legacy = Path.home() / ".autoagent_icon.ico"  # old PNG-in-ICO cache (invalid)
        if legacy.exists():
            try:
                legacy.unlink()
            except Exception:
                pass
        stale = (not ico_path.exists() or
                 ico_path.stat().st_mtime < logo_path.stat().st_mtime)
        if stale:
            w = img.width()
            frames = []
            for target in (16, 32, 48):
                f = max(1, round(w / target))
                frames.append(img.subsample(f, f))
            entries, blobs = [], []
            offset = 6 + 16 * len(frames)
            for ph in frames:
                fw, fh = ph.width(), ph.height()
                mask_row_len = ((fw + 31) // 32) * 4
                xor, mask = bytearray(), bytearray()
                for y in range(fh - 1, -1, -1):  # BMP rows are bottom-up
                    mrow = bytearray(mask_row_len)
                    for x in range(fw):
                        try:
                            tr = ph.tk.call(ph.name, "transparency", "get", x, y)
                            tr = bool(int(tr))
                        except Exception:
                            tr = False
                        if tr:
                            xor += b"\x00\x00\x00\x00"
                            mrow[x // 8] |= 0x80 >> (x % 8)
                        else:
                            px = ph.get(x, y)
                            if isinstance(px, str):
                                r, g, b = (int(v) for v in px.split())
                            else:
                                r, g, b = px[0], px[1], px[2]
                            xor += bytes((b, g, r, 255))
                    mask += mrow
                hdr = struct.pack("<IiiHHIIiiII", 40, fw, fh * 2, 1, 32, 0,
                                  len(xor) + len(mask), 0, 0, 0, 0)
                blob = hdr + bytes(xor) + bytes(mask)
                entries.append(struct.pack("<BBBBHHII", fw % 256, fh % 256,
                                           0, 0, 1, 32, len(blob), offset))
                blobs.append(blob)
                offset += len(blob)
            ico_path.write_bytes(struct.pack("<HHH", 0, 1, len(frames)) +
                                 b"".join(entries) + b"".join(blobs))
        root.iconbitmap(default=str(ico_path))

    # ── Config ────────────────────────────────────────────────
    def _load_config(self):
        self._saved_config = {}
        try:
            if self.CONFIG_FILE.exists():
                self._saved_config = json.loads(self.CONFIG_FILE.read_text())
        except Exception:
            self._saved_config = {}
        # Older versions could save the goal-box placeholder as a goal
        if self._saved_config.get("goal") == "Enter your improvement goal…":
            self._saved_config["goal"] = ""

    def _make_vars(self):
        c = self._saved_config
        self._prov_var = tk.StringVar(value=c.get("provider", "openai"))
        self._model_var = tk.StringVar(value=c.get("model", "gpt-4o"))
        self._api_key_var = tk.StringVar(value=c.get("api_key", ""))
        self._work_var = tk.StringVar(value=c.get("workspace", str(Path.cwd())))
        self._target_var = tk.StringVar(value=str(c.get("target", "85")))
        self._max_var = tk.StringVar(value=str(c.get("max_iterations", "100")))
        self._goal_var = tk.StringVar(value=c.get("goal", ""))
        # Auto-save: any settings change is persisted moments later,
        # so nothing is ever lost between sessions.
        self._autosave_job = None
        for v in (self._prov_var, self._model_var, self._api_key_var,
                  self._work_var, self._target_var, self._max_var,
                  self._goal_var):
            v.trace_add("write", self._schedule_autosave)

    def _model_id(self):
        """Raw model id with any '(Free …)' suffix stripped."""
        return strip_model_suffix(self._model_var.get())

    def _model_is_keyless(self):
        """True when the chosen model runs without any API key."""
        return model_tag(self._prov_var.get(), self._model_var.get()) == "free"

    def _schedule_autosave(self, *_):
        try:
            if self._autosave_job:
                self.root.after_cancel(self._autosave_job)
            self._autosave_job = self.root.after(800, self._autosave)
        except Exception:
            pass

    def _autosave(self):
        self._autosave_job = None
        self._save_config()
        try:
            if hasattr(self, "_badge_frame"):
                self._refresh_badges()
        except Exception:
            pass

    def _save_config(self):
        data = {
            "provider": self._prov_var.get(), "model": self._model_id(),
            "api_key": self._api_key_var.get(), "workspace": self._work_var.get(),
            "target": self._target_var.get(), "max_iterations": self._max_var.get(),
            "goal": self._goal_value(),
            "theme": getattr(self, "_theme", "dark"),
        }
        try:
            zoomed = self.root.state() == "zoomed"
            data["zoomed"] = zoomed
            data["geometry"] = (self.root.geometry() if not zoomed else
                                self._saved_config.get("geometry", "1380x880"))
        except Exception:
            pass
        self._saved_config.update(data)
        try:
            # Atomic write — a crash mid-save can never corrupt the file
            tmp = self.CONFIG_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2))
            os.replace(tmp, self.CONFIG_FILE)
        except Exception:
            pass

    def _bind_keys(self):
        self.root.bind("<Control-Return>", lambda e: self._start_engine())
        self.root.bind("<Escape>", lambda e: self._stop_engine())
        self.root.bind("<Control-s>", lambda e: self._save_config())

    # ── UI Primitives ─────────────────────────────────────────
    def _card(self, parent, pad=14, accent=None, glow=False):
        """Glass-style card with optional accent & glow border."""
        brd_color = GLOW_BRD if glow else BORDER
        outer = tk.Frame(parent, bg=brd_color, highlightthickness=0, bd=0)
        inner = tk.Frame(outer, bg=CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        if accent:
            tk.Frame(inner, bg=accent, height=2).pack(fill=tk.X)
        body = tk.Frame(inner, bg=CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)
        return outer, body

    def _section_title(self, body, title, icon="", color=FG_DIM):
        row = tk.Frame(body, bg=CARD)
        row.pack(fill=tk.X, pady=(0, 10))
        if icon:
            tk.Label(row, text=icon, bg=CARD, fg=color,
                     font=(UI_FONT, 11)).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(row, text=title, bg=CARD, fg=FG2,
                 font=(UI_FONT, 10, "bold")).pack(side=tk.LEFT)
        return row

    def _btn(self, parent, text, cmd, bg=BLUE, bg_h=BLUE_HL, fg="white",
             font=None, padx=16, pady=7, tip=None):
        b = HBtn(parent, bg_n=bg, bg_h=bg_h, fg_n=fg, text=text, command=cmd,
                 font=font or (UI_FONT, 9, "bold"), padx=padx, pady=pady)
        if tip:
            ToolTip(b, tip)
        return b

    # ── Build UI ──────────────────────────────────────────────
    def _build_ui(self):
        self._build_sidebar()
        container = tk.Frame(self.root, bg=BG)
        container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_topbar(container)
        self._body = tk.Frame(container, bg=BG)
        self._body.pack(fill=tk.BOTH, expand=True)
        self._pages = {}
        self._build_page_dashboard()
        self._build_page_projects()
        self._build_page_agents_view()
        self._build_page_activity()
        self._build_page_explorer()
        self._build_page_metrics()
        self._build_page_tools()
        self._show_page("Dashboard")
        self._build_statusbar(container)

    # ── Sidebar ───────────────────────────────────────────────
    def _build_sidebar(self):
        bar = tk.Frame(self.root, bg=SIDEBAR, width=228)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        bar.pack_propagate(False)
        # Vertical accent line
        tk.Frame(bar, bg=BORDER, width=1).pack(side=tk.RIGHT, fill=tk.Y)

        # Logo — load from logo.png
        logo_f = tk.Frame(bar, bg=SIDEBAR)
        logo_f.pack(fill=tk.X, padx=18, pady=(22, 24))
        logo_path = Path(__file__).resolve().parent / "logo.png"
        self._logo_img = None
        if logo_path.exists():
            try:
                src = tk.PhotoImage(file=str(logo_path))
                # Subsample to ~40px
                factor = max(1, src.width() // 40)
                self._logo_img = src.subsample(factor, factor)
                self._logo_src = src  # prevent GC
                lbl_img = tk.Label(logo_f, image=self._logo_img, bg=SIDEBAR)
                lbl_img.pack(side=tk.LEFT)
            except Exception:
                self._logo_img = None
        if not self._logo_img:
            # Fallback: canvas hex
            import math as _m
            cv = tk.Canvas(logo_f, width=44, height=44, bg=SIDEBAR, highlightthickness=0)
            cv.pack(side=tk.LEFT)
            cx, cy, r = 22, 22, 18
            hex_pts = [(cx + r*_m.cos(_m.radians(60*i - 30)),
                        cy + r*_m.sin(_m.radians(60*i - 30))) for i in range(6)]
            cv.create_polygon([c for p in hex_pts for c in p],
                              fill="#0a1628", outline=BLUE, width=2)
            cv.create_oval(cx-3, cy-3, cx+3, cy+3, fill=CYAN, outline="")
        lbl_f = tk.Frame(logo_f, bg=SIDEBAR)
        lbl_f.pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(lbl_f, text="AutoAgent", bg=SIDEBAR, fg=FG,
                 font=(TITLE_FONT, 14, "bold")).pack(anchor=tk.W)
        tk.Label(lbl_f, text="Self-Improving AI Coder", bg=SIDEBAR, fg=FG_FAINT,
                 font=(UI_FONT, 7)).pack(anchor=tk.W)

        # Separator
        tk.Frame(bar, bg=BORDER, height=1).pack(fill=tk.X, padx=18)

        # Section label
        tk.Label(bar, text="MENU", bg=SIDEBAR, fg=FG_FAINT,
                 font=(UI_FONT, 7, "bold")).pack(anchor=tk.W, padx=22, pady=(16, 8))

        nav = [
            ("⬡", "Dashboard"),  ("◫", "Projects"),   ("◆", "Agents"),
            ("≋", "Agent Activity"), ("⟨⟩", "Code Explorer"),
            ("◉", "Metrics"),    ("⚒", "Tools"),      ("⚙", "Settings"),
        ]
        for icon, name in nav:
            self._make_nav_item(bar, icon, name)
        self._select_nav("Dashboard")

        # Spacer
        tk.Frame(bar, bg=SIDEBAR).pack(fill=tk.BOTH, expand=True)

        # Engine status card
        tk.Frame(bar, bg=BORDER, height=1).pack(fill=tk.X, padx=18, pady=(0, 12))
        ef = tk.Frame(bar, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        ef.pack(fill=tk.X, padx=14, pady=(0, 8))
        eb = tk.Frame(ef, bg=CARD)
        eb.pack(fill=tk.X, padx=12, pady=10)
        tk.Label(eb, text="ENGINE STATUS", bg=CARD, fg=FG_FAINT,
                 font=(UI_FONT, 7, "bold")).pack(anchor=tk.W)
        sf = tk.Frame(eb, bg=CARD)
        sf.pack(anchor=tk.W, pady=(4, 2))
        self._engine_dot = tk.Label(sf, text="●", bg=CARD, fg=FG_FAINT, font=(UI_FONT, 11))
        self._engine_dot.pack(side=tk.LEFT, padx=(0, 6))
        self._engine_state_lbl = tk.Label(sf, text="Idle", bg=CARD, fg=FG_DIM,
                                          font=(UI_FONT, 10, "bold"))
        self._engine_state_lbl.pack(side=tk.LEFT)
        self._engine_proj_lbl = tk.Label(eb, text="No workspace set", bg=CARD, fg=FG_FAINT,
                                         font=(UI_FONT, 8), wraplength=175, justify=tk.LEFT)
        self._engine_proj_lbl.pack(anchor=tk.W, pady=(2, 0))

        # Provider quick-switch
        pf = tk.Frame(bar, bg=SIDEBAR)
        pf.pack(fill=tk.X, padx=18, pady=(4, 18))
        self._side_prov_lbl = tk.Label(pf, text="", bg=SIDEBAR, fg=FG2,
                                       font=(UI_FONT, 9, "bold"))
        self._side_prov_lbl.pack(side=tk.LEFT)
        self._btn(pf, "⚙", self._open_settings, bg=CARD2, bg_h=CARD3, fg=FG_DIM,
                  font=(UI_FONT, 9), padx=8, pady=3, tip="Settings").pack(side=tk.RIGHT)
        self._refresh_provider_labels()

    def _make_nav_item(self, parent, icon, name):
        row = tk.Frame(parent, bg=SIDEBAR, cursor="hand2")
        row.pack(fill=tk.X, padx=10, pady=1)
        ind = tk.Frame(row, bg=SIDEBAR, width=3)
        ind.pack(side=tk.LEFT, fill=tk.Y)
        ic = tk.Label(row, text=icon, bg=SIDEBAR, fg=FG_FAINT, font=(UI_FONT, 11), width=2)
        ic.pack(side=tk.LEFT, padx=(8, 7), pady=8)
        lbl = tk.Label(row, text=name, bg=SIDEBAR, fg=FG_DIM, font=(UI_FONT, 9))
        lbl.pack(side=tk.LEFT)
        self._nav_items[name] = (row, ind, ic, lbl)
        for w in (row, ic, lbl):
            w.bind("<Button-1>", lambda e, n=name: self._on_nav_click(n))
            w.bind("<Enter>", lambda e, n=name: self._nav_hover(n, True))
            w.bind("<Leave>", lambda e, n=name: self._nav_hover(n, False))

    def _nav_hover(self, name, entering):
        if name == self._sel_nav:
            return
        row, ind, ic, lbl = self._nav_items[name]
        bg = BG3 if entering else SIDEBAR
        for w in (row, ic, lbl):
            w.configure(bg=bg)
        ind.configure(bg=bg)

    _sel_nav = "Dashboard"

    def _select_nav(self, name):
        for n, (row, ind, ic, lbl) in self._nav_items.items():
            active = (n == name)
            bg = BG3 if active else SIDEBAR
            row.configure(bg=bg); ic.configure(bg=bg); lbl.configure(bg=bg)
            ind.configure(bg=CYAN if active else bg)
            ic.configure(fg=CYAN if active else FG_FAINT)
            lbl.configure(fg=FG if active else FG_DIM,
                          font=(UI_FONT, 9, "bold") if active else (UI_FONT, 9))
        self._sel_nav = name

    def _on_nav_click(self, name):
        self._select_nav(name)
        if name == "Settings":
            self._open_settings()
        else:
            self._show_page(name)

    def _show_page(self, name):
        for f in self._pages.values():
            f.pack_forget()
        p = self._pages.get(name)
        if p:
            p.pack(fill=tk.BOTH, expand=True)
        if name == "Projects":
            self._refresh_projects()
        elif name == "Code Explorer":
            self._refresh_explorer()
        elif name == "Agent Activity":
            self._refresh_activity_view()
        elif name == "Metrics":
            self._refresh_metrics_view()

    # ── Top Bar ───────────────────────────────────────────────
    def _build_topbar(self, parent):
        # Accent line
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)
        bar = tk.Frame(parent, bg=TOPBAR, height=68)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

        inner = tk.Frame(bar, bg=TOPBAR)
        inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=13)

        # Goal box
        gbox = tk.Frame(inner, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
        gbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(gbox, text="⎯⎯►", bg=CARD, fg=CYAN,
                 font=(MONO_FONT, 10, "bold")).pack(side=tk.LEFT, padx=(14, 8))
        self._goal_entry = tk.Entry(gbox, textvariable=self._goal_var, bg=CARD, fg=FG,
                                    insertbackground=CYAN, relief=tk.FLAT, bd=0,
                                    font=(UI_FONT, 11))
        self._goal_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12), pady=10)
        self._goal_ph = "Enter your improvement goal…"
        self._install_placeholder()
        # Focus glow on the goal field
        self._goal_entry.bind(
            "<FocusIn>", lambda _: gbox.config(highlightbackground=GLOW_BRD), add="+")
        self._goal_entry.bind(
            "<FocusOut>", lambda _: gbox.config(highlightbackground=BORDER2), add="+")

        # Badges
        self._badge_frame = tk.Frame(inner, bg=TOPBAR)
        self._badge_frame.pack(side=tk.LEFT, padx=16)
        self._refresh_badges()

        # Run / Stop
        self._run_btn = self._btn(inner, "▶  Run", self._start_engine,
                                  bg=BLUE, bg_h=BLUE_HL, tip="Ctrl+Enter")
        self._run_btn.pack(side=tk.LEFT, padx=(4, 8))
        self._stop_btn = self._btn(inner, "■  Stop", self._stop_engine,
                                   bg=CARD2, bg_h=STOP_HOVER, fg=FG_DIM, tip="Escape")
        self._stop_btn.configure(state=tk.DISABLED)
        self._stop_btn.pack(side=tk.LEFT)
        # Theme toggle
        self._theme_btn = self._btn(
            inner, "☀" if self._theme == "dark" else "☾", self._toggle_theme,
            bg=CARD2, bg_h=CARD3, fg=FG_DIM, padx=10,
            tip="Switch light / dark theme")
        self._theme_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _install_placeholder(self):
        e = self._goal_entry
        if not self._goal_var.get():
            e.insert(0, self._goal_ph); e.configure(fg=FG_FAINT)
            self._goal_ph_on = True
        else:
            self._goal_ph_on = False
        e.bind("<FocusIn>", lambda _: (e.delete(0, tk.END), e.configure(fg=FG),
               setattr(self, "_goal_ph_on", False)) if self._goal_ph_on else None)
        e.bind("<FocusOut>", lambda _: (e.insert(0, self._goal_ph), e.configure(fg=FG_FAINT),
               setattr(self, "_goal_ph_on", True)) if not e.get().strip() else None)

    def _goal_value(self):
        return "" if getattr(self, "_goal_ph_on", False) else self._goal_var.get().strip()

    def _refresh_badges(self):
        for w in self._badge_frame.winfo_children():
            w.destroy()
        badges = [(self._model_id(), BLUE), (self._prov_var.get(), PURPLE)]
        if self._model_is_keyless():
            badges.append(("FREE — No API Key", GREEN))
        elif model_tag(self._prov_var.get(), self._model_var.get()) == "freetier":
            badges.append(("FREE", GREEN))
        for text, color in badges:
            if not text:
                continue
            c = tk.Frame(self._badge_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            c.pack(side=tk.LEFT, padx=3)
            tk.Label(c, text="●", bg=CARD, fg=color, font=(UI_FONT, 6)).pack(
                side=tk.LEFT, padx=(10, 4), pady=5)
            tk.Label(c, text=text[:26], bg=CARD, fg=FG_DIM,
                     font=(UI_FONT, 8, "bold")).pack(side=tk.LEFT, padx=(0, 10))

    def _refresh_provider_labels(self):
        self._side_prov_lbl.configure(text=self._prov_var.get().upper())

    # ── Status Bar ────────────────────────────────────────────
    def _build_statusbar(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)
        sb = tk.Frame(parent, bg=BG2, height=28)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        sb.pack_propagate(False)
        self._status_dot = tk.Label(sb, text="●", bg=BG2, fg=FG_FAINT, font=(UI_FONT, 9))
        self._status_dot.pack(side=tk.LEFT, padx=(16, 5))
        self._status_lbl = tk.Label(sb, text="Ready", bg=BG2, fg=FG_DIM, font=(UI_FONT, 8))
        self._status_lbl.pack(side=tk.LEFT)
        self._foot_iter = tk.Label(sb, text="", bg=BG2, fg=FG_DIM, font=(UI_FONT, 8))
        self._foot_iter.pack(side=tk.RIGHT, padx=16)
        tk.Label(sb, text="Ctrl+↵ Run  ·  Esc Stop  ·  settings auto-save",
                 bg=BG2, fg=FG_FAINT, font=(UI_FONT, 7)).pack(side=tk.RIGHT, padx=16)
        tk.Label(sb, text="AutoAgent v0.1.0", bg=BG2, fg=FG_FAINT,
                 font=(UI_FONT, 7)).pack(side=tk.RIGHT, padx=(0, 4))

    # ── Animated pulse ────────────────────────────────────────
    def _animate_pulse(self):
        if self._running:
            colors = [CYAN, GREEN, BLUE, GREEN]
            c = colors[int(time.time() * 2) % 4]
            self._status_dot.config(fg=c)
            self._engine_dot.config(fg=c)
        self.root.after(450, self._animate_pulse)

    # ── Right Panel ───────────────────────────────────────────
    def _build_right_panel(self, parent):
        panel = tk.Frame(parent, bg=BG, width=286)
        panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 16), pady=(10, 12))
        panel.pack_propagate(False)

        # System Overview
        outer, b = self._card(panel, accent=BLUE, glow=True)
        outer.pack(fill=tk.X, pady=(0, 10))
        self._section_title(b, "System Overview", "◉", CYAN)
        self._sys_metrics = {}
        for key, label, color in (("quality", "Quality Score", GREEN),
                                  ("iterations", "Iterations", BLUE),
                                  ("snapshots", "Snapshots", PURPLE),
                                  ("elapsed", "Elapsed", TEAL)):
            self._make_metric_row(b, key, label, color)

        # Active Tasks
        outer, b = self._card(panel, accent=ORANGE)
        outer.pack(fill=tk.X, pady=(0, 10))
        self._section_title(b, "Active Tasks", "◆", ORANGE)
        self._tasks_box = tk.Frame(b, bg=CARD)
        self._tasks_box.pack(fill=tk.X)
        self._set_tasks(["Waiting for engine…"], idle=True)

        # Resources
        outer, b = self._card(panel, accent=TEAL)
        outer.pack(fill=tk.BOTH, expand=True)
        self._section_title(b, "Resources", "⬡", TEAL)
        gauges = tk.Frame(b, bg=CARD)
        gauges.pack(fill=tk.X, pady=(4, 0))
        self._res_canvases = {}
        for i, (key, lbl, color) in enumerate((("cpu", "CPU", CYAN), ("mem", "RAM", PURPLE))):
            col = tk.Frame(gauges, bg=CARD)
            col.grid(row=0, column=i, padx=14, pady=4)
            cv = tk.Canvas(col, width=94, height=94, bg=CARD, highlightthickness=0)
            cv.pack()
            tk.Label(col, text=lbl, bg=CARD, fg=FG_DIM, font=(UI_FONT, 8, "bold")).pack(pady=(4, 0))
            self._res_canvases[key] = cv
            self._draw_ring(cv, 0, color, "—")

    def _make_metric_row(self, parent, key, label, color):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill=tk.X, pady=5)
        left = tk.Frame(row, bg=CARD)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(left, text=label, bg=CARD, fg=FG_FAINT, font=(UI_FONT, 8)).pack(anchor=tk.W)
        val = tk.Label(left, text="—", bg=CARD, fg=FG, font=(UI_FONT, 16, "bold"))
        val.pack(anchor=tk.W)
        spark = tk.Canvas(row, width=82, height=34, bg=CARD, highlightthickness=0)
        spark.pack(side=tk.RIGHT)
        self._sys_metrics[key] = {"val": val, "spark": spark, "color": color, "hist": []}

    def _set_tasks(self, items, idle=False):
        for w in self._tasks_box.winfo_children():
            w.destroy()
        for it in items[:6]:
            r = tk.Frame(self._tasks_box, bg=CARD)
            r.pack(fill=tk.X, pady=2)
            dot_c = FG_FAINT if idle else GREEN
            tk.Label(r, text="●", bg=CARD, fg=dot_c, font=(UI_FONT, 7)).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(r, text=it[:38], bg=CARD, fg=FG_DIM if idle else FG2,
                     font=(UI_FONT, 8), anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ── Center Dashboard ──────────────────────────────────────
    def _build_center(self, parent):
        center = tk.Frame(parent, bg=BG)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=(10, 12))
        for c in range(2):
            center.columnconfigure(c, weight=1, uniform="col")
        center.rowconfigure(1, weight=1)
        center.rowconfigure(2, weight=1)
        self._build_objective(center)
        self._build_roadmap(center)
        self._build_agents(center)
        self._build_activity(center)
        self._build_changes(center)

    def _build_objective(self, parent):
        outer, b = self._card(parent, accent=GREEN, glow=True)
        outer.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        b.columnconfigure(0, weight=1)
        left = tk.Frame(b, bg=CARD)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        tk.Label(left, text="CURRENT OBJECTIVE", bg=CARD, fg=FG_FAINT,
                 font=(UI_FONT, 7, "bold")).pack(anchor=tk.W)
        self._obj_lbl = tk.Label(left, text="No active objective", bg=CARD, fg=FG,
                                 font=(TITLE_FONT, 16, "bold"), anchor=tk.W,
                                 justify=tk.LEFT, wraplength=520)
        self._obj_lbl.pack(anchor=tk.W, pady=(6, 14), fill=tk.X)
        prow = tk.Frame(left, bg=CARD)
        prow.pack(fill=tk.X)
        tk.Label(prow, text="Total Progress", bg=CARD, fg=FG_DIM, font=(UI_FONT, 8)).pack(side=tk.LEFT)
        self._tot_pct_lbl = tk.Label(prow, text="0%", bg=CARD, fg=GREEN,
                                     font=(UI_FONT, 9, "bold"))
        self._tot_pct_lbl.pack(side=tk.RIGHT)
        self._tot_bar = tk.Canvas(left, height=10, bg=CARD, highlightthickness=0)
        self._tot_bar.pack(fill=tk.X, pady=(6, 12))
        self._tot_frac = 0.0
        self._tot_bar.bind("<Configure>", lambda e: self._draw_hbar(self._tot_bar, self._tot_frac, GREEN))
        stat = tk.Frame(left, bg=CARD)
        stat.pack(fill=tk.X)
        self._obj_iter_lbl = tk.Label(stat, text="0 / 0 iterations", bg=CARD, fg=FG_DIM, font=(UI_FONT, 8))
        self._obj_iter_lbl.pack(side=tk.LEFT, padx=(0, 20))
        self._obj_eta_lbl = tk.Label(stat, text="\u2014", bg=CARD, fg=FG_DIM, font=(UI_FONT, 8))
        self._obj_eta_lbl.pack(side=tk.LEFT)
        right = tk.Frame(b, bg=CARD)
        right.grid(row=0, column=1, sticky="e")
        self._gauge = tk.Canvas(right, width=148, height=148, bg=CARD, highlightthickness=0)
        self._gauge.pack()
        tk.Label(right, text="Quality", bg=CARD, fg=FG_DIM, font=(UI_FONT, 8)).pack(pady=(4, 0))
        self._draw_ring(self._gauge, 0, GREEN, "0%", big=True)

    def _build_roadmap(self, parent):
        outer, b = self._card(parent, accent=PURPLE)
        outer.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self._section_title(b, "Improvement Roadmap", "\u2564", PURPLE)
        wrap = tk.Frame(b, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True)
        self._roadmap_text = tk.Text(wrap, wrap=tk.WORD, bg=BG, fg=FG_DIM,
                                     relief=tk.FLAT, bd=0, font=(MONO_FONT, 9),
                                     insertbackground=FG, height=8, padx=6, pady=4)
        sb = ttk.Scrollbar(wrap, command=self._roadmap_text.yview)
        self._roadmap_text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._roadmap_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._roadmap_text.tag_configure("done", foreground=GREEN)
        self._roadmap_text.tag_configure("head", foreground=FG, font=(MONO_FONT, 9, "bold"))
        self._roadmap_text.insert("1.0", "Roadmap appears after first audit.\n")
        self._roadmap_text.configure(state=tk.DISABLED)

    def _build_agents(self, parent):
        outer, b = self._card(parent, accent=BLUE)
        outer.grid(row=1, column=1, sticky="nsew", pady=(0, 10))
        self._section_title(b, "Active Agents", "\u25c6", BLUE)
        grid = tk.Frame(b, bg=CARD)
        grid.pack(fill=tk.BOTH, expand=True)
        for c in range(2):
            grid.columnconfigure(c, weight=1, uniform="ag")
        for i, (name, sub, color, _kw) in enumerate(AGENTS):
            cell = tk.Frame(grid, bg=CARD2, highlightbackground=BORDER, highlightthickness=1)
            cell.grid(row=i // 2, column=i % 2, sticky="nsew", padx=3, pady=3)
            top = tk.Frame(cell, bg=CARD2)
            top.pack(fill=tk.X, padx=9, pady=(8, 0))
            dot = tk.Label(top, text="\u25cf", bg=CARD2, fg=FG_FAINT, font=(UI_FONT, 9))
            dot.pack(side=tk.LEFT)
            tk.Label(top, text=name.replace(" Agent", ""), bg=CARD2, fg=FG,
                     font=(UI_FONT, 9, "bold")).pack(side=tk.LEFT, padx=(6, 0))
            st = tk.Label(cell, text="Idle", bg=CARD2, fg=FG_DIM, font=(UI_FONT, 7), anchor=tk.W)
            st.pack(fill=tk.X, padx=9, pady=(2, 8))
            self._agent_widgets[name] = {"cell": cell, "dot": dot, "st": st, "color": color, "sub": sub}

    def _build_activity(self, parent):
        outer, b = self._card(parent, accent=TEAL)
        outer.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        row = self._section_title(b, "Live Activity", "\u224b", TEAL)
        self._btn(row, "Clear", self._clear_output, bg=CARD2, bg_h=CARD3, fg=FG_DIM,
                  font=(UI_FONT, 7, "bold"), padx=8, pady=2).pack(side=tk.RIGHT)
        wrap = tk.Frame(b, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True)
        self._output_text = tk.Text(wrap, wrap=tk.WORD, bg=BG, fg=FG_DIM,
                                    relief=tk.FLAT, bd=0, font=(MONO_FONT, 9),
                                    insertbackground=FG, height=8, padx=8, pady=6)
        sb = ttk.Scrollbar(wrap, command=self._output_text.yview)
        self._output_text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for tag, cfg in (("phase", {"foreground": CYAN, "font": (MONO_FONT, 9, "bold")}),
                         ("improvement", {"foreground": GREEN}), ("quality", {"foreground": ORANGE}),
                         ("error", {"foreground": RED}), ("success", {"foreground": GREEN, "font": (MONO_FONT, 9, "bold")}),
                         ("dim", {"foreground": FG_FAINT}), ("warn", {"foreground": YELLOW}), ("time", {"foreground": FG_FAINT})):
            self._output_text.tag_configure(tag, **cfg)

    def _build_changes(self, parent):
        outer, b = self._card(parent, accent=ORANGE)
        outer.grid(row=2, column=1, sticky="nsew")
        self._section_title(b, "Recent Changes", "\u27e8\u27e9", ORANGE)
        wrap = tk.Frame(b, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True)
        self._changes_text = tk.Text(wrap, wrap=tk.WORD, bg=BG, fg=FG_DIM,
                                     relief=tk.FLAT, bd=0, font=(MONO_FONT, 9),
                                     insertbackground=FG, height=8, padx=8, pady=6)
        sb = ttk.Scrollbar(wrap, command=self._changes_text.yview)
        self._changes_text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._changes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._changes_text.tag_configure("add", foreground=GREEN)
        self._changes_text.tag_configure("title", foreground=FG, font=(MONO_FONT, 9, "bold"))
        self._changes_text.tag_configure("dim", foreground=FG_FAINT)
        self._changes_text.insert("1.0", "No changes yet.\n", "dim")
        self._changes_text.configure(state=tk.DISABLED)

    # ── Page Builders ───────────────────────────────────
    def _build_page_dashboard(self):
        page = tk.Frame(self._body, bg=BG)
        self._pages["Dashboard"] = page
        self._build_right_panel(page)
        self._build_center(page)

    def _build_page_projects(self):
        page = tk.Frame(self._body, bg=BG)
        self._pages["Projects"] = page
        hdr = tk.Frame(page, bg=BG)
        hdr.pack(fill=tk.X, padx=24, pady=(18, 10))
        tk.Label(hdr, text="Projects", bg=BG, fg=FG, font=(TITLE_FONT, 22, "bold")).pack(side=tk.LEFT)
        self._btn(hdr, "\u21bb Refresh", self._refresh_projects, bg=CARD2, bg_h=CARD3,
                  fg=FG_DIM, font=(UI_FONT, 9, "bold"), padx=12, pady=4).pack(side=tk.RIGHT)
        outer, b = self._card(page, pad=18, accent=BLUE, glow=True)
        outer.pack(fill=tk.X, padx=24, pady=(0, 12))
        self._section_title(b, "Workspace", "\u25eb", BLUE)
        self._proj_path_lbl = tk.Label(b, text=self._work_var.get() or "", bg=CARD, fg=FG2,
                                       font=(MONO_FONT, 9), anchor=tk.W, wraplength=720)
        self._proj_path_lbl.pack(fill=tk.X, pady=(0, 10))
        sr = tk.Frame(b, bg=CARD)
        sr.pack(fill=tk.X)
        self._proj_stats = {}
        for key, label, color in (("files", "Files", BLUE), ("dirs", "Dirs", PURPLE),
                                   ("py", "Python", GREEN), ("size", "Size", TEAL)):
            col = tk.Frame(sr, bg=CARD); col.pack(side=tk.LEFT, padx=(0, 30))
            tk.Label(col, text=label, bg=CARD, fg=FG_FAINT, font=(UI_FONT, 8)).pack(anchor=tk.W)
            v = tk.Label(col, text="\u2014", bg=CARD, fg=FG, font=(UI_FONT, 16, "bold"))
            v.pack(anchor=tk.W); self._proj_stats[key] = v
        outer, b = self._card(page, pad=16, accent=ORANGE)
        outer.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))
        self._section_title(b, "File Listing", "\u25c6", ORANGE)
        wrap = tk.Frame(b, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True)
        self._proj_file_list = tk.Text(wrap, wrap=tk.NONE, bg=BG, fg=FG_DIM,
                                       relief=tk.FLAT, bd=0, font=(MONO_FONT, 9), padx=8, pady=6)
        sb = ttk.Scrollbar(wrap, command=self._proj_file_list.yview)
        self._proj_file_list.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._proj_file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._proj_file_list.tag_configure("dir", foreground=BLUE, font=(MONO_FONT, 9, "bold"))
        self._proj_file_list.tag_configure("py", foreground=GREEN)
        self._proj_file_list.tag_configure("file", foreground=FG_DIM)

    def _refresh_projects(self):
        ws = Path(self._work_var.get())
        self._proj_path_lbl.config(text=str(ws))
        if not ws.exists():
            return
        # Instant: top-level file listing (cheap, one directory read)
        self._proj_file_list.configure(state=tk.NORMAL)
        self._proj_file_list.delete("1.0", tk.END)
        try:
            for entry in sorted(ws.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:100]:
                if entry.name.startswith('.'): continue
                if entry.is_dir(): self._proj_file_list.insert(tk.END, f"\ud83d\udcc1 {entry.name}/\n", "dir")
                elif entry.suffix == ".py": self._proj_file_list.insert(tk.END, f"   {entry.name}\n", "py")
                else: self._proj_file_list.insert(tk.END, f"   {entry.name}\n", "file")
        except Exception: pass
        self._proj_file_list.configure(state=tk.DISABLED)
        # Deep stats: run in background thread so the UI never freezes
        for k in ("files", "dirs", "py"):
            self._proj_stats[k].config(text="\u2026")
        self._proj_stats["size"].config(text="\u2026")
        scan_id = time.time()
        self._proj_scan_id = scan_id
        threading.Thread(target=self._scan_workspace, args=(ws, scan_id), daemon=True).start()

    _SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".venv", "venv", "env",
                  ".idea", ".vscode", "dist", "build", ".aicoder_snapshots"}

    def _scan_workspace(self, ws, scan_id):
        files = dirs = py_n = 0; total = 0
        limit = 20000  # hard cap so huge folders can't hang the scan
        try:
            stack = [ws]
            while stack and files + dirs < limit:
                cur = stack.pop()
                try:
                    with os.scandir(cur) as it:
                        for e in it:
                            name = e.name
                            if name.startswith('.') or name in self._SKIP_DIRS:
                                continue
                            if e.is_dir(follow_symlinks=False):
                                dirs += 1; stack.append(e.path)
                            elif e.is_file(follow_symlinks=False):
                                files += 1
                                try: total += e.stat(follow_symlinks=False).st_size
                                except OSError: pass
                                if name.endswith(".py"): py_n += 1
                except (PermissionError, OSError):
                    continue
        except Exception:
            pass
        capped = files + dirs >= limit
        self._update_queue.put(("projstats", scan_id, files, dirs, py_n, total, capped))

    def _build_page_agents_view(self):
        page = tk.Frame(self._body, bg=BG)
        self._pages["Agents"] = page
        tk.Label(page, text="AI Agents", bg=BG, fg=FG, font=(TITLE_FONT, 22, "bold")).pack(
            anchor=tk.W, padx=24, pady=(18, 12))
        grid = tk.Frame(page, bg=BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))
        for c in range(3): grid.columnconfigure(c, weight=1, uniform="ag")
        for i, (name, sub, color, kws) in enumerate(AGENTS):
            outer, b = self._card(grid, pad=16, accent=color, glow=True)
            outer.grid(row=i//3, column=i%3, sticky="nsew", padx=6, pady=6)
            grid.rowconfigure(i//3, weight=1)
            tk.Label(b, text=name, bg=CARD, fg=FG, font=(UI_FONT, 12, "bold")).pack(anchor=tk.W)
            tk.Label(b, text=sub, bg=CARD, fg=FG_DIM, font=(UI_FONT, 9)).pack(anchor=tk.W, pady=(3, 12))
            tk.Label(b, text="KEYWORDS", bg=CARD, fg=FG_FAINT, font=(UI_FONT, 7, "bold")).pack(anchor=tk.W)
            tk.Label(b, text=", ".join(kws), bg=CARD, fg=FG_DIM, font=(UI_FONT, 8),
                     wraplength=200, justify=tk.LEFT).pack(anchor=tk.W, pady=(3, 0))

    def _build_page_activity(self):
        page = tk.Frame(self._body, bg=BG)
        self._pages["Agent Activity"] = page
        hdr = tk.Frame(page, bg=BG)
        hdr.pack(fill=tk.X, padx=24, pady=(18, 10))
        tk.Label(hdr, text="Agent Activity", bg=BG, fg=FG, font=(TITLE_FONT, 22, "bold")).pack(side=tk.LEFT)
        # Search
        self._activity_search_var = tk.StringVar()
        sbox = tk.Frame(hdr, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
        sbox.pack(side=tk.RIGHT, padx=8)
        tk.Label(sbox, text="\U0001f50d", bg=CARD, fg=FG_DIM, font=(UI_FONT, 9)).pack(side=tk.LEFT, padx=(8, 4))
        tk.Entry(sbox, textvariable=self._activity_search_var, bg=CARD, fg=FG,
                 insertbackground=FG, relief=tk.FLAT, bd=0, font=(UI_FONT, 9), width=22).pack(side=tk.LEFT, pady=5, padx=(0, 8))
        self._activity_search_var.trace_add("write", lambda *a: self._filter_activity())
        self._btn(hdr, "Clear", self._clear_activity, bg=CARD2, bg_h=CARD3, fg=FG_DIM,
                  font=(UI_FONT, 9, "bold"), padx=10, pady=4).pack(side=tk.RIGHT)
        outer, b = self._card(page, pad=0, accent=TEAL)
        outer.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))
        wrap = tk.Frame(b, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True)
        self._activity_text = tk.Text(wrap, wrap=tk.WORD, bg=BG, fg=FG_DIM,
                                      relief=tk.FLAT, bd=0, font=(MONO_FONT, 9),
                                      insertbackground=FG, padx=12, pady=10)
        sb = ttk.Scrollbar(wrap, command=self._activity_text.yview)
        self._activity_text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._activity_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for tag, cfg in (("phase", {"foreground": CYAN, "font": (MONO_FONT, 9, "bold")}),
                         ("improvement", {"foreground": GREEN}), ("quality", {"foreground": ORANGE}),
                         ("error", {"foreground": RED}), ("success", {"foreground": GREEN, "font": (MONO_FONT, 9, "bold")}),
                         ("dim", {"foreground": FG_FAINT}), ("warn", {"foreground": YELLOW}), ("time", {"foreground": FG_FAINT})):
            self._activity_text.tag_configure(tag, **cfg)

    def _clear_activity(self):
        if hasattr(self, "_activity_text"): self._activity_text.delete("1.0", tk.END)
        self._activity_log.clear()

    def _refresh_activity_view(self):
        if not hasattr(self, "_activity_text"): return
        self._activity_text.delete("1.0", tk.END)
        for ts, text, tag in self._activity_log:
            self._activity_text.insert(tk.END, f"{ts}  ", "time")
            self._activity_text.insert(tk.END, text + "\n", tag)
        self._activity_text.see(tk.END)

    def _filter_activity(self):
        q = self._activity_search_var.get().lower()
        self._activity_text.delete("1.0", tk.END)
        for ts, text, tag in self._activity_log:
            if q and q not in text.lower(): continue
            self._activity_text.insert(tk.END, f"{ts}  ", "time")
            self._activity_text.insert(tk.END, text + "\n", tag)

    def _build_page_explorer(self):
        page = tk.Frame(self._body, bg=BG)
        self._pages["Code Explorer"] = page
        hdr = tk.Frame(page, bg=BG)
        hdr.pack(fill=tk.X, padx=24, pady=(18, 10))
        tk.Label(hdr, text="Code Explorer", bg=BG, fg=FG, font=(TITLE_FONT, 22, "bold")).pack(side=tk.LEFT)
        self._explorer_path_lbl = tk.Label(hdr, text="", bg=BG, fg=FG_DIM, font=(MONO_FONT, 8))
        self._explorer_path_lbl.pack(side=tk.LEFT, padx=14)
        self._btn(hdr, "\u2191 Up", self._explorer_up, bg=CARD2, bg_h=CARD3, fg=FG_DIM,
                  font=(UI_FONT, 9, "bold"), padx=10, pady=4).pack(side=tk.RIGHT)
        split = tk.Frame(page, bg=BG)
        split.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))
        lo, lb = self._card(split, pad=0, accent=BLUE)
        lo.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 8)); lo.configure(width=290); lo.pack_propagate(False)
        self._explorer_list = tk.Listbox(lb, bg=CARD, fg=FG_DIM, font=(MONO_FONT, 9),
                                         selectbackground=BLUE, selectforeground="white",
                                         relief=tk.FLAT, bd=0, highlightthickness=0, activestyle="none")
        self._explorer_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._explorer_list.bind("<<ListboxSelect>>", self._explorer_select)
        self._explorer_list.bind("<Double-Button-1>", self._explorer_open)
        ro, rb = self._card(split, pad=0, accent=PURPLE)
        ro.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._explorer_preview = tk.Text(rb, wrap=tk.NONE, bg=BG, fg=FG_DIM,
                                         relief=tk.FLAT, bd=0, font=(MONO_FONT, 9),
                                         insertbackground=FG, padx=10, pady=8)
        sv = ttk.Scrollbar(rb, command=self._explorer_preview.yview)
        self._explorer_preview.configure(yscrollcommand=sv.set)
        sv.pack(side=tk.RIGHT, fill=tk.Y)
        self._explorer_preview.pack(fill=tk.BOTH, expand=True)
        self._explorer_entries = []

    def _refresh_explorer(self):
        ws = Path(self._work_var.get())
        if not self._explorer_cwd or not Path(self._explorer_cwd).exists():
            self._explorer_cwd = str(ws)
        cwd = Path(self._explorer_cwd)
        self._explorer_path_lbl.config(text=str(cwd))
        self._explorer_list.delete(0, tk.END); self._explorer_entries = []
        try:
            for entry in sorted(cwd.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if entry.name.startswith('.'): continue
                self._explorer_list.insert(tk.END, f"{'\ud83d\udcc1 ' if entry.is_dir() else '   '}{entry.name}")
                self._explorer_entries.append(entry)
        except Exception: self._explorer_list.insert(tk.END, "  (cannot read)")

    def _explorer_select(self, event=None):
        sel = self._explorer_list.curselection()
        if not sel: return
        entry = self._explorer_entries[sel[0]]
        if entry.is_file():
            self._explorer_preview.configure(state=tk.NORMAL)
            self._explorer_preview.delete("1.0", tk.END)
            try: self._explorer_preview.insert("1.0", entry.read_text(encoding="utf-8", errors="replace")[:12000])
            except Exception as e: self._explorer_preview.insert("1.0", f"Cannot read: {e}")
            self._explorer_preview.configure(state=tk.DISABLED)

    def _explorer_open(self, event=None):
        sel = self._explorer_list.curselection()
        if sel and self._explorer_entries[sel[0]].is_dir():
            self._explorer_cwd = str(self._explorer_entries[sel[0]])
            self._refresh_explorer()

    def _explorer_up(self):
        if self._explorer_cwd:
            self._explorer_cwd = str(Path(self._explorer_cwd).parent)
            self._refresh_explorer()

    def _build_page_metrics(self):
        page = tk.Frame(self._body, bg=BG)
        self._pages["Metrics"] = page
        tk.Label(page, text="Metrics & Analytics", bg=BG, fg=FG, font=(TITLE_FONT, 22, "bold")).pack(
            anchor=tk.W, padx=24, pady=(18, 12))
        top = tk.Frame(page, bg=BG)
        top.pack(fill=tk.X, padx=24, pady=(0, 12))
        outer, b = self._card(top, accent=GREEN, glow=True)
        outer.pack(side=tk.LEFT, padx=(0, 14))
        tk.Label(b, text="QUALITY", bg=CARD, fg=FG_FAINT, font=(UI_FONT, 7, "bold")).pack()
        self._metrics_gauge = tk.Canvas(b, width=170, height=170, bg=CARD, highlightthickness=0)
        self._metrics_gauge.pack(pady=8)
        self._draw_ring(self._metrics_gauge, 0, GREEN, "0%", big=True)
        sf = tk.Frame(top, bg=BG)
        sf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._metrics_cards = {}
        for key, label, color, icon in (("iters", "Iterations", BLUE, "\u25ae"),
                                         ("improvements", "Improvements", GREEN, "\u2726"),
                                         ("avg", "Avg Quality", TEAL, "\u25c9"),
                                         ("best", "Best Quality", PURPLE, "\u2605")):
            o2, b2 = self._card(sf, accent=color)
            o2.pack(fill=tk.X, pady=3)
            r = tk.Frame(b2, bg=CARD); r.pack(fill=tk.X)
            tk.Label(r, text=icon, bg=CARD, fg=color, font=(UI_FONT, 14)).pack(side=tk.LEFT, padx=(0, 10))
            cl = tk.Frame(r, bg=CARD); cl.pack(side=tk.LEFT)
            tk.Label(cl, text=label, bg=CARD, fg=FG_FAINT, font=(UI_FONT, 8)).pack(anchor=tk.W)
            v = tk.Label(cl, text="\u2014", bg=CARD, fg=FG, font=(UI_FONT, 14, "bold"))
            v.pack(anchor=tk.W); self._metrics_cards[key] = v
        outer, b = self._card(page, accent=GREEN)
        outer.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))
        self._section_title(b, "Quality History", "\u223c", GREEN)
        self._metrics_chart = tk.Canvas(b, height=140, width=700, bg=CARD, highlightthickness=0)
        self._metrics_chart.pack(fill=tk.X)

    def _refresh_metrics_view(self):
        q = self._current_quality
        self._draw_ring(self._metrics_gauge, q, GREEN, f"{q:.0f}%", big=True)
        self._metrics_cards["iters"].config(text=str(self._iteration))
        n = len(self._quality_history)
        self._metrics_cards["improvements"].config(text=str(n))
        if n:
            self._metrics_cards["avg"].config(text=f"{sum(self._quality_history)/n:.1f}")
            self._metrics_cards["best"].config(text=f"{max(self._quality_history):.1f}")
        self._draw_spark(self._metrics_chart, self._quality_history[-60:], GREEN)

    def _build_page_tools(self):
        page = tk.Frame(self._body, bg=BG)
        self._pages["Tools"] = page
        tk.Label(page, text="Registered Tools", bg=BG, fg=FG, font=(TITLE_FONT, 22, "bold")).pack(
            anchor=tk.W, padx=24, pady=(18, 12))
        tools = [("read_file", "Read file contents", "File", BLUE), ("write_file", "Write/overwrite file", "File", BLUE),
                 ("list_directory", "List directory entries", "File", BLUE), ("grep", "Regex search in files", "Search", GREEN),
                 ("glob", "Find files by pattern", "Search", GREEN), ("web_search", "Web search", "Search", GREEN),
                 ("shell", "Execute shell commands", "Shell", ORANGE), ("git_status", "Git status", "Git", PURPLE),
                 ("git_diff", "Git diff", "Git", PURPLE), ("git_log", "Git log", "Git", PURPLE)]
        grid = tk.Frame(page, bg=BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))
        for c in range(2): grid.columnconfigure(c, weight=1, uniform="tl")
        for i, (nm, desc, cat, color) in enumerate(tools):
            o, b = self._card(grid, pad=14, accent=color)
            o.grid(row=i//2, column=i%2, sticky="nsew", padx=5, pady=5)
            grid.rowconfigure(i//2, weight=1)
            tr = tk.Frame(b, bg=CARD); tr.pack(fill=tk.X)
            tk.Label(tr, text="\u25cf", bg=CARD, fg=color, font=(UI_FONT, 10)).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(tr, text=nm, bg=CARD, fg=FG, font=(MONO_FONT, 10, "bold")).pack(side=tk.LEFT)
            tk.Label(tr, text=cat, bg=CARD, fg=color, font=(UI_FONT, 7, "bold")).pack(side=tk.RIGHT)
            tk.Label(b, text=desc, bg=CARD, fg=FG_DIM, font=(UI_FONT, 9)).pack(fill=tk.X, pady=(7, 0))

    # ══════════════════════════════════════════════════════════════
    # ── CANVAS HELPERS ────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════
    def _draw_ring(self, cv, pct, color, text="", big=False):
        cv.delete("all")
        size = int(cv.cget("width"))
        m = 14 if big else 10
        # Glow layer
        extent = max(1, int(3.6 * pct))
        cv.create_arc(m-4, m-4, size-m+4, size-m+4, start=90, extent=-extent,
                      outline=color, width=2, style=tk.ARC, stipple="gray25")
        # Track
        cv.create_arc(m, m, size-m, size-m, start=90, extent=-360,
                      outline=TRACK2, width=8 if big else 6, style=tk.ARC)
        # Value arc
        cv.create_arc(m, m, size-m, size-m, start=90, extent=-extent,
                      outline=color, width=9 if big else 7, style=tk.ARC)
        # Cap glow dot
        import math
        angle = math.radians(90 - extent)
        cx = size/2 + (size/2 - m) * math.cos(angle)
        cy = size/2 - (size/2 - m) * math.sin(angle)
        if pct > 0:
            cv.create_oval(cx-4, cy-4, cx+4, cy+4, fill=color, outline="")
        # Center text
        fs = 18 if big else 12
        cv.create_text(size//2, size//2, text=text, fill=FG, font=(TITLE_FONT, fs, "bold"))

    def _draw_hbar(self, cv, frac, color):
        cv.delete("all")
        cv.update_idletasks()
        w = cv.winfo_width()
        h = int(cv.cget("height"))
        r = 5
        # Track
        cv.create_rectangle(0, 1, w, h-1, fill=TRACK, outline="")
        # Value
        vw = max(0, int(w * min(frac, 1.0)))
        if vw > 0:
            cv.create_rectangle(0, 1, vw, h-1, fill=color, outline="")
            # Glow at end
            cv.create_rectangle(max(0, vw-4), 0, vw, h, fill=color, outline="", stipple="gray50")

    def _draw_spark(self, cv, data, color):
        cv.delete("all")
        cv.update_idletasks()
        w = cv.winfo_width() or 700
        h = int(cv.cget("height")) or 140
        if not data:
            cv.create_text(w//2, h//2, text="No data yet", fill=FG_FAINT, font=(UI_FONT, 9))
            return
        mn, mx = min(data), max(data)
        rng = mx - mn if mx != mn else 1
        pts = []
        for i, v in enumerate(data):
            x = int(i * w / max(len(data)-1, 1))
            y = int(h - 12 - (v - mn) / rng * (h - 24))
            pts.append((x, y))
        # Fill area
        fill_pts = [(0, h)] + pts + [(w, h)]
        flat = [c for pt in fill_pts for c in pt]
        cv.create_polygon(flat, fill=color, outline="", stipple="gray25")
        # Line
        if len(pts) > 1:
            flat_line = [c for pt in pts for c in pt]
            cv.create_line(flat_line, fill=color, width=2, smooth=True)
        # Dots at each point
        for x, y in pts[-5:]:
            cv.create_oval(x-3, y-3, x+3, y+3, fill=color, outline="")

    def _update_spark_mini(self, key, value):
        info = self._sys_metrics.get(key)
        if not info:
            return
        info["hist"].append(value)
        info["hist"] = info["hist"][-30:]
        cv = info["spark"]
        cv.delete("all")
        data = info["hist"]
        w, h = 82, 34
        if len(data) < 2:
            return
        mn, mx = min(data), max(data)
        rng = mx - mn if mx != mn else 1
        pts = []
        for i, v in enumerate(data):
            x = int(i * w / max(len(data)-1, 1))
            y = int(h - 4 - (v - mn) / rng * (h - 8))
            pts.append(x); pts.append(y)
        cv.create_line(pts, fill=info["color"], width=2, smooth=True)

    # ══════════════════════════════════════════════════════════════
    # ── RESOURCE TICK ─────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════
    def _tick_resources(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
        except Exception:
            cpu = mem = 0
        if hasattr(self, "_res_canvases"):
            self._draw_ring(self._res_canvases["cpu"], cpu, CYAN, f"{cpu:.0f}%")
            self._draw_ring(self._res_canvases["mem"], mem, PURPLE, f"{mem:.0f}%")
        self.root.after(2500, self._tick_resources)

    # ══════════════════════════════════════════════════════════════
    # ── SETTINGS DIALOG ───────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════
    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.configure(bg=BG2)
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        # Center over the main window
        self.root.update_idletasks()
        px = self.root.winfo_rootx() + (self.root.winfo_width() - 540) // 2
        py = self.root.winfo_rooty() + (self.root.winfo_height() - 700) // 2
        win.geometry(f"540x700+{max(px, 0)}+{max(py, 0)}")
        win.bind("<Escape>", lambda e: win.destroy())

        body = tk.Frame(win, bg=BG2)
        body.pack(fill=tk.BOTH, expand=True, padx=28, pady=22)

        tk.Label(body, text="Settings", bg=BG2, fg=FG,
                 font=(TITLE_FONT, 18, "bold")).pack(anchor=tk.W)
        tk.Label(body, text="Changes are saved automatically and kept between sessions",
                 bg=BG2, fg=FG_FAINT, font=(UI_FONT, 8)).pack(anchor=tk.W, pady=(2, 16))

        # Provider
        tk.Label(body, text="PROVIDER", bg=BG2, fg=FG_FAINT,
                 font=(UI_FONT, 7, "bold")).pack(anchor=tk.W, pady=(0, 5))
        pf = tk.Frame(body, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
        pf.pack(fill=tk.X, pady=(0, 12))
        prov_combo = ttk.Combobox(pf, textvariable=self._prov_var, values=PROVIDER_LIST,
                                   state="readonly", font=(UI_FONT, 10))
        prov_combo.pack(fill=tk.X, padx=8, pady=8)

        # Model — dropdown listing every model; free ones are labelled
        tk.Label(body, text="MODEL", bg=BG2, fg=FG_FAINT,
                 font=(UI_FONT, 7, "bold")).pack(anchor=tk.W, pady=(0, 5))
        mf = tk.Frame(body, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
        mf.pack(fill=tk.X, pady=(0, 4))
        model_combo = ttk.Combobox(mf, textvariable=self._model_var,
                                    font=(MONO_FONT, 9))
        model_combo.pack(fill=tk.X, padx=8, pady=8)
        free_lbl = tk.Label(body, text="", bg=BG2, fg=GREEN, font=(UI_FONT, 8, "bold"))
        free_lbl.pack(anchor=tk.W, pady=(0, 8))

        # API Key
        tk.Label(body, text="API KEY", bg=BG2, fg=FG_FAINT,
                 font=(UI_FONT, 7, "bold")).pack(anchor=tk.W, pady=(0, 5))
        kf = tk.Frame(body, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
        kf.pack(fill=tk.X, pady=(0, 12))
        key_entry = tk.Entry(kf, textvariable=self._api_key_var, show="●", bg=CARD, fg=FG,
                             insertbackground=FG, relief=tk.FLAT, bd=0,
                             font=(MONO_FONT, 10))
        key_entry.pack(fill=tk.X, padx=8, pady=8)
        hint_lbl = tk.Label(body, text="", bg=BG2, fg=FG_FAINT, font=(UI_FONT, 8))
        hint_lbl.pack(anchor=tk.W, pady=(0, 12))

        def _fill_models():
            prov = self._prov_var.get()
            model_combo["values"] = [model_display(m, t)
                                     for m, t in MODEL_CATALOG.get(prov, [])]

        def _refresh_free_state(*a):
            prov = self._prov_var.get()
            tag = model_tag(prov, self._model_var.get())
            if tag == "free":
                free_lbl.config(text="✓ Free — No API Key needed", fg=GREEN)
                key_entry.config(state=tk.DISABLED, disabledbackground=CARD)
                hint_lbl.config(text="This model runs locally via Ollama — no key, no cost.")
            elif tag == "freetier":
                free_lbl.config(text="✓ Free model — works with a free API key", fg=TEAL)
                key_entry.config(state=tk.NORMAL)
                hint_lbl.config(text="Hint: " + PROVIDER_DEFAULTS.get(prov, {}).get("hint", "")
                                + "  (key is free to create)")
            else:
                free_lbl.config(text="")
                key_entry.config(state=tk.NORMAL)
                h = PROVIDER_DEFAULTS.get(prov, {}).get("hint", "")
                hint_lbl.config(text=f"Hint: {h}" if h else "")

        def _on_prov(*a):
            prov = self._prov_var.get()
            d = PROVIDER_DEFAULTS.get(prov, {})
            cat = MODEL_CATALOG.get(prov, [])
            default = d.get("model", "")
            tag = next((t for m, t in cat if m == default), None)
            self._model_var.set(model_display(default, tag))
            _fill_models()
            _refresh_free_state()
        prov_combo.bind("<<ComboboxSelected>>", _on_prov)
        model_combo.bind("<<ComboboxSelected>>", _refresh_free_state)
        model_combo.bind("<KeyRelease>", _refresh_free_state)
        _fill_models()
        _refresh_free_state()

        # Workspace
        tk.Label(body, text="WORKSPACE", bg=BG2, fg=FG_FAINT,
                 font=(UI_FONT, 7, "bold")).pack(anchor=tk.W, pady=(0, 5))
        wf = tk.Frame(body, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
        wf.pack(fill=tk.X, pady=(0, 12))
        wfr = tk.Frame(wf, bg=CARD)
        wfr.pack(fill=tk.X, padx=8, pady=8)
        tk.Entry(wfr, textvariable=self._work_var, bg=CARD, fg=FG,
                 insertbackground=FG, relief=tk.FLAT, bd=0,
                 font=(MONO_FONT, 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._btn(wfr, "Browse", self._browse_workspace, bg=CARD3, bg_h=BORDER2, fg=FG_DIM,
                  font=(UI_FONT, 8, "bold"), padx=10, pady=3).pack(side=tk.RIGHT, padx=(8, 0))

        # Parameters
        parms = tk.Frame(body, bg=BG2)
        parms.pack(fill=tk.X, pady=(0, 12))
        for label, var in (("Target Quality (%)", self._target_var), ("Max Iterations", self._max_var)):
            col = tk.Frame(parms, bg=BG2)
            col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
            tk.Label(col, text=label.upper(), bg=BG2, fg=FG_FAINT,
                     font=(UI_FONT, 7, "bold")).pack(anchor=tk.W, pady=(0, 4))
            ef = tk.Frame(col, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
            ef.pack(fill=tk.X)
            tk.Entry(ef, textvariable=var, bg=CARD, fg=FG, insertbackground=FG,
                     relief=tk.FLAT, bd=0, font=(MONO_FONT, 10), width=10).pack(padx=8, pady=8)

        # Appearance
        tk.Label(body, text="THEME", bg=BG2, fg=FG_FAINT,
                 font=(UI_FONT, 7, "bold")).pack(anchor=tk.W, pady=(0, 5))
        tf = tk.Frame(body, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
        tf.pack(fill=tk.X, pady=(0, 12))
        theme_var = tk.StringVar(value=self._theme.capitalize())
        theme_combo = ttk.Combobox(tf, textvariable=theme_var,
                                   values=["Dark", "Light"], state="readonly",
                                   font=(UI_FONT, 10))
        theme_combo.pack(fill=tk.X, padx=8, pady=8)
        theme_combo.bind("<<ComboboxSelected>>",
                         lambda e: self._set_theme(theme_var.get().lower(),
                                                   reopen_settings=True))

        # Buttons
        brow = tk.Frame(body, bg=BG2)
        brow.pack(fill=tk.X, pady=(8, 0))
        self._btn(brow, "✓  Save & Close", lambda: (self._save_config(), self._refresh_badges(),
                  self._refresh_provider_labels(), win.destroy()),
                  bg=BLUE, bg_h=BLUE_HL).pack(side=tk.LEFT, padx=(0, 8))
        self._btn(brow, "Test Connection", lambda: self._test_connection(win),
                  bg=CARD2, bg_h=CARD3, fg=FG_DIM).pack(side=tk.LEFT)

    def _browse_workspace(self):
        d = filedialog.askdirectory(title="Select Workspace")
        if d:
            self._work_var.set(d)
            self._engine_proj_lbl.config(text=Path(d).name)

    def _test_connection(self, win=None):
        prov = self._prov_var.get()
        key = self._api_key_var.get().strip()
        if not key and prov != "ollama" and not self._model_is_keyless():
            self._toasts.show("No API key set", "warn")
            return
        self._toasts.show(f"Testing {prov}…", "info", 2000)
        def _do():
            try:
                from openai import OpenAI
                if prov == "ollama":
                    c = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
                elif prov == "deepseek":
                    c = OpenAI(base_url="https://api.deepseek.com/v1", api_key=key)
                elif prov == "groq":
                    c = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key)
                elif prov == "together":
                    c = OpenAI(base_url="https://api.together.xyz/v1", api_key=key)
                elif prov == "fireworks":
                    c = OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key=key)
                elif prov == "perplexity":
                    c = OpenAI(base_url="https://api.perplexity.ai", api_key=key)
                elif prov == "xai":
                    c = OpenAI(base_url="https://api.x.ai/v1", api_key=key)
                elif prov == "openrouter":
                    c = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
                elif prov == "qwen":
                    c = OpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key=key)
                elif prov == "kimi":
                    c = OpenAI(base_url="https://api.moonshot.cn/v1", api_key=key)
                elif prov == "glm":
                    c = OpenAI(base_url="https://open.bigmodel.cn/api/paas/v4", api_key=key)
                elif prov == "gemini":
                    c = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai", api_key=key)
                elif prov == "anthropic":
                    from anthropic import Anthropic
                    ac = Anthropic(api_key=key)
                    ac.messages.create(model=self._model_id(), max_tokens=5,
                                       messages=[{"role": "user", "content": "hi"}])
                    self._update_queue.put(("toast", "Connection OK ✓", "success"))
                    return
                else:
                    c = OpenAI(api_key=key)
                c.chat.completions.create(model=self._model_id(), max_tokens=5,
                                          messages=[{"role": "user", "content": "hi"}])
                self._update_queue.put(("toast", "Connection OK ✓", "success"))
            except Exception as e:
                self._update_queue.put(("toast", f"Connection failed: {e}", "error"))
        threading.Thread(target=_do, daemon=True).start()

    # ══════════════════════════════════════════════════════════════
    # ── ENGINE CONTROL ────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════
    def _start_engine(self):
        if self._running:
            return
        ws = self._work_var.get().strip()
        if not ws or not Path(ws).is_dir():
            self._toasts.show("Set a valid workspace first", "warn")
            return
        key = self._api_key_var.get().strip()
        prov = self._prov_var.get()
        if not key and prov != "ollama" and not self._model_is_keyless():
            self._toasts.show("No API key configured", "warn")
            return
        self._save_config()
        self._running = True
        self._engine = None
        self._stop_flag = threading.Event()
        self._iteration = 0
        self._max_iter = int(self._max_var.get() or 100)
        self._start_time = time.time()
        self._run_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.NORMAL)
        self._engine_state_lbl.config(text="Running", fg=GREEN)
        self._engine_dot.config(fg=GREEN)
        self._status_lbl.config(text="Engine running")
        self._status_dot.config(fg=GREEN)
        goal = self._goal_value()
        self._obj_lbl.config(text=goal if goal else "Auto-improvement mode")
        # Snapshot every setting on the main thread — the worker must not
        # touch tkinter variables
        self._run_params = {
            "prov": prov,
            "key": key,
            "model": self._model_id(),
            "workspace": ws,
            "target": self._target_var.get(),
            "goal": goal,
        }
        self._toasts.show("Engine started", "success", 2000)
        self._engine_thread = threading.Thread(target=self._run_engine, daemon=True)
        self._engine_thread.start()

    def _run_engine(self):
        try:
            from aicoder.config import PROVIDER_INFO, config
            from aicoder.core.agent import Agent
            from aicoder.core.tool_registry import ToolRegistry
            from aicoder.tools.file_tools import ListDirectoryTool, ReadFileTool, WriteFileTool
            from aicoder.tools.git_tools import GitDiffTool, GitLogTool, GitStatusTool
            from aicoder.tools.search_tools import GlobTool, GrepTool, WebSearchTool
            from aicoder.tools.shell_tool import ShellTool

            prov = self._run_params["prov"]
            key = self._run_params["key"]
            model = self._run_params["model"]

            # Point the framework at the chosen workspace / model
            config.workspace = Path(self._run_params["workspace"])
            config.provider = prov
            config.model = model
            if key:
                config.api_key = key

            # Build the LLM provider (lazy imports keep optional deps optional)
            if prov == "openai":
                from aicoder.llm.openai_provider import OpenAIProvider
                provider = OpenAIProvider(model=model, api_key=key)
            elif prov == "anthropic":
                from aicoder.llm.anthropic_provider import AnthropicProvider
                provider = AnthropicProvider(model=model, api_key=key)
            elif prov == "gemini":
                from aicoder.llm.gemini_provider import GeminiProvider
                provider = GeminiProvider(model=model, api_key=key)
            elif prov == "ollama":
                from aicoder.llm.ollama_provider import OllamaProvider
                provider = OllamaProvider(model=model)
            elif prov == "openrouter":
                from aicoder.llm.openrouter_provider import OpenRouterProvider
                provider = OpenRouterProvider(model=model, api_key=key or "free")
            else:
                from aicoder.llm.openai_compatible_provider import OpenAICompatibleProvider
                api_base = PROVIDER_INFO.get(prov, {}).get("api_base")
                provider = OpenAICompatibleProvider(model=model, api_key=key or "free",
                                                    api_base=api_base)

            # Full tool belt — same set the CLI gives the agent
            registry = ToolRegistry()
            for tool in (ReadFileTool(), WriteFileTool(), ListDirectoryTool(),
                         ShellTool(), GrepTool(), GlobTool(), WebSearchTool(),
                         GitStatusTool(), GitDiffTool(), GitLogTool()):
                registry.register(tool)

            goal = self._run_params["goal"] or "Improve the overall quality of this project"
            q = self._update_queue
            rounds = max(self._max_iter, 1)

            # Let the agent take enough steps to actually read + edit files,
            # but keep each round bounded so Stop stays responsive.
            config.max_iterations = 30

            class _Stopped(Exception):
                pass

            def _check_stop():
                if self._stop_flag.is_set():
                    raise _Stopped()

            def _on_think(text):
                _check_stop()
                if text and text.strip():
                    q.put(("phase", "reason", text.strip().splitlines()[0][:160]))

            def _on_tool(name, args):
                _check_stop()
                tgt = ""
                if isinstance(args, dict):
                    tgt = (args.get("path") or args.get("file_path")
                           or args.get("pattern") or args.get("command")
                           or args.get("query") or "")
                q.put(("phase", name, f"{name} {tgt}".strip()[:160]))
                if name in ("write_file", "edit_file") and tgt:
                    q.put(("improvement", f"Edited {tgt}",
                           "Agent wrote changes to the workspace.", ""))

            # ── DIRECT CODING LOOP ─────────────────────────────────────
            # Each round asks the agent to make one concrete improvement
            # toward the goal — it reads the project and edits real files.
            completed = 0
            for i in range(1, rounds + 1):
                if self._stop_flag.is_set():
                    break
                q.put(("phase", "implement",
                       f"Round {i}/{rounds}: coding toward your goal…"))
                if i == 1:
                    task = (
                        f"{goal}\n\n"
                        f"Work inside the workspace at {config.workspace}. "
                        f"Investigate the existing files first, then make the "
                        f"change by actually editing/creating files with your tools."
                    )
                else:
                    task = (
                        f"Continue improving this project toward the goal:\n{goal}\n\n"
                        f"Review the current state of the workspace at "
                        f"{config.workspace} and make the next concrete "
                        f"improvement. Actually edit or create files — don't just "
                        f"describe what to do."
                    )
                agent = Agent(
                    task=task,
                    provider=provider,
                    tool_registry=registry,
                    on_thinking=_on_think,
                    on_tool_call=_on_tool,
                )
                try:
                    result = agent.run()
                except _Stopped:
                    break
                completed = i
                q.put(("improvement", f"Round {i} complete",
                       (result or "Done.")[:400], ""))

            self._update_queue.put(
                ("final", f"Coding session finished after {completed} round(s)."))
        except Exception as e:
            self._update_queue.put(("error", str(e)))
        finally:
            self._update_queue.put(("done",))

    def _stop_engine(self):
        if getattr(self, "_stop_flag", None) is not None:
            self._stop_flag.set()
        if self._engine is not None and hasattr(self._engine, "stop"):
            try:
                self._engine.stop()
            except Exception:
                pass
        self._running = False
        self._run_btn.configure(state=tk.NORMAL)
        self._stop_btn.configure(state=tk.DISABLED)
        self._engine_state_lbl.config(text="Stopped", fg=ORANGE)
        self._engine_dot.config(fg=ORANGE)
        self._status_lbl.config(text="Stopped")
        self._status_dot.config(fg=ORANGE)
        self._toasts.show("Engine stopped", "warn", 2500)

    # ══════════════════════════════════════════════════════════════
    # ── MESSAGE PUMP ──────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════
    def _poll_queue(self):
        try:
            while True:
                msg = self._update_queue.get_nowait()
                self._handle_msg(msg)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_msg(self, msg):
        kind = msg[0]
        ts = time.strftime("%H:%M:%S")

        if kind == "toast":
            self._toasts.show(msg[1], msg[2] if len(msg) > 2 else "info")
            return

        if kind == "projstats":
            scan_id, files, dirs, py_n, total, capped = msg[1:]
            # Ignore stale results from a previous scan
            if scan_id != getattr(self, "_proj_scan_id", None):
                return
            suffix = "+" if capped else ""
            self._proj_stats["files"].config(text=f"{files}{suffix}")
            self._proj_stats["dirs"].config(text=f"{dirs}{suffix}")
            self._proj_stats["py"].config(text=f"{py_n}{suffix}")
            self._proj_stats["size"].config(
                text=f"{total/1024:.0f}KB" if total < 1048576 else f"{total/1048576:.1f}MB")
            return

        if kind == "phase":
            phase, detail = msg[1], msg[2]
            # One engine iteration = one improvement attempt
            if phase == "implement":
                self._iteration += 1
            # Log
            self._log(f"[{phase}] {detail}", "phase", ts)
            # Update objective
            self._obj_iter_lbl.config(text=f"{self._iteration} / {self._max_iter} iterations")
            frac = self._iteration / max(self._max_iter, 1)
            self._tot_frac = frac
            self._draw_hbar(self._tot_bar, frac, GREEN)
            self._tot_pct_lbl.config(text=f"{frac*100:.0f}%")
            # ETA
            elapsed = time.time() - self._start_time
            if frac > 0:
                eta = elapsed / frac * (1 - frac)
                self._obj_eta_lbl.config(text=f"ETA: {int(eta//60)}m {int(eta%60)}s")
            # Metrics
            self._sys_metrics["iterations"]["val"].config(text=str(self._iteration))
            self._update_spark_mini("iterations", self._iteration)
            # Footer
            self._foot_iter.config(text=f"Iteration {self._iteration}/{self._max_iter}")
            self._status_lbl.config(text=f"{phase}: {detail[:50]}")
            # Agent matching
            low = (phase + " " + detail).lower()
            for name, sub, color, kws in AGENTS:
                if any(k in low for k in kws):
                    self._activate_agent(name)
                    break
            # Tasks
            self._set_tasks([f"{phase}: {detail[:40]}"])
            # Elapsed
            em = int(elapsed // 60); es = int(elapsed % 60)
            self._sys_metrics["elapsed"]["val"].config(text=f"{em}m {es}s")

        elif kind == "improvement":
            title, desc, diff = msg[1], msg[2], msg[3]
            self._log(f"✦ {title}: {desc}", "improvement", ts)
            # Recent changes
            self._changes_text.configure(state=tk.NORMAL)
            self._changes_text.delete("1.0", tk.END)
            self._changes_text.insert(tk.END, f"✦ {title}\n", "title")
            self._changes_text.insert(tk.END, f"{desc}\n\n", "add")
            if diff:
                self._changes_text.insert(tk.END, diff[:800] + "\n", "dim")
            self._changes_text.configure(state=tk.DISABLED)
            try:
                snaps = int(self._sys_metrics["snapshots"]["val"].cget("text"))
            except (ValueError, TypeError):
                snaps = 0
            self._sys_metrics["snapshots"]["val"].config(text=str(snaps + 1))
            # Roadmap
            try:
                if self._engine and hasattr(self._engine, '_roadmap'):
                    summary = self._engine._roadmap.get_summary()
                    self._roadmap_text.configure(state=tk.NORMAL)
                    self._roadmap_text.delete("1.0", tk.END)
                    self._roadmap_text.insert("1.0", summary)
                    self._roadmap_text.configure(state=tk.DISABLED)
            except Exception:
                pass

        elif kind == "quality":
            score, delta, summary = msg[1], msg[2], msg[3]
            pct = score * 100 if score <= 1 else score
            self._current_quality = pct
            self._quality_history.append(pct)
            self._log(f"Quality: {pct:.1f}% (Δ{delta:+.2f}) {summary}", "quality", ts)
            # Gauges
            self._draw_ring(self._gauge, pct, GREEN, f"{pct:.0f}%", big=True)
            self._sys_metrics["quality"]["val"].config(text=f"{pct:.1f}%")
            self._update_spark_mini("quality", pct)

        elif kind == "final":
            for line in msg[1].split("\n"):
                self._log(line, "dim", ts)

        elif kind == "error":
            self._log(f"ERROR: {msg[1]}", "error", ts)
            self._toasts.show(msg[1][:80], "error", 5000)

        elif kind == "done":
            self._running = False
            self._run_btn.configure(state=tk.NORMAL)
            self._stop_btn.configure(state=tk.DISABLED)
            self._engine_state_lbl.config(text="Complete", fg=TEAL)
            self._engine_dot.config(fg=TEAL)
            self._status_lbl.config(text="Complete")
            self._status_dot.config(fg=TEAL)
            self._log("Engine run complete.", "success", ts)
            self._toasts.show("Run complete!", "success", 4000)
            self._set_tasks(["Run finished"], idle=True)
            for info in self._agent_widgets.values():
                info["dot"].config(fg=FG_FAINT)
                info["st"].config(text="Idle")
                info["cell"].config(bg=CARD2)

    def _log(self, text, tag, ts=None):
        ts = ts or time.strftime("%H:%M:%S")
        # Dashboard activity
        self._output_text.insert(tk.END, f"{ts}  ", "time")
        self._output_text.insert(tk.END, text + "\n", tag)
        self._output_text.see(tk.END)
        # Activity page
        self._activity_log.append((ts, text, tag))
        if hasattr(self, "_activity_text"):
            self._activity_text.insert(tk.END, f"{ts}  ", "time")
            self._activity_text.insert(tk.END, text + "\n", tag)
            self._activity_text.see(tk.END)

    def _activate_agent(self, name):
        for n, info in self._agent_widgets.items():
            if n == name:
                info["dot"].config(fg=info["color"])
                info["st"].config(text="Active", fg=info["color"])
                info["cell"].config(highlightbackground=info["color"])
            else:
                info["dot"].config(fg=FG_FAINT)
                info["st"].config(text="Idle", fg=FG_DIM)
                info["cell"].config(highlightbackground=BORDER)

    def _clear_output(self):
        self._output_text.delete("1.0", tk.END)


# ═══════════════════════════════════════════════════════════════════
# ── MAIN ENTRY ────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
def main():
    root = tk.Tk()
    app = AICoderApp(root)   # restores saved window size/state itself
    root.mainloop()


if __name__ == "__main__":
    main()
