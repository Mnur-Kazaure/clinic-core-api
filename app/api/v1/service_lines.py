from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.database import get_db
from app.core.rbac import require_clinic_admin
from app.schemas.department_assignment import (
    DepartmentResponse,
    DoctorServiceLineAssignRequest,
    DoctorServiceLineResponse,
    UserDepartmentAssignRequest,
    UserDepartmentResponse,
)
from app.schemas.service_line import (
    ServiceLineCreateRequest,
    ServiceLineResponse,
    ServiceLineTreeNode,
    ServiceLineUpdateRequest,
)
from app.services.department_mapping_service import DepartmentMappingService
from app.services.service_line_service import ServiceLineService
from app.shared.enums import ServiceLineKind


router = APIRouter(tags=["Service Lines"])


@router.get(
    "/departments",
    response_model=list[DepartmentResponse],
)
def list_departments(
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    mapping_service = DepartmentMappingService(db)
    return mapping_service.list_departments(
        clinic_id=current_user.clinic_id,
    )


@router.get(
    "/service-lines",
    response_model=list[ServiceLineTreeNode],
)
def list_service_lines(
    include_inactive: bool = False,
    department_id: UUID | None = None,
    service_line_kind: ServiceLineKind | None = None,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = ServiceLineService(db)
    nodes = service.list_tree(
        clinic_id=current_user.clinic_id,
        include_inactive=include_inactive,
        department_id=department_id,
        service_line_kind=service_line_kind,
    )
    return [ServiceLineTreeNode.model_validate(node) for node in nodes]


@router.post(
    "/service-lines",
    response_model=ServiceLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_service_line(
    payload: ServiceLineCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = ServiceLineService(db)
    line = service.create(
        clinic_id=current_user.clinic_id,
        name=payload.name,
        parent_id=payload.parent_id,
        department_id=payload.department_id,
        default_child_id=payload.default_child_id,
        requires_doctor=payload.requires_doctor,
        service_line_kind=payload.service_line_kind,
        is_active=payload.is_active,
    )
    return line


@router.put(
    "/service-lines/{service_line_id}",
    response_model=ServiceLineResponse,
)
def update_service_line(
    service_line_id: UUID,
    payload: ServiceLineUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    updates = payload.model_dump(exclude_unset=True)
    service = ServiceLineService(db)
    line = service.update(
        clinic_id=current_user.clinic_id,
        service_line_id=service_line_id,
        **updates,
    )
    return line


@router.delete(
    "/service-lines/{service_line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_service_line(
    service_line_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = ServiceLineService(db)
    service.soft_delete(
        clinic_id=current_user.clinic_id,
        service_line_id=service_line_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/users/{user_id}/departments",
    response_model=list[UserDepartmentResponse],
)
def list_user_departments(
    user_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    mapping_service = DepartmentMappingService(db)
    return mapping_service.list_user_departments(
        clinic_id=current_user.clinic_id,
        user_id=user_id,
    )


@router.post(
    "/users/{user_id}/departments",
    response_model=UserDepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_user_department(
    user_id: UUID,
    payload: UserDepartmentAssignRequest,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    mapping_service = DepartmentMappingService(db)
    return mapping_service.assign_user_department(
        clinic_id=current_user.clinic_id,
        user_id=user_id,
        department_id=payload.department_id,
        is_primary=payload.is_primary,
    )


@router.delete(
    "/users/{user_id}/departments/{dept_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_user_department(
    user_id: UUID,
    dept_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    mapping_service = DepartmentMappingService(db)
    mapping_service.remove_user_department(
        clinic_id=current_user.clinic_id,
        user_id=user_id,
        department_id=dept_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/doctors/{doctor_id}/service-lines",
    response_model=list[DoctorServiceLineResponse],
)
def list_doctor_service_lines(
    doctor_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    mapping_service = DepartmentMappingService(db)
    return mapping_service.list_doctor_service_lines(
        clinic_id=current_user.clinic_id,
        doctor_id=doctor_id,
    )


@router.post(
    "/doctors/{doctor_id}/service-lines",
    response_model=DoctorServiceLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_doctor_service_line(
    doctor_id: UUID,
    payload: DoctorServiceLineAssignRequest,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    mapping_service = DepartmentMappingService(db)
    return mapping_service.assign_doctor_service_line(
        clinic_id=current_user.clinic_id,
        doctor_id=doctor_id,
        service_line_id=payload.service_line_id,
    )


@router.delete(
    "/doctors/{doctor_id}/service-lines/{sl_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_doctor_service_line(
    doctor_id: UUID,
    sl_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    mapping_service = DepartmentMappingService(db)
    mapping_service.remove_doctor_service_line(
        clinic_id=current_user.clinic_id,
        doctor_id=doctor_id,
        service_line_id=sl_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
