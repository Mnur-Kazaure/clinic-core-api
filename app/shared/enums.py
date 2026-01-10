# # app/shared/enums.py
# app/shared/enums.py

from enum import Enum
import enum
from typing import Type, TypeVar

# ------------------------------
# Existing enums
# ------------------------------

class VisitStatus(str, Enum):
    REGISTERED = "REGISTERED"
    TRIAGED = "TRIAGED"
    IN_CONSULTATION = "IN_CONSULTATION"
    LAB_REQUESTED = "LAB_REQUESTED"
    LAB_COMPLETED = "LAB_COMPLETED"
    PHARMACY_PENDING = "PHARMACY_PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class UserRole(str, Enum):
    RECEPTION = "RECEPTION"
    DOCTOR = "DOCTOR"
    LAB = "LAB"
    PHARMACY = "PHARMACY"
    ADMIN = "ADMIN"
    # 🔒 Non-human actor
    SYSTEM = "SYSTEM"
    CLINIC_ADMIN = "CLINIC_ADMIN"



class LabRequestStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"



class PrescriptionStatus(str, Enum):
    ISSUED = "ISSUED"
    DISPENSED = "DISPENSED"
    CANCELLED = "CANCELLED"



class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

# ------------------------------
# Helper function
# ------------------------------

T = TypeVar("T", bound=Enum)

def to_enum(enum_cls: type[T], value: str) -> T:
    """
    Convert a string value to an Enum instance.
    If already an Enum instance, returns it as is.
    Raises ValueError if the value is invalid.
    """
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)





# from enum import Enum
# import enum


# class VisitStatus(str, Enum):
#     REGISTERED = "REGISTERED"
#     TRIAGED = "TRIAGED"
#     IN_CONSULTATION = "IN_CONSULTATION"
#     LAB_REQUESTED = "LAB_REQUESTED"
#     LAB_COMPLETED = "LAB_COMPLETED"
#     PHARMACY_PENDING = "PHARMACY_PENDING"
#     COMPLETED = "COMPLETED"
#     CANCELLED = "CANCELLED"


# class UserRole(str, Enum):
#     RECEPTION = "RECEPTION"
#     DOCTOR = "DOCTOR"
#     LAB = "LAB"
#     PHARMACY = "PHARMACY"
#     ADMIN = "ADMIN"
#      # 🔒 Non-human actor
#     SYSTEM = "SYSTEM"
#     CLINIC_ADMIN = "CLINIC_ADMIN"


# class Gender(str, enum.Enum):
#     MALE = "MALE"
#     FEMALE = "FEMALE"