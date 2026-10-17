# Examples

These examples run against the current **0.6.1** API. Versioned filenames record
when a capability was introduced; they are not separate installation requirements.
The [roadmap](../ROADMAP.md) describes upcoming enhancements.

From the repository root, install the development environment:

```bash
uv sync --extra dev --extra langgraph
```

All Python examples use local data or scripted responses and require no API keys.
The two LangGraph graph examples require the optional `langgraph` extra.

| Example | Demonstrates | Run |
| --- | --- | --- |
| [Customer support](governed_customer_support_agent.py) | Observe vs Govern, policy/risk/intent checks, BLOCK interception | `uv run python examples/governed_customer_support_agent.py` |
| [LangGraph Observe](langgraph_refund_observe_mode.py) | Real graph with a scripted model; advisory verdicts allow calls through | `uv run python examples/langgraph_refund_observe_mode.py` |
| [LangGraph Govern](langgraph_intent_guardian_govern_mode.py) | Real graph; $850 refund blocked, $120 refund allowed under a $500 constraint | `uv run python examples/langgraph_intent_guardian_govern_mode.py` |
| [Evaluator API](v0_3_planner_critic_judge.py) | Explicit plan ALLOW/REPLAN, heuristic CHALLENGE, mock Judge, pipeline composition | `uv run python examples/v0_3_planner_critic_judge.py` |
| [Provider contract](v0_3_judge_providers.py) | Explicit offline MockJudge responses, swapping, validation, synthetic usage accounting | `uv run python examples/v0_3_judge_providers.py` |
| [Budget and approval types](v0_4_budget_and_escalation.py) | Manual usage, PAUSE verdict, caller-managed approval response, audit serialization | `uv run python examples/v0_4_budget_and_escalation.py` |
| [Governance](v0_6_1_governance.py) | Runtime approve-once, rejection, suspension, full-plan review and shared Judge budget | `uv run python examples/v0_6_1_governance.py` |
| [Narration](v0_5_status_narration.py) | Manually recorded decisions, compliance, budget values, and narrator pause/resume state | `uv run python examples/v0_5_status_narration.py` |
| [CLI guide](v0_5_cli_guide.md) | Local status snapshots, follow formatting, JSON output, demo, and version | `uv run agentic-sidecar --help` |
| [Interactive notebook](sidecar_purpose_demo.ipynb) | Deterministic constraints across support, operations, and research scenarios | Open with Jupyter after installing it separately |

## Reading the output

`evaluate()` returns a decision; it does not execute or stop the action itself.
The LangGraph wrapper allows ALLOW/WARN in Govern mode; other outcomes resolve
or suspend. See [governance walkthrough](v0_6_1_governance.py) for runtime approvals.

Planner examples supply `plan` and `goal` directly to `PlanEvaluator.evaluate()`.
Mock Judge responses and usage values illustrate the interface rather than
measured model quality, latency, or pricing. Narrator pause/resume updates its
reported state; it does not control an agent. Live CLI/runtime status is planned
for 0.7, and additional adapters/integrations for 0.8.

See the v0.8 scoped-agent, correlated-evidence and MCP gateway examples described
in [the examples guide](../website/docs/examples.md).
