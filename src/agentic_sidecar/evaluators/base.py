"""Base classes and interfaces for Sidecar evaluators (v0.3.0).

Defines the abstract interfaces that Planner, Critic, and Judge evaluators
inherit from. All evaluators are optional and model-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EvaluatorResult:
    """Result from an evaluator (Planner, Critic, or Judge).

    Attributes:
        status: Decision status (ALLOW, CHALLENGE, REPLAN, BLOCK, WARN, PAUSE, ESCALATE)
        rationale: Human-readable explanation of the decision
        confidence: Confidence score (0.0-1.0) for LLM-based evaluators
        metadata: Additional context-specific fields
        timestamp: When the evaluation occurred
        latency_ms: Time spent evaluating (milliseconds)
    """

    status: str  # Decision status from Decision.status
    rationale: str
    confidence: float = 1.0  # 1.0 for rule-based, 0.0-1.0 for LLM-based
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON export."""
        return {
            "status": self.status,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
        }


class EvaluatorBase(ABC):
    """Abstract base class for all Sidecar evaluators (Planner, Critic, Judge).

    Evaluators are optional, composable decision-time reasoning components
    that can be enabled or disabled independently. Each evaluator answers a
    specific question:
    - Planner: "Is the entire plan aligned with the user's intent?"
    - Critic: "Are there unsupported assumptions or contradictions?"
    - Judge: "Should this decision proceed? (LLM-based)"
    """

    def __init__(self, enabled: bool = True, name: str = ""):
        """Initialize evaluator.

        Args:
            enabled: Whether this evaluator is active
            name: Human-readable name for logging/debugging
        """
        self.enabled = enabled
        self.name = name or self.__class__.__name__

    @abstractmethod
    def evaluate(self, context: dict[str, Any]) -> EvaluatorResult:
        """Evaluate and return a decision.

        Args:
            context: Evaluation context with keys:
                - tool_name: Name of the tool being evaluated
                - arguments: Tool arguments
                - decision: Current Decision from the gate
                - intent: Active IntentEnvelope (if any)
                - history: Prior decisions in this task
                - plan: Full plan being executed (for Planner)

        Returns:
            EvaluatorResult with status and rationale
        """
        pass

    async def evaluate_async(self, context: dict[str, Any]) -> EvaluatorResult:
        """Async version of evaluate (optional override for LLM-based evaluators).

        Default implementation calls sync evaluate.
        """
        return self.evaluate(context)

    def on_enabled(self) -> None:
        """Called when evaluator is enabled (hook for initialization)."""
        return

    def on_disabled(self) -> None:
        """Called when evaluator is disabled (hook for cleanup)."""
        return


class JudgeProvider(ABC):
    """Abstract interface for model-agnostic Judge providers.

    Implementations can use any LLM provider (OpenAI, Anthropic, local model,
    etc.) as long as they implement this interface. The Sidecar remains
    independent of any specific provider.

    Design principle: Main Agent Model A ≠ Sidecar Judge Model B
    """

    def __init__(self, model: str = ""):
        """Initialize provider.

        Args:
            model: Model identifier (e.g., 'gpt-4', 'claude-3-opus')
        """
        self.model = model

    @abstractmethod
    def evaluate(
        self,
        question: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a question using the judge model (synchronous).

        Args:
            question: The question to ask the judge
            context: Context information for the decision

        Returns:
            Dictionary with keys:
                - decision: The judge's decision (ALLOW, BLOCK, CHALLENGE, WARN, etc.)
                - reasoning: Explanation for the decision
                - confidence: Confidence score (0.0-1.0)
                - usage: Token usage (if tracked)
        """
        pass

    async def evaluate_async(
        self,
        question: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a question using the judge model (async).

        Default implementation calls sync evaluate. Override for true async.
        """
        return self.evaluate(question, context)

    def cost_tracking_available(self) -> bool:
        """Whether this provider is configured to return cost in its usage.

        Defaults to False: an arbitrary provider cannot be assumed to report cost,
        and defaulting to True would defeat the cost-limit/budget preflight check.
        Providers that do report cost must override this to return True.
        """
        return False

    def validate(self) -> bool:
        """Validate that the provider is properly configured.

        Returns:
            True if valid, False if configuration is missing/invalid
        """
        return bool(self.model)
