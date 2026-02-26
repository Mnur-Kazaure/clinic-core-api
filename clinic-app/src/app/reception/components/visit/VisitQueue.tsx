'use client';

import { useState, useEffect } from 'react';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitResponse } from '@/shared/types';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';

interface VisitQueueProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
  onVisitSelect?: (visit: VisitResponse) => void;
  onVisitClick?: (visit: VisitResponse) => void;
}

export function VisitQueue({
  autoRefresh = true,
  refreshInterval = 30000,
  onVisitSelect,
  onVisitClick,
}: VisitQueueProps) {
  const [visits, setVisits] = useState<VisitResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const statusOptions = [
    { value: 'all', label: 'All Visits' },
    { value: 'EMERGENCY', label: 'Emergency' },
    { value: 'ADMITTED', label: 'Admitted' },
    { value: 'REGISTERED', label: 'Registered' },
    { value: 'IN_CONSULTATION', label: 'In Consultation' },
    { value: 'LAB_REQUESTED', label: 'Lab Requested' },
    { value: 'PHARMACY_PENDING', label: 'Pharmacy Pending' },
    { value: 'COMPLETED', label: 'Completed' },
    { value: 'CANCELLED', label: 'Cancelled' },
  ];

  const loadQueue = async () => {
    try {
      setLoading(true);
      setError(null);
      const isSpecialFilter =
        statusFilter === 'all' ||
        statusFilter === 'EMERGENCY' ||
        statusFilter === 'ADMITTED';
      const statusParam = isSpecialFilter ? undefined : statusFilter;
      const data = await visitService.getQueue(statusParam);
      setVisits(data);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to load visit queue:', err);
      setError('Unable to load visit queue. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(loadQueue, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, statusFilter]);

  useEffect(() => {
    loadQueue();
  }, [statusFilter]);


  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { color: string; label: string }> = {
      EMERGENCY: { color: 'bg-red-100 text-red-800', label: 'Emergency' },
      ADMITTED: { color: 'bg-rose-100 text-rose-800', label: 'Admitted' },
      REGISTERED: { color: 'bg-blue-100 text-blue-800', label: 'Registered' },
      TRIAGED: { color: 'bg-blue-100 text-blue-800', label: 'Registered' },
      IN_CONSULTATION: {
        color: 'bg-purple-100 text-purple-800',
        label: 'In Consultation',
      },
      LAB_REQUESTED: {
        color: 'bg-indigo-100 text-indigo-800',
        label: 'Lab Requested',
      },
      LAB_COMPLETED: {
        color: 'bg-green-100 text-green-800',
        label: 'Lab Completed',
      },
      PHARMACY_PENDING: {
        color: 'bg-orange-100 text-orange-800',
        label: 'Pharmacy Pending',
      },
      COMPLETED: { color: 'bg-gray-100 text-gray-800', label: 'Completed' },
      CANCELLED: { color: 'bg-red-100 text-red-800', label: 'Cancelled' },
    };

    const config = statusConfig[status] || {
      color: 'bg-gray-100 text-gray-800',
      label: status,
    };

    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}
      >
        {config.label}
      </span>
    );
  };

  const maskId = (value?: string | null) =>
    value ? `${value.substring(0, 8)}...` : 'Unknown';

  const formatWaitingTime = (dateString?: string | null) => {
    const date = parseDate(dateString);
    if (!date) return 'Unknown';
    const now = new Date();
    const diffMs = Math.max(now.getTime() - date.getTime(), 0);
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m`;
    const diffHours = Math.floor(diffMins / 60);
    return `${diffHours}h ${diffMins % 60}m`;
  };

  const parseDate = (dateString?: string | null) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    return Number.isNaN(date.getTime()) ? null : date;
  };

  const formatTime = (dateString?: string | null) => {
    const date = parseDate(dateString);
    if (!date) return 'Unknown';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getTimeAgo = (dateString?: string | null) => {
    const date = parseDate(dateString);
    if (!date) return 'Unknown';
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
      <Card title="Visit Queue" titleClassName="text-[#0B4DA2]">
        <div className="space-y-4">
          <div className="animate-pulse h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  const filteredVisits = visits.filter((visit) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'EMERGENCY') return Boolean(visit.intake_emergency_flag);
    if (statusFilter === 'ADMITTED') return Boolean(visit.has_active_admission);
    if (statusFilter === 'REGISTERED') {
      return visit.status === 'REGISTERED' || visit.status === 'TRIAGED';
    }
    return visit.status === statusFilter;
  });

  return (
    <Card title="Visit Queue" titleClassName="text-[#0B4DA2]">
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <div className="text-sm text-gray-500">
              {filteredVisits.length} visit
              {filteredVisits.length !== 1 ? 's' : ''}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {lastUpdated && (
              <span className="text-sm text-gray-500">
                Last refreshed {getTimeAgo(lastUpdated.toISOString())}
              </span>
            )}
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

        {!error && filteredVisits.length === 0 && (
          <div className="text-center py-8">
            <div className="text-gray-400 mb-2">📋</div>
            <p className="text-gray-500">
              {statusFilter === 'all'
                ? 'No visits in queue'
                : `No visits with status "${
                    statusOptions.find((o) => o.value === statusFilter)?.label
                  }"`}
            </p>
          </div>
        )}

        {!error && filteredVisits.length > 0 && (
          <div className="border rounded-lg divide-y">
            {filteredVisits.map((visit) => (
              <div
                key={visit.id}
                className={`p-4 hover:bg-gray-50 transition-colors ${
                  onVisitSelect || onVisitClick ? 'cursor-pointer' : ''
                }`}
                onClick={() => {
                  if (onVisitSelect) onVisitSelect(visit);
                  if (onVisitClick) onVisitClick(visit);
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      {getStatusBadge(visit.status)}
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
                      <span className="text-sm text-gray-500">
                        Started {formatTime(visit.created_at)}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">Patient:</span>
                        <p className="font-medium text-gray-900">
                          {visit.patient_name || 'Unknown patient'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {visit.patient_mrn
                            ? `MRN: ${visit.patient_mrn}`
                            : `ID: ${maskId(visit.patient_id)}`}
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-600">Doctor ID:</span>
                        <p className="font-medium text-gray-900">
                          {visit.assigned_doctor_id
                            ? `${visit.assigned_doctor_id.substring(0, 8)}...`
                            : 'Unassigned'}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          Waiting {formatWaitingTime(visit.created_at)}
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-600">Duration:</span>
                        <p className="font-medium text-gray-900">
                          {getTimeAgo(visit.created_at)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center text-xs text-gray-500">
                      <span>
                        Visit ID: {maskId(visit.id)}
                      </span>
                      <span className="mx-2">•</span>
                      <span>
                        Created:{' '}
                        {parseDate(visit.created_at)?.toLocaleDateString() ||
                          'Unknown'}
                      </span>
                    </div>
                  </div>

                  {(onVisitSelect || onVisitClick) && (
                    <div className="ml-4">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onVisitSelect) onVisitSelect(visit);
                          if (onVisitClick) onVisitClick(visit);
                        }}
                        className="text-sm font-medium text-blue-700 hover:text-blue-800 underline underline-offset-2"
                      >
                        View Details
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {!error && visits.length > 0 && (
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Queue Summary
            </h4>
            <div className="flex flex-wrap gap-3">
              {statusOptions
                .filter((opt) => opt.value !== 'all')
                .map((opt) => {
                  const count =
                    opt.value === 'EMERGENCY'
                      ? visits.filter((v) => v.intake_emergency_flag).length
                      : opt.value === 'ADMITTED'
                      ? visits.filter((v) => v.has_active_admission).length
                      : visits.filter((v) => v.status === opt.value).length;
                  if (count === 0) return null;

                  return (
                    <div key={opt.value} className="flex items-center space-x-2">
                      {getStatusBadge(opt.value)}
                      <span className="text-sm text-gray-600">{count}</span>
                    </div>
                  );
                })
                .filter(Boolean)}
            </div>
          </div>
        )}

        {autoRefresh && (
          <div className="pt-2 border-t">
            <div className="flex items-center text-xs text-gray-500">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
              <span>
                Auto-refreshing every {refreshInterval / 1000} seconds
              </span>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
