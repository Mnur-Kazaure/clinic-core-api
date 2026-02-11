'use client';

import { useCallback, useEffect, useState } from 'react';
import { analyticsService, SystemPerformanceMetrics as Metrics } from '@/domains/admin/services/analyticsService';
import { Card } from '@/shared/Card';
import { Alert } from '@/shared/Alert';
import { Button } from '@/shared/Button';

function formatMinutes(value: number | null) {
  if (value === null || Number.isNaN(value)) return '—';
  return `${value.toFixed(2)} min`;
}

export function SystemPerformanceMetrics() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (mode: 'initial' | 'refresh' = 'initial') => {
    try {
      if (mode === 'initial') {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);
      const response = await analyticsService.getSystemMetrics();
      setMetrics(response);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || 'Unable to load system metrics.');
    } finally {
      if (mode === 'initial') {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    load('initial');
  }, [load]);

  if (loading) {
    return (
      <Card title="System Performance" titleClassName="text-slate-900">
        <div className="space-y-3">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="System Performance" titleClassName="text-slate-900">
      <div className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}

        {!error && metrics && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Avg Triage Wait
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {formatMinutes(metrics.avg_triage_wait_minutes)}
              </p>
              <p className="text-xs text-slate-500">Samples: {metrics.triage_samples}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Avg Consult Wait
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {formatMinutes(metrics.avg_consult_wait_minutes)}
              </p>
              <p className="text-xs text-slate-500">Samples: {metrics.consult_samples}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Avg Lab Turnaround
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {formatMinutes(metrics.avg_lab_turnaround_minutes)}
              </p>
              <p className="text-xs text-slate-500">Samples: {metrics.lab_samples}</p>
            </div>
          </div>
        )}

        <div className="flex justify-end">
          <Button variant="secondary" onClick={() => load('refresh')} isLoading={refreshing}>
            Refresh
          </Button>
        </div>
      </div>
    </Card>
  );
}
