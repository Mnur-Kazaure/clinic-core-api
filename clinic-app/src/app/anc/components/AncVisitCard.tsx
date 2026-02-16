import { Badge } from '@/shared/Badge';
import {
  AncVisitTimelineItem,
  calculateGestationalAgeWeeks,
  PregnancyEpisodeResponse,
} from '@/domains/anc/api/anc';

interface AncVisitCardProps {
  item: AncVisitTimelineItem;
  episode: PregnancyEpisodeResponse | null;
  expanded: boolean;
  onToggle: () => void;
}

function bpFlag(systolic?: number | null, diastolic?: number | null) {
  if (systolic == null || diastolic == null) return null;
  if (systolic >= 140 || diastolic >= 90) return { label: 'High BP', tone: 'error' as const };
  if (systolic < 90 || diastolic < 60) return { label: 'Low BP', tone: 'warning' as const };
  return null;
}

function missingFields(item: AncVisitTimelineItem) {
  const encounter = item.encounter;
  if (!encounter) {
    return ['Encounter not recorded'];
  }

  const missing: string[] = [];
  if (encounter.bp_systolic == null || encounter.bp_diastolic == null) missing.push('Blood pressure');
  if (encounter.weight_kg == null) missing.push('Weight');
  if (!encounter.fundus_height) missing.push('Fundal height');
  if (!encounter.foetal_heart) missing.push('Fetal heart');
  if (!encounter.urine) missing.push('Urine');
  return missing;
}

function compactValue(label: string, value: string | number | null | undefined) {
  return `${label}: ${value == null || value === '' ? '—' : value}`;
}

export function AncVisitCard({ item, episode, expanded, onToggle }: AncVisitCardProps) {
  const encounter = item.encounter;
  const bpAlert = bpFlag(encounter?.bp_systolic, encounter?.bp_diastolic);
  const missing = missingFields(item);
  const gestationalWeeks = calculateGestationalAgeWeeks(episode?.lmp_date, item.visit.created_at);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-slate-900">
              {new Date(item.visit.created_at).toLocaleString()}
            </p>
            <Badge variant="outline" size="sm">
              GA: {gestationalWeeks == null ? '—' : `${gestationalWeeks}w`}
            </Badge>
            <Badge variant={encounter?.record_status === 'SIGNED' ? 'success' : 'warning'} size="sm">
              {encounter?.record_status ?? 'No encounter'}
            </Badge>
            {bpAlert ? (
              <Badge variant={bpAlert.tone} size="sm">
                {bpAlert.label}
              </Badge>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-slate-500">Visit ID {item.visit.id.slice(0, 12)}…</p>
        </div>
        <button
          type="button"
          className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
          onClick={onToggle}
        >
          {expanded ? 'Collapse details' : 'View details'}
        </button>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          {compactValue('Fundal Height', encounter?.fundus_height)}
        </div>
        <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          {compactValue(
            'BP',
            encounter?.bp_systolic != null && encounter?.bp_diastolic != null
              ? `${encounter.bp_systolic}/${encounter.bp_diastolic}`
              : null
          )}
        </div>
        <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          {compactValue('FHR', encounter?.foetal_heart)}
        </div>
        <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          {compactValue('Weight', encounter?.weight_kg != null ? `${encounter.weight_kg} kg` : null)}
        </div>
        <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          {compactValue('Urine', encounter?.urine)}
        </div>
        <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          {compactValue('Presentation', encounter?.presentation_position)}
        </div>
      </div>

      {missing.length > 0 ? (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Missing key fields: {missing.join(', ')}
        </div>
      ) : null}

      {expanded ? (
        <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-700 lg:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Presenting Part</p>
            <p className="mt-1">{encounter?.presenting_part || '—'}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Reference</p>
            <p className="mt-1">{encounter?.ref || '—'}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Initial</p>
            <p className="mt-1">{encounter?.initial || '—'}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Signed at</p>
            <p className="mt-1">
              {encounter?.signed_at ? new Date(encounter.signed_at).toLocaleString() : '—'}
            </p>
          </div>
          <div className="lg:col-span-2">
            <p className="text-xs uppercase tracking-wide text-slate-500">Remarks</p>
            <p className="mt-1 whitespace-pre-wrap">{encounter?.remarks || '—'}</p>
          </div>
        </div>
      ) : null}
    </article>
  );
}
