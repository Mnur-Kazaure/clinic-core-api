'use client';

import { useState, useEffect } from 'react';
import {
  visitService,
  VisitTimelineResponse,
  AllowedTransitionsResponse,
} from '@/domains/visit/services/visitService';
import { VisitResponse } from '@/shared/types';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';
import { VisitTimeline } from './VisitTimeline';
import { QuickActionButtons } from './QuickActionButtons';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Tooltip } from '@/shared/Tooltip';

interface VisitDetailsModalProps {
  visitId: string | null;
  isOpen: boolean;
  onClose: () => void;
  hiddenTransitions?: string[];
}

export function VisitDetailsModal({
  visitId,
  isOpen,
  onClose,
  hiddenTransitions,
}: VisitDetailsModalProps) {
  const [visit, setVisit] = useState<VisitResponse | null>(null);
  const [timeline, setTimeline] = useState<VisitTimelineResponse | null>(null);
  const [allowedTransitions, setAllowedTransitions] =
    useState<AllowedTransitionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'details' | 'timeline'>('details');

  useEffect(() => {
    if (isOpen && visitId) {
      loadVisitDetails();
    } else {
      resetState();
    }
  }, [isOpen, visitId]);

  const loadVisitDetails = async () => {
    if (!visitId) return;

    try {
      setLoading(true);
      setError(null);

      const [visitData, timelineData, transitionsData] = await Promise.all([
        visitService.getVisit(visitId),
        visitService.getVisitTimeline(visitId),
        visitService.getAllowedTransitions(visitId),
      ]);

      setVisit(visitData);
      setTimeline(timelineData);
      setAllowedTransitions(transitionsData);
    } catch (err: any) {
      console.error('Failed to load visit details:', err);
      setError(err.response?.data?.detail || 'Failed to load visit details');
    } finally {
      setLoading(false);
    }
  };

  const resetState = () => {
    setVisit(null);
    setTimeline(null);
    setAllowedTransitions(null);
    setError(null);
    setLoading(false);
  };

  const handleStatusChange = (newStatus: string) => {
    if (visit) {
      setVisit({ ...visit, status: newStatus as any });
      loadVisitDetails();
    }
  };

  const handleReassignDoctor = () => {
    console.log('Reassign doctor for visit:', visitId);
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
                <p className="text-gray-600">
                  Visit ID: {visit.id.substring(0, 12)}...
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
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
                  </div>
                </div>

                {allowedTransitions && (
                  <div className="mt-6">
                    <QuickActionButtons
                      visitId={visit.id}
                      currentStatus={visit.status}
                      allowedTransitions={allowedTransitions.allowed}
                      hiddenTransitions={hiddenTransitions}
                      onStatusChange={handleStatusChange}
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
                            {visit.id}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Clinic ID
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {visit.clinic_id}
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

                    <Card title="Assigned Doctor" titleClassName="text-[#0B4DA2]">
                      <div className="space-y-3">
                        <div>
                          <dt className="text-sm font-medium text-gray-500">
                            Doctor ID
                          </dt>
                          <dd className="text-sm text-gray-900">
                            {visit.assigned_doctor_id || 'Unassigned'}
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
                            ID: {visit.patient_id}
                          </dd>
                        </div>
                        <div className="pt-4 border-t">
                          {visit.status !== 'REGISTERED' ? (
                            <Tooltip content="Reassigning is only allowed before triage." widthClassName="w-64">
                              <div>
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  onClick={handleReassignDoctor}
                                  disabled
                                >
                                  Doctor cannot be changed after triage
                                </Button>
                              </div>
                            </Tooltip>
                          ) : (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={handleReassignDoctor}
                            >
                              Reassign Doctor
                            </Button>
                          )}
                        </div>
                      </div>
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}
