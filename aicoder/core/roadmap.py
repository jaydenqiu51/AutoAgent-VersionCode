"""Prioritized improvement roadmap — manages the backlog of weaknesses.

The roadmap is a live, re-prioritized queue. After each improvement is applied,
the roadmap is re-evaluated: completed items are removed, new weaknesses may be
discovered, and priorities shift based on the updated project state.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from .auditor import AuditReport, Category, Severity, Weakness


class RoadmapItemStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class RoadmapItem:
    """A single improvement in the roadmap."""

    id: str
    weakness: Weakness
    status: RoadmapItemStatus = RoadmapItemStatus.PENDING
    priority_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    attempt_count: int = 0
    last_result: str = ""
    quality_before: float = 0.0
    quality_after: float = 0.0

    @property
    def is_ready(self) -> bool:
        """Check if this item's dependencies are all completed."""
        return self.status == RoadmapItemStatus.PENDING


class Roadmap:
    """A live, prioritized backlog of improvements.

    The roadmap is dynamic — it's rebuilt from audit data, re-prioritized
    after each improvement, and tracks completion history.
    """

    def __init__(self):
        self._items: Dict[str, RoadmapItem] = {}
        self._completed: List[RoadmapItem] = []
        self._iteration: int = 0

    @property
    def pending_count(self) -> int:
        return sum(1 for i in self._items.values() if i.status == RoadmapItemStatus.PENDING)

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    @property
    def total_count(self) -> int:
        return len(self._items) + len(self._completed)

    def load_from_audit(self, report: AuditReport) -> None:
        """Populate the roadmap from an audit report.

        Sorts by impact_score descending, then applies dependency ordering.
        """
        # Create roadmap items for all weaknesses
        new_items = {}
        for weakness in report.weaknesses:
            item = RoadmapItem(
                id=weakness.id,
                weakness=weakness,
                priority_score=weakness.impact_score,
            )
            new_items[weakness.id] = item

        # Merge with existing (keep completed items)
        for item_id, item in new_items.items():
            if item_id not in self._items:
                self._items[item_id] = item
            else:
                # Update existing item but preserve status
                existing = self._items[item_id]
                existing.weakness = item.weakness
                existing.priority_score = item.priority_score

        self._iteration += 1

    def get_next(self) -> Optional[RoadmapItem]:
        """Get the highest-priority ready item.

        Priority is determined by:
        1. impact_score (higher = more important)
        2. Dependencies must be satisfied
        3. effort_estimate is a tiebreaker (low effort first)
        """
        candidates = [
            item for item in self._items.values()
            if item.status == RoadmapItemStatus.PENDING
            and self._dependencies_satisfied(item)
        ]

        if not candidates:
            return None

        # Sort by priority (impact score), then effort (low effort first tiebreaker)
        effort_order = {"low": 0, "medium": 1, "high": 2, "epic": 3}
        candidates.sort(
            key=lambda i: (
                -i.priority_score,
                effort_order.get(i.weakness.effort_estimate, 1),
            )
        )

        return candidates[0]

    def mark_in_progress(self, item_id: str) -> None:
        if item_id in self._items:
            self._items[item_id].status = RoadmapItemStatus.IN_PROGRESS
            self._items[item_id].attempt_count += 1

    def mark_completed(self, item_id: str, result: str, quality_before: float, quality_after: float) -> None:
        """Mark an item as completed and move it to history."""
        if item_id in self._items:
            item = self._items.pop(item_id)
            item.status = RoadmapItemStatus.COMPLETED
            item.completed_at = datetime.now()
            item.last_result = result
            item.quality_before = quality_before
            item.quality_after = quality_after
            self._completed.append(item)

    def mark_failed(self, item_id: str, reason: str) -> None:
        """Mark an item as failed (will be retried later if priority remains high)."""
        if item_id in self._items:
            item = self._items[item_id]
            if item.attempt_count < 3:
                item.status = RoadmapItemStatus.PENDING  # Retry
                item.last_result = f"Attempt {item.attempt_count} failed: {reason}"
            else:
                item.status = RoadmapItemStatus.FAILED
                item.last_result = f"Failed after 3 attempts: {reason}"

    def mark_blocked(self, item_id: str, reason: str) -> None:
        if item_id in self._items:
            self._items[item_id].status = RoadmapItemStatus.BLOCKED
            self._items[item_id].last_result = reason

    def reprioritize(self, new_audit: Optional[AuditReport] = None) -> None:
        """Re-prioritize the backlog based on latest audit data."""
        if new_audit:
            self.load_from_audit(new_audit)

    def get_summary(self) -> str:
        """Return a human-readable summary of the roadmap."""
        by_category: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}

        for item in self._items.values():
            if item.status == RoadmapItemStatus.PENDING:
                cat = item.weakness.category.value
                sev = item.weakness.severity.value
                by_category[cat] = by_category.get(cat, 0) + 1
                by_severity[sev] = by_severity.get(sev, 0) + 1

        lines = [
            f"  Roadmap Status: {self.completed_count} completed, {self.pending_count} pending, {self.total_count} total",
        ]

        if by_severity:
            lines.append("  By Severity: " + ", ".join(f"{k}: {v}" for k, v in sorted(by_severity.items())))
        if by_category:
            lines.append("  By Category: " + ", ".join(f"{k}: {v}" for k, v in sorted(by_category.items())))

        return "\n".join(lines)

    def _dependencies_satisfied(self, item: RoadmapItem) -> bool:
        """Check if all dependencies for this item are completed."""
        if not item.weakness.dependencies:
            return True

        completed_ids = {c.weakness.id for c in self._completed}
        return all(dep in completed_ids for dep in item.weakness.dependencies)
