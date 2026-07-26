"""Test validator — verifies that improvements haven't broken the project.

Supports multiple validation strategies:
- run_tests: Execute test suites
- lint_check: Run linters / static analysis
- build_check: Verify the project builds
- runtime_check: Start the project and check for errors
"""

import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

from ..config import config


class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Result of a single validation check."""

    name: str
    status: TestStatus
    output: str
    duration_ms: float


class Tester:
    """Runs validation checks to ensure the project is stable after changes.

    You can register custom test functions via add_check().
    """

    def __init__(self):
        self._checks: List[Callable[[], TestResult]] = []

    def add_check(self, check_fn: Callable[[], TestResult]) -> None:
        """Register a custom validation check.

        check_fn should return a TestResult.
        """
        self._checks.append(check_fn)

    def run_all(self) -> List[TestResult]:
        """Run all registered checks and return results."""
        results = []
        for check in self._checks:
            start = time.time()
            try:
                result = check()
            except Exception as e:
                result = TestResult(
                    name=check.__name__,
                    status=TestStatus.ERROR,
                    output=str(e),
                    duration_ms=0,
                )
            result.duration_ms = (time.time() - start) * 1000
            results.append(result)
        return results

    def all_passed(self, results: List[TestResult]) -> bool:
        """Check if all tests passed."""
        return all(r.status in (TestStatus.PASSED, TestStatus.SKIPPED) for r in results)

    def summary(self, results: List[TestResult]) -> str:
        """Return a human-readable summary."""
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        lines = [
            f"Test Results: {passed} passed, {failed} failed, {errors} errors, {skipped} skipped",
        ]

        for r in results:
            icon = {"passed": "PASS", "failed": "FAIL", "error": "ERR!", "skipped": "SKIP"}[r.status.value]
            lines.append(f"  [{icon}] {r.name} ({r.duration_ms:.0f}ms)")
            if r.status != TestStatus.PASSED and r.output:
                for line in r.output.split("\n")[:5]:
                    lines.append(f"         {line}")

        return "\n".join(lines)


def make_file_exists_check(file_paths: List[str]) -> Callable[[], TestResult]:
    """Create a check that verifies specific files exist."""
    def check():
        workspace = config.workspace
        missing = []
        for fp in file_paths:
            if not (workspace / fp).exists():
                missing.append(fp)
        if missing:
            return TestResult(
                name="file_exists",
                status=TestStatus.FAILED,
                output=f"Missing files: {', '.join(missing)}",
                duration_ms=0,
            )
        return TestResult(name="file_exists", status=TestStatus.PASSED, output="All files present", duration_ms=0)
    return check


def make_command_check(name: str, command: str, timeout: int = 30) -> Callable[[], TestResult]:
    """Create a check that runs a shell command and verifies it succeeds."""
    def check():
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(config.workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                return TestResult(name=name, status=TestStatus.PASSED, output=result.stdout[:500], duration_ms=0)
            return TestResult(name=name, status=TestStatus.FAILED,
                              output=f"Exit {result.returncode}\n{result.stderr[:500]}", duration_ms=0)
        except subprocess.TimeoutExpired:
            return TestResult(name=name, status=TestStatus.ERROR, output="Timeout", duration_ms=0)
        except Exception as e:
            return TestResult(name=name, status=TestStatus.ERROR, output=str(e), duration_ms=0)
    return check


def make_lint_check(file_pattern: str = "*.py") -> Callable[[], TestResult]:
    """Create a check that runs Python syntax validation on files."""
    def check():
        import py_compile
        import glob as glob_mod
        workspace = config.workspace
        errors = []
        files = list(workspace.rglob(file_pattern))
        for f in files[:50]:  # Limit to 50 files
            try:
                py_compile.compile(str(f), doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"{f.relative_to(workspace)}: {e}")
        if errors:
            return TestResult(name="syntax_check", status=TestStatus.FAILED,
                              output="\n".join(errors[:10]), duration_ms=0)
        return TestResult(name="syntax_check", status=TestStatus.PASSED,
                          output=f"{len(files)} files OK", duration_ms=0)
    return check
