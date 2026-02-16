import { ReactNode } from 'react';
import { Badge } from '@/shared/Badge';
import { Button } from '@/shared/Button';
import { StatChip } from '@/app/components/common/StatChip';
import {
  calculateGestationalAgeWeeks,
  PregnancyEpisodeResponse,
  VisitResponse,
} from '@/domains/anc/api/anc';

interface PregnancyOverviewStickyProps {
  selectedVisit: VisitResponse | null;
  episode: PregnancyEpisodeResponse | null;
  onEditEpisode: () => void;
  actionSlot?: ReactNode;
}

function riskToneFromGestation(weeks: number | null): 'success' | 'warning' {
  if (weeks !== null && weeks >= 37) return 'warning';
  return 'success';
}

export function PregnancyOverviewSticky({
  selectedVisit,
  episode,
  onEditEpisode,
  actionSlot,
}: PregnancyOverviewStickyProps) {
  const gestationalWeeks = calculateGestationalAgeWeeks(episode?.lmp_date, undefined);
  const riskTone = riskToneFromGestation(gestationalWeeks);

  return (
    <section className="sticky top-4 z-10 rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-sm backdrop-blur">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
            Pregnancy overview
          </p>
          <h2 className="mt-1 text-xl font-semibold text-slate-900">
            {selectedVisit?.patient_name ?? 'Select a patient'}
          </h2>
          <p className="mt-1 text-sm text-slate-600">MRN {selectedVisit?.patient_mrn ?? '—'}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={riskTone} size="sm">
            Risk: {riskTone === 'success' ? 'Low' : 'Moderate'}
          </Badge>
          <Badge variant="outline" size="sm">
            Next visit due: —
          </Badge>
          <Button size="sm" variant="secondary" onClick={onEditEpisode} disabled={!selectedVisit}>
            Edit baseline
          </Button>
          {actionSlot}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-6">
        <StatChip label="LMP" value={episode?.lmp_date ?? '—'} />
        <StatChip label="EDD" value={episode?.edd_date ?? '—'} />
        <StatChip
          label="Gestational age"
          value={gestationalWeeks === null ? '—' : `${gestationalWeeks} weeks`}
          tone={gestationalWeeks !== null && gestationalWeeks >= 37 ? 'warning' : 'info'}
        />
        <StatChip label="Gravida" value={episode?.gravida ?? '—'} />
        <StatChip label="Parity" value={episode?.parity ?? '—'} />
        <StatChip label="Booking Reg." value={episode?.booking_reg_no ?? '—'} />
      </div>
    </section>
  );
}
