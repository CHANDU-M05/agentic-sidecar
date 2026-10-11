"""Budget Guardian -- cost/token ceilings enforced per task, through the same
Decision Gate as Policy and Risk rather than a side channel.

Tracks cumulative cost and token usage across a task's execution. When either
limit is exceeded, returns a PAUSE decision to escalate to human before
continuing -- the task isn't blocked outright, but human approval is required
to proceed over budget.

Planned for v0.4 -- fully implemented.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class BudgetResult:
    """Outcome of a budget evaluation: whether cost/token limits are exceeded."""

    exceeded: bool
    remaining_cost: float
    remaining_tokens: int | None
    reason: str = ""


@dataclass
class BudgetGuardian:
    """Tracks cumulative cost and token usage for a task, enforcing per-task
    ceilings.

    Not internally locked: use one `BudgetGuardian` per task, not one shared
    across concurrently-dispatched tool calls, or `record_invocation` can race.

    Attributes:
        max_cost: Maximum spend (USD) allowed for this task. Required.
        max_tokens: Maximum tokens (input + output) allowed. Optional.
    """

    max_cost: float
    max_tokens: int | None = None
    current_cost: float = field(default=0.0)
    current_tokens: int = field(default=0)

    def __post_init__(self) -> None:
        self._validate(self.max_cost, self.max_tokens)
        self._validate(self.current_cost, self.current_tokens)

    @staticmethod
    def _validate(cost: float, tokens: int | None) -> None:
        if isinstance(cost, bool) or not math.isfinite(cost) or cost < 0:
            raise ValueError("cost must be finite and nonnegative")
        if tokens is not None and (type(tokens) is not int or tokens < 0):
            raise ValueError("tokens must be a nonnegative integer")

    def record_invocation(
        self,
        cost: float,
        tokens: int | None = None,
    ) -> None:
        """Record a tool/LLM invocation's cost and tokens.

        Args:
            cost: Cost in USD for this invocation.
            tokens: Total tokens (input + output) for this invocation.
        """
        self._validate(cost, tokens)
        self._validate(self.current_cost + cost, self.current_tokens)
        self.current_cost += cost
        if tokens is not None:
            self.current_tokens += tokens

    def evaluate(self) -> BudgetResult:
        """Check whether cost/token limits are exceeded.

        Returns:
            BudgetResult with exceeded flag and remaining budget.
        """
        self._validate(self.max_cost, self.max_tokens)
        self._validate(self.current_cost, self.current_tokens)
        cost_exceeded = self.current_cost >= self.max_cost
        tokens_exceeded = self.max_tokens is not None and self.current_tokens >= self.max_tokens

        if cost_exceeded or tokens_exceeded:
            reasons = []
            if cost_exceeded:
                reasons.append(f"cost ${self.current_cost:.4f} >= ${self.max_cost:.4f}")
            if tokens_exceeded:
                reasons.append(f"tokens {self.current_tokens} >= {self.max_tokens}")
            return BudgetResult(
                exceeded=True,
                remaining_cost=max(0.0, self.max_cost - self.current_cost),
                remaining_tokens=(
                    max(0, self.max_tokens - self.current_tokens)
                    if self.max_tokens is not None
                    else None
                ),
                reason="; ".join(reasons),
            )

        return BudgetResult(
            exceeded=False,
            remaining_cost=self.max_cost - self.current_cost,
            remaining_tokens=(
                self.max_tokens - self.current_tokens if self.max_tokens is not None else None
            ),
        )

    def is_at_capacity(self) -> bool:
        """Quick check: are we at or over budget?"""
        return self.evaluate().exceeded

    def reset(self) -> None:
        """Reset cost/token counters for a new task."""
        self.current_cost = 0.0
        self.current_tokens = 0
