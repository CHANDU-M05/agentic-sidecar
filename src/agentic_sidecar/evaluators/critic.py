"""Critic evaluator: Challenge detection (v0.3.0)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic_sidecar.evaluators.base import EvaluatorBase, EvaluatorResult


@dataclass
class CriticChallenge:
    """A challenge raised by the Critic."""

    category: str
    severity: str
    description: str
    evidence: str = ""
    suggestion: str = ""


class CriticEvaluator(EvaluatorBase):
    """Challenges decisions for logical flaws and risky patterns."""

    def __init__(self, enabled: bool = True, threshold: float = 0.7):
        super().__init__(enabled=enabled, name="CriticEvaluator")
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between zero and one")
        self.threshold = threshold

    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        """Challenge a proposed decision."""
        if not self.enabled:
            return EvaluatorResult(
                status="ALLOW",
                rationale="CriticEvaluator is disabled",
                confidence=1.0,
            )

        tool_name = context.get("tool_name", "")
        arguments = context.get("arguments", {})
        goal = context.get("goal", "")
        history = context.get("history", [])

        challenges = self._analyze_decision(tool_name, arguments, goal, history)
        metadata = context.get("metadata", {})
        if metadata.get("authorized") is True:
            challenges = [c for c in challenges if c.category != "risky"]
        if metadata.get("eligibility_verified") is True:
            challenges = [c for c in challenges if c.category != "assumption"]
        if metadata.get("backup_verified") is True:
            challenges = [c for c in challenges if c.category != "reasoning"]
        for step in context.get("plan", []):
            name = step.get("tool_name", "") if isinstance(step, dict) else step.tool_name
            args = step.get("arguments", {}) if isinstance(step, dict) else (step.arguments or {})
            challenges.extend(self._analyze_decision(name, args or {}, goal, history))

        if not challenges or self.threshold > 0.85:
            return EvaluatorResult(
                status="ALLOW",
                rationale="Decision passes critical review",
                confidence=1.0,
            )

        rationale = self._format_challenges(challenges)
        return EvaluatorResult(
            status="CHALLENGE",
            rationale=rationale,
            confidence=0.85,
            metadata={"challenge_count": len(challenges)},
        )

    def _analyze_decision(
        self, tool_name: str, arguments: dict[str, Any], goal: str, history: list[Any]
    ) -> list[CriticChallenge]:
        """Analyze decision for challenges."""
        challenges = []
        challenges.extend(self._check_risky_operations(tool_name, arguments))
        challenges.extend(self._check_contradictions(tool_name, history))
        challenges.extend(self._check_assumptions(tool_name, arguments))
        challenges.extend(self._check_reasoning_completeness(tool_name))
        return [c for c in challenges if c.severity in ("medium", "high")]

    def _check_risky_operations(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> list[CriticChallenge]:
        """Identify risky operations."""
        challenges = []
        risky_tools = {
            "delete": "Deletes data permanently",
            "refund": "Refunds money to customer",
            "cancel": "Cancels service",
        }

        for risky_tool, desc in risky_tools.items():
            if risky_tool in tool_name.lower():
                challenges.append(
                    CriticChallenge(
                        category="risky",
                        severity="high",
                        description=f"Risky: {desc}",
                        suggestion="Ensure explicit authorization",
                    )
                )

        return challenges

    def _check_contradictions(self, tool_name: str, history: list[Any]) -> list[CriticChallenge]:
        """Check for contradictions."""
        opposites = {
            "approve": "reject",
            "reject": "approve",
            "enable_feature": "disable_feature",
            "disable_feature": "enable_feature",
        }
        opposite = opposites.get(tool_name.lower())
        if opposite is None:
            return []
        for entry in history:
            name = entry.get("tool_name") if isinstance(entry, dict) else entry.tool_name
            status = entry.get("status") if isinstance(entry, dict) else entry.status
            if name == opposite and status in ("ALLOW", "WARN"):
                return [
                    CriticChallenge(
                        "contradiction",
                        "high",
                        f"Proposed {tool_name} reverses previously permitted {opposite}",
                        suggestion="Explain the change in intent",
                    )
                ]
        return []

    def _check_assumptions(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> list[CriticChallenge]:
        """Identify unsupported assumptions."""
        challenges = []
        if "refund" in tool_name.lower():
            challenges.append(
                CriticChallenge(
                    category="assumption",
                    severity="medium",
                    description="Assumes refund is within policy",
                    suggestion="Verify refund eligibility",
                )
            )
        return challenges

    def _check_reasoning_completeness(self, tool_name: str) -> list[CriticChallenge]:
        """Check if reasoning is complete."""
        challenges = []
        if "delete" in tool_name.lower():
            challenges.append(
                CriticChallenge(
                    category="reasoning",
                    severity="high",
                    description="No backup mentioned",
                    suggestion="Confirm data is backed up",
                )
            )
        return challenges

    def _format_challenges(self, challenges: list[CriticChallenge]) -> str:
        """Format challenges as readable output."""
        lines = ["Critic has raised concerns:"]
        for challenge in challenges:
            lines.append(f"  - {challenge.description}")
            if challenge.suggestion:
                lines.append(f"    Suggestion: {challenge.suggestion}")
        return "\n".join(lines)
