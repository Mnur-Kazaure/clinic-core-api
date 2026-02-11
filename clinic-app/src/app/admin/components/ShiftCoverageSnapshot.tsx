'use client';

import { useEffect, useMemo, useState } from 'react';
import { clinicService } from '@/domains/clinic/services/clinicService';
import { Card } from '@/shared/Card';
import { Alert } from '@/shared/Alert';
import { Button } from '@/shared/Button';

function normalizeStatus(value?: string | null) {
  if (!value) return 'Unknown';
  const lower = value.toLowerCase();
  if (lower.includes('away')) return 'Away';
  if (lower.includes('off')) return 'Off-duty';
  if (lower.includes('active') || lower.includes('available')) return 'Active';
  return 'Other';
}

export function ShiftCoverageSnapshot() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});

  const load = async (mode: 'initial' | 'refresh' = 'initial') => {
    try {
      if (mode === 'initial') {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);
      const staff = await clinicService.listStaff();
      const map: Record<string, number> = {};
      staff.forEach((member) => {
        const label = normalizeStatus(member.availability_status);
        map[label] = (map[label] || 0) + 1;
      });
      setCounts(map);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Unable to load staff coverage.');
    } finally {
      if (mode === 'initial') {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  };

  useEffect(() => {
    load('initial');
  }, []);

  const entries = useMemo(() => Object.entries(counts), [counts]);

  if (loading) {
    return (
      <Card title="Shift Coverage" titleClassName="text-slate-900">
        <div className="space-y-3">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Shift Coverage" titleClassName="text-slate-900">
      <div className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}

        {!error && entries.length === 0 && (
          <Alert variant="warning">No availability data recorded yet.</Alert>
        )}

        {entries.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {entries.map(([label, value]) => (
              <div
                key={label}
                className="rounded-xl border border-slate-200 bg-white p-4"
              >
                <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p>
              </div>
            ))}
          </div>
        )}

        <p className="text-xs text-slate-500">
          Coverage is derived from staff availability_status values.
        </p>

        <div className="flex justify-end">
          <Button variant="secondary" onClick={() => load('refresh')} isLoading={refreshing}>
            Refresh
          </Button>
        </div>
      </div>
    </Card>
  );
}
