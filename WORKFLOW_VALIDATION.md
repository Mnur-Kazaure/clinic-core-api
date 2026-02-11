# WORKFLOW_VALIDATION.md
# Production Visit Workflow Validation

## Tested Scenarios
1. Patient Registration → Reception only
2. Visit Start → Reception only, prevents duplicates
3. Triage → Reception/Nurse, idempotent
4. Consultation → Assigned doctor only
5. Lab Requests → Doctor only
6. Lab Processing → Lab staff only
7. Prescriptions → Doctor issue, Pharmacy dispense

## Security Validations
- RBAC enforced at every step
- Clinic isolation maintained
- Idempotency prevents duplicate operations
- Audit trails for compliance

## API Endpoints Validated
- POST /api/patient
- POST /api/visits/start
- POST /api/visits/{id}/transition
- POST /api/consultations
- POST /api/lab/requests
- POST /api/prescriptions
- POST /api/prescriptions/{id}/dispense

## ANC/Maternity v1.0 Smoke Gate (Role-Based)

### Preconditions
- Alembic at head
- Backend tests passing on current branch
- Users available: RECEPTION, CHEW, MIDWIFE

### Execution Checklist
- Reception starts an ANC visit and assigns a CHEW owner.
- Reception starts a MATERNITY visit and assigns a MIDWIFE owner.
- CHEW sees only assigned ANC visits in `/anc` queue.
- CHEW opens ANC workspace and can create/select active pregnancy episode.
- CHEW can add previous pregnancy row and save ANC encounter draft.
- CHEW can sign ANC encounter and cannot edit signed encounter afterward.
- MIDWIFE sees only assigned MATERNITY visits in `/maternity` queue.
- MIDWIFE can save delivery draft and sign delivery record.
- MIDWIFE can append postnatal notes and family planning events.
- CHEW/MIDWIFE PMR summary access works only for assigned active visit.
- CHEW/MIDWIFE PMR access is denied for unassigned or inactive visits.

### Expected Outcome
- All checklist items pass.
- No dead-end workflow traps for ANC/MATERNITY users.
- Audit logs are produced for PMR reads in ANC/MATERNITY context.
