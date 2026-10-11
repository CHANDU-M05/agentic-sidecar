# Examples

The examples target the **0.6.1** API. Historical version labels in filenames
identify their introduction. Run them from the repository root:

```bash
uv sync --extra dev --extra langgraph
```

Every Python example uses local data or scripted responses; no API key is needed.
See the [example catalog](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/README.md)
for links and setup details.

| File under `examples/` | Purpose |
| --- | --- |
| `governed_customer_support_agent.py` | Observe vs Govern with policy/risk/intent checks; reads and within-limit refunds pass, over-limit refunds and deletions receive BLOCK |
| `langgraph_refund_observe_mode.py` | A scripted real LangGraph agent executes tools while Sidecar records advisory verdicts |
| `langgraph_intent_guardian_govern_mode.py` | A scripted real graph blocks $850 and permits $120 under a $500 refund constraint |
| `v0_3_planner_critic_judge.py` | Direct full-plan checks, heuristic Critic, mock Judge, and composed evaluation |
| `v0_3_judge_providers.py` | Mock provider swapping and synthetic usage accounting |
| `v0_4_budget_and_escalation.py` | Manual budget accounting, PAUSE verdict, explicitly invoked approval handler, and audit serialization |
| `v0_6_1_governance.py` | Runtime approval, suspension, full-plan review and shared Judge budget |
| `v0_5_status_narration.py` | Manually supplied decisions, compliance/budget values, and narrator pause/resume state |
| `v0_5_cli_guide.md` | Local CLI snapshots, JSON, follow formatting, demo, and version |
| `sidecar_purpose_demo.ipynb` | Interactive deterministic intent constraints for multiple domains |

For example:

```bash
uv run python examples/v0_3_planner_critic_judge.py
uv run python examples/v0_4_budget_and_escalation.py
uv run python examples/langgraph_intent_guardian_govern_mode.py
```

The customer-support example configures a budget but does not spend against it;
use the budget example to see a PAUSE verdict. Its over-limit refund is classified
by Risk before the Intent stage; the dedicated LangGraph Govern example isolates
Intent Guardian behavior.

The budget example handles an approval request in its own application code.
The governance example demonstrates runtime approval and suspension before
dispatch, plus full-plan review and automatic Judge accounting. Narrator methods update reported state, while a live
runtime connection is planned for 0.7. Provider mock costs are illustrative
values, not measured inference costs. See [supported scope](limitations.md)
and the [roadmap](roadmap.md).

For the notebook, install Jupyter separately and run:

```bash
jupyter notebook examples/sidecar_purpose_demo.ipynb
```
