'use client';

import { Card } from '@/shared/Card';

export default function RevenuePaymentsPage() {
  const transactions = [
    { id: 'TX-1001', time: '15:22', patient: 'Adebayo Musa', amount: '₦ 45,500.00', service: 'Surgery Deposit', method: 'POS', cashier: 'Amaka J.', status: 'SUCCESS' },
    { id: 'TX-1002', time: '15:10', patient: 'Chidi Okafor', amount: '₦ 12,000.00', service: 'Consultation', method: 'CASH', cashier: 'John D.', status: 'SUCCESS' },
    { id: 'TX-1003', time: '14:55', patient: 'Blessing Udoh', amount: '₦ 8,500.00', service: 'Lab Test', method: 'TRANSFER', cashier: 'Amaka J.', status: 'SUCCESS' },
    { id: 'TX-1004', time: '14:30', patient: 'Ibrahim Danjuma', amount: '₦ 25,000.00', service: 'Pharmacy', method: 'POS', cashier: 'Sarah K.', status: 'SUCCESS' },
  ];

  return (
    <div className="space-y-8">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Revenue & Payment Control</h1>
          <p className="mt-1 text-sm text-slate-500 font-medium">Traceable financial intelligence across all service lines.</p>
        </div>
        <div className="bg-emerald-50 border border-emerald-100 px-4 py-2 rounded-xl">
          <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">Today's Gross</div>
          <div className="text-xl font-black text-emerald-900">₦ 1,240,500.00</div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[
          { label: 'Outpatient Revenue', value: '₦ 450,200', color: 'blue' },
          { label: 'Inpatient Revenue', value: '₦ 680,300', color: 'indigo' },
          { label: 'Pharmacy Sales', value: '₦ 85,000', color: 'emerald' },
          { label: 'Lab Revenue', value: '₦ 25,000', color: 'amber' },
        ].map((stat) => (
          <Card key={stat.label}>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">{stat.label}</div>
            <div className="text-xl font-black text-slate-900">{stat.value}</div>
          </Card>
        ))}
      </div>

      <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
          <h3 className="text-xs font-black text-slate-800 uppercase tracking-widest">Live Transaction Stream</h3>
          <div className="flex gap-2">
            <button className="px-3 py-1 bg-white border border-slate-200 rounded text-[10px] font-bold text-slate-600 hover:bg-slate-50 transition-all">REFUNDS & WAIVERS</button>
            <button className="px-3 py-1 bg-white border border-slate-200 rounded text-[10px] font-bold text-slate-600 hover:bg-slate-50 transition-all">INSURANCE CLAIMS</button>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Time</th>
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Patient</th>
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Service</th>
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Cashier</th>
                <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {transactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4 text-xs font-mono font-bold text-slate-400">{tx.time}</td>
                  <td className="px-6 py-4">
                    <div className="text-xs font-bold text-slate-900">{tx.patient}</div>
                    <div className="text-[9px] font-mono text-slate-400">{tx.id}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-xs font-bold text-slate-700">{tx.service}</div>
                    <div className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">{tx.method}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-xs font-bold text-slate-800">{tx.cashier}</div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="text-xs font-black text-slate-900">{tx.amount}</div>
                    <div className="text-[9px] font-bold text-emerald-600">CLEARED</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-6 py-4 bg-slate-50/30 border-t border-slate-100 text-center">
          <button className="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 uppercase tracking-widest">View Detailed Ledger</button>
        </div>
      </section>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card className="border-amber-100 bg-amber-50/30">
          <h3 className="text-xs font-black text-amber-900 uppercase tracking-widest mb-4">Pending Payments</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-white rounded-lg border border-amber-100">
              <div>
                <div className="text-xs font-bold text-slate-900">Musa Yusuf</div>
                <div className="text-[9px] text-slate-500">Admission Fee Balance</div>
              </div>
              <div className="text-xs font-black text-rose-600">₦ 15,000.00</div>
            </div>
            <div className="flex justify-between items-center p-3 bg-white rounded-lg border border-amber-100">
              <div>
                <div className="text-xs font-bold text-slate-900">Grace Ebere</div>
                <div className="text-[9px] text-slate-500">Pharmacy - Pending POS</div>
              </div>
              <div className="text-xs font-black text-rose-600">₦ 4,200.00</div>
            </div>
          </div>
        </Card>
        
        <Card className="border-indigo-100 bg-indigo-50/30">
          <h3 className="text-xs font-black text-indigo-900 uppercase tracking-widest mb-4">Department Revenue Trends</h3>
          <div className="h-32 flex items-end gap-2 px-2">
             <div className="flex-1 bg-indigo-500 rounded-t-sm" style={{height: '60%'}}></div>
             <div className="flex-1 bg-indigo-500 rounded-t-sm" style={{height: '85%'}}></div>
             <div className="flex-1 bg-indigo-500 rounded-t-sm" style={{height: '45%'}}></div>
             <div className="flex-1 bg-indigo-500 rounded-t-sm" style={{height: '95%'}}></div>
             <div className="flex-1 bg-indigo-500 rounded-t-sm" style={{height: '75%'}}></div>
             <div className="flex-1 bg-indigo-500 rounded-t-sm" style={{height: '80%'}}></div>
          </div>
          <div className="mt-2 flex justify-between px-2">
             <span className="text-[8px] font-bold text-slate-400">OPD</span>
             <span className="text-[8px] font-bold text-slate-400">IPD</span>
             <span className="text-[8px] font-bold text-slate-400">ANC</span>
             <span className="text-[8px] font-bold text-slate-400">MAT</span>
             <span className="text-[8px] font-bold text-slate-400">LAB</span>
             <span className="text-[8px] font-bold text-slate-400">PHM</span>
          </div>
        </Card>
      </div>
    </div>
  );
}
