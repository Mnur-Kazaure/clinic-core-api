// clinic-app/src/app/cmd/activity/page.tsx
'use client';

import { useEffect, useState } from 'react';
import client from '@/api/client';
import { Card } from '@/shared/Card';

interface ActivityItem {
  id: string;
  event_type: string;
  actor_id: string;
  actor_role: string;
  created_at: string;
  payload: string;
}

export default function ActivityFeedPage() {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchActivity() {
      try {
        const response = await client.get('/v1/cmd/activity');
        setActivities(response.data);
      } catch (err) {
        console.error('Failed to fetch activity feed', err);
      } finally {
        setLoading(false);
      }
    }
    fetchActivity();
    const interval = setInterval(fetchActivity, 10000); // Live updates every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in slide-in-from-bottom-4 duration-500">
      <section>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Executive Intelligence</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-900">Live Activity Feed</h1>
        <p className="mt-2 text-sm text-slate-600">
          Real-time system-wide event stream. Every action is audit-sealed and traceable.
        </p>
      </section>

      <Card className="p-0 border-indigo-50 shadow-sm overflow-hidden">
        <div className="divide-y divide-slate-100">
          {activities.length === 0 ? (
            <div className="p-12 text-center text-slate-400 italic">No activities recorded yet.</div>
          ) : (
            activities.map((activity) => (
              <div key={activity.id} className="p-4 hover:bg-slate-50 transition-colors flex items-start gap-4">
                <div className={`mt-1 h-2 w-2 rounded-full flex-shrink-0 ${
                  activity.event_type.includes('ERROR') ? 'bg-rose-500' : 'bg-indigo-500'
                }`}></div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900 uppercase tracking-tight">{activity.event_type}</span>
                    <span className="text-[10px] font-mono text-slate-400">{new Date(activity.created_at).toLocaleString()}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600 leading-snug">{activity.payload}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-[10px] bg-slate-100 px-2 py-0.5 rounded text-slate-500 font-bold uppercase tracking-tighter">
                      {activity.actor_role}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">{activity.actor_id}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
