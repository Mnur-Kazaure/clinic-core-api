// clinic-app/src/app/cmd/staff-audit/page.tsx
'use client';

import { useEffect, useState } from 'react';
import client from '@/api/client';
import { Card } from '@/shared/Card';

interface StaffPerformance {
  user_id: string;
  full_name: string;
  role: string;
  punch_count: number;
  clinical_action_count: number;
}

export default function StaffAuditPage() {
  const [performance, setPerformance] = useState<StaffPerformance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPerformance() {
      try {
        const response = await client.get('/v1/cmd/performance');
        setPerformance(response.data);
      } catch (err) {
        console.error('Failed to fetch performance audit', err);
      } finally {
        setLoading(false);
      }
    }
    fetchPerformance();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in slide-in-from-right-4 duration-500">
      <section>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Staff Authority</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-900">Performance Audit</h1>
        <p className="mt-2 text-sm text-slate-600">
          Correlating physical presence (Attendance) with clinical output (Actions).
        </p>
      </section>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {performance.map((staff) => {
          const ratio = staff.punch_count > 0 ? (staff.clinical_action_count / staff.punch_count).toFixed(1) : '0';
          return (
            <Card key={staff.user_id} className="border-indigo-50 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div className="h-10 w-10 rounded-full bg-indigo-50 flex items-center justify-center font-bold text-indigo-600">
                  {staff.full_name.split(' ').map(n => n[0]).join('')}
                </div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{staff.role}</span>
              </div>
              <h3 className="mt-4 text-lg font-bold text-slate-900">{staff.full_name}</h3>
              
              <div className="mt-6 grid grid-cols-2 gap-4">
                <div className="bg-slate-50 p-3 rounded-lg">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Punch-ins</p>
                  <p className="mt-1 text-xl font-black text-slate-900">{staff.punch_count}</p>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Actions</p>
                  <p className="mt-1 text-xl font-black text-slate-900">{staff.clinical_action_count}</p>
                </div>
              </div>

              <div className="mt-6">
                <div className="flex justify-between text-[10px] font-bold text-slate-400 uppercase">
                  <span>Efficiency Index</span>
                  <span className="text-indigo-600">{ratio} actions/punch</span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    className="h-full bg-indigo-500 rounded-full" 
                    style={{ width: `${Math.min(parseFloat(ratio) * 20, 100)}%` }}
                  ></div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
