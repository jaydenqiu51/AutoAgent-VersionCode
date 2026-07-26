"""Shell execution tool with safety checks."""

import subprocess
from typing import Any, Dict

from ..config import config
from .base import BaseTool

# Patterns that require user confirmation
DANGEROUS_PATTERNS = [
    "rm -rf", "rm -r", "sudo", "chmod 777", "> /dev/",
    "mkfs", "dd if=", ":(){ :|:& };:",  # fork bomb
    "shutdown", "reboot", "format",
    "del /f", "del /q", "rmdir /s", "rmdir /q",  # Windows dangerous
    "format c:", "diskpart",
]


class ShellTool(BaseTool):
    """Execute shell commands with safety checks."""

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command. Returns stdout and stderr output. "
            "Commands are run from the workspace directory. "
            "Dangerous commands (rm -rf, sudo, etc.) will be blocked."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
            },
            "required": ["command"],
        }

    def _is_dangerous(self, command: str) -> bool:
        """Check if the command matches any dangerous pattern."""
        lower = command.lower()
        for pattern in DANGEROUS_PATTERNS:
            if pattern.lower() in lower:
                return True
        return False

    def execute(self, command: str, **kwargs) -> str:
        if self._is_dangerous(command):
            return (
                f"BLOCKED: The command contains a potentially dangerous pattern. "
                f"If you are sure, run it manually in your terminal.\n"
                f"Command: {command}"
            )

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(config.workspace),
                capture_output=True,
                text=True,
                timeout=60,
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"

            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"

            # Truncate long output
            if len(output) > 4000:
                output = output[:4000] + "\n... [output truncated]"

            return output.strip() or "(no output)"

        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 60 seconds."
        except Exception as e:
            return f"Error executing command: {e}"
