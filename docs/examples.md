# Examples

All examples live in the [`examples/`](https://github.com/DeepAgentLabs/agentic-sidecar/tree/main/examples) directory. Each is a self-contained runnable script.

---

## Governed Customer Support Agent

**File:** [`examples/governed_customer_support_agent.py`](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/governed_customer_support_agent.py)

Demonstrates all four Decision Gate modules (Policy, Risk, Intent Guardian, Budget Guardian) working together to govern a customer support agent that can read orders, issue refunds, and delete customers.

```bash
python examples/governed_customer_support_agent.py
```

What it shows:
- `read_order` → `ALLOW` (no rules triggered)
- `issue_refund(amount=250)` → `ALLOW` (under $500 constraint)
- `issue_refund(amount=850)` → `BLOCK` (IntentGuardian: exceeds `maximum_refund=500`)
- `delete_customer` → `BLOCK` (PolicyAdvisor: `delete_*` deny rule)
- Budget ceiling hit → `PAUSE` (BudgetGuardian: cumulative cost ≥ $5.00)

---

## LangGraph — Intent Guardian in Govern Mode

**File:** [`examples/langgraph_intent_guardian_govern_mode.py`](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/langgraph_intent_guardian_govern_mode.py)

Full LangGraph agent with `attach()`, IntentEnvelope, ConstraintBindings, and `SidecarBlockedError` handling.

```bash
pip install "agentic-sidecar[langgraph]"
python examples/langgraph_intent_guardian_govern_mode.py
```

---

## LangGraph — Observe Mode

**File:** [`examples/langgraph_refund_observe_mode.py`](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/langgraph_refund_observe_mode.py)

Shows how to start in Observe mode: the Sidecar evaluates every tool call and logs decisions without blocking execution. Good starting point for adding Sidecar to an existing agent.

```bash
pip install "agentic-sidecar[langgraph]"
python examples/langgraph_refund_observe_mode.py
```

---

## Plan Evaluator, Critic, and Judge (v0.3)

**File:** [`examples/v0_3_planner_critic_judge.py`](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/v0_3_planner_critic_judge.py)

Demonstrates the experimental evaluators: `PlanEvaluator` (REPLAN decisions), `CriticEvaluator` (CHALLENGE decisions), and `JudgeEvaluator`.

```bash
python examples/v0_3_planner_critic_judge.py
```

---

## Judge Providers (OpenAI and Anthropic)

**File:** [`examples/v0_3_judge_providers.py`](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/v0_3_judge_providers.py)

Shows how to configure `OpenAIJudge` and `AnthropicJudge` as providers for the `JudgeEvaluator`.

```bash
export OPENAI_API_KEY=...
python examples/v0_3_judge_providers.py
```

---

## Budget Guardian and Escalation (v0.4)

**File:** [`examples/v0_4_budget_and_escalation.py`](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/v0_4_budget_and_escalation.py)

Full example of `BudgetGuardian` with `record_invocation()`, triggering a `PAUSE` decision when the ceiling is reached, and handling the escalation via `@sidecar.on_escalation_required`.

```bash
python examples/v0_4_budget_and_escalation.py
```

---

## Status Narrator (v0.5)

**File:** [`examples/v0_5_status_narration.py`](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/v0_5_status_narration.py)

Demonstrates `StatusNarrator` — recording tool calls, generating narratives, tracking blocked decisions and intent violations, and printing a live status snapshot.

```bash
python examples/v0_5_status_narration.py
```

---

## CLI Guide (v0.5)

**File:** [`examples/v0_5_cli_guide.md`](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/v0_5_cli_guide.md)

A markdown walkthrough of the `agentic-sidecar` CLI commands with annotated output examples.

---

## Interactive Notebook

**File:** [`examples/sidecar_purpose_demo.ipynb`](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/examples/sidecar_purpose_demo.ipynb)

Jupyter notebook demonstrating the Sidecar concept end-to-end in an interactive format.

```bash
pip install jupyter
jupyter notebook examples/sidecar_purpose_demo.ipynb
```

---

## End-to-End Use Cases

For complete, step-by-step walkthroughs solving real-world production problems end-to-end (including multi-layer guardrails, LangGraph integration, and policy enforcement), visit the [Agentic Sidecar Use Cases Site](https://deepagentlabs.io/agentic-sidecar/usecases/).

