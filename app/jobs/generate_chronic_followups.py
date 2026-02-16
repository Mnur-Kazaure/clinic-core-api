import argparse
import json
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.services.follow_up_generation_service import ChronicRecallGenerator


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate due chronic recall follow-ups and transition MISSED items.",
    )
    parser.add_argument(
        "--now",
        help="Override current time in ISO-8601 format (UTC if timezone is omitted).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Max due recalls and due scheduled follow-ups processed per run.",
    )
    return parser.parse_args()


def _parse_now(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> None:
    args = _parse_args()
    now = _parse_now(args.now)
    db = SessionLocal()
    try:
        generator = ChronicRecallGenerator(db)
        stats = generator.run_due_generation(now=now, batch_size=args.batch_size)
    finally:
        db.close()
    print(json.dumps(stats, default=str))


if __name__ == "__main__":
    main()
