"""Authenticated client for the documented loopback operator protocol."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def request(endpoint: str, token: str, route: str, body: dict[str, Any] | None = None) -> Any:
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/tasks/")
    ):
        raise ValueError("Expected loopback http://127.0.0.1:PORT/tasks/TASK endpoint")
    req = Request(
        endpoint.rstrip("/") + route,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with build_opener(_NoRedirect()).open(req, timeout=10) as response:
        return json.loads(response.read())
