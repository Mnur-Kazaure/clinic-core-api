// /projects/clinic-monorepo/clinic-app/src/app/reception/page.tsx
'use client';

import { ReactNode, useEffect, useState } from 'react';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { StartVisitModal } from '@/app/reception/components/visit/StartVisitModal';
import { VisitDetailsModal } from '@/app/reception/components/visit/VisitDetailsModal';
import { VisitQueue } from '@/app/reception/components/visit/VisitQueue';
import { PatientRegistrationForm } from '@/app/reception/components/patient/PatientRegistrationForm';
import { PatientRegistryPanel } from '@/app/reception/components/patient/PatientRegistryPanel';
import { VisitResponse } from '@/shared/types';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';
import { PurposeOfUse, VisitServiceLine } from '@/shared/enums';
import { roleSessionService } from '@/domains/auth/services/roleSessionService';
import { authService } from '@/domains/auth/services/authService';
import {
  FollowUpListItem,
  followUpService,
} from '@/domains/followup/services/followupService';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { HOSPITAL_NAME } from '@/shared/constants/branding';

type IntakeWorkspaceKey =
  | 'overview'
  | 'lookup'
  | 'registration'
  | 'startVisit'
  | 'queue'
  | 'triage'
  | 'doctorAssignment'
  | 'reassignment'
  | 'referral'
  | 'emergency'
  | 'followUp'
  | 'audit';

const intakeNavigation: {
  key: IntakeWorkspaceKey;
  label: string;
  description: string;
  code: string;
}[] = [
  {
    key: 'overview',
    label: 'Intake Overview',
    description: 'Load, pressure, movement',
    code: 'IO',
  },
  {
    key: 'lookup',
    label: 'Patient Lookup',
    description: 'Find before registration',
    code: 'PL',
  },
  {
    key: 'registration',
    label: 'Patient Registration',
    description: 'New patient capture',
    code: 'PR',
  },
  {
    key: 'startVisit',
    label: 'Start OPD Visit',
    description: 'Create visit and route',
    code: 'SV',
  },
  {
    key: 'queue',
    label: 'Queue Intelligence',
    description: 'Operational queue board',
    code: 'QI',
  },
  {
    key: 'triage',
    label: 'Triage Routing',
    description: 'Clinical screening path',
    code: 'TR',
  },
  {
    key: 'doctorAssignment',
    label: 'Doctor Assignment',
    description: 'Queue to clinician',
    code: 'DA',
  },
  {
    key: 'reassignment',
    label: 'Reassignment / Rerouting',
    description: 'Wrong queue correction',
    code: 'RR',
  },
  {
    key: 'referral',
    label: 'Internal Referral',
    description: 'Specialty routing',
    code: 'IR',
  },
  {
    key: 'emergency',
    label: 'Emergency Escalation',
    description: 'GOPD to A&E',
    code: 'EE',
  },
  {
    key: 'followUp',
    label: 'Follow-Up Arrival',
    description: 'Return visit linkage',
    code: 'FA',
  },
  {
    key: 'audit',
    label: 'Intake Audit Trail',
    description: 'Movement trace',
    code: 'AT',
  },
];

const navigationGroups: {
  label: string;
  items: IntakeWorkspaceKey[];
}[] = [
  {
    label: 'GOPD Operations',
    items: ['overview', 'queue', 'lookup', 'registration', 'startVisit'],
  },
  {
    label: 'Clinical Movement',
    items: [
      'triage',
      'doctorAssignment',
      'reassignment',
      'referral',
      'emergency',
    ],
  },
  {
    label: 'Continuity & Traceability',
    items: ['followUp', 'audit'],
  },
];

const demoBadge =
  'Frontend demonstration - backend routing API pending';

function OperationalPanel({
  title,
  eyebrow,
  children,
  className = '',
  action,
}: {
  title?: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <section
      className={`overflow-hidden rounded-xl border border-slate-200/80 bg-white/95 shadow-[0_16px_40px_rgba(15,23,42,0.06)] ${className}`}
    >
      {(title || eyebrow || action) && (
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-white px-4 py-3">
          <div className="min-w-0">
            {eyebrow && (
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-700">
                {eyebrow}
              </p>
            )}
            {title && (
              <h3 className="mt-0.5 truncate text-sm font-semibold text-slate-950">
                {title}
              </h3>
            )}
          </div>
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export default function ReceptionPage() {
  const dashboardUser = useDashboardUser();
  const [isStartVisitModalOpen, setIsStartVisitModalOpen] = useState(false);
  const [activeWorkspace, setActiveWorkspace] =
    useState<IntakeWorkspaceKey>('overview');
  const [refreshQueue, setRefreshQueue] = useState(0);
  const [selectedVisit, setSelectedVisit] = useState<VisitResponse | null>(null);
  const [selectedVisitId, setSelectedVisitId] = useState<string | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [recentVisits, setRecentVisits] = useState<VisitResponse[]>([]);
  const [recentLoading, setRecentLoading] = useState(false);
  const [recentError, setRecentError] = useState<string | null>(null);
  const [recentMrnIssued, setRecentMrnIssued] = useState<string | null>(null);
  const [recentPatientName, setRecentPatientName] = useState<string | null>(null);
  const [queueStats, setQueueStats] = useState({
    total: 0,
    waiting: 0,
    completed: 0,
    emergency: 0,
  });
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [followUps, setFollowUps] = useState<{
    today: FollowUpListItem[];
    tomorrow: FollowUpListItem[];
  }>({
    today: [],
    tomorrow: [],
  });
  const [followUpsLoading, setFollowUpsLoading] = useState(false);
  const [followUpsError, setFollowUpsError] = useState<string | null>(null);
  const [followUpActionError, setFollowUpActionError] = useState<string | null>(null);
  const [followUpActionSuccess, setFollowUpActionSuccess] = useState<string | null>(null);
  const [followUpSearch, setFollowUpSearch] = useState('');
  const [startingFollowUpId, setStartingFollowUpId] = useState<string | null>(null);
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);
  const [rescheduleTarget, setRescheduleTarget] = useState<FollowUpListItem | null>(null);
  const [rescheduleDueAt, setRescheduleDueAt] = useState('');
  const [rescheduleReason, setRescheduleReason] = useState('Patient requested new date');
  const [rescheduleSubmitting, setRescheduleSubmitting] = useState(false);
  const [rescheduleError, setRescheduleError] = useState<string | null>(null);
  const [currentDepartmentId, setCurrentDepartmentId] = useState<string | null>(null);
  const [currentDepartmentName, setCurrentDepartmentName] = useState<string | null>(null);
  const [allowedDepartments, setAllowedDepartments] = useState<
    { id: string; name: string; is_primary: boolean }[]
  >([]);
  const [switchingDepartment, setSwitchingDepartment] = useState(false);
  const [departmentError, setDepartmentError] = useState<string | null>(null);

  const handleVisitCreated = () => {
    setIsStartVisitModalOpen(false);
    setRefreshQueue((prev) => prev + 1);
  };

  const handlePatientRegistered = (mrn?: string | null, patientName?: string | null) => {
    if (mrn) {
      setRecentMrnIssued(mrn);
    }
    if (patientName) {
      setRecentPatientName(patientName);
    }
    setActiveWorkspace('startVisit');
  };

  const handleVisitClick = (visit: VisitResponse) => {
    setSelectedVisit(visit);
    setSelectedVisitId(visit.id);
    setIsDetailsModalOpen(true);
  };

  const refreshDashboard = async () => {
    try {
      const queue = await visitService.getQueue(undefined, currentDepartmentId);
      const pending = queue.filter(
        (visit) => visit.status === 'PHARMACY_PENDING'
      );
      await Promise.all(
        pending.map((visit) =>
          visitService.recheckAutoComplete(visit.id).catch(() => null)
        )
      );
    } finally {
      setRefreshQueue((prev) => prev + 1);
    }
  };

  const loadFollowUps = async () => {
    try {
      setFollowUpsLoading(true);
      setFollowUpsError(null);
      const data = await followUpService.getReceptionFollowUps();
      setFollowUps({
        today: data.today || [],
        tomorrow: data.tomorrow || [],
      });
    } catch (error) {
      console.error('Failed to load reception follow-ups:', error);
      setFollowUpsError('Unable to load follow-up worklist.');
    } finally {
      setFollowUpsLoading(false);
    }
  };

  const openRescheduleModal = (item: FollowUpListItem) => {
    const suggested = new Date(Date.now() + 24 * 60 * 60 * 1000);
    suggested.setHours(10, 0, 0, 0);
    setRescheduleTarget(item);
    setRescheduleDueAt(suggested.toISOString().slice(0, 16));
    setRescheduleReason('Patient requested new date');
    setRescheduleError(null);
    setRescheduleModalOpen(true);
  };

  const closeRescheduleModal = () => {
    setRescheduleModalOpen(false);
    setRescheduleTarget(null);
    setRescheduleError(null);
    setRescheduleSubmitting(false);
  };

  const handleStartLinkedFollowUpVisit = async (item: FollowUpListItem) => {
    try {
      setStartingFollowUpId(item.id);
      setFollowUpActionError(null);
      setFollowUpActionSuccess(null);

      const activeVisit = await visitService.getActiveVisit(item.patient_id_canonical);
      if (activeVisit) {
        setFollowUpActionError(
          `Active visit already exists for ${item.patient_name || 'this patient'}. Continue the active visit instead of starting another one.`
        );
        setSelectedVisit(activeVisit);
        setSelectedVisitId(activeVisit.id);
        setIsDetailsModalOpen(true);
        return;
      }

      const visit = await visitService.startVisit({
        patient_id: item.patient_id_canonical,
        assigned_doctor_id: item.owner_user_id,
        service_line: item.recommended_service_line as VisitServiceLine,
        linked_follow_up_id: item.id,
      });
      setFollowUpActionSuccess(
        `Linked visit started for ${item.patient_name || 'patient'} (${visit.id.slice(
          0,
          8
        )}...).`
      );
      setSelectedVisit(visit);
      setRefreshQueue((prev) => prev + 1);
      await loadFollowUps();
    } catch (error: unknown) {
      const detail =
        typeof error === 'object' &&
        error &&
        'response' in error &&
        typeof (error as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (error as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setFollowUpActionError(detail || 'Unable to start linked follow-up visit.');
    } finally {
      setStartingFollowUpId(null);
    }
  };

  const handleRescheduleSubmit = async () => {
    if (!rescheduleTarget) return;
    try {
      setRescheduleSubmitting(true);
      setRescheduleError(null);
      await followUpService.rescheduleFollowUp(rescheduleTarget.id, {
        due_at: new Date(rescheduleDueAt).toISOString(),
        reason: rescheduleReason,
        justification: 'Reception follow-up reschedule',
      });
      closeRescheduleModal();
      setFollowUpActionSuccess(
        `Follow-up rescheduled for ${rescheduleTarget.patient_name || 'patient'}.`
      );
      await loadFollowUps();
    } catch (error: unknown) {
      const detail =
        typeof error === 'object' &&
        error &&
        'response' in error &&
        typeof (error as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (error as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setRescheduleError(detail || 'Unable to reschedule follow-up.');
    } finally {
      setRescheduleSubmitting(false);
    }
  };

  const maskId = (value?: string | null) =>
    value ? `${value.substring(0, 8)}...` : 'Unknown';

  const filterFollowUps = (items: FollowUpListItem[]) => {
    const term = followUpSearch.trim().toLowerCase();
    if (!term) return items;
    return items.filter((item) => {
      const patientName = (item.patient_name || '').toLowerCase();
      const patientMrn = (item.patient_mrn || '').toLowerCase();
      const patientId = item.patient_id_canonical.toLowerCase();
      const reason = (item.reason || '').toLowerCase();
      return (
        patientName.includes(term) ||
        patientMrn.includes(term) ||
        patientId.includes(term) ||
        reason.includes(term)
      );
    });
  };

  useEffect(() => {
    let isMounted = true;

    async function loadRecent() {
      try {
        setRecentLoading(true);
        setRecentError(null);
        const data = await visitService.getRecentVisits(5, currentDepartmentId);
        if (isMounted) {
          setRecentVisits(data);
        }
      } catch (error) {
        console.error('Failed to load recent activity:', error);
        if (isMounted) {
          setRecentError('Unable to load recent activity.');
        }
      } finally {
        if (isMounted) {
          setRecentLoading(false);
        }
      }
    }

    loadRecent();
    return () => {
      isMounted = false;
    };
  }, [refreshQueue, currentDepartmentId]);

  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null;
    void loadFollowUps();
    intervalId = setInterval(() => {
      void loadFollowUps();
    }, 60000);
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [refreshQueue]);

  useEffect(() => {
    let isMounted = true;

    async function loadStats() {
      try {
        setStatsLoading(true);
        setStatsError(null);
        const [queueData, completedData] = await Promise.all([
          visitService.getQueue(undefined, currentDepartmentId),
          visitService.getQueue('COMPLETED', currentDepartmentId),
        ]);
        if (!isMounted) return;
        const total = queueData.length;
        const waiting = queueData.filter((visit) =>
          ['REGISTERED', 'TRIAGED'].includes(visit.status)
        ).length;
        const completed = completedData.length;
        const emergency = queueData.filter(
          (visit) => visit.intake_emergency_flag
        ).length;
        setQueueStats({ total, waiting, completed, emergency });
      } catch {
        if (isMounted) {
          setStatsError('Metrics unavailable');
          setQueueStats({ total: 0, waiting: 0, completed: 0, emergency: 0 });
        }
      } finally {
        if (isMounted) {
          setStatsLoading(false);
        }
      }
    }

    loadStats();
    return () => {
      isMounted = false;
    };
  }, [refreshQueue, currentDepartmentId]);

  useEffect(() => {
    let cancelled = false;

    async function loadDepartmentContext() {
      try {
        setDepartmentError(null);
        const user = await roleSessionService.getCurrentUser();
        if (cancelled) return;
        setCurrentDepartmentId(user.current_department_id || null);
        setCurrentDepartmentName(user.current_department_name || null);
        setAllowedDepartments(user.allowed_departments || []);
      } catch (error) {
        if (cancelled) return;
        console.error('Failed to load department context:', error);
        setDepartmentError('Unable to load department context.');
      }
    }

    loadDepartmentContext();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleDepartmentSwitch = async (departmentId: string) => {
    try {
      setSwitchingDepartment(true);
      setDepartmentError(null);
      await authService.switchDepartment(departmentId);
      const user = await roleSessionService.getCurrentUser();
      setCurrentDepartmentId(user.current_department_id || null);
      setCurrentDepartmentName(user.current_department_name || null);
      setAllowedDepartments(user.allowed_departments || []);
      setRefreshQueue((prev) => prev + 1);
    } catch (error) {
      console.error('Failed to switch department:', error);
      setDepartmentError('Department switch failed. Please retry.');
    } finally {
      setSwitchingDepartment(false);
    }
  };

  useEffect(() => {
    if (!recentMrnIssued) return;
    const timer = setTimeout(() => {
      setRecentMrnIssued(null);
      setRecentPatientName(null);
    }, 12000);
    return () => clearTimeout(timer);
  }, [recentMrnIssued]);

  useEffect(() => {
    if (!followUpActionSuccess) return;
    const timer = setTimeout(() => setFollowUpActionSuccess(null), 9000);
    return () => clearTimeout(timer);
  }, [followUpActionSuccess]);

  const formatStat = (value: number) => (statsLoading ? '-' : value);
  const receptionistName = getDashboardUserDisplayName(dashboardUser);
  const resolvedDepartmentName =
    currentDepartmentName ||
    allowedDepartments.find((department) => department.id === currentDepartmentId)?.name ||
    allowedDepartments.find((department) => department.is_primary)?.name ||
    allowedDepartments[0]?.name ||
    'GOPD';
  const activeWorkspaceMeta =
    intakeNavigation.find((item) => item.key === activeWorkspace) ||
    intakeNavigation[0];
  const followUpArrivals = followUps.today.length + followUps.tomorrow.length;
  const topOperationalStats = [
    {
      label: 'Active intake load',
      value: formatStat(queueStats.total),
      tone: 'text-blue-700',
      helper: 'GOPD queue scope',
    },
    {
      label: 'Waiting patients',
      value: formatStat(queueStats.waiting),
      tone: 'text-amber-700',
      helper: 'Registered / triaged',
    },
    {
      label: 'Triage pressure',
      value: formatStat(queueStats.waiting + queueStats.emergency),
      tone: 'text-cyan-700',
      helper: 'Review candidates',
    },
    {
      label: 'Emergency flags',
      value: formatStat(queueStats.emergency),
      tone: 'text-rose-700',
      helper: 'Escalation watch',
    },
    {
      label: 'Follow-up arrivals',
      value: followUpArrivals,
      tone: 'text-emerald-700',
      helper: 'Today / tomorrow',
    },
    {
      label: 'Active referrals',
      value: 2,
      tone: 'text-indigo-700',
      helper: 'Demo routing queue',
    },
  ];

  const getWaitMinutes = (visit: VisitResponse) =>
    Math.max(
      0,
      Math.floor(
        (Date.now() - new Date(visit.created_at).getTime()) / 60000
      )
    );

  const getWaitSignal = (visit: VisitResponse) => {
    const waitMinutes = getWaitMinutes(visit);
    if (visit.intake_emergency_flag) {
      return {
        label: 'Emergency',
        className: 'border-rose-200 bg-rose-50 text-rose-800',
        rail: 'bg-rose-500',
      };
    }
    if (waitMinutes >= 60) {
      return {
        label: 'High wait',
        className: 'border-amber-200 bg-amber-50 text-amber-800',
        rail: 'bg-amber-500',
      };
    }
    if (waitMinutes >= 30) {
      return {
        label: 'Watch',
        className: 'border-blue-200 bg-blue-50 text-blue-800',
        rail: 'bg-blue-500',
      };
    }
    return {
      label: 'Normal',
      className: 'border-emerald-200 bg-emerald-50 text-emerald-800',
      rail: 'bg-emerald-500',
    };
  };

  const renderQueueIntelligenceRows = (limit = 6) => (
    <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white">
      {recentVisits.slice(0, limit).map((visit) => {
        const waitSignal = getWaitSignal(visit);
        const waitMinutes = getWaitMinutes(visit);
        return (
          <button
            key={visit.id}
            type="button"
            onClick={() => handleVisitClick(visit)}
            className="group grid w-full grid-cols-1 gap-3 px-3 py-3 text-left transition hover:bg-slate-50 lg:grid-cols-[8px_minmax(180px,1.2fr)_minmax(150px,0.8fr)_minmax(160px,0.9fr)_auto]"
          >
            <div
              className={`hidden h-full min-h-14 rounded-full lg:block ${waitSignal.rail}`}
            />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="truncate text-sm font-semibold text-slate-950">
                  {visit.patient_name || 'Unknown patient'}
                </p>
                {visit.intake_emergency_flag && (
                  <span className="rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-rose-700">
                    Urgent
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {visit.patient_mrn
                  ? `MRN ${visit.patient_mrn}`
                  : `ID ${maskId(visit.patient_id)}`}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Queue State
              </p>
              <div className="mt-1">
                <VisitStatusBadge status={visit.status} size="sm" />
              </div>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Wait Signal
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${waitSignal.className}`}
                >
                  {waitSignal.label}
                </span>
                <span className="text-xs text-slate-500">{waitMinutes}m</span>
              </div>
            </div>
            <div className="flex items-center gap-2 lg:justify-end">
              <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600">
                View
              </span>
            </div>
          </button>
        );
      })}
      {recentVisits.length === 0 && (
        <div className="px-3 py-8 text-center text-sm text-slate-500">
          No queue activity available yet.
        </div>
      )}
    </div>
  );

  const renderWorkspaceHeader = (
    title: string,
    description: string,
    badge?: string
  ) => (
    <div className="mb-5 flex flex-col gap-3 rounded-xl border border-slate-200/80 bg-white/90 px-4 py-4 shadow-[0_12px_30px_rgba(15,23,42,0.05)] lg:flex-row lg:items-start lg:justify-between">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-700">
          GOPD Intake Operations
        </p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950 lg:text-2xl">
          {title}
        </h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
          {description}
        </p>
      </div>
      {badge && (
        <span className="inline-flex w-fit rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-800">
          {badge}
        </span>
      )}
    </div>
  );

  const renderDemoNotice = () => (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
      {demoBadge}
    </div>
  );

  const renderRecentMovement = () => (
    <OperationalPanel
      title="Recent Patient Movement"
      eyebrow="Movement Intelligence"
    >
      {recentLoading && (
        <div className="text-sm text-slate-500">Loading movement activity...</div>
      )}
      {recentError && <div className="text-sm text-red-600">{recentError}</div>}
      {!recentLoading && !recentError && recentVisits.length === 0 && (
        <div className="text-sm text-slate-500">No recent movement yet.</div>
      )}
      {!recentLoading && !recentError && recentVisits.length > 0 && (
        <div className="space-y-3">
          {recentVisits.slice(0, 5).map((visit) => (
            <button
              key={visit.id}
              type="button"
              onClick={() => handleVisitClick(visit)}
              className="w-full rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2 text-left transition hover:border-blue-200 hover:bg-blue-50/50 hover:shadow-sm"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="min-w-0 truncate text-sm font-semibold text-slate-950">
                  {visit.patient_name || 'Unknown patient'}
                </p>
                <VisitStatusBadge status={visit.status} size="sm" />
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {visit.patient_mrn
                  ? `MRN: ${visit.patient_mrn}`
                  : `ID: ${maskId(visit.patient_id)}`}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Updated {new Date(visit.updated_at).toLocaleTimeString()}
              </p>
            </button>
          ))}
        </div>
      )}
    </OperationalPanel>
  );

  const renderFollowUpWorklist = () => (
    <OperationalPanel
      title="Follow-Up Arrival Worklist"
      eyebrow="Continuity Queue"
    >
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs leading-5 text-slate-500">
          Check in returning patients through linked follow-up records. Existing
          active visits are detected before another visit is started.
        </p>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => void loadFollowUps()}
          disabled={followUpsLoading}
        >
          {followUpsLoading ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>
      <Input
        label="Quick Search"
        placeholder="Name, MRN, patient ID, reason..."
        value={followUpSearch}
        onChange={(event) => setFollowUpSearch(event.target.value)}
      />

      {followUpsError && (
        <div className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {followUpsError}
        </div>
      )}

      {followUpsLoading && !followUpsError ? (
        <div className="space-y-2">
          <div className="shimmer h-10 rounded"></div>
          <div className="shimmer h-10 rounded"></div>
        </div>
      ) : (
        <div className="space-y-4">
          {[
            {
              key: 'today',
              label: 'Today',
              items: filterFollowUps(followUps.today),
            },
            {
              key: 'tomorrow',
              label: 'Tomorrow',
              items: filterFollowUps(followUps.tomorrow),
            },
          ].map((group) => (
            <div key={group.key}>
              <div className="mb-2 flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-900">
                  {group.label}
                </p>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                  {group.items.length}
                </span>
              </div>
              {group.items.length === 0 ? (
                <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                  No follow-ups due.
                </div>
              ) : (
                <div className="grid gap-3 xl:grid-cols-2">
                  {group.items.slice(0, 8).map((item) => (
                    <div
                      key={item.id}
                      className="rounded-lg border border-slate-200 bg-white px-3 py-3 shadow-sm"
                    >
                      <p className="text-sm font-semibold text-slate-950">
                        {item.patient_name || 'Unknown patient'}
                      </p>
                      <p className="text-xs text-slate-500">
                        {item.patient_mrn
                          ? `MRN ${item.patient_mrn}`
                          : `Patient ${maskId(item.patient_id_canonical)}`}
                      </p>
                      <p className="mt-2 text-xs leading-5 text-slate-600">
                        {item.reason}
                      </p>
                      <p className="text-xs text-slate-500">
                        Due {new Date(item.due_at).toLocaleString()}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button
                          variant="primary"
                          size="sm"
                          isLoading={startingFollowUpId === item.id}
                          onClick={() => void handleStartLinkedFollowUpVisit(item)}
                        >
                          Start Visit (Link)
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => openRescheduleModal(item)}
                        >
                          Reschedule
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </OperationalPanel>
  );

  const renderMovementWorkflow = (
    title: string,
    description: string,
    targets: string[],
    tone: 'blue' | 'amber' | 'rose'
  ) => {
    const toneClasses = {
      blue: 'border-blue-200 bg-blue-50 text-blue-800',
      amber: 'border-amber-200 bg-amber-50 text-amber-800',
      rose: 'border-rose-200 bg-rose-50 text-rose-800',
    };
    return (
      <div className="space-y-5">
        {renderWorkspaceHeader(title, description, demoBadge)}
        <div className={`rounded-xl border px-4 py-3 text-sm ${toneClasses[tone]}`}>
          This workspace is frontend-ready. Production movement requires routing
          APIs, authorization rules, and immutable audit logging.
        </div>
        <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
          <OperationalPanel title="Movement Review" eyebrow="Routing Control">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Source
                </label>
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  GOPD Queue
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Target
                </label>
                <select className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-800">
                  {targets.map((target) => (
                    <option key={target}>{target}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Reason
                </label>
                <textarea
                  rows={4}
                  placeholder="Document why this patient movement is required."
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800"
                />
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="secondary" disabled>
                Routing API Pending
              </Button>
              <Button variant="secondary" onClick={() => setActiveWorkspace('queue')}>
                Return to GOPD Queue
              </Button>
            </div>
          </OperationalPanel>
          <OperationalPanel title="Audit Posture" eyebrow="Traceability">
            <div className="space-y-3 text-sm text-slate-600">
              <p>Required trace before production:</p>
              <ul className="space-y-2 text-xs leading-5">
                <li>Patient, MRN, and visit ID</li>
                <li>Source and target department</li>
                <li>Previous and new queue state</li>
                <li>Reason, actor, role, and timestamp</li>
              </ul>
            </div>
          </OperationalPanel>
        </div>
      </div>
    );
  };

  const renderWorkspace = () => {
    switch (activeWorkspace) {
      case 'overview':
        return (
          <div className="space-y-6">
            {renderWorkspaceHeader(
              'Intake Overview',
              'Operational view of GOPD arrivals, queue pressure, follow-up arrivals, and patient movement risk.'
            )}
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {topOperationalStats.slice(0, 4).map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_14px_30px_rgba(15,23,42,0.05)]"
                >
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {stat.label}
                  </p>
                  <p className={`mt-2 text-3xl font-semibold ${stat.tone}`}>
                    {stat.value}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{stat.helper}</p>
                </div>
              ))}
            </div>
            <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
              <OperationalPanel title="Queue Pressure" eyebrow="Intake Board">
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    ['Waiting', queueStats.waiting, 'Registered / triaged'],
                    ['Emergency', queueStats.emergency, 'Escalation watch'],
                    ['Completed', queueStats.completed, 'Completed queue'],
                  ].map(([label, value, helper]) => (
                    <div
                      key={label}
                      className="rounded-lg border border-slate-200 bg-slate-50 p-3"
                    >
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {label}
                      </p>
                      <p className="mt-2 text-2xl font-semibold text-slate-950">
                        {value}
                      </p>
                      <p className="text-xs text-slate-500">{helper}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    variant="primary"
                    onClick={() => setIsStartVisitModalOpen(true)}
                  >
                    Start OPD Visit
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setActiveWorkspace('registration')}
                  >
                    Register Patient
                  </Button>
                  <Button variant="secondary" onClick={refreshDashboard}>
                    Refresh Intake
                  </Button>
                </div>
              </OperationalPanel>
              {renderRecentMovement()}
            </div>
            <OperationalPanel
              title="Queue Intelligence Preview"
              eyebrow="Operational Rows"
            >
              {renderQueueIntelligenceRows(4)}
            </OperationalPanel>
          </div>
        );

      case 'lookup':
        return (
          <div className="space-y-6">
            {renderWorkspaceHeader(
              'Patient Lookup',
              'Search existing patient records before registration or visit creation to prevent duplicate identity and lost active visits.'
            )}
            <OperationalPanel title="Lookup Safety" eyebrow="Identity Control">
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                  Search before registering a new patient.
                </div>
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                  Active visit warnings prevent duplicate visits.
                </div>
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                  Registry review uses operational purpose of use.
                </div>
              </div>
            </OperationalPanel>
            <PatientRegistryPanel />
          </div>
        );

      case 'registration':
        return (
          <div className="space-y-6">
            {renderWorkspaceHeader(
              'Patient Registration',
              'Register a new patient only after lookup confirms there is no existing patient identity.',
              'Duplicate-warning posture'
            )}
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Search existing patient identity first. Registration must not
              create duplicate MRNs for returning patients.
            </div>
            <PatientRegistrationForm
              onSuccess={handlePatientRegistered}
              onCancel={() => setActiveWorkspace('overview')}
            />
          </div>
        );

      case 'startVisit':
        return (
          <div className="space-y-6">
            {renderWorkspaceHeader(
              'Start OPD Visit',
              'Create a GOPD outpatient visit, confirm active visit status, and route the patient into the correct queue.'
            )}
            <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
              <OperationalPanel title="Visit Creation" eyebrow="Activation">
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Department
                    </p>
                    <p className="mt-1 text-sm font-semibold text-slate-950">
                      {resolvedDepartmentName}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Active Visit Check
                    </p>
                    <p className="mt-1 text-sm font-semibold text-emerald-700">
                      Preserved
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Routing
                    </p>
                    <p className="mt-1 text-sm font-semibold text-blue-700">
                      Service line aware
                    </p>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-600">
                  The existing start-visit workflow remains service-backed. It
                  searches patients, checks active visits, selects service line,
                  assigns clinician where required, and starts the visit.
                </p>
                <div className="mt-4">
                  <Button
                    variant="primary"
                    onClick={() => setIsStartVisitModalOpen(true)}
                  >
                    Open Start Visit Workflow
                  </Button>
                </div>
              </OperationalPanel>
              <OperationalPanel title="Visit Safety" eyebrow="Continuity">
                <div className="space-y-3 text-sm text-slate-600">
                  <p>Live behavior preserved:</p>
                  <ul className="space-y-2 text-xs leading-5">
                    <li>Patient search</li>
                    <li>Active visit detection</li>
                    <li>Department-aware service lines</li>
                    <li>Clinician assignment where required</li>
                  </ul>
                </div>
              </OperationalPanel>
            </div>
          </div>
        );

      case 'queue':
        return (
          <div className="space-y-6">
            {renderWorkspaceHeader(
              'Queue Intelligence',
              'Operational queue board with patient state, wait signals, emergency flags, and clinician-routing posture.'
            )}
            <OperationalPanel
              title="Operational Queue Console"
              eyebrow="High-Volume Intake"
              action={
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                  Auto-refresh 30s
                </span>
              }
            >
              {renderQueueIntelligenceRows(8)}
            </OperationalPanel>
            <VisitQueue
              autoRefresh={true}
              refreshInterval={30000}
              onVisitClick={handleVisitClick}
              key={refreshQueue}
            />
          </div>
        );

      case 'triage':
        return (
          <div className="space-y-6">
            {renderWorkspaceHeader(
              'Triage Routing',
              'Identify patients who need clinical screening before doctor queue or emergency escalation.',
              demoBadge
            )}
            <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
              <OperationalPanel title="Triage Candidates" eyebrow="Screening">
                <div className="space-y-3">
                  {recentVisits.slice(0, 4).map((visit) => (
                    <button
                      key={visit.id}
                      type="button"
                      onClick={() => handleVisitClick(visit)}
                      className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left hover:border-cyan-200 hover:bg-cyan-50/40"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-semibold text-slate-950">
                          {visit.patient_name || 'Unknown patient'}
                        </p>
                        <VisitStatusBadge status={visit.status} size="sm" />
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {visit.patient_mrn || maskId(visit.patient_id)}
                      </p>
                    </button>
                  ))}
                </div>
              </OperationalPanel>
              <OperationalPanel title="Routing Posture" eyebrow="Handoff">
                <div className="space-y-3">
                  {renderDemoNotice()}
                  <p className="text-sm text-slate-600">
                    Production triage routing will require queue state
                    transitions and nursing handoff audit events.
                  </p>
                </div>
              </OperationalPanel>
            </div>
          </div>
        );

      case 'doctorAssignment':
        return (
          <div className="space-y-6">
            {renderWorkspaceHeader(
              'Doctor Assignment',
              'Route eligible GOPD patients to the correct doctor or clinical queue while preserving visit context.',
              'Live start-visit assignment preserved'
            )}
            <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
              <OperationalPanel title="Assignment Readiness" eyebrow="Clinician Queue">
                <div className="grid gap-3 md:grid-cols-2">
                  {recentVisits.slice(0, 6).map((visit) => (
                    <button
                      key={visit.id}
                      type="button"
                      onClick={() => handleVisitClick(visit)}
                      className="rounded-lg border border-slate-200 bg-white p-3 text-left hover:border-blue-200 hover:bg-blue-50/40"
                    >
                      <p className="font-semibold text-slate-950">
                        {visit.patient_name || 'Unknown patient'}
                      </p>
                      <p className="text-xs text-slate-500">
                        {visit.patient_mrn || maskId(visit.patient_id)}
                      </p>
                      <div className="mt-2">
                        <VisitStatusBadge status={visit.status} size="sm" />
                      </div>
                    </button>
                  ))}
                </div>
              </OperationalPanel>
              <OperationalPanel title="Assignment Boundary" eyebrow="Role Safety">
                <p className="text-sm leading-6 text-slate-600">
                  GOPD Intake routes patients to doctor queues. Doctors own the
                  clinical consultation, diagnosis, notes, orders, and signing.
                </p>
              </OperationalPanel>
            </div>
          </div>
        );

      case 'reassignment':
        return renderMovementWorkflow(
          'Reassignment / Rerouting',
          'Correct wrong queue or wrong department placement before clinical consultation without losing visit traceability.',
          ['Specialist Clinics', 'Maternity', 'Pediatrics', 'Gynecology', 'A&E'],
          'amber'
        );

      case 'referral':
        return renderMovementWorkflow(
          'Internal Referral',
          'Route a patient from GOPD toward a specialist department while preserving the source encounter and referral reason.',
          [
            'Specialist Clinics',
            'Gynecology',
            'Pediatrics',
            'Maternity',
            'Theatre Review',
          ],
          'blue'
        );

      case 'emergency':
        return renderMovementWorkflow(
          'Emergency Escalation',
          'Escalate urgent GOPD presentations to A&E with reason capture, priority marking, and source context preservation.',
          ['Accident & Emergency (A&E)'],
          'rose'
        );

      case 'followUp':
        return (
          <div className="space-y-6">
            {renderWorkspaceHeader(
              'Follow-Up Arrival',
              'Check in returning patients through linked follow-up records and preserve continuity to the original encounter.'
            )}
            {renderFollowUpWorklist()}
          </div>
        );

      case 'audit':
        return (
          <div className="space-y-6">
            {renderWorkspaceHeader(
              'Intake Audit Trail',
              'Trace patient lookup, registration, visit creation, reassignment, referral, escalation, and follow-up check-in movement.',
              demoBadge
            )}
            <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
              <OperationalPanel title="Movement Timeline" eyebrow="Audit Trace">
                <div className="space-y-3">
                  {recentVisits.slice(0, 5).map((visit) => (
                    <button
                      key={visit.id}
                      type="button"
                      onClick={() => handleVisitClick(visit)}
                      className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left hover:bg-slate-50"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-semibold text-slate-950">
                          {visit.patient_name || 'Unknown patient'}
                        </p>
                        <span className="text-xs text-slate-500">
                          {new Date(visit.updated_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        Visit {maskId(visit.id)} updated in GOPD intake scope.
                      </p>
                    </button>
                  ))}
                </div>
              </OperationalPanel>
              <OperationalPanel title="Audit Requirements" eyebrow="Production Controls">
                <div className="space-y-3">
                  {renderDemoNotice()}
                  <ul className="space-y-2 text-xs leading-5 text-slate-600">
                    <li>Patient and MRN</li>
                    <li>Visit ID and queue state</li>
                    <li>Source and target department</li>
                    <li>Reason, actor, role, and timestamp</li>
                  </ul>
                </div>
              </OperationalPanel>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div
      className="min-h-screen bg-[#e9f0f6] text-slate-900"
      style={{
        backgroundImage:
          'radial-gradient(circle at top left, rgba(14, 165, 233, 0.14), transparent 34rem), linear-gradient(180deg, #f8fafc 0%, #e9f0f6 46%, #e2e8f0 100%)',
      }}
    >
      <div className="flex min-h-[calc(100vh-4rem)] flex-col xl:flex-row">
        <aside className="border-r border-slate-300/70 bg-slate-950 text-white shadow-[16px_0_45px_rgba(15,23,42,0.18)] xl:sticky xl:top-0 xl:h-[calc(100vh-4rem)] xl:w-[19rem] xl:shrink-0 xl:overflow-y-auto">
          <div className="border-b border-white/10 p-3">
            <div className="rounded-xl border border-cyan-300/15 bg-white/[0.04] p-3 shadow-inner">
              <div className="grid grid-cols-3 gap-3">
                {[
                  ['Operator', receptionistName],
                  ['Shift', 'Active'],
                  ['Desk', 'GOPD'],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="text-[10px] uppercase tracking-wide text-slate-400">
                      {label}
                    </p>
                    <p className="mt-0.5 truncate text-sm font-semibold text-white">
                      {value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <nav className="space-y-5 p-3" aria-label="GOPD intake navigation">
            {navigationGroups.map((group) => (
              <div key={group.label}>
                <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {group.label}
                </p>
                <div className="space-y-1">
                  {group.items.map((key) => {
                    const item = intakeNavigation.find((nav) => nav.key === key);
                    if (!item) return null;
                    const isActive = item.key === activeWorkspace;
                    return (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => setActiveWorkspace(item.key)}
                        className={`group flex w-full items-center gap-3 rounded-xl border px-2.5 py-2 text-left transition ${
                          isActive
                            ? 'border-cyan-300/40 bg-cyan-400/12 text-white shadow-[0_0_0_1px_rgba(34,211,238,0.12),0_12px_25px_rgba(8,145,178,0.12)]'
                            : 'border-transparent text-slate-300 hover:border-white/10 hover:bg-white/[0.05] hover:text-white'
                        }`}
                      >
                        <span
                          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-[11px] font-bold ${
                            isActive
                              ? 'border-cyan-200/50 bg-cyan-300/20 text-cyan-100'
                              : 'border-white/10 bg-white/[0.04] text-slate-400 group-hover:text-cyan-100'
                          }`}
                        >
                          {item.code}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-semibold">
                            {item.label}
                          </span>
                          <span className="mt-0.5 block truncate text-[11px] text-slate-400">
                            {item.description}
                          </span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>
        </aside>

        <div className="min-w-0 flex-1">
          <div className="border-b border-slate-300/80 bg-white/95 shadow-[0_8px_24px_rgba(15,23,42,0.05)]">
            <div className="px-4 py-4 sm:px-6 lg:px-8">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-700">
                    GOPD Intake Workspace
                  </p>
                  <h2 className="mt-0.5 text-2xl font-semibold tracking-tight text-slate-950">
                    {activeWorkspaceMeta.label}
                  </h2>
                  <p className="mt-1 max-w-2xl text-sm leading-5 text-slate-600">
                    Correct the patient journey without fragmenting the patient
                    record.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {allowedDepartments.length > 1 && (
                    <select
                      value={currentDepartmentId || allowedDepartments[0]?.id || ''}
                      onChange={(event) =>
                        void handleDepartmentSwitch(event.target.value)
                      }
                      disabled={switchingDepartment}
                      className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700"
                    >
                      {allowedDepartments.map((department) => (
                        <option key={department.id} value={department.id}>
                          {department.name}
                        </option>
                      ))}
                    </select>
                  )}
                  <Button
                    variant="primary"
                    onClick={() => setIsStartVisitModalOpen(true)}
                  >
                    Start OPD Visit
                  </Button>
                  <Button variant="secondary" onClick={refreshDashboard}>
                    {statsLoading ? 'Refreshing' : 'Refresh'}
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <div className="px-4 py-6 sm:px-6 lg:px-8">
            {statsError && (
              <div className="mb-4 text-sm text-red-600">{statsError}</div>
            )}
            {departmentError && (
              <div className="mb-4 text-sm text-red-600">{departmentError}</div>
            )}

            {recentMrnIssued && (
              <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-semibold text-emerald-900">
                      {recentPatientName ?? 'Patient'} registered successfully.
                    </p>
                    <p className="text-emerald-800">
                      MRN:{' '}
                      <span className="font-semibold">{recentMrnIssued}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setIsStartVisitModalOpen(true)}
                    >
                      Start Visit
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setRecentMrnIssued(null);
                        setRecentPatientName(null);
                      }}
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {followUpActionError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {followUpActionError}
              </div>
            )}
            {followUpActionSuccess && (
              <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {followUpActionSuccess}
              </div>
            )}

            <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_340px]">
              <section className="min-w-0">{renderWorkspace()}</section>

              <aside className="min-w-0">
                <div className="sticky top-40 space-y-4">
                  <section className="overflow-hidden rounded-xl border border-slate-300/80 bg-slate-950 text-white shadow-[0_18px_45px_rgba(15,23,42,0.18)]">
                    <div className="border-b border-white/10 bg-white/[0.04] px-4 py-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-200">
                        Patient Intelligence Rail
                      </p>
                      <h3 className="mt-0.5 text-sm font-semibold text-white">
                        Continuity Context
                      </h3>
                    </div>
                    <div className="p-4">
                    {selectedVisit ? (
                      <div className="space-y-4">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                            Selected Patient
                          </p>
                          <p className="mt-1 text-lg font-semibold text-white">
                            {selectedVisit.patient_name || 'Unknown patient'}
                          </p>
                          <p className="text-sm text-slate-300">
                            {selectedVisit.patient_mrn
                              ? `MRN ${selectedVisit.patient_mrn}`
                              : `ID ${maskId(selectedVisit.patient_id)}`}
                          </p>
                        </div>
                        <div className="grid gap-2 text-sm">
                          <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2">
                            <span className="text-slate-400">Active visit</span>
                            <span className="font-medium text-white">
                              {maskId(selectedVisit.id)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2">
                            <span className="text-slate-400">Queue state</span>
                            <VisitStatusBadge
                              status={selectedVisit.status}
                              size="sm"
                            />
                          </div>
                          <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2">
                            <span className="text-slate-400">Emergency</span>
                            <span
                              className={`font-medium ${
                                selectedVisit.intake_emergency_flag
                                  ? 'text-rose-200'
                                  : 'text-emerald-200'
                              }`}
                            >
                              {selectedVisit.intake_emergency_flag
                                ? 'Flagged'
                                : 'Not flagged'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2">
                            <span className="text-slate-400">Admission</span>
                            <span className="font-medium text-white">
                              {selectedVisit.has_active_admission
                                ? 'Active admission'
                                : 'No active admission'}
                            </span>
                          </div>
                        </div>
                        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                          Active visit warning preserved. Continue existing
                          patient journey instead of creating duplicate visits.
                        </div>
                        <div className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-3 py-2">
                          <p className="text-[10px] font-semibold uppercase tracking-wide text-cyan-200">
                            Movement Trace
                          </p>
                          <p className="mt-1 text-xs leading-5 text-slate-300">
                            GOPD intake - selected visit - details available.
                          </p>
                        </div>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setSelectedVisitId(selectedVisit.id);
                            setIsDetailsModalOpen(true);
                          }}
                        >
                          View Visit Details
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-3 text-sm text-slate-600">
                        <p className="text-slate-300">
                          Select a patient from queue, recent movement, or
                          follow-up worklist to anchor the intake context.
                        </p>
                        <div className="rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2 text-xs text-slate-300">
                          Patient identity, active visit, alerts, previous
                          visits, and follow-up linkage belong here.
                        </div>
                      </div>
                    )}
                    </div>
                  </section>

                  <OperationalPanel title="Continuity Guard" eyebrow="HIS Integrity">
                    <div className="space-y-3 text-sm text-slate-600">
                      <p className="font-medium text-slate-900">
                        No fragmented patient records.
                      </p>
                      <p>
                        GOPD can route, reassign, refer, or escalate the visit,
                        but the MRN, visit history, EMR, billing, and audit
                        trail remain shared across KSH Enterprise HIS.
                      </p>
                    </div>
                  </OperationalPanel>
                </div>
              </aside>
            </div>
          </div>
        </div>
      </div>

      <StartVisitModal
        isOpen={isStartVisitModalOpen}
        onClose={() => setIsStartVisitModalOpen(false)}
        onSuccess={handleVisitCreated}
        currentDepartmentId={currentDepartmentId}
        onContinueVisit={(visitId) => {
          setSelectedVisitId(visitId);
          setIsDetailsModalOpen(true);
        }}
      />

      <VisitDetailsModal
        visitId={selectedVisitId || null}
        isOpen={isDetailsModalOpen}
        onClose={() => {
          setIsDetailsModalOpen(false);
          setSelectedVisitId(null);
        }}
        purposeOfUse={PurposeOfUse.OPERATIONS}
      />

      {rescheduleModalOpen && rescheduleTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">
              Reschedule Follow-Up
            </h3>
            <p className="mt-1 text-sm text-slate-600">
              {rescheduleTarget.patient_name || 'Patient'} -{' '}
              {rescheduleTarget.patient_mrn
                ? `MRN ${rescheduleTarget.patient_mrn}`
                : `ID ${maskId(rescheduleTarget.patient_id_canonical)}`}
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                  New Due Date
                </label>
                <input
                  type="datetime-local"
                  value={rescheduleDueAt}
                  onChange={(event) => setRescheduleDueAt(event.target.value)}
                  className="h-10 w-full rounded-md border border-slate-300 px-3 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Reason
                </label>
                <textarea
                  value={rescheduleReason}
                  onChange={(event) => setRescheduleReason(event.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  rows={3}
                />
              </div>
              {rescheduleError && (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {rescheduleError}
                </div>
              )}
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <Button variant="secondary" onClick={closeRescheduleModal}>
                Cancel
              </Button>
              <Button
                variant="primary"
                isLoading={rescheduleSubmitting}
                disabled={!rescheduleDueAt || rescheduleReason.trim().length < 2}
                onClick={() => void handleRescheduleSubmit()}
              >
                Save Reschedule
              </Button>
            </div>
          </div>
        </div>
      )}

      <footer className="border-t border-slate-200 bg-white py-4">
        <div className="px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-slate-500">
            {HOSPITAL_NAME} - GOPD Intake Workspace -{' '}
            {new Date().toLocaleDateString()}
          </p>
        </div>
      </footer>
    </div>
  );
}
