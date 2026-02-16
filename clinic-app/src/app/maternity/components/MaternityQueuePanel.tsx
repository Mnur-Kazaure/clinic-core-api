import { Badge } from '@/shared/Badge';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { EmptyState } from '@/app/components/common/EmptyState';
import { VisitResponse } from '@/shared/types';

interface MaternityQueuePanelProps {
  visits: VisitResponse[];
  search: string;
  loading: boolean;
  error: string | null;
  selectedVisitId: string | null;
  onSearchChange: (value: string) => void;
  onSelectVisit: (visitId: string) => void;
  onRefresh: () => void;
}

export function MaternityQueuePanel({
  visits,
  search,
  loading,
  error,
  selectedVisitId,
  onSearchChange,
  onSelectVisit,
  onRefresh,
}: MaternityQueuePanelProps) {
  return (
    <aside className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-4 py-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Maternity Queue</h2>
            <p className="mt-1 text-xs text-slate-500">{visits.length} patients assigned</p>
          </div>
          <Button size="sm" variant="secondary" onClick={onRefresh} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </Button>
        </div>
        <div className="mt-3">
          <Input
            aria-label="Search maternity queue"
            placeholder="Search patient or MRN"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </div>
      </div>

      <div className="min-h-[22rem] space-y-2 overflow-y-auto px-3 py-3">
        {error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {!error && visits.length === 0 ? (
          <EmptyState
            title="No maternity visits assigned"
            description="Patients referred to maternity will appear here."
            className="px-3 py-8"
          />
        ) : null}

        {visits.map((visit) => {
          const isSelected = visit.id === selectedVisitId;
          return (
            <button
              key={visit.id}
              type="button"
              onClick={() => onSelectVisit(visit.id)}
              className={`w-full rounded-xl border px-3 py-3 text-left transition ${
                isSelected
                  ? 'border-emerald-300 bg-emerald-50'
                  : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{visit.patient_name ?? 'Unknown patient'}</p>
                  <p className="mt-1 text-xs text-slate-500">MRN {visit.patient_mrn ?? '—'}</p>
                </div>
                <Badge variant="outline" size="sm">
                  {visit.status}
                </Badge>
              </div>
              <p className="mt-2 text-xs text-slate-500">Visit started {new Date(visit.created_at).toLocaleString()}</p>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
