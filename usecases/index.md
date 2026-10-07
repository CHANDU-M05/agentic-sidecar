# Agentic Sidecar Use Cases

Practical, end-to-end walkthroughs for securing autonomous AI agents in real-world environments. Every use case listed here is fully reproducible on your local machine using `agentic-sidecar` v0.6.0.

---

## Catalog

| Use Case | Summary | Difficulty | Capabilities Used |
|---|---|---|---|
| [Prevent Unauthorized High-Value Refunds](prevent-unauthorized-refunds.md) | Intercept agent tool calls and enforce policy limits to block unauthorized monetary refunds in under 10 minutes. | Beginner | [Policy Advisor](https://deepagentlabs.io/agentic-sidecar/docs/features/#policy-advisor) |
| [Run a Governed Customer Support Agent](governed-customer-support-agent.md) | Combine Policy Advisor, Intent Guardian, Risk Evaluator, and Budget Guardrails into a unified synchronous supervision sidecar. | Intermediate | [Policy Advisor](https://deepagentlabs.io/agentic-sidecar/docs/features/#policy-advisor), [Intent Guardian](https://deepagentlabs.io/agentic-sidecar/docs/features/#intent-guardian), [Risk Evaluator](https://deepagentlabs.io/agentic-sidecar/docs/features/#risk-evaluator), [Budget Guardrails](https://deepagentlabs.io/agentic-sidecar/docs/features/#budget-guardrails) |
| [Govern LangGraph Agent Workflows with Sidecar Adapter](govern-langgraph-agent-workflows.md) | Attach Agentic Sidecar's native LangGraph adapter to intercept graph tool invocations and enforce intent constraints in govern mode. | Intermediate | [LangGraph Adapter](https://deepagentlabs.io/agentic-sidecar/docs/integrations/#langgraph), [Intent Guardian](https://deepagentlabs.io/agentic-sidecar/docs/features/#intent-guardian) |

---

## Verified Package Version

All use cases in this catalog have been executed and verified against **`agentic-sidecar` v0.6.0** running on **Python 3.12** on Ubuntu 24.04 LTS.

- **Package Version**: `agentic-sidecar==0.6.0`
- **Verification Date**: 2026-10-07
- **Test Suite Pass Rate**: 100% (218 tests passing, 89% code coverage)

---

## Quick Navigation

- [Go to Agentic Sidecar Documentation](https://deepagentlabs.io/agentic-sidecar/docs/)
- [Return to Agentic Sidecar Product Page](https://deepagentlabs.io/agentic-sidecar/)
