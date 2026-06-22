'use client';

import { useCallback, useEffect, useState } from 'react';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitResponse } from '@/shared/types';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';
import { Button } from '@/shared/Button';
import { VisitStatus } from '@/shared/enums';

interface DoctorQueueProps {
  onStartConsultation?: (visit: VisitResponse) => void;
  onViewVisit?: (visit: VisitResponse) => void;
  onSelectPatient?: (visit: VisitResponse, hasConsultation: boolean) => void;
  refreshToken?: number;
}

type DoctorQueueFilter =
  | VisitStatus.REGISTERED
  | VisitStatus.IN_CONSULTATION
  | VisitStatus.LAB_REQUESTED
  | 'EMERGENCY';

type DoctorQueueStatusOption = {
  value: DoctorQueueFilter;
  label: string;
  color: string;
};

const STATUS_OPTIONS: DoctorQueueStatusOption[] = [
  {
    value: VisitStatus.REGISTERED,
    label: 'Registered',
    color: 'bg-blue-100 text-blue-800',
  },
  {
    value: VisitStatus.IN_CONSULTATION,
    label: 'In Consultation',
    color: 'bg-purple-100 text-purple-800',
  },
  {
    value: 'EMERGENCY',
    label: 'Emergency',
    color: 'bg-red-100 text-red-800',
  },
  {
    value: VisitStatus.LAB_REQUESTED,
    label: 'Lab Requested',
    color: 'bg-indigo-100 text-indigo-800',
  },
];

// Keep doctor queue updates near real-time for newly assigned patients.
const QUEUE_POLL_INTERVAL_MS = 10_000;

export function DoctorQueue({
  onStartConsultation,
  onViewVisit,
  onSelectPatient,
  refreshToken,
}: DoctorQueueProps) {
  const [visits, setVisits] = useState<VisitResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [startingVisitId, setStartingVisitId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] =
    useState<DoctorQueueFilter>(VisitStatus.REGISTERED);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadQueue = useCallback(async () => {
    try {
      setError(null);
      const isEmergencyFilter = statusFilter === 'EMERGENCY';
      const data = await visitService.getDoctorQueue(
        isEmergencyFilter ? undefined : statusFilter
      );
      const filtered = isEmergencyFilter
        ? data.filter((visit) => visit.intake_emergency_flag)
        : data;
      setVisits(filtered);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      console.error('Failed to load doctor queue:', err);
      setError('Unable to load your patient queue. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null;

    loadQueue();
    intervalId = setInterval(() => {
      loadQueue();
    }, QUEUE_POLL_INTERVAL_MS);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [loadQueue, refreshToken]);

  const handleStartConsultation = async (visit: VisitResponse) => {
    try {
      setStartError(null);
      setStartingVisitId(visit.id);

      let visitForConsultation = visit;
      if (
        visit.status === VisitStatus.TRIAGED ||
        visit.status === VisitStatus.REGISTERED
      ) {
        visitForConsultation = await visitService.transitionVisit(visit.id, {
          to_status: VisitStatus.IN_CONSULTATION,
          expected_version: visit.version,
          mode: 'normal',
        });
        setVisits((prev) =>
          prev.map((item) =>
            item.id === visitForConsultation.id ? visitForConsultation : item
          )
        );
      }

      if (visitForConsultation.status !== VisitStatus.IN_CONSULTATION) {
        setStartError('Visit must be moved into consultation before starting.');
        return;
      }

      if (onStartConsultation) {
        onStartConsultation(visitForConsultation);
      }
    } catch (error: unknown) {
      console.error('Failed to start consultation:', error);
      const detail =
        typeof error === 'object' && error && 'response' in error
          ? (error as { response?: { data?: { detail?: unknown } } }).response
              ?.data?.detail
          : undefined;

      if (detail && typeof detail === 'object') {
        const code = (detail as { code?: string }).code;
        if (code === 'VERSION_CONFLICT') {
          setStartError(
            'Visit was updated by another user. Refresh queue and retry.'
          );
          return;
        }
      }

      setStartError(
        typeof detail === 'string'
          ? detail
          : 'Unable to start consultation. Please refresh and try again.'
      );
    } finally {
      setStartingVisitId(null);
    }
  };

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const maskId = (value?: string | null) =>
    value ? `${value.substring(0, 6)}…${value.substring(value.length - 4)}` : '—';

  if (loading && visits.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
            My Patient Queue
          </p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">
            Loading assigned patients
          </h3>
        </div>
        <div className="space-y-4">
          <div className="h-8 w-1/3 animate-pulse rounded bg-slate-200"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-200"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0B4DA2]">
              My Patient Queue
            </p>
            <h3 className="mt-1 text-lg font-semibold text-slate-950">
              Service-backed Consultation Queue
            </h3>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm font-semibold text-slate-700">Status</label>
            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as DoctorQueueFilter)
              }
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-[#0B4DA2]"
              aria-label="Filter by visit status"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <div className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700">
              {visits.length} patient{visits.length !== 1 ? 's' : ''}
            </div>

            <Button
              size="sm"
              variant="secondary"
              onClick={loadQueue}
              disabled={loading}
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </Button>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500">
          Last refreshed:{' '}
          {lastUpdated ? lastUpdated.toLocaleTimeString() : '—'}
        </div>

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <span className="text-rose-500">!</span>
              </div>
              <div className="ml-3">
                <p className="text-sm text-rose-700">{error}</p>
                <button
                  onClick={loadQueue}
                  className="mt-2 text-sm font-semibold text-rose-800 hover:text-rose-900"
                >
                  Try again
                </button>
              </div>
            </div>
          </div>
        )}
        {startError && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            {startError}
          </div>
        )}

        {!error && visits.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 py-8 text-center">
            <p className="font-semibold text-slate-700">
              No patients in your{' '}
              {STATUS_OPTIONS
                .find((o) => o.value === statusFilter)
                ?.label?.toLowerCase()}{' '}
              queue
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Patients will appear here when assigned to you.
            </p>
          </div>
        )}

        {!error && visits.length > 0 && (
          <div className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white">
            {visits.map((visit) => {
              const consultStatus = visit.consultation_status || 'none';
              const hasConsultation = consultStatus === 'in_progress' || consultStatus === 'completed';

              return (
                <div
                  key={visit.id}
                  className="cursor-pointer border-l-4 border-l-transparent p-4 transition hover:border-l-[#0B4DA2] hover:bg-sky-50/40"
                  onClick={() => {
                    if (onSelectPatient) {
                      onSelectPatient(visit, hasConsultation);
                    }
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        <VisitStatusBadge status={visit.status} size="sm" />
                        {visit.intake_emergency_flag && (
                          <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                            Emergency
                          </span>
                        )}
                        {visit.has_active_admission && (
                          <span className="inline-flex items-center rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-800">
                            Admitted
                          </span>
                        )}
                        {consultStatus === 'in_progress' && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Consultation started
                          </span>
                        )}
                        {consultStatus === 'completed' && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#E6F4FB] text-[#0B4DA2]">
                            Consultation completed
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
                        <div>
                          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Patient</span>
                          <p className="mt-1 font-semibold text-slate-950">
                            {visit.patient_name || 'Unknown patient'}
                          </p>
                          <p className="text-xs text-slate-500">
                            {visit.patient_mrn
                              ? `MRN: ${visit.patient_mrn}`
                              : `ID: ${maskId(visit.patient_id)}`}
                          </p>
                        </div>
                        <div>
                          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Status Duration</span>
                          <p className="mt-1 font-medium text-slate-900">
                            {getTimeAgo(visit.updated_at)}
                          </p>
                        </div>
                        <div>
                          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Visit Started</span>
                          <p className="mt-1 font-medium text-slate-900">
                            {new Date(visit.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>

                      <div className="mt-3 flex items-center text-xs text-slate-500">
                        <span>Visit ID: {maskId(visit.id)}</span>
                      </div>
                    </div>

                    <div className="ml-4 flex flex-col space-y-2">
                      {visit.status === 'IN_CONSULTATION' && !hasConsultation && (
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartConsultation(visit);
                          }}
                          isLoading={startingVisitId === visit.id}
                          disabled={startingVisitId !== null}
                        >
                          Start Consultation
                        </Button>
                      )}

                      {visit.status === 'IN_CONSULTATION' &&
                        consultStatus === 'in_progress' && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onStartConsultation) {
                              onStartConsultation(visit);
                            }
                          }}
                        >
                          Continue Consultation
                        </Button>
                      )}

                      {(visit.status === VisitStatus.TRIAGED ||
                        visit.status === VisitStatus.REGISTERED) && (
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartConsultation(visit);
                          }}
                          isLoading={startingVisitId === visit.id}
                          disabled={startingVisitId !== null}
                        >
                          Start Consultation
                        </Button>
                      )}

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onViewVisit) {
                            onViewVisit(visit);
                          }
                        }}
                      className="text-sm font-semibold text-[#0B4DA2] underline underline-offset-4 hover:text-[#08386f]"
                      >
                        View Details
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!error && visits.length > 0 && (
          <div className="border-t border-slate-200 pt-4">
            <h4 className="mb-2 text-sm font-semibold text-slate-950">
              Queue Summary
            </h4>
            <div className="flex flex-wrap gap-3">
              {STATUS_OPTIONS
                .map((opt) => {
                  const count =
                    opt.value === 'EMERGENCY'
                      ? visits.filter((v) => v.intake_emergency_flag).length
                      : visits.filter((v) => v.status === opt.value).length;
                  if (count === 0) return null;

                  return (
                    <div key={opt.value} className="flex items-center space-x-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${opt.color}`}
                      >
                        {opt.label}
                      </span>
                      <span className="text-sm font-medium text-slate-600">{count}</span>
                    </div>
                  );
                })
                .filter(Boolean)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
