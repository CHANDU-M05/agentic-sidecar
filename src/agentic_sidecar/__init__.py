"""agentic-sidecar: a companion intelligence and real-time decision
supervision layer for autonomous AI agents.

    The Main Agent acts. The Sidecar observes, thinks, advises, and governs.

0.8.0 adds scoped context/guardrails, native framework adapters and correlated
ecosystem evidence. See docs/scoped-supervision.md and docs/integrations.md.
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
from agentic_sidecar.operations import EventJournal, RuntimeEvent, TaskRuntime
from agentic_sidecar.operations.server import OperatorServer
from agentic_sidecar.scopes import BoundAgent, ContextSpec, GuardrailSpec, ScopedSystem, ScopeLayer
from agentic_sidecar.status import (
    StatusNarrative,
    StatusNarrator,
    ToolCallNarrative,
)

__version__ = "0.8.0"

__all__ = [
    "BoundAgent",
    "ContextSpec",
    "GuardrailSpec",
    "ScopedSystem",
    "ScopeLayer",
    "EventJournal",
    "OperatorServer",
    "RuntimeEvent",
    "TaskRuntime",
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
