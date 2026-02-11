'use client';

import { useCallback, useEffect, useState } from 'react';
import { complianceService, ComplianceSummary as Summary } from '@/domains/admin/services/complianceService';
import { Card } from '@/shared/Card';
import { Alert } from '@/shared/Alert';
import { Button } from '@/shared/Button';

export function ComplianceSummary() {
  const [summary, setSummary] = useState<Summary | null>(null);
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
      const response = await complianceService.getSummary();
      setSummary(response);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || 'Unable to load compliance summary.');
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
      <Card title="Compliance Summary" titleClassName="text-slate-900">
        <div className="space-y-3">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Compliance Summary" titleClassName="text-slate-900">
      <div className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}

        {!error && summary && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Break-glass (24h)
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {summary.break_glass_24h}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Open Audit Cases
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {summary.open_audit_cases}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Failed Logins (24h)
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {summary.failed_logins_24h}
              </p>
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
