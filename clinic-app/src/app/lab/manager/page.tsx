'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardHero } from '@/app/components/DashboardHero';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';
import { HOSPITAL_NAME } from '@/shared/constants/branding';
import { LAB_MANAGER_THEME } from '@/domains/lab/constants/labManagerTheme';
import { useLabManagerBadges } from '@/domains/lab/hooks/useLabManagerBadges';
import {
  LabManagerActivityAuditItem,
  LabManagerBadgeSectionKey,
  LabManagerConfigurationRequest,
  LabManagerConfigurationRequestCreate,
  LabManagerCriticalAlert,
  LabManagerDashboard,
  LabManagerPendingVerification,
  LabManagerReceiptRegisterRow,
  LabManagerSalesRevenueRow,
  LabManagerSpecimenIssue,
  LabManagerStaffPerformance,
  LabManagerStaffSummary,
  LabManagerUnitOperation,
  labManagerService,
} from '@/domains/lab/services/labManagerService';

type ManagerSectionId =
  | 'overview'
  | 'unit-operations'
  | 'staff-control'
  | 'unit-assignment'
  | 'pending-verifications'
  | 'critical-alerts'
  | 'specimen-issues'
  | 'quality-control'
  | 'activity-audit'
  | 'staff-performance'
  | 'sales-revenue'
  | 'receipt-register'
  | 'reports-analytics'
  | 'configuration-requests';

interface StaffAssignmentFormState {
  allowed_lab_unit_ids: string[];
  default_lab_unit_id: string | null;
  assignment_status: 'ACTIVE' | 'TEMP_COVERAGE' | 'ON_LEAVE' | 'RESTRICTED' | 'INACTIVE';
  coverage_note: string;
}

const managerSections: Array<{ id: ManagerSectionId; label: string; description: string }> = [
  { id: 'overview', label: 'Overview', description: 'Department command center' },
  { id: 'unit-operations', label: 'Unit Operations', description: 'Real-time unit workload' },
  { id: 'staff-control', label: 'Staff Control', description: 'Person-centered staff governance' },
  { id: 'unit-assignment', label: 'Unit Assignment', description: 'Operational staffing by bench' },
  { id: 'pending-verifications', label: 'Pending Verifications', description: 'Release-blocking queue' },
  { id: 'critical-alerts', label: 'Critical Alerts', description: 'Patient-safety oversight' },
  { id: 'specimen-issues', label: 'Specimen Issues', description: 'Rejected, delayed, and lost samples' },
  { id: 'quality-control', label: 'Quality Control', description: 'QC runs, failures, and overrides' },
  { id: 'activity-audit', label: 'Activity Audit', description: 'Departmental governance and traceability' },
  { id: 'staff-performance', label: 'Staff Performance', description: 'Operational analytics, not ranking' },
  { id: 'sales-revenue', label: 'Sales & Revenue', description: 'Read-only lab revenue visibility' },
  { id: 'receipt-register', label: 'Receipt Register', description: 'Receipt traceability by lab item' },
  { id: 'reports-analytics', label: 'Reports & Analytics', description: 'Volume, quality, and trend reporting' },
  { id: 'configuration-requests', label: 'Configuration Requests', description: 'Request workflow, not direct admin' },
];

const requestTypeOptions: Array<LabManagerConfigurationRequest['request_type']> = [
  'NEW_STAFF_ACCOUNT',
  'ROLE_ADJUSTMENT',
  'NEW_TEST_ACTIVATION',
  'PRICE_REVIEW',
  'TEMPLATE_ADJUSTMENT',
  'UNIT_CONFIGURATION_CHANGE',
];

const badgeSectionByManagerSection: Partial<Record<ManagerSectionId, LabManagerBadgeSectionKey>> = {
  'pending-verifications': 'PENDING_VERIFICATIONS',
  'critical-alerts': 'CRITICAL_ALERTS',
  'specimen-issues': 'SPECIMEN_ISSUES',
  'quality-control': 'QUALITY_CONTROL',
  'sales-revenue': 'SALES_REVENUE',
  'receipt-register': 'RECEIPT_REGISTER',
};

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en-NG', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatMoney(amountMinor: number, currency: string): string {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amountMinor / 100);
}

function formatMinutes(minutes?: number | null): string {
  if (minutes === null || minutes === undefined) return '—';
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainder = Math.round(minutes % 60);
  return `${hours}h ${remainder}m`;
}

function formatVisitReference(visitId?: string | null): string {
  if (!visitId) return '—';
  return `Visit ${visitId.slice(0, 8).toUpperCase()}`;
}

function titleize(value: string): string {
  return value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function statusTone(value: string): string {
  if (['CRITICAL', 'REJECTED', 'FAIL', 'ESCALATED', 'LOST'].includes(value)) {
    return 'bg-rose-50 text-rose-700 border-rose-200';
  }
  if (['SUBMITTED', 'WARNING', 'ACKNOWLEDGED', 'TEMP_COVERAGE'].includes(value)) {
    return 'bg-amber-50 text-amber-700 border-amber-200';
  }
  if (['VERIFIED', 'RELEASED', 'PASS', 'ACTIVE'].includes(value)) {
    return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  }
  return 'bg-slate-100 text-slate-700 border-slate-200';
}

function severityTone(value: string): string {
  if (value === 'critical' || value === 'CRITICAL') return 'border-l-rose-500 bg-rose-50';
  if (value === 'warning' || value === 'HIGH' || value === 'ESCALATED') return 'border-l-amber-500 bg-amber-50';
  return 'border-l-slate-300 bg-white';
}

function badgeToneStyles(tone: 'critical' | 'warning' | 'info'): string {
  if (tone === 'critical') {
    return 'bg-[#DC2626] text-white ring-1 ring-white/20';
  }
  if (tone === 'warning') {
    return 'bg-[#F59E0B] text-white ring-1 ring-white/20';
  }
  return 'bg-[#2563EB] text-white ring-1 ring-white/20';
}

function matchesSearch(values: Array<string | null | undefined>, term: string): boolean {
  if (!term.trim()) return true;
  const normalized = term.trim().toLowerCase();
  return values.some((value) => value?.toLowerCase().includes(normalized));
}

function buildAssignmentState(staff: LabManagerStaffSummary | null): StaffAssignmentFormState {
  if (!staff) {
    return {
      allowed_lab_unit_ids: [],
      default_lab_unit_id: null,
      assignment_status: 'ACTIVE',
      coverage_note: '',
    };
  }
  return {
    allowed_lab_unit_ids: staff.allowed_units.map((unit) => unit.id),
    default_lab_unit_id: staff.default_unit_id || null,
    assignment_status: staff.assignment_status,
    coverage_note: staff.coverage_note || '',
  };
}

function MetricTile({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-slate-900">{value}</p>
      {detail ? <p className="mt-2 text-sm text-slate-600">{detail}</p> : null}
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
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{eyebrow}</p>
      <div>
        <h2 className="text-2xl font-semibold text-slate-950">{title}</h2>
        <p className="mt-1 text-sm text-slate-600">{description}</p>
      </div>
    </div>
  );
}

export default function LabManagerPage() {
  const dashboardUser = useDashboardUser();
  const router = useRouter();
  const { snapshot: badgeSnapshot, markViewed: markBadgeViewed } = useLabManagerBadges({
    enabled: dashboardUser?.role === 'LAB_MANAGER',
  });
  const [activeSection, setActiveSection] = useState<ManagerSectionId>('overview');
  const [dashboard, setDashboard] = useState<LabManagerDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [startDate, setStartDate] = useState(todayIsoDate());
  const [endDate, setEndDate] = useState(todayIsoDate());
  const [selectedStaffId, setSelectedStaffId] = useState<string | null>(null);
  const [assignmentForm, setAssignmentForm] = useState<StaffAssignmentFormState>(
    buildAssignmentState(null)
  );
  const [assignmentSaving, setAssignmentSaving] = useState(false);
  const [auditSearch, setAuditSearch] = useState('');
  const [auditUnitFilter, setAuditUnitFilter] = useState('ALL');
  const [auditStaffFilter, setAuditStaffFilter] = useState('ALL');
  const [auditActionFilter, setAuditActionFilter] = useState('ALL');
  const [selectedAuditId, setSelectedAuditId] = useState<string | null>(null);
  const [staffSearch, setStaffSearch] = useState('');
  const [staffRoleFilter, setStaffRoleFilter] = useState('ALL');
  const [staffUnitFilter, setStaffUnitFilter] = useState('ALL');
  const [pendingSearch, setPendingSearch] = useState('');
  const [pendingUnitFilter, setPendingUnitFilter] = useState('ALL');
  const [pendingPolicyFilter, setPendingPolicyFilter] = useState('ALL');
  const [criticalSearch, setCriticalSearch] = useState('');
  const [criticalUnitFilter, setCriticalUnitFilter] = useState('ALL');
  const [criticalStatusFilter, setCriticalStatusFilter] = useState('ALL');
  const [specimenSearch, setSpecimenSearch] = useState('');
  const [specimenUnitFilter, setSpecimenUnitFilter] = useState('ALL');
  const [specimenIssueFilter, setSpecimenIssueFilter] = useState('ALL');
  const [salesSearch, setSalesSearch] = useState('');
  const [salesUnitFilter, setSalesUnitFilter] = useState('ALL');
  const [salesCashierFilter, setSalesCashierFilter] = useState('ALL');
  const [salesPaymentFilter, setSalesPaymentFilter] = useState('ALL');
  const [salesStatusFilter, setSalesStatusFilter] = useState('ALL');
  const [receiptSearch, setReceiptSearch] = useState('');
  const [receiptUnitFilter, setReceiptUnitFilter] = useState('ALL');
  const [receiptCashierFilter, setReceiptCashierFilter] = useState('ALL');
  const [performanceSearch, setPerformanceSearch] = useState('');
  const [performanceRoleFilter, setPerformanceRoleFilter] = useState('ALL');
  const [performanceUnitFilter, setPerformanceUnitFilter] = useState('ALL');
  const [requestForm, setRequestForm] = useState<LabManagerConfigurationRequestCreate>({
    request_type: 'NEW_STAFF_ACCOUNT',
    justification: '',
    linked_staff_id: null,
    linked_unit_id: null,
    linked_test_code: '',
    request_payload_json: {},
  });
  const [requestSaving, setRequestSaving] = useState(false);
  const lastViewedBadgeMarkerRef = useRef<string | null>(null);

  useEffect(() => {
    if (dashboardUser && dashboardUser.role !== 'LAB_MANAGER') {
      router.replace('/confirm-access');
    }
  }, [dashboardUser, router]);

  const loadDashboard = useCallback(async (mode: 'initial' | 'refresh' = 'initial') => {
    try {
      if (mode === 'initial') {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);
      const data = await labManagerService.getDashboard(startDate, endDate);
      setDashboard(data);
      setFlashMessage(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to load laboratory HOD dashboard.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [endDate, startDate]);

  useEffect(() => {
    if (dashboardUser?.role !== 'LAB_MANAGER') {
      return;
    }
    void loadDashboard('initial');
  }, [dashboardUser?.role]);

  const badgeMap = useMemo(() => {
    const next = new Map<LabManagerBadgeSectionKey, { count: number; tone: 'critical' | 'warning' | 'info' }>();
    for (const item of badgeSnapshot?.sections || []) {
      next.set(item.section_key, {
        count: item.count,
        tone: item.tone,
      });
    }
    return next;
  }, [badgeSnapshot]);

  useEffect(() => {
    if (!dashboard || loading) {
      return;
    }
    const sectionKey = badgeSectionByManagerSection[activeSection];
    if (!sectionKey) {
      return;
    }
    const badgeState = badgeMap.get(sectionKey);
    const marker = `${sectionKey}:${badgeState?.count ?? 0}`;
    if (lastViewedBadgeMarkerRef.current === marker) {
      return;
    }
    lastViewedBadgeMarkerRef.current = marker;

    const timeout = window.setTimeout(() => {
      void (async () => {
        if (badgeState && badgeState.count > 0) {
          await loadDashboard('refresh');
        }
        await markBadgeViewed(sectionKey);
      })();
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [activeSection, badgeMap, dashboard, loadDashboard, loading, markBadgeViewed]);

  useEffect(() => {
    if (!dashboard?.staff?.length) {
      setSelectedStaffId(null);
      setAssignmentForm(buildAssignmentState(null));
      return;
    }
    const selected = dashboard.staff.find((staff) => staff.user_id === selectedStaffId);
    const resolved = selected || dashboard.staff[0];
    setSelectedStaffId(resolved.user_id);
    setAssignmentForm(buildAssignmentState(resolved));
  }, [dashboard?.staff, selectedStaffId]);

  useEffect(() => {
    if (!dashboard?.activity_audit?.length) {
      setSelectedAuditId(null);
      return;
    }
    if (!selectedAuditId || !dashboard.activity_audit.some((item) => item.id === selectedAuditId)) {
      setSelectedAuditId(dashboard.activity_audit[0].id);
    }
  }, [dashboard?.activity_audit, selectedAuditId]);

  const units = dashboard?.units || [];
  const selectedStaff = useMemo(
    () => dashboard?.staff.find((staff) => staff.user_id === selectedStaffId) || null,
    [dashboard?.staff, selectedStaffId]
  );
  const selectedAuditItem = useMemo(
    () => dashboard?.activity_audit.find((item) => item.id === selectedAuditId) || null,
    [dashboard?.activity_audit, selectedAuditId]
  );

  const filteredStaff = useMemo(() => {
    const rows = dashboard?.staff || [];
    return rows.filter((staff) => {
      const matchesRole = staffRoleFilter === 'ALL' || staff.role === staffRoleFilter;
      const matchesUnit =
        staffUnitFilter === 'ALL' || staff.allowed_units.some((unit) => unit.id === staffUnitFilter);
      const matchesText = matchesSearch(
        [staff.full_name, staff.email, staff.default_unit_name, staff.recent_activity_summary],
        staffSearch
      );
      return matchesRole && matchesUnit && matchesText;
    });
  }, [dashboard?.staff, staffRoleFilter, staffUnitFilter, staffSearch]);

  const staffByUnit = useMemo(() => {
    const grouped: Record<string, LabManagerStaffSummary[]> = {};
    units.forEach((unit) => {
      grouped[unit.id] = (dashboard?.staff || []).filter((staff) =>
        staff.allowed_units.some((allowedUnit) => allowedUnit.id === unit.id)
      );
    });
    return grouped;
  }, [dashboard?.staff, units]);

  const filteredPendingVerifications = useMemo(() => {
    return (dashboard?.pending_verifications || []).filter((row) => {
      const matchesUnit = pendingUnitFilter === 'ALL' || row.unit_id === pendingUnitFilter;
      const matchesPolicy =
        pendingPolicyFilter === 'ALL' || row.verification_policy === pendingPolicyFilter;
      const matchesText = matchesSearch(
        [row.patient_name, row.patient_mrn, row.test_name, row.accession_number, row.entered_by_name],
        pendingSearch
      );
      return matchesUnit && matchesPolicy && matchesText;
    });
  }, [dashboard?.pending_verifications, pendingPolicyFilter, pendingSearch, pendingUnitFilter]);

  const filteredCriticalAlerts = useMemo(() => {
    return (dashboard?.critical_alerts || []).filter((row) => {
      const matchesUnit = criticalUnitFilter === 'ALL' || row.unit_id === criticalUnitFilter;
      const matchesStatus = criticalStatusFilter === 'ALL' || row.status === criticalStatusFilter;
      const matchesText = matchesSearch(
        [row.patient_name, row.patient_mrn, row.test_name, row.message],
        criticalSearch
      );
      return matchesUnit && matchesStatus && matchesText;
    });
  }, [criticalSearch, criticalStatusFilter, criticalUnitFilter, dashboard?.critical_alerts]);

  const filteredSpecimenIssues = useMemo(() => {
    return (dashboard?.specimen_issues || []).filter((row) => {
      const matchesUnit = specimenUnitFilter === 'ALL' || row.unit_id === specimenUnitFilter;
      const matchesIssue = specimenIssueFilter === 'ALL' || row.issue_type === specimenIssueFilter;
      const matchesText = matchesSearch(
        [row.patient_name, row.patient_mrn, row.test_name, row.accession_number, row.issue_type, row.responsible_staff_name],
        specimenSearch
      );
      return matchesUnit && matchesIssue && matchesText;
    });
  }, [dashboard?.specimen_issues, specimenIssueFilter, specimenSearch, specimenUnitFilter]);

  const filteredAuditItems = useMemo(() => {
    return (dashboard?.activity_audit || []).filter((item) => {
      const matchesUnit = auditUnitFilter === 'ALL' || item.unit_id === auditUnitFilter;
      const matchesStaff = auditStaffFilter === 'ALL' || item.actor_id === auditStaffFilter;
      const matchesAction = auditActionFilter === 'ALL' || item.action_type === auditActionFilter;
      const matchesText = matchesSearch(
        [
          item.summary,
          item.detail,
          item.patient_name,
          item.patient_mrn,
          item.accession_number,
          item.receipt_number,
          item.actor_name,
        ],
        auditSearch
      );
      return matchesUnit && matchesStaff && matchesAction && matchesText;
    });
  }, [dashboard?.activity_audit, auditActionFilter, auditSearch, auditStaffFilter, auditUnitFilter]);

  const filteredPerformance = useMemo(() => {
    return (dashboard?.staff_performance || []).filter((item) => {
      const matchesRole = performanceRoleFilter === 'ALL' || item.role === performanceRoleFilter;
      const matchesUnit =
        performanceUnitFilter === 'ALL' || item.unit_names.includes(units.find((unit) => unit.id === performanceUnitFilter)?.name || '');
      const matchesText = matchesSearch([item.full_name, item.unit_names.join(', ')], performanceSearch);
      return matchesRole && matchesUnit && matchesText;
    });
  }, [dashboard?.staff_performance, performanceRoleFilter, performanceUnitFilter, performanceSearch, units]);

  const filteredSalesRows = useMemo(() => {
    return (dashboard?.sales_revenue.rows || []).filter((row) => {
      const matchesUnit = salesUnitFilter === 'ALL' || row.unit_id === salesUnitFilter;
      const matchesCashier = salesCashierFilter === 'ALL' || row.cashier_name === salesCashierFilter;
      const matchesPayment = salesPaymentFilter === 'ALL' || row.payment_method === salesPaymentFilter;
      const matchesStatus = salesStatusFilter === 'ALL' || row.status === salesStatusFilter;
      const matchesText = matchesSearch(
        [row.receipt_number, row.patient_name, row.patient_mrn, row.test_name, row.cashier_name],
        salesSearch
      );
      return matchesUnit && matchesCashier && matchesPayment && matchesStatus && matchesText;
    });
  }, [dashboard?.sales_revenue.rows, salesCashierFilter, salesPaymentFilter, salesSearch, salesStatusFilter, salesUnitFilter]);

  const filteredReceiptRows = useMemo(() => {
    return (dashboard?.receipt_register.rows || []).filter((row) => {
      const matchesUnit =
        receiptUnitFilter === 'ALL' || row.unit_names.some((unitName) => unitName === units.find((unit) => unit.id === receiptUnitFilter)?.name);
      const matchesCashier = receiptCashierFilter === 'ALL' || row.cashier_name === receiptCashierFilter;
      const matchesText = matchesSearch(
        [row.receipt_number, row.patient_name, row.patient_mrn, row.cashier_name, row.linked_test_items.join(', ')],
        receiptSearch
      );
      return matchesUnit && matchesCashier && matchesText;
    });
  }, [dashboard?.receipt_register.rows, receiptCashierFilter, receiptSearch, receiptUnitFilter, units]);

  const uniqueAuditActions = useMemo(
    () => Array.from(new Set((dashboard?.activity_audit || []).map((item) => item.action_type))),
    [dashboard?.activity_audit]
  );
  const uniqueCriticalStatuses = useMemo(
    () => Array.from(new Set((dashboard?.critical_alerts || []).map((row) => row.status))),
    [dashboard?.critical_alerts]
  );
  const uniqueSpecimenIssueTypes = useMemo(
    () => Array.from(new Set((dashboard?.specimen_issues || []).map((row) => row.issue_type))),
    [dashboard?.specimen_issues]
  );
  const uniqueCashiers = useMemo(
    () => Array.from(new Set((dashboard?.sales_revenue.rows || []).map((row) => row.cashier_name).filter(Boolean))) as string[],
    [dashboard?.sales_revenue.rows]
  );

  const saveSelectedStaffAssignment = async () => {
    if (!selectedStaff) return;
    setAssignmentSaving(true);
    try {
      await labManagerService.updateStaffAssignment(selectedStaff.user_id, {
        allowed_lab_unit_ids: selectedStaff.role === 'LAB_MANAGER' ? [] : assignmentForm.allowed_lab_unit_ids,
        default_lab_unit_id:
          selectedStaff.role === 'LAB_MANAGER' ? null : assignmentForm.default_lab_unit_id,
        assignment_status: assignmentForm.assignment_status,
        coverage_note: assignmentForm.coverage_note || null,
      });
      setFlashMessage(`Updated assignment governance for ${selectedStaff.full_name || selectedStaff.email}.`);
      await loadDashboard('refresh');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to update lab staff assignment.');
    } finally {
      setAssignmentSaving(false);
    }
  };

  const submitConfigurationRequest = async () => {
    if (!requestForm.justification.trim()) {
      setError('Configuration request justification is required.');
      return;
    }
    setRequestSaving(true);
    try {
      await labManagerService.createConfigurationRequest({
        ...requestForm,
        linked_test_code: requestForm.linked_test_code || null,
      });
      setFlashMessage(`${titleize(requestForm.request_type)} request submitted.`);
      setRequestForm({
        request_type: 'NEW_STAFF_ACCOUNT',
        justification: '',
        linked_staff_id: null,
        linked_unit_id: null,
        linked_test_code: '',
        request_payload_json: {},
      });
      await loadDashboard('refresh');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to submit configuration request.');
    } finally {
      setRequestSaving(false);
    }
  };

  if (!dashboardUser || dashboardUser.role !== 'LAB_MANAGER') {
    return null;
  }

  const overview = dashboard?.overview;
  const activeSectionMeta = managerSections.find((item) => item.id === activeSection);

  return (
    <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
      <aside
        className="sticky top-6 h-[calc(100vh-3rem)] overflow-hidden rounded-[30px] border shadow-2xl"
        style={{
          background: LAB_MANAGER_THEME.sidebarBackground,
          color: LAB_MANAGER_THEME.sidebarText,
          borderColor: 'rgba(234,242,255,0.16)',
          boxShadow: '0 28px 50px rgba(15, 23, 42, 0.16)',
        }}
      >
        <div className="flex h-full flex-col">
          <div
            className="border-b px-6 py-6"
            style={{ borderColor: 'rgba(234,242,255,0.16)' }}
          >
            <p
              className="text-xs font-semibold uppercase tracking-[0.18em]"
              style={{ color: LAB_MANAGER_THEME.sidebarMutedText }}
            >
              Medical Laboratory
            </p>
            <h1 className="mt-3 text-2xl font-semibold leading-tight">Lab HOD Governance</h1>
            <p className="mt-3 text-sm" style={{ color: LAB_MANAGER_THEME.sidebarMutedText }}>
              {HOSPITAL_NAME}
            </p>
            <div
              className="mt-5 rounded-2xl border px-4 py-3 text-sm"
              style={{
                borderColor: 'rgba(234,242,255,0.16)',
                background: 'rgba(255,255,255,0.06)',
                color: LAB_MANAGER_THEME.sidebarText,
              }}
            >
              <p className="font-medium">{getDashboardUserDisplayName(dashboardUser)}</p>
              <p className="mt-1" style={{ color: LAB_MANAGER_THEME.sidebarMutedText }}>
                Department-only oversight workspace
              </p>
            </div>
          </div>

          <div className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
            {managerSections.map((section, index) => {
              const isActive = section.id === activeSection;
              return (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => setActiveSection(section.id)}
                  className="relative w-full overflow-hidden rounded-2xl border px-4 py-3 text-left transition hover:border-white/10 hover:bg-white/5"
                  style={
                    isActive
                      ? {
                          color: '#FEFEFE',
                          background: LAB_MANAGER_THEME.sidebarActiveGradient,
                          borderColor: 'rgba(234,242,255,0.18)',
                          boxShadow: LAB_MANAGER_THEME.sidebarActiveShadow,
                        }
                      : {
                          color: LAB_MANAGER_THEME.sidebarText,
                          background: 'transparent',
                          borderColor: 'transparent',
                        }
                  }
                >
                  {isActive ? (
                    <span
                      className="absolute inset-y-3 left-0 w-1 rounded-r-full"
                      style={{ background: LAB_MANAGER_THEME.sidebarActiveIndicator }}
                    />
                  ) : null}
                  <div className="flex items-start gap-3">
                    <span
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-xs font-semibold"
                      style={{
                        background: isActive ? 'rgba(254,254,254,0.18)' : 'rgba(255,255,255,0.12)',
                        color: '#FEFEFE',
                      }}
                    >
                      {index + 1}
                    </span>
                    <div>
                      <p className="text-sm font-semibold">{section.label}</p>
                      <p
                        className="mt-1 text-[10px] leading-4"
                        style={{
                          color: isActive ? 'rgba(254,254,254,0.90)' : LAB_MANAGER_THEME.sidebarMutedText,
                        }}
                      >
                        {section.description}
                      </p>
                    </div>
                    {(() => {
                      const badgeKey = badgeSectionByManagerSection[section.id];
                      const badgeState = badgeKey ? badgeMap.get(badgeKey) : undefined;
                      if (!badgeState || badgeState.count <= 0) {
                        return null;
                      }
                      return (
                        <span
                          className={`ml-auto inline-flex min-w-[1.75rem] items-center justify-center rounded-full px-2 py-1 text-[11px] font-semibold ${badgeToneStyles(
                            badgeState.tone
                          )}`}
                        >
                          {badgeState.count > 99 ? '99+' : badgeState.count}
                        </span>
                      );
                    })()}
                  </div>
                </button>
              );
            })}
          </div>

          <div
            className="border-t px-4 py-4"
            style={{ borderColor: 'rgba(234,242,255,0.16)' }}
          >
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
          title="Laboratory HOD Dashboard"
          subtitle={HOSPITAL_NAME}
          workspaceLabel={activeSectionMeta?.description || 'Department governance workspace'}
          monogram="L"
          variant="calm-light"
          accentLabel="Medical Laboratory HOD"
          rightSlot={
            <>
              <div>
                <span className="font-semibold">Scope:</span> Medical Laboratory only
              </div>
              <div>
                <span className="font-semibold">Date range:</span> {startDate} to {endDate}
              </div>
            </>
          }
        />

        <Card>
          <div className="grid gap-4 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
            <Input
              label="Start Date"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
            <Input
              label="End Date"
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
            <div className="flex gap-3">
              <Button onClick={() => void loadDashboard('refresh')} isLoading={refreshing}>
                Apply Range
              </Button>
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
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            {flashMessage}
          </div>
        ) : null}
        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {error}
          </div>
        ) : null}

        {loading ? (
          <Card title="Loading Governance Workspace">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
              Loading laboratory governance data…
            </div>
          </Card>
        ) : error && (!dashboard || !overview) ? (
          <Card title="Governance Workspace Unavailable">
            <div className="space-y-4 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-5">
              <div>
                <p className="text-sm font-semibold text-rose-900">
                  Unable to load the laboratory HOD dashboard.
                </p>
                <p className="mt-2 text-sm text-rose-800">
                  The dashboard request failed, so governance sections cannot load yet. This is not a valid steady state.
                </p>
              </div>
              <div className="rounded-2xl border border-rose-200 bg-white px-4 py-3 text-sm text-slate-700">
                <span className="font-medium text-slate-900">Error detail:</span>{' '}
                {error}
              </div>
              <div className="flex flex-wrap gap-3">
                <Button onClick={() => void loadDashboard('refresh')} isLoading={refreshing}>
                  Retry Dashboard Load
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    const today = todayIsoDate();
                    setStartDate(today);
                    setEndDate(today);
                  }}
                >
                  Reset Date Range
                </Button>
              </div>
            </div>
          </Card>
        ) : !dashboard || !overview ? (
          <Card title="Governance Workspace Unavailable">
            <div className="space-y-4 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-5 text-sm text-amber-900">
              <p className="font-semibold">Laboratory governance data is unavailable.</p>
              <p>
                The dashboard did not return any usable payload. Retry the load or refresh the page.
              </p>
              <div>
                <Button onClick={() => void loadDashboard('refresh')} isLoading={refreshing}>
                  Retry Dashboard Load
                </Button>
              </div>
            </div>
          </Card>
        ) : (
          <>
            {activeSection === 'overview' && (
              <div className="space-y-6">
                <SectionHeading
                  eyebrow="Overview"
                  title="Department Command Center"
                  description="Immediate visibility into workload, verification pressure, quality risk, and read-only revenue signals."
                />
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricTile label="Total Tests Today" value={overview.total_tests_today} />
                  <MetricTile label="Pending Verifications" value={overview.pending_verifications} />
                  <MetricTile label="Critical Alerts Open" value={overview.critical_alerts_open} />
                  <MetricTile label="Rejected Specimens" value={overview.rejected_specimens} />
                  <MetricTile label="QC Failures" value={overview.qc_failures} />
                  <MetricTile label="Revenue Today" value={formatMoney(overview.revenue_today_minor, overview.currency)} />
                  <MetricTile label="Blocked / Unpaid" value={overview.blocked_unpaid_requests} />
                  <MetricTile label="Active Staff On Duty" value={overview.active_staff_on_duty} />
                </div>
                <div className="grid gap-6 xl:grid-cols-[1.35fr_0.9fr]">
                  <Card title="Unit Bottlenecks" titleClassName="text-slate-900">
                    <div className="space-y-4">
                      {dashboard.unit_operations.map((unit) => (
                        <div key={unit.unit_id} className="rounded-2xl border border-slate-200 px-4 py-4">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="text-lg font-semibold text-slate-900">{unit.unit_name}</p>
                              <p className="mt-1 text-sm text-slate-600">
                                Queue {unit.queue_volume} • Staff on duty {unit.staff_on_duty} • Pending verifications {unit.pending_verifications}
                              </p>
                            </div>
                            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
                              {formatMoney(unit.revenue_today_minor, overview.currency)} today
                            </span>
                          </div>
                          <div className="mt-4 flex flex-wrap gap-2">
                            {unit.bottleneck_labels.length ? (
                              unit.bottleneck_labels.map((label) => (
                                <span key={label} className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                                  {label}
                                </span>
                              ))
                            ) : (
                              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                                No active bottleneck
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                  <Card title="Command Signals" titleClassName="text-slate-900">
                    <div className="space-y-4 text-sm text-slate-700">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                        <p className="font-semibold text-slate-900">Immediate focus</p>
                        <p className="mt-2">
                          {overview.bottleneck_units.length
                            ? `Current bottlenecks are concentrated in ${overview.bottleneck_units.join(', ')}.`
                            : 'No unit is currently signalling an elevated bottleneck condition.'}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                        <p className="font-semibold text-slate-900">Clinical safety</p>
                        <p className="mt-2">
                          {overview.critical_alerts_open} critical alert(s) and {overview.pending_verifications} pending verification item(s) are open right now.
                        </p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                        <p className="font-semibold text-slate-900">Revenue visibility</p>
                        <p className="mt-2">
                          Finance data here is read-only. Receipt capture, payment mutation, and refund approval remain outside the HOD dashboard.
                        </p>
                      </div>
                    </div>
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'unit-operations' && (
              <div className="space-y-6">
                <SectionHeading
                  eyebrow="Unit Operations"
                  title="Operational Status By Lab Unit"
                  description="Bench-first oversight for queue pressure, staffing, specimen flow, and current delays."
                />
                <div className="grid gap-5 xl:grid-cols-2">
                  {dashboard.unit_operations.map((unit) => (
                    <Card key={unit.unit_id} title={unit.unit_name} titleClassName="text-slate-900">
                      <div className="grid gap-3 md:grid-cols-2">
                        <MetricTile label="Queue Volume" value={unit.queue_volume} />
                        <MetricTile label="Staff On Duty" value={unit.staff_on_duty} />
                        <MetricTile label="Pending Specimens" value={unit.pending_specimens} />
                        <MetricTile label="Pending Results" value={unit.pending_results} />
                        <MetricTile label="Pending Verifications" value={unit.pending_verifications} />
                        <MetricTile label="Rejected Specimens" value={unit.rejected_specimens} />
                        <MetricTile label="Critical Alerts" value={unit.critical_alerts} />
                        <MetricTile label="Revenue Today" value={formatMoney(unit.revenue_today_minor, overview.currency)} />
                      </div>
                      <div className="mt-5 space-y-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                        <p className="text-sm font-semibold text-slate-900">Bottlenecks / delays</p>
                        <div className="flex flex-wrap gap-2">
                          {unit.bottleneck_labels.length ? (
                            unit.bottleneck_labels.map((label) => (
                              <span key={label} className="rounded-full border border-amber-200 bg-white px-3 py-1 text-xs font-medium text-amber-700">
                                {label}
                              </span>
                            ))
                          ) : (
                            <span className="rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-medium text-emerald-700">
                              Unit operating without flagged backlog
                            </span>
                          )}
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {activeSection === 'staff-control' && (
              <div className="space-y-6">
                <SectionHeading
                  eyebrow="Staff Control"
                  title="Person-Centered Lab Workforce Governance"
                  description="Manage operational assignment scope without crossing into global identity administration."
                />
                <Card>
                  <div className="grid gap-4 md:grid-cols-3">
                    <Input label="Search Staff" value={staffSearch} onChange={(event) => setStaffSearch(event.target.value)} placeholder="Name, email, recent activity" />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Role</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={staffRoleFilter} onChange={(event) => setStaffRoleFilter(event.target.value)}>
                        <option value="ALL">All roles</option>
                        <option value="LAB">Legacy Lab</option>
                        <option value="LAB_TECH">Lab Tech</option>
                        <option value="LAB_SCIENTIST">Lab Scientist</option>
                        <option value="LAB_SUPERVISOR">Lab Supervisor</option>
                        <option value="LAB_MANAGER">Lab Manager</option>
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={staffUnitFilter} onChange={(event) => setStaffUnitFilter(event.target.value)}>
                        <option value="ALL">All units</option>
                        {units.map((unit) => (
                          <option key={unit.id} value={unit.id}>{unit.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </Card>
                <div className="grid gap-6 xl:grid-cols-[1.15fr_0.95fr]">
                  <Card title="Lab Staff Directory" titleClassName="text-slate-900">
                    <div className="space-y-3">
                      {filteredStaff.map((staff) => {
                        const selected = staff.user_id === selectedStaffId;
                        return (
                          <button
                            key={staff.user_id}
                            type="button"
                            onClick={() => {
                              setSelectedStaffId(staff.user_id);
                              setAssignmentForm(buildAssignmentState(staff));
                            }}
                            className={`w-full rounded-2xl border px-4 py-4 text-left transition ${selected ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white hover:border-slate-300'}`}
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <p className={`text-base font-semibold ${selected ? 'text-white' : 'text-slate-900'}`}>
                                  {staff.full_name || staff.email}
                                </p>
                                <p className={`mt-1 text-sm ${selected ? 'text-slate-200' : 'text-slate-600'}`}>
                                  {titleize(staff.role)} • {staff.default_unit_name || 'No default unit'}
                                </p>
                              </div>
                              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${selected ? 'border-white/20 bg-white/10 text-white' : statusTone(staff.assignment_status)}`}>
                                {titleize(staff.assignment_status)}
                              </span>
                            </div>
                            <p className={`mt-3 text-sm ${selected ? 'text-slate-200' : 'text-slate-600'}`}>
                              {staff.recent_activity_summary || 'No recent department activity recorded.'}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-2">
                              {staff.allowed_units.length ? (
                                staff.allowed_units.map((unit) => (
                                  <span key={unit.id} className={`rounded-full px-3 py-1 text-xs font-medium ${selected ? 'bg-white/10 text-white' : 'bg-slate-100 text-slate-700'}`}>
                                    {unit.name}
                                  </span>
                                ))
                              ) : (
                                <span className={`rounded-full px-3 py-1 text-xs font-medium ${selected ? 'bg-white/10 text-white' : 'bg-slate-100 text-slate-700'}`}>
                                  No operational unit assignment
                                </span>
                              )}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </Card>

                  <Card title="Assignment Governance" titleClassName="text-slate-900">
                    {selectedStaff ? (
                      <div className="space-y-5">
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                          <p className="text-lg font-semibold text-slate-900">{selectedStaff.full_name || selectedStaff.email}</p>
                          <p className="mt-1 text-sm text-slate-600">{selectedStaff.email}</p>
                          <div className="mt-3 flex flex-wrap gap-2 text-xs">
                            <span className={`rounded-full border px-3 py-1 font-semibold ${statusTone(selectedStaff.assignment_status)}`}>
                              {titleize(selectedStaff.assignment_status)}
                            </span>
                            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 font-semibold text-slate-700">
                              {titleize(selectedStaff.role)}
                            </span>
                          </div>
                          <p className="mt-4 text-sm text-slate-600">
                            Recent activity: {selectedStaff.recent_activity_summary || 'No recent activity'}
                          </p>
                          <p className="mt-1 text-sm text-slate-500">
                            Last update: {formatDateTime(selectedStaff.last_updated_at)} by {selectedStaff.last_updated_by_name || '—'}
                          </p>
                        </div>

                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700">Department Assignment Status</label>
                          <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                            value={assignmentForm.assignment_status}
                            onChange={(event) =>
                              setAssignmentForm((current) => ({
                                ...current,
                                assignment_status: event.target.value as StaffAssignmentFormState['assignment_status'],
                              }))
                            }
                          >
                            <option value="ACTIVE">Active</option>
                            <option value="TEMP_COVERAGE">Temporary Coverage</option>
                            <option value="ON_LEAVE">On Leave</option>
                            <option value="RESTRICTED">Restricted Duty</option>
                            <option value="INACTIVE">Inactive</option>
                          </select>
                        </div>

                        {selectedStaff.role !== 'LAB_MANAGER' ? (
                          <>
                            <div>
                              <p className="mb-2 text-sm font-medium text-slate-700">Allowed Lab Units</p>
                              <div className="grid gap-2 md:grid-cols-2">
                                {units.map((unit) => {
                                  const checked = assignmentForm.allowed_lab_unit_ids.includes(unit.id);
                                  return (
                                    <label key={unit.id} className="flex items-center gap-3 rounded-2xl border border-slate-200 px-3 py-3 text-sm text-slate-700">
                                      <input
                                        type="checkbox"
                                        checked={checked}
                                        onChange={(event) => {
                                          const nextIds = event.target.checked
                                            ? [...assignmentForm.allowed_lab_unit_ids, unit.id]
                                            : assignmentForm.allowed_lab_unit_ids.filter((id) => id !== unit.id);
                                          setAssignmentForm((current) => ({
                                            ...current,
                                            allowed_lab_unit_ids: Array.from(new Set(nextIds)),
                                            default_lab_unit_id:
                                              current.default_lab_unit_id && !Array.from(new Set(nextIds)).includes(current.default_lab_unit_id)
                                                ? Array.from(new Set(nextIds))[0] || null
                                                : current.default_lab_unit_id,
                                          }));
                                        }}
                                      />
                                      <span>{unit.name}</span>
                                    </label>
                                  );
                                })}
                              </div>
                            </div>

                            <div>
                              <label className="mb-1 block text-sm font-medium text-slate-700">Default Unit</label>
                              <select
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                                value={assignmentForm.default_lab_unit_id || ''}
                                onChange={(event) =>
                                  setAssignmentForm((current) => ({
                                    ...current,
                                    default_lab_unit_id: event.target.value || null,
                                  }))
                                }
                              >
                                <option value="">Select default unit</option>
                                {units
                                  .filter((unit) => assignmentForm.allowed_lab_unit_ids.includes(unit.id))
                                  .map((unit) => (
                                    <option key={unit.id} value={unit.id}>{unit.name}</option>
                                  ))}
                              </select>
                            </div>
                          </>
                        ) : (
                          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                            LAB_MANAGER accounts use department governance access, not operational bench-unit assignment.
                          </div>
                        )}

                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700">Shift / Coverage Note</label>
                          <textarea
                            className="min-h-[120px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                            value={assignmentForm.coverage_note}
                            onChange={(event) =>
                              setAssignmentForm((current) => ({ ...current, coverage_note: event.target.value }))
                            }
                            placeholder="Document temporary coverage, shift note, or assignment context for this staff member."
                          />
                        </div>

                        <div className="flex flex-wrap gap-3">
                          <Button onClick={() => void saveSelectedStaffAssignment()} isLoading={assignmentSaving}>
                            Save Assignment Governance
                          </Button>
                          <Button
                            variant="secondary"
                            onClick={() => {
                              setRequestForm((current) => ({
                                ...current,
                                request_type: 'ROLE_ADJUSTMENT',
                                linked_staff_id: selectedStaff.user_id,
                                linked_unit_id: selectedStaff.default_unit_id || selectedStaff.allowed_units[0]?.id || null,
                                justification: current.justification || `Request role adjustment review for ${selectedStaff.full_name || selectedStaff.email}.`,
                              }));
                              setActiveSection('configuration-requests');
                            }}
                          >
                            Request Role Adjustment
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                        Select a lab staff member to review and update their department assignment governance.
                      </div>
                    )}
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'unit-assignment' && (
              <div className="space-y-6">
                <SectionHeading
                  eyebrow="Unit Assignment"
                  title="Operational Staffing By Bench"
                  description="Assign one or multiple lab units per staff member and detect thin coverage quickly."
                />
                <div className="grid gap-6 xl:grid-cols-2">
                  {units.map((unit) => {
                    const staffRows = staffByUnit[unit.id] || [];
                    return (
                      <Card key={unit.id} title={unit.name} titleClassName="text-slate-900">
                        <div className="space-y-3">
                          <div className="flex items-center justify-between text-sm text-slate-600">
                            <span>Assigned staff</span>
                            <span className="font-semibold text-slate-900">{staffRows.length}</span>
                          </div>
                          {staffRows.length ? (
                            staffRows.map((staff) => (
                              <button
                                key={staff.user_id}
                                type="button"
                                onClick={() => {
                                  setActiveSection('staff-control');
                                  setSelectedStaffId(staff.user_id);
                                  setAssignmentForm(buildAssignmentState(staff));
                                }}
                                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-left hover:border-slate-300"
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <div>
                                    <p className="font-semibold text-slate-900">{staff.full_name || staff.email}</p>
                                    <p className="mt-1 text-sm text-slate-600">{titleize(staff.role)} • Default {staff.default_unit_name || '—'}</p>
                                  </div>
                                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusTone(staff.assignment_status)}`}>
                                    {titleize(staff.assignment_status)}
                                  </span>
                                </div>
                              </button>
                            ))
                          ) : (
                            <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                              No lab staff are currently assigned to this unit.
                            </div>
                          )}
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </div>
            )}

            {activeSection === 'pending-verifications' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Pending Verifications" title="Verification Oversight" description="See what is holding clinical release without bypassing the sealed authority model." />
                <Card>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <Input
                      label="Search"
                      value={pendingSearch}
                      onChange={(event) => setPendingSearch(event.target.value)}
                      placeholder="Patient, MRN, accession, test, entering user"
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={pendingUnitFilter} onChange={(event) => setPendingUnitFilter(event.target.value)}>
                        <option value="ALL">All units</option>
                        {units.map((unit) => (
                          <option key={unit.id} value={unit.id}>{unit.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Verification Policy</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={pendingPolicyFilter} onChange={(event) => setPendingPolicyFilter(event.target.value)}>
                        <option value="ALL">All policies</option>
                        <option value="OPTIONAL">Optional</option>
                        <option value="REQUIRED_BEFORE_RELEASE">Required Before Release</option>
                        <option value="REQUIRED_IF_ABNORMAL">Required If Abnormal</option>
                        <option value="REQUIRED_IF_CRITICAL">Required If Critical</option>
                      </select>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                      <p className="font-semibold text-slate-900">Oversight only</p>
                      <p className="mt-2">This queue exposes release bottlenecks. It does not grant clinical verification authority by title alone.</p>
                    </div>
                  </div>
                </Card>
                <Card title="Verification Queue" titleClassName="text-slate-900">
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-slate-50 text-slate-600">
                        <tr>
                            <th className="px-4 py-3 text-left font-medium">Patient</th>
                            <th className="px-4 py-3 text-left font-medium">Visit</th>
                            <th className="px-4 py-3 text-left font-medium">Test</th>
                            <th className="px-4 py-3 text-left font-medium">Accession</th>
                            <th className="px-4 py-3 text-left font-medium">Unit</th>
                          <th className="px-4 py-3 text-left font-medium">Flags</th>
                          <th className="px-4 py-3 text-left font-medium">Entered By</th>
                          <th className="px-4 py-3 text-left font-medium">Waiting</th>
                          <th className="px-4 py-3 text-left font-medium">Policy</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {filteredPendingVerifications.map((row) => (
                          <tr key={row.result_id}>
                            <td className="px-4 py-3 text-slate-700">
                              <p className="font-medium text-slate-900">{row.patient_name || 'Unknown patient'}</p>
                              <p className="text-xs text-slate-500">{row.patient_mrn || 'No MRN'}</p>
                            </td>
                            <td className="px-4 py-3 text-slate-700">{formatVisitReference(row.visit_id)}</td>
                            <td className="px-4 py-3 text-slate-700">{row.test_name}</td>
                            <td className="px-4 py-3 text-slate-700">{row.accession_number || '—'}</td>
                            <td className="px-4 py-3 text-slate-700">{row.unit_name || 'Unassigned'}</td>
                            <td className="px-4 py-3">
                              <div className="flex flex-wrap gap-2">
                                {row.critical ? <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700">Critical</span> : null}
                                {row.abnormal ? <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">Abnormal</span> : null}
                                {!row.abnormal && !row.critical ? <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">No flag</span> : null}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-slate-700">{row.entered_by_name || '—'}</td>
                            <td className="px-4 py-3 text-slate-700">{formatMinutes(row.waiting_minutes)}</td>
                            <td className="px-4 py-3 text-slate-700">{titleize(row.verification_policy)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!filteredPendingVerifications.length ? (
                    <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                      No pending verification items match the current filters.
                    </div>
                  ) : null}
                </Card>
              </div>
            )}

            {activeSection === 'critical-alerts' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Critical Alerts" title="Critical Result Oversight" description="Department-level visibility into critical values and escalation state." />
                <Card>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <Input
                      label="Search"
                      value={criticalSearch}
                      onChange={(event) => setCriticalSearch(event.target.value)}
                      placeholder="Patient, MRN, analyte, alert message"
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={criticalUnitFilter} onChange={(event) => setCriticalUnitFilter(event.target.value)}>
                        <option value="ALL">All units</option>
                        {units.map((unit) => (
                          <option key={unit.id} value={unit.id}>{unit.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Alert Status</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={criticalStatusFilter} onChange={(event) => setCriticalStatusFilter(event.target.value)}>
                        <option value="ALL">All statuses</option>
                        {uniqueCriticalStatuses.map((statusValue) => (
                          <option key={statusValue} value={statusValue}>{titleize(statusValue)}</option>
                        ))}
                      </select>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                      Follow-up remains governed by the existing critical alert workflow. This section is for HOD monitoring, not unsealed acknowledgement logic.
                    </div>
                  </div>
                </Card>
                <div className="space-y-4">
                  {filteredCriticalAlerts.length ? (
                    filteredCriticalAlerts.map((alert) => (
                      <div key={alert.alert_id} className={`rounded-2xl border border-l-4 p-5 shadow-sm ${severityTone(alert.severity)}`}>
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-lg font-semibold text-slate-900">⚠ {alert.message}</p>
                            <p className="mt-1 text-sm text-slate-600">
                              {alert.patient_name || 'Unknown patient'} • {alert.patient_mrn || 'No MRN'} • {alert.unit_name || 'Unassigned'}
                            </p>
                          </div>
                          <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusTone(alert.status)}`}>
                            {titleize(alert.status)}
                          </span>
                        </div>
                        <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-4">
                          <div>
                            <p className="font-medium text-slate-900">Visit</p>
                            <p>{formatVisitReference(alert.visit_id)}</p>
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">Analyte / test</p>
                            <p>{alert.test_name || '—'}</p>
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">Severity</p>
                            <p>{titleize(alert.severity)}</p>
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">Created</p>
                            <p>{formatDateTime(alert.created_at)}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                      No critical alerts match the current filters.
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeSection === 'specimen-issues' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Specimen Issues" title="Specimen Risk and Traceability" description="Rejected, delayed, and lost specimens with patient and staff context." />
                <Card>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <Input
                      label="Search"
                      value={specimenSearch}
                      onChange={(event) => setSpecimenSearch(event.target.value)}
                      placeholder="Patient, MRN, accession, issue, staff"
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={specimenUnitFilter} onChange={(event) => setSpecimenUnitFilter(event.target.value)}>
                        <option value="ALL">All units</option>
                        {units.map((unit) => (
                          <option key={unit.id} value={unit.id}>{unit.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Issue Type</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={specimenIssueFilter} onChange={(event) => setSpecimenIssueFilter(event.target.value)}>
                        <option value="ALL">All issue types</option>
                        {uniqueSpecimenIssueTypes.map((issueType) => (
                          <option key={issueType} value={issueType}>{titleize(issueType)}</option>
                        ))}
                      </select>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                      Use this view to follow rejection patterns, delayed receipt, and recollection pressure by unit.
                    </div>
                  </div>
                </Card>
                <div className="grid gap-4 xl:grid-cols-2">
                  {filteredSpecimenIssues.length ? (
                    filteredSpecimenIssues.map((issue) => (
                      <Card key={issue.specimen_id} title={`${issue.accession_number} • ${issue.issue_type}`} titleClassName="text-slate-900">
                        <div className="space-y-3 text-sm text-slate-600">
                          <p><span className="font-medium text-slate-900">Patient:</span> {issue.patient_name || 'Unknown patient'} ({issue.patient_mrn || 'No MRN'})</p>
                          <p><span className="font-medium text-slate-900">Visit:</span> {formatVisitReference(issue.visit_id)}</p>
                          <p><span className="font-medium text-slate-900">Test:</span> {issue.test_name}</p>
                          <p><span className="font-medium text-slate-900">Unit:</span> {issue.unit_name || 'Unassigned'}</p>
                          <p><span className="font-medium text-slate-900">Responsible:</span> {issue.responsible_staff_name || '—'}</p>
                          <p><span className="font-medium text-slate-900">Updated:</span> {formatDateTime(issue.updated_at)}</p>
                          {issue.rejection_reason_text ? <p className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-3 text-rose-700">{issue.rejection_reason_text}</p> : null}
                        </div>
                      </Card>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 xl:col-span-2">
                      No specimen issues match the current filters.
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeSection === 'quality-control' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Quality Control" title="QC Monitoring and Override Visibility" description="Governance view into QC performance without opening unsealed edit workflows." />
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                  <MetricTile label="QC Runs" value={dashboard.quality_control.total_runs} />
                  <MetricTile label="QC Failures" value={dashboard.quality_control.fail_runs} />
                  <MetricTile label="Warnings" value={dashboard.quality_control.warning_runs} />
                  <MetricTile label="Override Events" value={dashboard.quality_control.override_events} />
                  <MetricTile label="Unresolved Failures" value={dashboard.quality_control.unresolved_failures} />
                </div>
                <Card title="QC Run Log" titleClassName="text-slate-900">
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-slate-50 text-slate-600">
                        <tr>
                          <th className="px-4 py-3 text-left font-medium">Unit</th>
                          <th className="px-4 py-3 text-left font-medium">QC Level</th>
                          <th className="px-4 py-3 text-left font-medium">Status</th>
                          <th className="px-4 py-3 text-left font-medium">Performed By</th>
                          <th className="px-4 py-3 text-left font-medium">Failures</th>
                          <th className="px-4 py-3 text-left font-medium">Overrides</th>
                          <th className="px-4 py-3 text-left font-medium">Performed</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {dashboard.quality_control.runs.map((row) => (
                          <tr key={row.qc_run_id}>
                            <td className="px-4 py-3">{row.unit_name || 'Unassigned'}</td>
                            <td className="px-4 py-3">{row.qc_level}</td>
                            <td className="px-4 py-3">
                              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusTone(row.status)}`}>
                                {titleize(row.status)}
                              </span>
                            </td>
                            <td className="px-4 py-3">{row.performed_by_name || '—'}</td>
                            <td className="px-4 py-3">{row.fail_count}</td>
                            <td className="px-4 py-3">{row.override_count}</td>
                            <td className="px-4 py-3">{formatDateTime(row.performed_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}

            {activeSection === 'activity-audit' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Activity Audit" title="Human-Readable Department Traceability" description="Readable feed first, drill-down detail second. Filters stay on top for fast review." />
                <Card>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                    <Input label="Search" value={auditSearch} onChange={(event) => setAuditSearch(event.target.value)} placeholder="Patient, MRN, accession, receipt, summary" />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={auditUnitFilter} onChange={(event) => setAuditUnitFilter(event.target.value)}>
                        <option value="ALL">All units</option>
                        {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Staff</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={auditStaffFilter} onChange={(event) => setAuditStaffFilter(event.target.value)}>
                        <option value="ALL">All staff</option>
                        {(dashboard.staff || []).map((staff) => (
                          <option key={staff.user_id} value={staff.user_id}>{staff.full_name || staff.email}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Action Type</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={auditActionFilter} onChange={(event) => setAuditActionFilter(event.target.value)}>
                        <option value="ALL">All actions</option>
                        {uniqueAuditActions.map((action) => <option key={action} value={action}>{titleize(action)}</option>)}
                      </select>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                      <p className="font-semibold text-slate-900">Department-only audit</p>
                      <p className="mt-2">This feed is restricted to Medical Laboratory workflow, finance visibility, and governance requests.</p>
                    </div>
                  </div>
                </Card>
                <div className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
                  <Card title="Audit Feed" titleClassName="text-slate-900">
                    <div className="space-y-3">
                      {filteredAuditItems.map((item) => {
                        const selected = item.id === selectedAuditId;
                        return (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => setSelectedAuditId(item.id)}
                            className={`w-full rounded-2xl border border-l-4 px-4 py-4 text-left transition ${selected ? 'border-slate-900 bg-slate-900 text-white' : severityTone(item.severity)}`}
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <p className={`font-semibold ${selected ? 'text-white' : 'text-slate-900'}`}>{item.summary}</p>
                                <p className={`mt-1 text-sm ${selected ? 'text-slate-200' : 'text-slate-600'}`}>{item.actor_name || 'System'} • {item.unit_name || 'Department'} • {formatDateTime(item.occurred_at)}</p>
                              </div>
                              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${selected ? 'border-white/20 bg-white/10 text-white' : statusTone(item.action_type)}`}>
                                {titleize(item.action_type)}
                              </span>
                            </div>
                            {item.detail ? <p className={`mt-3 text-sm ${selected ? 'text-slate-200' : 'text-slate-600'}`}>{item.detail}</p> : null}
                          </button>
                        );
                      })}
                    </div>
                  </Card>
                  <Card title="Audit Detail" titleClassName="text-slate-900">
                    {selectedAuditItem ? (
                      <div className="space-y-4 text-sm text-slate-700">
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                          <p className="text-lg font-semibold text-slate-900">{selectedAuditItem.summary}</p>
                          <p className="mt-2 text-slate-600">{selectedAuditItem.detail || 'No additional detail captured for this audit item.'}</p>
                        </div>
                        <div className="grid gap-3 md:grid-cols-2">
                          <div><span className="font-medium text-slate-900">Actor:</span> {selectedAuditItem.actor_name || 'System'}</div>
                          <div><span className="font-medium text-slate-900">Role:</span> {selectedAuditItem.actor_role || '—'}</div>
                          <div><span className="font-medium text-slate-900">Patient:</span> {selectedAuditItem.patient_name || '—'}</div>
                          <div><span className="font-medium text-slate-900">MRN:</span> {selectedAuditItem.patient_mrn || '—'}</div>
                          <div><span className="font-medium text-slate-900">Unit:</span> {selectedAuditItem.unit_name || '—'}</div>
                          <div><span className="font-medium text-slate-900">Occurred:</span> {formatDateTime(selectedAuditItem.occurred_at)}</div>
                          <div><span className="font-medium text-slate-900">Accession:</span> {selectedAuditItem.accession_number || '—'}</div>
                          <div><span className="font-medium text-slate-900">Receipt:</span> {selectedAuditItem.receipt_number || '—'}</div>
                        </div>
                        <div>
                          <p className="mb-2 font-medium text-slate-900">Structured metadata</p>
                          <pre className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(selectedAuditItem.metadata_json || {}, null, 2)}</pre>
                        </div>
                      </div>
                    ) : (
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                        Select an audit item to inspect its structured detail.
                      </div>
                    )}
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'staff-performance' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Staff Performance" title="Operational Performance, Not Punitive Ranking" description="Review workload, throughput, quality participation, and pending load without turning the dashboard into a leaderboard." />
                <Card>
                  <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-4">
                    <Input label="Search" value={performanceSearch} onChange={(event) => setPerformanceSearch(event.target.value)} placeholder="Staff or unit" />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Role</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={performanceRoleFilter} onChange={(event) => setPerformanceRoleFilter(event.target.value)}>
                        <option value="ALL">All roles</option>
                        <option value="LAB">Legacy Lab</option>
                        <option value="LAB_TECH">Lab Tech</option>
                        <option value="LAB_SCIENTIST">Lab Scientist</option>
                        <option value="LAB_SUPERVISOR">Lab Supervisor</option>
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={performanceUnitFilter} onChange={(event) => setPerformanceUnitFilter(event.target.value)}>
                        <option value="ALL">All units</option>
                        {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
                      </select>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                      <p className="font-semibold text-slate-900">Interpretation rule</p>
                      <p className="mt-2">Use these measures for workload balancing and process improvement, not punitive ranking.</p>
                    </div>
                  </div>
                </Card>
                <div className="space-y-4">
                  {filteredPerformance.map((item) => (
                    <Card key={item.user_id} title={item.full_name || item.user_id} titleClassName="text-slate-900">
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <MetricTile label="Workload Volume" value={item.workload_volume} detail={titleize(item.role)} />
                        <MetricTile label="Specimens Handled" value={item.specimens_handled} detail={item.unit_names.join(', ') || 'No units'} />
                        <MetricTile label="Results Entered" value={item.results_entered} detail={`Pending load ${item.pending_load}`} />
                        <MetricTile label="Verifications / Releases" value={`${item.verifications_completed} / ${item.releases_completed}`} detail={`QC entries ${item.qc_entries}`} />
                        <MetricTile label="QC Overrides" value={item.qc_overrides} detail={`Patients touched ${item.patients_touched}`} />
                        <MetricTile label="Specimen Issue Rate" value={`${(item.specimen_issue_rate * 100).toFixed(0)}%`} />
                        <MetricTile label="Average Release TAT" value={formatMinutes(item.average_release_turnaround_minutes)} />
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {activeSection === 'sales-revenue' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Sales & Revenue" title="Read-Only Department Revenue Visibility" description="Trace paid lab activity without drifting into cashier or refund control." />
                <Card>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                    <Input label="Search" value={salesSearch} onChange={(event) => setSalesSearch(event.target.value)} placeholder="Receipt, patient, MRN, test, cashier" />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={salesUnitFilter} onChange={(event) => setSalesUnitFilter(event.target.value)}>
                        <option value="ALL">All units</option>
                        {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Cashier</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={salesCashierFilter} onChange={(event) => setSalesCashierFilter(event.target.value)}>
                        <option value="ALL">All cashiers</option>
                        {uniqueCashiers.map((cashier) => <option key={cashier} value={cashier}>{cashier}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Payment Method</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={salesPaymentFilter} onChange={(event) => setSalesPaymentFilter(event.target.value)}>
                        <option value="ALL">All methods</option>
                        <option value="CASH">Cash</option>
                        <option value="CARD">POS / Card</option>
                        <option value="TRANSFER">Transfer</option>
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Status</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={salesStatusFilter} onChange={(event) => setSalesStatusFilter(event.target.value)}>
                        <option value="ALL">All statuses</option>
                        <option value="PAID">Paid</option>
                      </select>
                    </div>
                  </div>
                </Card>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricTile label="Total Revenue" value={formatMoney(dashboard.sales_revenue.total_revenue_minor, dashboard.sales_revenue.currency)} />
                  <MetricTile label="Paid Tests Count" value={dashboard.sales_revenue.paid_tests_count} />
                  <MetricTile label="Receipts Count" value={dashboard.sales_revenue.receipt_count} />
                  <MetricTile label="Blocked / Unpaid" value={dashboard.sales_revenue.blocked_unpaid_count} />
                </div>
                <Card title="Revenue By Unit" titleClassName="text-slate-900">
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    {dashboard.sales_revenue.revenue_by_unit.map((row) => (
                      <div key={`${row.unit_id || row.unit_name}`} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                        <p className="text-sm font-semibold text-slate-900">{row.unit_name}</p>
                        <p className="mt-2 text-lg font-semibold text-slate-950">{formatMoney(row.revenue_minor, dashboard.sales_revenue.currency)}</p>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card title="Sales Table" titleClassName="text-slate-900">
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-slate-50 text-slate-600">
                        <tr>
                          <th className="px-4 py-3 text-left font-medium">Receipt</th>
                          <th className="px-4 py-3 text-left font-medium">Date</th>
                            <th className="px-4 py-3 text-left font-medium">Patient</th>
                            <th className="px-4 py-3 text-left font-medium">MRN</th>
                            <th className="px-4 py-3 text-left font-medium">Visit</th>
                            <th className="px-4 py-3 text-left font-medium">Test</th>
                            <th className="px-4 py-3 text-left font-medium">Unit</th>
                            <th className="px-4 py-3 text-left font-medium">Amount</th>
                          <th className="px-4 py-3 text-left font-medium">Method</th>
                          <th className="px-4 py-3 text-left font-medium">Cashier</th>
                          <th className="px-4 py-3 text-left font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {filteredSalesRows.map((row) => (
                          <tr key={`${row.receipt_id}:${row.test_name}`}> 
                            <td className="px-4 py-3 font-medium text-slate-900">{row.receipt_number}</td>
                            <td className="px-4 py-3 text-slate-700">{formatDateTime(row.occurred_at)}</td>
                            <td className="px-4 py-3 text-slate-700">{row.patient_name || '—'}</td>
                            <td className="px-4 py-3 text-slate-700">{row.patient_mrn || '—'}</td>
                            <td className="px-4 py-3 text-slate-700">{formatVisitReference(row.visit_id)}</td>
                            <td className="px-4 py-3 text-slate-700">{row.test_name}</td>
                            <td className="px-4 py-3 text-slate-700">{row.unit_name || 'Unassigned'}</td>
                            <td className="px-4 py-3 text-slate-700">{formatMoney(row.amount_minor, row.currency)}</td>
                            <td className="px-4 py-3 text-slate-700">{titleize(row.payment_method)}</td>
                            <td className="px-4 py-3 text-slate-700">{row.cashier_name || '—'}</td>
                            <td className="px-4 py-3"><span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusTone(row.status)}`}>{titleize(row.status)}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}

            {activeSection === 'receipt-register' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Receipt Register" title="Receipt Traceability By Lab Department" description="Searchable receipt archive for linked patient, visit, cashier, and lab item context." />
                <Card>
                  <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-4">
                    <Input label="Search" value={receiptSearch} onChange={(event) => setReceiptSearch(event.target.value)} placeholder="Receipt, patient, MRN, cashier, test" />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Unit</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={receiptUnitFilter} onChange={(event) => setReceiptUnitFilter(event.target.value)}>
                        <option value="ALL">All units</option>
                        {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Cashier</label>
                      <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={receiptCashierFilter} onChange={(event) => setReceiptCashierFilter(event.target.value)}>
                        <option value="ALL">All cashiers</option>
                        {uniqueCashiers.map((cashier) => <option key={cashier} value={cashier}>{cashier}</option>)}
                      </select>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                      Receipt data is traceability-oriented only. No mutation, refund, or reprint action is exposed here.
                    </div>
                  </div>
                </Card>
                <div className="space-y-4">
                  {filteredReceiptRows.length ? (
                    filteredReceiptRows.map((row) => (
                      <Card key={row.receipt_id} title={row.receipt_number} titleClassName="text-slate-900">
                        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5 text-sm text-slate-700">
                          <div>
                            <p className="font-medium text-slate-900">Patient</p>
                            <p>{row.patient_name || '—'}</p>
                            <p className="text-xs text-slate-500">{row.patient_mrn || 'No MRN'}</p>
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">Linked Visit</p>
                            <p>{formatVisitReference(row.visit_id)}</p>
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">Cashier</p>
                            <p>{row.cashier_name || '—'}</p>
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">Amount</p>
                            <p>{formatMoney(row.amount_minor, row.currency)}</p>
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">Occurred</p>
                            <p>{formatDateTime(row.occurred_at)}</p>
                          </div>
                        </div>
                        <div className="mt-4 flex flex-wrap gap-2">
                          {row.linked_test_items.map((item) => (
                            <span key={item} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">{item}</span>
                          ))}
                        </div>
                      </Card>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                      No lab-linked receipts match the current filters.
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeSection === 'reports-analytics' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Reports & Analytics" title="Department Trends and Reporting Signals" description="Volume, revenue, quality, and turnaround views for lab governance." />
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricTile label="Verification TAT" value={formatMinutes(dashboard.reports_analytics.verification_turnaround_minutes)} />
                  <MetricTile label="Completion TAT" value={formatMinutes(dashboard.reports_analytics.completion_turnaround_minutes)} />
                  <MetricTile label="Common Tests" value={dashboard.reports_analytics.common_tests_ordered.length} />
                  <MetricTile label="QC Status Groups" value={dashboard.reports_analytics.qc_pass_fail_trend.length} />
                </div>
                <div className="grid gap-6 xl:grid-cols-2">
                  <Card title="Test Volume By Day" titleClassName="text-slate-900">
                    <div className="space-y-3">
                      {dashboard.reports_analytics.test_volume_by_day.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                          <span className="text-sm text-slate-700">{row.label}</span>
                          <span className="text-sm font-semibold text-slate-900">{row.count}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                  <Card title="Common Tests Ordered" titleClassName="text-slate-900">
                    <div className="space-y-3">
                      {dashboard.reports_analytics.common_tests_ordered.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                          <span className="text-sm text-slate-700">{row.label}</span>
                          <span className="text-sm font-semibold text-slate-900">{row.count}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                  <Card title="Critical Result Frequency" titleClassName="text-slate-900">
                    <div className="space-y-3">
                      {dashboard.reports_analytics.critical_result_frequency.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                          <span className="text-sm text-slate-700">{row.label}</span>
                          <span className="text-sm font-semibold text-slate-900">{row.count}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                  <Card title="Staff Workload Trend" titleClassName="text-slate-900">
                    <div className="space-y-3">
                      {dashboard.reports_analytics.staff_workload_trend.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                          <span className="text-sm text-slate-700">{row.label}</span>
                          <span className="text-sm font-semibold text-slate-900">{row.count}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'configuration-requests' && (
              <div className="space-y-6">
                <SectionHeading eyebrow="Configuration Requests" title="Request Workflow For Operational Changes" description="New staff accounts, role adjustments, test activation, pricing, template updates, and unit configuration changes all stay request-based." />
                <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
                  <Card title="Submit Request" titleClassName="text-slate-900">
                    <div className="space-y-4">
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Request Type</label>
                        <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={requestForm.request_type} onChange={(event) => setRequestForm((current) => ({ ...current, request_type: event.target.value as LabManagerConfigurationRequestCreate['request_type'] }))}>
                          {requestTypeOptions.map((option) => <option key={option} value={option}>{titleize(option)}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Linked Staff (optional)</label>
                        <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={requestForm.linked_staff_id || ''} onChange={(event) => setRequestForm((current) => ({ ...current, linked_staff_id: event.target.value || null }))}>
                          <option value="">No linked staff</option>
                          {dashboard.staff.map((staff) => <option key={staff.user_id} value={staff.user_id}>{staff.full_name || staff.email}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Linked Unit (optional)</label>
                        <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={requestForm.linked_unit_id || ''} onChange={(event) => setRequestForm((current) => ({ ...current, linked_unit_id: event.target.value || null }))}>
                          <option value="">No linked unit</option>
                          {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
                        </select>
                      </div>
                      <Input label="Linked Test Code (optional)" value={requestForm.linked_test_code || ''} onChange={(event) => setRequestForm((current) => ({ ...current, linked_test_code: event.target.value }))} placeholder="e.g. CHEM_UE" />
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Justification</label>
                        <textarea className="min-h-[140px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={requestForm.justification} onChange={(event) => setRequestForm((current) => ({ ...current, justification: event.target.value }))} placeholder="State the operational reason, urgency, and the expected outcome." />
                      </div>
                      <Button onClick={() => void submitConfigurationRequest()} isLoading={requestSaving}>
                        Submit Configuration Request
                      </Button>
                    </div>
                  </Card>

                  <Card title="Request Register" titleClassName="text-slate-900">
                    <div className="space-y-3">
                      {dashboard.configuration_requests.map((request) => (
                        <div key={request.id} className="rounded-2xl border border-slate-200 px-4 py-4">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="font-semibold text-slate-900">{titleize(request.request_type)}</p>
                              <p className="mt-1 text-sm text-slate-600">Requested by {request.requested_by_name || 'Lab HOD'} • {formatDateTime(request.created_at)}</p>
                            </div>
                            <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusTone(request.status)}`}>
                              {titleize(request.status)}
                            </span>
                          </div>
                          <p className="mt-3 text-sm text-slate-700">{request.justification}</p>
                          <div className="mt-3 flex flex-wrap gap-2 text-xs">
                            {request.linked_staff_name ? <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-700">Staff: {request.linked_staff_name}</span> : null}
                            {request.linked_unit_name ? <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-700">Unit: {request.linked_unit_name}</span> : null}
                            {request.linked_test_code ? <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-700">Test: {request.linked_test_code}</span> : null}
                          </div>
                        </div>
                      ))}
                    </div>
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
