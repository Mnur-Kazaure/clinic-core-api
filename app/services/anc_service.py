# app/services/anc_service.py
from datetime import datetime, timezone
import textwrap
from uuid import UUID

from fastapi import HTTPException, status

from app.models.anc_encounter import ANCEncounter
from app.models.clinic import Clinic
from app.models.patient_identity_map import PatientIdentityMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.patient_mrn import PatientMRN
from app.models.pregnancy_episode import PregnancyEpisode
from app.models.pregnancy_previous_pregnancy import PregnancyPreviousPregnancy
from app.models.visit import Visit
from app.models.patient import Patient
from app.services.access_log_service import AccessLogService
from app.shared.enums import (
    MRNStatus,
    PregnancyEpisodeStatus,
    RecordStatus,
    UserRole,
    VisitServiceLine,
    VisitStatus,
)


class ANCService:
    MAX_EXPORT_ENCOUNTERS = 500

    def __init__(self, db):
        self.db = db

    def _get_visit_for_anc(self, *, visit_id: UUID, clinic_id: UUID, actor_id: UUID) -> Visit:
        visit = (
            self.db.query(Visit)
            .filter(
                Visit.id == visit_id,
                Visit.clinic_id == clinic_id,
            )
            .first()
        )
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        if visit.service_line != VisitServiceLine.ANC:
            raise HTTPException(status_code=400, detail="Visit is not ANC")
        if visit.assigned_doctor_id != actor_id:
            raise HTTPException(status_code=403, detail="Visit not assigned to you")
        if visit.status in {VisitStatus.CANCELLED}:
            raise HTTPException(status_code=400, detail="Visit is cancelled")
        return visit

    def create_episode(
        self,
        *,
        clinic_id: UUID,
        patient_id: UUID,
        actor_id: UUID,
        close_existing: bool,
        payload,
    ) -> PregnancyEpisode:
        patient = (
            self.db.query(Patient)
            .filter(Patient.id == patient_id, Patient.clinic_id == clinic_id)
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        existing = (
            self.db.query(PregnancyEpisode)
            .filter(
                PregnancyEpisode.clinic_id == clinic_id,
                PregnancyEpisode.patient_id == patient_id,
                PregnancyEpisode.status == PregnancyEpisodeStatus.ACTIVE,
            )
            .first()
        )
        if existing and not close_existing:
            existing.lmp_date = payload.lmp_date
            existing.edd_date = payload.edd_date
            existing.gravida = payload.gravida
            existing.parity = payload.parity
            existing.booking_reg_no = payload.booking_reg_no
            existing.past_medical_history = payload.past_medical_history
            existing.past_surgical_history = payload.past_surgical_history
            existing.history_present_pregnancy = payload.history_present_pregnancy
            existing.general_exam = payload.general_exam
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        if existing and close_existing:
            existing.status = PregnancyEpisodeStatus.CLOSED
            existing.closed_at = datetime.now(timezone.utc)
            self.db.add(existing)

        episode = PregnancyEpisode(
            clinic_id=clinic_id,
            patient_id=patient_id,
            status=PregnancyEpisodeStatus.ACTIVE,
            lmp_date=payload.lmp_date,
            edd_date=payload.edd_date,
            gravida=payload.gravida,
            parity=payload.parity,
            booking_reg_no=payload.booking_reg_no,
            past_medical_history=payload.past_medical_history,
            past_surgical_history=payload.past_surgical_history,
            history_present_pregnancy=payload.history_present_pregnancy,
            general_exam=payload.general_exam,
            created_by=actor_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(episode)
        self.db.commit()
        self.db.refresh(episode)
        return episode

    def get_active_episode(
        self, *, clinic_id: UUID, patient_id: UUID
    ) -> PregnancyEpisode | None:
        return (
            self.db.query(PregnancyEpisode)
            .filter(
                PregnancyEpisode.clinic_id == clinic_id,
                PregnancyEpisode.patient_id == patient_id,
                PregnancyEpisode.status == PregnancyEpisodeStatus.ACTIVE,
            )
            .first()
        )

    def get_episode(self, *, clinic_id: UUID, episode_id: UUID) -> PregnancyEpisode:
        episode = (
            self.db.query(PregnancyEpisode)
            .filter(
                PregnancyEpisode.id == episode_id,
                PregnancyEpisode.clinic_id == clinic_id,
            )
            .first()
        )
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        return episode

    def add_previous_pregnancy(
        self,
        *,
        clinic_id: UUID,
        episode_id: UUID,
        actor_id: UUID,
        payload,
    ) -> PregnancyPreviousPregnancy:
        episode = self.get_episode(clinic_id=clinic_id, episode_id=episode_id)
        row = PregnancyPreviousPregnancy(
            clinic_id=clinic_id,
            episode_id=episode.id,
            year=payload.year,
            duration=payload.duration,
            antenatal_complications=payload.antenatal_complications,
            labour=payload.labour,
            age_alive=payload.age_alive,
            age_dead=payload.age_dead,
            cause_of_death=payload.cause_of_death,
            created_by=actor_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_previous_pregnancies(
        self, *, clinic_id: UUID, episode_id: UUID
    ) -> list[PregnancyPreviousPregnancy]:
        return (
            self.db.query(PregnancyPreviousPregnancy)
            .filter(
                PregnancyPreviousPregnancy.clinic_id == clinic_id,
                PregnancyPreviousPregnancy.episode_id == episode_id,
            )
            .order_by(PregnancyPreviousPregnancy.created_at.desc())
            .all()
        )

    def get_encounter(
        self, *, clinic_id: UUID, visit_id: UUID, actor_id: UUID
    ) -> ANCEncounter | None:
        self._get_visit_for_anc(visit_id=visit_id, clinic_id=clinic_id, actor_id=actor_id)
        return (
            self.db.query(ANCEncounter)
            .filter(
                ANCEncounter.clinic_id == clinic_id,
                ANCEncounter.visit_id == visit_id,
            )
            .first()
        )

    def upsert_encounter(
        self,
        *,
        clinic_id: UUID,
        visit_id: UUID,
        actor_id: UUID,
        payload,
    ) -> ANCEncounter:
        visit = self._get_visit_for_anc(visit_id=visit_id, clinic_id=clinic_id, actor_id=actor_id)
        episode = self.get_episode(clinic_id=clinic_id, episode_id=payload.episode_id)

        encounter = (
            self.db.query(ANCEncounter)
            .filter(
                ANCEncounter.clinic_id == clinic_id,
                ANCEncounter.visit_id == visit_id,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        if not encounter:
            encounter = ANCEncounter(
                clinic_id=clinic_id,
                visit_id=visit_id,
                episode_id=episode.id,
                recorded_by=actor_id,
                recorded_at=now,
                record_status=RecordStatus.DRAFT,
            )
            self.db.add(encounter)

        if encounter.record_status == RecordStatus.SIGNED:
            raise HTTPException(status_code=409, detail="Encounter already signed")

        encounter.episode_id = episode.id
        encounter.fundus_height = payload.fundus_height
        encounter.presentation_position = payload.presentation_position
        encounter.presenting_part = payload.presenting_part
        encounter.foetal_heart = payload.foetal_heart
        encounter.bp_systolic = payload.bp_systolic
        encounter.bp_diastolic = payload.bp_diastolic
        encounter.urine = payload.urine
        encounter.weight_kg = payload.weight_kg
        encounter.remarks = payload.remarks
        encounter.ref = payload.ref
        encounter.initial = payload.initial

        if payload.action == "SIGN":
            encounter.record_status = RecordStatus.SIGNED
            encounter.signed_at = now
        else:
            encounter.record_status = RecordStatus.DRAFT

        self.db.add(encounter)
        self.db.commit()
        self.db.refresh(encounter)
        return encounter

    def export_episode_pdf(
        self,
        *,
        clinic_id: UUID,
        episode_id: UUID,
        actor,
        purpose_of_use,
        justification: str,
        include_previous_pregnancies: bool = True,
        include_encounters: bool = True,
        include_blank_rows: int = 0,
    ) -> tuple[bytes, str]:
        include_blank_rows = max(0, min(include_blank_rows, 20))
        episode = self.get_episode(clinic_id=clinic_id, episode_id=episode_id)
        canonical_id = self._resolve_canonical_patient_id(
            patient_id=episode.patient_id,
            clinic_id=clinic_id,
        )
        closure_ids = self._resolve_identity_closure(
            canonical_id=canonical_id,
            clinic_id=clinic_id,
        )
        active_visit_id = self._authorize_export_access(
            actor=actor,
            clinic_id=clinic_id,
            identity_closure_ids=closure_ids,
        )

        patient = (
            self.db.query(Patient)
            .filter(Patient.id == episode.patient_id, Patient.clinic_id == clinic_id)
            .first()
        )
        clinic = self.db.query(Clinic).filter(Clinic.id == clinic_id).first()
        if not patient or not clinic:
            raise HTTPException(status_code=404, detail="Episode context not found")

        active_mrn = (
            self.db.query(PatientMRN)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id == canonical_id,
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .first()
        )
        previous = []
        if include_previous_pregnancies:
            previous = (
                self.db.query(PregnancyPreviousPregnancy)
                .filter(
                    PregnancyPreviousPregnancy.clinic_id == clinic_id,
                    PregnancyPreviousPregnancy.episode_id == episode_id,
                )
                .order_by(
                    PregnancyPreviousPregnancy.created_at.asc(),
                    PregnancyPreviousPregnancy.id.asc(),
                )
                .all()
            )
        encounters = []
        if include_encounters:
            encounters = (
                self.db.query(ANCEncounter)
                .filter(
                    ANCEncounter.clinic_id == clinic_id,
                    ANCEncounter.episode_id == episode_id,
                )
                .order_by(ANCEncounter.recorded_at.asc(), ANCEncounter.id.asc())
                .limit(self.MAX_EXPORT_ENCOUNTERS)
                .all()
            )

        access_log = AccessLogService(self.db).log_chart_read(
            actor=actor,
            clinic_id=clinic_id,
            patient_id=canonical_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="ANC",
            extra_payload={
                "episode_id": str(episode.id),
                "patient_id_requested": str(episode.patient_id),
                "patient_id_canonical": str(canonical_id),
                "active_visit_id": str(active_visit_id) if active_visit_id else None,
            },
        )

        lines = self._build_export_lines(
            clinic_name=clinic.name,
            patient=patient,
            episode=episode,
            active_mrn=active_mrn.mrn if active_mrn else None,
            previous_pregnancies=previous,
            encounters=encounters,
            include_blank_rows=include_blank_rows,
            generated_at=datetime.now(timezone.utc),
            access_log_id=str(access_log.id),
        )
        pdf_bytes = self._render_pdf(lines)
        filename = self._build_export_filename(
            patient_id=episode.patient_id,
            mrn=active_mrn.mrn if active_mrn else None,
            generated_at=datetime.now(timezone.utc),
        )
        return pdf_bytes, filename

    def _authorize_export_access(
        self,
        *,
        actor,
        clinic_id: UUID,
        identity_closure_ids: list[UUID],
    ) -> UUID | None:
        if actor.clinic_id != clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")

        if actor.role in {UserRole.RECEPTION, UserRole.CLINIC_ADMIN}:
            return None

        if actor.role == UserRole.CHEW:
            active_visit = (
                self.db.query(Visit)
                .filter(
                    Visit.clinic_id == clinic_id,
                    Visit.patient_id.in_(identity_closure_ids),
                    Visit.assigned_doctor_id == actor.id,
                    Visit.service_line == VisitServiceLine.ANC,
                    Visit.status.notin_([VisitStatus.COMPLETED, VisitStatus.CANCELLED]),
                )
                .order_by(Visit.started_at.desc(), Visit.id.desc())
                .first()
            )
            if not active_visit:
                raise HTTPException(
                    status_code=403,
                    detail="ANC export requires an active ANC visit assigned to you",
                )
            return active_visit.id

        raise HTTPException(
            status_code=403,
            detail="Not authorized to export ANC record",
        )

    def _resolve_canonical_patient_id(self, *, patient_id: UUID, clinic_id: UUID) -> UUID:
        visited = set()
        current = patient_id
        for _ in range(10):
            if current in visited:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Identity mapping cycle detected",
                )
            visited.add(current)
            mapping = (
                self.db.query(PatientIdentityMap)
                .filter(
                    PatientIdentityMap.clinic_id == clinic_id,
                    PatientIdentityMap.from_patient_id == current,
                )
                .first()
            )
            if not mapping:
                return current
            revoked = (
                self.db.query(IdentityMapRevocation)
                .filter(
                    IdentityMapRevocation.clinic_id == clinic_id,
                    IdentityMapRevocation.map_id == mapping.id,
                )
                .first()
            )
            if revoked:
                return current
            current = mapping.to_patient_id
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identity resolution exceeded hop limit",
        )

    def _resolve_identity_closure(self, *, canonical_id: UUID, clinic_id: UUID) -> list[UUID]:
        seen = {canonical_id}
        queue = [canonical_id]
        while queue:
            target = queue.pop()
            mappings = (
                self.db.query(PatientIdentityMap)
                .filter(
                    PatientIdentityMap.clinic_id == clinic_id,
                    PatientIdentityMap.to_patient_id == target,
                )
                .all()
            )
            for mapping in mappings:
                revoked = (
                    self.db.query(IdentityMapRevocation)
                    .filter(
                        IdentityMapRevocation.clinic_id == clinic_id,
                        IdentityMapRevocation.map_id == mapping.id,
                    )
                    .first()
                )
                if revoked:
                    continue
                if mapping.from_patient_id not in seen:
                    seen.add(mapping.from_patient_id)
                    queue.append(mapping.from_patient_id)
        return list(seen)

    def _build_export_filename(
        self,
        *,
        patient_id: UUID,
        mrn: str | None,
        generated_at: datetime,
    ) -> str:
        date_str = generated_at.date().isoformat()
        if mrn and mrn.strip():
            token = mrn.replace(" ", "_")
            return f"ANC_{token}_{date_str}.pdf"
        return f"ANC_ID_{str(patient_id)[:8]}_{date_str}.pdf"

    def _build_export_lines(
        self,
        *,
        clinic_name: str,
        patient: Patient,
        episode: PregnancyEpisode,
        active_mrn: str | None,
        previous_pregnancies: list[PregnancyPreviousPregnancy],
        encounters: list[ANCEncounter],
        include_blank_rows: int,
        generated_at: datetime,
        access_log_id: str,
    ) -> list[str]:
        lines: list[str] = []

        def add_line(text: str = ""):
            wrapped = textwrap.wrap(text, width=105) or [""]
            lines.extend(wrapped)

        add_line(clinic_name)
        add_line("Antenatal Care (ANC) Card - Summary")
        add_line(
            f"Patient: {patient.full_name or '-'} | MRN: {active_mrn or '-'} | DOB: {patient.date_of_birth or '-'} | Phone: {patient.phone_number or '-'}"
        )
        add_line(
            f"Episode: {str(episode.id)[:8]}... | Generated: {generated_at.isoformat()} | Access Log: {access_log_id[:8]}..."
        )
        add_line("-" * 105)
        add_line("Episode Header")
        add_line(
            f"LMP: {episode.lmp_date or '-'} | EDD: {episode.edd_date or '-'} | Gravida: {episode.gravida or '-'} | Parity: {episode.parity or '-'} | Reg No: {episode.booking_reg_no or '-'}"
        )
        add_line(f"Past Medical History: {episode.past_medical_history or '-'}")
        add_line(f"Past Surgical History: {episode.past_surgical_history or '-'}")
        add_line(f"History of Present Pregnancy: {episode.history_present_pregnancy or '-'}")
        add_line(f"General Examination: {episode.general_exam or '-'}")
        add_line("")

        add_line("Previous Pregnancies")
        add_line(
            "Year | Duration | Antenatal Complications | Labour | Age Alive | Age Dead | Cause of Death"
        )
        if previous_pregnancies:
            for row in previous_pregnancies:
                add_line(
                    f"{row.year or '-'} | {row.duration or '-'} | {row.antenatal_complications or '-'} | {row.labour or '-'} | {row.age_alive or '-'} | {row.age_dead or '-'} | {row.cause_of_death or '-'}"
                )
        else:
            add_line("No previous pregnancies recorded.")
        add_line("")

        add_line("ANC Encounters")
        add_line(
            "Date | Fundus | Presentation/Position | Presenting Part | Fetal Heart | BP | Urine | Weight | Remarks | Ref | Initial"
        )
        if encounters:
            for row in encounters:
                bp = (
                    f"{row.bp_systolic or '-'} / {row.bp_diastolic or '-'}"
                    if row.bp_systolic or row.bp_diastolic
                    else "-"
                )
                add_line(
                    f"{row.recorded_at.date()} | {row.fundus_height or '-'} | {row.presentation_position or '-'} | {row.presenting_part or '-'} | {row.foetal_heart or '-'} | {bp} | {row.urine or '-'} | {row.weight_kg or '-'} | {row.remarks or '-'} | {row.ref or '-'} | {row.initial or '-'}"
                )
        else:
            add_line("No ANC encounters recorded.")

        for _ in range(include_blank_rows):
            add_line("- | - | - | - | - | - | - | - | - | - | -")

        add_line("")
        add_line("This is a system-generated summary-only ANC record.")
        return lines

    def _render_pdf(self, lines: list[str]) -> bytes:
        lines_per_page = 48
        pages = [lines[i : i + lines_per_page] for i in range(0, len(lines), lines_per_page)]
        if not pages:
            pages = [["ANC Export"]]
        return self._build_pdf_document(pages)

    def _build_pdf_document(self, pages: list[list[str]]) -> bytes:
        objects: dict[int, bytes] = {}
        page_count = len(pages)
        page_numbers = []

        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        page_kids = []
        for idx in range(page_count):
            page_num = 4 + (idx * 2)
            page_numbers.append(page_num)
            page_kids.append(f"{page_num} 0 R")
        objects[2] = (
            f"<< /Type /Pages /Kids [{' '.join(page_kids)}] /Count {page_count} >>"
        ).encode("latin-1")
        objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

        for idx, page_lines in enumerate(pages):
            page_num = page_numbers[idx]
            content_num = page_num + 1

            content_commands = ["BT", "/F1 10 Tf", "14 TL", "1 0 0 1 36 806 Tm"]
            for line in page_lines:
                safe = self._escape_pdf_text(line)
                content_commands.append(f"({safe}) Tj")
                content_commands.append("T*")
            content_commands.append("ET")
            content_stream = "\n".join(content_commands).encode("latin-1", errors="replace")
            objects[content_num] = (
                f"<< /Length {len(content_stream)} >>\nstream\n".encode("latin-1")
                + content_stream
                + b"\nendstream"
            )
            objects[page_num] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_num} 0 R >>"
            ).encode("latin-1")

        out = bytearray()
        out.extend(b"%PDF-1.4\n")
        offsets: dict[int, int] = {}
        max_obj = max(objects.keys())
        for obj_num in range(1, max_obj + 1):
            offsets[obj_num] = len(out)
            out.extend(f"{obj_num} 0 obj\n".encode("latin-1"))
            out.extend(objects[obj_num])
            out.extend(b"\nendobj\n")

        xref_pos = len(out)
        out.extend(f"xref\n0 {max_obj + 1}\n".encode("latin-1"))
        out.extend(b"0000000000 65535 f \n")
        for obj_num in range(1, max_obj + 1):
            out.extend(f"{offsets[obj_num]:010d} 00000 n \n".encode("latin-1"))
        out.extend(
            (
                "trailer\n"
                f"<< /Size {max_obj + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_pos}\n%%EOF"
            ).encode("latin-1")
        )
        return bytes(out)

    def _escape_pdf_text(self, text: str) -> str:
        sanitized = text.encode("latin-1", errors="replace").decode("latin-1")
        return (
            sanitized.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
