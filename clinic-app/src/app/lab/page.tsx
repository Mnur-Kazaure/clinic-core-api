'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { DashboardHero } from '@/app/components/DashboardHero';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { LabRequestDetailsModal } from '@/app/lab/components/LabRequestDetailsModal';
import { LAB_WORKSPACE_THEME } from '@/domains/lab/constants/labWorkspaceTheme';
import { useLabWorkspaceBenchSnapshot } from '@/domains/lab/hooks/useLabWorkspaceBenchSnapshot';
import {
  LabRequest,
  LabWorkspaceAttentionItem,
  LabWorkspaceQcRunSummary,
  LabWorkspaceSpecimenSummary,
  LabWorkspaceTabBadge,
  LabWorkspaceTabKey,
  labService,
} from '@/domains/lab/services/labService';
import { HOSPITAL_NAME } from '@/shared/constants/branding';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';

type LabTab = 'queue' | 'specimens' | 'results' | 'completed' | 'qc';

const BENCH_THEME = LAB_WORKSPACE_THEME;

const tabs: Array<{ id: LabTab; label: string; badgeKey?: LabWorkspaceTabKey }> = [
  { id: 'queue', label: 'Queue', badgeKey: 'QUEUE' },
  { id: 'specimens', label: 'Specimens', badgeKey: 'SPECIMENS' },
  { id: 'results', label: 'Results', badgeKey: 'RESULTS' },
  { id: 'completed', label: 'Completed', badgeKey: 'COMPLETED' },
  { id: 'qc', label: 'QC', badgeKey: 'QC' },
];

const tabIdByWorkspaceKey: Record<LabWorkspaceTabKey, LabTab> = {
  QUEUE: 'queue',
  SPECIMENS: 'specimens',
  RESULTS: 'results',
  COMPLETED: 'completed',
  QC: 'qc',
};

const queueWorkflowStatuses = new Set(['ORDERED', 'PAID', 'AWAITING_SPECIMEN']);
const resultWorkbenchWorkflowStatuses = new Set([
  'IN_ANALYSIS',
  'RESULT_ENTERED',
  'VERIFIED',
  'RELEASED',
]);
const resultWorkbenchResultStatuses = new Set([
  'DRAFT',
  'SUBMITTED',
  'VERIFIED',
  'RELEASED',
  'AMENDED',
]);

function statusBadge(status: string) {
  const styles: Record<string, string> = {
    PENDING: 'bg-amber-50 text-amber-800 border-amber-200',
    COMPLETED: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    CANCELLED: 'bg-rose-50 text-rose-800 border-rose-200',
    RECEIVED: 'bg-sky-50 text-sky-800 border-sky-200',
    IN_PROCESS: 'bg-indigo-50 text-indigo-800 border-indigo-200',
    REJECTED: 'bg-rose-50 text-rose-800 border-rose-200',
    LOST: 'bg-rose-50 text-rose-800 border-rose-200',
    PASS: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    FAIL: 'bg-rose-50 text-rose-800 border-rose-200',
    WARNING: 'bg-amber-50 text-amber-800 border-amber-200',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${styles[status] ?? 'bg-slate-50 text-slate-700 border-slate-200'}`}
    >
      {status.replaceAll('_', ' ')}
    </span>
  );
}

function toneClasses(tone: string) {
  switch (tone) {
    case 'critical':
      return {
        card: 'border-rose-200 bg-rose-50 text-rose-900',
        badge: 'border-rose-200 bg-rose-100 text-rose-700',
      };
    case 'warning':
      return {
        card: 'border-amber-200 bg-amber-50 text-amber-900',
        badge: 'border-amber-200 bg-amber-100 text-amber-700',
      };
    case 'success':
      return {
        card: 'border-emerald-200 bg-emerald-50 text-emerald-900',
        badge: 'border-emerald-200 bg-emerald-100 text-emerald-700',
      };
    default:
      return {
        card: 'border-sky-200 bg-sky-50 text-sky-900',
        badge: 'border-sky-200 bg-sky-100 text-sky-700',
      };
  }
}

function pluralize(count: number, singular: string, plural?: string) {
  return `${count} ${count === 1 ? singular : plural ?? `${singular}s`}`;
}

function attentionPriority(key: LabWorkspaceAttentionItem['key']) {
  switch (key) {
    case 'CRITICAL_ALERTS':
    case 'PENDING_VERIFICATIONS':
    case 'QC_FAILURES':
      return 'high';
    case 'AWAITING_SPECIMEN':
    case 'PENDING_QUEUE':
      return 'medium';
    default:
      return 'low';
  }
}

function attentionDisplayLabel(item: LabWorkspaceAttentionItem) {
  if (item.key === 'QC_FAILURES') {
    return 'QC Issues';
  }
  return item.label;
}

function attentionCaption(item: LabWorkspaceAttentionItem) {
  switch (item.key) {
    case 'CRITICAL_ALERTS':
      return 'Immediate attention';
    case 'PENDING_VERIFICATIONS':
      return 'Awaiting release review';
    case 'AWAITING_SPECIMEN':
      return 'Specimens to receive';
    case 'QC_FAILURES':
      return 'QC review needed';
    case 'COMPLETED_TODAY':
      return 'Finished today';
    default:
      return 'Paid work ready';
  }
}

function commandStripStyles(item: LabWorkspaceAttentionItem) {
  const priority = attentionPriority(item.key);

  if (priority === 'high') {
    if (item.tone === 'critical') {
      return {
        card: 'border-rose-200 bg-white text-slate-900 shadow-sm ring-1 ring-rose-100',
        badge: 'border-rose-200 bg-rose-100 text-rose-700',
        eyebrow: 'text-rose-700',
        accent: 'bg-rose-500',
        count: 'text-slate-950',
        helper: 'text-slate-600',
      };
    }

    return {
      card: 'border-amber-200 bg-white text-slate-900 shadow-sm ring-1 ring-amber-100',
      badge: 'border-amber-200 bg-amber-100 text-amber-700',
      eyebrow: 'text-amber-700',
      accent: 'bg-amber-500',
      count: 'text-slate-950',
      helper: 'text-slate-600',
    };
  }

  if (priority === 'medium') {
    return item.tone === 'warning'
      ? {
          card: 'border-amber-200 bg-amber-50/80 text-amber-950',
          badge: 'border-amber-200 bg-white text-amber-700',
          eyebrow: 'text-amber-700',
          accent: 'bg-amber-400',
          count: 'text-amber-950',
          helper: 'text-amber-800/80',
        }
      : {
          card: 'border-sky-200 bg-sky-50/85 text-sky-950',
          badge: 'border-sky-200 bg-white text-sky-700',
          eyebrow: 'text-sky-700',
          accent: 'bg-sky-400',
          count: 'text-sky-950',
          helper: 'text-sky-900/75',
        };
  }

  return {
    card: 'border-slate-200 bg-slate-50 text-slate-800',
    badge: 'border-slate-200 bg-white text-slate-600',
    eyebrow: 'text-slate-500',
    accent: 'bg-slate-300',
    count: 'text-slate-900',
    helper: 'text-slate-600',
  };
}

function formatLabRole(role: string) {
  const labels: Record<string, string> = {
    LAB: 'Lab Staff',
    LAB_TECH: 'Lab Technician',
    LAB_SCIENTIST: 'Lab Scientist',
    LAB_SUPERVISOR: 'Lab Supervisor',
    LAB_MANAGER: 'Medical Laboratory HOD',
  };
  return labels[role] ?? role.replaceAll('_', ' ');
}

function formatRefreshTime(timestamp: string | null) {
  if (!timestamp) {
    return 'Waiting for first sync';
  }
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function nextActionSummary(snapshot: {
  critical_alerts?: number;
  pending_verifications?: number;
  awaiting_specimen?: number;
  qc_failures?: number;
  queue_count?: number;
}) {
  if ((snapshot.critical_alerts || 0) > 0) {
    return {
      tone: 'critical',
      text: `${pluralize(snapshot.critical_alerts || 0, 'critical alert')} require${(snapshot.critical_alerts || 0) === 1 ? 's' : ''} immediate review`,
    };
  }
  if ((snapshot.pending_verifications || 0) > 0) {
    return {
      tone: 'warning',
      text: `${pluralize(snapshot.pending_verifications || 0, 'result')} ${snapshot.pending_verifications === 1 ? 'awaits' : 'await'} verification`,
    };
  }
  if ((snapshot.awaiting_specimen || 0) > 0) {
    return {
      tone: 'warning',
      text: `${pluralize(snapshot.awaiting_specimen || 0, 'specimen')} ${snapshot.awaiting_specimen === 1 ? 'is' : 'are'} awaiting receipt`,
    };
  }
  if ((snapshot.qc_failures || 0) > 0) {
    return {
      tone: 'critical',
      text: `${pluralize(snapshot.qc_failures || 0, 'QC issue')} require${(snapshot.qc_failures || 0) === 1 ? 's' : ''} review`,
    };
  }
  if ((snapshot.queue_count || 0) > 0) {
    return {
      tone: 'info',
      text: `${pluralize(snapshot.queue_count || 0, 'paid request')} ${snapshot.queue_count === 1 ? 'is' : 'are'} ready in the queue`,
    };
  }
  return {
    tone: 'success',
    text: 'No immediate bench action is pending.',
  };
}

function extractErrorMessage(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    if (typeof response?.data?.detail === 'string' && response.data.detail.trim()) {
      return response.data.detail;
    }
  }
  return fallback;
}

export default function LabPage() {
  const dashboardUser = useDashboardUser();
  const [activeTab, setActiveTab] = useState<LabTab>('queue');
  const [selectedUnitId, setSelectedUnitId] = useState<string | null>(null);
  const [selectedRequest, setSelectedRequest] = useState<LabRequest | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [requests, setRequests] = useState<LabRequest[]>([]);
  const [specimens, setSpecimens] = useState<LabWorkspaceSpecimenSummary[]>([]);
  const [qcRuns, setQcRuns] = useState<LabWorkspaceQcRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastWorkspaceRefreshAt, setLastWorkspaceRefreshAt] = useState<string | null>(null);
  const [lastBenchEventAt, setLastBenchEventAt] = useState<string | null>(null);

  const allowedUnits = useMemo(
    () => dashboardUser?.allowed_lab_units ?? [],
    [dashboardUser?.allowed_lab_units]
  );

  useEffect(() => {
    if (!allowedUnits.length) {
      setSelectedUnitId(null);
      return;
    }
    const preferred =
      allowedUnits.find((unit) => unit.id === dashboardUser?.default_lab_unit_id)?.id ||
      allowedUnits[0].id;
    setSelectedUnitId((current) =>
      current && allowedUnits.some((unit) => unit.id === current) ? current : preferred
    );
  }, [allowedUnits, dashboardUser?.default_lab_unit_id]);

  const selectedUnit = useMemo(
    () => allowedUnits.find((unit) => unit.id === selectedUnitId) || null,
    [allowedUnits, selectedUnitId]
  );

  const {
    snapshot,
    error: benchError,
    refresh: refreshBenchSnapshot,
  } = useLabWorkspaceBenchSnapshot({
    enabled: Boolean(dashboardUser && selectedUnitId),
    unitId: selectedUnitId,
  });

  const loadWorkspace = useCallback(
    async (mode: 'initial' | 'refresh' = 'initial') => {
      if (!selectedUnitId) {
        setLoading(false);
        return;
      }

      try {
        if (mode === 'initial') {
          setLoading(true);
        } else {
          setRefreshing(true);
        }
        setError(null);
        const [requestData, specimenData, qcData] = await Promise.all([
          labService.getRequests(undefined, { unit_id: selectedUnitId }),
          labService.getWorkspaceSpecimens(selectedUnitId),
          labService.getWorkspaceQcRuns(selectedUnitId),
        ]);
        setRequests(requestData);
        setSpecimens(specimenData);
        setQcRuns(qcData);
        setLastWorkspaceRefreshAt(new Date().toISOString());
      } catch (error: unknown) {
        console.error('Failed to load lab workspace:', error);
        setError(extractErrorMessage(error, 'Unable to load laboratory workspace.'));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [selectedUnitId]
  );

  useEffect(() => {
    setLastBenchEventAt(null);
  }, [selectedUnitId]);

  useEffect(() => {
    void loadWorkspace('initial');
    const interval = setInterval(() => {
      void loadWorkspace('refresh');
    }, 30000);
    return () => clearInterval(interval);
  }, [loadWorkspace]);

  useEffect(() => {
    if (!snapshot?.generated_at) {
      return;
    }
    if (lastBenchEventAt === null) {
      setLastBenchEventAt(snapshot.generated_at);
      return;
    }
    if (snapshot.generated_at !== lastBenchEventAt) {
      setLastBenchEventAt(snapshot.generated_at);
      void loadWorkspace('refresh');
    }
  }, [snapshot?.generated_at, lastBenchEventAt, loadWorkspace]);

  const pendingRequests = useMemo(
    () => requests.filter((request) => request.status === 'PENDING'),
    [requests]
  );
  const queueRequests = useMemo(
    () =>
      pendingRequests.filter((request) =>
        queueWorkflowStatuses.has(request.workflow_status || 'ORDERED')
      ),
    [pendingRequests]
  );
  const resultRequests = useMemo(
    () =>
      pendingRequests.filter(
        (request) =>
          (request.ready_specimen_count || 0) > 0 ||
          resultWorkbenchResultStatuses.has(request.latest_result_status || '') ||
          resultWorkbenchWorkflowStatuses.has(request.workflow_status || '')
      ),
    [pendingRequests]
  );
  const completedRequests = useMemo(
    () => requests.filter((request) => request.status === 'COMPLETED'),
    [requests]
  );

  const tabBadgeMap = useMemo(() => {
    const badgeMap = new Map<LabWorkspaceTabKey, LabWorkspaceTabBadge>();
    for (const badge of snapshot?.tab_badges || []) {
      badgeMap.set(badge.tab_key, badge);
    }
    return badgeMap;
  }, [snapshot?.tab_badges]);

  const orderedAttentionItems = useMemo(
    () =>
      [...(snapshot?.attention_items || [])].sort((left, right) => {
        const priorityOrder = { high: 0, medium: 1, low: 2 };
        const leftPriority = priorityOrder[attentionPriority(left.key)];
        const rightPriority = priorityOrder[attentionPriority(right.key)];
        if (leftPriority !== rightPriority) {
          return leftPriority - rightPriority;
        }
        return right.count - left.count;
      }),
    [snapshot?.attention_items]
  );

  const workloadMetrics = useMemo(
    () => [
      {
        label: 'Active Queue',
        value: snapshot?.queue_count ?? queueRequests.length,
        helper: 'Paid or waiting for specimen',
      },
      {
        label: 'Result Workbench',
        value: snapshot?.result_workbench_count ?? resultRequests.length,
        helper: 'Requests ready for entry or review',
      },
      {
        label: 'Completed Today',
        value: snapshot?.completed_today ?? completedRequests.length,
        helper: 'Released work finished today',
      },
    ],
    [completedRequests.length, queueRequests.length, resultRequests.length, snapshot]
  );

  const attentionMetrics = useMemo(
    () => [
      {
        label: 'Critical Alerts',
        value: snapshot?.critical_alerts ?? 0,
        helper: 'Immediate escalation risk',
      },
      {
        label: 'Pending Verification',
        value: snapshot?.pending_verifications ?? 0,
        helper: 'Supervisor review queue',
      },
      {
        label: 'Specimen Issues',
        value: snapshot?.specimen_issue_count ?? 0,
        helper: 'Rejected or lost specimens',
      },
      {
        label: 'QC Issues',
        value: snapshot?.qc_attention_count ?? 0,
        helper: 'Warnings and failures in this bench',
      },
    ],
    [snapshot]
  );

  const nextAction = useMemo(
    () =>
      nextActionSummary({
        critical_alerts: snapshot?.critical_alerts,
        pending_verifications: snapshot?.pending_verifications,
        awaiting_specimen: snapshot?.awaiting_specimen,
        qc_failures: snapshot?.qc_failures,
        queue_count: snapshot?.queue_count,
      }),
    [snapshot]
  );

  const surfaceError = error ?? benchError;

  const openRequest = (request: LabRequest) => {
    setSelectedRequest(request);
    setIsDetailsModalOpen(true);
  };

  const handleAttentionClick = (item: LabWorkspaceAttentionItem) => {
    setActiveTab(tabIdByWorkspaceKey[item.target_tab]);
  };

  const handleManualRefresh = async () => {
    await Promise.all([loadWorkspace('refresh'), refreshBenchSnapshot()]);
  };

  const renderRequestTable = (
    data: LabRequest[],
    emptyMessage: string,
    title: string,
    mode: 'default' | 'completed' = 'default'
  ) => (
    <Card title={title} titleClassName="text-slate-900">
      {data.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          {emptyMessage}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Patient</th>
                <th className="px-4 py-3 text-left font-medium">Test</th>
                <th className="px-4 py-3 text-left font-medium">Workflow</th>
                <th className="px-4 py-3 text-left font-medium">Specimen</th>
                {mode === 'completed' ? (
                  <>
                    <th className="px-4 py-3 text-left font-medium">Result</th>
                    <th className="px-4 py-3 text-left font-medium">Completed Time</th>
                  </>
                ) : (
                  <th className="px-4 py-3 text-left font-medium">Alerts</th>
                )}
                <th className="px-4 py-3 text-right font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {data.map((request) => (
                <tr key={request.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">
                      {request.patient_name || 'Unknown patient'}
                    </div>
                    <div className="text-xs text-slate-500">
                      {request.patient_mrn || request.visit_id.slice(0, 10)}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{request.test_name}</div>
                    <div className="text-xs text-slate-500">
                      {request.target_unit_name || selectedUnit?.name || 'Unassigned unit'}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-2">
                      {statusBadge(request.status)}
                      {request.workflow_status && statusBadge(request.workflow_status)}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {request.ready_specimen_count || 0} ready
                  </td>
                  {mode === 'completed' ? (
                    <>
                      <td className="px-4 py-3">
                        {request.latest_result_status
                          ? statusBadge(request.latest_result_status)
                          : '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-700">
                        {request.completed_at
                          ? new Date(request.completed_at).toLocaleString()
                          : '—'}
                      </td>
                    </>
                  ) : (
                    <td className="px-4 py-3 text-slate-700">
                      {request.critical_alert_count || 0}
                    </td>
                  )}
                  <td className="px-4 py-3 text-right">
                    <Button size="sm" variant="primary" onClick={() => openRequest(request)}>
                      Open
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );

  const renderSpecimenTable = () => (
    <Card title="Specimens" titleClassName="text-slate-900">
      {specimens.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          No specimens are currently routed to this unit.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Accession</th>
                <th className="px-4 py-3 text-left font-medium">Patient</th>
                <th className="px-4 py-3 text-left font-medium">Test</th>
                <th className="px-4 py-3 text-left font-medium">Specimen</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {specimens.map((specimen) => (
                <tr key={specimen.id}>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {specimen.accession_number}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">
                      {specimen.patient_name || 'Unknown patient'}
                    </div>
                    <div className="text-xs text-slate-500">
                      {specimen.patient_mrn || specimen.visit_id.slice(0, 10)}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{specimen.test_name}</td>
                  <td className="px-4 py-3 text-slate-700">
                    {specimen.specimen_type} • {specimen.specimen_source}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-2">
                      {statusBadge(specimen.status)}
                      {specimen.rejection_reason_text && (
                        <span className="text-xs text-rose-700">
                          {specimen.rejection_reason_text}
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );

  const renderQcTable = () => (
    <Card title="Quality Control" titleClassName="text-slate-900">
      {qcRuns.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          No QC runs have been recorded for this unit yet.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-3 text-left font-medium">QC Level</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Performed</th>
                <th className="px-4 py-3 text-left font-medium">Warnings</th>
                <th className="px-4 py-3 text-left font-medium">Failures</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {qcRuns.map((run) => (
                <tr key={run.id}>
                  <td className="px-4 py-3 font-medium text-slate-900">{run.qc_level}</td>
                  <td className="px-4 py-3">{statusBadge(run.status)}</td>
                  <td className="px-4 py-3 text-slate-700">
                    {new Date(run.performed_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-slate-700">{run.warning_count}</td>
                  <td className="px-4 py-3 text-slate-700">{run.fail_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'queue':
        return renderRequestTable(
          queueRequests,
          'No paid work is currently waiting in this unit queue.',
          'Paid Queue'
        );
      case 'specimens':
        return renderSpecimenTable();
      case 'results':
        return renderRequestTable(
          resultRequests,
          'No active requests are available for result work in this unit.',
          'Result Workbench'
        );
      case 'completed':
        return renderRequestTable(
          completedRequests,
          'No completed laboratory work has been recorded for this unit yet.',
          'Completed Work',
          'completed'
        );
      case 'qc':
        return renderQcTable();
      default:
        return null;
    }
  };

  if (!dashboardUser) {
    return null;
  }

  if (!allowedUnits.length) {
    return (
      <div className="space-y-6">
        <DashboardHero
          title="Laboratory Workspace"
          subtitle={HOSPITAL_NAME}
          workspaceLabel="Operational laboratory bench workspace"
          monogram="L"
          rightSlot={
            <div>
              <span className="font-semibold">Lab Staff:</span>{' '}
              {getDashboardUserDisplayName(dashboardUser)}
            </div>
          }
        />
        <Card title="Configuration Required" titleClassName="text-slate-900">
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-900">
            No allowed laboratory units are configured for this account. Assign at least
            one `LAB_UNIT` to this user in Admin Staff Management before using the
            operational lab workspace.
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <DashboardHero
        title="Laboratory Workspace"
        subtitle={HOSPITAL_NAME}
        workspaceLabel={`${selectedUnit?.name || 'Laboratory'} • Active Bench`}
        monogram="L"
        variant="calm-light"
        accentLabel="Operational Bench"
        rightSlot={
          <div className="space-y-1 text-right">
            <div>
              <span className="font-semibold">Lab Staff:</span>{' '}
              {getDashboardUserDisplayName(dashboardUser)}
            </div>
            <div>
              <span className="font-semibold">Role:</span> {formatLabRole(dashboardUser.role)}
            </div>
            <div>
              <span className="font-semibold">Last sync:</span>{' '}
              <span data-testid="lab-bench-last-refresh">
                {formatRefreshTime(lastWorkspaceRefreshAt)}
              </span>
            </div>
          </div>
        }
      />

      <div
        data-testid="lab-bench-attention-strip"
        className="grid gap-3 md:grid-cols-2 xl:grid-cols-6"
      >
        {orderedAttentionItems.map((item) => {
          const tone = commandStripStyles(item);
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => handleAttentionClick(item)}
              className={`rounded-2xl border px-4 py-3 text-left transition hover:-translate-y-0.5 hover:shadow-sm ${tone.card}`}
              data-testid={`lab-attention-${item.key.toLowerCase()}`}
            >
              <div className={`mb-3 h-1.5 w-12 rounded-full ${tone.accent}`} />
              <p
                className={`text-[11px] font-semibold uppercase tracking-[0.16em] ${tone.eyebrow}`}
              >
                {attentionDisplayLabel(item)}
              </p>
              <p className={`mt-2 text-3xl font-semibold ${tone.count}`}>{item.count}</p>
              <p className={`mt-1 text-xs ${tone.helper}`}>{attentionCaption(item)}</p>
            </button>
          );
        })}
      </div>

      <div
        className={`flex flex-wrap items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-sm ${
          nextAction.tone === 'critical'
            ? 'border-rose-200 bg-rose-50 text-rose-900'
            : nextAction.tone === 'warning'
              ? 'border-amber-200 bg-amber-50 text-amber-900'
              : nextAction.tone === 'success'
                ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                : 'border-sky-200 bg-sky-50 text-sky-900'
        }`}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">•</span>
          <span className="font-semibold">Next Action</span>
        </div>
        <span>{nextAction.text}</span>
      </div>

      <Card className="border border-[#D7E6F8] bg-[#FEFEFE] shadow-sm">
        <div data-testid="lab-bench-header" className="grid gap-4 xl:grid-cols-[minmax(280px,0.95fr)_minmax(280px,0.95fr)_minmax(360px,1.15fr)]">
          <div
            className="space-y-4 rounded-[1.4rem] border px-5 py-4"
            style={{
              borderColor: 'rgba(30, 75, 140, 0.12)',
              background:
                'linear-gradient(180deg, rgba(245,250,254,0.96) 0%, rgba(255,255,255,1) 100%)',
            }}
          >
            <div className="flex flex-wrap items-center gap-2">
              {selectedUnit && (
                <span
                  data-testid="lab-bench-unit-chip"
                  className="inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold"
                  style={{
                    borderColor: 'rgba(30, 75, 140, 0.16)',
                    background: 'rgba(63, 163, 207, 0.10)',
                    color: BENCH_THEME.primary,
                  }}
                >
                  {selectedUnit.name}
                </span>
              )}
              <span
                className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700"
                data-testid="lab-bench-status-chip"
              >
                Active Bench
              </span>
            </div>
            <div>
              <h2 className="text-[1.75rem] font-semibold" style={{ color: BENCH_THEME.textPrimary }}>
                {selectedUnit?.name || 'Laboratory'} Bench
              </h2>
              <p className="mt-1 text-sm" style={{ color: BENCH_THEME.textSecondary }}>
                Unit-filtered queue, specimen, result, and QC workflow for the selected bench.
              </p>
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">Active Unit</label>
              <select
                value={selectedUnitId || ''}
                onChange={(event) => setSelectedUnitId(event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-[#1E4B8C] focus:ring-4 focus:ring-[#1E4B8C]/10"
              >
                {allowedUnits.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500">
                Only records for {selectedUnit?.name || 'the selected unit'} are loaded in this bench.
              </p>
              <span
                data-testid="lab-selected-unit-persistent-chip"
                className="inline-flex items-center rounded-full border border-[#D7E6F8] bg-white px-3 py-1 text-xs font-semibold text-[#1E4B8C]"
              >
                {selectedUnit?.name || 'No unit selected'}
              </span>
            </div>
          </div>

          <div className="rounded-[1.4rem] border border-[#D7E6F8] bg-white px-5 py-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1E4B8C]">
                  Assigned Units
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  {pluralize(allowedUnits.length, 'unit')} assigned
                </p>
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => void handleManualRefresh()}
                isLoading={refreshing}
              >
                Refresh
              </Button>
            </div>
            <div className="mt-4 space-y-2.5" data-testid="lab-assigned-units-card">
              {allowedUnits.map((unit) => {
                const isActive = unit.id === selectedUnitId;
                return (
                  <div
                    key={unit.id}
                    className={`flex items-center justify-between rounded-xl border px-3 py-2.5 ${
                      isActive
                        ? 'border-[#BFD8F2] bg-[#F5FAFE]'
                        : 'border-slate-200 bg-slate-50/70'
                    }`}
                  >
                    <span className={`text-sm font-medium ${isActive ? 'text-[#1E4B8C]' : 'text-slate-700'}`}>
                      {unit.name}
                    </span>
                    {isActive ? (
                      <span className="inline-flex items-center rounded-full border border-[#BFD8F2] bg-white px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#1E4B8C]">
                        Active
                      </span>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="grid gap-3">
            <div className="rounded-[1.4rem] border border-slate-200 bg-white px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Workload
              </p>
              <div className="mt-3 space-y-3">
                {workloadMetrics.map((metric) => (
                  <div key={metric.label} className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-slate-900">{metric.label}</p>
                      <p className="text-xs text-slate-500">{metric.helper}</p>
                    </div>
                    <span className="text-2xl font-semibold text-slate-900">{metric.value}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-[1.4rem] border border-[#F2D0D0] bg-[#FFF9F9] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-rose-700">
                Attention
              </p>
              <div className="mt-3 space-y-3">
                {attentionMetrics.map((metric) => (
                  <div key={metric.label} className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-slate-900">{metric.label}</p>
                      <p className="text-xs text-slate-500">{metric.helper}</p>
                    </div>
                    <span className="text-2xl font-semibold text-slate-900">{metric.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {snapshot && snapshot.unrouted_requests > 0 && (
        <div
          className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50/70 px-4 py-2.5 text-sm text-amber-900"
          data-testid="lab-bench-unrouted-alert"
        >
          <p>
            {snapshot.unrouted_requests} paid lab request
            {snapshot.unrouted_requests === 1 ? '' : 's'} are not yet mapped to a lab unit.
          </p>
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-amber-700">
            Informational
          </span>
        </div>
      )}

      {surfaceError && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-800">
          {surfaceError}
        </div>
      )}

      <div
        className="flex flex-wrap gap-2 border-b border-slate-200 pb-3"
        data-testid="lab-bench-tabs"
      >
        {tabs.map((tab) => {
          const badge = tab.badgeKey ? tabBadgeMap.get(tab.badgeKey) : undefined;
          const tone = toneClasses(badge?.tone || 'info');
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              data-testid={`lab-tab-${tab.id}`}
              className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${
                isActive
                  ? 'border-transparent text-white shadow-sm'
                  : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-100'
              }`}
              style={
                isActive
                  ? {
                      background: `linear-gradient(135deg, ${BENCH_THEME.primary} 0%, ${BENCH_THEME.accent} 100%)`,
                    }
                  : undefined
              }
            >
              <span>{tab.label}</span>
              {badge && badge.count > 0 ? (
                <span
                  className={`inline-flex min-w-[1.5rem] items-center justify-center rounded-full border px-2 py-0.5 text-xs font-semibold ${tone.badge}`}
                  data-testid={`lab-tab-badge-${tab.id}`}
                >
                  {badge.count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {loading ? (
        <Card title="Loading Workspace" titleClassName="text-slate-900">
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
            Loading selected laboratory unit workspace…
          </div>
        </Card>
      ) : (
        renderActiveTab()
      )}

      {selectedUnitId && (
        <LabRequestDetailsModal
          request={selectedRequest}
          technicianId={dashboardUser.id}
          selectedUnitId={selectedUnitId}
          isOpen={isDetailsModalOpen}
          onClose={() => {
            setIsDetailsModalOpen(false);
            setSelectedRequest(null);
          }}
          onSuccess={() => {
            void Promise.all([loadWorkspace('refresh'), refreshBenchSnapshot()]);
          }}
        />
      )}
    </div>
  );
}
