curl -X POST http://localhost:8000/api/visits/119e5edd-c6d9-4a36-bf3f-191d76f4c691/transition   -H "Content-Type: application/json"   -H "Authorization: Bearer <LabToken>"   -H "Idempotency-Key: lab-complete-001"   -d '{
    "to_status": "LAB_COMPLETED"
  }'



1️⃣ The API returned 500 Internal Server Error
2️⃣ Idempotency insert failed (created_at NOT NULL violation)
3️⃣ Visit state still changed to LAB_COMPLETED

This means that state mutation committed even though the request failed.
This is never accepted in a clinic system.


sqlalchemy.exc.IntegrityError: (psycopg2.errors.NotNullViolation) null value in column "created_at" of relation "idempotency_keys" violates not-null constraint
DETAIL:  Failing row contains (5dbcaea4-4fe8-447c-86d6-6a00b736ca4f, lab-complete-001, 51550e32-17d6-4c74-87b9-d056892ebac5, VISIT_TRANSITION, 4f23c37357e9b3c497fc1b959810c1ae97cc1707c41f88e836f863df3b32fa97, {"id": "119e5edd-c6d9-4a36-bf3f-191d76f4c691", "patient_id": "5e..., null, 2026-01-04 09:44:37.565334+00).

[SQL: INSERT INTO idempotency_keys (id, key, user_id, endpoint, request_hash, response_body) VALUES (%(id)s::UUID, %(key)s, %(user_id)s::UUID, %(endpoint)s, %(request_hash)s, %(response_body)s::JSON) RETURNING idempotency_keys.created_at, idempotency_keys.updated_at]
[parameters: {'id': UUID('5dbcaea4-4fe8-447c-86d6-6a00b736ca4f'), 'key': 'lab-complete-001', 'user_id': UUID('51550e32-17d6-4c74-87b9-d056892ebac5'), 'endpoint': 'VISIT_TRANSITION', 'request_hash': '4f23c37357e9b3c497fc1b959810c1ae97cc1707c41f88e836f863df3b32fa97', 'response_body': '{"id": "119e5edd-c6d9-4a36-bf3f-191d76f4c691", "patient_id": "5ea6bf5d-d732-4d80-b189-7b3f2fd7e687", "clinic_id": "9deb314f-6292-44f5-a38f-77ad1d7002 ... (34 characters truncated) ... ssigned_doctor_id": "66c5c76b-bf84-4ac0-ae74-87e2ae59bb80", "created_at": "2026-01-01T14:03:18.012613Z", "updated_at": "2026-01-04T09:44:37.526951Z"}'}]
(Background on this error at: https://sqlalche.me/e/20/gkpj)



✅ What Actually Happened (Truth, Not Excuses)


1️⃣ 500 Internal Server Error
→ Idempotency insert failed (created_at NOT NULL)

2️⃣ Visit state still transitioned to LAB_COMPLETED
→ Mutation committed outside idempotency transaction

3️⃣ Repeat call correctly blocked
→ State machine is intact, but transactional atomicity is broken

This is not acceptable for a clinic system — and you caught it early. Good.

🔎 Root Cause (Clear & Isolated)

This is NOT a Lab bug.
This is NOT a Visit state bug.

It is a cross-cutting infrastructure flaw:

❌ Idempotency persistence is not in the same transaction boundary as the Visit transition

Result:

State mutation committed

Idempotency write failed

API returned 500

System entered an inconsistent observable state


Need to enforce:
Idempotency transactional integrity

This is infrastructure, not domain logic.
Deferring it is a professional decision, not a shortcut.