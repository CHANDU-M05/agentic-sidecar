# Examples

The examples target the **0.8.0** API. Historical version labels in filenames
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
| `v0_7_control_room.py` | Real HTTP approval/rejection, execution lifecycle and Control Room |
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
dispatch, plus full-plan review and automatic Judge accounting. The v0.7 Control
Room example uses a real local HTTP interface, records approval and rejection,
and counts actual tool effects. Standalone narrator methods update reported state. Provider mock costs are illustrative
values, not measured inference costs. See [supported scope](limitations.md)
and the [roadmap](roadmap.md).

For the notebook, install Jupyter separately and run:

```bash
jupyter notebook examples/sidecar_purpose_demo.ipynb
```

---

## End-to-End Use Cases

For complete, step-by-step walkthroughs solving real-world production problems end-to-end (including multi-layer guardrails, LangGraph integration, and policy enforcement), visit the [Agentic Sidecar Use Cases Site](https://deepagentlabs.io/agentic-sidecar/usecases/).


## v0.8 examples

- `examples/v0_8_scoped_agents.py`: two agents, shared context and policy, exclusive
  context/restrictions, explicit host delivery and blocked dispatch.
- `examples/v0_8_framework_agents.py`: host-bound LangGraph research and AutoGen
  refund tools, shared denial and separate exclusive context (requires both extras).
- `examples/v0_8_correlated_evidence.py`: credential-free native evidence export.
- `examples/v0_8_gateway_server.py`: separate-process credential-owning MCP server,
  launched by `tests/test_mcp_gateway.py` with `SIDECAR_RUN_GATEWAY=1`.

Run `uv run python examples/v0_8_scoped_agents.py`; install the `mcp` extra and run
`uv run pytest tests/test_mcp_gateway.py` for the real transport/gateway scenario.
Framework conformance runs through real native SDK dispatch without model calls.
