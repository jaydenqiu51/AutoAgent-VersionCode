"""Search tools: grep_search, glob_find, web_search."""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict

from ..config import config
from .base import BaseTool


class GrepTool(BaseTool):
    """Search for text patterns in files using regex."""

    @property
    def name(self) -> str:
        return "grep_search"

    @property
    def description(self) -> str:
        return "Search for a regex pattern in files within the workspace."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in. Defaults to workspace root.",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g. '*.py' or '*.{js,ts}').",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Whether the search is case-sensitive. Defaults to false.",
                },
            },
            "required": ["pattern"],
        }

    def execute(
        self,
        pattern: str,
        path: str = "",
        file_pattern: str = "*",
        case_sensitive: bool = False,
        **kwargs,
    ) -> str:
        search_dir = config.workspace
        if path:
            p = Path(path)
            search_dir = p if p.is_absolute() else config.workspace / p

        if not search_dir.exists():
            return f"Error: Directory not found: {search_dir}"

        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"

        results = []
        match_count = 0

        try:
            for root, dirs, files in os.walk(search_dir):
                # Skip hidden directories and common ignores
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".git", "venv", ".venv")]

                for fname in files:
                    if not fnmatch.fnmatch(fname, file_pattern):
                        continue

                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            for i, line in enumerate(f, 1):
                                if regex.search(line):
                                    rel_path = os.path.relpath(fpath, config.workspace)
                                    results.append(f"{rel_path}:{i}: {line.strip()[:200]}")
                                    match_count += 1
                                    if match_count >= 100:
                                        results.append("... [truncated, found 100+ matches]")
                                        return "\n".join(results)
                    except (OSError, UnicodeDecodeError):
                        continue

        except Exception as e:
            return f"Error during search: {e}"

        if not results:
            return f"No matches found for pattern '{pattern}'."

        return "\n".join(results)


class GlobTool(BaseTool):
    """Find files matching a glob pattern."""

    @property
    def name(self) -> str:
        return "glob_find"

    @property
    def description(self) -> str:
        return "Find files matching a glob pattern (e.g. '**/*.py', '*.js')."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files (e.g. '**/*.py', 'src/**/*.ts').",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in. Defaults to workspace root.",
                },
            },
            "required": ["pattern"],
        }

    def execute(self, pattern: str, path: str = "", **kwargs) -> str:
        search_dir = config.workspace
        if path:
            p = Path(path)
            search_dir = p if p.is_absolute() else config.workspace / p

        if not search_dir.exists():
            return f"Error: Directory not found: {search_dir}"

        matches = []
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".git", "venv", ".venv")]

            for fname in files:
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, search_dir)

                # Match against both relative and just the filename
                if fnmatch.fnmatch(rel_path, f"**/{pattern}") or fnmatch.fnmatch(fname, pattern) or fnmatch.fnmatch(rel_path, pattern):
                    matches.append(os.path.relpath(full_path, config.workspace))

            if len(matches) >= 200:
                break

        if not matches:
            return f"No files found matching '{pattern}'."

        matches = sorted(matches)
        if len(matches) > 100:
            matches = matches[:100]
            matches.append(f"... and {len(matches) - 100} more matches")

        return "\n".join(matches)


class WebSearchTool(BaseTool):
    """Search the web (placeholder — requires API key integration)."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information. Returns a summary of results."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
            },
            "required": ["query"],
        }

    def execute(self, query: str, **kwargs) -> str:
        # This is a placeholder. Real implementation would use SerpAPI, Brave Search, etc.
        return (
            f"Web search is not configured. To enable it, integrate a search API "
            f"(e.g., SerpAPI, Brave Search, Google Custom Search).\n"
            f"Query was: {query}\n"
            f"Tip: Set AICODER_SEARCH_API_KEY in your .env file."
        )
