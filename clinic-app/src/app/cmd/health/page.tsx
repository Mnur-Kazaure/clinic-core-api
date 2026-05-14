'use client';

import { Card } from '@/shared/Card';

export default function SystemHealthPage() {
  const services = [
    { name: 'Core API Gateway', status: 'OPERATIONAL', latency: '42ms', uptime: '99.98%', load: '12%' },
    { name: 'Primary Database Node', status: 'OPERATIONAL', latency: '8ms', uptime: '100%', load: '24%' },
    { name: 'Audit Logging Engine', status: 'OPERATIONAL', latency: '15ms', uptime: '100%', load: '5%' },
    { name: 'Biometric Sync Service', status: 'DEGRADED', latency: '450ms', uptime: '98.5%', load: '85%', alert: true },
    { name: 'Pharmacy Inventory Node', status: 'OPERATIONAL', latency: '30ms', uptime: '99.95%', load: '18%' },
  ];

  return (
    <div className="space-y-8">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">System Health & Stability</h1>
          <p className="mt-1 text-sm text-slate-500 font-medium">Real-time infrastructure monitoring and incident management.</p>
        </div>
        <div className="flex gap-2">
           <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full text-[10px] font-bold uppercase tracking-widest">
              <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
              API: 200 OK
           </div>
           <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full text-[10px] font-bold uppercase tracking-widest">
              <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
              DB: CONNECTED
           </div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
         {[
           { label: 'System Uptime', value: '142 Days', sub: 'Last restart: Jan 12' },
           { label: 'Active Sessions', value: '452', sub: 'Unique authorized users' },
           { label: 'Error Rate (24h)', value: '0.02%', sub: 'Within threshold' },
           { label: 'Last Backup', value: '22m ago', sub: 'Verified & Encrypted' },
         ].map((s) => (
            <Card key={s.label}>
               <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">{s.label}</div>
               <div className="text-2xl font-black text-slate-900">{s.value}</div>
               <p className="mt-2 text-[10px] text-slate-500 font-medium">{s.sub}</p>
            </Card>
         ))}
      </div>

      <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
         <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
            <h3 className="text-xs font-black text-slate-800 uppercase tracking-widest">Core Service Registry</h3>
         </div>
         <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
               <thead>
                  <tr className="bg-slate-50 border-b border-slate-100">
                     <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Service Name</th>
                     <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Status</th>
                     <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Latency</th>
                     <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Uptime</th>
                     <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest text-right">Load</th>
                  </tr>
               </thead>
               <tbody className="divide-y divide-slate-50">
                  {services.map((s) => (
                     <tr key={s.name} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-6 py-4">
                           <div className="text-xs font-bold text-slate-900">{s.name}</div>
                        </td>
                        <td className="px-6 py-4">
                           <span className={`text-[9px] font-black px-2 py-0.5 rounded ${s.alert ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                              {s.status}
                           </span>
                        </td>
                        <td className="px-6 py-4 text-xs font-mono text-slate-500">{s.latency}</td>
                        <td className="px-6 py-4 text-xs font-bold text-slate-700">{s.uptime}</td>
                        <td className="px-6 py-4 text-right">
                           <div className="text-xs font-black text-slate-900">{s.load}</div>
                           <div className="mt-1 h-1 w-20 bg-slate-100 rounded-full overflow-hidden ml-auto">
                              <div className={`h-full ${s.alert ? 'bg-amber-500' : 'bg-indigo-500'}`} style={{width: s.load}}></div>
                           </div>
                        </td>
                     </tr>
                  ))}
               </tbody>
            </table>
         </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
         <Card className="border-rose-100 bg-rose-50/20">
            <div className="flex justify-between items-center mb-4">
               <h3 className="text-xs font-black text-rose-900 uppercase tracking-widest">Active Incident Alerts</h3>
               <span className="text-[10px] font-bold text-rose-600">REQUIRING ACTION</span>
            </div>
            <div className="space-y-4">
               <div className="p-3 bg-white rounded-lg border border-rose-100">
                  <div className="flex justify-between mb-1">
                     <span className="text-[10px] font-black text-rose-700 uppercase">HIGH LATENCY</span>
                     <span className="text-[9px] font-mono text-slate-400">15:42:01</span>
                  </div>
                  <p className="text-xs font-medium text-slate-800">Biometric Sync Service is experiencing delays in packet verification from Ward B Terminal.</p>
               </div>
               <div className="p-3 bg-white rounded-lg border border-slate-100 opacity-60">
                  <div className="flex justify-between mb-1">
                     <span className="text-[10px] font-black text-slate-500 uppercase">RESOLVED: DB Backup</span>
                     <span className="text-[9px] font-mono text-slate-400">14:20:12</span>
                  </div>
                  <p className="text-xs font-medium text-slate-500">Scheduled database integrity check and off-site backup completed successfully.</p>
               </div>
            </div>
         </Card>

         <Card className="bg-[#0F172A] text-white">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-6">Security Monitoring</h3>
            <div className="space-y-6">
               <div className="flex justify-between items-center">
                  <span className="text-xs font-medium text-slate-400">MFA Readiness</span>
                  <span className="text-[10px] font-bold text-emerald-400 uppercase">100% ENFORCED</span>
               </div>
               <div className="flex justify-between items-center">
                  <span className="text-xs font-medium text-slate-400">Failed Logins (1h)</span>
                  <span className="text-[10px] font-bold text-slate-200">2 Attempts</span>
               </div>
               <div className="flex justify-between items-center">
                  <span className="text-xs font-medium text-slate-400">Session Hijack Protection</span>
                  <span className="text-[10px] font-bold text-emerald-400 uppercase">ACTIVE</span>
               </div>
               <div className="flex justify-between items-center">
                  <span className="text-xs font-medium text-slate-400">Traffic Source Audit</span>
                  <span className="text-[10px] font-bold text-indigo-400 uppercase">LOCAL-ONLY SECURED</span>
               </div>
               <button className="w-full mt-4 py-2 bg-indigo-600 rounded-lg text-[10px] font-bold uppercase tracking-widest hover:bg-indigo-700 transition-all">Launch Security Console</button>
            </div>
         </Card>
      </div>
    </div>
  );
}
