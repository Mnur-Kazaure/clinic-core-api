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


class ServiceLineKind(str, Enum):
    GENERAL = "GENERAL"
    LAB_UNIT = "LAB_UNIT"
    PHARMACY_UNIT = "PHARMACY_UNIT"


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
    CASHIER = "CASHIER"
    ACCOUNTANT = "ACCOUNTANT"
    CMD = "CMD"
    DOCTOR = "DOCTOR"
    LAB = "LAB"
    LAB_TECH = "LAB_TECH"
    LAB_SCIENTIST = "LAB_SCIENTIST"
    LAB_SUPERVISOR = "LAB_SUPERVISOR"
    LAB_MANAGER = "LAB_MANAGER"
    PHARMACY = "PHARMACY"
    PHARMACY_HOD = "PHARMACY_HOD"
    PHARMACY_STORE_OFFICER = "PHARMACY_STORE_OFFICER"
    # Community Health Extension Worker (often runs ANC clinic in PHC settings)
    CHEW = "CHEW"
    # Midwife (maternity / labour & delivery workflows)
    MIDWIFE = "MIDWIFE"
    ADMIN = "ADMIN"
    # 🔒 Non-human actor
    SYSTEM = "SYSTEM"
    CLINIC_ADMIN = "CLINIC_ADMIN"


LAB_OPERATION_ROLES = frozenset(
    {
        UserRole.LAB,
        UserRole.LAB_TECH,
        UserRole.LAB_SCIENTIST,
        UserRole.LAB_SUPERVISOR,
    }
)
LAB_WORKFORCE_ROLES = frozenset(set(LAB_OPERATION_ROLES) | {UserRole.LAB_MANAGER})



class LabRequestStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"



class LabRequestWorkflowStatus(str, Enum):
    ORDERED = "ORDERED"
    PAID = "PAID"
    AWAITING_SPECIMEN = "AWAITING_SPECIMEN"
    IN_ANALYSIS = "IN_ANALYSIS"
    RESULT_ENTERED = "RESULT_ENTERED"
    VERIFIED = "VERIFIED"
    RELEASED = "RELEASED"
    COMPLETED = "COMPLETED"


class LabResultTemplateType(str, Enum):
    NUMERIC = "NUMERIC"
    QUALITATIVE = "QUALITATIVE"
    SELECT = "SELECT"
    TEXT = "TEXT"
    PANEL = "PANEL"
    MIXED = "MIXED"
    MIXED_STRUCTURED = "MIXED_STRUCTURED"
    NARRATIVE = "NARRATIVE"
    ATTACHMENT = "ATTACHMENT"


class LabResultFieldType(str, Enum):
    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    SELECT = "SELECT"
    TEXT = "TEXT"
    JSON = "JSON"
    ATTACHMENT = "ATTACHMENT"


class LabResultLifecycleStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    RELEASED = "RELEASED"
    AMENDED = "AMENDED"


class LabSpecimenStatus(str, Enum):
    PENDING_COLLECTION = "PENDING_COLLECTION"
    COLLECTED = "COLLECTED"
    RECEIVED = "RECEIVED"
    IN_PROCESS = "IN_PROCESS"
    REJECTED = "REJECTED"
    LOST = "LOST"
    DISPOSED = "DISPOSED"


class LabSpecimenEventType(str, Enum):
    CREATED = "CREATED"
    LABEL_PRINTED = "LABEL_PRINTED"
    COLLECTED = "COLLECTED"
    RECEIVED = "RECEIVED"
    ROUTED_TO_UNIT = "ROUTED_TO_UNIT"
    REJECTED = "REJECTED"
    RECOLLECTION_REQUESTED = "RECOLLECTION_REQUESTED"
    LOST = "LOST"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    DISPOSED = "DISPOSED"


class LabSpecimenRejectionReasonCode(str, Enum):
    WRONG_LABEL = "WRONG_LABEL"
    BROKEN_CONTAINER = "BROKEN_CONTAINER"
    MISSING_SAMPLE = "MISSING_SAMPLE"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    HEMOLYSED_SAMPLE = "HEMOLYSED_SAMPLE"
    WRONG_CONTAINER = "WRONG_CONTAINER"
    MISLABELLED_SPECIMEN = "MISLABELLED_SPECIMEN"
    CONTAMINATED_SAMPLE = "CONTAMINATED_SAMPLE"
    EXPIRED_SAMPLE = "EXPIRED_SAMPLE"
    OTHER = "OTHER"


class LabVerificationPolicy(str, Enum):
    NONE = "NONE"
    OPTIONAL = "OPTIONAL"
    REQUIRED_BEFORE_RELEASE = "REQUIRED_BEFORE_RELEASE"
    REQUIRED_IF_ABNORMAL = "REQUIRED_IF_ABNORMAL"
    REQUIRED_IF_CRITICAL = "REQUIRED_IF_CRITICAL"


class LabCriticalAlertType(str, Enum):
    CRITICAL_RESULT = "CRITICAL_RESULT"
    QC_FAILURE = "QC_FAILURE"
    SYSTEM_ALERT = "SYSTEM_ALERT"


class LabCriticalAlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LabCriticalAlertStatus(str, Enum):
    CREATED = "CREATED"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class LabCriticalAlertEventType(str, Enum):
    CREATED = "CREATED"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class LabQcStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


class LabStaffAssignmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    TEMP_COVERAGE = "TEMP_COVERAGE"
    ON_LEAVE = "ON_LEAVE"
    RESTRICTED = "RESTRICTED"
    INACTIVE = "INACTIVE"


class LabConfigurationRequestType(str, Enum):
    NEW_STAFF_ACCOUNT = "NEW_STAFF_ACCOUNT"
    ROLE_ADJUSTMENT = "ROLE_ADJUSTMENT"
    NEW_TEST_ACTIVATION = "NEW_TEST_ACTIVATION"
    PRICE_REVIEW = "PRICE_REVIEW"
    TEMPLATE_ADJUSTMENT = "TEMPLATE_ADJUSTMENT"
    UNIT_CONFIGURATION_CHANGE = "UNIT_CONFIGURATION_CHANGE"


class LabConfigurationRequestStatus(str, Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


class GovernanceWorkspaceKey(str, Enum):
    LAB_MANAGER = "LAB_MANAGER"


class GovernanceSectionKey(str, Enum):
    PENDING_VERIFICATIONS = "PENDING_VERIFICATIONS"
    CRITICAL_ALERTS = "CRITICAL_ALERTS"
    SPECIMEN_ISSUES = "SPECIMEN_ISSUES"
    QUALITY_CONTROL = "QUALITY_CONTROL"
    SALES_REVENUE = "SALES_REVENUE"
    RECEIPT_REGISTER = "RECEIPT_REGISTER"


class LabWorkspaceAttentionKey(str, Enum):
    PENDING_QUEUE = "PENDING_QUEUE"
    AWAITING_SPECIMEN = "AWAITING_SPECIMEN"
    PENDING_VERIFICATIONS = "PENDING_VERIFICATIONS"
    CRITICAL_ALERTS = "CRITICAL_ALERTS"
    QC_FAILURES = "QC_FAILURES"
    COMPLETED_TODAY = "COMPLETED_TODAY"


class LabWorkspaceTabKey(str, Enum):
    QUEUE = "QUEUE"
    SPECIMENS = "SPECIMENS"
    RESULTS = "RESULTS"
    COMPLETED = "COMPLETED"
    QC = "QC"


class PrescriptionStatus(str, Enum):
    ISSUED = "ISSUED"
    DISPENSED = "DISPENSED"
    CANCELLED = "CANCELLED"
    EXTERNALLY_FULFILLED = "EXTERNALLY_FULFILLED"



class PrescriptionFulfillmentType(str, Enum):
    DISPENSED_IN_HOUSE = "DISPENSED_IN_HOUSE"
    DISPENSED_EXTERNAL = "DISPENSED_EXTERNAL"


class PharmacyPrescriptionWorkflowStatus(str, Enum):
    ASSIGNED = "ASSIGNED"
    AWAITING_PAYMENT_CLEARANCE = "AWAITING_PAYMENT_CLEARANCE"
    READY_TO_DISPENSE = "READY_TO_DISPENSE"
    PARTIALLY_DISPENSED = "PARTIALLY_DISPENSED"
    IN_DISPENSE = "IN_DISPENSE"
    DISPENSED = "DISPENSED"
    REASSIGNED = "REASSIGNED"
    CANCELLED = "CANCELLED"
    EXTERNALLY_FULFILLED = "EXTERNALLY_FULFILLED"


class PharmacyExceptionAuthorizationType(str, Enum):
    NONE = "NONE"
    NHIS_COVERED = "NHIS_COVERED"
    EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"
    HOD_AUTHORIZED_OVERRIDE = "HOD_AUTHORIZED_OVERRIDE"


class PharmacyUnitCategory(str, Enum):
    STORE = "STORE"
    DISPENSING = "DISPENSING"
    SATELLITE = "SATELLITE"


class PharmacyRequestType(str, Enum):
    PHARMACY_REFILL = "PHARMACY_REFILL"
    DEPARTMENT_COMMODITY = "DEPARTMENT_COMMODITY"
    EMERGENCY_REQUEST = "EMERGENCY_REQUEST"
    EQUIPMENT_REQUEST = "EQUIPMENT_REQUEST"


class PharmacyInventoryClassification(str, Enum):
    DRUG = "DRUG"
    CONSUMABLE = "CONSUMABLE"
    EQUIPMENT = "EQUIPMENT"


class PharmacyInventoryTrackingMode(str, Enum):
    LOT_TRACKED = "LOT_TRACKED"
    QUANTITY_ONLY = "QUANTITY_ONLY"
    SERIALIZED = "SERIALIZED"


class PharmacyCatalogLifecycleStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    AWAITING_CMD_APPROVAL = "AWAITING_CMD_APPROVAL"
    CMD_APPROVED = "CMD_APPROVED"
    PRICING_PENDING = "PRICING_PENDING"
    PRICED = "PRICED"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    DEACTIVATED = "DEACTIVATED"


class PharmacyPricingStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    PRICED = "PRICED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PharmacyRefillRequestStatus(str, Enum):
    PENDING = "PENDING"
    AWAITING_CMD_APPROVAL = "AWAITING_CMD_APPROVAL"
    APPROVED = "APPROVED"
    BACKORDERED = "BACKORDERED"
    ISSUE_PREPARATION_IN_PROGRESS = "ISSUE_PREPARATION_IN_PROGRESS"
    BACKORDER_PENDING = "BACKORDER_PENDING"
    REJECTED = "REJECTED"
    PARTIALLY_ISSUED = "PARTIALLY_ISSUED"
    ISSUED = "ISSUED"
    DISPATCHED = "DISPATCHED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PharmacyIssueVoucherStatus(str, Enum):
    DRAFT = "DRAFT"
    PREPARED = "PREPARED"
    ISSUED = "ISSUED"
    DISPATCHED = "DISPATCHED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CLOSED = "CLOSED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class PharmacyReturnRequestStatus(str, Enum):
    RETURN_REQUESTED = "RETURN_REQUESTED"
    RETURN_PENDING_STORE_REVIEW = "RETURN_PENDING_STORE_REVIEW"
    RETURN_ACCEPTED = "RETURN_ACCEPTED"
    RETURN_REJECTED = "RETURN_REJECTED"
    RETURN_RECEIVED = "RETURN_RECEIVED"
    RETURN_CLOSED = "RETURN_CLOSED"


class PharmacyReturnReasonCode(str, Enum):
    EXCESS_UNUSED = "EXCESS_UNUSED"
    WRONG_ISSUE = "WRONG_ISSUE"
    DAMAGED_ON_RECEIPT = "DAMAGED_ON_RECEIPT"
    EXPIRED_AT_UNIT = "EXPIRED_AT_UNIT"
    UNIT_TRANSFER_CORRECTION = "UNIT_TRANSFER_CORRECTION"
    OTHER = "OTHER"


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


class BillingItemStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    WAIVED = "WAIVED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"

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
