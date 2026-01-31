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
    UNKNOWN = "UNKNOWN"
    MALE = "MALE"
    FEMALE = "FEMALE"


class RecordStatus(str, Enum):
    DRAFT = "DRAFT"
    SIGNED = "SIGNED"
    AMENDED = "AMENDED"
    VOIDED = "VOIDED"

# ------------------------------
# Access Logs / Audit
# ------------------------------

class PurposeOfUse(str, Enum):
    TREATMENT = "TREATMENT"
    OPERATIONS = "OPERATIONS"
    EMERGENCY = "EMERGENCY"
    AUDIT = "AUDIT"
    BILLING = "BILLING"
    SECURITY = "SECURITY"


class AuditCaseStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    CLOSED = "CLOSED"


class AuditCaseSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditCaseOutcome(str, Enum):
    JUSTIFIED = "JUSTIFIED"
    UNJUSTIFIED = "UNJUSTIFIED"
    TRAINING_REQUIRED = "TRAINING_REQUIRED"
    ESCALATED = "ESCALATED"


class AuditItemType(str, Enum):
    ACCESS_LOG = "ACCESS_LOG"
    EVENT_LOG = "EVENT_LOG"

# ------------------------------
# Billing / Ledger
# ------------------------------

class BillingEntryType(str, Enum):
    CHARGE = "CHARGE"
    PAYMENT = "PAYMENT"
    ADJUSTMENT = "ADJUSTMENT"
    REFUND = "REFUND"
    WRITE_OFF = "WRITE_OFF"
    REVERSAL = "REVERSAL"


class BillingReasonCode(str, Enum):
    SERVICE = "SERVICE"
    LAB_TEST = "LAB_TEST"
    MEDICATION = "MEDICATION"
    PROCEDURE = "PROCEDURE"
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    INSURANCE = "INSURANCE"
    DISCOUNT = "DISCOUNT"
    CORRECTION = "CORRECTION"
    REFUND = "REFUND"
    WRITE_OFF = "WRITE_OFF"
    REVERSAL = "REVERSAL"
    OTHER = "OTHER"

# ------------------------------
# Admissions / Beds
# ------------------------------

class AdmissionType(str, Enum):
    EMERGENCY = "EMERGENCY"
    ELECTIVE = "ELECTIVE"


class AdmissionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISCHARGED = "DISCHARGED"
    CANCELLED = "CANCELLED"


class WardType(str, Enum):
    GENERAL = "GENERAL"
    ICU = "ICU"
    MATERNITY = "MATERNITY"
    PEDIATRIC = "PEDIATRIC"
    EMERGENCY = "EMERGENCY"
    ISOLATION = "ISOLATION"


class BedStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class BedAssignmentType(str, Enum):
    ASSIGN = "ASSIGN"
    TRANSFER = "TRANSFER"

# ------------------------------
# Clinical Priority
# ------------------------------

class ClinicalPriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    URGENT = "URGENT"
    ROUTINE = "ROUTINE"


class ClinicalPrioritySource(str, Enum):
    TRIAGE = "TRIAGE"
    CLINICIAN = "CLINICIAN"
    SYSTEM = "SYSTEM"

# ------------------------------
# Identity Resolution
# ------------------------------

class IdentityState(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    VERIFIED = "VERIFIED"
    MERGED = "MERGED"
    SPLIT = "SPLIT"


class IdentityCaseType(str, Enum):
    VERIFY = "VERIFY"
    MERGE = "MERGE"
    SPLIT = "SPLIT"


class IdentityCaseStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    ROLLED_BACK = "ROLLED_BACK"


class PatientAliasType(str, Enum):
    NAME = "NAME"
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    GOV_ID = "GOV_ID"
    NEXT_OF_KIN = "NEXT_OF_KIN"
    PHOTO_REF = "PHOTO_REF"


class PatientAliasConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PatientAliasSource(str, Enum):
    PATIENT = "PATIENT"
    STAFF = "STAFF"
    DOCUMENT = "DOCUMENT"
    SYSTEM = "SYSTEM"


class IdentityEvidenceType(str, Enum):
    DOCUMENT_REF = "DOCUMENT_REF"
    STAFF_WITNESS = "STAFF_WITNESS"
    BIOMETRIC_REF = "BIOMETRIC_REF"
    PHOTO_REF = "PHOTO_REF"
    SYSTEM_MATCH = "SYSTEM_MATCH"


class IdentityApprovalRole(str, Enum):
    ADMIN = "ADMIN"
    CLINIC_ADMIN = "CLINIC_ADMIN"


class IdentityApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"

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
