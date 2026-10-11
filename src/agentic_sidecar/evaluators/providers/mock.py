"""Explicit offline provider for examples and contract tests; never calls an API."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from agentic_sidecar.evaluators.base import JudgeProvider


class MockJudge(JudgeProvider):
    def __init__(
        self,
        model: str = "mock",
        *,
        decision: str = "ALLOW",
        reasoning: str = "Offline fixture verdict",
        cost: float = 0.0,
        tokens: int = 0,
    ) -> None:
        super().__init__(model)
        self.response = {
            "decision": decision,
            "reasoning": reasoning,
            "confidence": 1.0,
            "usage": {"cost": cost, "total_tokens": tokens},
        }

    def evaluate(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(self.response)

    def cost_tracking_available(self) -> bool:
        return True
