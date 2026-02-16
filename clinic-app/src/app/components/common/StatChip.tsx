import { ReactNode } from 'react';

interface StatChipProps {
  label: string;
  value: ReactNode;
  tone?: 'neutral' | 'info' | 'success' | 'warning' | 'critical';
}

const toneClasses: Record<NonNullable<StatChipProps['tone']>, string> = {
  neutral: 'border-slate-200 bg-white text-slate-700',
  info: 'border-blue-200 bg-blue-50 text-blue-700',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  critical: 'border-rose-200 bg-rose-50 text-rose-700',
};

export function StatChip({ label, value, tone = 'neutral' }: StatChipProps) {
  return (
    <div className={`rounded-xl border px-3 py-2 ${toneClasses[tone]}`}>
      <p className="text-[11px] uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
