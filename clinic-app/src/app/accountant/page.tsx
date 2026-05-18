'use client';

import { useState, type ReactNode } from 'react';

type Workspace =
  | 'overview'
  | 'cashiers'
  | 'reconciliation'
  | 'verification'
  | 'refunds'
  | 'waivers'
  | 'outstanding'
  | 'departments'
  | 'close'
  | 'exceptions'
  | 'audit'
  | 'preferences';

type Tone = 'steel' | 'cyan' | 'emerald' | 'amber' | 'rose' | 'indigo' | 'slate';

type Metric = {
  label: string;
  value: string;
  detail: string;
  tone: Tone;
};

type CashierSession = {
  cashier: string;
  desk: string;
  shift: string;
  collections: string;
  expectedCash: string;
  declaredCash: string;
  variance: string;
  receipts: string;
  status: string;
  reviewState: string;
  tone: Tone;
};

type ReconciliationSource = {
  source: string;
  expected: string;
  matched: string;
  variance: string;
  status: string;
  tone: Tone;
};

type TransactionVerification = {
  receipt: string;
  patient: string;
  mrn: string;
  department: string;
  amount: string;
  method: string;
  reference: string;
  settlement: string;
  state: string;
  cashier: string;
  tone: Tone;
};

const navItems: Array<{ key: Workspace; label: string; description: string }> = [
  {
    key: 'overview',
    label: 'Financial Control Overview',
    description: 'Collections, variance, reviews, and close posture',
  },
  {
    key: 'cashiers',
    label: 'Cashier Session Oversight',
    description: 'Cashier shift, receipts, cash, and variance control',
  },
  {
    key: 'reconciliation',
    label: 'Revenue Reconciliation Intelligence',
    description: 'Matched receipts, settlement evidence, and risk signals',
  },
  {
    key: 'verification',
    label: 'Payment Verification',
    description: 'Receipt, reference, method, and settlement checks',
  },
  {
    key: 'refunds',
    label: 'Refund & Reversal Governance',
    description: 'Controlled financial approval queue',
  },
  {
    key: 'waivers',
    label: 'Waiver & Discount Review',
    description: 'Financial concession and policy compliance review',
  },
  {
    key: 'outstanding',
    label: 'Outstanding Bills Control',
    description: 'Unpaid balances and discharge financial holds',
  },
  {
    key: 'departments',
    label: 'Department Revenue Control',
    description: 'Department revenue, variance, and traceability posture',
  },
  {
    key: 'close',
    label: 'Daily Close & Handover',
    description: 'Close integrity, handover, exceptions, and lock status',
  },
  {
    key: 'exceptions',
    label: 'Financial Exceptions',
    description: 'Duplicate, void, variance, and settlement anomalies',
  },
  {
    key: 'audit',
    label: 'Audit Trail & Reports',
    description: 'Immutable trace rows and export readiness',
  },
  {
    key: 'preferences',
    label: 'Financial Control Preferences',
    description: 'Workstation, thresholds, reports, and notifications',
  },
];

const overviewMetrics: Metric[] = [
  { label: 'Total Collections Today', value: '₦8.42M', detail: 'All cashier-posted collections', tone: 'cyan' },
  { label: 'Reconciled Amount', value: '₦8.31M', detail: 'Matched to receipt and settlement evidence', tone: 'emerald' },
  { label: 'Outstanding Variance', value: '₦110K', detail: 'Requires review before clean close', tone: 'rose' },
  { label: 'Pending Reviews', value: '11', detail: 'Refund, reversal, waiver, and variance queue', tone: 'amber' },
  { label: 'Unmatched Transfers', value: '4', detail: 'Bank references awaiting evidence match', tone: 'amber' },
  { label: 'Refund Exposure', value: '₦86K', detail: 'Sensitive exception value pending control', tone: 'rose' },
  { label: 'Daily Close Status', value: 'Pending Review', detail: 'Blocked until critical variance is resolved', tone: 'indigo' },
  { label: 'Critical Exceptions', value: '3', detail: 'CMD/Admin visibility required', tone: 'rose' },
];

const reconciliationMetrics: Metric[] = [
  { label: 'Total Collections', value: '₦8.42M', detail: 'Declared collection posture', tone: 'cyan' },
  { label: 'Reconciled Amount', value: '₦8.31M', detail: 'Receipts and settlement matched', tone: 'emerald' },
  { label: 'Variance', value: '₦110K', detail: 'Unresolved variance queue', tone: 'rose' },
  { label: 'Matched Receipts', value: '176 / 184', detail: 'Receipt traceability coverage', tone: 'emerald' },
  { label: 'Unmatched Transactions', value: '8', detail: 'Needs reconciliation evidence', tone: 'amber' },
  { label: 'Suspicious Adjustments', value: '3', detail: 'Audit-visible control signals', tone: 'rose' },
  { label: 'Pending Cashier Closures', value: '2', detail: 'Cashier sessions awaiting close evidence', tone: 'amber' },
];

const cashierSessions: CashierSession[] = [
  {
    cashier: 'Aisha Bello',
    desk: 'Main Cashier Desk',
    shift: 'Open',
    collections: '₦1.85M',
    expectedCash: '₦470K',
    declaredCash: '₦470K',
    variance: '₦0',
    receipts: '42',
    status: 'Matched',
    reviewState: 'Clean',
    tone: 'emerald',
  },
  {
    cashier: 'Musa Abdullahi',
    desk: 'OPD Cashier Point',
    shift: 'Pending Close',
    collections: '₦1.22M',
    expectedCash: '₦315K',
    declaredCash: '₦295K',
    variance: '₦20K',
    receipts: '38',
    status: 'Review',
    reviewState: 'Accountant review',
    tone: 'amber',
  },
  {
    cashier: 'Hauwa Sani',
    desk: 'Laboratory/Radiology Cashier',
    shift: 'Closed',
    collections: '₦980K',
    expectedCash: '₦188K',
    declaredCash: '₦188K',
    variance: '₦0',
    receipts: '31',
    status: 'Matched',
    reviewState: 'Close ready',
    tone: 'emerald',
  },
  {
    cashier: 'Ibrahim Lawal',
    desk: 'A&E Cashier Point',
    shift: 'Open',
    collections: '₦760K',
    expectedCash: '₦205K',
    declaredCash: '₦155K',
    variance: '₦50K',
    receipts: '24',
    status: 'Critical Variance',
    reviewState: 'CMD visibility',
    tone: 'rose',
  },
  {
    cashier: 'Maryam Ali',
    desk: 'Pharmacy Cashier',
    shift: 'Pending Close',
    collections: '₦2.14M',
    expectedCash: '₦402K',
    declaredCash: '₦362K',
    variance: '₦40K',
    receipts: '49',
    status: 'Review',
    reviewState: 'Pharmacy variance',
    tone: 'amber',
  },
];

const reconciliationSources: ReconciliationSource[] = [
  { source: 'POS', expected: '₦3.62M', matched: '₦3.60M', variance: '₦20K', status: 'Review', tone: 'amber' },
  { source: 'Bank Transfer', expected: '₦2.88M', matched: '₦2.88M', variance: '₦0', status: 'Matched', tone: 'emerald' },
  { source: 'Cash', expected: '₦1.92M', matched: '₦1.83M', variance: '₦90K', status: 'Pending Review', tone: 'rose' },
  { source: 'Pharmacy', expected: '₦2.14M', matched: '₦2.10M', variance: '₦40K', status: 'Review', tone: 'amber' },
  { source: 'Laboratory', expected: '₦1.38M', matched: '₦1.38M', variance: '₦0', status: 'Matched', tone: 'emerald' },
  { source: 'OPD/GOPD', expected: '₦1.22M', matched: '₦1.20M', variance: '₦20K', status: 'Review', tone: 'amber' },
  { source: 'A&E', expected: '₦960K', matched: '₦910K', variance: '₦50K', status: 'Critical Variance', tone: 'rose' },
];

const verificationRows: TransactionVerification[] = [
  {
    receipt: 'RCP-2026-00091',
    patient: 'Abba Nura',
    mrn: '0000001-9',
    department: 'Pharmacy',
    amount: '₦18,500',
    method: 'POS',
    reference: 'POS-A92F',
    settlement: 'Matched',
    state: 'Verified',
    cashier: 'Maryam Ali',
    tone: 'emerald',
  },
  {
    receipt: 'RCP-2026-00092',
    patient: 'Muhammad Nura',
    mrn: '0000002-8',
    department: 'Laboratory',
    amount: '₦7,500',
    method: 'Cash',
    reference: 'CASH-1182',
    settlement: 'Cash declared',
    state: 'Verified',
    cashier: 'Hauwa Sani',
    tone: 'emerald',
  },
  {
    receipt: 'RCP-2026-00093',
    patient: 'Sani Umar',
    mrn: '0000003-7',
    department: 'A&E',
    amount: '₦25,000',
    method: 'Bank Transfer',
    reference: 'TRF-8841',
    settlement: 'Reference pending',
    state: 'Review',
    cashier: 'Ibrahim Lawal',
    tone: 'amber',
  },
  {
    receipt: 'RCP-2026-00094',
    patient: 'Fatima Kabir',
    mrn: '0000005-3',
    department: 'Radiology',
    amount: '₦12,000',
    method: 'Bank Transfer',
    reference: 'TRF-5510',
    settlement: 'Matched',
    state: 'Verified',
    cashier: 'Hauwa Sani',
    tone: 'emerald',
  },
  {
    receipt: 'RCP-2026-00108',
    patient: 'Umar Garba',
    mrn: '0000011-2',
    department: 'Theatre',
    amount: '₦185,000',
    method: 'Cash',
    reference: 'CASH-1190',
    settlement: 'High-value cash',
    state: 'CMD Visibility Required',
    cashier: 'Ibrahim Lawal',
    tone: 'rose',
  },
];

const departmentRevenue = [
  { department: 'Pharmacy', revenue: '₦2.14M', share: 26, transactions: 49, split: 'POS 42% · Transfer 35% · Cash 23%', variance: '₦40K', status: 'Review', tone: 'amber' as Tone },
  { department: 'Laboratory', revenue: '₦1.38M', share: 17, transactions: 31, split: 'POS 36% · Transfer 44% · Cash 20%', variance: '₦0', status: 'Matched', tone: 'emerald' as Tone },
  { department: 'OPD/GOPD', revenue: '₦1.22M', share: 15, transactions: 38, split: 'POS 50% · Transfer 18% · Cash 32%', variance: '₦20K', status: 'Review', tone: 'amber' as Tone },
  { department: 'A&E', revenue: '₦960K', share: 12, transactions: 24, split: 'POS 33% · Transfer 28% · Cash 39%', variance: '₦50K', status: 'Critical', tone: 'rose' as Tone },
  { department: 'Radiology', revenue: '₦890K', share: 11, transactions: 22, split: 'POS 30% · Transfer 57% · Cash 13%', variance: '₦0', status: 'Matched', tone: 'emerald' as Tone },
  { department: 'Maternity', revenue: '₦620K', share: 8, transactions: 16, split: 'POS 45% · Transfer 34% · Cash 21%', variance: '₦0', status: 'Matched', tone: 'emerald' as Tone },
  { department: 'Theatre', revenue: '₦540K', share: 7, transactions: 9, split: 'POS 20% · Transfer 46% · Cash 34%', variance: '₦35K', status: 'Review', tone: 'amber' as Tone },
  { department: 'Pediatrics', revenue: '₦310K', share: 4, transactions: 11, split: 'POS 41% · Transfer 37% · Cash 22%', variance: '₦0', status: 'Matched', tone: 'emerald' as Tone },
];

const refundRequests = [
  { type: 'Refund', receipt: 'RCP-2026-00078', patient: 'Hauwa Sani', amount: '₦42,000', requestedBy: 'Billing Supervisor', reason: 'Duplicate charge correction', risk: 'Significant', status: 'Secondary Approval', tone: 'amber' as Tone },
  { type: 'Reversal', receipt: 'RCP-2026-00083', patient: 'Sani Umar', amount: '₦185,000', requestedBy: 'A&E Desk', reason: 'High-value cash correction', risk: 'Critical', status: 'CMD Visibility', tone: 'rose' as Tone },
  { type: 'Refund', receipt: 'RCP-2026-00096', patient: 'Fatima Kabir', amount: '₦12,000', requestedBy: 'Radiology Lead', reason: 'Service cancelled before imaging', risk: 'Minor', status: 'Review Request', tone: 'amber' as Tone },
];

const waiverRequests = [
  { patient: 'Amina Lawal', mrn: '0000021-5', type: 'Waiver', amount: '₦25,000', source: 'Hospital Admin', justification: 'Social welfare concession', policy: 'Policy evidence required', tone: 'amber' as Tone },
  { patient: 'Bala Garba', mrn: '0000022-4', type: 'Discount', amount: '₦8,500', source: 'Department HOD', justification: 'Approved staff dependent discount', policy: 'Compliant', tone: 'emerald' as Tone },
  { patient: 'Zainab Musa', mrn: '0000023-3', type: 'Waiver', amount: '₦67,000', source: 'Manual request', justification: 'Critical hardship request', policy: 'CMD visibility required', tone: 'rose' as Tone },
];

const outstandingRows = [
  { patient: 'Maryam Aliyu', mrn: '0000040-2', department: 'Inpatient', amount: '₦420,000', aging: '6 days', status: 'Discharge Hold', tone: 'rose' as Tone },
  { patient: 'Abba Sani', mrn: '0000041-1', department: 'Pharmacy', amount: '₦78,000', aging: '2 days', status: 'Pending clearance', tone: 'amber' as Tone },
  { patient: 'Umar Bala', mrn: '0000042-0', department: 'Laboratory', amount: '₦19,500', aging: 'Today', status: 'Awaiting payment', tone: 'amber' as Tone },
  { patient: 'Hadiza Ibrahim', mrn: '0000043-9', department: 'Maternity', amount: '₦126,000', aging: '4 days', status: 'Review', tone: 'amber' as Tone },
];

const closeChecklist = [
  { item: 'Cashier sessions reviewed', state: '4 / 5 complete', done: false, tone: 'amber' as Tone },
  { item: 'Transfers verified', state: '4 unmatched references', done: false, tone: 'amber' as Tone },
  { item: 'POS settlement checked', state: '₦20K review variance', done: false, tone: 'amber' as Tone },
  { item: 'Variance reviewed', state: 'Critical variance unresolved', done: false, tone: 'rose' as Tone },
  { item: 'Refunds reviewed', state: '3 pending reviews', done: false, tone: 'amber' as Tone },
  { item: 'Waivers reviewed', state: '1 CMD-visible request', done: false, tone: 'rose' as Tone },
  { item: 'Exceptions acknowledged', state: 'Pending accountant action', done: false, tone: 'rose' as Tone },
];

const exceptionRows = [
  { category: 'Duplicate Payments', count: '2', detail: 'Possible duplicate POS attempt and repeated invoice reference', severity: 'Significant', tone: 'amber' as Tone },
  { category: 'Voided Receipts', count: '3', detail: 'Voids after cashier shift close require audit review', severity: 'Significant', tone: 'amber' as Tone },
  { category: 'Delayed Settlements', count: '4', detail: 'Bank transfer confirmations delayed beyond review threshold', severity: 'Minor', tone: 'amber' as Tone },
  { category: 'Repeated Variance', count: '2', detail: 'Repeated variance pattern across OPD and A&E desks', severity: 'Critical', tone: 'rose' as Tone },
  { category: 'Unmatched Transfers', count: '4', detail: 'Transfer references require evidence match', severity: 'Significant', tone: 'amber' as Tone },
  { category: 'Suspicious Adjustments', count: '3', detail: 'Manual cashier adjustments require secondary authorization', severity: 'CMD Visibility Required', tone: 'rose' as Tone },
];

const auditEvents = [
  { time: '08:44 AM', actor: 'Aisha Bello', event: 'Receipt issued', detail: 'RCP-2026-00091 matched to POS reference POS-A92F', tone: 'emerald' as Tone },
  { time: '09:18 AM', actor: 'Musa Abdullahi', event: 'Cash variance detected', detail: 'OPD cashier session variance moved to accountant review', tone: 'amber' as Tone },
  { time: '10:05 AM', actor: 'System', event: 'Settlement evidence matched', detail: 'Bank transfer batch TRF-5510 verified against receipt register', tone: 'emerald' as Tone },
  { time: '11:22 AM', actor: 'Ibrahim Lawal', event: 'Critical variance escalated', detail: 'A&E cashier variance reached CMD visibility threshold', tone: 'rose' as Tone },
  { time: '12:14 PM', actor: 'Amina Yusuf', event: 'Reconciliation note added', detail: 'Unmatched receipts queued for accountant evidence review', tone: 'cyan' as Tone },
];

const reports = [
  { title: 'Daily Close Report', detail: 'Close readiness, unresolved exceptions, cashier summaries', state: 'Pending close', tone: 'amber' as Tone },
  { title: 'Reconciliation Report', detail: 'Matched receipts, variances, settlement evidence', state: 'Draft ready', tone: 'cyan' as Tone },
  { title: 'Refund/Reversal Report', detail: 'Sensitive exception queue with approval states', state: 'Review required', tone: 'rose' as Tone },
  { title: 'Department Revenue Report', detail: 'Revenue, transactions, method split, variance by department', state: 'Export ready', tone: 'emerald' as Tone },
];

const integrityPrinciples = [
  'No untraceable financial action',
  'No destructive financial mutation',
  'No reconciliation without evidence',
  'No clean close with unresolved critical variance',
  'No sensitive approval without authority',
  'No financial exception without audit visibility',
  'No settlement verification without reference evidence',
  'No financial control outside immutable auditability',
];

const metricVisuals: Record<string, number[]> = {
  'Total Collections Today': [54, 62, 58, 67, 72, 81, 88, 92],
  'Reconciled Amount': [48, 55, 60, 68, 73, 77, 84, 91],
  'Outstanding Variance': [18, 24, 16, 28, 39, 34, 46, 41],
  'Pending Reviews': [32, 35, 28, 41, 43, 39, 47, 44],
  'Unmatched Transfers': [26, 31, 22, 29, 35, 30, 33, 28],
  'Refund Exposure': [14, 22, 18, 24, 21, 29, 34, 31],
  'Daily Close Status': [20, 25, 36, 42, 49, 54, 61, 64],
  'Critical Exceptions': [18, 21, 19, 24, 29, 35, 40, 37],
  'Total Collections': [52, 64, 61, 70, 76, 82, 88, 94],
  'Variance': [14, 19, 22, 18, 27, 35, 31, 38],
  'Matched Receipts': [58, 61, 67, 71, 76, 80, 87, 96],
  'Unmatched Transactions': [24, 22, 29, 34, 31, 28, 33, 30],
  'Suspicious Adjustments': [10, 14, 9, 18, 22, 19, 25, 21],
  'Pending Cashier Closures': [20, 18, 24, 29, 26, 30, 27, 24],
};

const financeMissionStates = [
  { label: 'Stable', detail: 'Matched evidence', tone: 'emerald' as Tone, active: false },
  { label: 'Elevated Review', detail: '11 pending controls', tone: 'amber' as Tone, active: true },
  { label: 'Variance Exposure', detail: '₦110K unresolved', tone: 'rose' as Tone, active: true },
  { label: 'Critical Review', detail: '3 escalations', tone: 'rose' as Tone, active: true },
  { label: 'Close Locked', detail: 'Clean close blocked', tone: 'indigo' as Tone, active: true },
];

const paymentDistribution = [
  { label: 'POS', value: '₦3.62M', share: 43, tone: 'cyan' as Tone },
  { label: 'Transfer', value: '₦2.88M', share: 34, tone: 'steel' as Tone },
  { label: 'Cash', value: '₦1.92M', share: 23, tone: 'emerald' as Tone },
];

const closeProgress = [
  { label: 'Sessions', value: 80, tone: 'amber' as Tone },
  { label: 'Settlement', value: 72, tone: 'amber' as Tone },
  { label: 'Variance', value: 38, tone: 'rose' as Tone },
  { label: 'Audit Evidence', value: 86, tone: 'emerald' as Tone },
];

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function badgeClass(tone: Tone) {
  const classes: Record<Tone, string> = {
    steel: 'border-slate-400 bg-slate-100 text-slate-800',
    cyan: 'border-cyan-300 bg-cyan-50 text-cyan-800',
    emerald: 'border-emerald-300 bg-emerald-50 text-emerald-800',
    amber: 'border-amber-300 bg-amber-50 text-amber-800',
    rose: 'border-rose-300 bg-rose-50 text-rose-800',
    indigo: 'border-indigo-300 bg-indigo-50 text-indigo-800',
    slate: 'border-slate-300 bg-white text-slate-700',
  };
  return classes[tone];
}

function surfaceClass(tone: Tone) {
  const classes: Record<Tone, string> = {
    steel: 'border-slate-400 bg-slate-100/95 shadow-slate-300',
    cyan: 'border-cyan-400 bg-cyan-50/90 shadow-cyan-200',
    emerald: 'border-emerald-400 bg-emerald-50/90 shadow-emerald-200',
    amber: 'border-amber-400 bg-amber-50/90 shadow-amber-200',
    rose: 'border-rose-400 bg-rose-50/90 shadow-rose-200',
    indigo: 'border-indigo-400 bg-indigo-50/90 shadow-indigo-200',
    slate: 'border-slate-300 bg-slate-50 shadow-slate-200',
  };
  return classes[tone];
}

function methodTone(method: string): Tone {
  if (method === 'POS') return 'cyan';
  if (method === 'Bank Transfer') return 'steel';
  if (method === 'Cash') return 'emerald';
  return 'slate';
}

function fillClass(tone: Tone) {
  const classes: Record<Tone, string> = {
    steel: 'bg-slate-600',
    cyan: 'bg-cyan-500',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    rose: 'bg-rose-500',
    indigo: 'bg-indigo-500',
    slate: 'bg-slate-400',
  };
  return classes[tone];
}

function glowClass(tone: Tone) {
  const classes: Record<Tone, string> = {
    steel: 'shadow-slate-400/50',
    cyan: 'shadow-cyan-400/50',
    emerald: 'shadow-emerald-400/50',
    amber: 'shadow-amber-400/50',
    rose: 'shadow-rose-400/50',
    indigo: 'shadow-indigo-400/50',
    slate: 'shadow-slate-300/50',
  };
  return classes[tone];
}

function MicroBars({ values, tone = 'cyan' }: { values: number[]; tone?: Tone }) {
  return (
    <div className="flex h-9 items-end gap-1" aria-hidden="true">
      {values.map((value, index) => (
        <span
          key={`${value}-${index}`}
          className={cx('flex-1 rounded-t-sm opacity-80 transition-all duration-300 hover:opacity-100', fillClass(tone))}
          style={{ height: `${Math.max(18, Math.min(100, value))}%` }}
        />
      ))}
    </div>
  );
}

function DistributionStrip({
  items,
}: {
  items: Array<{ label: string; value: string; share: number; tone: Tone }>;
}) {
  return (
    <div className="space-y-2">
      <div className="flex h-2.5 overflow-hidden rounded-full bg-slate-200">
        {items.map((item) => (
          <span key={item.label} className={fillClass(item.tone)} style={{ width: `${item.share}%` }} />
        ))}
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        {items.map((item) => (
          <div key={item.label} className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 shadow-sm">
            <p className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">{item.label}</p>
            <p className="mt-0.5 text-sm font-black text-slate-950">{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function OperationalFinanceShell({ activeLabel }: { activeLabel: string }) {
  return (
    <section className="mb-4 overflow-hidden rounded-2xl border border-slate-700/60 bg-[radial-gradient(circle_at_top_right,rgba(6,182,212,0.16),transparent_34%),linear-gradient(135deg,#020617,#0f172a_48%,#111827)] px-4 py-3 text-white shadow-[0_24px_70px_-45px_rgba(6,182,212,0.75)]">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-cyan-300">Operational Finance Workspace</p>
          <h1 className="mt-1 whitespace-nowrap text-[clamp(1.35rem,2.8vw,1.875rem)] font-black tracking-tight text-white">
            Accountant Financial Control Center
          </h1>
          <p className="mt-1 text-sm font-semibold text-slate-300">
            Active workspace: <span className="text-cyan-100">{activeLabel}</span>
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-3 xl:justify-end">
          {[
            ['Finance State', 'Elevated Review', 'amber' as Tone],
            ['Close Integrity', 'Locked', 'rose' as Tone],
            ['Audit Mode', 'Immutable Trace', 'emerald' as Tone],
          ].map(([label, value, tone]) => (
            <div key={label} className="min-w-[142px] rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 shadow-inner">
              <p className="text-[10px] font-black uppercase tracking-[0.13em] text-slate-400">{label}</p>
              <div className="mt-1 flex items-center gap-2">
                <span className={cx('h-2 w-2 rounded-full shadow-md animate-pulse', fillClass(tone as Tone), glowClass(tone as Tone))} />
                <p className="text-sm font-black text-white">{value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Badge({ children, tone = 'slate' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span className={cx('inline-flex rounded-full border px-2.5 py-1 text-xs font-black shadow-sm', badgeClass(tone))}>
      {children}
    </span>
  );
}

function Panel({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-300/80 bg-[linear-gradient(rgba(15,23,42,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.025)_1px,transparent_1px),linear-gradient(135deg,#f8fafc,#f1f5f9_58%,#e2e8f0)] bg-[length:28px_28px,28px_28px,auto] p-3.5 shadow-[0_18px_45px_-34px_rgba(15,23,42,0.75)] ring-1 ring-slate-100/80">
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-[15px] font-black tracking-tight text-slate-950">{title}</h2>
          {description ? <p className="mt-1 text-[13px] leading-6 text-slate-600">{description}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function WorkspaceShell({
  eyebrow,
  title,
  description,
  children,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <div className="overflow-hidden rounded-2xl border border-slate-700/70 bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.16),transparent_28%),linear-gradient(135deg,#020617,#0f172a_48%,#111827)] p-4 text-white shadow-[0_26px_70px_-45px_rgba(14,165,233,0.75)]">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] font-black uppercase tracking-[0.16em] text-cyan-300">{eyebrow}</p>
            <h1 className="mt-1.5 text-2xl font-black tracking-tight text-white sm:text-3xl">{title}</h1>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-300">{description}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="amber">Frontend demonstration data</Badge>
            {action}
          </div>
        </div>
      </div>
      {children}
    </section>
  );
}

function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <article
          key={metric.label}
          className={cx(
            'group rounded-xl border p-3.5 shadow-sm transition duration-300 hover:-translate-y-0.5 hover:shadow-lg',
            surfaceClass(metric.tone)
          )}
        >
          <p className="text-[10px] font-black uppercase tracking-[0.13em] text-slate-500">{metric.label}</p>
          <p className="mt-2 text-2xl font-black tracking-tight text-slate-950">{metric.value}</p>
          <p className="mt-1 text-[13px] leading-5 text-slate-600">{metric.detail}</p>
          {metricVisuals[metric.label] ? (
            <div className="mt-3 rounded-lg border border-slate-200/80 bg-slate-50/80 p-2">
              <MicroBars values={metricVisuals[metric.label]} tone={metric.tone} />
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function FilterPanel({ searchPlaceholder }: { searchPlaceholder: string }) {
  return (
    <Panel title="Filters & Search" description="UI-ready controls prepared for future finance APIs.">
      <div className="grid gap-3 lg:grid-cols-[minmax(260px,1.4fr)_repeat(5,minmax(135px,1fr))]">
        <label className="block">
          <span className="text-[11px] font-black uppercase tracking-[0.13em] text-slate-500">Search</span>
          <input
            className="mt-2 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none placeholder:text-slate-400 focus:border-cyan-500 focus:ring-4 focus:ring-cyan-100"
            placeholder={searchPlaceholder}
          />
        </label>
        {[
          ['Method', ['All Methods', 'POS', 'Bank Transfer', 'Cash']],
          ['Department', ['All Departments', 'Pharmacy', 'Laboratory', 'A&E', 'OPD/GOPD']],
          ['Date', ['Today', 'This Week', 'This Month']],
          ['Verification State', ['All States', 'Verified', 'Review', 'CMD Visibility Required']],
          ['Cashier', ['All Cashiers', 'Aisha Bello', 'Musa Abdullahi', 'Ibrahim Lawal']],
        ].map(([label, options]) => (
          <label key={label as string} className="block">
            <span className="text-[11px] font-black uppercase tracking-[0.13em] text-slate-500">{label as string}</span>
            <select className="mt-2 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none focus:border-cyan-500 focus:ring-4 focus:ring-cyan-100">
              {(options as string[]).map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>
        ))}
      </div>
    </Panel>
  );
}

function AccountantIdentityBadge() {
  return (
    <div className="rounded-xl border border-slate-600/50 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 p-2.5 text-white shadow-[0_18px_45px_-32px_rgba(6,182,212,0.9)]">
      <p className="text-[9px] font-black uppercase tracking-[0.16em] text-cyan-200">Financial Control Center</p>
      <p className="mt-0.5 text-[11px] font-semibold text-slate-300">Finance Operations Unit</p>
      <div className="mt-2 rounded-xl border border-white/10 bg-white/[0.06] px-2.5 py-2">
        <p className="text-sm font-black">Amina Yusuf</p>
        <p className="text-xs font-semibold text-slate-300">Senior Accountant</p>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        <div className="rounded-xl border border-amber-300/30 bg-amber-400/10 px-2 py-1.5">
          <p className="text-[9px] font-black uppercase tracking-[0.12em] text-amber-100">Daily Close</p>
          <p className="mt-0.5 text-xs font-black text-white">Pending</p>
        </div>
        <div className="rounded-xl border border-rose-300/30 bg-rose-400/10 px-2 py-1.5">
          <p className="text-[9px] font-black uppercase tracking-[0.12em] text-rose-100">Variance</p>
          <p className="mt-0.5 text-xs font-black text-white">3</p>
        </div>
      </div>
    </div>
  );
}

function IntegrityStrip() {
  return (
    <div className="grid gap-2 rounded-xl border border-indigo-300 bg-indigo-50/90 p-2.5 shadow-sm shadow-indigo-100 md:grid-cols-2 xl:grid-cols-4">
      {integrityPrinciples.slice(0, 4).map((principle) => (
        <div key={principle} className="rounded-lg border border-indigo-200 bg-slate-50 px-3 py-2 shadow-sm">
          <p className="text-xs font-black text-indigo-800">{principle}</p>
        </div>
      ))}
    </div>
  );
}

function MissionStatePanel() {
  return (
    <Panel
      title="Operational Finance State"
      description="Mission-state posture for reconciliation exposure, close integrity, and audit visibility."
      action={<Badge tone="rose">Close Locked</Badge>}
    >
      <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="grid gap-2 md:grid-cols-5">
          {financeMissionStates.map((state) => (
            <article
              key={state.label}
              className={cx(
                'rounded-xl border bg-slate-50 p-3 shadow-sm transition duration-300 hover:-translate-y-0.5',
                state.active ? 'border-slate-300' : 'border-slate-200 opacity-75'
              )}
            >
              <div className="flex items-center gap-2">
                <span className={cx('h-2.5 w-2.5 rounded-full shadow-md', state.active && 'animate-pulse', fillClass(state.tone), glowClass(state.tone))} />
                <p className="text-xs font-black text-slate-950">{state.label}</p>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">{state.detail}</p>
            </article>
          ))}
        </div>
        <div className="rounded-xl border border-slate-300 bg-slate-950 p-3 text-white shadow-inner">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.14em] text-cyan-300">Daily Close Progress</p>
              <p className="mt-1 text-lg font-black">64% evidence-ready</p>
            </div>
            <Badge tone="amber">Review Required</Badge>
          </div>
          <div className="mt-3 grid gap-2">
            {closeProgress.map((item) => (
              <div key={item.label}>
                <div className="mb-1 flex items-center justify-between text-[11px] font-black uppercase tracking-[0.1em] text-slate-300">
                  <span>{item.label}</span>
                  <span>{item.value}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div className={cx('h-full rounded-full', fillClass(item.tone))} style={{ width: `${item.value}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}

function StatusRows({ rows }: { rows: Array<{ title: string; detail: string; tone: Tone; value?: string }> }) {
  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <article key={row.title} className="flex items-center justify-between gap-3 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2.5 shadow-sm">
          <div className="min-w-0">
            <p className="text-sm font-black text-slate-950">{row.title}</p>
            <p className="mt-0.5 text-xs leading-5 text-slate-500">{row.detail}</p>
          </div>
          <Badge tone={row.tone}>{row.value ?? 'Active'}</Badge>
        </article>
      ))}
    </div>
  );
}

function CashierSessionMatrix() {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-300 bg-slate-50 shadow-sm shadow-slate-300/60">
      <div className="hidden grid-cols-[1.15fr_1.15fr_0.8fr_0.75fr_0.75fr_0.7fr_0.75fr_auto] gap-3 border-b border-slate-300 bg-slate-100 px-4 py-2.5 text-[11px] font-black uppercase tracking-[0.12em] text-slate-500 xl:grid">
        <span>Cashier</span>
        <span>Desk</span>
        <span>Shift</span>
        <span>Collections</span>
        <span>Expected</span>
        <span>Declared</span>
        <span>Variance</span>
        <span className="text-right">Review</span>
      </div>
      <div className="divide-y divide-slate-200">
        {cashierSessions.map((session) => (
          <article
            key={`${session.cashier}-${session.desk}`}
            className="grid gap-3 px-4 py-3 transition hover:bg-slate-50 xl:grid-cols-[1.15fr_1.15fr_0.8fr_0.75fr_0.75fr_0.7fr_0.75fr_auto] xl:items-center"
          >
            <div>
              <p className="font-black text-slate-950">{session.cashier}</p>
              <p className="text-xs text-slate-500">{session.receipts} receipts</p>
            </div>
            <p className="text-sm font-semibold text-slate-700">{session.desk}</p>
            <Badge tone={session.shift === 'Closed' ? 'emerald' : 'amber'}>{session.shift}</Badge>
            <p className="font-black text-slate-950">{session.collections}</p>
            <p className="text-sm font-bold text-slate-700">{session.expectedCash}</p>
            <p className="text-sm font-bold text-slate-700">{session.declaredCash}</p>
            <p className={cx('font-black', session.tone === 'rose' ? 'text-rose-700' : session.tone === 'amber' ? 'text-amber-700' : 'text-emerald-700')}>
              {session.variance}
            </p>
            <div className="xl:text-right">
              <Badge tone={session.tone}>{session.status}</Badge>
              <p className="mt-1 text-xs text-slate-500">{session.reviewState}</p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function ReconciliationMatrix() {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-300 bg-slate-50 shadow-sm">
      <div className="grid grid-cols-[1fr_0.8fr_0.8fr_0.7fr_auto] gap-3 border-b border-slate-300 bg-slate-100 px-4 py-2.5 text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">
        <span>Source</span>
        <span>Expected</span>
        <span>Matched</span>
        <span>Variance</span>
        <span className="text-right">Status</span>
      </div>
      <div className="divide-y divide-slate-200">
        {reconciliationSources.map((source) => (
          <div key={source.source} className="grid grid-cols-[1fr_0.8fr_0.8fr_0.7fr_auto] gap-3 px-4 py-3 text-sm">
            <p className="font-black text-slate-950">{source.source}</p>
            <p className="font-semibold text-slate-700">{source.expected}</p>
            <p className="font-semibold text-slate-700">{source.matched}</p>
            <p className="font-black text-slate-950">{source.variance}</p>
            <div className="text-right">
              <Badge tone={source.tone}>{source.status}</Badge>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TransactionVerificationRows() {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-300 bg-slate-50 shadow-sm">
      <div className="hidden grid-cols-[1fr_1fr_0.9fr_0.7fr_0.75fr_0.9fr_0.95fr_auto] gap-3 border-b border-slate-300 bg-slate-100 px-4 py-2.5 text-[11px] font-black uppercase tracking-[0.12em] text-slate-500 xl:grid">
        <span>Receipt</span>
        <span>Patient</span>
        <span>Department</span>
        <span>Amount</span>
        <span>Method</span>
        <span>Reference</span>
        <span>Settlement</span>
        <span className="text-right">State</span>
      </div>
      <div className="divide-y divide-slate-200">
        {verificationRows.map((row) => (
          <article
            key={row.receipt}
            className="grid gap-3 px-4 py-3 transition hover:bg-slate-50 xl:grid-cols-[1fr_1fr_0.9fr_0.7fr_0.75fr_0.9fr_0.95fr_auto] xl:items-center"
          >
            <div>
              <p className="font-black text-slate-950">{row.receipt}</p>
              <p className="text-xs text-slate-500">Cashier {row.cashier}</p>
            </div>
            <div>
              <p className="font-bold text-slate-900">{row.patient}</p>
              <p className="text-xs text-slate-500">MRN {row.mrn}</p>
            </div>
            <p className="text-sm font-semibold text-slate-700">{row.department}</p>
            <p className="font-black text-slate-950">{row.amount}</p>
            <Badge tone={methodTone(row.method)}>{row.method}</Badge>
            <p className="text-sm font-semibold text-slate-700">{row.reference}</p>
            <p className="text-sm font-semibold text-slate-700">{row.settlement}</p>
            <div className="xl:text-right">
              <Badge tone={row.tone}>{row.state}</Badge>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function FinancialControlOverviewWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Financial Control Authority"
      title="Financial Control Overview"
      description="High-level accountant posture for collections, reconciliation, pending reviews, exceptions, variance exposure, and daily close readiness."
      action={<Badge tone="indigo">Close Pending</Badge>}
    >
      <IntegrityStrip />
      <MissionStatePanel />
      <MetricGrid metrics={overviewMetrics} />
      <div className="grid gap-4 xl:grid-cols-4">
        <Panel title="Reconciliation Posture" description="Evidence-based matching before clean close.">
          <StatusRows
            rows={[
              { title: 'Receipt matching', detail: '176 of 184 receipts matched', tone: 'emerald', value: '96%' },
              { title: 'Variance control', detail: 'Critical variance blocks clean close', tone: 'rose', value: 'Blocked' },
              { title: 'Settlement evidence', detail: '4 transfer references pending', tone: 'amber', value: 'Review' },
            ]}
          />
        </Panel>
        <Panel title="Payment Method Posture" description="POS, transfer, and cash settlement state.">
          <div className="mb-3">
            <DistributionStrip items={paymentDistribution} />
          </div>
          <StatusRows
            rows={[
              { title: 'POS settlement', detail: '₦20K variance requires review', tone: 'amber', value: 'Review' },
              { title: 'Bank transfer', detail: 'Reference evidence mostly matched', tone: 'amber', value: '4 pending' },
              { title: 'Cash handover', detail: '₦90K cash variance exposure', tone: 'rose', value: 'Blocked' },
            ]}
          />
        </Panel>
        <Panel title="Cashier Posture" description="Cashier sessions and variance status.">
          <StatusRows
            rows={[
              { title: 'Open sessions', detail: '2 sessions still active', tone: 'amber', value: '2' },
              { title: 'Pending closures', detail: '2 cashier shifts awaiting close', tone: 'amber', value: '2' },
              { title: 'High variance', detail: 'A&E session reached threshold', tone: 'rose', value: '1' },
            ]}
          />
        </Panel>
        <Panel title="Close Readiness" description="No clean close with unresolved critical variance.">
          <StatusRows
            rows={[
              { title: 'Daily close', detail: 'Pending accountant review', tone: 'indigo', value: 'Pending' },
              { title: 'Critical exceptions', detail: 'CMD/Admin visibility required', tone: 'rose', value: '3' },
              { title: 'Accountant notes', detail: 'Close summary draft not final', tone: 'amber', value: 'Draft' },
            ]}
          />
        </Panel>
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Financial Alerts" description="Anti-leakage signals requiring accountant control.">
          <StatusRows
            rows={[
              { title: 'A&E critical variance', detail: '₦50K cashier variance requires CMD/Admin visibility.', tone: 'rose', value: 'Critical' },
              { title: 'Unmatched transfer references', detail: '4 references require settlement evidence.', tone: 'amber', value: 'Review' },
              { title: 'Suspicious adjustments', detail: '3 manual adjustments require audit-visible review.', tone: 'rose', value: '3' },
            ]}
          />
        </Panel>
        <Panel title="Control Principles" description="Financial integrity rules embedded in the workstation.">
          <div className="grid gap-2">
            {integrityPrinciples.slice(4).map((principle) => (
              <div key={principle} className="rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-xs font-black text-slate-800">
                {principle}
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </WorkspaceShell>
  );
}

function CashierSessionOversightWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Cashier Accountability Control"
      title="Cashier Session Oversight"
      description="Cashier-by-cashier review of shift collections, receipt counts, declared cash, expected cash, variance, open/closed status, and supervisor review."
    >
      <MetricGrid
        metrics={[
          { label: 'Cashier Sessions', value: '5', detail: '4 general points + pharmacy', tone: 'cyan' },
          { label: 'Matched Sessions', value: '2', detail: 'Eligible for close posture', tone: 'emerald' },
          { label: 'Pending Closures', value: '2', detail: 'Awaiting close evidence', tone: 'amber' },
          { label: 'Critical Variance', value: '1', detail: 'A&E cashier point', tone: 'rose' },
        ]}
      />
      <Panel title="Cashier Session Matrix" description="Accountant control matrix, not a cashier payment screen.">
        <CashierSessionMatrix />
      </Panel>
      <Panel title="Cashier Variance Heat Indicator" description="Compact variance movement preview for accountant review priority.">
        <div className="grid gap-3 md:grid-cols-5">
          {cashierSessions.map((session) => {
            const heat = session.tone === 'rose' ? 88 : session.tone === 'amber' ? 58 : 18;
            return (
              <article key={`${session.cashier}-heat`} className="rounded-2xl border border-slate-300 bg-white p-3 shadow-sm">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-black text-slate-950">{session.cashier}</p>
                  <Badge tone={session.tone}>{session.variance}</Badge>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
                  <div className={cx('h-full rounded-full', fillClass(session.tone))} style={{ width: `${heat}%` }} />
                </div>
                <p className="mt-2 text-[11px] font-semibold text-slate-500">{session.desk}</p>
              </article>
            );
          })}
        </div>
      </Panel>
    </WorkspaceShell>
  );
}

function RevenueReconciliationWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Reconciliation Intelligence"
      title="Revenue Reconciliation Intelligence"
      description="Guided reconciliation of total collections, matched receipts, settlement evidence, cashier variance, department alignment, and risk signals."
      action={<Badge tone="rose">No clean close yet</Badge>}
    >
      <MetricGrid metrics={reconciliationMetrics} />
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Reconciliation Source Matrix" description="Expected values compared against matched receipt and settlement evidence.">
          <ReconciliationMatrix />
        </Panel>
        <Panel title="Guided Reconciliation Review" description="Demo-only guidance for accountant reconciliation sequence.">
          <div className="space-y-3">
            {[
              'Verify unmatched receipts',
              'Review cashier variances',
              'Compare settlement evidence',
              'Review suspicious adjustments',
              'Approve reconciliation posture',
            ].map((step, index) => (
              <div key={step} className="flex items-center gap-3 rounded-xl border border-slate-300 bg-slate-50 px-3 py-2.5">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 text-xs font-black text-white">{index + 1}</span>
                <p className="text-sm font-black text-slate-900">{step}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {['View Variance Details', 'Review Unmatched Receipts', 'Export Reconciliation Brief', 'Mark for CMD Visibility'].map((label) => (
              <button key={label} type="button" className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-left text-xs font-black text-slate-800 shadow-sm">
                {label}
              </button>
            ))}
          </div>
        </Panel>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Payment Method Reconciliation" description="POS, transfer, and cash matching status.">
          <div className="mb-3">
            <DistributionStrip items={paymentDistribution} />
          </div>
          <StatusRows
            rows={[
              { title: 'POS expected ₦3.62M', detail: 'Matched ₦3.60M · variance ₦20K', tone: 'amber', value: 'Review' },
              { title: 'Bank transfer expected ₦2.88M', detail: 'Matched ₦2.88M · 4 delayed references', tone: 'emerald', value: 'Matched' },
              { title: 'Cash expected ₦1.92M', detail: 'Matched ₦1.83M · variance ₦90K', tone: 'rose', value: 'Blocked' },
            ]}
          />
        </Panel>
        <Panel title="Reconciliation Timeline" description="Immutable control timeline preview.">
          <StatusRows
            rows={[
              { title: '11:02 AM — Pharmacy reconciled', detail: 'Pharmacy receipts matched except dedicated cashier variance.', tone: 'amber', value: 'Review' },
              { title: '11:15 AM — Transfer mismatch detected', detail: 'Bank reference evidence pending for four transfers.', tone: 'amber', value: 'Pending' },
              { title: '11:48 AM — Cashier variance escalated', detail: 'A&E variance crossed CMD visibility threshold.', tone: 'rose', value: 'Critical' },
              { title: '12:02 PM — Settlement evidence verified', detail: 'Radiology transfer reference matched.', tone: 'emerald', value: 'Verified' },
            ]}
          />
        </Panel>
      </div>
    </WorkspaceShell>
  );
}

function PaymentVerificationWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Transaction Verification Desk"
      title="Payment Verification"
      description="Verification of POS, Bank Transfer, Cash, and references against posted receipts and invoices."
    >
      <FilterPanel searchPlaceholder="Search receipt, MRN, reference, patient, or cashier" />
      <Panel title="Payment Verification Register" description="Compact verification rows prepared for future backend pagination.">
        <TransactionVerificationRows />
      </Panel>
    </WorkspaceShell>
  );
}

function RefundGovernanceWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="High-Risk Approval Zone"
      title="Refund & Reversal Governance"
      description="Controlled approval/rejection preview for refunds and payment reversals. Actions are visual only in this frontend demonstration."
      action={<Badge tone="rose">Dual authorization may apply</Badge>}
    >
      <MetricGrid
        metrics={[
          { label: 'Refund Exposure', value: '₦86K', detail: 'Pending sensitive exception value', tone: 'rose' },
          { label: 'Pending Reversals', value: '2', detail: 'Requires authority and linked correction', tone: 'amber' },
          { label: 'High-Value Requests', value: '1', detail: 'CMD/Admin visibility required', tone: 'rose' },
          { label: 'Secondary Approval', value: '2', detail: 'Dual authorization queue', tone: 'indigo' },
        ]}
      />
      <Panel title="Controlled Approval Queue" description="Strict review queue with no casual approval language.">
        <div className="grid gap-3">
          {refundRequests.map((request) => (
            <article key={`${request.type}-${request.receipt}`} className={cx('rounded-2xl border p-4 shadow-sm', surfaceClass(request.tone))}>
              <div className="grid gap-3 xl:grid-cols-[0.8fr_1fr_0.65fr_1fr_auto] xl:items-center">
                <div>
                  <p className="text-sm font-black text-slate-950">{request.type}</p>
                  <p className="text-xs text-slate-500">{request.receipt}</p>
                </div>
                <div>
                  <p className="font-black text-slate-950">{request.patient}</p>
                  <p className="text-xs text-slate-600">Requested by {request.requestedBy}</p>
                </div>
                <p className="text-lg font-black text-slate-950">{request.amount}</p>
                <p className="text-sm leading-5 text-slate-700">{request.reason}</p>
                <div className="flex flex-wrap gap-2 xl:justify-end">
                  <Badge tone={request.tone}>{request.risk}</Badge>
                  <Badge tone="indigo">{request.status}</Badge>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {['Review Request', 'Require Secondary Approval', 'Mark for CMD Visibility'].map((label) => (
                  <button key={label} type="button" className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-black text-slate-800">
                    {label}
                  </button>
                ))}
              </div>
            </article>
          ))}
        </div>
      </Panel>
    </WorkspaceShell>
  );
}

function WaiverDiscountWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Financial Concession Governance"
      title="Waiver & Discount Review"
      description="Review of financial concessions, approval source, patient billing impact, justification, and policy compliance state."
    >
      <Panel title="Waiver and Discount Review Queue" description="Concessions remain governed and audit-visible.">
        <div className="grid gap-3 xl:grid-cols-3">
          {waiverRequests.map((request) => (
            <article key={`${request.patient}-${request.amount}`} className={cx('rounded-2xl border p-4 shadow-sm', surfaceClass(request.tone))}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-black text-slate-950">{request.patient}</p>
                  <p className="text-xs text-slate-500">MRN {request.mrn}</p>
                </div>
                <Badge tone={request.tone}>{request.type}</Badge>
              </div>
              <p className="mt-3 text-2xl font-black text-slate-950">{request.amount}</p>
              <p className="mt-2 text-sm leading-5 text-slate-700">{request.justification}</p>
              <div className="mt-3 space-y-1 text-xs font-semibold text-slate-600">
                <p>Approval source: {request.source}</p>
                <p>Policy state: {request.policy}</p>
              </div>
            </article>
          ))}
        </div>
      </Panel>
    </WorkspaceShell>
  );
}

function OutstandingBillsWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Unpaid Balance Governance"
      title="Outstanding Bills Control"
      description="Visibility into unpaid balances, discharge clearance holds, inpatient pending bills, department debt exposure, and aging risk."
    >
      <MetricGrid
        metrics={[
          { label: 'Total Outstanding', value: '₦1.18M', detail: 'Current unpaid exposure', tone: 'amber' },
          { label: 'Inpatient Pending', value: '₦620K', detail: 'Running inpatient balances', tone: 'rose' },
          { label: 'Discharge Holds', value: '4', detail: 'Financial clearance pending', tone: 'rose' },
          { label: 'Pharmacy Pending', value: '₦180K', detail: 'Medication bills unpaid', tone: 'amber' },
          { label: 'Lab Pending', value: '₦96K', detail: 'Investigation bills unpaid', tone: 'amber' },
          { label: 'Aging Exposure', value: '₦420K', detail: 'Older than 5 days', tone: 'rose' },
        ]}
      />
      <Panel title="Patient Outstanding Preview" description="Patient debt exposure and discharge clearance signals.">
        <div className="grid gap-3">
          {outstandingRows.map((row) => (
            <article key={row.mrn} className="grid gap-3 rounded-2xl border border-slate-300 bg-white p-3 shadow-sm xl:grid-cols-[1fr_0.8fr_0.65fr_0.55fr_auto] xl:items-center">
              <div>
                <p className="font-black text-slate-950">{row.patient}</p>
                <p className="text-xs text-slate-500">MRN {row.mrn}</p>
              </div>
              <p className="font-bold text-slate-700">{row.department}</p>
              <p className="text-lg font-black text-slate-950">{row.amount}</p>
              <p className="text-sm font-semibold text-slate-600">{row.aging}</p>
              <Badge tone={row.tone}>{row.status}</Badge>
            </article>
          ))}
        </div>
      </Panel>
    </WorkspaceShell>
  );
}

function DepartmentRevenueWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Department Revenue Control"
      title="Department Revenue Control"
      description="Department/service-line revenue control, method split, variance posture, and traceability state."
    >
      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel title="Revenue Leaderboard" description="Ranked department revenue contribution.">
          <div className="space-y-3">
            {departmentRevenue.map((row, index) => (
              <div key={row.department}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="font-black text-slate-900">
                    {index + 1}. {row.department}
                  </span>
                  <span className="font-black text-slate-950">{row.revenue}</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-slate-200">
                  <div className="h-full rounded-full bg-cyan-600" style={{ width: `${row.share}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Department Control Cards" description="Revenue, transactions, method split, variance, and traceability posture.">
          <div className="grid gap-3 xl:grid-cols-2">
            {departmentRevenue.map((row) => (
              <article key={row.department} className={cx('rounded-2xl border p-4 shadow-sm', surfaceClass(row.tone))}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-black text-slate-950">{row.department}</p>
                    <p className="text-xs text-slate-500">{row.transactions} transactions</p>
                  </div>
                  <Badge tone={row.tone}>{row.status}</Badge>
                </div>
                <p className="mt-3 text-2xl font-black text-slate-950">{row.revenue}</p>
                <p className="mt-2 text-xs font-semibold text-slate-600">{row.split}</p>
                <p className="mt-1 text-xs font-semibold text-slate-600">Variance: {row.variance}</p>
                <div className="mt-3 rounded-xl border border-white/80 bg-white/70 p-2">
                  <MicroBars values={[22, 38, 34, 48, row.share + 42, 58, 64, row.share + 54]} tone={row.tone} />
                </div>
              </article>
            ))}
          </div>
        </Panel>
      </div>
      <Panel title="Department Posture Summary">
        <div className="grid gap-3 md:grid-cols-3">
          {[
            ['Best Performing', 'Pharmacy · ₦2.14M', 'cyan' as Tone],
            ['Most Stable', 'Laboratory / Radiology / Maternity', 'emerald' as Tone],
            ['Needs Review', 'A&E critical variance', 'rose' as Tone],
          ].map(([title, detail, tone]) => (
            <div key={title} className={cx('rounded-2xl border p-4 shadow-sm', surfaceClass(tone as Tone))}>
              <p className="text-xs font-black uppercase tracking-[0.13em] text-slate-500">{title}</p>
              <p className="mt-2 text-lg font-black text-slate-950">{detail}</p>
            </div>
          ))}
        </div>
      </Panel>
    </WorkspaceShell>
  );
}

function DailyCloseWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Financial Lockdown Workflow"
      title="Daily Close & Handover"
      description="End-of-day close checklist, close readiness, handover summary, accountant notes, and critical exception lock state."
      action={<Badge tone="rose">Close blocked</Badge>}
    >
      <MetricGrid
        metrics={[
          { label: 'Close Readiness', value: 'Blocked', detail: 'Critical variance unresolved', tone: 'rose' },
          { label: 'Cashier Sessions Reviewed', value: '4 / 5', detail: 'One session needs accountant review', tone: 'amber' },
          { label: 'Collections', value: '₦8.42M', detail: 'Daily collection posture', tone: 'cyan' },
          { label: 'Pending Exceptions', value: '11', detail: 'Must be listed before close', tone: 'amber' },
        ]}
      />
      <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
        <Panel title="Daily Close Checklist" description="No clean close with unresolved critical variance.">
          <div className="space-y-2">
            {closeChecklist.map((item) => (
              <div key={item.item} className="flex items-center justify-between gap-3 rounded-xl border border-slate-300 bg-white px-3 py-2.5 shadow-sm">
                <div>
                  <p className="font-black text-slate-950">{item.item}</p>
                  <p className="text-xs text-slate-500">{item.state}</p>
                </div>
                <Badge tone={item.tone}>{item.done ? 'Complete' : 'Pending'}</Badge>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Handover Summary" description="Close state preserved for audit and CMD visibility.">
          <div className="space-y-3">
            {[
              ['Collections', '₦8.42M'],
              ['Variances', '₦110K unresolved'],
              ['Pending Exceptions', '11'],
              ['Accountant Notes', 'Draft required before close approval'],
              ['Close Status', 'Blocked / Pending Review'],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between rounded-xl border border-slate-300 bg-slate-50 px-3 py-2.5">
                <span className="text-sm font-semibold text-slate-600">{label}</span>
                <span className="font-black text-slate-950">{value}</span>
              </div>
            ))}
          </div>
          <textarea
            className="mt-4 min-h-28 w-full rounded-2xl border border-slate-300 bg-white p-4 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-cyan-500 focus:ring-4 focus:ring-cyan-100"
            placeholder="Accountant close notes preview..."
          />
        </Panel>
      </div>
    </WorkspaceShell>
  );
}

function FinancialExceptionsWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Risk and Anomaly Control"
      title="Financial Exceptions"
      description="Duplicate payments, voided receipts, delayed settlements, repeated variance, unmatched transfers, and suspicious adjustments."
    >
      <div className="grid gap-3 xl:grid-cols-3">
        {exceptionRows.map((row) => (
          <article key={row.category} className={cx('rounded-2xl border p-4 shadow-sm', surfaceClass(row.tone))}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-black text-slate-950">{row.category}</p>
                <p className="mt-1 text-sm leading-5 text-slate-600">{row.detail}</p>
              </div>
              <p className="text-2xl font-black text-slate-950">{row.count}</p>
            </div>
            <div className="mt-3">
              <Badge tone={row.tone}>{row.severity}</Badge>
            </div>
          </article>
        ))}
      </div>
    </WorkspaceShell>
  );
}

function AuditReportsWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Immutable Financial Trace"
      title="Audit Trail & Reports"
      description="Accountant-facing audit timeline, actor trace rows, receipt audit reports, reconciliation reports, close reports, and export readiness."
    >
      <div className="grid gap-4 xl:grid-cols-[1fr_0.85fr]">
        <Panel title="Financial Activity Timeline" description="Immutable actor, event, reference, and risk trace preview.">
          <div className="space-y-3">
            {auditEvents.map((event) => (
              <article key={`${event.time}-${event.event}`} className="rounded-2xl border border-slate-300 bg-white p-3 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-black text-slate-950">{event.time} — {event.event}</p>
                    <p className="text-xs font-semibold text-slate-500">Actor: {event.actor}</p>
                    <p className="mt-1 text-sm leading-5 text-slate-600">{event.detail}</p>
                  </div>
                  <Badge tone={event.tone}>Trace</Badge>
                </div>
              </article>
            ))}
          </div>
        </Panel>
        <Panel title="Export-Ready Reports" description="Visual-only report export readiness.">
          <div className="space-y-3">
            {reports.map((report) => (
              <article key={report.title} className={cx('rounded-2xl border p-4 shadow-sm', surfaceClass(report.tone))}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-black text-slate-950">{report.title}</p>
                    <p className="mt-1 text-sm leading-5 text-slate-600">{report.detail}</p>
                  </div>
                  <Badge tone={report.tone}>{report.state}</Badge>
                </div>
              </article>
            ))}
          </div>
        </Panel>
      </div>
    </WorkspaceShell>
  );
}

function FinancialControlPreferencesWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Financial Workstation Configuration"
      title="Financial Control Preferences"
      description="Accountant profile, approval preferences, report preferences, workstation controls, variance threshold preview, and notification preferences."
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {[
          ['Accountant Profile', 'Amina Yusuf · Senior Accountant · Finance Operations Unit'],
          ['Approval Preferences', 'Secondary authorization enabled for high-risk financial actions'],
          ['Report Preferences', 'Daily close, reconciliation, refund/reversal, and department revenue reports'],
          ['Workstation Controls', 'Financial control mode · no cashier collection workflow'],
          ['Variance Threshold Preview', '₦0 matched · ₦1-₦5K minor · above ₦50K critical'],
          ['Notification Preferences', 'CMD/Admin visibility for critical variance and suspicious adjustments'],
        ].map(([title, detail]) => (
          <Panel key={title} title={title}>
            <p className="text-sm leading-6 text-slate-600">{detail}</p>
          </Panel>
        ))}
      </div>
    </WorkspaceShell>
  );
}

function WorkspaceContent({ active }: { active: Workspace }) {
  if (active === 'overview') return <FinancialControlOverviewWorkspace />;
  if (active === 'cashiers') return <CashierSessionOversightWorkspace />;
  if (active === 'reconciliation') return <RevenueReconciliationWorkspace />;
  if (active === 'verification') return <PaymentVerificationWorkspace />;
  if (active === 'refunds') return <RefundGovernanceWorkspace />;
  if (active === 'waivers') return <WaiverDiscountWorkspace />;
  if (active === 'outstanding') return <OutstandingBillsWorkspace />;
  if (active === 'departments') return <DepartmentRevenueWorkspace />;
  if (active === 'close') return <DailyCloseWorkspace />;
  if (active === 'exceptions') return <FinancialExceptionsWorkspace />;
  if (active === 'audit') return <AuditReportsWorkspace />;
  return <FinancialControlPreferencesWorkspace />;
}

export default function AccountantPage() {
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace>('overview');
  const activeLabel = navItems.find((item) => item.key === activeWorkspace)?.label ?? 'Financial Control Overview';

  return (
    <div className="min-h-screen rounded-3xl border border-slate-700/50 bg-[linear-gradient(rgba(15,23,42,0.045)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.035)_1px,transparent_1px),radial-gradient(circle_at_top_left,rgba(14,165,233,0.18),transparent_28%),linear-gradient(135deg,#0f172a_0%,#1e293b_34%,#e2e8f0_34%,#f1f5f9_100%)] bg-[length:32px_32px,32px_32px,auto,auto] p-3 text-slate-950 shadow-[0_30px_90px_-60px_rgba(15,23,42,0.9)] sm:p-4 lg:p-5">
      <OperationalFinanceShell activeLabel={activeLabel} />
      <div className="grid gap-4 xl:grid-cols-[282px_minmax(0,1fr)]">
        <aside className="xl:sticky xl:top-6 xl:h-[calc(100vh-3rem)]">
          <div className="flex h-full flex-col rounded-2xl border border-slate-700/35 bg-slate-50/95 p-2.5 shadow-[0_22px_60px_-45px_rgba(15,23,42,0.9)] backdrop-blur">
            <AccountantIdentityBadge />
            <nav className="mt-2 flex-1 space-y-1 overflow-y-auto pr-1">
              {navItems.map((item) => {
                const isActive = item.key === activeWorkspace;
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setActiveWorkspace(item.key)}
                    className={cx(
                      'w-full rounded-xl border px-2.5 py-2 text-left transition duration-200',
                      isActive
                        ? 'border-cyan-300 bg-cyan-50 shadow-sm shadow-cyan-100'
                        : 'border-transparent bg-slate-50 hover:border-slate-300 hover:bg-slate-100'
                    )}
                  >
                    <p className={cx('text-[13px] font-black', isActive ? 'text-slate-950' : 'text-slate-800')}>{item.label}</p>
                    <p className="mt-0.5 text-[10px] leading-4 text-slate-500">{item.description}</p>
                  </button>
                );
              })}
            </nav>
          </div>
        </aside>
        <main className="min-w-0">
          <WorkspaceContent active={activeWorkspace} />
        </main>
      </div>
    </div>
  );
}
