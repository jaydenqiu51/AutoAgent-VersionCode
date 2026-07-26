"""Project auditor — analyzes the entire codebase for weaknesses across all dimensions.

Produces a structured audit report with categorized weaknesses, severity scores,
and concrete improvement suggestions.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from ..config import config
from ..llm.base import BaseProvider, Message


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    COSMETIC = "cosmetic"


class Category(Enum):
    GRAPHICS = "graphics"
    PHYSICS = "physics"
    AI = "ai"
    VEHICLES = "vehicles"
    WORLD = "world_design"
    OPTIMIZATION = "optimization"
    NETWORKING = "networking"
    UI = "ui"
    AUDIO = "audio"
    LIGHTING = "lighting"
    ANIMATIONS = "animations"
    GAMEPLAY = "gameplay"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"


@dataclass
class Weakness:
    """A single identified weakness in the project."""

    id: str
    category: Category
    severity: Severity
    title: str
    description: str
    impact_score: float  # 0.0 - 10.0
    effort_estimate: str  # "low", "medium", "high", "epic"
    affected_files: List[str] = field(default_factory=list)
    suggested_fix: str = ""
    dependencies: List[str] = field(default_factory=list)  # IDs of prerequisites


@dataclass
class AuditReport:
    """Complete project audit containing all identified weaknesses."""

    project_name: str
    total_files: int
    weaknesses: List[Weakness] = field(default_factory=list)
    overall_score: float = 0.0  # 0-100
    category_scores: Dict[str, float] = field(default_factory=dict)
    summary: str = ""

    def get_by_category(self, category: Category) -> List[Weakness]:
        return [w for w in self.weaknesses if w.category == category]

    def get_by_severity(self, severity: Severity) -> List[Weakness]:
        return [w for w in self.weaknesses if w.severity == severity]

    def get_top_issues(self, n: int = 10) -> List[Weakness]:
        return sorted(self.weaknesses, key=lambda w: w.impact_score, reverse=True)[:n]


AUDIT_SYSTEM_PROMPT = """You are a senior game developer and software architect conducting a comprehensive project audit.

Analyze the project and identify ALL weaknesses, flaws, missing features, performance issues, and improvement opportunities. Think like a AAA studio lead.

## Categories to Analyze
- **graphics**: Visual quality, shaders, post-processing, materials, textures, rendering pipeline
- **physics**: Movement, collisions, forces, realism, edge cases
- **ai**: NPC behavior, pathfinding, decision-making, believability
- **vehicles**: Handling, variety, customization, damage, audio
- **world_design**: Level layout, variety, landmarks, districts, immersion, scale
- **optimization**: FPS, draw calls, memory usage, loading times, asset efficiency
- **networking**: Multiplayer readiness, sync, latency handling
- **ui**: HUD, menus, readability, responsiveness, accessibility
- **audio**: SFX, music, spatial audio, variety, polish
- **lighting**: Dynamic lights, shadows, ambient, atmosphere, performance
- **animations**: Smoothness, variety, transitions, character/vehicle animation
- **gameplay**: Core loop, fun factor, progression, balance, mechanics depth
- **architecture**: Code organization, modularity, maintainability, error handling
- **testing**: Test coverage, stability, edge case handling
- **security**: Input validation, data safety, anti-cheat considerations
- **accessibility**: Color blindness, controls, subtitles, difficulty options

## Output Format
Respond with a JSON object:
{
  "overall_score": 65,
  "summary": "The project has solid core mechanics but lacks polish...",
  "category_scores": {
    "graphics": 55,
    "physics": 70,
    ...
  },
  "weaknesses": [
    {
      "id": "w001",
      "category": "graphics",
      "severity": "high",
      "title": "No shadows in outdoor scenes",
      "description": "Shadow maps are not configured...",
      "impact_score": 8.5,
      "effort_estimate": "medium",
      "affected_files": ["src/renderer.js", "src/scene.js"],
      "suggested_fix": "Enable shadow maps on the directional light...",
      "dependencies": []
    }
  ]
}

Be THOROUGH. Find at least 15-20 weaknesses across multiple categories.
For each weakness, assign a realistic impact_score (0-10) and effort_estimate.
The overall_score should reflect the project's current quality (0-100)."""


class Auditor:
    """Performs a comprehensive project audit to identify all weaknesses."""

    def __init__(self, provider: BaseProvider):
        self._provider = provider

    def audit(self, project_info: str) -> AuditReport:
        """Run a full project audit.

        Args:
            project_info: Description of the project (file listing, tech stack, etc.)

        Returns:
            AuditReport with all identified weaknesses.
        """
        messages = [
            Message(role="system", content=AUDIT_SYSTEM_PROMPT),
            Message(role="user", content=f"Audit this project:\n\n{project_info}"),
        ]

        response = self._provider.chat(messages=messages)

        if not response.content:
            return self._empty_report("No audit data received from LLM.")

        # Parse JSON from response
        try:
            # Find JSON block in response
            content = response.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                return self._parse_report(data)
        except (json.JSONDecodeError, KeyError) as e:
            pass

        return self._empty_report(f"Failed to parse audit data: {response.content[:200]}")

    def _parse_report(self, data: dict) -> AuditReport:
        """Parse the JSON audit data into an AuditReport."""
        report = AuditReport(
            project_name=data.get("project_name", "Unknown Project"),
            total_files=data.get("total_files", 0),
            overall_score=data.get("overall_score", 50.0),
            category_scores=data.get("category_scores", {}),
            summary=data.get("summary", ""),
        )

        for w_data in data.get("weaknesses", []):
            try:
                weakness = Weakness(
                    id=w_data.get("id", f"w{len(report.weaknesses)}"),
                    category=Category(w_data.get("category", "architecture")),
                    severity=Severity(w_data.get("severity", "medium")),
                    title=w_data.get("title", "Untitled weakness"),
                    description=w_data.get("description", ""),
                    impact_score=float(w_data.get("impact_score", 5.0)),
                    effort_estimate=w_data.get("effort_estimate", "medium"),
                    affected_files=w_data.get("affected_files", []),
                    suggested_fix=w_data.get("suggested_fix", ""),
                    dependencies=w_data.get("dependencies", []),
                )
                report.weaknesses.append(weakness)
            except (ValueError, KeyError):
                continue

        return report

    def _empty_report(self, summary: str) -> AuditReport:
        return AuditReport(
            project_name="Unknown",
            total_files=0,
            summary=summary,
        )
