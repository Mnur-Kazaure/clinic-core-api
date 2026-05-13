'use client';
import { Card } from '@/shared/Card';
import { useEffect, useState } from 'react';
import client from '@/api/client';

export default function OutpatientsPage() {
  const [stats, setStats] = useState({
    long_waiting_count: 0,
    delayed_consultations_count: 0,
    doctor_workload_percent: 0,
  });

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await client.get('/v1/cmd/stats');
        setStats(res.data);
      } catch (err) {
        console.error('Failed to fetch OPD stats', err);
      }
    }
    fetchStats();
  }, []);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Outpatient Operations (OPD)</h1>
        <p className="mt-1 text-sm text-slate-500 font-medium">Workflow visibility: Registration → Vitals → Consultation → Lab → Pharmacy.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Long Waiting Patients</div>
          <div className="text-3xl font-black text-rose-600">{stats.long_waiting_count}</div>
        </Card>
        <Card>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Delayed Consultations</div>
          <div className="text-3xl font-black text-amber-600">{stats.delayed_consultations_count}</div>
        </Card>
        <Card>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Doctor Workload Avg</div>
          <div className="text-3xl font-black text-indigo-600">{stats.doctor_workload_percent}%</div>
        </Card>
      </div>
    </div>
  );
}
