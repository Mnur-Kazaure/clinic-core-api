'use client';

import { useState, type ReactNode } from 'react';

type CashierWorkspace =
  | 'overview'
  | 'pending'
  | 'lookup'
  | 'process'
  | 'receipts'
  | 'history'
  | 'shift'
  | 'till'
  | 'exceptions'
  | 'settings';

type Tone = 'blue' | 'cyan' | 'emerald' | 'amber' | 'rose' | 'slate';

type SummaryCard = {
  label: string;
  value: string;
  detail: string;
  tone: Tone;
};

type PendingPayment = {
  patient: string;
  mrn: string;
  invoice: string;
  department: string;
  serviceLine: string;
  amount: string;
  requestedBy: string;
  priority: 'Routine' | 'Priority' | 'Urgent';
  status: 'Awaiting Payment' | 'Ready for Collection' | 'Supervisor Review';
};

type Receipt = {
  receiptNo: string;
  patient: string;
  mrn: string;
  amount: string;
  method: 'POS' | 'Bank Transfer' | 'Cash' | 'Split';
  cashier: string;
  time: string;
  status: 'Issued' | 'Verified' | 'Reprint Ready' | 'Voided';
};

type Transaction = Receipt & {
  department: string;
  purpose: string;
  reference: string;
};

const navItems: Array<{
  key: CashierWorkspace;
  label: string;
  description: string;
  priority: 'Highest' | 'High' | 'Low';
}> = [
  {
    key: 'overview',
    label: 'Collection Overview',
    description: 'Daily collection posture',
    priority: 'Highest',
  },
  {
    key: 'pending',
    label: 'Pending Payments',
    description: 'Bills awaiting cashier action',
    priority: 'Highest',
  },
  {
    key: 'lookup',
    label: 'Patient Bill Lookup',
    description: 'Fast MRN, name, phone, visit, or invoice search',
    priority: 'Highest',
  },
  {
    key: 'process',
    label: 'Process Payment',
    description: 'Guided POS, transfer, cash, or split payment',
    priority: 'Highest',
  },
  {
    key: 'receipts',
    label: 'Receipt Center',
    description: 'Receipt generation, preview, search, and reprint',
    priority: 'Highest',
  },
  {
    key: 'history',
    label: 'Payment History',
    description: 'Cashier-visible transaction record',
    priority: 'High',
  },
  {
    key: 'shift',
    label: 'Shift Management',
    description: 'Open, active, close, handover, and review status',
    priority: 'Highest',
  },
  {
    key: 'till',
    label: 'Cash Drawer / Till Summary',
    description: 'Cash accountability and handover posture',
    priority: 'High',
  },
  {
    key: 'exceptions',
    label: 'Payment Exceptions',
    description: 'Failed, duplicate, unmatched, voided, and review items',
    priority: 'High',
  },
  {
    key: 'settings',
    label: 'Cashier Settings',
    description: 'Profile, desk, printer, and notifications',
    priority: 'Low',
  },
];

const overviewCards: SummaryCard[] = [
  {
    label: "Today's Collections",
    value: '₦1.85M',
    detail: 'A & E / Theater Pay Point collection total',
    tone: 'blue',
  },
  {
    label: 'Receipts Issued',
    value: '42',
    detail: 'Verified receipts generated today',
    tone: 'emerald',
  },
  {
    label: 'Pending Payments',
    value: '18',
    detail: 'Bills awaiting cashier processing',
    tone: 'amber',
  },
  {
    label: 'Active Shift Status',
    value: 'Open',
    detail: 'Shift opened at 07:45 AM',
    tone: 'cyan',
  },
];

const methodSplit = [
  { label: 'POS Collections', value: '₦820K', share: 44, tone: 'blue' as Tone },
  { label: 'Bank Transfer', value: '₦610K', share: 33, tone: 'cyan' as Tone },
  { label: 'Cash Collections', value: '₦420K', share: 23, tone: 'emerald' as Tone },
];

const pendingPayments: PendingPayment[] = [
  {
    patient: 'Abba Nura',
    mrn: '0000001-9',
    invoice: 'INV-2026-091',
    department: 'Pharmacy',
    serviceLine: 'Medication Dispensing',
    amount: '₦18,500',
    requestedBy: 'Dr. Nasir Ya’u',
    priority: 'Priority',
    status: 'Ready for Collection',
  },
  {
    patient: 'Muhammad Nura',
    mrn: '0000002-8',
    invoice: 'INV-2026-092',
    department: 'Laboratory',
    serviceLine: 'FBC + Malaria Test',
    amount: '₦7,500',
    requestedBy: 'Dr. Nasir Ya’u',
    priority: 'Routine',
    status: 'Awaiting Payment',
  },
  {
    patient: 'Sani Umar',
    mrn: '0000003-7',
    invoice: 'INV-2026-093',
    department: 'A&E',
    serviceLine: 'Emergency Service Charge',
    amount: '₦25,000',
    requestedBy: 'A&E Nurse Lead',
    priority: 'Urgent',
    status: 'Ready for Collection',
  },
  {
    patient: 'Fatima Kabir',
    mrn: '0000005-3',
    invoice: 'INV-2026-095',
    department: 'Radiology',
    serviceLine: 'Chest X-Ray',
    amount: '₦12,000',
    requestedBy: 'Dr. Aisha Musa',
    priority: 'Priority',
    status: 'Awaiting Payment',
  },
];

const receipts: Receipt[] = [
  {
    receiptNo: 'RCP-2026-00091',
    patient: 'Abba Nura',
    mrn: '0000001-9',
    amount: '₦18,500',
    method: 'POS',
    cashier: 'Aisha Bello',
    time: '09:42 AM',
    status: 'Verified',
  },
  {
    receiptNo: 'RCP-2026-00092',
    patient: 'Muhammad Nura',
    mrn: '0000002-8',
    amount: '₦7,500',
    method: 'Cash',
    cashier: 'Aisha Bello',
    time: '10:08 AM',
    status: 'Issued',
  },
  {
    receiptNo: 'RCP-2026-00093',
    patient: 'Sani Umar',
    mrn: '0000003-7',
    amount: '₦25,000',
    method: 'Bank Transfer',
    cashier: 'Aisha Bello',
    time: '10:31 AM',
    status: 'Verified',
  },
  {
    receiptNo: 'RCP-2026-00094',
    patient: 'Maryam Aliyu',
    mrn: '0000004-6',
    amount: '₦3,000',
    method: 'POS',
    cashier: 'Aisha Bello',
    time: '11:12 AM',
    status: 'Reprint Ready',
  },
];

const transactions: Transaction[] = [
  {
    ...receipts[0],
    department: 'Pharmacy',
    purpose: 'Ceftriaxone injection',
    reference: 'POS-A92F',
  },
  {
    ...receipts[1],
    department: 'Laboratory',
    purpose: 'FBC + Malaria test',
    reference: 'CASH-1182',
  },
  {
    ...receipts[2],
    department: 'A&E',
    purpose: 'Emergency service charge',
    reference: 'TRF-8841',
  },
  {
    ...receipts[3],
    department: 'GOPD',
    purpose: 'Consultation fee',
    reference: 'POS-B772',
  },
];

const billItems = [
  { item: 'Emergency service charge', department: 'A&E', amount: '₦15,000' },
  { item: 'Procedure consumables', department: 'A&E', amount: '₦6,500' },
  { item: 'Observation bed fee', department: 'A&E', amount: '₦3,500' },
];

const exceptionRows = [
  {
    title: 'Unmatched bank transfer',
    detail: 'TRF-8849 requires payment reference confirmation before receipt release.',
    count: '2',
    tone: 'amber' as Tone,
  },
  {
    title: 'Duplicate payment alert',
    detail: 'Possible duplicate POS attempt for MRN 0000007-1.',
    count: '1',
    tone: 'rose' as Tone,
  },
  {
    title: 'Voided receipt visibility',
    detail: 'Cashier can view and flag, but approval belongs to Accountant/Admin.',
    count: '1',
    tone: 'slate' as Tone,
  },
  {
    title: 'Pending supervisor review',
    detail: 'Payment reversal requests are locked for supervisor decision.',
    count: '3',
    tone: 'amber' as Tone,
  },
];

const shiftSteps = [
  'Open Shift',
  'Active Shift',
  'Close Shift',
  'Shift Handover',
  'Shift Summary',
  'Supervisor Review Status',
];

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function toneBadge(tone: Tone) {
  const tones: Record<Tone, string> = {
    blue: 'border-blue-200 bg-blue-50 text-blue-700',
    cyan: 'border-cyan-200 bg-cyan-50 text-cyan-700',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    rose: 'border-rose-200 bg-rose-50 text-rose-700',
    slate: 'border-slate-200 bg-slate-100 text-slate-700',
  };
  return tones[tone];
}

function toneSurface(tone: Tone) {
  const tones: Record<Tone, string> = {
    blue: 'border-blue-300 bg-blue-50/90 shadow-blue-100',
    cyan: 'border-cyan-300 bg-cyan-50/90 shadow-cyan-100',
    emerald: 'border-emerald-300 bg-emerald-50/90 shadow-emerald-100',
    amber: 'border-amber-300 bg-amber-50/90 shadow-amber-100',
    rose: 'border-rose-300 bg-rose-50/90 shadow-rose-100',
    slate: 'border-slate-300 bg-slate-50 shadow-slate-200',
  };
  return tones[tone];
}

function methodTone(method: string): Tone {
  if (method === 'POS') return 'blue';
  if (method === 'Bank Transfer') return 'cyan';
  if (method === 'Cash') return 'emerald';
  return 'slate';
}

function methodActiveClass(method: string) {
  if (method === 'POS') return 'border-blue-600 bg-blue-700 text-white shadow-md shadow-blue-200';
  if (method === 'Bank Transfer') return 'border-cyan-600 bg-cyan-700 text-white shadow-md shadow-cyan-200';
  if (method === 'Cash') return 'border-emerald-600 bg-emerald-700 text-white shadow-md shadow-emerald-200';
  return 'border-slate-700 bg-slate-800 text-white shadow-md shadow-slate-200';
}

function priorityTone(priority: PendingPayment['priority']) {
  if (priority === 'Urgent') return 'rose';
  if (priority === 'Priority') return 'amber';
  return 'slate';
}

function statusTone(status: string): Tone {
  if (status.includes('Verified') || status.includes('Issued') || status.includes('Ready')) return 'emerald';
  if (status.includes('Review') || status.includes('Awaiting') || status.includes('Reprint')) return 'amber';
  if (status.includes('Void') || status.includes('Failed')) return 'rose';
  return 'slate';
}

function WorkspaceShell({
  title,
  eyebrow,
  description,
  children,
  action,
}: {
  title: string;
  eyebrow: string;
  description: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-blue-200 bg-white p-4 shadow-sm shadow-blue-100/80 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-blue-600">{eyebrow}</p>
            <h1 className="mt-2 text-2xl font-black tracking-tight text-slate-950 sm:text-3xl lg:text-4xl">
              {title}
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700">
              Frontend demonstration workspace
            </span>
            {action}
          </div>
        </div>
      </div>
      {children}
    </section>
  );
}

function SummaryCards({ cards }: { cards: SummaryCard[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <article
          key={card.label}
          className={cx(
            'rounded-2xl border p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md',
            toneSurface(card.tone)
          )}
        >
          <p className="text-[11px] font-bold uppercase tracking-[0.13em] text-slate-500">{card.label}</p>
          <p className="mt-2 text-2xl font-black tracking-tight text-slate-950">{card.value}</p>
          <p className="mt-1.5 text-sm leading-5 text-slate-600">{card.detail}</p>
        </article>
      ))}
    </div>
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
    <section className="rounded-2xl border border-slate-300 bg-white p-4 shadow-sm shadow-slate-200/70">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-black tracking-tight text-slate-950">{title}</h2>
          {description ? <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function Badge({ children, tone = 'slate' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span className={cx('inline-flex rounded-full border px-2.5 py-1 text-xs font-bold', toneBadge(tone))}>
      {children}
    </span>
  );
}

function ShiftAccountabilityStrip() {
  const items = [
    ['Cashier', 'Aisha Bello'],
    ['Desk', 'A & E / Theater Pay Point'],
    ['Shift Opened', '07:45 AM'],
    ['Supervisor', 'Finance Lead'],
    ['Shift Status', 'Open'],
  ];

  return (
    <div className="grid gap-2 rounded-2xl border border-blue-200 bg-white px-3 py-3 shadow-sm shadow-blue-100/80 sm:grid-cols-2 xl:grid-cols-5">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
          <p className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-500">{label}</p>
          <p className="mt-1 text-sm font-black text-slate-950">{value}</p>
        </div>
      ))}
    </div>
  );
}

function Field({ label, placeholder }: { label: string; placeholder: string }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <input
        className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
        placeholder={placeholder}
      />
    </label>
  );
}

function SelectField({ label, options }: { label: string; options: string[] }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <select
        defaultValue={options[0]}
        className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
      >
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

function MethodSplit() {
  return (
    <Panel title="Payment Method Split" description="Authorized collection channels for this cashier desk.">
      <div className="space-y-3">
        {methodSplit.map((method) => (
          <div key={method.label}>
            <div className="mb-2 flex items-center justify-between gap-3 text-sm">
              <span className="font-bold text-slate-800">{method.label}</span>
              <span className="font-black text-slate-950">{method.value}</span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-slate-100 ring-1 ring-slate-200">
              <div
                className={cx(
                  'h-full rounded-full',
                  method.tone === 'blue' && 'bg-blue-600',
                  method.tone === 'cyan' && 'bg-cyan-500',
                  method.tone === 'emerald' && 'bg-emerald-500'
                )}
                style={{ width: `${method.share}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function RecentTransactions({ compact = false }: { compact?: boolean }) {
  return (
    <div className="space-y-3">
      {transactions.slice(0, compact ? 3 : transactions.length).map((transaction) => (
        <article
          key={transaction.receiptNo}
          className="grid gap-3 rounded-2xl border border-slate-300 bg-white p-3 shadow-sm transition hover:border-blue-300 hover:shadow-md lg:grid-cols-[1.25fr_1fr_auto]"
        >
          <div className="min-w-0">
            <p className="font-black text-slate-950">{transaction.patient}</p>
            <p className="mt-1 text-sm text-slate-600">
              MRN {transaction.mrn} · {transaction.department} · {transaction.purpose}
            </p>
            <p className="mt-1 text-xs font-semibold text-slate-500">
              {transaction.receiptNo} · {transaction.reference}
            </p>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Payment</p>
            <p className="mt-1 font-black text-slate-950">
              {transaction.amount} · {transaction.method}
            </p>
            <p className="mt-1 text-sm text-slate-600">Time: {transaction.time}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 lg:justify-end">
            <Badge tone={methodTone(transaction.method)}>{transaction.method}</Badge>
            <Badge tone={statusTone(transaction.status)}>{transaction.status}</Badge>
            <Badge tone="blue">Receipt trace</Badge>
          </div>
        </article>
      ))}
    </div>
  );
}

function CompactTransactionRows() {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-300 bg-white shadow-sm shadow-slate-200/70">
      <div className="hidden grid-cols-[minmax(160px,1.1fr)_minmax(190px,1fr)_minmax(140px,0.8fr)_minmax(120px,0.65fr)_minmax(90px,0.5fr)_auto] gap-3 border-b border-slate-300 bg-slate-100 px-4 py-2.5 text-[11px] font-black uppercase tracking-[0.13em] text-slate-500 lg:grid">
        <span>Patient</span>
        <span>Department / Service</span>
        <span>Receipt</span>
        <span>Amount</span>
        <span>Time</span>
        <span className="text-right">Trace</span>
      </div>
      <div className="divide-y divide-slate-200">
        {transactions.map((transaction) => (
          <article
            key={transaction.receiptNo}
            className="grid gap-3 px-4 py-3 transition hover:bg-blue-50/60 lg:grid-cols-[minmax(160px,1.1fr)_minmax(190px,1fr)_minmax(140px,0.8fr)_minmax(120px,0.65fr)_minmax(90px,0.5fr)_auto] lg:items-center"
          >
            <div className="min-w-0">
              <p className="font-black text-slate-950">{transaction.patient}</p>
              <p className="mt-0.5 text-xs font-semibold text-slate-500">MRN {transaction.mrn}</p>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-slate-900">{transaction.department}</p>
              <p className="mt-0.5 text-xs leading-5 text-slate-500">{transaction.purpose}</p>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-black text-slate-950">{transaction.receiptNo}</p>
              <p className="mt-0.5 text-xs text-slate-500">{transaction.reference}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2 lg:block">
              <p className="font-black text-slate-950">{transaction.amount}</p>
              <div className="mt-0 lg:mt-1">
                <Badge tone={methodTone(transaction.method)}>{transaction.method}</Badge>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 lg:block">
              <p className="text-sm font-bold text-slate-700">{transaction.time}</p>
              <div className="mt-0 lg:mt-1">
                <Badge tone={statusTone(transaction.status)}>{transaction.status}</Badge>
              </div>
            </div>
            <div className="lg:text-right">
              <button
                type="button"
                className="rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-black text-blue-700 transition hover:border-blue-300 hover:bg-blue-100"
              >
                Receipt trace
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function FilterSurface({
  searchPlaceholder,
  children,
}: {
  searchPlaceholder: string;
  children: ReactNode;
}) {
  return (
    <Panel title="Filters & Search" description="UI-ready filters prepared for future cashier payment APIs.">
      <div className="grid gap-3 lg:grid-cols-[minmax(260px,1.4fr)_repeat(4,minmax(150px,1fr))]">
        <Field label="Search" placeholder={searchPlaceholder} />
        {children}
      </div>
    </Panel>
  );
}

function PendingPaymentRows() {
  return (
    <div className="space-y-3">
      {pendingPayments.map((payment) => (
        <article
          key={payment.invoice}
          className="grid gap-3 rounded-2xl border border-slate-300 bg-white p-3 shadow-sm transition hover:border-blue-300 hover:shadow-md xl:grid-cols-[1.2fr_1fr_0.9fr_auto]"
        >
          <div className="min-w-0">
            <p className="font-black text-slate-950">{payment.patient}</p>
            <p className="mt-1 text-sm font-semibold text-slate-600">MRN {payment.mrn}</p>
            <p className="mt-1 text-xs text-slate-500">{payment.invoice}</p>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Bill Source</p>
            <p className="mt-1 font-bold text-slate-900">{payment.department}</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">{payment.serviceLine}</p>
            <p className="mt-1 text-xs text-slate-500">Requested by {payment.requestedBy}</p>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Payment State</p>
            <p className="mt-1 text-2xl font-black text-slate-950">{payment.amount}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge tone={priorityTone(payment.priority)}>{payment.priority}</Badge>
              <Badge tone={statusTone(payment.status)}>{payment.status}</Badge>
            </div>
          </div>
          <div className="flex items-center xl:justify-end">
            <button
              type="button"
              className="w-full rounded-xl bg-blue-700 px-4 py-3 text-sm font-black text-white shadow-sm shadow-blue-200 transition hover:bg-blue-800 xl:w-auto"
            >
              Process Payment
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}

function CollectionOverviewWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Revenue Collection Desk"
      title="Collection Overview"
      description="Fast daily collection posture for the cashier desk with receipt-first traceability, pending payment visibility, and safe quick actions."
      action={<Badge tone="emerald">Shift Open</Badge>}
    >
      <SummaryCards cards={overviewCards} />
      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <MethodSplit />
        <Panel title="Recent Transactions" description="Latest cashier-visible receipt activity.">
          <RecentTransactions compact />
        </Panel>
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Quick Actions" description="Demo-only action surfaces for fast cashier flow.">
          <div className="grid gap-3 sm:grid-cols-2">
            {['Lookup Patient Bill', 'Process Payment', 'Generate Receipt', 'Review Pending Payments'].map((action) => (
              <button
                key={action}
                type="button"
                className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-left text-sm font-black text-blue-800 transition hover:border-blue-300 hover:bg-blue-100"
              >
                {action}
              </button>
            ))}
          </div>
        </Panel>
        <Panel title="Shift Status" description="Cashier desk accountability snapshot.">
          <div className="rounded-2xl border border-emerald-300 bg-emerald-50 p-4 shadow-sm shadow-emerald-100">
            <p className="text-sm font-bold text-emerald-700">Aisha Bello · A & E / Theater Pay Point</p>
            <p className="mt-2 text-2xl font-black text-slate-950">₦1.85M</p>
            <p className="mt-1 text-sm text-slate-600">42 receipts issued · opened 07:45 AM</p>
          </div>
        </Panel>
      </div>
    </WorkspaceShell>
  );
}

function PendingPaymentsWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Payment Queue"
      title="Pending Payments"
      description="Operational cashier queue for bills awaiting payment by department, service line, priority, and payment state."
    >
      <FilterSurface searchPlaceholder="Search by patient name, MRN, invoice number, or department">
        <SelectField label="Department" options={['All Departments', 'OPD', 'Pharmacy', 'Laboratory', 'Radiology', 'A&E', 'Inpatient']} />
        <SelectField label="Service Line" options={['All Service Lines', 'Consultation', 'Medication', 'Lab Test', 'Imaging', 'Emergency']} />
        <SelectField label="Priority" options={['All Priorities', 'Routine', 'Priority', 'Urgent']} />
        <SelectField label="Payment Status" options={['All Status', 'Awaiting Payment', 'Ready for Collection', 'Supervisor Review']} />
      </FilterSurface>
      <Panel title="Pending Payment Queue" description="Bills are shown as safe cashier-ready cards, not raw database rows.">
        <PendingPaymentRows />
      </Panel>
    </WorkspaceShell>
  );
}

function PatientBillLookupWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Patient Bill Verification"
      title="Patient Bill Lookup"
      description="Fast patient and invoice lookup surface for validating active bills before payment collection."
    >
      <Panel title="Search Patient or Invoice" description="Frontend-ready search fields for future billing APIs.">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <Field label="MRN" placeholder="0000001-9" />
          <Field label="Patient Name" placeholder="Abba Nura" />
          <Field label="Phone Number" placeholder="08030001111" />
          <Field label="Visit ID" placeholder="VIS-2026-0041" />
          <Field label="Invoice Number" placeholder="INV-2026-091" />
        </div>
      </Panel>
      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel title="Patient Summary" description="Selected patient preview for cashier verification.">
          <div className="rounded-2xl border border-blue-300 bg-blue-50 p-4 shadow-sm shadow-blue-100">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-blue-700">Active Patient</p>
            <p className="mt-2 text-xl font-black text-slate-950">Abba Nura</p>
            <p className="mt-1 text-sm font-semibold text-slate-700">MRN 0000001-9 · 08030001111</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge tone="blue">Pharmacy bill active</Badge>
              <Badge tone="emerald">Ready for payment</Badge>
            </div>
          </div>
        </Panel>
        <Panel title="Active Bill Summary" description="Unpaid items and previous payment trace.">
          <div className="space-y-3">
            {[
              ['Ceftriaxone injection', 'Pharmacy', '₦12,500'],
              ['Dispensing fee', 'Pharmacy', '₦2,000'],
              ['Consumables', 'Pharmacy', '₦4,000'],
            ].map(([item, department, amount]) => (
              <div key={item} className="flex items-center justify-between gap-4 rounded-xl border border-slate-300 bg-white px-4 py-3 shadow-sm">
                <div>
                  <p className="font-bold text-slate-950">{item}</p>
                  <p className="text-sm text-slate-500">{department}</p>
                </div>
                <p className="font-black text-slate-950">{amount}</p>
              </div>
            ))}
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
              <p className="text-sm font-bold text-emerald-700">Payment readiness state: bill verified and ready for cashier collection.</p>
            </div>
          </div>
        </Panel>
      </div>
    </WorkspaceShell>
  );
}

function ProcessPaymentWorkspace() {
  const [method, setMethod] = useState<'POS' | 'Bank Transfer' | 'Cash' | 'Split Payment'>('POS');

  return (
    <WorkspaceShell
      eyebrow="Guided Payment Execution"
      title="Process Payment"
      description="Core cashier workspace for confirming a bill, validating payment method, and generating a traceable receipt."
      action={<Badge tone="amber">Demo buttons only</Badge>}
    >
      <div className="grid gap-4 xl:grid-cols-[1.08fr_0.92fr]">
        <div className="space-y-4">
          <Panel title="Selected Patient / Invoice" description="Cashier verifies patient and invoice before accepting payment.">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-blue-300 bg-blue-50 p-4 shadow-sm shadow-blue-100">
                <p className="text-xs font-bold uppercase text-blue-700">Patient</p>
                <p className="mt-2 text-xl font-black text-slate-950">Sani Umar</p>
                <p className="text-sm text-slate-600">MRN 0000003-7</p>
              </div>
              <div className="rounded-2xl border border-slate-300 bg-white p-4 shadow-sm">
                <p className="text-xs font-bold uppercase text-slate-500">Invoice</p>
                <p className="mt-2 text-xl font-black text-slate-950">INV-2026-093</p>
                <p className="text-sm text-slate-600">A&E · Emergency Care</p>
              </div>
              <div className="rounded-2xl border border-emerald-300 bg-emerald-50 p-4 shadow-sm shadow-emerald-100">
                <p className="text-xs font-bold uppercase text-emerald-700">Amount Due</p>
                <p className="mt-2 text-2xl font-black text-slate-950">₦25,000</p>
                <p className="text-sm text-slate-600">Ready for receipt</p>
              </div>
            </div>
          </Panel>
          <Panel title="Bill Item Breakdown" description="Item-level visibility reduces cashier mistakes.">
            <div className="space-y-3">
              {billItems.map((item) => (
                <div key={item.item} className="flex items-center justify-between gap-4 rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 shadow-sm">
                  <div>
                    <p className="font-bold text-slate-950">{item.item}</p>
                    <p className="text-sm text-slate-500">{item.department}</p>
                  </div>
                  <p className="font-black text-slate-950">{item.amount}</p>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Payment Method" description="Authorized methods: POS, Bank Transfer, Cash. Split payment is prepared for future API support.">
            <div className="grid gap-3 sm:grid-cols-4">
              {(['POS', 'Bank Transfer', 'Cash', 'Split Payment'] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setMethod(option)}
                  className={cx(
                    'rounded-2xl border px-4 py-3 text-sm font-black transition',
                    method === option
                      ? methodActiveClass(option)
                      : 'border-slate-300 bg-white text-slate-700 hover:border-blue-300 hover:bg-blue-50'
                  )}
                >
                  {option}
                </button>
              ))}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <Field label="Amount Received" placeholder="₦25,000" />
              <Field label="Payment Reference" placeholder={method === 'Cash' ? 'Cash reference optional' : 'POS or transfer reference'} />
            </div>
          </Panel>
        </div>
        <div className="space-y-4">
          <Panel title="Validation Summary" description="Payment safety checks before receipt generation.">
            <div className="space-y-3">
              {[
                ['Invoice amount matches selected bill', 'Passed', 'emerald' as Tone],
                ['Payment method authorized for cashier desk', 'Passed', 'emerald' as Tone],
                ['Receipt number ready for generation', 'Ready', 'blue' as Tone],
                ['Backend posting', 'Pending integration', 'amber' as Tone],
              ].map(([label, state, tone]) => (
                <div key={label} className="flex items-center justify-between gap-3 rounded-xl border border-slate-300 bg-white px-4 py-3 shadow-sm">
                  <span className="text-sm font-semibold text-slate-700">{label}</span>
                  <Badge tone={tone as Tone}>{state}</Badge>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Receipt Preview" description="Traceable receipt preview before confirmation.">
            <OfficialReceiptPreview method={method} />
            <div className="mt-4 rounded-2xl border border-blue-300 bg-blue-50 p-4">
              <p className="text-sm font-black text-blue-900">
                Final cashier confirmation creates a traceable receipt record.
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-600">
                Confirm only after patient, invoice, amount, method, and reference are verified.
              </p>
              <button
                type="button"
                className="mt-4 w-full rounded-2xl bg-blue-800 px-5 py-4 text-sm font-black text-white shadow-lg shadow-blue-200 transition hover:bg-blue-900"
              >
                Confirm Payment & Generate Receipt
              </button>
              <p className="mt-3 text-xs leading-5 text-slate-500">
                Demo-only action. Production confirmation requires backend billing, receipt, audit, and payment validation APIs.
              </p>
            </div>
          </Panel>
        </div>
      </div>
    </WorkspaceShell>
  );
}

function OfficialReceiptPreview({ method }: { method: 'POS' | 'Bank Transfer' | 'Cash' | 'Split Payment' }) {
  return (
    <div className="rounded-2xl border border-slate-400 bg-white p-4 shadow-md shadow-slate-200">
      <div className="border-b border-dashed border-slate-300 pb-3 text-center">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Specialist Hospital Kazaure</p>
        <p className="mt-1 text-[11px] font-semibold text-slate-500">Official payment receipt preview</p>
      </div>
      <div className="py-4">
        <p className="text-[11px] font-black uppercase tracking-[0.14em] text-blue-700">Receipt No.</p>
        <p className="mt-1 text-2xl font-black tracking-tight text-slate-950">RCP-2026-00096</p>
        <div className="mt-4 grid gap-2 text-sm text-slate-700">
          {[
            ['Patient', 'Sani Umar'],
            ['MRN', '0000003-7'],
            ['Department', 'A&E'],
            ['Service / Purpose', 'Emergency service charge'],
            ['Amount', '₦25,000'],
            ['Payment Method', method],
            ['Cashier', 'Aisha Bello'],
            ['Time', '11:46 AM'],
            ['Trace ID / Reference', method === 'Cash' ? 'CASH-1196' : 'PAY-2026-1196'],
          ].map(([label, value]) => (
            <div key={label} className="flex items-start justify-between gap-4 border-b border-slate-100 pb-1.5">
              <span className="font-semibold text-slate-500">{label}</span>
              <span className="text-right font-black text-slate-900">{value}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Badge tone={methodTone(method)}>{method}</Badge>
          <Badge tone="emerald">Status: Issued</Badge>
          <Badge tone="blue">Audit trace ready</Badge>
        </div>
      </div>
    </div>
  );
}

function ReceiptCenterWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Receipt Traceability"
      title="Receipt Center"
      description="Receipt generation, preview, reprint readiness, search, status visibility, and audit note preview."
    >
      <FilterSurface searchPlaceholder="Search receipt number, patient name, MRN, amount, or payment method">
        <SelectField label="Receipt Status" options={['All Status', 'Issued', 'Verified', 'Reprint Ready', 'Voided']} />
        <SelectField label="Payment Method" options={['All Methods', 'POS', 'Bank Transfer', 'Cash', 'Split']} />
        <SelectField label="Time Window" options={['Today', 'This Shift', 'Last 7 Days']} />
        <SelectField label="Department" options={['All Departments', 'Pharmacy', 'Laboratory', 'A&E', 'GOPD']} />
      </FilterSurface>
      <div className="grid gap-4 xl:grid-cols-[1fr_0.8fr]">
        <Panel title="Generated Receipts" description="Cashier-visible receipts with reprint and trace states.">
          <div className="space-y-3">
            {receipts.map((receipt) => (
              <div key={receipt.receiptNo} className="rounded-2xl border border-slate-300 bg-white p-3 shadow-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="font-black text-slate-950">{receipt.receiptNo}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      {receipt.patient} · MRN {receipt.mrn}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {receipt.method} · {receipt.cashier} · {receipt.time}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge tone={methodTone(receipt.method)}>{receipt.method}</Badge>
                    <Badge tone={statusTone(receipt.status)}>{receipt.status}</Badge>
                    <Badge tone="blue">{receipt.amount}</Badge>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Receipt Preview & Audit Note" description="Presentation-ready receipt surface.">
          <div className="rounded-2xl border border-slate-400 bg-white p-4 shadow-md shadow-slate-200">
            <div className="border-b border-dashed border-slate-300 pb-3 text-center">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Specialist Hospital Kazaure</p>
              <p className="mt-1 text-[11px] font-semibold text-slate-500">Official receipt archive preview</p>
            </div>
            <p className="mt-4 text-[11px] font-black uppercase tracking-[0.14em] text-blue-700">Receipt No.</p>
            <p className="mt-1 text-2xl font-black text-slate-950">RCP-2026-00091</p>
            <div className="mt-3 grid gap-1.5 text-sm text-slate-700">
              {[
                ['Patient', 'Abba Nura'],
                ['MRN', '0000001-9'],
                ['Department', 'Pharmacy'],
                ['Amount', '₦18,500'],
                ['Payment Method', 'POS'],
                ['Cashier', 'Aisha Bello'],
                ['Time', '09:42 AM'],
                ['Trace ID / Reference', 'POS-A92F'],
              ].map(([label, value]) => (
                <div key={label} className="flex items-start justify-between gap-4 border-b border-slate-100 pb-1">
                  <span className="font-semibold text-slate-500">{label}</span>
                  <span className="text-right font-black text-slate-900">{value}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge tone="blue">POS</Badge>
              <Badge tone="emerald">Verified</Badge>
              <Badge tone="blue">Reprint allowed</Badge>
            </div>
          </div>
          <div className="mt-4 rounded-2xl border border-slate-300 bg-white p-4 shadow-sm">
            <p className="text-sm font-black text-slate-950">Receipt Audit Note</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Reprints and void visibility are traceable. Refunds, reversals, and receipt void approvals remain outside cashier authority.
            </p>
          </div>
        </Panel>
      </div>
    </WorkspaceShell>
  );
}

function PaymentHistoryWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Cashier Payment Records"
      title="Payment History"
      description="Cashier-visible transaction history for today, patients, departments, payment methods, and receipt timeline."
    >
      <FilterSurface searchPlaceholder="Search payment records by receipt, MRN, patient, department, or reference">
        <SelectField label="View" options={['Today Transactions', 'Patient Payments', 'Department Payments', 'Receipt Timeline']} />
        <SelectField label="Method" options={['All Methods', 'POS', 'Bank Transfer', 'Cash']} />
        <SelectField label="Status" options={['All Status', 'Verified', 'Issued', 'Review']} />
        <SelectField label="Department" options={['All Departments', 'Pharmacy', 'Laboratory', 'A&E', 'GOPD']} />
      </FilterSurface>
      <Panel title="Searchable Transaction Records" description="Readable cashier transaction rows prepared for future backend pagination.">
        <CompactTransactionRows />
      </Panel>
    </WorkspaceShell>
  );
}

function ShiftManagementWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Cashier Accountability"
      title="Shift Management"
      description="Shift opening, active shift posture, close readiness, handover summary, and supervisor review state."
      action={<Badge tone="emerald">Open</Badge>}
    >
      <SummaryCards
        cards={[
          { label: 'Cashier', value: 'Aisha Bello', detail: 'A & E / Theater Pay Point', tone: 'blue' },
          { label: 'Shift Opened', value: '07:45 AM', detail: 'Active shift in progress', tone: 'emerald' },
          { label: 'Current Collections', value: '₦1.85M', detail: '42 receipts issued', tone: 'cyan' },
          { label: 'Supervisor Review', value: 'Clear', detail: 'No close variance detected', tone: 'emerald' },
        ]}
      />
      <Panel title="Shift Control Flow" description="Visual workflow only. Production shift actions require backend cashier-session APIs.">
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {shiftSteps.map((step, index) => (
            <div
              key={step}
              className={cx(
                'rounded-2xl border p-4',
                index <= 1 ? 'border-emerald-300 bg-emerald-50 shadow-sm shadow-emerald-100' : 'border-slate-300 bg-white shadow-sm'
              )}
            >
              <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">Step {index + 1}</p>
              <p className="mt-2 font-black text-slate-950">{step}</p>
              <p className="mt-1 text-sm text-slate-600">{index <= 1 ? 'Active' : 'Pending'}</p>
            </div>
          ))}
        </div>
      </Panel>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Shift Summary" description="Operational summary for safe close-out.">
          <div className="space-y-3">
            {[
              ['Opening float', '₦50,000'],
              ['Collections posted', '₦1.85M'],
              ['Receipts issued', '42'],
              ['Last receipt time', '11:42 AM'],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between rounded-xl border border-slate-300 bg-white px-4 py-3 shadow-sm">
                <span className="text-sm font-semibold text-slate-600">{label}</span>
                <span className="font-black text-slate-950">{value}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Shift Handover" description="Cashier handover is visible but final review belongs to supervisor/accountant.">
          <textarea
            className="min-h-28 w-full rounded-2xl border border-slate-300 bg-white p-4 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
            placeholder="Shift handover note preview..."
          />
          <button type="button" className="mt-3 rounded-xl bg-blue-700 px-4 py-3 text-sm font-black text-white shadow-sm shadow-blue-200">
            Prepare Shift Close Summary
          </button>
        </Panel>
      </div>
    </WorkspaceShell>
  );
}

function TillSummaryWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Cash Accountability"
      title="Cash Drawer / Till Summary"
      description="Cash-specific accountability surface for opening balance, collected cash, expected cash, declared cash, variance, and handover."
    >
      <SummaryCards
        cards={[
          { label: 'Opening Cash Balance', value: '₦50,000', detail: 'Float declared at shift open', tone: 'blue' },
          { label: 'Cash Collected', value: '₦420,000', detail: 'Cash payments received today', tone: 'emerald' },
          { label: 'Expected Cash', value: '₦470,000', detail: 'Opening float plus cash collections', tone: 'cyan' },
          { label: 'Cash Variance', value: '₦0', detail: 'Declared cash matches expected cash', tone: 'emerald' },
        ]}
      />
      <div className="grid gap-4 xl:grid-cols-[1fr_0.8fr]">
        <Panel title="Declared Cash & Handover" description="Frontend-only cash drawer posture.">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Declared Cash" placeholder="₦470,000" />
            <Field label="Cash Handover Recipient" placeholder="Supervisor or accountant name" />
          </div>
          <div className="mt-4 rounded-2xl border border-emerald-300 bg-emerald-50 p-4 shadow-sm shadow-emerald-100">
            <p className="font-black text-emerald-800">Variance status: ₦0</p>
            <p className="mt-1 text-sm text-slate-600">Cash drawer is ready for controlled handover preview.</p>
          </div>
        </Panel>
        <Panel title="Till Safety Notes" description="Mistake-resistant cashier rules.">
          <div className="space-y-3">
            {['Do not close shift with unresolved cash variance.', 'Refund and reversal approval belongs to Accountant/Admin.', 'Receipt reprint requires an audit note.', 'Bank transfer must include a payment reference.'].map((rule) => (
              <div key={rule} className="rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm">
                {rule}
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </WorkspaceShell>
  );
}

function PaymentExceptionsWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Controlled Exceptions"
      title="Payment Exceptions"
      description="Cashier can view and flag payment exceptions, but cannot approve refunds, reversals, or sensitive financial adjustments."
      action={<Badge tone="rose">Approval restricted</Badge>}
    >
      <SummaryCards
        cards={[
          { label: 'Failed Payments', value: '4', detail: 'Payment attempts needing trace review', tone: 'rose' },
          { label: 'Duplicate Alerts', value: '1', detail: 'Potential duplicate payment signal', tone: 'amber' },
          { label: 'Unmatched Transfers', value: '2', detail: 'Transfer references awaiting match', tone: 'amber' },
          { label: 'Supervisor Review', value: '3', detail: 'Locked for authorized review', tone: 'blue' },
        ]}
      />
      <Panel title="Exception Queue" description="Exception visibility without cashier approval authority.">
        <div className="grid gap-3 xl:grid-cols-2">
          {exceptionRows.map((row) => (
            <article key={row.title} className={cx('rounded-2xl border p-4 shadow-sm', toneSurface(row.tone))}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-lg font-black text-slate-950">{row.title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{row.detail}</p>
                </div>
                <Badge tone={row.tone}>{row.count}</Badge>
              </div>
              <button type="button" className="mt-4 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-800 shadow-sm">
                Flag for Review
              </button>
            </article>
          ))}
        </div>
      </Panel>
    </WorkspaceShell>
  );
}

function CashierSettingsWorkspace() {
  return (
    <WorkspaceShell
      eyebrow="Workstation Configuration"
      title="Cashier Workstation Settings"
      description="Cashier profile, desk identity, receipt printer status, default payment method, notifications, biometric session, and receipt note controls."
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {[
          ['Cashier Profile', 'Aisha Bello · CASHIER · active workstation session'],
          ['Desk Identity', 'A & E / Theater Pay Point · default pay point locked'],
          ['Receipt Printer Status', 'Printer online · paper available · reprint enabled'],
          ['Default Payment Method', 'POS selected by default · cashier can switch to Transfer or Cash'],
          ['Shift Notification Preferences', 'Payment alerts and exception review notifications enabled'],
          ['Biometric Session Status', 'Cashier session verified · re-auth required for sensitive actions'],
          ['Receipt Reprint Note Requirement', 'Audit note required before receipt reprint preview'],
        ].map(([title, detail]) => (
          <Panel key={title} title={title}>
            <p className="text-sm leading-6 text-slate-600">{detail}</p>
          </Panel>
        ))}
      </div>
    </WorkspaceShell>
  );
}

function WorkspaceContent({ active }: { active: CashierWorkspace }) {
  if (active === 'overview') return <CollectionOverviewWorkspace />;
  if (active === 'pending') return <PendingPaymentsWorkspace />;
  if (active === 'lookup') return <PatientBillLookupWorkspace />;
  if (active === 'process') return <ProcessPaymentWorkspace />;
  if (active === 'receipts') return <ReceiptCenterWorkspace />;
  if (active === 'history') return <PaymentHistoryWorkspace />;
  if (active === 'shift') return <ShiftManagementWorkspace />;
  if (active === 'till') return <TillSummaryWorkspace />;
  if (active === 'exceptions') return <PaymentExceptionsWorkspace />;
  return <CashierSettingsWorkspace />;
}

export default function CashierPage() {
  const [activeWorkspace, setActiveWorkspace] = useState<CashierWorkspace>('overview');

  return (
    <div className="min-h-screen rounded-[2rem] bg-gradient-to-br from-slate-50 via-white to-blue-50/80 p-3 text-slate-950 sm:p-4 lg:p-6">
      <div className="grid gap-4 xl:grid-cols-[278px_minmax(0,1fr)]">
        <aside className="xl:sticky xl:top-6 xl:h-[calc(100vh-3rem)]">
          <div className="flex h-full flex-col rounded-3xl border border-blue-200 bg-white p-3 shadow-sm shadow-blue-100/80">
            <div className="rounded-2xl border border-blue-500/30 bg-blue-700 p-3 text-white shadow-md shadow-blue-200">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[10px] font-black uppercase tracking-[0.16em] text-blue-100">Pay Point</p>
                  <h2 className="mt-1 text-base font-black leading-tight tracking-tight">A & E / Theater Pay Point</h2>
                </div>
                <span className="shrink-0 rounded-full border border-emerald-300/50 bg-emerald-400/15 px-2 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-emerald-50">
                  Active
                </span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <div className="rounded-xl border border-white/15 bg-white/10 px-2.5 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-blue-100">Cashier</p>
                  <p className="mt-0.5 truncate text-xs font-black text-white">Aisha Bello</p>
                </div>
                <div className="rounded-xl border border-white/15 bg-white/10 px-2.5 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-blue-100">Role</p>
                  <p className="mt-0.5 truncate text-xs font-black text-white">Cashier Operator</p>
                </div>
                <div className="rounded-xl border border-white/15 bg-white/10 px-2.5 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-blue-100">Collections</p>
                  <p className="mt-0.5 text-sm font-black text-white">₦1.85M</p>
                </div>
                <div className="rounded-xl border border-white/15 bg-white/10 px-2.5 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-blue-100">Receipts</p>
                  <p className="mt-0.5 text-sm font-black text-white">42</p>
                </div>
              </div>
            </div>
            <nav className="mt-3 flex-1 space-y-1.5 overflow-y-auto pr-1">
              {navItems.map((item) => {
                const isActive = item.key === activeWorkspace;
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setActiveWorkspace(item.key)}
                    className={cx(
                      'w-full rounded-2xl border px-3 py-2.5 text-left transition',
                      isActive
                        ? 'border-blue-300 bg-blue-50 shadow-sm'
                        : 'border-transparent bg-white hover:border-slate-200 hover:bg-slate-50'
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className={cx('text-sm font-black', isActive ? 'text-blue-800' : 'text-slate-800')}>
                        {item.label}
                      </span>
                      <span
                        className={cx(
                          'rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.12em]',
                          item.priority === 'Highest' && 'bg-blue-100 text-blue-700',
                          item.priority === 'High' && 'bg-amber-100 text-amber-700',
                          item.priority === 'Low' && 'bg-slate-100 text-slate-500'
                        )}
                      >
                        {item.priority}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] leading-4 text-slate-500">{item.description}</p>
                  </button>
                );
              })}
            </nav>
          </div>
        </aside>

        <main className="min-w-0 space-y-4">
          <ShiftAccountabilityStrip />
          <WorkspaceContent active={activeWorkspace} />
        </main>
      </div>
    </div>
  );
}
