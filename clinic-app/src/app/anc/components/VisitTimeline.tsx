import { useMemo, useState } from 'react';
import { Button } from '@/shared/Button';
import { EmptyState } from '@/app/components/common/EmptyState';
import { AncVisitCard } from '@/app/anc/components/AncVisitCard';
import { AncVisitTimelineItem, PregnancyEpisodeResponse } from '@/domains/anc/api/anc';

interface VisitTimelineProps {
  timeline: AncVisitTimelineItem[];
  episode: PregnancyEpisodeResponse | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export function VisitTimeline({
  timeline,
  episode,
  loading,
  error,
  onRefresh,
}: VisitTimelineProps) {
  const [expandedVisitIds, setExpandedVisitIds] = useState<Record<string, boolean>>({});

  const latestVisitId = useMemo(() => timeline[0]?.visit.id ?? null, [timeline]);

  const toggleExpand = (visitId: string) => {
    setExpandedVisitIds((prev) => ({ ...prev, [visitId]: !prev[visitId] }));
  };

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">ANC Visit Timeline</h3>
          <p className="text-sm text-slate-600">Newest visits appear first for quick clinical scanning.</p>
        </div>
        <Button size="sm" variant="secondary" onClick={onRefresh} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh timeline'}
        </Button>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-2">
          <div className="h-24 animate-pulse rounded-xl bg-slate-100" />
          <div className="h-24 animate-pulse rounded-xl bg-slate-100" />
        </div>
      ) : null}

      {!loading && timeline.length === 0 ? (
        <EmptyState
          title="No ANC visits recorded"
          description="Start a new ANC encounter to begin the pregnancy timeline."
        />
      ) : null}

      {!loading && timeline.length > 0 ? (
        <div className="space-y-3">
          {timeline.map((item) => {
            const isExpanded = expandedVisitIds[item.visit.id] ?? item.visit.id === latestVisitId;
            return (
              <AncVisitCard
                key={item.visit.id}
                item={item}
                episode={episode}
                expanded={isExpanded}
                onToggle={() => toggleExpand(item.visit.id)}
              />
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
