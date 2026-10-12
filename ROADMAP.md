# agentic-sidecar — Roadmap & Architecture

> **Updated 2026-10-11 · Current checkout: 0.7.0 (prepared for review; unpublished).**
> This is the canonical capability roadmap. Each stage builds on the existing
> runtime with explicit deliverables and acceptance criteria. Future version
> targets describe development priorities, not committed delivery dates.

## Release History

| Version | Focus |
| --- | --- |
| v0.2.0 | Intent Envelope, constraint validation, expiry warnings, intent/history injection, and LangGraph Govern `BLOCK` enforcement |
| v0.3.0 | Planner/Critic heuristics, model-agnostic Judge interface, and provider examples |
| v0.4.0 | Budget accounting, seven decision outcome types, escalation request/response types, and provenance serialization |
| v0.5.0 | Human-readable StatusNarrator and Typer/Rich CLI (`status`, `demo`, `version`) |
| v0.6.0 | Combined runtime with optional evaluator stages and public evaluator exports |

**0.6.1 governance implementation:** governance resolution, full-plan context, optional
live providers, timeout/usage accounting and reproducible validation. See
[usage and acceptance evidence](docs/governance.md). Authenticated provider smoke remains
pending credentials by request. **0.7.0 implementation:** runtime events, audit,
local operator interface and Control Room; see [live operations](docs/live-operations.md).

## Current Capabilities and Next Steps

| Capability | Available today | Next step |
| --- | --- | --- |
| Runtime, Policy Advisor, Risk Evaluator | Deterministic rules and explicit failure configuration | Extend failure-path coverage |
| Intent Guardian | Numeric/enum/allow-list constraint bindings and expiry warnings | Task-authority bindings and delegation |
| LangGraph adapter | Sync/async wrapping, governed outcome suspension and local approvals | Further adapter conformance |
| Planner | Explicit full-plan gate, goal/constraints/history/metadata and bound checks | Broader evidence-driven reasoning |
| Critic | Selected risk/assumption/history checks and supplied evidence | Broader evidence-driven reasoning |
| Judge | Explicit MockJudge and optional live OpenAI/Anthropic, limits and shared usage | Recorded live smoke evidence |
| Budget Guardian | Validated manual/Judge usage, governed PAUSE and approvals | Measured usage extraction needs |
| Human escalation | ID-correlated local/HTTP handlers, CLI prompt and five actions | Additional adapter conformance |
| Provenance | Immutable runtime events, durable JSONL and causal execution/approval IDs | Formal schema stability |
| Narration and CLI | Runtime-connected HTTP status, control/approval and narration | Broader adapter coverage |
| Additional framework adapters | LangGraph provides the initial integration surface | CrewAI, AutoGen, OpenAI Agents, and Google ADK |
| Ecosystem integrations | Optional package boundaries | Decision export and shared correlation contracts |
| Control Room | Authenticated task-scoped runtime controls | Broader adapter coverage |
| Evaluation and interoperability | Outcome tests and four deterministic intent fixtures | Broader comparative evidence and schemas |

The 0.6.1 validation includes outcome/approval/failure tests, real LangGraph
execution boundaries, deterministic provider contracts, eight offline examples,
a four-scenario Intent Guardian benchmark, strict docs and package metadata
checks. See [acceptance evidence](docs/governance.md) for scope and live-smoke status.

## Architecture

**The Main Agent acts. The Sidecar observes, thinks, advises, and governs.**
The package owns pre-action decision supervision, not agent orchestration,
retrospective observability, fault injection, or fleet deployment health.

```text
src/agentic_sidecar/
  core/          runtime, decision context/outcomes, provenance types
  gate/          deterministic policy/risk, budget, escalation primitives
  intent/        IntentEnvelope and constraint alignment
  evaluators/    plan/critic heuristics, explicit mock and optional live providers
  status/        runtime-connected and standalone human-readable narration
  operations/    task runtime, immutable journal, authenticated HTTP and Control Room
  cli/           connected status/control/approval and local demo/version commands
  adapters/      LangGraph callable wrapper; four additional placeholders
  integrations/  optional AgenticLens and Agentic Chaos placeholders
```

One repository and one PyPI package. Framework adapters own `attach()`;
`core/` must not import adapters. Policy/risk remain independent of evaluators
and intent. Provider SDKs must remain optional and outside the core abstraction.
The CLI entry point, Typer/Rich dependencies, landing page, MkDocs site, docs
workflow, and committed `uv.lock` already exist. Ruff checks `src tests scripts examples`.

## Design Constraints

1. **Prove the adapter contract before expanding frameworks.** LangGraph is
   the current implementation. A second adapter must demonstrate the same
   enforcement behavior before framework independence is claimed. LangChain
   shares the initial interception surface; additional Microsoft/custom/MCP
   surfaces require a concrete use case before scheduling.
2. **Rules before models.** Policy, Risk, Intent constraints, and Budget work
   without LLM calls. Judge use is opt-in. Real provider dependencies and
   costs must be explicit; example/mock and live provider modes must be clearly labelled.
3. **Failure policy is required.** `on_sidecar_failure` has no silent default.
   `fail_closed` is recommended for governed decision boundaries. Injection,
   evaluation, result validation, timeout, and provider failures must resolve
   under that policy. Observe mode remains advisory.
4. **Measure before adding inference.** Keep risk rules as the default.
   Local-model classification, sampling, caching, and asynchronous advisory
   evaluation are deferred until measured bottlenecks justify them.
5. **Preserve distinct questions.** Policy asks permission; Risk asks danger;
   Intent asks whether an action fits the request. Authority binding must
   connect a task's granted authority to actions, rather than duplicate a
   global policy allow/deny list.

## Cross-Project Dependencies

The package stays standalone: no required DeepAgentLabs sibling dependency.
Use `Depends on` for an actual prerequisite, `Coordinate with` for shared
contracts, and `Validate in` for integration checks.

| Project | Relationship and ownership | Target |
| --- | --- | --- |
| `ai-operations-spec` | Coordinate envelope/decision terminology and mappings now; publish versioned schemas only once tested and stable | Informal alignment now; formal contract v1.0 |
| `agenticlens` | Coordinate optional decision export and common run/trace/decision IDs; Lens owns instrumentation and retrospective analysis | v0.8 |
| `agentic-evals` | Validate standalone scoring and release-gate reports; Sidecar owns supervision experiments, not another generic scoring engine | v0.9 |
| `agentic-chaos` | Validate gate/provider timeout, malformed response, and recovery scenarios; optional same-run integration needs its own interface | Failure tests v0.6.x; optional integration v0.8 |
| `semantica` (third party) | Optional governance/provenance export for all outcomes; coordinate a versioned correlation convention with AgenticLens | v0.8, contract before implementation |
| `deep-agentic-core-mcp` | Validate a real gated MCP call without moving tool connectivity into Sidecar | v0.8 |
| `agenticops-control-tower` | Coordinate native decision/status evidence and escalation state; Tower owns fleet/operator aggregation and deployment health | v0.7–v0.8 |

No fixed sibling minimum version is promised before compatibility is tested.
Semantica export must include decision boundary, trigger, rationale, and causal
links, with a common ID convention tested in both Sidecar and AgenticLens.

## Definition of Done

A deliverable is complete when its intended behavior is usable, with:

- meaningful outcome tests, including governed execution and applicable
  `fail_open` / `fail_closed`, timeout, malformed-result, and approval paths;
- runnable examples and accurate README/API/limitations documentation;
- roadmap status updated in both this file and its docs summary;
- documented artifact mappings and sibling compatibility evidence where relevant;
- release tag, `pyproject.toml`, `__version__`, and changelog agreeing when released;
- required local/CI checks passing before publishing, including release-note
  validation before publication.

Acceptance covers the end-to-end behavior of each deliverable. Feature stages
may span multiple releases; documentation updates use the current package version.

## Build Order

### v0.6.x — Governance & Evaluator Enhancements

**0.6.1 status:** implementation and local validation prepared. The live-provider
smoke acceptance item below remains open until authenticated runs are recorded.

Implemented foundations:

- [x] Deterministic Policy/Risk gate with explicit failure configuration.
- [x] Constraint-based Intent Guardian and Govern `BLOCK` interception.
- [x] Seven decision status values and provenance/escalation data types.
- [x] Manual budget accounting, narrator, CLI, evaluator interfaces and examples.

Enhancement checklist:

- [x] Make `PAUSE`, `ESCALATE`, `CHALLENGE`, and `REPLAN` return control or
      suspend execution in Govern mode; only `ALLOW`/`WARN` may call through
      without further resolution. Test the real LangGraph boundary in CI.
- [x] Invoke registered escalation handlers and validate response/decision IDs.
      Implement approve-once, reject, modify intent, replan, and stop semantics,
      including a usable CLI approval prompt and an explicit missing-handler path.
- [x] Apply failure policy across context injection, provider errors/timeouts,
      malformed hook/provider results, and decision recording, with explicit
      validation of supported verdicts.
- [x] Provide an explicit full-plan evaluation boundary; pass goal, constraints,
      history, and plan consistently to evaluators; expand plan/critic checks
      and document their supported scope.
- [x] Provide explicit MockJudge and live optional OpenAI/Anthropic backends,
      with deterministic sync/async SDK contract tests and credential-free CI.
- [ ] Record authenticated live smoke evidence for both provider backends.
      Local credential-free status is recorded separately in acceptance evidence.
- [x] Enforce judge timeout/cost settings, sync/async parity, and judge usage
      accounting through BudgetGuardian; validate negative/non-finite usage.
- [x] Add a deterministic Intent Guardian benchmark in `tests/validation/`:
      3–5 refund/environment/export/delegation fixtures, guardian off/on, clean
      controls, measured catch and false-positive rates published with scope limits.
- [x] Automate release tag/package/changelog validation before publishing.
- [x] Publish usage guidance and acceptance evidence for each enhancement.

**Acceptance criteria:** governed tools cannot execute while a decision requires
resolution; all approval/failure paths are exercised; a supplied plan is
evaluated with its intent context; provider modes are explicit; benchmark results
are reproducible. Safe conservative behavior takes precedence over latency.

### v0.7 — Live Status, Audit Lifecycle & Control Room

**Depends on:** the v0.6.x enforcement and escalation contract.

- [x] Emit runtime decision/execution/status events and connect `status --follow`
      to a real Sidecar through a documented local IPC or HTTP interface.
- [x] Distinguish proposed, blocked, paused, executed, and completed actions in
      narration; report actual intent/risk/budget state and task identity.
- [x] Create immutable decision-time audit snapshots with decision IDs, timestamps,
      trigger/rationale, parent plan/decision links, and approval/rejection records.
- [x] Add an optional durable audit sink and verify export/restore behavior;
      define its artifact mapping against AIOS conventions.
- [x] Build a Control Room consuming the same event/approval interface: objective,
      plan, calls, alignment, risk, budget, pause/resume/stop, approve/reject,
      modify intent, and ask-to-replan. Use actual runtime controls.
- [x] Document operator access and task isolation; validate native evidence with
      Control Tower without treating blocked actions as deployment failures.
- [x] Add an end-to-end example and demo recording showing a real paused action
      being approved or rejected with a causally linked audit record.

**0.7 scope:** task-scoped local HTTP controls, owned async cancellation and
harness-supplied access revocation callbacks. No built-in credential issuer or
process isolation; receipts explicitly report unconfigured/failed revocation.
Native Tower readback is tested; Lens integrity integration remains v0.8.

### v0.8 — Framework Adapters & Optional Integrations

**Depends on:** a stable, tested gate and audit/event contract.

- [ ] Implement a second real adapter and revise the interception abstraction
      only where integration evidence requires it.
- [ ] Implement CrewAI, AutoGen, OpenAI Agents SDK, and Google ADK adapters
      incrementally; maintain explicit dependency/version compatibility tables.
- [ ] Run conformance tests for all seven statuses, both modes, both failure
      policies, and supported approval behavior across every shipped adapter.
- [ ] Implement optional AgenticLens decision export with tested ID correlation.
- [ ] Define a versioned correlation contract tested by Sidecar and AgenticLens;
      reserve Semantica's module/extra, then implement optional provenance export
      only once that contract and the upstream API are validated.
- [ ] Define and test optional Agentic Chaos coordination for supervised recovery
      decisions and Sidecar failure injection.
- [ ] Validate a real MCP tool call and cross-agent adapter setup; preserve core
      independence from framework SDKs and sibling installations.
- [ ] Add runnable integration examples and record sibling compatibility checks.

### v0.9 — Evaluation Evidence & Authority Boundaries

**Depends on:** working evaluators, enforcement, and the v0.6.x narrow fixtures.
Coordinate generic scoring with Agentic Evals while keeping supervision
scenarios and intervention measurements within Sidecar.

- [ ] Extend the fixtures to compare Agent Alone vs. Agent + Sidecar, including
      unnecessary plan steps, unsupported assumptions, and degraded providers.
- [ ] Publish reproducible task-success, unsafe-action, false-intervention,
      latency, token, and cost results with sample sizes and configuration.
- [ ] Measure reliability improvement per added inference cost; separate model
      evaluation results from deterministic constraint performance.
- [ ] Define authority bindings from a concrete use case, enforce granted/denied
      task authority, and test expiry/handoff behavior without conflating policy.
- [ ] Add cross-agent delegation examples with explicit authority and task scope;
      verify envelope narrowing and correlation across boundaries.
- [ ] Add optional model-backed plan/critic reasoning only where benchmark evidence
      supports it; keep heuristic and deterministic defaults explicit.

Local-model risk classification, automatic framework usage extraction,
caching, and sampling remain conditional follow-ups, not mandatory release
features. Schedule them only when performance/cost measurements justify them.

### v1.0 — Stable Interoperability Contract

**Depends on:** validated runtime behavior and coordinated AIOS schema work.

- [ ] Publish versioned Intent Envelope and Decision/audit schemas in
      `ai-operations-spec`, with documented mappings and compatibility tests.
- [ ] Demonstrate cross-instance and cross-agent intent propagation, preserving
      authority, constraints, expiry, and causal identity.
- [ ] Define public API stability, schema evolution, and migration guarantees.
- [ ] Validate sibling/framework compatibility and publish supported versions.
- [ ] Complete release readiness: docs, examples, benchmark evidence, failure
      semantics, synchronized metadata, and README/roadmap/schema release notes.

## Sequencing and Maintenance

Work in the order **governance enhancements → live operations → adapters/integrations
→ broader evidence and authority → stable schemas**. Reassign a target version
when scope changes; mark each capability complete when its acceptance criteria pass.
There is no calendar commitment or week estimate in this plan.

Update this canonical file when scope or status changes, then update
[the docs summary](docs/roadmap.md), README, and relevant ecosystem profile
statements in the same change. [concept.md](concept.md) contains the original
architecture proposal.

## Operational safety acceptance criteria (planned)

Added 2026-10-11. Extend existing milestones; local STOP_AGENT and Govern
interception already exist, but remote stopping and isolated enforcement do not.
Sidecar owns both the emergency brake (stop, prevent further calls, revoke task
access) and independent policy enforcement. MCP/credential issuers implement
access-boundary revocation; Tower supplies optional operator coordination.

- [x] v0.7: authenticated, task-scoped operator stop independent of LLM approval;
      latch stop before additional dispatch and acknowledge its effective time.
      Test queued calls, concurrent proposals, retries and explicit restart.
- [x] v0.7: distinguish already-running calls and completed side effects; cancel
      only where supported by the harness/provider. Coordinate MCP revocation and
      Tower results without taking ownership of credentials. Require task-access
      revocation acknowledgements, report partial failure, and verify stopped
      agents cannot regain access through retries, sessions or delegated tasks.
- [ ] v0.8: test deterministic permissions at every supported adapter boundary,
      including direct-call bypass attempts. Document unwrapped tools, Observe,
      custom hooks and fail_open as limits; use fail_closed for containment tests.
- [ ] v0.8: demonstrate protected tools/credentials accessible only through an
      enforcing gateway; in-process wrappers alone are not process isolation.
- [ ] v0.7–v0.8: correlate immutable decision records, policy versions, task IDs,
      actors, approvals and stop acknowledgements with actual dispatch/completion.
      Integrate Lens integrity verification; verdict history alone is not execution.
- [ ] v0.9: test revoked/expired delegated authority and, with Chaos/Evals, prove
      zero forbidden dispatches after acknowledged stop/revocation. Cover injected
      instructions, policy bypass and failures of the gate itself.

Shared authority/event semantics belong in AI Operations Specification.
