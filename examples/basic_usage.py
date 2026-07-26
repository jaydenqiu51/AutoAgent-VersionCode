"""Basic usage example for the AI Coding Agent Framework."""

import sys
from pathlib import Path

# Add parent to path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from aicoder.config import config
from aicoder.core.agent import Agent
from aicoder.core.tool_registry import ToolRegistry
from aicoder.llm.openai_provider import OpenAIProvider
from aicoder.tools.file_tools import ListDirectoryTool, ReadFileTool, WriteFileTool
from aicoder.tools.search_tools import GrepTool, GlobTool


def main():
    """Demonstrate using the framework programmatically."""

    # 1. Configure (set your API key via environment variable)
    # export OPENAI_API_KEY=sk-...

    # 2. Create a provider
    provider = OpenAIProvider(model="gpt-4o")

    # 3. Create a tool registry with your chosen tools
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListDirectoryTool())
    registry.register(GrepTool())
    registry.register(GlobTool())

    # 4. Create and run an agent
    agent = Agent(
        task="List all Python files in the current project and count them",
        provider=provider,
        tool_registry=registry,
        on_thinking=lambda text: print(f"\n[Thinking] {text}"),
        on_tool_call=lambda name, args: print(f"[Tool] {name}: {args}"),
    )

    result = agent.run()
    print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
