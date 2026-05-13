// clinic-app/src/app/cmd/ledger/page.tsx
'use client';

import { useEffect, useState } from 'react';
import client from '@/api/client';
import { Card } from '@/shared/Card';

interface LedgerEntry {
  id: string;
  entry_type: string;
  amount_minor: number;
  currency: string;
  description: string;
  occurred_at: string;
  actor_role: string;
}

export default function CMDLedgerPage() {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLedger() {
      try {
        // We'll use a general ledger endpoint or a new one for CMD
        // For now, let's assume we can fetch all clinic ledger entries
        const response = await client.get('/v1/billing/ledger/summary'); // I might need to create this
        setEntries(response.data);
      } catch (err) {
        console.error('Failed to fetch ledger summary', err);
      } finally {
        setLoading(false);
      }
    }
    fetchLedger();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <section>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Financial Registry</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-900">Immutable Financial Ledger</h1>
        <p className="mt-2 text-sm text-slate-600">
          Executive audit of all clinical charges, payments, and reversals.
        </p>
      </section>

      <Card className="p-0 border-indigo-50 shadow-sm overflow-hidden">
        <table className="min-w-full divide-y divide-slate-100">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Date/Time</th>
              <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Type</th>
              <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Description</th>
              <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Amount</th>
              <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Actor</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50 bg-white">
            {entries.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-12 text-center text-slate-400 italic">No ledger entries found.</td></tr>
            ) : (
              entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-xs font-mono text-slate-500">
                    {new Date(entry.occurred_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold ${
                      entry.entry_type === 'CHARGE' ? 'bg-indigo-50 text-indigo-700' : 
                      entry.entry_type === 'PAYMENT' ? 'bg-emerald-50 text-emerald-700' : 
                      'bg-rose-50 text-rose-700'
                    }`}>
                      {entry.entry_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600 font-medium">{entry.description}</td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm font-black ${
                    entry.amount_minor > 0 ? 'text-slate-900' : 'text-emerald-600'
                  }`}>
                    ₦ {Math.abs(entry.amount_minor / 100).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-[10px] bg-slate-100 px-2 py-0.5 rounded text-slate-500 font-bold">{entry.actor_role}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
