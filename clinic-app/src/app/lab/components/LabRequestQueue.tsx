'use client';

import { useEffect, useState } from 'react';
import { labService, LabRequest } from '@/domains/lab/services/labService';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';

type LabStatusFilter = 'PENDING' | 'COMPLETED' | 'CANCELLED' | 'ALL';

interface LabRequestQueueProps {
  onSelectRequest?: (request: LabRequest) => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function LabRequestQueue({
  onSelectRequest,
  autoRefresh = true,
  refreshInterval = 30000,
}: LabRequestQueueProps) {
  const [requests, setRequests] = useState<LabRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] =
    useState<LabStatusFilter>('PENDING');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const statusParam = statusFilter === 'ALL' ? undefined : statusFilter;
      const data = await labService.getRequests(statusParam);
      setRequests(data);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to load lab requests:', err);
      setError('Unable to load lab requests. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(loadRequests, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, statusFilter]);

  useEffect(() => {
    loadRequests();
  }, [statusFilter]);

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

  const getStatusBadge = (status: string) => {
    const config =
      {
        PENDING: { color: 'bg-yellow-100 text-yellow-800', label: 'Pending' },
        COMPLETED: { color: 'bg-green-100 text-green-800', label: 'Completed' },
        CANCELLED: { color: 'bg-red-100 text-red-800', label: 'Cancelled' },
      }[status] || { color: 'bg-gray-100 text-gray-800', label: status };

    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}
      >
        {config.label}
      </span>
    );
  };

  const maskId = (value?: string | null) =>
    value ? `${value.substring(0, 6)}…${value.substring(value.length - 4)}` : '—';

  if (loading && requests.length === 0) {
    return (
      <Card title="Lab Requests" titleClassName="text-[#0B4DA2]">
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

  const filteredRequests = requests.filter(
    (request) => statusFilter === 'ALL' || request.status === statusFilter
  );

  return (
    <Card title="Lab Requests" titleClassName="text-[#0B4DA2]">
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as LabStatusFilter)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="PENDING">Pending</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
              <option value="ALL">All</option>
            </select>

            <div className="text-sm text-gray-500">
              {filteredRequests.length} request
              {filteredRequests.length !== 1 ? 's' : ''}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {lastUpdated && (
              <span className="text-sm text-gray-500">
                Updated {getTimeAgo(lastUpdated.toISOString())}
              </span>
            )}
            <Button
              size="sm"
              variant="secondary"
              onClick={loadRequests}
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
                  onClick={loadRequests}
                  className="mt-2 text-sm font-medium text-red-700 hover:text-red-800"
                >
                  Try again
                </button>
              </div>
            </div>
          </div>
        )}

        {!error && filteredRequests.length === 0 && (
          <div className="text-center py-8">
            <div className="text-gray-400 mb-2">🧪</div>
            <p className="text-gray-500">
              {statusFilter === 'PENDING'
                ? 'No pending lab requests'
                : `No ${statusFilter.toLowerCase()} lab requests`}
            </p>
          </div>
        )}

        {!error && filteredRequests.length > 0 && (
          <div className="border rounded-lg divide-y">
            {filteredRequests.map((request) => (
              <div
                key={request.id}
                className={`p-4 hover:bg-gray-50 transition-colors ${
                  onSelectRequest ? 'cursor-pointer' : ''
                }`}
                onClick={() => onSelectRequest && onSelectRequest(request)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      {getStatusBadge(request.status)}
                      <span className="text-xs text-gray-500">
                        {getTimeAgo(request.created_at)}
                      </span>
                    </div>

                    <div className="mt-2">
                      <p className="text-base font-semibold text-gray-900">
                        {request.patient_name || 'Unknown patient'}
                      </p>
                      <p className="text-xs text-gray-500">
                        {request.patient_mrn
                          ? `MRN ${request.patient_mrn}`
                          : `ID: ${maskId(request.patient_id)}`}
                      </p>
                    </div>

                    <div className="mt-3">
                      <p className="text-sm font-medium text-gray-900">
                        {request.test_name}
                      </p>
                      {request.special_instructions && (
                        <p className="mt-1 text-xs text-gray-600">
                          <span className="font-medium text-gray-700">
                            Instructions:
                          </span>{' '}
                          {request.special_instructions.length > 90
                            ? `${request.special_instructions.slice(0, 90)}…`
                            : request.special_instructions}
                        </p>
                      )}
                    </div>

                    <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-gray-500">
                      <span>
                        Requested by:{' '}
                        {request.requested_by_name
                          ? request.requested_by_name
                          : maskId(request.requested_by)}
                        {request.requested_by_role
                          ? ` · ${request.requested_by_role}`
                          : ''}
                      </span>
                      <span>
                        Visit: {maskId(request.visit_id)}
                      </span>
                      <span>
                        Request: {maskId(request.id)}
                      </span>
                    </div>

                    {request.completed_at && (
                      <div className="mt-2 text-xs text-gray-500">
                        Completed{' '}
                        {new Date(request.completed_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>

                  {onSelectRequest && request.status === 'PENDING' && (
                    <div className="shrink-0">
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectRequest(request);
                        }}
                      >
                        Process
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {!error && requests.length > 0 && (
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Summary</h4>
            <div className="flex flex-wrap gap-3">
              <div className="flex items-center space-x-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                  Pending
                </span>
                <span className="text-sm text-gray-600">
                  {requests.filter((r) => r.status === 'PENDING').length}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Completed
                </span>
                <span className="text-sm text-gray-600">
                  {requests.filter((r) => r.status === 'COMPLETED').length}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                  Cancelled
                </span>
                <span className="text-sm text-gray-600">
                  {requests.filter((r) => r.status === 'CANCELLED').length}
                </span>
              </div>
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
