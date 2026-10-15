"""Shared serialization and usage helpers; no SDK imports."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from agentic_sidecar.gate.budget import BudgetGuardian


def serialize(context: dict[str, Any]) -> str:
    def encode(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        raise TypeError(f"Unsupported context type: {type(value).__name__}")

    return json.dumps(context, default=encode, allow_nan=False)


def result_with_usage(
    text: str,
    input_tokens: int,
    output_tokens: int,
    input_rate: float | None,
    output_rate: float | None,
) -> dict[str, Any]:
    BudgetGuardian._validate(0.0, input_tokens)
    BudgetGuardian._validate(0.0, output_tokens)
    cost = None
    if input_rate is not None and output_rate is not None:
        cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost": cost,
    }
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"provider_error": "Provider output is not valid JSON"}
    if not isinstance(result, dict):
        result = {"provider_error": "Provider output must be a JSON object"}
    result["usage"] = usage
    return result
