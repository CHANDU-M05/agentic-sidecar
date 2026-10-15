"""Optional live OpenAIJudge provider. Install agentic-sidecar[openai]."""

from __future__ import annotations

import importlib
import os
from typing import Any

from agentic_sidecar.evaluators.base import JudgeProvider
from agentic_sidecar.evaluators.providers.common import result_with_usage, serialize
from agentic_sidecar.gate.budget import BudgetGuardian


class OpenAIJudge(JudgeProvider):
    """Live SDK calls; choose the model and current USD rates explicitly.

    Inject client/async_client for tests or custom SDK configuration. SDK imports
    occur only on first invocation. Missing credentials never produce a mock verdict.
    """

    def __init__(
        self,
        model: str,
        api_key: str = "",
        *,
        client: Any = None,
        async_client: Any = None,
        timeout_ms: int = 5000,
        input_cost_per_million: float | None = None,
        output_cost_per_million: float | None = None,
    ) -> None:
        super().__init__(model)
        if type(timeout_ms) is not int or timeout_ms <= 0:
            raise ValueError("timeout_ms must be a positive integer")
        for rate in (input_cost_per_million, output_cost_per_million):
            if rate is not None:
                BudgetGuardian._validate(rate, None)
        if (input_cost_per_million is None) != (output_cost_per_million is None):
            raise ValueError("Supply both input and output token rates")
        self.api_key = api_key
        self.client = client
        self.async_client = async_client
        self.timeout_ms = timeout_ms
        self.input_rate = input_cost_per_million
        self.output_rate = output_cost_per_million

    def cost_tracking_available(self) -> bool:
        return self.input_rate is not None and self.output_rate is not None

    def validate(self) -> bool:
        return bool(
            self.model
            and (
                self.client is not None
                or self.async_client is not None
                or self.api_key
                or os.environ.get("OPENAI_API_KEY")
            )
        )

    def _client(self, asynchronous: bool = False) -> Any:
        existing = self.async_client if asynchronous else self.client
        if existing is not None:
            return existing
        sdk = importlib.import_module("openai")
        constructor = getattr(sdk, "AsyncOpenAI" if asynchronous else "OpenAI")
        client = constructor(
            api_key=self.api_key or os.environ.get("OPENAI_API_KEY"),
            timeout=self.timeout_ms / 1000,
            max_retries=0,
        )
        if asynchronous:
            self.async_client = client
        else:
            self.client = client
        return client

    def evaluate(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        client = self._client().with_options(timeout=self.timeout_ms / 1000, max_retries=0)
        response = client.responses.create(
            model=self.model,
            instructions=question,
            input=serialize(context),
            text={"format": {"type": "json_object"}},
            max_output_tokens=512,
            store=False,
        )
        return self._result(response)

    async def evaluate_async(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        client = self._client(True).with_options(timeout=self.timeout_ms / 1000, max_retries=0)
        response = await client.responses.create(
            model=self.model,
            instructions=question,
            input=serialize(context),
            text={"format": {"type": "json_object"}},
            max_output_tokens=512,
            store=False,
        )
        return self._result(response)

    def _result(self, response: Any) -> dict[str, Any]:
        return result_with_usage(
            response.output_text,
            response.usage.input_tokens,
            response.usage.output_tokens,
            self.input_rate,
            self.output_rate,
        )
