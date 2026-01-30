'use client';

import { useState, useEffect } from 'react';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitResponse } from '@/shared/types';
import { consultationService } from '@/domains/consultation/services/consultationService';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Tooltip } from '@/shared/Tooltip';

interface DoctorQueueProps {
  onStartConsultation?: (visit: VisitResponse) => void;
  onViewVisit?: (visit: VisitResponse) => void;
  onSelectPatient?: (visit: VisitResponse, hasConsultation: boolean) => void;
}

export function DoctorQueue({
  onStartConsultation,
  onViewVisit,
  onSelectPatient,
}: DoctorQueueProps) {
  const [visits, setVisits] = useState<VisitResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] =
    useState<string>('IN_CONSULTATION');
  const [consultationStatus, setConsultationStatus] = useState<
    Record<string, 'none' | 'in_progress' | 'completed'>
  >({});
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const statusOptions = [
    {
      value: 'IN_CONSULTATION',
      label: 'In Consultation',
      color: 'bg-purple-100 text-purple-800',
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

  const loadQueue = async () => {
    try {
      setError(null);
      const data = await visitService.getDoctorQueue(statusFilter);
      setVisits(data);

      const consultationChecks = await Promise.all(
        data.map(async (visit) => {
          try {
            const consultation =
              await consultationService.getConsultationByVisit(visit.id);
            if (!consultation) {
              return { visitId: visit.id, status: 'none' as const };
            }
            return {
              visitId: visit.id,
              status: consultation.completed_at ? 'completed' : 'in_progress',
            };
          } catch {
            return { visitId: visit.id, status: 'none' as const };
          }
        })
      );

      const statusMap = consultationChecks.reduce(
        (acc, curr) => ({
          ...acc,
          [curr.visitId]: curr.status,
        }),
        {}
      );

      setConsultationStatus(statusMap);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to load doctor queue:', err);
      setError('Unable to load your patient queue. Please try again.');
    } finally {
      setLoading(false);
    }
  };

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
  }, [statusFilter]);

  const handleStartConsultation = async (visit: VisitResponse) => {
    try {
      if (visit.status !== 'IN_CONSULTATION') {
        return;
      }

      if (onStartConsultation) {
        onStartConsultation(visit);
      }
    } catch (error) {
      console.error('Failed to start consultation:', error);
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
              const consultStatus = consultationStatus[visit.id];
              const hasConsultation = consultStatus === 'in_progress' || consultStatus === 'completed';

              return (
                <div
                  key={visit.id}
                  className="p-4 hover:bg-gray-50"
                  onClick={() =>
                    onSelectPatient && onSelectPatient(visit, hasConsultation)
                  }
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-3">
                        <VisitStatusBadge status={visit.status} size="sm" />
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
                            ID: {visit.patient_id.substring(0, 8)}...
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
                        <span>Visit ID: {visit.id.substring(0, 8)}...</span>
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
                            onStartConsultation && onStartConsultation(visit);
                          }}
                        >
                          Continue Consultation
                        </Button>
                      )}

                      {visit.status === 'TRIAGED' && (
                        <Tooltip content="Consultation starts after status changes to IN_CONSULTATION.">
                          <div>
                            <Button
                              size="sm"
                              variant="secondary"
                              disabled
                            >
                              Awaiting Consultation Status
                            </Button>
                          </div>
                        </Tooltip>
                      )}

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewVisit && onViewVisit(visit);
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
