# Troubleshooting

Common errors and how to fix them.

---

## `ValueError: on_sidecar_failure=... is invalid`

**Cause:** You constructed `Sidecar` without the required `on_sidecar_failure` argument, or passed an invalid value.

```
ValueError: on_sidecar_failure='auto' is invalid -- it is a required setting with no default
and must be 'fail_open' or 'fail_closed'
```

**Fix:** Always pass `on_sidecar_failure="fail_closed"` (recommended) or `"fail_open"`:

```python
# ✅ Correct
sidecar = Sidecar(on_sidecar_failure="fail_closed", ...)

# ❌ Wrong — no default exists
sidecar = Sidecar(...)
```

---

## `ValueError: intent=... was given but 'intent_guardian' is not in roles`

**Cause:** You passed an `IntentGuardian` to `Sidecar.__init__` or `set_intent()`, but `"intent_guardian"` is not in `sidecar.roles`.

**Fix:** Add `"intent_guardian"` to the `roles` list:

```python
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    intent=guardian,
    roles=["policy", "risk", "intent_guardian"],  # ← must include this
)
```

---

## `ValueError: Unknown role '...'`

**Cause:** You passed an unrecognised string in the `roles` list.

**Fix:** Use only the supported role names: `"policy"`, `"risk"`, `"intent_guardian"`, `"budget"`, `"planner"`, `"critic"`, `"judge"`.

---

## `SidecarBlockedError` raised unexpectedly

**Cause:** Your `Sidecar` is in `mode="govern"` and a tool call matched a `deny` policy rule or exceeded the risk threshold.

**Fix options:**

1. **Switch to Observe mode** temporarily to understand which decisions are being blocked:
   ```python
   sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="observe", ...)
   # Run the agent, then inspect:
   for ctx, dec in sidecar.decisions:
       print(ctx.tool_name, dec.status, dec.reason)
   ```

2. **Adjust the policy or risk rules** that are causing the block.

3. **Handle the exception** at the call site:
   ```python
   from agentic_sidecar import SidecarBlockedError
   try:
       agent.invoke(...)
   except SidecarBlockedError as exc:
       print(f"Blocked: {exc.decision.reason}")
   ```

---

## `NotImplementedError: No EscalationHandler registered`

**Cause:** A `PAUSE` decision was returned (e.g. by Budget Guardian) but no escalation handler is registered.

**Fix:** Register a handler with `@sidecar.on_escalation_required`:

```python
from agentic_sidecar.gate import ApprovalAction, ApprovalResponse

@sidecar.on_escalation_required
def handle_pause(request):
    print(f"PAUSED: {request.reason}")
    # Return an approval action
    return ApprovalResponse(
        decision_id=request.decision_id,
        action=ApprovalAction.APPROVE_ONCE,
    )
```

---

## Budget Guardian never triggers

**Cause:** `BudgetGuardian` is passed to `Sidecar`, but `"budget"` is not in `roles`, so it is never consulted.

**Fix:** Include `"budget"` in the `roles` list:

```python
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    budget=BudgetGuardian(max_cost=5.00),
    roles=["policy", "risk", "budget"],  # ← must include "budget"
)
```

---

## Intent Guardian never triggers

Same pattern as Budget Guardian. You must include `"intent_guardian"` in `roles` *and* call `sidecar.set_intent(guardian)`.

---

## `ImportError: No module named 'langgraph'`

**Cause:** You're using the LangGraph adapter without installing the optional dependency.

**Fix:**
```bash
pip install "agentic-sidecar[langgraph]"
```

---

## Policy rules not matching as expected

**Cause:** `PolicyAdvisor` uses `fnmatch` glob matching, not regex. Common misunderstandings:

- `"delete_*"` matches `delete_customer`, `delete_record` — ✅
- `"delete_*"` does **not** match `"soft_delete"` — ❌
- `"*delete*"` matches both — ✅

**Fix:** Test your patterns with Python's `fnmatch.fnmatch`:

```python
import fnmatch
print(fnmatch.fnmatch("soft_delete", "delete_*"))  # False
print(fnmatch.fnmatch("soft_delete", "*delete*"))  # True
```

---

## Risk rules with argument checks not triggering

**Cause:** The argument must exist in `tool_args` with exactly the name specified in `arg_name`.

**Fix:** Check that the argument name matches exactly. Use `DecisionContext` directly to debug:

```python
from agentic_sidecar import DecisionContext
ctx = DecisionContext(tool_name="issue_refund", tool_args={"amount": 850.0})
result = risk.evaluate(ctx)
print(result.risk, result.reason)
```

---

## `uv sync --extra docs` fails

**Cause:** `mkdocs-material` requires Python ≥ 3.8 and uv ≥ 0.4.

**Fix:**
```bash
pip install uv --upgrade
uv sync --extra docs --python 3.12
```

---

## `mkdocs build --strict` fails with omitted page warning

**Cause:** A file exists in `docs/` but is not listed in `mkdocs.yml` `nav`.

**Fix:** Every markdown file in `docs/` must appear in the `nav` section of `mkdocs.yml`, or the strict build treats it as an error.
