from __future__ import annotations

import asyncio
from collections.abc import Callable
from json import dumps

from fastapi import Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool


def encode_sse_event(*, event: str, data: dict, event_id: str | None = None) -> str:
    lines: list[str] = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {dumps(data)}")
    return "\n".join(lines) + "\n\n"


def build_snapshot_stream(
    *,
    request: Request,
    event_name: str,
    load_snapshot: Callable[[], object],
    signature_for: Callable[[object], str],
    payload_for: Callable[[object], dict],
    event_id_for: Callable[[object], str | None],
    poll_interval_seconds: int = 3,
    heartbeat_interval_seconds: int = 15,
) -> StreamingResponse:
    async def event_stream():
        last_signature: str | None = None
        last_keepalive_at = asyncio.get_running_loop().time()

        while True:
            if await request.is_disconnected():
                break

            snapshot = await run_in_threadpool(load_snapshot)
            signature = await run_in_threadpool(signature_for, snapshot)

            if signature != last_signature:
                yield encode_sse_event(
                    event=event_name,
                    data=payload_for(snapshot),
                    event_id=event_id_for(snapshot),
                )
                last_signature = signature
                last_keepalive_at = asyncio.get_running_loop().time()
            elif (
                asyncio.get_running_loop().time() - last_keepalive_at
                >= heartbeat_interval_seconds
            ):
                yield ": keepalive\n\n"
                last_keepalive_at = asyncio.get_running_loop().time()

            await asyncio.sleep(poll_interval_seconds)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
