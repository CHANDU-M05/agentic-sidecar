# Roadmap

Updated **2026-10-10 · Current version: 0.6.1 (release preparation)**.
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

- Connect CLI status to actual runtime events through documented local IPC/HTTP.
- Distinguish proposed, executed, completed, blocked, and paused actions.
- Create causally linked audit snapshots and approval records with optional persistence.
- Build real pause/resume/stop/approval/intent/replan controls on the shared interface.
- Validate native evidence with Control Tower and provide an end-to-end operator demo.

## v0.8 — Framework Adapters & Optional Integrations

- Prove a second adapter, then ship CrewAI, AutoGen, OpenAI Agents, and Google ADK incrementally.
- Test outcome, mode, failure, and approval conformance across supported frameworks.
- Add optional AgenticLens export and a shared, versioned correlation-ID contract.
- Add Semantica export after contract validation; define optional Chaos coordination.
- Validate real MCP tool calls and cross-agent setups with supported-version evidence.

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

## Conditional follow-ups

Local-model risk classification, automatic framework usage extraction, caching,
and sampling require measured need before scheduling. Core runtime remains
independent of sibling packages; integrations and provider SDKs stay optional.
