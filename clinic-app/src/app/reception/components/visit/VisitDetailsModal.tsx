'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  visitService,
  VisitTimelineResponse,
  AllowedTransitionsResponse,
} from '@/domains/visit/services/visitService';
import { pmrService, PMRResponse } from '@/domains/pmr/services/pmrService';
import { PurposeOfUse, VisitServiceLine, VisitStatus } from '@/shared/enums';
import { VisitResponse } from '@/shared/types';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';
import { VisitTimeline } from './VisitTimeline';
import { QuickActionButtons } from './QuickActionButtons';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Tooltip } from '@/shared/Tooltip';
import { admissionRequestService, AdmissionType } from '@/domains/admission/services/admissionRequestService';
import { roleSessionService } from '@/domains/auth/services/roleSessionService';
import { UserRole } from '@/shared/enums';
import { userService, Doctor } from '@/domains/user/services/userService';

interface VisitDetailsModalProps {
  visitId: string | null;
  isOpen: boolean;
  onClose: () => void;
  hiddenTransitions?: string[];
  purposeOfUse?: PurposeOfUse;
  allowAdmissionRequest?: boolean;
}

export function VisitDetailsModal({
  visitId,
  isOpen,
  onClose,
  hiddenTransitions,
  purposeOfUse = PurposeOfUse.OPERATIONS,
  allowAdmissionRequest = false,
}: VisitDetailsModalProps) {
  const getErrorDetail = (err: unknown) => {
    if (!err || typeof err !== 'object' || !('response' in err)) {
      return null;
    }
    const detail = (err as { response?: { data?: { detail?: unknown } } })
      .response?.data?.detail;
    return typeof detail === 'string' ? detail : null;
  };
  const [visit, setVisit] = useState<VisitResponse | null>(null);
  const [timeline, setTimeline] = useState<VisitTimelineResponse | null>(null);
  const [allowedTransitions, setAllowedTransitions] =
    useState<AllowedTransitionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'details' | 'timeline' | 'pmr'>(
    'details'
  );
  const [pmr, setPmr] = useState<PMRResponse | null>(null);
  const [pmrLoading, setPmrLoading] = useState(false);
  const [pmrError, setPmrError] = useState<string | null>(null);
  const [pmrErrorStatus, setPmrErrorStatus] = useState<number | null>(null);
  const [showPmrPrompt, setShowPmrPrompt] = useState(false);
  const [pmrJustification, setPmrJustification] = useState('');
  const [issuingMrn, setIssuingMrn] = useState(false);
  const [mrnIssueError, setMrnIssueError] = useState<string | null>(null);
  const [canIssueMrn, setCanIssueMrn] = useState(false);
  const [showEmergencyPrompt, setShowEmergencyPrompt] = useState(false);
  const [emergencyReason, setEmergencyReason] = useState('');
  const [emergencyError, setEmergencyError] = useState<string | null>(null);
  const [emergencySubmitting, setEmergencySubmitting] = useState(false);
  const [showAdmissionPrompt, setShowAdmissionPrompt] = useState(false);
  const [admissionType, setAdmissionType] = useState<AdmissionType>('EMERGENCY');
  const [admissionReason, setAdmissionReason] = useState('');
  const [admissionError, setAdmissionError] = useState<string | null>(null);
  const [admissionSubmitting, setAdmissionSubmitting] = useState(false);
  const [admissionSuccess, setAdmissionSuccess] = useState<string | null>(null);
  const [hasPendingAdmissionRequest, setHasPendingAdmissionRequest] = useState(false);
  const [recheckLoading, setRecheckLoading] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    type: 'success' | 'error';
  } | null>(null);
  const [currentUserRole, setCurrentUserRole] = useState<UserRole | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [showReassignPrompt, setShowReassignPrompt] = useState(false);
  const [reassignReason, setReassignReason] = useState('');
  const [reassignTargetId, setReassignTargetId] = useState('');
  const [reassigning, setReassigning] = useState(false);
  const [reassignError, setReassignError] = useState<string | null>(null);
  const [assignableStaff, setAssignableStaff] = useState<Doctor[]>([]);
  const [loadingAssignableStaff, setLoadingAssignableStaff] = useState(false);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [expandedClinicalHistoryVisitId, setExpandedClinicalHistoryVisitId] =
    useState<string | null>(null);
  const didAutoExpandClinicalHistoryRef = useRef(false);

  const loadVisitDetails = useCallback(async () => {
    if (!visitId) return;

    try {
      setLoading(true);
      setError(null);

      const [visitData, timelineData, transitionsData] = await Promise.all([
        visitService.getVisit(visitId),
        visitService.getVisitTimeline(visitId, purposeOfUse),
        visitService.getAllowedTransitions(visitId),
      ]);

      setVisit(visitData);
      setTimeline(timelineData);
      setAllowedTransitions(transitionsData);
    } catch (err: unknown) {
      console.error('Failed to load visit details:', err);
      setError(getErrorDetail(err) || 'Failed to load visit details');
    } finally {
      setLoading(false);
    }
  }, [purposeOfUse, visitId]);

  useEffect(() => {
    if (isOpen && visitId) {
      setPmrJustification('');
      setPmrError(null);
      setPmrErrorStatus(null);
      setShowPmrPrompt(false);
      setToast(null);
      setAdmissionReason('');
      setAdmissionError(null);
      setAdmissionSuccess(null);
      setShowAdmissionPrompt(false);
      setHasPendingAdmissionRequest(false);
      setExpandedClinicalHistoryVisitId(null);
      didAutoExpandClinicalHistoryRef.current = false;
      loadVisitDetails();
      roleSessionService
        .getCurrentUser()
        .then((user) => {
          setCurrentUserRole(user.role as UserRole);
          setCurrentUserId(user.id);
          setCanIssueMrn(
            user.role === UserRole.RECEPTION ||
              user.role === UserRole.CLINIC_ADMIN
          );
        })
        .catch(() => {
          setCanIssueMrn(false);
          setCurrentUserRole(null);
          setCurrentUserId(null);
        });
    } else {
      resetState();
    }
  }, [isOpen, visitId, loadVisitDetails]);

  useEffect(() => {
    if (!isOpen) return;
    if (!pmr?.clinical_history?.length) return;
    if (didAutoExpandClinicalHistoryRef.current) return;

    // Auto-expand the most recent clinical-history row once per modal open.
    setExpandedClinicalHistoryVisitId(pmr.clinical_history[0].visit_id);
    didAutoExpandClinicalHistoryRef.current = true;
  }, [isOpen, pmr]);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
    };
  }, []);

  const resetState = () => {
    setVisit(null);
    setTimeline(null);
    setAllowedTransitions(null);
    setError(null);
    setLoading(false);
    setPmr(null);
    setPmrError(null);
    setPmrErrorStatus(null);
    setPmrLoading(false);
    setShowPmrPrompt(false);
    setPmrJustification('');
    setExpandedClinicalHistoryVisitId(null);
    didAutoExpandClinicalHistoryRef.current = false;
    setIssuingMrn(false);
    setMrnIssueError(null);
    setCanIssueMrn(false);
    setShowEmergencyPrompt(false);
    setEmergencyReason('');
    setEmergencyError(null);
    setEmergencySubmitting(false);
    setShowAdmissionPrompt(false);
    setAdmissionReason('');
    setAdmissionError(null);
    setAdmissionSubmitting(false);
    setAdmissionSuccess(null);
    setHasPendingAdmissionRequest(false);
    setRecheckLoading(false);
    setToast(null);
    setCurrentUserRole(null);
    setCurrentUserId(null);
    setShowReassignPrompt(false);
    setReassignReason('');
    setReassignTargetId('');
    setReassigning(false);
    setReassignError(null);
    setAssignableStaff([]);
    setLoadingAssignableStaff(false);
  };

  const handleStatusChange = (newStatus: string) => {
    if (visit) {
      setVisit({ ...visit, status: newStatus as VisitStatus });
      loadVisitDetails();
    }
  };

  const handleVisitUpdated = (updated: VisitResponse) => {
    setVisit(updated);
    loadVisitDetails();
  };

  const getOwnerRoleForServiceLine = (serviceLine?: string) => {
    if (serviceLine === 'ANC') return UserRole.CHEW;
    if (serviceLine === 'MATERNITY') return UserRole.MIDWIFE;
    return UserRole.DOCTOR;
  };

  const getOwnerLabelForServiceLine = (serviceLine?: string) => {
    if (serviceLine === 'ANC') return 'CHEW';
    if (serviceLine === 'MATERNITY') return 'Midwife';
    return 'Doctor';
  };

  const getServiceLineForRole = (role?: string): VisitServiceLine | null => {
    if (role === UserRole.CHEW) return VisitServiceLine.ANC;
    if (role === UserRole.MIDWIFE) return VisitServiceLine.MATERNITY;
    if (role === UserRole.DOCTOR) return VisitServiceLine.OPD;
    return null;
  };

  const canReassignCurrentVisit = () => {
    if (!visit || !currentUserRole) return false;
    if (
      visit.status === VisitStatus.COMPLETED ||
      visit.status === VisitStatus.CANCELLED
    ) {
      return false;
    }
    if (
      currentUserRole === UserRole.RECEPTION ||
      currentUserRole === UserRole.CLINIC_ADMIN ||
      currentUserRole === UserRole.ADMIN
    ) {
      return true;
    }
    const ownerRole = getOwnerRoleForServiceLine(visit.service_line);
    return (
      currentUserRole === ownerRole &&
      currentUserId === visit.assigned_doctor_id
    );
  };

  const loadAssignableOwners = async () => {
    if (!visit) return;
    try {
      setLoadingAssignableStaff(true);
      const staff = await userService.listAssignableStaff();
      const isAdminRole =
        currentUserRole === UserRole.RECEPTION ||
        currentUserRole === UserRole.CLINIC_ADMIN ||
        currentUserRole === UserRole.ADMIN;
      const roleKey = getOwnerRoleForServiceLine(visit.service_line);
      const filtered = isAdminRole
        ? staff
        : staff.filter((member) => member.role === roleKey);
      setAssignableStaff(filtered);
      const defaultTarget =
        filtered.find((member) => member.id !== visit.assigned_doctor_id)?.id ??
        '';
      setReassignTargetId(defaultTarget);
    } catch {
      setAssignableStaff([]);
      setReassignTargetId('');
      setReassignError('Unable to load assignable colleagues.');
    } finally {
      setLoadingAssignableStaff(false);
    }
  };

  const handleOpenReassignPrompt = async () => {
    if (!visit) return;
    setReassignError(null);
    setReassignReason('');
    setShowReassignPrompt(true);
    await loadAssignableOwners();
  };

  const handleSubmitReassign = async () => {
    if (!visit || !reassignTargetId || reassigning) return;
    try {
      setReassigning(true);
      setReassignError(null);
      const selectedStaff = assignableStaff.find(
        (member) => member.id === reassignTargetId
      );
      const isAdminRole =
        currentUserRole === UserRole.RECEPTION ||
        currentUserRole === UserRole.CLINIC_ADMIN ||
        currentUserRole === UserRole.ADMIN;
      const selectedServiceLine = getServiceLineForRole(selectedStaff?.role);
      const updated = await visitService.reassignOwner(visit.id, {
        assigned_doctor_id: reassignTargetId,
        expected_version: visit.version,
        service_line:
          isAdminRole && selectedServiceLine ? selectedServiceLine : undefined,
        reason: reassignReason.trim() || 'Workflow handover',
      });
      setVisit(updated);
      setShowReassignPrompt(false);
      showToast(
        `${getOwnerLabelForServiceLine(updated.service_line)} reassigned successfully.`,
        'success'
      );
      loadVisitDetails();
    } catch (err: unknown) {
      setReassignError(getErrorDetail(err) || 'Unable to reassign visit owner.');
    } finally {
      setReassigning(false);
    }
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return 'Unknown';
    return date.toLocaleString([], {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const maskId = (value?: string | null) =>
    value ? `${value.substring(0, 8)}...` : 'Unknown';

  const openPmrPrompt = () => {
    if (!visit) return;
    setPmrJustification('');
    setPmrError(null);
    setPmrErrorStatus(null);
    setShowPmrPrompt(true);
  };

  const loadPmr = async () => {
    if (!visit) return;
    const trimmedJustification = pmrJustification.trim();
    if (trimmedJustification.length < 2) {
      setPmrError('Justification must be at least 2 characters.');
      return;
    }

    try {
      setPmrLoading(true);
      setPmrError(null);
      setPmrErrorStatus(null);
      const pmrData = await pmrService.getPMR(visit.patient_id, {
        purpose_of_use: purposeOfUse,
        justification: `PMR view: ${trimmedJustification}`,
        break_glass: false,
      });
      setPmr(pmrData);
      setShowPmrPrompt(false);
      setActiveTab('pmr');
    } catch (err: unknown) {
      const detail =
        getErrorDetail(err) || 'Unable to load PMR. Please try again.';
      const status =
        (err as { response?: { status?: number } })?.response?.status ?? null;
      setPmrError(detail);
      setPmrErrorStatus(status);
    } finally {
      setPmrLoading(false);
    }
  };

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }
    toastTimerRef.current = setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  const handleRecheckAutoComplete = async () => {
    if (!visit) return;
    try {
      setRecheckLoading(true);
      const updated = await visitService.recheckAutoComplete(visit.id);
      setVisit(updated);
      if (updated.status === VisitStatus.COMPLETED) {
        showToast('Visit auto-completed successfully.', 'success');
      } else {
        showToast(
          'Visit not eligible yet. Ensure all issued prescriptions are dispensed.',
          'error'
        );
      }
      loadVisitDetails();
    } catch (err: unknown) {
      showToast(
        getErrorDetail(err) || 'Unable to recheck auto-complete.',
        'error'
      );
    } finally {
      setRecheckLoading(false);
    }
  };

  const handleIssueMrn = async () => {
    if (!visit || visit.patient_mrn || issuingMrn) return;
    try {
      setIssuingMrn(true);
      setMrnIssueError(null);
      const mrn = await pmrService.issueMrn(visit.patient_id);
      setVisit({ ...visit, patient_mrn: mrn.mrn });
    } catch (err: unknown) {
      setMrnIssueError(
        getErrorDetail(err) || 'Unable to issue MRN. Please try again.'
      );
    } finally {
      setIssuingMrn(false);
    }
  };

  const openEmergencyPrompt = () => {
    if (!visit) return;
    setEmergencyReason('');
    setEmergencyError(null);
    setShowEmergencyPrompt(true);
  };

  const submitEmergencyFlag = async () => {
    if (!visit || emergencySubmitting) return;
    const trimmedReason = emergencyReason.trim();
    if (trimmedReason.length < 3) {
      setEmergencyError('Reason must be at least 3 characters.');
      return;
    }
    try {
      setEmergencySubmitting(true);
      setEmergencyError(null);
      const updated = await visitService.setIntakeFlag(visit.id, {
        flagged: true,
        reason: trimmedReason,
      });
      setVisit(updated);
      setShowEmergencyPrompt(false);
    } catch (err: unknown) {
      setEmergencyError(getErrorDetail(err) || 'Unable to flag emergency.');
    } finally {
      setEmergencySubmitting(false);
    }
  };

  const openAdmissionPrompt = () => {
    if (!visit) return;
    setAdmissionReason('');
    setAdmissionError(null);
    setAdmissionSuccess(null);
    setShowAdmissionPrompt(true);
  };

  const submitAdmissionRequest = async () => {
    if (!visit || admissionSubmitting) return;
    const trimmedReason = admissionReason.trim();
    if (trimmedReason.length < 3) {
      setAdmissionError('Reason must be at least 3 characters.');
      return;
    }
    try {
      setAdmissionSubmitting(true);
      setAdmissionError(null);
      await admissionRequestService.createRequest({
        patient_id: visit.patient_id,
        admission_type: admissionType,
        reason: trimmedReason,
      });
      setAdmissionSuccess('Admission request submitted.');
      setHasPendingAdmissionRequest(true);
      setShowAdmissionPrompt(false);
    } catch (err: unknown) {
      const detail = getErrorDetail(err);
      if (detail?.toLowerCase().includes('pending admission request')) {
        setHasPendingAdmissionRequest(true);
      }
      setAdmissionError(
        detail || 'Unable to submit admission request.'
      );
    } finally {
      setAdmissionSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                Visit Details
              </h2>
              {visit && (
                <div className="space-y-1 text-gray-600">
                  <p>Visit ID: {maskId(visit.id)}</p>
                  <p className="text-sm text-gray-500">
                    {visit.patient_name || 'Unknown patient'} •{' '}
                    {visit.patient_mrn
                      ? `MRN ${visit.patient_mrn}`
                      : `ID ${maskId(visit.patient_id)}`}
                  </p>
                </div>
              )}
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
              aria-label="Close visit details"
            >
              ✕
            </button>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <div className="flex">
                <div className="flex-shrink-0">
                  <span className="text-red-400">⚠</span>
                </div>
                <div className="ml-3">
                  <p className="text-red-600">{error}</p>
                  <button
                    onClick={loadVisitDetails}
                    className="mt-2 text-sm font-medium text-red-700 hover:text-red-800"
                  >
                    Try again
                  </button>
                </div>
              </div>
            </div>
          )}

          {loading && !visit && (
            <div className="space-y-4">
              <div className="animate-pulse h-8 bg-gray-200 rounded w-1/3"></div>
              <div className="grid grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="animate-pulse h-20 bg-gray-200 rounded"></div>
                ))}
              </div>
            </div>
          )}

          {visit && (
            <>
              <div className="mb-8">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <VisitStatusBadge status={visit.status} size="lg" />
                      <div className="text-sm text-gray-500">
                        Created: {formatDateTime(visit.created_at)}
                      </div>
                    </div>

                    <div className="flex space-x-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={loadVisitDetails}
                        disabled={loading}
                      >
                        Refresh
                      </Button>
                      {visit.status === VisitStatus.PHARMACY_PENDING && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={handleRecheckAutoComplete}
                          disabled={recheckLoading}
                          isLoading={recheckLoading}
                        >
                          Recheck Completion
                        </Button>
                      )}
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={openPmrPrompt}
                        disabled={pmrLoading}
                    >
                      View PMR
                    </Button>
                  </div>
                </div>

                {allowedTransitions && (
                  <div className="mt-6">
                    <QuickActionButtons
                      visitId={visit.id}
                      currentStatus={visit.status}
                      visitVersion={visit.version}
                      allowedTransitions={allowedTransitions.allowed}
                      currentUserRole={currentUserRole}
                      hiddenTransitions={hiddenTransitions}
                      onStatusChange={handleStatusChange}
                      onVisitUpdated={handleVisitUpdated}
                      onReassign={
                        canReassignCurrentVisit()
                          ? handleOpenReassignPrompt
                          : undefined
                      }
                    />
                  </div>
                )}
              </div>

              <div className="border-b border-gray-200 mb-6">
                <nav className="-mb-px flex space-x-8">
                  <button
                    onClick={() => setActiveTab('details')}
                    className={`
                      py-2 px-1 border-b-2 font-medium text-sm
                      ${
                        activeTab === 'details'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }
                    `}
                  >
                    Details
                  </button>
                  <button
                    onClick={() => setActiveTab('timeline')}
                    className={`
                      py-2 px-1 border-b-2 font-medium text-sm
                      ${
                        activeTab === 'timeline'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }
                    `}
                  >
                    Timeline
                  </button>
                  <button
                    onClick={() => setActiveTab('pmr')}
                    className={`
                      py-2 px-1 border-b-2 font-medium text-sm
                      ${
                        activeTab === 'pmr'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }
                    `}
                  >
                    PMR
                  </button>
                </nav>
              </div>

              {activeTab === 'details' && (
                <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Card title="Visit Information" titleClassName="text-[#0B4DA2]">
                      <dl className="space-y-3">
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Visit ID
                          </dt>
                          <dd className="text-sm text-gray-900 font-mono">
                            {maskId(visit.id)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Clinic ID
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {maskId(visit.clinic_id)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Status
                          </dt>
                          <dd>
                            <VisitStatusBadge status={visit.status} size="sm" />
                          </dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Created
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {formatDateTime(visit.created_at)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Last Updated
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {formatDateTime(visit.updated_at)}
                          </dd>
                        </div>
                      </dl>
                    </Card>

                    <Card
                      title={`Assigned ${getOwnerLabelForServiceLine(
                        visit.service_line
                      )}`}
                      titleClassName="text-[#0B4DA2]"
                    >
                      <div className="space-y-3">
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Owner ID
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {visit.assigned_doctor_id
                              ? maskId(visit.assigned_doctor_id)
                              : 'Unassigned'}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Patient
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {visit.patient_name || 'Unknown patient'}
                          </dd>
                          <dd className="text-xs text-gray-500">
                            {visit.patient_mrn
                              ? `MRN: ${visit.patient_mrn}`
                              : `ID: ${maskId(visit.patient_id)}`}
                          </dd>
                        </div>
                        <div className="pt-4 border-t">
                          {!canReassignCurrentVisit() ? (
                            <Tooltip
                              content="You can reassign while the visit is active, if you are Reception/Admin or the currently assigned owner."
                              widthClassName="w-64"
                            >
                              <div>
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  onClick={handleOpenReassignPrompt}
                                  disabled
                                >
                                  Reassign unavailable
                                </Button>
                              </div>
                            </Tooltip>
                          ) : (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={handleOpenReassignPrompt}
                            >
                              Reassign {getOwnerLabelForServiceLine(visit.service_line)}
                            </Button>
                          )}
                          {showReassignPrompt && (
                            <div className="mt-3 space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
                              <p className="text-xs text-slate-600">
                                Transfer ownership to another staff owner.
                              </p>
                              <select
                                value={reassignTargetId}
                                onChange={(e) =>
                                  setReassignTargetId(e.target.value)
                                }
                                className="w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
                                disabled={loadingAssignableStaff || reassigning}
                              >
                                <option value="">
                                  {loadingAssignableStaff
                                    ? 'Loading colleagues...'
                                    : 'Select colleague'}
                                </option>
                                {assignableStaff.map((member) => (
                                  <option key={member.id} value={member.id}>
                                    {member.full_name || member.email}
                                    {member.role ? ` • ${member.role}` : ''}
                                  </option>
                                ))}
                              </select>
                              <input
                                value={reassignReason}
                                onChange={(e) => setReassignReason(e.target.value)}
                                placeholder="Reason (optional)"
                                className="w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
                                maxLength={200}
                                disabled={reassigning}
                              />
                              {reassignError && (
                                <p className="text-xs text-red-600">
                                  {reassignError}
                                </p>
                              )}
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  onClick={handleSubmitReassign}
                                  disabled={!reassignTargetId || reassigning}
                                  isLoading={reassigning}
                                >
                                  Confirm Reassign
                                </Button>
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={() => {
                                    setShowReassignPrompt(false);
                                    setReassignError(null);
                                  }}
                                  disabled={reassigning}
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </Card>

                    <Card title="Patient Record" titleClassName="text-[#0B4DA2]">
                      <dl className="space-y-3">
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            MRN
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {visit.patient_mrn ||
                              pmr?.active_mrn?.mrn ||
                              'Not issued yet'}
                          </dd>
                          {!visit.patient_mrn && (
                            <p className="text-xs text-gray-500 mt-1">
                              Patient ID: {maskId(visit.patient_id)}
                            </p>
                          )}
                          {!visit.patient_mrn && canIssueMrn && (
                            <div className="mt-2">
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={handleIssueMrn}
                                disabled={issuingMrn}
                                isLoading={issuingMrn}
                              >
                                Issue MRN
                              </Button>
                            </div>
                          )}
                          {!visit.patient_mrn && !canIssueMrn && (
                            <p className="mt-2 text-xs text-slate-500">
                              MRN issuance requires Reception or Clinic Admin.
                            </p>
                          )}
                          {mrnIssueError && (
                            <p className="mt-2 text-xs text-red-600">
                              {mrnIssueError}
                            </p>
                          )}
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Identity State
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {pmr?.identity_state ? (
                              <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                                {pmr.identity_state}
                              </span>
                            ) : (
                              <span className="inline-flex items-center rounded-full bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600">
                                Not loaded (PMR required)
                              </span>
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Admission
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {visit.has_active_admission ? (
                              <span className="inline-flex items-center rounded-full bg-rose-100 px-2 py-1 text-xs font-medium text-rose-800">
                                Active admission
                              </span>
                            ) : (
                              <span className="text-gray-500">None</span>
                            )}
                          </dd>
                          {admissionSuccess && (
                            <p className="mt-2 text-xs text-emerald-600">
                              {admissionSuccess}
                            </p>
                          )}
                          {allowAdmissionRequest &&
                            !visit.has_active_admission &&
                            !hasPendingAdmissionRequest && (
                            <div className="mt-2">
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={openAdmissionPrompt}
                              >
                                Request Admission
                              </Button>
                            </div>
                          )}
                          {allowAdmissionRequest && hasPendingAdmissionRequest && (
                            <p className="mt-2 text-xs text-slate-500">
                              Pending admission request already exists.
                            </p>
                          )}
                          {allowAdmissionRequest && visit.has_active_admission && (
                            <p className="mt-2 text-xs text-slate-500">
                              Admission already active for this patient.
                            </p>
                          )}
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Emergency Intake
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {visit.intake_emergency_flag ? (
                              <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
                                Flagged
                              </span>
                            ) : (
                              <span className="text-gray-500">Not flagged</span>
                            )}
                          </dd>
                          {visit.intake_emergency_flag && visit.intake_emergency_reason && (
                            <p className="mt-1 text-xs text-gray-600">
                              Reason: {visit.intake_emergency_reason}
                            </p>
                          )}
                          {!visit.intake_emergency_flag && (
                            <div className="mt-2">
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={openEmergencyPrompt}
                              >
                                Flag Emergency
                              </Button>
                            </div>
                          )}
                        </div>
                        <div className="pt-2 border-t text-xs text-gray-500">
                          PMR access is logged for audit.
                        </div>
                      </dl>
                    </Card>
                  </div>

                  {allowedTransitions &&
                    allowedTransitions.allowed.length > 0 && (
                      <Card title="Next Possible Statuses" titleClassName="text-[#0B4DA2]">
                        <div className="space-y-2">
                          <p className="text-sm text-gray-600">
                            Based on current status and your role, you can
                            transition to:
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {allowedTransitions.allowed.map((status) => (
                              <VisitStatusBadge
                                key={status}
                                status={status}
                                size="sm"
                              />
                            ))}
                          </div>
                        </div>
                      </Card>
                    )}
                </div>
              )}

              {activeTab === 'timeline' && timeline && (
                <Card title="Visit Timeline" titleClassName="text-[#0B4DA2]">
                  <VisitTimeline events={timeline.timeline} />
                </Card>
              )}

              {activeTab === 'pmr' && (
                <div className="space-y-6">
                  {!pmr ? (
                    <Card title="Patient Medical Record" titleClassName="text-[#0B4DA2]">
                      <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-600">
                        PMR is not loaded yet. Click “View PMR” and provide a justification to load the
                        patient’s medical record.
                      </div>
                      <div className="mt-4">
                        <Button variant="primary" size="sm" onClick={openPmrPrompt}>
                          View PMR
                        </Button>
                      </div>
                    </Card>
                  ) : (
                    <>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Card title="Patient" titleClassName="text-[#0B4DA2]">
                          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                            <div>
                              <dt className="text-gray-500">Name</dt>
                              <dd className="font-medium text-gray-900">
                                {pmr.full_name || 'Unknown'}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">Identity State</dt>
                              <dd>
                                <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                                  {pmr.identity_state || '—'}
                                </span>
                              </dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">MRN</dt>
                              <dd className="font-medium text-gray-900">
                                {pmr.active_mrn?.mrn || visit?.patient_mrn || 'Not issued'}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">Patient ID</dt>
                              <dd className="text-gray-700">
                                {maskId(pmr.patient_id_canonical)}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">DOB</dt>
                              <dd className="text-gray-900">
                                {pmr.date_of_birth
                                  ? new Date(pmr.date_of_birth).toLocaleDateString()
                                  : '—'}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">Gender</dt>
                              <dd className="text-gray-900">{pmr.gender || '—'}</dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">Phone</dt>
                              <dd className="text-gray-900">{pmr.phone_number || '—'}</dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">Occupation</dt>
                              <dd className="text-gray-900">{pmr.occupation || '—'}</dd>
                            </div>
                            <div className="sm:col-span-2">
                              <dt className="text-gray-500">Address</dt>
                              <dd className="text-gray-900">{pmr.address || '—'}</dd>
                            </div>
                          </dl>
                        </Card>

                        <Card title="Identifiers" titleClassName="text-[#0B4DA2]">
                          <div className="space-y-3 text-sm">
                            <div>
                              <div className="text-gray-500">Active MRN</div>
                              <div className="text-lg font-semibold text-gray-900">
                                {pmr.active_mrn?.mrn || visit?.patient_mrn || 'Not issued'}
                              </div>
                            </div>
                            <div>
                              <div className="text-gray-500">Retired MRNs</div>
                              {pmr.retired_mrns?.length ? (
                                <div className="mt-2 flex flex-wrap gap-2">
                                  {pmr.retired_mrns.slice(0, 6).map((mrn) => (
                                    <span
                                      key={mrn.id}
                                      className="inline-flex items-center rounded-full bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700"
                                    >
                                      {mrn.mrn}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <div className="mt-1 text-gray-600">None</div>
                              )}
                            </div>
                          </div>
                        </Card>
                      </div>

                      <Card title="Visit History" titleClassName="text-[#0B4DA2]">
                        {pmr.visits?.length ? (
                          <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                              <thead className="text-left text-xs uppercase tracking-wide text-gray-500">
                                <tr>
                                  <th className="py-2 pr-4">Status</th>
                                  <th className="py-2 pr-4">Started</th>
                                  <th className="py-2 pr-4">Completed</th>
                                  <th className="py-2 pr-4">Doctor</th>
                                  <th className="py-2 pr-4">Visit</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y">
                                {pmr.visits.slice(0, 10).map((v) => (
                                  <tr key={v.id} className="text-gray-800">
                                    <td className="py-2 pr-4">
                                      <VisitStatusBadge status={v.status as VisitStatus} size="sm" />
                                    </td>
                                    <td className="py-2 pr-4">
                                      {v.started_at ? formatDateTime(v.started_at) : '—'}
                                    </td>
                                    <td className="py-2 pr-4">
                                      {v.completed_at ? formatDateTime(v.completed_at) : '—'}
                                    </td>
                                    <td className="py-2 pr-4 text-gray-600">
                                      {v.assigned_doctor_id ? maskId(v.assigned_doctor_id) : '—'}
                                    </td>
                                    <td className="py-2 pr-4 text-gray-600">
                                      {maskId(v.id)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="text-sm text-gray-600">No visits recorded yet.</div>
                        )}
                      </Card>

                      <Card title="Clinical History" titleClassName="text-[#0B4DA2]">
                        <div className="mb-3 text-xs text-slate-500">
                          Select a visit row to expand clinical history.
                        </div>
                        {pmr.clinical_history?.length ? (
                          <div className="space-y-2">
                            {pmr.clinical_history.map((h) => {
                              const isExpanded =
                                expandedClinicalHistoryVisitId === h.visit_id;
                              const panelId = `pmr-clinical-history-${h.visit_id}`;

                              const consultRestricted =
                                h.sections.consultation.missing_reason ===
                                'PERMISSION_REDACTED';
                              const rxRestricted =
                                h.sections.prescriptions.missing_reason ===
                                'PERMISSION_REDACTED';
                              const labsRestricted =
                                h.sections.labs.missing_reason ===
                                'PERMISSION_REDACTED';

                              const consultationBadge = consultRestricted
                                ? 'Restricted'
                                : h.sections.consultation.exists
                                  ? 'Recorded'
                                  : 'None';
                              const rxBadge = rxRestricted
                                ? 'Restricted'
                                : String(h.sections.prescriptions.count ?? 0);
                              const labsBadge = labsRestricted
                                ? 'Restricted'
                                : String(h.sections.labs.count ?? 0);

                              const handleToggle = () => {
                                setExpandedClinicalHistoryVisitId(
                                  isExpanded ? null : h.visit_id
                                );
                              };

                              return (
                                <div
                                  key={h.visit_id}
                                  className="rounded-lg border border-slate-200 bg-white"
                                >
                                  <button
                                    type="button"
                                    onClick={handleToggle}
                                    aria-expanded={isExpanded}
                                    aria-controls={panelId}
                                    className="w-full cursor-pointer px-4 py-3 text-left hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
                                  >
                                    <div className="flex items-start justify-between gap-4">
                                      <div className="min-w-0">
                                        <div className="flex flex-wrap items-center gap-2">
                                          <VisitStatusBadge
                                            status={h.visit_status as VisitStatus}
                                            size="sm"
                                          />
                                          <div className="text-sm font-medium text-slate-900">
                                            {h.visit_started_at
                                              ? formatDateTime(h.visit_started_at)
                                              : '—'}
                                          </div>
                                          <div className="text-xs font-mono text-slate-500">
                                            {maskId(h.visit_id)}
                                          </div>
                                          <div className="text-xs text-slate-500">
                                            {h.visit_closed_at ? 'Closed' : 'Open'}
                                          </div>
                                        </div>

                                        <div className="mt-2 flex flex-wrap items-center gap-2">
                                          <span
                                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                              consultationBadge === 'Recorded'
                                                ? 'bg-emerald-50 text-emerald-700'
                                                : consultationBadge === 'Restricted'
                                                  ? 'bg-amber-50 text-amber-700'
                                                  : 'bg-slate-100 text-slate-600'
                                            }`}
                                          >
                                            Consultation: {consultationBadge}
                                          </span>
                                          <span
                                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                              rxRestricted
                                                ? 'bg-amber-50 text-amber-700'
                                                : 'bg-slate-100 text-slate-600'
                                            }`}
                                          >
                                            Rx: {rxBadge}
                                          </span>
                                          <span
                                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                              labsRestricted
                                                ? 'bg-amber-50 text-amber-700'
                                                : 'bg-slate-100 text-slate-600'
                                            }`}
                                          >
                                            Labs: {labsBadge}
                                          </span>
                                        </div>
                                      </div>

                                      <div className="mt-0.5 flex items-center gap-2 text-xs font-medium text-slate-600">
                                        <span>
                                          {isExpanded ? 'Hide history' : 'View history'}
                                        </span>
                                        <svg
                                          aria-hidden="true"
                                          viewBox="0 0 24 24"
                                          className={`h-4 w-4 text-slate-500 transition-transform ${
                                            isExpanded ? 'rotate-90' : ''
                                          }`}
                                          fill="none"
                                          stroke="currentColor"
                                          strokeWidth="2"
                                          strokeLinecap="round"
                                          strokeLinejoin="round"
                                        >
                                          <path d="M9 18l6-6-6-6" />
                                        </svg>
                                      </div>
                                    </div>
                                  </button>

                                  {isExpanded ? (
                                    <div
                                      id={panelId}
                                      role="region"
                                      aria-label="Clinical history details"
                                      className="border-t border-slate-200 px-4 py-4"
                                    >
                                      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                                        <div className="rounded-md border border-slate-100 bg-slate-50 p-3 text-sm">
                                          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Consultation
                                          </div>
                                          {h.sections.consultation.exists &&
                                          h.sections.consultation.item ? (
                                            <div className="space-y-2">
                                              <div>
                                                <div className="text-xs text-slate-500">
                                                  Complaint
                                                </div>
                                                <div className="text-slate-900">
                                                  {h.sections.consultation.item
                                                    .presenting_complaint_preview || '—'}
                                                </div>
                                              </div>
                                              <div>
                                                <div className="text-xs text-slate-500">
                                                  Diagnosis
                                                </div>
                                                <div className="text-slate-900">
                                                  {h.sections.consultation.item
                                                    .diagnosis_summary || '—'}
                                                </div>
                                              </div>
                                            </div>
                                          ) : (
                                            <div className="text-slate-600">
                                              {h.sections.consultation
                                                .missing_reason ===
                                              'TEMPORARILY_UNAVAILABLE'
                                                ? 'Temporarily unavailable.'
                                                : h.sections.consultation
                                                      .missing_reason ===
                                                    'PERMISSION_REDACTED'
                                                  ? 'Restricted.'
                                                  : 'No consultation recorded.'}
                                            </div>
                                          )}
                                        </div>

                                        <div className="rounded-md border border-slate-100 bg-slate-50 p-3 text-sm">
                                          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Prescriptions
                                          </div>
                                          {h.sections.prescriptions.exists ? (
                                            <div className="space-y-2">
                                              <div className="text-slate-700">
                                                {h.sections.prescriptions.count}{' '}
                                                item(s)
                                              </div>
                                              <div className="space-y-1">
                                                {h.sections.prescriptions.items
                                                  .slice(0, 5)
                                                  .map((p) => (
                                                    <div
                                                      key={p.prescription_id}
                                                      className="flex items-center justify-between gap-2"
                                                    >
                                                      <div className="text-slate-900">
                                                        {p.drugs?.[0]?.name ||
                                                          'Medication'}
                                                      </div>
                                                      <div className="text-xs text-slate-500">
                                                        {p.status}
                                                      </div>
                                                    </div>
                                                  ))}
                                                {h.sections.prescriptions.count >
                                                5 ? (
                                                  <div className="text-xs text-slate-500">
                                                    +
                                                    {h.sections.prescriptions
                                                      .count - 5}{' '}
                                                    more
                                                  </div>
                                                ) : null}
                                              </div>
                                            </div>
                                          ) : (
                                            <div className="text-slate-600">
                                              {h.sections.prescriptions
                                                .missing_reason ===
                                              'TEMPORARILY_UNAVAILABLE'
                                                ? 'Temporarily unavailable.'
                                                : h.sections.prescriptions
                                                      .missing_reason ===
                                                    'PERMISSION_REDACTED'
                                                  ? 'Restricted.'
                                                  : 'No prescriptions recorded.'}
                                            </div>
                                          )}
                                        </div>

                                        <div className="rounded-md border border-slate-100 bg-slate-50 p-3 text-sm">
                                          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Labs
                                          </div>
                                          {h.sections.labs.exists ? (
                                            <div className="space-y-2">
                                              <div className="text-slate-700">
                                                {h.sections.labs.count} request(s)
                                              </div>
                                              <div className="space-y-1">
                                                {h.sections.labs.requests
                                                  .slice(0, 5)
                                                  .map((r) => (
                                                    <div
                                                      key={r.lab_request_id}
                                                      className="flex items-center justify-between gap-2"
                                                    >
                                                      <div className="text-slate-900">
                                                        {r.tests?.[0]?.name ||
                                                          'Lab test'}
                                                      </div>
                                                      <div className="text-xs text-slate-500">
                                                        {r.status}
                                                      </div>
                                                    </div>
                                                  ))}
                                                {h.sections.labs.count > 5 ? (
                                                  <div className="text-xs text-slate-500">
                                                    +{h.sections.labs.count - 5}{' '}
                                                    more
                                                  </div>
                                                ) : null}
                                              </div>
                                            </div>
                                          ) : (
                                            <div className="text-slate-600">
                                              {h.sections.labs.missing_reason ===
                                              'TEMPORARILY_UNAVAILABLE'
                                                ? 'Temporarily unavailable.'
                                                : h.sections.labs.missing_reason ===
                                                    'PERMISSION_REDACTED'
                                                  ? 'Restricted.'
                                                  : 'No lab requests recorded.'}
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  ) : null}
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="text-sm text-gray-600">
                            No clinical history recorded yet.
                          </div>
                        )}
                        <div className="mt-3 text-xs text-slate-500">
                          PMR access is logged for audit. This view is summary-only.
                        </div>
                      </Card>

                      <Card title="Admissions" titleClassName="text-[#0B4DA2]">
                        {pmr.admissions?.length ? (
                          <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                              <thead className="text-left text-xs uppercase tracking-wide text-gray-500">
                                <tr>
                                  <th className="py-2 pr-4">Status</th>
                                  <th className="py-2 pr-4">Admitted</th>
                                  <th className="py-2 pr-4">Discharged</th>
                                  <th className="py-2 pr-4">Admission</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y">
                                {pmr.admissions.slice(0, 10).map((a) => (
                                  <tr key={a.id} className="text-gray-800">
                                    <td className="py-2 pr-4">
                                      <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                                        {a.status}
                                      </span>
                                    </td>
                                    <td className="py-2 pr-4">
                                      {a.admitted_at ? formatDateTime(a.admitted_at) : '—'}
                                    </td>
                                    <td className="py-2 pr-4">
                                      {a.discharged_at ? formatDateTime(a.discharged_at) : '—'}
                                    </td>
                                    <td className="py-2 pr-4 text-gray-600">
                                      {maskId(a.id)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="text-sm text-gray-600">No admissions recorded yet.</div>
                        )}
                      </Card>
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {showPmrPrompt && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900">
              PMR Access Required
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              PMR access is audited. Provide a justification.
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Justification
                </label>
                <textarea
                  value={pmrJustification}
                  onChange={(e) => {
                    setPmrJustification(e.target.value);
                    if (pmrError) {
                      setPmrError(null);
                      setPmrErrorStatus(null);
                    }
                  }}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Reason for accessing the PMR..."
                />
                <p className="mt-1 text-xs text-gray-500">
                  Minimum 2 characters.
                </p>
              </div>

              {pmrError && (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  <div className="font-medium">
                    PMR access failed{pmrErrorStatus ? ` (${pmrErrorStatus})` : ''}
                  </div>
                  <div className="mt-1">{pmrError}</div>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowPmrPrompt(false);
                  setPmrJustification('');
                  setPmrError(null);
                  setPmrErrorStatus(null);
                }}
                disabled={pmrLoading}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={loadPmr}
                isLoading={pmrLoading}
                disabled={pmrLoading || pmrJustification.trim().length < 2}
              >
                Access PMR
              </Button>
            </div>
          </div>
        </div>
      )}

      {showEmergencyPrompt && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900">
              Flag Emergency Intake
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              This does not set clinical priority. Clinician must confirm.
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason
                </label>
                <textarea
                  value={emergencyReason}
                  onChange={(e) => setEmergencyReason(e.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Reason for emergency flag..."
                />
              </div>

              {emergencyError && (
                <div className="text-sm text-red-600">{emergencyError}</div>
              )}
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowEmergencyPrompt(false);
                  setEmergencyReason('');
                  setEmergencyError(null);
                }}
                disabled={emergencySubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={submitEmergencyFlag}
                isLoading={emergencySubmitting}
                disabled={emergencySubmitting}
              >
                Flag Emergency
              </Button>
            </div>
          </div>
        </div>
      )}

      {showAdmissionPrompt && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900">
              Request Admission
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Submit a request for admin approval. Admission will not be
              activated until approved.
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Admission type
                </label>
                <select
                  value={admissionType}
                  onChange={(e) => setAdmissionType(e.target.value as AdmissionType)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="EMERGENCY">Emergency</option>
                  <option value="ELECTIVE">Elective</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason
                </label>
                <textarea
                  value={admissionReason}
                  onChange={(e) => setAdmissionReason(e.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Reason for admission request..."
                />
              </div>

              {admissionError && (
                <div className="text-sm text-red-600">{admissionError}</div>
              )}
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowAdmissionPrompt(false);
                  setAdmissionReason('');
                  setAdmissionError(null);
                }}
                disabled={admissionSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={submitAdmissionRequest}
                isLoading={admissionSubmitting}
                disabled={admissionSubmitting}
              >
                Submit Request
              </Button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 z-[9999]">
          <div
            className={`rounded-lg border px-4 py-3 text-sm shadow-lg ${
              toast.type === 'error'
                ? 'border-red-200 bg-red-50 text-red-700'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700'
            }`}
          >
            {toast.message}
          </div>
        </div>
      )}
    </div>
  );
}
