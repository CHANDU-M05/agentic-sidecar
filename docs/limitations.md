# Limitations

Known constraints and current boundaries in Agentic Sidecar v0.6.0. Planned improvements appear in [Roadmap](roadmap.md).

---

## Scope

### Policy and Risk rules are static

Policy Advisor and Risk Evaluator use `fnmatch` glob patterns and argument value comparisons. They cannot:

- Understand the semantic meaning of arguments (e.g. "is this a sensitive customer?")
- Learn from past decisions
- Apply contextual reasoning

LLM-based risk scoring is a planned capability. For now, rules must be written explicitly.

### Intent Guardian enforces only `constraints`

The `IntentEnvelope` model carries both `constraints` and `authority` fields, but only `constraints` enforcement is implemented via `ConstraintBinding`. The `authority` dict (e.g. `{"can_delete": False}`) is stored but not evaluated against any tool call. Authority-based blocking requires a real use-case design before being built.

### Budget tracking is manual

`BudgetGuardian.record_invocation()` must be called manually after each LLM or tool invocation. There is no automatic cost extraction from LangGraph callbacks, OpenAI usage metadata, or Anthropic response headers. Automatic cost tracking is planned.

---

## Adapter Coverage

### Only LangGraph is production-tested

The `adapters/` module contains wrappers for LangGraph, CrewAI, AutoGen, OpenAI Agents, and Google ADK, but only the LangGraph adapter has a test suite. The others are present as starting points but are not verified against their respective frameworks.

### No multi-agent boundary enforcement

The current Sidecar attaches to a single agent's tool list. Enforcing decisions across a multi-agent system (supervisor + worker agents) requires an adapter-per-agent setup, which is not yet documented or tested.

---

## CLI

### `status` command does not connect to a live agent

`agentic-sidecar status` creates a demo `StatusNarrator` instance. It does not yet connect to a running `Sidecar` instance via IPC, Unix socket, or HTTP. Real-time status from a production agent requires v0.7's Control Room integration.

---

## Evaluators

### Critic and Plan Evaluators are rule-based only

`CriticEvaluator` and `PlanEvaluator` use heuristic rule matching. The LLM-backed versions that call an actual model to reason about the plan are planned for a future version.

### Custom hook replaces all modules

When `@sidecar.before_tool_call` is used, it replaces the entire built-in pipeline — Policy, Risk, Intent Guardian, Budget, etc. There is no mechanism to run both a custom hook and built-in modules simultaneously.

---

## Audit and Observability

### No persistence

`sidecar.decisions` is in-memory only. There is no built-in persistence to disk, database, or a tracing backend. Decision records are lost when the process exits.

### No AgenticLens integration yet

The `agentic_sidecar.integrations.agenticlens` module is a placeholder. Forwarding Sidecar decisions to AgenticLens traces is not yet implemented.

---

## Version

This package is classified as **Pre-Alpha** (`Development Status :: 2 - Pre-Alpha` in PyPI classifiers). The API surface is stable within a minor version but may change between minor versions until v1.0.
