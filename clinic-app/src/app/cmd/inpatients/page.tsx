'use client';
 
import { Card } from '@/shared/Card';
import { useEffect, useState } from 'react';
import client from '@/api/client';

export default function InpatientsPage() {
  const [stats, setStats] = useState({
    bed_occupancy_percent: 0,
    admissions_today: 0,
    discharges_today: 0,
  });
  const [wards, setWards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsRes, wardsRes] = await Promise.all([
          client.get('/v1/cmd/stats'),
          client.get('/v1/cmd/wards')
        ]);
        setStats(statsRes.data);
        setWards(wardsRes.data);
      } catch (err) {
        console.error('Failed to fetch inpatient telemetry', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);
 
  if (loading) return <div className="p-12 text-center text-slate-400 font-mono text-xs">LOADING IPD TELEMETRY...</div>;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Inpatient Operations (IPD)</h1>
        <p className="mt-1 text-sm text-slate-500 font-medium">Ward management, bed occupancy, and critical patient tracking.</p>
      </header>
 
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[
          { label: 'Bed Occupancy', value: `${stats.bed_occupancy_percent}%`, sub: 'Real-time load' },
          { label: 'Admissions (Today)', value: stats.admissions_today, sub: 'New arrivals' },
          { label: 'Discharges (Today)', value: stats.discharges_today, sub: 'Successful departures' },
          { label: 'Critical Patients', value: wards.reduce((acc, w) => acc + w.critical, 0), sub: 'Across all wards' },
        ].map((stat) => (
          <Card key={stat.label}>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">{stat.label}</div>
            <div className="text-3xl font-black text-slate-900 tracking-tighter">{stat.value}</div>
            <p className="mt-2 text-[10px] text-slate-500 font-medium">{stat.sub}</p>
          </Card>
        ))}
      </div>
 
      <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
          <h3 className="text-xs font-black text-slate-800 uppercase tracking-widest">Ward Status & Bed Occupancy</h3>
          <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded uppercase tracking-widest">Live Telemetry Active</span>
        </div>
        
        <div className="p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {wards.map((ward) => (
              <div key={ward.name} className="p-5 rounded-xl border border-slate-100 bg-slate-50/30 hover:shadow-md transition-all">
                <div className="flex justify-between items-start mb-4">
                  <h4 className="text-sm font-black text-slate-900 uppercase">{ward.name}</h4>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${(ward.capacity > 0 && ward.occupied / ward.capacity > 0.8) ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}`}>
                    {ward.capacity > 0 ? Math.round((ward.occupied / ward.capacity) * 100) : 0}% FULL
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Occupied</div>
                    <div className="text-lg font-black text-slate-900">{ward.occupied} <span className="text-slate-300 text-xs font-medium">/ {ward.capacity}</span></div>
                  </div>
                  <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Critical</div>
                    <div className={`text-lg font-black ${ward.critical > 0 ? 'text-rose-600' : 'text-slate-900'}`}>{ward.critical}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {wards.length === 0 && (
            <div className="text-center py-12 text-slate-400 italic text-sm">No active wards found in clinic registry.</div>
          )}
        </div>
      </section>
    </div>
  );
}
