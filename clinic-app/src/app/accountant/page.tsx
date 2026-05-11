'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { DashboardHero } from '@/app/components/DashboardHero';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';
import { HOSPITAL_NAME } from '@/shared/constants/branding';
import {
  pharmacyCatalogGovernanceService,
  type PharmacyCatalogRegistryRow,
} from '@/domains/pharmacy/services/pharmacyCatalogGovernanceService';
import {
  accountantService,
  AccountantAuditFeedRow,
  AccountantOverview,
  AccountantRefundRow,
  CashierSessionDetail,
  CashierSessionSummary,
  DepartmentRevenueItem,
  FraudSignals,
  OutstandingBillRow,
  PaymentMethodAnalysisItem,
} from '@/domains/accountant/services/accountantService';

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatMoney(amountMinor: number, currency: string): string {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amountMinor / 100);
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function methodLabel(method: string): string {
  if (method === 'CASH') return 'Cash';
  if (method === 'CARD') return 'POS/Card';
  if (method === 'TRANSFER') return 'Bank Transfer';
  return method;
}

export default function AccountantPage() {
  const dashboardUser = useDashboardUser();
  const [startDate, setStartDate] = useState(todayIsoDate());
  const [endDate, setEndDate] = useState(todayIsoDate());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<AccountantOverview | null>(null);
  const [departmentRevenue, setDepartmentRevenue] = useState<DepartmentRevenueItem[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodAnalysisItem[]>([]);
  const [cashierSessions, setCashierSessions] = useState<CashierSessionSummary[]>([]);
  const [recentRefunds, setRecentRefunds] = useState<AccountantRefundRow[]>([]);
  const [outstandingBills, setOutstandingBills] = useState<OutstandingBillRow[]>([]);
  const [auditFeed, setAuditFeed] = useState<AccountantAuditFeedRow[]>([]);
  const [fraudSignals, setFraudSignals] = useState<FraudSignals | null>(null);
  const [pricingQueue, setPricingQueue] = useState<PharmacyCatalogRegistryRow[]>([]);

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<CashierSessionDetail | null>(null);
  const [sessionDetailLoading, setSessionDetailLoading] = useState(false);
  const [sessionActionMessage, setSessionActionMessage] = useState<string | null>(null);
  const [pricingDrafts, setPricingDrafts] = useState<
    Record<string, { charge_code: string; unit_price_minor: string; effective_date: string }>
  >({});
  const [pricingSavingId, setPricingSavingId] = useState<string | null>(null);

  const currency = useMemo(() => {
    if (overview?.currency) return overview.currency;
    if (fraudSignals?.currency) return fraudSignals.currency;
    return 'NGN';
  }, [overview, fraudSignals]);

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [
        overviewResponse,
        revenueResponse,
        methodsResponse,
        sessionsResponse,
        refundsResponse,
        outstandingResponse,
        auditResponse,
        fraudResponse,
        pricingResponse,
      ] = await Promise.all([
        accountantService.getOverview(endDate),
        accountantService.getRevenueByDepartment({
          start_date: startDate,
          end_date: endDate,
        }),
        accountantService.getPaymentMethods({
          start_date: startDate,
          end_date: endDate,
        }),
        accountantService.listCashierSessions({
          limit: 5,
          offset: 0,
        }),
        accountantService.listRefunds({
          start_date: startDate,
          end_date: endDate,
          limit: 5,
          offset: 0,
        }),
        accountantService.listOutstanding({
          limit: 5,
          offset: 0,
        }),
        accountantService.getAuditFeed({
          limit: 15,
          offset: 0,
        }),
        accountantService.getFraudSignals(endDate),
        pharmacyCatalogGovernanceService.listAccountantPricingQueue(),
      ]);

      setOverview(overviewResponse);
      setDepartmentRevenue(revenueResponse);
      setPaymentMethods(methodsResponse);
      setCashierSessions(sessionsResponse.data);
      setRecentRefunds(refundsResponse.data);
      setOutstandingBills(outstandingResponse.data);
      setAuditFeed(auditResponse.data);
      setFraudSignals(fraudResponse);
      setPricingQueue(pricingResponse);
    } catch (loadError: unknown) {
      const detail =
        typeof loadError === 'object' &&
        loadError &&
        'response' in loadError &&
        typeof (loadError as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (loadError as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setError(detail || 'Unable to load accountant dashboard data.');
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  const loadSessionDetail = useCallback(async (sessionId: string) => {
    try {
      setSessionDetailLoading(true);
      setSessionActionMessage(null);
      const detail = await accountantService.getCashierSession(sessionId);
      setSessionDetail(detail);
      setSelectedSessionId(sessionId);
    } catch (detailError: unknown) {
      const detail =
        typeof detailError === 'object' &&
        detailError &&
        'response' in detailError &&
        typeof (detailError as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (detailError as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setSessionActionMessage(detail || 'Unable to load cashier session detail.');
    } finally {
      setSessionDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    setPricingDrafts((current) => {
      const next = { ...current };
      for (const item of pricingQueue) {
        if (!next[item.id]) {
          next[item.id] = {
            charge_code: item.charge_code || item.catalog_code.replace(/[^A-Z0-9]/gi, '_').toUpperCase(),
            unit_price_minor:
              item.current_price_minor !== null && item.current_price_minor !== undefined
                ? String(item.current_price_minor)
                : '',
            effective_date: item.effective_date || todayIsoDate(),
          };
        }
      }
      return next;
    });
  }, [pricingQueue]);

  const handleApplyFilters = () => {
    void loadDashboard();
  };

  const handleRefresh = () => {
    void loadDashboard();
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = async () => {
    try {
      const blob = await accountantService.downloadCsv({
        start_date: startDate,
        end_date: endDate,
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.setAttribute(
        'download',
        `accountant-report-${startDate}-to-${endDate}.csv`
      );
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch {
      setSessionActionMessage('Unable to export report at this time.');
    }
  };

  const handlePricingFieldChange = (
    itemId: string,
    field: 'charge_code' | 'unit_price_minor' | 'effective_date',
    value: string
  ) => {
    setPricingDrafts((current) => ({
      ...current,
      [itemId]: {
        charge_code: current[itemId]?.charge_code || '',
        unit_price_minor: current[itemId]?.unit_price_minor || '',
        effective_date: current[itemId]?.effective_date || todayIsoDate(),
        [field]: value,
      },
    }));
  };

  const handleSavePricing = async (itemId: string) => {
    const draft = pricingDrafts[itemId];
    if (!draft) return;
    try {
      setPricingSavingId(itemId);
      setSessionActionMessage(null);
      await pharmacyCatalogGovernanceService.upsertPricing(itemId, {
        charge_code: draft.charge_code,
        unit_price_minor: Number(draft.unit_price_minor),
        currency,
        effective_date: draft.effective_date,
        activate: true,
      });
      setSessionActionMessage('Pharmacy pricing updated and activated.');
      await loadDashboard();
    } catch {
      setSessionActionMessage('Unable to save pharmacy pricing configuration.');
    } finally {
      setPricingSavingId(null);
    }
  };

  const metrics = [
    {
      label: 'Revenue Today',
      value: overview ? formatMoney(overview.revenue_today_minor, currency) : '—',
      tone: 'text-[#1E3A8A]',
    },
    {
      label: 'Revenue This Month',
      value: overview ? formatMoney(overview.revenue_this_month_minor, currency) : '—',
      tone: 'text-[#1E3A8A]',
    },
    {
      label: 'Outstanding Bills',
      value: overview ? formatMoney(overview.outstanding_bills_minor, currency) : '—',
      tone: 'text-[#0F766E]',
    },
    {
      label: 'Refunds Today',
      value: overview ? formatMoney(overview.refunds_today_minor, currency) : '—',
      tone: 'text-amber-600',
    },
    {
      label: 'Net Revenue',
      value: overview ? formatMoney(overview.net_revenue_minor, currency) : '—',
      tone: 'text-slate-900',
    },
  ];

  return (
    <div className="space-y-6">
      <DashboardHero
        title="Accountant Dashboard"
        subtitle={HOSPITAL_NAME}
        workspaceLabel="Enterprise financial oversight and revenue cycle governance"
        monogram="K"
        rightSlot={
          <>
            <div>
              <span className="font-semibold">Accountant:</span>{' '}
              {getDashboardUserDisplayName(dashboardUser)}
            </div>
            <div>Period: {startDate} to {endDate}</div>
            <div>Date: {overview?.date || endDate}</div>
          </>
        }
        actionsSlot={
          <>
            <button
              type="button"
              onClick={handleDownload}
              className="rounded-md border border-white/40 bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20"
            >
              Download Report
            </button>
            <button
              type="button"
              onClick={handleRefresh}
              className="rounded-md border border-white/40 bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20"
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={handlePrint}
              className="rounded-md border border-white/40 bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20"
            >
              Print
            </button>
          </>
        }
      />

      <Card title="Filters">
        <div className="grid gap-3 md:grid-cols-4">
          <Input
            label="From"
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
          />
          <Input
            label="To"
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
          />
          <div className="flex items-end">
            <button
              type="button"
              onClick={handleApplyFilters}
              className="h-10 rounded-md bg-[#1E3A8A] px-4 text-sm font-semibold text-white hover:bg-[#172d6f]"
            >
              Apply Range
            </button>
          </div>
        </div>
      </Card>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {metric.label}
            </p>
            <p className={`mt-2 text-2xl font-semibold ${metric.tone}`}>
              {loading ? 'Loading...' : metric.value}
            </p>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card title="Revenue by Department">
          {departmentRevenue.length === 0 ? (
            <p className="text-sm text-slate-500">No departmental revenue for selected period.</p>
          ) : (
            <div className="space-y-3">
              {departmentRevenue.map((item) => (
                <div key={`${item.department_id || 'unassigned'}-${item.department_name}`}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-800">{item.department_name}</span>
                    <span className="text-slate-600">
                      {formatMoney(item.revenue_minor, currency)} ({formatPercent(item.percentage)})
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-[#1E3A8A]"
                      style={{ width: `${Math.max(item.percentage, 1)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Payment Method Analysis">
          {paymentMethods.length === 0 ? (
            <p className="text-sm text-slate-500">No payment methods recorded in selected period.</p>
          ) : (
            <div className="space-y-3">
              {paymentMethods.map((item) => (
                <div key={item.payment_method}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-800">
                      {methodLabel(item.payment_method)}
                    </span>
                    <span className="text-slate-600">
                      {formatMoney(item.total_minor, currency)} ({formatPercent(item.percentage)})
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-[#0F766E]"
                      style={{ width: `${Math.max(item.percentage, 1)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>

      <Card title="Cashier Session Oversight">
        <div className="space-y-3">
          <div className="overflow-x-auto rounded-md border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-700">
                <tr>
                  <th className="px-3 py-2 text-left">Cashier</th>
                  <th className="px-3 py-2 text-left">Shift Start</th>
                  <th className="px-3 py-2 text-right">Expected</th>
                  <th className="px-3 py-2 text-right">Counted</th>
                  <th className="px-3 py-2 text-right">Variance</th>
                  <th className="px-3 py-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {cashierSessions.map((session) => (
                  <tr
                    key={session.id}
                    className={`cursor-pointer hover:bg-slate-50 ${
                      selectedSessionId === session.id ? 'bg-[#EFF6FF]' : ''
                    }`}
                    onClick={() => void loadSessionDetail(session.id)}
                  >
                    <td className="px-3 py-2 font-medium text-slate-900">
                      {session.cashier_name || 'Unknown'}
                    </td>
                    <td className="px-3 py-2 text-slate-700">
                      {new Date(session.shift_start).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right text-slate-700">
                      {formatMoney(session.expected_total_minor, session.currency)}
                    </td>
                    <td className="px-3 py-2 text-right text-slate-700">
                      {session.counted_total_minor !== null &&
                      session.counted_total_minor !== undefined
                        ? formatMoney(session.counted_total_minor, session.currency)
                        : '—'}
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-semibold ${
                        session.variance_minor && session.variance_minor !== 0
                          ? 'text-amber-700'
                          : 'text-slate-700'
                      }`}
                    >
                      {session.variance_minor !== null &&
                      session.variance_minor !== undefined
                        ? formatMoney(session.variance_minor, session.currency)
                        : '—'}
                    </td>
                    <td className="px-3 py-2 text-slate-700">{session.status}</td>
                  </tr>
                ))}
                {cashierSessions.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-4 text-center text-slate-500">
                      No cashier sessions found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {sessionDetailLoading && (
            <p className="text-sm text-slate-500">Loading session detail...</p>
          )}

          {sessionDetail && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="mb-2">
                <h4 className="text-sm font-semibold text-slate-900">
                  Session Detail: {sessionDetail.session.cashier_name || 'Unknown'}
                </h4>
              </div>
              <p className="text-xs text-slate-600">
                Payments: {formatMoney(sessionDetail.payments_total_minor, sessionDetail.session.currency)}
                {' | '}
                Refunds: {formatMoney(sessionDetail.refunds_total_minor, sessionDetail.session.currency)}
                {' | '}
                Net: {formatMoney(sessionDetail.net_total_minor, sessionDetail.session.currency)}
              </p>
            </div>
          )}
          {sessionActionMessage && (
            <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
              {sessionActionMessage}
            </div>
          )}
        </div>
      </Card>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card title="Refund Monitoring">
          {recentRefunds.length === 0 ? (
            <p className="text-sm text-slate-500">No refunds in selected period.</p>
          ) : (
            <div className="space-y-2">
              {recentRefunds.map((refund) => (
                <div
                  key={refund.id}
                  className="rounded-md border border-slate-200 px-3 py-2 text-sm"
                >
                  <p className="font-medium text-slate-900">
                    {formatMoney(refund.amount_minor, refund.currency)} -{' '}
                    {refund.cashier_name || 'Unknown'}
                  </p>
                  <p className="text-slate-600">{refund.reason}</p>
                  <p className="text-xs text-slate-500">
                    {new Date(refund.processed_at).toLocaleString()} | {refund.receipt_number}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Outstanding Bills (Top 5)">
          {outstandingBills.length === 0 ? (
            <p className="text-sm text-slate-500">No outstanding bills.</p>
          ) : (
            <div className="space-y-2">
              {outstandingBills.map((bill) => (
                <div
                  key={bill.patient_id}
                  className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-sm"
                >
                  <div>
                    <p className="font-medium text-slate-900">{bill.patient_name || 'Unknown'}</p>
                    <p className="text-xs text-slate-500">{bill.visits_count} visit(s)</p>
                  </div>
                  <p className="font-semibold text-slate-900">
                    {formatMoney(bill.outstanding_minor, bill.currency)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>

      <Card title="Audit Activity Feed">
        {auditFeed.length === 0 ? (
          <p className="text-sm text-slate-500">No recent financial events.</p>
        ) : (
          <div className="space-y-2">
            {auditFeed.map((event) => (
              <div
                key={`${event.event_type}-${event.id}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium text-slate-900">
                    {event.event_type.replaceAll('_', ' ')}
                    {event.severity === 'warning' ? ' [Alert]' : ''}
                  </p>
                  <p className="text-xs text-slate-500">
                    {new Date(event.occurred_at).toLocaleString()} | {event.actor_name || 'System'} |{' '}
                    {event.reference || '—'}
                  </p>
                  {event.detail && <p className="text-xs text-slate-600">{event.detail}</p>}
                </div>
                <div className="text-right">
                  {event.amount_minor !== null && event.amount_minor !== undefined ? (
                    <p className="font-semibold text-slate-900">
                      {formatMoney(event.amount_minor, event.currency || currency)}
                    </p>
                  ) : (
                    <p className="text-xs text-slate-500">—</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Pharmacy Pricing Configuration">
        {pricingQueue.length === 0 ? (
          <p className="text-sm text-slate-500">No pharmacy catalog items are awaiting pricing action.</p>
        ) : (
          <div className="space-y-4">
            {pricingQueue.map((item) => {
              const draft = pricingDrafts[item.id] || {
                charge_code: item.charge_code || '',
                unit_price_minor:
                  item.current_price_minor !== null && item.current_price_minor !== undefined
                    ? String(item.current_price_minor)
                    : '',
                effective_date: item.effective_date || todayIsoDate(),
              };
              return (
                <div key={item.id} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900">
                        {item.generic_name}
                        {item.strength ? ` ${item.strength}` : ''} {item.dosage_form}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        {item.catalog_code} • {item.lifecycle_status} • Billing {item.billing_status}
                      </p>
                    </div>
                    <div className="text-sm text-slate-500">
                      CMD review:{' '}
                      {item.cmd_reviewed_at
                        ? new Date(item.cmd_reviewed_at).toLocaleString()
                        : 'Pending'}
                    </div>
                  </div>
                  <div className="mt-4 grid gap-4 lg:grid-cols-[220px_220px_180px_140px]">
                    <Input
                      label="Charge Code"
                      value={draft.charge_code}
                      onChange={(event) =>
                        handlePricingFieldChange(item.id, 'charge_code', event.target.value)
                      }
                    />
                    <Input
                      label="Unit Price (minor)"
                      value={draft.unit_price_minor}
                      onChange={(event) =>
                        handlePricingFieldChange(item.id, 'unit_price_minor', event.target.value)
                      }
                    />
                    <Input
                      label="Effective Date"
                      type="date"
                      value={draft.effective_date}
                      onChange={(event) =>
                        handlePricingFieldChange(item.id, 'effective_date', event.target.value)
                      }
                    />
                    <div className="flex items-end">
                      <button
                        type="button"
                        onClick={() => void handleSavePricing(item.id)}
                        disabled={
                          pricingSavingId === item.id ||
                          !draft.charge_code ||
                          !draft.unit_price_minor ||
                          !draft.effective_date
                        }
                        className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
                      >
                        {pricingSavingId === item.id ? 'Saving...' : 'Save & Activate'}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Card title="Fraud Prevention Signals">
        <div className="grid gap-3 md:grid-cols-4">
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
            <p className="text-xs uppercase text-slate-500">Large refunds {'>'} NGN 50k</p>
            <p className="text-lg font-semibold text-slate-900">
              {fraudSignals?.large_refunds_count ?? 0}
            </p>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
            <p className="text-xs uppercase text-slate-500">Receipt reprints today</p>
            <p className="text-lg font-semibold text-slate-900">
              {fraudSignals?.reprints_today_count ?? 0}
            </p>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
            <p className="text-xs uppercase text-slate-500">Variances {'>'} NGN 100</p>
            <p className="text-lg font-semibold text-slate-900">
              {fraudSignals?.open_variances_count ?? 0}
            </p>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
            <p className="text-xs uppercase text-slate-500">High cash total today</p>
            <p
              className={`text-lg font-semibold ${
                fraudSignals?.high_cash_today ? 'text-amber-700' : 'text-slate-900'
              }`}
            >
              {fraudSignals
                ? formatMoney(fraudSignals.cash_total_today_minor, fraudSignals.currency)
                : formatMoney(0, currency)}
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
