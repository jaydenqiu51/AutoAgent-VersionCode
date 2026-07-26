"""Improvement Engine — the autonomous self-improving development loop.

This is the core of the framework. Instead of "run one task and stop",
the Engine continuously:

1. Audits the project for weaknesses
2. Builds a prioritized roadmap
3. Picks the highest-impact improvement
4. Implements it using the agent
5. Tests that nothing broke
6. Measures quality change
7. Updates the roadmap
8. Repeats until quality target reached or no improvements remain
"""

import logging
import os
from pathlib import Path
from typing import Callable, List, Optional

from ..config import config
from ..llm.base import BaseProvider
from ..tools.file_tools import ListDirectoryTool, ReadFileTool
from .agent import Agent
from .auditor import Auditor, AuditReport
from .memory import Memory
from .metrics import MetricsEvaluator, QualityTracker
from .planner import Planner
from .roadmap import Roadmap, RoadmapItemStatus
from .tester import Tester, TestResult
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class ImprovementEngine:
    """Autonomous self-improving development loop.

    Usage:
        engine = ImprovementEngine(
            goal="Transform this into a AAA-quality driving game",
            provider=provider,
            tool_registry=registry,
            tester=tester,
        )
        engine.run()
    """

    def __init__(
        self,
        goal: str,
        provider: BaseProvider,
        tool_registry: ToolRegistry,
        tester: Optional[Tester] = None,
        target_quality: float = 85.0,
        max_iterations: int = 100,
        reaudit_every: int = 10,  # Re-audit every N improvements
        on_phase: Optional[Callable[[str, str], None]] = None,
        on_improvement: Optional[Callable[[str, str, str], None]] = None,
        on_quality: Optional[Callable[[float, float, str], None]] = None,
    ):
        self._goal = goal
        self._provider = provider
        self._tools = tool_registry
        self._tester = tester or Tester()
        self._target_quality = target_quality
        self._max_iterations = max_iterations
        self._reaudit_every = reaudit_every

        self._auditor = Auditor(provider)
        self._roadmap = Roadmap()
        self._quality = QualityTracker(target_score=target_quality)
        self._metrics = MetricsEvaluator(provider)

        self._iteration = 0
        self._is_running = False
        self._should_stop = False

        # Callbacks
        self._on_phase = on_phase or (lambda phase, msg: None)
        self._on_improvement = on_improvement or (lambda iid, title, result: None)
        self._on_quality = on_quality or (lambda before, after, trend: None)

    def run(self) -> str:
        """Start the continuous improvement loop.

        Runs until:
        - Quality target reached
        - No improvements remain
        - Max iterations exhausted
        - User stops (via stop())
        """
        self._is_running = True
        self._should_stop = False

        # =========================================================
        # PHASE 1: PROJECT AUDIT
        # =========================================================
        self._on_phase("audit", "Performing comprehensive project audit...")
        project_info = self._gather_project_info()
        report = self._auditor.audit(project_info)

        self._on_phase("audit", f"Audit complete: {len(report.weaknesses)} weaknesses found across {len(report.category_scores)} categories")
        self._on_phase("audit", f"Overall score: {report.overall_score:.0f}/100")

        # Record baseline quality
        self._quality.record(
            score=report.overall_score,
            category_scores=report.category_scores,
            iteration=0,
            improvement_id="audit",
            notes=report.summary,
        )

        # =========================================================
        # PHASE 2: BUILD ROADMAP
        # =========================================================
        self._on_phase("roadmap", "Building prioritized improvement roadmap...")
        self._roadmap.load_from_audit(report)
        self._on_phase("roadmap", self._roadmap.get_summary())

        # =========================================================
        # PHASE 3: CONTINUOUS IMPROVEMENT LOOP
        # =========================================================
        self._on_phase("loop", "Entering continuous improvement loop...")
        self._on_phase("loop", f"Target quality: {self._target_quality:.0f}/100 | Max iterations: {self._max_iterations}")
        self._on_phase("loop", "")

        while not self._should_stop and self._iteration < self._max_iterations:
            self._iteration += 1

            # Check termination conditions
            if self._quality.target_reached:
                self._on_phase("complete", f"Target quality ({self._target_quality:.0f}) reached!")
                break

            # Get next improvement
            next_item = self._roadmap.get_next()
            if next_item is None:
                self._on_phase("complete", "No more improvements available in the roadmap.")
                break

            # Periodic re-audit
            if self._iteration > 1 and self._iteration % self._reaudit_every == 0:
                self._on_phase("reaudit", f"Re-auditing project (iteration {self._iteration})...")
                project_info = self._gather_project_info()
                new_report = self._auditor.audit(project_info)
                self._roadmap.reprioritize(new_report)
                self._on_phase("reaudit", self._roadmap.get_summary())

                # Skip to next iteration to pick from updated roadmap
                continue

            # =========================================================
            # STEP A: IMPLEMENT
            # =========================================================
            self._roadmap.mark_in_progress(next_item.id)

            quality_before = self._quality.current_score
            weakness = next_item.weakness

            self._on_phase("implement",
                f"[{self._iteration}/{self._max_iterations}] {weakness.category.value}/{weakness.severity.value}: "
                f"{weakness.title} (impact: {weakness.impact_score:.1f})")

            # Create a focused agent for this single improvement
            task_description = (
                f"Category: {weakness.category.value} | Severity: {weakness.severity.value}\n\n"
                f"IMPROVEMENT: {weakness.title}\n\n"
                f"Description: {weakness.description}\n\n"
                f"Suggested approach: {weakness.suggested_fix}\n\n"
                f"Affected files: {', '.join(weakness.affected_files) if weakness.affected_files else 'Investigate and determine'}\n\n"
                f"Implement this improvement. After you're done, the project should be demonstrably better."
            )

            agent = Agent(
                task=task_description,
                provider=self._provider,
                tool_registry=self._tools,
            )

            try:
                agent_result = agent.run()
            except Exception as e:
                logger.error(f"Agent failed on {weakness.id}: {e}")
                self._roadmap.mark_failed(next_item.id, str(e))
                continue

            # =========================================================
            # STEP B: TEST
            # =========================================================
            self._on_phase("test", f"Running validation checks...")
            test_results = self._tester.run_all()

            if not self._tester.all_passed(test_results):
                failures = [r for r in test_results if r.status.value in ("failed", "error")]
                failure_text = "; ".join(f"{r.name}: {r.output[:100]}" for r in failures)
                self._on_phase("test_failed", f"Tests failed: {failure_text}")

                # Try to fix failures
                self._on_phase("fix", "Attempting to fix test failures...")
                fix_task = (
                    f"The following improvement was just made but caused test failures:\n"
                    f"Improvement: {weakness.title}\n"
                    f"Test failures: {failure_text}\n\n"
                    f"Fix these failures while preserving the improvement."
                )
                fix_agent = Agent(task=fix_task, provider=self._provider, tool_registry=self._tools)
                try:
                    fix_agent.run()
                except Exception:
                    pass

                # Re-test
                test_results = self._tester.run_all()
                if not self._tester.all_passed(test_results):
                    failures = [r for r in test_results if r.status.value in ("failed", "error")]
                    self._roadmap.mark_failed(next_item.id, "; ".join(f"{r.name}: {r.output[:100]}" for r in failures))
                    continue

            # =========================================================
            # STEP C: MEASURE QUALITY
            # =========================================================
            self._on_phase("measure", "Evaluating quality impact...")
            project_state = self._gather_project_info()
            eval_result = self._metrics.evaluate(
                project_state=project_state,
                previous_quality=self._quality.get_progress(),
                recent_changes=f"Implemented: {weakness.title}\nAgent result: {agent_result[:500]}",
            )

            new_score = eval_result.get("overall_score", quality_before)
            category_scores = eval_result.get("category_scores", {})

            snapshot = self._quality.record(
                score=new_score,
                category_scores=category_scores,
                iteration=self._iteration,
                improvement_id=weakness.id,
                notes=eval_result.get("notes", ""),
            )

            # =========================================================
            # STEP D: EVALUATE & UPDATE ROADMAP
            # =========================================================
            quality_delta = new_score - quality_before

            if quality_delta > 0:
                self._roadmap.mark_completed(
                    next_item.id,
                    result=agent_result[:500],
                    quality_before=quality_before,
                    quality_after=new_score,
                )
                self._on_improvement(weakness.id, weakness.title,
                    f"Quality +{quality_delta:.1f}: {quality_before:.0f} → {new_score:.0f}")
            elif quality_delta >= -1:
                # Neutral — completed but didn't move the needle
                self._roadmap.mark_completed(
                    next_item.id,
                    result=f"Neutral impact: {agent_result[:200]}",
                    quality_before=quality_before,
                    quality_after=new_score,
                )
                self._on_improvement(weakness.id, weakness.title, f"Neutral (quality unchanged)")
            else:
                # Regression — mark as failed, will be reverted or retried
                self._roadmap.mark_failed(next_item.id,
                    f"Quality regression: {quality_before:.0f} → {new_score:.0f}")
                self._on_improvement(weakness.id, weakness.title,
                    f"REGRESSION: quality dropped {abs(quality_delta):.1f} points")

            self._on_quality(quality_before, new_score, self._quality.trend)

            # Progress report every 5 iterations
            if self._iteration % 5 == 0:
                self._on_phase("progress", self._quality.get_progress())
                self._on_phase("progress", self._roadmap.get_summary())

        # =========================================================
        # FINAL REPORT
        # =========================================================
        self._is_running = False

        return self._build_final_report()

    def stop(self) -> None:
        """Signal the engine to stop after the current iteration."""
        self._should_stop = True

    def _gather_project_info(self) -> str:
        """Collect information about the project for the auditor."""
        workspace = config.workspace
        if not workspace.exists():
            return f"Workspace: {workspace} (not found)"

        # Get file listing
        files = []
        total_files = 0

        for root, dirs, filenames in os.walk(workspace):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                       ("__pycache__", "node_modules", ".git", "venv", ".venv", "dist", "build")]
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), workspace)
                files.append(rel)
                total_files += 1
                if len(files) > 200:
                    break
            if len(files) > 200:
                break

        file_list = "\n".join(files[:150])

        # Get key file contents (up to 3 important-looking files)
        key_files = []
        important_patterns = ["main", "app", "index", "game", "engine", "config", "package.json", "setup.py"]
        for pattern in important_patterns:
            for f in files:
                if pattern in f.lower() and len(key_files) < 3:
                    try:
                        content = (workspace / f).read_text(encoding="utf-8", errors="replace")
                        key_files.append(f"=== {f} ===\n{content[:1500]}")
                    except Exception:
                        pass
                    break

        key_files_text = "\n\n".join(key_files) if key_files else "(no key files read)"

        return (
            f"Goal: {self._goal}\n\n"
            f"Workspace: {workspace}\n"
            f"Total files: {total_files}\n\n"
            f"Project structure:\n{file_list}\n\n"
            f"Key file contents:\n{key_files_text}"
        )

    def _build_final_report(self) -> str:
        """Build the final summary report."""
        lines = [
            "=" * 60,
            " IMPROVEMENT ENGINE - FINAL REPORT",
            "=" * 60,
            "",
            f"Goal: {self._goal}",
            f"Iterations: {self._iteration}",
            f"Stop reason: {self._get_stop_reason()}",
            "",
            self._quality.get_progress(),
            "",
            self._roadmap.get_summary(),
            "",
        ]

        if self._iteration > 0:
            lines.append("Completed improvements:")
            for item in self._roadmap._completed[-10:]:
                delta = item.quality_after - item.quality_before
                sign = "+" if delta > 0 else ""
                lines.append(f"  [{item.weakness.category.value}] {item.weakness.title} (quality {sign}{delta:.1f})")

        return "\n".join(lines)

    def _get_stop_reason(self) -> str:
        if self._should_stop:
            return "User stopped"
        if self._quality.target_reached:
            return f"Quality target ({self._target_quality:.0f}) reached"
        if self._roadmap.get_next() is None:
            return "No improvements remaining"
        if self._iteration >= self._max_iterations:
            return f"Max iterations ({self._max_iterations}) reached"
        return "Unknown"
