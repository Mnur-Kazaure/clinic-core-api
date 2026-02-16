'use client';

import { useCallback, useEffect, useState } from 'react';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { Badge } from '@/shared/Badge';
import { Input } from '@/shared/Input';
import {
  bedService,
  Bed,
  BedBoardResponse,
  BedStatus,
  BedBoardWard,
  OccupiedBedItem,
  OccupiedBedDetailResponse,
  WardBedRangePreview,
  Ward,
} from '@/domains/bed/services/bedService';
import {
  admissionRequestService,
  AdmissionRequest,
  AdmissionDischargeDisposition,
  AdmissionStatus,
  AdmissionRequestStatus,
  VisitServiceLine,
} from '@/domains/admission/services/admissionRequestService';
import { auditService, AuditTimelineItem } from '@/domains/admin/services/auditService';
import { userService, Doctor as StaffMember } from '@/domains/user/services/userService';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitServiceLine as SharedVisitServiceLine } from '@/shared/enums';

const statusLabels: Record<AdmissionRequestStatus, string> = {
  PENDING: 'Pending',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  CANCELLED: 'Cancelled',
};

const statusVariant: Record<AdmissionRequestStatus, 'warning' | 'success' | 'error' | 'ghost'> = {
  PENDING: 'warning',
  APPROVED: 'success',
  REJECTED: 'error',
  CANCELLED: 'ghost',
};
const admissionStatusLabels: Record<AdmissionStatus, string> = {
  ACTIVE: 'Admission Active',
  DISCHARGED: 'Admission Discharged',
  CANCELLED: 'Admission Cancelled',
};
const admissionStatusVariant: Record<AdmissionStatus, 'success' | 'warning' | 'ghost'> = {
  ACTIVE: 'success',
  DISCHARGED: 'warning',
  CANCELLED: 'ghost',
};

const maskId = (value: string) => `${value.slice(0, 8)}...`;
const formatWardLabel = (prefix: string, number: number, padding?: number | null) => {
  const width = padding && padding > 0 ? padding : 0;
  const suffix = width > 0 ? String(number).padStart(width, '0') : String(number);
  return `${prefix}${suffix}`;
};
type BedActionMode = 'assign' | 'transfer';
type BedStatusTarget = Extract<BedStatus, 'AVAILABLE' | 'OUT_OF_SERVICE'>;
type WardTypeValue =
  | 'GENERAL'
  | 'ICU'
  | 'MATERNITY'
  | 'PEDIATRIC'
  | 'EMERGENCY'
  | 'ISOLATION';
type ActivityTargetType = 'ward' | 'bed';
type OwnerRole = 'DOCTOR' | 'CHEW' | 'MIDWIFE';

interface BedStatusModalContext {
  bedId: string;
  bedLabel: string;
  wardName: string;
  fromStatus: BedStatusTarget;
  toStatus: BedStatusTarget;
}

interface ActiveToggleModalContext {
  targetType: ActivityTargetType;
  targetId: string;
  targetLabel: string;
  fromActive: boolean;
  toActive: boolean;
}

const occupancyBadgeClass: Record<string, string> = {
  AVAILABLE: 'bg-emerald-100 text-emerald-700',
  OCCUPIED: 'bg-amber-100 text-amber-700',
  OUT_OF_SERVICE: 'bg-rose-100 text-rose-700',
  INACTIVE: 'bg-slate-200 text-slate-700',
};

const renderInpatientFlags = (reviewDue: boolean, chronicDue: boolean) => {
  if (!reviewDue && !chronicDue) {
    return <span className="text-xs text-slate-500">Stable</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {reviewDue && (
        <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
          Review Due
        </span>
      )}
      {chronicDue && (
        <span className="inline-flex items-center rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-800">
          Chronic Due
        </span>
      )}
    </div>
  );
};

const bedAdmissionEvents = new Set([
  'ADMISSION_REQUEST_CREATED',
  'ADMISSION_REQUEST_APPROVED',
  'ADMISSION_REQUEST_REJECTED',
  'ADMISSION_REQUEST_CANCELLED',
  'PATIENT_ADMITTED',
  'PATIENT_DISCHARGED',
  'ADMISSION_CANCELLED',
  'BED_ASSIGNED',
  'BED_TRANSFERRED',
  'BED_STATUS_CHANGED',
  'BED_RELEASED',
  'BED_ACTIVITY_CHANGED',
  'WARD_ACTIVITY_CHANGED',
  'ENTRY_AMENDED',
]);

const formatEventLabel = (value: string) =>
  value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');

const getActivityDetail = (item: AuditTimelineItem): string | null => {
  const payload = item.event_payload || {};
  if (
    item.event_type === 'ENTRY_AMENDED' &&
    payload.entity === 'visit' &&
    payload.action === 'owner_reassigned'
  ) {
    const fromServiceLine =
      typeof payload.from_service_line === 'string'
        ? payload.from_service_line
        : null;
    const toServiceLine =
      typeof payload.to_service_line === 'string' ? payload.to_service_line : null;
    const fromOwnerId =
      typeof payload.from_owner_id === 'string' ? payload.from_owner_id : null;
    const toOwnerId = typeof payload.to_owner_id === 'string' ? payload.to_owner_id : null;
    const parts: string[] = [];
    if (fromOwnerId || toOwnerId) {
      parts.push(
        `Owner ${fromOwnerId ? `${fromOwnerId.slice(0, 8)}...` : '—'} -> ${
          toOwnerId ? `${toOwnerId.slice(0, 8)}...` : '—'
        }`
      );
    }
    if (fromServiceLine || toServiceLine) {
      parts.push(
        `Service ${fromServiceLine ?? '—'} -> ${toServiceLine ?? fromServiceLine ?? '—'}`
      );
    }
    return parts.join(' • ') || 'Visit owner reassigned';
  }
  return null;
};

const formatAssignmentLabel = (value: 'ASSIGN' | 'TRANSFER') =>
  value === 'ASSIGN' ? 'Assigned' : 'Reassigned';

const blockerMessage: Record<string, string> = {
  NO_AVAILABLE_BEDS_ASSIGN:
    'Assignment blocked: no available beds. Release a bed or reactivate capacity first.',
  NO_AVAILABLE_BEDS_REASSIGN:
    'Bed reassignment blocked: no destination bed is currently available.',
  NO_ACTIVE_VISIT_CONTEXT:
    'Visit link missing: owner reassignment unavailable; bed actions are still allowed.',
  ADMISSION_NOT_ACTIVE:
    'Actions blocked: admission is no longer active.',
  ADMISSION_RECORD_UNAVAILABLE:
    'Actions blocked: admission record is unavailable.',
};

const wardTypeOptions: Array<{ value: WardTypeValue; label: string }> = [
  { value: 'GENERAL', label: 'General' },
  { value: 'ICU', label: 'ICU' },
  { value: 'MATERNITY', label: 'Maternity' },
  { value: 'PEDIATRIC', label: 'Pediatric' },
  { value: 'EMERGENCY', label: 'Emergency' },
  { value: 'ISOLATION', label: 'Isolation' },
];

const ownerRoleByServiceLine: Record<VisitServiceLine, OwnerRole> = {
  OPD: 'DOCTOR',
  ANC: 'CHEW',
  MATERNITY: 'MIDWIFE',
};

const serviceLineLabel: Record<VisitServiceLine, string> = {
  OPD: 'Consultation',
  ANC: 'ANC',
  MATERNITY: 'Maternity',
};

const serviceLineOptions: VisitServiceLine[] = ['OPD', 'ANC', 'MATERNITY'];

export default function AdmissionRequestsPage() {
  const [requests, setRequests] = useState<AdmissionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<AdmissionRequestStatus>('PENDING');
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [decisionRequestId, setDecisionRequestId] = useState<string | null>(null);
  const [decisionAction, setDecisionAction] = useState<'approve' | 'reject'>('approve');
  const [decisionReason, setDecisionReason] = useState('');
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [decisionSafetyChecked, setDecisionSafetyChecked] = useState(false);
  const [bedActionRequest, setBedActionRequest] = useState<AdmissionRequest | null>(null);
  const [bedActionMode, setBedActionMode] = useState<BedActionMode>('assign');
  const [bedActionModalOpen, setBedActionModalOpen] = useState(false);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [wards, setWards] = useState<Ward[]>([]);
  const [bedsLoading, setBedsLoading] = useState(false);
  const [bedActionError, setBedActionError] = useState<string | null>(null);
  const [bedActionReason, setBedActionReason] = useState('');
  const [selectedWard, setSelectedWard] = useState<string>('all');
  const [selectedBedId, setSelectedBedId] = useState('');
  const [bedActionSubmitting, setBedActionSubmitting] = useState(false);
  const [bedActionSafetyChecked, setBedActionSafetyChecked] = useState(false);
  const [bedActionSuccess, setBedActionSuccess] = useState<string | null>(null);
  const [bedBoard, setBedBoard] = useState<BedBoardResponse | null>(null);
  const [bedBoardLoading, setBedBoardLoading] = useState(true);
  const [bedBoardError, setBedBoardError] = useState<string | null>(null);
  const [bedBoardWardFilter, setBedBoardWardFilter] = useState<string>('all');
  const [bedBoardWardFocus, setBedBoardWardFocus] = useState<string | null>(null);
  const [occupiedQuery, setOccupiedQuery] = useState('');
  const [occupiedItems, setOccupiedItems] = useState<OccupiedBedItem[]>([]);
  const [occupiedTotal, setOccupiedTotal] = useState(0);
  const [occupiedOffset, setOccupiedOffset] = useState(0);
  const [occupiedLoading, setOccupiedLoading] = useState(false);
  const [occupiedError, setOccupiedError] = useState<string | null>(null);
  const [occupiedDetailOpen, setOccupiedDetailOpen] = useState(false);
  const [occupiedDetail, setOccupiedDetail] =
    useState<OccupiedBedDetailResponse | null>(null);
  const [occupiedDetailLoading, setOccupiedDetailLoading] = useState(false);
  const [occupiedDetailError, setOccupiedDetailError] = useState<string | null>(null);
  const [activityItems, setActivityItems] = useState<AuditTimelineItem[]>([]);
  const [activityLoading, setActivityLoading] = useState(true);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [bedRangeWardName, setBedRangeWardName] = useState('');
  const [bedRangeWardType, setBedRangeWardType] = useState<WardTypeValue>('GENERAL');
  const [bedRangePrefix, setBedRangePrefix] = useState('A-');
  const [bedRangeFrom, setBedRangeFrom] = useState(1);
  const [bedRangeTo, setBedRangeTo] = useState(10);
  const [bedRangePadding, setBedRangePadding] = useState(2);
  const [bedRangePreview, setBedRangePreview] = useState<WardBedRangePreview | null>(null);
  const [bedRangePreviewLoading, setBedRangePreviewLoading] = useState(false);
  const [bedRangeCreateLoading, setBedRangeCreateLoading] = useState(false);
  const [bedRangeActionError, setBedRangeActionError] = useState<string | null>(null);
  const [bedRangeActionSuccess, setBedRangeActionSuccess] = useState<string | null>(null);
  const [wardInventoryError, setWardInventoryError] = useState<string | null>(null);
  const [retireModalOpen, setRetireModalOpen] = useState(false);
  const [retireWard, setRetireWard] = useState<Ward | null>(null);
  const [retireReason, setRetireReason] = useState('');
  const [retireSubmitting, setRetireSubmitting] = useState(false);
  const [retireError, setRetireError] = useState<string | null>(null);
  const [appendSubmitting, setAppendSubmitting] = useState(false);
  const [appendError, setAppendError] = useState<string | null>(null);
  const [bedStatusModalContext, setBedStatusModalContext] =
    useState<BedStatusModalContext | null>(null);
  const [bedStatusSubmitting, setBedStatusSubmitting] = useState(false);
  const [bedStatusReason, setBedStatusReason] = useState('');
  const [bedStatusError, setBedStatusError] = useState<string | null>(null);
  const [bedStatusModalOpen, setBedStatusModalOpen] = useState(false);
  const [bedStatusSafetyChecked, setBedStatusSafetyChecked] = useState(false);
  const [bedReleaseModalOpen, setBedReleaseModalOpen] = useState(false);
  const [bedReleaseRequest, setBedReleaseRequest] = useState<AdmissionRequest | null>(null);
  const [bedReleaseReason, setBedReleaseReason] = useState('');
  const [bedReleaseError, setBedReleaseError] = useState<string | null>(null);
  const [bedReleaseSubmitting, setBedReleaseSubmitting] = useState(false);
  const [bedReleaseSafetyChecked, setBedReleaseSafetyChecked] = useState(false);
  const [dischargeModalOpen, setDischargeModalOpen] = useState(false);
  const [dischargeRequest, setDischargeRequest] = useState<AdmissionRequest | null>(null);
  const [dischargeDisposition, setDischargeDisposition] =
    useState<AdmissionDischargeDisposition>('HOME');
  const [dischargeReason, setDischargeReason] = useState('');
  const [dischargeTransferredToFacility, setDischargeTransferredToFacility] = useState('');
  const [dischargePronouncedAt, setDischargePronouncedAt] = useState('');
  const [dischargeError, setDischargeError] = useState<string | null>(null);
  const [dischargeSubmitting, setDischargeSubmitting] = useState(false);
  const [dischargeSafetyChecked, setDischargeSafetyChecked] = useState(false);
  const [ownerReassignModalOpen, setOwnerReassignModalOpen] = useState(false);
  const [ownerReassignRequest, setOwnerReassignRequest] =
    useState<AdmissionRequest | null>(null);
  const [ownerReassignServiceLine, setOwnerReassignServiceLine] =
    useState<VisitServiceLine>('OPD');
  const [ownerReassignTargetId, setOwnerReassignTargetId] = useState('');
  const [ownerReassignReason, setOwnerReassignReason] = useState('');
  const [ownerReassignError, setOwnerReassignError] = useState<string | null>(null);
  const [ownerReassignSubmitting, setOwnerReassignSubmitting] = useState(false);
  const [ownerReassignHandoverChecked, setOwnerReassignHandoverChecked] = useState(false);
  const [assignableStaff, setAssignableStaff] = useState<StaffMember[]>([]);
  const [assignableStaffLoading, setAssignableStaffLoading] = useState(false);
  const [assignableStaffError, setAssignableStaffError] = useState<string | null>(null);
  const [activeToggleModalOpen, setActiveToggleModalOpen] = useState(false);
  const [activeToggleModalContext, setActiveToggleModalContext] =
    useState<ActiveToggleModalContext | null>(null);
  const [activeToggleReason, setActiveToggleReason] = useState('');
  const [activeToggleError, setActiveToggleError] = useState<string | null>(null);
  const [activeToggleSubmitting, setActiveToggleSubmitting] = useState(false);
  const [activeToggleSafetyChecked, setActiveToggleSafetyChecked] = useState(false);
  const listActionLocked =
    actionLoading !== null ||
    bedActionSubmitting ||
    bedStatusSubmitting ||
    bedReleaseSubmitting ||
    dischargeSubmitting ||
    bedRangePreviewLoading ||
    bedRangeCreateLoading ||
    appendSubmitting ||
    retireSubmitting ||
    ownerReassignSubmitting ||
    activeToggleSubmitting;

  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await admissionRequestService.listRequests(filter);
      setRequests(data);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setError(detail || 'Unable to load admission requests.');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const loadBedBoard = useCallback(async () => {
    try {
      setBedBoardLoading(true);
      setBedBoardError(null);
      const data = await bedService.getBedBoard();
      setBedBoard(data);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setBedBoardError(detail || 'Unable to load bed board.');
    } finally {
      setBedBoardLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBedBoard();
  }, [loadBedBoard]);

  const occupiedLimit = 10;

  const loadOccupiedBeds = useCallback(async () => {
    try {
      setOccupiedLoading(true);
      setOccupiedError(null);
      const response = await bedService.searchOccupiedBeds({
        query: occupiedQuery.trim() || undefined,
        wardId: bedBoardWardFilter === 'all' ? undefined : bedBoardWardFilter,
        limit: occupiedLimit,
        offset: occupiedOffset,
      });
      setOccupiedItems(response.items);
      setOccupiedTotal(response.total);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setOccupiedError(detail || 'Unable to load occupied beds.');
    } finally {
      setOccupiedLoading(false);
    }
  }, [bedBoardWardFilter, occupiedOffset, occupiedQuery]);

  useEffect(() => {
    setOccupiedOffset(0);
  }, [occupiedQuery, bedBoardWardFilter]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      loadOccupiedBeds();
    }, 300);
    return () => window.clearTimeout(handle);
  }, [loadOccupiedBeds]);

  const openOccupiedDetail = async (admissionId: string, wardId?: string) => {
    try {
      if (wardId) {
        setBedBoardWardFocus(wardId);
        setBedBoardWardFilter(wardId);
      }
      setOccupiedDetailLoading(true);
      setOccupiedDetailError(null);
      setOccupiedDetailOpen(true);
      const detail = await bedService.getOccupiedBedDetail(admissionId);
      setOccupiedDetail(detail);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setOccupiedDetailError(detail || 'Unable to load bed details.');
    } finally {
      setOccupiedDetailLoading(false);
    }
  };

  const closeOccupiedDetail = () => {
    setOccupiedDetailOpen(false);
    setOccupiedDetail(null);
    setOccupiedDetailError(null);
  };

  const loadWardInventory = useCallback(async () => {
    try {
      setWardInventoryError(null);
      const data = await bedService.listWards();
      setWards(data);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setWardInventoryError(detail || 'Unable to load ward inventory.');
    }
  }, []);

  useEffect(() => {
    loadWardInventory();
  }, [loadWardInventory]);

  const loadBedAdmissionActivity = useCallback(async () => {
    try {
      setActivityLoading(true);
      setActivityError(null);
      const timeline = await auditService.getTimeline({ limit: 120 });
      const filtered = timeline
        .filter((item) => {
          if (item.source !== 'EVENT') return false;
          if (!bedAdmissionEvents.has(item.event_type)) return false;
          if (item.event_type !== 'ENTRY_AMENDED') return true;
          const payload = item.event_payload || {};
          return payload.entity === 'visit' && payload.action === 'owner_reassigned';
        })
        .slice(0, 15);
      setActivityItems(filtered);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setActivityError(detail || 'Unable to load admission activity timeline.');
    } finally {
      setActivityLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBedAdmissionActivity();
  }, [loadBedAdmissionActivity]);

  useEffect(() => {
    if (!bedRangeActionSuccess) return;
    const timeout = window.setTimeout(() => setBedRangeActionSuccess(null), 8000);
    return () => window.clearTimeout(timeout);
  }, [bedRangeActionSuccess]);

  useEffect(() => {
    if (!bedActionSuccess) return;
    const timeout = window.setTimeout(() => setBedActionSuccess(null), 8000);
    return () => window.clearTimeout(timeout);
  }, [bedActionSuccess]);

  useEffect(() => {
    if (!ownerReassignModalOpen || !ownerReassignRequest) return;
    const requiredRole = ownerRoleByServiceLine[ownerReassignServiceLine];
    const eligible = assignableStaff.filter((member) => member.role === requiredRole);
    if (eligible.some((member) => member.id === ownerReassignTargetId)) return;
    const next =
      eligible.find((member) => member.id !== ownerReassignRequest.active_visit_owner_id)?.id ||
      eligible[0]?.id ||
      '';
    setOwnerReassignTargetId(next);
  }, [
    ownerReassignModalOpen,
    ownerReassignRequest,
    ownerReassignServiceLine,
    assignableStaff,
    ownerReassignTargetId,
  ]);

  useEffect(() => {
    if (!ownerReassignModalOpen) return;
    setOwnerReassignHandoverChecked(false);
  }, [ownerReassignServiceLine, ownerReassignModalOpen]);

  const loadAvailableBeds = useCallback(async (wardId?: string) => {
    if (!wardId) {
      setBeds([]);
      return;
    }
    try {
      setBedsLoading(true);
      setBedActionError(null);
      const bedList = await bedService.listBeds({
        availableOnly: true,
        wardId,
      });
      setBeds(bedList);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setBedActionError(detail || 'Unable to load available beds.');
    } finally {
      setBedsLoading(false);
    }
  }, []);

  const openBedActionModal = async (
    request: AdmissionRequest,
    mode: BedActionMode
  ) => {
    if (!request.admission_id || request.admission_status !== 'ACTIVE') {
      setError('Bed actions are allowed only when the admission is ACTIVE.');
      return;
    }
    setBedActionSuccess(null);
    setError(null);
    setBedActionRequest(request);
    setBedActionMode(mode);
    setBedActionModalOpen(true);
    setBedActionReason('');
    setBedActionSafetyChecked(false);
    setSelectedWard('');
    setSelectedBedId('');
    try {
      setBedsLoading(true);
      setBedActionError(null);
      const wardList = await bedService.listWards();
      setWards(wardList);
      const activeWard = wardList.find((ward) => ward.active);
      const defaultWardId = activeWard?.id || '';
      setSelectedWard(defaultWardId);
      await loadAvailableBeds(defaultWardId);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setBedActionError(detail || 'Unable to load available beds.');
    } finally {
      setBedsLoading(false);
    }
  };

  const closeBedActionModal = () => {
    if (bedActionSubmitting) return;
    setBedActionModalOpen(false);
    setBedActionRequest(null);
    setBedActionError(null);
    setBedActionSafetyChecked(false);
  };

  const handleSubmitBedAction = async () => {
    if (!bedActionRequest?.admission_id) {
      setBedActionError('Admission is not active yet. Approve the request first.');
      return;
    }
    if (bedActionRequest.admission_status !== 'ACTIVE') {
      setBedActionError('Admission is no longer active. Refresh the queue.');
      return;
    }
    if (!selectedBedId) {
      setBedActionError('Select an available bed to continue.');
      return;
    }
    if (bedActionMode === 'transfer' && bedActionReason.trim().length < 3) {
      setBedActionError('Transfer reason must be at least 3 characters.');
      return;
    }
    if (bedActionMode === 'transfer' && !bedActionSafetyChecked) {
      setBedActionError('Confirm handover impact before reassigning bed.');
      return;
    }
    try {
      setBedActionSubmitting(true);
      setBedActionError(null);
      if (bedActionMode === 'assign') {
        await bedService.assignBed({
          admission_id: bedActionRequest.admission_id,
          bed_id: selectedBedId,
          reason: bedActionReason.trim() || undefined,
        });
      } else {
        await bedService.transferBed({
          admission_id: bedActionRequest.admission_id,
          to_bed_id: selectedBedId,
          reason: bedActionReason.trim(),
        });
      }
      await Promise.all([loadRequests(), loadBedBoard(), loadBedAdmissionActivity()]);
      setBedActionSuccess(
        bedActionMode === 'assign'
          ? 'Bed assigned successfully.'
          : 'Bed reassigned successfully.'
      );
      closeBedActionModal();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      const normalized = (detail || '').toLowerCase();

      if (normalized.includes('bed not available')) {
        await loadAvailableBeds(selectedWard);
        setBedActionError(
          'Selected bed is no longer available. Choose another bed.'
        );
        return;
      }
      if (normalized.includes('admission not active')) {
        await Promise.all([loadRequests(), loadBedBoard(), loadBedAdmissionActivity()]);
        setBedActionError('Admission is no longer active. Bed action blocked.');
        return;
      }
      if (normalized.includes('transfer target must differ from current bed')) {
        setBedActionError('Choose a different bed for transfer.');
        return;
      }

      setBedActionError(
        detail ||
          (bedActionMode === 'assign'
            ? 'Unable to assign bed.'
            : 'Unable to reassign bed.')
      );
    } finally {
      setBedActionSubmitting(false);
    }
  };

  const openDecisionModal = (
    requestId: string,
    action: 'approve' | 'reject'
  ) => {
    setDecisionRequestId(requestId);
    setDecisionAction(action);
    setDecisionReason('');
    setDecisionError(null);
    setDecisionSafetyChecked(false);
    setDecisionModalOpen(true);
  };

  const closeDecisionModal = () => {
    setDecisionModalOpen(false);
    setDecisionRequestId(null);
    setDecisionError(null);
    setDecisionSafetyChecked(false);
  };

  const handleDecisionSubmit = async () => {
    if (!decisionRequestId) return;
    if (decisionReason.trim().length < 3) {
      setDecisionError('Reason must be at least 3 characters.');
      return;
    }
    if (decisionAction === 'reject' && !decisionSafetyChecked) {
      setDecisionError('Confirm the impact before rejecting.');
      return;
    }

    try {
      setActionLoading(decisionRequestId);
      setDecisionError(null);
      if (decisionAction === 'approve') {
        await admissionRequestService.approveRequest(decisionRequestId, {
          reason: decisionReason.trim(),
        });
      } else {
        await admissionRequestService.rejectRequest(decisionRequestId, {
          reason: decisionReason.trim(),
        });
      }
      await Promise.all([loadRequests(), loadBedBoard(), loadBedAdmissionActivity()]);
      closeDecisionModal();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setDecisionError(detail || 'Action failed.');
    } finally {
      setActionLoading(null);
    }
  };

  const openBedStatusModal = (
    bedId: string,
    bedLabel: string,
    wardName: string,
    fromStatus: BedStatusTarget,
    toStatus: BedStatusTarget
  ) => {
    setBedStatusModalContext({
      bedId,
      bedLabel,
      wardName,
      fromStatus,
      toStatus,
    });
    setBedStatusReason('');
    setBedStatusError(null);
    setBedStatusSafetyChecked(false);
    setBedStatusModalOpen(true);
  };

  const closeBedStatusModal = () => {
    if (bedStatusSubmitting) return;
    setBedStatusModalOpen(false);
    setBedStatusModalContext(null);
    setBedStatusReason('');
    setBedStatusError(null);
    setBedStatusSafetyChecked(false);
  };

  const submitBedStatusChange = async () => {
    if (!bedStatusModalContext || bedStatusSubmitting) return;
    if (
      bedStatusModalContext.toStatus === 'OUT_OF_SERVICE' &&
      bedStatusReason.trim().length < 3
    ) {
      setBedStatusError('Reason must be at least 3 characters.');
      return;
    }
    if (
      bedStatusModalContext.toStatus === 'OUT_OF_SERVICE' &&
      !bedStatusSafetyChecked
    ) {
      setBedStatusError('Confirm the impact before marking bed out of service.');
      return;
    }
    try {
      setBedStatusSubmitting(true);
      setBedStatusError(null);
      await bedService.updateBedStatus(bedStatusModalContext.bedId, {
        status: bedStatusModalContext.toStatus,
        reason: bedStatusReason.trim() || undefined,
      });
      await Promise.all([loadBedBoard(), loadBedAdmissionActivity(), loadWardInventory()]);
      setBedActionSuccess(
        bedStatusModalContext.toStatus === 'OUT_OF_SERVICE'
          ? `Bed ${bedStatusModalContext.bedLabel} marked out of service.`
          : `Bed ${bedStatusModalContext.bedLabel} marked available.`
      );
      closeBedStatusModal();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setBedStatusError(detail || 'Unable to update bed status.');
      await Promise.all([loadBedBoard(), loadBedAdmissionActivity(), loadWardInventory()]);
    } finally {
      setBedStatusSubmitting(false);
    }
  };

  const openBedReleaseModal = (request: AdmissionRequest) => {
    if (!request.admission_id || request.admission_status !== 'ACTIVE') {
      setError('Admission must be active to release bed.');
      return;
    }
    setBedReleaseRequest(request);
    setBedReleaseReason('');
    setBedReleaseError(null);
    setBedReleaseSafetyChecked(false);
    setBedReleaseModalOpen(true);
  };

  const closeBedReleaseModal = () => {
    if (bedReleaseSubmitting) return;
    setBedReleaseModalOpen(false);
    setBedReleaseRequest(null);
    setBedReleaseReason('');
    setBedReleaseError(null);
    setBedReleaseSafetyChecked(false);
  };

  const submitBedRelease = async () => {
    if (!bedReleaseRequest?.admission_id || bedReleaseSubmitting) return;
    if (bedReleaseReason.trim().length < 3) {
      setBedReleaseError('Reason must be at least 3 characters.');
      return;
    }
    if (!bedReleaseSafetyChecked) {
      setBedReleaseError('Confirm the impact before releasing bed.');
      return;
    }
    try {
      setBedReleaseSubmitting(true);
      setBedReleaseError(null);
      await admissionRequestService.releaseBed(bedReleaseRequest.admission_id, {
        reason: bedReleaseReason.trim(),
      });
      await Promise.all([loadRequests(), loadBedBoard(), loadBedAdmissionActivity()]);
      setBedActionSuccess(
        `Bed released for ${
          bedReleaseRequest.patient_name ||
          `Patient ${maskId(bedReleaseRequest.patient_id)}`
        }.`
      );
      closeBedReleaseModal();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setBedReleaseError(detail || 'Unable to release bed.');
      await Promise.all([loadRequests(), loadBedBoard(), loadBedAdmissionActivity()]);
    } finally {
      setBedReleaseSubmitting(false);
    }
  };

  const openDischargeModal = (request: AdmissionRequest) => {
    if (!request.admission_id || request.admission_status !== 'ACTIVE') {
      setError('Admission must be active to discharge.');
      return;
    }
    setDischargeRequest(request);
    setDischargeDisposition('HOME');
    setDischargeReason('');
    setDischargeTransferredToFacility('');
    setDischargePronouncedAt('');
    setDischargeError(null);
    setDischargeSafetyChecked(false);
    setDischargeModalOpen(true);
  };

  const closeDischargeModal = () => {
    if (dischargeSubmitting) return;
    setDischargeModalOpen(false);
    setDischargeRequest(null);
    setDischargeDisposition('HOME');
    setDischargeReason('');
    setDischargeTransferredToFacility('');
    setDischargePronouncedAt('');
    setDischargeError(null);
    setDischargeSafetyChecked(false);
  };

  const submitDischarge = async () => {
    if (!dischargeRequest?.admission_id || dischargeSubmitting) return;
    if (dischargeReason.trim().length < 3) {
      setDischargeError('Discharge note must be at least 3 characters.');
      return;
    }
    if (
      dischargeDisposition === 'TRANSFERRED_OUT' &&
      dischargeTransferredToFacility.trim().length < 3
    ) {
      setDischargeError('Receiving facility must be at least 3 characters.');
      return;
    }
    if (dischargeDisposition === 'DECEASED' && !dischargePronouncedAt) {
      setDischargeError('Pronouncement time is required for deceased disposition.');
      return;
    }
    if (!dischargeSafetyChecked) {
      setDischargeError('Confirm the impact before discharging this admission.');
      return;
    }

    try {
      setDischargeSubmitting(true);
      setDischargeError(null);
      await admissionRequestService.dischargeAdmission(dischargeRequest.admission_id, {
        disposition: dischargeDisposition,
        discharge_notes: dischargeReason.trim(),
        transferred_to_facility:
          dischargeDisposition === 'TRANSFERRED_OUT'
            ? dischargeTransferredToFacility.trim()
            : null,
        death_pronounced_at:
          dischargeDisposition === 'DECEASED'
            ? new Date(dischargePronouncedAt).toISOString()
            : null,
      });
      await Promise.all([loadRequests(), loadBedBoard(), loadBedAdmissionActivity()]);
      setBedActionSuccess(
        `Admission discharged for ${
          dischargeRequest.patient_name ||
          `Patient ${maskId(dischargeRequest.patient_id)}`
        }.`
      );
      closeDischargeModal();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setDischargeError(detail || 'Unable to discharge admission.');
      await Promise.all([loadRequests(), loadBedBoard(), loadBedAdmissionActivity()]);
    } finally {
      setDischargeSubmitting(false);
    }
  };

  const closeOwnerReassignModal = () => {
    if (ownerReassignSubmitting) return;
    setOwnerReassignModalOpen(false);
    setOwnerReassignRequest(null);
    setOwnerReassignReason('');
    setOwnerReassignError(null);
    setAssignableStaffError(null);
    setOwnerReassignHandoverChecked(false);
  };

  const openOwnerReassignModal = async (request: AdmissionRequest) => {
    if (
      !request.active_visit_id ||
      request.active_visit_version === null ||
      request.active_visit_version === undefined ||
      !request.active_visit_service_line
    ) {
      setError('No active visit is linked for owner reassignment.');
      return;
    }

    try {
      setAssignableStaffLoading(true);
      setAssignableStaffError(null);
      const staff = await userService.listAssignableStaff();
      setAssignableStaff(staff);
      setOwnerReassignRequest(request);
      setOwnerReassignReason('Workflow handover');
      setOwnerReassignError(null);
      setOwnerReassignServiceLine(request.active_visit_service_line);
      setOwnerReassignHandoverChecked(false);

      const requiredRole = ownerRoleByServiceLine[request.active_visit_service_line];
      const eligible = staff.filter((member) => member.role === requiredRole);
      const defaultTarget =
        eligible.find((member) => member.id !== request.active_visit_owner_id)?.id ||
        eligible[0]?.id ||
        '';
      setOwnerReassignTargetId(defaultTarget);
      setOwnerReassignModalOpen(true);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setAssignableStaffError(detail || 'Unable to load assignable staff.');
    } finally {
      setAssignableStaffLoading(false);
    }
  };

  const submitOwnerReassign = async () => {
    if (!ownerReassignRequest || ownerReassignSubmitting) return;
    if (!ownerReassignRequest.active_visit_id || ownerReassignRequest.active_visit_version == null) {
      setOwnerReassignError('Active visit context missing.');
      return;
    }
    if (!ownerReassignTargetId) {
      setOwnerReassignError('Select a target owner.');
      return;
    }
    if (ownerReassignReason.trim().length < 3) {
      setOwnerReassignError('Reason must be at least 3 characters.');
      return;
    }
    if (isOwnerReassignNoOp) {
      setOwnerReassignError('Select a different owner or change service line.');
      return;
    }
    if (isOwnerServiceLineHandover && !ownerReassignHandoverChecked) {
      setOwnerReassignError('Confirm handover impact before changing service line.');
      return;
    }

    try {
      setOwnerReassignSubmitting(true);
      setOwnerReassignError(null);
      await visitService.reassignOwner(ownerReassignRequest.active_visit_id, {
        assigned_doctor_id: ownerReassignTargetId,
        expected_version: ownerReassignRequest.active_visit_version,
        service_line: ownerReassignServiceLine as SharedVisitServiceLine,
        reason: ownerReassignReason.trim(),
      });
      await Promise.all([
        loadRequests(),
        loadBedBoard(),
        loadBedAdmissionActivity(),
      ]);
      setBedActionSuccess('Visit owner reassigned successfully.');
      closeOwnerReassignModal();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setOwnerReassignError(detail || 'Unable to reassign visit owner.');
      await Promise.all([loadRequests(), loadBedBoard(), loadBedAdmissionActivity()]);
    } finally {
      setOwnerReassignSubmitting(false);
    }
  };

  const previewBedRange = async () => {
    const trimmedName = bedRangeWardName.trim();
    if (trimmedName.length < 2) {
      setBedRangeActionError('Ward name must be at least 2 characters.');
      return;
    }
    if (!bedRangePrefix.trim()) {
      setBedRangeActionError('Bed label prefix is required.');
      return;
    }
    if (bedRangeTo < bedRangeFrom) {
      setBedRangeActionError('Range end must be greater than or equal to start.');
      return;
    }
    try {
      setBedRangePreviewLoading(true);
      setBedRangeActionError(null);
      const preview = await bedService.previewWardBedRange({
        name: trimmedName,
        ward_type: bedRangeWardType,
        label_prefix: bedRangePrefix.trim(),
        label_from: bedRangeFrom,
        label_to: bedRangeTo,
        label_padding: bedRangePadding,
      });
      setBedRangePreview(preview);
      if (!preview.is_valid) {
        setBedRangeActionError('Resolve conflicts before confirming this bed range.');
      }
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setBedRangeActionError(detail || 'Unable to preview ward bed range.');
    } finally {
      setBedRangePreviewLoading(false);
    }
  };

  const confirmBedRange = async () => {
    if (!bedRangePreview || !bedRangePreview.is_valid) {
      setBedRangeActionError('Preview bed range before confirming.');
      return;
    }
    try {
      setBedRangeCreateLoading(true);
      setBedRangeActionError(null);
      const commit = await bedService.createWardWithBedRange({
        name: bedRangePreview.name,
        ward_type: bedRangePreview.ward_type as WardTypeValue,
        label_prefix: bedRangePreview.label_prefix,
        label_from: bedRangePreview.label_from,
        label_to: bedRangePreview.label_to,
        label_padding: bedRangePreview.label_padding,
      });
      setBedRangeActionSuccess(
        `Created ${commit.ward.name} with ${commit.created_beds} beds.`
      );
      setBedRangePreview(null);
      setBedRangeWardName('');
      setBedRangeFrom(1);
      setBedRangeTo(10);
      await Promise.all([loadBedBoard(), loadBedAdmissionActivity(), loadWardInventory()]);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setBedRangeActionError(detail || 'Unable to create ward with bed range.');
    } finally {
      setBedRangeCreateLoading(false);
    }
  };

  const handleAppendBed = async (ward: Ward) => {
    try {
      setAppendSubmitting(true);
      setAppendError(null);
      const response = await bedService.appendWardBed(ward.id);
      setBedRangeActionSuccess(`Added bed ${response.bed_label} to ${ward.name}.`);
      await Promise.all([loadBedBoard(), loadBedAdmissionActivity()]);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setAppendError(detail || 'Unable to add next bed.');
    } finally {
      setAppendSubmitting(false);
    }
  };

  const openRetireModal = (ward: Ward) => {
    setRetireWard(ward);
    setRetireReason('');
    setRetireError(null);
    setRetireModalOpen(true);
  };

  const closeRetireModal = () => {
    if (retireSubmitting) return;
    setRetireModalOpen(false);
    setRetireWard(null);
    setRetireReason('');
    setRetireError(null);
  };

  const confirmRetireBed = async () => {
    if (!retireWard) return;
    if (retireReason.trim().length < 3) {
      setRetireError('Reason must be at least 3 characters.');
      return;
    }
    try {
      setRetireSubmitting(true);
      setRetireError(null);
      const response = await bedService.retireLastWardBed(retireWard.id, {
        reason: retireReason.trim(),
      });
      setBedRangeActionSuccess(
        `Retired bed ${response.bed_label} from ${retireWard.name}.`
      );
      closeRetireModal();
      await Promise.all([loadBedBoard(), loadBedAdmissionActivity()]);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setRetireError(detail || 'Unable to retire last bed.');
    } finally {
      setRetireSubmitting(false);
    }
  };

  const openActiveToggleModal = (
    targetType: ActivityTargetType,
    targetId: string,
    targetLabel: string,
    fromActive: boolean,
    toActive: boolean
  ) => {
    setActiveToggleModalContext({
      targetType,
      targetId,
      targetLabel,
      fromActive,
      toActive,
    });
    setActiveToggleReason('');
    setActiveToggleError(null);
    setActiveToggleSafetyChecked(false);
    setActiveToggleModalOpen(true);
  };

  const closeActiveToggleModal = () => {
    if (activeToggleSubmitting) return;
    setActiveToggleModalOpen(false);
    setActiveToggleModalContext(null);
    setActiveToggleReason('');
    setActiveToggleError(null);
    setActiveToggleSafetyChecked(false);
  };

  const submitActiveToggle = async () => {
    if (!activeToggleModalContext || activeToggleSubmitting) return;
    const trimmedReason = activeToggleReason.trim();
    if (!activeToggleModalContext.toActive && trimmedReason.length < 3) {
      setActiveToggleError('Reason must be at least 3 characters.');
      return;
    }
    if (!activeToggleModalContext.toActive && !activeToggleSafetyChecked) {
      setActiveToggleError('Confirm the impact before deactivation.');
      return;
    }

    try {
      setActiveToggleSubmitting(true);
      setActiveToggleError(null);
      if (activeToggleModalContext.targetType === 'ward') {
        await bedService.updateWardActive(activeToggleModalContext.targetId, {
          active: activeToggleModalContext.toActive,
          reason: trimmedReason || undefined,
        });
      } else {
        await bedService.updateBedActive(activeToggleModalContext.targetId, {
          active: activeToggleModalContext.toActive,
          reason: trimmedReason || undefined,
        });
      }
      await loadBedBoard();
      setBedActionSuccess(
        `${activeToggleModalContext.targetType === 'ward' ? 'Ward' : 'Bed'} ${
          activeToggleModalContext.targetLabel
        } ${activeToggleModalContext.toActive ? 'reactivated' : 'deactivated'}.`
      );
      closeActiveToggleModal();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setActiveToggleError(detail || 'Unable to update activity state.');
      await loadBedBoard();
    } finally {
      setActiveToggleSubmitting(false);
    }
  };

  const boardWards: BedBoardWard[] = bedBoard
    ? bedBoardWardFilter === 'all'
      ? bedBoard.wards
      : bedBoard.wards.filter(
          (ward) => ward.summary.ward_id === bedBoardWardFilter
        )
    : [];
  const focusedWard =
    bedBoard && bedBoardWardFocus
      ? bedBoard.wards.find((ward) => ward.summary.ward_id === bedBoardWardFocus) || null
      : null;
  const assignableWards = wards.filter((ward) => ward.active);
  const wardSummaryById = (bedBoard?.wards || []).reduce<Record<string, BedBoardWard['summary']>>(
    (acc, ward) => {
      acc[ward.summary.ward_id] = ward.summary;
      return acc;
    },
    {}
  );
  const ownerEligibleStaff =
    ownerReassignModalOpen && ownerReassignRequest
      ? assignableStaff.filter(
          (member) => member.role === ownerRoleByServiceLine[ownerReassignServiceLine]
        )
      : [];
  const isOwnerServiceLineHandover =
    ownerReassignModalOpen &&
    !!ownerReassignRequest?.active_visit_service_line &&
    ownerReassignServiceLine !== ownerReassignRequest.active_visit_service_line;
  const isOwnerReassignNoOp =
    ownerReassignModalOpen &&
    !!ownerReassignRequest &&
    ownerReassignTargetId === ownerReassignRequest.active_visit_owner_id &&
    ownerReassignServiceLine === ownerReassignRequest.active_visit_service_line;
  const bedCapacityKnown = !bedBoardLoading && bedBoard !== null;
  const hasAvailableBeds = (bedBoard?.totals.available_beds ?? 0) > 0;

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
          Admission governance
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">
          Admission Requests
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Review doctor admission requests and approve or reject with audit
          reasons.
        </p>
      </section>

      <Card title="Ward Capacity Setup" className="order-4">
        <div className="space-y-6">
          <p className="text-sm text-slate-600">
            Build wards and generate bed ranges in one action. Bed history stays
            append-only and retirements are audit-safe.
          </p>

          {(bedRangeActionError || appendError || wardInventoryError) && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {bedRangeActionError || appendError || wardInventoryError}
            </div>
          )}

          {bedRangeActionSuccess && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {bedRangeActionSuccess}
            </div>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">
                Ward Bed Range Setup
              </p>
              <div className="mt-3 space-y-3">
                <Input
                  label="Ward name"
                  placeholder="Male Ward"
                  value={bedRangeWardName}
                  onChange={(event) => setBedRangeWardName(event.target.value)}
                />
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Ward type
                  </label>
                  <select
                    value={bedRangeWardType}
                    onChange={(event) =>
                      setBedRangeWardType(event.target.value as WardTypeValue)
                    }
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
                  >
                    {wardTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <Input
                    label="Bed label prefix"
                    placeholder="A-"
                    value={bedRangePrefix}
                    onChange={(event) => setBedRangePrefix(event.target.value)}
                  />
                  <Input
                    label="Padding"
                    type="number"
                    min={0}
                    max={6}
                    value={bedRangePadding}
                    onChange={(event) =>
                      setBedRangePadding(Number(event.target.value || 0))
                    }
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <Input
                    label="From"
                    type="number"
                    min={1}
                    value={bedRangeFrom}
                    onChange={(event) =>
                      setBedRangeFrom(Number(event.target.value || 1))
                    }
                  />
                  <Input
                    label="To"
                    type="number"
                    min={1}
                    value={bedRangeTo}
                    onChange={(event) => setBedRangeTo(Number(event.target.value || 1))}
                  />
                </div>
                <p className="text-xs text-slate-500">
                  Example: {formatWardLabel(bedRangePrefix || 'A-', bedRangeFrom, bedRangePadding)}{' '}
                  →{' '}
                  {formatWardLabel(bedRangePrefix || 'A-', bedRangeTo, bedRangePadding)}
                </p>
                <div className="flex justify-end">
                  <Button
                    size="sm"
                    onClick={previewBedRange}
                    isLoading={bedRangePreviewLoading}
                    disabled={listActionLocked || bedRangeWardName.trim().length < 2}
                  >
                    Preview Bed Range
                  </Button>
                </div>
              </div>

              {bedRangePreview && (
                <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {bedRangePreview.name} • {bedRangePreview.total_beds} beds
                      </p>
                      <p className="text-xs text-slate-500">
                        {formatWardLabel(
                          bedRangePreview.label_prefix,
                          bedRangePreview.label_from,
                          bedRangePreview.label_padding
                        )}{' '}
                        →{' '}
                        {formatWardLabel(
                          bedRangePreview.label_prefix,
                          bedRangePreview.label_to,
                          bedRangePreview.label_padding
                        )}
                      </p>
                    </div>
                    <Badge variant={bedRangePreview.is_valid ? 'success' : 'warning'} size="sm">
                      {bedRangePreview.is_valid ? 'Ready' : 'Conflict'}
                    </Badge>
                  </div>
                  {bedRangePreview.conflicts.length > 0 && (
                    <div className="mt-2 text-xs text-amber-700">
                      {bedRangePreview.conflicts.includes('WARD_NAME_EXISTS')
                        ? 'Ward name already exists. Choose a different name.'
                        : 'Resolve conflicts before confirming.'}
                    </div>
                  )}
                  <div className="mt-3 text-xs text-slate-500">
                    {bedRangePreview.bed_labels.slice(0, 8).join(', ')}
                    {bedRangePreview.bed_labels.length > 8
                      ? ` … +${bedRangePreview.bed_labels.length - 8} more`
                      : ''}
                  </div>
                  <div className="mt-4 flex justify-end gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setBedRangePreview(null)}
                      disabled={bedRangeCreateLoading}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      onClick={confirmBedRange}
                      isLoading={bedRangeCreateLoading}
                      disabled={!bedRangePreview.is_valid || bedRangeCreateLoading}
                    >
                      Confirm & Create
                    </Button>
                  </div>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">
                Ward Bed Controls
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Add or retire beds for wards configured with generated ranges.
              </p>
              <div className="mt-3 space-y-3">
                {wards.length === 0 && (
                  <div className="rounded-lg border border-slate-200 bg-white px-4 py-4 text-sm text-slate-500">
                    No wards configured yet.
                  </div>
                )}
                {wards.map((ward) => {
                  const summary = wardSummaryById[ward.id];
                  const nextLabel =
                    ward.bed_label_prefix && ward.bed_label_next
                      ? formatWardLabel(
                          ward.bed_label_prefix,
                          ward.bed_label_next,
                          ward.bed_label_padding
                        )
                      : null;
                  const canManageRangeBeds = !!ward.bed_label_prefix && ward.bed_label_next !== null;
                  return (
                    <div
                      key={ward.id}
                      className="rounded-lg border border-slate-200 bg-white px-4 py-3"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">
                            {ward.name}
                          </p>
                          <p className="text-xs text-slate-500">
                            {ward.ward_type} • {summary?.total_beds ?? 0} beds
                          </p>
                          {canManageRangeBeds && nextLabel && (
                            <p className="text-xs text-slate-500">
                              Next label: {nextLabel}
                            </p>
                          )}
                        </div>
                        <Badge
                          variant={ward.active ? 'success' : 'ghost'}
                          size="sm"
                        >
                          {ward.active ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleAppendBed(ward)}
                          disabled={!canManageRangeBeds || appendSubmitting}
                        >
                          + Add Next Bed
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => openRetireModal(ward)}
                          disabled={!canManageRangeBeds || retireSubmitting}
                        >
                          - Retire Last Bed
                        </Button>
                      </div>
                      {!canManageRangeBeds && (
                        <p className="mt-2 text-xs text-amber-700">
                          Bed controls require a label prefix and next-label configuration.
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Bed Board" className="order-2">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                Total {bedBoard?.totals.total_beds ?? 0}
              </span>
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs text-emerald-700">
                Available {bedBoard?.totals.available_beds ?? 0}
              </span>
              <span className="rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-700">
                Occupied {bedBoard?.totals.occupied_beds ?? 0}
              </span>
              <span className="rounded-full bg-rose-100 px-3 py-1 text-xs text-rose-700">
                Out of service {bedBoard?.totals.out_of_service_beds ?? 0}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {focusedWard && (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                  Selected ward: {focusedWard.summary.ward_name}
                </span>
              )}
              {focusedWard && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setBedBoardWardFocus(null);
                    setBedBoardWardFilter('all');
                  }}
                  disabled={bedActionSubmitting}
                >
                  Clear selection
                </Button>
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={loadBedBoard}
                isLoading={bedBoardLoading}
                disabled={bedActionSubmitting}
              >
                Refresh Board
              </Button>
            </div>
          </div>

          {bedBoardError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {bedBoardError}
            </div>
          )}

          {bedActionSuccess && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {bedActionSuccess}
            </div>
          )}

          {bedBoardLoading ? (
            <div className="space-y-3">
              <div className="shimmer h-12 rounded"></div>
              <div className="shimmer h-12 rounded"></div>
            </div>
          ) : boardWards.length === 0 ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
              No wards available for bed-board view.
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {boardWards.map((ward) => {
                const isFocused = bedBoardWardFocus === ward.summary.ward_id;
                return (
                  <button
                    key={ward.summary.ward_id}
                    type="button"
                    onClick={() => {
                      setBedBoardWardFocus(ward.summary.ward_id);
                      setBedBoardWardFilter(ward.summary.ward_id);
                    }}
                    className={`group rounded-xl border px-4 py-4 text-left transition ${
                      isFocused
                        ? 'border-slate-400 bg-white shadow-sm'
                        : 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white'
                    }`}
                    aria-pressed={isFocused}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">
                          {ward.summary.ward_name}
                        </p>
                        <p className="text-xs text-slate-500">
                          {ward.summary.ward_type} • {ward.summary.total_beds} beds
                        </p>
                      </div>
                      <span
                        className={`rounded-full px-2 py-1 text-xs ${
                          ward.summary.ward_active
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-slate-200 text-slate-700'
                        }`}
                      >
                        {ward.summary.ward_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                      <div className="rounded-lg bg-emerald-50 px-2 py-2 text-emerald-700">
                        <p className="text-[10px] uppercase tracking-wide text-emerald-600">
                          Avail
                        </p>
                        <p className="text-sm font-semibold">
                          {ward.summary.available_beds}
                        </p>
                      </div>
                      <div className="rounded-lg bg-amber-50 px-2 py-2 text-amber-700">
                        <p className="text-[10px] uppercase tracking-wide text-amber-600">
                          Occupied
                        </p>
                        <p className="text-sm font-semibold">
                          {ward.summary.occupied_beds}
                        </p>
                      </div>
                      <div className="rounded-lg bg-rose-50 px-2 py-2 text-rose-700">
                        <p className="text-[10px] uppercase tracking-wide text-rose-600">
                          OOS
                        </p>
                        <p className="text-sm font-semibold">
                          {ward.summary.out_of_service_beds}
                        </p>
                      </div>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                      <span>
                        {ward.summary.inactive_beds > 0
                          ? `${ward.summary.inactive_beds} inactive`
                          : 'All beds active'}
                      </span>
                      <span className="text-slate-400">
                        {isFocused ? 'Selected' : 'View beds'}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {focusedWard && (
            <div className="rounded-xl border border-slate-200 bg-white">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    Ward Resources • {focusedWard.summary.ward_name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {focusedWard.summary.ward_type} •{' '}
                    {focusedWard.summary.total_beds} beds
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      openActiveToggleModal(
                        'ward',
                        focusedWard.summary.ward_id,
                        focusedWard.summary.ward_name,
                        focusedWard.summary.ward_active,
                        !focusedWard.summary.ward_active
                      )
                    }
                    disabled={listActionLocked}
                  >
                    {focusedWard.summary.ward_active
                      ? 'Deactivate Ward'
                      : 'Reactivate Ward'}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setBedBoardWardFocus(null);
                      setBedBoardWardFilter('all');
                    }}
                  >
                    Close Ward
                  </Button>
                </div>
              </div>
              {focusedWard.beds.length === 0 ? (
                <p className="px-4 py-4 text-sm text-slate-500">
                  No beds configured in this ward.
                </p>
              ) : (
                <div className="grid gap-3 px-4 py-3 md:grid-cols-2">
                  {focusedWard.beds.map((bed) => {
                    const canMarkOutOfService =
                      bed.occupancy_status === 'AVAILABLE' && bed.bed_active;
                    const canMarkAvailable =
                      bed.occupancy_status === 'OUT_OF_SERVICE' && bed.bed_active;
                    const canDeactivateBed =
                      bed.bed_active && bed.occupancy_status !== 'OCCUPIED';
                    const canReactivateBed = !bed.bed_active;
                    return (
                      <div
                        key={bed.bed_id}
                        className="rounded-lg border border-slate-200 px-3 py-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-slate-900">
                            Bed {bed.bed_label}
                          </p>
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${occupancyBadgeClass[bed.occupancy_status]}`}
                          >
                            {bed.occupancy_status === 'OUT_OF_SERVICE'
                              ? 'Out of service'
                              : bed.occupancy_status}
                          </span>
                        </div>
                        <div className="mt-2 text-xs">
                          <span
                            className={`rounded-full px-2 py-0.5 ${
                              bed.bed_active
                                ? 'bg-emerald-100 text-emerald-700'
                                : 'bg-slate-200 text-slate-700'
                            }`}
                          >
                            {bed.bed_active ? 'Bed active' : 'Bed inactive'}
                          </span>
                        </div>
                        {bed.occupancy_status === 'OCCUPIED' && bed.occupant && (
                          <div className="mt-2 space-y-0.5 text-xs text-slate-600">
                            <p>
                              {bed.occupant.patient_name ||
                                `Patient ${maskId(bed.occupant.patient_id)}`}
                            </p>
                            <p>
                              {bed.occupant.patient_mrn
                                ? `MRN ${bed.occupant.patient_mrn}`
                                : `Patient ID ${maskId(bed.occupant.patient_id)}`}
                            </p>
                            <p>Admission {maskId(bed.occupant.admission_id)}</p>
                          </div>
                        )}
                        {(canMarkOutOfService || canMarkAvailable) && (
                          <div className="mt-3">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() =>
                                openBedStatusModal(
                                  bed.bed_id,
                                  bed.bed_label,
                                  focusedWard.summary.ward_name,
                                  canMarkOutOfService ? 'AVAILABLE' : 'OUT_OF_SERVICE',
                                  canMarkOutOfService ? 'OUT_OF_SERVICE' : 'AVAILABLE'
                                )
                              }
                              disabled={listActionLocked}
                            >
                              {canMarkOutOfService
                                ? 'Mark Out of Service'
                                : 'Mark Available'}
                            </Button>
                          </div>
                        )}
                        {(canDeactivateBed || canReactivateBed) && (
                          <div className="mt-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() =>
                                openActiveToggleModal(
                                  'bed',
                                  bed.bed_id,
                                  bed.bed_label,
                                  bed.bed_active,
                                  !bed.bed_active
                                )
                              }
                              disabled={listActionLocked}
                            >
                              {canDeactivateBed ? 'Deactivate Bed' : 'Reactivate Bed'}
                            </Button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          <div className="mt-6 border-t border-slate-200 pt-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-900">Occupied Beds</p>
                <p className="text-xs text-slate-500">
                  Search by patient name, MRN, or patient ID.
                </p>
              </div>
              <div className="w-full max-w-sm">
                <Input
                  label="Search"
                  placeholder="Name, MRN, patient ID..."
                  value={occupiedQuery}
                  onChange={(event) => setOccupiedQuery(event.target.value)}
                />
              </div>
            </div>

            {occupiedError && (
              <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {occupiedError}
              </div>
            )}

            <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
              <table className="min-w-full text-sm text-slate-700">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-4 py-3 text-left">Bed</th>
                    <th className="px-4 py-3 text-left">Ward</th>
                    <th className="px-4 py-3 text-left">Patient</th>
                    <th className="px-4 py-3 text-left">MRN</th>
                    <th className="px-4 py-3 text-left">Type</th>
                    <th className="px-4 py-3 text-left">Assigned</th>
                    <th className="px-4 py-3 text-left">Flags</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {occupiedLoading ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-6 text-center text-slate-500">
                        Loading occupied beds…
                      </td>
                    </tr>
                  ) : occupiedItems.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-6 text-center text-slate-500">
                        No occupied beds match this search.
                      </td>
                    </tr>
                  ) : (
                    occupiedItems.map((item) => (
                      <tr key={item.admission_id} className="border-t border-slate-100">
                        <td className="px-4 py-3 font-semibold text-slate-900">
                          {item.bed_label}
                        </td>
                        <td className="px-4 py-3">{item.ward_name}</td>
                        <td className="px-4 py-3">
                          {item.patient_name || `Patient ${maskId(item.patient_id)}`}
                        </td>
                        <td className="px-4 py-3">
                          {item.patient_mrn ? `MRN ${item.patient_mrn}` : '—'}
                        </td>
                        <td className="px-4 py-3">{item.admission_type}</td>
                        <td className="px-4 py-3">
                          {new Date(item.assigned_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3">
                          {renderInpatientFlags(item.review_due, item.chronic_due)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() =>
                              openOccupiedDetail(item.admission_id, item.ward_id)
                            }
                          >
                            View Details
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
              <span>
                Showing {occupiedItems.length} of {occupiedTotal} occupied beds
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    setOccupiedOffset(Math.max(0, occupiedOffset - occupiedLimit))
                  }
                  disabled={occupiedOffset === 0 || occupiedLoading}
                >
                  Prev
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    setOccupiedOffset(occupiedOffset + occupiedLimit)
                  }
                  disabled={
                    occupiedLoading || occupiedOffset + occupiedLimit >= occupiedTotal
                  }
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Recent Bed & Admission Activity" className="order-3">
        <div className="space-y-4">
          <div className="flex items-center justify-end">
            <Button
              variant="secondary"
              size="sm"
              onClick={loadBedAdmissionActivity}
              isLoading={activityLoading}
              disabled={listActionLocked}
            >
              Refresh Activity
            </Button>
          </div>

          {activityError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {activityError}
            </div>
          )}

          {activityLoading ? (
            <div className="space-y-3">
              <div className="shimmer h-10 rounded"></div>
              <div className="shimmer h-10 rounded"></div>
            </div>
          ) : activityItems.length === 0 ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
              No bed/admission activity logged yet.
            </div>
          ) : (
            <div className="space-y-2">
              {activityItems.map((item) => {
                const detail = getActivityDetail(item);
                const title =
                  item.event_type === 'ENTRY_AMENDED' && detail
                    ? 'Visit Owner Reassigned'
                    : formatEventLabel(item.event_type);
                return (
                <div
                  key={item.id}
                  className="flex flex-col gap-1 rounded-lg border border-slate-200 px-3 py-3 text-sm text-slate-700 md:flex-row md:items-center md:justify-between"
                >
                  <div className="space-y-0.5">
                    <p className="font-semibold text-slate-900">
                      {title}
                    </p>
                    <p className="text-xs text-slate-500">
                      Role {item.actor_role}
                      {item.patient_id ? ` • Patient ${maskId(item.patient_id)}` : ''}
                    </p>
                    {detail && (
                      <p className="text-xs text-slate-500">{detail}</p>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">
                    {new Date(item.occurred_at).toLocaleString()}
                  </p>
                </div>
                );
              })}
            </div>
          )}
        </div>
      </Card>

      <Card title="Requests Queue" className="order-1">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {(['PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'] as const).map(
              (status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  disabled={listActionLocked}
                  className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                    filter === status
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {statusLabels[status]}
                </button>
              )
            )}
          </div>

          {bedActionSuccess && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {bedActionSuccess}
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {loading ? (
            <div className="space-y-3">
              <div className="shimmer h-12 rounded"></div>
              <div className="shimmer h-12 rounded"></div>
            </div>
          ) : (
            <div className="space-y-3">
              {requests.length === 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                  No admission requests in this queue.
                </div>
              )}

              {requests.map((request) => {
                const isApprovedActiveAdmission =
                  request.status === 'APPROVED' &&
                  !!request.admission_id &&
                  request.admission_status === 'ACTIVE';
                const hasActiveBed = !!request.has_active_bed_assignment;
                const fallbackCanAssignBed =
                  isApprovedActiveAdmission &&
                  !hasActiveBed &&
                  (!bedCapacityKnown || hasAvailableBeds);
                const fallbackCanReassignBed =
                  isApprovedActiveAdmission &&
                  hasActiveBed &&
                  (!bedCapacityKnown || hasAvailableBeds);
                const fallbackCanReassignOwner =
                  isApprovedActiveAdmission &&
                  !!request.active_visit_id &&
                  !!request.active_visit_service_line &&
                  request.active_visit_version != null;
                const canAssignBed =
                  request.can_assign_bed ?? fallbackCanAssignBed;
                const canReassignBed =
                  request.can_reassign_bed ?? fallbackCanReassignBed;
                const canReassignOwner =
                  request.can_reassign_owner ?? fallbackCanReassignOwner;
                const canReleaseBed = isApprovedActiveAdmission && hasActiveBed;
                const hasReadyActions =
                  canReleaseBed || canAssignBed || canReassignBed || canReassignOwner;
                const readinessPrompts = (request.action_blockers ?? [])
                  .map((code) => blockerMessage[code] ?? null)
                  .filter((value): value is string => Boolean(value));
                if (readinessPrompts.length === 0) {
                  if (
                    isApprovedActiveAdmission &&
                    !hasActiveBed &&
                    bedCapacityKnown &&
                    !hasAvailableBeds
                  ) {
                    readinessPrompts.push(
                      'Assignment blocked: no available beds. Release a bed or reactivate capacity first.'
                    );
                  }
                  if (
                    isApprovedActiveAdmission &&
                    hasActiveBed &&
                    bedCapacityKnown &&
                    !hasAvailableBeds
                  ) {
                    readinessPrompts.push(
                      'Bed reassignment blocked: no destination bed is currently available.'
                    );
                  }
                  if (isApprovedActiveAdmission && !canReassignOwner) {
                    readinessPrompts.push(
                      'Owner reassignment blocked: active linked visit metadata is missing.'
                    );
                  }
                }

                return (
                <div
                  key={request.id}
                  className="flex flex-col gap-3 rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-700 md:flex-row md:items-center md:justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-slate-900">
                        {request.patient_name || `Patient ${maskId(request.patient_id)}`}
                      </span>
                      <Badge variant={statusVariant[request.status]} size="sm">
                        {statusLabels[request.status]}
                      </Badge>
                      {request.admission_status && (
                        <Badge
                          variant={admissionStatusVariant[request.admission_status]}
                          size="sm"
                        >
                          {admissionStatusLabels[request.admission_status]}
                        </Badge>
                      )}
                      <Badge variant="outline" size="sm">
                        {request.admission_type}
                      </Badge>
                      {isApprovedActiveAdmission && (
                        <Badge
                          variant={hasReadyActions ? 'success' : 'warning'}
                          size="sm"
                        >
                          {hasReadyActions ? 'Actions Ready' : 'Actions Blocked'}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-slate-500">
                      Requested {new Date(request.requested_at).toLocaleString()}
                    </p>
                    <p className="text-xs text-slate-500">
                      {request.patient_mrn
                        ? `MRN ${request.patient_mrn}`
                        : `Patient ID ${maskId(request.patient_id)}`}
                    </p>
                    <p className="text-xs text-slate-600">
                      Reason: {request.reason}
                    </p>
                    {request.active_visit_id && request.active_visit_service_line && (
                      <p className="text-xs text-slate-500">
                        Active visit {maskId(request.active_visit_id)} •{' '}
                        {serviceLineLabel[request.active_visit_service_line]} • Owner{' '}
                        {request.active_visit_owner_name ||
                          (request.active_visit_owner_id
                            ? maskId(request.active_visit_owner_id)
                            : '—')}
                      </p>
                    )}
                    {request.bed_timeline && request.bed_timeline.length > 0 && (
                      <div className="mt-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                          Bed Timeline
                        </p>
                        <div className="mt-1 space-y-1">
                          {request.bed_timeline.slice(0, 3).map((entry) => (
                            <p key={entry.assignment_id} className="text-xs text-slate-600">
                              {formatAssignmentLabel(entry.assignment_type)}
                              {entry.from_bed_label
                                ? ` ${entry.from_bed_label} -> ${entry.bed_label}`
                                : ` ${entry.bed_label}`}
                              {` • ${new Date(entry.assigned_at).toLocaleString()}`}
                              {entry.assigned_by_name
                                ? ` • ${entry.assigned_by_name}`
                                : ''}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                    {readinessPrompts.length > 0 && (
                      <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                          Action Readiness
                        </p>
                        <div className="mt-1 space-y-1">
                          {readinessPrompts.map((prompt) => (
                            <p key={prompt} className="text-xs text-amber-700">
                              {prompt}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {request.status === 'PENDING' && (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => openDecisionModal(request.id, 'approve')}
                        isLoading={actionLoading === request.id}
                        disabled={listActionLocked}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => openDecisionModal(request.id, 'reject')}
                        isLoading={actionLoading === request.id}
                        disabled={listActionLocked}
                      >
                        Reject
                      </Button>
                    </div>
                  )}

                  {isApprovedActiveAdmission && (
                    <div className="flex items-center gap-2">
                      {hasActiveBed ? (
                        <>
                          <Badge variant="outline" size="sm">
                            Bed {request.current_bed_label || 'Assigned'}
                          </Badge>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => openBedReleaseModal(request)}
                            disabled={listActionLocked}
                          >
                            Release Bed (Keep Active)
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openDischargeModal(request)}
                            disabled={listActionLocked}
                          >
                            Discharge Admission
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openBedActionModal(request, 'transfer')}
                            disabled={listActionLocked || !canReassignBed}
                          >
                            Reassign Bed
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openOwnerReassignModal(request)}
                            disabled={listActionLocked || !canReassignOwner}
                          >
                            Reassign Owner
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => openBedActionModal(request, 'assign')}
                            disabled={listActionLocked || !canAssignBed}
                          >
                            Assign Bed
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openDischargeModal(request)}
                            disabled={listActionLocked}
                          >
                            Discharge Admission
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openOwnerReassignModal(request)}
                            disabled={listActionLocked || !canReassignOwner}
                          >
                            Reassign Owner
                          </Button>
                        </>
                      )}
                    </div>
                    )}

                  {request.status === 'APPROVED' &&
                    (request.admission_status !== 'ACTIVE' || !request.admission_id) && (
                      <Badge variant="warning" size="sm">
                        {request.admission_status
                          ? `Admission ${request.admission_status.toLowerCase()} (read-only)`
                          : request.admission_id
                          ? 'Bed actions blocked: admission is not active'
                          : 'Admission record unavailable'}
                      </Badge>
                    )}
                </div>
                );
              })}
            </div>
          )}
        </div>
      </Card>

      {ownerReassignModalOpen && ownerReassignRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-xl rounded-2xl bg-white shadow-xl">
            <div className="border-b border-slate-200 px-6 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                Visit ownership
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">
                Reassign visit owner
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                Active visit{' '}
                {ownerReassignRequest.active_visit_id
                  ? maskId(ownerReassignRequest.active_visit_id)
                  : 'N/A'}
              </p>
            </div>
            <div className="space-y-4 px-6 py-5">
              {(ownerReassignError || assignableStaffError) && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {ownerReassignError || assignableStaffError}
                </div>
              )}
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Service line
                </label>
                <select
                  value={ownerReassignServiceLine}
                  onChange={(event) =>
                    setOwnerReassignServiceLine(event.target.value as VisitServiceLine)
                  }
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
                  disabled={ownerReassignSubmitting}
                >
                  {serviceLineOptions.map((line) => (
                    <option key={line} value={line}>
                      {serviceLineLabel[line]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Target owner
                </label>
                <select
                  value={ownerReassignTargetId}
                  onChange={(event) => setOwnerReassignTargetId(event.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
                  disabled={ownerReassignSubmitting || assignableStaffLoading}
                >
                  {ownerEligibleStaff.length === 0 && (
                    <option value="">No eligible staff for this service line</option>
                  )}
                  {ownerEligibleStaff.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.full_name || member.email}
                    </option>
                  ))}
                </select>
              </div>
              <Input
                label="Reason *"
                placeholder="Shift handover, workload balancing..."
                value={ownerReassignReason}
                onChange={(event) => setOwnerReassignReason(event.target.value)}
              />
              {isOwnerServiceLineHandover && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                  <p className="text-xs text-amber-800">
                    Changing service line transfers ownership across workflows.
                    Confirm handover to avoid losing continuity.
                  </p>
                  <label className="mt-2 flex items-center gap-2 text-xs text-amber-900">
                    <input
                      type="checkbox"
                      checked={ownerReassignHandoverChecked}
                      onChange={(event) =>
                        setOwnerReassignHandoverChecked(event.target.checked)
                      }
                      className="h-4 w-4 rounded border-amber-300 text-amber-700 focus:ring-amber-400"
                    />
                    I confirm the receiving service line has accepted this handover.
                  </label>
                </div>
              )}
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={closeOwnerReassignModal}
                disabled={ownerReassignSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={submitOwnerReassign}
                isLoading={ownerReassignSubmitting}
                disabled={
                  ownerReassignSubmitting ||
                  !ownerReassignTargetId ||
                  ownerReassignReason.trim().length < 3 ||
                  isOwnerReassignNoOp ||
                  (isOwnerServiceLineHandover && !ownerReassignHandoverChecked)
                }
              >
                Reassign Owner
              </Button>
            </div>
          </div>
        </div>
      )}

      {decisionModalOpen && decisionRequestId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
            <div className="border-b border-slate-200 px-6 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                Admission decision
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">
                {decisionAction === 'approve'
                  ? 'Approve admission request'
                  : 'Reject admission request'}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                Reason is required for audit traceability.
              </p>
            </div>

            <div className="space-y-4 px-6 py-5">
              {decisionError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {decisionError}
                </div>
              )}
              <Input
                label="Decision reason *"
                placeholder={
                  decisionAction === 'approve'
                    ? 'Approval justification'
                    : 'Rejection reason'
                }
                value={decisionReason}
                onChange={(event) => setDecisionReason(event.target.value)}
              />
              {decisionAction === 'reject' && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                  <p className="text-xs text-amber-800">
                    Rejecting stops admission workflow for this request and requires a new request to continue.
                  </p>
                  <label className="mt-2 flex items-center gap-2 text-xs text-amber-900">
                    <input
                      type="checkbox"
                      checked={decisionSafetyChecked}
                      onChange={(event) => setDecisionSafetyChecked(event.target.checked)}
                      className="h-4 w-4 rounded border-amber-300 text-amber-700 focus:ring-amber-400"
                    />
                    I understand this rejection blocks further bed actions for this request.
                  </label>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={closeDecisionModal}
                disabled={actionLoading !== null}
              >
                Cancel
              </Button>
              <Button
                variant={decisionAction === 'approve' ? 'primary' : 'danger'}
                size="sm"
                onClick={handleDecisionSubmit}
                isLoading={actionLoading !== null}
                disabled={
                  decisionReason.trim().length < 3 ||
                  (decisionAction === 'reject' && !decisionSafetyChecked)
                }
              >
                {decisionAction === 'approve' ? 'Approve' : 'Reject'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {bedStatusModalOpen && bedStatusModalContext && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
            <div className="border-b border-slate-200 px-6 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                Bed status update
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">
                {bedStatusModalContext.toStatus === 'OUT_OF_SERVICE'
                  ? 'Mark bed out of service'
                  : 'Mark bed available'}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                Bed {bedStatusModalContext.bedLabel} • {bedStatusModalContext.wardName}
              </p>
            </div>
            <div className="space-y-4 px-6 py-5">
              {bedStatusError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {bedStatusError}
                </div>
              )}
              <Input
                label={
                  bedStatusModalContext.toStatus === 'OUT_OF_SERVICE'
                    ? 'Reason *'
                    : 'Reason (optional)'
                }
                placeholder={
                  bedStatusModalContext.toStatus === 'OUT_OF_SERVICE'
                    ? 'Maintenance, cleaning, repair...'
                    : 'Optional note'
                }
                value={bedStatusReason}
                onChange={(event) => setBedStatusReason(event.target.value)}
              />
              {bedStatusModalContext.toStatus === 'OUT_OF_SERVICE' && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                  <p className="text-xs text-amber-800">
                    This removes the bed from operational capacity until it is marked available again.
                  </p>
                  <label className="mt-2 flex items-center gap-2 text-xs text-amber-900">
                    <input
                      type="checkbox"
                      checked={bedStatusSafetyChecked}
                      onChange={(event) => setBedStatusSafetyChecked(event.target.checked)}
                      className="h-4 w-4 rounded border-amber-300 text-amber-700 focus:ring-amber-400"
                    />
                    I confirm this bed should be out of service now.
                  </label>
                </div>
              )}
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={closeBedStatusModal}
                disabled={bedStatusSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={submitBedStatusChange}
                isLoading={bedStatusSubmitting}
                disabled={
                  bedStatusSubmitting ||
                  (bedStatusModalContext.toStatus === 'OUT_OF_SERVICE' &&
                    (bedStatusReason.trim().length < 3 || !bedStatusSafetyChecked))
                }
              >
                Confirm
              </Button>
            </div>
          </div>
        </div>
      )}

      {activeToggleModalOpen && activeToggleModalContext && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
            <div className="border-b border-slate-200 px-6 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                Capacity activity
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">
                {activeToggleModalContext.toActive ? 'Reactivate' : 'Deactivate'}{' '}
                {activeToggleModalContext.targetType === 'ward' ? 'ward' : 'bed'}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {activeToggleModalContext.targetLabel}
              </p>
            </div>
            <div className="space-y-4 px-6 py-5">
              {activeToggleError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {activeToggleError}
                </div>
              )}
              <Input
                label={activeToggleModalContext.toActive ? 'Reason (optional)' : 'Reason *'}
                placeholder={
                  activeToggleModalContext.toActive
                    ? 'Optional note'
                    : 'Reason for deactivation'
                }
                value={activeToggleReason}
                onChange={(event) => setActiveToggleReason(event.target.value)}
              />
              {!activeToggleModalContext.toActive && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                  <p className="text-xs text-amber-800">
                    Deactivation blocks new assignments and may affect downstream workflow until reactivated.
                  </p>
                  <label className="mt-2 flex items-center gap-2 text-xs text-amber-900">
                    <input
                      type="checkbox"
                      checked={activeToggleSafetyChecked}
                      onChange={(event) => setActiveToggleSafetyChecked(event.target.checked)}
                      className="h-4 w-4 rounded border-amber-300 text-amber-700 focus:ring-amber-400"
                    />
                    I confirm this capacity should be deactivated now.
                  </label>
                </div>
              )}
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={closeActiveToggleModal}
                disabled={activeToggleSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={submitActiveToggle}
                isLoading={activeToggleSubmitting}
                disabled={
                  activeToggleSubmitting ||
                  (!activeToggleModalContext.toActive &&
                    (activeToggleReason.trim().length < 3 || !activeToggleSafetyChecked))
                }
              >
                Confirm
              </Button>
            </div>
          </div>
        </div>
      )}

      {bedReleaseModalOpen && bedReleaseRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
            <div className="border-b border-slate-200 px-6 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                Bed release
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">
                Release bed (keep admission active)
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {bedReleaseRequest.patient_name ||
                  `Patient ${maskId(bedReleaseRequest.patient_id)}`}{' '}
                • Admission{' '}
                {bedReleaseRequest.admission_id
                  ? maskId(bedReleaseRequest.admission_id)
                  : 'N/A'}
              </p>
            </div>
            <div className="space-y-4 px-6 py-5">
              {bedReleaseError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {bedReleaseError}
                </div>
              )}
              <Input
                label="Release reason *"
                placeholder="Patient moved, temporary discharge, cleaning..."
                value={bedReleaseReason}
                onChange={(event) => setBedReleaseReason(event.target.value)}
              />
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                <p className="text-xs text-amber-800">
                  Releasing bed does not discharge this patient. Admission stays active and can be reassigned.
                </p>
                <label className="mt-2 flex items-center gap-2 text-xs text-amber-900">
                  <input
                    type="checkbox"
                    checked={bedReleaseSafetyChecked}
                    onChange={(event) => setBedReleaseSafetyChecked(event.target.checked)}
                    className="h-4 w-4 rounded border-amber-300 text-amber-700 focus:ring-amber-400"
                  />
                  I confirm this patient should no longer hold the current bed.
                </label>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={closeBedReleaseModal}
                disabled={bedReleaseSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={submitBedRelease}
                isLoading={bedReleaseSubmitting}
                disabled={
                  bedReleaseSubmitting ||
                  bedReleaseReason.trim().length < 3 ||
                  !bedReleaseSafetyChecked
                }
              >
                Release Bed (Keep Active)
              </Button>
            </div>
          </div>
        </div>
      )}

      {retireModalOpen && retireWard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
            <div className="border-b border-slate-200 px-6 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                Bed retirement
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">
                Retire last bed in {retireWard.name}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                This retires the most recently generated bed if it is not occupied.
              </p>
            </div>
            <div className="space-y-4 px-6 py-5">
              {retireError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {retireError}
                </div>
              )}
              <Input
                label="Retirement reason *"
                placeholder="Capacity reduction, renovation..."
                value={retireReason}
                onChange={(event) => setRetireReason(event.target.value)}
              />
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={closeRetireModal}
                disabled={retireSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={confirmRetireBed}
                isLoading={retireSubmitting}
                disabled={retireSubmitting || retireReason.trim().length < 3}
              >
                Retire Bed
              </Button>
            </div>
          </div>
        </div>
      )}

      {occupiedDetailOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white shadow-xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                  Occupied bed detail
                </p>
                <h2 className="mt-1 text-xl font-semibold text-slate-900">
                  Admission bed timeline
                </h2>
              </div>
              <button
                onClick={closeOccupiedDetail}
                className="text-2xl text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            </div>
            <div className="space-y-4 px-6 py-5">
              {occupiedDetailError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {occupiedDetailError}
                </div>
              )}
              {occupiedDetailLoading ? (
                <div className="space-y-3">
                  <div className="shimmer h-10 rounded"></div>
                  <div className="shimmer h-10 rounded"></div>
                </div>
              ) : occupiedDetail ? (
                <>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    <p className="font-semibold text-slate-900">
                      {occupiedDetail.patient_name ||
                        `Patient ${maskId(occupiedDetail.patient_id)}`}
                    </p>
                    <p className="text-xs text-slate-500">
                      {occupiedDetail.patient_mrn
                        ? `MRN ${occupiedDetail.patient_mrn}`
                        : `Patient ID ${maskId(occupiedDetail.patient_id)}`}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Admission {occupiedDetail.admission_type} •{' '}
                      {occupiedDetail.ward_name || 'Ward'}
                    </p>
                    <div className="mt-2">
                      {renderInpatientFlags(
                        occupiedDetail.review_due,
                        occupiedDetail.chronic_due
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      Bed Timeline
                    </p>
                    {occupiedDetail.timeline.length === 0 ? (
                      <p className="mt-2 text-sm text-slate-500">
                        No bed history recorded yet.
                      </p>
                    ) : (
                      <div className="mt-2 space-y-2">
                        {occupiedDetail.timeline.map((entry) => (
                          <div
                            key={entry.assignment_id}
                            className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-600"
                          >
                            <p className="font-semibold text-slate-900">
                              {entry.assignment_type === 'ASSIGN'
                                ? 'Assigned'
                                : 'Transferred'}{' '}
                              • {entry.ward_name}
                            </p>
                            <p>
                              {new Date(entry.assigned_at).toLocaleString()}
                              {entry.released_at
                                ? ` → ${new Date(entry.released_at).toLocaleString()}`
                                : ''}
                            </p>
                            {entry.reason && <p>Reason: {entry.reason}</p>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              ) : null}
            </div>
            <div className="flex items-center justify-end border-t border-slate-200 px-6 py-4">
              <Button variant="secondary" size="sm" onClick={closeOccupiedDetail}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {dischargeModalOpen && dischargeRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
            <div className="border-b border-slate-200 px-6 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                Admission discharge
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">
                Discharge active admission
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {dischargeRequest.patient_name ||
                  `Patient ${maskId(dischargeRequest.patient_id)}`}{' '}
                • Admission{' '}
                {dischargeRequest.admission_id
                  ? maskId(dischargeRequest.admission_id)
                  : 'N/A'}
              </p>
            </div>
            <div className="space-y-4 px-6 py-5">
              {dischargeError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {dischargeError}
                </div>
              )}
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Disposition
                </label>
                <select
                  value={dischargeDisposition}
                  onChange={(event) =>
                    setDischargeDisposition(
                      event.target.value as AdmissionDischargeDisposition
                    )
                  }
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
                  disabled={dischargeSubmitting}
                >
                  <option value="HOME">Home</option>
                  <option value="TRANSFERRED_OUT">Transferred Out</option>
                  <option value="LAMA">LAMA</option>
                  <option value="ELOPED">Eloped</option>
                  <option value="DECEASED">Deceased</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
              {dischargeDisposition === 'TRANSFERRED_OUT' && (
                <Input
                  label="Receiving facility *"
                  placeholder="Receiving hospital name"
                  value={dischargeTransferredToFacility}
                  onChange={(event) =>
                    setDischargeTransferredToFacility(event.target.value)
                  }
                />
              )}
              {dischargeDisposition === 'DECEASED' && (
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Pronounced at *
                  </label>
                  <input
                    type="datetime-local"
                    value={dischargePronouncedAt}
                    onChange={(event) => setDischargePronouncedAt(event.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
                    disabled={dischargeSubmitting}
                  />
                </div>
              )}
              <Input
                label="Discharge note *"
                placeholder="Clinical/operational discharge reason..."
                value={dischargeReason}
                onChange={(event) => setDischargeReason(event.target.value)}
              />
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                <p className="text-xs text-amber-800">
                  Discharging closes this admission and any remaining bed assignment is
                  auto-released.
                </p>
                <label className="mt-2 flex items-center gap-2 text-xs text-amber-900">
                  <input
                    type="checkbox"
                    checked={dischargeSafetyChecked}
                    onChange={(event) => setDischargeSafetyChecked(event.target.checked)}
                    className="h-4 w-4 rounded border-amber-300 text-amber-700 focus:ring-amber-400"
                  />
                  I confirm this admission should be closed now.
                </label>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={closeDischargeModal}
                disabled={dischargeSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={submitDischarge}
                isLoading={dischargeSubmitting}
                disabled={
                  dischargeSubmitting ||
                  dischargeReason.trim().length < 3 ||
                  (dischargeDisposition === 'TRANSFERRED_OUT' &&
                    dischargeTransferredToFacility.trim().length < 3) ||
                  (dischargeDisposition === 'DECEASED' && !dischargePronouncedAt) ||
                  !dischargeSafetyChecked
                }
              >
                Discharge Admission
              </Button>
            </div>
          </div>
        </div>
      )}

      {bedActionModalOpen && bedActionRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="bed-action-dialog-title"
            className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
          >
            <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                  {bedActionMode === 'assign' ? 'Bed assignment' : 'Bed reassignment'}
                </p>
                <h2
                  id="bed-action-dialog-title"
                  className="mt-1 text-xl font-semibold text-slate-900"
                >
                  {bedActionMode === 'assign'
                    ? 'Assign bed for admission'
                    : 'Reassign bed for admission'}
                </h2>
                <p className="mt-1 text-sm text-slate-600">
                  Patient {maskId(bedActionRequest.patient_id)} • Admission{' '}
                  {bedActionRequest.admission_id
                    ? maskId(bedActionRequest.admission_id)
                    : 'Not created'}
                </p>
              </div>
              <button
                onClick={closeBedActionModal}
                disabled={bedActionSubmitting}
                className="text-2xl text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            </div>

            <div className="flex-1 space-y-6 overflow-y-auto px-6 py-5">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                {bedActionMode === 'assign'
                  ? 'Use Assign Bed when the patient has no current bed.'
                  : 'Use Reassign Bed only when the patient already has an active bed assignment.'}
              </div>

              {bedActionMode === 'transfer' && bedActionRequest.current_bed_label && (
                <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                  Current bed: <span className="font-semibold">{bedActionRequest.current_bed_label}</span>
                </div>
              )}

              {bedActionError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {bedActionError}
                </div>
              )}
              {bedActionMode === 'transfer' && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                  <p className="text-xs text-amber-800">
                    Reassigning bed releases current occupancy and allocates the new
                    bed immediately.
                  </p>
                  <label className="mt-2 flex items-center gap-2 text-xs text-amber-900">
                    <input
                      type="checkbox"
                      checked={bedActionSafetyChecked}
                      onChange={(event) =>
                        setBedActionSafetyChecked(event.target.checked)
                      }
                      className="h-4 w-4 rounded border-amber-300 text-amber-700 focus:ring-amber-400"
                    />
                    I confirm handover is complete and this transfer should proceed.
                  </label>
                </div>
              )}

              <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
                <div className="space-y-3">
                  <label
                    htmlFor="bed-action-ward-select"
                    className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400"
                  >
                    Ward
                  </label>
                  <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
                    <select
                      id="bed-action-ward-select"
                      value={selectedWard}
                      disabled={bedsLoading || bedActionSubmitting}
                      onChange={async (event) => {
                        const next = event.target.value;
                        setSelectedWard(next);
                        setSelectedBedId('');
                        await loadAvailableBeds(next);
                      }}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
                    >
                      {assignableWards.length === 0 && (
                        <option value="">No wards available</option>
                      )}
                      {assignableWards.map((ward) => (
                        <option key={ward.id} value={ward.id}>
                          {ward.name}
                        </option>
                      ))}
                    </select>
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                      <span>
                        {selectedWard
                          ? wards.find((ward) => ward.id === selectedWard)?.ward_type ||
                            'Ward'
                          : 'Select a ward'}
                      </span>
                      <span>{bedsLoading ? 'Loading' : `${beds.length} available`}</span>
                    </div>
                  </div>
                  {selectedBedId ? (
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs text-emerald-700">
                      Selected bed ready for assignment.
                    </div>
                  ) : (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-500">
                      Select a bed from the list to continue.
                    </div>
                  )}
                </div>

                <div className="flex-1">
                  <Input
                    label={
                      bedActionMode === 'assign'
                        ? 'Assignment note (optional)'
                        : 'Reassignment reason *'
                    }
                    placeholder={
                      bedActionMode === 'assign'
                        ? 'Reason or placement note'
                        : 'Reason for reassignment'
                    }
                    value={bedActionReason}
                    onChange={(event) => setBedActionReason(event.target.value)}
                  />
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-sm font-semibold text-slate-900">
                    Available beds
                  </p>
                  <span className="text-xs text-slate-500">
                    {bedsLoading ? 'Loading…' : `${beds.length} available`}
                  </span>
                </div>

                <div className="max-h-[45vh] overflow-y-auto pr-2">
                  {bedsLoading ? (
                    <div className="space-y-3">
                      <div className="shimmer h-12 rounded-lg"></div>
                      <div className="shimmer h-12 rounded-lg"></div>
                      <div className="shimmer h-12 rounded-lg"></div>
                    </div>
                  ) : beds.length === 0 ? (
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                      No available beds for the selected ward.
                    </div>
                  ) : (
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {beds.map((bed) => {
                        const ward = wards.find((item) => item.id === bed.ward_id);
                        const selected = selectedBedId === bed.id;
                        return (
                          <button
                            key={bed.id}
                            type="button"
                            disabled={bedActionSubmitting}
                            onClick={() => setSelectedBedId(bed.id)}
                            aria-pressed={selected}
                            className={`flex flex-col items-start gap-2 rounded-xl border px-4 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300 ${
                              selected
                                ? 'border-sky-400 bg-sky-50 text-slate-900 ring-1 ring-sky-200'
                                : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'
                            }`}
                          >
                            <div className="flex w-full items-start justify-between gap-2">
                              <div>
                                <p className="text-sm font-semibold">
                                  Bed {bed.bed_label}
                                </p>
                                <p className="text-xs text-slate-500">
                                  {ward?.name || 'Unassigned ward'}
                                </p>
                              </div>
                              <span
                                className={`rounded-full px-2 py-0.5 text-xs ${
                                  selected
                                    ? 'bg-emerald-100 text-emerald-700'
                                    : 'bg-slate-100 text-slate-600'
                                }`}
                              >
                                Available
                              </span>
                            </div>
                            {selected && (
                              <div className="text-xs text-sky-700">
                                Selected for assignment
                              </div>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
              <p className="text-xs text-slate-500">
                {bedActionMode === 'assign'
                  ? 'Assignment will reserve the bed immediately.'
                  : 'Reassignment will release current bed and reserve the new bed.'}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={closeBedActionModal}
                  disabled={bedActionSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSubmitBedAction}
                  isLoading={bedActionSubmitting}
                  disabled={
                    bedActionSubmitting ||
                    !selectedBedId ||
                    (bedActionMode === 'transfer' &&
                      (bedActionReason.trim().length < 3 || !bedActionSafetyChecked))
                  }
                >
                  {bedActionMode === 'assign' ? 'Assign Bed' : 'Reassign Bed'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
