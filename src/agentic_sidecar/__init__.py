"""agentic-sidecar: a companion intelligence and real-time decision
supervision layer for autonomous AI agents.

    The Main Agent acts. The Sidecar observes, thinks, advises, and governs.

0.6.1 adds governed outcome resolution, local approvals, full-plan review,
optional live Judge SDK providers and validated task usage accounting. See
ROADMAP.md and docs/governance.md for supported scope and acceptance evidence.
"""

from agentic_sidecar.core.context import DecisionContext
from agentic_sidecar.core.decision import Decision, DecisionStatus, RiskLevel
from agentic_sidecar.core.exceptions import SidecarBlockedError, SidecarSuspendedError
from agentic_sidecar.core.provenance import (
    AuditRecord,
    CausalLink,
    DecisionRationale,
    DecisionTrigger,
)
from agentic_sidecar.core.sidecar import Sidecar
from agentic_sidecar.evaluators import (
    AnthropicJudge,
    CriticChallenge,
    CriticEvaluator,
    EvaluatorBase,
    EvaluatorResult,
    JudgeEvaluator,
    JudgeProvider,
    OpenAIJudge,
    PlanEvaluator,
    PlanStep,
)
from agentic_sidecar.gate import (
    ApprovalAction,
    ApprovalResponse,
    BudgetGuardian,
    BudgetResult,
    EscalationHandler,
    EscalationRequest,
)
from agentic_sidecar.status import (
    StatusNarrative,
    StatusNarrator,
    ToolCallNarrative,
)

__version__ = "0.6.1"

__all__ = [
    "MockJudge",
    "AnthropicJudge",
    "ApprovalAction",
    "ApprovalResponse",
    "AuditRecord",
    "BudgetGuardian",
    "BudgetResult",
    "CausalLink",
    "CriticChallenge",
    "CriticEvaluator",
    "Decision",
    "DecisionContext",
    "DecisionRationale",
    "DecisionStatus",
    "DecisionTrigger",
    "EscalationHandler",
    "EscalationRequest",
    "EvaluatorBase",
    "EvaluatorResult",
    "JudgeEvaluator",
    "JudgeProvider",
    "OpenAIJudge",
    "PlanEvaluator",
    "PlanStep",
    "RiskLevel",
    "Sidecar",
    "SidecarBlockedError",
    "SidecarSuspendedError",
    "StatusNarrative",
    "StatusNarrator",
    "ToolCallNarrative",
    "__version__",
]

from agentic_sidecar.evaluators.providers.mock import MockJudge
