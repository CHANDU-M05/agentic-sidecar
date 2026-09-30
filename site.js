// Agentic Sidecar — Interactive GitHub Pages Script

document.addEventListener('DOMContentLoaded', () => {
  initCopyButton();
  initCodeTabs();
  initInteractiveDemo();
});

// Copy Install Command
function initCopyButton() {
  const btn = document.getElementById('copy-install');
  if (!btn) return;

  btn.addEventListener('click', () => {
    const codeText = "pip install agentic-sidecar";
    navigator.clipboard.writeText(codeText).then(() => {
      const original = btn.innerHTML;
      btn.innerHTML = '<code>pip install agentic-sidecar</code> <span>✓ Copied!</span>';
      setTimeout(() => {
        btn.innerHTML = original;
      }, 2000);
    });
  });
}

// Code Snippet Tabs
function initCodeTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const codeSnippets = {
    langgraph: `# Wrap tools for LangGraph agent
from agentic_sidecar import Sidecar
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule

sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    mode="govern",
    policy=PolicyAdvisor([PolicyRule(tool="delete_*", effect="deny")])
)

# Intercept tools before passing to react agent
tools = attach(sidecar, [read_order, issue_refund, delete_customer])
agent = create_react_agent(model, tools=tools)`,
    intent: `# Intent Envelope & Constraint Binding
from agentic_sidecar.intent import IntentEnvelope, IntentGuardian, ConstraintBinding, Requester

envelope = IntentEnvelope(
    goal="Assist customer dispute & refund up to $500",
    requested_by=Requester(type="human", id="user_12"),
    constraints={"maximum_refund": 500.0}
)

binding = ConstraintBinding(
    constraint="maximum_refund",
    tool="issue_refund",
    arg_name="amount",
    op="lte",
    severity="BLOCK"
)

guardian = IntentGuardian(envelope, [binding])
sidecar.set_intent(guardian)`,
    budget: `# Budget Guardian Ceiling
from agentic_sidecar.gate import BudgetGuardian

budget = BudgetGuardian(max_cost=5.00, max_tokens=10000)
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    budget=budget,
    roles=["policy", "risk", "budget"]
)

# Returns PAUSE decision when ceiling is reached`,
    govern: `# Handling Govern Mode Block Exceptions
from agentic_sidecar import SidecarBlockedError

try:
    agent.invoke({"messages": [("user", "Delete customer record cust_1001")]})
except SidecarBlockedError as exc:
    print(f"Call prevented: {exc.decision.reason}")
    print(f"Tool attempted: {exc.context.tool_name}")`
  };

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const target = btn.dataset.tab;
      const codeBlock = document.getElementById('code-display');
      if (codeBlock && codeSnippets[target]) {
        codeBlock.textContent = codeSnippets[target];
      }
    });
  });
}

// Interactive Live Demo Simulator
function initInteractiveDemo() {
  let currentMode = 'govern'; // 'observe' or 'govern'
  const modeObserveBtn = document.getElementById('mode-observe');
  const modeGovernBtn = document.getElementById('mode-govern');
  const consoleDisplay = document.getElementById('demo-console');
  const jsonDisplay = document.getElementById('json-console');

  if (!consoleDisplay) return;

  if (modeObserveBtn && modeGovernBtn) {
    modeObserveBtn.addEventListener('click', () => {
      currentMode = 'observe';
      modeObserveBtn.classList.add('active');
      modeGovernBtn.classList.remove('active');
      logMessage(`[SYSTEM] Switched to OBSERVE mode (Decisions logged, execution never stopped).`);
    });

    modeGovernBtn.addEventListener('click', () => {
      currentMode = 'govern';
      modeGovernBtn.classList.add('active');
      modeObserveBtn.classList.remove('active');
      logMessage(`[SYSTEM] Switched to GOVERN mode (BLOCK decisions raise SidecarBlockedError).`);
    });
  }

  // Action Simulations
  const actions = {
    read_order: {
      tool: 'read_order',
      args: { order_id: 'ORD-999' },
      status: 'ALLOW',
      risk: 'LOW',
      reason: 'No policy or risk rules matched. Intent compliant.',
      exec: () => '{"order_id": "ORD-999", "amount": 450.0, "status": "delivered"}'
    },
    refund_250: {
      tool: 'issue_refund',
      args: { order_id: 'ORD-999', amount: 250.0 },
      status: 'ALLOW',
      risk: 'LOW',
      reason: 'Refund $250 <= $500 maximum_refund constraint.',
      exec: () => '{"status": "refund_processed", "refund_amount": 250.0}'
    },
    refund_850: {
      tool: 'issue_refund',
      args: { order_id: 'ORD-999', amount: 850.0 },
      status: 'BLOCK',
      risk: 'HIGH',
      reason: 'Risk Evaluator & Intent Guardian: Refund $850 > $500 max constraint.',
      exec: () => '{"status": "refund_processed", "refund_amount": 850.0}'
    },
    delete_customer: {
      tool: 'delete_customer_record',
      args: { customer_id: 'cust_1001' },
      status: 'BLOCK',
      risk: 'HIGH',
      reason: 'Policy Advisor: Rule delete_* effect=deny matches tool.',
      exec: () => '{"status": "deleted"}'
    },
    over_budget: {
      tool: 'fetch_external_audit_logs',
      args: { range: 'all_history' },
      status: 'PAUSE',
      risk: 'MEDIUM',
      reason: 'Budget Guardian: Cumulative spend $5.20 >= $5.00 limit.',
      exec: () => '{"status": "logs_fetched"}'
    }
  };

  const actBtns = document.querySelectorAll('.act-btn');
  actBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const actKey = btn.dataset.action;
      if (actions[actKey]) {
        simulateAction(actions[actKey], currentMode);
      }
    });
  });

  function logMessage(msg) {
    const line = document.createElement('div');
    line.style.margin = '4px 0';
    line.style.color = 'var(--text-muted)';
    line.textContent = msg;
    consoleDisplay.appendChild(line);
    consoleDisplay.scrollTop = consoleDisplay.scrollHeight;
  }

  function simulateAction(act, mode) {
    const timestamp = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.style.margin = '12px 0';
    entry.style.padding = '12px';
    entry.style.background = 'rgba(255,255,255,0.02)';
    entry.style.borderRadius = '8px';
    entry.style.border = '1px solid rgba(255,255,255,0.06)';

    let badgeClass = 'badge-allow';
    if (act.status === 'BLOCK') badgeClass = 'badge-block';
    if (act.status === 'PAUSE') badgeClass = 'badge-pause';

    let execOutput = '';
    if (mode === 'govern' && act.status === 'BLOCK') {
      execOutput = `<div style="color: var(--red); margin-top: 8px;">🛑 SidecarBlockedError: Call prevented by Sidecar in GOVERN mode.</div>`;
    } else {
      execOutput = `<div style="color: var(--green); margin-top: 8px;">✓ Tool Executed: ${act.exec()}</div>`;
    }

    entry.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span class="verdict-badge ${badgeClass}">[${mode.toUpperCase()}] ${act.status}</span>
        <span style="color: var(--text-dim); font-size: 11px;">${timestamp}</span>
      </div>
      <div style="margin-top: 8px; color: var(--cyan); font-weight: 600;">tool: ${act.tool}(${JSON.stringify(act.args)})</div>
      <div style="color: var(--text-muted); font-size: 12px; margin-top: 4px;">Reason: ${act.reason}</div>
      ${execOutput}
    `;

    consoleDisplay.appendChild(entry);
    consoleDisplay.scrollTop = consoleDisplay.scrollHeight;

    // Update JSON inspector tab
    if (jsonDisplay) {
      jsonDisplay.textContent = JSON.stringify({
        mode: mode,
        decision: {
          status: act.status,
          risk: act.risk,
          reason: act.reason,
          decision_point: "tool_call",
          trigger_details: { tool_name: act.tool, arguments: act.args }
        },
        context: {
          tool_name: act.tool,
          tool_args: act.args,
          intent: { goal: "Customer Support Governance", constraints: { maximum_refund: 500 } }
        }
      }, null, 2);
    }
  }
}
