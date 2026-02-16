# app/shared/enums.py

from enum import Enum
import enum
from typing import Type, TypeVar

# ------------------------------
# Existing enums
# ------------------------------

class VisitStatus(str, Enum):
    REGISTERED = "REGISTERED"
    # Deprecated legacy value. Triage lifecycle is tracked in VisitTriageState.
    TRIAGED = "TRIAGED"
    IN_CONSULTATION = "IN_CONSULTATION"
    LAB_REQUESTED = "LAB_REQUESTED"
    LAB_COMPLETED = "LAB_COMPLETED"
    PHARMACY_PENDING = "PHARMACY_PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class VisitServiceLine(str, Enum):
    OPD = "OPD"
    ANC = "ANC"
    MATERNITY = "MATERNITY"


class VisitTriageState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    TRIAGED = "TRIAGED"


class VisitOverrideReasonCode(str, Enum):
    PATIENT_LEFT = "PATIENT_LEFT"
    REFERRED_OUT = "REFERRED_OUT"
    NO_LAB_REAGENTS = "NO_LAB_REAGENTS"
    DRUG_OUT_OF_STOCK_EXTERNAL_PURCHASE = "DRUG_OUT_OF_STOCK_EXTERNAL_PURCHASE"
    EQUIPMENT_DOWN = "EQUIPMENT_DOWN"
    AFTER_HOURS = "AFTER_HOURS"
    PAYMENT_ISSUE = "PAYMENT_ISSUE"
    SYSTEM_OUTAGE = "SYSTEM_OUTAGE"
    DOCUMENTATION_PENDING = "DOCUMENTATION_PENDING"
    OTHER = "OTHER"


class UserRole(str, Enum):
    RECEPTION = "RECEPTION"
    DOCTOR = "DOCTOR"
    LAB = "LAB"
    PHARMACY = "PHARMACY"
    # Community Health Extension Worker (often runs ANC clinic in PHC settings)
    CHEW = "CHEW"
    # Midwife (maternity / labour & delivery workflows)
    MIDWIFE = "MIDWIFE"
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



class PrescriptionFulfillmentType(str, Enum):
    DISPENSED_IN_HOUSE = "DISPENSED_IN_HOUSE"
    DISPENSED_EXTERNAL = "DISPENSED_EXTERNAL"


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
    REGISTRATION_FEE = "REGISTRATION_FEE"
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
# PMR / MRN
# ------------------------------

class MRNStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"

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

class AdmissionDischargeDisposition(str, Enum):
    HOME = "HOME"
    TRANSFERRED_OUT = "TRANSFERRED_OUT"
    DECEASED = "DECEASED"
    LAMA = "LAMA"  # Left against medical advice
    ELOPED = "ELOPED"  # Left without notice / absconded
    OTHER = "OTHER"

class AdmissionRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
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
# ANC / Maternity
# ------------------------------

class PregnancyEpisodeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class DeliveryMode(str, Enum):
    SVD = "SVD"
    C_SECTION = "C_SECTION"
    ASSISTED = "ASSISTED"
    UNKNOWN = "UNKNOWN"


class DeliveryOutcome(str, Enum):
    LIVE_BIRTH = "LIVE_BIRTH"
    STILLBIRTH = "STILLBIRTH"
    NEONATAL_DEATH = "NEONATAL_DEATH"
    UNKNOWN = "UNKNOWN"


class BabySex(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    UNKNOWN = "UNKNOWN"


class PostnatalSubject(str, Enum):
    MOTHER = "MOTHER"
    BABY = "BABY"


class FamilyPlanningCommodity(str, Enum):
    IMPLANT = "IMPLANT"
    IUD = "IUD"
    INJECTABLE = "INJECTABLE"
    PILL = "PILL"
    CONDOM = "CONDOM"
    OTHER = "OTHER"

# ------------------------------
# Follow-up / Chronic Recall
# ------------------------------


class FollowUpPriority(str, Enum):
    ROUTINE = "ROUTINE"
    IMPORTANT = "IMPORTANT"
    CRITICAL = "CRITICAL"


class FollowUpType(str, Enum):
    MANUAL = "MANUAL"
    POST_DISCHARGE = "POST_DISCHARGE"
    LAB_REVIEW = "LAB_REVIEW"
    ANC_REVIEW = "ANC_REVIEW"
    CHRONIC_RECALL = "CHRONIC_RECALL"


class FollowUpStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"


class FollowUpGeneratedBy(str, Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"


class RecallIntervalUnit(str, Enum):
    DAYS = "DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"


class DiagnosisSystem(str, Enum):
    ICD10 = "ICD10"
    ICPC2 = "ICPC2"
    LOCAL = "LOCAL"


class DiagnosisMappingConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class RecallSuggestionConfidence(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"

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


class TriageScaleVersion(str, Enum):
    PHC_V1 = "PHC_V1"


class TriageAssessmentRecordStatus(str, Enum):
    DRAFT = "DRAFT"
    SIGNED = "SIGNED"


class TriageComplaintSeverity(str, Enum):
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class TriageFinalizeAction(str, Enum):
    QUEUE_FOR_CONSULTATION = "QUEUE_FOR_CONSULTATION"
    REFER_OUT_IMMEDIATE = "REFER_OUT_IMMEDIATE"


class TriageFallbackReasonCode(str, Enum):
    NO_TRIAGER_ON_DUTY = "NO_TRIAGER_ON_DUTY"
    MASS_CASUALTY = "MASS_CASUALTY"
    EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"
    OTHER = "OTHER"


class TriageMissingVitalReasonCode(str, Enum):
    DEVICE_UNAVAILABLE = "DEVICE_UNAVAILABLE"
    PATIENT_UNSTABLE = "PATIENT_UNSTABLE"
    CLINICAL_JUDGMENT = "CLINICAL_JUDGMENT"
    REFUSED = "REFUSED"

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
