"""Task-local execution lifecycle, operator controls, and correlated approvals."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from agentic_sidecar.core.context import DecisionContext
from agentic_sidecar.core.decision import Decision
from agentic_sidecar.core.exceptions import SidecarBlockedError, SidecarSuspendedError
from agentic_sidecar.gate.escalation import (
    ApprovalAction,
    ApprovalResponse,
    EscalationHandler,
    EscalationRequest,
)
from agentic_sidecar.operations.events import EventJournal

if TYPE_CHECKING:
    from agentic_sidecar.core.sidecar import Sidecar


class TaskRuntime(EscalationHandler):
    """One controller per Sidecar task. Stop is independent of models/failure policy.

    Dispatch reservation and stop latch share a lock. Already dispatched calls
    may complete; revocation/cancellation is supplied explicitly by the harness.
    """

    def __init__(
        self,
        task_id: str | None = None,
        *,
        journal: EventJournal | None = None,
        approval_timeout: float = 300,
        revokers: dict[str, Callable[[str], bool]] | None = None,
    ) -> None:
        self.task_id = task_id or (journal.task_id if journal else str(uuid4()))
        if re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", self.task_id) is None:
            raise ValueError("Task ID must be a safe path identifier")
        if journal and journal.task_id != self.task_id:
            raise ValueError("Journal task identity mismatch")
        if approval_timeout <= 0 or not approval_timeout < float("inf"):
            raise ValueError("approval_timeout must be finite and positive")
        self.journal = journal or EventJournal(self.task_id)
        self.approval_timeout = approval_timeout
        self.revokers = dict(revokers or {})
        self._condition = threading.Condition(threading.RLock())
        self._sidecar: Sidecar | None = None
        self._epoch = 0
        self._paused = False
        self._stopped = bool(self.journal.export())
        self._revocation_failed = False
        self._revocation_pending = False
        self._decisions: dict[str, tuple[int, str]] = {}
        self._stop_operation_lock = threading.Lock()
        self._dispatched: set[str] = set()
        self._running: dict[str, dict[str, Any]] = {}
        self._cancellers: dict[str, Callable[[], None]] = {}
        self._pending: dict[str, EscalationRequest] = {}
        self._responses: dict[str, ApprovalResponse] = {}
        self._audit_errors: list[str] = []
        self._executed = 0
        self._completed = 0
        for event in self.journal.export():
            payload = event["payload"]
            if event["kind"] == "executed":
                self._executed += 1
                self._running[payload["invocation_id"]] = payload
            elif event["kind"] in {"completed", "failed"}:
                self._completed += int(event["kind"] == "completed")
                self._running.pop(payload["invocation_id"], None)
            elif event["kind"] == "stop_acknowledged":
                self._revocation_failed = payload["access_revocation"] == "partial_failure"
            elif event["kind"] == "control" and payload["action"] == "stop":
                self._revocation_pending = True
            if event["kind"] == "stop_acknowledged":
                self._revocation_pending = False

    def bind(self, sidecar: Sidecar) -> None:
        if self._sidecar is not None:
            raise ValueError("Runtime already bound to a task")
        self._sidecar = sidecar

    @property
    def stopped(self) -> bool:
        with self._condition:
            return self._stopped

    @property
    def epoch(self) -> int:
        with self._condition:
            return self._epoch

    def propose(self, context: DecisionContext) -> None:
        with self._condition:
            event = self.journal.append(
                "proposed",
                {
                    "context": context.model_dump(mode="json"),
                    "epoch": context._runtime_epoch,
                },
            )
            context._proposal_id = event.event_id

    def record(self, context: DecisionContext, decision: Decision) -> None:
        with self._condition:
            sidecar = self._require_sidecar()
            serialized = context.model_dump(mode="json")
            policy = {
                "default": sidecar.policy.default_effect,
                "rules": [rule.model_dump(mode="json") for rule in sidecar.policy.rules],
            }
            policy_version = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
            self.journal.append(
                "decision",
                {
                    "decision": decision.model_dump(mode="json"),
                    "trigger": {
                        "boundary_type": context.boundary,
                        "tool_name": context.tool_name,
                        "arguments": serialized["tool_args"],
                    },
                    "rationale": {
                        "reason": decision.reason,
                        "risk": decision.risk,
                        "findings": context._findings,
                    },
                    "context": serialized,
                    "proposal_id": context._proposal_id,
                    "epoch": context._runtime_epoch,
                    "policy_version": policy_version,
                    "policy": policy,
                    "parent_plan_step": context.parent_plan_step,
                },
            )
            self.authorize(context, decision)

    def authorize(self, context: DecisionContext, decision: Decision) -> None:
        """Remember the validated result even if recording resolved via fail_open."""
        with self._condition:
            self._decisions[decision.decision_id] = (
                context._runtime_epoch,
                decision.model_dump_json(),
            )

    def _emit_execution(self, kind: str, payload: dict[str, Any]) -> None:
        try:
            self.journal.append(kind, payload)
        except Exception as exc:
            self._audit_errors.append(type(exc).__name__)
            if self._require_sidecar().on_sidecar_failure == "fail_closed":
                raise

    def dispatch(
        self,
        context: DecisionContext,
        decision: Decision,
        *,
        cancel: Callable[[], None] | None = None,
    ) -> str:
        """Reserve dispatch exactly once after enforcement; reject stale approvals."""
        with self._condition:
            sidecar = self._require_sidecar()
            if self._stopped or sidecar.stopped:
                raise SidecarBlockedError(
                    Decision(status="BLOCK", risk=None, reason="Task stopped"), context
                )
            if sidecar.mode == "govern" and decision.status not in {"ALLOW", "WARN"}:
                if decision.status == "BLOCK":
                    raise SidecarBlockedError(decision, context)
                raise SidecarSuspendedError(decision, context)
            if self._paused:
                raise SidecarSuspendedError(
                    Decision(status="PAUSE", risk=None, reason="Operator paused task"), context
                )
            if (
                self._decisions.get(decision.decision_id)
                != (self._epoch, decision.model_dump_json())
                or decision.decision_id in self._dispatched
            ):
                raise SidecarBlockedError(
                    Decision(status="BLOCK", risk=None, reason="Stale or consumed decision"),
                    context,
                )
            invocation_id = str(uuid4())
            payload: dict[str, Any] = {
                "invocation_id": invocation_id,
                "decision_id": decision.decision_id,
                "tool_name": context.tool_name,
            }
            try:
                payload["arguments"] = context.model_dump(mode="json")["tool_args"]
            except Exception as exc:
                self._audit_errors.append(type(exc).__name__)
                if sidecar.on_sidecar_failure == "fail_closed":
                    raise
                payload["arguments_unavailable"] = True
            self._emit_execution("executed", payload)
            self._executed += 1
            self._dispatched.add(decision.decision_id)
            self._running[invocation_id] = payload
            if cancel is not None:
                self._cancellers[invocation_id] = cancel
            return invocation_id

    def complete(self, invocation_id: str, error: BaseException | None = None) -> None:
        with self._condition:
            payload = self._running[invocation_id]
            self._emit_execution(
                "failed" if error else "completed",
                {**payload, "error_type": type(error).__name__ if error else None},
            )
            self._completed += int(error is None)
            del self._running[invocation_id]
            self._cancellers.pop(invocation_id, None)

    def is_running(self, invocation_id: str) -> bool:
        with self._condition:
            return invocation_id in self._running

    def handle_escalation(self, request: EscalationRequest) -> ApprovalResponse:
        with self._condition:
            self.journal.append("paused", {"request": asdict(request)})
            self._pending[request.decision_id] = deepcopy(request)
            deadline = time.monotonic() + self.approval_timeout
            try:
                while request.decision_id not in self._responses and not self._stopped:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        # Timeout suspends rather than allowing under fail_open.
                        return ApprovalResponse(
                            request.decision_id,
                            ApprovalAction.ASK_AGENT_TO_REPLAN,
                            explanation="Operator approval timed out",
                        )
                    self._condition.wait(remaining)
                if self._stopped:
                    return ApprovalResponse(request.decision_id, ApprovalAction.STOP_AGENT)
                return self._responses.pop(request.decision_id)
            finally:
                self._pending.pop(request.decision_id, None)

    def approve(self, response: ApprovalResponse, actor: str) -> None:
        with self._condition:
            if self._stopped:
                raise ValueError("Task stopped")
            request = self._pending.get(response.decision_id)
            if request is None or response.decision_id in self._responses:
                raise ValueError("No unresolved approval with that decision ID")
            if not isinstance(response.action, ApprovalAction):
                raise ValueError("ApprovalAction required")
            if response.action not in request.available_actions:
                raise ValueError("Unavailable approval action")
            if response.action == ApprovalAction.MODIFY_INTENT:
                from agentic_sidecar.intent.envelope import IntentEnvelope

                sidecar = self._require_sidecar()
                if sidecar.intent is None or response.modified_intent is None:
                    raise ValueError("Active intent and a complete envelope required")
                IntentEnvelope.model_validate(response.modified_intent)
            self.journal.append("approval", {"actor": actor, **asdict(response)})
            if response.action == ApprovalAction.STOP_AGENT:
                self._stopped = True
                self._require_sidecar().stopped = True
                self._revocation_pending = True
            self._responses[response.decision_id] = deepcopy(response)
            self._condition.notify_all()
        if response.action == ApprovalAction.STOP_AGENT:
            self.control("stop", actor)

    def modify_intent(self, envelope: dict[str, Any], actor: str) -> None:
        """Replace a full task envelope and invalidate all earlier verdicts."""
        from agentic_sidecar.intent.alignment import IntentGuardian
        from agentic_sidecar.intent.envelope import IntentEnvelope

        validated = IntentEnvelope.model_validate(envelope)
        with self._condition:
            sidecar = self._require_sidecar()
            if self._stopped or sidecar.intent is None:
                raise ValueError("An active, non-stopped intent task is required")
            self.journal.append(
                "intent_modified",
                {
                    "actor": actor,
                    "previous": sidecar.intent.envelope.model_dump(mode="json"),
                    "intent": validated.model_dump(mode="json"),
                },
            )
            sidecar.set_intent(IntentGuardian(validated, sidecar.intent.bindings))
            self._epoch += 1

    def control(self, action: str, actor: str) -> dict[str, Any]:
        if action == "stop":
            with self._stop_operation_lock:
                return self._control(action, actor)
        return self._control(action, actor)

    def _control(self, action: str, actor: str) -> dict[str, Any]:
        if action not in {"pause", "resume", "stop", "restart", "replan"}:
            raise ValueError("Unknown control action")
        with self._condition:
            sidecar = self._require_sidecar()
            if action == "restart":
                if (
                    not self._stopped
                    or self._running
                    or self._revocation_failed
                    or self._revocation_pending
                ):
                    raise ValueError("Restart requires stopped, idle, successfully revoked task")
            elif self._stopped and action != "stop":
                raise ValueError("Task stopped; explicit restart required")
            if action == "stop":
                # Latch first, even if persistence or external revocation fails.
                self._revocation_pending = True
                self._stopped = True
                sidecar.stopped = True
                self._epoch += 1
                self._condition.notify_all()
            receipt: dict[str, Any] = {
                "action": action,
                "actor": actor,
                "epoch": self._epoch + int(action in {"pause", "replan", "restart"}),
                "effective_at": datetime.now(timezone.utc).isoformat(),
                "running": list(self._running),
                "cancellation": "harness_owned",
            }
            try:
                self.journal.append("control", receipt)
            except Exception as exc:
                if action != "stop":
                    raise
                # Emergency access revocation must proceed even with a broken sink.
                self._audit_errors.append(type(exc).__name__)
                receipt["audit_error"] = type(exc).__name__
            if action == "restart":
                self._epoch += 1
                self._stopped = False
                sidecar.stopped = False
                self._paused = False
            elif action == "pause" or action == "replan":
                self._paused = True
                self._epoch += 1
            elif action == "resume":
                self._paused = False
            cancellers = dict(self._cancellers)
        if action == "stop":
            cancellations = {}
            for invocation_id in receipt["running"]:
                cancel = cancellers.get(invocation_id)
                try:
                    if cancel is not None:
                        cancel()
                    cancellations[invocation_id] = "requested" if cancel else "unsupported"
                except Exception:
                    cancellations[invocation_id] = "failed"
            receipt["cancellations"] = cancellations
            acknowledgements = {}
            for name, revoke in self.revokers.items():
                try:
                    acknowledgements[name] = revoke(self.task_id) is True
                except Exception:
                    acknowledgements[name] = False
            with self._condition:
                self._revocation_pending = False
                self._revocation_failed = not all(acknowledgements.values())
                receipt["revocations"] = acknowledgements
                receipt["access_revocation"] = (
                    "partial_failure"
                    if self._revocation_failed
                    else "acknowledged"
                    if acknowledgements
                    else "not_configured"
                )
                try:
                    self.journal.append("stop_acknowledged", receipt)
                except Exception as exc:
                    self._audit_errors.append(type(exc).__name__)
                    receipt["audit_error"] = type(exc).__name__
        return receipt

    def snapshot(self) -> dict[str, Any]:
        with self._condition:
            sidecar = self._require_sidecar()
            events = self.journal.export()
            decisions = [e["payload"] for e in events if e["kind"] == "decision"]
            actions = {}
            for event in events:
                payload = event["payload"]
                if event["kind"] == "decision" and payload["context"]["boundary"] == "tool_call":
                    decision = payload["decision"]
                    status = decision["status"]
                    actions[decision["decision_id"]] = {
                        "decision_id": decision["decision_id"],
                        "tool_name": payload["context"]["tool_name"],
                        "reason": decision["reason"],
                        "state": (
                            "blocked"
                            if status == "BLOCK"
                            else "paused"
                            if status in {"PAUSE", "ESCALATE"}
                            else "suspended"
                            if status in {"CHALLENGE", "REPLAN"}
                            else "proposed"
                        ),
                    }
                    parent = decision["causal_link"]
                    if parent in actions:
                        actions[parent]["state"] = "resolved"
                elif event["kind"] in {"executed", "completed", "failed"}:
                    decision_id = payload["decision_id"]
                    if decision_id in actions:
                        actions[decision_id]["state"] = event["kind"]
            budget = asdict(sidecar.budget.evaluate()) if sidecar.budget else None
            return {
                "task_id": self.task_id,
                "mode": sidecar.mode,
                "objective": sidecar.intent.envelope.goal if sidecar.intent else None,
                "intent": sidecar.intent.envelope.model_dump(mode="json")
                if sidecar.intent
                else None,
                "plan": next(
                    (
                        d["context"]["plan"]
                        for d in reversed(decisions)
                        if d["context"]["boundary"] == "plan"
                    ),
                    [],
                ),
                "budget": budget,
                "stopped": self._stopped or sidecar.stopped,
                "paused": self._paused or bool(self._pending),
                "pending": [asdict(r) for r in self._pending.values()],
                "running": list(self._running.values()),
                "completed": self._completed,
                "executed": self._executed,
                "audit_errors": list(self._audit_errors),
                "decisions": decisions,
                "actions": list(actions.values()),
                "sequence": len(events),
                "risk": decisions[-1]["decision"]["risk"] if decisions else None,
                "alignment": (
                    decisions[-1]["rationale"]["findings"].get("alignment", {}) if decisions else {}
                ),
                "revocation_failed": self._revocation_failed,
            }

    def _require_sidecar(self) -> Sidecar:
        if self._sidecar is None:
            raise RuntimeError("Runtime is not bound to a Sidecar")
        return self._sidecar
