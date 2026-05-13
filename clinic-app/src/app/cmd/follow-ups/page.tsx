'use client';
import { Card } from '@/shared/Card';
import { useEffect, useState } from 'react';
import client from '@/api/client';

export default function FollowUpsPage() {
  const [stats, setStats] = useState({
    follow_ups_today: 0,
    missed_follow_ups: 0,
    chronic_monitoring_count: 0,
  });

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await client.get('/v1/cmd/stats');
        setStats(res.data);
      } catch (err) {
        console.error('Failed to fetch follow-up stats', err);
      }
    }
    fetchStats();
  }, []);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Follow-Ups & Continuity</h1>
        <p className="mt-1 text-sm text-slate-500 font-medium">Monitoring chronic patient revisits and treatment continuity.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Follow-Ups Today</div>
          <div className="text-3xl font-black text-indigo-900">{stats.follow_ups_today}</div>
        </Card>
        <Card>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Missed Follow-Ups</div>
          <div className="text-3xl font-black text-rose-600">{stats.missed_follow_ups}</div>
        </Card>
        <Card>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Chronic Monitoring</div>
          <div className="text-3xl font-black text-emerald-600">{stats.chronic_monitoring_count}</div>
        </Card>
      </div>
    </div>
  );
}
