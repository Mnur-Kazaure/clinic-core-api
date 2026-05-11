'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  BillingItem,
  BillingPayResponse,
  BillingReasonCode,
  CashierDashboardActivityRow,
  CashierDashboardChargeRow,
  CashierDashboardExceptionHoldRow,
  CashierDashboardResponse,
  CashierShift,
  billingWorkflowService,
} from '@/domains/billing/services/billingWorkflowService';
import { roleSessionService } from '@/domains/auth/services/roleSessionService';
import { clinicService } from '@/domains/clinic/services/clinicService';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';
import { useEventStreamSnapshot } from '@/shared/hooks/useEventStreamSnapshot';
import { UserDTO } from '@/shared/types';
import { DashboardHero } from '@/app/components/DashboardHero';
import {
  HOSPITAL_NAME,
  normalizeClinicDisplayName,
} from '@/shared/constants/branding';

const CASHIER_COLORS = {
  primary: '#1E3A8A',
  secondary: '#0F766E',
  accent: '#F59E0B',
  selectedBg: '#EFF6FF',
} as const;

type CashierSection =
  | 'overview'
  | 'pending'
  | 'pharmacy'
  | 'laboratory'
  | 'receipts'
  | 'transactions'
  | 'exceptions'
  | 'audit';

const SECTION_CONFIG: Array<{
  id: CashierSection;
  label: string;
  description: string;
}> = [
  {
    id: 'overview',
    label: 'Overview',
    description: 'Financial snapshot for this cashier desk',
  },
  {
    id: 'pending',
    label: 'Pending Charges',
    description: 'All unpaid billable items across the desk',
  },
  {
    id: 'pharmacy',
    label: 'Pharmacy Charges',
    description: 'Dedicated billing lane for pharmacy-linked charges',
  },
  {
    id: 'laboratory',
    label: 'Laboratory Charges',
    description: 'Laboratory billing queue with item-level visibility',
  },
  {
    id: 'receipts',
    label: 'Receipts',
    description: 'Issued receipt archive and print utilities',
  },
  {
    id: 'transactions',
    label: 'Transactions',
    description: 'Recent payment ledger view',
  },
  {
    id: 'exceptions',
    label: 'Exceptions / Holds',
    description: 'Controlled exception visibility without cashier overrides',
  },
  {
    id: 'audit',
    label: 'Activity Audit',
    description: 'Human-readable cashier and pharmacy unlock traceability',
  },
];

function formatMoney(amountMinor: number, currency: string): string {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amountMinor / 100);
}

function formatClock(value?: string | null): string {
  if (!value) return 'N/A';
  return new Date(value).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDateTime(value?: string | null): string {
  if (!value) return 'N/A';
  return new Date(value).toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function extractErrorDetail(error: unknown): string | null {
  if (typeof error !== 'object' || error === null || !('response' in error)) {
    return null;
  }
  const response = (
    error as { response?: { data?: { detail?: string } } }
  ).response;
  return response?.data?.detail || null;
}

function isChargeSection(section: CashierSection): boolean {
  return (
    section === 'pending' || section === 'pharmacy' || section === 'laboratory'
  );
}

function filterVisitItemsForSection(
  items: BillingItem[],
  section: CashierSection,
  payPointId?: string | null
): BillingItem[] {
  return items.filter((item) => {
    if (item.status !== 'PENDING') return false;
    if (
      payPointId &&
      item.cashier_pay_point_id &&
      item.cashier_pay_point_id !== payPointId
    ) {
      return false;
    }
    if (section === 'pharmacy') {
      return item.service_type === 'MEDICATION';
    }
    if (section === 'laboratory') {
      return item.service_type === 'LAB_TEST';
    }
    return true;
  });
}

function paymentActionLabel(
  section: CashierSection,
  selectedCharge: CashierDashboardChargeRow | null
): string {
  if (section === 'pharmacy' || selectedCharge?.service_type === 'MEDICATION') {
    return 'Pay Pharmacy Charges';
  }
  if (section === 'laboratory' || selectedCharge?.service_type === 'LAB_TEST') {
    return 'Pay Laboratory Charges';
  }
  return 'Process Selected Charges';
}

function badgeTone(count: number, accent: 'blue' | 'amber' | 'slate' = 'blue'): string {
  if (count <= 0) return 'border-slate-200 bg-slate-100 text-slate-600';
  if (accent === 'amber') return 'border-amber-200 bg-amber-50 text-amber-700';
  if (accent === 'slate') return 'border-slate-300 bg-white text-slate-700';
  return 'border-blue-200 bg-blue-50 text-blue-700';
}

function statusTone(value?: string | null): string {
  if (!value) return 'border-slate-200 bg-slate-100 text-slate-600';
  if (
    value.includes('READY') ||
    value.includes('PAID') ||
    value.includes('AUTHORIZED')
  ) {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  }
  if (value.includes('AWAITING') || value.includes('UNPAID')) {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }
  return 'border-blue-200 bg-blue-50 text-blue-700';
}

function agingTone(createdAt?: string): string {
  if (!createdAt) return 'text-slate-500';
  const ageMinutes = Math.max(
    0,
    Math.round((Date.now() - new Date(createdAt).getTime()) / 60000)
  );
  if (ageMinutes >= 30) return 'text-red-600';
  if (ageMinutes >= 15) return 'text-amber-600';
  return 'text-emerald-600';
}

export default function CashierPage() {
  const [user, setUser] = useState<UserDTO | null>(null);
  const [clinicName, setClinicName] = useState(HOSPITAL_NAME);
  const [selectedPayPointId, setSelectedPayPointId] = useState<string | null>(null);

  const [currentShift, setCurrentShift] = useState<CashierShift | null>(null);
  const [shiftLoading, setShiftLoading] = useState(true);
  const [shiftActionLoading, setShiftActionLoading] = useState(false);
  const [shiftError, setShiftError] = useState<string | null>(null);
  const [openingFloatMinor, setOpeningFloatMinor] = useState('0');
  const [closingCashMinor, setClosingCashMinor] = useState('');
  const [closingNote, setClosingNote] = useState('');
  const [showEndShiftModal, setShowEndShiftModal] = useState(false);

  const [dashboard, setDashboard] = useState<CashierDashboardResponse | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [activeSection, setActiveSection] = useState<CashierSection>('overview');

  const [selectedChargeId, setSelectedChargeId] = useState<string | null>(null);
  const [selectedVisitId, setSelectedVisitId] = useState<string | null>(null);
  const [visitItems, setVisitItems] = useState<BillingItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [itemsError, setItemsError] = useState<string | null>(null);
  const [selectedItemIds, setSelectedItemIds] = useState<string[]>([]);
  const [paymentMethod, setPaymentMethod] = useState<BillingReasonCode>('CASH');
  const [externalRef, setExternalRef] = useState('');
  const [notes, setNotes] = useState('Service payment');
  const [isPaying, setIsPaying] = useState(false);
  const [payError, setPayError] = useState<string | null>(null);
  const [lastReceipt, setLastReceipt] = useState<BillingPayResponse | null>(null);
  const [reprintMessage, setReprintMessage] = useState<string | null>(null);

  const clearPaymentSelectionState = useCallback(() => {
    setLastReceipt(null);
    setPayError(null);
  }, []);

  const loadIdentityContext = useCallback(async () => {
    try {
      const [currentUser, profile] = await Promise.all([
        roleSessionService.getCurrentUser(),
        clinicService.getProfile(),
      ]);
      setUser(currentUser);
      setSelectedPayPointId(
        currentUser.default_cashier_pay_point_id ||
          currentUser.allowed_cashier_pay_points?.[0]?.id ||
          null
      );
      setClinicName(normalizeClinicDisplayName(profile?.name));
    } catch {
      try {
        const fallbackUser = await roleSessionService.getCurrentUser();
        setUser(fallbackUser);
        setSelectedPayPointId(
          fallbackUser.default_cashier_pay_point_id ||
            fallbackUser.allowed_cashier_pay_points?.[0]?.id ||
            null
        );
      } catch {
        setUser(null);
      }
    }
  }, []);

  const loadCurrentShift = useCallback(async () => {
    try {
      setShiftError(null);
      const shift = await billingWorkflowService.getCurrentShift();
      setCurrentShift(shift);
    } catch {
      setShiftError('Unable to load shift status.');
      setCurrentShift(null);
    } finally {
      setShiftLoading(false);
    }
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      setDashboardError(null);
      const response = await billingWorkflowService.getDashboard({
        cashier_pay_point_id: selectedPayPointId || undefined,
        search: search.trim() || undefined,
        limit: 60,
      });
      setDashboard(response);
    } catch {
      setDashboardError('Unable to load cashier dashboard data.');
      setDashboard(null);
    } finally {
      setDashboardLoading(false);
    }
  }, [search, selectedPayPointId]);

  const dashboardStreamUrl = useMemo(
    () =>
      billingWorkflowService.getDashboardStreamUrl({
        cashier_pay_point_id: selectedPayPointId || undefined,
        search: search.trim() || undefined,
        limit: 60,
      }),
    [search, selectedPayPointId]
  );
  const { snapshot: liveDashboardSnapshot, error: liveDashboardError } =
    useEventStreamSnapshot<CashierDashboardResponse>({
      enabled: true,
      url: dashboardStreamUrl,
      eventName: 'cashier_dashboard_snapshot',
      errorMessage: 'Live cashier updates are temporarily unavailable.',
    });

  const loadVisitItems = useCallback(
    async (
      visitId: string,
      preferredItemId?: string | null,
      section: CashierSection = activeSection
    ) => {
      try {
        setItemsLoading(true);
        setItemsError(null);
        const data = await billingWorkflowService.listVisitItems(visitId);
        setVisitItems(data);
        const eligible = filterVisitItemsForSection(
          data,
          section,
          selectedPayPointId || undefined
        );
        const initialSelection =
          preferredItemId && eligible.some((item) => item.id === preferredItemId)
            ? [preferredItemId]
            : eligible.slice(0, 1).map((item) => item.id);
        setSelectedItemIds(initialSelection);
      } catch {
        setItemsError('Unable to load billing item details for this visit.');
        setVisitItems([]);
        setSelectedItemIds([]);
      } finally {
        setItemsLoading(false);
      }
    },
    [activeSection, selectedPayPointId]
  );

  useEffect(() => {
    void loadIdentityContext();
  }, [loadIdentityContext]);

  useEffect(() => {
    void Promise.all([loadCurrentShift(), loadDashboard()]);
  }, [loadCurrentShift, loadDashboard]);

  useEffect(() => {
    if (!liveDashboardSnapshot) {
      return;
    }
    setDashboard(liveDashboardSnapshot);
    setDashboardError(null);
    setDashboardLoading(false);
  }, [liveDashboardSnapshot]);

  useEffect(() => {
    if (!liveDashboardError) {
      return;
    }
    setDashboardError((current) => current ?? liveDashboardError);
  }, [liveDashboardError]);

  const allowedPayPoints = user?.allowed_cashier_pay_points || [];
  const activePayPoint =
    allowedPayPoints.find((payPoint) => payPoint.id === selectedPayPointId) ||
    allowedPayPoints[0] ||
    null;
  const shiftIsOpen = !!currentShift;
  const dashboardCurrency = dashboard?.overview.currency || 'NGN';

  const sectionBadges = useMemo(
    () => ({
      pending: dashboard?.overview.pending_charges_count || 0,
      pharmacy: dashboard?.overview.pharmacy_charges_pending || 0,
      laboratory: dashboard?.overview.laboratory_charges_pending || 0,
      receipts: dashboard?.receipts.length || 0,
      transactions: dashboard?.transactions.length || 0,
      exceptions: dashboard?.exceptions_holds.length || 0,
      audit: dashboard?.activity_audit.length || 0,
    }),
    [dashboard]
  );

  const activeChargeRows = useMemo(() => {
    if (!dashboard) return [];
    if (activeSection === 'pending') return dashboard.pending_charges;
    if (activeSection === 'pharmacy') return dashboard.pharmacy_charges;
    if (activeSection === 'laboratory') return dashboard.laboratory_charges;
    return [];
  }, [activeSection, dashboard]);

  useEffect(() => {
    if (!isChargeSection(activeSection)) {
      return;
    }
    if (activeChargeRows.length === 0) {
      setSelectedChargeId(null);
      return;
    }
    if (!selectedChargeId) {
      setSelectedChargeId(activeChargeRows[0].billing_item_id);
      return;
    }
    if (
      !activeChargeRows.some((row) => row.billing_item_id === selectedChargeId)
    ) {
      setSelectedChargeId(activeChargeRows[0].billing_item_id);
    }
  }, [activeChargeRows, activeSection, selectedChargeId]);

  const selectedCharge = useMemo(() => {
    if (!isChargeSection(activeSection)) return null;
    return (
      activeChargeRows.find((row) => row.billing_item_id === selectedChargeId) ||
      activeChargeRows[0] ||
      null
    );
  }, [activeChargeRows, activeSection, selectedChargeId]);

  const selectedChargeVisitId = selectedCharge?.visit_id || null;

  useEffect(() => {
    if (!selectedChargeId || !selectedChargeVisitId) {
      setSelectedVisitId(null);
      setVisitItems([]);
      setSelectedItemIds([]);
      return;
    }
    setSelectedVisitId(selectedChargeVisitId);
    void loadVisitItems(
      selectedChargeVisitId,
      selectedChargeId,
      activeSection
    );
  }, [activeSection, loadVisitItems, selectedChargeId, selectedChargeVisitId]);

  const handleSelectCharge = (billingItemId: string) => {
    clearPaymentSelectionState();
    setSelectedChargeId(billingItemId);
  };

  const handleSelectSection = (section: CashierSection) => {
    clearPaymentSelectionState();
    setActiveSection(section);
  };

  const payableItems = useMemo(
    () =>
      filterVisitItemsForSection(
        visitItems,
        activeSection,
        selectedPayPointId || undefined
      ),
    [activeSection, selectedPayPointId, visitItems]
  );

  const selectedItems = useMemo(
    () => payableItems.filter((item) => selectedItemIds.includes(item.id)),
    [payableItems, selectedItemIds]
  );

  const selectedTotalMinor = useMemo(
    () => selectedItems.reduce((sum, item) => sum + item.total_minor, 0),
    [selectedItems]
  );

  const selectedCurrency =
    selectedItems[0]?.currency || payableItems[0]?.currency || dashboardCurrency;
  const requiresRef = paymentMethod === 'TRANSFER' || paymentMethod === 'CARD';

  const parseMinorValue = (value: string): number | null => {
    if (!value.trim()) return null;
    const parsed = Number.parseInt(value.trim(), 10);
    if (Number.isNaN(parsed)) return null;
    return parsed;
  };

  const toggleItemSelection = (itemId: string) => {
    setSelectedItemIds((prev) =>
      prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]
    );
  };

  const handleStartShift = async () => {
    const opening = parseMinorValue(openingFloatMinor);
    if (opening === null || opening < 0) {
      setShiftError('Opening float must be a valid non-negative number.');
      return;
    }
    try {
      setShiftActionLoading(true);
      setShiftError(null);
      await billingWorkflowService.startShift(opening);
      await loadCurrentShift();
      await loadDashboard();
    } catch (error: unknown) {
      setShiftError(extractErrorDetail(error) || 'Unable to start shift.');
    } finally {
      setShiftActionLoading(false);
    }
  };

  const handleEndShift = async () => {
    const closing = parseMinorValue(closingCashMinor);
    if (closingCashMinor.trim() && (closing === null || closing < 0)) {
      setShiftError('Closing cash must be a valid non-negative number.');
      return;
    }
    try {
      setShiftActionLoading(true);
      setShiftError(null);
      await billingWorkflowService.endShift({
        closing_cash_minor: closing ?? undefined,
        closing_note: closingNote.trim() || undefined,
      });
      setClosingCashMinor('');
      setClosingNote('');
      setShowEndShiftModal(false);
      await loadCurrentShift();
      await loadDashboard();
    } catch (error: unknown) {
      setShiftError(extractErrorDetail(error) || 'Unable to end shift.');
    } finally {
      setShiftActionLoading(false);
    }
  };

  const handlePay = async () => {
    if (!shiftIsOpen) {
      setPayError('Start cashier shift before collecting payment.');
      return;
    }
    if (!selectedVisitId || selectedItemIds.length === 0) {
      setPayError('Select at least one billing item to settle.');
      return;
    }
    if (requiresRef && externalRef.trim().length < 3) {
      setPayError('Reference is required for transfer/card payments.');
      return;
    }
    try {
      setIsPaying(true);
      setPayError(null);
      setLastReceipt(null);
      const response = await billingWorkflowService.pay({
        visit_id: selectedVisitId,
        billing_item_ids: selectedItemIds,
        cashier_pay_point_id: selectedPayPointId || undefined,
        payment_method: paymentMethod,
        external_ref: requiresRef ? externalRef.trim() : undefined,
        notes: notes.trim() || undefined,
      });
      setLastReceipt(response);
      await loadDashboard();
      if (selectedVisitId) {
        await loadVisitItems(selectedVisitId, null, activeSection);
      }
    } catch (error: unknown) {
      setPayError(extractErrorDetail(error) || 'Payment failed. Please retry.');
    } finally {
      setIsPaying(false);
    }
  };

  const handleReprintReceipt = async (receiptId: string, receiptNumber: string) => {
    try {
      setReprintMessage(null);
      await billingWorkflowService.reprintReceipt(receiptId, 'Cashier desk reprint');
      setReprintMessage(`Receipt ${receiptNumber} reprint logged successfully.`);
      await loadDashboard();
    } catch (error: unknown) {
      setReprintMessage(extractErrorDetail(error) || 'Unable to log receipt reprint.');
    }
  };

  const renderOverview = () => (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Card>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Pending Charges
            </p>
            <p className="text-3xl font-semibold" style={{ color: CASHIER_COLORS.primary }}>
              {dashboard?.overview.pending_charges_count || 0}
            </p>
            <p className="text-sm text-slate-600">All unpaid items on this cashier desk</p>
          </div>
        </Card>
        <Card>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Pharmacy Charges Pending
            </p>
            <p className="text-3xl font-semibold" style={{ color: CASHIER_COLORS.primary }}>
              {dashboard?.overview.pharmacy_charges_pending || 0}
            </p>
            <p className="text-sm text-slate-600">
              Pharmacy items awaiting payment clearance
            </p>
          </div>
        </Card>
        <Card>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Paid Today
            </p>
            <p className="text-3xl font-semibold" style={{ color: CASHIER_COLORS.primary }}>
              {formatMoney(dashboard?.overview.paid_today_minor || 0, dashboardCurrency)}
            </p>
            <p className="text-sm text-slate-600">Receipts captured on this desk today</p>
          </div>
        </Card>
        <Card>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Receipts Today
            </p>
            <p className="text-3xl font-semibold" style={{ color: CASHIER_COLORS.primary }}>
              {dashboard?.overview.receipts_today || 0}
            </p>
            <p className="text-sm text-slate-600">Completed payment receipts today</p>
          </div>
        </Card>
        <Card>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Active Queue
            </p>
            <p className="text-3xl font-semibold" style={{ color: CASHIER_COLORS.primary }}>
              {dashboard?.overview.active_queue || 0}
            </p>
            <p className="text-sm text-slate-600">Visits with remaining unpaid items</p>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card title="Pharmacy Charges" titleClassName="text-slate-900">
          <div className="space-y-3">
            {dashboard?.pharmacy_charges.slice(0, 4).map((row) => (
              <button
                key={row.billing_item_id}
                type="button"
                onClick={() => {
                  handleSelectSection('pharmacy');
                  setSelectedChargeId(row.billing_item_id);
                }}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-left transition hover:border-slate-300 hover:bg-slate-50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {row.patient_name || 'Unknown patient'}
                    </p>
                    <p className="text-xs text-slate-500">
                      {row.patient_mrn ? `MRN ${row.patient_mrn}` : 'MRN not available'} •{' '}
                      {row.item_name}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {row.destination_hint || row.assigned_dispensing_unit_name || 'Awaiting routing'}
                    </p>
                  </div>
                  <span
                    className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(
                      row.payment_status
                    )}`}
                  >
                    {row.payment_status}
                  </span>
                </div>
              </button>
            ))}
            {dashboard?.pharmacy_charges.length === 0 && (
              <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
                No pending pharmacy charges on this pay point.
              </p>
            )}
          </div>
        </Card>

        <Card title="Recent Receipts" titleClassName="text-slate-900">
          <div className="space-y-3">
            {dashboard?.receipts.slice(0, 4).map((receipt) => (
              <div
                key={receipt.receipt_id}
                className="rounded-xl border border-slate-200 px-4 py-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {receipt.receipt_number}
                    </p>
                    <p className="text-xs text-slate-500">
                      {receipt.patient_name || 'Unknown patient'} •{' '}
                      {receipt.patient_mrn || 'No MRN'}
                    </p>
                  </div>
                  <p className="text-sm font-semibold text-slate-900">
                    {formatMoney(receipt.amount_minor, receipt.currency)}
                  </p>
                </div>
                {receipt.destination_hints.length > 0 && (
                  <p className="mt-2 text-xs text-emerald-700">
                    {receipt.destination_hints[0]}
                  </p>
                )}
              </div>
            ))}
            {dashboard?.receipts.length === 0 && (
              <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
                No receipts recorded for this view.
              </p>
            )}
          </div>
        </Card>

        <Card title="Activity Audit" titleClassName="text-slate-900">
          <div className="space-y-3">
            {dashboard?.activity_audit.slice(0, 4).map((row) => (
              <div
                key={row.id}
                className="rounded-xl border border-slate-200 px-4 py-3"
              >
                <p className="text-sm font-semibold text-slate-900">{row.title}</p>
                <p className="mt-1 text-sm text-slate-600">{row.detail}</p>
                <p className="mt-2 text-xs text-slate-500">
                  {row.patient_name || 'Unknown patient'} • {row.patient_mrn || 'No MRN'} •{' '}
                  {formatDateTime(row.occurred_at)}
                </p>
              </div>
            ))}
            {dashboard?.activity_audit.length === 0 && (
              <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
                No recent cashier activity for this scope.
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );

  const renderChargeWorkspace = (
    title: string,
    description: string,
    rows: CashierDashboardChargeRow[]
  ) => (
    <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
      <Card title={title} titleClassName="text-slate-900">
        <div className="space-y-4">
          <p className="text-sm text-slate-600">{description}</p>
          {rows.length === 0 ? (
            <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
              No rows are available for this lane.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="px-3 py-2 text-left">Patient</th>
                    <th className="px-3 py-2 text-left">Item</th>
                    <th className="px-3 py-2 text-left">Source</th>
                    <th className="px-3 py-2 text-left">Destination</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-slate-700">
                  {rows.map((row) => {
                    const selected = selectedCharge?.billing_item_id === row.billing_item_id;
                    return (
                      <tr
                        key={row.billing_item_id}
                        data-testid={`cashier-charge-row-${row.billing_item_id}`}
                        onClick={() => handleSelectCharge(row.billing_item_id)}
                        className={`cursor-pointer transition hover:bg-slate-50 ${
                          selected ? 'bg-blue-50/80' : 'bg-white'
                        }`}
                      >
                        <td className="px-3 py-3">
                          <p className="font-medium text-slate-900">
                            {row.patient_name || 'Unknown patient'}
                          </p>
                          <p className="text-xs text-slate-500">
                            {row.patient_mrn ? `MRN ${row.patient_mrn}` : 'MRN not available'}
                          </p>
                        </td>
                        <td className="px-3 py-3">
                          <p className="font-medium text-slate-900">{row.item_name}</p>
                          <p className={`text-xs ${agingTone(row.created_at)}`}>
                            Qty {row.quantity} • Waiting since {formatClock(row.created_at)}
                          </p>
                        </td>
                        <td className="px-3 py-3 text-slate-600">
                          {row.source_department_name || 'Unassigned source'}
                        </td>
                        <td className="px-3 py-3">
                          <p className="text-slate-700">
                            {row.assigned_dispensing_unit_name || 'Not applicable'}
                          </p>
                          {row.destination_hint && (
                            <p className="text-xs text-slate-500">{row.destination_hint}</p>
                          )}
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex flex-col gap-2">
                            <span
                              className={`inline-flex w-fit rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(
                                row.payment_status
                              )}`}
                            >
                              {row.payment_status}
                            </span>
                            {row.pharmacy_readiness_state && (
                              <span
                                className={`inline-flex w-fit rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(
                                  row.pharmacy_readiness_state
                                )}`}
                              >
                                {row.pharmacy_readiness_state}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-3 text-right font-semibold text-slate-900">
                          {formatMoney(row.amount_minor, row.currency)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      <Card title="Payment Collection" titleClassName="text-slate-900">
        <div className="space-y-4">
          {lastReceipt && (
            <div
              className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
              data-testid="cashier-payment-confirmation"
            >
              <p className="font-semibold">Payment confirmed</p>
              <p className="mt-1">Receipt: {lastReceipt.receipt_number}</p>
              <p>
                Amount: {formatMoney(lastReceipt.total_paid_minor, lastReceipt.currency)}
              </p>
              <p>Method: {lastReceipt.payment_method}</p>
              {lastReceipt.destination_hints.length > 0 && (
                <div className="mt-3 space-y-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-emerald-800">
                  {lastReceipt.destination_hints.map((hint) => (
                    <p key={hint.billing_item_id}>{hint.destination_label}</p>
                  ))}
                </div>
              )}
            </div>
          )}

          {!selectedCharge ? (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-600">
              Select a charge row to start item-level payment collection.
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <h4 className="text-sm font-semibold text-slate-800">Selected Charge</h4>
                <div className="mt-2 space-y-2 text-sm text-slate-700">
                  <p>
                    Patient:{' '}
                    <span className="font-medium">
                      {selectedCharge.patient_name || 'Unknown patient'}
                    </span>
                  </p>
                  <p>
                    Visit:{' '}
                    <span className="font-medium">
                      {selectedCharge.visit_id.slice(0, 8)}...
                    </span>
                  </p>
                  <p>
                    Item: <span className="font-medium">{selectedCharge.item_name}</span>
                  </p>
                  <p>
                    Assigned Dispensing Unit:{' '}
                    <span className="font-medium">
                      {selectedCharge.assigned_dispensing_unit_name || 'Not applicable'}
                    </span>
                  </p>
                  {selectedCharge.destination_hint && (
                    <p className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
                      {selectedCharge.destination_hint}
                    </p>
                  )}
                </div>
              </div>

              {itemsError && (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {itemsError}
                </div>
              )}
              {itemsLoading && (
                <p className="text-sm text-slate-500">Loading billed items for this visit...</p>
              )}
              {!itemsLoading && payableItems.length === 0 && (
                <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
                  No payable items remain in this lane for the selected visit.
                </p>
              )}

              {!itemsLoading && payableItems.length > 0 && (
                <>
                  <div className="space-y-2 rounded-xl border border-slate-200 p-3">
                    {payableItems.map((item) => (
                      <label
                        key={item.id}
                        className="flex items-center justify-between gap-3 rounded-md border border-slate-100 px-3 py-2"
                      >
                        <div className="flex items-start gap-2">
                          <input
                            type="checkbox"
                            checked={selectedItemIds.includes(item.id)}
                            onChange={() => toggleItemSelection(item.id)}
                            className="mt-0.5"
                          />
                          <div>
                            <p className="text-sm font-medium text-slate-900">
                              {item.item_name}
                            </p>
                            <p className="text-xs text-slate-500">
                              {item.charge_code || item.service_type} • Qty {item.quantity}
                            </p>
                          </div>
                        </div>
                        <p className="text-sm font-semibold text-slate-900">
                          {formatMoney(item.total_minor, item.currency)}
                        </p>
                      </label>
                    ))}
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="space-y-1">
                      <span className="text-sm font-medium text-slate-700">Payment Method</span>
                      <select
                        value={paymentMethod}
                        onChange={(event) =>
                          setPaymentMethod(event.target.value as BillingReasonCode)
                        }
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                        disabled={isPaying}
                      >
                        <option value="CASH">Cash</option>
                        <option value="TRANSFER">Bank Transfer</option>
                        <option value="CARD">POS/Card</option>
                      </select>
                    </label>

                    <Input
                      label={`Reference ${requiresRef ? '(Required)' : '(Optional)'}`}
                      value={externalRef}
                      onChange={(event) => setExternalRef(event.target.value)}
                      placeholder="Transaction reference"
                      disabled={isPaying}
                    />
                  </div>

                  <label className="block space-y-1">
                    <span className="text-sm font-medium text-slate-700">Notes</span>
                    <textarea
                      value={notes}
                      onChange={(event) => setNotes(event.target.value)}
                      rows={3}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                      disabled={isPaying}
                      placeholder="Optional cashier note"
                    />
                  </label>

                  <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                    <span className="text-sm text-slate-600">
                      {selectedItemIds.length} item(s) selected
                    </span>
                    <span className="text-base font-semibold text-slate-900">
                      {formatMoney(selectedTotalMinor, selectedCurrency)}
                    </span>
                  </div>

                  {payError && (
                    <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                      {payError}
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={handlePay}
                    disabled={isPaying || selectedItemIds.length === 0 || !shiftIsOpen}
                    className="w-full rounded-md px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                    style={{ backgroundColor: CASHIER_COLORS.primary }}
                  >
                    {isPaying
                      ? 'Processing Payment...'
                      : paymentActionLabel(activeSection, selectedCharge)}
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </Card>
    </div>
  );

  const renderReceipts = () => (
    <Card title="Receipts" titleClassName="text-slate-900">
      <div className="space-y-4">
        {reprintMessage && (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            {reprintMessage}
          </div>
        )}
        {!dashboard?.receipts.length ? (
          <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            No receipts recorded for this view.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left">Receipt</th>
                  <th className="px-3 py-2 text-left">Patient</th>
                  <th className="px-3 py-2 text-left">Items</th>
                  <th className="px-3 py-2 text-left">Destination</th>
                  <th className="px-3 py-2 text-right">Amount</th>
                  <th className="px-3 py-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-slate-700">
                {dashboard.receipts.map((receipt) => (
                  <tr key={receipt.receipt_id} className="hover:bg-slate-50">
                    <td className="px-3 py-3">
                      <p className="font-medium text-slate-900">{receipt.receipt_number}</p>
                      <p className="text-xs text-slate-500">
                        {formatDateTime(receipt.occurred_at)}
                      </p>
                    </td>
                    <td className="px-3 py-3">
                      <p className="font-medium text-slate-900">
                        {receipt.patient_name || 'Unknown patient'}
                      </p>
                      <p className="text-xs text-slate-500">
                        {receipt.patient_mrn || 'No MRN'}
                      </p>
                    </td>
                    <td className="px-3 py-3 text-slate-600">
                      {receipt.linked_items.join(', ') || 'No linked items'}
                    </td>
                    <td className="px-3 py-3 text-slate-600">
                      {receipt.destination_hints[0] || 'No pharmacy destination'}
                    </td>
                    <td className="px-3 py-3 text-right font-semibold text-slate-900">
                      {formatMoney(receipt.amount_minor, receipt.currency)}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <button
                        type="button"
                        onClick={() =>
                          handleReprintReceipt(receipt.receipt_id, receipt.receipt_number)
                        }
                        className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-100"
                      >
                        Print / Reprint
                      </button>
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

  const renderTransactions = () => (
    <Card title="Transactions" titleClassName="text-slate-900">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-slate-600">
            Recent cashier transactions for the selected pay point scope.
          </p>
          <Link
            href="/cashier/transactions"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Open Full Activities
          </Link>
        </div>
        {!dashboard?.transactions.length ? (
          <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            No transactions recorded for this view.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left">Receipt</th>
                  <th className="px-3 py-2 text-left">Patient</th>
                  <th className="px-3 py-2 text-left">Pay Point</th>
                  <th className="px-3 py-2 text-left">Method</th>
                  <th className="px-3 py-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-slate-700">
                {dashboard.transactions.map((row) => (
                  <tr key={row.receipt_id} className="hover:bg-slate-50">
                    <td className="px-3 py-3">
                      <p className="font-medium text-slate-900">{row.receipt_number}</p>
                      <p className="text-xs text-slate-500">
                        {formatDateTime(row.occurred_at)}
                      </p>
                    </td>
                    <td className="px-3 py-3">
                      <p className="font-medium text-slate-900">
                        {row.patient_name || 'Unknown patient'}
                      </p>
                      <p className="text-xs text-slate-500">{row.patient_mrn || 'No MRN'}</p>
                    </td>
                    <td className="px-3 py-3 text-slate-600">
                      {row.cashier_pay_point_name || 'Unassigned'}
                    </td>
                    <td className="px-3 py-3 text-slate-600">{row.payment_method}</td>
                    <td className="px-3 py-3 text-right font-semibold text-slate-900">
                      {formatMoney(row.amount_minor, row.currency)}
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

  const renderExceptions = () => (
    <Card title="Exceptions / Holds" titleClassName="text-slate-900">
      <div className="space-y-4">
        {!dashboard?.exceptions_holds.length ? (
          <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            No controlled exception items are currently visible on this desk.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left">Patient</th>
                  <th className="px-3 py-2 text-left">Item</th>
                  <th className="px-3 py-2 text-left">Exception</th>
                  <th className="px-3 py-2 text-left">Unit</th>
                  <th className="px-3 py-2 text-left">Readiness</th>
                  <th className="px-3 py-2 text-left">Payment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-slate-700">
                {dashboard.exceptions_holds.map((row: CashierDashboardExceptionHoldRow) => (
                  <tr key={row.prescription_id} className="hover:bg-slate-50">
                    <td className="px-3 py-3">
                      <p className="font-medium text-slate-900">
                        {row.patient_name || 'Unknown patient'}
                      </p>
                      <p className="text-xs text-slate-500">{row.patient_mrn || 'No MRN'}</p>
                    </td>
                    <td className="px-3 py-3 text-slate-700">{row.item_name}</td>
                    <td className="px-3 py-3 text-slate-700">
                      {row.exception_authorization_type}
                    </td>
                    <td className="px-3 py-3 text-slate-700">
                      {row.assigned_dispensing_unit_name || 'Unassigned'}
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(
                          row.readiness_state
                        )}`}
                      >
                        {row.readiness_state}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(
                          row.payment_status
                        )}`}
                      >
                        {row.payment_status}
                      </span>
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

  const renderAudit = () => (
    <Card title="Activity Audit" titleClassName="text-slate-900">
      <div className="space-y-3">
        {!dashboard?.activity_audit.length ? (
          <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            No cashier activity is available for this scope.
          </p>
        ) : (
          dashboard.activity_audit.map((row: CashierDashboardActivityRow) => (
            <div
              key={row.id}
              className="rounded-xl border border-slate-200 px-4 py-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-semibold text-slate-900">{row.title}</p>
                <span className="text-xs text-slate-500">
                  {formatDateTime(row.occurred_at)}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600">{row.detail}</p>
              <p className="mt-2 text-xs text-slate-500">
                {row.patient_name || 'Unknown patient'} • {row.patient_mrn || 'No MRN'} •{' '}
                {row.receipt_number || 'No receipt'}
              </p>
            </div>
          ))
        )}
      </div>
    </Card>
  );

  return (
    <div className="space-y-6">
      <DashboardHero
        title="Cashier Financial Workstation"
        subtitle={clinicName || HOSPITAL_NAME}
        workspaceLabel={`Desk: ${activePayPoint?.name || 'Unassigned pay point'}`}
        monogram="K"
        rightSlot={
          <>
            <div>
              <span className="font-semibold">Cashier:</span>{' '}
              {user?.full_name || 'Loading...'}
            </div>
            <div className="flex items-center gap-2 lg:justify-end">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  shiftIsOpen ? 'bg-emerald-300' : 'bg-red-300'
                }`}
              />
              <span>Shift: {shiftIsOpen ? 'OPEN' : 'CLOSED'}</span>
            </div>
            <div>Started: {formatClock(currentShift?.started_at)}</div>
            <div>
              Pay Point: <span className="font-semibold">{activePayPoint?.name || 'N/A'}</span>
            </div>
            <div>
              Paid Today:{' '}
              <span className="font-semibold">
                {formatMoney(dashboard?.overview.paid_today_minor || 0, dashboardCurrency)}
              </span>
            </div>
          </>
        }
        actionsSlot={
          <Link
            href="/cashier/transactions"
            className="rounded-md border border-white/40 bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/20"
          >
            Full Activities
          </Link>
        }
      />

      {dashboardError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {dashboardError}
        </div>
      )}
      {shiftError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {shiftError}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
        <Card title="Cashier Filters" titleClassName="text-slate-900">
          <div className="grid gap-3 lg:grid-cols-[240px_minmax(0,1fr)_auto]">
            <label className="space-y-1">
              <span className="text-sm font-medium text-slate-700">Cashier Pay Point</span>
              <select
                value={selectedPayPointId || ''}
                onChange={(event) => setSelectedPayPointId(event.target.value || null)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                {allowedPayPoints.map((payPoint) => (
                  <option key={payPoint.id} value={payPoint.id}>
                    {payPoint.name}
                  </option>
                ))}
              </select>
            </label>

            <Input
              label="Search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Patient, MRN, item, receipt, or visit"
            />

            <button
              type="button"
              onClick={() => void loadDashboard()}
              className="rounded-md px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
              style={{ backgroundColor: CASHIER_COLORS.secondary }}
            >
              Refresh
            </button>
          </div>
        </Card>

        <Card title="Shift Control" titleClassName="text-slate-900">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  shiftIsOpen ? 'bg-emerald-500' : 'bg-red-500'
                }`}
              />
              <span className="text-sm font-medium text-slate-700">
                {shiftIsOpen ? 'OPEN' : 'CLOSED'}
              </span>
            </div>
            {!shiftIsOpen ? (
              <div className="space-y-3">
                <Input
                  label="Opening Float (minor units)"
                  value={openingFloatMinor}
                  onChange={(event) => setOpeningFloatMinor(event.target.value)}
                  placeholder="0"
                  disabled={shiftActionLoading}
                />
                <button
                  type="button"
                  onClick={handleStartShift}
                  disabled={shiftActionLoading}
                  className="w-full rounded-md px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                  style={{ backgroundColor: CASHIER_COLORS.primary }}
                >
                  {shiftActionLoading ? 'Starting...' : 'Start Shift'}
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-slate-600">
                  Started at {formatClock(currentShift?.started_at)}
                </p>
                <button
                  type="button"
                  onClick={() => setShowEndShiftModal(true)}
                  disabled={shiftActionLoading || shiftLoading}
                  className="w-full rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  End Shift
                </button>
              </div>
            )}
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[260px_minmax(0,1fr)]">
        <aside>
          <Card title="Cashier Navigation" titleClassName="text-slate-900">
            <div className="space-y-2">
              {SECTION_CONFIG.map((section) => {
                const selected = activeSection === section.id;
                const badgeCount =
                  section.id === 'pending'
                    ? sectionBadges.pending
                    : section.id === 'pharmacy'
                      ? sectionBadges.pharmacy
                      : section.id === 'laboratory'
                        ? sectionBadges.laboratory
                        : section.id === 'receipts'
                          ? sectionBadges.receipts
                          : section.id === 'transactions'
                            ? sectionBadges.transactions
                            : section.id === 'exceptions'
                              ? sectionBadges.exceptions
                              : section.id === 'audit'
                                ? sectionBadges.audit
                                : 0;
                return (
                  <button
                    key={section.id}
                    type="button"
                    onClick={() => handleSelectSection(section.id)}
                    className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                      selected
                        ? 'border-blue-300 shadow-sm'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                    style={selected ? { backgroundColor: CASHIER_COLORS.selectedBg } : undefined}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">
                          {section.label}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {section.description}
                        </p>
                      </div>
                      {badgeCount > 0 && (
                        <span
                          className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${badgeTone(
                            badgeCount,
                            section.id === 'pharmacy' || section.id === 'exceptions'
                              ? 'amber'
                              : 'blue'
                          )}`}
                        >
                          {badgeCount}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </Card>
        </aside>

        <section className="min-w-0">
          {dashboardLoading && !dashboard && (
            <div className="space-y-3">
              <div className="h-24 rounded-xl shimmer" />
              <div className="h-80 rounded-xl shimmer" />
            </div>
          )}

          {!dashboardLoading && activeSection === 'overview' && renderOverview()}
          {!dashboardLoading &&
            activeSection === 'pending' &&
            renderChargeWorkspace(
              'Pending Charges',
              'All unpaid billable items, with item-level selection and payment collection.',
              dashboard?.pending_charges || []
            )}
          {!dashboardLoading &&
            activeSection === 'pharmacy' &&
            renderChargeWorkspace(
              'Pharmacy Charges',
              'Dedicated pharmacy billing lane with dispensing-unit visibility and readiness context.',
              dashboard?.pharmacy_charges || []
            )}
          {!dashboardLoading &&
            activeSection === 'laboratory' &&
            renderChargeWorkspace(
              'Laboratory Charges',
              'Laboratory billing lane kept distinct from the pharmacy payment gate.',
              dashboard?.laboratory_charges || []
            )}
          {!dashboardLoading && activeSection === 'receipts' && renderReceipts()}
          {!dashboardLoading && activeSection === 'transactions' && renderTransactions()}
          {!dashboardLoading && activeSection === 'exceptions' && renderExceptions()}
          {!dashboardLoading && activeSection === 'audit' && renderAudit()}
        </section>
      </div>

      {showEndShiftModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
            <div className="border-b border-slate-200 px-5 py-4">
              <h3 className="text-lg font-semibold text-slate-900">End Shift</h3>
              <p className="mt-1 text-sm text-slate-600">
                Declare closing cash and optional note before shift closure.
              </p>
            </div>
            <div className="space-y-3 px-5 py-4">
              <Input
                label="Closing Cash (minor units)"
                value={closingCashMinor}
                onChange={(event) => setClosingCashMinor(event.target.value)}
                placeholder="Optional"
                disabled={shiftActionLoading}
              />
              <label className="block space-y-1">
                <span className="text-sm font-medium text-slate-700">Closing Note</span>
                <textarea
                  value={closingNote}
                  onChange={(event) => setClosingNote(event.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  placeholder="Optional variance note"
                  disabled={shiftActionLoading}
                />
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button
                type="button"
                onClick={() => setShowEndShiftModal(false)}
                disabled={shiftActionLoading}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleEndShift}
                disabled={shiftActionLoading}
                className="rounded-md px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                style={{ backgroundColor: CASHIER_COLORS.accent }}
              >
                {shiftActionLoading ? 'Ending Shift...' : 'Confirm End Shift'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
