'use client';

import { useCallback, useEffect, useState } from 'react';
import { healthService, ClinicHealthSnapshot as Snapshot } from '@/domains/admin/services/healthService';
import { Card } from '@/shared/Card';
import { Alert } from '@/shared/Alert';
import { Button } from '@/shared/Button';

export function ClinicHealthSnapshot() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSnapshot = useCallback(async (mode: 'initial' | 'refresh' = 'initial') => {
    try {
      if (mode === 'initial') {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);
      const data = await healthService.getSnapshot();
      setSnapshot(data);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || 'Unable to load clinic health.');
    } finally {
      if (mode === 'initial') {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    loadSnapshot('initial');
  }, [loadSnapshot]);

  if (loading) {
    return (
      <Card title="Clinic Health" titleClassName="text-slate-900">
        <div className="space-y-3">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Clinic Health" titleClassName="text-slate-900">
      <div className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}

        {!error && !snapshot && (
          <Alert variant="warning">No clinic health data available.</Alert>
        )}

        {snapshot && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Active Visits
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {snapshot.active_visits}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Active Staff
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {snapshot.active_staff}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Break-glass (24h)
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {snapshot.break_glass_24h}
              </p>
            </div>
          </div>
        )}

        <div className="flex justify-end">
          <Button
            variant="secondary"
            onClick={() => loadSnapshot('refresh')}
            isLoading={refreshing}
          >
            Refresh
          </Button>
        </div>
      </div>
    </Card>
  );
}
