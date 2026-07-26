"""Quality metrics — measures project quality across dimensions.

Tracks quality scores over time to determine if improvements are actually working.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..llm.base import BaseProvider, Message


@dataclass
class QualitySnapshot:
    """A quality measurement at a point in time."""

    timestamp: datetime = field(default_factory=datetime.now)
    overall_score: float = 0.0  # 0-100
    category_scores: Dict[str, float] = field(default_factory=dict)
    iteration: int = 0
    improvement_id: str = ""
    notes: str = ""


class QualityTracker:
    """Tracks project quality over time through a series of snapshots.

    Used to answer: "Did that improvement actually make things better?"
    """

    def __init__(self, target_score: float = 85.0):
        self._history: List[QualitySnapshot] = []
        self._target_score = target_score

    @property
    def current_score(self) -> float:
        if not self._history:
            return 0.0
        return self._history[-1].overall_score

    @property
    def target_reached(self) -> bool:
        return self.current_score >= self._target_score

    @property
    def trend(self) -> str:
        """Is quality improving, declining, or stable?"""
        if len(self._history) < 2:
            return "stable"

        recent = [s.overall_score for s in self._history[-5:]]
        if len(recent) < 2:
            return "stable"

        if recent[-1] > recent[0] + 1:
            return "improving"
        elif recent[-1] < recent[0] - 1:
            return "declining"
        return "stable"

    def record(self, score: float, category_scores: Dict[str, float],
               iteration: int, improvement_id: str, notes: str = "") -> QualitySnapshot:
        """Record a new quality measurement."""
        snapshot = QualitySnapshot(
            overall_score=score,
            category_scores=category_scores,
            iteration=iteration,
            improvement_id=improvement_id,
            notes=notes,
        )
        self._history.append(snapshot)
        return snapshot

    def get_progress(self) -> str:
        """Return a human-readable progress summary."""
        if not self._history:
            return "No measurements yet."

        first = self._history[0]
        latest = self._history[-1]
        delta = latest.overall_score - first.overall_score
        direction = "up" if delta > 0 else "down"

        lines = [
            f"Quality: {first.overall_score:.1f} → {latest.overall_score:.1f} ({direction} {abs(delta):.1f})",
            f"Target: {self._target_score:.0f} ({latest.overall_score / self._target_score * 100:.0f}% reached)",
            f"Trend: {self.trend}, Iterations: {len(self._history)}",
        ]

        # Show category breakdown
        if latest.category_scores:
            lines.append("Categories:")
            for cat, score in sorted(latest.category_scores.items()):
                bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                lines.append(f"  {cat:<20} {bar} {score:.0f}/100")

        return "\n".join(lines)

    def to_summary_json(self) -> str:
        """Export quality history as JSON."""
        return json.dumps([{
            "timestamp": s.timestamp.isoformat(),
            "score": s.overall_score,
            "iteration": s.iteration,
            "categories": s.category_scores,
        } for s in self._history], indent=2)


METRICS_PROMPT = """You are a quality assurance expert. Evaluate the current state of the project against quality metrics.

Rate the project on a 0-100 scale for overall quality, and provide category-specific scores.
Be honest and critical — inflated scores prevent real improvement.

Categories to score (0-100 each):
- graphics, physics, ai, vehicles, world_design, optimization, networking
- ui, audio, lighting, animations, gameplay, architecture, testing, security

## Current Project State
{project_state}

## Previous Quality
{previous_quality}

## Recent Changes
{recent_changes}

Respond with JSON:
{{
  "overall_score": 72,
  "category_scores": {{
    "graphics": 65,
    "physics": 78,
    ...
  }},
  "notes": "Quality improved due to...",
  "biggest_remaining_weakness": "The next priority should be..."
}}"""


class MetricsEvaluator:
    """Evaluates project quality using the LLM."""

    def __init__(self, provider: BaseProvider):
        self._provider = provider

    def evaluate(
        self,
        project_state: str,
        previous_quality: str = "No previous measurement",
        recent_changes: str = "No recent changes",
    ) -> dict:
        """Evaluate current project quality.

        Returns a dict with overall_score, category_scores, notes.
        """
        prompt = METRICS_PROMPT.format(
            project_state=project_state,
            previous_quality=previous_quality,
            recent_changes=recent_changes,
        )

        response = self._provider.chat(
            messages=[Message(role="user", content=prompt)],
        )

        if not response.content:
            return {"overall_score": 50.0, "category_scores": {}, "notes": "No data"}

        try:
            content = response.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        except (json.JSONDecodeError, KeyError):
            pass

        return {"overall_score": 50.0, "category_scores": {}, "notes": "Parse failed"}
