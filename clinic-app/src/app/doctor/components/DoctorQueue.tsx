'use client';

import { useCallback, useEffect, useState } from 'react';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitResponse } from '@/shared/types';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { VisitStatus } from '@/shared/enums';

interface DoctorQueueProps {
  onStartConsultation?: (visit: VisitResponse) => void;
  onViewVisit?: (visit: VisitResponse) => void;
  onSelectPatient?: (visit: VisitResponse, hasConsultation: boolean) => void;
  refreshToken?: number;
}

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
    useState<string>('IN_CONSULTATION');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const statusOptions = [
    {
      value: 'IN_CONSULTATION',
      label: 'In Consultation',
      color: 'bg-purple-100 text-purple-800',
    },
    {
      value: 'EMERGENCY',
      label: 'Emergency',
      color: 'bg-red-100 text-red-800',
    },
    {
      value: 'TRIAGED',
      label: 'Triaged (Ready)',
      color: 'bg-yellow-100 text-yellow-800',
    },
    {
      value: 'LAB_REQUESTED',
      label: 'Lab Requested',
      color: 'bg-indigo-100 text-indigo-800',
    },
  ];

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
    }, 30000);

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
      if (visit.status === VisitStatus.TRIAGED) {
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
      <Card title="My Patient Queue">
        <div className="space-y-4">
          <div className="animate-pulse h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="My Patient Queue">
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Filter by visit status"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <div className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-xs font-medium text-gray-700">
              {visits.length} patient{visits.length !== 1 ? 's' : ''}
            </div>
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
        <div className="text-xs text-gray-500">
          Last refreshed:{' '}
          {lastUpdated ? lastUpdated.toLocaleTimeString() : '—'}
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <div className="flex">
              <div className="flex-shrink-0">
                <span className="text-red-400">⚠</span>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-600">{error}</p>
                <button
                  onClick={loadQueue}
                  className="mt-2 text-sm font-medium text-red-700 hover:text-red-800"
                >
                  Try again
                </button>
              </div>
            </div>
          </div>
        )}
        {startError && (
          <div className="p-3 rounded-md border border-amber-200 bg-amber-50 text-sm text-amber-900">
            {startError}
          </div>
        )}

        {!error && visits.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-600 font-medium">
              No patients in your{' '}
              {statusOptions
                .find((o) => o.value === statusFilter)
                ?.label?.toLowerCase()}{' '}
              queue
            </p>
            <p className="text-sm text-gray-400 mt-1">
              Patients will appear here when assigned to you.
            </p>
          </div>
        )}

        {!error && visits.length > 0 && (
          <div className="border rounded-lg divide-y">
            {visits.map((visit) => {
              const consultStatus = visit.consultation_status || 'none';
              const hasConsultation = consultStatus === 'in_progress' || consultStatus === 'completed';

              return (
                <div
                  key={visit.id}
                  className="p-4 hover:bg-gray-50"
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

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">Patient</span>
                          <p className="font-semibold text-gray-900">
                            {visit.patient_name || 'Unknown patient'}
                          </p>
                          <p className="text-xs text-gray-500">
                            {visit.patient_mrn
                              ? `MRN: ${visit.patient_mrn}`
                              : `ID: ${maskId(visit.patient_id)}`}
                          </p>
                        </div>
                        <div>
                          <span className="text-gray-600">Status Duration</span>
                          <p className="font-medium text-gray-900">
                            {getTimeAgo(visit.updated_at)}
                          </p>
                        </div>
                        <div>
                          <span className="text-gray-600">Visit Started</span>
                          <p className="font-medium text-gray-900">
                            {new Date(visit.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>

                      <div className="mt-3 flex items-center text-xs text-gray-500">
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

                      {visit.status === 'TRIAGED' && (
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
                        className="text-sm font-medium text-blue-700 hover:text-blue-800 underline underline-offset-2"
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
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Queue Summary
            </h4>
            <div className="flex flex-wrap gap-3">
              {statusOptions
                .map((opt) => {
                  const count = visits.filter((v) => v.status === opt.value)
                    .length;
                  if (count === 0) return null;

                  return (
                    <div key={opt.value} className="flex items-center space-x-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${opt.color}`}
                      >
                        {opt.label}
                      </span>
                      <span className="text-sm text-gray-600">{count}</span>
                    </div>
                  );
                })
                .filter(Boolean)}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
