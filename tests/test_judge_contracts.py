"""Provider contracts and sync/async failure, timeout and accounting parity."""

import asyncio
import json
import threading
from types import SimpleNamespace

import pytest

from agentic_sidecar import BudgetGuardian, DecisionContext, JudgeEvaluator, MockJudge, Sidecar
from agentic_sidecar.evaluators.providers import AnthropicJudge, OpenAIJudge


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "status", ["ALLOW", "WARN", "BLOCK", "CHALLENGE", "REPLAN", "PAUSE", "ESCALATE"]
)
def test_verdict_and_usage_parity(asynchronous, status):
    budget = BudgetGuardian(max_cost=1, max_tokens=100)
    judge = JudgeEvaluator(MockJudge(decision=status, cost=0.1, tokens=20), budget=budget)
    result = asyncio.run(judge.evaluate_async({})) if asynchronous else judge.evaluate({})
    assert result.status == status
    assert result.metadata["usage"]["total_tokens"] == 20
    assert result.latency_ms > 0
    assert budget.current_tokens == 20
    assert budget.current_cost == judge.get_cost() == 0.1


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("bad", ["status", "confidence", "reason", "usage", "cost", "tokens"])
def test_malformed_provider_outputs_raise(asynchronous, bad):
    provider = MockJudge(cost=0.1, tokens=20)
    if bad == "status":
        provider.response["decision"] = "INVALID"
    elif bad == "confidence":
        provider.response["confidence"] = float("nan")
    elif bad == "reason":
        del provider.response["reasoning"]
    elif bad == "usage":
        provider.response["usage"] = None
    elif bad == "cost":
        provider.response["usage"]["cost"] = -1
    else:
        provider.response["usage"]["total_tokens"] = 1.5
    judge = JudgeEvaluator(provider)
    with pytest.raises((ValueError, KeyError, TypeError)):
        if asynchronous:
            asyncio.run(judge.evaluate_async({}))
        else:
            judge.evaluate({})
    if bad in ("status", "confidence", "reason"):
        assert judge.get_cost() == 0.1


@pytest.mark.parametrize("failure,status", [("fail_closed", "BLOCK"), ("fail_open", "ALLOW")])
def test_provider_failure_reaches_sidecar(failure, status):
    provider = MockJudge()
    provider.response["decision"] = "garbage"
    sidecar = Sidecar(on_sidecar_failure=failure, roles=["judge"], judge=JudgeEvaluator(provider))
    assert sidecar.evaluate(DecisionContext(tool_name="read")).status == status


@pytest.mark.parametrize("asynchronous", [False, True])
def test_cost_ceiling(asynchronous):
    judge = JudgeEvaluator(MockJudge(cost=0.2), cost_limit=0.1)
    result = asyncio.run(judge.evaluate_async({})) if asynchronous else judge.evaluate({})
    assert result.status == "PAUSE"
    assert judge.get_cost() == 0.2


def test_judge_usage_automatically_reaches_budget_once():
    budget = BudgetGuardian(max_cost=0.1, max_tokens=20)
    judge = JudgeEvaluator(MockJudge(cost=0.1, tokens=20))
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed", roles=["budget", "judge"], budget=budget, judge=judge
    )
    decision = sidecar.evaluate(DecisionContext(tool_name="read"))
    assert decision.status == "PAUSE"
    assert "Budget Guardian" in decision.reason
    assert budget.current_cost == 0.1
    assert budget.current_tokens == 20
    assert sidecar.evaluate(DecisionContext(tool_name="read")).status == "PAUSE"
    assert judge.get_cost() == 0.1


def test_sync_timeout_late_usage_accounted_and_no_duplicate_call():
    release = threading.Event()
    finished = threading.Event()

    class Slow(MockJudge):
        def evaluate(self, question, context):
            release.wait(1)
            return super().evaluate(question, context)

    budget = BudgetGuardian(max_cost=1)
    judge = JudgeEvaluator(Slow(cost=0.1), timeout_ms=10, budget=budget)
    original = judge._finish

    def finish(*args):
        result = original(*args)
        finished.set()
        return result

    judge._finish = finish
    try:
        with pytest.raises(TimeoutError):
            judge.evaluate({})
        with pytest.raises(RuntimeError, match="outstanding"):
            judge.evaluate({})
    finally:
        release.set()
    assert finished.wait(1)
    assert budget.current_cost == judge.get_cost() == 0.1


def test_native_async_timeout():
    class Slow(MockJudge):
        async def evaluate_async(self, question, context):
            await asyncio.sleep(1)
            return self.response

    judge = JudgeEvaluator(Slow(), timeout_ms=10)
    with pytest.raises(TimeoutError):
        asyncio.run(judge.evaluate_async({}))


@pytest.mark.parametrize("provider_type", [OpenAIJudge, AnthropicJudge])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_live_provider_sdk_contract(provider_type, asynchronous):
    payload = json.dumps({"decision": "ESCALATE", "reasoning": "ask user", "confidence": 0.9})
    calls = []
    response = SimpleNamespace(
        output_text=payload,
        content=[SimpleNamespace(type="text", text=payload)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )

    class Client:
        def __init__(self):
            self.responses = self.messages = self

        def with_options(self, **kwargs):
            assert kwargs == {"timeout": 5.0, "max_retries": 0}
            return self

        def create(self, **kwargs):
            calls.append(kwargs)
            return response

    class AsyncClient(Client):
        async def create(self, **kwargs):
            return super().create(**kwargs)

    provider = provider_type(
        "explicit-model",
        client=Client(),
        async_client=AsyncClient(),
        input_cost_per_million=1,
        output_cost_per_million=2,
    )
    judge = JudgeEvaluator(provider)
    context = {"goal": "review", "constraints": {"maximum": 10}, "history": [], "plan": []}
    result = asyncio.run(judge.evaluate_async(context)) if asynchronous else judge.evaluate(context)
    assert result.status == "ESCALATE"
    assert result.metadata["usage"]["total_tokens"] == 15
    assert judge.get_cost() == 0.00002
    assert calls[0]["model"] == "explicit-model"
    serialized = calls[0].get("input") or calls[0]["messages"][0]["content"]
    assert json.loads(serialized) == context


@pytest.mark.parametrize(
    "provider_type,key", [(OpenAIJudge, "OPENAI_API_KEY"), (AnthropicJudge, "ANTHROPIC_API_KEY")]
)
def test_live_provider_never_falls_back_to_mock(provider_type, key, monkeypatch):
    monkeypatch.delenv(key, raising=False)
    provider = provider_type("explicit-model")
    assert not provider.validate()
    with pytest.raises(ValueError, match="not configured"):
        JudgeEvaluator(provider).evaluate({})


@pytest.mark.parametrize(
    "cost,tokens", [(-1, 1), (float("nan"), 1), (float("inf"), 1), (1, -1), (1, 1.5), (True, 1)]
)
def test_invalid_accounting_is_atomic(cost, tokens):
    budget = BudgetGuardian(max_cost=1)
    with pytest.raises(ValueError):
        budget.record_invocation(cost, tokens)
    assert budget.current_cost == budget.current_tokens == 0


def test_zero_token_budget():
    result = BudgetGuardian(max_cost=1, max_tokens=0).evaluate()
    assert result.exceeded
    assert result.remaining_tokens == 0


@pytest.mark.parametrize(
    "text", ["not JSON", "[]", '{"decision":"INVALID","reasoning":"bad","confidence":1}']
)
def test_malformed_live_output_still_accounts_returned_usage(text):
    from agentic_sidecar.evaluators.providers.common import result_with_usage

    provider = MockJudge()
    provider.response = result_with_usage(text, 10, 5, 1, 2)
    budget = BudgetGuardian(max_cost=1)
    judge = JudgeEvaluator(provider, budget=budget)
    with pytest.raises(ValueError):
        judge.evaluate({})
    assert budget.current_tokens == 15
    assert budget.current_cost == judge.get_cost() == 0.00002


@pytest.mark.parametrize("provider_type", [OpenAIJudge, AnthropicJudge])
def test_live_cost_configuration_rejected_before_spending(provider_type):
    provider = provider_type("explicit-model", client=object())
    with pytest.raises(ValueError, match="token rates"):
        JudgeEvaluator(provider).evaluate({})


@pytest.mark.parametrize("failure,executes", [("fail_closed", False), ("fail_open", True)])
def test_provider_timeout_controls_governed_dispatch(failure, executes):
    from agentic_sidecar import SidecarBlockedError
    from agentic_sidecar.adapters.langgraph import attach

    release = threading.Event()

    class Slow(MockJudge):
        def evaluate(self, question, context):
            release.wait(1)
            return super().evaluate(question, context)

    calls = []

    def read():
        calls.append(1)
        return "done"

    sidecar = Sidecar(
        on_sidecar_failure=failure,
        mode="govern",
        roles=["judge"],
        judge=JudgeEvaluator(Slow(), timeout_ms=10),
    )
    wrapped = attach(sidecar, [read])[0]
    try:
        if executes:
            assert wrapped() == "done"
        else:
            with pytest.raises(SidecarBlockedError):
                wrapped()
        assert calls == ([1] if executes else [])
        assert "TimeoutError" in sidecar.decisions[-1][1].reason
    finally:
        release.set()
