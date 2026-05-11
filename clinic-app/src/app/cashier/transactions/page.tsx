'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  BillingReasonCode,
  BillingTransactionsResponse,
  billingWorkflowService,
} from '@/domains/billing/services/billingWorkflowService';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';
import { DashboardHero } from '@/app/components/DashboardHero';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { HOSPITAL_NAME } from '@/shared/constants/branding';

const PAGE_SIZE = 25;

function formatMoney(amountMinor: number, currency: string): string {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amountMinor / 100);
}

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function buildCsv(
  rows: BillingTransactionsResponse['data'],
  currency: string
): string {
  const header = [
    'Receipt Number',
    'Date Time',
    'Patient',
    'Visit ID',
    'Amount',
    'Payment Method',
    'Collected By',
  ];
  const lines = rows.map((row) => [
    row.receipt_number,
    new Date(row.occurred_at).toISOString(),
    row.patient_name || '',
    row.visit_id,
    (row.amount_minor / 100).toFixed(2),
    row.payment_method,
    row.collected_by_name || '',
  ]);
  const all = [header, ...lines];
  return `Currency,${currency}\n${all
    .map((line) =>
      line
        .map((value) => `"${String(value).replace(/"/g, '""')}"`)
        .join(',')
    )
    .join('\n')}`;
}

export default function CashierTransactionsPage() {
  const dashboardUser = useDashboardUser();
  const paymentMethodSelectId = 'cashier-transactions-payment-method';
  const [fromDate, setFromDate] = useState(todayIsoDate());
  const [toDate, setToDate] = useState(todayIsoDate());
  const [paymentMethod, setPaymentMethod] = useState<'ALL' | BillingReasonCode>(
    'ALL'
  );
  const [search, setSearch] = useState('');
  const [activeFilters, setActiveFilters] = useState<{
    fromDate: string;
    toDate: string;
    paymentMethod: 'ALL' | BillingReasonCode;
    search: string;
  }>({
    fromDate: todayIsoDate(),
    toDate: todayIsoDate(),
    paymentMethod: 'ALL',
    search: '',
  });

  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reprintMessage, setReprintMessage] = useState<string | null>(null);
  const [data, setData] = useState<BillingTransactionsResponse>({
    data: [],
    total: 0,
    page: 1,
    limit: PAGE_SIZE,
    total_amount_minor: 0,
    currency: 'NGN',
  });

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(data.total / data.limit)),
    [data.total, data.limit]
  );

  const loadTransactions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await billingWorkflowService.listTransactions({
        start_date: activeFilters.fromDate || undefined,
        end_date: activeFilters.toDate || undefined,
        payment_method:
          activeFilters.paymentMethod === 'ALL'
            ? undefined
            : activeFilters.paymentMethod,
        search: activeFilters.search.trim() || undefined,
        page,
        limit: PAGE_SIZE,
      });
      setData(response);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' &&
        err &&
        'response' in err &&
        typeof (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (err as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setError(detail || 'Unable to load transactions.');
      setData((prev) => ({ ...prev, data: [] }));
    } finally {
      setLoading(false);
    }
  }, [activeFilters, page]);

  useEffect(() => {
    void loadTransactions();
  }, [loadTransactions]);

  const handleApplyFilters = () => {
    setPage(1);
    setActiveFilters({
      fromDate,
      toDate,
      paymentMethod,
      search,
    });
  };

  const handleReprint = async (receiptId: string, receiptNumber: string) => {
    try {
      setReprintMessage(null);
      await billingWorkflowService.reprintReceipt(receiptId, 'Cashier transactions workspace');
      setReprintMessage(`Reprint logged for ${receiptNumber}.`);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' &&
        err &&
        'response' in err &&
        typeof (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (err as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setReprintMessage(detail || 'Unable to log reprint.');
    }
  };

  const handleExportCsv = () => {
    const csv = buildCsv(data.data, data.currency || 'NGN');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.setAttribute(
      'download',
      `cashier-transactions-${new Date().toISOString().slice(0, 10)}.csv`
    );
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <DashboardHero
        title="Cashier Full Activities"
        subtitle={HOSPITAL_NAME}
        workspaceLabel="Filtered payment analytics and transaction tracking"
        monogram="K"
        rightSlot={
          <>
            <div>
              <span className="font-semibold">Cashier:</span>{' '}
              {getDashboardUserDisplayName(dashboardUser)}
            </div>
            <div>
              Period: {activeFilters.fromDate || '—'} to {activeFilters.toDate || '—'}
            </div>
          </>
        }
        actionsSlot={
          <>
            <Link
              href="/cashier"
              className="rounded-md border border-white/40 bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20"
            >
              ← Back to Cashier Desk
            </Link>
            <button
              type="button"
              onClick={handleExportCsv}
              className="rounded-md border border-white/40 bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20"
            >
              Export CSV
            </button>
          </>
        }
      />

      <Card title="Filters">
        <div className="grid gap-3 lg:grid-cols-[repeat(5,minmax(0,1fr))_auto]">
          <Input
            label="From"
            type="date"
            value={fromDate}
            onChange={(event) => setFromDate(event.target.value)}
          />
          <Input
            label="To"
            type="date"
            value={toDate}
            onChange={(event) => setToDate(event.target.value)}
          />
          <label htmlFor={paymentMethodSelectId} className="space-y-1">
            <span className="text-sm font-medium text-slate-700">Payment Method</span>
            <select
              id={paymentMethodSelectId}
              value={paymentMethod}
              onChange={(event) =>
                setPaymentMethod(event.target.value as 'ALL' | BillingReasonCode)
              }
              className="h-10 w-full rounded-md border border-slate-300 px-3 text-sm text-slate-900"
            >
              <option value="ALL">All Methods</option>
              <option value="CASH">Cash</option>
              <option value="CARD">POS / Card</option>
              <option value="TRANSFER">Bank Transfer</option>
            </select>
          </label>
          <Input
            label="Search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Patient, visit ID, receipt..."
          />
          <div className="flex items-end">
            <button
              type="button"
              onClick={handleApplyFilters}
              className="h-10 rounded-md bg-[#1E3A8A] px-4 text-sm font-semibold text-white hover:bg-[#172d6f]"
            >
              Apply Filters
            </button>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Total Received Payments
          </p>
          <p className="mt-2 text-3xl font-semibold text-[#1E3A8A]">{data.total}</p>
        </Card>
        <Card>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Total Payments Amount
          </p>
          <p className="mt-2 text-3xl font-semibold text-[#0F766E]">
            {formatMoney(data.total_amount_minor, data.currency)}
          </p>
        </Card>
      </div>

      <Card title="Transactions">
        <div className="space-y-4">
          {reprintMessage && (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
              {reprintMessage}
            </div>
          )}
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
          <p className="text-sm text-slate-500">
            Showing {data.data.length} of {data.total} transactions
          </p>

          {loading ? (
            <div className="space-y-2">
              <div className="h-12 rounded-md shimmer" />
              <div className="h-12 rounded-md shimmer" />
              <div className="h-12 rounded-md shimmer" />
            </div>
          ) : data.data.length === 0 ? (
            <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
              No transactions found for the selected filters.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-slate-700">
                  <tr>
                    <th className="px-3 py-2 text-left">Receipt #</th>
                    <th className="px-3 py-2 text-left">Date / Time</th>
                    <th className="px-3 py-2 text-left">Patient</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                    <th className="px-3 py-2 text-left">Method</th>
                    <th className="px-3 py-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.data.map((row) => (
                    <tr key={row.receipt_id} className="hover:bg-[#EFF6FF]">
                      <td className="px-3 py-2 font-medium text-slate-900">
                        {row.receipt_number}
                      </td>
                      <td className="px-3 py-2 text-slate-600">
                        <div>{new Date(row.occurred_at).toLocaleDateString()}</div>
                        <div className="text-xs">
                          {new Date(row.occurred_at).toLocaleTimeString()}
                        </div>
                      </td>
                      <td className="px-3 py-2">{row.patient_name || 'Unknown'}</td>
                      <td className="px-3 py-2 text-right font-semibold">
                        {formatMoney(row.amount_minor, row.currency)}
                      </td>
                      <td className="px-3 py-2">{row.payment_method}</td>
                      <td className="px-3 py-2 text-right">
                        <button
                          type="button"
                          onClick={() => handleReprint(row.receipt_id, row.receipt_number)}
                          className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
                        >
                          Print
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={page <= 1}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Prev
            </button>
            <span className="text-sm text-slate-600">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={page >= totalPages}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}
