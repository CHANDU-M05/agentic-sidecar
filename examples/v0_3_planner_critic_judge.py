"""Evaluator API examples for 0.6.1 (filename records introduction in 0.3).

Uses explicit plan dictionaries, heuristic Critic, and a bundled mock Judge.
No tools or remote model APIs are called. Run from the repository root:
    uv run python examples/v0_3_planner_critic_judge.py
"""

from agentic_sidecar import CriticEvaluator, DecisionContext, JudgeEvaluator, PlanEvaluator, Sidecar
from agentic_sidecar.evaluators.providers import MockJudge


def demo_1_planner_alignment() -> None:
    """Supply the full plan and goal directly to the Planner API."""
    planner = PlanEvaluator()
    goal = "Explain the disputed charge"
    clean = planner.evaluate({"goal": goal, "plan": [{"tool_name": "read_charge"}]})
    overreach = planner.evaluate(
        {
            "goal": goal,
            "plan": [{"tool_name": "read_charge"}, {"tool_name": "issue_refund"}],
        }
    )
    assert clean.status == "ALLOW"
    assert overreach.status == "REPLAN"
    print("\nExplicit plan:", clean.status)
    print("Plan with an unrequested refund:", overreach.status)
    print(overreach.rationale)


def demo_2_critic_challenges() -> None:
    """Show a heuristic challenge without dispatching any action."""
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        critic=CriticEvaluator(),
        roles=["critic"],
    )
    for tool in ("read_customer", "delete_records", "issue_refund"):
        verdict = sidecar.evaluate(DecisionContext(tool_name=tool))
        expected = "ALLOW" if tool == "read_customer" else "CHALLENGE"
        assert verdict.status == expected
        print(f"Critic {tool}: {verdict.status}")


def demo_3_judge_evaluation() -> None:
    """Show the bundled mock provider contract and synthetic usage."""
    judge = JudgeEvaluator(provider=MockJudge(model="demo-model"))
    result = judge.evaluate(
        {
            "tool_name": "send_notification",
            "arguments": {},
            "goal": "Notify the customer",
            "history": [],
        }
    )
    assert result.status == "ALLOW"
    print("\nMock Judge:", result.status, "illustrative confidence:", result.confidence)
    print("Synthetic usage cost:", judge.get_cost())


def demo_4_all_evaluators() -> None:
    """Compose tool-call stages and evaluate an explicit plan through Sidecar."""
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        planner=PlanEvaluator(),
        critic=CriticEvaluator(),
        judge=JudgeEvaluator(provider=MockJudge(model="demo-model")),
        roles=["policy", "risk", "planner", "critic", "judge"],
    )
    verdict = sidecar.evaluate(DecisionContext(tool_name="read_order"))
    assert verdict.status == "ALLOW"
    print("\nTool-call pipeline:", verdict.status)
    plan_verdict = sidecar.evaluate_plan([{"tool_name": "read_order"}], goal="Review order")
    assert plan_verdict.status == "ALLOW"
    print("Full-plan pipeline:", plan_verdict.status)


def demo_5_cost_tracking() -> None:
    """Account for synthetic mock usage locally, then reset it."""
    judge = JudgeEvaluator(provider=MockJudge(model="demo-model"))
    for _ in range(3):
        judge.evaluate({"tool_name": "read_order", "arguments": {}})
    print("\nSynthetic usage total:", judge.get_cost(), "(not measured API spend)")
    judge.reset_cost()
    assert judge.get_cost() == 0


def main() -> None:
    print("Evaluator API demo — explicit plans, heuristics, and mock provider responses")
    demo_1_planner_alignment()
    demo_2_critic_challenges()
    demo_3_judge_evaluation()
    demo_4_all_evaluators()
    demo_5_cost_tracking()


if __name__ == "__main__":
    main()
