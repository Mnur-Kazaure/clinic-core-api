'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { ConsultationModal } from '@/app/doctor/components/consultation/ConsultationModal';
import { LabRequestForm } from '@/app/doctor/components/lab/LabRequestForm';
import { LabResultsViewerModal } from '@/app/doctor/components/lab/LabResultsViewerModal';
import { PrescriptionForm } from '@/app/doctor/components/prescription/PrescriptionForm';
import { DoctorQueue } from '@/app/doctor/components/DoctorQueue';
import { VisitDetailsModal } from '@/app/reception/components/visit/VisitDetailsModal';
import { PurposeOfUse, VisitStatus } from '@/shared/enums';
import { Button } from '@/shared/Button';
import { Tooltip } from '@/shared/Tooltip';
import { ConsultationResponse, VisitResponse } from '@/shared/types';
import { consultationService } from '@/domains/consultation/services/consultationService';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';
import { doctorLabService } from '@/domains/lab/services/doctorLabService';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { HOSPITAL_NAME } from '@/shared/constants/branding';

type DoctorWorkspaceKey =
  | 'overview'
  | 'queue'
  | 'active'
  | 'completed'
  | 'summary'
  | 'complaints'
  | 'examination'
  | 'diagnosis'
  | 'notes'
  | 'labRequests'
  | 'labResults'
  | 'radiology'
  | 'prescription'
  | 'pharmacy'
  | 'followUp'
  | 'admission'
  | 'referral'
  | 'audit';

const WORKSPACE_NAV: {
  group: string;
  items: { key: DoctorWorkspaceKey; label: string; short: string }[];
}[] = [
  {
    group: 'Clinical Command',
    items: [
      { key: 'overview', label: 'Consultation Overview', short: 'CO' },
      { key: 'queue', label: 'My Patient Queue', short: 'PQ' },
      { key: 'active', label: 'Active Consultation', short: 'AC' },
      { key: 'completed', label: 'Completed Consultations', short: 'CC' },
    ],
  },
  {
    group: 'Patient Encounter',
    items: [
      { key: 'summary', label: 'Patient Clinical Summary', short: 'PS' },
      { key: 'complaints', label: 'Complaints & History', short: 'CH' },
      { key: 'examination', label: 'Examination Findings', short: 'EF' },
      { key: 'diagnosis', label: 'Diagnosis / Assessment', short: 'DA' },
      { key: 'notes', label: 'Clinical Notes', short: 'CN' },
    ],
  },
  {
    group: 'Orders & Treatment',
    items: [
      { key: 'labRequests', label: 'Lab Requests', short: 'LR' },
      { key: 'labResults', label: 'Lab Results', short: 'LS' },
      { key: 'radiology', label: 'Radiology Requests', short: 'XR' },
      { key: 'prescription', label: 'Prescription Plan', short: 'RX' },
      { key: 'pharmacy', label: 'Send to Pharmacy', short: 'PH' },
    ],
  },
  {
    group: 'Disposition',
    items: [
      { key: 'followUp', label: 'Follow-Up / Recall', short: 'FU' },
      { key: 'admission', label: 'Admission Request', short: 'AD' },
      { key: 'referral', label: 'Internal Referral', short: 'IR' },
      { key: 'audit', label: 'Consultation Audit Trail', short: 'AT' },
    ],
  },
];

const API_PENDING_WORKSPACES = new Set<DoctorWorkspaceKey>([
  'radiology',
  'referral',
  'audit',
]);

const PRIMARY_WORKFLOW_WORKSPACES = new Set<DoctorWorkspaceKey>([
  'queue',
  'active',
  'labRequests',
  'labResults',
  'prescription',
  'pharmacy',
  'admission',
]);

export default function DoctorPage() {
  const dashboardUser = useDashboardUser();
  type ConsultationLabState = {
    labStatus: 'pending' | 'ready' | 'none';
    labRequestedAt: string | null;
  };

  const [selectedVisit, setSelectedVisit] = useState<VisitResponse | null>(null);
  const [consultationVisit, setConsultationVisit] =
    useState<VisitResponse | null>(null);
  const [isConsultationModalOpen, setIsConsultationModalOpen] = useState(false);
  const [isLabRequestModalOpen, setIsLabRequestModalOpen] = useState(false);
  const [isPrescriptionModalOpen, setIsPrescriptionModalOpen] = useState(false);
  const [isVisitDetailsModalOpen, setIsVisitDetailsModalOpen] = useState(false);
  const [actionWarning, setActionWarning] = useState<string | null>(null);
  const [allowedTransitions, setAllowedTransitions] = useState<string[]>([]);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [startingConsultation, setStartingConsultation] = useState(false);

  const [activeConsultation, setActiveConsultation] = useState<{
    visitId: string;
    consultationId: string;
  } | null>(null);

  const [allVisits, setAllVisits] = useState<VisitResponse[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [activeConsultations, setActiveConsultations] = useState<
    {
      visit: VisitResponse;
      consultation: ConsultationResponse;
      labStatus: 'pending' | 'ready' | 'none';
      labRequestedAt?: string | null;
    }[]
  >([]);

  const [labResultsOpen, setLabResultsOpen] = useState(false);
  const [doctorFullName, setDoctorFullName] = useState<string | null>(null);
  const [activeConsultationsUpdatedAt, setActiveConsultationsUpdatedAt] =
    useState<Date | null>(null);
  const [queueRefreshToken, setQueueRefreshToken] = useState(0);
  const [activeWorkspace, setActiveWorkspace] =
    useState<DoctorWorkspaceKey>('overview');

  const getApiErrorDetail = (err: unknown): unknown => {
    if (!err || typeof err !== 'object' || !('response' in err)) {
      return null;
    }
    return (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  };

  useEffect(() => {
    let isMounted = true;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    async function loadStats() {
      try {
        setStatsLoading(true);
        setStatsError(null);
        const data = await visitService.getDoctorQueue();
        if (isMounted) {
          setAllVisits(data);
        }
      } catch (error) {
        console.error('Failed to load doctor stats:', error);
        if (isMounted) {
          setStatsError('Unable to load live statistics.');
        }
      } finally {
        if (isMounted) {
          setStatsLoading(false);
        }
      }
    }

    loadStats();
    intervalId = setInterval(() => {
      loadStats();
    }, 30000);

    return () => {
      isMounted = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadAllowedTransitions() {
      if (!consultationVisit) {
        if (isMounted) {
          setAllowedTransitions([]);
        }
        return;
      }
      try {
        const result = await visitService.getAllowedTransitions(
          consultationVisit.id
        );
        if (isMounted) {
          setAllowedTransitions(result.allowed || []);
        }
      } catch {
        if (isMounted) {
          setAllowedTransitions([]);
        }
      }
    }

    loadAllowedTransitions();

    return () => {
      isMounted = false;
    };
  }, [consultationVisit]);

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const maskId = (value?: string | null) =>
    value ? `${value.substring(0, 6)}…${value.substring(value.length - 4)}` : '—';

  const getLabStatusForVisit = useCallback(
    async (visitId: string): Promise<ConsultationLabState> => {
    try {
      const requests = await doctorLabService.getLabRequestsByVisit(visitId);
      if (requests.length === 0) {
        return { labStatus: 'none', labRequestedAt: null };
      }
      const latest = requests[0];
      const hasCompleted = requests.some((r) => r.status === 'COMPLETED');
      return {
        labStatus: hasCompleted ? 'ready' : 'pending',
        labRequestedAt: latest.created_at,
      };
    } catch {
      return { labStatus: 'none', labRequestedAt: null };
    }
    },
    []
  );

  useEffect(() => {
    let isMounted = true;

    async function loadActiveConsultations() {
      if (allVisits.length === 0) {
        setActiveConsultations([]);
        return;
      }
      if (isConsultationModalOpen) {
        return;
      }

      const candidates = allVisits.filter((visit) =>
        ['IN_CONSULTATION', 'LAB_REQUESTED', 'LAB_COMPLETED'].includes(
          visit.status
        )
      );

      const entries = await Promise.all(
        candidates.map(async (visit) => {
          try {
            const consultation =
              await consultationService.getConsultationByVisit(visit.id);
            if (!consultation) {
              return null;
            }
            const labState = await getLabStatusForVisit(visit.id);
            return {
              visit,
              consultation,
              labStatus: labState.labStatus,
              labRequestedAt: labState.labRequestedAt,
            };
          } catch {
            return null;
          }
        })
      );

      if (!isMounted) return;
      const active = entries.filter(Boolean) as {
        visit: VisitResponse;
        consultation: ConsultationResponse;
        labStatus: 'pending' | 'ready' | 'none';
        labRequestedAt?: string | null;
      }[];

      setActiveConsultations(active);
      setActiveConsultationsUpdatedAt(new Date());

      if (
        activeConsultation &&
        !active.find((entry) => entry.visit.id === activeConsultation.visitId) &&
        !isConsultationModalOpen
      ) {
        setActiveConsultation(null);
        setConsultationVisit(null);
      }
    }

    loadActiveConsultations();
    return () => {
      isMounted = false;
    };
  }, [
    allVisits,
    activeConsultation,
    consultationVisit,
    getLabStatusForVisit,
    isConsultationModalOpen,
  ]);

  const stats = useMemo(() => {
    const today = new Date().toDateString();
    const totalToday = allVisits.filter(
      (visit) => new Date(visit.created_at).toDateString() === today
    ).length;
    const inProgress = allVisits.filter(
      (visit) => visit.status === 'IN_CONSULTATION'
    ).length;
    const completedToday = allVisits.filter(
      (visit) =>
        visit.status === 'COMPLETED' &&
        new Date(visit.updated_at).toDateString() === today
    ).length;
    const pendingLab = allVisits.filter(
      (visit) => visit.status === 'LAB_REQUESTED'
    ).length;
    const emergency = allVisits.filter(
      (visit) => visit.intake_emergency_flag
    ).length;

    return { totalToday, inProgress, completedToday, pendingLab, emergency };
  }, [allVisits]);

  const completedTodayVisits = useMemo(() => {
    const today = new Date().toDateString();
    return allVisits
      .filter(
        (visit) =>
          visit.status === 'COMPLETED' &&
          new Date(visit.updated_at).toDateString() === today
      )
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      .slice(0, 5);
  }, [allVisits]);

  const recentActivity = useMemo(() => {
    return [...allVisits]
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      .slice(0, 3);
  }, [allVisits]);

  const handleStartConsultation = (visit: VisitResponse) => {
    setConsultationVisit(visit);
    setIsConsultationModalOpen(true);
  };

  const handleViewVisit = (visit: VisitResponse) => {
    setSelectedVisit(visit);
    setIsVisitDetailsModalOpen(true);
  };

  const handleConsultationComplete = (consultationId: string) => {
    if (!consultationVisit && selectedVisit) {
      setConsultationVisit(selectedVisit);
    }
    setActiveConsultation({
      visitId: consultationVisit?.id || selectedVisit?.id || '',
      consultationId,
    });
    setQueueRefreshToken((prev) => prev + 1);
  };

  const handleConsultationReady = async (
    visitId: string,
    consultation: ConsultationResponse
  ) => {
    setActiveConsultation({ visitId, consultationId: consultation.id });
    setQueueRefreshToken((prev) => prev + 1);
    if (!consultationVisit || consultationVisit.id !== visitId) {
      const visitMatch = allVisits.find((visit) => visit.id === visitId);
      if (visitMatch) {
        setConsultationVisit(visitMatch);
      }
    }
    setDoctorFullName(consultation.doctor_full_name);

    const labState = await getLabStatusForVisit(visitId);
    setActiveConsultations((prev) => {
      const existingIndex = prev.findIndex((entry) => entry.visit.id === visitId);
      const visitMatch =
        prev[existingIndex]?.visit ||
        allVisits.find((visit) => visit.id === visitId) ||
        consultationVisit;

      if (!visitMatch) {
        return prev;
      }

      const entry = {
        visit: visitMatch,
        consultation,
        labStatus: labState.labStatus,
        labRequestedAt: labState.labRequestedAt,
      };

      if (existingIndex === -1) {
        return [entry, ...prev];
      }

      const updated = [...prev];
      updated[existingIndex] = entry;
      return updated;
    });
  };

  const handleResumeConsultation = (visit: VisitResponse) => {
    setConsultationVisit(visit);
    setIsConsultationModalOpen(true);
  };

  const handleSelectConsultationContext = async (visit: VisitResponse) => {
    setConsultationVisit(visit);
    try {
      const consultation = await consultationService.getConsultationByVisit(
        visit.id
      );
      if (consultation) {
        setActiveConsultation({
          visitId: visit.id,
          consultationId: consultation.id,
        });
        setDoctorFullName(consultation.doctor_full_name);
      } else {
        setActiveConsultation(null);
        setDoctorFullName(null);
      }
    } catch {
      setActiveConsultation(null);
      setDoctorFullName(null);
    }
  };

  const handleCheckLabResults = async () => {
    if (!activeConsultation) return;
    setLabResultsOpen(true);
    try {
      const consultation = await consultationService.getConsultationByVisit(
        activeConsultation.visitId
      );
      if (consultation) {
        setDoctorFullName(consultation.doctor_full_name);
      } else {
        setDoctorFullName(null);
      }
    } catch {
      setDoctorFullName(null);
    }
  };

  const handleRequestLab = () => {
    if (!activeConsultation) return;
    setIsLabRequestModalOpen(true);
  };

  const handleIssuePrescription = () => {
    if (!activeConsultation) return;
    setIsPrescriptionModalOpen(true);
  };

  const handleRestrictedAction = (action: 'lab' | 'prescription') => {
    const message =
      action === 'lab'
        ? 'A consultation must be started before ordering lab tests.'
        : 'A consultation must be started before issuing prescriptions.';
    setActionWarning(message);
  };

  const handleLabRequestSuccess = (_labRequestId: string) => {
    void _labRequestId;
    setIsLabRequestModalOpen(false);
  };

  const handlePrescriptionSuccess = (_prescriptionId: string) => {
    void _prescriptionId;
    setIsPrescriptionModalOpen(false);
    if (consultationVisit) {
      visitService
        .getAllowedTransitions(consultationVisit.id)
        .then((result) => setAllowedTransitions(result.allowed || []))
        .catch(() => setAllowedTransitions([]));
    }
  };

  const handleSendToPharmacy = async () => {
    if (!consultationVisit) return;
    try {
      setIsTransitioning(true);
      setActionWarning(null);
      const updated = await visitService.transitionVisit(
        consultationVisit.id,
        {
          to_status: VisitStatus.PHARMACY_PENDING,
          expected_version: consultationVisit.version,
          mode: 'normal',
        }
      );
      setConsultationVisit(updated);
      setSelectedVisit(updated);
      setAllVisits((prev) =>
        prev.map((visit) => (visit.id === updated.id ? updated : visit))
      );
      setQueueRefreshToken((prev) => prev + 1);
      setAllowedTransitions([]);
    } catch (err: unknown) {
      const detail = getApiErrorDetail(err);
      setActionWarning(
        typeof detail === 'string'
          ? detail
          : 'Unable to send visit to pharmacy. Please refresh and try again.'
      );
    } finally {
      setIsTransitioning(false);
    }
  };

  const handleOpenConsultationWorkspace = async (
    visit: VisitResponse,
    hasActiveConsultation: boolean
  ) => {
    const needsTransitionToConsultation =
      !hasActiveConsultation &&
      [VisitStatus.REGISTERED, VisitStatus.TRIAGED].includes(visit.status);

    if (!needsTransitionToConsultation) {
      setIsConsultationModalOpen(true);
      return;
    }

    if (!allowedTransitions.includes(VisitStatus.IN_CONSULTATION)) {
      setActionWarning(
        'This visit cannot move to consultation yet. Refresh visit details and retry.'
      );
      return;
    }

    try {
      setStartingConsultation(true);
      setActionWarning(null);
      const updated = await visitService.transitionVisit(visit.id, {
        to_status: VisitStatus.IN_CONSULTATION,
        expected_version: visit.version,
        mode: 'normal',
      });
      setConsultationVisit(updated);
      setSelectedVisit(updated);
      setAllVisits((prev) =>
        prev.map((entry) => (entry.id === updated.id ? updated : entry))
      );
      setQueueRefreshToken((prev) => prev + 1);
      setIsConsultationModalOpen(true);
    } catch (err: unknown) {
      const detail = getApiErrorDetail(err);
      if (
        detail &&
        typeof detail === 'object' &&
        'code' in detail &&
        (detail as { code?: string }).code === 'VERSION_CONFLICT'
      ) {
        setActionWarning(
          'Visit was updated by another user. Refresh queue and try again.'
        );
        return;
      }
      setActionWarning(
        typeof detail === 'string'
          ? detail
          : 'Unable to move visit into consultation. Please refresh and retry.'
      );
    } finally {
      setStartingConsultation(false);
    }
  };

  const doctorDisplayName = getDashboardUserDisplayName(dashboardUser);
  const encounterVisit =
    consultationVisit || selectedVisit || activeConsultations[0]?.visit || null;
  const encounterEntry = encounterVisit
    ? activeConsultations.find((entry) => entry.visit.id === encounterVisit.id)
    : null;
  const activeQueueCount = allVisits.filter((visit) =>
    [VisitStatus.REGISTERED, VisitStatus.TRIAGED].includes(visit.status)
  ).length;
  const activeWorkspaceLabel =
    WORKSPACE_NAV.flatMap((group) => group.items).find(
      (item) => item.key === activeWorkspace
    )?.label || 'Consultation Overview';

  const isEncounterConsultationActive = Boolean(
    activeConsultation &&
      encounterVisit &&
      activeConsultation.visitId === encounterVisit.id
  );
  const isEncounterCompleted = Boolean(encounterEntry?.consultation.completed_at);
  const encounterLabStatus =
    encounterEntry?.labStatus ||
    (encounterVisit?.status === VisitStatus.LAB_COMPLETED
      ? 'ready'
      : encounterVisit?.status === VisitStatus.LAB_REQUESTED
        ? 'pending'
        : 'none');

  const panelClass =
    'rounded-2xl border border-slate-200/80 bg-gradient-to-br from-white via-sky-50/35 to-slate-50/90 shadow-[0_20px_55px_-38px_rgba(15,23,42,0.7)] ring-1 ring-white/70';
  const secondaryPanelClass =
    'rounded-2xl border border-slate-200/80 bg-slate-50/85 shadow-sm';

  const openEncounterVisitDetails = () => {
    if (!encounterVisit) return;
    setSelectedVisit(encounterVisit);
    setIsVisitDetailsModalOpen(true);
  };

  const openEncounterConsultation = () => {
    if (!encounterVisit) return;
    setConsultationVisit(encounterVisit);
    void handleOpenConsultationWorkspace(
      encounterVisit,
      Boolean(encounterEntry || isEncounterConsultationActive)
    );
  };

  const renderStatusPill = (
    label: string,
    tone: 'blue' | 'green' | 'amber' | 'rose' | 'slate' = 'slate'
  ) => {
    const toneClass = {
      blue: 'border-sky-200 bg-sky-50 text-sky-800',
      green: 'border-emerald-200 bg-emerald-50 text-emerald-800',
      amber: 'border-amber-200 bg-amber-50 text-amber-800',
      rose: 'border-rose-200 bg-rose-50 text-rose-800',
      slate: 'border-slate-200 bg-slate-100 text-slate-700',
    }[tone];

    return (
      <span
        className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClass}`}
      >
        {label}
      </span>
    );
  };

  const renderActionState = (
    state: 'available' | 'requiresConsultation' | 'pendingApi' | 'locked',
    label?: string
  ) => {
    const content = {
      available: {
        text: label || 'Available now',
        tone: 'green' as const,
      },
      requiresConsultation: {
        text: label || 'Requires active consultation',
        tone: 'amber' as const,
      },
      pendingApi: {
        text: label || 'Frontend demonstration — clinical API pending',
        tone: 'amber' as const,
      },
      locked: {
        text: label || 'Record locked',
        tone: 'blue' as const,
      },
    }[state];

    return renderStatusPill(content.text, content.tone);
  };

  const renderEmptyEncounter = () => (
    <div className="rounded-xl border border-dashed border-sky-200 bg-sky-50/55 px-4 py-6 text-sm text-slate-600">
      Select a patient from the queue to anchor the encounter context. The
      clinical record, orders, prescriptions, and disposition controls will
      remain tied to that visit.
    </div>
  );

  const renderMetricCard = (
    label: string,
    value: number | string,
    caption: string,
    tone: 'blue' | 'green' | 'amber' | 'rose' | 'slate'
  ) => {
    const toneClass = {
      blue: 'from-[#0B4DA2]/12 to-sky-50 text-[#0B4DA2]',
      green: 'from-emerald-500/12 to-emerald-50 text-emerald-700',
      amber: 'from-amber-500/14 to-amber-50 text-amber-700',
      rose: 'from-rose-500/12 to-rose-50 text-rose-700',
      slate: 'from-slate-500/12 to-slate-50 text-slate-800',
    }[tone];

    return (
      <div className={`rounded-2xl border border-slate-200 bg-gradient-to-br ${toneClass} px-4 py-3 shadow-sm`}>
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          {label}
        </p>
        <div className="mt-2 text-2xl font-semibold">
          {statsLoading ? '—' : value}
        </div>
        <p className="mt-1 text-xs text-slate-500">{caption}</p>
      </div>
    );
  };

  const renderClinicalActions = () => {
    if (!encounterVisit) {
      return renderEmptyEncounter();
    }

    const canStartConsultation = [
      VisitStatus.REGISTERED,
      VisitStatus.TRIAGED,
      VisitStatus.IN_CONSULTATION,
      VisitStatus.LAB_REQUESTED,
      VisitStatus.LAB_COMPLETED,
      VisitStatus.PHARMACY_PENDING,
    ].includes(encounterVisit.status);

    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-sky-100 bg-gradient-to-br from-[#F5FAFE] to-white px-4 py-3 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Encounter Control
              </p>
              <h3 className="mt-1 text-lg font-semibold text-slate-950">
                {encounterVisit.patient_name || 'Unknown patient'}
              </h3>
              <p className="text-sm text-slate-600">
                {encounterVisit.patient_mrn
                  ? `MRN ${encounterVisit.patient_mrn}`
                  : `Patient ID ${maskId(encounterVisit.patient_id)}`}{' '}
                • Visit {maskId(encounterVisit.id)}
              </p>
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <VisitStatusBadge status={encounterVisit.status} size="sm" />
              {encounterVisit.intake_emergency_flag &&
                renderStatusPill('Emergency flagged', 'rose')}
              {isEncounterCompleted && renderStatusPill('Record locked', 'blue')}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {isEncounterCompleted
            ? renderActionState('locked', 'Completed record: read-only')
            : isEncounterConsultationActive
              ? renderActionState('available', 'Encounter actions available')
              : renderActionState(
                  'requiresConsultation',
                  'Lab, prescription, and pharmacy require active consultation'
                )}
          {renderStatusPill('Service-backed clinical workflow', 'green')}
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {!canStartConsultation ? (
            <Tooltip content="This visit is not eligible for consultation yet.">
              <div>
                <Button
                  variant="secondary"
                  onClick={openEncounterConsultation}
                  className="w-full justify-center"
                  disabled
                >
                  Start Consultation
                </Button>
              </div>
            </Tooltip>
          ) : (
            <Button
              variant={isEncounterCompleted ? 'secondary' : 'primary'}
              onClick={openEncounterConsultation}
              className="w-full justify-center"
              disabled={startingConsultation || isTransitioning}
              isLoading={startingConsultation}
            >
              {isEncounterConsultationActive || encounterEntry
                ? isEncounterCompleted
                  ? 'View Completed Consultation'
                  : 'Continue Consultation'
                : 'Start Consultation'}
            </Button>
          )}

          {isEncounterConsultationActive && !isEncounterCompleted ? (
            <Button
              variant="secondary"
              onClick={handleRequestLab}
              className="w-full justify-center"
            >
              Request Lab Test
            </Button>
          ) : (
            <Tooltip
              content={
                isEncounterCompleted
                  ? 'Consultation is completed and locked.'
                  : 'Start a consultation before ordering labs.'
              }
            >
              <div>
                <Button
                  variant="secondary"
                  onClick={() => handleRestrictedAction('lab')}
                  className="w-full justify-center"
                  disabled
                >
                  Request Lab Test
                </Button>
              </div>
            </Tooltip>
          )}

          {isEncounterConsultationActive && !isEncounterCompleted ? (
            <Button
              variant="secondary"
              onClick={handleIssuePrescription}
              className="w-full justify-center"
            >
              Issue Prescription
            </Button>
          ) : (
            <Tooltip
              content={
                isEncounterCompleted
                  ? 'Consultation is completed and locked.'
                  : 'Start a consultation before issuing prescriptions.'
              }
            >
              <div>
                <Button
                  variant="secondary"
                  onClick={() => handleRestrictedAction('prescription')}
                  className="w-full justify-center"
                  disabled
                >
                  Issue Prescription
                </Button>
              </div>
            </Tooltip>
          )}

          {allowedTransitions.includes(VisitStatus.PHARMACY_PENDING) ? (
            <Button
              variant="primary"
              onClick={handleSendToPharmacy}
              className="w-full justify-center"
              disabled={isTransitioning || startingConsultation}
            >
              {isTransitioning ? 'Sending...' : 'Send to Pharmacy'}
            </Button>
          ) : (
            <Tooltip content="Issue a prescription to send this visit to pharmacy.">
              <div>
                <Button
                  variant="secondary"
                  className="w-full justify-center"
                  onClick={handleSendToPharmacy}
                  disabled
                >
                  Send to Pharmacy
                </Button>
              </div>
            </Tooltip>
          )}

          <Button
            variant="secondary"
            onClick={openEncounterVisitDetails}
            className="w-full justify-center"
          >
            View Visit Details
          </Button>

          <Button
            variant="secondary"
            onClick={handleCheckLabResults}
            className="w-full justify-center"
            disabled={!isEncounterConsultationActive}
          >
            Lab Results
          </Button>
        </div>

        {actionWarning && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {actionWarning}
            <button
              type="button"
              onClick={() => setActionWarning(null)}
              className="ml-3 font-medium text-amber-950 underline underline-offset-2"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>
    );
  };

  const renderActiveConsultations = () => (
    <div className={`${panelClass} p-4`}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
            Live Encounters
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">
            Active Consultation Register
          </h2>
        </div>
        <span className="text-xs font-medium text-slate-500">
          Updated{' '}
          {activeConsultationsUpdatedAt
            ? activeConsultationsUpdatedAt.toLocaleTimeString()
            : '—'}
        </span>
      </div>
      {activeConsultations.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm text-slate-600">
          No active consultations yet. Patients started from the queue appear
          here for fast resumption.
        </div>
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {activeConsultations.map((entry) => {
            const selected = encounterVisit?.id === entry.visit.id;
            return (
              <button
                key={entry.visit.id}
                type="button"
                onClick={() => handleSelectConsultationContext(entry.visit)}
                className={`rounded-xl border p-3 text-left transition ${
                  selected
                    ? 'border-[#0B4DA2] bg-[#F5FAFE] shadow-sm'
                    : 'border-slate-200 bg-white hover:border-sky-200 hover:bg-sky-50/40'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-950">
                      {entry.visit.patient_name || 'Unknown patient'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {entry.visit.patient_mrn
                        ? `MRN ${entry.visit.patient_mrn}`
                        : `ID ${maskId(entry.visit.patient_id)}`}{' '}
                      • {getTimeAgo(entry.consultation.started_at)} in consult
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    {entry.consultation.completed_at
                      ? renderStatusPill('Completed', 'blue')
                      : renderStatusPill('In progress', 'green')}
                    {entry.labStatus !== 'none' &&
                      renderStatusPill(
                        entry.labStatus === 'ready'
                          ? 'Results ready'
                          : 'Lab pending',
                        entry.labStatus === 'ready' ? 'green' : 'amber'
                      )}
                  </div>
                </div>
                {!entry.consultation.completed_at && (
                  <span
                    onClick={(event) => {
                      event.stopPropagation();
                      handleResumeConsultation(entry.visit);
                    }}
                    className="mt-3 inline-flex text-xs font-semibold text-[#0B4DA2] underline underline-offset-4"
                  >
                    Resume consultation
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );

  const renderCompletedConsultations = () => (
    <div className={`${panelClass} p-4`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
            Completed Today
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">
            Signed Consultation Activity
          </h2>
        </div>
        {renderStatusPill(`${completedTodayVisits.length} signed`, 'green')}
      </div>
      {completedTodayVisits.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm text-slate-600">
          No completed consultations today yet.
        </div>
      ) : (
        <div className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white">
          {completedTodayVisits.map((visit) => (
            <div key={visit.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-950">
                  {visit.patient_name || 'Unknown patient'}
                </p>
                <p className="text-xs text-slate-500">
                  {visit.patient_mrn ? `MRN ${visit.patient_mrn}` : `ID ${maskId(visit.patient_id)}`}{' '}
                  • Signed {new Date(visit.updated_at).toLocaleTimeString()}
                </p>
              </div>
              <VisitStatusBadge status={visit.status} size="sm" />
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderQueueWorkspace = () => (
    <div className="space-y-4">
      <div className={`${panelClass} p-4`}>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
              GOPD Queue
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-950">
              Consultation Queue Control
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Service-backed queue with near real-time polling. Selecting a
              patient anchors the encounter context.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {renderStatusPill(`${activeQueueCount} waiting`, 'blue')}
            {stats.emergency > 0
              ? renderStatusPill(`${stats.emergency} emergency`, 'rose')
              : renderStatusPill('No emergency flag', 'green')}
          </div>
        </div>
        <DoctorQueue
          onStartConsultation={handleStartConsultation}
          onViewVisit={handleViewVisit}
          onSelectPatient={(visit) => {
            handleSelectConsultationContext(visit);
          }}
          refreshToken={queueRefreshToken}
        />
      </div>
    </div>
  );

  const renderEncounterSummary = () => (
    <div className={`${panelClass} p-4`}>
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
          Patient Encounter
        </p>
        <h2 className="mt-1 text-lg font-semibold text-slate-950">
          Clinical Summary
        </h2>
      </div>
      {!encounterVisit ? (
        renderEmptyEncounter()
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {[
            ['Patient', encounterVisit.patient_name || 'Unknown patient'],
            [
              'Identifier',
              encounterVisit.patient_mrn
                ? `MRN ${encounterVisit.patient_mrn}`
                : `ID ${maskId(encounterVisit.patient_id)}`,
            ],
            ['Visit State', encounterVisit.status],
            [
              'Clinical Record',
              isEncounterCompleted
                ? 'Completed and locked'
                : isEncounterConsultationActive || encounterEntry
                  ? 'Consultation active'
                  : 'Not started',
            ],
            [
              'Vitals',
              encounterEntry?.consultation.vitals
                ? 'Captured in consultation record'
                : 'Pending clinical capture',
            ],
            [
              'Allergy / Risk',
              encounterVisit.intake_emergency_flag
                ? 'Emergency intake flag present'
                : 'Allergy feed pending',
            ],
            [
              'Lab State',
              encounterLabStatus === 'ready'
                ? 'Results available'
                : encounterLabStatus === 'pending'
                  ? 'Lab pending'
                  : 'No lab request',
            ],
            [
              'Disposition',
              encounterVisit.has_active_admission
                ? 'Admission active'
                : 'No active admission',
            ],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-200 bg-white/80 px-4 py-3 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                {label}
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-950">{value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderDocumentationWorkspace = (
    title: string,
    description: string,
    focus: string
  ) => (
    <div className={`${panelClass} p-4`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
            Clinical Documentation
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">{title}</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">
            {description}
          </p>
        </div>
        {renderStatusPill(focus, encounterVisit ? 'blue' : 'slate')}
      </div>
      {renderClinicalActions()}
      <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        This workspace opens the service-backed consultation record. Current
        fields are preserved in the existing consultation workflow; the visual
        shell keeps patient context visible before the record is opened.
      </div>
    </div>
  );

  const renderOrdersWorkspace = (
    title: string,
    description: string,
    action: 'lab' | 'results' | 'radiology' | 'prescription' | 'pharmacy'
  ) => {
    const isDemoOnly = action === 'radiology';
    const canUseActiveConsultation =
      isEncounterConsultationActive && !isEncounterCompleted;
    const canReviewResults = isEncounterConsultationActive;
    const canSendToPharmacy =
      allowedTransitions.includes(VisitStatus.PHARMACY_PENDING) &&
      !isTransitioning;
    const state =
      isDemoOnly
        ? 'pendingApi'
        : action === 'results'
          ? canReviewResults
            ? 'available'
            : 'requiresConsultation'
          : action === 'pharmacy'
            ? canSendToPharmacy
              ? 'available'
              : 'requiresConsultation'
            : canUseActiveConsultation
              ? 'available'
              : isEncounterCompleted
                ? 'locked'
                : 'requiresConsultation';

    const containerClass = isDemoOnly ? secondaryPanelClass : panelClass;
    return (
      <div className={`${containerClass} p-4`}>
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
              Orders & Treatment
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-950">{title}</h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">
              {description}
            </p>
          </div>
          {isDemoOnly
            ? renderActionState('pendingApi')
            : renderStatusPill('Service-backed workflow', 'green')}
        </div>
        <div className="mb-4 rounded-xl border border-slate-200 bg-white/75 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            {renderActionState(state)}
            {!isDemoOnly && renderStatusPill('Protected by active encounter context', 'blue')}
          </div>
          {state === 'requiresConsultation' && (
            <p className="mt-2 text-sm text-slate-600">
              Select a patient and start or resume consultation before using this action.
            </p>
          )}
          {state === 'locked' && (
            <p className="mt-2 text-sm text-slate-600">
              Completed consultation records are read-only. New orders require a new clinical encounter.
            </p>
          )}
        </div>
        {action === 'lab' && (
          <Button
            variant="primary"
            onClick={handleRequestLab}
            disabled={!canUseActiveConsultation}
          >
            Request Lab Test
          </Button>
        )}
        {action === 'results' && (
          <Button
            variant="primary"
            onClick={handleCheckLabResults}
            disabled={!canReviewResults}
          >
            Review Lab Results
          </Button>
        )}
        {action === 'prescription' && (
          <Button
            variant="primary"
            onClick={handleIssuePrescription}
            disabled={!canUseActiveConsultation}
          >
            Issue Prescription
          </Button>
        )}
        {action === 'pharmacy' && (
          <Button
            variant="primary"
            onClick={handleSendToPharmacy}
            disabled={
              !canSendToPharmacy
            }
          >
            {isTransitioning ? 'Sending...' : 'Send to Pharmacy'}
          </Button>
        )}
        {action === 'radiology' && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Frontend demonstration — clinical API pending. Radiology request
            routing will require a dedicated diagnostic imaging order workflow.
          </div>
        )}
        <div className="mt-4">{renderEncounterSummary()}</div>
      </div>
    );
  };

  const renderDispositionWorkspace = (
    title: string,
    description: string,
    action: 'followUp' | 'admission' | 'referral' | 'audit'
  ) => {
    const isPendingApi = action === 'referral' || action === 'audit';
    const containerClass = isPendingApi ? secondaryPanelClass : panelClass;
    return (
      <div className={`${containerClass} p-4`}>
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
              Disposition
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-950">{title}</h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">
              {description}
            </p>
          </div>
          {action === 'admission'
            ? renderStatusPill('Service-backed via visit details', 'green')
            : action === 'followUp'
              ? renderStatusPill('Recall support after completion', 'green')
              : renderActionState('pendingApi')}
        </div>
        <div className="mb-4 rounded-xl border border-slate-200 bg-white/75 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            {isPendingApi
              ? renderActionState('pendingApi')
              : encounterVisit
                ? renderActionState('available')
                : renderActionState('requiresConsultation', 'Requires selected patient')}
            {!isPendingApi && renderStatusPill('Encounter-linked disposition', 'blue')}
          </div>
        </div>
        {action === 'admission' && (
          <Button
            variant="primary"
            onClick={openEncounterVisitDetails}
            disabled={!encounterVisit}
          >
            Open Admission Request
          </Button>
        )}
        {action === 'followUp' && (
          <Button
            variant="primary"
            onClick={openEncounterConsultation}
            disabled={!encounterVisit}
          >
            Open Consultation Recall Controls
          </Button>
        )}
        {isPendingApi && (
          <div className="rounded-xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-900">
            Frontend demonstration — clinical API pending. This surface preserves
            the governance slot without creating unsupported clinical actions.
          </div>
        )}
        <div className="mt-4">{renderEncounterSummary()}</div>
      </div>
    );
  };

  const renderRecentActivity = () => (
    <div className={`${panelClass} p-4`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Movement Trace
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">
            Recent Clinical Activity
          </h2>
        </div>
      </div>
      {recentActivity.length === 0 ? (
        <p className="text-sm text-slate-500">No recent updates yet.</p>
      ) : (
        <div className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white">
          {recentActivity.map((visit) => (
            <button
              key={visit.id}
              type="button"
              onClick={() => handleSelectConsultationContext(visit)}
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-sky-50/50"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-950">
                  {visit.patient_name || 'Unknown patient'}
                </p>
                <p className="text-xs text-slate-500">
                  Updated {new Date(visit.updated_at).toLocaleTimeString()}
                </p>
              </div>
              <VisitStatusBadge status={visit.status} size="sm" />
            </button>
          ))}
        </div>
      )}
    </div>
  );

  const renderOverview = () => (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {renderMetricCard(
          'Active Queue',
          activeQueueCount,
          'Waiting for doctor action',
          'blue'
        )}
        {renderMetricCard(
          'In Consultation',
          stats.inProgress,
          'Currently under doctor care',
          'slate'
        )}
        {renderMetricCard(
          'Pending Labs',
          stats.pendingLab,
          'Awaiting diagnostic results',
          'amber'
        )}
        {renderMetricCard(
          'Emergency Flagged',
          stats.emergency,
          'Requires clinical attention',
          stats.emergency > 0 ? 'rose' : 'green'
        )}
        {renderMetricCard(
          'Completed Today',
          stats.completedToday,
          'Signed clinical encounters',
          'green'
        )}
      </div>
      {statsError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {statsError}
        </div>
      )}
      <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        {renderQueueWorkspace()}
        <div className="space-y-4">
          {renderActiveConsultations()}
          {renderRecentActivity()}
        </div>
      </div>
    </div>
  );

  const renderWorkspace = () => {
    switch (activeWorkspace) {
      case 'overview':
        return renderOverview();
      case 'queue':
        return renderQueueWorkspace();
      case 'active':
        return (
          <div className="space-y-4">
            <div className={`${panelClass} p-4`}>{renderClinicalActions()}</div>
            {renderActiveConsultations()}
          </div>
        );
      case 'completed':
        return renderCompletedConsultations();
      case 'summary':
        return renderEncounterSummary();
      case 'complaints':
        return renderDocumentationWorkspace(
          'Complaints & History',
          'Document presenting complaints, relevant history, and clinical context inside the protected consultation record.',
          'History capture'
        );
      case 'examination':
        return renderDocumentationWorkspace(
          'Examination Findings',
          'Record vitals and examination findings while preserving the active visit and doctor context.',
          'Vitals and findings'
        );
      case 'diagnosis':
        return renderDocumentationWorkspace(
          'Diagnosis / Assessment',
          'Capture diagnosis, differential assessment, and clinical impression in the encounter record.',
          'Assessment'
        );
      case 'notes':
        return renderDocumentationWorkspace(
          'Clinical Notes',
          'Maintain signed clinical notes with draft and completion controls preserved.',
          'Clinical notes'
        );
      case 'labRequests':
        return renderOrdersWorkspace(
          'Lab Requests',
          'Create service-backed laboratory requests from the active consultation. Billing item creation remains preserved.',
          'lab'
        );
      case 'labResults':
        return renderOrdersWorkspace(
          'Lab Results',
          'Review released diagnostic results with abnormal, critical, amended, and specimen trace visibility.',
          'results'
        );
      case 'radiology':
        return renderOrdersWorkspace(
          'Radiology Requests',
          'Governed placeholder for future imaging order workflow.',
          'radiology'
        );
      case 'prescription':
        return renderOrdersWorkspace(
          'Prescription Plan',
          'Issue prescriptions from governed pharmacy catalog items tied to the active consultation.',
          'prescription'
        );
      case 'pharmacy':
        return renderOrdersWorkspace(
          'Send to Pharmacy',
          'Move eligible prescription visits into pharmacy workflow using preserved visit transition controls.',
          'pharmacy'
        );
      case 'followUp':
        return renderDispositionWorkspace(
          'Follow-Up / Recall',
          'Manage clinical continuity after consultation completion. Recall suggestions remain preserved in the consultation record.',
          'followUp'
        );
      case 'admission':
        return renderDispositionWorkspace(
          'Admission Request',
          'Open the existing visit details workflow to submit admission requests where clinically required.',
          'admission'
        );
      case 'referral':
        return renderDispositionWorkspace(
          'Internal Referral',
          'Governed placeholder for clinical referral routing to Specialist Clinics, A&E, Gynecology, Pediatrics, Maternity, or other departments.',
          'referral'
        );
      case 'audit':
        return renderDispositionWorkspace(
          'Consultation Audit Trail',
          'Governed placeholder for encounter audit trace, actor history, and clinical record movement events.',
          'audit'
        );
      default:
        return renderOverview();
    }
  };

  const renderEncounterRail = () => (
    <aside className={`${panelClass} h-fit p-4 xl:sticky xl:top-4`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
            Encounter Context
          </p>
          <h2 className="mt-1 text-base font-semibold text-slate-950">
            Clinical Record Anchor
          </h2>
        </div>
        <span className="h-2.5 w-2.5 rounded-full bg-cyan-500 shadow-[0_0_0_4px_rgba(34,211,238,0.16)]" />
      </div>

      {!encounterVisit ? (
        renderEmptyEncounter()
      ) : (
        <div className="space-y-3">
          <div className="rounded-2xl border border-[#0B4DA2]/15 bg-gradient-to-br from-[#F5FAFE] to-white p-4 shadow-sm">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
              Selected patient
            </p>
            <p className="text-lg font-semibold leading-tight text-slate-950">
              {encounterVisit.patient_name || 'Unknown patient'}
            </p>
            <p className="mt-1 text-sm text-slate-600">
              {encounterVisit.patient_mrn
                ? `MRN ${encounterVisit.patient_mrn}`
                : `Patient ID ${maskId(encounterVisit.patient_id)}`}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <VisitStatusBadge status={encounterVisit.status} size="sm" />
              {encounterVisit.intake_emergency_flag &&
                renderStatusPill('Emergency', 'rose')}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white/80 px-3 py-2">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                Context state
              </span>
              {isEncounterCompleted
                ? renderActionState('locked', 'Locked')
                : isEncounterConsultationActive || encounterEntry
                  ? renderActionState('available', 'Active')
                  : renderActionState('requiresConsultation', 'Pending')}
            </div>
          </div>

          {[
            ['Visit', maskId(encounterVisit.id)],
            [
              'Queue State',
              isEncounterConsultationActive || encounterEntry
                ? 'Clinical encounter active'
                : 'Awaiting consultation start',
            ],
            [
              'Vitals',
              encounterEntry?.consultation.vitals ? 'Captured' : 'Pending',
            ],
            ['Allergy / Risk', 'Clinical allergy API pending'],
            [
              'Lab',
              encounterLabStatus === 'ready'
                ? 'Results available'
                : encounterLabStatus === 'pending'
                  ? 'Pending result'
                  : 'No request',
            ],
            [
              'Pharmacy',
              encounterVisit.status === VisitStatus.PHARMACY_PENDING
                ? 'Sent to pharmacy'
                : allowedTransitions.includes(VisitStatus.PHARMACY_PENDING)
                  ? 'Ready after prescription'
                  : 'Not ready',
            ],
            [
              'Admission',
              encounterVisit.has_active_admission ? 'Active admission' : 'No active admission',
            ],
            [
              'Audit Lock',
              isEncounterCompleted
                ? 'Completed record locked'
                : isEncounterConsultationActive || encounterEntry
                  ? 'Draft editable'
                  : 'No consultation record',
            ],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-xl border border-slate-200 bg-white/85 px-3 py-2.5 shadow-sm"
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                {label}
              </p>
              <p className="mt-1 text-sm font-medium text-slate-900">{value}</p>
            </div>
          ))}

          <div className="grid gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={openEncounterConsultation}
              disabled={!encounterVisit}
              className="justify-center"
            >
              Open Encounter
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={openEncounterVisitDetails}
              disabled={!encounterVisit}
              className="justify-center"
            >
              Visit Details
            </Button>
          </div>
        </div>
      )}
    </aside>
  );

  return (
    <main className="min-h-screen bg-[linear-gradient(135deg,#eef6fb_0%,#f8fafc_42%,#e8f1f8_100%)] text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-[1680px] gap-4 px-4 py-4 lg:px-5">
        <aside className="hidden w-[270px] shrink-0 lg:block">
          <div className="sticky top-4 rounded-3xl border border-slate-200/80 bg-[#071B35] p-2.5 text-white shadow-[0_24px_80px_-45px_rgba(7,27,53,0.9)]">
            <div className="rounded-2xl border border-white/10 bg-white/10 px-3 py-2.5">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-200">
                    GOPD Clinical
                  </p>
                  <p className="mt-1 truncate text-sm font-semibold text-white">
                    {doctorDisplayName}
                  </p>
                </div>
                <span className="rounded-full border border-emerald-300/30 bg-emerald-400/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-emerald-100">
                  Active
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between rounded-xl bg-white/10 px-3 py-1.5 text-xs text-slate-200">
                <span>Department</span>
                <span className="font-semibold text-white">GOPD</span>
              </div>
            </div>

            <nav className="mt-3 max-h-[calc(100vh-156px)] space-y-3 overflow-y-auto pr-1">
              {WORKSPACE_NAV.map((group) => (
                <div key={group.group}>
                  <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                    {group.group}
                  </p>
                  <div className="space-y-1">
                    {group.items.map((item) => {
                      const active = activeWorkspace === item.key;
                      const apiPending = API_PENDING_WORKSPACES.has(item.key);
                      const primary = PRIMARY_WORKFLOW_WORKSPACES.has(item.key);
                      return (
                        <button
                          key={item.key}
                          type="button"
                          onClick={() => setActiveWorkspace(item.key)}
                          className={`flex w-full items-center gap-2 rounded-xl px-2.5 py-1.5 text-left text-[13px] transition ${
                            active
                              ? 'bg-cyan-400/16 text-white ring-1 ring-cyan-300/30'
                              : apiPending
                                ? 'text-slate-500 hover:bg-white/8 hover:text-slate-200'
                                : 'text-slate-300 hover:bg-white/10 hover:text-white'
                          }`}
                        >
                          <span
                            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-[9px] font-bold ${
                              active
                                ? 'bg-cyan-300 text-[#071B35]'
                                : apiPending
                                  ? 'bg-white/5 text-slate-500'
                                  : 'bg-white/10 text-cyan-100'
                            }`}
                          >
                            {item.short}
                          </span>
                          <span className="min-w-0 truncate">{item.label}</span>
                          {primary && !active && (
                            <span className="ml-auto h-1.5 w-1.5 rounded-full bg-cyan-300/80" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </nav>
          </div>
        </aside>

        <section className="min-w-0 flex-1 space-y-4">
          <header className={`${panelClass} overflow-hidden`}>
            <div className="border-b border-slate-200 bg-gradient-to-br from-white via-sky-50/60 to-slate-50 px-5 py-4">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#0B4DA2]">
                    {HOSPITAL_NAME} • KSH Enterprise HIS
                  </p>
                  <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 md:text-3xl">
                    GOPD Clinical Consultation Workspace
                  </h1>
                  <p className="mt-2 max-w-3xl text-sm text-slate-600">
                    Reception moves the patient. Doctor owns the encounter. HIS
                    preserves the clinical record.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 xl:w-[520px]">
                  {[
                    ['Queue', activeQueueCount],
                    ['In consult', stats.inProgress],
                    ['Pending labs', stats.pendingLab],
                    ['Completed', stats.completedToday],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      className="rounded-xl border border-slate-200 bg-white/85 px-3 py-2 shadow-sm"
                    >
                      <p className="font-semibold uppercase tracking-[0.14em] text-slate-500">
                        {label}
                      </p>
                      <p className="mt-1 text-lg font-semibold text-slate-950">
                        {statsLoading ? '—' : value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-100/70 px-5 py-3 text-sm">
              <div className="min-w-0">
                <span className="font-semibold text-slate-900">
                  {activeWorkspaceLabel}
                </span>
                <span className="mx-2 text-slate-300">/</span>
                <span className="text-slate-600">Department: GOPD</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {activeConsultation
                  ? renderStatusPill('Active consultation', 'green')
                  : renderStatusPill('Queue monitoring', 'blue')}
                {stats.emergency > 0
                  ? renderStatusPill(`${stats.emergency} emergency flagged`, 'rose')
                  : renderStatusPill('No emergency flag', 'green')}
              </div>
            </div>
          </header>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="min-w-0">{renderWorkspace()}</div>
            {renderEncounterRail()}
          </div>
        </section>
      </div>

      {consultationVisit && (
        <ConsultationModal
          visitId={consultationVisit.id}
          visitSummary={{
            patientName: consultationVisit.patient_name,
            status: consultationVisit.status,
            mrn: consultationVisit.patient_mrn,
            intakeEmergencyFlag: consultationVisit.intake_emergency_flag,
          }}
          isOpen={isConsultationModalOpen}
          onClose={() => {
            setIsConsultationModalOpen(false);
            if (
              !activeConsultation ||
              activeConsultation.visitId !== consultationVisit.id
            ) {
              setConsultationVisit(null);
            }
          }}
          onComplete={handleConsultationComplete}
          onConsultationReady={handleConsultationReady}
          existingConsultation={null}
        />
      )}

      <LabResultsViewerModal
        visit={consultationVisit}
        doctorFullName={doctorFullName}
        isOpen={labResultsOpen}
        onClose={() => setLabResultsOpen(false)}
      />

      {activeConsultation && isLabRequestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 shadow-2xl">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0B4DA2]">
                    Investigation Order
                  </p>
                  <h2 className="mt-1 text-2xl font-semibold text-slate-950">
                    Request Lab Test
                  </h2>
                </div>
                <button
                  onClick={() => setIsLabRequestModalOpen(false)}
                  className="text-2xl text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <LabRequestForm
                visitId={activeConsultation.visitId}
                consultationId={activeConsultation.consultationId}
                onSuccess={handleLabRequestSuccess}
                onCancel={() => setIsLabRequestModalOpen(false)}
                compact
              />
            </div>
          </div>
        </div>
      )}

      {activeConsultation && isPrescriptionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 shadow-2xl">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0B4DA2]">
                    Treatment Plan
                  </p>
                  <h2 className="mt-1 text-2xl font-semibold text-slate-950">
                    Issue Prescription
                  </h2>
                </div>
                <button
                  onClick={() => setIsPrescriptionModalOpen(false)}
                  className="text-2xl text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <PrescriptionForm
                visitId={activeConsultation.visitId}
                consultationId={activeConsultation.consultationId}
                onSuccess={handlePrescriptionSuccess}
                onCancel={() => setIsPrescriptionModalOpen(false)}
                compact
              />
            </div>
          </div>
        </div>
      )}

      {selectedVisit && (
        <VisitDetailsModal
          visitId={selectedVisit.id}
          isOpen={isVisitDetailsModalOpen}
          onClose={() => {
            setIsVisitDetailsModalOpen(false);
            setSelectedVisit(null);
          }}
          hiddenTransitions={['LAB_REQUESTED']}
          purposeOfUse={PurposeOfUse.TREATMENT}
          allowAdmissionRequest
        />
      )}

      <footer className="border-t border-slate-200 bg-white/80 py-4">
        <div className="mx-auto max-w-[1680px] px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            GOPD Clinical Consultation Workspace • {HOSPITAL_NAME} •{' '}
            {new Date().toLocaleDateString()}
          </p>
        </div>
      </footer>
    </main>
  );
}
