// Agentic Sidecar — Interactive GitHub Pages Script

document.addEventListener('DOMContentLoaded', () => {
  initCopyButton();
  initCodeTabs();
  initInteractiveDemo();
  initNavDropdowns();
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
from agentic_sidecar import Sidecar
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
sidecar = Sidecar(
    on_sidecar_failure="fail_closed", mode="govern",
    intent=guardian, roles=["policy", "risk", "intent_guardian"]
)`,
    budget: `# Budget Guardian Ceiling
from agentic_sidecar import BudgetGuardian, DecisionContext, Sidecar

budget = BudgetGuardian(max_cost=5.00, max_tokens=10000)
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    mode="govern", budget=budget,
    roles=["policy", "risk", "budget"]
)

# Record external usage; Judge usage is connected automatically when configured.
budget.record_invocation(cost=5.00, tokens=1200)
print(sidecar.evaluate(DecisionContext(tool_name="read_order")).status)  # PAUSE
# An attached Govern tool suspends until approval resolution.`,
    govern: `# Handling Govern Mode Interventions
from agentic_sidecar import SidecarBlockedError, SidecarSuspendedError

try:
    agent.invoke({"messages": [("user", "Delete customer record cust_1001")]})
except (SidecarBlockedError, SidecarSuspendedError) as exc:
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
      logMessage(`[SYSTEM] Switched to GOVERN mode (Only ALLOW/WARN proceed; other outcomes resolve or suspend).`);
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
    } else if (mode === 'govern' && !['ALLOW', 'WARN'].includes(act.status)) {
      execOutput = `<div style="color: var(--amber); margin-top: 8px;">⏸ SidecarSuspendedError: Approval or agent-loop resolution required; tool has not executed.</div>`;
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


// Accessible dropdown navigation (Product / Docs / Use Cases)
function initNavDropdowns() {
  const items = Array.from(document.querySelectorAll('.nav-item[data-nav]'));
  if (!items.length) return;

  const setOpen = (item, open) => {
    item.classList.toggle('is-open', open);
    const caret = item.querySelector('.nav-caret');
    if (caret) caret.setAttribute('aria-expanded', open ? 'true' : 'false');
  };
  const closeAll = (except) => items.forEach((it) => { if (it !== except) setOpen(it, false); });

  items.forEach((item) => {
    const caret = item.querySelector('.nav-caret');
    const menu = item.querySelector('.nav-menu');
    if (!caret || !menu) return;

    caret.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = !item.classList.contains('is-open');
      closeAll(item);
      setOpen(item, open);
    });

    // Keyboard: ArrowDown opens the menu and focuses the first item.
    caret.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        closeAll(item);
        setOpen(item, true);
        const first = menu.querySelector('a');
        if (first) first.focus();
      }
    });

    // Keyboard: ArrowUp/ArrowDown move focus between menu links.
    menu.addEventListener('keydown', (e) => {
      const links = Array.from(menu.querySelectorAll('a'));
      const idx = links.indexOf(document.activeElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); links[(idx + 1) % links.length].focus(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); links[(idx - 1 + links.length) % links.length].focus(); }
    });

    // Close the menu when an item is chosen. Navigating links reload anyway,
    // but same-page #anchor links (Product tab) would otherwise leave it open.
    menu.addEventListener('click', (e) => {
      if (e.target.closest('a')) setOpen(item, false);
    });
  });

  // Escape closes the open menu and returns focus to its caret.
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const open = items.find((it) => it.classList.contains('is-open'));
    if (!open) return;
    setOpen(open, false);
    const caret = open.querySelector('.nav-caret');
    if (caret) caret.focus();
  });

  // Click outside any nav item closes all menus.
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-item')) closeAll(null);
  });
}
