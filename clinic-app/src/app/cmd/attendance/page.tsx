// clinic-app/src/app/cmd/attendance/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { attendanceService, AttendanceLog } from '@/domains/attendance/services/attendanceService';
import { clinicService } from '@/domains/clinic/services/clinicService';
import { StaffResponse } from '@/shared/types';
import { Card } from '@/shared/Card';

export default function AttendancePage() {
  const [logs, setLogs] = useState<AttendanceLog[]>([]);
  const [staff, setStaff] = useState<Record<string, StaffResponse>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [logsData, staffData] = await Promise.all([
          attendanceService.listLogs(),
          clinicService.listStaff()
        ]);
        
        const staffMap = staffData.reduce((acc, s) => {
          acc[s.id] = s;
          return acc;
        }, {} as Record<string, StaffResponse>);

        setLogs(logsData);
        setStaff(staffMap);
      } catch (err) {
        console.error('Failed to load attendance logs', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Staff & Biometrics Authority</h1>
          <p className="mt-1 text-sm text-slate-500 font-medium">
            Immutable staff activity registry. Cross-referenced with clinical session tokens.
          </p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-[10px] font-bold text-slate-700 hover:bg-slate-50 shadow-sm transition-all uppercase tracking-widest">
            Export Attendance Log
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-8">
        <Card className="p-0 overflow-hidden border-indigo-50 shadow-sm">
          <table className="min-w-full divide-y divide-slate-100">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Staff Member</th>
                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Role</th>
                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Punch Type</th>
                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Timestamp</th>
                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Location</th>
                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Hardware Ref</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 bg-white">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-sm text-slate-400 italic">
                    No biometric logs detected in this period.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-indigo-50/30 transition-colors group">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-slate-500">
                          {staff[log.user_id]?.full_name?.split(' ').map(n => n[0]).join('') || '?'}
                        </div>
                        <span className="text-sm font-bold text-slate-900">{staff[log.user_id]?.full_name || 'Unknown User'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tighter">
                        {staff[log.user_id]?.role || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold ${
                        log.punch_type === 'PUNCH_IN' 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                          : 'bg-slate-100 text-slate-700 border border-slate-200'
                      }`}>
                        {log.punch_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-xs font-mono text-slate-500">
                      {new Date(log.punched_at).toLocaleString('en-GB')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-600 font-medium">
                      {log.location || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-[10px] font-mono text-slate-400">
                      {log.hardware_ref || 'SOFT_PUNCH'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
