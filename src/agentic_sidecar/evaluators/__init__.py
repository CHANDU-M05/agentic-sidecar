"""Evaluators module: LLM-based decision evaluation (v0.3.0+).

Provides optional, model-agnostic evaluators for plan-level and decision-level
assessment. All evaluators inherit from EvaluatorBase and can be composed
independently into the Sidecar.

Available Evaluators:
- PlanEvaluator: Assesses plan alignment with intent
- CriticEvaluator: Challenges decisions for flaws and risks
- JudgeEvaluator: LLM-based decision evaluation

Available Providers:
- OpenAIJudge: Uses OpenAI models (GPT-4, GPT-3.5, etc.)
- AnthropicJudge: Uses Anthropic models (Claude, etc.)
"""

from agentic_sidecar.evaluators.base import (
    EvaluatorBase,
    EvaluatorResult,
    JudgeProvider,
)
from agentic_sidecar.evaluators.critic import CriticChallenge, CriticEvaluator
from agentic_sidecar.evaluators.judge import JudgeEvaluator
from agentic_sidecar.evaluators.planner import PlanEvaluator, PlanStep
from agentic_sidecar.evaluators.providers import AnthropicJudge, OpenAIJudge

__all__ = [
    "MockJudge",
    "EvaluatorBase",
    "EvaluatorResult",
    "JudgeProvider",
    "PlanEvaluator",
    "PlanStep",
    "CriticEvaluator",
    "CriticChallenge",
    "JudgeEvaluator",
    "OpenAIJudge",
    "AnthropicJudge",
]

from agentic_sidecar.evaluators.providers.mock import MockJudge
