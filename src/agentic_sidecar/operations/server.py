"""Loopback HTTP status/events/control interface and embedded Control Room."""

from __future__ import annotations

import hmac
import json
import threading
from contextlib import AbstractContextManager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from agentic_sidecar.gate.escalation import ApprovalAction, ApprovalResponse
from agentic_sidecar.operations.runtime import TaskRuntime

_CONTROL_ROOM = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sidecar Control Room</title>
<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;
background:#111827;color:#e5e7eb}button,input,select,textarea{font:inherit;padding:8px;
margin:4px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#1f2937;padding:16px}
button{cursor:pointer}section{margin:24px 0}label{display:block}</style>
<h1>Sidecar Control Room</h1><p>Task-scoped runtime supervision</p>
<label>Operator token <input id="token" type="password" autocomplete="off"></label>
<button id="connect">Connect</button><span id="message" role="status"></span>
<section id="controls"><button data-action="pause">Pause</button>
<button data-action="resume">Resume</button><button data-action="stop">Stop</button>
<button data-action="restart">Restart</button><button data-action="replan">Ask to replan</button>
<button id="intent">Modify intent</button>
</section><h2>Objective, plan, alignment, risk and budget</h2><pre id="summary"></pre>
<h2>Calls and execution</h2><pre id="calls"></pre><h2>Pending approvals</h2>
<div id="pending"></div><h2>Audit events</h2><pre id="events"></pre>
<script>
let endpoint='',timer;
const $=id=>document.getElementById(id);
async function api(path,body){const r=await fetch(endpoint+path,{method:body?'POST':'GET',
headers:{'Authorization':'Bearer '+$('token').value,'Content-Type':'application/json'},
body:body?JSON.stringify(body):undefined});const data=await r.json();
if(!r.ok)throw Error(data.error||r.status);return data;}
async function refresh(){try{const s=await api('/status');
$('summary').textContent=JSON.stringify({task:s.task_id,mode:s.mode,objective:s.objective,
plan:s.plan,intent:s.intent,alignment:s.alignment,risk:s.risk,budget:s.budget,
paused:s.paused,stopped:s.stopped},null,2);
$('calls').textContent=JSON.stringify({running:s.running,executed:s.executed,
completed:s.completed,decisions:s.decisions},null,2);
$('events').textContent=JSON.stringify(await api('/events'),null,2);
$('pending').replaceChildren();for(const p of s.pending){const box=document.createElement('div');
const text=document.createElement('p');
text.textContent=p.decision_id+': '+p.reason;box.append(text);
for(const action of p.available_actions){const b=document.createElement('button');
b.textContent=action;
b.onclick=async()=>{try{let modified_intent;
if(action==='modify_intent')modified_intent=JSON.parse(prompt('Complete intent envelope JSON',
JSON.stringify(s.intent)));
await api('/approval',{decision_id:p.decision_id,action,modified_intent});
await refresh();}catch(e){$('message').textContent=e.message;}};box.append(b);}
$('pending').append(box);}$('message').textContent='Connected';
}catch(e){$('message').textContent=e.message;}}
$('intent').onclick=async()=>{try{const s=await api('/status');
const intent=JSON.parse(prompt('Complete intent envelope JSON',JSON.stringify(s.intent)));
await api('/intent',{intent});await refresh();}catch(e){$('message').textContent=e.message;}};
$('connect').onclick=async()=>{endpoint=location.pathname.replace(/\\/$/,'');
clearInterval(timer);await refresh();timer=setInterval(refresh,1000);};
for(const b of document.querySelectorAll('[data-action]'))b.onclick=async()=>{
try{await api('/control',{action:b.dataset.action});await refresh();}
catch(e){$('message').textContent=e.message;}};
</script></html>"""


class OperatorServer(AbstractContextManager["OperatorServer"]):
    """Explicit opt-in loopback server; one secret/actor and task per instance.

    The token must have at least 32 characters. All API reads and mutations
    require it. It is never embedded in HTML, URLs or logs. No cross-origin API.
    """

    def __init__(self, runtime: TaskRuntime, *, token: str, actor: str, port: int = 0) -> None:
        if len(token) < 32 or not actor:
            raise ValueError("A token of at least 32 characters and an actor are required")
        self.runtime = runtime
        self.token = token
        self.actor = actor
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                self._handle(False)

            def do_POST(self) -> None:
                self._handle(True)

            def _reply(self, status: int, data: Any, *, html: bool = False) -> None:
                encoded = (data if html else json.dumps(data, allow_nan=False)).encode()
                self.send_response(status)
                self.send_header(
                    "Content-Type", "text/html; charset=utf-8" if html else "application/json"
                )
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; "
                    "script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                    "frame-ancestors 'none'",
                )
                self.end_headers()
                self.wfile.write(encoded)

            def _handle(self, mutation: bool) -> None:
                parsed = urlsplit(self.path)
                prefix = f"/tasks/{owner.runtime.task_id}"
                if parsed.path == prefix and not mutation:
                    self._reply(200, _CONTROL_ROOM, html=True)
                    return
                if not parsed.path.startswith(prefix + "/"):
                    self._reply(404, {"error": "Unknown task"})
                    return
                supplied = self.headers.get("Authorization", "")
                if not hmac.compare_digest(supplied.encode(), ("Bearer " + owner.token).encode()):
                    self._reply(401, {"error": "Operator authentication required"})
                    return
                origin = self.headers.get("Origin")
                if origin and origin != owner.url.split("/tasks/")[0]:
                    self._reply(403, {"error": "Cross-origin access denied"})
                    return
                route = parsed.path[len(prefix) :]
                try:
                    if not mutation:
                        if route == "/status":
                            self._reply(200, owner.runtime.snapshot())
                        elif route == "/events":
                            after = int(parse_qs(parsed.query).get("after", ["0"])[0])
                            self._reply(200, owner.runtime.journal.export(after))
                        else:
                            self._reply(404, {"error": "Unknown endpoint"})
                        return
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 65536:
                        raise ValueError("JSON body must be 1–65536 bytes")
                    body = json.loads(self.rfile.read(size))
                    if not isinstance(body, dict):
                        raise ValueError("JSON object required")
                    if route == "/control":
                        self._reply(200, owner.runtime.control(body["action"], owner.actor))
                    elif route == "/intent":
                        owner.runtime.modify_intent(body["intent"], owner.actor)
                        self._reply(200, {"accepted": True})
                    elif route == "/approval":
                        response = ApprovalResponse(
                            body["decision_id"],
                            ApprovalAction(body["action"]),
                            body.get("modified_intent"),
                            body.get("explanation", ""),
                        )
                        owner.runtime.approve(response, owner.actor)
                        self._reply(200, {"accepted": True})
                    else:
                        self._reply(404, {"error": "Unknown endpoint"})
                except (ValueError, KeyError, TypeError) as exc:
                    self._reply(400, {"error": str(exc)})
                except Exception:
                    self._reply(503, {"error": "Runtime operation failed"})

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self._server.daemon_threads = True
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}/tasks/{self.runtime.task_id}"

    def __enter__(self) -> OperatorServer:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._thread:
            self._server.shutdown()
            self._thread.join()
        self._server.server_close()
