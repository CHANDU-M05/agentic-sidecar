"""`Decision(status, risk, reason)` -- the Decision Gate's output type.

v0.1 shipped `status in {"ALLOW", "BLOCK"}` only. v0.2 adds `WARN` --
Intent Guardian's outcome for a finding that's worth surfacing (e.g. a
stale/expired envelope) but not severe enough to block. v0.4 completes the
seven outcomes from concept.md §15: `CHALLENGE`, `REPLAN`, `PAUSE`, and
`ESCALATE`. See README.md's "How the Decision Gate evaluates a decision"
and ROADMAP.md's build order.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

DecisionStatus = Literal["ALLOW", "WARN", "BLOCK", "CHALLENGE", "REPLAN", "PAUSE", "ESCALATE"]
"""Seven outcomes from concept.md §15, fully implemented as of v0.4:

- ALLOW: proceed without intervention
- WARN: proceed but alert user (intent/policy concern, not blocking)
- BLOCK: hard stop, enforced by adapter (Govern mode only)
- CHALLENGE: Critic found issues; Main Agent must justify before continuing
- REPLAN: Planner/Critic suggests replanning the full task
- PAUSE: escalate to human for approve/reject/modify
- ESCALATE: escalate to human for guidance on task adjustment
"""

RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
"""Risk Evaluator classification (gate/risk.py) -- static rules only in v0.1."""


class Decision(BaseModel):
    """The outcome of a single Decision Gate evaluation for one proposed
    action (tool call).

    `risk` is `None` only on the `on_sidecar_failure` path (core/sidecar.py)
    -- when the Sidecar itself errored before Policy/Risk ever ran, there is
    no risk classification to report, and reporting one would misrepresent
    what actually happened.

    v0.4 adds provenance fields for audit trail: `decision_point` (which
    boundary fired), `trigger_details` (tool/action + arguments), and
    `causal_link` (correlation to prior decisions). Escalation outcomes
    (PAUSE, ESCALATE) may populate `escalation_required`.

    Frozen: a `Decision` is a record of what was decided, not a value meant
    to be mutated after the fact.
    """

    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    status: DecisionStatus
    risk: RiskLevel | None
    reason: str
    decision_point: str | None = None
    trigger_details: dict[str, Any] | None = None
    escalation_required: bool = False
    causal_link: str | None = None
