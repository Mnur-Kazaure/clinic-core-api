from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status


def parse_optional_iso_date(value: str | None, *, field_name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must use YYYY-MM-DD format",
        ) from exc
