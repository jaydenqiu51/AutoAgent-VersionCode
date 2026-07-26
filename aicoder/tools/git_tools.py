"""Git tools: status, diff, log (read-only + safe writes)."""

import subprocess
from typing import Any, Dict

from ..config import config
from .base import BaseTool


def _run_git(args: list) -> str:
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(config.workspace),
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        return output.strip() or "(no output)"
    except FileNotFoundError:
        return "Error: git is not installed or not found in PATH."
    except subprocess.TimeoutExpired:
        return "Error: git command timed out."
    except Exception as e:
        return f"Error running git command: {e}"


class GitStatusTool(BaseTool):
    """Show the working tree status."""

    @property
    def name(self) -> str:
        return "git_status"

    @property
    def description(self) -> str:
        return "Show the git working tree status (modified, staged, untracked files)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def execute(self, **kwargs) -> str:
        return _run_git(["status", "--short"])


class GitDiffTool(BaseTool):
    """Show changes between commits or working tree."""

    @property
    def name(self) -> str:
        return "git_diff"

    @property
    def description(self) -> str:
        return "Show git diff of unstaged changes, or between commits."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "staged": {
                    "type": "boolean",
                    "description": "Show staged changes instead of unstaged. Defaults to false.",
                },
            },
            "required": [],
        }

    def execute(self, staged: bool = False, **kwargs) -> str:
        args = ["diff"]
        if staged:
            args.append("--staged")
        result = _run_git(args)
        if len(result) > 4000:
            result = result[:4000] + "\n... [diff truncated]"
        return result


class GitLogTool(BaseTool):
    """Show commit logs."""

    @property
    def name(self) -> str:
        return "git_log"

    @property
    def description(self) -> str:
        return "Show recent git commit history."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of recent commits to show. Defaults to 10.",
                },
            },
            "required": [],
        }

    def execute(self, count: int = 10, **kwargs) -> str:
        return _run_git(["log", f"-{count}", "--oneline", "--decorate"])
