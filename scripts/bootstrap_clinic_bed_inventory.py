"""Bootstrap clinic ward/bed inventory in an idempotent way.

This script is intended for tenant operational setup (not schema migration).
It creates missing wards/beds for a single clinic and is safe to re-run.

Default PHC plan:
- Male Ward: 15 beds
- Female Ward: 15 beds
- Labour Ward: 3 beds
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from uuid import UUID

from app.core.database import SessionLocal
from app.models.bed import Bed
from app.models.clinic import Clinic
from app.models.ward import Ward
from app.shared.enums import BedStatus, WardType


@dataclass(frozen=True)
class WardPlan:
    name: str
    ward_type: WardType
    prefix: str
    bed_count: int


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("Value must be >= 0")
    return parsed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Idempotent clinic ward/bed bootstrap"
    )
    parser.add_argument(
        "--clinic-id",
        type=UUID,
        required=True,
        help="Target clinic UUID",
    )
    parser.add_argument(
        "--male-beds",
        type=_non_negative_int,
        default=15,
        help="Beds to ensure in Male Ward (default: 15)",
    )
    parser.add_argument(
        "--female-beds",
        type=_non_negative_int,
        default=15,
        help="Beds to ensure in Female Ward (default: 15)",
    )
    parser.add_argument(
        "--labour-beds",
        type=_non_negative_int,
        default=3,
        help="Beds to ensure in Labour Ward (default: 3)",
    )
    parser.add_argument(
        "--reactivate-inactive",
        action="store_true",
        help="Reactivate matching inactive wards/beds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without committing",
    )
    return parser.parse_args()


def _build_plan(args: argparse.Namespace) -> list[WardPlan]:
    plan = [
        WardPlan(
            name="Male Ward",
            ward_type=WardType.GENERAL,
            prefix="M",
            bed_count=args.male_beds,
        ),
        WardPlan(
            name="Female Ward",
            ward_type=WardType.GENERAL,
            prefix="F",
            bed_count=args.female_beds,
        ),
        WardPlan(
            name="Labour Ward",
            ward_type=WardType.MATERNITY,
            prefix="L",
            bed_count=args.labour_beds,
        ),
    ]
    return [entry for entry in plan if entry.bed_count > 0]


def _build_labels(prefix: str, count: int) -> list[str]:
    width = max(2, len(str(count)))
    return [f"{prefix}-{index:0{width}d}" for index in range(1, count + 1)]


def main() -> None:
    args = _parse_args()
    plan = _build_plan(args)
    db = SessionLocal()
    try:
        clinic = db.query(Clinic).filter(Clinic.id == args.clinic_id).first()
        if clinic is None:
            raise SystemExit(f"Clinic not found: {args.clinic_id}")

        wards_created = 0
        wards_existing = 0
        wards_reactivated = 0
        beds_created = 0
        beds_existing = 0
        beds_reactivated = 0
        skipped_inactive_wards: list[str] = []
        skipped_inactive_beds: list[str] = []

        for ward_plan in plan:
            ward = (
                db.query(Ward)
                .filter(
                    Ward.clinic_id == clinic.id,
                    Ward.name == ward_plan.name,
                )
                .first()
            )

            if ward is None:
                ward = Ward(
                    clinic_id=clinic.id,
                    name=ward_plan.name,
                    ward_type=ward_plan.ward_type,
                    active=True,
                )
                db.add(ward)
                db.flush()
                wards_created += 1
            else:
                wards_existing += 1

            if not ward.active:
                if args.reactivate_inactive:
                    ward.active = True
                    wards_reactivated += 1
                else:
                    skipped_inactive_wards.append(ward_plan.name)
                    continue

            for bed_label in _build_labels(ward_plan.prefix, ward_plan.bed_count):
                bed = (
                    db.query(Bed)
                    .filter(
                        Bed.clinic_id == clinic.id,
                        Bed.ward_id == ward.id,
                        Bed.bed_label == bed_label,
                    )
                    .first()
                )

                if bed is None:
                    db.add(
                        Bed(
                            clinic_id=clinic.id,
                            ward_id=ward.id,
                            bed_label=bed_label,
                            status=BedStatus.AVAILABLE,
                            active=True,
                        )
                    )
                    beds_created += 1
                    continue

                beds_existing += 1
                if not bed.active:
                    if args.reactivate_inactive:
                        bed.active = True
                        beds_reactivated += 1
                    else:
                        skipped_inactive_beds.append(
                            f"{ward_plan.name}:{bed_label}"
                        )

        if args.dry_run:
            db.rollback()
        else:
            db.commit()

        mode = "DRY-RUN" if args.dry_run else "APPLIED"
        print(f"[{mode}] Clinic {clinic.name} ({clinic.id})")
        print(
            f"wards: created={wards_created}, existing={wards_existing}, "
            f"reactivated={wards_reactivated}"
        )
        print(
            f"beds: created={beds_created}, existing={beds_existing}, "
            f"reactivated={beds_reactivated}"
        )

        if skipped_inactive_wards:
            print(
                "inactive wards skipped (use --reactivate-inactive): "
                + ", ".join(skipped_inactive_wards)
            )
        if skipped_inactive_beds:
            preview = ", ".join(skipped_inactive_beds[:6])
            suffix = " ..." if len(skipped_inactive_beds) > 6 else ""
            print(
                "inactive beds kept inactive (use --reactivate-inactive): "
                f"{preview}{suffix}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
