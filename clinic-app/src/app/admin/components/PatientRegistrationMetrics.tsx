'use client';

import { useEffect, useState } from 'react';
import { financeService, PatientMetrics } from '@/domains/admin/services/financeService';
import { Card } from '@/shared/Card';
import { Alert } from '@/shared/Alert';
import { Button } from '@/shared/Button';

export function PatientRegistrationMetrics() {
  const [data, setData] = useState<PatientMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async (mode: 'initial' | 'refresh' = 'initial') => {
    try {
      if (mode === 'initial') {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);
      const response = await financeService.getPatientMetrics();
      setData(response);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Unable to load patient metrics.');
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

  if (loading) {
    return (
      <Card title="Patient Metrics" titleClassName="text-slate-900">
        <div className="space-y-3">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Patient Metrics" titleClassName="text-slate-900">
      <div className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}

        {!error && data && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">Registered Today</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">{data.registered_today}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-400">Total Patients</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">{data.total_patients}</p>
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
