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
