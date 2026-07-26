"""Task planner — decomposes a high-level task into actionable steps."""

from typing import List, Optional

from ..config import config
from ..llm.base import BaseProvider, Message


class Planner:
    """Decomposes a coding task into a sequence of actionable steps.

    Uses a quick LLM call (without tools) to produce a plan before
    the main agent loop begins executing.
    """

    PLANNING_PROMPT = """You are a task planner for an AI coding agent. Given a coding task, break it down into a numbered list of concrete, actionable steps. Each step should be specific enough for the agent to execute with its available tools (read_file, write_file, run_command, grep_search, glob_find, git_*, list_directory).

Rules:
- Keep each step focused on ONE action
- Include file paths where relevant
- Order steps logically (investigate first, then modify)
- Output ONLY the numbered list, no preamble

Task: {task}

Plan:"""

    def __init__(self, provider: BaseProvider):
        self._provider = provider

    def plan(self, task: str) -> List[str]:
        """Generate a step-by-step plan for the given task.

        Args:
            task: The high-level coding task description.

        Returns:
            List of step descriptions.
        """
        prompt = self.PLANNING_PROMPT.format(task=task)

        response = self._provider.chat(
            messages=[
                Message(role="user", content=prompt),
            ],
        )

        if not response.content:
            return [task]

        # Parse numbered list from response
        steps = []
        for line in response.content.strip().split("\n"):
            line = line.strip()
            # Match patterns like "1. ", "1) ", "Step 1: ", "- "
            if line and (line[0].isdigit() or line.startswith("- ")):
                # Remove numbering
                for prefix in [". ", ") ", ": "]:
                    idx = line.find(prefix)
                    if idx > 0 and line[:idx].replace("Step ", "").strip().isdigit():
                        line = line[idx + len(prefix):].strip()
                        break

                if line:
                    steps.append(line)

        if not steps:
            return [task]

        return steps
