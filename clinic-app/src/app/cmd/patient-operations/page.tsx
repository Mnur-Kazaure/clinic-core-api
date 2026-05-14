'use client';
 
import { Card } from '@/shared/Card';
import { useEffect, useState } from 'react';
import client from '@/api/client';

export default function PatientOperationsOverviewPage() {
  const [stats, setStats] = useState({
    patient_throughput: 0,
    bed_occupancy_percent: 0,
    emergency_alerts_count: 0,
    opd_active_count: 0,
    anc_active_count: 0,
    maternity_active_count: 0,
    long_waiting_count: 0,
    delayed_consultations_count: 0,
    doctor_workload_percent: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await client.get('/v1/cmd/stats');
        setStats(res.data);
      } catch (err) {
        console.error('Failed to fetch patient ops stats', err);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
     return (
       <div className="flex items-center justify-center h-[60vh]">
         <div className="text-center space-y-4">
           <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
           <p className="text-slate-500 font-mono text-xs uppercase tracking-widest">Synchronizing Operational Intelligence...</p>
         </div>
       </div>
     );
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Patient Operations Overview</h1>
        <p className="mt-1 text-sm text-slate-500 font-medium">Global visibility into hospital clinical throughput and workflow efficiency.</p>
      </header>
 
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
         <Card>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Total Daily Volume</div>
            <div className="text-2xl font-black text-slate-900">{stats.patient_throughput}</div>
            <p className="mt-1 text-[10px] text-emerald-600 font-bold">Stable flow</p>
         </Card>
         <Card>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Inpatient Occupancy</div>
            <div className="text-2xl font-black text-slate-900">{stats.bed_occupancy_percent}%</div>
            <p className={`mt-1 text-[10px] font-bold ${stats.bed_occupancy_percent > 80 ? 'text-rose-600' : 'text-amber-600'}`}>
              {stats.bed_occupancy_percent > 80 ? 'CRITICAL LOAD' : 'Near capacity'}
            </p>
         </Card>
         <Card>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Emergency Cases</div>
            <div className="text-2xl font-black text-rose-600">{stats.emergency_alerts_count}</div>
            <p className="mt-1 text-[10px] text-rose-500 font-bold">High priority</p>
         </Card>
      </div>
 
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
         <div className="space-y-6">
            <h3 className="text-xs font-black text-slate-800 uppercase tracking-widest">Live Load Matrix</h3>
            <div className="space-y-4">
               {[
                 { dept: 'General OPD', count: stats.opd_active_count, color: 'blue' },
                 { dept: 'Antenatal (ANC)', count: stats.anc_active_count, color: 'emerald' },
                 { dept: 'Maternity', count: stats.maternity_active_count, color: 'rose' },
               ].map((w) => (
                  <div key={w.dept} className="flex items-center justify-between p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                     <div className="flex items-center gap-3">
                        <div className={`h-2 w-2 rounded-full bg-${w.color}-500`}></div>
                        <span className="text-sm font-bold text-slate-700">{w.dept}</span>
                     </div>
                     <div className="text-right">
                        <div className="text-sm font-black text-slate-900">{w.count}</div>
                        <div className="text-[9px] font-bold text-slate-400 uppercase">Active Patients</div>
                     </div>
                  </div>
               ))}
            </div>
         </div>
 
         <div className="space-y-6">
            <h3 className="text-xs font-black text-slate-800 uppercase tracking-widest">Workflow Bottlenecks</h3>
            <div className="p-6 bg-white rounded-2xl border border-slate-200">
               <div className="space-y-5">
                  <div>
                     <div className="flex justify-between mb-1">
                        <span className="text-xs font-bold text-slate-700">Long Waiting Patients</span>
                        <span className={`text-xs font-bold ${stats.long_waiting_count > 5 ? 'text-rose-600' : 'text-emerald-600'}`}>
                          {stats.long_waiting_count > 5 ? 'HIGH LOAD' : 'OPTIMAL'}
                        </span>
                     </div>
                     <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div className={`h-full ${stats.long_waiting_count > 5 ? 'bg-rose-500' : 'bg-emerald-500'}`} style={{ width: `${Math.min(stats.long_waiting_count * 10, 100)}%` }}></div>
                     </div>
                  </div>
                  <div>
                     <div className="flex justify-between mb-1">
                        <span className="text-xs font-bold text-slate-700">Doctor Consultations</span>
                        <span className="text-xs font-bold text-indigo-600">{stats.doctor_workload_percent}% UTILIZED</span>
                     </div>
                     <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-500" style={{ width: `${stats.doctor_workload_percent}%` }}></div>
                     </div>
                  </div>
                  <div>
                     <div className="flex justify-between mb-1">
                        <span className="text-xs font-bold text-slate-700">Delayed Consultations</span>
                        <span className={`text-xs font-bold ${stats.delayed_consultations_count > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                          {stats.delayed_consultations_count > 0 ? 'ATTENTION REQUIRED' : 'ON TRACK'}
                        </span>
                     </div>
                     <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div className={`h-full ${stats.delayed_consultations_count > 0 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${Math.min(stats.delayed_consultations_count * 20, 100)}%` }}></div>
                     </div>
                  </div>
               </div>
               <p className="mt-6 text-[10px] text-slate-400 font-medium italic leading-relaxed">
                  System recommendation: {stats.long_waiting_count > 5 ? 'Prioritize triage clearance.' : 'Operational flow is within executive thresholds.'}
               </p>
            </div>
         </div>
      </section>
    </div>
  );
}
