// /projects/clinic-monorepo/clinic-app/src/app/reception/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';
import { StartVisitModal } from '@/app/reception/components/visit/StartVisitModal';
import { VisitDetailsModal } from '@/app/reception/components/visit/VisitDetailsModal';
import { VisitQueue } from '@/app/reception/components/visit/VisitQueue';
import { PatientRegistrationForm } from '@/app/reception/components/patient/PatientRegistrationForm';
import { VisitResponse } from '@/shared/types';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';
import { PurposeOfUse, VisitServiceLine } from '@/shared/enums';
import {
  FollowUpListItem,
  followUpService,
} from '@/domains/followup/services/followupService';

export default function ReceptionPage() {
  const [isStartVisitModalOpen, setIsStartVisitModalOpen] = useState(false);
  const [showRegistrationForm, setShowRegistrationForm] = useState(false);
  const [refreshQueue, setRefreshQueue] = useState(0);
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
    setShowRegistrationForm(false);
  };

  const handleVisitClick = (visit: VisitResponse) => {
    setSelectedVisitId(visit.id);
    setIsDetailsModalOpen(true);
  };

  const refreshDashboard = async () => {
    try {
      const queue = await visitService.getQueue();
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
        const data = await visitService.getRecentVisits(5);
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
  }, [refreshQueue]);

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
          visitService.getQueue(),
          visitService.getQueue('COMPLETED'),
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
      } catch (error) {
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
  }, [refreshQueue]);

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

  const formatStat = (value: number) => (statsLoading ? '—' : value);


  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Reception Dashboard
              </h1>
              <p className="text-gray-600">
                Manage patient visits and clinic workflow
              </p>
            </div>
            <div className="mt-4 sm:mt-0 flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
                Today • {new Date().toLocaleDateString()}
              </span>
              <Button
                variant="primary"
                onClick={() => setIsStartVisitModalOpen(true)}
              >
                Start New Visit
              </Button>
              <Button
                variant="secondary"
                onClick={() => setShowRegistrationForm(!showRegistrationForm)}
              >
                {showRegistrationForm
                  ? 'Hide Registration'
                  : 'Register Patient'}
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">
                {formatStat(queueStats.total)}
              </div>
              <p className="text-gray-600">Queue Total</p>
              <p className="text-xs text-gray-400 mt-1">Active queue scope</p>
            </div>
          </Card>
          <Card>
            <div className="text-center">
              <div className="text-3xl font-bold text-yellow-600">
                {formatStat(queueStats.waiting)}
              </div>
              <p className="text-gray-600">Waiting (Registered/Triaged)</p>
              <p className="text-xs text-gray-400 mt-1">Active queue scope</p>
            </div>
          </Card>
          <Card>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">
                {formatStat(queueStats.completed)}
              </div>
              <p className="text-gray-600">Completed (Queue)</p>
              <p className="text-xs text-gray-400 mt-1">Completed in queue</p>
            </div>
          </Card>
          <Card>
            <div className="text-center">
              <div className="text-3xl font-bold text-red-600">
                {formatStat(queueStats.emergency)}
              </div>
              <p className="text-gray-600">Emergency (Queue)</p>
              <p className="text-xs text-gray-400 mt-1">Flagged emergency</p>
            </div>
          </Card>
        </div>

        {statsError && (
          <div className="mb-6 text-sm text-red-600">{statsError}</div>
        )}

        {showRegistrationForm && (
          <div className="mb-8">
            <PatientRegistrationForm
              onSuccess={handlePatientRegistered}
              onCancel={() => setShowRegistrationForm(false)}
            />
          </div>
        )}

        {recentMrnIssued && (
          <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-semibold text-emerald-900">
                  {recentPatientName ?? 'Patient'} registered successfully.
                </p>
                <p className="text-emerald-800">
                  MRN: <span className="font-semibold">{recentMrnIssued}</span>
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
            <p className="mt-2 text-xs text-emerald-700">
              This message will disappear automatically.
            </p>
          </div>
        )}

        {followUpActionError && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {followUpActionError}
          </div>
        )}
        {followUpActionSuccess && (
          <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {followUpActionSuccess}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <Card title="Quick Actions" titleClassName="text-[#0B4DA2]">
              <div className="space-y-3">
                <Button
                  variant="primary"
                  className="w-full justify-center"
                  onClick={() => setIsStartVisitModalOpen(true)}
                >
                  Start New Visit
                </Button>
                <Button
                  variant="secondary"
                  className="w-full justify-center"
                  onClick={() => setShowRegistrationForm(true)}
                >
                  Register New Patient
                </Button>
                <Button
                  variant="secondary"
                  className="w-full justify-center"
                  onClick={refreshDashboard}
                >
                  Refresh Dashboard
                </Button>
              </div>
              <p className="mt-3 text-xs text-gray-500">
                PMR access is audited. Use break-glass only for inactive visits.
              </p>
            </Card>

            <Card title="Recent Activity" titleClassName="text-[#0B4DA2]" className="mt-6">
              {recentLoading && (
                <div className="text-sm text-gray-500">Loading activity...</div>
              )}
              {recentError && (
                <div className="text-sm text-red-600">{recentError}</div>
              )}
              {!recentLoading && !recentError && recentVisits.length === 0 && (
                <div className="text-sm text-gray-500">No recent visits yet.</div>
              )}
              {!recentLoading && !recentError && recentVisits.length > 0 && (
                <div className="space-y-3">
                  {recentVisits.map((visit) => (
                    <button
                      key={visit.id}
                      onClick={() => handleVisitClick(visit)}
                      className="w-full rounded-lg border border-gray-200 px-3 py-2 text-left transition hover:bg-gray-50"
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-gray-900">
                          {visit.patient_name || 'Unknown patient'}
                        </p>
                        <VisitStatusBadge status={visit.status} size="sm" />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {visit.patient_mrn
                          ? `MRN: ${visit.patient_mrn}`
                          : `ID: ${maskId(visit.patient_id)}`}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        Updated {new Date(visit.updated_at).toLocaleTimeString()}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </Card>

            <Card title="Follow-Ups" titleClassName="text-[#0B4DA2]" className="mt-6">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-xs text-slate-500">
                  Start linked visits and reschedule from existing follow-up records.
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
                        <p className="text-sm font-semibold text-slate-900">{group.label}</p>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                          {group.items.length}
                        </span>
                      </div>
                      {group.items.length === 0 ? (
                        <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                          No follow-ups due.
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {group.items.slice(0, 6).map((item) => (
                            <div
                              key={item.id}
                              className="rounded-md border border-slate-200 bg-white px-3 py-2"
                            >
                              <p className="text-sm font-semibold text-slate-900">
                                {item.patient_name || 'Unknown patient'}
                              </p>
                              <p className="text-xs text-slate-500">
                                {item.patient_mrn
                                  ? `MRN ${item.patient_mrn}`
                                  : `Patient ${maskId(item.patient_id_canonical)}`}
                              </p>
                              <p className="mt-1 text-xs text-slate-600">{item.reason}</p>
                              <p className="text-xs text-slate-500">
                                Due {new Date(item.due_at).toLocaleString()}
                              </p>
                              <div className="mt-2 flex flex-wrap gap-2">
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
            </Card>
          </div>

          <div className="lg:col-span-2">
            <VisitQueue
              autoRefresh={true}
              refreshInterval={30000}
              onVisitClick={handleVisitClick}
              key={refreshQueue}
            />
          </div>
        </div>

        <StartVisitModal
          isOpen={isStartVisitModalOpen}
          onClose={() => setIsStartVisitModalOpen(false)}
          onSuccess={handleVisitCreated}
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
              <h3 className="text-lg font-semibold text-slate-900">Reschedule Follow-Up</h3>
              <p className="mt-1 text-sm text-slate-600">
                {rescheduleTarget.patient_name || 'Patient'} •{' '}
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
      </main>

      <footer className="bg-white border-t mt-8 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            Clinic Management System • {new Date().toLocaleDateString()}
          </p>
        </div>
      </footer>
    </div>
  );
}
