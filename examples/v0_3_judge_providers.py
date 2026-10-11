"""Mock Judge provider contract for 0.6.1 (introduced in 0.3).

MockJudge returns scripted responses. Model identifiers
are labels in this example; no API key or network connection is used, and
usage values do not represent real pricing or provider performance.

Run: uv run python examples/v0_3_judge_providers.py
"""

from agentic_sidecar import JudgeEvaluator, MockJudge


def main() -> None:
    print("Mock provider contract demo — no API calls; synthetic usage only")
    context = {
        "tool_name": "read_order",
        "arguments": {"order_id": "A100"},
        "goal": "Review the order",
        "history": [],
    }
    judge = JudgeEvaluator(provider=MockJudge(model="mock-first"))
    first = judge.evaluate(context)
    assert first.status == "ALLOW"
    print("First offline mock:", first.status, first.metadata["usage"])
    print("Synthetic cost counter:", judge.get_cost())

    # Swap the implementation through the same provider interface.
    judge.provider = MockJudge(model="mock-second")
    judge.reset_cost()
    second = judge.evaluate(context)
    assert second.status == "ALLOW"
    print("Second offline mock:", second.status, second.metadata["usage"])
    print("Synthetic cost counter:", judge.get_cost())
    print("These values illustrate accounting and are not a provider ranking.")

    # Current validation checks the model label, not remote authentication.
    assert MockJudge(model="mock-first").validate()
    assert not MockJudge(model="").validate()
    print("Model-label validation and provider swapping passed.")
    judge.reset_cost()
    assert judge.get_cost() == 0


if __name__ == "__main__":
    main()
