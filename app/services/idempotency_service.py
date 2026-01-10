# import uuid
# from fastapi import HTTPException, status
# from sqlalchemy.orm import Session
# from app.models.idempotency import IdempotencyKey
# from app.core.idempotency import hash_request


# class IdempotencyService:
#     def __init__(self, db: Session):
#         self.db = db

#     def get_existing(
#         self,
#         *,
#         key: str,
#         endpoint: str,
#         user_id: uuid.UUID,
#         payload: dict,
#     ):
#         request_hash = hash_request(payload)

#         record = (
#             self.db.query(IdempotencyKey)
#             .filter(
#                 IdempotencyKey.key == key,
#                 IdempotencyKey.endpoint == endpoint,
#                 IdempotencyKey.user_id == user_id,
#             )
#             .first()
#         )

#         if not record:
#             return None

#         if record.request_hash != request_hash:
#             raise HTTPException(
#                 status_code=status.HTTP_409_CONFLICT,
#                 detail="Idempotency key reuse with different payload",
#             )

#         return record.response_body

#     def persist(
#         self,
#         *,
#         key: str,
#         endpoint: str,
#         user_id: uuid.UUID,
#         payload: dict,
#         response_body: dict,
#     ):
#         record = IdempotencyKey(
#             key=key,
#             endpoint=endpoint,
#             user_id=user_id,
#             request_hash=hash_request(payload),
#             response_body=response_body,
#         )

#         self.db.add(record)