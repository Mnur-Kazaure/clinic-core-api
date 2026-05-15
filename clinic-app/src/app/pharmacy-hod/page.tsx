'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
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
  pharmacyCatalogGovernanceService,
  type PharmacyCatalogRequestCreatePayload,
  type PharmacyInventoryClassification,
  type PharmacyInventoryTrackingMode,
} from '@/domains/pharmacy/services/pharmacyCatalogGovernanceService';
import {
  pharmacyHodService,
  type PharmacyHodActivityAuditRow,
  type PharmacyHodCriticalAlertRow,
  type PharmacyHodDashboardResponse,
  type PharmacyHodIssueVoucherRow,
  type PharmacyHodRefillRequestRow,
  type PharmacyHodSalesRevenueRow,
  type PharmacyHodStaffSummary,
} from '@/domains/pharmacy/services/pharmacyHodService';

const sidebarSections = [
  { id: 'overview', label: 'Overview', description: 'Command center for queue, risk, and payment visibility' },
  { id: 'unit-operations', label: 'Unit Operations', description: 'Operational view by pharmacy unit' },
  { id: 'dispensing-oversight', label: 'Dispensing Oversight', description: 'Assigned prescriptions and readiness states' },
  { id: 'store-supply', label: 'Store Supply', description: 'Refill demand with CMD-driven approval visibility' },
  { id: 'issue-vouchers', label: 'Issue Vouchers', description: 'Internal supply traceability and partial issue handling' },
  { id: 'staff-control', label: 'Staff Control', description: 'Person-centered pharmacy governance' },
  { id: 'unit-assignment', label: 'Unit Assignment', description: 'Coverage and default unit distribution' },
  { id: 'pending-approvals', label: 'Pending Approvals', description: 'Requests waiting for CMD decision' },
  { id: 'exception-oversight', label: 'Exception Oversight', description: 'NHIS and override monitoring' },
  { id: 'critical-alerts', label: 'Critical Alerts', description: 'Urgent operational pharmacy risks' },
  { id: 'stock-risk', label: 'Stock Risk & Expiry', description: 'Low stock, critical stock, and expiry watch' },
  { id: 'activity-audit', label: 'Activity Audit', description: 'Human-readable pharmacy traceability' },
  { id: 'staff-performance', label: 'Staff Performance', description: 'Operational insight without punitive ranking' },
  { id: 'sales-revenue', label: 'Sales & Revenue', description: 'Read-only finance visibility' },
  { id: 'receipt-register', label: 'Receipt Register', description: 'Pharmacy-linked receipt traceability' },
  { id: 'reports-analytics', label: 'Reports & Analytics', description: 'Trends across units, pay points, and stock' },
  { id: 'configuration-requests', label: 'Configuration Requests', description: 'Structured future governance workflow' },
] as const;

type SidebarSectionId = (typeof sidebarSections)[number]['id'];
type SelectOption = { value: string; label: string };
const ALL_FILTER = 'ALL';
type CatalogRequestFormState = Omit<
  PharmacyCatalogRequestCreatePayload,
  'submit_now' | 'brand_name' | 'strength'
> & {
  brand_name: string;
  strength: string;
};

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function formatMoney(minor: number, currency: string) {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(minor / 100);
}

function formatDateTime(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleString();
}

function formatDateOnly(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleDateString();
}

function formatMinutes(value?: number | null) {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(1)} min`;
}

function roleLabel(role: UserRole) {
  switch (role) {
    case UserRole.PHARMACY_HOD:
      return 'Pharmacy HOD';
    case UserRole.PHARMACY_STORE_OFFICER:
      return 'Pharmacy Store Officer';
    case UserRole.PHARMACY:
      return 'Pharmacist';
    default:
      return role;
  }
}

function workflowLabel(value: string) {
  return value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function buildOptions(
  values: Array<string | null | undefined>,
  labeler: (value: string) => string = (value) => value
): SelectOption[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value))))
    .sort((left, right) => left.localeCompare(right))
    .map((value) => ({ value, label: labeler(value) }));
}

function matchesSelectFilter(value: string | null | undefined, filter: string) {
  return filter === ALL_FILTER || value === filter;
}

function matchesSearch(values: Array<string | null | undefined>, term: string) {
  const normalized = term.trim().toLowerCase();
  if (!normalized) return true;
  return values.some((value) => value?.toLowerCase().includes(normalized));
}

function badgeClass(count: number, tone: 'info' | 'warning' | 'critical') {
  if (count <= 0) return '';
  if (tone === 'critical') return 'border border-red-200 bg-red-50 text-red-700';
  if (tone === 'warning') return 'border border-amber-200 bg-amber-50 text-amber-700';
  return 'border border-blue-200 bg-blue-50 text-blue-700';
}

function catalogStatusClass(status: string) {
  if (status === 'REJECTED' || status === 'DEACTIVATED') {
    return 'border border-red-200 bg-red-50 text-red-700';
  }
  if (status === 'ACTIVE') {
    return 'border border-emerald-200 bg-emerald-50 text-emerald-700';
  }
  if (status === 'PRICED' || status === 'PRICING_PENDING') {
    return 'border border-blue-200 bg-blue-50 text-blue-700';
  }
  return 'border border-amber-200 bg-amber-50 text-amber-700';
}

function sectionBadgeCount(sectionId: SidebarSectionId, dashboard: PharmacyHodDashboardResponse | null) {
  if (!dashboard) return 0;
  switch (sectionId) {
    case 'pending-approvals':
      return dashboard.pending_approvals.length;
    case 'exception-oversight':
      return dashboard.exception_oversight.length;
    case 'critical-alerts':
      return dashboard.critical_alerts.length;
    case 'stock-risk':
      return dashboard.stock_risk_expiry.length;
    case 'sales-revenue':
      return dashboard.sales_revenue.receipt_count;
    case 'receipt-register':
      return dashboard.receipt_register.length;
    default:
      return 0;
  }
}

function sectionBadgeTone(sectionId: SidebarSectionId): 'info' | 'warning' | 'critical' {
  switch (sectionId) {
    case 'critical-alerts':
    case 'stock-risk':
      return 'critical';
    case 'pending-approvals':
    case 'exception-oversight':
      return 'warning';
    default:
      return 'info';
  }
}

function SectionHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1E4B8C]">{eyebrow}</p>
      <h2 className="mt-2 text-2xl font-semibold text-slate-900">{title}</h2>
      <p className="mt-2 max-w-3xl text-sm text-slate-600">{description}</p>
    </div>
  );
}

function MetricTile({ label, value, detail, tone = 'neutral' }: { label: string; value: string | number; detail?: string; tone?: 'neutral' | 'warning' | 'critical' | 'info' }) {
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

function DataTable({ children }: { children: React.ReactNode }) {
  return <div className="overflow-x-auto">{children}</div>;
}

export default function PharmacyHodPage() {
  const dashboardUser = useDashboardUser();
  const [dashboard, setDashboard] = useState<PharmacyHodDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<SidebarSectionId>('overview');
  const [startDate, setStartDate] = useState(todayIsoDate());
  const [endDate, setEndDate] = useState(todayIsoDate());
  const [dispensingSearch, setDispensingSearch] = useState('');
  const [dispensingUnitFilter, setDispensingUnitFilter] = useState(ALL_FILTER);
  const [dispensingReadinessFilter, setDispensingReadinessFilter] = useState(ALL_FILTER);
  const [dispensingStaffFilter, setDispensingStaffFilter] = useState(ALL_FILTER);
  const [staffSearch, setStaffSearch] = useState('');
  const [staffRoleFilter, setStaffRoleFilter] = useState(ALL_FILTER);
  const [staffUnitFilter, setStaffUnitFilter] = useState(ALL_FILTER);
  const [staffStatusFilter, setStaffStatusFilter] = useState(ALL_FILTER);
  const [auditSearch, setAuditSearch] = useState('');
  const [auditUnitFilter, setAuditUnitFilter] = useState(ALL_FILTER);
  const [auditStaffFilter, setAuditStaffFilter] = useState(ALL_FILTER);
  const [auditActionFilter, setAuditActionFilter] = useState(ALL_FILTER);
  const [salesSearch, setSalesSearch] = useState('');
  const [salesUnitFilter, setSalesUnitFilter] = useState(ALL_FILTER);
  const [salesPayPointFilter, setSalesPayPointFilter] = useState(ALL_FILTER);
  const [receiptSearch, setReceiptSearch] = useState('');
  const [receiptUnitFilter, setReceiptUnitFilter] = useState(ALL_FILTER);
  const [receiptPayPointFilter, setReceiptPayPointFilter] = useState(ALL_FILTER);
  const [selectedStaffId, setSelectedStaffId] = useState<string | null>(null);
  const [selectedAuditId, setSelectedAuditId] = useState<string | null>(null);
  const [assignmentUnitIds, setAssignmentUnitIds] = useState<string[]>([]);
  const [assignmentDefaultUnitId, setAssignmentDefaultUnitId] = useState<string>('');
  const [assignmentSaving, setAssignmentSaving] = useState(false);
  const [catalogForm, setCatalogForm] = useState<CatalogRequestFormState>({
    generic_name: '',
    brand_name: '',
    strength: '',
    dosage_form: '',
    dispense_unit: '',
    classification: 'DRUG' as PharmacyInventoryClassification,
    tracking_mode: 'LOT_TRACKED' as PharmacyInventoryTrackingMode,
    requires_expiry: true,
    justification: '',
  });
  const [catalogSubmitting, setCatalogSubmitting] = useState(false);

  const loadDashboard = useCallback(
    async (mode: 'initial' | 'refresh' | 'poll' = 'initial') => {
      try {
        if (mode === 'initial') {
          setLoading(true);
        } else if (mode === 'refresh') {
          setRefreshing(true);
        }
        setError(null);
        const payload = await pharmacyHodService.getDashboard({
          start_date: startDate,
          end_date: endDate,
        });
        setDashboard(payload);
        setSelectedStaffId((current) => current || payload.staff_control[0]?.user_id || null);
        setSelectedAuditId((current) => current || payload.activity_audit[0]?.id || null);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Unable to load the pharmacy HOD dashboard.');
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [endDate, startDate]
  );

  const dashboardStreamUrl = useMemo(
    () =>
      pharmacyHodService.getDashboardStreamUrl({
        start_date: startDate,
        end_date: endDate,
      }),
    [endDate, startDate]
  );
  const { snapshot: liveDashboardSnapshot, error: liveDashboardError } =
    useEventStreamSnapshot<PharmacyHodDashboardResponse>({
      enabled: Boolean(dashboardUser),
      url: dashboardStreamUrl,
      eventName: 'pharmacy_hod_dashboard_snapshot',
      errorMessage: 'Live pharmacy HOD updates are temporarily unavailable.',
    });

  useEffect(() => {
    void loadDashboard('initial');
  }, [loadDashboard]);

  useEffect(() => {
    if (!liveDashboardSnapshot) {
      return;
    }
    setDashboard(liveDashboardSnapshot);
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

  const selectedStaff = useMemo(
    () => dashboard?.staff_control.find((item) => item.user_id === selectedStaffId) || null,
    [dashboard, selectedStaffId]
  );

  useEffect(() => {
    if (!selectedStaff) {
      setAssignmentUnitIds([]);
      setAssignmentDefaultUnitId('');
      return;
    }
    setAssignmentUnitIds(selectedStaff.assigned_units.map((unit) => unit.id));
    setAssignmentDefaultUnitId(selectedStaff.default_unit_id || '');
  }, [selectedStaff]);

  const availableUnits = useMemo(() => {
    const assignmentUnits = dashboard?.unit_assignment || [];
    return assignmentUnits.map((unit) => ({ id: unit.unit_id, name: unit.unit_name }));
  }, [dashboard]);
  const configurationRequests = useMemo(
    () => dashboard?.configuration_requests || [],
    [dashboard]
  );

  const dispensingUnitOptions = useMemo(
    () => buildOptions((dashboard?.dispensing_oversight || []).map((row) => row.unit_name)),
    [dashboard]
  );
  const dispensingReadinessOptions = useMemo(
    () =>
      buildOptions(
        (dashboard?.dispensing_oversight || []).map((row) => row.readiness_state),
        workflowLabel
      ),
    [dashboard]
  );
  const dispensingStaffOptions = useMemo(
    () => buildOptions((dashboard?.dispensing_oversight || []).map((row) => row.assigned_staff_name)),
    [dashboard]
  );
  const staffRoleOptions = useMemo(
    () =>
      buildOptions(
        (dashboard?.staff_control || []).map((row) => row.role),
        (value) => roleLabel(value as UserRole)
      ),
    [dashboard]
  );
  const staffUnitOptions = useMemo(
    () => buildOptions((dashboard?.unit_assignment || []).map((row) => row.unit_name)),
    [dashboard]
  );
  const auditUnitOptions = useMemo(
    () => buildOptions((dashboard?.activity_audit || []).map((row) => row.unit_name)),
    [dashboard]
  );
  const auditStaffOptions = useMemo(
    () => buildOptions((dashboard?.activity_audit || []).map((row) => row.actor_name)),
    [dashboard]
  );
  const auditActionOptions = useMemo(
    () =>
      buildOptions(
        (dashboard?.activity_audit || []).map((row) => row.action_type),
        workflowLabel
      ),
    [dashboard]
  );
  const salesUnitOptions = useMemo(
    () => buildOptions((dashboard?.sales_revenue.rows || []).map((row) => row.unit_name)),
    [dashboard]
  );
  const salesPayPointOptions = useMemo(
    () => buildOptions((dashboard?.sales_revenue.rows || []).map((row) => row.cashier_pay_point_name)),
    [dashboard]
  );
  const receiptUnitOptions = useMemo(
    () =>
      buildOptions(
        (dashboard?.receipt_register || []).flatMap((row) => row.unit_names)
      ),
    [dashboard]
  );
  const receiptPayPointOptions = useMemo(
    () => buildOptions((dashboard?.receipt_register || []).map((row) => row.cashier_pay_point_name)),
    [dashboard]
  );

  const filteredDispensingRows = useMemo(() => {
    const rows = dashboard?.dispensing_oversight || [];
    return rows.filter(
      (row) =>
        matchesSearch(
          [
            row.patient_name,
            row.patient_mrn,
            row.item_name,
            row.unit_name,
            row.assigned_staff_name,
            workflowLabel(row.readiness_state),
            workflowLabel(row.payment_state),
          ],
          dispensingSearch
        ) &&
        matchesSelectFilter(row.unit_name, dispensingUnitFilter) &&
        matchesSelectFilter(row.readiness_state, dispensingReadinessFilter) &&
        matchesSelectFilter(row.assigned_staff_name, dispensingStaffFilter)
    );
  }, [
    dashboard,
    dispensingReadinessFilter,
    dispensingSearch,
    dispensingStaffFilter,
    dispensingUnitFilter,
  ]);

  const filteredStaff = useMemo(() => {
    const rows = dashboard?.staff_control || [];
    return rows.filter((row) => {
      const unitNames = row.assigned_units.map((unit) => unit.name);
      return (
        matchesSearch([row.full_name, row.email, roleLabel(row.role), ...unitNames], staffSearch) &&
        matchesSelectFilter(row.role, staffRoleFilter) &&
        (staffUnitFilter === ALL_FILTER || unitNames.includes(staffUnitFilter)) &&
        matchesSelectFilter(row.is_active ? 'ACTIVE' : 'INACTIVE', staffStatusFilter)
      );
    });
  }, [dashboard, staffRoleFilter, staffSearch, staffStatusFilter, staffUnitFilter]);

  const filteredAuditRows = useMemo(() => {
    const rows = dashboard?.activity_audit || [];
    return rows.filter(
      (row) =>
        matchesSearch(
          [
            row.summary,
            row.detail,
            row.actor_name,
            row.unit_name,
            row.patient_name,
            row.patient_mrn,
            row.receipt_number,
            workflowLabel(row.action_type),
          ],
          auditSearch
        ) &&
        matchesSelectFilter(row.unit_name, auditUnitFilter) &&
        matchesSelectFilter(row.actor_name, auditStaffFilter) &&
        matchesSelectFilter(row.action_type, auditActionFilter)
    );
  }, [auditActionFilter, auditSearch, auditStaffFilter, auditUnitFilter, dashboard]);

  const filteredSalesRows = useMemo(() => {
    const rows = dashboard?.sales_revenue.rows || [];
    return rows.filter(
      (row) =>
        matchesSearch(
          [
            row.receipt_number,
            row.patient_name,
            row.patient_mrn,
            row.item_name,
            row.unit_name,
            row.cashier_pay_point_name,
            row.cashier_name,
          ],
          salesSearch
        ) &&
        matchesSelectFilter(row.unit_name, salesUnitFilter) &&
        matchesSelectFilter(row.cashier_pay_point_name, salesPayPointFilter)
    );
  }, [dashboard, salesPayPointFilter, salesSearch, salesUnitFilter]);

  const filteredReceipts = useMemo(() => {
    const rows = dashboard?.receipt_register || [];
    return rows.filter(
      (row) =>
        matchesSearch(
          [
            row.receipt_number,
            row.patient_name,
            row.patient_mrn,
            row.cashier_pay_point_name,
            ...row.unit_names,
            ...row.linked_items,
          ],
          receiptSearch
        ) &&
        matchesSelectFilter(row.cashier_pay_point_name, receiptPayPointFilter) &&
        (receiptUnitFilter === ALL_FILTER || row.unit_names.includes(receiptUnitFilter))
    );
  }, [dashboard, receiptPayPointFilter, receiptSearch, receiptUnitFilter]);

  const selectedAudit = useMemo(
    () => filteredAuditRows.find((row) => row.id === selectedAuditId) || filteredAuditRows[0] || null,
    [filteredAuditRows, selectedAuditId]
  );

  const handleToggleUnit = (unitId: string) => {
    setAssignmentUnitIds((current) => {
      const next = current.includes(unitId)
        ? current.filter((value) => value !== unitId)
        : [...current, unitId];
      if (!next.includes(assignmentDefaultUnitId)) {
        setAssignmentDefaultUnitId(next[0] || '');
      }
      return next;
    });
  };

  const handleSaveAssignment = async () => {
    if (!selectedStaff || selectedStaff.role !== UserRole.PHARMACY) {
      return;
    }
    try {
      setAssignmentSaving(true);
      const updated = await pharmacyHodService.updateStaffAssignment(selectedStaff.user_id, {
        allowed_unit_ids: assignmentUnitIds,
        default_unit_id: assignmentDefaultUnitId || null,
      });
      setFlashMessage(`${updated.full_name || updated.email} assignment updated.`);
      await loadDashboard('refresh');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to update staff assignment.');
    } finally {
      setAssignmentSaving(false);
    }
  };

  const handleCreateCatalogRequest = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      setCatalogSubmitting(true);
      setError(null);
      await pharmacyCatalogGovernanceService.createHodCatalogRequest({
        ...catalogForm,
        brand_name: catalogForm.brand_name || undefined,
        strength: catalogForm.strength || undefined,
        submit_now: true,
      });
      setFlashMessage('Pharmacy catalog request submitted for CMD approval.');
      setCatalogForm({
        generic_name: '',
        brand_name: '',
        strength: '',
        dosage_form: '',
        dispense_unit: '',
        classification: 'DRUG',
        tracking_mode: 'LOT_TRACKED',
        requires_expiry: true,
        justification: '',
      });
      await loadDashboard('refresh');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to submit the catalog request.');
    } finally {
      setCatalogSubmitting(false);
    }
  };

  const activeSectionMeta = sidebarSections.find((item) => item.id === activeSection);
  const currency = dashboard?.overview.currency || 'NGN';

  return (
    <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="sticky top-6 h-[calc(100vh-3rem)] overflow-hidden rounded-[30px] border border-[#17407A] bg-[#1E4B8C] text-[#EAF2FF] shadow-[0_28px_50px_rgba(15,23,42,0.18)]">
        <div className="flex h-full flex-col">
          <div className="border-b border-white/15 px-6 py-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#B9D7F2]">Pharmacy</p>
            <h1 className="mt-3 text-2xl font-semibold leading-tight">Pharmacy HOD Governance</h1>
            <p className="mt-3 text-sm text-[#C8DBF3]">{HOSPITAL_NAME}</p>
            <div className="mt-5 rounded-2xl border border-white/15 bg-white/8 px-4 py-3 text-sm">
              <p className="font-medium text-white">{getDashboardUserDisplayName(dashboardUser)}</p>
              <p className="mt-1 text-[#C8DBF3]">Department-only oversight workspace</p>
            </div>
          </div>
          <div className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
            {sidebarSections.map((section, index) => {
              const isActive = section.id === activeSection;
              const badgeCount = sectionBadgeCount(section.id, dashboard);
              return (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => setActiveSection(section.id)}
                  className={`relative w-full overflow-hidden rounded-2xl border px-4 py-3 text-left transition ${
                    isActive
                      ? 'border-white/20 bg-[linear-gradient(135deg,#1E4B8C_0%,#3FA3CF_100%)] text-white shadow-[0_16px_32px_rgba(15,23,42,0.18)]'
                      : 'border-transparent text-[#EAF2FF] hover:border-white/10 hover:bg-white/5'
                  }`}
                >
                  {isActive ? <span className="absolute inset-y-3 left-0 w-1 rounded-r-full bg-white" /> : null}
                  <div className="flex items-start gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/15 text-xs font-semibold text-white">
                      {index + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold">{section.label}</p>
                      <p className={`mt-1 text-[10px] leading-4 ${isActive ? 'text-white/90' : 'text-[#B9D7F2]'}`}>
                        {section.description}
                      </p>
                    </div>
                    {badgeCount > 0 ? (
                      <span className={`ml-auto inline-flex min-w-[1.75rem] items-center justify-center rounded-full px-2 py-1 text-[11px] font-semibold ${badgeClass(badgeCount, sectionBadgeTone(section.id))}`}>
                        {badgeCount > 99 ? '99+' : badgeCount}
                      </span>
                    ) : null}
                  </div>
                </button>
              );
            })}
          </div>
          <div className="border-t border-white/15 px-4 py-4">
            <Button
              variant="secondary"
              className="w-full border-none bg-white text-[#1E4B8C] hover:bg-[#EAF4FB]"
              onClick={() => void loadDashboard('refresh')}
              isLoading={refreshing}
            >
              Refresh Dashboard
            </Button>
          </div>
        </div>
      </aside>

      <div className="space-y-6">
        <DashboardHero
          title="Pharmacy HOD Dashboard"
          subtitle={HOSPITAL_NAME}
          workspaceLabel={activeSectionMeta?.description || 'Pharmacy governance workspace'}
          monogram="P"
          variant="calm-light"
          accentLabel="Pharmacy HOD"
          rightSlot={
            <>
              <div>
                <span className="font-semibold">Scope:</span> Pharmacy governance only
              </div>
              <div>
                <span className="font-semibold">Date range:</span> {startDate} to {endDate}
              </div>
              <div>
                <span className="font-semibold">Last updated:</span>{' '}
                {dashboard ? formatDateTime(dashboard.overview.last_updated_at) : 'N/A'}
              </div>
            </>
          }
        />

        <Card>
          <div className="grid gap-4 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
            <Input label="Start Date" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
            <Input label="End Date" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
            <div className="flex gap-3">
              <Button onClick={() => void loadDashboard('refresh')} isLoading={refreshing}>Apply Range</Button>
              <Button
                variant="secondary"
                onClick={() => {
                  const today = todayIsoDate();
                  setStartDate(today);
                  setEndDate(today);
                }}
              >
                Today
              </Button>
            </div>
          </div>
        </Card>

        {flashMessage ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{flashMessage}</div>
        ) : null}
        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
        ) : null}

        {loading ? (
          <Card title="Loading Pharmacy Governance Workspace">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
              Loading pharmacy HOD dashboard data…
            </div>
          </Card>
        ) : !dashboard ? (
          <Card title="Pharmacy Governance Workspace Unavailable">
            <EmptyState title="Dashboard unavailable" detail="The pharmacy HOD payload did not return usable data. Retry the load." />
          </Card>
        ) : (
          <>
            {activeSection === 'overview' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Overview" title="Pharmacy Command Center" description="Immediate view into dispensing readiness, payment clearance, store demand, and pharmacy risk." />
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  <MetricTile label="Pending Prescriptions" value={dashboard.overview.pending_prescriptions} />
                  <MetricTile label="Ready to Dispense" value={dashboard.overview.ready_to_dispense} tone="info" />
                  <MetricTile label="Awaiting Payment Clearance" value={dashboard.overview.awaiting_payment_clearance} tone="warning" />
                  <MetricTile label="Stock Risk Items" value={dashboard.overview.stock_risk_items} tone={dashboard.overview.stock_risk_items ? 'critical' : 'neutral'} />
                  <MetricTile label="Pending Refill Requests" value={dashboard.overview.pending_refill_requests} tone={dashboard.overview.pending_refill_requests ? 'warning' : 'neutral'} />
                  <MetricTile label="Critical Alerts" value={dashboard.overview.critical_alerts} tone={dashboard.overview.critical_alerts ? 'critical' : 'neutral'} />
                  <MetricTile label="Dispense Delays" value={dashboard.overview.delayed_dispense_count} detail="Items above the delay threshold" tone={dashboard.overview.delayed_dispense_count ? 'warning' : 'neutral'} />
                </div>

                <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
                  <Card title="Unit Summary Grid" titleClassName="text-slate-900">
                    {dashboard.unit_summary.length === 0 ? (
                      <EmptyState title="No pharmacy units available" detail="Seed or configure pharmacy units before using the HOD dashboard." />
                    ) : (
                      <DataTable>
                        <table className="min-w-full divide-y divide-slate-200 text-sm">
                          <thead>
                            <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                              <th className="px-3 py-3">Unit</th>
                              <th className="px-3 py-3">Queue</th>
                              <th className="px-3 py-3">Ready</th>
                              <th className="px-3 py-3">Awaiting Payment</th>
                              <th className="px-3 py-3">Stock Risk</th>
                              <th className="px-3 py-3">Revenue</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {dashboard.unit_summary.map((unit) => (
                              <tr key={unit.unit_id}>
                                <td className="px-3 py-3 font-medium text-slate-900">{unit.unit_name}</td>
                                <td className="px-3 py-3 text-slate-700">{unit.queue_volume}</td>
                                <td className="px-3 py-3 text-slate-700">{unit.ready_to_dispense}</td>
                                <td className="px-3 py-3 text-slate-700">{unit.awaiting_payment_clearance}</td>
                                <td className="px-3 py-3 text-slate-700">{unit.stock_risk}</td>
                                <td className="px-3 py-3 text-slate-700">{formatMoney(unit.revenue_today_minor, currency)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </DataTable>
                    )}
                  </Card>
                  <div className="space-y-6">
                    <Card title="System Health" titleClassName="text-slate-900">
                      <div className="space-y-3">
                        {dashboard.system_health.map((item) => (
                          <div key={item.key} className={`rounded-2xl border px-4 py-4 ${item.status === 'ATTENTION' ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'}`}>
                            <div className="flex items-center justify-between gap-3">
                              <p className="font-semibold text-slate-900">{item.label}</p>
                              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${item.status === 'ATTENTION' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-700'}`}>
                                {item.status}
                              </span>
                            </div>
                            <p className="mt-2 text-sm text-slate-700">{item.detail}</p>
                          </div>
                        ))}
                      </div>
                    </Card>
                    <Card title="Bottleneck / Delay Panel" titleClassName="text-slate-900">
                      <div className="space-y-3">
                        {dashboard.bottlenecks.length === 0 ? (
                          <EmptyState title="No active bottlenecks" detail="No unit is currently above the configured delay or queue threshold." />
                        ) : (
                          dashboard.bottlenecks.map((item, index) => (
                            <div key={`${item.title}-${index}`} className={`rounded-2xl border px-4 py-4 ${item.severity === 'critical' ? 'border-red-200 bg-red-50' : item.severity === 'warning' ? 'border-amber-200 bg-amber-50' : 'border-blue-200 bg-blue-50'}`}>
                              <p className="font-semibold text-slate-900">{item.title}</p>
                              <p className="mt-2 text-sm text-slate-700">{item.detail}</p>
                              {item.unit_name ? <p className="mt-2 text-xs uppercase tracking-[0.14em] text-slate-500">{item.unit_name}</p> : null}
                            </div>
                          ))
                        )}
                      </div>
                    </Card>
                  </div>
                </div>

                <Card title="Pay-Point Performance" titleClassName="text-slate-900">
                  <DataTable>
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead>
                        <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                          <th className="px-3 py-3">Cashier Point</th>
                          <th className="px-3 py-3">Transactions</th>
                          <th className="px-3 py-3">Revenue</th>
                          <th className="px-3 py-3">Awaiting Clearance</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {dashboard.pay_point_performance.map((item) => (
                          <tr key={item.pay_point_id}>
                            <td className="px-3 py-3 font-medium text-slate-900">{item.pay_point_name}</td>
                            <td className="px-3 py-3 text-slate-700">{item.transaction_count}</td>
                            <td className="px-3 py-3 text-slate-700">{formatMoney(item.revenue_minor, item.currency)}</td>
                            <td className="px-3 py-3 text-slate-700">{item.awaiting_clearance_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </DataTable>
                </Card>
              </div>
            )}

            {activeSection === 'unit-operations' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Unit Operations" title="Operational Pharmacy View by Unit" description="The HOD thinks by unit first. This section keeps queue, staffing, and stock pressure visible without duplicating the dispenser workspace." />
                <div className="grid gap-4 xl:grid-cols-2">
                  {dashboard.unit_operations.map((unit) => (
                    <Card key={unit.unit_id} className="h-full">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="text-lg font-semibold text-slate-900">{unit.unit_name}</p>
                          <p className="mt-1 text-sm text-slate-600">{workflowLabel(unit.category)}</p>
                        </div>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${unit.stock_status === 'Critical attention' ? 'bg-red-100 text-red-700' : unit.stock_status === 'Watchlist' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>{unit.stock_status}</span>
                      </div>
                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <MetricTile label="Queue" value={unit.queue_volume} />
                        <MetricTile label="Ready" value={unit.ready_to_dispense} tone="info" />
                        <MetricTile label="Awaiting Payment" value={unit.awaiting_payment_clearance} tone="warning" />
                        <MetricTile label="Staff on Duty" value={unit.staff_on_duty} />
                      </div>
                      <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-700">
                        <p><span className="font-semibold text-slate-900">Average dispense time:</span> {formatMinutes(unit.average_dispense_time_minutes)}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {unit.bottlenecks.length ? unit.bottlenecks.map((item) => (
                            <span key={item} className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">{item}</span>
                          )) : <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">No active bottleneck</span>}
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {activeSection === 'dispensing-oversight' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Dispensing Oversight" title="Assigned Prescriptions and Readiness State" description="Pharmacy visibility without routine dispense action. Assigned items remain visible even when they are still awaiting payment clearance." />
                <Card>
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <Input
                      placeholder="Search patient, MRN, item, unit, or staff"
                      value={dispensingSearch}
                      onChange={(event) => setDispensingSearch(event.target.value)}
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={dispensingUnitFilter}
                        onChange={(event) => setDispensingUnitFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All units</option>
                        {dispensingUnitOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Readiness</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={dispensingReadinessFilter}
                        onChange={(event) => setDispensingReadinessFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All readiness states</option>
                        {dispensingReadinessOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Assigned staff</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={dispensingStaffFilter}
                        onChange={(event) => setDispensingStaffFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All staff</option>
                        {dispensingStaffOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </Card>
                <Card>
                  {filteredDispensingRows.length === 0 ? (
                    <EmptyState title="No assigned prescriptions" detail="Pharmacy has no active assigned prescription items in the current dashboard range." />
                  ) : (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                            <th className="px-3 py-3">Patient</th>
                            <th className="px-3 py-3">Unit</th>
                            <th className="px-3 py-3">Prescription</th>
                            <th className="px-3 py-3">Readiness</th>
                            <th className="px-3 py-3">Payment</th>
                            <th className="px-3 py-3">Assigned Staff</th>
                            <th className="px-3 py-3">Delay</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {filteredDispensingRows.map((row) => (
                            <tr key={row.prescription_id}>
                              <td className="px-3 py-3">
                                <p className="font-medium text-slate-900">{row.patient_name || 'Unknown patient'}</p>
                                <p className="text-xs text-slate-500">{row.patient_mrn || 'No MRN'}</p>
                              </td>
                              <td className="px-3 py-3 text-slate-700">{row.unit_name || 'Unassigned'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.item_name}</td>
                              <td className="px-3 py-3"><span className={`rounded-full px-3 py-1 text-xs font-semibold ${row.readiness_state === 'READY_TO_DISPENSE' ? 'bg-blue-100 text-blue-700' : row.readiness_state === 'AWAITING_PAYMENT_CLEARANCE' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-700'}`}>{workflowLabel(row.readiness_state)}</span></td>
                              <td className="px-3 py-3 text-slate-700">{workflowLabel(row.payment_state)}</td>
                              <td className="px-3 py-3 text-slate-700">{row.assigned_staff_name || 'Unassigned'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.delay_minutes} min</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  )}
                </Card>
              </div>
            )}

            {activeSection === 'store-supply' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Store Supply" title="Refill Demand and CMD Approval Visibility" description="Requests from dispensing units stay visible here for oversight, but approval authority remains with CMD and execution remains with Store." />
                <Card>
                  {dashboard.store_supply.length === 0 ? (
                    <EmptyState title="No store requests" detail="Dispensing units have not raised refill or transfer requests yet." />
                  ) : (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                            <th className="px-3 py-3">Unit</th>
                            <th className="px-3 py-3">Requested By</th>
                            <th className="px-3 py-3">Urgency</th>
                            <th className="px-3 py-3">Status</th>
                            <th className="px-3 py-3">Items</th>
                            <th className="px-3 py-3">Requested Qty</th>
                            <th className="px-3 py-3">Approved Qty</th>
                            <th className="px-3 py-3">Requested At</th>
                            <th className="px-3 py-3">Governance</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {dashboard.store_supply.map((row) => (
                            <tr key={row.request_id}>
                              <td className="px-3 py-3 font-medium text-slate-900">{row.requesting_unit_name}</td>
                              <td className="px-3 py-3 text-slate-700">{row.requested_by_name || 'Unknown'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.urgency || 'Routine'}</td>
                              <td className="px-3 py-3"><span className={`rounded-full px-3 py-1 text-xs font-semibold ${row.status === 'AWAITING_CMD_APPROVAL' ? 'bg-amber-100 text-amber-700' : row.status === 'REJECTED' ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}>{workflowLabel(row.status)}</span></td>
                              <td className="px-3 py-3 text-slate-700">{row.item_count}</td>
                              <td className="px-3 py-3 text-slate-700">{row.total_requested_quantity}</td>
                              <td className="px-3 py-3 text-slate-700">{row.total_approved_quantity}</td>
                              <td className="px-3 py-3 text-slate-700">{formatDateTime(row.requested_at)}</td>
                              <td className="px-3 py-3">
                                <span className="text-sm text-slate-500">
                                  {row.status === 'AWAITING_CMD_APPROVAL'
                                    ? 'CMD decision required'
                                    : 'Visible for HOD oversight'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  )}
                </Card>
              </div>
            )}

            {activeSection === 'issue-vouchers' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Issue Vouchers" title="Internal Supply Voucher Traceability" description="Internal pharmacy supply is tracked with issue vouchers, not patient invoices. Partial issue and backorder state remain visible." />
                <Card>
                  {dashboard.issue_vouchers.length === 0 ? (
                    <EmptyState title="No issue vouchers" detail="Store has not issued any supply vouchers in the selected range." />
                  ) : (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                            <th className="px-3 py-3">Voucher</th>
                            <th className="px-3 py-3">Store</th>
                            <th className="px-3 py-3">Receiving Unit</th>
                            <th className="px-3 py-3">Status</th>
                            <th className="px-3 py-3">Partial</th>
                            <th className="px-3 py-3">Backorder</th>
                            <th className="px-3 py-3">Issued By</th>
                            <th className="px-3 py-3">Issued At</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {dashboard.issue_vouchers.map((row) => (
                            <tr key={row.voucher_id}>
                              <td className="px-3 py-3 font-medium text-slate-900">{row.voucher_number}</td>
                              <td className="px-3 py-3 text-slate-700">{row.store_unit_name}</td>
                              <td className="px-3 py-3 text-slate-700">{row.receiving_unit_name}</td>
                              <td className="px-3 py-3 text-slate-700">{workflowLabel(row.status)}</td>
                              <td className="px-3 py-3 text-slate-700">{row.partial_issue ? 'Yes' : 'No'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.backorder_pending ? 'Pending' : 'Closed'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.issued_by_name || 'Unknown'}</td>
                              <td className="px-3 py-3 text-slate-700">{formatDateTime(row.issued_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  )}
                </Card>
              </div>
            )}

            {activeSection === 'staff-control' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Staff Control" title="Person-Centered Pharmacy Workforce Governance" description="The HOD may change unit coverage and default dispensing unit for pharmacy staff, but cannot create users or mutate global identity data from here." />
                <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                  <Card title="Pharmacy Staff" titleClassName="text-slate-900">
                    <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <Input
                        placeholder="Search staff, role, email, or unit"
                        value={staffSearch}
                        onChange={(event) => setStaffSearch(event.target.value)}
                      />
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Role</label>
                        <select
                          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                          value={staffRoleFilter}
                          onChange={(event) => setStaffRoleFilter(event.target.value)}
                        >
                          <option value={ALL_FILTER}>All roles</option>
                          {staffRoleOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Assigned unit</label>
                        <select
                          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                          value={staffUnitFilter}
                          onChange={(event) => setStaffUnitFilter(event.target.value)}
                        >
                          <option value={ALL_FILTER}>All units</option>
                          {staffUnitOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Status</label>
                        <select
                          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                          value={staffStatusFilter}
                          onChange={(event) => setStaffStatusFilter(event.target.value)}
                        >
                          <option value={ALL_FILTER}>All statuses</option>
                          <option value="ACTIVE">Active</option>
                          <option value="INACTIVE">Inactive</option>
                        </select>
                      </div>
                    </div>
                    {filteredStaff.length === 0 ? (
                      <EmptyState title="No matching staff" detail="Adjust the search term or add pharmacy department users." />
                    ) : (
                      <div className="space-y-3">
                        {filteredStaff.map((row) => {
                          const isSelected = row.user_id === selectedStaffId;
                          return (
                            <button
                              key={row.user_id}
                              type="button"
                              onClick={() => setSelectedStaffId(row.user_id)}
                              className={`w-full rounded-2xl border px-4 py-4 text-left transition ${isSelected ? 'border-[#1E4B8C] bg-[#F4F9FF]' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'}`}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <p className="font-semibold text-slate-900">{row.full_name || row.email}</p>
                                  <p className="mt-1 text-sm text-slate-600">{roleLabel(row.role)} • {row.email}</p>
                                  <p className="mt-2 text-sm text-slate-600">Assigned Units: {row.assigned_units.length ? row.assigned_units.map((unit) => unit.name).join(', ') : 'None'}</p>
                                </div>
                                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${row.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{row.is_active ? 'Active' : 'Inactive'}</span>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </Card>
                  <Card title="Assignment Governance" titleClassName="text-slate-900">
                    {!selectedStaff ? (
                      <EmptyState title="No staff selected" detail="Select a pharmacy staff member to review coverage and default unit assignment." />
                    ) : (
                      <div className="space-y-4">
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-700">
                          <p className="font-semibold text-slate-900">{selectedStaff.full_name || selectedStaff.email}</p>
                          <p className="mt-1">{roleLabel(selectedStaff.role)}</p>
                          <p className="mt-2 text-slate-600">Recent activity: {selectedStaff.recent_activity_summary || 'No recent pharmacy event recorded'}</p>
                        </div>
                        {selectedStaff.role !== UserRole.PHARMACY ? (
                          <EmptyState title="Governance-only account" detail="Pharmacy HOD accounts do not use operational dispensing-unit assignments." />
                        ) : (
                          <>
                            <div className="space-y-3">
                              {availableUnits.map((unit) => (
                                <label key={unit.id} className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
                                  <input
                                    type="checkbox"
                                    checked={assignmentUnitIds.includes(unit.id)}
                                    onChange={() => handleToggleUnit(unit.id)}
                                  />
                                  <span>{unit.name}</span>
                                </label>
                              ))}
                            </div>
                            <div>
                              <label className="mb-2 block text-sm font-medium text-slate-700">Default Unit</label>
                              <select
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                value={assignmentDefaultUnitId}
                                onChange={(event) => setAssignmentDefaultUnitId(event.target.value)}
                              >
                                {assignmentUnitIds.map((unitId) => {
                                  const unit = availableUnits.find((item) => item.id === unitId);
                                  if (!unit) return null;
                                  return (
                                    <option key={unit.id} value={unit.id}>
                                      {unit.name}
                                    </option>
                                  );
                                })}
                              </select>
                            </div>
                            <Button onClick={handleSaveAssignment} isLoading={assignmentSaving} disabled={assignmentUnitIds.length === 0}>
                              Save Assignment Governance
                            </Button>
                          </>
                        )}
                      </div>
                    )}
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'unit-assignment' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Unit Assignment" title="Coverage Distribution by Unit" description="This section stays unit-centered so the HOD can see where staffing is thin, overloaded, or dependent on one default user." />
                <div className="grid gap-4 xl:grid-cols-2">
                  {dashboard.unit_assignment.map((unit) => (
                    <Card key={unit.unit_id} title={unit.unit_name} titleClassName="text-slate-900">
                      {unit.members.length === 0 ? (
                        <EmptyState title="No assigned staff" detail="This unit currently has no pharmacy staff coverage configured." />
                      ) : (
                        <div className="space-y-3">
                          {unit.members.map((member) => (
                            <div key={`${unit.unit_id}-${member.user_id}`} className="rounded-2xl border border-slate-200 px-4 py-3 text-sm">
                              <div className="flex items-center justify-between gap-3">
                                <div>
                                  <p className="font-semibold text-slate-900">{member.full_name || 'Unnamed staff'}</p>
                                  <p className="mt-1 text-slate-600">{roleLabel(member.role)}</p>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {member.is_default ? <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">Default</span> : null}
                                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${member.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{member.is_active ? 'Active' : 'Inactive'}</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {activeSection === 'pending-approvals' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Pending Approvals" title="Requests Waiting for CMD Decision" description="HOD sees the demand queue here for oversight, but approval authority is explicitly separated into the CMD workspace." />
                <Card>
                  {dashboard.pending_approvals.length === 0 ? (
                    <EmptyState title="No pending approvals" detail="There are no refill or store requests waiting for CMD decision right now." />
                  ) : (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                            <th className="px-3 py-3">Unit</th>
                            <th className="px-3 py-3">Requested By</th>
                            <th className="px-3 py-3">Urgency</th>
                            <th className="px-3 py-3">Items</th>
                            <th className="px-3 py-3">Requested Qty</th>
                            <th className="px-3 py-3">Requested At</th>
                            <th className="px-3 py-3">Authority</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {dashboard.pending_approvals.map((row) => (
                            <tr key={row.request_id}>
                              <td className="px-3 py-3 font-medium text-slate-900">{row.requesting_unit_name}</td>
                              <td className="px-3 py-3 text-slate-700">{row.requested_by_name || 'Unknown'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.urgency || 'Routine'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.item_count}</td>
                              <td className="px-3 py-3 text-slate-700">{row.total_requested_quantity}</td>
                              <td className="px-3 py-3 text-slate-700">{formatDateTime(row.requested_at)}</td>
                              <td className="px-3 py-3 text-sm text-slate-500">CMD authority required</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  )}
                </Card>
              </div>
            )}

            {activeSection === 'exception-oversight' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Exception Oversight" title="Policy-Based Exception Monitoring" description="Exception authorization stays separate from readiness state so HOD can review NHIS and override usage cleanly." />
                <Card>
                  {dashboard.exception_oversight.length === 0 ? (
                    <EmptyState title="No pharmacy exceptions recorded" detail="No NHIS-covered or override-authorized prescription items are visible in this dashboard window." />
                  ) : (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                            <th className="px-3 py-3">Patient</th>
                            <th className="px-3 py-3">Unit</th>
                            <th className="px-3 py-3">Exception Type</th>
                            <th className="px-3 py-3">Authorized By</th>
                            <th className="px-3 py-3">Workflow</th>
                            <th className="px-3 py-3">Resolution</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {dashboard.exception_oversight.map((row) => (
                            <tr key={row.prescription_id}>
                              <td className="px-3 py-3">
                                <p className="font-medium text-slate-900">{row.patient_name || 'Unknown patient'}</p>
                                <p className="text-xs text-slate-500">{row.patient_mrn || 'No MRN'}</p>
                              </td>
                              <td className="px-3 py-3 text-slate-700">{row.unit_name || 'Unassigned'}</td>
                              <td className="px-3 py-3 text-slate-700">{workflowLabel(row.exception_type)}</td>
                              <td className="px-3 py-3 text-slate-700">{row.authorized_by_name || 'Unknown'}</td>
                              <td className="px-3 py-3 text-slate-700">{workflowLabel(row.workflow_status)}</td>
                              <td className="px-3 py-3 text-slate-700">{workflowLabel(row.resolution_status)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  )}
                </Card>
              </div>
            )}

            {activeSection === 'critical-alerts' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Critical Alerts" title="Urgent Pharmacy Risk Visibility" description="Critical drug unavailability, dispense delays, and urgent refill attention stay visible here with severity-aware presentation." />
                {dashboard.critical_alerts.length === 0 ? (
                  <Card>
                    <EmptyState title="No active critical alerts" detail="The current pharmacy snapshot is not reporting urgent operational issues." />
                  </Card>
                ) : (
                  <div className="grid gap-4 xl:grid-cols-2">
                    {dashboard.critical_alerts.map((alert, index) => (
                      <Card key={`${alert.alert_type}-${index}`} className={alert.severity === 'critical' ? 'border-red-200' : 'border-amber-200'}>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-lg font-semibold text-slate-900">{alert.title}</p>
                            <p className="mt-2 text-sm text-slate-700">{alert.detail}</p>
                          </div>
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${alert.severity === 'critical' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{alert.severity === 'critical' ? 'Critical' : 'Warning'}</span>
                        </div>
                        <div className="mt-4 text-sm text-slate-600">
                          <p>Unit: {alert.unit_name || 'Unassigned'}</p>
                          {alert.patient_name ? <p>Patient: {alert.patient_name}</p> : null}
                          <p>Occurred: {formatDateTime(alert.occurred_at)}</p>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeSection === 'stock-risk' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Stock Risk & Expiry" title="Unit and Store Stock Risk Watch" description="Low stock, critical stock, expiring, and expired drug risk stays visible without turning the HOD into the storekeeper." />
                <Card>
                  {dashboard.stock_risk_expiry.length === 0 ? (
                    <EmptyState title="No stock risk rows" detail="The current pharmacy snapshot is not reporting low, critical, or expiry-based stock risks." />
                  ) : (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                            <th className="px-3 py-3">Unit</th>
                            <th className="px-3 py-3">Item</th>
                            <th className="px-3 py-3">Qty</th>
                            <th className="px-3 py-3">Threshold</th>
                            <th className="px-3 py-3">Expiry</th>
                            <th className="px-3 py-3">Risk</th>
                            <th className="px-3 py-3">Detail</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {dashboard.stock_risk_expiry.map((row) => (
                            <tr key={`${row.unit_id || 'store'}-${row.item_id}`}> 
                              <td className="px-3 py-3 font-medium text-slate-900">{row.unit_name}</td>
                              <td className="px-3 py-3 text-slate-700">{row.item_name}</td>
                              <td className="px-3 py-3 text-slate-700">{row.quantity_on_hand}</td>
                              <td className="px-3 py-3 text-slate-700">{row.low_stock_threshold}</td>
                              <td className="px-3 py-3 text-slate-700">{formatDateOnly(row.earliest_expiry_date)}</td>
                              <td className="px-3 py-3"><span className={`rounded-full px-3 py-1 text-xs font-semibold ${row.risk_level === 'EXPIRED' || row.risk_level === 'CRITICAL' ? 'bg-red-100 text-red-700' : row.risk_level === 'EXPIRING_SOON' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>{workflowLabel(row.risk_level)}</span></td>
                              <td className="px-3 py-3 text-slate-700">{row.detail}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  )}
                </Card>
              </div>
            )}

            {activeSection === 'activity-audit' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Activity Audit" title="Human-Readable Pharmacy Traceability" description="Readable feed first, structured detail second. Filters stay on top so HOD can review pharmacy activity without dropping into raw logs." />
                <Card>
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <Input
                      placeholder="Search action, staff, patient, MRN, or receipt"
                      value={auditSearch}
                      onChange={(event) => setAuditSearch(event.target.value)}
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={auditUnitFilter}
                        onChange={(event) => setAuditUnitFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All units</option>
                        {auditUnitOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Staff</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={auditStaffFilter}
                        onChange={(event) => setAuditStaffFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All staff</option>
                        {auditStaffOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Action type</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={auditActionFilter}
                        onChange={(event) => setAuditActionFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All actions</option>
                        {auditActionOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </Card>
                <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
                  <Card title="Activity Feed" titleClassName="text-slate-900">
                    {filteredAuditRows.length === 0 ? (
                      <EmptyState title="No matching activity" detail="Adjust the audit filter or widen the date range." />
                    ) : (
                      <div className="space-y-3">
                        {filteredAuditRows.map((row) => (
                          <button
                            key={row.id}
                            type="button"
                            onClick={() => setSelectedAuditId(row.id)}
                            className={`w-full rounded-2xl border px-4 py-4 text-left transition ${selectedAudit?.id === row.id ? 'border-[#1E4B8C] bg-[#F4F9FF]' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'}`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="font-semibold text-slate-900">{row.summary}</p>
                                <p className="mt-1 text-sm text-slate-600">{row.actor_name || 'System'} • {row.unit_name || 'No unit'} • {formatDateTime(row.occurred_at)}</p>
                              </div>
                              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${row.severity === 'critical' ? 'bg-red-100 text-red-700' : row.severity === 'warning' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>{workflowLabel(row.severity)}</span>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </Card>
                  <Card title="Structured Detail" titleClassName="text-slate-900">
                    {!selectedAudit ? (
                      <EmptyState title="No activity selected" detail="Select an audit row to view structured traceability detail." />
                    ) : (
                      <div className="space-y-4 text-sm text-slate-700">
                        <div>
                          <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Summary</p>
                          <p className="mt-2 text-base font-semibold text-slate-900">{selectedAudit.summary}</p>
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                            <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Action</p>
                            <p className="mt-2 font-medium text-slate-900">{workflowLabel(selectedAudit.action_type)}</p>
                          </div>
                          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                            <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Occurred</p>
                            <p className="mt-2 font-medium text-slate-900">{formatDateTime(selectedAudit.occurred_at)}</p>
                          </div>
                          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                            <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Actor</p>
                            <p className="mt-2 font-medium text-slate-900">{selectedAudit.actor_name || 'System'}</p>
                          </div>
                          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                            <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Traceability</p>
                            <p className="mt-2 font-medium text-slate-900">{selectedAudit.receipt_number || selectedAudit.patient_mrn || 'Operational event'}</p>
                          </div>
                        </div>
                        {selectedAudit.detail ? (
                          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                            <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Detail</p>
                            <p className="mt-2 text-slate-700">{selectedAudit.detail}</p>
                          </div>
                        ) : null}
                      </div>
                    )}
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'staff-performance' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Staff Performance" title="Operational Performance Without Ranking" description="These metrics are for staffing and support decisions, not public ranking or punitive comparison." />
                <Card>
                  {dashboard.staff_performance.length === 0 ? (
                    <EmptyState title="No staff performance data" detail="No pharmacy activity has been recorded for the selected range." />
                  ) : (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                            <th className="px-3 py-3">Staff</th>
                            <th className="px-3 py-3">Assigned Units</th>
                            <th className="px-3 py-3">Handled</th>
                            <th className="px-3 py-3">Avg Time</th>
                            <th className="px-3 py-3">Pending Load</th>
                            <th className="px-3 py-3">Reassignments</th>
                            <th className="px-3 py-3">Stock Events</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {dashboard.staff_performance.map((row) => (
                            <tr key={row.user_id}>
                              <td className="px-3 py-3">
                                <p className="font-medium text-slate-900">{row.full_name || 'Unnamed staff'}</p>
                                <p className="text-xs text-slate-500">{roleLabel(row.role)}</p>
                              </td>
                              <td className="px-3 py-3 text-slate-700">{row.assigned_units.join(', ') || 'None'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.prescriptions_handled}</td>
                              <td className="px-3 py-3 text-slate-700">{formatMinutes(row.average_dispense_time_minutes)}</td>
                              <td className="px-3 py-3 text-slate-700">{row.pending_load}</td>
                              <td className="px-3 py-3 text-slate-700">{row.reassignment_count}</td>
                              <td className="px-3 py-3 text-slate-700">{row.stock_issue_events}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  )}
                </Card>
              </div>
            )}

            {activeSection === 'sales-revenue' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Sales & Revenue" title="Read-Only Pharmacy Finance Visibility" description="The HOD can see pharmacy-linked revenue and pay-point flow here, but cannot alter receipts, payments, or refunds." />
                <div className="grid gap-4 md:grid-cols-3">
                  <MetricTile label="Revenue in Range" value={formatMoney(dashboard.sales_revenue.total_revenue_minor, dashboard.sales_revenue.currency)} tone="info" />
                  <MetricTile label="Receipt Count" value={dashboard.sales_revenue.receipt_count} />
                  <MetricTile label="Paid Item Count" value={dashboard.sales_revenue.paid_item_count} />
                </div>
                <Card>
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    <Input
                      placeholder="Search receipt, patient, item, unit, or pay point"
                      value={salesSearch}
                      onChange={(event) => setSalesSearch(event.target.value)}
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={salesUnitFilter}
                        onChange={(event) => setSalesUnitFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All units</option>
                        {salesUnitOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Cashier pay point</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={salesPayPointFilter}
                        onChange={(event) => setSalesPayPointFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All pay points</option>
                        {salesPayPointOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </Card>
                <Card>
                  {filteredSalesRows.length === 0 ? (
                    <EmptyState title="No sales rows" detail="No pharmacy-linked paid billing items match the current range or filter." />
                  ) : (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                            <th className="px-3 py-3">Receipt</th>
                            <th className="px-3 py-3">Patient</th>
                            <th className="px-3 py-3">Item</th>
                            <th className="px-3 py-3">Unit</th>
                            <th className="px-3 py-3">Pay Point</th>
                            <th className="px-3 py-3">Amount</th>
                            <th className="px-3 py-3">Cashier</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {filteredSalesRows.map((row) => (
                            <tr key={`${row.receipt_id}-${row.item_name}`}> 
                              <td className="px-3 py-3 font-medium text-slate-900">{row.receipt_number}</td>
                              <td className="px-3 py-3">
                                <p className="font-medium text-slate-900">{row.patient_name || 'Unknown patient'}</p>
                                <p className="text-xs text-slate-500">{row.patient_mrn || 'No MRN'}</p>
                              </td>
                              <td className="px-3 py-3 text-slate-700">{row.item_name}</td>
                              <td className="px-3 py-3 text-slate-700">{row.unit_name || 'Unassigned'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.cashier_pay_point_name || 'Unassigned'}</td>
                              <td className="px-3 py-3 text-slate-700">{formatMoney(row.amount_minor, row.currency)}</td>
                              <td className="px-3 py-3 text-slate-700">{row.cashier_name || 'Unknown'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  )}
                </Card>
              </div>
            )}

            {activeSection === 'receipt-register' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Receipt Register" title="Receipt Traceability by Pharmacy Linkage" description="This archive is traceability-oriented. It shows receipts tied to pharmacy bill items without becoming a cashier workspace." />
                <Card>
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    <Input
                      placeholder="Search receipt number, patient, pay point, unit, or item"
                      value={receiptSearch}
                      onChange={(event) => setReceiptSearch(event.target.value)}
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={receiptUnitFilter}
                        onChange={(event) => setReceiptUnitFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All units</option>
                        {receiptUnitOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Cashier pay point</label>
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                        value={receiptPayPointFilter}
                        onChange={(event) => setReceiptPayPointFilter(event.target.value)}
                      >
                        <option value={ALL_FILTER}>All pay points</option>
                        {receiptPayPointOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </Card>
                <Card>
                  {filteredReceipts.length === 0 ? (
                    <EmptyState title="No receipts found" detail="No pharmacy-linked receipts match the current range or filter." />
                  ) : (
                    <DataTable>
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                            <th className="px-3 py-3">Receipt</th>
                            <th className="px-3 py-3">Patient</th>
                            <th className="px-3 py-3">Amount</th>
                            <th className="px-3 py-3">Pay Point</th>
                            <th className="px-3 py-3">Units</th>
                            <th className="px-3 py-3">Items</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {filteredReceipts.map((row) => (
                            <tr key={row.receipt_id}>
                              <td className="px-3 py-3 font-medium text-slate-900">{row.receipt_number}</td>
                              <td className="px-3 py-3">
                                <p className="font-medium text-slate-900">{row.patient_name || 'Unknown patient'}</p>
                                <p className="text-xs text-slate-500">{row.patient_mrn || 'No MRN'}</p>
                              </td>
                              <td className="px-3 py-3 text-slate-700">{formatMoney(row.amount_minor, row.currency)}</td>
                              <td className="px-3 py-3 text-slate-700">{row.cashier_pay_point_name || 'Unassigned'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.unit_names.join(', ') || 'Unassigned'}</td>
                              <td className="px-3 py-3 text-slate-700">{row.linked_items.join(', ')}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </DataTable>
                  )}
                </Card>
              </div>
            )}

            {activeSection === 'reports-analytics' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Reports & Analytics" title="Operational Pharmacy Trends" description="Trend cards here stay read-only and governance-oriented. They are for direction, not cashier mutation or store action execution." />
                <div className="grid gap-6 xl:grid-cols-2">
                  <Card title="Revenue by Unit" titleClassName="text-slate-900">
                    {dashboard.reports_analytics.revenue_by_unit.length === 0 ? (
                      <EmptyState title="No revenue trend" detail="No pharmacy-linked revenue rows are available for this range." />
                    ) : (
                      <div className="space-y-3">
                        {dashboard.reports_analytics.revenue_by_unit.map((row) => (
                          <div key={`${row.unit_id || 'none'}-${row.unit_name}`} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm">
                            <span className="font-medium text-slate-900">{row.unit_name}</span>
                            <span className="font-semibold text-slate-700">{formatMoney(row.revenue_minor, currency)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                  <Card title="Revenue by Pay Point" titleClassName="text-slate-900">
                    {dashboard.reports_analytics.revenue_by_pay_point.length === 0 ? (
                      <EmptyState title="No pay-point trend" detail="No cashier performance rows are available in this range." />
                    ) : (
                      <div className="space-y-3">
                        {dashboard.reports_analytics.revenue_by_pay_point.map((row) => (
                          <div key={row.pay_point_id} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm">
                            <span className="font-medium text-slate-900">{row.pay_point_name}</span>
                            <span className="font-semibold text-slate-700">{formatMoney(row.revenue_minor, row.currency)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                  <Card title="Refill Frequency by Unit" titleClassName="text-slate-900">
                    {dashboard.reports_analytics.refill_frequency_by_unit.length === 0 ? (
                      <EmptyState title="No refill frequency data" detail="No refill requests were recorded in this range." />
                    ) : (
                      <div className="space-y-3">
                        {dashboard.reports_analytics.refill_frequency_by_unit.map((row) => (
                          <div key={`${row.unit_id || 'none'}-${row.unit_name}`} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm">
                            <span className="font-medium text-slate-900">{row.unit_name}</span>
                            <span className="font-semibold text-slate-700">{row.revenue_minor} request(s)</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                  <Card title="Dispense Turnaround by Unit" titleClassName="text-slate-900">
                    {dashboard.reports_analytics.dispense_turnaround_by_unit.length === 0 ? (
                      <EmptyState title="No turnaround data" detail="No dispense turnaround metrics are available for this range." />
                    ) : (
                      <div className="space-y-3">
                        {dashboard.reports_analytics.dispense_turnaround_by_unit.map((row) => (
                          <div key={`${row.unit_id || 'none'}-${row.unit_name}`} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm">
                            <span className="font-medium text-slate-900">{row.unit_name}</span>
                            <span className="font-semibold text-slate-700">{row.revenue_minor} min</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                  <Card title="Stock Risk Counts" titleClassName="text-slate-900">
                    {dashboard.reports_analytics.stock_risk_counts.length === 0 ? (
                      <EmptyState title="No stock risk trend" detail="No stock risk rows were generated for the current snapshot." />
                    ) : (
                      <div className="space-y-3">
                        {dashboard.reports_analytics.stock_risk_counts.map((row) => (
                          <div key={row.label} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm">
                            <span className="font-medium text-slate-900">{workflowLabel(row.label)}</span>
                            <span className="font-semibold text-slate-700">{row.count}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'configuration-requests' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Configuration Requests" title="Catalog Governance Workflow" description="Pharmacy HOD requests new items here, CMD approves, and Accounts completes pricing before the item becomes operational." />
                <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
                  <Card title="Request New Catalog Item" titleClassName="text-slate-900">
                    <form className="space-y-4" onSubmit={handleCreateCatalogRequest}>
                      <div className="grid gap-4 md:grid-cols-2">
                        <Input
                          label="Generic Name"
                          value={catalogForm.generic_name}
                          onChange={(event) =>
                            setCatalogForm((current) => ({
                              ...current,
                              generic_name: event.target.value,
                            }))
                          }
                          placeholder="Paracetamol"
                        />
                        <Input
                          label="Brand Name"
                          value={catalogForm.brand_name}
                          onChange={(event) =>
                            setCatalogForm((current) => ({
                              ...current,
                              brand_name: event.target.value,
                            }))
                          }
                          placeholder="Optional"
                        />
                        <Input
                          label="Strength"
                          value={catalogForm.strength}
                          onChange={(event) =>
                            setCatalogForm((current) => ({
                              ...current,
                              strength: event.target.value,
                            }))
                          }
                          placeholder="500mg"
                        />
                        <Input
                          label="Dosage Form"
                          value={catalogForm.dosage_form}
                          onChange={(event) =>
                            setCatalogForm((current) => ({
                              ...current,
                              dosage_form: event.target.value,
                            }))
                          }
                          placeholder="Tablet"
                        />
                        <Input
                          label="Dispense Unit"
                          value={catalogForm.dispense_unit}
                          onChange={(event) =>
                            setCatalogForm((current) => ({
                              ...current,
                              dispense_unit: event.target.value,
                            }))
                          }
                          placeholder="Tablet"
                        />
                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700">Classification</label>
                          <select
                            value={catalogForm.classification}
                            onChange={(event) =>
                              setCatalogForm((current) => ({
                                ...current,
                                classification: event.target
                                  .value as PharmacyInventoryClassification,
                              }))
                            }
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                          >
                            <option value="DRUG">Drug</option>
                            <option value="CONSUMABLE">Consumable</option>
                            <option value="EQUIPMENT">Equipment</option>
                          </select>
                        </div>
                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700">Tracking Mode</label>
                          <select
                            value={catalogForm.tracking_mode}
                            onChange={(event) =>
                              setCatalogForm((current) => ({
                                ...current,
                                tracking_mode: event.target
                                  .value as PharmacyInventoryTrackingMode,
                              }))
                            }
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                          >
                            <option value="LOT_TRACKED">Lot Tracked</option>
                            <option value="QUANTITY_ONLY">Quantity Only</option>
                            <option value="SERIALIZED">Serialized</option>
                          </select>
                        </div>
                        <label className="flex items-center gap-3 rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={catalogForm.requires_expiry}
                            onChange={(event) =>
                              setCatalogForm((current) => ({
                                ...current,
                                requires_expiry: event.target.checked,
                              }))
                            }
                            className="h-4 w-4 rounded border-slate-300"
                          />
                          Requires expiry tracking
                        </label>
                      </div>
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Justification</label>
                        <textarea
                          value={catalogForm.justification}
                          onChange={(event) =>
                            setCatalogForm((current) => ({
                              ...current,
                              justification: event.target.value,
                            }))
                          }
                          className="min-h-[120px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                          placeholder="Why this item should enter hospital operations"
                        />
                      </div>
                      <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                        <span>Workflow: HOD request → CMD approval → Accounts pricing → activation</span>
                        <Button
                          type="submit"
                          isLoading={catalogSubmitting}
                          disabled={
                            catalogSubmitting ||
                            !catalogForm.generic_name ||
                            !catalogForm.dosage_form ||
                            !catalogForm.dispense_unit ||
                            !catalogForm.justification
                          }
                        >
                          Submit Request
                        </Button>
                      </div>
                    </form>
                  </Card>

                  <Card title="Request Timeline" titleClassName="text-slate-900">
                    {configurationRequests.length === 0 ? (
                      <EmptyState
                        title="No catalog requests yet"
                        detail="Submit a new item request to begin the CMD and Accounts governance chain."
                      />
                    ) : (
                      <div className="space-y-3">
                        {configurationRequests.map((row) => (
                          <div key={row.id} className="rounded-2xl border border-slate-200 px-4 py-4">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <p className="font-semibold text-slate-900">
                                  {row.generic_name}
                                  {row.strength ? ` ${row.strength}` : ''}
                                  {row.dosage_form ? ` ${row.dosage_form}` : ''}
                                </p>
                                <p className="mt-1 text-sm text-slate-600">
                                  {row.catalog_code} • Requested by {row.requested_by_name || 'Unknown'}
                                </p>
                              </div>
                              <div className="flex flex-wrap items-center gap-2">
                                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${catalogStatusClass(row.lifecycle_status)}`}>
                                  {workflowLabel(row.lifecycle_status)}
                                </span>
                                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${catalogStatusClass(row.billing_status)}`}>
                                  Billing: {workflowLabel(row.billing_status)}
                                </span>
                              </div>
                            </div>
                            <p className="mt-3 text-sm text-slate-600">{row.justification}</p>
                            <div className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                              <span>Submitted: {formatDateTime(row.submitted_at)}</span>
                              <span>CMD Review: {formatDateTime(row.cmd_reviewed_at)}</span>
                              <span>Priced: {formatDateTime(row.priced_at)}</span>
                              <span>
                                Current Price:{' '}
                                {row.current_price_minor !== null && row.current_price_minor !== undefined
                                  ? formatMoney(row.current_price_minor, row.current_currency || 'NGN')
                                  : 'Pending'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
