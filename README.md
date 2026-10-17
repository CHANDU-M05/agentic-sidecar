# agentic-sidecar

**A companion intelligence and real-time supervision layer for autonomous AI agents.**

> The Main Agent acts. The Sidecar observes, thinks, advises, and governs.

## Status

**Current checkout version: 0.8.1.** The runtime brings together deterministic
intent/policy/risk supervision, optional evaluators, budget accounting,
narration, and the CLI. See the [roadmap](ROADMAP.md) for release history
and upcoming capability stages.

| Capability | Current behavior |
| --- | --- |
| Runtime, policy/risk, Intent Guardian | Deterministic rules, constraint bindings, expiry warnings, intent/history injection |
| Observe / Govern modes | Observe records; Govern executes ALLOW/WARN and resolves or suspends other outcomes |
| Budget | Validated manual accounting plus automatic Judge usage; ceilings produce PAUSE |
| Human escalation and provenance | Local/HTTP approvals, immutable runtime audit events, optional durable JSONL and causal execution links |
| Planner / Critic | Full-plan boundary, bound constraints, selected plan/history heuristics and supplied evidence flags |
| Judge | Explicit MockJudge; optional live OpenAI/Anthropic SDK providers, validated verdicts, timeouts and usage accounting |
| Narration / CLI | Runtime-connected `status --endpoint ... --follow`, execution narration and `control`/`approve`; standalone narrator remains available |
| Frameworks / integrations | LangGraph, AutoGen, CrewAI, OpenAI Agents, Google ADK and MCP; correlated Lens decisions and Chaos recovery |
| Shared / Exclusive scopes | Context only, guardrails only, or both; explicit host context delivery and mandatory guardrail composition |

Live status, audit and Control Room: [usage and acceptance evidence](website/docs/live-operations.md).
Authenticated provider smoke remains pending credentials.

Next: **0.9 evaluation, privacy and authority → 1.0 stable schemas**.
See [supported scope and limitations](website/docs/limitations.md) for operational details.

### Installation & Usage
```bash
# Core package
pip install agentic-sidecar

# With LangGraph adapter (v0.4 features)
pip install "agentic-sidecar[langgraph]"

# CLI usage (v0.5)
agentic-sidecar status              # Single status snapshot
agentic-sidecar status --endpoint "$SIDECAR_ENDPOINT" --follow  # Live task
agentic-sidecar status --json       # JSON output
agentic-sidecar demo                # Interactive demo
agentic-sidecar version             # Show version
agentic-sidecar approval-demo       # Try the local approval prompt
```

See [Python API (implemented)](#python-api-implemented) below and [`examples/`](examples/) 
for runnable scripts. See [ROADMAP.md](ROADMAP.md) for the full build plan.

## Contents

- [Why](#why)
- [What it is not](#what-it-is-not)
- [Architecture](#architecture)
- [Sidecar vs. Agent Harness](#sidecar-vs-agent-harness)
- [Main Agent vs. Sidecar](#main-agent-vs-sidecar)
- [How the Decision Gate evaluates a decision](#how-the-decision-gate-evaluates-a-decision)
- [Sidecar modules](#sidecar-modules)
- [Python API (implemented)](#python-api-implemented)
- [Planned Python API](#planned-python-api)
- [Operating modes](#operating-modes)
- [Long-term: an intent propagation layer](#long-term-an-intent-propagation-layer)
- [The DeepAgentLabs ecosystem](#the-deepagentlabs-ecosystem)
- [Roadmap](#roadmap)
- [License](#license)

## Why

Autonomous agents chain a lot of reasoning and tool calls between a user's
request and a real-world effect:

```text
User → Agent → Planning → Sub-Agent → MCP → Tool → API → External System
```

Three things go wrong in that chain that permission checks alone don't catch:

- **Intent drift** — "investigate why production is slow" quietly becomes
  "restart the production database." Nobody revoked authority; the agent's
  plan just wandered.
- **Technically-allowed, contextually-wrong actions** — `refund_customer()`
  is a permitted tool call. Refunding $850 against a $500 authorization is
  not a permitted *decision*, even though the tool call succeeds.
- **No live visibility** — long-running agents act for minutes at a time
  with no answer to "what is it doing right now, and can I stop it?"

`agentic-sidecar` is designed to attach to any agent framework, but the first
release proves that against one framework only — LangGraph — before claiming
the rest (see [Design Constraints](ROADMAP.md#design-constraints)
in ROADMAP.md). Either way, it answers a different question than permission
checks or observability tools do:

> **Not** "can this agent call this tool?" — **"should it, right now, given
> what the user actually asked for?"**

## What it is not

- **Not a multi-agent framework.** The Sidecar never owns or executes the
  task plan, and it never replaces a worker agent. It may independently
  critique the Main Agent's plan or propose alternatives (the Planner
  module) — but the Main Agent decides whether to act on that critique, and
  remains the one that executes.
- **Not a content-safety guardrail.** Libraries like NeMo Guardrails or
  Guardrails AI validate a single prompt/response turn against rules. The
  Sidecar evaluates a *decision* — a tool call or plan step — against intent
  and context accumulated across an entire task.
- **Not a tracing/observability tool.** That's
  [AgenticLens](https://github.com/DeepAgentLabs/agenticlens)'s job:
  "what did the agent do, and why did it fail?" — after the fact. The
  Sidecar's job is "should it continue?" — while it's still running.
- **Not just LLM-as-a-Judge.** A judge model is one possible evaluator inside
  one Sidecar module (§ [Sidecar modules](#sidecar-modules)). Most decisions
  should never reach an LLM at all — see [Operating
  modes](#operating-modes) and the cost-control design in
  [ROADMAP.md](ROADMAP.md).
- **Not an agent harness.** It doesn't run the agent loop, manage tools, or
  handle retries — that's LangGraph's, CrewAI's, or your custom loop's job.
  The Sidecar attaches to whatever harness is already running the agent; see
  [Sidecar vs. Agent Harness](#sidecar-vs-agent-harness).

## Architecture

```text
                    USER
                      │
                 User Intent
                      │
                      ▼
              ┌───────────────┐
              │  MAIN AGENT   │
              │   EXECUTOR    │
              └───────┬───────┘
                      │
              Plans / Decisions
                      │
                      ▼
            ┌─────────────────────┐
            │   AGENTIC SIDECAR   │
            │                     │
            │ Intent Guardian     │
            │ Planner             │
            │ Critic              │
            │ Judge               │
            │ Risk Evaluator      │
            │ Policy Advisor      │
            │ Decision Gate       │
            │ Status Interpreter  │
            └──────────┬──────────┘
                       │
          Advice / Approval / Challenge
                       │
                       ▼
                 MAIN AGENT
                       │
                       ▼
                  MCP / Tools
                       │
                       ▼
                External Systems
```

The Sidecar is attached to the execution lifecycle. It does not own the
user's task and is never a second worker in the plan.

## Sidecar vs. Agent Harness

An **agent harness** (LangGraph, a custom loop, OpenAI Agents SDK, Microsoft
Agent Framework, ...) is the control and execution environment: it runs the
agent loop and manages tools, state, context, retries, and lifecycle.
`agentic-sidecar` doesn't replace that — it attaches to it as a decision-time
supervision layer:

```text
Agent Harness   = control and execution loop.
Agentic Sidecar = decision-time supervision layer for that loop.
```

The harness answers *"how do I execute this workflow?"* The Sidecar answers
*"should this decision happen, given what the human originally asked for?"*

This distinction matters most once a task fans out across a delegation
chain — Agent A → Agent B → Agent C → MCP/Tool — where each hop tends to
receive only the sub-task it needs to perform, not the original constraints
and authority behind it:

```text
Human Intent → Agent A → delegates → Agent B → delegates → Agent C → MCP/Tool
```

The Sidecar's Intent Envelope (§ [Sidecar modules](#sidecar-modules)) is
designed to travel with the task through that chain instead of being
reconstructed from conversation history at every hop — see [Long-term: an
intent propagation layer](#long-term-an-intent-propagation-layer).

Where it pays for itself: without a supervision layer, a harness typically
discovers a bad decision only after acting on it —

```text
Plan → Act → Fail → Recover → Replan
```

— versus catching it before execution:

```text
Plan → Sidecar Check → Act
          ├── ALLOW
          ├── CHALLENGE
          ├── REPLAN
          ├── BLOCK
          └── ESCALATE
```

This architecture focuses on decision reliability and control. Comparative
reliability and inference-overhead measurements are planned in the roadmap.
Architecture rationale:
[concept.md § 23](concept.md#23-sidecar-vs-agent-harness).

## Main Agent vs. Sidecar

| Main Agent | Agentic Sidecar |
| --- | --- |
| Accomplishes the task | Maintains original intent |
| Reasons about the domain problem | Independently evaluates plans and decisions |
| Selects and calls tools | Challenges questionable decisions |
| Interacts with MCP servers / APIs | Evaluates risk and checks policy |
| Executes actions | Decides when human approval is required |
| Produces the final result | Reports supplied execution state and verdicts; adapters enforce configured boundaries |

## How the Decision Gate evaluates a decision

Three modules ask three genuinely different questions about the same
proposed action, and the roadmap's job is to keep them from collapsing into
one generic "policy engine":

```text
             USER INTENT
                  │
          Intent Envelope
                  │
                  ▼
             MAIN AGENT
                  │
           proposed action
                  │
                  ▼
              SIDECAR
          ┌───────┼────────┐
          │       │        │
       Policy    Risk    Intent
          │       │        │
   "Are you    "How      "Is this
   permitted   dangerous  actually what
   to do       is this    the human
   this?"      action?"   asked you to
                          accomplish?"
          │       │        │
          └───────┼────────┘
                  │
             DECISION GATE
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
     ALLOW      REPLAN     ESCALATE
                              │
                            HUMAN
```

Policy and Risk are largely mechanical — permission lists, thresholds,
tool-argument patterns — and v0.1 ships them with zero LLM calls (see
[ROADMAP.md](ROADMAP.md)). Intent (v0.2) is still deterministic, not
LLM-based, but is the one that gets closest to "what the user actually
meant" so far, via structured `IntentEnvelope` constraints rather than
free-form judgment — full semantic understanding is further out on the
roadmap.

The diagram shows the supervision model. The current `Decision` type supports
all seven outcomes. Govern permits ALLOW/WARN, raises `SidecarBlockedError`
for BLOCK, invokes approvals for PAUSE/ESCALATE, and raises `SidecarSuspendedError`
for unresolved outcomes, CHALLENGE and REPLAN before dispatch.
See [supported scope](website/docs/limitations.md) and the [roadmap](ROADMAP.md#build-order).

## Sidecar modules

The target architecture below includes partial and planned capabilities.
See the Status table above for current behavior. Users enable only what they need:

```text
Agentic Sidecar
│
├── Intent Guardian     — Intent Envelope, alignment checks, drift detection
├── Planner              — independently evaluates the agent's plan
├── Critic                — challenges a proposed decision before it executes
├── Judge                 — optional independent (and independent-model) evaluation
├── Risk Evaluator        — classifies an action's risk before deciding whether to escalate
├── Policy Advisor        — deterministic policy rules (cheapest check, runs first)
├── Decision Gate         — turns evaluations into ALLOW / WARN / CHALLENGE / REPLAN / PAUSE / BLOCK / ESCALATE
├── Budget Guardian       — cost/token ceilings per task
├── Status Interpreter    — translates raw tool/MCP traces into human-readable narration
└── Human Escalation      — pauses execution and requests approval
```

```yaml
sidecar:
  intent:
    enabled: true
    preserve_original_intent: true
  planner:
    enabled: false        # off by default — see cost design in ROADMAP.md
  critic:
    enabled: false        # off by default — see cost design in ROADMAP.md
  policy:
    enabled: true
    source: policies.yaml
  risk:
    enabled: true
    intervention_threshold: 0.80
  judge:
    enabled: false        # off by default — see cost design in ROADMAP.md
    model: independent-model
  budget:
    enabled: true
    max_cost: 2.00
  human_approval:
    enabled: true
  on_sidecar_failure: fail_closed   # or fail_open — see ROADMAP.md
```

## Python API (implemented)

A runnable constraint example using plain callables, with no model or API key:

```python
from agentic_sidecar import Sidecar, SidecarBlockedError
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.intent import ConstraintBinding, IntentEnvelope, IntentGuardian, Requester

def issue_refund(order_id: str, amount: float) -> str:
    """Issue a refund for an order."""
    return f"refunded {amount} for {order_id}"

envelope = IntentEnvelope(
    goal="Refund order A100 up to $500",
    requested_by=Requester(id="support_lead"),
    constraints={"maximum_refund": 500},
)
guardian = IntentGuardian(envelope, [ConstraintBinding(
    constraint="maximum_refund", tool="issue_refund", arg_name="amount", op="lte",
)])
sidecar = Sidecar(
    on_sidecar_failure="fail_closed", mode="govern",
    intent=guardian, roles=["policy", "risk", "intent_guardian"],
)
(refund,) = attach(sidecar, [issue_refund])
print(refund("A100", 120))  # refunded 120 for A100
try:
    refund("A100", 850)
except SidecarBlockedError as exc:
    print(exc.decision.status)  # BLOCK; refund function was not called
```

Use `mode="observe"` to record verdicts while permitting wrapped calls.
`evaluate(DecisionContext(...))` computes a verdict without dispatching tools.
`set_intent(guardian)` changes the active task envelope; budget reset is separate.

For full-plan review, supply the plan explicitly:

```python
from agentic_sidecar import PlanEvaluator, Sidecar

reviewer = Sidecar(on_sidecar_failure="fail_closed", planner=PlanEvaluator(), roles=["planner"])
result = reviewer.evaluate_plan(
    [{"tool_name": "read_charge"}, {"tool_name": "issue_refund"}],
    goal="Explain the disputed charge",
)
print(result.status)  # REPLAN
```

A `before_tool_call` hook replaces the entire built-in pipeline, including
budget and evaluators. See [API reference](website/docs/api-reference.md),
[configuration](website/docs/configuration.md), and [runnable examples](examples/README.md).

## Planned Python API

Live operations and v0.8 framework/scoped integrations are implemented. See
[validated SDK versions and limits](website/docs/integrations.md).
Today `attach(sidecar, tools)` is adapter-specific and `evaluate()` accepts
`DecisionContext`. Generic whole-agent attachment will be considered when
multiple integrations demonstrate a useful shared boundary.

## Operating modes

| Mode | Current behavior |
| --- | --- |
| **Observe** | Computes/logs decisions; wrapped calls execute regardless of verdict |
| **Govern** | ALLOW/WARN execute; BLOCK stops; PAUSE/ESCALATE invoke approvals or suspend; CHALLENGE/REPLAN suspend |

Catch `SidecarSuspendedError` to return control to your agent loop. Configure
`escalation_handler=CLIApprovalHandler()` or register `on_escalation_required`
for local approval. Approve-once applies to the current call; modify-intent
reevaluates with a complete envelope; stop persists on that Sidecar instance.
Use TaskRuntime and OperatorServer for [live operator controls](website/docs/live-operations.md).
See [governance usage and validation](website/docs/governance.md).

## Long-term: an intent propagation layer

The nearer-term stages above focus on runtime supervision. The
`IntentEnvelope` (§ [Sidecar modules](#sidecar-modules)) is designed to
survive being handed off — not just checked once and discarded:

```text
Human
  │
  └── Intent Envelope #182
            │
            ▼
         Agent A
            │
        delegates
            ▼
         Agent B
            │
           MCP
            ▼
         Agent C
            │
           Tool
```

If every hop in a delegation chain can answer *what was originally
requested, who authorized it, what constraints apply, what authority was
actually delegated, and whether intent has since changed* — that's no
longer just a feature of one package. It's closer to an interoperability
concern for autonomous systems generally, which is why v1.0 targets
publishing the envelope as a versioned schema in `ai-operations-spec`
rather than keeping it as an internal Sidecar structure (see the v1.0 entry
in [ROADMAP.md](ROADMAP.md#build-order)).
This is explicitly a v1.0 target, not something v0.1 needs to anticipate —
noted here because it's the reason the envelope's shape deserves care early,
even though nothing consumes it across process boundaries yet.

## The DeepAgentLabs ecosystem

```text
                 DeepAgentLabs
              Autonomous AI Systems
                      │
        ┌─────────────┼─────────────┐
        │             │             │
     OBSERVE         GUIDE        CONNECT
        │             │             │
 AgenticLens    Agentic Sidecar  Agentic MCP
        │             │             │
        └─────────────┼─────────────┘
                      │
                     TEST
                      │
                Agentic Chaos
```

| Project | Question it answers |
| --- | --- |
| [AgenticLens](https://github.com/DeepAgentLabs/agenticlens) | What did the agent do, and what happened? |
| [Agentic Chaos](https://github.com/DeepAgentLabs/agentic-chaos) | How does the agent behave when things go wrong? |
| [Agentic MCP](https://github.com/DeepAgentLabs/mcp-server) | How does the agent interact with tools and external capabilities? |
| [AgenticOps Control Tower](https://github.com/DeepAgentLabs/agenticops-control-tower) | What is deployed, what governance posture exists across agents, and how do operators manage it centrally? |
| **Agentic Sidecar** | Should the agent continue with this decision, and is it still acting according to intent? |

Each project is independently installable; none requires another as a hard
dependency (see [Cross-Project Dependencies](ROADMAP.md#cross-project-dependencies)
in the roadmap).

## Roadmap

Canonical release history, capability status, completion checklists, and future sequencing:
[ROADMAP.md](ROADMAP.md).

**Shared & Exclusive context/intent and guardrails are available in v0.8.** Users may choose
context only, guardrails only, or both, independently Shared across a system/task
or Exclusive to designated agent(s). Each agent receives shared plus assigned
exclusive context; shared guardrails remain mandatory alongside exclusive rules.
v0.8 provides scoped configuration, delivery and composition; v0.9 validates
privacy, authority and lifecycle behavior; v1.0 stabilizes contracts. Use `ScopedSystem.bind()` and `BoundAgent.deliver()` for explicit host context
transport; this does not provide automatic prompt rewriting or process isolation.

See the [deliverables and acceptance criteria](ROADMAP.md#shared--exclusive-context-and-guardrails).

See [scoped usage](website/docs/scoped-supervision.md) and the two-agent example
[examples/v0_8_scoped_agents.py](examples/v0_8_scoped_agents.py).

Original architecture proposal: [concept.md](concept.md).

## License

MIT — see [`LICENSE`](LICENSE).

## Control Tower integration boundary

AgenticOps Control Tower owns deployment registration, heartbeat, fleet
inventory and operator workflows. AgenticLens owns observability and analysis;
Agentic Evals owns scoring and release-gate computation; Agentic Sidecar owns
decision supervision (SUPERVISE); Agentic Chaos owns fault injection and
resilience experiments. AI Operations Specification owns shared semantics and
is currently draft.

Tower's native artifact readers consume existing producer outputs using an
explicit deployment/evidence link. They do not change producer behavior or
convert a failed run, failed gate, blocked action or injected fault into fleet
health. This link is a Tower-local contract, not a normative AIOS schema.
See [Control Tower's evidence contract](https://github.com/DeepAgentLabs/agenticops-control-tower/blob/main/docs/ecosystem-alignment.md).
Tower 0.5 introduced pushed evidence posture; 0.6.0 adds cited investigation
and approved deterministic staging recovery. Pull collection and production runtime adapters
remain planned; native interoperability does not establish stable AIOS conformance.

## Operational safety roadmap

Sidecar implements task-scoped local stop, dispatch prevention, async cancellation
requests and harness-revocation receipts alongside deterministic policy enforcement.
MCP and Tower support access enforcement and operator coordination.

See [planned safety acceptance criteria](ROADMAP.md#operational-safety-acceptance-criteria) for responsibilities and
dependencies. See [live operator scope](website/docs/live-operations.md) for implemented
controls and the remaining gateway-isolation and issuer responsibilities.

## Control Tower 0.6.0 integration

Tower Phase 6 and 6A ship together in 0.6.0 with MCP 0.3.6: evidence-cited
investigation, exact-preview human approval and verified deterministic staging
recovery. Native producer outcomes and package ownership remain unchanged.
See [compatibility, examples and dependency matrix](website/docs/control-tower-0.6.md).
This is documentation alignment; no package release or dependency bump is needed.
