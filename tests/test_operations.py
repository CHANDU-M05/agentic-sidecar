"""Real dispatch, persistence and authenticated task operator acceptance tests."""

import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError

import pytest
from typer.testing import CliRunner

from agentic_sidecar import (
    Decision,
    DecisionContext,
    EventJournal,
    OperatorServer,
    Sidecar,
    SidecarBlockedError,
    SidecarSuspendedError,
    TaskRuntime,
)
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.cli.main import app
from agentic_sidecar.gate.escalation import ApprovalAction, ApprovalResponse
from agentic_sidecar.intent.alignment import IntentGuardian
from agentic_sidecar.intent.envelope import IntentEnvelope
from agentic_sidecar.operations.client import request

TOKEN = "test-operator-secret-" + "x" * 32


def make_task(**kwargs):
    runtime = kwargs.pop("runtime", TaskRuntime(approval_timeout=3))
    sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern", runtime=runtime, **kwargs)
    return sidecar, runtime


def wait_pending(runtime):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        snapshot = runtime.snapshot()
        if snapshot["pending"]:
            return snapshot["pending"][0]["decision_id"]
        time.sleep(0.005)
    pytest.fail("No runtime approval appeared")


def test_lifecycle_and_deep_immutable_snapshots(tmp_path):
    path = tmp_path / "audit.jsonl"
    journal = EventJournal("task-a", path)
    sidecar, runtime = make_task(runtime=TaskRuntime(journal=journal))
    calls = []

    def read(value):
        calls.append(value)
        return value

    wrapped = attach(sidecar, [read])[0]
    assert wrapped({"nested": [1]}) == {"nested": [1]}
    events = journal.export()
    assert [e["kind"] for e in events] == ["proposed", "decision", "executed", "completed"]
    decision_id = events[1]["payload"]["decision"]["decision_id"]
    assert events[2]["payload"]["decision_id"] == decision_id
    calls[0]["nested"].append(2)
    events[0]["payload"]["context"]["tool_args"]["value"]["nested"].append(3)
    assert journal.export()[0]["payload"]["context"]["tool_args"]["value"] == {"nested": [1]}
    assert EventJournal("task-a", path).export() == journal.export()
    assert runtime.snapshot()["completed"] == 1
    with pytest.raises(ValueError, match="task"):
        EventJournal("wrong-task", path)
    rows = path.read_text().splitlines()
    changed = json.loads(rows[0])
    changed["payload"]["context"]["tool_name"] = "altered"
    path.write_text(json.dumps(changed) + "\n" + "\n".join(rows[1:]) + "\n")
    with pytest.raises(ValueError, match="chain"):
        EventJournal("task-a", path)


@pytest.mark.parametrize(
    "action,status",
    [("approve_once", "completed"), ("reject", "BLOCK"), ("ask_agent_to_replan", "REPLAN")],
)
def test_real_paused_action_over_http(action, status):
    sidecar, runtime = make_task()
    sidecar.escalation_handler = runtime
    sidecar.before_tool_call(lambda context: Decision(status="PAUSE", risk="LOW", reason="Review"))
    calls = []
    wrapped = attach(sidecar, [lambda: calls.append("effect")])[0]
    with (
        OperatorServer(runtime, token=TOKEN, actor="operator") as server,
        ThreadPoolExecutor() as pool,
    ):
        future = pool.submit(wrapped)
        decision_id = wait_pending(runtime)
        assert calls == []
        assert request(server.url, TOKEN, "/status")["paused"]
        request(server.url, TOKEN, "/approval", {"decision_id": decision_id, "action": action})
        if action == "approve_once":
            future.result(timeout=3)
            assert calls == ["effect"]
        else:
            with pytest.raises((SidecarBlockedError, SidecarSuspendedError)) as exc:
                future.result(timeout=3)
            assert exc.value.decision.status == status
            assert calls == []
        events = request(server.url, TOKEN, "/events")
        approval = next(e for e in events if e["kind"] == "approval")
        assert approval["payload"]["actor"] == "operator"
        resolved = [e for e in events if e["kind"] == "decision"][-1]
        assert resolved["payload"]["decision"]["causal_link"] == decision_id
        with pytest.raises(HTTPError) as exc:
            request(server.url, TOKEN, "/approval", {"decision_id": decision_id, "action": action})
        assert exc.value.code == 400


def test_http_authentication_isolation_and_cli(monkeypatch):
    sidecar, runtime = make_task()
    attach(sidecar, [lambda: 1])[0]()
    with OperatorServer(runtime, token=TOKEN, actor="operator") as server:
        for token in ("", "wrong"):
            with pytest.raises(HTTPError) as exc:
                request(server.url, token, "/control", {"action": "stop"})
            assert exc.value.code == 401
        with pytest.raises(HTTPError) as exc:
            request(server.url.replace(runtime.task_id, "other-task"), TOKEN, "/status")
        assert exc.value.code == 404
        monkeypatch.setenv("SIDECAR_OPERATOR_TOKEN", TOKEN)
        result = CliRunner().invoke(app, ["status", "--endpoint", server.url, "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["status"]["completed"] == 1
        assert len(data["events"]) == 4
        result = CliRunner().invoke(app, ["control", "stop", "--endpoint", server.url])
        assert result.exit_code == 0, result.output
        assert runtime.snapshot()["stopped"]


def test_stop_invalidates_queued_decisions_retries_and_requires_restart():
    sidecar, runtime = make_task()
    context = DecisionContext(tool_name="read")
    decision = sidecar.evaluate(context)
    receipt = runtime.control("stop", "operator")
    assert receipt["effective_at"]
    assert receipt["access_revocation"] == "not_configured"
    with pytest.raises(SidecarBlockedError):
        runtime.dispatch(context, decision)
    for _ in range(3):
        with pytest.raises(SidecarBlockedError):
            attach(sidecar, [lambda: None])[0]()
    with pytest.raises(ValueError):
        runtime.control("resume", "operator")
    runtime.control("restart", "operator")
    with pytest.raises(SidecarBlockedError):
        runtime.dispatch(context, decision)
    attach(sidecar, [lambda: None])[0]()
    assert runtime.snapshot()["completed"] == 1


def test_stop_during_running_call_records_completion_and_revocation():
    started, finish = threading.Event(), threading.Event()
    revoked = []
    runtime = TaskRuntime(revokers={"gateway": lambda task: revoked.append(task) or True})
    sidecar, runtime = make_task(runtime=runtime)

    def tool():
        started.set()
        assert finish.wait(3)

    with ThreadPoolExecutor() as pool:
        future = pool.submit(attach(sidecar, [tool])[0])
        assert started.wait(3)
        receipt = runtime.control("stop", "operator")
        assert len(receipt["running"]) == 1
        assert receipt["access_revocation"] == "acknowledged"
        assert revoked == [runtime.task_id]
        with pytest.raises(ValueError):
            runtime.control("restart", "operator")
        finish.set()
        future.result(timeout=3)
    assert runtime.snapshot()["completed"] == 1
    assert runtime.snapshot()["stopped"]


def test_stop_revocation_failure_blocks_restart_and_sink_failure_latches(tmp_path):
    sidecar, runtime = make_task(runtime=TaskRuntime(revokers={"gateway": lambda task: False}))
    assert runtime.control("stop", "operator")["access_revocation"] == "partial_failure"
    with pytest.raises(ValueError):
        runtime.control("restart", "operator")
    runtime.journal.path = tmp_path / "missing" / "audit.jsonl"
    assert runtime.control("stop", "operator")["audit_error"] == "FileNotFoundError"
    assert sidecar.stopped
    with pytest.raises(SidecarBlockedError):
        attach(sidecar, [lambda: None])[0]()


def test_concurrent_proposals_cannot_dispatch_after_acknowledged_stop():
    sidecar, runtime = make_task()
    started = threading.Barrier(9)
    release = threading.Event()
    effects = []

    def evaluate(context):
        started.wait(timeout=3)
        assert release.wait(3)
        return Decision(status="ALLOW", risk="LOW", reason="Allowed")

    sidecar.before_tool_call(evaluate)
    tool = attach(sidecar, [lambda: effects.append(1)])[0]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(tool) for _ in range(8)]
        started.wait(timeout=3)
        runtime.control("stop", "operator")
        release.set()
        for future in futures:
            with pytest.raises(SidecarBlockedError):
                future.result(timeout=3)
    assert effects == []
    assert runtime.snapshot()["executed"] == 0


def test_pause_resume_and_consumed_decisions():
    sidecar, runtime = make_task()
    runtime.control("pause", "operator")
    with pytest.raises(SidecarSuspendedError):
        attach(sidecar, [lambda: None])[0]()
    runtime.control("resume", "operator")
    context = DecisionContext(tool_name="read")
    decision = sidecar.evaluate(context)
    invocation = runtime.dispatch(context, decision)
    runtime.complete(invocation)
    with pytest.raises(SidecarBlockedError):
        runtime.dispatch(context, decision)


def test_modify_intent_invalidates_verdicts_and_records_actor():
    guardian = IntentGuardian(IntentEnvelope(goal="Read account", requested_by={"id": "u"}))
    sidecar, runtime = make_task(intent=guardian, roles=["intent_guardian"])
    context = DecisionContext(tool_name="read")
    decision = sidecar.evaluate(context)
    envelope = guardian.envelope.model_dump(mode="json")
    envelope["goal"] = "Read another account"
    runtime.modify_intent(envelope, "operator")
    assert runtime.snapshot()["objective"] == envelope["goal"]
    with pytest.raises(SidecarBlockedError):
        runtime.dispatch(context, decision)
    event = runtime.journal.export()[-1]
    assert event["kind"] == "intent_modified"
    assert event["payload"]["actor"] == "operator"


def test_restore_never_automatically_resumes(tmp_path):
    journal = EventJournal("task", tmp_path / "audit.jsonl")
    first, runtime = make_task(runtime=TaskRuntime(journal=journal))
    attach(first, [lambda: 1])[0]()
    second, restored = make_task(runtime=TaskRuntime(journal=EventJournal("task", journal.path)))
    with pytest.raises(SidecarBlockedError):
        attach(second, [lambda: 1])[0]()
    assert restored.snapshot()["completed"] == 1


def test_async_success_failure_and_cancellation_are_execution_evidence():
    sidecar, runtime = make_task()

    async def success():
        return 1

    async def failure():
        raise RuntimeError("tool failed")

    async def cancelled():
        raise asyncio.CancelledError()

    async def run():
        assert await attach(sidecar, [success])[0]() == 1
        with pytest.raises(RuntimeError):
            await attach(sidecar, [failure])[0]()
        with pytest.raises(asyncio.CancelledError):
            await attach(sidecar, [cancelled])[0]()

    asyncio.run(run())
    kinds = [e["kind"] for e in runtime.journal.export()]
    assert kinds.count("executed") == 3
    assert kinds.count("completed") == 1
    assert kinds.count("failed") == 2
    assert runtime.snapshot()["running"] == []


def test_approval_timeout_never_fail_opens():
    runtime = TaskRuntime(approval_timeout=0.01)
    sidecar = Sidecar(
        on_sidecar_failure="fail_open", mode="govern", runtime=runtime, escalation_handler=runtime
    )
    sidecar.before_tool_call(lambda context: Decision(status="PAUSE", risk=None, reason="Review"))
    effects = []
    with pytest.raises(SidecarSuspendedError):
        attach(sidecar, [lambda: effects.append(1)])[0]()
    assert effects == []
    assert runtime.snapshot()["pending"] == []


def test_plan_parent_correlation_and_policy_version():
    sidecar, runtime = make_task()
    plan = sidecar.evaluate_plan([{"tool_name": "read", "arguments": {}}])
    context = DecisionContext(
        tool_name="read", parent_decision_id=plan.decision_id, parent_plan_step=0
    )
    decision = sidecar.evaluate(context)
    assert decision.causal_link == plan.decision_id
    payload = runtime.journal.export()[-1]["payload"]
    assert payload["parent_plan_step"] == 0
    assert len(payload["policy_version"]) == 64
    assert payload["rationale"]["findings"]["policy"]["effect"] == "allow"


@pytest.mark.parametrize(
    "endpoint",
    ["https://example.com/tasks/a", "http://localhost/tasks/a", "http://127.0.0.1/tasks/a?token=x"],
)
def test_client_rejects_nonlocal_or_query_endpoints(endpoint):
    with pytest.raises(ValueError):
        request(endpoint, TOKEN, "/status")


def test_stop_cancels_owned_async_tool_and_preserves_prior_side_effects():
    sidecar, runtime = make_task()
    effects = []

    async def run():
        started = asyncio.Event()

        async def tool():
            effects.append("already happened")
            started.set()
            await asyncio.Event().wait()
            effects.append("must not happen")

        task = asyncio.create_task(attach(sidecar, [tool])[0]())
        await asyncio.wait_for(started.wait(), timeout=3)
        receipt = await asyncio.to_thread(runtime.control, "stop", "operator")
        assert list(receipt["cancellations"].values()) == ["requested"]
        with pytest.raises(asyncio.CancelledError):
            await task
        assert effects == ["already happened"]
        assert runtime.snapshot()["running"] == []

    asyncio.run(run())


def test_restored_partial_revocation_and_inflight_cannot_restart(tmp_path):
    journal = EventJournal("task", tmp_path / "audit.jsonl")
    sidecar, runtime = make_task(
        runtime=TaskRuntime(journal=journal, revokers={"gateway": lambda task: False})
    )
    context = DecisionContext(tool_name="read")
    runtime.dispatch(context, sidecar.evaluate(context))
    runtime.control("stop", "operator")
    restored_sidecar, restored = make_task(
        runtime=TaskRuntime(journal=EventJournal("task", journal.path))
    )
    assert restored.snapshot()["running"]
    assert restored.snapshot()["revocation_failed"]
    with pytest.raises(ValueError):
        restored.control("restart", "operator")
    assert restored_sidecar.runtime is restored


def test_revoked_harness_rejects_retry_sessions_and_delegated_task_access():
    task_access = {"root": True, "session": True, "delegated": True}

    def revoke(task):
        for identity in task_access:
            task_access[identity] = False
        return not any(task_access.values())

    sidecar, runtime = make_task(runtime=TaskRuntime(revokers={"issuer": revoke}))
    runtime.control("stop", "operator")
    for identity in ("root", "session", "delegated"):
        for _ in range(3):
            assert task_access[identity] is False
            with pytest.raises(SidecarBlockedError):
                attach(sidecar, [lambda: None])[0]()


def test_live_narration_separates_blocked_proposals_from_completed_calls():
    from agentic_sidecar.status.live import narrate_status

    sidecar, runtime = make_task()
    attach(sidecar, [lambda: 1])[0]()
    sidecar.before_tool_call(lambda context: Decision(status="BLOCK", risk="HIGH", reason="Denied"))
    with pytest.raises(SidecarBlockedError):
        attach(sidecar, [lambda: 2])[0]()
    text = narrate_status(runtime.snapshot())
    assert "COMPLETED:" in text
    assert "BLOCKED:" in text
    assert "Executed: 1; completed: 1" in text
    assert runtime.task_id in text


def test_remote_stop_approval_latches_and_revokes_before_other_dispatch():
    acknowledgements = []
    runtime = TaskRuntime(revokers={"issuer": lambda task: acknowledgements.append(task) or True})
    sidecar, runtime = make_task(runtime=runtime)
    sidecar.escalation_handler = runtime
    sidecar.before_tool_call(lambda context: Decision(status="PAUSE", risk=None, reason="Review"))
    effects = []
    with ThreadPoolExecutor() as pool:
        future = pool.submit(attach(sidecar, [lambda: effects.append(1)])[0])
        decision_id = wait_pending(runtime)
        runtime.approve(ApprovalResponse(decision_id, ApprovalAction.STOP_AGENT), "operator")
        with pytest.raises(SidecarBlockedError):
            future.result(timeout=3)
    assert effects == []
    assert acknowledgements == [runtime.task_id]
    stop = next(e for e in runtime.journal.export() if e["kind"] == "stop_acknowledged")
    assert stop["payload"]["actor"] == "operator"


def test_remote_modify_intent_reevaluates_and_invalidates_other_verdicts():
    guardian = IntentGuardian(IntentEnvelope(goal="Old goal", requested_by={"id": "u"}))
    sidecar, runtime = make_task(intent=guardian, roles=["intent_guardian"])
    sidecar.escalation_handler = runtime
    sidecar.before_tool_call(
        lambda context: Decision(
            status="PAUSE" if context.intent.goal == "Old goal" else "ALLOW",
            risk="LOW",
            reason="Goal review",
        )
    )
    effects = []
    with ThreadPoolExecutor() as pool:
        future = pool.submit(attach(sidecar, [lambda: effects.append(1)])[0])
        decision_id = wait_pending(runtime)
        envelope = guardian.envelope.model_dump(mode="json")
        envelope["goal"] = "New goal"
        runtime.approve(
            ApprovalResponse(decision_id, ApprovalAction.MODIFY_INTENT, envelope), "operator"
        )
        future.result(timeout=3)
    assert effects == [1]
    assert runtime.snapshot()["objective"] == "New goal"
    decisions = [e for e in runtime.journal.export() if e["kind"] == "decision"]
    assert decisions[-1]["payload"]["decision"]["causal_link"] == decision_id


def test_dispatch_refuses_unresolved_and_forged_verdicts():
    sidecar, runtime = make_task()
    sidecar.before_tool_call(lambda context: Decision(status="BLOCK", risk="HIGH", reason="Denied"))
    context = DecisionContext(tool_name="read")
    decision = sidecar.evaluate(context)
    with pytest.raises(SidecarBlockedError):
        runtime.dispatch(context, decision)
    forged = decision.model_copy(update={"status": "ALLOW"})
    with pytest.raises(SidecarBlockedError):
        runtime.dispatch(context, forged)


def test_connected_follow_reads_only_new_events(monkeypatch):
    sidecar, runtime = make_task()
    attach(sidecar, [lambda: 1])[0]()
    sleeps = []

    def refresh_sleep(interval):
        sleeps.append(interval)
        if len(sleeps) == 1:
            attach(sidecar, [lambda: 2])[0]()
        else:
            raise KeyboardInterrupt

    monkeypatch.setenv("SIDECAR_OPERATOR_TOKEN", TOKEN)
    with OperatorServer(runtime, token=TOKEN, actor="operator") as server:
        monkeypatch.setattr("agentic_sidecar.cli.main.time.sleep", refresh_sleep)
        result = CliRunner().invoke(app, ["status", "--endpoint", server.url, "--follow", "--json"])
    assert result.exit_code == 0, result.output
    decoder = json.JSONDecoder()
    first, end = decoder.raw_decode(result.output)
    second, _ = decoder.raw_decode(result.output[end:].lstrip())
    assert first["status"]["completed"] == 1
    assert second["status"]["completed"] == 2
    assert len(first["events"]) == len(second["events"]) == 4
    assert second["events"][0]["sequence"] == 5


def test_http_rejects_cross_origin_and_shell_contains_no_task_data():
    from urllib.request import Request, urlopen

    sidecar, runtime = make_task()
    with OperatorServer(runtime, token=TOKEN, actor="operator") as server:
        with urlopen(server.url) as response:
            html = response.read().decode()
        assert "Sidecar Control Room" in html
        assert TOKEN not in html
        assert runtime.task_id not in html
        req = Request(
            server.url + "/control",
            data=b'{"action":"stop"}',
            headers={"Authorization": "Bearer " + TOKEN, "Origin": "http://attacker.test"},
        )
        with pytest.raises(HTTPError) as exc:
            urlopen(req)
        assert exc.value.code == 403
        assert not runtime.snapshot()["stopped"]


@pytest.mark.parametrize("failure_mode", ["fail_open", "fail_closed"])
def test_broken_sink_respects_failure_policy_without_bypassing_stop(tmp_path, failure_mode):
    journal = EventJournal("task", tmp_path / "missing" / "audit.jsonl")
    runtime = TaskRuntime(journal=journal)
    sidecar = Sidecar(on_sidecar_failure=failure_mode, mode="govern", runtime=runtime)
    effects = []
    tool = attach(sidecar, [lambda: effects.append(1)])[0]
    if failure_mode == "fail_open":
        tool()
        assert effects == [1]
        assert runtime.snapshot()["completed"] == 1
        assert runtime.snapshot()["audit_errors"]
    else:
        with pytest.raises(SidecarBlockedError):
            tool()
        assert effects == []
    assert runtime.control("stop", "operator")["audit_error"] == "FileNotFoundError"
    with pytest.raises(SidecarBlockedError):
        tool()


def test_operator_stop_in_observe_prevents_evaluator_and_tool_calls():
    sidecar = Sidecar(on_sidecar_failure="fail_open", mode="observe")
    evaluations = []
    effects = []
    sidecar.before_tool_call(
        lambda context: (
            evaluations.append(1)
            or Decision(
                status="ALLOW",
                risk="LOW",
                reason="Allowed",
            )
        )
    )
    sidecar.runtime.control("stop", "operator")
    with pytest.raises(SidecarBlockedError):
        attach(sidecar, [lambda: effects.append(1)])[0]()
    assert evaluations == effects == []


def test_client_does_not_forward_operator_token_through_redirects():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Redirect(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "http://example.invalid/collect-token")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        with pytest.raises(HTTPError) as exc:
            request(f"http://127.0.0.1:{server.server_port}/tasks/a", TOKEN, "/status")
        assert exc.value.code == 302
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_audit_failure_cannot_prevent_emergency_access_revocation(tmp_path):
    revoked = []
    runtime = TaskRuntime(
        journal=EventJournal("task", tmp_path / "missing" / "audit.jsonl"),
        revokers={"issuer": lambda task: revoked.append(task) or True},
    )
    sidecar, runtime = make_task(runtime=runtime)
    receipt = runtime.control("stop", "operator")
    assert receipt["audit_error"] == "FileNotFoundError"
    assert receipt["access_revocation"] == "acknowledged"
    assert revoked == [runtime.task_id]
    assert sidecar.stopped
