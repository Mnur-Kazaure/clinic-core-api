'use client';
import { Card } from '@/shared/Card';
export default function EmergencyCasesPage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Emergency Case Management</h1>
        <p className="mt-1 text-sm text-slate-500 font-medium">Critical care tracking and real-time emergency response oversight.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-rose-100 bg-rose-50/20"><div className="text-[10px] font-bold text-rose-600 uppercase tracking-widest mb-2">Active Emergencies</div><div className="text-3xl font-black text-rose-700">4</div></Card>
        <Card><div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">ER Bed Availability</div><div className="text-3xl font-black text-slate-900">2 / 10</div></Card>
        <Card><div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Avg Response Time</div><div className="text-3xl font-black text-emerald-600">4.5m</div></Card>
      </div>
    </div>
  );
}
