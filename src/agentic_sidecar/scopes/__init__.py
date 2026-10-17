"""Trusted harness configuration for shared/exclusive context and guardrails.

Scopes are configured by the host, never selected by tool arguments. Context
transport is explicit; this module is not an orchestrator or process sandbox.
"""

import fnmatch
import json
from collections.abc import Callable, Sequence
from copy import deepcopy
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field

from agentic_sidecar.core.context import DecisionContext
from agentic_sidecar.core.decision import Decision
from agentic_sidecar.core.sidecar import Sidecar, SidecarFailureMode, SidecarMode
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyEffect, PolicyRule
from agentic_sidecar.intent.alignment import ConstraintBinding, IntentGuardian
from agentic_sidecar.intent.envelope import IntentEnvelope, Requester
from agentic_sidecar.operations import TaskRuntime


class ContextSpec(BaseModel):
    """Agent-visible instructions and structured context, without enforcement."""

    model_config = ConfigDict(extra="forbid")
    goal: str = ""
    values: dict[str, Any] = Field(default_factory=dict)


class GuardrailSpec(BaseModel):
    """A deterministic policy and bound constraints, independent of context."""

    model_config = ConfigDict(extra="forbid")
    rules: list[PolicyRule] = Field(default_factory=list)
    default_effect: PolicyEffect = "allow"
    constraints: dict[str, Any] = Field(default_factory=dict)
    bindings: list[ConstraintBinding] = Field(default_factory=list)

    def checker(self) -> Callable[[DecisionContext], Decision]:
        """Snapshot a layer; each layer must pass independently (deny wins)."""
        spec = self.model_copy(deep=True)
        for binding in spec.bindings:
            if binding.constraint not in spec.constraints:
                raise ValueError(f"Unknown guardrail constraint: {binding.constraint}")
        policy = PolicyAdvisor(spec.rules, default_effect=spec.default_effect)
        guardian = IntentGuardian(
            IntentEnvelope(
                goal="Scoped guardrails",
                requested_by=Requester(id="harness"),
                constraints=spec.constraints,
            ),
            spec.bindings,
        )

        def check(context: DecisionContext) -> Decision:
            contexts = [context]
            if context.boundary == "plan":
                contexts = [
                    DecisionContext(
                        tool_name=step["tool_name"],
                        tool_args=step.get("arguments", step.get("tool_args", {})),
                    )
                    for step in context.plan
                ]
            warning = None
            for proposed in contexts:
                result = policy.evaluate(proposed)
                if result.effect == "deny":
                    return Decision(status="BLOCK", risk="LOW", reason=result.reason)
                # Existing IntentGuardian skips missing arguments; scoped configuration
                # must fail closed instead of treating an unevaluated binding as a pass.
                for binding in spec.bindings:
                    if (
                        fnmatch.fnmatch(proposed.tool_name, binding.tool)
                        and binding.arg_name not in proposed.tool_args
                    ):
                        return Decision(status="BLOCK", risk="LOW", reason="Missing bound argument")
                alignment = guardian.evaluate(proposed)
                if alignment.status == "BLOCK":
                    return Decision(status="BLOCK", risk="LOW", reason=alignment.reason)
                if alignment.status == "WARN":
                    warning = Decision(status="WARN", risk="LOW", reason=alignment.reason)
            return warning or Decision(
                status="ALLOW", risk="LOW", reason="Scoped guardrails satisfied"
            )

        return check


class ScopeLayer(BaseModel):
    """Context only, guardrails only, or both at a shared/exclusive scope."""

    model_config = ConfigDict(extra="forbid")
    context: ContextSpec | None = None
    guardrails: GuardrailSpec | None = None


class BoundAgent:
    """A host-bound identity with its own Sidecar/history and context payload."""

    def __init__(self, sidecar: Sidecar, payload: dict[str, Any]) -> None:
        self.sidecar = sidecar
        self._payload = deepcopy(payload)

    def context(self) -> dict[str, Any]:
        """Return only this agent's resolved context as a defensive copy."""
        return deepcopy(self._payload)

    def deliver(self, receiver: Callable[[dict[str, Any]], None]) -> None:
        """Explicit host prompt/memory transport; no implicit agent mutation."""
        receiver(self.context())


class ScopedSystem:
    """Snapshot system/task scope configuration before constructing agents.

    This object contains all exclusive configuration and belongs to the trusted
    harness. Give agents only their BoundAgent payload and supervised tools.
    """

    def __init__(
        self,
        *,
        system_id: str,
        task_id: str,
        agents: Sequence[str],
        shared: ScopeLayer | None = None,
        exclusive: dict[str, ScopeLayer] | None = None,
    ) -> None:
        if not system_id.strip() or not task_id.strip() or not agents:
            raise ValueError("Non-empty system/task and agents are required")
        if any(not agent.strip() for agent in agents) or len(set(agents)) != len(agents):
            raise ValueError("Agent IDs must be non-empty and unique")
        if set(exclusive or {}) - set(agents):
            raise ValueError("Exclusive scope references an unknown agent")
        self._identity = {"system_id": system_id, "task_id": task_id}
        self._agents = frozenset(agents)
        self._shared = (shared or ScopeLayer()).model_copy(deep=True)
        self._exclusive = deepcopy(exclusive or {})
        # Validate all configurations before dispatch can begin.
        for agent in agents:
            self._resolve(agent)

    def _resolve(
        self, agent_id: str
    ) -> tuple[dict[str, Any], list[Callable[[DecisionContext], Decision]]]:
        if agent_id not in self._agents:
            raise ValueError("Unknown agent identity")
        layers = [self._shared, self._exclusive.get(agent_id, ScopeLayer())]
        values: dict[str, Any] = {}
        goals: list[str] = []
        checks = []
        for layer in layers:
            if layer.context is not None:
                if layer.context.goal:
                    goals.append(layer.context.goal)
                for key, value in layer.context.values.items():
                    if key in values and values[key] != value:
                        raise ValueError(f"Conflicting shared/exclusive context key: {key}")
                    values[key] = deepcopy(value)
            if layer.guardrails is not None:
                checks.append(layer.guardrails.checker())
        return {**self._identity, "agent_id": agent_id, "goals": goals, "values": values}, checks

    def bind(
        self, agent_id: str, *, on_sidecar_failure: SidecarFailureMode, mode: SidecarMode = "govern"
    ) -> BoundAgent:
        """Bind trusted identity, context and mandatory guardrails to a Sidecar."""
        payload, checks = self._resolve(agent_id)
        goal = "\n".join(payload["goals"])
        sidecar = Sidecar(
            on_sidecar_failure=on_sidecar_failure,
            mode=mode,
            mandatory_checks=checks,
            context_metadata={
                "sidecar.scope": {**self._identity, "agent_id": agent_id},
                "sidecar.context": payload["values"],
            },
            roles=("policy", "risk", "intent_guardian"),
            intent=IntentGuardian(IntentEnvelope(goal=goal, requested_by=Requester(id="harness"))),
            runtime=TaskRuntime(
                task_id=str(uuid5(NAMESPACE_URL, json.dumps([*self._identity.values(), agent_id])))
            ),
        )
        return BoundAgent(sidecar, payload)
