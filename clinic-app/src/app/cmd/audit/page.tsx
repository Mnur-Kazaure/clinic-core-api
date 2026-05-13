'use client';

import { Card } from '@/shared/Card';

export default function AuditTraceabilityPage() {
  const auditLogs = [
    { id: '1', timestamp: '2026-05-13 15:45:22', actor: 'Dr. Bello', action: 'VIEW_PATIENT_RECORD', target: 'P-8820', device: 'CMD-TERM-01', ip: '192.168.1.45', status: 'AUTHORIZED' },
    { id: '2', timestamp: '2026-05-13 15:42:10', actor: 'Pharmacist John', action: 'DISPENSE_DRUG', target: 'RX-9902', device: 'PHARM-TERM-02', ip: '192.168.1.56', status: 'AUTHORIZED' },
    { id: '3', timestamp: '2026-05-13 15:38:05', actor: 'Admin Sarah', action: 'REVOKE_ACCESS', target: 'U-7721 (Receptionist)', device: 'ADMIN-TERM-01', ip: '192.168.1.10', status: 'AUTHORIZED' },
    { id: '4', timestamp: '2026-05-13 15:30:44', actor: 'SYSTEM', action: 'FAILED_LOGIN_ATTEMPT', target: 'U-0000', device: 'MOBILE-APP', ip: '41.203.78.12', status: 'DENIED', alert: true },
    { id: '5', timestamp: '2026-05-13 15:25:12', actor: 'Cashier Amaka', action: 'MODIFY_INVOICE', target: 'INV-1002', device: 'CASH-TERM-01', ip: '192.168.1.102', status: 'AUTHORIZED' },
  ];

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Audit & Traceability Engine</h1>
        <p className="mt-1 text-sm text-slate-500 font-medium">Immutable record of every clinical and administrative action within the system.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-slate-900 text-white border-none shadow-xl">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Total Events (24h)</div>
          <div className="text-3xl font-black">12,842</div>
          <div className="mt-4 h-1 w-full bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full bg-indigo-500 w-3/4"></div>
          </div>
        </Card>
        <Card>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Security Alerts</div>
          <div className="text-3xl font-black text-rose-600">3</div>
          <p className="mt-2 text-xs text-slate-500 font-medium italic">Requires CMD review</p>
        </Card>
        <Card>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Clinical Changes</div>
          <div className="text-3xl font-black text-emerald-600">452</div>
          <p className="mt-2 text-xs text-slate-500 font-medium italic">Signed by authorized personnel</p>
        </Card>
      </div>

      <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
          <div className="flex gap-4">
            <input 
              type="text" 
              placeholder="Search by Actor, Target, or IP..." 
              className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg w-64 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all"
            />
            <select className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all">
              <option>All Actions</option>
              <option>Security Only</option>
              <option>Clinical Only</option>
              <option>Financial Only</option>
            </select>
          </div>
          <button className="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 uppercase tracking-widest">Generate Audit Report</button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Timestamp</th>
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Actor</th>
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Action</th>
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Target</th>
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Terminal / IP</th>
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {auditLogs.map((log) => (
                <tr key={log.id} className={`hover:bg-slate-50/50 transition-colors ${log.alert ? 'bg-rose-50/30' : ''}`}>
                  <td className="px-6 py-4 text-xs font-mono font-medium text-slate-500">{log.timestamp}</td>
                  <td className="px-6 py-4">
                    <div className="text-xs font-bold text-slate-900">{log.actor}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`text-[10px] font-black px-2 py-0.5 rounded ${log.alert ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-600'}`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs font-bold text-slate-700">{log.target}</td>
                  <td className="px-6 py-4">
                    <div className="text-[10px] font-bold text-slate-800">{log.device}</div>
                    <div className="text-[9px] font-mono text-slate-400">{log.ip}</div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className={`text-[10px] font-bold ${log.status === 'AUTHORIZED' ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {log.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-6 py-4 bg-slate-50/50 border-t border-slate-100 text-center">
          <button className="text-[10px] font-bold text-slate-400 hover:text-slate-600 uppercase tracking-widest transition-colors">Load More Audit Data</button>
        </div>
      </section>
    </div>
  );
}
