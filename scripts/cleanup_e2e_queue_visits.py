#!/usr/bin/env python3
"""Cancel active E2E-generated visits via service-layer transitions.

This script is intentionally non-destructive:
- It does not delete patients or visits.
- It only transitions REGISTERED/TRIAGED visits to CANCELLED.
- It uses VisitService so audit history/events are preserved.

Usage:
  PYTHONPATH=. python scripts/cleanup_e2e_queue_visits.py --dry-run
  PYTHONPATH=. python scripts/cleanup_e2e_queue_visits.py --apply
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException

from app.core.database import SessionLocal
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.services.visit.service import VisitService
from app.shared.enums import UserRole, VisitStatus

ACTIVE_STATUSES = [VisitStatus.REGISTERED, VisitStatus.TRIAGED]
ACTOR_ROLE_PRIORITY = [UserRole.RECEPTION, UserRole.CLINIC_ADMIN, UserRole.ADMIN]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cancel active E2E queue visits safely.")
    parser.add_argument(
        "--pattern",
        default="E2E %",
        help="ILIKE pattern for synthetic patient names (default: 'E2E %%').",
    )
    parser.add_argument(
        "--clinic-id",
        default=None,
        help="Optional clinic UUID to scope cleanup.",
    )
    parser.add_argument(
        "--actor-email",
        default=None,
        help="Optional staff email to execute transitions.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum visits to process (default: 1000).",
    )
    parser.add_argument("--apply", action="store_true", help="Apply cancellation transitions.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List candidates only (default mode if --apply not set).",
    )
    return parser.parse_args()


def resolve_actor(db, clinic_id: UUID, actor_email: str | None) -> User | None:
    if actor_email:
        actor = (
            db.query(User)
            .filter(
                User.email == actor_email,
                User.clinic_id == clinic_id,
                User.is_active.is_(True),
            )
            .first()
        )
        return actor

    for role in ACTOR_ROLE_PRIORITY:
        actor = (
            db.query(User)
            .filter(
                User.clinic_id == clinic_id,
                User.role == role,
                User.is_active.is_(True),
            )
            .order_by(User.created_at.asc())
            .first()
        )
        if actor:
            return actor
    return None


def main() -> int:
    args = parse_args()
    apply_mode = bool(args.apply)

    db = SessionLocal()
    try:
        query = (
            db.query(Visit, Patient)
            .join(Patient, Patient.id == Visit.patient_id)
            .filter(
                Patient.full_name.ilike(args.pattern),
                Visit.status.in_(ACTIVE_STATUSES),
            )
            .order_by(Visit.created_at.asc())
            .limit(args.limit)
        )

        if args.clinic_id:
            query = query.filter(Visit.clinic_id == UUID(args.clinic_id))

        candidates = query.all()
        if not candidates:
            print("No active E2E visits found.")
            return 0

        print(f"Found {len(candidates)} candidate active E2E visit(s):")
        by_clinic = defaultdict(int)
        for visit, patient in candidates:
            by_clinic[str(visit.clinic_id)] += 1
            print(
                f"- clinic={visit.clinic_id} visit={visit.id} status={visit.status.value} "
                f"version={visit.version} patient='{patient.full_name}'"
            )

        print("By clinic:")
        for clinic_id, count in by_clinic.items():
            print(f"  {clinic_id}: {count}")

        if not apply_mode:
            print("Dry run complete. Re-run with --apply to cancel these visits.")
            return 0

        service = VisitService(db)
        success = 0
        failed = 0
        skipped = 0
        actor_cache: dict[UUID, User | None] = {}

        for visit, _patient in candidates:
            clinic_id = visit.clinic_id
            if clinic_id not in actor_cache:
                actor_cache[clinic_id] = resolve_actor(db, clinic_id, args.actor_email)

            actor = actor_cache[clinic_id]
            if not actor:
                skipped += 1
                print(
                    f"SKIP visit={visit.id}: no active RECEPTION/CLINIC_ADMIN/ADMIN actor "
                    f"for clinic {clinic_id}."
                )
                continue

            try:
                service.transition_visit(
                    visit_id=visit.id,
                    to_status=VisitStatus.CANCELLED,
                    user=actor,
                    expected_version=visit.version,
                    mode="normal",
                )
                success += 1
                print(f"OK   visit={visit.id} cancelled by {actor.email}")
            except HTTPException as exc:
                failed += 1
                print(f"FAIL visit={visit.id}: {exc.detail}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"FAIL visit={visit.id}: {exc}")

        print(
            f"Completed: success={success}, failed={failed}, skipped={skipped}, total={len(candidates)}"
        )
        return 1 if failed else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
