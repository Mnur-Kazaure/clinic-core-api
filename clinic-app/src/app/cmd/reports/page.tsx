'use client';
import { Card } from '@/shared/Card';
export default function ReportsCenterPage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Executive Reports Center</h1>
        <p className="mt-1 text-sm text-slate-500 font-medium">Generate and download production-grade clinical and financial audits.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button className="p-6 border border-slate-200 rounded-2xl bg-white hover:bg-slate-50 text-left transition-all group">
          <div className="text-xs font-black text-slate-900 uppercase">Monthly Revenue Audit</div>
          <p className="text-[10px] text-slate-500 mt-1">Detailed breakdown of all financial activities.</p>
        </button>
        <button className="p-6 border border-slate-200 rounded-2xl bg-white hover:bg-slate-50 text-left transition-all group">
          <div className="text-xs font-black text-slate-900 uppercase">Staff Performance Review</div>
          <p className="text-[10px] text-slate-500 mt-1">Attendance vs Clinical Activity metrics.</p>
        </button>
      </div>
    </div>
  );
}
