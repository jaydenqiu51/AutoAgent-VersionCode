"""Command-line interface for the AI Coding Agent Framework."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import PROVIDER_INFO, config
from .core.agent import Agent
from .core.engine import ImprovementEngine
from .core.tester import Tester
from .core.tool_registry import ToolRegistry
from .llm.anthropic_provider import AnthropicProvider
from .llm.gemini_provider import GeminiProvider
from .llm.ollama_provider import OllamaProvider
from .llm.openai_compatible_provider import OpenAICompatibleProvider
from .llm.openai_provider import OpenAIProvider
from .llm.openrouter_provider import OpenRouterProvider
from .tools.file_tools import ListDirectoryTool, ReadFileTool, WriteFileTool
from .tools.git_tools import GitDiffTool, GitLogTool, GitStatusTool
from .tools.search_tools import GlobTool, GrepTool, WebSearchTool
from .tools.shell_tool import ShellTool


def _create_provider(provider_name: str, model: Optional[str] = None):
    """Create an LLM provider instance by name.

    Supports: openai, anthropic, gemini, ollama, deepseek, groq, together,
              fireworks, perplexity, xai, openrouter, qwen, kimi, glm, openai_compatible
    """
    # Use default model from presets if none specified
    if model is None and provider_name in PROVIDER_INFO:
        model = PROVIDER_INFO[provider_name].get("default_model")

    # Determine API base from presets
    api_base = None
    if provider_name in PROVIDER_INFO:
        api_base = PROVIDER_INFO[provider_name].get("api_base")
    api_base = config.api_base or api_base

    if provider_name == "openai":
        return OpenAIProvider(model=model)
    elif provider_name == "anthropic":
        return AnthropicProvider(model=model)
    elif provider_name == "gemini":
        return GeminiProvider(model=model)
    elif provider_name == "ollama":
        return OllamaProvider(model=model)
    elif provider_name == "openrouter":
        return OpenRouterProvider(model=model)
    elif provider_name in ("deepseek", "groq", "together", "fireworks", "perplexity", "xai", "qwen", "kimi", "glm", "openai_compatible"):
        return OpenAICompatibleProvider(model=model, api_base=api_base)
    else:
        print(f"Error: Unknown provider '{provider_name}'.")
        print(f"Available: {', '.join(sorted(PROVIDER_INFO.keys()))}")
        sys.exit(1)


def _create_tool_registry() -> ToolRegistry:
    """Create and register all standard tools."""
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListDirectoryTool())
    registry.register(ShellTool())
    registry.register(GrepTool())
    registry.register(GlobTool())
    registry.register(WebSearchTool())
    registry.register(GitStatusTool())
    registry.register(GitDiffTool())
    registry.register(GitLogTool())
    return registry


def main():
    parser = argparse.ArgumentParser(
        description="AI Coding Agent Framework - Your AI-powered coding assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aicoder "Add input validation to src/auth.py"
  aicoder --interactive
  aicoder --continuous "Transform this into a AAA driving game"
  aicoder --provider ollama --model codellama "Explain this codebase"
  aicoder --workspace ~/myproject --continuous --target 90 "Improve the project"
        """,
    )

    parser.add_argument(
        "task",
        nargs="?",
        help="The coding task to perform",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start an interactive session",
    )
    parser.add_argument(
        "--provider", "-p",
        default=None,
        help=f"LLM provider (openai, anthropic, ollama). Default: {config.provider}",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help=f"Model name. Default: {config.model}",
    )
    parser.add_argument(
        "--workspace", "-w",
        default=None,
        help="Workspace directory path",
    )
    parser.add_argument(
        "--continuous", "-c",
        action="store_true",
        help="Run in continuous self-improving mode (audit → roadmap → improve → repeat)",
    )
    parser.add_argument(
        "--target", "-t",
        type=float,
        default=85.0,
        help="Target quality score (0-100) for continuous mode. Default: 85",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=100,
        help="Max improvement iterations in continuous mode. Default: 100",
    )
    parser.add_argument(
        "--gui", "-g",
        action="store_true",
        help="Launch the desktop GUI application",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    # Override config
    if args.workspace:
        config.workspace = Path(args.workspace)

    provider_name = args.provider or config.provider
    model = args.model or config.model

    # Check configuration
    if provider_name != "ollama" and not config.api_key:
        print("Error: No API key configured. Set AICODER_API_KEY or OPENAI_API_KEY in your environment.")
        print("Or use --provider ollama for local models.")
        sys.exit(1)

    # Create provider and tools
    provider = _create_provider(provider_name, model)
    registry = _create_tool_registry()

    print(f" AICoder v0.1.0 | Provider: {provider_name} | Model: {model}")
    print(f" Workspace: {config.workspace}")
    print()

    if args.gui:
        _run_gui()
    elif args.continuous:
        if not args.task:
            print("Error: --continuous requires a goal. Example: aicoder --continuous 'Make this a AAA game'")
            sys.exit(1)
        _run_continuous(args.task, provider, registry, args.target, args.max_iterations)
    elif args.interactive:
        _run_interactive(provider, registry)
    elif args.task:
        _run_task(args.task, provider, registry)
    else:
        parser.print_help()
        sys.exit(1)


def _run_task(task: str, provider, registry: ToolRegistry):
    """Run a single task."""
    agent = Agent(
        task=task,
        provider=provider,
        tool_registry=registry,
        on_thinking=lambda text: print(f"\n[Thinking] {text}"),
        on_tool_call=lambda name, args: print(f"\n[Tool] {name}: {args}"),
    )

    result = agent.run()

    print("\n" + "=" * 60)
    print(" RESULT")
    print("=" * 60)
    print(result)


def _run_interactive(provider, registry: ToolRegistry):
    """Run an interactive session."""
    print("Interactive mode. Type 'exit' or 'quit' to leave.")
    print("Type your tasks and press Enter. Use Ctrl+C to cancel a running task.")
    print()

    while True:
        try:
            task = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not task:
            continue
        if task.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        print()
        agent = Agent(
            task=task,
            provider=provider,
            tool_registry=registry,
            on_thinking=lambda text: print(f"[...] {text[:200]}") if text else None,
            on_tool_call=lambda name, args: print(f"[Tool] {name}"),
        )

        try:
            result = agent.run()
            print(f"\n[Agent] {result}\n")
        except KeyboardInterrupt:
            print("\n[Cancelled]\n")


def _run_continuous(goal: str, provider, registry: ToolRegistry, target: float, max_iterations: int):
    """Run the continuous self-improving engine."""
    print(f" Goal: {goal}")
    print(f" Target quality: {target:.0f}/100 | Max iterations: {max_iterations}")
    print(f" Press Ctrl+C to stop after current iteration")
    print()

    tester = Tester()

    engine = ImprovementEngine(
        goal=goal,
        provider=provider,
        tool_registry=registry,
        tester=tester,
        target_quality=target,
        max_iterations=max_iterations,
        on_phase=lambda phase, msg: print(f"[{phase.upper()}] {msg}"),
        on_improvement=lambda iid, title, result: print(f"  {'=' * 50}\n  IMPROVEMENT: {title}\n  Result: {result}\n"),
        on_quality=lambda before, after, trend: print(f"  [QUALITY] {before:.0f} → {after:.0f} | Trend: {trend}"),
    )

    try:
        report = engine.run()
        print(report)
    except KeyboardInterrupt:
        engine.stop()
        print("\nStopping after current iteration...")


def _run_gui():
    """Launch the desktop GUI application."""
    from .gui import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
