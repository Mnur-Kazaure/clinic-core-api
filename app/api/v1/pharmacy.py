from fastapi import APIRouter, Depends, status
from uuid import UUID

from app.core.pharmacy_guards import require_pharmacy_access
from app.services.pharmacy_service import PharmacyService
from app.schemas.pharmacy import DispenseCreate, DispenseResponse
from app.core.dependencies import get_db

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])


@router.post(
    "/{visit_id}/dispense",
    response_model=DispenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def dispense_medication(
    visit_id: UUID,
    payload: DispenseCreate,
    visit=Depends(require_pharmacy_access),  # 🔒 Guard enforced here
    db=Depends(get_db),
):
    service = PharmacyService(db)

    dispense = service.dispense(
        visit=visit,
        payload=payload,
    )

    return dispense