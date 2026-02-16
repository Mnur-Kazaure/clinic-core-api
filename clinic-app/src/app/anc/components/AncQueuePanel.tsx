import { Badge } from '@/shared/Badge';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { VisitResponse } from '@/shared/types';
import { EmptyState } from '@/app/components/common/EmptyState';

interface AncQueuePanelProps {
  visits: VisitResponse[];
  searchValue: string;
  selectedVisitId: string | null;
  loading: boolean;
  error: string | null;
  onSearchChange: (value: string) => void;
  onSelectVisit: (visitId: string) => void;
  onRefresh: () => void;
}

function triageBadgeTone(state?: VisitResponse['triage_state']) {
  if (state === 'TRIAGED') return 'success' as const;
  if (state === 'PENDING') return 'warning' as const;
  return 'ghost' as const;
}

export function AncQueuePanel({
  visits,
  searchValue,
  selectedVisitId,
  loading,
  error,
  onSearchChange,
  onSelectVisit,
  onRefresh,
}: AncQueuePanelProps) {
  return (
    <aside className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-4 py-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
              ANC Queue
            </h2>
            <p className="mt-1 text-xs text-slate-500">{visits.length} patients assigned</p>
          </div>
          <Button size="sm" variant="secondary" onClick={onRefresh} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </Button>
        </div>

        <div className="mt-3">
          <Input
            aria-label="Search ANC queue"
            placeholder="Search patient or MRN"
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </div>
      </div>

      <div className="min-h-[22rem] flex-1 space-y-2 overflow-y-auto px-3 py-3">
        {error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {!error && visits.length === 0 ? (
          <EmptyState
            title="No patients in ANC queue"
            description="Patients assigned to your antenatal queue will appear here."
            className="px-3 py-8"
          />
        ) : null}

        {visits.map((visit) => {
          const selected = selectedVisitId === visit.id;

          return (
            <button
              key={visit.id}
              type="button"
              onClick={() => onSelectVisit(visit.id)}
              className={`w-full rounded-xl border px-3 py-3 text-left transition ${
                selected
                  ? 'border-blue-300 bg-blue-50 shadow-sm'
                  : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    {visit.patient_name ?? 'Unknown patient'}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">MRN {visit.patient_mrn ?? '—'}</p>
                </div>
                <Badge variant={triageBadgeTone(visit.triage_state)} size="sm">
                  {visit.triage_state === 'TRIAGED'
                    ? 'Triage complete'
                    : visit.triage_state === 'PENDING'
                    ? 'Triage pending'
                    : 'No triage'}
                </Badge>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Visit started {new Date(visit.created_at).toLocaleString()}
              </p>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
