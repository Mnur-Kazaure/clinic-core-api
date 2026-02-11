'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { analyticsService, StaffActivityBucket } from '@/domains/admin/services/analyticsService';
import { Card } from '@/shared/Card';
import { Alert } from '@/shared/Alert';
import { Button } from '@/shared/Button';

function formatRoleCounts(counts: Record<string, number>) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return '—';
  return entries.map(([role, count]) => `${role}: ${count}`).join(', ');
}

export function StaffActivityHeatmap() {
  const [data, setData] = useState<StaffActivityBucket[]>([]);
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
      const response = await analyticsService.getStaffActivity(7);
      setData(response);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || 'Unable to load staff activity.');
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

  const rows = useMemo(() => {
    const map = new Map<string, {
      hour: string;
      registrations: Record<string, number>;
      consultations: Record<string, number>;
    }>();

    for (const item of data) {
      const hourKey = item.hour;
      const entry = map.get(hourKey) || {
        hour: hourKey,
        registrations: {},
        consultations: {},
      };

      if (item.activity_type === 'visit_registration') {
        entry.registrations[item.actor_role] =
          (entry.registrations[item.actor_role] || 0) + item.count;
      } else {
        entry.consultations[item.actor_role] =
          (entry.consultations[item.actor_role] || 0) + item.count;
      }

      map.set(hourKey, entry);
    }

    return Array.from(map.values()).sort(
      (a, b) => new Date(b.hour).getTime() - new Date(a.hour).getTime()
    );
  }, [data]);

  if (loading) {
    return (
      <Card title="Staff Activity Heatmap" titleClassName="text-slate-900">
        <div className="space-y-3">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Staff Activity Heatmap (Last 7 Days)" titleClassName="text-slate-900">
      <div className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}

        {!error && rows.length === 0 && (
          <Alert variant="warning">No staff activity recorded in the past 7 days.</Alert>
        )}

        {rows.length > 0 && (
          <div className="overflow-x-auto border border-slate-200 rounded-md">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">Hour</th>
                  <th className="text-left px-4 py-3 font-medium">Registrations</th>
                  <th className="text-left px-4 py-3 font-medium">Consultations</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((row) => (
                  <tr key={row.hour}>
                    <td className="px-4 py-3 text-slate-700">
                      {new Date(row.hour).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatRoleCounts(row.registrations)}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatRoleCounts(row.consultations)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
