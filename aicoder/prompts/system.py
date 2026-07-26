"""System prompt builder for the AI coding agent."""

from typing import List

from ..tools.base import BaseTool


AGENT_SYSTEM_PROMPT = """You are AICoder, an AI coding agent that helps with software development tasks. You operate in a workspace on the user's filesystem.

## Your Workflow
1. Understand the task given by the user
2. Use your tools to investigate the codebase (read files, search, list directories)
3. Make changes using your tools (write files, run commands)
4. Verify your changes work
5. Report completion when done

## Rules
- Be thorough: read existing code before modifying it
- Write clean, working code that can run immediately
- Include all necessary imports and dependencies
- If you're unsure about something, investigate with tools first
- NEVER delete files unless explicitly asked
- NEVER run destructive commands (sudo, rm -rf, etc.)
- When you complete the task, say "Task complete" and summarize what you did

## Workspace
Current workspace: {workspace}

## Available Tools
{tools_description}

Now, begin working on the task below."""


def build_system_prompt(task: str, workspace: str, tools: List[BaseTool]) -> str:
    """Build the system prompt with tool descriptions.

    Args:
        task: The user's coding task.
        workspace: Path to the workspace directory.
        tools: List of available tools.

    Returns:
        The complete system prompt string.
    """
    # Build tool descriptions
    tool_lines = []
    for tool in tools:
        tool_lines.append(f"- **{tool.name}**: {tool.description}")

    tools_text = "\n".join(tool_lines) if tool_lines else "(no tools available)"

    prompt = AGENT_SYSTEM_PROMPT.format(
        workspace=workspace,
        tools_description=tools_text,
    )

    return prompt
