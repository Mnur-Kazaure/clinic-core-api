'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { DashboardHero } from '@/app/components/DashboardHero';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { DispenseForm } from '@/app/pharmacy/components/DispenseForm';
import { PrescriptionDetailsModal } from '@/app/pharmacy/components/PrescriptionDetailsModal';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';
import { useEventStreamSnapshot } from '@/shared/hooks/useEventStreamSnapshot';
import { HOSPITAL_NAME } from '@/shared/constants/branding';
import {
  pharmacyService,
  type PharmacyDispensingActivityRow,
  type PharmacyDispensingAlertRow,
  type PharmacyDispensingDashboardResponse,
  type PharmacyDispensingQueueRow,
  type PharmacyIssueVoucherResponse,
  type PharmacyRefillRequestResponse,
  type PharmacyReturnRequestResponse,
} from '@/domains/pharmacy/services/pharmacyService';
import {
  PharmacyExceptionAuthorizationType,
  PharmacyPrescriptionWorkflowStatus,
} from '@/shared/enums';
import { PrescriptionResponse } from '@/shared/types';

const sidebarSections = [
  { id: 'overview', label: 'Overview', description: 'Fast command view for readiness, delays, and blockers' },
  { id: 'assigned', label: 'Assigned Prescriptions', description: 'All active prescriptions assigned to this dispensing unit' },
  { id: 'ready', label: 'Ready to Dispense', description: 'High-speed dispense lane for cleared prescriptions' },
  { id: 'awaiting', label: 'Awaiting Payment Clearance', description: 'Visible but blocked prescriptions awaiting cashier unlock' },
  { id: 'reassigned', label: 'Reassigned', description: 'Prescriptions recently routed into this unit' },
  { id: 'dispensed', label: 'Dispensed Today', description: 'Completed dispensing activity for the current day' },
  { id: 'stock', label: 'Local Stock', description: 'Local unit stock, batch, expiry, and refill trigger view' },
  { id: 'refills', label: 'Refill Requests', description: 'Replenishment requests, incoming supply acknowledgements, and return-to-store actions' },
  { id: 'alerts', label: 'Alerts', description: 'Out-of-stock, delay, and expiry attention items' },
  { id: 'activity', label: 'Activity Audit', description: 'Readable unit-level dispensing and replenishment history' },
] as const;

type SidebarSectionId = (typeof sidebarSections)[number]['id'];
const ALL_FILTER = 'ALL';

function formatDateTime(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleString();
}

function formatDateOnly(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleDateString();
}

function workflowLabel(value: string) {
  return value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function statusChip(status: string) {
  if (status.includes('OUT_OF_STOCK') || status.includes('EXPIRED') || status.includes('REJECTED') || status === 'UNMAPPED') {
    return 'border border-red-200 bg-red-50 text-red-700';
  }
  if (status.includes('LOW') || status.includes('AWAITING') || status.includes('PARTIAL') || status.includes('PENDING') || status.includes('ACCEPTED')) {
    return 'border border-amber-200 bg-amber-50 text-amber-700';
  }
  if (status.includes('READY') || status.includes('DISPENSED') || status.includes('RECEIVED') || status.includes('CLOSED')) {
    return 'border border-emerald-200 bg-emerald-50 text-emerald-700';
  }
  return 'border border-blue-200 bg-blue-50 text-blue-700';
}

function priorityChip(priority: string) {
  if (priority === 'EMERGENCY') return 'border border-red-200 bg-red-50 text-red-700';
  if (priority === 'URGENT') return 'border border-amber-200 bg-amber-50 text-amber-700';
  return 'border border-slate-200 bg-slate-100 text-slate-700';
}

function agingChip(minutes: number) {
  if (minutes >= 30) return 'text-red-700';
  if (minutes >= 20) return 'text-amber-700';
  return 'text-slate-600';
}

function badgeClass(tone: 'info' | 'warning' | 'critical') {
  if (tone === 'critical') return 'border border-red-200 bg-red-50 text-red-700';
  if (tone === 'warning') return 'border border-amber-200 bg-amber-50 text-amber-700';
  return 'border border-blue-200 bg-blue-50 text-blue-700';
}

function isReadyForDispenseState(status: PharmacyPrescriptionWorkflowStatus) {
  return (
    status === PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE ||
    status === PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED
  );
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <p className="mt-2 text-sm text-slate-600">{detail}</p>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1E4B8C]">
        {eyebrow}
      </p>
      <h2 className="mt-2 text-2xl font-semibold text-slate-900">{title}</h2>
      <p className="mt-2 max-w-3xl text-sm text-slate-600">{description}</p>
    </div>
  );
}

function MetricTile({
  label,
  value,
  detail,
  tone = 'neutral',
  onClick,
}: {
  label: string;
  value: string | number;
  detail?: string;
  tone?: 'neutral' | 'warning' | 'critical' | 'info';
  onClick?: () => void;
}) {
  const toneClass =
    tone === 'critical'
      ? 'border-red-200 bg-red-50'
      : tone === 'warning'
        ? 'border-amber-200 bg-amber-50'
        : tone === 'info'
          ? 'border-blue-200 bg-blue-50'
          : 'border-slate-200 bg-white';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-sm ${toneClass}`}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
        {label}
      </p>
      <p className="mt-3 text-3xl font-semibold text-slate-900">{value}</p>
      {detail ? <p className="mt-2 text-sm text-slate-600">{detail}</p> : null}
    </button>
  );
}

function matchesSearch(
  row: PharmacyDispensingQueueRow,
  term: string
) {
  const normalized = term.trim().toLowerCase();
  if (!normalized) return true;
  return [
    row.patient_name,
    row.patient_mrn,
    row.item_name,
    row.source_department_name,
    row.assigned_unit_name,
    row.cashier_pay_point_name,
  ]
    .filter(Boolean)
    .some((value) => value!.toLowerCase().includes(normalized));
}

function QueueTable({
  title,
  rows,
  emptyTitle,
  emptyDetail,
  onView,
  onBench,
}: {
  title: string;
  rows: PharmacyDispensingQueueRow[];
  emptyTitle: string;
  emptyDetail: string;
  onView: (row: PharmacyDispensingQueueRow) => void;
  onBench: (row: PharmacyDispensingQueueRow) => void;
}) {
  return (
    <Card title={title} titleClassName="text-[#1E4B8C]">
      {!rows.length ? (
        <EmptyState title={emptyTitle} detail={emptyDetail} />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-xs uppercase tracking-[0.12em] text-slate-500">
                <th className="px-4 py-3">Patient</th>
                <th className="px-4 py-3">Item</th>
                <th className="px-4 py-3">State</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Aging</th>
                <th className="px-4 py-3">Payment</th>
                <th className="px-4 py-3">Stock</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {rows.map((row) => {
                const canBench =
                  isReadyForDispenseState(row.readiness_state) &&
                  ['IN_STOCK', 'LOW_STOCK'].includes(row.local_stock_status);
                return (
                  <tr
                    key={row.prescription_id}
                    data-testid={`pharmacy-queue-row-${row.prescription_id}`}
                  >
                    <td className="px-4 py-4 align-top">
                      <p className="font-medium text-slate-900">
                        {row.patient_name || 'Unknown patient'}
                      </p>
                      <p className="mt-1 text-slate-500">
                        {row.patient_mrn ? `MRN ${row.patient_mrn}` : 'MRN not available'}
                      </p>
                      <p className="mt-1 text-slate-500">
                        {row.source_department_name || 'Source not mapped'}
                      </p>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <p className="font-medium text-slate-900">{row.item_name}</p>
                      <p className="mt-1 text-slate-500">
                        {row.dosage} • {row.frequency} • {row.duration}
                      </p>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusChip(row.readiness_state)}`}>
                        {workflowLabel(row.readiness_state)}
                      </span>
                      {row.quantity_remaining > 0 &&
                      row.quantity_dispensed_total > 0 ? (
                        <p className="mt-2 text-xs text-amber-700">
                          {row.quantity_remaining} remaining
                        </p>
                      ) : null}
                      {row.recently_reassigned ? (
                        <p className="mt-2 text-xs text-blue-700">
                          Reassigned into this unit
                        </p>
                      ) : null}
                    </td>
                    <td className="px-4 py-4 align-top">
                      <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${priorityChip(row.priority)}`}>
                        {row.priority}
                      </span>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <span className={`font-medium ${agingChip(row.aging_minutes)}`}>
                        {row.aging_minutes} min
                      </span>
                    </td>
                    <td className="px-4 py-4 align-top text-slate-700">
                      {workflowLabel(row.payment_state)}
                    </td>
                    <td className="px-4 py-4 align-top">
                      <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusChip(row.local_stock_status)}`}>
                        {workflowLabel(row.local_stock_status)}
                      </span>
                      <p className="mt-1 text-xs text-slate-500">
                        {row.local_stock_available_quantity} available
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Prescribed {row.quantity_prescribed} • Dispensed {row.quantity_dispensed_total}
                      </p>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="secondary" onClick={() => onView(row)}>
                          View
                        </Button>
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() => onBench(row)}
                          disabled={!canBench}
                        >
                          Bench
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export default function PharmacyPage() {
  const dashboardUser = useDashboardUser();
  const [dashboard, setDashboard] = useState<PharmacyDispensingDashboardResponse | null>(null);
  const [selectedUnitId, setSelectedUnitId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<SidebarSectionId>('overview');
  const [queueSearch, setQueueSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<string>(ALL_FILTER);
  const [stockFilter, setStockFilter] = useState<string>(ALL_FILTER);
  const [refillStatusFilter, setRefillStatusFilter] = useState<string>(ALL_FILTER);
  const [auditSearch, setAuditSearch] = useState('');
  const [selectedPrescription, setSelectedPrescription] =
    useState<PrescriptionResponse | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [benchOpen, setBenchOpen] = useState(false);
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [selectedVoucher, setSelectedVoucher] =
    useState<PharmacyIssueVoucherResponse | null>(null);
  const [voucherDraft, setVoucherDraft] = useState<Record<string, string>>({});
  const [voucherNote, setVoucherNote] = useState('');
  const [voucherSubmitting, setVoucherSubmitting] = useState(false);
  const [selectedReturnVoucher, setSelectedReturnVoucher] =
    useState<PharmacyIssueVoucherResponse | null>(null);
  const [selectedReturnVoucherItemId, setSelectedReturnVoucherItemId] = useState('');
  const [returnQuantity, setReturnQuantity] = useState('0');
  const [returnReasonCode, setReturnReasonCode] = useState('EXCESS_UNUSED');
  const [returnReasonNote, setReturnReasonNote] = useState('');
  const [returnSubmitting, setReturnSubmitting] = useState(false);
  const [refillItemId, setRefillItemId] = useState('');
  const [refillQuantity, setRefillQuantity] = useState('0');
  const [refillPriority, setRefillPriority] = useState('ROUTINE');
  const [refillNote, setRefillNote] = useState('');
  const [refillSubmitting, setRefillSubmitting] = useState(false);

  const assignedUnits = dashboardUser?.allowed_pharmacy_units || [];
  const dashboardStreamUrl = useMemo(
    () =>
      pharmacyService.getDashboardStreamUrl({
        unit_id:
          selectedUnitId || dashboardUser?.default_pharmacy_unit_id || undefined,
      }),
    [dashboardUser?.default_pharmacy_unit_id, selectedUnitId]
  );
  const { snapshot: liveDashboardSnapshot, error: liveDashboardError } =
    useEventStreamSnapshot<PharmacyDispensingDashboardResponse>({
      enabled: Boolean(dashboardUser),
      url: dashboardStreamUrl,
      eventName: 'pharmacy_dashboard_snapshot',
      errorMessage: 'Live pharmacy dispensing updates are temporarily unavailable.',
    });

  const loadDashboard = useCallback(
    async (mode: 'initial' | 'refresh' | 'poll' = 'initial') => {
      try {
        if (mode === 'initial') {
          setLoading(true);
        } else if (mode === 'refresh') {
          setRefreshing(true);
        }
        const payload = await pharmacyService.getDashboard({
          unit_id: selectedUnitId || undefined,
        });
        setDashboard(payload);
        setSelectedUnitId(payload.unit_id);
        setError(null);
      } catch (err: any) {
        setError(
          err?.response?.data?.detail ||
            'Unable to load the pharmacy dispensing workspace.'
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [selectedUnitId]
  );

  useEffect(() => {
    if (!selectedUnitId && dashboardUser?.default_pharmacy_unit_id) {
      setSelectedUnitId(dashboardUser.default_pharmacy_unit_id);
    }
  }, [dashboardUser?.default_pharmacy_unit_id, selectedUnitId]);

  useEffect(() => {
    void loadDashboard('initial');
  }, [loadDashboard]);

  useEffect(() => {
    if (!liveDashboardSnapshot) {
      return;
    }
    setDashboard(liveDashboardSnapshot);
    setSelectedUnitId(liveDashboardSnapshot.unit_id);
    setError(null);
    setLoading(false);
    setRefreshing(false);
  }, [liveDashboardSnapshot]);

  useEffect(() => {
    if (!liveDashboardError) {
      return;
    }
    setError((current) => current ?? liveDashboardError);
  }, [liveDashboardError]);

  useEffect(() => {
    if (!flashMessage) return;
    const timer = window.setTimeout(() => setFlashMessage(null), 4000);
    return () => window.clearTimeout(timer);
  }, [flashMessage]);

  const queueRows = dashboard?.prescriptions || [];
  const activeUnit =
    assignedUnits.find((unit) => unit.id === selectedUnitId) ||
    assignedUnits[0] ||
    null;

  const filteredQueueRows = useMemo(() => {
    return queueRows.filter((row) => {
      const matchesPriority =
        priorityFilter === ALL_FILTER || row.priority === priorityFilter;
      const matchesStock =
        stockFilter === ALL_FILTER || row.local_stock_status === stockFilter;
      return matchesPriority && matchesStock && matchesSearch(row, queueSearch);
    });
  }, [priorityFilter, queueRows, queueSearch, stockFilter]);

  const assignedRows = useMemo(
    () =>
      filteredQueueRows.filter((row) =>
        [
          PharmacyPrescriptionWorkflowStatus.ASSIGNED,
          PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE,
          PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
          PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
          PharmacyPrescriptionWorkflowStatus.IN_DISPENSE,
        ].includes(row.readiness_state)
      ),
    [filteredQueueRows]
  );
  const readyRows = useMemo(
    () =>
      filteredQueueRows.filter(
        (row) => isReadyForDispenseState(row.readiness_state)
      ),
    [filteredQueueRows]
  );
  const awaitingRows = useMemo(
    () =>
      filteredQueueRows.filter(
        (row) =>
          row.readiness_state ===
          PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE
      ),
    [filteredQueueRows]
  );
  const reassignedRows = useMemo(
    () => filteredQueueRows.filter((row) => row.recently_reassigned),
    [filteredQueueRows]
  );
  const dispensedTodayRows = useMemo(
    () =>
      filteredQueueRows.filter(
        (row) =>
          row.readiness_state === PharmacyPrescriptionWorkflowStatus.DISPENSED ||
          row.readiness_state ===
            PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED
      ),
    [filteredQueueRows]
  );

  const refillRequests = useMemo(() => {
    return (dashboard?.refill_requests || []).filter((request) =>
      refillStatusFilter === ALL_FILTER
        ? true
        : request.status === refillStatusFilter
    );
  }, [dashboard?.refill_requests, refillStatusFilter]);

  const incomingVouchers = useMemo(
    () =>
      (dashboard?.issue_vouchers || []).filter((voucher) =>
        ['DISPATCHED', 'ISSUED', 'PARTIALLY_RECEIVED'].includes(voucher.status)
      ),
    [dashboard?.issue_vouchers]
  );
  const returnRequests = useMemo(
    () => dashboard?.return_requests || [],
    [dashboard?.return_requests]
  );
  const returnableVouchers = useMemo(
    () =>
      (dashboard?.issue_vouchers || []).filter(
        (voucher) =>
          ['ACKNOWLEDGED', 'RECEIVED', 'CLOSED'].includes(voucher.status) &&
          voucher.items.some((item) => item.received_quantity > 0)
      ),
    [dashboard?.issue_vouchers]
  );

  const refillInventoryOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const stockRow of dashboard?.local_stock || []) {
      if (!seen.has(stockRow.inventory_item_id)) {
        seen.set(stockRow.inventory_item_id, stockRow.item_name);
      }
    }
    return Array.from(seen.entries())
      .map(([value, label]) => ({ value, label }))
      .sort((left, right) => left.label.localeCompare(right.label));
  }, [dashboard?.local_stock]);

  useEffect(() => {
    if (!refillItemId && refillInventoryOptions[0]) {
      setRefillItemId(refillInventoryOptions[0].value);
    }
  }, [refillInventoryOptions, refillItemId]);

  const activeSectionMeta =
    sidebarSections.find((section) => section.id === activeSection) ||
    sidebarSections[0];

  const detailFetch = async (
    row: PharmacyDispensingQueueRow,
    mode: 'detail' | 'bench'
  ) => {
    try {
      setDetailLoadingId(row.prescription_id);
      const prescription = await pharmacyService.getPrescription(
        row.prescription_id,
        selectedUnitId || undefined
      );
      setSelectedPrescription(prescription);
      setDetailsOpen(mode === 'detail');
      setBenchOpen(mode === 'bench');
    } catch (err) {
      console.error('Failed to load prescription detail:', err);
      setFlashMessage('Prescription detail could not be loaded.');
    } finally {
      setDetailLoadingId(null);
    }
  };

  const handleWorkflowSuccess = async (message?: string) => {
    setBenchOpen(false);
    setDetailsOpen(false);
    setSelectedPrescription(null);
    await loadDashboard('refresh');
    setFlashMessage(message || 'Dispensing workflow updated for this unit.');
  };

  const handleRefillSubmit = async () => {
    const quantity = Number(refillQuantity);
    if (!refillItemId || !quantity || quantity <= 0) {
      setFlashMessage('Enter a valid refill item and quantity.');
      return;
    }
    try {
      setRefillSubmitting(true);
      await pharmacyService.createRefillRequest({
        unit_id: selectedUnitId || undefined,
        request_type: 'PHARMACY_REFILL',
        urgency: refillPriority,
        note: refillNote.trim() || undefined,
        items: [
          {
            inventory_item_id: refillItemId,
            requested_quantity: quantity,
            note: refillNote.trim() || undefined,
          },
        ],
      });
      setFlashMessage('Refill request submitted and routed into the CMD approval workflow.');
      setRefillQuantity('0');
      setRefillNote('');
      await loadDashboard('refresh');
    } catch (err: any) {
      setFlashMessage(
        err?.response?.data?.detail || 'Refill request could not be submitted.'
      );
    } finally {
      setRefillSubmitting(false);
    }
  };

  const openVoucher = (voucher: PharmacyIssueVoucherResponse) => {
    setSelectedVoucher(voucher);
    const draft: Record<string, string> = {};
    for (const item of voucher.items) {
      draft[item.id] = String(item.issued_quantity - item.received_quantity);
    }
    setVoucherDraft(draft);
    setVoucherNote('');
  };

  const openReturnVoucher = (voucher: PharmacyIssueVoucherResponse) => {
    const fallbackItem =
      voucher.items.find((item) => item.received_quantity > 0) || voucher.items[0];
    setSelectedReturnVoucher(voucher);
    setSelectedReturnVoucherItemId(fallbackItem?.id || '');
    setReturnQuantity('0');
    setReturnReasonCode('EXCESS_UNUSED');
    setReturnReasonNote('');
  };

  const acknowledgeVoucher = async () => {
    if (!selectedVoucher) return;
    try {
      setVoucherSubmitting(true);
      await pharmacyService.acknowledgeIssueVoucher(selectedVoucher.id, {
        unit_id: selectedUnitId || undefined,
        note: voucherNote.trim() || undefined,
        items: selectedVoucher.items.map((item) => ({
          voucher_item_id: item.id,
          received_quantity: Number(voucherDraft[item.id] || '0'),
        })),
      });
      setFlashMessage('Incoming stock acknowledged for this unit.');
      setSelectedVoucher(null);
      await loadDashboard('refresh');
    } catch (err: any) {
      setFlashMessage(
        err?.response?.data?.detail || 'Voucher acknowledgement failed.'
      );
    } finally {
      setVoucherSubmitting(false);
    }
  };

  const submitReturnRequest = async () => {
    if (!selectedReturnVoucher || !selectedReturnVoucherItemId) {
      setFlashMessage('Select an issued stock line to return.');
      return;
    }
    const quantityNowReturned = Number(returnQuantity);
    if (!Number.isFinite(quantityNowReturned) || quantityNowReturned <= 0) {
      setFlashMessage('Enter a valid return quantity.');
      return;
    }
    try {
      setReturnSubmitting(true);
      await pharmacyService.createReturnRequest({
        unit_id: selectedUnitId || undefined,
        issue_voucher_id: selectedReturnVoucher.id,
        issue_voucher_item_id: selectedReturnVoucherItemId,
        quantity_now_returned: quantityNowReturned,
        reason_code: returnReasonCode as
          | 'EXCESS_UNUSED'
          | 'WRONG_ISSUE'
          | 'DAMAGED_ON_RECEIPT'
          | 'EXPIRED_AT_UNIT'
          | 'UNIT_TRANSFER_CORRECTION'
          | 'OTHER',
        reason_note: returnReasonNote.trim() || undefined,
      });
      setFlashMessage('Return request submitted to store for review.');
      setSelectedReturnVoucher(null);
      await loadDashboard('refresh');
    } catch (err: any) {
      setFlashMessage(
        err?.response?.data?.detail || 'Return request could not be submitted.'
      );
    } finally {
      setReturnSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-44 animate-pulse rounded-3xl bg-slate-200" />
        <div className="grid gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-40 animate-pulse rounded-3xl bg-slate-200" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <DashboardHero
        title="Pharmacy Dispensing Workspace"
        subtitle={HOSPITAL_NAME}
        workspaceLabel={
          activeUnit
            ? `${activeUnit.name} • Fast, safe, unit-scoped dispensing`
            : 'Assigned prescriptions with readiness, stock, and refill visibility'
        }
        monogram="P"
        variant="calm-light"
        accentLabel="Dispensing Bench"
        rightSlot={
          <>
            <div>
              <span className="font-semibold">Staff:</span>{' '}
              {getDashboardUserDisplayName(dashboardUser)}
            </div>
            <div>
              <span className="font-semibold">Role:</span> Pharmacist
            </div>
            <div>
              <span className="font-semibold">Active Unit:</span>{' '}
              {dashboard?.unit_name || 'No unit selected'}
            </div>
            <div>
              <span className="font-semibold">Last updated:</span>{' '}
              {formatDateTime(dashboard?.overview.last_updated_at)}
            </div>
          </>
        }
        actionsSlot={
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => void loadDashboard('refresh')} isLoading={refreshing}>
              Refresh Workspace
            </Button>
          </div>
        }
      />

      {flashMessage ? (
        <div
          className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700"
          data-testid="pharmacy-workflow-flash"
        >
          {flashMessage}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card title="Active Unit" titleClassName="text-[#1E4B8C]">
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Switch between assigned units
          </label>
          <select
            value={selectedUnitId}
            onChange={(event) => setSelectedUnitId(event.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {assignedUnits.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name}
              </option>
            ))}
          </select>
          <p className="mt-3 text-sm text-slate-600">
            The queue, stock view, alerts, and refills stay strictly scoped to the active dispensing unit.
          </p>
        </Card>

        <Card title="Assigned Units" titleClassName="text-[#1E4B8C]">
          <div className="space-y-2">
            {assignedUnits.map((unit) => {
              const isActive = unit.id === selectedUnitId;
              return (
                <div
                  key={unit.id}
                  className={`flex items-center justify-between rounded-2xl border px-4 py-3 text-sm ${
                    isActive
                      ? 'border-blue-200 bg-blue-50 text-blue-700'
                      : 'border-slate-200 bg-white text-slate-700'
                  }`}
                >
                  <span className="font-medium">{unit.name}</span>
                  <span className="text-xs uppercase tracking-[0.14em]">
                    {isActive ? 'Active' : 'Assigned'}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>

        <Card title="Next Action" titleClassName="text-[#1E4B8C]">
          {dashboard?.next_action ? (
            <div className={`rounded-2xl border px-4 py-4 ${badgeClass(dashboard.next_action.severity)}`}>
              <p className="text-sm font-semibold">{dashboard.next_action.title}</p>
              <p className="mt-2 text-sm">{dashboard.next_action.detail}</p>
            </div>
          ) : (
            <EmptyState
              title="No active blocker"
              detail="This dispensing unit currently has no outstanding next-action prompt."
            />
          )}
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <MetricTile
          label="Assigned Prescriptions"
          value={dashboard?.overview.assigned_prescriptions || 0}
          detail="Open prescriptions owned by this unit"
          onClick={() => setActiveSection('assigned')}
        />
        <MetricTile
          label="Ready to Dispense"
          value={dashboard?.overview.ready_to_dispense || 0}
          detail="Fast lane for cleared prescriptions"
          tone={readyRows.some((row) => row.aging_minutes >= 20) ? 'warning' : 'info'}
          onClick={() => setActiveSection('ready')}
        />
        <MetricTile
          label="Awaiting Payment Clearance"
          value={dashboard?.overview.awaiting_payment_clearance || 0}
          detail="Visible but blocked by cashier state"
          tone="warning"
          onClick={() => setActiveSection('awaiting')}
        />
        <MetricTile
          label="Reassigned"
          value={dashboard?.overview.reassigned || 0}
          detail="Recently routed into this unit"
          tone="info"
          onClick={() => setActiveSection('reassigned')}
        />
        <MetricTile
          label="Out of Stock"
          value={dashboard?.overview.out_of_stock || 0}
          detail="Prescriptions blocked by local stock"
          tone={(dashboard?.overview.out_of_stock || 0) > 0 ? 'critical' : 'neutral'}
          onClick={() => setActiveSection('alerts')}
        />
        <MetricTile
          label="Completed Today"
          value={dashboard?.overview.completed_today || 0}
          detail="Unit throughput for today"
          tone="info"
          onClick={() => setActiveSection('dispensed')}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[280px,minmax(0,1fr)]">
        <aside className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1E4B8C]">
              Dispensing Sections
            </p>
            <h2 className="mt-2 text-lg font-semibold text-slate-900">
              {activeSectionMeta.label}
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              {activeSectionMeta.description}
            </p>
          </div>

          <div className="mt-6 space-y-2">
            {sidebarSections.map((section) => {
              const count =
                section.id === 'alerts'
                  ? dashboard?.alerts.length || 0
                  : section.id === 'refills'
                    ? (dashboard?.refill_requests.length || 0) +
                      (dashboard?.return_requests.length || 0)
                    : section.id === 'activity'
                      ? dashboard?.activity_audit.length || 0
                      : section.id === 'stock'
                        ? dashboard?.local_stock.length || 0
                        : 0;
              return (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                    activeSection === section.id
                      ? 'border-blue-200 bg-blue-50'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-slate-900">
                      {section.label}
                    </span>
                    {count > 0 ? (
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${section.id === 'alerts' ? badgeClass('critical') : badgeClass('info')}`}>
                        {count}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{section.description}</p>
                </button>
              );
            })}
          </div>
        </aside>

        <div className="space-y-6">
          {(activeSection === 'overview' ||
            activeSection === 'assigned' ||
            activeSection === 'ready' ||
            activeSection === 'awaiting' ||
            activeSection === 'reassigned' ||
            activeSection === 'dispensed') && (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Queue Control"
                title={activeSectionMeta.label}
                description={activeSectionMeta.description}
              />

              <Card title="Queue Filters" titleClassName="text-[#1E4B8C]">
                <div className="grid gap-4 lg:grid-cols-3">
                  <Input
                    label="Search queue"
                    value={queueSearch}
                    onChange={(event) => setQueueSearch(event.target.value)}
                    placeholder="Patient, MRN, item, department"
                  />
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-700">
                      Priority
                    </label>
                    <select
                      value={priorityFilter}
                      onChange={(event) => setPriorityFilter(event.target.value)}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value={ALL_FILTER}>All priorities</option>
                      <option value="ROUTINE">Routine</option>
                      <option value="URGENT">Urgent</option>
                      <option value="EMERGENCY">Emergency</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-700">
                      Local stock state
                    </label>
                    <select
                      value={stockFilter}
                      onChange={(event) => setStockFilter(event.target.value)}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value={ALL_FILTER}>All stock states</option>
                      <option value="IN_STOCK">In stock</option>
                      <option value="LOW_STOCK">Low stock</option>
                      <option value="OUT_OF_STOCK">Out of stock</option>
                      <option value="EXPIRED">Expired</option>
                      <option value="UNMAPPED">Unmapped</option>
                    </select>
                  </div>
                </div>
              </Card>

              {activeSection === 'overview' ? (
                <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
                  <QueueTable
                    title="Ready to Dispense"
                    rows={readyRows.slice(0, 8)}
                    emptyTitle="No ready prescriptions"
                    emptyDetail="This unit currently has no prescriptions in the fast dispense lane."
                    onView={(row) => void detailFetch(row, 'detail')}
                    onBench={(row) => void detailFetch(row, 'bench')}
                  />
                  <Card title="Operational Attention" titleClassName="text-[#1E4B8C]">
                    <div className="space-y-4">
                      {dashboard?.alerts.length ? (
                        dashboard.alerts.slice(0, 6).map((alert) => (
                          <div
                            key={alert.id}
                            className={`rounded-2xl border px-4 py-3 ${badgeClass(alert.severity)}`}
                          >
                            <p className="text-sm font-semibold">{alert.title}</p>
                            <p className="mt-2 text-sm">{alert.detail}</p>
                          </div>
                        ))
                      ) : (
                        <EmptyState
                          title="No active alert"
                          detail="This unit has no current stock, delay, or receiving alerts."
                        />
                      )}
                    </div>
                  </Card>
                </div>
              ) : null}

              {activeSection === 'assigned' ? (
                <QueueTable
                  title="Assigned Prescriptions"
                  rows={assignedRows}
                  emptyTitle="No assigned prescriptions"
                  emptyDetail="This dispensing unit has no open assigned prescriptions right now."
                  onView={(row) => void detailFetch(row, 'detail')}
                  onBench={(row) => void detailFetch(row, 'bench')}
                />
              ) : null}

              {activeSection === 'ready' ? (
                <QueueTable
                  title="Ready to Dispense"
                  rows={readyRows}
                  emptyTitle="No ready prescriptions"
                  emptyDetail="No prescriptions are fully cleared for dispense at this moment."
                  onView={(row) => void detailFetch(row, 'detail')}
                  onBench={(row) => void detailFetch(row, 'bench')}
                />
              ) : null}

              {activeSection === 'awaiting' ? (
                <QueueTable
                  title="Awaiting Payment Clearance"
                  rows={awaitingRows}
                  emptyTitle="No blocked prescriptions"
                  emptyDetail="All visible prescriptions are already cleared or resolved."
                  onView={(row) => void detailFetch(row, 'detail')}
                  onBench={(row) => void detailFetch(row, 'bench')}
                />
              ) : null}

              {activeSection === 'reassigned' ? (
                <QueueTable
                  title="Reassigned into This Unit"
                  rows={reassignedRows}
                  emptyTitle="No reassigned prescriptions"
                  emptyDetail="No recent dispensing reassignments are waiting in this unit."
                  onView={(row) => void detailFetch(row, 'detail')}
                  onBench={(row) => void detailFetch(row, 'bench')}
                />
              ) : null}

              {activeSection === 'dispensed' ? (
                <QueueTable
                  title="Dispensed Today"
                  rows={dispensedTodayRows}
                  emptyTitle="No dispensed activity"
                  emptyDetail="This unit has no completed dispensing activity for today."
                  onView={(row) => void detailFetch(row, 'detail')}
                  onBench={(row) => void detailFetch(row, 'bench')}
                />
              ) : null}
            </div>
          )}

          {activeSection === 'stock' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Local Inventory"
                title="Local Stock"
                description="Only the active dispensing unit stock is shown here. Store stock is intentionally excluded."
              />
              <Card title="Unit Stock on Hand" titleClassName="text-[#1E4B8C]">
                {!dashboard?.local_stock.length ? (
                  <EmptyState
                    title="No local stock recorded"
                    detail="This unit has no stock lots on hand yet. Incoming vouchers must be acknowledged before they appear here."
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead className="bg-slate-50">
                        <tr className="text-left text-xs uppercase tracking-[0.12em] text-slate-500">
                          <th className="px-4 py-3">Item</th>
                          <th className="px-4 py-3">Batch</th>
                          <th className="px-4 py-3">Expiry</th>
                          <th className="px-4 py-3">Quantity</th>
                          <th className="px-4 py-3">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 bg-white">
                        {dashboard.local_stock.map((row) => (
                          <tr
                            key={`${row.inventory_item_id}:${row.batch_number}`}
                            data-testid={`pharmacy-stock-row-${row.batch_number}`}
                          >
                            <td className="px-4 py-4">
                              <p className="font-medium text-slate-900">{row.item_name}</p>
                              <p className="mt-1 text-xs text-slate-500">{row.source_label}</p>
                            </td>
                            <td className="px-4 py-4 text-slate-700">{row.batch_number}</td>
                            <td className="px-4 py-4 text-slate-700">{formatDateOnly(row.expiry_date)}</td>
                            <td className="px-4 py-4 text-slate-700">{row.quantity_on_hand}</td>
                            <td className="px-4 py-4">
                              <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusChip(row.stock_status)}`}>
                                {workflowLabel(row.stock_status)}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </div>
          ) : null}

          {activeSection === 'refills' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Replenishment"
                title="Refill Requests"
                description="Create refill requests for this unit, trace CMD approval and store preparation, acknowledge incoming dispatched supply, and initiate linked returns to store."
              />

              <div className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
                <Card title="Create Refill Request" titleClassName="text-[#1E4B8C]">
                  <div className="grid gap-4">
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">
                        Item
                      </label>
                      <select
                        value={refillItemId}
                        onChange={(event) => setRefillItemId(event.target.value)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        {refillInventoryOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <Input
                      label="Requested quantity"
                      type="number"
                      min="1"
                      value={refillQuantity}
                      onChange={(event) => setRefillQuantity(event.target.value)}
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">
                        Priority
                      </label>
                      <select
                        value={refillPriority}
                        onChange={(event) => setRefillPriority(event.target.value)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="ROUTINE">Routine</option>
                        <option value="URGENT">Urgent</option>
                        <option value="EMERGENCY">Emergency</option>
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">
                        Reason
                      </label>
                      <textarea
                        value={refillNote}
                        onChange={(event) => setRefillNote(event.target.value)}
                        rows={4}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Explain why this refill is needed for the active unit."
                      />
                    </div>
                    <Button
                      variant="primary"
                      onClick={() => void handleRefillSubmit()}
                      isLoading={refillSubmitting}
                    >
                      Submit Refill Request
                    </Button>
                  </div>
                </Card>

                <Card title="Request Tracker" titleClassName="text-[#1E4B8C]">
                  <div className="mb-4">
                    <label className="mb-1 block text-sm font-medium text-slate-700">
                      Status
                    </label>
                    <select
                      value={refillStatusFilter}
                      onChange={(event) => setRefillStatusFilter(event.target.value)}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value={ALL_FILTER}>All statuses</option>
                      <option value="AWAITING_CMD_APPROVAL">Awaiting CMD approval</option>
                      <option value="APPROVED">Approved</option>
                      <option value="ISSUE_PREPARATION_IN_PROGRESS">Store preparing</option>
                      <option value="BACKORDER_PENDING">Backorder pending</option>
                      <option value="PARTIALLY_ISSUED">Partially issued</option>
                      <option value="DISPATCHED">Dispatched</option>
                      <option value="ACKNOWLEDGED">Acknowledged</option>
                      <option value="CLOSED">Closed</option>
                      <option value="PARTIALLY_RECEIVED">Partially received</option>
                      <option value="RECEIVED">Received</option>
                    </select>
                  </div>
                  {!refillRequests.length ? (
                    <EmptyState
                      title="No refill requests"
                      detail="This unit has not submitted any refill requests in the current view."
                    />
                  ) : (
                    <div className="space-y-3">
                      {refillRequests.map((request) => (
                        <div key={request.id} className="rounded-2xl border border-slate-200 p-4">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <p className="font-medium text-slate-900">
                                {request.requesting_unit_name}
                              </p>
                              <p className="mt-1 text-sm text-slate-600">
                                {workflowLabel(request.request_type)} • Submitted {formatDateTime(request.requested_at)}
                              </p>
                            </div>
                            <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusChip(request.status)}`}>
                              {workflowLabel(request.status)}
                            </span>
                          </div>
                          <div className="mt-3 space-y-2 text-sm text-slate-600">
                            {request.items.map((item) => (
                              <p key={item.id}>
                                {item.inventory_item_name}: requested {item.requested_quantity}, approved {item.approved_quantity ?? 0}, received {item.received_quantity}
                              </p>
                            ))}
                          </div>
                          {request.requester_timeline.length ? (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {request.requester_timeline.map((step) => (
                                <span
                                  key={`${request.id}-${step}`}
                                  className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700"
                                >
                                  {step}
                                </span>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>

              <Card title="Incoming Supply Awaiting Acknowledgement" titleClassName="text-[#1E4B8C]">
                {!incomingVouchers.length ? (
                  <EmptyState
                    title="No incoming supply"
                    detail="There are no outstanding issue vouchers awaiting acknowledgement for this unit."
                  />
                ) : (
                  <div className="space-y-3">
                    {incomingVouchers.map((voucher) => (
                      <div key={voucher.id} className="rounded-2xl border border-slate-200 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className="font-medium text-slate-900">{voucher.voucher_number}</p>
                            <p className="mt-1 text-sm text-slate-600">
                              Issued {formatDateTime(voucher.issued_at)} • {voucher.store_unit_name}
                            </p>
                          </div>
                          <Button size="sm" variant="primary" onClick={() => openVoucher(voucher)}>
                            Acknowledge Receipt
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              <div className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
                <Card title="Return to Store" titleClassName="text-[#1E4B8C]">
                  {!returnableVouchers.length ? (
                    <EmptyState
                      title="No acknowledged supply eligible for return"
                      detail="Return-to-store starts from previously acknowledged issue vouchers."
                    />
                  ) : (
                    <div className="space-y-3">
                      {returnableVouchers.map((voucher) => (
                        <div
                          key={`returnable-${voucher.id}`}
                          className="rounded-2xl border border-slate-200 p-4"
                          data-testid="returnable-voucher-card"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <p className="font-medium text-slate-900">{voucher.voucher_number}</p>
                              <p className="mt-1 text-sm text-slate-600">
                                Received from {voucher.store_unit_name} • {formatDateTime(voucher.acknowledged_at || voucher.issued_at)}
                              </p>
                              <p className="mt-2 text-xs text-slate-500">
                                {voucher.items
                                  .filter((item) => item.received_quantity > 0)
                                  .map(
                                    (item) =>
                                      `${item.inventory_item_name}: ${item.received_quantity} acknowledged`
                                  )
                                  .join(' • ')}
                              </p>
                            </div>
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => openReturnVoucher(voucher)}
                              data-testid="return-to-store-trigger"
                            >
                              Return to Store
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                <Card title="Return Tracker" titleClassName="text-[#1E4B8C]">
                  {!returnRequests.length ? (
                    <EmptyState
                      title="No return requests submitted"
                      detail="Submitted returns will appear here with store review and receipt status."
                    />
                  ) : (
                    <div className="space-y-3">
                      {returnRequests.map((request: PharmacyReturnRequestResponse) => (
                        <div key={request.id} className="rounded-2xl border border-slate-200 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <p className="font-medium text-slate-900">
                                {request.return_number} • {request.inventory_item_name}
                              </p>
                              <p className="mt-1 text-sm text-slate-600">
                                {request.issue_voucher_number} • {request.quantity_now_returned} requested • {workflowLabel(request.reason_code)}
                              </p>
                            </div>
                            <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusChip(request.status)}`}>
                              {workflowLabel(request.status)}
                            </span>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {request.return_timeline.map((step) => (
                              <span
                                key={`${request.id}-${step}`}
                                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700"
                              >
                                {step}
                              </span>
                            ))}
                          </div>
                          <p className="mt-3 text-xs text-slate-500">
                            Submitted {formatDateTime(request.requested_at)}
                            {request.received_at ? ` • Received ${formatDateTime(request.received_at)}` : ''}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            </div>
          ) : null}

          {activeSection === 'alerts' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Operational Attention"
                title="Alerts"
                description="Delays, stock blockers, expiry issues, and receiving items needing immediate awareness."
              />
              {!dashboard?.alerts.length ? (
                <EmptyState
                  title="No alerts"
                  detail="This unit currently has no active dispensing alerts."
                />
              ) : (
                <div className="space-y-3">
                  {dashboard.alerts.map((alert: PharmacyDispensingAlertRow) => (
                    <div
                      key={alert.id}
                      className={`rounded-2xl border px-4 py-4 ${badgeClass(alert.severity)}`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold">{alert.title}</p>
                          <p className="mt-2 text-sm">{alert.detail}</p>
                        </div>
                        <span className="text-xs font-semibold uppercase tracking-[0.14em]">
                          {workflowLabel(alert.alert_type)}
                        </span>
                      </div>
                      <p className="mt-3 text-xs">
                        {formatDateTime(alert.occurred_at)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : null}

          {activeSection === 'activity' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Traceability"
                title="Activity Audit"
                description="Readable unit-level events for dispensing, refill, reassignment, and incoming stock."
              />
              <Card title="Recent Activity" titleClassName="text-[#1E4B8C]">
                <Input
                  label="Search activity"
                  value={auditSearch}
                  onChange={(event) => setAuditSearch(event.target.value)}
                  placeholder="Item, patient, or action"
                />
                <div className="mt-4 space-y-3">
                  {(dashboard?.activity_audit || [])
                    .filter((row: PharmacyDispensingActivityRow) => {
                      const normalized = auditSearch.trim().toLowerCase();
                      if (!normalized) return true;
                      return [
                        row.summary,
                        row.detail,
                        row.patient_name,
                        row.patient_mrn,
                        row.item_name,
                        row.action_type,
                      ]
                        .filter(Boolean)
                        .some((value) => value!.toLowerCase().includes(normalized));
                    })
                    .map((row) => (
                      <div
                        key={row.id}
                        className={`rounded-2xl border px-4 py-4 ${badgeClass(row.severity)}`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="font-semibold text-slate-900">{row.summary}</p>
                          <span className="text-xs uppercase tracking-[0.14em] text-slate-500">
                            {workflowLabel(row.action_type)}
                          </span>
                        </div>
                        {row.detail ? (
                          <p className="mt-2 text-sm text-slate-700">{row.detail}</p>
                        ) : null}
                        <p className="mt-3 text-xs text-slate-500">
                          {formatDateTime(row.occurred_at)}
                          {row.actor_name ? ` • ${row.actor_name}` : ''}
                        </p>
                      </div>
                    ))}
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      </div>

      {detailLoadingId ? (
        <div className="fixed bottom-6 right-6 rounded-full border border-blue-200 bg-white px-4 py-2 text-sm text-blue-700 shadow-lg">
          Loading prescription detail...
        </div>
      ) : null}

      {selectedPrescription ? (
        <PrescriptionDetailsModal
          prescription={selectedPrescription}
          unitId={selectedUnitId || undefined}
          isOpen={detailsOpen}
          onClose={() => {
            setDetailsOpen(false);
            setSelectedPrescription(null);
          }}
          onDispense={(prescription) => {
            setDetailsOpen(false);
            setSelectedPrescription(prescription);
            setBenchOpen(true);
          }}
          onRefresh={(prescription) => setSelectedPrescription(prescription)}
        />
      ) : null}

      {benchOpen && selectedPrescription ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
          <div className="max-h-[94vh] w-full max-w-5xl overflow-y-auto rounded-3xl bg-white shadow-2xl">
            <div className="border-b border-slate-200 px-6 py-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1E4B8C]">
                    Dispense Bench
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                    {selectedPrescription.drug_name}
                  </h2>
                  <p className="mt-2 text-sm text-slate-600">
                    {selectedPrescription.patient_name || 'Unknown patient'}
                    {selectedPrescription.patient_mrn
                      ? ` • MRN ${selectedPrescription.patient_mrn}`
                      : ''}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setBenchOpen(false);
                    setSelectedPrescription(null);
                  }}
                  className="rounded-full border border-slate-200 px-3 py-1 text-sm text-slate-500 hover:bg-slate-50"
                >
                  Close
                </button>
              </div>
            </div>
            <div className="px-6 py-6">
              <DispenseForm
                prescription={selectedPrescription}
                pharmacistId={dashboardUser?.id || ''}
                unitId={selectedUnitId || undefined}
                onSuccess={(message) => void handleWorkflowSuccess(message)}
                onCancel={() => {
                  setBenchOpen(false);
                  setSelectedPrescription(null);
                }}
              />
            </div>
          </div>
        </div>
      ) : null}

      {selectedReturnVoucher ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
          <div className="w-full max-w-3xl rounded-3xl bg-white shadow-2xl">
            <div className="border-b border-slate-200 px-6 py-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1E4B8C]">
                    Return to Store
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                    {selectedReturnVoucher.voucher_number}
                  </h2>
                  <p className="mt-2 text-sm text-slate-600">
                    {selectedReturnVoucher.receiving_unit_name} → {selectedReturnVoucher.store_unit_name}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedReturnVoucher(null)}
                  className="rounded-full border border-slate-200 px-3 py-1 text-sm text-slate-500 hover:bg-slate-50"
                >
                  Close
                </button>
              </div>
            </div>
            <div className="space-y-4 px-6 py-6">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Issued Line
                </label>
                <select
                  value={selectedReturnVoucherItemId}
                  onChange={(event) => setSelectedReturnVoucherItemId(event.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {selectedReturnVoucher.items
                    .filter((item) => item.received_quantity > 0)
                    .map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.inventory_item_name} • Batch {item.batch_number} • Received {item.received_quantity}
                      </option>
                    ))}
                </select>
                {selectedReturnVoucherItemId ? (
                  <p className="mt-2 text-xs text-slate-500">
                    {(() => {
                      const selectedItem = selectedReturnVoucher.items.find(
                        (item) => item.id === selectedReturnVoucherItemId
                      );
                      const alreadyReturned = returnRequests
                        .filter(
                          (request) =>
                            request.issue_voucher_item_id === selectedReturnVoucherItemId &&
                            request.status !== 'RETURN_REJECTED'
                        )
                        .reduce(
                          (total, request) => total + request.quantity_now_returned,
                          0
                        );
                      return selectedItem
                        ? `Acknowledged ${selectedItem.received_quantity} • Already requested for return ${alreadyReturned}`
                        : '';
                    })()}
                  </p>
                ) : null}
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Input
                  label="Quantity to Return"
                  type="number"
                  min="1"
                  value={returnQuantity}
                  onChange={(event) => setReturnQuantity(event.target.value)}
                />
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Reason Code
                  </label>
                  <select
                    value={returnReasonCode}
                    onChange={(event) => setReturnReasonCode(event.target.value)}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="EXCESS_UNUSED">Excess Unused</option>
                    <option value="WRONG_ISSUE">Wrong Issue</option>
                    <option value="DAMAGED_ON_RECEIPT">Damaged On Receipt</option>
                    <option value="EXPIRED_AT_UNIT">Expired At Unit</option>
                    <option value="UNIT_TRANSFER_CORRECTION">Unit Transfer Correction</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
              </div>
              <div>
                <label
                  htmlFor="return-reason-note"
                  className="mb-1 block text-sm font-medium text-slate-700"
                >
                  Return Note
                </label>
                <textarea
                  id="return-reason-note"
                  value={returnReasonNote}
                  onChange={(event) => setReturnReasonNote(event.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Explain why this issued stock is being returned."
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4">
              <Button variant="secondary" onClick={() => setSelectedReturnVoucher(null)} disabled={returnSubmitting}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => void submitReturnRequest()} isLoading={returnSubmitting}>
                Submit Return Request
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {selectedVoucher ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
          <div className="w-full max-w-3xl rounded-3xl bg-white shadow-2xl">
            <div className="border-b border-slate-200 px-6 py-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1E4B8C]">
                    Incoming Stock
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                    {selectedVoucher.voucher_number}
                  </h2>
                  <p className="mt-2 text-sm text-slate-600">
                    {selectedVoucher.store_unit_name} → {selectedVoucher.receiving_unit_name}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedVoucher(null)}
                  className="rounded-full border border-slate-200 px-3 py-1 text-sm text-slate-500 hover:bg-slate-50"
                >
                  Close
                </button>
              </div>
            </div>
            <div className="space-y-4 px-6 py-6">
              {selectedVoucher.items.map((item) => (
                <div key={item.id} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-slate-900">{item.inventory_item_name}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        Batch {item.batch_number} • Exp {formatDateOnly(item.expiry_date)}
                      </p>
                    </div>
                    <div className="w-36">
                      <Input
                        label="Received qty"
                        type="number"
                        min="0"
                        max={item.issued_quantity - item.received_quantity}
                        value={voucherDraft[item.id] || '0'}
                        onChange={(event) =>
                          setVoucherDraft((current) => ({
                            ...current,
                            [item.id]: event.target.value,
                          }))
                        }
                      />
                    </div>
                  </div>
                </div>
              ))}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Receipt note
                </label>
                <textarea
                  value={voucherNote}
                  onChange={(event) => setVoucherNote(event.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Record any discrepancy or unit note."
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4">
              <Button variant="secondary" onClick={() => setSelectedVoucher(null)} disabled={voucherSubmitting}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => void acknowledgeVoucher()} isLoading={voucherSubmitting}>
                Acknowledge Receipt
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
