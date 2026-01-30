# app/core/middleware.py
import json
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


def _contains_break_glass(payload: Any) -> bool:
    if isinstance(payload, dict):
        if "break_glass" in payload:
            return True
        return any(_contains_break_glass(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_contains_break_glass(item) for item in payload)
    return False


async def reject_break_glass_on_write(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if "break_glass" in request.query_params:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Break-glass not allowed on write operations"},
            )
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            body = await request.body()
            if body:
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    payload = None
                if payload is not None and _contains_break_glass(payload):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "Break-glass not allowed on write operations"},
                    )
            request._body = body
    return await call_next(request)
