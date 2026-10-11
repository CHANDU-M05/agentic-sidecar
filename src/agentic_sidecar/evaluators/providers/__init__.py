"""LLM Judge providers: Model-agnostic implementations.

Provides different LLM backend options for the Judge evaluator:
- OpenAIJudge: Uses OpenAI models (GPT-4, GPT-3.5, etc.)
- AnthropicJudge: Uses Anthropic models (Claude 3, Claude 2, etc.)

Design: Swap providers without changing Sidecar code.
"""

from agentic_sidecar.evaluators.providers.anthropic import AnthropicJudge
from agentic_sidecar.evaluators.providers.openai import OpenAIJudge

__all__ = ["MockJudge", "OpenAIJudge", "AnthropicJudge"]

from agentic_sidecar.evaluators.providers.mock import MockJudge
