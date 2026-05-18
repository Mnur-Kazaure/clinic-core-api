'use client';

import { type ReactNode, useState } from 'react';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { HOSPITAL_NAME } from '@/shared/constants/branding';

type SignalTone = 'cyan' | 'emerald' | 'amber' | 'rose' | 'slate' | 'steel' | 'gold';
type KpiPriority = 'primary' | 'secondary' | 'support';
type PanelVariant = 'dominant' | 'standard' | 'compact' | 'alert' | 'open' | 'steel' | 'governance';

type NavigationGroup = {
  title: string;
  code: string;
  items: string[];
};

type KpiMetric = {
  label: string;
  value: string;
  detail: string;
  delta: string;
  context: string;
  tone: SignalTone;
  priority: KpiPriority;
  trend: number[];
};

type ActivityItem = {
  time: string;
  severity: string;
  title: string;
  detail: string;
  tone: SignalTone;
};

type DepartmentLoad = {
  department: string;
  current: number;
  capacity: number;
  pressure: string;
  tone: SignalTone;
};

type ExecutiveTableRow = {
  domain: string;
  signal: string;
  owner: string;
  state: string;
  tone: SignalTone;
};

type ExecutiveSignal = {
  label: string;
  value: string;
  context: string;
  tone: SignalTone;
};

type StaffAttendanceMetric = {
  label: string;
  value: string;
  context: string;
  tone: SignalTone;
};

type AttendanceStatus =
  | 'On Time'
  | 'Late Arrival'
  | 'Absent'
  | 'Early Departure'
  | 'No Clock-Out'
  | 'Manual Review';

type StaffAttendanceRecord = {
  name: string;
  staffId: string;
  role: string;
  department: string;
  phone: string;
  shift: string;
  clockIn: string;
  clockOut: string;
  status: AttendanceStatus;
  lateness: string;
  device: string;
  review: string;
  tone: SignalTone;
};

type DepartmentAttendanceSnapshot = {
  department: string;
  expected: number;
  onDuty: number;
  status: string;
  tone: SignalTone;
};

type DepartmentStaffingStatus = {
  department: string;
  required: number;
  onDuty: number;
  status: string;
  risk: string;
  visibility: string;
  tone: SignalTone;
};

type BiometricEvent = {
  time: string;
  device: string;
  subject: string;
  event: string;
  state: string;
  detail: string;
  tone: SignalTone;
};

type BiometricDeviceHealth = {
  name: string;
  status: string;
  events: number;
  lastSync: string;
  location: string;
  latency: string;
  integrity: string;
  tone: SignalTone;
};

type ShiftWindowCompliance = {
  name: string;
  window: string;
  expected: number;
  present: number;
  late: number;
  absent: number;
  compliance: number;
  state: string;
  tone: SignalTone;
};

type DepartmentShiftCompliance = {
  department: string;
  shift: string;
  expected: number;
  present: number;
  compliance: number;
  state: string;
  tone: SignalTone;
};

type ShiftComplianceException = {
  title: string;
  detail: string;
  severity: string;
  tone: SignalTone;
};

type ShiftComplianceEvent = {
  time: string;
  title: string;
  detail: string;
  tone: SignalTone;
};

type WorkforceComparison = {
  department: string;
  state: string;
  coverage: string;
  pressure: string;
  tone: SignalTone;
};

type WorkforcePattern = {
  label: string;
  value: string;
  detail: string;
  tone: SignalTone;
};

type WorkforceInsight = {
  title: string;
  detail: string;
  tone: SignalTone;
};

type CashierCollection = {
  cashier: string;
  location: string;
  desk: string;
  total: string;
  pos: string;
  bankTransfer: string;
  cash: string;
  receipts: number;
  shiftStatus: string;
  variance: string;
  lastReceipt: string;
  tone: SignalTone;
};

type PaymentTransaction = {
  receipt: string;
  patient: string;
  mrn: string;
  department: string;
  serviceLine: string;
  purpose: string;
  requestedBy: string;
  cashier: string;
  method: string;
  amount: string;
  reference: string;
  receiptTime: string;
  status: string;
  traceability: string;
  tone: SignalTone;
};

type DepartmentRevenue = {
  department: string;
  revenue: string;
  share: number;
  transactions: number;
  state: string;
  tone: SignalTone;
};

type OutstandingBill = {
  patient: string;
  mrn: string;
  department: string;
  amount: string;
  age: string;
  state: string;
  tone: SignalTone;
};

type FinancialException = {
  title: string;
  amount: string;
  detail: string;
  state: string;
  tone: SignalTone;
};

type CashierReconciliation = {
  cashier: string;
  location: string;
  declared: string;
  matched: string;
  variance: string;
  receipts: number;
  status: string;
  visibility: string;
  tone: SignalTone;
};

type PaymentMethodReconciliation = {
  method: string;
  expected: string;
  matched: string;
  variance: string;
  status: string;
  tone: SignalTone;
};

type DepartmentReconciliation = {
  department: string;
  amount: string;
  status: string;
  detail: string;
  tone: SignalTone;
};

type ReconciliationTimelineEvent = {
  time: string;
  title: string;
  detail: string;
  tone: SignalTone;
};

type ActiveNavigation = {
  section: string;
  subsection: string;
};

const navigationGroups: NavigationGroup[] = [
  {
    title: 'Executive Overview',
    code: 'EO',
    items: [
      'Hospital Snapshot',
      'Critical Alerts',
      'Operational KPIs',
      'Daily Executive Summary',
      'Operational Systems Status',
    ],
  },
  {
    title: 'Hospital Operations',
    code: 'HO',
    items: [
      'Patient Flow Overview',
      'Admission & Discharge Monitoring',
      'Bed & Ward Utilization',
      'Emergency Monitoring',
      'Department Performance',
      'Follow-Up Compliance',
    ],
  },
  {
    title: 'Financial Intelligence',
    code: 'FI',
    items: [
      'Revenue Overview',
      'Cashier Collections',
      'Payment Traceability',
      'Department Revenue',
      'Revenue Reconciliation Intelligence',
      'Outstanding Bills',
      'Refund & Waiver Audit',
      'Pharmacy Revenue & Traceability',
    ],
  },
  {
    title: 'Pharmacy & Supply Governance',
    code: 'PS',
    items: [
      'Supply Approval Queue',
      'Departmental Requests',
      'Dispensing Unit Requests',
      'Pharmacy Store Oversight',
      'Stock Movement Audit',
      'Critical Stock Alerts',
      'High-Risk Commodity Monitoring',
      'Supply Consumption Analytics',
      'Approval History',
      'Emergency Supply Requests',
    ],
  },
  {
    title: 'Staff Governance',
    code: 'SG',
    items: [
      'Attendance Intelligence',
      'Biometric Monitoring',
      'Shift Compliance',
      'Workforce Analytics',
      'Department Staffing Posture',
    ],
  },
  {
    title: 'Audit & Compliance',
    code: 'AC',
    items: [
      'User Activity Audit',
      'Patient Record Access Audit',
      'Financial Audit Trail',
      'Clinical Change History',
      'Login & Session Audit',
      'Permission Change Audit',
      'Suspicious Activities',
      'Compliance Reports',
    ],
  },
  {
    title: 'Executive Reports',
    code: 'ER',
    items: [
      'Operational Reports',
      'Financial Reports',
      'Audit Reports',
      'Department Performance Reports',
      'Executive Export Center',
    ],
  },
  {
    title: 'Executive Settings',
    code: 'ES',
    items: [
      'Dashboard Preferences',
      'Notification Preferences',
      'Report Preferences',
      'Executive Profile',
    ],
  },
];

const executiveSignals: ExecutiveSignal[] = [
  {
    label: 'Hospital Status',
    value: 'Stable',
    context: 'Preview command posture',
    tone: 'emerald',
  },
  {
    label: 'Emergency Pressure',
    value: 'Moderate',
    context: '2 elevated cases',
    tone: 'amber',
  },
  {
    label: 'Bed Utilization',
    value: '78%',
    context: 'Ward visibility threshold',
    tone: 'cyan',
  },
  {
    label: 'Critical Signals',
    value: '3',
    context: 'CMD attention queue',
    tone: 'rose',
  },
  {
    label: 'Active Departments',
    value: '12',
    context: 'Operational view scope',
    tone: 'slate',
  },
];

const kpiMetrics: KpiMetric[] = [
  {
    label: 'Critical Alerts',
    value: '9',
    detail: 'Operational, audit, attendance, and supply governance signals.',
    delta: '3 require CMD attention',
    context: 'Risk pressure elevated',
    tone: 'rose',
    priority: 'primary',
    trend: [28, 36, 42, 51, 47, 64, 59, 74, 71, 82, 76, 88],
  },
  {
    label: 'Revenue Today',
    value: '₦8.42M',
    detail: 'Cashier, pharmacy, lab, and service-line revenue snapshot.',
    delta: '+12% pharmacy revenue signal',
    context: 'Traceability pending API wiring',
    tone: 'cyan',
    priority: 'primary',
    trend: [34, 39, 41, 52, 58, 63, 70, 68, 79, 84, 89, 95],
  },
  {
    label: 'Bed Occupancy',
    value: '78%',
    detail: 'Ward and bed utilization executive visibility.',
    delta: 'Male medical ward at 91%',
    context: 'Admission pressure watch',
    tone: 'amber',
    priority: 'primary',
    trend: [48, 51, 55, 61, 58, 66, 72, 75, 73, 79, 78, 82],
  },
  {
    label: 'Hospital Census',
    value: '214',
    detail: 'Patients visible across active service lines.',
    delta: '+18 since 06:00',
    context: 'Outpatient and inpatient flow',
    tone: 'cyan',
    priority: 'secondary',
    trend: [38, 44, 47, 53, 51, 60, 64, 68, 71, 76, 75, 81],
  },
  {
    label: 'Admissions',
    value: '37',
    detail: 'Admission events queued for executive oversight.',
    delta: '12 inpatient conversions',
    context: 'Admission desk throughput',
    tone: 'emerald',
    priority: 'support',
    trend: [25, 31, 28, 42, 45, 48, 54, 53, 61, 66, 64, 70],
  },
  {
    label: 'Staff On Duty',
    value: '126',
    detail: 'Biometric attendance and shift coverage intelligence.',
    delta: '8 late arrivals flagged',
    context: 'Workforce compliance view',
    tone: 'emerald',
    priority: 'support',
    trend: [66, 70, 68, 73, 76, 80, 78, 82, 84, 86, 83, 88],
  },
];

const departmentLoads: DepartmentLoad[] = [
  {
    department: 'Outpatient / Records',
    current: 84,
    capacity: 120,
    pressure: 'Registration and triage moving normally',
    tone: 'emerald',
  },
  {
    department: 'Emergency',
    current: 21,
    capacity: 30,
    pressure: 'Moderate pressure, two high-priority cases',
    tone: 'amber',
  },
  {
    department: 'Ward & Admissions',
    current: 78,
    capacity: 100,
    pressure: 'Bed utilization approaching review threshold',
    tone: 'amber',
  },
  {
    department: 'Laboratory',
    current: 43,
    capacity: 70,
    pressure: 'Specimen processing within expected window',
    tone: 'cyan',
  },
];

const financeRows: ExecutiveTableRow[] = [
  {
    domain: 'Revenue Overview',
    signal: 'Hospital-wide daily revenue summary and payment method posture',
    owner: 'CMD / Finance',
    state: 'High priority',
    tone: 'cyan',
  },
  {
    domain: 'Cashier Collections',
    signal: 'Cashier-by-cashier collections by location, payment method, shift, and variance status',
    owner: 'Cashier Supervisor',
    state: 'Monitored',
    tone: 'emerald',
  },
  {
    domain: 'Payment Traceability',
    signal: 'Receipt-level transaction audit trail with patient, MRN, cashier, reference, and trace state',
    owner: 'Accountant',
    state: 'Governed',
    tone: 'cyan',
  },
  {
    domain: 'Department Revenue',
    signal: 'Revenue ranking by department and service line',
    owner: 'Finance / Departments',
    state: 'Ranked',
    tone: 'steel',
  },
  {
    domain: 'Revenue Reconciliation Intelligence',
    signal: 'Variance detection, settlement matching, cashier reconciliation, and guided CMD review',
    owner: 'Finance Governance',
    state: 'Review required',
    tone: 'amber',
  },
  {
    domain: 'Outstanding Bills',
    signal: 'Unpaid balances, pending discharge clearance, and aging visibility',
    owner: 'Billing / Ward',
    state: '₦1.18M',
    tone: 'amber',
  },
  {
    domain: 'Refund & Waiver Audit',
    signal: 'Refund, waiver, discount, and sensitive financial adjustment oversight',
    owner: 'Finance / CMD',
    state: 'Controlled',
    tone: 'rose',
  },
  {
    domain: 'Pharmacy Revenue & Traceability',
    signal: 'Dispensing revenue and commodity traceability',
    owner: 'Pharmacy HOD',
    state: 'Watch',
    tone: 'gold',
  },
];

const revenueOverviewMetrics: ExecutiveSignal[] = [
  { label: 'Total Revenue Today', value: '₦8.42M', context: 'Hospital-wide posted revenue', tone: 'cyan' },
  { label: 'Total Collections Today', value: '₦8.42M', context: 'All posted collections', tone: 'emerald' },
  { label: 'POS Collections', value: '₦3.62M', context: 'Card terminal collections', tone: 'cyan' },
  { label: 'Bank Transfer Collections', value: '₦2.88M', context: 'Matched transfer receipts', tone: 'steel' },
  { label: 'Cash Collections', value: '₦1.92M', context: 'Cashier cash received', tone: 'gold' },
  { label: 'Pharmacy Revenue', value: '₦2.14M', context: 'Dedicated pharmacy cashier', tone: 'emerald' },
  { label: 'Outstanding Bills', value: '₦1.18M', context: 'Unpaid balances visible', tone: 'amber' },
  { label: 'Refund/Waiver Exposure', value: '₦86K', context: 'Controlled exception exposure', tone: 'rose' },
];

const cashierCollectionMetrics: ExecutiveSignal[] = [
  { label: 'Cashier Points', value: '5', context: '4 general points + pharmacy', tone: 'cyan' },
  { label: 'Collections Preview', value: '₦6.95M', context: 'Visible cashier register total', tone: 'emerald' },
  { label: 'Total Receipts', value: '184', context: 'Receipt records represented', tone: 'steel' },
  { label: 'Variance Watch', value: '1', context: 'One cashier requires review', tone: 'amber' },
];

const paymentTraceabilityMetrics: ExecutiveSignal[] = [
  { label: 'Traceable Transactions', value: '184', context: 'Receipt-level audit coverage', tone: 'cyan' },
  { label: 'Verified / Matched', value: '181', context: 'Payment references reconciled', tone: 'emerald' },
  { label: 'High-Value Flags', value: '3', context: 'CMD-visible transaction watch', tone: 'gold' },
  { label: 'Trace Exceptions', value: '3', context: 'Requires accountant review', tone: 'rose' },
];

const departmentRevenueMetrics: ExecutiveSignal[] = [
  { label: 'Best Performing Department', value: 'Pharmacy', context: '26% revenue share', tone: 'emerald' },
  { label: 'Department Revenue View', value: '8 units', context: 'Ranked service-line preview', tone: 'cyan' },
  { label: 'Top 3 Share', value: '58%', context: 'Pharmacy, Laboratory, OPD/GOPD', tone: 'steel' },
  { label: 'Traceability Preview', value: 'Active', context: 'Department receipt drilldown ready', tone: 'gold' },
];

const revenueReconciliationMetrics: ExecutiveSignal[] = [
  { label: 'Total Collections', value: '₦8.42M', context: 'Declared collection posture', tone: 'cyan' },
  { label: 'Reconciled Amount', value: '₦8.31M', context: 'Matched against receipt and settlement records', tone: 'emerald' },
  { label: 'Variance', value: '₦110K', context: 'Requires finance governance review', tone: 'rose' },
  { label: 'Reconciliation Status', value: 'Review Required', context: 'CMD visibility active', tone: 'amber' },
  { label: 'Matched Receipts', value: '176 / 184', context: 'Receipt traceability posture', tone: 'steel' },
  { label: 'Unmatched Transactions', value: '8', context: 'Transactions requiring reconciliation', tone: 'amber' },
  { label: 'Suspicious Adjustments', value: '3', context: 'Sensitive adjustment signals', tone: 'rose' },
  { label: 'Pending Cashier Closures', value: '2', context: 'Cashier shifts awaiting closure confirmation', tone: 'gold' },
];

const outstandingBillMetrics: ExecutiveSignal[] = [
  { label: 'Total Outstanding Today', value: '₦1.18M', context: 'Unpaid balances requiring visibility', tone: 'amber' },
  { label: 'Inpatient Pending Bills', value: '₦520K', context: 'Ward billing not yet cleared', tone: 'gold' },
  { label: 'Pharmacy Unpaid Bills', value: '₦260K', context: 'Dispensed items pending payment', tone: 'amber' },
  { label: 'Lab Unpaid Bills', value: '₦180K', context: 'Investigations pending settlement', tone: 'steel' },
  { label: 'Discharge Clearance', value: '₦220K', context: 'Pending discharge billing clearance', tone: 'rose' },
  { label: 'Aging Risk', value: '4 cases', context: 'Above 24h visibility threshold', tone: 'rose' },
];

const refundWaiverMetrics: ExecutiveSignal[] = [
  { label: 'Refund Requests', value: '6', context: 'Requests awaiting controlled review', tone: 'amber' },
  { label: 'Approved Refunds', value: '2', context: 'Approved with audit record', tone: 'emerald' },
  { label: 'Rejected Refunds', value: '1', context: 'Rejected by policy control', tone: 'steel' },
  { label: 'Waiver Requests', value: '4', context: 'Waiver visibility queue', tone: 'gold' },
  { label: 'Discounts', value: '₦31K', context: 'Approved financial discounts', tone: 'cyan' },
  { label: 'Adjustment Risk', value: '2 alerts', context: 'Suspicious adjustment watch', tone: 'rose' },
];

const pharmacyRevenueMetrics: ExecutiveSignal[] = [
  { label: 'Pharmacy Revenue Today', value: '₦2.14M', context: 'Dedicated pharmacy cashier collection', tone: 'emerald' },
  { label: 'Pharmacy Receipts', value: '48', context: 'Medication dispensing receipts', tone: 'cyan' },
  { label: 'Dispensing Unit Revenue', value: '₦1.62M', context: 'Unit-level pharmacy revenue', tone: 'steel' },
  { label: 'Voided Receipts', value: '1', context: 'Requires trace review', tone: 'rose' },
  { label: 'High-Value Medicines', value: '7', context: 'High-value transaction flags', tone: 'gold' },
  { label: 'Traceability State', value: 'Stable', context: 'Receipt-to-dispensing visibility', tone: 'emerald' },
];

const cashierCollections: CashierCollection[] = [
  {
    cashier: 'Aisha Bello',
    location: 'Main Cashier Desk',
    desk: 'Main billing desk',
    total: '₦1.85M',
    pos: '₦960K',
    bankTransfer: '₦570K',
    cash: '₦320K',
    receipts: 46,
    shiftStatus: 'Open',
    variance: 'Stable',
    lastReceipt: '11:39 AM',
    tone: 'emerald',
  },
  {
    cashier: 'Musa Abdullahi',
    location: 'OPD Cashier Point',
    desk: 'OPD / GOPD',
    total: '₦1.22M',
    pos: '₦540K',
    bankTransfer: '₦380K',
    cash: '₦300K',
    receipts: 38,
    shiftStatus: 'Open',
    variance: 'Stable',
    lastReceipt: '11:36 AM',
    tone: 'emerald',
  },
  {
    cashier: 'Hauwa Sani',
    location: 'Laboratory/Radiology Cashier',
    desk: 'Lab / Radiology',
    total: '₦980K',
    pos: '₦310K',
    bankTransfer: '₦440K',
    cash: '₦230K',
    receipts: 32,
    shiftStatus: 'Open',
    variance: 'Watch',
    lastReceipt: '11:31 AM',
    tone: 'amber',
  },
  {
    cashier: 'Ibrahim Lawal',
    location: 'A&E Cashier Point',
    desk: 'Accident & Emergency',
    total: '₦760K',
    pos: '₦280K',
    bankTransfer: '₦210K',
    cash: '₦270K',
    receipts: 20,
    shiftStatus: 'Open',
    variance: 'Stable',
    lastReceipt: '11:27 AM',
    tone: 'steel',
  },
  {
    cashier: 'Maryam Ali',
    location: 'Pharmacy Cashier',
    desk: 'Pharmacy',
    total: '₦2.14M',
    pos: '₦890K',
    bankTransfer: '₦760K',
    cash: '₦490K',
    receipts: 48,
    shiftStatus: 'Open',
    variance: 'Stable',
    lastReceipt: '11:42 AM',
    tone: 'emerald',
  },
];

const paymentTransactions: PaymentTransaction[] = [
  {
    receipt: 'RCP-2026-00091',
    patient: 'Abba Nura',
    mrn: 'MRN 0000001-9',
    department: 'Pharmacy',
    serviceLine: 'Medication Dispensing',
    purpose: 'Ceftriaxone injection',
    requestedBy: "Dr. Nasir Ya'u",
    cashier: 'Maryam Ali',
    method: 'POS',
    amount: '₦18,500',
    reference: 'POS-A92F',
    receiptTime: '11:42 AM',
    status: 'Verified',
    traceability: 'Receipt matched',
    tone: 'emerald',
  },
  {
    receipt: 'RCP-2026-00092',
    patient: 'Muhammad Nura',
    mrn: 'MRN 0000002-8',
    department: 'Laboratory',
    serviceLine: 'Lab Investigation',
    purpose: 'FBC + Malaria test',
    requestedBy: "Dr. Nasir Ya'u",
    cashier: 'Hauwa Sani',
    method: 'Cash',
    amount: '₦7,500',
    reference: 'CASH-1182',
    receiptTime: '11:36 AM',
    status: 'Verified',
    traceability: 'Cash drawer linked',
    tone: 'emerald',
  },
  {
    receipt: 'RCP-2026-00093',
    patient: 'Sani Umar',
    mrn: 'MRN 0000003-7',
    department: 'A&E',
    serviceLine: 'Emergency Care',
    purpose: 'Emergency service charge',
    requestedBy: 'A&E Nurse Lead',
    cashier: 'Ibrahim Lawal',
    method: 'Bank Transfer',
    amount: '₦25,000',
    reference: 'TRF-8841',
    receiptTime: '11:28 AM',
    status: 'Matched',
    traceability: 'Bank reference matched',
    tone: 'cyan',
  },
  {
    receipt: 'RCP-2026-00094',
    patient: 'Abba Sani',
    mrn: 'MRN 0000004-6',
    department: 'OPD',
    serviceLine: 'Consultation',
    purpose: 'GOPD consultation fee',
    requestedBy: 'Reception Desk',
    cashier: 'Musa Abdullahi',
    method: 'POS',
    amount: '₦3,000',
    reference: 'POS-B772',
    receiptTime: '11:19 AM',
    status: 'Verified',
    traceability: 'Receipt matched',
    tone: 'emerald',
  },
  {
    receipt: 'RCP-2026-00095',
    patient: 'Fatima Kabir',
    mrn: 'MRN 0000005-3',
    department: 'Radiology',
    serviceLine: 'Imaging',
    purpose: 'X-ray chest',
    requestedBy: 'Dr. Aisha Musa',
    cashier: 'Hauwa Sani',
    method: 'Bank Transfer',
    amount: '₦12,000',
    reference: 'TRF-5510',
    receiptTime: '11:11 AM',
    status: 'Matched',
    traceability: 'Bank reference matched',
    tone: 'cyan',
  },
];

const departmentRevenueRows: DepartmentRevenue[] = [
  { department: 'Pharmacy', revenue: '₦2.14M', share: 26, transactions: 48, state: 'Best performing', tone: 'emerald' },
  { department: 'Laboratory', revenue: '₦1.38M', share: 17, transactions: 39, state: 'Strong', tone: 'cyan' },
  { department: 'OPD/GOPD', revenue: '₦1.22M', share: 15, transactions: 44, state: 'Stable', tone: 'steel' },
  { department: 'A&E', revenue: '₦960K', share: 12, transactions: 20, state: 'Pressure', tone: 'amber' },
  { department: 'Radiology', revenue: '₦890K', share: 11, transactions: 24, state: 'Stable', tone: 'cyan' },
  { department: 'Maternity', revenue: '₦620K', share: 8, transactions: 13, state: 'Stable', tone: 'emerald' },
  { department: 'Theatre', revenue: '₦540K', share: 7, transactions: 8, state: 'High value', tone: 'gold' },
  { department: 'Pediatrics', revenue: '₦310K', share: 4, transactions: 12, state: 'Stable', tone: 'steel' },
];

const cashierReconciliationRows: CashierReconciliation[] = [
  {
    cashier: 'Aisha Bello',
    location: 'Main Cashier Desk',
    declared: '₦1.85M',
    matched: '₦1.85M',
    variance: '₦0',
    receipts: 42,
    status: 'Verified',
    visibility: 'No CMD action required',
    tone: 'emerald',
  },
  {
    cashier: 'Musa Abdullahi',
    location: 'OPD Cashier Point',
    declared: '₦1.22M',
    matched: '₦1.20M',
    variance: '₦20K',
    receipts: 38,
    status: 'Review',
    visibility: 'Supervisor review',
    tone: 'amber',
  },
  {
    cashier: 'Hauwa Sani',
    location: 'Laboratory/Radiology Cashier',
    declared: '₦980K',
    matched: '₦980K',
    variance: '₦0',
    receipts: 31,
    status: 'Verified',
    visibility: 'No CMD action required',
    tone: 'emerald',
  },
  {
    cashier: 'Ibrahim Lawal',
    location: 'A&E Cashier Point',
    declared: '₦760K',
    matched: '₦710K',
    variance: '₦50K',
    receipts: 24,
    status: 'Review Required',
    visibility: 'CMD visibility required',
    tone: 'rose',
  },
  {
    cashier: 'Maryam Ali',
    location: 'Pharmacy Cashier',
    declared: '₦2.14M',
    matched: '₦2.10M',
    variance: '₦40K',
    receipts: 49,
    status: 'Review',
    visibility: 'Pharmacy cashier review',
    tone: 'amber',
  },
];

const paymentMethodReconciliation: PaymentMethodReconciliation[] = [
  {
    method: 'POS',
    expected: '₦3.62M',
    matched: '₦3.60M',
    variance: '₦20K',
    status: 'Review',
    tone: 'amber',
  },
  {
    method: 'Bank Transfer',
    expected: '₦2.88M',
    matched: '₦2.88M',
    variance: '₦0',
    status: 'Matched',
    tone: 'emerald',
  },
  {
    method: 'Cash',
    expected: '₦1.92M',
    matched: '₦1.83M',
    variance: '₦90K',
    status: 'Pending Review',
    tone: 'rose',
  },
];

const departmentReconciliationRows: DepartmentReconciliation[] = [
  {
    department: 'Pharmacy',
    amount: '₦2.14M',
    status: 'Review',
    detail: 'Dedicated pharmacy cashier variance requires receipt matching.',
    tone: 'amber',
  },
  {
    department: 'Laboratory',
    amount: '₦1.38M',
    status: 'Matched',
    detail: 'Laboratory revenue aligned with receipt and service records.',
    tone: 'emerald',
  },
  {
    department: 'OPD/GOPD',
    amount: '₦1.22M',
    status: 'Review',
    detail: 'OPD cashier declared total requires variance review.',
    tone: 'amber',
  },
  {
    department: 'A&E',
    amount: '₦960K',
    status: 'Review Required',
    detail: 'A&E cashier variance is above monitoring threshold.',
    tone: 'rose',
  },
  {
    department: 'Radiology',
    amount: '₦890K',
    status: 'Matched',
    detail: 'Radiology receipts aligned with cashier settlement.',
    tone: 'emerald',
  },
  {
    department: 'Maternity',
    amount: '₦620K',
    status: 'Matched',
    detail: 'Maternity revenue aligned with department service records.',
    tone: 'emerald',
  },
];

const reconciliationRiskSignals: FinancialException[] = [
  {
    title: '3 receipts voided after shift close',
    amount: '3',
    detail: 'Voided receipts after cashier closure require audit review.',
    state: 'Review',
    tone: 'rose',
  },
  {
    title: '2 high-value cash transactions require review',
    amount: '2',
    detail: 'High-value cash receipts are visible for finance governance review.',
    state: 'Cash watch',
    tone: 'amber',
  },
  {
    title: '1 cashier variance above threshold',
    amount: '₦50K',
    detail: 'A&E cashier variance exceeded the configured review threshold.',
    state: 'Review required',
    tone: 'rose',
  },
  {
    title: '4 delayed bank transfer confirmations',
    amount: '4',
    detail: 'Delayed transfer confirmations remain in settlement watch.',
    state: 'Pending',
    tone: 'gold',
  },
  {
    title: '1 pharmacy receipt adjustment flagged',
    amount: '1',
    detail: 'Pharmacy receipt adjustment requires traceability confirmation.',
    state: 'Flagged',
    tone: 'amber',
  },
];

const reconciliationTimeline: ReconciliationTimelineEvent[] = [
  {
    time: '09:12 AM',
    title: 'Pharmacy collections submitted',
    detail: 'Dedicated pharmacy cashier submitted collection batch for settlement matching.',
    tone: 'cyan',
  },
  {
    time: '10:08 AM',
    title: 'POS settlement partially matched',
    detail: 'POS expected amount is ₦20K above matched settlement record.',
    tone: 'amber',
  },
  {
    time: '10:48 AM',
    title: 'Bank transfer settlement matched',
    detail: 'Bank transfer collections reconciled against transfer references.',
    tone: 'emerald',
  },
  {
    time: '11:22 AM',
    title: 'A&E cashier variance detected',
    detail: 'A&E declared collections exceeded matched amount by ₦50K.',
    tone: 'rose',
  },
  {
    time: '12:14 PM',
    title: 'Manual cashier adjustment flagged',
    detail: 'Manual adjustment entered the finance governance review queue.',
    tone: 'rose',
  },
  {
    time: '01:05 PM',
    title: 'CMD review queue updated',
    detail: 'Reconciliation items requiring executive visibility were grouped for CMD review.',
    tone: 'gold',
  },
];

const guidedReconciliationSteps = [
  'Verify unmatched receipts',
  'Review cashier variances',
  'Compare payment method settlement',
  'Review voided/adjusted receipts',
  'Confirm department revenue alignment',
];

const guidedReconciliationActions = [
  { label: 'View Variance Details', tone: 'amber' as SignalTone },
  { label: 'Review Unmatched Receipts', tone: 'rose' as SignalTone },
  { label: 'Export Reconciliation Brief', tone: 'cyan' as SignalTone },
  { label: 'Mark for Accountant Review', tone: 'gold' as SignalTone },
];

const outstandingBills: OutstandingBill[] = [
  { patient: 'Aminu Bello', mrn: 'MRN 0000011-4', department: 'Male Ward', amount: '₦180K', age: '18h', state: 'Inpatient pending', tone: 'amber' },
  { patient: 'Hafsat Musa', mrn: 'MRN 0000012-3', department: 'Pharmacy', amount: '₦92K', age: '6h', state: 'Medication unpaid', tone: 'gold' },
  { patient: 'Usman Garba', mrn: 'MRN 0000013-2', department: 'Laboratory', amount: '₦48K', age: '9h', state: 'Lab unpaid', tone: 'steel' },
  { patient: 'Zainab Ali', mrn: 'MRN 0000014-1', department: 'Maternity', amount: '₦220K', age: '26h', state: 'Discharge clearance', tone: 'rose' },
];

const refundWaiverExceptions: FinancialException[] = [
  { title: 'Refund request queue', amount: '₦42K', detail: 'Six refund requests pending accountant/CMD review.', state: 'Review', tone: 'amber' },
  { title: 'Approved refunds', amount: '₦18K', detail: 'Two refunds approved with audit trail attached.', state: 'Approved', tone: 'emerald' },
  { title: 'Waiver exposure', amount: '₦26K', detail: 'Four waiver requests visible for controlled exception review.', state: 'Controlled', tone: 'gold' },
  { title: 'Suspicious adjustment alerts', amount: '2 flags', detail: 'Two adjustment events require financial audit verification.', state: 'Alert', tone: 'rose' },
];

const auditRows: ExecutiveTableRow[] = [
  {
    domain: 'User Activity Audit',
    signal: 'Critical user actions grouped by role and workstation',
    owner: 'Audit & Compliance',
    state: 'Live view',
    tone: 'steel',
  },
  {
    domain: 'Patient Record Access',
    signal: 'Access trail for sensitive patient records',
    owner: 'Records / Compliance',
    state: 'Restricted',
    tone: 'amber',
  },
  {
    domain: 'Financial Audit Trail',
    signal: 'Receipt edits, refunds, waivers, and cashier session events',
    owner: 'Finance / Audit',
    state: 'Traceable',
    tone: 'cyan',
  },
  {
    domain: 'Clinical Change History',
    signal: 'Executive preview of diagnosis, medication, and order amendment trails',
    owner: 'Clinical Governance',
    state: 'Preview',
    tone: 'steel',
  },
  {
    domain: 'Login & Session Audit',
    signal: 'Authentication posture, session continuity, and workstation access signals',
    owner: 'IT / Compliance',
    state: 'Monitored',
    tone: 'steel',
  },
  {
    domain: 'Permission Change Audit',
    signal: 'Role elevation, permission edits, and administrative access changes',
    owner: 'Hospital Admin',
    state: 'Governed',
    tone: 'gold',
  },
  {
    domain: 'Suspicious Activities',
    signal: 'Permission drift, unusual access, and finance exceptions',
    owner: 'CMD Oversight',
    state: '3 flags',
    tone: 'rose',
  },
  {
    domain: 'Compliance Reports',
    signal: 'CMD-ready compliance summary and regulated activity overview',
    owner: 'Audit & Compliance',
    state: 'Reportable',
    tone: 'steel',
  },
];

const activityFeed: ActivityItem[] = [
  {
    time: '08:42',
    severity: 'Warning',
    title: 'Emergency pressure changed',
    detail: 'Two emergency cases escalated for doctor review and bed-readiness monitoring.',
    tone: 'amber',
  },
  {
    time: '08:35',
    severity: 'Operational',
    title: 'Payment traceability event',
    detail: 'High-value pharmacy receipt moved into accountant reconciliation visibility.',
    tone: 'cyan',
  },
  {
    time: '08:18',
    severity: 'Critical',
    title: 'Biometric attendance signal',
    detail: 'Late-arrival cluster detected in one department shift window.',
    tone: 'rose',
  },
  {
    time: '08:03',
    severity: 'Governance',
    title: 'Supply approval queue updated',
    detail: 'Dispensing unit request awaits CMD governance decision.',
    tone: 'emerald',
  },
];

const supplySignals: ExecutiveTableRow[] = [
  {
    domain: 'Supply Approval Queue',
    signal: 'Departmental and dispensing unit requests awaiting authority',
    owner: 'CMD / Pharmacy HOD',
    state: 'Priority',
    tone: 'gold',
  },
  {
    domain: 'Stock Movement Audit',
    signal: 'Store-to-dispensing movement, issue notes, and receiving visibility',
    owner: 'Pharmacy Store',
    state: 'Traceable',
    tone: 'steel',
  },
  {
    domain: 'Critical Stock Alerts',
    signal: 'Controlled commodity and stockout pressure monitoring',
    owner: 'Pharmacy Store',
    state: '2 alerts',
    tone: 'rose',
  },
  {
    domain: 'High-Risk Commodity Monitoring',
    signal: 'Controlled, high-cost, and high-risk pharmacy item oversight',
    owner: 'CMD / Pharmacy HOD',
    state: 'Governed',
    tone: 'gold',
  },
  {
    domain: 'Supply Consumption Analytics',
    signal: 'Department consumption pressure and unusual usage trends',
    owner: 'Pharmacy Store',
    state: 'Analytics',
    tone: 'cyan',
  },
  {
    domain: 'Emergency Supply Requests',
    signal: 'Urgent commodity requests requiring executive visibility',
    owner: 'Emergency / Store',
    state: '1 urgent',
    tone: 'amber',
  },
  {
    domain: 'Approval History',
    signal: 'Executive decision trail for supply governance',
    owner: 'Audit Trail',
    state: 'Traceable',
    tone: 'steel',
  },
];

const financialTrustSignals: ExecutiveSignal[] = [
  {
    label: 'Receipt Traceability',
    value: 'Stable',
    context: 'Cashier sessions visible',
    tone: 'cyan',
  },
  {
    label: 'Refund Risk',
    value: 'Low',
    context: 'Waiver review controlled',
    tone: 'steel',
  },
  {
    label: 'Cashier Variance',
    value: '0.8%',
    context: 'Within oversight range',
    tone: 'gold',
  },
  {
    label: 'Pharmacy Spike',
    value: '+12%',
    context: 'Revenue trace watch',
    tone: 'cyan',
  },
];

const staffAttendanceMetrics: StaffAttendanceMetric[] = [
  {
    label: 'Expected Staff',
    value: '142',
    context: 'Rostered across current shift',
    tone: 'steel',
  },
  {
    label: 'Staff On Duty',
    value: '126',
    context: 'Across monitored clinical and support units',
    tone: 'emerald',
  },
  {
    label: 'Biometric Coverage',
    value: '94%',
    context: 'Enrolled staff with active biometric profile',
    tone: 'cyan',
  },
  {
    label: 'Clock-Ins Today',
    value: '118',
    context: 'Fingerprint clock-ins received by sync window',
    tone: 'steel',
  },
  {
    label: 'Late Arrivals',
    value: '3',
    context: 'Clock-in after 09:30 AM threshold',
    tone: 'amber',
  },
  {
    label: 'Absent Staff',
    value: '2',
    context: 'No biometric record against assigned shift',
    tone: 'rose',
  },
  {
    label: 'Early Departures',
    value: '1',
    context: 'Clock-out earlier than shift policy',
    tone: 'gold',
  },
  {
    label: 'Attendance Compliance',
    value: '91%',
    context: 'Clock-in and department coverage alignment',
    tone: 'emerald',
  },
];

const staffAttendanceRecords: StaffAttendanceRecord[] = [
  {
    name: "Dr. Nasir Ya'u",
    staffId: 'SHK-DR-014',
    role: 'Doctor',
    department: 'A&E',
    phone: '08030001111',
    shift: 'Morning',
    clockIn: '08:52 AM',
    clockOut: 'In progress',
    status: 'On Time',
    lateness: 'None',
    device: 'A&E Gate Device',
    review: 'Normal',
    tone: 'emerald',
  },
  {
    name: 'Nurse Amina Bello',
    staffId: 'SHK-NS-041',
    role: 'Nurse',
    department: 'Female Ward',
    phone: '08030002222',
    shift: 'Morning',
    clockIn: '09:47 AM',
    clockOut: 'In progress',
    status: 'Late Arrival',
    lateness: '17 mins late',
    device: 'Ward Device 02',
    review: 'Review',
    tone: 'amber',
  },
  {
    name: 'Musa Abdullahi',
    staffId: 'SHK-LB-006',
    role: 'Lab Scientist',
    department: 'Laboratory',
    phone: '08030003333',
    shift: 'Morning',
    clockIn: '08:58 AM',
    clockOut: 'In progress',
    status: 'On Time',
    lateness: 'None',
    device: 'Lab Device',
    review: 'Normal',
    tone: 'emerald',
  },
  {
    name: 'Hauwa Sani',
    staffId: 'SHK-PH-011',
    role: 'Pharmacist',
    department: 'Pharmacy',
    phone: '08030004444',
    shift: 'Morning',
    clockIn: '09:55 AM',
    clockOut: 'In progress',
    status: 'Late Arrival',
    lateness: '25 mins late',
    device: 'Pharmacy Device',
    review: 'Review',
    tone: 'amber',
  },
  {
    name: 'Ibrahim Lawal',
    staffId: 'SHK-RD-004',
    role: 'Radiographer',
    department: 'Radiology',
    phone: '08030005555',
    shift: 'Morning',
    clockIn: '08:49 AM',
    clockOut: 'In progress',
    status: 'On Time',
    lateness: 'None',
    device: 'Radiology Device',
    review: 'Normal',
    tone: 'emerald',
  },
  {
    name: 'Zainab Yusuf',
    staffId: 'SHK-MW-017',
    role: 'Midwife',
    department: 'Maternity',
    phone: '08030006666',
    shift: 'Morning',
    clockIn: '10:12 AM',
    clockOut: 'In progress',
    status: 'Late Arrival',
    lateness: '42 mins late',
    device: 'Maternity Device',
    review: 'Escalate',
    tone: 'amber',
  },
  {
    name: 'Umar Garba',
    staffId: 'SHK-NS-052',
    role: 'Nurse',
    department: 'Male Ward',
    phone: '08030007777',
    shift: 'Morning',
    clockIn: 'No clock-in',
    clockOut: 'Not applicable',
    status: 'Absent',
    lateness: 'None',
    device: 'No biometric record',
    review: 'Escalate',
    tone: 'rose',
  },
  {
    name: 'Fatima Kabir',
    staffId: 'SHK-NS-063',
    role: 'Nurse',
    department: 'Pediatrics',
    phone: '08030008888',
    shift: 'Morning',
    clockIn: '08:45 AM',
    clockOut: '12:20 PM',
    status: 'Early Departure',
    lateness: 'None',
    device: 'Pediatrics Device',
    review: 'Review',
    tone: 'gold',
  },
  {
    name: 'Sani Umar',
    staffId: 'SHK-TH-009',
    role: 'Theatre Assistant',
    department: 'Theatre',
    phone: '08030009999',
    shift: 'Morning',
    clockIn: 'No clock-in',
    clockOut: 'Not applicable',
    status: 'Absent',
    lateness: 'None',
    device: 'No biometric record',
    review: 'Escalate',
    tone: 'rose',
  },
  {
    name: 'Maryam Ali',
    staffId: 'SHK-RC-018',
    role: 'Records Officer',
    department: 'GOPD',
    phone: '08030001010',
    shift: 'Morning',
    clockIn: '08:55 AM',
    clockOut: 'In progress',
    status: 'On Time',
    lateness: 'None',
    device: 'Main Entrance Device',
    review: 'Normal',
    tone: 'emerald',
  },
];

const attendanceDepartmentSnapshots: DepartmentAttendanceSnapshot[] = [
  { department: 'GOPD', expected: 14, onDuty: 14, status: 'Covered', tone: 'emerald' },
  { department: 'A&E', expected: 16, onDuty: 15, status: 'Covered', tone: 'emerald' },
  { department: 'Female Ward', expected: 13, onDuty: 11, status: 'Review', tone: 'rose' },
  { department: 'Theatre', expected: 7, onDuty: 5, status: 'Understaffed', tone: 'rose' },
  { department: 'Pharmacy', expected: 11, onDuty: 10, status: 'Watch', tone: 'amber' },
  { department: 'Laboratory', expected: 9, onDuty: 9, status: 'Covered', tone: 'emerald' },
];

const biometricWorkflowSignals: ExecutiveSignal[] = [
  {
    label: 'Device Capture',
    value: 'Fingerprint scan',
    context: '01',
    tone: 'steel',
  },
  {
    label: 'Identity Match',
    value: 'Staff profile linked',
    context: '02',
    tone: 'cyan',
  },
  {
    label: 'Clock Event Created',
    value: 'Time stamped',
    context: '03',
    tone: 'emerald',
  },
  {
    label: 'Attendance Rule Applied',
    value: 'Policy checked',
    context: '04',
    tone: 'gold',
  },
  {
    label: 'Exception Flagged',
    value: 'Risk classified',
    context: '05',
    tone: 'amber',
  },
  {
    label: 'CMD Visibility',
    value: 'Monitoring view',
    context: '06',
    tone: 'emerald',
  },
];

const biometricDeviceHealth: BiometricDeviceHealth[] = [
  {
    name: 'Main Entrance Device',
    status: 'Online',
    events: 36,
    lastSync: '11:42 AM',
    location: 'Main entrance',
    latency: '8 sec',
    integrity: 'Matched',
    tone: 'emerald',
  },
  {
    name: 'A&E Gate Device',
    status: 'Online',
    events: 18,
    lastSync: '11:41 AM',
    location: 'A&E gate',
    latency: '10 sec',
    integrity: 'Matched',
    tone: 'emerald',
  },
  {
    name: 'Female Ward Device 02',
    status: 'Online',
    events: 14,
    lastSync: '11:39 AM',
    location: 'Female ward',
    latency: '11 sec',
    integrity: 'Late flag generated',
    tone: 'emerald',
  },
  {
    name: 'Laboratory Device',
    status: 'Online',
    events: 12,
    lastSync: '11:38 AM',
    location: 'Laboratory',
    latency: '12 sec',
    integrity: 'Matched',
    tone: 'emerald',
  },
  {
    name: 'Pharmacy Device',
    status: 'Online',
    events: 10,
    lastSync: '11:37 AM',
    location: 'Pharmacy',
    latency: '14 sec',
    integrity: 'Matched',
    tone: 'emerald',
  },
  {
    name: 'Theatre Device',
    status: 'Warning',
    events: 6,
    lastSync: '11:21 AM',
    location: 'Theatre',
    latency: '4 min',
    integrity: 'Sync delay',
    tone: 'amber',
  },
  {
    name: 'Maternity Device',
    status: 'Online',
    events: 11,
    lastSync: '11:36 AM',
    location: 'Maternity',
    latency: '13 sec',
    integrity: 'Matched',
    tone: 'emerald',
  },
  {
    name: 'Radiology Device',
    status: 'Online',
    events: 7,
    lastSync: '11:35 AM',
    location: 'Radiology',
    latency: '15 sec',
    integrity: 'Matched',
    tone: 'emerald',
  },
];

const shiftComplianceMetrics: ExecutiveSignal[] = [
  { label: 'Overall Shift Compliance', value: '91%', context: 'Roster coverage across active shifts', tone: 'emerald' },
  { label: 'Morning Shift Coverage', value: '88%', context: 'Current morning roster posture', tone: 'amber' },
  { label: 'Afternoon Shift Coverage', value: '96%', context: 'Handover readiness stable', tone: 'emerald' },
  { label: 'Night Shift Coverage', value: '93%', context: 'Night roster coverage visible', tone: 'emerald' },
  { label: 'Late Arrival Impact', value: '3', context: 'Departments affected by lateness', tone: 'amber' },
  { label: 'Understaffed Units', value: '2', context: 'Female Ward and Theatre', tone: 'rose' },
  { label: 'Supervisor Reviews', value: '4', context: 'Shift exceptions needing review', tone: 'gold' },
  { label: 'Roster Exceptions', value: '6', context: 'Late, absent, and coverage exceptions', tone: 'rose' },
];

const shiftWindowCompliance: ShiftWindowCompliance[] = [
  {
    name: 'Morning Shift',
    window: '7:30 AM-2:00 PM',
    expected: 142,
    present: 126,
    late: 3,
    absent: 2,
    compliance: 88,
    state: 'Watch',
    tone: 'amber',
  },
  {
    name: 'Afternoon Shift',
    window: '2:00 PM-9:00 PM',
    expected: 118,
    present: 113,
    late: 1,
    absent: 0,
    compliance: 96,
    state: 'Stable',
    tone: 'emerald',
  },
  {
    name: 'Night Shift',
    window: '9:00 PM-7:30 AM',
    expected: 74,
    present: 69,
    late: 0,
    absent: 1,
    compliance: 93,
    state: 'Stable',
    tone: 'emerald',
  },
];

const departmentShiftCompliance: DepartmentShiftCompliance[] = [
  { department: 'GOPD', shift: 'Morning', expected: 14, present: 14, compliance: 100, state: 'Covered', tone: 'emerald' },
  { department: 'A&E', shift: 'Morning', expected: 16, present: 15, compliance: 94, state: 'Pressure', tone: 'amber' },
  { department: 'Female Ward', shift: 'Morning', expected: 13, present: 11, compliance: 85, state: 'Review', tone: 'rose' },
  { department: 'Theatre', shift: 'Morning', expected: 7, present: 5, compliance: 71, state: 'Understaffed', tone: 'rose' },
  { department: 'Pharmacy', shift: 'Morning', expected: 11, present: 10, compliance: 91, state: 'Watch', tone: 'amber' },
  { department: 'Laboratory', shift: 'Morning', expected: 9, present: 9, compliance: 100, state: 'Covered', tone: 'emerald' },
  { department: 'Maternity', shift: 'Morning', expected: 10, present: 10, compliance: 100, state: 'Covered', tone: 'emerald' },
  { department: 'Pediatrics', shift: 'Morning', expected: 9, present: 8, compliance: 89, state: 'Watch', tone: 'amber' },
  { department: 'Male Ward', shift: 'Morning', expected: 11, present: 11, compliance: 100, state: 'Covered', tone: 'emerald' },
  { department: 'Radiology', shift: 'Morning', expected: 6, present: 6, compliance: 100, state: 'Covered', tone: 'emerald' },
];

const shiftComplianceExceptions: ShiftComplianceException[] = [
  {
    title: 'Female Ward below coverage threshold',
    detail: 'Morning roster coverage is 11 of 13 with supervisor review required.',
    severity: 'Review',
    tone: 'rose',
  },
  {
    title: 'Theatre understaffed',
    detail: 'Theatre is operating at 5 of 7 rostered staff and needs CMD visibility.',
    severity: 'Understaffed',
    tone: 'rose',
  },
  {
    title: 'Pharmacy watch due to late arrival',
    detail: 'One late arrival reduced early morning coverage confidence.',
    severity: 'Watch',
    tone: 'amber',
  },
  {
    title: 'Pediatrics watch due to early departure',
    detail: 'Early departure requires supervisor confirmation for roster continuity.',
    severity: 'Watch',
    tone: 'gold',
  },
  {
    title: 'A&E pressure due to one absent staff',
    detail: 'A&E remains functional but shows pressure against expected emergency shift coverage.',
    severity: 'Pressure',
    tone: 'amber',
  },
];

const shiftComplianceTimeline: ShiftComplianceEvent[] = [
  {
    time: '07:30 AM',
    title: 'Morning shift opened',
    detail: 'Morning roster window activated for department coverage monitoring.',
    tone: 'steel',
  },
  {
    time: '08:52 AM',
    title: 'A&E doctor coverage confirmed',
    detail: 'Emergency department doctor coverage moved to compliant posture.',
    tone: 'emerald',
  },
  {
    time: '09:47 AM',
    title: 'Female Ward late arrival affected coverage',
    detail: 'Female Ward moved below coverage threshold and entered review state.',
    tone: 'rose',
  },
  {
    time: '10:12 AM',
    title: 'Maternity late arrival reviewed',
    detail: 'Maternity late-arrival signal reviewed without reducing coverage below threshold.',
    tone: 'amber',
  },
  {
    time: '12:20 PM',
    title: 'Pediatrics early departure flagged',
    detail: 'Pediatrics requires supervisor confirmation before shift close.',
    tone: 'gold',
  },
  {
    time: '02:00 PM',
    title: 'Afternoon shift handover pending',
    detail: 'Afternoon roster coverage is prepared for handover verification.',
    tone: 'cyan',
  },
];

const workforceAnalyticsMetrics: ExecutiveSignal[] = [
  { label: 'Departments Covered', value: '10 / 12', context: 'Department workforce visibility', tone: 'emerald' },
  { label: 'Workforce Pressure', value: 'Moderate', context: 'Composite staffing pressure signal', tone: 'amber' },
  { label: 'Exception Pattern', value: '13', context: 'Trend-level workforce exceptions', tone: 'rose' },
  { label: 'Understaffed Units', value: '2', context: 'High-pressure departments', tone: 'rose' },
  { label: 'Attendance Trend', value: '+8%', context: 'Arrival consistency movement', tone: 'emerald' },
  { label: 'Overtime Risk', value: 'Medium', context: 'Coverage pressure forecast', tone: 'gold' },
  { label: 'Coverage Stability', value: '91%', context: 'Overall workforce stability', tone: 'cyan' },
  { label: 'Review Required', value: '4 units', context: 'CMD insight follow-up scope', tone: 'amber' },
];

const workforceComparison: WorkforceComparison[] = [
  { department: 'GOPD', state: 'Stable', coverage: '14/14', pressure: 'Low pressure', tone: 'emerald' },
  { department: 'A&E', state: 'Pressure', coverage: '15/16', pressure: 'Moderate pressure', tone: 'amber' },
  { department: 'Female Ward', state: 'Review', coverage: '11/13', pressure: 'High pressure', tone: 'rose' },
  { department: 'Theatre', state: 'Understaffed', coverage: '5/7', pressure: 'High pressure', tone: 'rose' },
  { department: 'Pharmacy', state: 'Watch', coverage: '10/11', pressure: 'Moderate pressure', tone: 'amber' },
  { department: 'Laboratory', state: 'Stable', coverage: '9/9', pressure: 'Low pressure', tone: 'emerald' },
  { department: 'Maternity', state: 'Stable', coverage: '10/10', pressure: 'Low pressure', tone: 'emerald' },
  { department: 'Pediatrics', state: 'Watch', coverage: '8/9', pressure: 'Moderate pressure', tone: 'amber' },
  { department: 'Male Ward', state: 'Stable', coverage: '11/11', pressure: 'Low pressure', tone: 'emerald' },
  { department: 'Radiology', state: 'Stable', coverage: '6/6', pressure: 'Low pressure', tone: 'emerald' },
];

const workforceExceptionPatterns: WorkforcePattern[] = [
  {
    label: 'Late arrival concentration',
    value: 'Female Ward / Pharmacy / Maternity',
    detail: 'Repeated late-arrival signals affecting early shift stability.',
    tone: 'amber',
  },
  {
    label: 'Absence concentration',
    value: 'Theatre / Male Ward',
    detail: 'Absence signals create coverage pressure in critical areas.',
    tone: 'rose',
  },
  {
    label: 'Early departure pattern',
    value: 'Pediatrics',
    detail: 'One early departure pattern requires supervisor confirmation.',
    tone: 'gold',
  },
  {
    label: 'Highest-risk unit',
    value: 'Theatre',
    detail: 'Theatre combines understaffing and handover pressure risk.',
    tone: 'rose',
  },
  {
    label: 'Most stable units',
    value: 'GOPD, Laboratory, Radiology',
    detail: 'Stable coverage and low exception pressure across the trend window.',
    tone: 'emerald',
  },
];

const workforceRiskForecast: WorkforcePattern[] = [
  {
    label: 'Next 24h risk',
    value: 'Moderate',
    detail: 'Coverage risk remains manageable with supervisor follow-up.',
    tone: 'amber',
  },
  {
    label: 'Theatre staffing risk',
    value: 'High',
    detail: 'Theatre should be reviewed before the next shift window.',
    tone: 'rose',
  },
  {
    label: 'Female Ward pressure',
    value: 'Elevated',
    detail: 'Late-arrival pattern is affecting coverage stability.',
    tone: 'amber',
  },
  {
    label: 'A&E pressure',
    value: 'Watch',
    detail: 'A&E remains covered but has limited buffer capacity.',
    tone: 'gold',
  },
  {
    label: 'Recommended action',
    value: 'Supervisor review',
    detail: 'Department leads should confirm corrective coverage before handover.',
    tone: 'cyan',
  },
];

const workforceInsights: WorkforceInsight[] = [
  {
    title: 'Theatre requires staffing attention before next shift window.',
    detail: 'Coverage pressure is highest in Theatre and should remain CMD-visible.',
    tone: 'rose',
  },
  {
    title: 'Female Ward late-arrival pattern is affecting coverage stability.',
    detail: 'Repeated morning lateness is creating avoidable supervisor review pressure.',
    tone: 'amber',
  },
  {
    title: 'GOPD and Laboratory are stable with complete coverage.',
    detail: 'Both units show consistent coverage and low workforce exception pressure.',
    tone: 'emerald',
  },
  {
    title: 'Pharmacy remains under watch due to repeated lateness signal.',
    detail: 'Pharmacy is not understaffed, but the trend justifies executive monitoring.',
    tone: 'gold',
  },
];

const departmentStaffingStatus: DepartmentStaffingStatus[] = [
  {
    department: 'General Outpatient Department (GOPD)',
    required: 14,
    onDuty: 14,
    status: 'Covered',
    risk: 'Low',
    visibility: 'Routine visibility',
    tone: 'emerald',
  },
  {
    department: 'Accident & Emergency (A&E)',
    required: 16,
    onDuty: 15,
    status: 'Pressure',
    risk: 'Medium',
    visibility: 'CMD watch',
    tone: 'amber',
  },
  {
    department: 'Specialist Clinics',
    required: 12,
    onDuty: 12,
    status: 'Covered',
    risk: 'Low',
    visibility: 'Routine visibility',
    tone: 'emerald',
  },
  {
    department: 'Maternity',
    required: 10,
    onDuty: 10,
    status: 'Covered',
    risk: 'Low',
    visibility: 'Routine visibility',
    tone: 'emerald',
  },
  {
    department: 'Pediatrics',
    required: 9,
    onDuty: 8,
    status: 'Watch',
    risk: 'Medium',
    visibility: 'Supervisor watch',
    tone: 'amber',
  },
  {
    department: 'Gynecology',
    required: 8,
    onDuty: 8,
    status: 'Covered',
    risk: 'Low',
    visibility: 'Routine visibility',
    tone: 'emerald',
  },
  {
    department: 'Male Ward',
    required: 11,
    onDuty: 11,
    status: 'Covered',
    risk: 'Low',
    visibility: 'Routine visibility',
    tone: 'emerald',
  },
  {
    department: 'Female Ward',
    required: 13,
    onDuty: 11,
    status: 'Review',
    risk: 'High',
    visibility: 'CMD review',
    tone: 'rose',
  },
  {
    department: 'Theatre',
    required: 7,
    onDuty: 5,
    status: 'Understaffed',
    risk: 'High',
    visibility: 'Immediate CMD visibility',
    tone: 'rose',
  },
  {
    department: 'Laboratory',
    required: 9,
    onDuty: 9,
    status: 'Covered',
    risk: 'Low',
    visibility: 'Routine visibility',
    tone: 'emerald',
  },
  {
    department: 'Radiology',
    required: 6,
    onDuty: 6,
    status: 'Covered',
    risk: 'Low',
    visibility: 'Routine visibility',
    tone: 'emerald',
  },
  {
    department: 'Pharmacy',
    required: 11,
    onDuty: 10,
    status: 'Watch',
    risk: 'Medium',
    visibility: 'Supervisor watch',
    tone: 'amber',
  },
];

const departmentStaffingMetrics: ExecutiveSignal[] = [
  { label: 'Departments Covered', value: '10 / 12', context: 'Departments with acceptable coverage posture', tone: 'emerald' },
  { label: 'Fully Covered Units', value: '7', context: 'Departments at 100% coverage', tone: 'emerald' },
  { label: 'Watch Units', value: '3', context: 'Pressure or watch posture', tone: 'amber' },
  { label: 'Understaffed Units', value: '2', context: 'High-risk coverage gaps', tone: 'rose' },
  { label: 'Staff Required', value: '154', context: 'Hospital-wide staffing requirement', tone: 'steel' },
  { label: 'Staff On Duty', value: '126', context: 'Staff currently visible on duty', tone: 'cyan' },
  { label: 'Coverage Compliance', value: '91%', context: 'Current staffing posture compliance', tone: 'emerald' },
  { label: 'CMD Review Required', value: '4', context: 'Units requiring executive visibility', tone: 'gold' },
];

const priorityStaffingRisks = [
  { department: 'Theatre', gap: '2 staff short', risk: 'High risk', tone: 'rose' as SignalTone },
  { department: 'Female Ward', gap: '2 staff short', risk: 'High risk', tone: 'rose' as SignalTone },
  { department: 'A&E', gap: '1 staff short', risk: 'Medium pressure', tone: 'amber' as SignalTone },
  { department: 'Pharmacy', gap: '1 staff short', risk: 'Watch', tone: 'gold' as SignalTone },
  { department: 'Pediatrics', gap: '1 staff short', risk: 'Watch', tone: 'gold' as SignalTone },
];

const departmentCoverageDistribution = [
  { label: 'Covered', value: '7 departments', tone: 'emerald' as SignalTone },
  { label: 'Watch / Pressure', value: '3 departments', tone: 'amber' as SignalTone },
  { label: 'Understaffed / Review', value: '2 departments', tone: 'rose' as SignalTone },
];

const cmdStaffingActions = [
  { label: 'Notify department supervisor', tone: 'cyan' as SignalTone },
  { label: 'Request staffing justification', tone: 'gold' as SignalTone },
  { label: 'Escalate understaffed unit', tone: 'rose' as SignalTone },
  { label: 'Export staffing posture report', tone: 'emerald' as SignalTone },
];

const recentBiometricEvents: BiometricEvent[] = [
  {
    time: '11:42 AM',
    device: 'Main Entrance Device',
    subject: 'Fingerprint match',
    event: 'Successful',
    state: 'Verified',
    detail: 'Device captured and synced a valid fingerprint match.',
    tone: 'emerald',
  },
  {
    time: '11:41 AM',
    device: 'A&E Gate Device',
    subject: "Dr. Nasir Ya'u",
    event: 'Successful',
    state: 'Identity matched',
    detail: 'Fingerprint event linked to A&E staff profile.',
    tone: 'emerald',
  },
  {
    time: '11:39 AM',
    device: 'Female Ward Device 02',
    subject: 'Nurse Amina Bello',
    event: 'Late flag generated',
    state: 'Rule applied',
    detail: 'Clock-in event synced and late-arrival rule applied.',
    tone: 'amber',
  },
  {
    time: '11:31 AM',
    device: 'Theatre Device',
    subject: 'Device sync',
    event: 'Sync delay warning',
    state: 'Warning',
    detail: 'Device latency exceeded monitoring threshold.',
    tone: 'amber',
  },
  {
    time: '11:28 AM',
    device: 'Pharmacy Device',
    subject: 'Pharmacy staff',
    event: 'Identity matched',
    state: 'Verified',
    detail: 'Fingerprint template matched to registered staff identity.',
    tone: 'emerald',
  },
  {
    time: '11:22 AM',
    device: 'Main Entrance Device',
    subject: 'Unknown fingerprint',
    event: 'Unmatched attempt',
    state: 'Review',
    detail: 'Unmatched fingerprint attempt retained for monitoring review.',
    tone: 'rose',
  },
];

const executiveReportRows: ExecutiveTableRow[] = [
  {
    domain: 'Operational Reports',
    signal: 'Patient flow, admissions, discharges, ward utilization, and follow-up compliance',
    owner: 'Hospital Operations',
    state: 'Preview',
    tone: 'emerald',
  },
  {
    domain: 'Financial Reports',
    signal: 'Revenue, outstanding bills, refund activity, and pharmacy revenue traceability',
    owner: 'Finance / Cashier',
    state: 'Preview',
    tone: 'cyan',
  },
  {
    domain: 'Audit Reports',
    signal: 'User activity, patient record access, financial audit, and session posture',
    owner: 'Audit & Compliance',
    state: 'Governed',
    tone: 'steel',
  },
  {
    domain: 'Department Performance Reports',
    signal: 'Department throughput, staffing pressure, and service-line performance summary',
    owner: 'CMD Office',
    state: 'New',
    tone: 'gold',
  },
  {
    domain: 'Executive Export Center',
    signal: 'CMD-ready exports for operational, financial, and compliance briefings',
    owner: 'Executive Reports',
    state: 'Ready',
    tone: 'cyan',
  },
];

const patientFlowTrend = [42, 58, 51, 69, 63, 81, 74, 88, 79, 91, 86, 94];
const revenueTrend = [36, 42, 39, 55, 62, 71, 68, 79, 83, 88, 92, 96];
const workforceArrivalConsistencyTrend = [54, 57, 61, 59, 64, 68, 66, 72, 76, 74, 80, 82];
const workforcePressureTrend = [62, 65, 69, 72, 70, 76, 81, 78, 83, 86, 82, 79];
const workforceExceptionPatternTrend = [38, 44, 41, 49, 52, 58, 56, 63, 67, 72, 69, 74];

const toneClasses: Record<SignalTone, string> = {
  cyan: 'border-cyan-300/26 bg-cyan-400/[0.085] text-cyan-100 shadow-cyan-950/24',
  emerald: 'border-emerald-300/26 bg-emerald-400/[0.085] text-emerald-100 shadow-emerald-950/24',
  amber: 'border-amber-300/26 bg-amber-400/[0.085] text-amber-100 shadow-amber-950/24',
  rose: 'border-rose-300/24 bg-rose-400/[0.085] text-rose-100 shadow-rose-950/26',
  slate: 'border-slate-300/22 bg-slate-400/[0.085] text-slate-100 shadow-slate-950/24',
  steel: 'border-sky-200/22 bg-sky-400/[0.07] text-sky-100 shadow-sky-950/24',
  gold: 'border-yellow-200/22 bg-yellow-400/[0.08] text-yellow-100 shadow-yellow-950/24',
};

const toneSurfaceClasses: Record<SignalTone, string> = {
  cyan: 'border-cyan-300/20 bg-[linear-gradient(135deg,rgba(8,47,73,0.88),rgba(8,145,178,0.115)_45%,rgba(15,23,42,0.74))] shadow-cyan-950/28',
  emerald: 'border-emerald-300/21 bg-[linear-gradient(135deg,rgba(6,78,59,0.82),rgba(16,185,129,0.115)_45%,rgba(15,23,42,0.74))] shadow-emerald-950/28',
  amber: 'border-amber-300/20 bg-[linear-gradient(135deg,rgba(69,39,10,0.84),rgba(245,158,11,0.105)_45%,rgba(15,23,42,0.76))] shadow-amber-950/28',
  rose: 'border-rose-300/22 bg-[linear-gradient(135deg,rgba(76,5,25,0.90),rgba(244,63,94,0.145)_44%,rgba(15,23,42,0.80))] shadow-rose-950/34',
  slate: 'border-slate-300/18 bg-[linear-gradient(135deg,rgba(15,23,42,0.92),rgba(51,65,85,0.17)_45%,rgba(2,6,23,0.78))] shadow-slate-950/30',
  steel: 'border-sky-200/18 bg-[linear-gradient(135deg,rgba(15,23,42,0.92),rgba(56,80,118,0.15)_46%,rgba(2,6,23,0.80))] shadow-sky-950/28',
  gold: 'border-yellow-200/20 bg-[linear-gradient(135deg,rgba(63,42,7,0.82),rgba(234,179,8,0.095)_45%,rgba(15,23,42,0.76))] shadow-yellow-950/28',
};

const dotClasses: Record<SignalTone, string> = {
  cyan: 'bg-cyan-300 shadow-cyan-300/38',
  emerald: 'bg-emerald-300 shadow-emerald-300/38',
  amber: 'bg-amber-300 shadow-amber-300/38',
  rose: 'bg-rose-300 shadow-rose-300/38',
  slate: 'bg-slate-300 shadow-slate-300/36',
  steel: 'bg-sky-200 shadow-sky-200/36',
  gold: 'bg-yellow-200 shadow-yellow-200/36',
};

const lineStrokeClasses: Record<SignalTone, string> = {
  cyan: 'stroke-cyan-200',
  emerald: 'stroke-emerald-200',
  amber: 'stroke-amber-200',
  rose: 'stroke-rose-200',
  slate: 'stroke-slate-200',
  steel: 'stroke-sky-200',
  gold: 'stroke-yellow-200',
};

const chartFillClasses: Record<SignalTone, string> = {
  cyan: 'fill-cyan-400/10',
  emerald: 'fill-emerald-400/10',
  amber: 'fill-amber-400/10',
  rose: 'fill-rose-400/10',
  slate: 'fill-slate-400/10',
  steel: 'fill-sky-400/10',
  gold: 'fill-yellow-400/10',
};

const priorityClasses: Record<KpiPriority, string> = {
  primary: 'md:col-span-2 xl:col-span-4 min-h-[260px] p-5 md:p-6',
  secondary: 'md:col-span-2 xl:col-span-6 min-h-[218px] p-5',
  support: 'md:col-span-1 xl:col-span-3 min-h-[218px] p-5',
};

const panelVariantClasses: Record<PanelVariant, string> = {
  dominant:
    'border-emerald-200/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.92),rgba(6,78,59,0.29)_44%,rgba(2,6,23,0.90))] p-5 md:p-7 shadow-2xl shadow-emerald-950/18',
  standard:
    'border-white/10 bg-white/[0.048] p-5 shadow-xl shadow-slate-950/18',
  compact:
    'border-white/8 bg-white/[0.032] p-5 shadow-lg shadow-slate-950/16',
  alert:
    'border-rose-300/20 bg-[linear-gradient(135deg,rgba(76,5,25,0.48),rgba(15,23,42,0.89)_44%,rgba(2,6,23,0.91))] p-5 md:p-6 shadow-2xl shadow-rose-950/28',
  open:
    'border-white/7 bg-white/[0.024] p-5 md:p-6 shadow-lg shadow-slate-950/14',
  steel:
    'border-sky-200/13 bg-[linear-gradient(135deg,rgba(15,23,42,0.88),rgba(30,58,90,0.20)_46%,rgba(2,6,23,0.86))] p-5 md:p-6 shadow-xl shadow-sky-950/17',
  governance:
    'border-yellow-200/14 bg-[linear-gradient(135deg,rgba(45,32,9,0.34),rgba(15,23,42,0.89)_46%,rgba(2,6,23,0.88))] p-5 md:p-6 shadow-xl shadow-yellow-950/15',
};

function buildPolyline(values: number[], width: number, height: number) {
  const step = width / Math.max(values.length - 1, 1);

  return values
    .map((value, index) => {
      const x = Math.round(index * step);
      const y = Math.round(height - (Math.min(Math.max(value, 0), 100) / 100) * height);
      return `${x},${y}`;
    })
    .join(' ');
}

function CmdAtmosphereStyles() {
  return (
    <style>{`
      @keyframes cmd-atmosphere-drift {
        0%, 100% { transform: translate3d(0, 0, 0) scale(1); opacity: 0.52; }
        50% { transform: translate3d(18px, -14px, 0) scale(1.035); opacity: 0.74; }
      }

      @keyframes cmd-grid-drift {
        0% { background-position: 0 0, 0 0; }
        100% { background-position: 72px 72px, 72px 72px; }
      }

      @keyframes cmd-signal-breathe {
        0%, 100% { transform: scale(1); opacity: 0.42; }
        50% { transform: scale(2.55); opacity: 0.08; }
      }

      @keyframes cmd-soft-sheen {
        0% { transform: translateX(-48%); opacity: 0; }
        35%, 65% { opacity: 0.34; }
        100% { transform: translateX(48%); opacity: 0; }
      }

      .cmd-atmosphere-drift {
        animation: cmd-atmosphere-drift 18s ease-in-out infinite;
        will-change: transform, opacity;
      }

      .cmd-atmosphere-drift-slow {
        animation: cmd-atmosphere-drift 28s ease-in-out infinite reverse;
        will-change: transform, opacity;
      }

      .cmd-grid-drift {
        animation: cmd-grid-drift 46s linear infinite;
        will-change: background-position;
      }

      .cmd-signal-pulse {
        animation: cmd-signal-breathe 3.8s ease-in-out infinite;
        will-change: transform, opacity;
      }

      .cmd-sheen::after {
        content: '';
        position: absolute;
        inset: 0;
        transform: translateX(-48%);
        background: linear-gradient(105deg, transparent 22%, rgba(255,255,255,0.10) 48%, transparent 72%);
        animation: cmd-soft-sheen 9s ease-in-out infinite;
        pointer-events: none;
      }

      @media (prefers-reduced-motion: reduce) {
        .cmd-atmosphere-drift,
        .cmd-atmosphere-drift-slow,
        .cmd-grid-drift,
        .cmd-signal-pulse,
        .cmd-sheen::after {
          animation: none;
        }
      }
    `}</style>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-100/62">
      {children}
    </p>
  );
}

function LiveDot({ tone, pulse = false }: { tone: SignalTone; pulse?: boolean }) {
  return (
    <span className="relative flex h-2.5 w-2.5">
      {pulse ? (
        <span className={`cmd-signal-pulse absolute inline-flex h-full w-full rounded-full opacity-50 ${dotClasses[tone]}`} />
      ) : null}
      <span className={`relative inline-flex h-2.5 w-2.5 rounded-full shadow-lg ${dotClasses[tone]}`} />
    </span>
  );
}

function SignalBadge({
  children,
  tone = 'cyan',
  pulse = false,
}: {
  children: ReactNode;
  tone?: SignalTone;
  pulse?: boolean;
}) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-md border px-2.5 py-1 text-xs font-semibold ${toneClasses[tone]}`}>
      <LiveDot tone={tone} pulse={pulse} />
      {children}
    </span>
  );
}

function LiveSystemMarkers({ compact = false }: { compact?: boolean }) {
  const markers = [
    { label: 'Executive telemetry active', tone: 'cyan' as SignalTone },
    { label: 'Governance refresh stable', tone: 'emerald' as SignalTone },
    { label: 'Bed telemetry synchronized', tone: 'steel' as SignalTone },
  ];

  return (
    <div className={`grid gap-2 ${compact ? 'sm:grid-cols-3' : 'md:grid-cols-3'}`}>
      {markers.map((marker) => (
        <div
          key={marker.label}
          className="flex items-center gap-2 rounded-md border border-white/[0.08] bg-slate-950/28 px-3 py-2"
        >
          <LiveDot tone={marker.tone} pulse={marker.tone === 'cyan'} />
          <p className="text-xs font-semibold text-slate-300">{marker.label}</p>
        </div>
      ))}
    </div>
  );
}

function CmdSidebar({
  activeSection,
  activeSubsection,
  onNavigate,
}: {
  activeSection: string;
  activeSubsection: string;
  onNavigate: (next: ActiveNavigation) => void;
}) {
  return (
    <aside className="cmd-sheen relative overflow-hidden rounded-lg border border-cyan-200/10 bg-[#051120]/92 p-4 shadow-2xl shadow-cyan-950/35 backdrop-blur-2xl xl:sticky xl:top-5 xl:h-[calc(100vh-2.5rem)] xl:overflow-y-auto">
      <div className="pointer-events-none absolute inset-y-6 left-0 w-px bg-gradient-to-b from-transparent via-cyan-300/55 to-transparent" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(8,145,178,0.10),transparent_34%,rgba(16,185,129,0.05)_72%,transparent)]" />
      <div className="cmd-atmosphere-drift-slow pointer-events-none absolute -right-24 top-10 h-64 w-56 bg-[radial-gradient(ellipse_at_center,rgba(125,211,252,0.10),transparent_68%)] blur-3xl" />

      <div className="relative rounded-lg border border-cyan-300/20 bg-gradient-to-br from-cyan-300/12 via-white/[0.035] to-emerald-300/10 p-4 shadow-xl shadow-cyan-950/25">
        <div className="flex items-center gap-3">
          <div className="relative flex h-12 w-12 items-center justify-center rounded-lg border border-cyan-200/30 bg-cyan-100/10 text-sm font-bold text-cyan-50 shadow-lg shadow-cyan-950/30">
            <span className="absolute inset-0 rounded-lg bg-cyan-200/5" />
            <span className="relative">CMD</span>
          </div>
          <div>
            <p className="text-sm font-bold text-white">Executive Center</p>
            <p className="text-xs leading-5 text-cyan-100/60">{HOSPITAL_NAME}</p>
          </div>
        </div>
        <div className="mt-4 h-px bg-gradient-to-r from-transparent via-cyan-200/30 to-transparent" />
        <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
          <span>Command navigation</span>
          <SignalBadge tone="emerald" pulse>
            Active
          </SignalBadge>
        </div>
      </div>

      <nav className="relative mt-6 space-y-5">
        {navigationGroups.map((group) => {
          const isActiveSection = activeSection === group.title;

          return (
          <div key={group.title} className="space-y-2">
            <button
              type="button"
              onClick={() => onNavigate({ section: group.title, subsection: group.items[0] })}
              aria-current={isActiveSection ? 'page' : undefined}
              className={`group relative flex w-full items-center gap-3 overflow-hidden rounded-lg border px-3 py-3 text-left transition duration-300 hover:-translate-y-0.5 hover:border-cyan-200/28 hover:bg-white/[0.065] hover:shadow-lg hover:shadow-cyan-950/20 ${
                isActiveSection
                  ? 'border-cyan-200/32 bg-cyan-300/12 shadow-lg shadow-cyan-950/25'
                  : 'border-white/10 bg-white/[0.03]'
              }`}
            >
              {isActiveSection ? (
                <span className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-cyan-200 shadow-lg shadow-cyan-200/45" />
              ) : null}
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-white/10 bg-white/[0.08] text-xs font-bold text-cyan-100 transition duration-300 group-hover:border-cyan-200/30 group-hover:text-white">
                {group.code}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-white">{group.title}</span>
                <span className="text-xs text-slate-400">{group.items.length} governed views</span>
              </span>
            </button>
            <div className={`ml-11 space-y-1 border-l pl-3 ${isActiveSection ? 'border-cyan-200/24' : 'border-white/[0.07]'}`}>
              {group.items.map((item) => {
                const isActiveSubsection = isActiveSection && activeSubsection === item;

                return (
                <button
                  key={item}
                  type="button"
                  onClick={() => onNavigate({ section: group.title, subsection: item })}
                  aria-current={isActiveSubsection ? 'page' : undefined}
                  className={`relative block w-full rounded-md px-2 py-1.5 text-left text-xs leading-5 transition duration-200 ${
                    isActiveSubsection
                      ? 'bg-cyan-200/10 text-cyan-50 shadow-sm shadow-cyan-950/20'
                      : 'text-slate-500 hover:bg-cyan-200/5 hover:text-cyan-100'
                  }`}
                >
                  {isActiveSubsection ? (
                    <span className="absolute inset-y-2 -left-[13px] w-1 rounded-r-full bg-cyan-200 shadow-md shadow-cyan-200/40" />
                  ) : null}
                  {item}
                </button>
                );
              })}
            </div>
          </div>
          );
        })}
      </nav>
    </aside>
  );
}

function ExecutiveHeader({
  activeSection,
  activeSubsection,
}: {
  activeSection: string;
  activeSubsection: string;
}) {
  const user = useDashboardUser();
  const userName = getDashboardUserDisplayName(user);
  const isDefaultView = activeSection === 'Executive Overview' && activeSubsection === 'Hospital Snapshot';

  return (
    <header className="relative min-h-[360px] overflow-hidden rounded-lg border border-cyan-200/14 bg-[#071526]/94 p-5 shadow-[0_34px_104px_rgba(8,47,73,0.30)] backdrop-blur-2xl md:min-h-[390px] md:p-8 xl:p-10">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(8,145,178,0.145),transparent_30%,rgba(16,185,129,0.08)_64%,rgba(2,6,23,0.22))]" />
      <div className="cmd-grid-drift pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(125,211,252,0.052)_1px,transparent_1px),linear-gradient(90deg,rgba(125,211,252,0.042)_1px,transparent_1px)] bg-[size:56px_56px] opacity-42" />
      <div className="cmd-atmosphere-drift pointer-events-none absolute -left-28 -top-28 h-80 w-[72%] bg-[radial-gradient(ellipse_at_center,rgba(125,211,252,0.13),transparent_68%)] blur-3xl" />
      <div className="cmd-atmosphere-drift-slow pointer-events-none absolute -bottom-28 right-0 h-72 w-[62%] bg-[radial-gradient(ellipse_at_center,rgba(45,212,191,0.10),transparent_70%)] blur-3xl" />
      <div className="pointer-events-none absolute inset-x-10 bottom-0 h-28 bg-gradient-to-t from-slate-950/52 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-200/60 to-transparent" />

      <div className="relative flex min-h-[310px] flex-col justify-between gap-9">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SectionLabel>Chief Medical Director Workstation</SectionLabel>
          <div className="flex flex-wrap gap-2">
            <SignalBadge tone="emerald" pulse>
              Executive access verified
            </SignalBadge>
            <SignalBadge tone="amber">{activeSection}</SignalBadge>
          </div>
        </div>

        <div className="grid gap-8 2xl:grid-cols-[minmax(520px,1fr)_minmax(360px,520px)] 2xl:items-end">
          <div className="min-w-0 max-w-full">
            <h1 className="max-w-[780px] whitespace-normal text-4xl font-bold leading-[0.95] tracking-tight text-white [overflow-wrap:normal] [text-wrap:balance] [word-break:normal] sm:text-5xl lg:text-6xl 2xl:text-7xl">
              {isDefaultView ? 'Executive Command Center' : activeSubsection}
            </h1>
              <p className="mt-6 max-w-3xl text-sm leading-7 text-slate-200/90 md:text-base">
              {isDefaultView
                ? 'Hospital-wide operational intelligence for governance, financial visibility, audit traceability, workforce accountability, and supply oversight.'
                : `Focused CMD-level view for ${activeSubsection.toLowerCase()} under ${activeSection}.`}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-cyan-300/18 bg-cyan-300/[0.08] p-4 shadow-lg shadow-cyan-950/16">
              <p className="text-xs uppercase tracking-[0.18em] text-cyan-100/72">Executive</p>
              <p className="mt-2 truncate text-base font-semibold text-white">{userName}</p>
            </div>
            <div className="rounded-lg border border-emerald-300/18 bg-emerald-300/[0.08] p-4 shadow-lg shadow-emerald-950/16">
              <p className="text-xs uppercase tracking-[0.18em] text-emerald-100/72">Command Posture</p>
              <p className="mt-2 text-base font-semibold text-white">Oversight active</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-slate-950/40 p-4 sm:col-span-2">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm leading-6 text-slate-300">
                  Preview data only. Live HIS telemetry is not connected in this frontend pass.
                </p>
                <SignalBadge tone="cyan">Frontend intelligence view</SignalBadge>
              </div>
              <div className="mt-4">
                <LiveSystemMarkers compact />
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {executiveSignals.map((signal) => (
            <div
              key={signal.label}
              className={`group rounded-lg border p-3.5 shadow-lg transition duration-300 hover:-translate-y-0.5 hover:shadow-xl ${toneSurfaceClasses[signal.tone]}`}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-current/74">
                  {signal.label}
                </p>
                <LiveDot tone={signal.tone} pulse={signal.tone === 'rose' || signal.tone === 'emerald'} />
              </div>
              <p className="mt-3 text-2xl font-bold text-white">{signal.value}</p>
              <p className="mt-1 text-xs leading-5 text-slate-200/88">{signal.context}</p>
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}

function Sparkline({ values, tone }: { values: number[]; tone: SignalTone }) {
  const points = buildPolyline(values, 112, 44);

  return (
    <div className="rounded-lg border border-white/10 bg-slate-950/30 p-2">
      <svg className="h-12 w-full" viewBox="0 0 112 44" aria-hidden="true">
        <polyline
          points={points}
          fill="none"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`${lineStrokeClasses[tone]} drop-shadow-[0_0_8px_rgba(125,211,252,0.25)]`}
        />
      </svg>
    </div>
  );
}

function KpiCard({ metric }: { metric: KpiMetric }) {
  const isPrimary = metric.priority === 'primary';

  return (
    <article
      className={`cmd-sheen group relative overflow-hidden rounded-lg border shadow-2xl transition duration-300 hover:-translate-y-1 hover:border-white/22 hover:shadow-cyan-950/28 ${toneSurfaceClasses[metric.tone]} ${priorityClasses[metric.priority]}`}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/38 to-transparent opacity-70" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(125,211,252,0.024)_1px,transparent_1px),linear-gradient(90deg,rgba(125,211,252,0.018)_1px,transparent_1px)] bg-[size:44px_44px] opacity-32" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.058),transparent_30%,rgba(255,255,255,0.016)_72%,transparent)] opacity-70 transition duration-300 group-hover:opacity-90" />

      <div className="relative flex h-full flex-col justify-between gap-5">
        <div>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-current/78">
                {metric.label}
              </p>
              <p className="mt-2 text-xs font-semibold text-slate-300">{metric.context}</p>
            </div>
            <LiveDot tone={metric.tone} pulse={isPrimary} />
          </div>
          <p className={`mt-5 font-bold leading-none text-white ${isPrimary ? 'text-5xl md:text-6xl' : 'text-4xl'}`}>
            {metric.value}
          </p>
          <p className="mt-4 text-sm leading-6 text-slate-200/88">{metric.detail}</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_132px] sm:items-end">
          <div className="border-t border-white/10 pt-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-current/72">
              {metric.delta}
            </p>
          </div>
          <Sparkline values={metric.trend} tone={metric.tone} />
        </div>
      </div>
    </article>
  );
}

function Panel({
  title,
  eyebrow,
  children,
  action,
  variant = 'standard',
}: {
  title: string;
  eyebrow: string;
  children: ReactNode;
  action?: ReactNode;
  variant?: PanelVariant;
}) {
  return (
    <section className={`cmd-sheen relative overflow-hidden rounded-lg border backdrop-blur-xl ${panelVariantClasses[variant]}`}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-200/28 to-transparent" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(125,211,252,0.026)_1px,transparent_1px),linear-gradient(90deg,rgba(125,211,252,0.020)_1px,transparent_1px)] bg-[size:48px_48px] opacity-35" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.055),transparent_32%,rgba(255,255,255,0.018)_70%,transparent)]" />
      <div className="relative">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <SectionLabel>{eyebrow}</SectionLabel>
            <h2 className="mt-2 text-xl font-bold text-white md:text-2xl">{title}</h2>
          </div>
          {action}
        </div>
        {children}
      </div>
    </section>
  );
}

function ProgressMeter({ value, tone }: { value: number; tone: SignalTone }) {
  const fillClass: Record<SignalTone, string> = {
    cyan: 'bg-gradient-to-r from-cyan-500 to-cyan-200 shadow-cyan-300/22',
    emerald: 'bg-gradient-to-r from-emerald-500 to-emerald-200 shadow-emerald-300/22',
    amber: 'bg-gradient-to-r from-amber-500 to-amber-200 shadow-amber-300/22',
    rose: 'bg-gradient-to-r from-rose-500 to-rose-200 shadow-rose-300/22',
    slate: 'bg-gradient-to-r from-slate-500 to-slate-200 shadow-slate-300/22',
    steel: 'bg-gradient-to-r from-sky-600 to-sky-200 shadow-sky-300/22',
    gold: 'bg-gradient-to-r from-yellow-600 to-yellow-200 shadow-yellow-300/22',
  };

  return (
    <div className="h-2 overflow-hidden rounded-md bg-white/10">
      <div className={`h-full rounded-md shadow-lg ${fillClass[tone]}`} style={{ width: `${value}%` }} />
    </div>
  );
}

function DepartmentLoadCard({ item }: { item: DepartmentLoad }) {
  const utilization = Math.round((item.current / item.capacity) * 100);

  return (
    <div className="group relative overflow-hidden rounded-lg border border-white/10 bg-slate-950/35 p-4 transition duration-300 hover:-translate-y-0.5 hover:border-cyan-200/25 hover:bg-white/[0.065]">
      <div className="absolute inset-y-4 left-0 w-px bg-gradient-to-b from-transparent via-cyan-200/35 to-transparent opacity-0 transition duration-300 group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-white">{item.department}</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">{item.pressure}</p>
        </div>
        <SignalBadge tone={item.tone}>{utilization}%</SignalBadge>
      </div>
      <div className="mt-5">
        <ProgressMeter value={utilization} tone={item.tone} />
      </div>
      <p className="mt-3 text-xs text-slate-400">
        {item.current} active out of {item.capacity} monitored capacity
      </p>
    </div>
  );
}

function TelemetryChart({
  values,
  tone,
  label,
  meta,
}: {
  values: number[];
  tone: SignalTone;
  label: string;
  meta: string;
}) {
  const points = buildPolyline(values, 360, 128);
  const areaPoints = `0,128 ${points} 360,128`;

  return (
    <div className={`relative overflow-hidden rounded-lg border p-4 shadow-xl ${toneSurfaceClasses[tone]}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">{label}</p>
          <p className="mt-1 text-xs text-slate-300">{meta}</p>
        </div>
        <SignalBadge tone={tone}>Telemetry</SignalBadge>
      </div>
      <div className="relative mt-5 h-40 rounded-lg border border-white/10 bg-slate-950/35 p-3">
        <div className="absolute inset-3 bg-[linear-gradient(rgba(148,163,184,0.105)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.085)_1px,transparent_1px)] bg-[size:40px_32px] opacity-38" />
        <svg className="relative h-full w-full" viewBox="0 0 360 128" preserveAspectRatio="none" aria-hidden="true">
          <polygon points={areaPoints} className={chartFillClasses[tone]} />
          <polyline
            points={points}
            fill="none"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`${lineStrokeClasses[tone]} drop-shadow-[0_0_10px_rgba(125,211,252,0.22)]`}
          />
        </svg>
      </div>
    </div>
  );
}

function ExecutiveRows({ rows }: { rows: ExecutiveTableRow[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-white/[0.08]">
      {rows.map((row) => (
        <div
          key={row.domain}
          className="group relative grid gap-4 border-b border-white/[0.065] bg-slate-950/20 px-4 py-5 transition duration-300 last:border-b-0 hover:bg-white/[0.045] md:grid-cols-[1fr_1.55fr_0.8fr_auto]"
        >
          <div className={`absolute inset-y-3 left-0 w-px rounded-full ${dotClasses[row.tone]}`} />
          <div>
            <p className="font-semibold text-white">{row.domain}</p>
            <p className="mt-1 text-xs text-slate-500">Executive visibility domain</p>
          </div>
          <p className="text-sm leading-6 text-slate-400">{row.signal}</p>
          <div className="text-sm text-slate-400">{row.owner}</div>
          <div className="md:text-right">
            <SignalBadge tone={row.tone}>{row.state}</SignalBadge>
          </div>
        </div>
      ))}
    </div>
  );
}

function AlertCard({
  title,
  detail,
  tone,
  label,
}: {
  title: string;
  detail: string;
  tone: SignalTone;
  label: string;
}) {
  return (
      <div className={`group relative overflow-hidden rounded-lg border p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-xl ${toneSurfaceClasses[tone]} ${tone === 'rose' ? 'shadow-[0_0_52px_rgba(127,29,29,0.16)]' : ''}`}>
      {tone === 'rose' ? (
        <div className="cmd-atmosphere-drift pointer-events-none absolute -inset-x-8 -top-14 h-28 bg-[radial-gradient(ellipse_at_center,rgba(251,113,133,0.145),transparent_72%)] blur-2xl" />
      ) : null}
      <div className="absolute inset-y-4 left-0 w-px bg-current opacity-40" />
      <div className="relative flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-white">{title}</p>
          <p className="mt-2 text-sm leading-6 text-slate-200/88">{detail}</p>
        </div>
        <SignalBadge tone={tone} pulse={tone === 'rose'}>
          {label}
        </SignalBadge>
      </div>
    </div>
  );
}

function ActivityFeed() {
  return (
    <div className="relative">
      <div className="absolute bottom-4 left-[18px] top-4 w-px bg-gradient-to-b from-cyan-200/60 via-white/16 to-emerald-200/45" />
      <div className="space-y-4">
        {activityFeed.map((item) => (
          <div key={`${item.time}-${item.title}`} className="relative pl-11">
            <div className="absolute left-0 top-5 flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-slate-950 shadow-lg shadow-cyan-950/20">
              <LiveDot tone={item.tone} pulse={item.tone === 'rose' || item.tone === 'amber'} />
            </div>
            <div className={`group rounded-lg border p-4 transition duration-300 hover:-translate-y-0.5 hover:border-white/24 ${toneSurfaceClasses[item.tone]}`}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-cyan-100/72">{item.time}</span>
                  <SignalBadge tone={item.tone}>{item.severity}</SignalBadge>
                </div>
              </div>
              <p className="mt-3 font-semibold text-white">{item.title}</p>
              <p className="mt-2 text-sm leading-6 text-slate-200/88">{item.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TrustSignalGrid() {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {financialTrustSignals.map((signal) => (
        <div key={signal.label} className={`rounded-lg border p-3 ${toneSurfaceClasses[signal.tone]}`}>
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-current/65">
              {signal.label}
            </p>
            <LiveDot tone={signal.tone} />
          </div>
          <p className="mt-2 text-xl font-bold text-white">{signal.value}</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">{signal.context}</p>
        </div>
      ))}
    </div>
  );
}

function FinancialFilterPanel({
  searchPlaceholder,
  filters,
}: {
  searchPlaceholder: string;
  filters: { label: string; options: string[] }[];
}) {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-slate-950/24 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Executive Filters & Search</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Backend-ready financial search surface prepared for CMD audit and drilldown.
          </p>
        </div>
        <SignalBadge tone="cyan">Demo controls</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[1.35fr_repeat(5,minmax(0,1fr))]">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Search
          </span>
          <input
            type="search"
            placeholder={searchPlaceholder}
            className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/45 px-3 py-3 text-sm font-medium text-slate-200 outline-none transition placeholder:text-slate-400 focus:border-cyan-200/45"
          />
        </label>
        {filters.map((filter) => (
          <DemoSelect key={filter.label} label={filter.label} options={filter.options} />
        ))}
      </div>
    </div>
  );
}

function PaymentMethodSplitPanel() {
  const methodSplit = [
    { label: 'POS Collections', value: '₦3.62M', share: 43, tone: 'cyan' as SignalTone },
    { label: 'Bank Transfer', value: '₦2.88M', share: 34, tone: 'steel' as SignalTone },
    { label: 'Cash Collections', value: '₦1.92M', share: 23, tone: 'gold' as SignalTone },
  ];

  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.04] p-5 shadow-xl shadow-cyan-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Payment Method Split</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Collection method posture for authorized POS, Bank Transfer, and Cash payments.
          </p>
        </div>
        <SignalBadge tone="emerald">Reconciliation stable</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {methodSplit.map((item) => (
          <div key={item.label} className={`rounded-lg border p-4 ${toneSurfaceClasses[item.tone]}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-current/65">{item.label}</p>
                <p className="mt-2 text-2xl font-bold text-white">{item.value}</p>
              </div>
              <SignalBadge tone={item.tone}>{item.share}%</SignalBadge>
            </div>
            <div className="mt-4">
              <ProgressMeter value={item.share} tone={item.tone} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RevenueDepartmentSummaryPanel() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Top Revenue Departments</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Highest revenue-generating departments in the current CMD financial view.
          </p>
        </div>
        <SignalBadge tone="cyan">Department summary</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {departmentRevenueRows.slice(0, 3).map((department) => (
          <div key={department.department} className={`rounded-lg border p-4 ${toneSurfaceClasses[department.tone]}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-white">{department.department}</p>
                <p className="mt-1 text-xs text-slate-400">{department.transactions} transactions</p>
              </div>
              <SignalBadge tone={department.tone}>{department.share}%</SignalBadge>
            </div>
            <p className="mt-4 text-2xl font-bold text-white">{department.revenue}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CashierCollectionsPanel() {
  return (
    <div className="rounded-lg border border-emerald-300/14 bg-emerald-400/[0.04] p-5 shadow-xl shadow-emerald-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Cashier Collections Register</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Cashier-by-cashier collections across general cashier points and the dedicated pharmacy cashier.
          </p>
        </div>
        <SignalBadge tone="emerald">5 cashier points</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {cashierCollections.map((cashier) => (
          <article key={cashier.cashier} className={`rounded-lg border p-4 ${toneSurfaceClasses[cashier.tone]}`}>
            <div className="grid gap-4 xl:grid-cols-[1.05fr_1fr_1.15fr_auto] xl:items-center">
              <div className="min-w-0">
                <p className="whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {cashier.cashier}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-400">{cashier.location}</p>
                <p className="mt-1 text-xs text-slate-500">{cashier.desk}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-current/65">Total collected</p>
                <p className="mt-2 text-2xl font-bold text-white">{cashier.total}</p>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-2">
                  <p className="text-slate-500">POS</p>
                  <p className="mt-1 font-semibold text-white">{cashier.pos}</p>
                </div>
                <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-2">
                  <p className="text-slate-500">Transfer</p>
                  <p className="mt-1 font-semibold text-white">{cashier.bankTransfer}</p>
                </div>
                <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-2">
                  <p className="text-slate-500">Cash</p>
                  <p className="mt-1 font-semibold text-white">{cashier.cash}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 xl:justify-end">
                <SignalBadge tone={cashier.tone}>{cashier.variance}</SignalBadge>
                <SignalBadge tone="steel">{cashier.shiftStatus}</SignalBadge>
                <SignalBadge tone="cyan">{cashier.receipts} receipts</SignalBadge>
                <SignalBadge tone="gold">{cashier.lastReceipt}</SignalBadge>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function PaymentTraceabilityPanel() {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.035] p-5 shadow-xl shadow-cyan-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Transaction Traceability Trail</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Receipt-level visibility from patient and service request to cashier, payment method, reference, and trace state.
          </p>
        </div>
        <SignalBadge tone="cyan">Audit trail preview</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {paymentTransactions.map((transaction) => (
          <article key={transaction.receipt} className={`rounded-lg border p-4 ${toneSurfaceClasses[transaction.tone]}`}>
            <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr_1fr_auto]">
              <div className="min-w-0">
                <p className="font-semibold text-white">{transaction.receipt}</p>
                <p className="mt-1 whitespace-normal text-sm leading-6 text-slate-300 [overflow-wrap:anywhere]">
                  {transaction.patient} · {transaction.mrn}
                </p>
                <p className="mt-1 text-xs text-slate-500">{transaction.receiptTime}</p>
              </div>
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-[0.14em] text-current/65">Service</p>
                <p className="mt-2 whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {transaction.department} · {transaction.serviceLine}
                </p>
                <p className="mt-1 text-sm leading-6 text-slate-400">{transaction.purpose}</p>
                <p className="mt-1 text-xs text-slate-500">Requested by {transaction.requestedBy}</p>
              </div>
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-[0.14em] text-current/65">Payment</p>
                <p className="mt-2 text-xl font-bold text-white">{transaction.amount}</p>
                <p className="mt-1 text-sm leading-6 text-slate-400">
                  {transaction.method} · {transaction.reference}
                </p>
                <p className="mt-1 text-xs text-slate-500">Cashier: {transaction.cashier}</p>
              </div>
              <div className="flex flex-wrap gap-2 xl:justify-end">
                <SignalBadge tone={transaction.tone}>{transaction.status}</SignalBadge>
                <SignalBadge tone="steel">{transaction.traceability}</SignalBadge>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function DepartmentRevenueLeaderboardPanel() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Department Revenue Leaderboard</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Ranked department/service-line revenue with share percentage and transaction count.
          </p>
        </div>
        <SignalBadge tone="cyan">Revenue ranking</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {departmentRevenueRows.map((department, index) => (
          <div key={department.department} className={`rounded-lg border p-4 ${toneSurfaceClasses[department.tone]}`}>
            <div className="grid gap-4 md:grid-cols-[auto_1fr_auto] md:items-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 bg-slate-950/35 text-sm font-bold text-white">
                {index + 1}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="font-semibold text-white">{department.department}</p>
                  <SignalBadge tone={department.tone}>{department.state}</SignalBadge>
                </div>
                <p className="mt-1 text-sm text-slate-400">
                  {department.transactions} transactions · {department.share}% share
                </p>
                <div className="mt-3">
                  <ProgressMeter value={department.share} tone={department.tone} />
                </div>
              </div>
              <p className="text-2xl font-bold text-white">{department.revenue}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CashierReconciliationMatrix() {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.035] p-5 shadow-xl shadow-cyan-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Cashier Reconciliation Matrix</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Declared collections compared with matched receipt and settlement records for each cashier point.
          </p>
        </div>
        <SignalBadge tone="amber">Variance detection</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {cashierReconciliationRows.map((cashier) => (
          <article key={cashier.cashier} className={`rounded-lg border p-4 ${toneSurfaceClasses[cashier.tone]}`}>
            <div className="grid gap-4 2xl:grid-cols-[1.1fr_1.2fr_0.9fr_auto] 2xl:items-center">
              <div className="min-w-0">
                <p className="whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {cashier.cashier}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-400">{cashier.location}</p>
                <p className="mt-1 text-xs text-slate-500">{cashier.visibility}</p>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-2">
                  <p className="text-slate-500">Declared</p>
                  <p className="mt-1 font-semibold text-white">{cashier.declared}</p>
                </div>
                <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-2">
                  <p className="text-slate-500">Matched</p>
                  <p className="mt-1 font-semibold text-white">{cashier.matched}</p>
                </div>
                <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-2">
                  <p className="text-slate-500">Variance</p>
                  <p className="mt-1 font-semibold text-white">{cashier.variance}</p>
                </div>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-current/65">Receipts</p>
                <p className="mt-2 text-2xl font-bold text-white">{cashier.receipts}</p>
              </div>
              <div className="flex flex-wrap gap-2 2xl:justify-end">
                <SignalBadge tone={cashier.tone}>{cashier.status}</SignalBadge>
                <SignalBadge tone="steel">Receipt traceability</SignalBadge>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function PaymentMethodReconciliationPanel() {
  return (
    <div className="rounded-lg border border-emerald-300/14 bg-emerald-400/[0.04] p-5 shadow-xl shadow-emerald-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Payment Method Reconciliation</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Settlement matching for POS, Bank Transfer, and Cash collections.
          </p>
        </div>
        <SignalBadge tone="cyan">Settlement matching</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 xl:grid-cols-3">
        {paymentMethodReconciliation.map((method) => (
          <div key={method.method} className={`rounded-lg border p-4 ${toneSurfaceClasses[method.tone]}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-white">{method.method}</p>
                <p className="mt-1 text-xs text-slate-400">Expected versus matched settlement</p>
              </div>
              <SignalBadge tone={method.tone}>{method.status}</SignalBadge>
            </div>
            <div className="mt-5 grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-2">
                <p className="text-slate-500">Expected</p>
                <p className="mt-1 font-semibold text-white">{method.expected}</p>
              </div>
              <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-2">
                <p className="text-slate-500">Matched</p>
                <p className="mt-1 font-semibold text-white">{method.matched}</p>
              </div>
              <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-2">
                <p className="text-slate-500">Variance</p>
                <p className="mt-1 font-semibold text-white">{method.variance}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DepartmentReconciliationStatusPanel() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Department Reconciliation Status</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Department revenue alignment against collection and receipt traceability records.
          </p>
        </div>
        <SignalBadge tone="amber">Department matching</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {departmentReconciliationRows.map((department) => (
          <div key={department.department} className={`rounded-lg border p-4 ${toneSurfaceClasses[department.tone]}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {department.department}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{department.detail}</p>
              </div>
              <SignalBadge tone={department.tone}>{department.status}</SignalBadge>
            </div>
            <p className="mt-4 text-2xl font-bold text-white">{department.amount}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReconciliationRiskSignalsPanel() {
  return (
    <div className="rounded-lg border border-rose-300/16 bg-rose-400/[0.04] p-5 shadow-xl shadow-rose-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Reconciliation Risk Signals</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Revenue governance signals that require controlled review before financial close.
          </p>
        </div>
        <SignalBadge tone="rose">Risk queue</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {reconciliationRiskSignals.map((risk) => (
          <div key={risk.title} className={`rounded-lg border p-4 ${toneSurfaceClasses[risk.tone]}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {risk.title}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{risk.detail}</p>
              </div>
              <div className="text-right">
                <p className="text-xl font-bold text-white">{risk.amount}</p>
                <SignalBadge tone={risk.tone}>{risk.state}</SignalBadge>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReconciliationTimelinePanel() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Reconciliation Timeline</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Time-based reconciliation events for settlement matching, variance detection, and CMD review routing.
          </p>
        </div>
        <SignalBadge tone="cyan">Governance timeline</SignalBadge>
      </div>

      <div className="relative mt-5">
        <div className="absolute bottom-4 left-[18px] top-4 w-px bg-gradient-to-b from-cyan-200/55 via-white/14 to-rose-200/45" />
        <div className="space-y-4">
          {reconciliationTimeline.map((event) => (
            <div key={`${event.time}-${event.title}`} className="relative pl-11">
              <div className="absolute left-0 top-5 flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-slate-950 shadow-lg shadow-cyan-950/20">
                <LiveDot tone={event.tone} pulse={event.tone === 'rose' || event.tone === 'amber'} />
              </div>
              <div className={`rounded-lg border p-4 ${toneSurfaceClasses[event.tone]}`}>
                <span className="text-xs font-semibold text-cyan-100/60">{event.time}</span>
                <p className="mt-2 font-semibold text-white">{event.title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{event.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function GuidedReconciliationPanel() {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.045] p-5 shadow-xl shadow-cyan-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Guided Reconciliation Review</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Executive workflow guidance for resolving unmatched receipts, cashier variances, and settlement mismatches.
          </p>
        </div>
        <SignalBadge tone="amber">Review required</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-5">
        {guidedReconciliationSteps.map((step, index) => (
          <div key={step} className="rounded-lg border border-white/[0.08] bg-slate-950/28 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-100/60">
              Step {index + 1}
            </p>
            <p className="mt-3 text-sm font-semibold leading-6 text-white">{step}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {guidedReconciliationActions.map((action) => (
          <button
            key={action.label}
            type="button"
            className={`rounded-lg border p-4 text-left text-sm font-semibold text-white transition duration-300 hover:-translate-y-0.5 hover:border-white/25 ${toneSurfaceClasses[action.tone]}`}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function OutstandingBillsPanel() {
  const agingSummary = [
    { label: '0-6h', value: '₦310K', tone: 'emerald' as SignalTone },
    { label: '6-24h', value: '₦650K', tone: 'amber' as SignalTone },
    { label: '24h+', value: '₦220K', tone: 'rose' as SignalTone },
  ];

  return (
    <div className="grid gap-5 2xl:grid-cols-[0.78fr_1.22fr]">
      <div className="rounded-lg border border-amber-300/16 bg-amber-400/[0.04] p-5 shadow-xl shadow-amber-950/16">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">Aging Summary</p>
            <p className="mt-1 text-xs leading-5 text-slate-400">
              Unpaid balances grouped by collection aging window.
            </p>
          </div>
          <SignalBadge tone="amber">₦1.18M total</SignalBadge>
        </div>
        <div className="mt-5 space-y-3">
          {agingSummary.map((item) => (
            <div key={item.label} className={`rounded-lg border p-4 ${toneSurfaceClasses[item.tone]}`}>
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-white">{item.label}</p>
                <p className="text-xl font-bold text-white">{item.value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">Patient Outstanding Preview</p>
            <p className="mt-1 text-xs leading-5 text-slate-400">
              CMD visibility of unpaid patient balances without operational billing edits.
            </p>
          </div>
          <SignalBadge tone="rose">4 priority cases</SignalBadge>
        </div>
        <div className="mt-5 space-y-3">
          {outstandingBills.map((bill) => (
            <div key={`${bill.mrn}-${bill.department}`} className={`rounded-lg border p-4 ${toneSurfaceClasses[bill.tone]}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-white">{bill.patient}</p>
                  <p className="mt-1 text-sm text-slate-400">
                    {bill.mrn} · {bill.department} · {bill.age}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold text-white">{bill.amount}</p>
                  <SignalBadge tone={bill.tone}>{bill.state}</SignalBadge>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RefundWaiverAuditPanel() {
  return (
    <div className="rounded-lg border border-rose-300/16 bg-rose-400/[0.04] p-5 shadow-xl shadow-rose-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Refund & Waiver Exception Audit</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Sensitive financial exception queue for refunds, waivers, discounts, adjustments, and suspicious activity.
          </p>
        </div>
        <SignalBadge tone="rose">Controlled exceptions</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {refundWaiverExceptions.map((item) => (
          <div key={item.title} className={`rounded-lg border p-4 ${toneSurfaceClasses[item.tone]}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-semibold text-white">{item.title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{item.detail}</p>
              </div>
              <div className="text-right">
                <p className="text-xl font-bold text-white">{item.amount}</p>
                <SignalBadge tone={item.tone}>{item.state}</SignalBadge>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PharmacyRevenueTracePanel() {
  return (
    <div className="grid gap-5 2xl:grid-cols-[0.82fr_1.18fr]">
      <div className="rounded-lg border border-emerald-300/14 bg-emerald-400/[0.04] p-5 shadow-xl shadow-emerald-950/16">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">Dedicated Pharmacy Cashier</p>
            <p className="mt-1 text-xs leading-5 text-slate-400">
              Pharmacy-specific cashier visibility for a high-value hospital revenue hub.
            </p>
          </div>
          <SignalBadge tone="emerald">Maryam Ali</SignalBadge>
        </div>
        <div className="mt-5 space-y-3">
          {[
            ['Pharmacy revenue today', '₦2.14M'],
            ['Pharmacy receipts', '48'],
            ['Voided pharmacy receipts', '1'],
            ['High-value medicine transactions', '7'],
            ['Payment reconciliation posture', 'Stable'],
          ].map(([label, value]) => (
            <div key={label} className="flex items-center justify-between gap-4 rounded-lg border border-white/[0.08] bg-slate-950/28 p-4">
              <span className="text-sm text-slate-400">{label}</span>
              <span className="text-sm font-semibold text-white">{value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">Pharmacy Transaction Trace Preview</p>
            <p className="mt-1 text-xs leading-5 text-slate-400">
              Pharmacy receipt and high-value medicine transaction visibility.
            </p>
          </div>
          <SignalBadge tone="gold">Traceable</SignalBadge>
        </div>
        <div className="mt-5 space-y-3">
          {paymentTransactions
            .filter((transaction) => transaction.department === 'Pharmacy')
            .map((transaction) => (
              <div key={transaction.receipt} className={`rounded-lg border p-4 ${toneSurfaceClasses[transaction.tone]}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-white">{transaction.receipt}</p>
                    <p className="mt-1 text-sm leading-6 text-slate-400">
                      {transaction.patient} · {transaction.purpose}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {transaction.method} · {transaction.reference} · Cashier {transaction.cashier}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-bold text-white">{transaction.amount}</p>
                    <SignalBadge tone={transaction.tone}>{transaction.status}</SignalBadge>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

function FinancialDemoNotice({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.045] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm leading-6 text-slate-300">
          No backend connected. This is frontend demo data prepared for future finance, cashier, receipt, and audit APIs.
        </p>
        <SignalBadge tone="cyan">{label}</SignalBadge>
      </div>
    </div>
  );
}

function BiometricWorkflowStrip() {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-slate-950/24 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Biometric Workflow Demonstration</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Device-to-CMD event flow prepared for backend biometric device API integration.
          </p>
        </div>
        <SignalBadge tone="cyan">Monitoring workflow</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {biometricWorkflowSignals.map((signal, index) => (
          <div
            key={signal.label}
            className="relative rounded-lg border border-white/[0.08] bg-slate-950/28 p-4"
          >
            {index < biometricWorkflowSignals.length - 1 ? (
              <div className="pointer-events-none absolute -right-3 top-1/2 hidden h-px w-3 bg-gradient-to-r from-cyan-200/35 to-transparent 2xl:block" />
            ) : null}
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                {signal.context}
              </p>
              <LiveDot tone={signal.tone} pulse={signal.tone === 'amber'} />
            </div>
            <p className="mt-3 text-sm font-semibold text-white">{signal.label}</p>
            <p className="mt-2 text-xs leading-5 text-slate-400">{signal.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function BiometricDeviceStatusPanel() {
  return (
    <div className="rounded-lg border border-emerald-300/16 bg-emerald-400/[0.045] p-5 shadow-xl shadow-emerald-950/18">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Device Health Grid</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            CMD-level monitoring of device availability, sync posture, capture volume, and latency.
          </p>
        </div>
        <SignalBadge tone="emerald" pulse>
          8 devices monitored
        </SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {biometricDeviceHealth.map((device) => (
          <div
            key={device.name}
            className={`rounded-lg border p-4 transition duration-300 hover:-translate-y-0.5 hover:border-white/20 ${toneSurfaceClasses[device.tone]}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="whitespace-normal text-sm font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {device.name}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-400">{device.location}</p>
              </div>
              <SignalBadge tone={device.tone} pulse={device.status === 'Warning'}>
                {device.status}
              </SignalBadge>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
              <div>
                <p className="text-slate-500">Events</p>
                <p className="mt-1 text-base font-bold text-white">{device.events}</p>
              </div>
              <div>
                <p className="text-slate-500">Last sync</p>
                <p className="mt-1 text-base font-bold text-white">{device.lastSync}</p>
              </div>
              <div>
                <p className="text-slate-500">Latency</p>
                <p className="mt-1 font-semibold text-slate-200">{device.latency}</p>
              </div>
              <div>
                <p className="text-slate-500">Integrity</p>
                <p className="mt-1 font-semibold text-slate-200">{device.integrity}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BiometricDeviceRiskPanel() {
  const riskItems = [
    { label: 'Theatre Device sync delay', value: 'Warning', tone: 'amber' as SignalTone },
    { label: 'Unmatched identity attempts', value: '2', tone: 'rose' as SignalTone },
    { label: 'Failed scans', value: '4', tone: 'rose' as SignalTone },
    { label: 'Offline devices', value: '0', tone: 'emerald' as SignalTone },
    { label: 'CMD visibility', value: 'Monitoring only', tone: 'steel' as SignalTone },
  ];

  return (
    <div className="rounded-lg border border-amber-300/16 bg-amber-400/[0.045] p-5 shadow-xl shadow-amber-950/18">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Device Risk Panel</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Device-focused risk signals only: sync delay, failed scan, unmatched identity, and offline posture.
          </p>
        </div>
        <SignalBadge tone="amber">Monitoring only</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {riskItems.map((item) => (
          <div
            key={item.label}
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/[0.08] bg-slate-950/28 p-4"
          >
            <span className="text-sm leading-6 text-slate-300">{item.label}</span>
            <SignalBadge tone={item.tone}>{item.value}</SignalBadge>
          </div>
        ))}
      </div>
    </div>
  );
}

function DepartmentStaffingMatrix() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Department Staffing Matrix</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Department-by-department required staff, on-duty staff, coverage percentage, risk, and CMD visibility.
          </p>
        </div>
        <SignalBadge tone="amber">12 departments</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {departmentStaffingStatus.map((department) => {
          const coverage = Math.round((department.onDuty / department.required) * 100);
          const gap = Math.max(department.required - department.onDuty, 0);

          return (
            <div
              key={department.department}
              className={`rounded-lg border p-4 transition duration-300 hover:-translate-y-0.5 hover:border-white/20 ${toneSurfaceClasses[department.tone]}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="whitespace-normal text-sm font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                    {department.department}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-400">{department.visibility}</p>
                </div>
                <SignalBadge tone={department.tone}>{department.status}</SignalBadge>
              </div>

              <div className="mt-5 grid grid-cols-3 gap-3 text-xs">
                <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-3">
                  <p className="text-slate-500">Required</p>
                  <p className="mt-1 text-lg font-bold text-white">{department.required}</p>
                </div>
                <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-3">
                  <p className="text-slate-500">On duty</p>
                  <p className="mt-1 text-lg font-bold text-white">{department.onDuty}</p>
                </div>
                <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-3">
                  <p className="text-slate-500">Gap</p>
                  <p className="mt-1 text-lg font-bold text-white">{gap}</p>
                </div>
              </div>

              <div className="mt-5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Coverage</p>
                  <p className="text-xl font-bold text-white">{coverage}%</p>
                </div>
                <div className="mt-3">
                  <ProgressMeter value={coverage} tone={department.tone} />
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs text-slate-500">Risk level</p>
                <SignalBadge tone={department.tone}>{department.risk}</SignalBadge>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PriorityStaffingRisksPanel() {
  return (
    <div className="rounded-lg border border-rose-300/16 bg-rose-400/[0.04] p-5 shadow-xl shadow-rose-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Priority Staffing Risks</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Highest-priority department staffing gaps for CMD visibility.
          </p>
        </div>
        <SignalBadge tone="rose">5 priority gaps</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {priorityStaffingRisks.map((risk) => (
          <div
            key={risk.department}
            className={`rounded-lg border p-4 ${toneSurfaceClasses[risk.tone]}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-white">{risk.department}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{risk.gap}</p>
              </div>
              <SignalBadge tone={risk.tone}>{risk.risk}</SignalBadge>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DepartmentCoverageDistributionPanel() {
  return (
    <div className="rounded-lg border border-amber-300/14 bg-amber-400/[0.04] p-5 shadow-xl shadow-amber-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Department Coverage Distribution</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Compact executive grouping of department coverage posture.
          </p>
        </div>
        <SignalBadge tone="amber">Coverage mix</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3">
        {departmentCoverageDistribution.map((item) => (
          <div key={item.label} className={`rounded-lg border p-4 ${toneSurfaceClasses[item.tone]}`}>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-white">{item.label}</p>
              <SignalBadge tone={item.tone}>{item.value}</SignalBadge>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CmdActionReadinessPanel() {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.04] p-5 shadow-xl shadow-cyan-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">CMD Action Readiness</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Frontend-only action previews for future staffing governance workflow integration.
          </p>
        </div>
        <SignalBadge tone="cyan">Demo actions</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {cmdStaffingActions.map((action) => (
          <button
            key={action.label}
            type="button"
            className={`rounded-lg border p-4 text-left text-sm font-semibold text-white transition duration-300 hover:-translate-y-0.5 hover:border-white/25 ${toneSurfaceClasses[action.tone]}`}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function DepartmentStaffingDemoNotice() {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.045] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm leading-6 text-slate-300">
          Frontend demo data only. Staffing API, supervisor notification, escalation, and report export actions are pending.
        </p>
        <SignalBadge tone="cyan">Staffing API pending</SignalBadge>
      </div>
    </div>
  );
}

function BiometricActivityTimeline() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Biometric Event Stream</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Recent device capture, identity matching, sync warning, and unmatched fingerprint events.
          </p>
        </div>
        <SignalBadge tone="cyan">Live event preview</SignalBadge>
      </div>

      <div className="relative mt-5">
        <div className="absolute bottom-4 left-[18px] top-4 w-px bg-gradient-to-b from-emerald-200/55 via-white/14 to-sky-200/45" />
        <div className="space-y-4">
          {recentBiometricEvents.map((event) => (
            <div key={`${event.time}-${event.device}-${event.event}`} className="relative pl-11">
              <div className="absolute left-0 top-5 flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-slate-950 shadow-lg shadow-emerald-950/20">
                <LiveDot tone={event.tone} pulse={event.tone === 'rose' || event.tone === 'amber'} />
              </div>
              <div className={`rounded-lg border p-4 ${toneSurfaceClasses[event.tone]}`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="text-xs font-semibold text-emerald-100/60">{event.time}</span>
                  <SignalBadge tone={event.tone}>{event.state}</SignalBadge>
                </div>
                <p className="mt-2 font-semibold text-white">{event.device}</p>
                <p className="mt-1 text-sm leading-6 text-slate-300">
                  {event.subject} — {event.event}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{event.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function BiometricDemoNotice() {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.055] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm leading-6 text-slate-300">
          Frontend demo data only. Backend biometric device API, event ingestion, and identity reconciliation are pending.
        </p>
        <SignalBadge tone="cyan">Backend device API pending</SignalBadge>
      </div>
    </div>
  );
}

function ShiftWindowCompliancePanel() {
  return (
    <div className="rounded-lg border border-emerald-300/14 bg-emerald-400/[0.04] p-5 shadow-xl shadow-emerald-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Shift Window Compliance</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            CMD view of roster coverage across morning, afternoon, and night shift windows.
          </p>
        </div>
        <SignalBadge tone="amber">Morning watch</SignalBadge>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-3">
        {shiftWindowCompliance.map((shift) => (
          <div
            key={shift.name}
            className={`rounded-lg border p-4 transition duration-300 hover:-translate-y-0.5 hover:border-white/20 ${toneSurfaceClasses[shift.tone]}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-base font-semibold text-white">{shift.name}</p>
                <p className="mt-1 text-xs leading-5 text-slate-400">{shift.window}</p>
              </div>
              <SignalBadge tone={shift.tone}>{shift.state}</SignalBadge>
            </div>

            <div className="mt-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Compliance</p>
                <p className="text-2xl font-bold text-white">{shift.compliance}%</p>
              </div>
              <div className="mt-3">
                <ProgressMeter value={shift.compliance} tone={shift.tone} />
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-3">
                <p className="text-slate-500">Expected</p>
                <p className="mt-1 text-lg font-bold text-white">{shift.expected}</p>
              </div>
              <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-3">
                <p className="text-slate-500">Present</p>
                <p className="mt-1 text-lg font-bold text-white">{shift.present}</p>
              </div>
              <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-3">
                <p className="text-slate-500">Late flags</p>
                <p className="mt-1 text-lg font-bold text-white">{shift.late}</p>
              </div>
              <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-3">
                <p className="text-slate-500">Absent flags</p>
                <p className="mt-1 text-lg font-bold text-white">{shift.absent}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DepartmentShiftComplianceGrid() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Department Shift Compliance</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Department-level roster coverage, compliance percentage, and risk state for the active shift.
          </p>
        </div>
        <SignalBadge tone="steel">10 monitored units</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
        {departmentShiftCompliance.map((department) => (
          <div
            key={department.department}
            className={`rounded-lg border p-4 transition duration-300 hover:-translate-y-0.5 hover:border-white/20 ${toneSurfaceClasses[department.tone]}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="whitespace-normal text-sm font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {department.department}
                </p>
                <p className="mt-1 text-xs text-slate-500">{department.shift} shift</p>
              </div>
              <SignalBadge tone={department.tone}>{department.state}</SignalBadge>
            </div>

            <div className="mt-4 flex items-end justify-between gap-3">
              <div>
                <p className="text-xs text-slate-500">Coverage</p>
                <p className="mt-1 text-xl font-bold text-white">
                  {department.present}/{department.expected}
                </p>
              </div>
              <p className="text-2xl font-bold text-white">{department.compliance}%</p>
            </div>
            <div className="mt-4">
              <ProgressMeter value={department.compliance} tone={department.tone} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ShiftComplianceExceptionsPanel() {
  return (
    <div className="rounded-lg border border-rose-300/16 bg-rose-400/[0.04] p-5 shadow-xl shadow-rose-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Compliance Exceptions</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Roster coverage exceptions requiring supervisor review or CMD visibility.
          </p>
        </div>
        <SignalBadge tone="rose">5 risk signals</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {shiftComplianceExceptions.map((exception) => (
          <div
            key={exception.title}
            className={`rounded-lg border p-4 ${toneSurfaceClasses[exception.tone]}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {exception.title}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{exception.detail}</p>
              </div>
              <SignalBadge tone={exception.tone}>{exception.severity}</SignalBadge>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ShiftComplianceTimelinePanel() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Shift Compliance Timeline</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Time-based roster posture events for shift opening, coverage confirmation, exceptions, and handover.
          </p>
        </div>
        <SignalBadge tone="cyan">Roster timeline</SignalBadge>
      </div>

      <div className="relative mt-5">
        <div className="absolute bottom-4 left-[18px] top-4 w-px bg-gradient-to-b from-emerald-200/55 via-white/14 to-amber-200/45" />
        <div className="space-y-4">
          {shiftComplianceTimeline.map((event) => (
            <div key={`${event.time}-${event.title}`} className="relative pl-11">
              <div className="absolute left-0 top-5 flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-slate-950 shadow-lg shadow-emerald-950/20">
                <LiveDot tone={event.tone} pulse={event.tone === 'rose' || event.tone === 'amber'} />
              </div>
              <div className={`rounded-lg border p-4 ${toneSurfaceClasses[event.tone]}`}>
                <span className="text-xs font-semibold text-cyan-100/60">{event.time}</span>
                <p className="mt-2 font-semibold text-white">{event.title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{event.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ShiftComplianceDemoNotice() {
  return (
    <div className="rounded-lg border border-emerald-200/12 bg-emerald-300/[0.045] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm leading-6 text-slate-300">
          Frontend demo data only. Roster API, supervisor review workflow, and live shift coverage integration are pending.
        </p>
        <SignalBadge tone="emerald">Roster API pending</SignalBadge>
      </div>
    </div>
  );
}

function WorkforceTrendPanel() {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.04] p-5 shadow-xl shadow-cyan-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Workforce Trend Panel</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Executive telemetry for workforce stability, department pressure movement, and exception patterns.
          </p>
        </div>
        <SignalBadge tone="cyan">Analytics preview</SignalBadge>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-3">
        <TelemetryChart
          values={workforceArrivalConsistencyTrend}
          tone="emerald"
          label="Arrival consistency trend"
          meta="Attendance pattern analytics"
        />
        <TelemetryChart
          values={workforcePressureTrend}
          tone="amber"
          label="Department pressure movement"
          meta="Workload versus staff availability"
        />
        <TelemetryChart
          values={workforceExceptionPatternTrend}
          tone="rose"
          label="Weekly exception pattern"
          meta="Late, absence, and early-departure signal trend"
        />
      </div>
    </div>
  );
}

function DepartmentWorkforceComparisonPanel() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Department Workforce Comparison</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            CMD comparison of department staffing posture, coverage trend, and pressure level.
          </p>
        </div>
        <SignalBadge tone="steel">10 departments</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
        {workforceComparison.map((department) => (
          <div
            key={department.department}
            className={`rounded-lg border p-4 transition duration-300 hover:-translate-y-0.5 hover:border-white/20 ${toneSurfaceClasses[department.tone]}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="whitespace-normal text-sm font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {department.department}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-400">{department.pressure}</p>
              </div>
              <SignalBadge tone={department.tone}>{department.state}</SignalBadge>
            </div>
            <div className="mt-5 flex items-end justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Coverage</p>
                <p className="mt-1 text-2xl font-bold text-white">{department.coverage}</p>
              </div>
              <LiveDot tone={department.tone} pulse={department.tone === 'rose' || department.tone === 'amber'} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ExceptionPatternAnalyticsPanel() {
  return (
    <div className="rounded-lg border border-amber-300/16 bg-amber-400/[0.04] p-5 shadow-xl shadow-amber-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Exception Pattern Analytics</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Pattern-level view of recurring workforce signals without exposing individual attendance logs.
          </p>
        </div>
        <SignalBadge tone="amber">Pattern signals</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {workforceExceptionPatterns.map((pattern) => (
          <div key={pattern.label} className={`rounded-lg border p-4 ${toneSurfaceClasses[pattern.tone]}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-current/65">
                  {pattern.label}
                </p>
                <p className="mt-2 whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {pattern.value}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{pattern.detail}</p>
              </div>
              <LiveDot tone={pattern.tone} pulse={pattern.tone === 'rose'} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function WorkforceRiskForecastPanel() {
  return (
    <div className="rounded-lg border border-rose-300/16 bg-rose-400/[0.04] p-5 shadow-xl shadow-rose-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Workforce Risk Forecast</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Executive forecast of likely workforce risk over the next operational window.
          </p>
        </div>
        <SignalBadge tone="rose">Forecast</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3">
        {workforceRiskForecast.map((risk) => (
          <div
            key={risk.label}
            className="flex flex-wrap items-start justify-between gap-4 rounded-lg border border-white/[0.08] bg-slate-950/28 p-4"
          >
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white">{risk.label}</p>
              <p className="mt-2 text-xs leading-5 text-slate-400">{risk.detail}</p>
            </div>
            <SignalBadge tone={risk.tone}>{risk.value}</SignalBadge>
          </div>
        ))}
      </div>
    </div>
  );
}

function CmdWorkforceInsightPanel() {
  return (
    <div className="rounded-lg border border-emerald-300/14 bg-emerald-400/[0.04] p-5 shadow-xl shadow-emerald-950/16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">CMD Insight Panel</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Concise executive interpretation of workforce pressure, stability, and follow-up needs.
          </p>
        </div>
        <SignalBadge tone="emerald">Executive insights</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        {workforceInsights.map((insight) => (
          <div key={insight.title} className={`rounded-lg border p-4 ${toneSurfaceClasses[insight.tone]}`}>
            <div className="flex items-start gap-3">
              <LiveDot tone={insight.tone} pulse={insight.tone === 'rose' || insight.tone === 'amber'} />
              <div className="min-w-0">
                <p className="whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                  {insight.title}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{insight.detail}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function WorkforceAnalyticsDemoNotice() {
  return (
    <div className="rounded-lg border border-cyan-200/12 bg-cyan-300/[0.045] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm leading-6 text-slate-300">
          Frontend demo data only. Workforce analytics API, forecasting model, and historical trend backend are pending.
        </p>
        <SignalBadge tone="cyan">Workforce analytics API pending</SignalBadge>
      </div>
    </div>
  );
}

function FocusMetricGrid({ metrics }: { metrics: ExecutiveSignal[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <div key={metric.label} className={`rounded-lg border p-4 ${toneSurfaceClasses[metric.tone]}`}>
          <div className="flex items-start justify-between gap-3">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-current/78">
              {metric.label}
            </p>
            <LiveDot tone={metric.tone} pulse={metric.tone === 'rose' || metric.tone === 'emerald'} />
          </div>
          <p className="mt-4 text-2xl font-bold leading-none text-white">{metric.value}</p>
          <p className="mt-3 text-xs leading-5 text-slate-300">{metric.context}</p>
        </div>
      ))}
    </div>
  );
}

function FocusedWorkspace({
  section,
  subsection,
  summary,
  metrics,
  children,
  variant = 'standard',
}: {
  section: string;
  subsection: string;
  summary: string;
  metrics: ExecutiveSignal[];
  children: ReactNode;
  variant?: PanelVariant;
}) {
  return (
    <Panel
      eyebrow={section}
      title={subsection}
      action={<SignalBadge tone="amber">Frontend demo data</SignalBadge>}
      variant={variant}
    >
      <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-4 text-sm leading-6 text-slate-300">
        {summary}
      </div>
      <div className="mt-5 space-y-5">
        <FocusMetricGrid metrics={metrics} />
        {children}
      </div>
    </Panel>
  );
}

function getWorkspaceTone(section: string): SignalTone {
  if (section === 'Hospital Operations') return 'emerald';
  if (section === 'Financial Intelligence') return 'cyan';
  if (section === 'Pharmacy & Supply Governance') return 'gold';
  if (section === 'Staff Governance') return 'emerald';
  if (section === 'Audit & Compliance') return 'steel';
  if (section === 'Executive Reports') return 'cyan';
  if (section === 'Executive Settings') return 'slate';
  return 'cyan';
}

function getWorkspaceVariant(section: string, subsection: string): PanelVariant {
  if (subsection.includes('Critical') || subsection.includes('Suspicious')) return 'alert';
  if (section === 'Audit & Compliance') return 'steel';
  if (section === 'Pharmacy & Supply Governance') return 'governance';
  if (section === 'Executive Reports' || section === 'Financial Intelligence') return 'open';
  if (section === 'Executive Settings') return 'compact';
  return 'dominant';
}

function getWorkspaceMetrics(section: string, subsection: string): ExecutiveSignal[] {
  if (section === 'Financial Intelligence') {
    return financialTrustSignals;
  }

  if (section === 'Pharmacy & Supply Governance') {
    return [
      { label: 'Approval Queue', value: '14', context: 'Requests visible for governance', tone: 'gold' },
      { label: 'Critical Stock Alerts', value: '2', context: 'Stockout pressure signals', tone: 'rose' },
      { label: 'High-Risk Items', value: '6', context: 'Controlled commodity watch', tone: 'amber' },
      { label: 'Traceability', value: 'Active', context: 'Stock movement audit posture', tone: 'steel' },
    ];
  }

  if (section === 'Audit & Compliance') {
    return [
      { label: 'Audit Events', value: '248', context: 'User and record activity signals', tone: 'steel' },
      { label: 'Critical Flags', value: '3', context: 'Requires compliance review', tone: 'rose' },
      { label: 'Session Posture', value: 'Stable', context: 'Login/session monitoring', tone: 'cyan' },
      { label: 'Reports', value: 'Ready', context: 'Compliance export preview', tone: 'gold' },
    ];
  }

  if (section === 'Executive Reports') {
    return [
      { label: 'Operational Pack', value: 'Ready', context: 'Patient flow and ward view', tone: 'emerald' },
      { label: 'Financial Pack', value: 'Ready', context: 'Revenue and payment trace', tone: 'cyan' },
      { label: 'Audit Pack', value: 'Ready', context: 'Access and compliance view', tone: 'steel' },
      { label: 'Export Center', value: 'Preview', context: 'CMD briefing workspace', tone: 'gold' },
    ];
  }

  if (section === 'Executive Settings') {
    return [
      { label: 'Dashboard', value: 'Configured', context: 'Executive view preferences', tone: 'slate' },
      { label: 'Notifications', value: 'Governed', context: 'Critical signal routing', tone: 'amber' },
      { label: 'Reports', value: 'Preview', context: 'Export preference scope', tone: 'cyan' },
      { label: 'Profile', value: 'Restricted', context: 'CMD identity boundary', tone: 'steel' },
    ];
  }

  if (section === 'Hospital Operations') {
    return [
      { label: 'Patient Flow', value: '214', context: 'Active patient visibility', tone: 'cyan' },
      { label: 'Admissions', value: '37', context: 'Inpatient conversions visible', tone: 'emerald' },
      { label: 'Bed Occupancy', value: '78%', context: 'Ward utilization posture', tone: 'amber' },
      { label: 'Emergency Pressure', value: 'Moderate', context: 'A&E escalation watch', tone: 'amber' },
    ];
  }

  return [
    { label: 'Selected View', value: 'Active', context: subsection, tone: getWorkspaceTone(section) },
    { label: 'Critical Signals', value: '3', context: 'CMD attention queue', tone: 'rose' },
    { label: 'Operational Scope', value: '12', context: 'Departments represented', tone: 'steel' },
    { label: 'Demo Mode', value: 'On', context: 'Frontend-only content', tone: 'amber' },
  ];
}

function getWorkspaceSummary(section: string, subsection: string) {
  if (section === 'Staff Governance') {
    return 'CMD-level staff governance view using frontend-only biometric demo data. This remains an executive oversight surface, not an HR operations workstation.';
  }

  if (section === 'Hospital Operations') {
    return `Focused operational intelligence for ${subsection.toLowerCase()}, including patient movement, pressure signals, and department-level visibility.`;
  }

  if (section === 'Financial Intelligence') {
    return `Executive financial observability for ${subsection.toLowerCase()}, using demo revenue, payment traceability, and risk indicators.`;
  }

  if (section === 'Pharmacy & Supply Governance') {
    return `CMD governance preview for ${subsection.toLowerCase()}, covering supply risk, approval visibility, and stock traceability signals.`;
  }

  if (section === 'Audit & Compliance') {
    return `Institutional accountability preview for ${subsection.toLowerCase()}, with user, session, record, and compliance visibility.`;
  }

  if (section === 'Executive Reports') {
    return `CMD reporting workspace for ${subsection.toLowerCase()}, prepared as frontend-only executive briefing content.`;
  }

  if (section === 'Executive Settings') {
    return `Executive preference preview for ${subsection.toLowerCase()}, separated from operational workstation controls.`;
  }

  return `Focused executive overview for ${subsection.toLowerCase()}, using frontend-only hospital command-center signals.`;
}

function FocusedRows({
  section,
  subsection,
  rows,
}: {
  section: string;
  subsection: string;
  rows?: ExecutiveTableRow[];
}) {
  const tone = getWorkspaceTone(section);
  const exactRows = rows?.filter((row) => row.domain === subsection);
  const displayRows =
    exactRows && exactRows.length > 0
      ? exactRows
      : [
          {
            domain: subsection,
            signal: getWorkspaceSummary(section, subsection),
            owner: section,
            state: 'Demo',
            tone,
          },
          ...(rows ?? []).slice(0, 2),
        ];

  return <ExecutiveRows rows={displayRows} />;
}

function DemoSelect({
  label,
  options,
}: {
  label: string;
  options: string[];
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        {label}
      </span>
      <select
        defaultValue={options[0]}
        className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/45 px-3 py-3 text-sm font-medium text-slate-200 outline-none transition focus:border-cyan-200/40"
      >
        {options.map((option) => (
          <option key={option} className="bg-slate-950 text-slate-100">
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function AttendanceFiltersPanel() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Attendance Filters & Search</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Backend-ready filter surface for CMD attendance traceability demonstration.
          </p>
        </div>
        <SignalBadge tone="steel">Demo controls</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[1.4fr_repeat(5,minmax(0,1fr))]">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Search
          </span>
          <input
            type="search"
            placeholder="Search by staff name, phone number, staff ID, or clock-in time"
            className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/45 px-3 py-3 text-sm font-medium text-slate-200 outline-none transition placeholder:text-slate-400 focus:border-cyan-200/45"
          />
        </label>
        <DemoSelect
          label="Department"
          options={['All Departments', 'GOPD', 'A&E', 'Female Ward', 'Theatre', 'Pharmacy', 'Laboratory']}
        />
        <DemoSelect
          label="Status"
          options={[
            'All Status',
            'On Time',
            'Late Arrival',
            'Absent',
            'Early Departure',
            'No Clock-Out',
            'Manual Review',
          ]}
        />
        <DemoSelect label="Shift" options={['All Shifts', 'Morning', 'Afternoon', 'Night']} />
        <DemoSelect label="Time Window" options={['Today', '07:00 - 09:00', '09:00 - 12:00', 'Custom Time']} />
        <DemoSelect
          label="Device Location"
          options={['All Devices', 'Main Entrance', 'A&E Gate', 'Ward Device 02', 'Pharmacy Device', 'Lab Device']}
        />
      </div>
    </div>
  );
}

function StaffAttendanceTraceTable() {
  return (
    <div className="overflow-hidden rounded-lg border border-white/[0.08] bg-slate-950/24">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/[0.08] p-5">
        <div>
          <p className="text-sm font-semibold text-white">Staff Attendance Trace</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Executive-readable attendance rows showing identity, department, time, device source,
            and exception risk without horizontal scrolling.
          </p>
        </div>
        <SignalBadge tone="cyan">10 demo records</SignalBadge>
      </div>

      <div className="divide-y divide-white/[0.055]">
        {staffAttendanceRecords.map((record) => (
          <article
            key={record.staffId}
            className={`group relative grid gap-5 px-5 py-5 transition hover:bg-white/[0.035] xl:grid-cols-2 2xl:grid-cols-[minmax(220px,1.2fr)_minmax(180px,0.9fr)_minmax(220px,1fr)_minmax(210px,0.9fr)] ${
              record.status === 'Late Arrival' || record.status === 'Absent'
                ? 'bg-white/[0.026]'
                : 'bg-transparent'
            }`}
          >
            <div className={`absolute inset-y-4 left-0 w-px rounded-full ${dotClasses[record.tone]}`} />

            <div className="min-w-0">
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Staff
              </p>
              <div className="flex items-start gap-3">
                <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full shadow-lg ${dotClasses[record.tone]}`} />
                <div className="min-w-0">
                  <p className="whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                    {record.name}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{record.staffId}</p>
                  <p className="mt-2 whitespace-normal text-xs leading-5 text-slate-400 [overflow-wrap:anywhere]">
                    {record.phone}
                  </p>
                </div>
              </div>
            </div>

            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Department / Role
              </p>
              <p className="mt-2 whitespace-normal text-sm font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                {record.department}
              </p>
              <p className="mt-1 whitespace-normal text-sm leading-6 text-slate-400 [overflow-wrap:anywhere]">
                {record.role}
              </p>
              <p className="mt-3 text-xs text-slate-500">Shift: {record.shift}</p>
            </div>

            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Time Details
              </p>
              <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
                <div className="min-w-0">
                  <p className="text-slate-500">Clock-in</p>
                  <p className="mt-1 whitespace-normal font-semibold leading-6 text-white [overflow-wrap:anywhere]">
                    {record.clockIn}
                  </p>
                </div>
                <div className="min-w-0">
                  <p className="text-slate-500">Clock-out</p>
                  <p className="mt-1 whitespace-normal font-semibold leading-6 text-slate-300 [overflow-wrap:anywhere]">
                    {record.clockOut}
                  </p>
                </div>
              </div>
              <p className="mt-3 text-xs text-slate-500">Late rule: after 09:30 AM</p>
            </div>

            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Status / Review
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <SignalBadge tone={record.tone} pulse={record.status === 'Absent'}>
                  {record.status}
                </SignalBadge>
                <SignalBadge tone={record.lateness === 'None' ? 'steel' : record.tone}>
                  {record.lateness}
                </SignalBadge>
                <SignalBadge
                  tone={
                    record.review === 'Escalate'
                      ? 'rose'
                      : record.review === 'Review'
                        ? 'gold'
                        : 'steel'
                  }
                >
                  {record.review}
                </SignalBadge>
              </div>
              <p className="mt-3 whitespace-normal text-xs leading-5 text-slate-500 [overflow-wrap:anywhere]">
                Source: {record.device}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function LateArrivalIntelligencePanel() {
  return (
    <div className="rounded-lg border border-amber-300/18 bg-amber-400/[0.055] p-5 shadow-xl shadow-amber-950/18">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Late Arrival Intelligence</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            CMD visibility into lateness cluster patterns and affected departments.
          </p>
        </div>
        <SignalBadge tone="amber">Review required</SignalBadge>
      </div>

      <div className="mt-5 space-y-3">
        {[
          ['Late arrival cluster', 'Female Ward / Pharmacy / Maternity'],
          ['Highest lateness', '42 mins'],
          ['Departments affected', 'Female Ward, Pharmacy, Maternity'],
          ['CMD visibility status', 'Review required'],
        ].map(([label, value]) => (
          <div
            key={label}
            className="flex items-center justify-between gap-4 rounded-lg border border-white/[0.08] bg-slate-950/28 p-4"
          >
            <span className="text-sm text-slate-400">{label}</span>
            <span className="text-sm font-semibold text-white">{value}</span>
          </div>
        ))}
      </div>
      <p className="mt-4 rounded-lg border border-amber-200/12 bg-slate-950/24 p-3 text-xs leading-5 text-amber-100/80">
        Demo lateness rule: Morning shift clock-in after 09:30 AM is flagged late.
      </p>
    </div>
  );
}

function AttendanceExceptionsPanel() {
  return (
    <div className="rounded-lg border border-rose-300/16 bg-rose-400/[0.045] p-5 shadow-xl shadow-rose-950/18">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Attendance Exceptions</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Exception categories prepared for backend-driven filtering and CMD review.
          </p>
        </div>
        <SignalBadge tone="rose">6 exception records</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {[
          { label: 'Late Arrivals', value: '3', tone: 'amber' as SignalTone },
          { label: 'Absent', value: '2', tone: 'rose' as SignalTone },
          { label: 'Early Departures', value: '1', tone: 'gold' as SignalTone },
          { label: 'No Clock-Out', value: '0', tone: 'steel' as SignalTone },
          { label: 'Manual Review', value: '4', tone: 'gold' as SignalTone },
        ].map((item) => (
          <div key={item.label} className={`rounded-lg border p-4 ${toneSurfaceClasses[item.tone]}`}>
            <p className="text-xs uppercase tracking-[0.14em] text-current/65">{item.label}</p>
            <p className="mt-2 text-2xl font-bold text-white">{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function DepartmentAttendanceSnapshotPanel() {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-950/22 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Department Attendance Snapshot</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Compact department coverage view for CMD attendance oversight.
          </p>
        </div>
        <SignalBadge tone="emerald">6 priority units</SignalBadge>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {attendanceDepartmentSnapshots.map((department) => {
          const coverage = Math.round((department.onDuty / department.expected) * 100);

          return (
            <div
              key={department.department}
              className="rounded-lg border border-white/[0.075] bg-white/[0.035] p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">{department.department}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {department.onDuty}/{department.expected} on duty
                  </p>
                </div>
                <SignalBadge tone={department.tone}>{department.status}</SignalBadge>
              </div>
              <div className="mt-4">
                <ProgressMeter value={coverage} tone={department.tone} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AttendanceIntelligenceWorkspace() {
  return (
    <FocusedWorkspace
      section="Staff Governance"
      subsection="Attendance Intelligence"
      summary="CMD-level attendance control room for tracing staff clock-in times, clock-out posture, department coverage, biometric source, and exception risk. This is frontend-only demo data prepared for backend integration."
      metrics={staffAttendanceMetrics}
      variant="dominant"
    >
      <AttendanceFiltersPanel />
      <StaffAttendanceTraceTable />
      <div className="grid gap-5 2xl:grid-cols-[0.92fr_1.08fr]">
        <LateArrivalIntelligencePanel />
        <AttendanceExceptionsPanel />
      </div>
      <DepartmentAttendanceSnapshotPanel />
    </FocusedWorkspace>
  );
}

function HospitalSnapshotWorkspace() {
  return (
    <div className="space-y-5">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
        {kpiMetrics.map((metric) => (
          <KpiCard key={metric.label} metric={metric} />
        ))}
      </section>

      <section className="grid gap-5 2xl:grid-cols-[1.38fr_0.62fr]">
        <Panel
          eyebrow="Executive Overview"
          title="Hospital Snapshot"
          action={<SignalBadge tone="amber">Frontend demo data</SignalBadge>}
          variant="dominant"
        >
          <div className="mb-4">
            <LiveSystemMarkers />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {departmentLoads.map((item) => (
              <DepartmentLoadCard key={item.department} item={item} />
            ))}
          </div>
        </Panel>

        <Panel
          eyebrow="Critical Alerts"
          title="Executive Attention Queue"
          action={<SignalBadge tone="rose" pulse>3 critical</SignalBadge>}
          variant="alert"
        >
          <div className="space-y-3">
            <AlertCard
              title="Patient record access spike"
              detail="Sensitive record access requires audit review before close of day."
              tone="rose"
              label="Critical"
            />
            <AlertCard
              title="Bed utilization threshold"
              detail="Male medical ward utilization is above CMD visibility threshold."
              tone="amber"
              label="Warning"
            />
            <AlertCard
              title="System operational status"
              detail="Application shell stable; live telemetry adapters remain frontend-only here."
              tone="cyan"
              label="Info"
            />
          </div>
        </Panel>
      </section>

      <section className="grid gap-5 2xl:grid-cols-[1.22fr_0.78fr]">
        <Panel
          eyebrow="Real-Time Operational Feed"
          title="Live Executive Intelligence Feed"
          action={<SignalBadge tone="emerald" pulse>Live operational feed</SignalBadge>}
          variant="dominant"
        >
          <ActivityFeed />
        </Panel>

        <Panel eyebrow="Financial Intelligence" title="Executive Financial Observability" variant="open">
          <div className="grid gap-4">
            <TelemetryChart
              values={revenueTrend}
              tone="cyan"
              label="Revenue movement"
              meta="Service-line collection trajectory"
            />
            <TrustSignalGrid />
          </div>
        </Panel>
      </section>
    </div>
  );
}

function ExecutiveOverviewWorkspace({ activeSubsection }: { activeSubsection: string }) {
  if (activeSubsection === 'Hospital Snapshot') return <HospitalSnapshotWorkspace />;

  if (activeSubsection === 'Critical Alerts') {
    return (
      <FocusedWorkspace
        section="Executive Overview"
        subsection={activeSubsection}
        summary="Executive alert queue for operational, audit, bed, and attendance pressure signals requiring CMD visibility."
        metrics={getWorkspaceMetrics('Executive Overview', activeSubsection)}
        variant="alert"
      >
        <div className="grid gap-4 lg:grid-cols-3">
          <AlertCard title="Patient record access spike" detail="Sensitive record access requires audit review before close of day." tone="rose" label="Critical" />
          <AlertCard title="Bed utilization threshold" detail="Male medical ward utilization is above CMD visibility threshold." tone="amber" label="Warning" />
          <AlertCard title="Biometric attendance signal" detail="Late-arrival cluster detected in one department shift window." tone="rose" label="Critical" />
        </div>
      </FocusedWorkspace>
    );
  }

  if (activeSubsection === 'Operational KPIs') {
    return (
      <FocusedWorkspace
        section="Executive Overview"
        subsection={activeSubsection}
        summary="CMD operational KPI view for census, admission, revenue, bed utilization, staffing, and critical signals."
        metrics={getWorkspaceMetrics('Executive Overview', activeSubsection)}
        variant="dominant"
      >
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
          {kpiMetrics.map((metric) => (
            <KpiCard key={metric.label} metric={metric} />
          ))}
        </section>
      </FocusedWorkspace>
    );
  }

  return (
    <FocusedWorkspace
      section="Executive Overview"
      subsection={activeSubsection}
      summary={getWorkspaceSummary('Executive Overview', activeSubsection)}
      metrics={getWorkspaceMetrics('Executive Overview', activeSubsection)}
      variant="dominant"
    >
      {activeSubsection === 'Daily Executive Summary' ? <ActivityFeed /> : <FocusedRows section="Executive Overview" subsection={activeSubsection} />}
    </FocusedWorkspace>
  );
}

function StaffGovernanceWorkspace({ activeSubsection }: { activeSubsection: string }) {
  if (activeSubsection === 'Attendance Intelligence') {
    return <AttendanceIntelligenceWorkspace />;
  }

  if (activeSubsection === 'Biometric Monitoring') {
    return (
      <FocusedWorkspace
        section="Staff Governance"
        subsection={activeSubsection}
        summary="CMD-level biometric infrastructure monitoring for device health, sync posture, fingerprint capture, identity matching, failed attempts, unmatched events, and event integrity. This view intentionally excludes the full attendance trace table."
        metrics={[
          { label: 'Active Devices', value: '8 / 8', context: 'Biometric terminals reporting', tone: 'emerald' },
          { label: 'Last Sync', value: '11:42 AM', context: 'Latest device reconciliation', tone: 'cyan' },
          { label: 'Events Captured Today', value: '118', context: 'Clock-in/out device events', tone: 'steel' },
          { label: 'Failed Attempts', value: '4', context: 'Fingerprint scans requiring retry', tone: 'rose' },
          { label: 'Unmatched Identities', value: '2', context: 'Captured but not matched', tone: 'rose' },
          { label: 'Sync Latency', value: '12 sec', context: 'Average event ingestion delay', tone: 'emerald' },
          { label: 'Offline Devices', value: '0', context: 'No terminal currently offline', tone: 'emerald' },
          { label: 'Coverage', value: '94%', context: 'Staff biometric profile coverage', tone: 'cyan' },
        ]}
        variant="dominant"
      >
        <div className="grid gap-5 2xl:grid-cols-[1.12fr_0.88fr]">
          <BiometricDeviceStatusPanel />
          <BiometricDeviceRiskPanel />
        </div>
        <BiometricActivityTimeline />
        <BiometricWorkflowStrip />
        <BiometricDemoNotice />
      </FocusedWorkspace>
    );
  }

  if (activeSubsection === 'Shift Compliance') {
    return (
      <FocusedWorkspace
        section="Staff Governance"
        subsection={activeSubsection}
        summary="CMD-level shift compliance view for roster coverage, department shift status, late/absence impact, handover readiness, and supervisor review needs. This view intentionally excludes the full attendance trace table and biometric device health grid."
        metrics={shiftComplianceMetrics}
        variant="alert"
      >
        <ShiftWindowCompliancePanel />
        <DepartmentShiftComplianceGrid />
        <div className="grid gap-5 2xl:grid-cols-[0.9fr_1.1fr]">
          <ShiftComplianceExceptionsPanel />
          <ShiftComplianceTimelinePanel />
        </div>
        <ShiftComplianceDemoNotice />
      </FocusedWorkspace>
    );
  }

  if (activeSubsection === 'Workforce Analytics') {
    return (
      <FocusedWorkspace
        section="Staff Governance"
        subsection={activeSubsection}
        summary="CMD-level workforce intelligence focused on trends, pressure patterns, workload versus staff availability, exception analytics, and risk forecasting. This view intentionally excludes staff trace tables, device monitoring, and roster-compliance grids."
        metrics={workforceAnalyticsMetrics}
        variant="dominant"
      >
        <WorkforceTrendPanel />
        <DepartmentWorkforceComparisonPanel />
        <div className="grid gap-5 2xl:grid-cols-[1fr_0.92fr]">
          <ExceptionPatternAnalyticsPanel />
          <WorkforceRiskForecastPanel />
        </div>
        <CmdWorkforceInsightPanel />
        <WorkforceAnalyticsDemoNotice />
      </FocusedWorkspace>
    );
  }

  return (
    <FocusedWorkspace
      section="Staff Governance"
      subsection="Department Staffing Posture"
      summary="CMD-level department staffing posture view for required staff, on-duty staff, coverage percentage, risk level, staffing gaps, and executive visibility priority. This view intentionally excludes attendance logs, biometric device logs, shift timelines, and workforce trend forecasting."
      metrics={departmentStaffingMetrics}
      variant="dominant"
    >
      <DepartmentStaffingMatrix />
      <div className="grid gap-5 2xl:grid-cols-[1fr_0.82fr]">
        <PriorityStaffingRisksPanel />
        <DepartmentCoverageDistributionPanel />
      </div>
      <CmdActionReadinessPanel />
      <DepartmentStaffingDemoNotice />
    </FocusedWorkspace>
  );
}

function FinancialIntelligenceWorkspace({ activeSubsection }: { activeSubsection: string }) {
  if (activeSubsection === 'Revenue Overview') {
    return (
      <FocusedWorkspace
        section="Financial Intelligence"
        subsection={activeSubsection}
        summary="Hospital-wide financial command summary for daily revenue, collection method posture, pharmacy contribution, outstanding exposure, and top revenue departments."
        metrics={revenueOverviewMetrics}
        variant="open"
      >
        <div className="grid gap-5 2xl:grid-cols-[1fr_0.9fr]">
          <TelemetryChart
            values={revenueTrend}
            tone="cyan"
            label="Daily revenue trend"
            meta="Hospital-wide revenue trajectory"
          />
          <TrustSignalGrid />
        </div>
        <PaymentMethodSplitPanel />
        <RevenueDepartmentSummaryPanel />
        <FinancialDemoNotice label="Frontend finance demo data" />
      </FocusedWorkspace>
    );
  }

  if (activeSubsection === 'Cashier Collections') {
    return (
      <FocusedWorkspace
        section="Financial Intelligence"
        subsection={activeSubsection}
        summary="CMD cashier-level collection visibility across 4 general cashier points and the dedicated pharmacy cashier. This is an oversight view, not a cashier operations screen."
        metrics={cashierCollectionMetrics}
        variant="open"
      >
        <FinancialFilterPanel
          searchPlaceholder="Search by patient name, MRN, receipt number, cashier, or payment reference"
          filters={[
            { label: 'Date', options: ['Today', 'Yesterday', 'This Week', 'Custom Date'] },
            { label: 'Department', options: ['All Departments', 'Main Desk', 'OPD/GOPD', 'Laboratory/Radiology', 'A&E', 'Pharmacy'] },
            { label: 'Payment Method', options: ['All Methods', 'POS', 'Bank Transfer', 'Cash'] },
            { label: 'Cashier Name', options: ['All Cashiers', 'Aisha Bello', 'Musa Abdullahi', 'Hauwa Sani', 'Ibrahim Lawal', 'Maryam Ali'] },
            { label: 'Shift Status', options: ['All Shifts', 'Open', 'Closed', 'Variance Watch'] },
          ]}
        />
        <CashierCollectionsPanel />
        <FinancialDemoNotice label="Collections API pending" />
      </FocusedWorkspace>
    );
  }

  if (activeSubsection === 'Payment Traceability') {
    return (
      <FocusedWorkspace
        section="Financial Intelligence"
        subsection={activeSubsection}
        summary="Transaction-level audit trail showing every visible receipt, patient, MRN, department, service, cashier, payment method, reference, status, and traceability state."
        metrics={paymentTraceabilityMetrics}
        variant="open"
      >
        <FinancialFilterPanel
          searchPlaceholder="Search receipt, MRN, patient, cashier, reference, or service"
          filters={[
            { label: 'Date', options: ['Today', 'Yesterday', 'This Week', 'Custom Date'] },
            { label: 'Department', options: ['All Departments', 'Pharmacy', 'Laboratory', 'A&E', 'OPD', 'Radiology'] },
            { label: 'Cashier', options: ['All Cashiers', 'Maryam Ali', 'Hauwa Sani', 'Ibrahim Lawal', 'Musa Abdullahi'] },
            { label: 'Payment Method', options: ['All Methods', 'POS', 'Bank Transfer', 'Cash'] },
            { label: 'Transaction Status', options: ['All Status', 'Verified', 'Matched', 'Pending Review'] },
            { label: 'Amount Range', options: ['All Amounts', 'Under ₦10K', '₦10K-₦50K', 'Above ₦50K'] },
          ]}
        />
        <PaymentTraceabilityPanel />
        <FinancialDemoNotice label="Receipt trace API pending" />
      </FocusedWorkspace>
    );
  }

  if (activeSubsection === 'Department Revenue') {
    return (
      <FocusedWorkspace
        section="Financial Intelligence"
        subsection={activeSubsection}
        summary="Revenue ranking by department and service line, with department share, transaction count, performance state, and traceability preview."
        metrics={departmentRevenueMetrics}
        variant="open"
      >
        <div className="grid gap-5 2xl:grid-cols-[0.82fr_1.18fr]">
          <TelemetryChart
            values={revenueTrend}
            tone="cyan"
            label="Department revenue trend"
            meta="Service-line movement preview"
          />
          <RevenueDepartmentSummaryPanel />
        </div>
        <DepartmentRevenueLeaderboardPanel />
        <FinancialDemoNotice label="Department revenue API pending" />
      </FocusedWorkspace>
    );
  }

  if (activeSubsection === 'Revenue Reconciliation Intelligence') {
    return (
      <FocusedWorkspace
        section="Financial Intelligence"
        subsection={activeSubsection}
        summary="Executive financial governance intelligence for reconciliation, variance detection, payment method settlement matching, cashier accountability, department alignment, and CMD review guidance."
        metrics={revenueReconciliationMetrics}
        variant="open"
      >
        <div className="grid gap-5 2xl:grid-cols-[1.12fr_0.88fr]">
          <CashierReconciliationMatrix />
          <PaymentMethodReconciliationPanel />
        </div>
        <DepartmentReconciliationStatusPanel />
        <div className="grid gap-5 2xl:grid-cols-[0.9fr_1.1fr]">
          <ReconciliationRiskSignalsPanel />
          <ReconciliationTimelinePanel />
        </div>
        <GuidedReconciliationPanel />
        <FinancialDemoNotice label="Reconciliation API pending" />
      </FocusedWorkspace>
    );
  }

  if (activeSubsection === 'Outstanding Bills') {
    return (
      <FocusedWorkspace
        section="Financial Intelligence"
        subsection={activeSubsection}
        summary="Unpaid balance visibility for inpatient pending bills, pharmacy unpaid bills, laboratory unpaid bills, discharge clearance, aging, and patient outstanding preview."
        metrics={outstandingBillMetrics}
        variant="open"
      >
        <OutstandingBillsPanel />
        <FinancialDemoNotice label="Outstanding bills API pending" />
      </FocusedWorkspace>
    );
  }

  if (activeSubsection === 'Refund & Waiver Audit') {
    return (
      <FocusedWorkspace
        section="Financial Intelligence"
        subsection={activeSubsection}
        summary="CMD control surface for sensitive financial exceptions including refund requests, waivers, discounts, adjustment history, approval audit trail, and suspicious adjustment alerts."
        metrics={refundWaiverMetrics}
        variant="alert"
      >
        <RefundWaiverAuditPanel />
        <FinancialDemoNotice label="Refund/waiver API pending" />
      </FocusedWorkspace>
    );
  }

  return (
    <FocusedWorkspace
      section="Financial Intelligence"
      subsection="Pharmacy Revenue & Traceability"
      summary="Pharmacy-specific revenue visibility for the dedicated pharmacy cashier, dispensing receipts, high-value medicine transactions, voided receipt risk, payment method posture, and receipt traceability."
      metrics={pharmacyRevenueMetrics}
      variant="open"
    >
      <PharmacyRevenueTracePanel />
      <FinancialDemoNotice label="Pharmacy revenue API pending" />
    </FocusedWorkspace>
  );
}

function GenericWorkspace({
  activeSection,
  activeSubsection,
}: {
  activeSection: string;
  activeSubsection: string;
}) {
  const metrics = getWorkspaceMetrics(activeSection, activeSubsection);
  const summary = getWorkspaceSummary(activeSection, activeSubsection);
  const variant = getWorkspaceVariant(activeSection, activeSubsection);

  if (activeSection === 'Hospital Operations') {
    return (
      <FocusedWorkspace section={activeSection} subsection={activeSubsection} summary={summary} metrics={metrics} variant={variant}>
        <div className="grid gap-4 lg:grid-cols-2">
          {departmentLoads.map((item) => (
            <DepartmentLoadCard key={item.department} item={item} />
          ))}
        </div>
        <TelemetryChart values={patientFlowTrend} tone="emerald" label={activeSubsection} meta="Operational pressure trend" />
      </FocusedWorkspace>
    );
  }

  if (activeSection === 'Financial Intelligence') {
    return (
      <FocusedWorkspace section={activeSection} subsection={activeSubsection} summary={summary} metrics={metrics} variant={variant}>
        <div className="grid gap-5 2xl:grid-cols-[1fr_1fr]">
          <TelemetryChart values={revenueTrend} tone="cyan" label={activeSubsection} meta="Executive financial telemetry" />
          <TrustSignalGrid />
        </div>
        <FocusedRows section={activeSection} subsection={activeSubsection} rows={financeRows} />
      </FocusedWorkspace>
    );
  }

  if (activeSection === 'Pharmacy & Supply Governance') {
    return (
      <FocusedWorkspace section={activeSection} subsection={activeSubsection} summary={summary} metrics={metrics} variant={variant}>
        <FocusedRows section={activeSection} subsection={activeSubsection} rows={supplySignals} />
      </FocusedWorkspace>
    );
  }

  if (activeSection === 'Audit & Compliance') {
    return (
      <FocusedWorkspace section={activeSection} subsection={activeSubsection} summary={summary} metrics={metrics} variant={variant}>
        <FocusedRows section={activeSection} subsection={activeSubsection} rows={auditRows} />
      </FocusedWorkspace>
    );
  }

  if (activeSection === 'Executive Reports') {
    return (
      <FocusedWorkspace section={activeSection} subsection={activeSubsection} summary={summary} metrics={metrics} variant={variant}>
        <FocusedRows section={activeSection} subsection={activeSubsection} rows={executiveReportRows} />
      </FocusedWorkspace>
    );
  }

  if (activeSection === 'Executive Settings') {
    return (
      <FocusedWorkspace section={activeSection} subsection={activeSubsection} summary={summary} metrics={metrics} variant={variant}>
        <div className="rounded-lg border border-white/[0.08] bg-slate-950/24 p-5 text-sm leading-6 text-slate-400">
          {activeSubsection} is represented as a CMD preference preview. Operational controls remain separated from executive oversight.
        </div>
      </FocusedWorkspace>
    );
  }

  return <ExecutiveOverviewWorkspace activeSubsection={activeSubsection} />;
}

function WorkspaceContent({
  activeSection,
  activeSubsection,
}: {
  activeSection: string;
  activeSubsection: string;
}) {
  if (activeSection === 'Executive Overview') {
    return <ExecutiveOverviewWorkspace activeSubsection={activeSubsection} />;
  }

  if (activeSection === 'Staff Governance') {
    return <StaffGovernanceWorkspace activeSubsection={activeSubsection} />;
  }

  if (activeSection === 'Financial Intelligence') {
    return <FinancialIntelligenceWorkspace activeSubsection={activeSubsection} />;
  }

  return <GenericWorkspace activeSection={activeSection} activeSubsection={activeSubsection} />;
}

export default function CmdPage() {
  const [activeNavigation, setActiveNavigation] = useState<ActiveNavigation>({
    section: navigationGroups[0].title,
    subsection: navigationGroups[0].items[0],
  });

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#030b16] text-white">
      <CmdAtmosphereStyles />
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(135deg,#030b16_0%,#061526_38%,#092033_72%,#030b16_100%)]" />
      <div className="cmd-grid-drift pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(125,211,252,0.042)_1px,transparent_1px),linear-gradient(90deg,rgba(125,211,252,0.034)_1px,transparent_1px)] bg-[size:72px_72px] opacity-[0.34]" />
      <div className="cmd-atmosphere-drift pointer-events-none fixed -left-32 top-0 h-[44rem] w-[58rem] bg-[radial-gradient(ellipse_at_center,rgba(34,211,238,0.085),transparent_70%)] blur-3xl" />
      <div className="cmd-atmosphere-drift-slow pointer-events-none fixed right-0 top-72 h-[34rem] w-[44rem] bg-[radial-gradient(ellipse_at_center,rgba(16,185,129,0.062),transparent_72%)] blur-3xl" />
      <div className="pointer-events-none fixed bottom-0 left-1/4 h-[28rem] w-[50rem] bg-[radial-gradient(ellipse_at_center,rgba(15,23,42,0.72),transparent_70%)] blur-3xl" />
      <div className="pointer-events-none fixed inset-x-0 top-0 h-56 bg-gradient-to-b from-cyan-300/[0.055] to-transparent" />
      <div className="pointer-events-none fixed inset-y-0 right-0 w-1/3 bg-gradient-to-l from-emerald-300/[0.045] to-transparent" />

      <div className="relative grid gap-5 p-4 md:p-6 xl:grid-cols-[330px_minmax(0,1fr)]">
        <CmdSidebar
          activeSection={activeNavigation.section}
          activeSubsection={activeNavigation.subsection}
          onNavigate={setActiveNavigation}
        />

        <main className="space-y-6">
          <ExecutiveHeader
            activeSection={activeNavigation.section}
            activeSubsection={activeNavigation.subsection}
          />
          <WorkspaceContent
            activeSection={activeNavigation.section}
            activeSubsection={activeNavigation.subsection}
          />
        </main>
      </div>
    </div>
  );
}
