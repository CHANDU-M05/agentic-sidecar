# Changelog

All notable changes to this project are documented here.

## [Unreleased]

## [0.7.0] - 2026-10-11

### Added

- TaskRuntime and immutable runtime events for proposals, decisions, actual
  dispatch, completion/failure, actor-attributed approvals and stop receipts.
- Optional fsynced JSONL journal with hash/sequence/task validation on restore,
  decision-time context, findings, policy fingerprints and causal plan links.
- Authenticated task-scoped loopback HTTP status/events/control/approval interface
  and embedded Control Room for objective, plan, intent, risk, budget and calls.
- Connected `status --endpoint ... --follow`, remote `control` and `approve` CLI
  commands; measured execution narration separates proposals from completions.
- Independent stop latch, stale/consumed verdict rejection, pause/resume/replan,
  explicit restart, owned async-tool cancellation and harness revocation receipts.
- Runnable HTTP approval/rejection demo and recorded lifecycle evidence; optional
  Control Tower readback tests preserve supervision outcomes separately from health.

### Changed

- LangGraph wrapped sync/async tools report actual execution lifecycle; operator
  stop prevents dispatch in both modes and cannot be bypassed by fail_open.
- Restored runtimes start stopped; incomplete execution/revocation prevents restart.

### Validation limitation

- Authenticated OpenAI/Anthropic live smoke from v0.6.1 remains pending credentials
  by user request. Deterministic SDK contract validation remains available.

## [0.6.1] - 2026-10-10

### Added

- Govern resolution for all seven outcomes with sync/async callable interception;
  unresolved PAUSE/ESCALATE/CHALLENGE/REPLAN return control before tool execution.
- ID-correlated approve-once, reject, modify-intent, replan and stop handling;
  local CLIApprovalHandler and safe `approval-demo` prompt.
- Full-plan Sidecar boundary with goal, constraints, history, plan and metadata;
  deterministic step checks and expanded scoped Planner/Critic heuristics.
- Explicit offline MockJudge and optional live OpenAI/Anthropic SDK providers,
  with lazy imports, explicit models/rates and deterministic SDK contracts.
- Judge timeout and post-response cost ceilings, sync/async usage/latency parity,
  automatic task budget accounting and validated nonnegative finite usage.
- Four deterministic intent scenarios with guardian-off/on and clean controls;
  measured fixture catch rate 4/4 and false positives 0/4 with guardian enabled.
- Release tag/source/changelog/wheel/sdist validation before publication;
  offline example/doc snippet checks and strict docs builds on pull requests.

### Changed

- Injection, malformed hook/evaluator/provider output and recording failures
  follow the configured Sidecar failure policy. Judge errors propagate to it.
- In-memory history stores deep context copies; decisions have generated IDs,
  and approval resolutions link back to the originating decision.
- Bundled OpenAIJudge/AnthropicJudge now make live calls; offline usage moves
  to MockJudge. Live cost ceilings require configured token rates.
- Pages deployment is restricted to main; provider credentials remain optional
  in CI. Authenticated provider smoke evidence is pending credentialed validation.

### Fixed

- `evaluate_plan()` no longer re-checks Policy/Risk/Intent Guardian against the
  synthetic `"__plan__"` marker after every real step already passed; a
  default-deny policy or high default risk could otherwise false-BLOCK an
  already-valid plan.
- A plan step's `WARN`-severity `ConstraintBinding` finding is now aggregated
  into the plan's final verdict instead of being silently dropped.
- Custom governance-loop docs now call `sidecar.enforce()` so PAUSE/ESCALATE/
  CHALLENGE/REPLAN are handled the same as the adapter, not just BLOCK.
- Judge's internal question no longer interpolates caller-controlled
  `goal`/`tool_name` into the privileged provider prompt; that data still
  reaches the model only through the separately serialized untrusted context.
- `JudgeProvider.cost_tracking_available()` now defaults to `False`; a custom
  provider must opt in explicitly before cost limits/budget accounting trust it.
- `PlanEvaluator._analyze_plan()` no longer takes an unused `intent` parameter.
- `tests/test_critic.py` passes a `str` for `CriticChallenge.evidence`, matching
  its declared type instead of a `list`.

### Documentation

- Clarified that a recorder failure discards the already-computed verdict, so
  `fail_open` resolves it to ALLOW and `fail_closed` resolves it to BLOCK.
- Documented that `BudgetGuardian` is not internally locked and is meant for
  one task at a time, not shared across concurrently-dispatched tool calls.
- Updated the canonical and docs roadmaps with release history through 0.6.0,
  current capabilities, and acceptance criteria for upcoming stages.
- Prioritized 0.6.x governance/evaluator enhancements, followed by live operations,
  adapters/integrations, evaluation/authority, and stable interoperability schemas.
- Aligned README, API/configuration/CLI guidance, example catalog, and ecosystem roadmap summaries.
- Updated runnable demos for explicit plan review, mock-provider contracts,
  caller-managed approval/audit records, and local narration; refreshed notebook scope.

## [0.6.0] - 2026-09-14

### Added

- Complete v0.3.0 evaluators integration: Planner, Critic, and Judge evaluators now fully integrated and production-ready
- Evaluators module exports: All evaluator classes and LLM providers available from main module for easy importing

### Changed

- Version bump: 0.5.0 → 0.6.0 to reflect inclusion of v0.3.0 evaluators alongside v0.4.0 and v0.5.0 features
- Sidecar Decision Gate now includes three new optional evaluator stages: Planner → Critic → Judge

### Documentation

- Updated README.md with v0.3.0 evaluator features and examples
- Updated CHANGELOG.md with complete v0.3.0 release notes
- Added comprehensive examples for evaluator usage

### Testing

- 39 evaluator tests with 100% pass rate
- 90%+ code coverage for evaluator modules
- All CI checks passing: ruff linting, formatting, mypy type checking

## [0.3.0] - 2026-09-14

### Added

- Evaluators: LLM-based decision evaluation framework (`agentic_sidecar.evaluators`)
  - `EvaluatorBase` abstract interface for all evaluators (Planner, Critic, Judge)
  - `EvaluatorResult` dataclass with status, rationale, confidence (0.0-1.0),
    metadata, timestamp, and latency_ms for comprehensive evaluation tracking
  - `JudgeProvider` abstract interface for model-agnostic LLM providers
- Planner evaluator (`agentic_sidecar.evaluators.planner.PlanEvaluator`)
  - Plan-level intent alignment evaluation
  - Detects unnecessary steps (cancel, refund, delete not in original request)
  - Identifies contradictions (create + delete, enable + disable patterns)
  - Checks plan against `IntentEnvelope` constraints
  - Returns ALLOW or REPLAN decisions with detailed rationale
  - 100% rule-based (no LLM calls)
- Critic evaluator (`agentic_sidecar.evaluators.critic.CriticEvaluator`)
  - Challenges decisions for unsupported assumptions and risks
  - Detects risky operations (delete, refund, cancel without supporting context)
  - Flags large financial amounts (> $1000)
  - Identifies contradictions with prior actions
  - Identifies unsupported assumptions (refund without policy check)
  - Validates reasoning completeness (backup before delete)
  - `CriticChallenge` dataclass with category, severity, description, evidence, suggestion
  - Challenge categories: risky, assumption, contradiction, reasoning
  - Returns CHALLENGE when issues found
- Judge evaluator (`agentic_sidecar.evaluators.judge.JudgeEvaluator`)
  - LLM-based decision evaluation with pluggable provider interface
  - Model-agnostic design: separates Main Agent (Model A) from Judge (Model B)
  - Reduces correlated reasoning failures
  - Async/sync evaluation paths for production use
  - Cost tracking per evaluation, integrated with BudgetGuardian
  - Timeout handling with graceful fallback (returns WARN on LLM failure)
- Judge Provider implementations
  - `OpenAIJudge` (`agentic_sidecar.evaluators.providers.openai`)
    - Supports GPT-4, GPT-3.5-turbo, and other OpenAI models
    - Cost tracking: $0.03/1K input, $0.06/1K output tokens (GPT-4 pricing)
  - `AnthropicJudge` (`agentic_sidecar.evaluators.providers.anthropic`)
    - Supports Claude 3 Opus, Sonnet, and other Anthropic models
    - Cost tracking: $0.015/1K input, $0.075/1K output tokens
  - Provider swapping without changing Sidecar code
  - Mock implementations for v0.3.0 (ready for real API integration)
- Sidecar integration (`agentic_sidecar.core.sidecar`)
  - Added planner, critic, judge as optional parameters to `Sidecar.__init__`
  - Updated `_SUPPORTED_ROLES` to include "planner", "critic", "judge"
  - Evaluation routing in `_default_evaluate()`:
    * Planner: Checks plan alignment, returns REPLAN/BLOCK if issues
    * Critic: Challenges decisions, returns CHALLENGE if flaws found
    * Judge: LLM-based evaluation, returns BLOCK/WARN/PAUSE based on model
  - Each evaluator independently enabled/disabled
  - Evaluation context includes tool_name, arguments, history, intent
  - Early exit: Any evaluator can return BLOCK/CHALLENGE/REPLAN to stop chain
- Evaluators exported from main module (`agentic_sidecar`):
  `EvaluatorBase`, `EvaluatorResult`, `JudgeProvider`, `PlanEvaluator`,
  `PlanStep`, `CriticEvaluator`, `CriticChallenge`, `JudgeEvaluator`,
  `OpenAIJudge`, `AnthropicJudge` for easy importing
- Comprehensive test suite (90%+ coverage)
  - `tests/test_planner.py`: PlanEvaluator and PlanStep tests (10 tests)
  - `tests/test_critic.py`: CriticEvaluator and CriticChallenge tests (12 tests)
  - `tests/test_judge.py`: JudgeEvaluator and provider tests (15 tests)
  - `tests/test_sidecar_evaluators.py`: Sidecar integration tests (8 tests)
- Examples: Comprehensive working demos
  - `examples/v0_3_planner_critic_judge.py`: Five demos (Planner, Critic, Judge, all together, cost tracking)
  - `examples/v0_3_judge_providers.py`: Six demos (OpenAI, Anthropic, provider swapping, cost comparison, validation, different models)

### Changed

- `Sidecar._default_evaluate()` now invokes Planner → Critic → Judge in sequence
  after Policy, Risk, Intent, and Budget evaluations
- `_SUPPORTED_ROLES` now includes "planner", "critic", "judge"
- `_KNOWN_FUTURE_ROLES` cleared (all major v0.3 roles now implemented)

### Backward Compatibility

- All new features are optional and disabled by default
- Existing v0.4.0 agents work without changes
- New code path only activated when evaluators are explicitly enabled
- Zero breaking changes to existing Decision Gate outcomes

## [0.5.0] - 2026-09-14

### Added

- Status Narration (`agentic_sidecar.status.narrate`): `StatusNarrator` class
  tracks agent execution and generates human-readable narration. Records
  objectives, tool calls, decisions (ALLOW/WARN/BLOCK/PAUSE), risk levels,
  and intent compliance status. `ToolCallNarrative` dataclass captures each
  tool invocation with emoji-based narration (e.g., "🔍 Searching for
  information"). `StatusNarrative` dataclass provides complete status snapshot
  with metrics (tool calls made, decisions blocked/paused, max risk, budget
  remaining, token remaining). Heuristic narration patterns for 12+ common
  tool names; fallback to generic "⚙️ Executing X" for unknown tools.
- CLI with status monitoring (`agentic_sidecar.cli.main`): Typer-based CLI
  with Rich terminal formatting. `status` command displays live agent
  execution with `--follow` (streaming updates), `--json` (JSON output), and
  `--interval` (refresh rate in seconds). `demo` command shows interactive
  StatusNarrator usage with progress bar. `version` command displays package
  version. Entry point: `agentic-sidecar` script installed via setup.py.
- Dependencies: `typer>=0.9,<1` (CLI framework), `rich>=13.0,<14` (terminal
  formatting with color, tables, progress bars).
- Comprehensive CLI tests (`tests/test_cli_main.py`): 13 tests covering
  version command, status display (once/json/streaming), demo, and
  StatusNarrator integration with decision tracking. All tests passing with
  91% CLI module coverage.
- Exports: `StatusNarrator`, `ToolCallNarrative`, `StatusNarrative` added to
  main `agentic_sidecar` module for easy access.

### Changed

- `pyproject.toml`: Added typer and rich to dependencies and
  `[project.scripts]` entry point for `agentic-sidecar` CLI command.

## [0.4.0] - 2026-09-14

### Added

- Budget Guardian (`agentic_sidecar.gate.budget`): `BudgetGuardian`
  (tracks cumulative cost and token usage per task), `BudgetResult`
  (evaluation outcome with exceeded flag and remaining budget). Enforces
  per-task cost/token ceilings through the same Decision Gate as Policy and
  Risk, returning a PAUSE decision to escalate to human for approval before
  continuing over budget. Zero LLM calls, per Design Constraint 2.
- Human Escalation flow (`agentic_sidecar.gate.escalation`): `EscalationRequest`
  (pause reason, context, available actions), `ApprovalResponse` (human's
  decision), `ApprovalAction` enum (APPROVE_ONCE, REJECT, MODIFY_INTENT,
  ASK_AGENT_TO_REPLAN, STOP_AGENT), and `EscalationHandler` interface for
  custom approval workflows. v0.4 implements data structures; CLI (v0.5) and
  Control Room dashboard (v0.7) integration deferred.
- Decision Provenance (`agentic_sidecar.core.provenance`): `DecisionTrigger`
  (boundary type, tool name, arguments), `DecisionRationale` (policy/risk/intent/budget
  findings), `CausalLink` (parent decision correlation), and `AuditRecord`
  (complete decision audit trail with timestamp, trigger, rationale, execution
  context). Serializable to JSON for audit and compliance logging.
- Extended `Decision.status` from ["ALLOW", "WARN", "BLOCK"] to full seven-outcome
  set: added CHALLENGE, REPLAN, PAUSE, ESCALATE. Added `decision_point`,
  `trigger_details`, `escalation_required`, and `causal_link` fields to
  `Decision` dataclass for richer audit context.
- `Sidecar` now accepts `budget` parameter and `escalation_handler` in `__init__`.
  `"budget"` is now a supported role (previously in `_KNOWN_FUTURE_ROLES`).
  New hook: `@sidecar.on_escalation_required()` for registering custom
  escalation handlers.
- Budget Guardian integration in `_default_evaluate()`: when budget is exceeded,
  returns PAUSE decision with `escalation_required=True` for human approval
  workflow.
- Interactive web demos: `demo_web_server.py` (stdlib-based, no dependencies)
  and `demo_server.py` (Flask alternative) showcase Budget Guardian tracking,
  Policy blocking, and Intent Guardian validation with live dashboards and JSON
  API endpoints.
- Example: `examples/v0_4_budget_and_escalation.py` demonstrating Budget
  Guardian, Escalation, and Provenance workflows end-to-end.
- Comprehensive test suite: `test_budget.py` (12 tests, 100% coverage of
  BudgetGuardian), `test_escalation.py` (6 tests, 100% coverage of Escalation
  primitives), `test_provenance.py` (8 tests, 100% coverage of Provenance),
  plus new Decision tests for v0.4 statuses and provenance fields.
  `test_v0_4_locally.py` provides 6 end-to-end scenarios (151 total tests, 97%
  coverage).

### Changed

- `Sidecar._default_evaluate()` extended to evaluate Budget Guardian after
  Policy, Risk, and Intent checks, returning PAUSE (not BLOCK) when limits
  exceeded to enable human-in-the-loop escalation workflows.

## [0.2.0] - 2026-08-15

### Added

- Intent Guardian (`agentic_sidecar.intent`): `IntentEnvelope` (goal,
  requester, constraints, authority, expiry — concept.md §6), `Requester`,
  `ConstraintBinding` (binds one envelope constraint to a specific tool
  argument and comparison op), `IntentGuardian` (mirrors
  `PolicyAdvisor`/`RiskEvaluator`'s construction shape), and
  `evaluate_alignment()`. Scope is deliberately narrow: constraint
  validation only (numeric/enum/allow-list, e.g. `maximum_refund: 500` vs.
  a proposed `850`) and envelope-expiry detection. `authority` is carried
  on the envelope (matching concept.md §6's shape, for future
  `ai-operations-spec` alignment) but has no binding/enforcement mechanism
  yet — deferred for the same reason Design Constraint 4 defers a
  model-based risk classifier: build it once a real scenario motivates the
  shape, not speculatively.
- `WARN` added to `Decision.status` (previously `ALLOW`/`BLOCK` only) —
  Intent Guardian's outcome for a finding worth surfacing (a stale/expired
  envelope) but not severe enough to block.
- Govern mode (`Sidecar(mode="govern")`): a `BLOCK` decision is now
  actually enforced. `agentic_sidecar.core.exceptions.SidecarBlockedError`
  is raised by an adapter (not by `Sidecar.evaluate()` itself, which only
  ever computes a `Decision` — see its docstring) when Govern mode's
  `BLOCK` should stop the call. `agentic_sidecar.adapters.langgraph.attach`
  now raises it instead of calling the real tool when
  `sidecar.mode == "govern"` and the decision is `BLOCK`; `WARN` and
  `ALLOW` still call through in both modes.
- `Sidecar.set_intent(guardian)` — swaps the active `IntentGuardian`
  between tasks (an `IntentEnvelope` is meant to be per-task, concept.md
  §6, not fixed for a Sidecar's whole lifetime). Raises if `intent=...` is
  given (at construction or via `set_intent`) without `"intent_guardian"`
  in `roles` — the same "no silent gap" principle `on_sidecar_failure`
  already applies, extended to this footgun.
- `"intent_guardian"` is now a supported `Sidecar` role (previously raised
  `NotImplementedError` naming v0.2).
- `core/context.py`: `IntentSnapshot` (goal + constraints only — the
  lightweight view attached to `DecisionContext.intent`, not the full
  `IntentEnvelope`, which `core/` does not depend on) and `HistoryEntry`.
  `Sidecar.evaluate()` now injects both into every `DecisionContext` before
  dispatching to an evaluator (concept.md §7, Intent Injection), built from
  `self.decisions` and the active `IntentGuardian` automatically.
- `core/operators.py`: shared `ArgOp` + `compare()`, extracted so
  `gate/risk.py`'s argument-pattern rules and `intent/alignment.py`'s
  constraint bindings don't duplicate identical comparator logic.
  `gate/risk.py` refactored to use it; its own rule-matching behavior is
  unchanged.
- `examples/langgraph_intent_guardian_govern_mode.py` — the refund-limit
  scenario from concept.md §9 end to end against a real
  `langgraph.prebuilt.create_react_agent` agent: an $850 refund request
  raises `SidecarBlockedError` before the real tool runs; a $120 request
  goes through normally.
- Test suite extended: `test_operators.py`, `test_envelope.py`,
  `test_alignment.py`, `test_exceptions.py`, plus new coverage in
  `test_sidecar.py` and `test_langgraph_adapter.py` for Govern mode, the
  intent/role consistency checks, and injected intent/history.

### Fixed

- `risk_block_threshold` was never validated at construction — an
  unrecognized value (e.g. a typo like `"SEVERE"`) passed straight through
  `Sidecar.__init__` and only surfaced as a `KeyError` deep inside
  `evaluate()`, silently resolved via `on_sidecar_failure` instead of
  failing fast. A misconfigured threshold could therefore fail open on a
  genuinely high-risk action. Now validated against `RISK_ORDER` at
  construction, raising immediately.
- `IntentEnvelope.is_expired()` raised an unhandled `TypeError` for a naive
  (no `tzinfo`) `expires` value — a realistic input shape from YAML or a
  caller that forgot `tzinfo=timezone.utc` — comparing it against the
  timezone-aware `datetime.now(timezone.utc)`. Inside `evaluate()` that
  error was swallowed into `on_sidecar_failure`'s fallback instead of
  producing the deterministic intent-expiry `WARN` it should have. Now
  rejected explicitly, at `IntentEnvelope` construction (a `field_validator`
  on `expires`) and in `is_expired()`'s own `now=` parameter, with an error
  naming the fix rather than a bare `TypeError`.
- `SidecarBlockedError`, raised by the LangGraph adapter in Govern mode,
  carried the bare pre-evaluation `DecisionContext` the adapter built, not
  the one Intent Guardian actually evaluated — `Sidecar.evaluate()`
  injected `intent`/`history` into a *copy* (`context.model_copy(...)`)
  rather than the object the caller held, so `SidecarBlockedError.context`
  always had `intent=None`, even when an intent-drift finding was exactly
  why the call was blocked. `evaluate()` now injects by mutating the
  caller's `DecisionContext` in place (documented as intentional on the
  model itself — it's why `DecisionContext`, unlike `Decision`, isn't
  frozen), so any caller's own reference — not just `sidecar.decisions` —
  reflects the fully-evaluated context once `evaluate()` returns.
- ROADMAP.md's v0.2 deliverable cited concept.md §22 (the DEV/production
  cleanup scenario, actually used by the v0.2.x benchmark) for the
  refund-limit worked example; corrected to §9, which is where that
  scenario actually appears.

## [0.1.0] - 2026-08-15

### Added

- Sidecar runtime (`agentic_sidecar.core`): `Sidecar`, `Decision(status,
  risk, reason)`, `DecisionContext`. `on_sidecar_failure: fail_open |
  fail_closed` is a required setting with no default; both paths are
  tested. `roles` validates against v0.1's supported set (`policy`, `risk`)
  and raises `NotImplementedError` (naming the version) for roles planned
  but not yet built, rather than silently ignoring them.
- Decision Gate (`agentic_sidecar.gate`): YAML-driven Policy Advisor
  (`policy.py`, allow/deny rules by tool-name glob) and rule-based Risk
  Evaluator (`risk.py`, tool-name glob plus an optional argument-pattern
  check). Zero LLM calls, per ROADMAP.md's Design Constraint 2.
- LangGraph adapter (`agentic_sidecar.adapters.langgraph.attach`): wraps a
  list of tool callables so every call is evaluated by a `Sidecar` first.
  v0.1 ships Observe mode only — the wrapped call always executes; nothing
  yet enforces a `BLOCK`. No import-time dependency on the `langgraph`
  package itself; a `langgraph` extra is declared in `pyproject.toml` for
  code that actually builds a graph around the wrapped tools.
- `examples/langgraph_refund_observe_mode.py` — a runnable, offline
  (no API key) example against a real `langgraph.prebuilt.create_react_agent`
  agent, demonstrating a Policy Advisor deny rule and a Risk Evaluator
  argument-threshold rule both firing in Observe mode.
- Test suite covering `Decision`, `DecisionContext`, `PolicyAdvisor`,
  `RiskEvaluator`, `Sidecar` (including both `on_sidecar_failure` paths),
  and the LangGraph adapter.

### Changed

- `Sidecar.attach(agent)` from README.md's Planned Python API is *not* how
  v0.1 actually ships attach: `core/` must not import from `adapters/`
  (AGENTS.md's Package Boundaries), so wrapping a specific framework's
  tool-call surface is each adapter's own function
  (`agentic_sidecar.adapters.langgraph.attach(sidecar, tools)`) rather than
  a generic method on `Sidecar`. README.md documents both the real v0.1
  shape and the longer-term generic shape this is expected to grow toward
  once a second adapter exists (Design Constraint 1).

### Fixed

- ROADMAP.md's Release Status/summary described v0.1 as "Rule-Based
  Decision Gate" without noting it's Observe-mode-only (advisory logging,
  not enforcement) — a reader skimming just the top could overestimate
  what shipped. Now says so explicitly in both places.
- ROADMAP.md's Package Layout diagram listed a `semantica.py` placeholder
  under `integrations/` as if it already existed, alongside `agenticlens.py`
  and `agentic_chaos.py`, which do. It doesn't yet (no code, no
  `pyproject.toml` extra) — it's a v0.6 deliverable; the diagram now says
  so. Same diagram also still described `core/sidecar.py` as owning
  `attach()`, which isn't how v0.1 actually shipped it (see "Changed"
  above) — corrected to match.
- ROADMAP.md's Design Constraints section header said "these four" while
  listing five items.
- ROADMAP.md's top summary said v0.2-onward modules were "still unstarted"
  when docstring-only placeholders for several of them already exist in
  the tree — reworded to distinguish "no real logic yet" from "doesn't
  exist yet."

## [0.0.1] - 2026-08-12

### Added

- Initial repository scaffold: proposed package layout under
  `src/agentic_sidecar/` (placeholder modules only, no logic), `pyproject.toml`,
  `Makefile`, CI and PyPI-release GitHub Actions workflows, and contributor
  docs (`AGENTS.md`, `CONTRIBUTING.md`, `CI.md`, `SECURITY.md`).
- `README.md` and `ROADMAP.md` describing the architecture and v0.1–v1.0
  build plan.
- Reserved (not implemented) optional integration seats for both sibling
  projects: `agenticlens` and `agentic-chaos` extras in `pyproject.toml`,
  each with a docstring-only placeholder under
  `src/agentic_sidecar/integrations/`.

### Fixed

- Audited `README.md`/`ROADMAP.md` against the original concept doc and
  corrected two gaps: the `Planner` module was named throughout the docs
  but had no package file, version, or repo-map entry (now
  `evaluators/planner.py`, v0.3); the `CHALLENGE` Decision Gate outcome was
  dropped from every enumeration while `ROADMAP.md` still claimed "all
  seven" outcomes (now restored, v0.4). Also documented two previously
  silent scope cuts (`LangChain` folded into the `LangGraph` adapter;
  sampling/caching/async-advisory cost-control ideas left unscheduled)
  instead of leaving them unexplained.

### Changed

- Renamed `future-plans.md` to `concept.md` and updated every reference.
