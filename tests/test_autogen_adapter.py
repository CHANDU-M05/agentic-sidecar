"""Exercise the second adapter through a real SDK dispatch, without a model."""

import asyncio

import pytest

from agentic_sidecar import Sidecar, SidecarBlockedError
from agentic_sidecar.adapters.autogen import attach
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule


def test_real_autogen_dispatch() -> None:
    core = pytest.importorskip("autogen_core")
    calls: list[int] = []

    def refund(amount: int) -> str:
        """Refund a customer."""
        calls.append(amount)
        return "refunded"

    sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")
    (tool,) = attach(sidecar, [refund])
    assert asyncio.run(tool.run_json({"amount": 10}, core.CancellationToken())) == "refunded"
    sidecar.policy = PolicyAdvisor([PolicyRule(tool="refund", effect="deny")])
    with pytest.raises(SidecarBlockedError):
        asyncio.run(tool.run_json({"amount": 100}, core.CancellationToken()))
    assert calls == [10]
