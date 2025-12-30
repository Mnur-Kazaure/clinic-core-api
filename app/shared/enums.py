# app/shared/enums.py

from enum import Enum
import enum


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


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"