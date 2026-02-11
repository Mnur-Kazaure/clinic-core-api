'use client';

import { useCallback, useEffect, useState } from 'react';
import { auditService, AuditTimelineItem } from '@/domains/admin/services/auditService';
import { Card } from '@/shared/Card';
import { Alert } from '@/shared/Alert';
import { Button } from '@/shared/Button';

function maskId(value: string | null | undefined) {
  if (!value) return '—';
  return `${value.slice(0, 6)}…${value.slice(-4)}`;
}

export function AuditTimeline() {
  const [items, setItems] = useState<AuditTimelineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [eventType, setEventType] = useState('');

  const loadTimeline = useCallback(async (mode: 'initial' | 'refresh' = 'initial') => {
    try {
      if (mode === 'initial') {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);
      const params = {
        from: fromDate || undefined,
        to: toDate || undefined,
        event_type: eventType || undefined,
        limit: 200,
      };
      const data = await auditService.getTimeline(params);
      setItems(data);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || 'Unable to load audit timeline.');
    } finally {
      if (mode === 'initial') {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  }, [eventType, fromDate, toDate]);

  useEffect(() => {
    loadTimeline('initial');
  }, [loadTimeline]);

  if (loading) {
    return (
      <Card title="Audit Trail" titleClassName="text-slate-900">
        <div className="space-y-3">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Audit Trail" titleClassName="text-slate-900">
      <div className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              From
            </label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              To
            </label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Event Type
            </label>
            <input
              type="text"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              placeholder="e.g. BREAK_GLASS_USED"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            variant="secondary"
            onClick={() => loadTimeline('refresh')}
            isLoading={refreshing}
          >
            Apply Filters
          </Button>
        </div>

        {!error && items.length === 0 && (
          <Alert variant="warning">No audit entries match the filters.</Alert>
        )}

        {items.length > 0 && (
          <div className="overflow-x-auto border border-slate-200 rounded-md">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">Time</th>
                  <th className="text-left px-4 py-3 font-medium">Type</th>
                  <th className="text-left px-4 py-3 font-medium">Source</th>
                  <th className="text-left px-4 py-3 font-medium">Actor</th>
                  <th className="text-left px-4 py-3 font-medium">Resource</th>
                  <th className="text-left px-4 py-3 font-medium">Patient</th>
                  <th className="text-left px-4 py-3 font-medium">Break-glass</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3 text-slate-700">
                      {new Date(item.occurred_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-slate-700">{item.event_type}</td>
                    <td className="px-4 py-3 text-slate-600">{item.source}</td>
                    <td className="px-4 py-3 text-slate-600">{item.actor_role}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {item.resource || '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {maskId(item.patient_id || null)}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {item.break_glass ? 'Yes' : 'No'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Card>
  );
}
