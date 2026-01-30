import json

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.middleware import reject_break_glass_on_write


async def _run_middleware(method: str, query: str = "", body: dict | None = None):
    payload = b""
    headers = []
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers.append((b"content-type", b"application/json"))

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    scope = {
        "type": "http",
        "method": method,
        "path": "/write",
        "raw_path": b"/write",
        "query_string": query.encode("utf-8"),
        "headers": headers,
        "client": ("test", 123),
        "server": ("test", 80),
        "scheme": "http",
    }
    request = Request(scope, receive)

    async def call_next(_request):
        return JSONResponse({"ok": True})

    return await reject_break_glass_on_write(request, call_next)


@pytest.mark.anyio
async def test_break_glass_rejected_on_write_body():
    response = await _run_middleware("POST", body={"break_glass": True})
    assert response.status_code == 403


@pytest.mark.anyio
async def test_break_glass_rejected_on_write_nested():
    response = await _run_middleware("POST", body={"payload": {"break_glass": True}})
    assert response.status_code == 403


@pytest.mark.anyio
async def test_break_glass_rejected_on_write_query():
    response = await _run_middleware("POST", query="break_glass=true", body={"data": "ok"})
    assert response.status_code == 403


@pytest.mark.anyio
async def test_write_without_break_glass_allowed():
    response = await _run_middleware("POST", body={"data": "ok"})
    assert response.status_code == 200
