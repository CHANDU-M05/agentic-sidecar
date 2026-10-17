# Shared & Exclusive context and guardrails

Added in **0.8.0**. Configure context/intent only, guardrails only, or both.
Shared layers apply to a declared system/task; Exclusive layers apply to named
agents. The trusted harness creates `ScopedSystem`, binds each agent identity,
then gives that agent only its context payload and supervised tools.

```python
from agentic_sidecar import ContextSpec, GuardrailSpec, ScopedSystem, ScopeLayer
from agentic_sidecar.gate.policy import PolicyRule

system = ScopedSystem(
    system_id="support", task_id="ticket-42", agents=["research", "refund"],
    shared=ScopeLayer(
        context=ContextSpec(goal="Resolve billing", values={"customer": "A100"}),
        guardrails=GuardrailSpec(rules=[PolicyRule(tool="delete_*", effect="deny")]),
    ),
    exclusive={"refund": ScopeLayer(
        context=ContextSpec(goal="Prepare refund", values={"transaction": "T100"}),
        guardrails=GuardrailSpec(rules=[PolicyRule(tool="export_*", effect="deny")]),
    )},
)
refund = system.bind("refund", on_sidecar_failure="fail_closed")
payload = refund.context()
# Explicit transport: host writes the payload into this agent's instructions.
refund.deliver(lambda context: print(context["goals"]))
# Pass refund.sidecar to the selected framework adapter's attach().
```

`ContextSpec` carries goal text and structured values; text is not a deterministic
guardrail. Shared and exclusive goals are preserved in order. Equal duplicate
context keys are accepted; conflicting values are rejected during configuration.
Unknown/duplicate agent identities and unknown exclusive targets are rejected.
A single exclusive layer may be assigned to several agent IDs by the host.

`GuardrailSpec` carries ordered tool policies plus optional constraint values and
`ConstraintBinding` entries. Each layer is evaluated independently: an exclusive
allow cannot override a shared deny, or a weaker local limit override a shared
limit. Missing bound arguments and unknown constraint references cannot silently
pass. All mandatory checks precede custom decision hooks; warnings cannot hide a
later denial. The same checks cover full-plan evaluation. Within each policy
layer, first matching rule wins, as in `PolicyAdvisor`.

Each bound agent has a separate Sidecar/history/runtime. Configuration and returned
payloads are copied. Harness-bound IDs overwrite spoofed reserved decision metadata
(`sidecar.scope`, `sidecar.context`); tool arguments never select an identity.
Audit policy fingerprints include shared and exclusive guardrail configuration.

## Limits and responsibilities

This is explicit host integration, not automatic prompt/memory rewriting. SDK
adapters cover returned tool objects, not every framework action, handoff or
retained raw function. Observe mode records without enforcement; fail_open can
permit calls after evaluation failures. Use Govern/fail_closed for containment.

The configuration object and Sidecar belong to the trusted host. In-process Python
wrappers are not process isolation. Run protected tools and credentials in an
enforcing service under a separate identity; restrict agent access to that service.
The [MCP gateway example](examples.md) demonstrates a separate-process boundary,
server-side checks and an unavailable raw tool; it does not sandbox a hostile OS
user who can inspect gateway memory/files or change its launch environment.

Only assigned exclusive context is returned/injected for each bound agent.
End-to-end private-context isolation across framework memories, model providers,
handoffs, outputs, logs and operator views remains v0.9 validation work. Native
journals include context and decision reasons: store them with task-authorized
access. Revocation/delegated authority and live shared configuration updates are
also v0.9; reconfigure through a new trusted task rather than mutating a live binding.
