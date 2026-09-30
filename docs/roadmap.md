# Roadmap

This page documents **planned** capabilities that are not yet implemented. Nothing on this page should be treated as a committed delivery date.

For implemented capabilities, see [Features](features.md).

---

## v0.7 — Control Room & Live Status

- **Live agent connection for CLI:** `agentic-sidecar status --follow` will connect to a running `Sidecar` instance via IPC/HTTP rather than creating a demo narrator.
- **AgenticLens integration:** Forward `Decision` events as spans to AgenticLens for unified tracing across the DeepAgentLabs stack.
- **Persistent audit log:** Option to write `sidecar.decisions` to a SQLite database or JSONL file on disk.

---

## v0.8 — LLM-Backed Risk and Critic

- **LLM-based Risk Evaluator:** Small local model option for semantic risk classification beyond tool name and argument patterns.
- **LLM-backed Critic Evaluator:** Full model-based assumption checking rather than heuristic rule matching.
- **LLM-backed Plan Evaluator:** Model reasoning over multi-step plans for unnecessary or unsafe sequences.

---

## v0.9 — Authority Enforcement

- **`IntentEnvelope.authority` binding:** Enforce the `authority` dict (e.g. `{"can_delete": False}`) against tool calls, with a defined `AuthorityBinding` shape parallel to `ConstraintBinding`.
- **Multi-agent boundary enforcement:** Documentation and tested adapter patterns for multi-agent topologies (supervisor + worker).

---

## v1.0 — Stability and Ecosystem

- **API stability guarantee:** Public API frozen until v2.0.
- **Automatic budget tracking:** Extract cost/token data from LangGraph callbacks, OpenAI usage metadata, and Anthropic response headers — removing the need to call `record_invocation()` manually.
- **Agentic Chaos integration:** Receive chaos signals (latency injection, tool failure simulation) and factor them into risk decisions.
- **AI Operations Spec alignment:** Publish `IntentEnvelope` as a versioned schema aligned with the AIOS operational-intent standard.

---

## Cross-package dependencies

| Capability | Depends on |
|---|---|
| AgenticLens trace forwarding | [AgenticLens](https://deepagentlabs.io/agenticlens/) v0.2+ |
| Agentic Chaos integration | [agentic-chaos](https://deepagentlabs.io/agentic-chaos/) v0.1+ |
| MCP tool call interception | [deep-agenticcore-mcp](https://deepagentlabs.io/deep-agenticcore-mcp/) v0.1+ |

---

> **Note:** This roadmap reflects intent as of v0.6.0. Priorities may shift based on real-world usage feedback. Contributions to any planned capability are welcome — see [CONTRIBUTING.md](https://github.com/DeepAgentLabs/agentic-sidecar/blob/main/CONTRIBUTING.md).
