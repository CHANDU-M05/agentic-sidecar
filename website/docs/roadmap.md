# Roadmap

Updated **2026-10-17 · Current version: 0.8.1**.
The [root ROADMAP.md](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/ROADMAP.md)
is the canonical plan with detailed deliverables and acceptance criteria.
Future version targets describe priorities, not committed delivery dates.

## Release history

| Version | Focus |
| --- | --- |
| 0.2.0 | Runtime, policy/risk, Intent Guardian, and LangGraph Govern BLOCK |
| 0.3.0 | Planner/Critic heuristics, Judge interface, and provider examples |
| 0.4.0 | Budget accounting, seven outcome types, escalation/provenance types |
| 0.5.0 | Narration and status/demo/version CLI |
| 0.6.0 | Combined runtime with optional evaluator pipeline and public exports |

See [Features](features.md) for current capabilities and
[Limitations](limitations.md) for their supported scope.

## v0.6.x — Governance & Evaluator Enhancements

**0.6.1 implementation prepared**, with [usage and validation evidence](governance.md).

- [x] Govern suspension for PAUSE/ESCALATE/CHALLENGE/REPLAN and real LangGraph tests.
- [x] Five approval actions, response IDs, missing-handler suspension and local CLI prompt.
- [x] Failure policy across injection, providers, timeouts, malformed results and recording.
- [x] Explicit full-plan boundary and goal/constraints/history/metadata context.
- [x] Explicit MockJudge plus optional live OpenAI/Anthropic SDK backends and contract tests.
- [x] Judge limits, sync/async accounting and validated shared BudgetGuardian usage.
- [x] Four-scenario deterministic intent benchmark with guardian off/on and clean controls.
- [x] Release tag/source/changelog/distribution validation before publication.
- [ ] Authenticated live smoke evidence for both providers; local status is recorded separately.

## v0.7 — Live Status, Audit Lifecycle & Control Room

Implemented; see [live operations and acceptance evidence](live-operations.md).

- [x] Connect CLI status to actual runtime events through documented local IPC/HTTP.
- [x] Distinguish proposed, executed, completed, blocked, and paused actions.
- [x] Create causally linked audit snapshots and approval records with optional persistence.
- [x] Build real pause/resume/stop/approval/intent/replan controls on the shared interface.
- [x] Validate native evidence with Control Tower and provide an end-to-end operator demo.

## v0.8 — Framework Adapters & Optional Integrations

Implemented in 0.8.0; see [compatibility and usage](integrations.md).

- Native AutoGen, CrewAI, OpenAI Agents and Google ADK tool adapters share the
  LangGraph execution boundary with native SDK conformance tests.
- Shared/Exclusive context-only, guardrails-only and combined scopes have
  explicit host delivery, independent mandatory checks and trusted identity.
- Versioned correlation links verified native journals and Lens 0.7.1 decisions;
  Chaos 0.5.3 recovery proposals have native event IDs.
- Real MCP 2.3.0 calls and a separate-process enforcing gateway are exercised.
- Semantica module/extra is reserved; export awaits upstream API validation.

## v0.9 — Evaluation Evidence & Authority Boundaries

- Compare Agent Alone vs. Agent + Sidecar using reproducible supervision scenarios.
- Publish success, unsafe-action, false-intervention, latency, token, and cost results.
- Coordinate standalone scoring/reporting with Agentic Evals.
- Implement task-authority bindings from a concrete use case and test delegation/handoff.
- Add model-backed plan/critic reasoning only where evidence supports it.

## v1.0 — Stable Interoperability Contract

- Publish versioned Intent Envelope and Decision/audit schemas with AI Operations Specification.
- Test cross-instance/agent propagation, schema compatibility, and migration behavior.
- Define public API stability and document supported sibling/framework versions.

**Shared & Exclusive context/intent and guardrails (v0.8 implemented).** Users may choose
context only, guardrails only, or both, independently Shared across a system/task
or Exclusive to designated agent(s). Each agent receives shared plus assigned
exclusive context; shared guardrails remain mandatory alongside exclusive rules.
v0.8 provides scoped configuration, delivery and composition; v0.9 validates
privacy, authority and lifecycle behavior; v1.0 stabilizes contracts. Host context
delivery is explicit; it does not automatically rewrite agent
prompts or provide process isolation.

See the [canonical acceptance criteria](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/ROADMAP.md#shared--exclusive-context-and-guardrails).

## Conditional follow-ups

Local-model risk classification, automatic framework usage extraction, caching,
and sampling require measured need before scheduling. Core runtime remains
independent of sibling packages; integrations and provider SDKs stay optional.

## Planned operational safety acceptance criteria

Sidecar owns emergency braking (stop, block further dispatch and revoke task
access through supporting access boundaries) and independent policy enforcement.
See the [canonical acceptance criteria](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/ROADMAP.md#operational-safety-acceptance-criteria)
for milestone dependencies and validation requirements. The v0.7 local stop,
cancellation, audit and harness-revocation interface is implemented. v0.8 adds
a separate-process enforcing MCP gateway demonstration and Lens native journal
verification. Secure service deployment is a harness responsibility; delegated
authority and end-to-end privacy validation remain v0.9 work.
