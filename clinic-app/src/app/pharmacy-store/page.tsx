'use client';

import { useCallback, useEffect, useId, useMemo, useState } from 'react';
import { DashboardHero } from '@/app/components/DashboardHero';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';
import { useEventStreamSnapshot } from '@/shared/hooks/useEventStreamSnapshot';
import { HOSPITAL_NAME } from '@/shared/constants/branding';
import { UserRole } from '@/shared/enums';
import {
  pharmacyStoreService,
  type PharmacyStoreActivityRow,
  type PharmacyStoreAdjustmentPayload,
  type PharmacyStoreApprovedRequestRow,
  type PharmacyStoreDashboardResponse,
  type PharmacyStoreInventoryRow,
  type PharmacyStoreIssueVoucherCreatePayload,
  type PharmacyStoreIssueVoucherRow,
  type PharmacyStoreMovementRow,
  type PharmacyStoreReturnRequestRow,
} from '@/domains/pharmacy/services/pharmacyStoreService';

const sidebarSections = [
  { id: 'overview', label: 'Overview', description: 'Central supply control room' },
  { id: 'inventory', label: 'Inventory', description: 'Classification-aware central stock visibility' },
  { id: 'department-requests', label: 'Department Requests', description: 'Requester demand and CMD approval visibility' },
  { id: 'approved', label: 'Approved Requests', description: 'Execute CMD-approved supply requests' },
  { id: 'vouchers', label: 'Issue Vouchers', description: 'Document layer for prepared store release' },
  { id: 'dispatch', label: 'Issue & Dispatch', description: 'Execution layer for prepared voucher release' },
  { id: 'receiving', label: 'Receiving & Acknowledgement', description: 'Dispatched supply acknowledgements and controlled unit returns' },
  { id: 'movements', label: 'Movement History', description: 'Audited stock movement ledger' },
  { id: 'expiry', label: 'Stock Risk & Expiry', description: 'Risk-driven store action surface' },
  { id: 'adjustments', label: 'Adjustments & Reconciliation', description: 'Controlled store corrections' },
  { id: 'activity', label: 'Activity Audit', description: 'Human-readable operational traceability' },
  { id: 'reports', label: 'Reports & Analytics', description: 'Consumption, backorder, and supply trends' },
] as const;

type SidebarSectionId = (typeof sidebarSections)[number]['id'];
type SelectOption = { value: string; label: string };
type IssueDraftEntry = {
  refillRequestItemId: string;
  inventoryItemId: string;
  issuedQuantity: string;
  batchNumber: string;
  expiryDate: string;
};

const ALL_FILTER = 'ALL';

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function formatDateTime(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleString();
}

function formatDateOnly(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleDateString();
}

function formatMoney(minor: number, currency: string) {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(minor / 100);
}

function formatDelta(value: number) {
  return `${value > 0 ? '+' : ''}${value}`;
}

function roleLabel(role?: string | null) {
  switch (role) {
    case UserRole.PHARMACY_STORE_OFFICER:
      return 'Pharmacy Store Officer';
    case UserRole.PHARMACY_HOD:
      return 'Pharmacy HOD';
    case UserRole.PHARMACY:
      return 'Pharmacist';
    default:
      return 'Pharmacy Store Officer';
  }
}

function workflowLabel(value: string) {
  return value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function buildOptions(values: Array<string | null | undefined>, labeler: (value: string) => string = (value) => value): SelectOption[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value))))
    .sort((left, right) => left.localeCompare(right))
    .map((value) => ({ value, label: labeler(value) }));
}

function matchesSelect(value: string | null | undefined, filter: string) {
  return filter === ALL_FILTER || value === filter;
}

function matchesSearch(values: Array<string | null | undefined>, term: string) {
  const normalized = term.trim().toLowerCase();
  if (!normalized) return true;
  return values.some((value) => value?.toLowerCase().includes(normalized));
}

function badgeClass(tone: 'info' | 'warning' | 'critical') {
  if (tone === 'critical') return 'border border-red-200 bg-red-50 text-red-700';
  if (tone === 'warning') return 'border border-amber-200 bg-amber-50 text-amber-700';
  return 'border border-blue-200 bg-blue-50 text-blue-700';
}

function statusClass(status: string) {
  if (status.includes('BACKORDER') || status.includes('REJECTED') || status === 'EXPIRED' || status === 'OUT_OF_STOCK') {
    return 'border border-red-200 bg-red-50 text-red-700';
  }
  if (status.includes('PARTIAL') || status.includes('LOW') || status.includes('EXPIR') || status.includes('AWAITING') || status.includes('PENDING') || status.includes('ACCEPTED')) {
    return 'border border-amber-200 bg-amber-50 text-amber-700';
  }
  if (status === 'ACKNOWLEDGED' || status === 'CLOSED' || status.includes('RECEIVED')) {
    return 'border border-emerald-200 bg-emerald-50 text-emerald-700';
  }
  return 'border border-blue-200 bg-blue-50 text-blue-700';
}

function sectionBadgeCount(sectionId: SidebarSectionId, dashboard: PharmacyStoreDashboardResponse | null) {
  if (!dashboard) return 0;
  switch (sectionId) {
    case 'department-requests':
      return dashboard.department_requests.length;
    case 'approved':
      return dashboard.approved_requests.length;
    case 'vouchers':
      return dashboard.issue_vouchers.length;
    case 'dispatch':
      return dashboard.issue_vouchers.filter((row) => ['PREPARED', 'ISSUED'].includes(row.status)).length;
    case 'receiving':
      return dashboard.dispatch_receiving.length + dashboard.return_requests.length;
    case 'expiry':
      return dashboard.expiry_low_stock.length;
    default:
      return 0;
  }
}

function sectionBadgeTone(sectionId: SidebarSectionId): 'info' | 'warning' | 'critical' {
  switch (sectionId) {
    case 'expiry':
      return 'critical';
    case 'department-requests':
    case 'approved':
    case 'dispatch':
    case 'receiving':
      return 'warning';
    default:
      return 'info';
  }
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
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1E4B8C]">{eyebrow}</p>
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
}: {
  label: string;
  value: string | number;
  detail?: string;
  tone?: 'neutral' | 'warning' | 'critical' | 'info';
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
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-slate-900">{value}</p>
      {detail ? <p className="mt-2 text-sm text-slate-600">{detail}</p> : null}
    </div>
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

function SelectField({
  label,
  value,
  onChange,
  options,
  disabled = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <div className="w-full">
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-gray-700">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const id = useId();
  return (
    <div className="w-full">
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-gray-700">
        {label}
      </label>
      <textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="min-h-[88px] w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}

function DataTable({ children }: { children: React.ReactNode }) {
  return <div className="overflow-x-auto">{children}</div>;
}

export default function PharmacyStorePage() {
  const dashboardUser = useDashboardUser();
  const [dashboard, setDashboard] = useState<PharmacyStoreDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<SidebarSectionId>('overview');
  const [startDate, setStartDate] = useState(todayIsoDate());
  const [endDate, setEndDate] = useState(todayIsoDate());
  const [storeUnitFilter, setStoreUnitFilter] = useState('');
  const [inventorySearch, setInventorySearch] = useState('');
  const [inventoryStatusFilter, setInventoryStatusFilter] = useState(ALL_FILTER);
  const [requestSearch, setRequestSearch] = useState('');
  const [movementTypeFilter, setMovementTypeFilter] = useState(ALL_FILTER);
  const [auditSearch, setAuditSearch] = useState('');
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [issueNote, setIssueNote] = useState('');
  const [issueDraft, setIssueDraft] = useState<Record<string, IssueDraftEntry>>({});

  const [receiveItemId, setReceiveItemId] = useState('');
  const [receiveBatchNumber, setReceiveBatchNumber] = useState('');
  const [receiveExpiryDate, setReceiveExpiryDate] = useState('');
  const [receiveQuantity, setReceiveQuantity] = useState('0');
  const [receiveNote, setReceiveNote] = useState('');
  const [receiveSubmitting, setReceiveSubmitting] = useState(false);

  const [adjustItemId, setAdjustItemId] = useState('');
  const [adjustBatchNumber, setAdjustBatchNumber] = useState('');
  const [adjustExpiryDate, setAdjustExpiryDate] = useState('');
  const [adjustDelta, setAdjustDelta] = useState('0');
  const [adjustReason, setAdjustReason] = useState('');
  const [adjustSubmitting, setAdjustSubmitting] = useState(false);
  const [issueSubmitting, setIssueSubmitting] = useState(false);
  const [dispatchingVoucherId, setDispatchingVoucherId] = useState<string | null>(null);
  const [selectedReturnRequestId, setSelectedReturnRequestId] = useState<string | null>(null);
  const [returnReviewNote, setReturnReviewNote] = useState('');
  const [returnReceiveNote, setReturnReceiveNote] = useState('');
  const [returnReviewSubmitting, setReturnReviewSubmitting] = useState(false);
  const [returnReceiveSubmitting, setReturnReceiveSubmitting] = useState(false);

  const loadDashboard = useCallback(
    async (silent = false) => {
      try {
        if (silent) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }
        const response = await pharmacyStoreService.getDashboard({
          start_date: startDate,
          end_date: endDate,
          store_unit_id: storeUnitFilter || undefined,
        });
        setDashboard(response);
        if (!storeUnitFilter) {
          setStoreUnitFilter(response.store_unit_id);
        }
        setError(null);
      } catch (requestError) {
        console.error('Failed to load pharmacy store dashboard', requestError);
        setError('Unable to load the pharmacy store dashboard.');
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [endDate, startDate, storeUnitFilter]
  );

  const dashboardStreamUrl = useMemo(
    () =>
      pharmacyStoreService.getDashboardStreamUrl({
        start_date: startDate,
        end_date: endDate,
        store_unit_id: storeUnitFilter || undefined,
      }),
    [endDate, startDate, storeUnitFilter]
  );
  const { snapshot: liveDashboardSnapshot, error: liveDashboardError } =
    useEventStreamSnapshot<PharmacyStoreDashboardResponse>({
      enabled: Boolean(dashboardUser),
      url: dashboardStreamUrl,
      eventName: 'pharmacy_store_dashboard_snapshot',
      errorMessage: 'Live pharmacy store updates are temporarily unavailable.',
    });

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!liveDashboardSnapshot) {
      return;
    }
    setDashboard(liveDashboardSnapshot);
    if (!storeUnitFilter) {
      setStoreUnitFilter(liveDashboardSnapshot.store_unit_id);
    }
    setError(null);
    setLoading(false);
    setRefreshing(false);
  }, [liveDashboardSnapshot, storeUnitFilter]);

  useEffect(() => {
    if (!liveDashboardError) {
      return;
    }
    setError((current) => current ?? liveDashboardError);
  }, [liveDashboardError]);

  const uniqueInventoryItems = useMemo(() => {
    const seen = new Map<string, PharmacyStoreInventoryRow>();
    for (const row of dashboard?.inventory || []) {
      if (!seen.has(row.inventory_item_id)) {
        seen.set(row.inventory_item_id, row);
      }
    }
    return Array.from(seen.values());
  }, [dashboard?.inventory]);

  const itemOptions = useMemo<SelectOption[]>(
    () => [
      { value: '', label: 'Select item' },
      ...uniqueInventoryItems.map((row) => ({
        value: row.inventory_item_id,
        label: `${row.item_name}${row.strength ? ` ${row.strength}` : ''}`,
      })),
    ],
    [uniqueInventoryItems]
  );

  const requestOptions = useMemo<SelectOption[]>(
    () => [
      { value: '', label: 'Select approved request' },
      ...(dashboard?.approved_requests || []).map((row) => ({
        value: row.request_id,
        label: `${row.request_number} • ${row.requesting_unit_name}`,
      })),
    ],
    [dashboard?.approved_requests]
  );

  const selectedRequest = useMemo<PharmacyStoreApprovedRequestRow | null>(
    () =>
      dashboard?.approved_requests.find((request) => request.request_id === selectedRequestId) ||
      null,
    [dashboard?.approved_requests, selectedRequestId]
  );

  useEffect(() => {
    if (!selectedRequest) {
      setIssueDraft({});
      return;
    }
    const nextDraft: Record<string, IssueDraftEntry> = {};
    for (const item of selectedRequest.items) {
      const batchCandidates = (dashboard?.inventory || [])
        .filter(
          (row) =>
            row.inventory_item_id === item.inventory_item_id &&
            row.can_issue &&
            row.quantity_on_hand > 0
        )
        .sort((left, right) => {
          const leftExpiry = left.expiry_date || '9999-12-31';
          const rightExpiry = right.expiry_date || '9999-12-31';
          return leftExpiry.localeCompare(rightExpiry);
        });
      const batch = batchCandidates[0];
      nextDraft[item.refill_request_item_id] = {
        refillRequestItemId: item.refill_request_item_id,
        inventoryItemId: item.inventory_item_id,
        issuedQuantity: String(
          Math.max(Math.min(item.reserved_quantity, batch?.quantity_on_hand || item.reserved_quantity), 0)
        ),
        batchNumber: batch?.batch_number || '',
        expiryDate: batch?.expiry_date || '',
      };
    }
    setIssueDraft(nextDraft);
  }, [dashboard?.inventory, selectedRequest]);

  const inventoryRows = useMemo(() => {
    return (dashboard?.inventory || []).filter((row) => {
      return (
        matchesSearch(
          [row.item_name, row.strength, row.batch_number, row.stock_status],
          inventorySearch
        ) && matchesSelect(row.stock_status, inventoryStatusFilter)
      );
    });
  }, [dashboard?.inventory, inventorySearch, inventoryStatusFilter]);

  const approvedRequests = useMemo(() => {
    return (dashboard?.approved_requests || []).filter(
      (row) =>
        !['DISPATCHED', 'ACKNOWLEDGED', 'CLOSED', 'REJECTED'].includes(row.status) &&
        matchesSearch([row.request_number, row.requesting_unit_name, row.priority, row.status], requestSearch)
    );
  }, [dashboard?.approved_requests, requestSearch]);

  const departmentRequests = useMemo(() => {
    return (dashboard?.department_requests || []).filter((row) =>
      matchesSearch(
        [row.request_number, row.requesting_unit_name, row.priority, row.status, row.request_type],
        requestSearch
      )
    );
  }, [dashboard?.department_requests, requestSearch]);

  const dispatchQueue = useMemo(
    () =>
      (dashboard?.issue_vouchers || []).filter((voucher) =>
        ['PREPARED', 'ISSUED'].includes(voucher.status)
      ),
    [dashboard?.issue_vouchers]
  );

  const receivingQueue = useMemo(() => dashboard?.dispatch_receiving || [], [dashboard?.dispatch_receiving]);
  const returnRequests = useMemo(
    () => dashboard?.return_requests || [],
    [dashboard?.return_requests]
  );
  const selectedReturnRequest = useMemo<PharmacyStoreReturnRequestRow | null>(
    () =>
      returnRequests.find((request) => request.id === selectedReturnRequestId) || null,
    [returnRequests, selectedReturnRequestId]
  );

  const movementRows = useMemo(() => {
    return (dashboard?.movement_history || []).filter(
      (row) =>
        matchesSelect(row.movement_type, movementTypeFilter) &&
        matchesSearch([row.item_name, row.reference_number, row.destination_label], auditSearch)
    );
  }, [dashboard?.movement_history, movementTypeFilter, auditSearch]);

  const activityRows = useMemo(() => {
    return (dashboard?.activity_audit || []).filter((row) =>
      matchesSearch([row.summary, row.detail, row.item_name, row.unit_name, row.actor_name], auditSearch)
    );
  }, [dashboard?.activity_audit, auditSearch]);

  const movementTypeOptions = useMemo<SelectOption[]>(
    () => [{ value: ALL_FILTER, label: 'All movement types' }, ...buildOptions((dashboard?.movement_history || []).map((row) => row.movement_type))],
    [dashboard?.movement_history]
  );

  const inventoryStatusOptions = useMemo<SelectOption[]>(
    () => [{ value: ALL_FILTER, label: 'All stock states' }, ...buildOptions((dashboard?.inventory || []).map((row) => row.stock_status))],
    [dashboard?.inventory]
  );

  const selectedAdjustBatchOptions = useMemo<SelectOption[]>(() => {
    if (!adjustItemId) {
      return [{ value: '', label: 'Select batch' }];
    }
    return [
      { value: '', label: 'Select batch' },
      ...(dashboard?.inventory || [])
        .filter((row) => row.inventory_item_id === adjustItemId && row.batch_number)
        .map((row) => ({
          value: row.batch_number || '',
          label: `${row.batch_number} • ${row.quantity_on_hand} on hand${row.expiry_date ? ` • exp ${formatDateOnly(row.expiry_date)}` : ''}`,
        })),
    ];
  }, [adjustItemId, dashboard?.inventory]);

  useEffect(() => {
    if (!adjustItemId || !adjustBatchNumber) return;
    const batch = (dashboard?.inventory || []).find(
      (row) => row.inventory_item_id === adjustItemId && row.batch_number === adjustBatchNumber
    );
    setAdjustExpiryDate(batch?.expiry_date || '');
  }, [adjustBatchNumber, adjustItemId, dashboard?.inventory]);

  const commandStrip: Array<{
    label: string;
    value: number;
    tone: 'info' | 'warning' | 'critical';
  }> = dashboard
    ? [
        {
          label: 'Pending Approved Requests',
          value: dashboard.overview.pending_approved_requests,
          tone: dashboard.overview.pending_approved_requests > 0 ? 'warning' : 'info',
        },
        {
          label: 'Items Awaiting Issue',
          value: dashboard.overview.items_awaiting_issue,
          tone: dashboard.overview.items_awaiting_issue > 0 ? 'warning' : 'info',
        },
        {
          label: 'Receiving Pending',
          value:
            dashboard.overview.pending_receiving_acknowledgements +
            dashboard.overview.pending_return_reviews,
          tone:
            dashboard.overview.pending_receiving_acknowledgements > 0 ||
            dashboard.overview.pending_return_reviews > 0
              ? 'warning'
              : 'info',
        },
        {
          label: 'Pending Returns',
          value: dashboard.overview.pending_return_reviews,
          tone: dashboard.overview.pending_return_reviews > 0 ? 'warning' : 'info',
        },
        {
          label: 'Low Stock',
          value: dashboard.overview.low_stock_items,
          tone: dashboard.overview.low_stock_items > 0 ? 'critical' : 'info',
        },
        {
          label: 'Expiry Alerts',
          value: dashboard.overview.expiring_soon_items,
          tone: dashboard.overview.expiring_soon_items > 0 ? 'critical' : 'info',
        },
      ]
    : [];

  const storeUnits = useMemo<SelectOption[]>(
    () =>
      dashboard
        ? [{ value: dashboard.store_unit_id, label: dashboard.store_unit_name }]
        : [{ value: '', label: 'Store unit' }],
    [dashboard]
  );

  async function handleReceiveStock() {
    if (!dashboard || !receiveItemId) {
      setError('Select an item to receive into store.');
      return;
    }
    const quantityReceived = Number(receiveQuantity);
    if (!Number.isFinite(quantityReceived) || quantityReceived <= 0) {
      setError('Enter a valid quantity to receive.');
      return;
    }
    try {
      setReceiveSubmitting(true);
      await pharmacyStoreService.receiveStock({
        store_unit_id: dashboard.store_unit_id,
        inventory_item_id: receiveItemId,
        batch_number: receiveBatchNumber.trim(),
        expiry_date: receiveExpiryDate || null,
        quantity_received: quantityReceived,
        source_reference_note: receiveNote.trim() || null,
      });
      setFlashMessage('Store stock received successfully.');
      setReceiveBatchNumber('');
      setReceiveExpiryDate('');
      setReceiveQuantity('0');
      setReceiveNote('');
      await loadDashboard(true);
    } catch (requestError) {
      console.error(requestError);
      setError('Failed to receive stock into the store.');
    } finally {
      setReceiveSubmitting(false);
    }
  }

  async function handleAdjustment() {
    if (!dashboard || !adjustItemId) {
      setError('Select an item before recording an adjustment.');
      return;
    }
    const quantityDelta = Number(adjustDelta);
    if (!Number.isFinite(quantityDelta) || quantityDelta === 0) {
      setError('Enter a non-zero adjustment value.');
      return;
    }
    if (!adjustReason.trim()) {
      setError('Provide an adjustment reason.');
      return;
    }
    try {
      setAdjustSubmitting(true);
      const payload: PharmacyStoreAdjustmentPayload = {
        store_unit_id: dashboard.store_unit_id,
        inventory_item_id: adjustItemId,
        batch_number: adjustBatchNumber || null,
        expiry_date: adjustExpiryDate || null,
        quantity_delta: quantityDelta,
        reason: adjustReason.trim(),
      };
      await pharmacyStoreService.createAdjustment(payload);
      setFlashMessage('Store adjustment recorded.');
      setAdjustDelta('0');
      setAdjustReason('');
      setAdjustBatchNumber('');
      setAdjustExpiryDate('');
      await loadDashboard(true);
    } catch (requestError) {
      console.error(requestError);
      setError('Failed to record the store adjustment.');
    } finally {
      setAdjustSubmitting(false);
    }
  }

  async function handleCreateIssueVoucher() {
    if (!dashboard || !selectedRequest) {
      setError('Select an approved request to prepare issue.');
      return;
    }
    const items = selectedRequest.items.reduce<PharmacyStoreIssueVoucherCreatePayload['items']>(
      (accumulator, item) => {
        const draft = issueDraft[item.refill_request_item_id];
        const issuedQuantity = Number(draft?.issuedQuantity || 0);
        if (!draft || !draft.batchNumber || !Number.isFinite(issuedQuantity) || issuedQuantity <= 0) {
          return accumulator;
        }
        accumulator.push({
          refill_request_item_id: item.refill_request_item_id,
          batch_number: draft.batchNumber,
          expiry_date: draft.expiryDate || null,
          issued_quantity: issuedQuantity,
        });
        return accumulator;
      },
      []
    );

    if (!items.length) {
      setError('Prepare at least one voucher line with a batch and quantity.');
      return;
    }

    try {
      setIssueSubmitting(true);
      await pharmacyStoreService.createIssueVoucher({
        refill_request_id: selectedRequest.request_id,
        store_unit_id: dashboard.store_unit_id,
        note: issueNote.trim() || null,
        items,
      });
      setFlashMessage('Issue voucher created successfully.');
      setSelectedRequestId(null);
      setIssueNote('');
      setIssueDraft({});
      await loadDashboard(true);
      setActiveSection('vouchers');
    } catch (requestError) {
      console.error(requestError);
      setError('Failed to create issue voucher.');
    } finally {
      setIssueSubmitting(false);
    }
  }

  async function handleDispatchVoucher(voucherId: string) {
    try {
      setDispatchingVoucherId(voucherId);
      await pharmacyStoreService.dispatchIssueVoucher(voucherId, {
        note: issueNote.trim() || null,
      });
      setFlashMessage('Issue voucher dispatched successfully.');
      await loadDashboard(true);
      setActiveSection('receiving');
    } catch (requestError) {
      console.error(requestError);
      setError('Failed to dispatch the issue voucher.');
    } finally {
      setDispatchingVoucherId(null);
    }
  }

  function openReturnRequest(request: PharmacyStoreReturnRequestRow) {
    setSelectedReturnRequestId(request.id);
    setReturnReviewNote(request.review_note || '');
    setReturnReceiveNote(request.receive_note || '');
  }

  async function handleReviewReturnRequest(decision: 'ACCEPT' | 'REJECT') {
    if (!selectedReturnRequest) {
      setError('Select a return request to review.');
      return;
    }
    try {
      setReturnReviewSubmitting(true);
      await pharmacyStoreService.reviewReturnRequest(selectedReturnRequest.id, {
        decision,
        review_note: returnReviewNote.trim() || null,
      });
      setFlashMessage(
        decision === 'ACCEPT'
          ? 'Return request accepted for store receipt.'
          : 'Return request rejected.'
      );
      setSelectedReturnRequestId(null);
      setReturnReviewNote('');
      setReturnReceiveNote('');
      await loadDashboard(true);
    } catch (requestError) {
      console.error(requestError);
      setError('Failed to review the return request.');
    } finally {
      setReturnReviewSubmitting(false);
    }
  }

  async function handleReceiveReturnRequest() {
    if (!selectedReturnRequest) {
      setError('Select an accepted return request to receive.');
      return;
    }
    try {
      setReturnReceiveSubmitting(true);
      await pharmacyStoreService.receiveReturnRequest(selectedReturnRequest.id, {
        receive_note: returnReceiveNote.trim() || null,
      });
      setFlashMessage('Returned stock received back into store.');
      setSelectedReturnRequestId(null);
      setReturnReviewNote('');
      setReturnReceiveNote('');
      await loadDashboard(true);
    } catch (requestError) {
      console.error(requestError);
      setError('Failed to receive returned stock into store.');
    } finally {
      setReturnReceiveSubmitting(false);
    }
  }

  function updateIssueDraft(itemId: string, patch: Partial<IssueDraftEntry>) {
    setIssueDraft((current) => ({
      ...current,
      [itemId]: {
        ...current[itemId],
        ...patch,
      },
    }));
  }

  if (loading && !dashboard) {
    return (
      <div className="space-y-6">
        <DashboardHero
          title="Pharmacy Store Dashboard"
          subtitle={HOSPITAL_NAME}
          workspaceLabel="Central stock, vouchers, dispatch, and reconciliation"
          variant="calm-light"
          accentLabel="Central Supply Control"
          rightSlot={<p className="text-sm text-slate-500">Loading store workspace...</p>}
        />
        <Card>
          <p className="text-sm text-slate-600">Loading pharmacy store dashboard...</p>
        </Card>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="space-y-6">
        <DashboardHero
          title="Pharmacy Store Dashboard"
          subtitle={HOSPITAL_NAME}
          workspaceLabel="Central stock, vouchers, dispatch, and reconciliation"
          variant="calm-light"
          accentLabel="Central Supply Control"
        />
        <Card>
          <p className="text-sm text-red-600">{error || 'Unable to load store dashboard.'}</p>
          <Button className="mt-4" onClick={() => void loadDashboard()}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <DashboardHero
        title="Pharmacy Store Dashboard"
        subtitle={HOSPITAL_NAME}
        workspaceLabel={`${dashboard.store_unit_name} • Central stock, vouchers, dispatch, and reconciliation`}
        variant="calm-light"
        accentLabel="Central Supply Control"
        monogram="S"
        rightSlot={
          <>
            <p className="font-semibold text-slate-900">{getDashboardUserDisplayName(dashboardUser)}</p>
            <p>Role: {roleLabel(dashboardUser?.role)}</p>
            <p>Store status: Active</p>
            <p>Last updated: {formatDateTime(dashboard.overview.last_updated_at)}</p>
          </>
        }
        actionsSlot={
          <>
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-[150px]">
                <SelectField
                  label="Store Unit"
                  value={storeUnitFilter}
                  onChange={setStoreUnitFilter}
                  options={storeUnits}
                />
              </div>
              <Input label="Start Date" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
              <Input label="End Date" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
              <Button variant="secondary" onClick={() => void loadDashboard(true)} isLoading={refreshing}>
                Refresh
              </Button>
            </div>
          </>
        }
      />

      {flashMessage ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {flashMessage}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-6" aria-label="Store command strip">
        {commandStrip.map((item) => (
          <MetricTile
            key={item.label}
            label={item.label}
            value={item.value}
            tone={item.tone}
          />
        ))}
      </section>

      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="h-fit">
          <nav className="space-y-2" aria-label="Pharmacy store sections">
            {sidebarSections.map((section) => {
              const count = sectionBadgeCount(section.id, dashboard);
              const tone = sectionBadgeTone(section.id);
              return (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                    activeSection === section.id
                      ? 'border-[#1E4B8C] bg-[#EAF4FB]'
                      : 'border-transparent bg-slate-50 hover:border-slate-200 hover:bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900">{section.label}</p>
                      <p className="mt-1 text-sm text-slate-600">{section.description}</p>
                    </div>
                    {count > 0 ? (
                      <span className={`rounded-full px-2 py-1 text-xs font-semibold ${badgeClass(tone)}`}>
                        {count}
                      </span>
                    ) : null}
                  </div>
                </button>
              );
            })}
          </nav>
        </Card>

        <div className="space-y-6">
          {activeSection === 'overview' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Store Overview"
                title="Central Supply Control Room"
                description="Track approved workload, stock risk, dispatch state, and which units are consuming central stock fastest."
              />
              <div className="grid gap-4 xl:grid-cols-3">
                <Card title="Supply Workload">
                  <div className="space-y-3">
                    {dashboard.supply_workload.map((row) => (
                      <div key={row.label} className="flex items-start justify-between gap-4 rounded-xl border border-slate-100 px-4 py-3">
                        <div>
                          <p className="font-medium text-slate-900">{row.label}</p>
                          {row.detail ? <p className="mt-1 text-sm text-slate-600">{row.detail}</p> : null}
                        </div>
                        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${badgeClass(row.severity)}`}>
                          {row.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card title="Stock Risk">
                  <div className="space-y-3">
                    {dashboard.stock_risk_summary.map((row) => (
                      <div key={row.label} className="flex items-start justify-between gap-4 rounded-xl border border-slate-100 px-4 py-3">
                        <div>
                          <p className="font-medium text-slate-900">{row.label}</p>
                          {row.detail ? <p className="mt-1 text-sm text-slate-600">{row.detail}</p> : null}
                        </div>
                        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${badgeClass(row.severity)}`}>
                          {row.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card title="Dispatch Status">
                  <div className="space-y-3">
                    {dashboard.dispatch_status.map((row) => (
                      <div key={row.label} className="flex items-start justify-between gap-4 rounded-xl border border-slate-100 px-4 py-3">
                        <div>
                          <p className="font-medium text-slate-900">{row.label}</p>
                          {row.detail ? <p className="mt-1 text-sm text-slate-600">{row.detail}</p> : null}
                        </div>
                        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${badgeClass(row.severity)}`}>
                          {row.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
              <Card title="Top Consuming Units">
                {dashboard.top_consuming_units.length ? (
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {dashboard.top_consuming_units.map((row) => (
                      <div key={row.label} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                        <p className="text-sm font-medium text-slate-600">{row.label}</p>
                        <p className="mt-2 text-2xl font-semibold text-slate-900">{row.value}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="No consumption trend available"
                    detail="Issued stock will appear here when units start consuming from store."
                  />
                )}
              </Card>
            </div>
          ) : null}

          {activeSection === 'inventory' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Inventory"
                title="Central Stock Inventory"
                description="View central stock by item class and tracking mode, with reservation-aware availability for approved requests and controlled intake."
              />
              <Card>
                <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px]">
                  <Input
                    label="Search inventory"
                    placeholder="Item, batch, or stock state"
                    value={inventorySearch}
                    onChange={(event) => setInventorySearch(event.target.value)}
                  />
                  <SelectField
                    label="Stock Status"
                    value={inventoryStatusFilter}
                    onChange={setInventoryStatusFilter}
                    options={inventoryStatusOptions}
                  />
                </div>
                <div className="mt-4">
                  {inventoryRows.length ? (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-slate-500">
                            <th className="py-3 pr-4">Item</th>
                            <th className="py-3 pr-4">Class / Tracking</th>
                            <th className="py-3 pr-4">Batch</th>
                            <th className="py-3 pr-4">Expiry</th>
                            <th className="py-3 pr-4">On Hand</th>
                            <th className="py-3 pr-4">Reserved</th>
                            <th className="py-3 pr-4">Available</th>
                            <th className="py-3 pr-4">Threshold</th>
                            <th className="py-3 pr-4">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {inventoryRows.map((row) => (
                            <tr key={`${row.inventory_item_id}-${row.batch_number || 'aggregate'}`}>
                              <td className="py-3 pr-4">
                                <div>
                                  <p className="font-medium text-slate-900">{row.item_name}</p>
                                  <p className="text-xs text-slate-500">
                                    {row.dosage_form}
                                    {row.strength ? ` • ${row.strength}` : ''}
                                    {row.unit_of_measure ? ` • ${row.unit_of_measure}` : ''}
                                  </p>
                                </div>
                              </td>
                              <td className="py-3 pr-4">
                                <div className="space-y-1">
                                  <p className="text-slate-700">{workflowLabel(row.classification)}</p>
                                  <p className="text-xs text-slate-500">
                                    {workflowLabel(row.tracking_mode)}
                                    {row.requires_expiry ? ' • Expiry required' : ' • No expiry required'}
                                  </p>
                                </div>
                              </td>
                              <td className="py-3 pr-4">{row.batch_number || 'Aggregate stock'}</td>
                              <td className="py-3 pr-4">{formatDateOnly(row.expiry_date)}</td>
                              <td className="py-3 pr-4">{row.quantity_on_hand}</td>
                              <td className="py-3 pr-4">{row.reserved_quantity}</td>
                              <td className="py-3 pr-4">{row.available_quantity}</td>
                              <td className="py-3 pr-4">{row.low_stock_threshold}</td>
                              <td className="py-3 pr-4">
                                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(row.stock_status)}`}>
                                  {row.stock_status.replaceAll('_', ' ')}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  ) : (
                    <EmptyState
                      title="No inventory rows match this filter"
                      detail="Adjust the stock status filter or search term."
                    />
                  )}
                </div>
              </Card>
              <div className="grid gap-6 xl:grid-cols-[0.92fr,1.08fr]">
                <Card title="Receive Stock">
                  <div className="grid gap-4 lg:grid-cols-2">
                    <SelectField label="Item" value={receiveItemId} onChange={setReceiveItemId} options={itemOptions} />
                    <Input label="Batch / Lot" value={receiveBatchNumber} onChange={(event) => setReceiveBatchNumber(event.target.value)} />
                    <Input label="Expiry Date" type="date" value={receiveExpiryDate} onChange={(event) => setReceiveExpiryDate(event.target.value)} />
                    <Input label="Quantity Received" type="number" min={1} value={receiveQuantity} onChange={(event) => setReceiveQuantity(event.target.value)} />
                    <div className="lg:col-span-2">
                      <TextAreaField
                        label="Source / Reference Note"
                        value={receiveNote}
                        onChange={setReceiveNote}
                        placeholder="Supplier note, transfer note, or source reference"
                      />
                    </div>
                  </div>
                  <div className="mt-4 flex justify-end">
                    <Button onClick={() => void handleReceiveStock()} isLoading={receiveSubmitting}>
                      Receive Into Store
                    </Button>
                  </div>
                </Card>
                <Card title="Recent Stock Receipts">
                  {dashboard.movement_history.filter((row) => row.movement_type === 'RESTOCK').length > 0 ? (
                    <div className="space-y-3">
                      {dashboard.movement_history
                        .filter((row) => row.movement_type === 'RESTOCK')
                        .slice(0, 8)
                        .map((row) => (
                          <div key={row.movement_id} className="rounded-xl border border-slate-100 px-4 py-3">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div>
                                <p className="font-medium text-slate-900">{row.item_name}</p>
                                <p className="text-sm text-slate-600">
                                  {row.batch_number || 'No batch'} • {formatDateTime(row.occurred_at)}
                                </p>
                              </div>
                              <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">
                                {formatDelta(row.quantity_delta)}
                              </span>
                            </div>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <EmptyState
                      title="No stock receipts recorded in this period"
                      detail="Received stock entries will appear here."
                    />
                  )}
                </Card>
              </div>
            </div>
          ) : null}

          {activeSection === 'department-requests' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Requests"
                title="Department Requests"
                description="Requester demand stays visible here with CMD approval state and requester-facing timeline before store execution begins."
              />
              <Card>
                <Input
                  label="Search requests"
                  placeholder="Request number, unit, type, priority, or status"
                  value={requestSearch}
                  onChange={(event) => setRequestSearch(event.target.value)}
                />
                <div className="mt-4">
                  {departmentRequests.length ? (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-slate-500">
                            <th className="py-3 pr-4">Request</th>
                            <th className="py-3 pr-4">Unit</th>
                            <th className="py-3 pr-4">Type</th>
                            <th className="py-3 pr-4">Priority</th>
                            <th className="py-3 pr-4">Status</th>
                            <th className="py-3 pr-4">Approved By</th>
                            <th className="py-3 pr-4">Timeline</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {departmentRequests.map((row) => (
                            <tr key={row.request_id}>
                              <td className="py-3 pr-4">
                                <p className="font-medium text-slate-900">{row.request_number}</p>
                                <p className="text-xs text-slate-500">{formatDateTime(row.requested_at)}</p>
                              </td>
                              <td className="py-3 pr-4">{row.requesting_unit_name}</td>
                              <td className="py-3 pr-4">{workflowLabel(row.request_type)}</td>
                              <td className="py-3 pr-4">
                                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${row.priority === 'EMERGENCY' ? 'border border-red-200 bg-red-50 text-red-700' : row.priority === 'URGENT' ? 'border border-amber-200 bg-amber-50 text-amber-700' : 'border border-blue-200 bg-blue-50 text-blue-700'}`}>
                                  {row.priority}
                                </span>
                              </td>
                              <td className="py-3 pr-4">
                                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(row.status)}`}>
                                  {row.status.replaceAll('_', ' ')}
                                </span>
                              </td>
                              <td className="py-3 pr-4">{row.approved_by_name || 'Awaiting CMD decision'}</td>
                              <td className="py-3 pr-4">
                                <div className="flex flex-wrap gap-1">
                                  {row.requester_timeline.map((step) => (
                                    <span
                                      key={`${row.request_id}-${step}`}
                                      className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-medium text-slate-700"
                                    >
                                      {step}
                                    </span>
                                  ))}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  ) : (
                    <EmptyState
                      title="No department requests for this period"
                      detail="Requester demand and approval visibility will appear here."
                    />
                  )}
                </div>
              </Card>
            </div>
          ) : null}

          {activeSection === 'approved' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Approved Requests"
                title="Approved Request Execution"
                description="Only CMD-approved requests appear here for store preparation, voucher generation, and controlled partial issue handling."
              />
              <Card>
                <Input
                  label="Search requests"
                  placeholder="Request number, unit, priority, or status"
                  value={requestSearch}
                  onChange={(event) => setRequestSearch(event.target.value)}
                />
                <div className="mt-4">
                  {approvedRequests.length ? (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-slate-500">
                            <th className="py-3 pr-4">Request</th>
                            <th className="py-3 pr-4">Unit</th>
                            <th className="py-3 pr-4">Type</th>
                            <th className="py-3 pr-4">Priority</th>
                            <th className="py-3 pr-4">Status</th>
                            <th className="py-3 pr-4">Approved By</th>
                            <th className="py-3 pr-4">Reserved</th>
                            <th className="py-3 pr-4">Pending</th>
                            <th className="py-3 pr-4">Waiting</th>
                            <th className="py-3 pr-4">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {approvedRequests.map((row) => (
                            <tr key={row.request_id}>
                              <td className="py-3 pr-4">
                                <p className="font-medium text-slate-900">{row.request_number}</p>
                                <p className="text-xs text-slate-500">{formatDateTime(row.requested_at)}</p>
                              </td>
                              <td className="py-3 pr-4">{row.requesting_unit_name}</td>
                              <td className="py-3 pr-4">{workflowLabel(row.request_type)}</td>
                              <td className="py-3 pr-4">
                                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${row.priority === 'EMERGENCY' ? 'border border-red-200 bg-red-50 text-red-700' : row.priority === 'URGENT' ? 'border border-amber-200 bg-amber-50 text-amber-700' : 'border border-blue-200 bg-blue-50 text-blue-700'}`}>
                                  {row.priority}
                                </span>
                              </td>
                              <td className="py-3 pr-4">
                                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(row.status)}`}>
                                  {row.status.replaceAll('_', ' ')}
                                </span>
                              </td>
                              <td className="py-3 pr-4">{row.approved_by_name || 'CMD'}</td>
                              <td className="py-3 pr-4">{row.total_reserved_quantity}</td>
                              <td className="py-3 pr-4">
                                <div>
                                  <p>{row.total_pending_quantity}</p>
                                  {row.backorder_pending ? <p className="text-xs text-red-600">Backorder pending</p> : null}
                                </div>
                              </td>
                              <td className="py-3 pr-4">{row.waiting_minutes} min</td>
                              <td className="py-3 pr-4">
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={() => {
                                    setSelectedRequestId(row.request_id);
                                    setActiveSection('approved');
                                  }}
                                >
                                  Prepare Issue
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  ) : (
                    <EmptyState
                      title="No approved requests for this period"
                      detail="Approved and backordered requests will appear here once CMD review is complete."
                    />
                  )}
                </div>
              </Card>

              <Card title="Prepare Issue Voucher">
                <div className="grid gap-4 lg:grid-cols-[minmax(0,260px)_1fr]">
                  <SelectField
                    label="Approved Request"
                    value={selectedRequestId || ''}
                    onChange={(value) => setSelectedRequestId(value || null)}
                    options={requestOptions}
                  />
                  <TextAreaField
                    label="Issue Note"
                    value={issueNote}
                    onChange={setIssueNote}
                    placeholder="Dispatch note, backorder context, or handling instruction"
                  />
                </div>
                <div className="mt-4">
                  {selectedRequest ? (
                    <div className="space-y-4">
                      {selectedRequest.items.map((item) => {
                        const draft = issueDraft[item.refill_request_item_id];
                        const batchOptions: SelectOption[] = [
                          { value: '', label: 'Select batch' },
                          ...(dashboard.inventory || [])
                            .filter(
                              (row) =>
                                row.inventory_item_id === item.inventory_item_id &&
                                row.batch_number &&
                                row.quantity_on_hand > 0 &&
                                row.can_issue
                            )
                            .map((row) => ({
                              value: row.batch_number || '',
                              label: `${row.batch_number} • ${row.quantity_on_hand} available${row.expiry_date ? ` • exp ${formatDateOnly(row.expiry_date)}` : ''}`,
                            })),
                        ];

                        return (
                          <div key={item.refill_request_item_id} className="rounded-2xl border border-slate-200 px-4 py-4">
                            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_180px_200px_140px]">
                              <div>
                                <p className="font-semibold text-slate-900">{item.inventory_item_name}</p>
                                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                                  <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-blue-700">
                                    Approved {item.approved_quantity}
                                  </span>
                                  <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-emerald-700">
                                    Reserved {item.reserved_quantity}
                                  </span>
                                  {item.backorder_quantity > 0 ? (
                                    <span className="rounded-full border border-red-200 bg-red-50 px-2 py-1 text-red-700">
                                      Backorder {item.backorder_quantity}
                                    </span>
                                  ) : null}
                                </div>
                              </div>
                              <SelectField
                                label="Batch"
                                value={draft?.batchNumber || ''}
                                onChange={(value) => {
                                  const selectedBatch = dashboard.inventory.find(
                                    (row) =>
                                      row.inventory_item_id === item.inventory_item_id &&
                                      row.batch_number === value
                                  );
                                  updateIssueDraft(item.refill_request_item_id, {
                                    batchNumber: value,
                                    expiryDate: selectedBatch?.expiry_date || '',
                                  });
                                }}
                                options={batchOptions}
                              />
                              <Input
                                label="Expiry Date"
                                type="date"
                                value={draft?.expiryDate || ''}
                                onChange={(event) =>
                                  updateIssueDraft(item.refill_request_item_id, { expiryDate: event.target.value })
                                }
                              />
                              <Input
                                label="Issue Qty"
                                type="number"
                                min={0}
                                max={item.reserved_quantity}
                                value={draft?.issuedQuantity || '0'}
                                onChange={(event) =>
                                  updateIssueDraft(item.refill_request_item_id, { issuedQuantity: event.target.value })
                                }
                              />
                            </div>
                          </div>
                        );
                      })}
                      <div className="flex justify-end">
                        <Button onClick={() => void handleCreateIssueVoucher()} isLoading={issueSubmitting}>
                          Generate Issue Voucher
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <EmptyState
                      title="No request selected"
                      detail="Choose an approved request to prepare a full or partial issue voucher."
                    />
                  )}
                </div>
              </Card>
            </div>
          ) : null}

          {activeSection === 'vouchers' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Issue Vouchers"
                title="Internal Supply Documents"
                description="This is the document and control layer. Voucher generation happens during issue preparation, before dispatch deducts stock."
              />
              <Card>
                {dashboard.issue_vouchers.length ? (
                  <DataTable>
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead>
                        <tr className="text-left text-slate-500">
                          <th className="py-3 pr-4">Voucher</th>
                          <th className="py-3 pr-4">Receiving Unit</th>
                          <th className="py-3 pr-4">Prepared</th>
                          <th className="py-3 pr-4">Dispatched</th>
                          <th className="py-3 pr-4">Approved</th>
                          <th className="py-3 pr-4">Received</th>
                          <th className="py-3 pr-4">Status</th>
                          <th className="py-3 pr-4">Pending Qty</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                          {dashboard.issue_vouchers.map((voucher) => (
                            <tr key={voucher.voucher_id}>
                              <td className="py-3 pr-4">
                                <p className="font-medium text-slate-900">{voucher.voucher_number}</p>
                                <p className="text-xs text-slate-500">{formatDateTime(voucher.prepared_at || voucher.issue_date)}</p>
                              </td>
                              <td className="py-3 pr-4">{voucher.receiving_unit_name}</td>
                              <td className="py-3 pr-4">
                                <p>{voucher.prepared_by_name || 'N/A'}</p>
                                <p className="text-xs text-slate-500">{formatDateTime(voucher.prepared_at)}</p>
                              </td>
                              <td className="py-3 pr-4">
                                <p>{voucher.issued_by_name || 'Awaiting dispatch'}</p>
                                <p className="text-xs text-slate-500">{formatDateTime(voucher.dispatched_at || voucher.issue_date)}</p>
                              </td>
                              <td className="py-3 pr-4">{voucher.approved_by_name || 'N/A'}</td>
                              <td className="py-3 pr-4">{voucher.received_by_name || 'Awaiting acknowledgement'}</td>
                              <td className="py-3 pr-4">
                              <div className="flex flex-col gap-1">
                                <span className={`inline-flex w-fit rounded-full px-2 py-1 text-xs font-semibold ${statusClass(voucher.status)}`}>
                                  {voucher.status.replaceAll('_', ' ')}
                                </span>
                                {voucher.partial_issue ? (
                                  <span className="text-xs text-amber-700">Partial issue</span>
                                ) : null}
                              </div>
                            </td>
                            <td className="py-3 pr-4">{voucher.pending_quantity}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </DataTable>
                ) : (
                  <EmptyState
                    title="No issue vouchers in this period"
                    detail="Generated store vouchers will appear here."
                  />
                )}
              </Card>
            </div>
          ) : null}

          {activeSection === 'dispatch' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Execution"
                title="Issue & Dispatch"
                description="Dispatch is the stock-moving action. Prepared vouchers stay here until store confirms release to the requesting unit."
              />
              <Card>
                {dispatchQueue.length ? (
                  <DataTable>
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead>
                        <tr className="text-left text-slate-500">
                          <th className="py-3 pr-4">Voucher</th>
                          <th className="py-3 pr-4">Receiving Unit</th>
                          <th className="py-3 pr-4">Status</th>
                          <th className="py-3 pr-4">Prepared By</th>
                          <th className="py-3 pr-4">Pending Qty</th>
                          <th className="py-3 pr-4">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {dispatchQueue.map((row) => (
                          <tr key={row.voucher_id}>
                            <td className="py-3 pr-4">
                              <p className="font-medium text-slate-900">{row.voucher_number}</p>
                              <p className="text-xs text-slate-500">{formatDateTime(row.prepared_at || row.issue_date)}</p>
                            </td>
                            <td className="py-3 pr-4">{row.receiving_unit_name}</td>
                            <td className="py-3 pr-4">
                              <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(row.status)}`}>
                                {row.status.replaceAll('_', ' ')}
                              </span>
                            </td>
                            <td className="py-3 pr-4">{row.prepared_by_name || 'Store officer'}</td>
                            <td className="py-3 pr-4">{row.pending_quantity}</td>
                            <td className="py-3 pr-4">
                              <Button
                                size="sm"
                                onClick={() => void handleDispatchVoucher(row.voucher_id)}
                                isLoading={dispatchingVoucherId === row.voucher_id}
                                disabled={Boolean(dispatchingVoucherId && dispatchingVoucherId !== row.voucher_id)}
                              >
                                Dispatch
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </DataTable>
                ) : (
                  <EmptyState
                    title="No prepared vouchers awaiting dispatch"
                    detail="Prepared store vouchers will appear here once issue preparation is complete."
                  />
                )}
              </Card>
            </div>
          ) : null}

          {activeSection === 'receiving' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Receiving"
                title="Receiving & Acknowledgement"
                description="Dispatch does not close the loop. Units must acknowledge receipt, and accepted return-to-store requests are received back here with full voucher linkage."
              />
              <Card>
                {receivingQueue.length ? (
                  <DataTable>
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead>
                        <tr className="text-left text-slate-500">
                          <th className="py-3 pr-4">Voucher</th>
                          <th className="py-3 pr-4">Receiving Unit</th>
                          <th className="py-3 pr-4">Status</th>
                          <th className="py-3 pr-4">Awaiting Ack</th>
                          <th className="py-3 pr-4">Discrepancy</th>
                          <th className="py-3 pr-4">Dispatched</th>
                          <th className="py-3 pr-4">Received By</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {receivingQueue.map((row) => (
                          <tr key={row.voucher_id}>
                            <td className="py-3 pr-4">
                              <p className="font-medium text-slate-900">{row.voucher_number}</p>
                              <p className="text-xs text-slate-500">{formatDateTime(row.dispatched_at || row.issue_date)}</p>
                            </td>
                            <td className="py-3 pr-4">{row.receiving_unit_name}</td>
                            <td className="py-3 pr-4">
                              <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(row.status)}`}>
                                {row.status.replaceAll('_', ' ')}
                              </span>
                            </td>
                            <td className="py-3 pr-4">{row.awaiting_acknowledgement ? 'Yes' : 'No'}</td>
                            <td className="py-3 pr-4">{row.discrepancy_pending ? 'Pending review' : 'None'}</td>
                            <td className="py-3 pr-4">{row.issued_by_name || 'Store officer'}</td>
                            <td className="py-3 pr-4">{row.received_by_name || 'Awaiting acknowledgement'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </DataTable>
                ) : (
                  <EmptyState
                    title="No receiving records awaiting attention"
                    detail="Dispatched vouchers with pending acknowledgement or discrepancies will appear here."
                  />
                )}
              </Card>

              <Card title="Returns to Store">
                {returnRequests.length ? (
                  <DataTable>
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead>
                        <tr className="text-left text-slate-500">
                          <th className="py-3 pr-4">Return</th>
                          <th className="py-3 pr-4">Origin Voucher</th>
                          <th className="py-3 pr-4">Returning Unit</th>
                          <th className="py-3 pr-4">Item</th>
                          <th className="py-3 pr-4">Qty</th>
                          <th className="py-3 pr-4">Reason</th>
                          <th className="py-3 pr-4">Status</th>
                          <th className="py-3 pr-4">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {returnRequests.map((row) => (
                          <tr key={row.id}>
                            <td className="py-3 pr-4">
                              <p className="font-medium text-slate-900">{row.return_number}</p>
                              <p className="text-xs text-slate-500">{formatDateTime(row.requested_at)}</p>
                            </td>
                            <td className="py-3 pr-4">{row.issue_voucher_number}</td>
                            <td className="py-3 pr-4">{row.returning_unit_name}</td>
                            <td className="py-3 pr-4">
                              <p>{row.inventory_item_name}</p>
                              <p className="text-xs text-slate-500">
                                Batch {row.batch_number}
                                {row.expiry_date ? ` • Exp ${formatDateOnly(row.expiry_date)}` : ''}
                              </p>
                            </td>
                            <td className="py-3 pr-4">
                              <p>{row.quantity_now_returned}</p>
                              <p className="text-xs text-slate-500">
                                Eligible now {row.eligible_return_quantity}
                              </p>
                            </td>
                            <td className="py-3 pr-4">{workflowLabel(row.reason_code)}</td>
                            <td className="py-3 pr-4">
                              <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(row.status)}`}>
                                {row.status.replaceAll('_', ' ')}
                              </span>
                            </td>
                            <td className="py-3 pr-4">
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => openReturnRequest(row)}
                              >
                                {row.status === 'RETURN_ACCEPTED'
                                  ? 'Receive Return'
                                  : row.status === 'RETURN_PENDING_STORE_REVIEW' ||
                                      row.status === 'RETURN_REQUESTED'
                                    ? 'Review Return'
                                    : 'View'}
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </DataTable>
                ) : (
                  <EmptyState
                    title="No return requests awaiting store action"
                    detail="Returns requested by units will appear here with voucher linkage and review status."
                  />
                )}
              </Card>
            </div>
          ) : null}

          {activeSection === 'movements' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Movement Ledger"
                title="Movement History"
                description="Review fully linked stock movement history across receive, issue, adjustment, transfer-ready, and future return flows."
              />
              <Card>
                <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_240px]">
                  <Input
                    label="Search movement history"
                    placeholder="Item, reference, or destination"
                    value={auditSearch}
                    onChange={(event) => setAuditSearch(event.target.value)}
                  />
                  <SelectField
                    label="Movement Type"
                    value={movementTypeFilter}
                    onChange={setMovementTypeFilter}
                    options={movementTypeOptions}
                  />
                </div>
                <div className="mt-4">
                  {movementRows.length ? (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-slate-500">
                            <th className="py-3 pr-4">When</th>
                            <th className="py-3 pr-4">Movement</th>
                            <th className="py-3 pr-4">Item</th>
                            <th className="py-3 pr-4">Batch</th>
                            <th className="py-3 pr-4">Qty</th>
                            <th className="py-3 pr-4">Destination</th>
                            <th className="py-3 pr-4">Actor</th>
                            <th className="py-3 pr-4">Reference</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {movementRows.map((row: PharmacyStoreMovementRow) => (
                            <tr key={row.movement_id}>
                              <td className="py-3 pr-4">{formatDateTime(row.occurred_at)}</td>
                              <td className="py-3 pr-4">{row.movement_type}</td>
                              <td className="py-3 pr-4">{row.item_name}</td>
                              <td className="py-3 pr-4">{row.batch_number || '—'}</td>
                              <td className="py-3 pr-4">{formatDelta(row.quantity_delta)}</td>
                              <td className="py-3 pr-4">{row.destination_label || row.source_label || 'Central Store'}</td>
                              <td className="py-3 pr-4">{row.actor_name || 'System'}</td>
                              <td className="py-3 pr-4">{row.reference_number || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  ) : (
                    <EmptyState
                      title="No movements match this filter"
                      detail="Change the movement type filter or search term."
                    />
                  )}
                </div>
              </Card>
            </div>
          ) : null}

          {activeSection === 'expiry' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Risk"
                title="Expiry & Low Stock"
                description="Treat low stock and expiry as action surfaces, not passive alerts. This is where disposal, transfer, and priority issue attention starts."
              />
              <Card>
                {dashboard.expiry_low_stock.length ? (
                  <DataTable>
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead>
                        <tr className="text-left text-slate-500">
                          <th className="py-3 pr-4">Item</th>
                          <th className="py-3 pr-4">Batch</th>
                          <th className="py-3 pr-4">Expiry</th>
                          <th className="py-3 pr-4">Quantity</th>
                          <th className="py-3 pr-4">Risk</th>
                          <th className="py-3 pr-4">Recommended Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {dashboard.expiry_low_stock.map((row) => (
                          <tr key={`${row.inventory_item_id}-${row.batch_number}-${row.risk_level}`}>
                            <td className="py-3 pr-4">{row.item_name}</td>
                            <td className="py-3 pr-4">{row.batch_number}</td>
                            <td className="py-3 pr-4">{formatDateOnly(row.expiry_date)}</td>
                            <td className="py-3 pr-4">{row.quantity_on_hand}</td>
                            <td className="py-3 pr-4">
                              <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(row.risk_level)}`}>
                                {row.risk_level.replaceAll('_', ' ')}
                              </span>
                            </td>
                            <td className="py-3 pr-4">{row.recommended_action}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </DataTable>
                ) : (
                  <EmptyState
                    title="No expiry or low stock risks in this period"
                    detail="Store risk rows will appear here when thresholds or expiry windows are reached."
                  />
                )}
              </Card>
            </div>
          ) : null}

          {activeSection === 'adjustments' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Reconciliation"
                title="Adjustments & Reconciliation"
                description="Record controlled stock corrections with explicit reasons, linked references, and auditable before/after movement state."
              />
              <Card title="Record Adjustment">
                <div className="grid gap-4 lg:grid-cols-2">
                  <SelectField label="Item" value={adjustItemId} onChange={setAdjustItemId} options={itemOptions} />
                  <SelectField label="Batch" value={adjustBatchNumber} onChange={setAdjustBatchNumber} options={selectedAdjustBatchOptions} />
                  <Input label="Expiry Date" type="date" value={adjustExpiryDate} onChange={(event) => setAdjustExpiryDate(event.target.value)} />
                  <Input label="Quantity Delta" type="number" value={adjustDelta} onChange={(event) => setAdjustDelta(event.target.value)} />
                  <div className="lg:col-span-2">
                    <TextAreaField
                      label="Reason"
                      value={adjustReason}
                      onChange={setAdjustReason}
                      placeholder="Cycle count correction, damaged stock, mismatch, or reconciliation note"
                    />
                  </div>
                </div>
                <div className="mt-4 flex justify-end">
                  <Button onClick={() => void handleAdjustment()} isLoading={adjustSubmitting}>
                    Record Adjustment
                  </Button>
                </div>
              </Card>
              <Card title="Recent Adjustments">
                {dashboard.adjustments_reconciliation.length ? (
                  <div className="space-y-3">
                    {dashboard.adjustments_reconciliation.map((row) => (
                      <div key={row.movement_id} className="rounded-xl border border-slate-100 px-4 py-3">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className="font-medium text-slate-900">
                              {row.item_name} {row.batch_number ? `• ${row.batch_number}` : ''}
                            </p>
                            <p className="text-sm text-slate-600">
                              {row.reason || 'Adjustment'} • {formatDateTime(row.occurred_at)}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className={`text-sm font-semibold ${row.quantity_delta < 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                              {formatDelta(row.quantity_delta)}
                            </p>
                            <p className="text-xs text-slate-500">{row.actor_name || 'System'}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="No adjustments in this period"
                    detail="Recorded adjustments will appear here for reconciliation review."
                  />
                )}
              </Card>
            </div>
          ) : null}

          {activeSection === 'activity' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Audit"
                title="Activity Audit"
                description="Review a human-readable activity stream tied to refill review, issue, acknowledgement, receiving, and adjustment events."
              />
              <Card>
                <Input
                  label="Search activity"
                  placeholder="Summary, unit, item, or actor"
                  value={auditSearch}
                  onChange={(event) => setAuditSearch(event.target.value)}
                />
                <div className="mt-4 space-y-3">
                  {activityRows.length ? (
                    activityRows.map((row: PharmacyStoreActivityRow) => (
                      <div key={row.id} className="rounded-2xl border border-slate-200 px-4 py-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="font-semibold text-slate-900">{row.summary}</p>
                              <span className={`rounded-full px-2 py-1 text-xs font-semibold ${badgeClass(row.severity)}`}>
                                {row.action_type.replaceAll('_', ' ')}
                              </span>
                            </div>
                            <p className="mt-2 text-sm text-slate-600">{row.detail || 'No additional detail recorded.'}</p>
                            <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                              {row.item_name ? <span>Item: {row.item_name}</span> : null}
                              {row.unit_name ? <span>Unit: {row.unit_name}</span> : null}
                              {row.voucher_number ? <span>Voucher: {row.voucher_number}</span> : null}
                              {row.request_number ? <span>Request: {row.request_number}</span> : null}
                              {row.actor_name ? <span>Actor: {row.actor_name}</span> : null}
                            </div>
                          </div>
                          <p className="text-sm text-slate-500">{formatDateTime(row.occurred_at)}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <EmptyState
                      title="No activity matches this filter"
                      detail="Audit events and movement summaries will appear here."
                    />
                  )}
                </div>
              </Card>
            </div>
          ) : null}

          {activeSection === 'reports' ? (
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Analytics"
                title="Reports & Analytics"
                description="Use store trends to spot stock-out pressure, high-consuming units, expiry risk, and adjustment patterns."
              />
              <div className="grid gap-4 xl:grid-cols-2">
                <MetricTile
                  label="Stock Received in Period"
                  value={dashboard.reports_analytics.stock_received_by_period}
                  tone="info"
                />
                <MetricTile
                  label="Stock Issued in Period"
                  value={dashboard.reports_analytics.stock_issued_by_period}
                  tone="info"
                />
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                <Card title="Issue Volume by Unit">
                  {dashboard.reports_analytics.issue_volume_by_unit.length ? (
                    <div className="space-y-3">
                      {dashboard.reports_analytics.issue_volume_by_unit.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3">
                          <p className="text-slate-700">{row.label}</p>
                          <p className="font-semibold text-slate-900">{row.value}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState title="No issue volume yet" detail="Issued stock will populate this trend." />
                  )}
                </Card>
                <Card title="Top Consumed Items">
                  {dashboard.reports_analytics.top_consumed_items.length ? (
                    <div className="space-y-3">
                      {dashboard.reports_analytics.top_consumed_items.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3">
                          <p className="text-slate-700">{row.label}</p>
                          <p className="font-semibold text-slate-900">{row.value}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState title="No consumption trend yet" detail="Issued stock will populate this list." />
                  )}
                </Card>
                <Card title="Backorder Trend">
                  {dashboard.reports_analytics.backorder_trend.length ? (
                    <div className="space-y-3">
                      {dashboard.reports_analytics.backorder_trend.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3">
                          <p className="text-slate-700">{row.label}</p>
                          <p className="font-semibold text-slate-900">{row.value}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState title="No active backorders" detail="Backordered units or requests will surface here." />
                  )}
                </Card>
                <Card title="Adjustment Trend">
                  {dashboard.reports_analytics.adjustment_trend.length ? (
                    <div className="space-y-3">
                      {dashboard.reports_analytics.adjustment_trend.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3">
                          <p className="text-slate-700">{row.label}</p>
                          <p className="font-semibold text-slate-900">{row.value}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState title="No adjustment trend yet" detail="Store adjustments will be summarized here." />
                  )}
                </Card>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {selectedReturnRequest ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
          <div className="w-full max-w-3xl rounded-3xl bg-white shadow-2xl">
            <div className="border-b border-slate-200 px-6 py-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1E4B8C]">
                    Return Review
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                    {selectedReturnRequest.return_number}
                  </h2>
                  <p className="mt-2 text-sm text-slate-600">
                    {selectedReturnRequest.returning_unit_name} • {selectedReturnRequest.issue_voucher_number}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedReturnRequestId(null)}
                  className="rounded-full border border-slate-200 px-3 py-1 text-sm text-slate-500 hover:bg-slate-50"
                >
                  Close
                </button>
              </div>
            </div>
            <div className="space-y-4 px-6 py-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Origin</p>
                  <p className="mt-2 font-medium text-slate-900">{selectedReturnRequest.issue_voucher_number}</p>
                  <p className="mt-1 text-sm text-slate-600">{selectedReturnRequest.inventory_item_name}</p>
                  <p className="mt-1 text-sm text-slate-600">
                    Batch {selectedReturnRequest.batch_number}
                    {selectedReturnRequest.expiry_date
                      ? ` • Exp ${formatDateOnly(selectedReturnRequest.expiry_date)}`
                      : ''}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Quantity</p>
                  <p className="mt-2 text-sm text-slate-700">
                    Originally issued {selectedReturnRequest.original_issued_quantity}
                  </p>
                  <p className="mt-1 text-sm text-slate-700">
                    Already returned {selectedReturnRequest.quantity_already_returned}
                  </p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    Returning now {selectedReturnRequest.quantity_now_returned}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    Remaining balance {selectedReturnRequest.remaining_issued_balance}
                  </p>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 p-4">
                <p className="text-sm font-medium text-slate-900">Reason</p>
                <p className="mt-2 text-sm text-slate-700">
                  {workflowLabel(selectedReturnRequest.reason_code)}
                </p>
                <p className="mt-2 text-sm text-slate-600">
                  {selectedReturnRequest.reason_note || 'No additional return note provided.'}
                </p>
              </div>

              {selectedReturnRequest.status === 'RETURN_PENDING_STORE_REVIEW' ||
              selectedReturnRequest.status === 'RETURN_REQUESTED' ? (
                <div>
                  <TextAreaField
                    label="Review Note"
                    value={returnReviewNote}
                    onChange={setReturnReviewNote}
                    placeholder="Record store review decision or rejection reason."
                  />
                </div>
              ) : null}

              {selectedReturnRequest.status === 'RETURN_ACCEPTED' ? (
                <div>
                  <TextAreaField
                    label="Receive Note"
                    value={returnReceiveNote}
                    onChange={setReturnReceiveNote}
                    placeholder="Record receipt condition or store intake note."
                  />
                </div>
              ) : null}

              <div className="flex flex-wrap gap-2">
                {selectedReturnRequest.return_timeline.map((step) => (
                  <span
                    key={`${selectedReturnRequest.id}-${step}`}
                    className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700"
                  >
                    {step}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4">
              <Button variant="secondary" onClick={() => setSelectedReturnRequestId(null)}>
                Close
              </Button>
              {selectedReturnRequest.status === 'RETURN_PENDING_STORE_REVIEW' ||
              selectedReturnRequest.status === 'RETURN_REQUESTED' ? (
                <>
                  <Button
                    variant="secondary"
                    onClick={() => void handleReviewReturnRequest('REJECT')}
                    isLoading={returnReviewSubmitting}
                    disabled={returnReviewSubmitting}
                  >
                    Reject Return
                  </Button>
                  <Button
                    onClick={() => void handleReviewReturnRequest('ACCEPT')}
                    isLoading={returnReviewSubmitting}
                    disabled={returnReviewSubmitting}
                  >
                    Accept Return
                  </Button>
                </>
              ) : null}
              {selectedReturnRequest.status === 'RETURN_ACCEPTED' ? (
                <Button
                  onClick={() => void handleReceiveReturnRequest()}
                  isLoading={returnReceiveSubmitting}
                  disabled={returnReceiveSubmitting}
                >
                  Receive Into Store
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
