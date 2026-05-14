// clinic-app/src/app/cmd/page.tsx
'use client';

import { Card } from '@/shared/Card';
import { useEffect, useState } from 'react';
import client from '@/api/client';
import { PatientModal } from './components/PatientModal';

interface ActivityItem {
  id: string;
  event_type: string;
  actor_id: string | null;
  actor_role: string;
  patient_id: string | null;
  created_at: string;
  payload: string;
}

export default function CmdPage() {
  const [stats, setStats] = useState({
    daily_revenue_minor: 0,
    patient_throughput: 0,
    total_patients_count: 0,
    staff_compliance_count: 0,
    system_health: 'OPTIMAL',
    opd_active_count: 0,
    anc_active_count: 0,
    maternity_active_count: 0,
    latest_attendance: [],
    admissions_today: 0,
    discharges_today: 0,
    outstanding_payments_minor: 0,
    bed_occupancy_percent: 0,
    emergency_alerts_count: 0,
    pending_approvals_count: 0,
    suspicious_activities_count: 0,
    long_waiting_count: 0,
    delayed_consultations_count: 0,
    doctor_workload_percent: 0
  });
  const [activityFeed, setActivityFeed] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsRes, activityRes] = await Promise.all([
          client.get('/v1/cmd/stats'),
          client.get('/v1/cmd/activity')
        ]);
        setStats(statsRes.data);
        setActivityFeed(activityRes.data);
      } catch (err) {
        console.error('Failed to fetch CMD data', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (q.length < 3) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const res = await client.get('/v1/cmd/search/patients', { params: { q } });
      setSearchResults(res.data);
    } catch (err) {
      console.error('Search failed', err);
    } finally {
      setSearching(false);
    }
  };


  const primaryMetrics = [
    {
      label: 'Patient Volume',
      value: stats.patient_throughput,
      subValue: `${stats.total_patients_count} Total Registered`,
      trend: 'Live Flow',
      trendUp: true,
      color: 'blue'
    },
    {
      label: 'Daily Revenue',
      value: `₦ ${(stats.daily_revenue_minor / 100).toLocaleString()}`,
      subValue: 'Gross collections',
      trend: 'Real-time',
      trendUp: true,
      color: 'emerald'
    },
    {
      label: 'Bed Occupancy',
      value: `${stats.bed_occupancy_percent}%`,
      subValue: 'Across all wards',
      trend: stats.bed_occupancy_percent > 80 ? 'High load' : 'Stable',
      trendUp: stats.bed_occupancy_percent > 80,
      color: 'indigo'
    },
    {
      label: 'Staff On Duty',
      value: stats.staff_compliance_count,
      subValue: 'Biometrically verified',
      trend: 'Shift active',
      trendUp: true,
      color: 'slate'
    }
  ];

  const operationalIndicators = [
    { label: 'Admissions Today', value: stats.admissions_today, icon: '📥' },
    { label: 'Discharges Today', value: stats.discharges_today, icon: '📤' },
    { label: 'Pending Approvals', value: stats.pending_approvals_count, icon: '⚖️', alert: stats.pending_approvals_count > 0 },
    { label: 'Emergency Alerts', value: stats.emergency_alerts_count, icon: '🚨', alert: stats.emergency_alerts_count > 0 },
  ];

  if (loading) {
     return (
       <div className="flex items-center justify-center h-[60vh]">
         <div className="text-center space-y-4">
           <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
           <p className="text-slate-500 font-mono text-xs uppercase tracking-widest">Synchronizing Command Center Data...</p>
         </div>
       </div>
     );
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Premium Executive Banner */}
      <div className="bg-[#0F172A] pt-12 pb-24 px-8 relative overflow-hidden">
        {/* Abstract Background Accents */}
        <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-indigo-500/10 to-transparent pointer-events-none"></div>
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none"></div>
        
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-8 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="h-2 w-10 bg-indigo-500 rounded-full"></div>
              <span className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.3em]">Institutional Oversight</span>
            </div>
            <h1 className="text-4xl font-black text-white tracking-tighter uppercase leading-none">
              Hospital <span className="text-indigo-400">Command</span> Center
            </h1>
            <p className="text-slate-400 text-sm font-medium max-w-md leading-relaxed">
              Real-time clinical telemetry and operational intelligence for KSH Executive Management.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            <div className="relative w-full sm:w-80 group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <svg className="h-4 w-4 text-slate-500 group-focus-within:text-indigo-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                placeholder="PATIENT QUICK-LOOKUP..."
                className="block w-full pl-11 pr-4 py-3 bg-white/5 border border-white/10 rounded-2xl text-xs font-black text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white/10 backdrop-blur-md transition-all uppercase tracking-widest"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
              />
              
              {searchResults.length > 0 && (
                <div className="absolute z-50 w-full mt-3 bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-200 divide-y divide-slate-50">
                  {searchResults.map((p) => (
                    <button 
                      key={p.id} 
                      className="w-full text-left px-5 py-4 hover:bg-slate-50 flex items-center justify-between group/result transition-colors"
                      onClick={() => {
                        setSelectedPatientId(p.id);
                        setSearchResults([]);
                        setSearchQuery('');
                      }}
                    >
                      <div>
                        <p className="text-xs font-black text-slate-900 group-hover/result:text-indigo-600 uppercase tracking-tight">{p.full_name}</p>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter">{p.gender} • {p.phone_number || 'NO CONTACT'}</p>
                      </div>
                      <svg className="w-4 h-4 text-slate-300 group-hover/result:text-indigo-500 transition-all transform group-hover/result:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="flex gap-3 w-full sm:w-auto">
              <button className="flex-1 sm:flex-none px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-black rounded-2xl shadow-xl shadow-indigo-900/20 transition-all uppercase tracking-widest">
                OPS Report
              </button>
              <button className="flex-1 sm:flex-none px-6 py-3 bg-rose-600 hover:bg-rose-500 text-white text-[10px] font-black rounded-2xl shadow-xl shadow-rose-900/20 transition-all uppercase tracking-widest">
                Emergency
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-8 -mt-12 space-y-8 relative z-20">
      {/* Primary Intelligence Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {primaryMetrics.map((m) => (
          <Card key={m.label} className="border-none shadow-xl shadow-slate-200/50 hover:translate-y-[-4px] transition-all duration-300 group">
            <div className="flex justify-between items-start mb-4">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] group-hover:text-indigo-600 transition-colors">
                {m.label}
              </span>
              <div className={`h-2 w-2 rounded-full bg-${m.color}-500 shadow-[0_0_8px_rgba(var(--${m.color}-500),0.5)] animate-pulse`}></div>
            </div>
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-4xl font-black text-slate-900 tracking-tighter">{m.value}</span>
            </div>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-tight mb-6">{m.subValue}</div>
            
            <div className="flex items-center justify-between pt-4 border-t border-slate-50">
              <span className={`text-[10px] font-black uppercase tracking-tighter ${m.trendUp && m.label !== 'Bed Occupancy' ? 'text-emerald-600' : m.label === 'Bed Occupancy' && m.trendUp ? 'text-rose-600' : 'text-slate-500'}`}>
                {m.trend}
              </span>
              <div className="flex gap-1">
                {[1, 2, 3].map((i) => (
                  <div key={i} className={`h-1 w-3 rounded-full ${i <= 2 ? `bg-${m.color}-100` : 'bg-slate-50'}`}></div>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </section>

      {/* Secondary Operational Indicators & Live Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Operational Status */}
        <div className="lg:col-span-2 space-y-8">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {operationalIndicators.map((oi) => (
              <div key={oi.label} className={`p-4 rounded-xl border ${oi.alert ? 'bg-rose-50 border-rose-100' : 'bg-slate-50 border-slate-100'}`}>
                <div className="text-xl mb-2">{oi.icon}</div>
                <div className="text-2xl font-black text-slate-900">{oi.value}</div>
                <div className={`text-[10px] font-bold uppercase tracking-tight ${oi.alert ? 'text-rose-600' : 'text-slate-500'}`}>
                  {oi.label}
                </div>
              </div>
            ))}
          </div>

          {/* Department Performance Matrix */}
          <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h3 className="text-xs font-black text-slate-800 uppercase tracking-widest">Department Throughput Matrix</h3>
              <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">REAL-TIME DATA</span>
            </div>
            <div className="p-6">
              <div className="space-y-6">
                {[
                  { name: 'General Outpatients (OPD)', count: stats.opd_active_count, capacity: 100, color: 'blue' },
                  { name: 'Antenatal (ANC)', count: stats.anc_active_count, capacity: 50, color: 'emerald' },
                  { name: 'Maternity & Labour', count: stats.maternity_active_count, capacity: 30, color: 'rose' },
                ].map((dept) => (
                  <div key={dept.name} className="space-y-2">
                    <div className="flex justify-between items-end">
                      <span className="text-sm font-bold text-slate-700">{dept.name}</span>
                      <span className="text-xs font-mono font-bold text-slate-900">{dept.count} <span className="text-slate-400">/ {dept.capacity}</span></span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full bg-${dept.color}-500 transition-all duration-1000`} 
                        style={{ width: `${Math.min((dept.count / dept.capacity) * 100, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Live Activity Feed */}
          <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-xs font-black text-slate-800 uppercase tracking-widest">Live Operational Feed</h3>
            </div>
            <div className="divide-y divide-slate-50">
              {activityFeed.length === 0 ? (
                <div className="px-6 py-12 text-center text-sm text-slate-400 italic">No recent activity logs available.</div>
              ) : (
                activityFeed.map((feed, i) => (
                  <div 
                    key={i} 
                    className={`px-6 py-4 flex gap-4 items-start hover:bg-slate-50 transition-colors ${feed.patient_id ? 'cursor-pointer group/item' : ''}`}
                    onClick={() => feed.patient_id && setSelectedPatientId(feed.patient_id)}
                  >
                    <span className="text-[10px] font-mono font-bold text-slate-400 mt-0.5">
                      {new Date(feed.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded ${feed.event_type.includes('ERROR') || feed.event_type.includes('DENIED') ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-600'}`}>
                          {feed.event_type}
                        </span>
                        <p className={`text-sm font-medium ${feed.event_type.includes('ERROR') ? 'text-rose-900' : 'text-slate-800'} ${feed.patient_id ? 'group-hover/item:text-indigo-600 underline decoration-indigo-200 decoration-2 underline-offset-4' : ''}`}>
                          {feed.payload}
                        </p>
                      </div>
                      <p className="mt-1 text-[10px] text-slate-400 font-medium italic">By {feed.actor_role}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="px-6 py-3 border-t border-slate-50 bg-slate-50/30 text-center">
              <a href="/cmd/audit" className="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 uppercase tracking-tighter">View Full Audit Stream</a>
            </div>
          </section>
        </div>

        {/* Right Column: Security & Health */}
        <div className="space-y-8">
          {/* System Health Indicators */}
          <section className="bg-[#0F172A] rounded-2xl p-6 text-white shadow-xl">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-6">Security & Health</h3>
            <div className="space-y-5">
              {[
                { label: 'Database Node', status: 'Active', color: 'emerald' },
                { label: 'API Gateway', status: 'Responsive', color: 'emerald' },
                { label: 'Audit Engine', status: 'Immutable', color: 'indigo' },
                { label: 'Biometric Sync', status: 'Live', color: 'emerald' },
                { label: 'Last Check', status: 'Just now', color: 'slate' },
              ].map((s) => (
                <div key={s.label} className="flex justify-between items-center">
                  <span className="text-xs font-medium text-slate-400">{s.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold font-mono">{s.status}</span>
                    <div className={`h-1.5 w-1.5 rounded-full bg-${s.color}-400`}></div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-8 p-4 rounded-xl bg-slate-800/50 border border-slate-700">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Anomalies Detected</div>
              <div className={`text-2xl font-black ${stats.suspicious_activities_count > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {stats.suspicious_activities_count}
              </div>
              <p className="mt-1 text-[9px] text-slate-400 leading-snug">
                {stats.suspicious_activities_count > 0 ? 'Potential security events require review.' : 'No anomalies detected in the last 24 hours.'}
              </p>
            </div>
          </section>

          {/* Staff Duty Roster (Biometric) */}
          <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
             <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h3 className="text-xs font-black text-slate-800 uppercase tracking-widest">Staff On Duty</h3>
              <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
            </div>
            <div className="p-4 space-y-3">
              {stats.latest_attendance.length === 0 ? (
                <p className="text-[10px] text-slate-400 italic text-center py-4">No active logs today.</p>
              ) : (
                stats.latest_attendance.map((staff: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100">
                    <div className="h-8 w-8 rounded-full bg-indigo-50 flex items-center justify-center text-[10px] font-black text-indigo-600">
                      {staff.name?.split(' ').map((n: string) => n[0]).join('') || '?'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-bold text-slate-900 truncate">{staff.name}</div>
                      <div className="text-[9px] text-slate-400 font-medium uppercase tracking-tighter">{staff.role}</div>
                    </div>
                    <div className="text-[9px] font-mono font-bold text-slate-400">
                      {new Date(staff.punched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          {/* Revenue Leakage Prevention */}
          <section className="bg-indigo-50 rounded-2xl p-6 border border-indigo-100">
             <h3 className="text-xs font-black text-indigo-900 uppercase tracking-widest mb-4">Financial Oversight</h3>
             <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-[10px] font-bold text-indigo-700">Outstanding Balance</span>
                  <span className="text-[10px] font-black text-indigo-900">₦ {(stats.outstanding_payments_minor / 100).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[10px] font-bold text-indigo-700">Waivers (Today)</span>
                  <span className="text-[10px] font-black text-indigo-900">₦ 0</span>
                </div>
                <a href="/cmd/revenue" className="block w-full mt-2 py-2 bg-indigo-600 text-white text-center text-[10px] font-bold rounded-lg hover:bg-indigo-700 shadow-md shadow-indigo-200 transition-all uppercase tracking-widest">
                  Review Financial Audit
                </a>
             </div>
          </section>
        </div>
      </div>
    </div>

      {selectedPatientId && (
        <PatientModal 
          patientId={selectedPatientId} 
          onClose={() => setSelectedPatientId(null)} 
        />
      )}
    </div>
  );
}
