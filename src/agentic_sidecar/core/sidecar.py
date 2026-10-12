"""Decision supervision runtime; deterministic gates and optional evaluators.

Sidecar.evaluate computes decisions without dispatch. Adapters call enforce in
Govern mode to resolve local approvals or stop/suspend unresolved proposals.
All evaluation and approval errors respect explicit on_sidecar_failure.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Sequence
from contextlib import suppress
from copy import deepcopy
from typing import Any, Literal
from uuid import uuid4

from agentic_sidecar.core.context import DecisionContext, HistoryEntry
from agentic_sidecar.core.decision import Decision, DecisionStatus, RiskLevel
from agentic_sidecar.core.exceptions import SidecarBlockedError, SidecarSuspendedError
from agentic_sidecar.evaluators.base import EvaluatorResult
from agentic_sidecar.evaluators.critic import CriticEvaluator
from agentic_sidecar.evaluators.judge import JudgeEvaluator
from agentic_sidecar.evaluators.planner import PlanEvaluator
from agentic_sidecar.gate.budget import BudgetGuardian
from agentic_sidecar.gate.escalation import (
    ApprovalAction,
    ApprovalResponse,
    EscalationHandler,
    EscalationRequest,
)
from agentic_sidecar.gate.policy import PolicyAdvisor
from agentic_sidecar.gate.risk import RISK_ORDER, RiskEvaluator
from agentic_sidecar.intent.alignment import AlignmentResult, IntentGuardian
from agentic_sidecar.intent.envelope import IntentEnvelope
from agentic_sidecar.operations.runtime import TaskRuntime

logger = logging.getLogger("agentic_sidecar")

SidecarFailureMode = Literal["fail_open", "fail_closed"]
SidecarMode = Literal["observe", "govern"]
DecisionHook = Callable[[DecisionContext], Decision]
EscalationHook = Callable[..., ApprovalResponse]

_SUPPORTED_ROLES = frozenset(
    {
        "policy",
        "risk",
        "intent_guardian",
        "budget",
        "planner",
        "critic",
        "judge",
    }
)
_KNOWN_FUTURE_ROLES: dict[str, str] = {}


class Sidecar:
    """Owns the Decision Gate: Policy Advisor, Risk Evaluator, Intent Guardian
    (v0.2), Budget Guardian (v0.4), and Evaluators (v0.3: Planner, Critic, Judge),
    combined into a single `Decision` per proposed action.

    `on_sidecar_failure` is a required keyword argument with no default --
    pick `"fail_closed"` unless you have a specific reason to fail open (see
    ROADMAP.md's Design Constraint 3: anything that reaches a Decision Gate
    at all is, by definition, a decision boundary worth being conservative
    about).

    Observe records every Decision. Govern adapters call enforce before
    dispatch: ALLOW/WARN proceed; BLOCK stops; PAUSE/ESCALATE invoke local
    approvals or suspend; CHALLENGE/REPLAN suspend for the caller to resolve.

    v0.1 has no `attach()` method here: routing a specific framework's
    tool-call surface through `evaluate()` is an adapter's job, not core's
    (AGENTS.md's Package Boundaries -- `core/` must not import from
    `adapters/`). See `agentic_sidecar.adapters.langgraph.attach()`.
    """

    def __init__(
        self,
        *,
        on_sidecar_failure: SidecarFailureMode,
        policy: PolicyAdvisor | None = None,
        risk: RiskEvaluator | None = None,
        intent: IntentGuardian | None = None,
        budget: BudgetGuardian | None = None,
        planner: PlanEvaluator | None = None,
        critic: CriticEvaluator | None = None,
        judge: JudgeEvaluator | None = None,
        escalation_handler: EscalationHandler | None = None,
        risk_block_threshold: RiskLevel = "HIGH",
        mode: SidecarMode = "observe",
        roles: Sequence[str] | None = None,
        runtime: TaskRuntime | None = None,
    ) -> None:
        if on_sidecar_failure not in ("fail_open", "fail_closed"):
            raise ValueError(
                f"on_sidecar_failure={on_sidecar_failure!r} is invalid -- it "
                "is a required setting with no default and must be "
                "'fail_open' or 'fail_closed' (ROADMAP.md's Design "
                "Constraint 3). 'fail_closed' is the recommended default."
            )
        if mode not in ("observe", "govern"):
            raise ValueError(
                f"mode={mode!r} is invalid -- must be 'observe' (logs "
                "decisions, enforces nothing) or 'govern' (a BLOCK is "
                "actually enforced by the attached adapter). See "
                "ROADMAP.md's Operating modes."
            )
        if risk_block_threshold not in RISK_ORDER:
            raise ValueError(
                f"risk_block_threshold={risk_block_threshold!r} is invalid "
                f"-- must be one of {list(RISK_ORDER)!r}. An unrecognized "
                "threshold would otherwise only surface as a KeyError "
                "inside evaluate(), silently resolved via "
                "on_sidecar_failure instead of failing fast here."
            )

        self.on_sidecar_failure = on_sidecar_failure
        self.policy = policy or PolicyAdvisor()
        self.risk = risk or RiskEvaluator()
        self.budget = budget
        self.planner = planner
        self.critic = critic
        self.judge = judge
        if judge is not None and budget is not None and (roles is not None and "budget" in roles):
            if judge.budget is not None and judge.budget is not budget:
                raise ValueError("Judge and Sidecar must share the same task budget")
            judge.budget = budget
        self.escalation_handler = escalation_handler
        self.risk_block_threshold = risk_block_threshold
        self.mode = mode
        self.roles = self._validate_roles(roles)
        self.decisions: list[tuple[DecisionContext, Decision]] = []
        self.stopped = False
        self.runtime = runtime or TaskRuntime()
        self.runtime.bind(self)
        self.stopped = self.runtime.stopped
        self._hook: DecisionHook | None = None
        self._escalation_hook: EscalationHook | None = None
        self.intent: IntentGuardian | None = None
        self.set_intent(intent)

    @staticmethod
    def _validate_roles(roles: Sequence[str] | None) -> tuple[str, ...]:
        resolved = tuple(roles) if roles is not None else ("policy", "risk")
        for role in resolved:
            if role in _SUPPORTED_ROLES:
                continue
            if role in _KNOWN_FUTURE_ROLES:
                raise NotImplementedError(
                    f"role={role!r} is not implemented until "
                    f"{_KNOWN_FUTURE_ROLES[role]} -- see ROADMAP.md's build "
                    f"order. Currently supported: {sorted(_SUPPORTED_ROLES)}."
                )
            raise ValueError(
                f"Unknown role {role!r}. Currently supported: {sorted(_SUPPORTED_ROLES)}."
            )
        return resolved

    def set_intent(self, intent: IntentGuardian | None) -> None:
        """Set (or clear) the active `IntentGuardian` -- separate from
        `__init__` because a long-lived Sidecar is expected to serve one
        `IntentEnvelope` per task, not one for its whole lifetime (concept.md
        §6: the envelope is created "when a user initiates a task").

        Raises if `intent` is given but `"intent_guardian"` isn't in
        `self.roles` -- a `Sidecar` that would silently never consult the
        guardian you just handed it is exactly the kind of silent gap
        ROADMAP.md's Design Constraint 3 warns against for
        `on_sidecar_failure`, and the same principle applies here. The
        reverse (role enabled, no envelope yet) is *not* an error: a
        multi-task Sidecar may legitimately start before its first
        envelope arrives.
        """
        if intent is not None and "intent_guardian" not in self.roles:
            raise ValueError(
                "intent=... was given but 'intent_guardian' is not in "
                f"roles={list(self.roles)!r} -- it would never be "
                "consulted. Add 'intent_guardian' to roles, or don't pass "
                "intent."
            )
        self.intent = intent

    def before_tool_call(self, func: DecisionHook) -> DecisionHook:
        """Register a custom decision hook, overriding the default
        Policy + Risk + Intent Guardian evaluation for every subsequent
        `evaluate()` call.

        ```python
        @sidecar.before_tool_call
        def evaluate_action(context: DecisionContext) -> Decision:
            if context.tool_name == "delete_database":
                return Decision(status="BLOCK", risk="HIGH", reason="never")
            return Decision(status="ALLOW", risk="LOW", reason="ok")
        ```

        Mirrors the shape sketched in README.md's Planned Python API. Once
        registered, the hook fully replaces the built-in Decision Gate
        modules for every `evaluate()` call -- there is no v0.2 mechanism
        to run both a custom hook and the built-in modules together. The
        hook still receives a context with `intent`/`history` already
        injected (see `evaluate()`).
        """
        self._hook = func
        return func

    def on_escalation_required(self, func: EscalationHook) -> EscalationHook:
        """Register a custom escalation handler for PAUSE/ESCALATE outcomes.

        The handler receives an EscalationRequest and returns an ApprovalResponse.
        This is called when a Decision outcome is PAUSE or ESCALATE and
        escalation_handler is not set in __init__.

        ```python
        @sidecar.on_escalation_required
        def handle_approval(request: EscalationRequest) -> ApprovalResponse:
            # Custom UI or CLI logic here
            action = user_approval_dialog(request.reason)
            return ApprovalResponse(
                decision_id=request.decision_id,
                action=action
            )
        ```

        Govern enforcement invokes this hook unless escalation_handler was supplied.
        """
        self._escalation_hook = func
        return func

    def evaluate(self, context: DecisionContext, *, causal_link: str | None = None) -> Decision:
        """Evaluate one proposed action and return a `Decision`.

        Injects the active intent snapshot and this Sidecar's decision
        history into `context` first (concept.md §7, Intent Injection) --
        the caller only needs to supply `tool_name`/`tool_args`. This
        mutates the `context` object the caller passed in, in place (rather
        than evaluating a copy) -- `DecisionContext` is deliberately not
        frozen for exactly this reason, and it means a caller (e.g. an
        adapter constructing `SidecarBlockedError`) sees the fully-injected
        context on its own reference after `evaluate()` returns, not the
        bare one it originally built. Always resolves, per
        `on_sidecar_failure`, even if injection, evaluation, validation or
        recording fails. Records contain deep copies; failed recording cannot
        guarantee an entry. Each invocation receives a fresh decision ID.
        Never raises for a `BLOCK` decision itself,
        in either mode -- that a `BLOCK` should actually stop the call is
        enforced by the attached adapter in Govern mode, not by
        `evaluate()` (see `agentic_sidecar.core.exceptions.SidecarBlockedError`).
        """
        context._runtime_epoch = self.runtime.epoch
        context._findings = {}
        try:
            self._inject(context)
            self.runtime.propose(context)
            if self.stopped:
                decision = Decision(status="BLOCK", risk=None, reason="Task stopped")
            else:
                evaluator = self._hook or self._default_evaluate
                decision = evaluator(context)
            if not isinstance(decision, Decision):
                raise TypeError("Decision hooks must return a Decision")
            # Revalidate even objects constructed with model_construct/model_copy.
            decision = Decision.model_validate(decision.model_dump()).model_copy(
                update={
                    "decision_id": str(uuid4()),
                    "causal_link": causal_link
                    or context.parent_decision_id
                    or decision.causal_link,
                }
            )
            self._record(context, decision)
        except Exception as exc:
            decision = self._on_failure(context, exc).model_copy(
                update={"causal_link": causal_link}
            )
            # A broken recorder must not bypass the configured failure policy.
            with suppress(Exception):
                self._record(context, decision)
        self.runtime.authorize(context, decision)
        return decision

    def _record(self, context: DecisionContext, decision: Decision) -> None:
        self.runtime.record(context, decision)
        self._log_decision(context, decision)
        self.decisions.append((context.model_copy(deep=True), decision.model_copy(deep=True)))

    def evaluate_plan(
        self, plan: list[dict[str, Any]], *, goal: str = "", metadata: dict[str, Any] | None = None
    ) -> Decision:
        """Evaluate a full plan before dispatch; does not execute any plan step.

        Each step must have tool_name and an optional arguments mapping.
        Policy, risk and bound intent constraints are checked for every step.
        """
        return self.evaluate(
            DecisionContext(
                tool_name="__plan__",
                boundary="plan",
                plan=plan,
                goal=goal,
                metadata=metadata or {},
            )
        )

    def enforce(self, context: DecisionContext, decision: Decision) -> Decision:
        """Resolve a governance boundary; adapters call this before dispatch.

        BLOCK cannot be approved. CHALLENGE/REPLAN return control immediately.
        PAUSE/ESCALATE call a registered handler, or suspend if none exists.
        Approval is scoped to this invocation and is never cached.
        """
        if self.mode == "observe":
            return decision
        if decision.status in ("PAUSE", "ESCALATE"):
            decision = self._resolve_approval(context, decision)
            self.runtime.authorize(context, decision)
        if decision.status == "BLOCK":
            raise SidecarBlockedError(decision, context)
        if decision.status not in ("ALLOW", "WARN"):
            raise SidecarSuspendedError(decision, context)
        return decision

    def _resolve_approval(self, context: DecisionContext, decision: Decision) -> Decision:
        handler = self.escalation_handler
        callback = handler.handle_escalation if handler is not None else self._escalation_hook
        if callback is None:
            return decision.model_copy(
                update={
                    "reason": decision.reason + "; no escalation handler registered",
                }
            )
        try:
            request = EscalationRequest(
                decision_id=decision.decision_id,
                reason=decision.reason,
                context=context.model_dump(mode="json"),
                available_actions=list(ApprovalAction),
            )
            response = callback(request)
            if not isinstance(response, ApprovalResponse):
                raise TypeError("Escalation handler must return ApprovalResponse")
            if response.decision_id != decision.decision_id:
                raise ValueError("Approval decision_id does not match the request")
            if not isinstance(response.action, ApprovalAction):
                raise ValueError("Approval action must be an ApprovalAction")
            if response.action not in list(ApprovalAction):
                raise ValueError("Approval action is not available")
            status: DecisionStatus
            if response.action == ApprovalAction.MODIFY_INTENT:
                if self.intent is None or response.modified_intent is None:
                    raise ValueError("modify_intent requires an active intent and a full envelope")
                envelope = IntentEnvelope.model_validate(response.modified_intent)
                self.runtime.modify_intent(envelope.model_dump(mode="json"), "escalation_handler")
                # Reevaluate once; another PAUSE returns to the caller without a prompt loop.
                return self.evaluate(context, causal_link=decision.decision_id)
            if response.action == ApprovalAction.STOP_AGENT:
                if not self.stopped:
                    self.runtime.control("stop", "escalation_handler")
                status = "BLOCK"
            elif response.action == ApprovalAction.REJECT:
                status = "BLOCK"
            elif response.action == ApprovalAction.ASK_AGENT_TO_REPLAN:
                status = "REPLAN"
            else:
                status = "ALLOW"
            resolved = Decision(
                status=status,
                risk=decision.risk,
                reason=f"Approval: {response.action.value}. {response.explanation}",
                decision_point=context.boundary,
                causal_link=decision.decision_id,
                trigger_details={"tool_name": context.tool_name, "arguments": context.tool_args},
            )
            self._record(context, resolved)
            return resolved
        except Exception as exc:
            fallback = self._on_failure(context, exc).model_copy(
                update={
                    "causal_link": decision.decision_id,
                }
            )
            with suppress(Exception):
                self._record(context, fallback)
            return fallback

    def _evaluator_context(self, context: DecisionContext) -> dict[str, Any]:
        return {
            "tool_name": context.tool_name,
            "arguments": context.tool_args,
            "history": [entry.model_dump() for entry in context.history],
            "intent": context.intent.model_dump() if context.intent else None,
            "goal": context.intent.goal if context.intent else context.goal,
            "constraints": context.intent.constraints if context.intent else {},
            "plan": context.plan,
            "metadata": context.metadata,
            "boundary": context.boundary,
            "constraint_bindings": [binding.model_dump() for binding in self.intent.bindings]
            if self.intent
            else [],
        }

    @staticmethod
    def _validate_result(result: EvaluatorResult) -> DecisionStatus:
        if not isinstance(result, EvaluatorResult):
            raise TypeError("Evaluator must return EvaluatorResult")
        if not math.isfinite(result.confidence) or not 0 <= result.confidence <= 1:
            raise ValueError("Evaluator confidence must be finite and between zero and one")
        return Decision.model_validate(
            {"status": result.status, "risk": None, "reason": result.rationale}
        ).status

    def _inject(self, context: DecisionContext) -> None:
        history = [
            HistoryEntry(tool_name=c.tool_name, tool_args=c.tool_args, status=d.status)
            for c, d in self.decisions
        ]
        intent_snapshot = self.intent.envelope.to_snapshot() if self.intent is not None else None
        context.intent = intent_snapshot
        context.history = history

    def _default_evaluate(self, context: DecisionContext) -> Decision:
        is_plan = context.boundary == "plan"
        plan_warnings: list[str] = []
        if is_plan:
            if not context.plan:
                raise ValueError("Plan boundary requires at least one step")
            for step in context.plan:
                if not isinstance(step.get("tool_name"), str) or not step["tool_name"]:
                    raise ValueError("Every plan step requires a nonempty tool_name")
                step_context = DecisionContext(
                    tool_name=step["tool_name"],
                    tool_args=step.get("arguments", {}),
                    intent=context.intent,
                    history=context.history,
                )
                if "policy" in self.roles and self.policy.evaluate(step_context).effect == "deny":
                    return Decision(
                        status="BLOCK",
                        risk=None,
                        reason="Plan step denied by policy",
                        decision_point="plan",
                    )
                if "risk" in self.roles:
                    risk = self.risk.evaluate(step_context)
                    if RISK_ORDER[risk.risk] >= RISK_ORDER[self.risk_block_threshold]:
                        return Decision(
                            status="BLOCK",
                            risk=risk.risk,
                            reason=risk.reason,
                            decision_point="plan",
                        )
                if self.intent is not None and "intent_guardian" in self.roles:
                    alignment = self.intent.evaluate(step_context)
                    if alignment.status == "BLOCK":
                        return Decision(
                            status=alignment.status,
                            risk=None,
                            reason=alignment.reason,
                            decision_point="plan",
                        )
                    if alignment.status == "WARN":
                        plan_warnings.append(alignment.reason)

        # Each real step was already checked above against its own tool_name; the
        # synthetic "__plan__" marker itself has no policy/risk/binding rule to match,
        # so re-running these generic per-call checks against it would only produce
        # false BLOCKs (default-deny policy, high default risk) for an already-valid plan.
        policy_result = None
        if not is_plan and "policy" in self.roles:
            policy_result = self.policy.evaluate(context)
            context._findings["policy"] = policy_result.model_dump(mode="json")
            if policy_result.effect == "deny":
                return Decision(
                    status="BLOCK",
                    risk=None,
                    reason=f"Policy Advisor: {policy_result.reason}",
                    decision_point=context.boundary,
                    trigger_details={
                        "tool_name": context.tool_name,
                        "arguments": context.tool_args,
                    },
                )

        risk_result = None
        if not is_plan and "risk" in self.roles:
            risk_result = self.risk.evaluate(context)
            context._findings["risk"] = risk_result.model_dump(mode="json")
            if RISK_ORDER[risk_result.risk] >= RISK_ORDER[self.risk_block_threshold]:
                return Decision(
                    status="BLOCK",
                    risk=risk_result.risk,
                    reason=(
                        f"Risk Evaluator: {risk_result.reason} "
                        f"(risk >= block threshold '{self.risk_block_threshold}')"
                    ),
                    decision_point=context.boundary,
                    trigger_details={
                        "tool_name": context.tool_name,
                        "arguments": context.tool_args,
                    },
                )

        alignment_result: AlignmentResult | None = None
        if not is_plan and "intent_guardian" in self.roles and self.intent is not None:
            alignment_result = self.intent.evaluate(context)
            context._findings["alignment"] = alignment_result.model_dump(mode="json")
            if alignment_result.status == "BLOCK":
                return Decision(
                    status="BLOCK",
                    risk=risk_result.risk if risk_result else None,
                    reason=f"Intent Guardian: {alignment_result.reason}",
                    decision_point=context.boundary,
                    trigger_details={
                        "tool_name": context.tool_name,
                        "arguments": context.tool_args,
                    },
                )
        elif plan_warnings:
            # Surface the WARN findings collected per-step above; they would
            # otherwise be lost since the synthetic context matches no binding.
            alignment_result = AlignmentResult(status="WARN", reason="; ".join(plan_warnings))

        budget_result = None
        if "budget" in self.roles and self.budget is not None:
            budget_result = self.budget.evaluate()
            context._findings["budget"] = {
                "exceeded": budget_result.exceeded,
                "reason": budget_result.reason,
            }
            if budget_result.exceeded:
                return Decision(
                    status="PAUSE",
                    risk=risk_result.risk if risk_result else None,
                    reason=f"Budget Guardian: {budget_result.reason}",
                    decision_point=context.boundary,
                    trigger_details={
                        "tool_name": context.tool_name,
                        "arguments": context.tool_args,
                    },
                    escalation_required=True,
                )

        results: dict[str, EvaluatorResult] = {}
        for role, evaluator in (
            ("planner", self.planner),
            ("critic", self.critic),
            ("judge", self.judge),
        ):
            if role not in self.roles or evaluator is None or not evaluator.enabled:
                continue
            result = evaluator.evaluate(deepcopy(self._evaluator_context(context)))
            status = self._validate_result(result)
            results[role] = result
            context._findings[role] = {"status": result.status, "reason": result.rationale}
            intervention_reason = f"{role.title()}: {result.rationale}"
            if (
                role == "judge"
                and self.budget is not None
                and "budget" in self.roles
                and self.budget.is_at_capacity()
                and status in ("ALLOW", "WARN")
            ):
                status = "PAUSE"
                intervention_reason += f"; Budget Guardian: {self.budget.evaluate().reason}"
            if status not in ("ALLOW", "WARN"):
                return Decision(
                    status=status,
                    risk=risk_result.risk if risk_result else None,
                    reason=intervention_reason,
                    decision_point=context.boundary,
                    trigger_details={
                        "tool_name": context.tool_name,
                        "arguments": context.tool_args,
                    },
                    escalation_required=status in ("PAUSE", "ESCALATE"),
                )
        planner_result = results.get("planner")
        critic_result = results.get("critic")
        judge_result = results.get("judge")

        reasons = [
            f"Policy Advisor: {policy_result.reason}" if policy_result else None,
            f"Risk Evaluator: {risk_result.reason}" if risk_result else None,
            f"Intent Guardian: {alignment_result.reason}" if alignment_result else None,
            f"Budget Guardian: {budget_result.reason}" if budget_result else None,
            f"Planner: {planner_result.rationale}" if planner_result else None,
            f"Critic: {critic_result.rationale}" if critic_result else None,
            f"Judge: {judge_result.rationale}" if judge_result else None,
        ]
        reason = "; ".join(r for r in reasons if r) or (
            "No Decision Gate modules enabled in `roles`; defaulting to ALLOW."
        )
        final_status: DecisionStatus = (
            "WARN"
            if (alignment_result and alignment_result.status == "WARN")
            or any(result.status == "WARN" for result in results.values())
            else "ALLOW"
        )
        return Decision(
            status=final_status,
            risk=risk_result.risk if risk_result else None,
            reason=reason,
            decision_point=context.boundary,
            trigger_details={"tool_name": context.tool_name, "arguments": context.tool_args},
        )

    def _on_failure(self, context: DecisionContext, exc: Exception) -> Decision:
        status: Literal["ALLOW", "BLOCK"] = (
            "ALLOW" if self.on_sidecar_failure == "fail_open" else "BLOCK"
        )
        with suppress(Exception):
            logger.error(
                "Sidecar evaluation failed for tool '%s': %s", context.tool_name, exc, exc_info=exc
            )
        return Decision(
            status=status,
            risk=None,
            reason=(
                f"Sidecar evaluation raised {exc.__class__.__name__}: {exc}. "
                f"Resolved via on_sidecar_failure='{self.on_sidecar_failure}'."
            ),
        )

    def _log_decision(self, context: DecisionContext, decision: Decision) -> None:
        escalation_marker = " [ESCALATION]" if decision.escalation_required else ""
        if decision.status == "ALLOW":
            level = logging.INFO
        elif decision.status in ("BLOCK", "PAUSE", "ESCALATE"):
            level = logging.ERROR
        else:
            level = logging.WARNING
        logger.log(
            level,
            "[%s] %s tool=%s args=%s risk=%s reason=%s%s",
            self.mode.upper(),
            decision.status,
            context.tool_name,
            context.tool_args,
            decision.risk,
            decision.reason,
            escalation_marker,
        )
