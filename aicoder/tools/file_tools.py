"""File I/O tools: read_file, write_file, list_directory."""

import os
from pathlib import Path
from typing import Any, Dict

from ..config import config
from .base import BaseTool


class ReadFileTool(BaseTool):
    """Read the contents of a file."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the given path."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read. Can be absolute or relative to workspace.",
                },
                "start_line": {
                    "type": "integer",
                    "description": "Optional line number to start reading from (1-based).",
                },
                "end_line": {
                    "type": "integer",
                    "description": "Optional line number to end reading at (1-based, inclusive).",
                },
            },
            "required": ["file_path"],
        }

    def execute(self, file_path: str, start_line: int = 0, end_line: int = 0, **kwargs) -> str:
        path = Path(file_path)
        if not path.is_absolute():
            path = config.workspace / path

        if not path.exists():
            return f"Error: File not found: {path}"

        if not path.is_file():
            return f"Error: Not a file: {path}"

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if start_line > 0 or end_line > 0:
                start = max(0, start_line - 1) if start_line > 0 else 0
                end = min(len(lines), end_line) if end_line > 0 else len(lines)
                lines = lines[start:end]

            # Truncate very large files
            if len(lines) > 500:
                lines = lines[:500]
                lines.append(f"\n... [truncated, {len(lines) - 500} more lines]")

            # Add line numbers
            numbered = []
            line_offset = max(0, start_line - 1) if start_line > 0 else 0
            for i, line in enumerate(lines):
                numbered.append(f"{line_offset + i + 1:>6}|{line}".rstrip())

            return "\n".join(numbered)

        except Exception as e:
            return f"Error reading file: {e}"


class WriteFileTool(BaseTool):
    """Write or overwrite a file."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to write to. Can be absolute or relative to workspace.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["file_path", "content"],
        }

    def execute(self, file_path: str, content: str, **kwargs) -> str:
        path = Path(file_path)
        if not path.is_absolute():
            path = config.workspace / path

        # Safety: don't write outside workspace
        try:
            path.resolve().relative_to(config.workspace.resolve())
        except ValueError:
            return f"Error: Cannot write outside workspace. Path: {path}"

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Error writing file: {e}"


class ListDirectoryTool(BaseTool):
    """List contents of a directory."""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and directories at the given path."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list. Defaults to workspace root.",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively.",
                },
            },
            "required": [],
        }

    def execute(self, path: str = "", recursive: bool = False, **kwargs) -> str:
        target = config.workspace
        if path:
            p = Path(path)
            target = p if p.is_absolute() else config.workspace / p

        if not target.exists():
            return f"Error: Directory not found: {target}"
        if not target.is_dir():
            return f"Error: Not a directory: {target}"

        try:
            lines = []
            if recursive:
                for root, dirs, files in os.walk(target):
                    level = root.replace(str(target), "").count(os.sep)
                    indent = "  " * level
                    lines.append(f"{indent}{os.path.basename(root)}/")
                    sub_indent = "  " * (level + 1)
                    for f in sorted(files)[:50]:
                        lines.append(f"{sub_indent}{f}")
                    if len(files) > 50:
                        lines.append(f"{sub_indent}... and {len(files) - 50} more files")
            else:
                items = sorted(target.iterdir())
                for item in items:
                    suffix = "/" if item.is_dir() else ""
                    lines.append(f"{item.name}{suffix}")

            return "\n".join(lines[:200])

        except Exception as e:
            return f"Error listing directory: {e}"
