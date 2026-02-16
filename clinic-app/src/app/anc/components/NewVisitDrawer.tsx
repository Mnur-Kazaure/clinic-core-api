import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import {
  ANCEncounterResponse,
  ANCEncounterUpsert,
  PregnancyEpisodeResponse,
  VisitResponse,
} from '@/domains/anc/api/anc';

interface NewVisitDrawerProps {
  isOpen: boolean;
  visit: VisitResponse | null;
  episode: PregnancyEpisodeResponse | null;
  existingEncounter: ANCEncounterResponse | null;
  saving: boolean;
  onClose: () => void;
  onSubmit: (payload: ANCEncounterUpsert) => Promise<void>;
}

interface EncounterFormState {
  encounter_date: string;
  fundus_height: string;
  presentation_position: string;
  presenting_part: string;
  foetal_heart: string;
  bp_systolic: string;
  bp_diastolic: string;
  urine: string;
  weight_kg: string;
  remarks: string;
  ref: string;
  initial: string;
}

const emptyForm = (): EncounterFormState => ({
  encounter_date: new Date().toISOString().slice(0, 10),
  fundus_height: '',
  presentation_position: '',
  presenting_part: '',
  foetal_heart: '',
  bp_systolic: '',
  bp_diastolic: '',
  urine: '',
  weight_kg: '',
  remarks: '',
  ref: '',
  initial: '',
});

function mapEncounterToForm(encounter: ANCEncounterResponse | null): EncounterFormState {
  if (!encounter) return emptyForm();

  return {
    encounter_date: encounter.recorded_at?.slice(0, 10) || new Date().toISOString().slice(0, 10),
    fundus_height: encounter.fundus_height ?? '',
    presentation_position: encounter.presentation_position ?? '',
    presenting_part: encounter.presenting_part ?? '',
    foetal_heart: encounter.foetal_heart ?? '',
    bp_systolic: encounter.bp_systolic?.toString() ?? '',
    bp_diastolic: encounter.bp_diastolic?.toString() ?? '',
    urine: encounter.urine ?? '',
    weight_kg: encounter.weight_kg?.toString() ?? '',
    remarks: encounter.remarks ?? '',
    ref: encounter.ref ?? '',
    initial: encounter.initial ?? '',
  };
}

export function NewVisitDrawer({
  isOpen,
  visit,
  episode,
  existingEncounter,
  saving,
  onClose,
  onSubmit,
}: NewVisitDrawerProps) {
  const [form, setForm] = useState<EncounterFormState>(emptyForm());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setForm(mapEncounterToForm(existingEncounter));
    setError(null);
  }, [isOpen, existingEncounter]);

  const signingDisabledReason = useMemo(() => {
    if (!episode) return 'Start pregnancy episode before signing.';
    if (!form.bp_systolic || !form.bp_diastolic) return 'Blood pressure is required.';
    if (!form.weight_kg) return 'Weight is required.';
    if (!form.fundus_height) return 'Fundal height is required.';
    if (!form.foetal_heart) return 'Fetal heart is required.';
    if (!form.urine) return 'Urine finding is required.';
    if (!form.remarks) return 'Remarks are required.';
    if (!form.initial) return 'Initial is required.';
    return null;
  }, [episode, form]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40" role="dialog" aria-modal="true">
      <div className="h-full w-full max-w-2xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">New ANC visit</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-900">
            {visit?.patient_name ?? 'Patient'} • MRN {visit?.patient_mrn ?? '—'}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            Encounter date is captured for UI continuity. Backend records timestamp on save/sign.
          </p>
        </div>

        <div className="space-y-4 px-5 py-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label="Date"
              type="date"
              value={form.encounter_date}
              onChange={(event) => setForm((prev) => ({ ...prev, encounter_date: event.target.value }))}
            />
            <Input
              label="Fundal height"
              value={form.fundus_height}
              onChange={(event) => setForm((prev) => ({ ...prev, fundus_height: event.target.value }))}
            />
            <Input
              label="BP systolic"
              value={form.bp_systolic}
              onChange={(event) => setForm((prev) => ({ ...prev, bp_systolic: event.target.value }))}
            />
            <Input
              label="BP diastolic"
              value={form.bp_diastolic}
              onChange={(event) => setForm((prev) => ({ ...prev, bp_diastolic: event.target.value }))}
            />
            <Input
              label="Weight (kg)"
              value={form.weight_kg}
              onChange={(event) => setForm((prev) => ({ ...prev, weight_kg: event.target.value }))}
            />
            <Input
              label="Fetal heart"
              value={form.foetal_heart}
              onChange={(event) => setForm((prev) => ({ ...prev, foetal_heart: event.target.value }))}
            />
            <Input
              label="Urine"
              value={form.urine}
              onChange={(event) => setForm((prev) => ({ ...prev, urine: event.target.value }))}
            />
            <Input
              label="Initial"
              value={form.initial}
              onChange={(event) => setForm((prev) => ({ ...prev, initial: event.target.value }))}
            />
            <Input
              label="Presentation / Position"
              value={form.presentation_position}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, presentation_position: event.target.value }))
              }
            />
            <Input
              label="Presenting Part"
              value={form.presenting_part}
              onChange={(event) => setForm((prev) => ({ ...prev, presenting_part: event.target.value }))}
            />
            <Input
              label="Reference"
              value={form.ref}
              onChange={(event) => setForm((prev) => ({ ...prev, ref: event.target.value }))}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Remarks</label>
            <textarea
              className="min-h-[104px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.remarks}
              onChange={(event) => setForm((prev) => ({ ...prev, remarks: event.target.value }))}
            />
          </div>

          {error ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          ) : null}

          {signingDisabledReason ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              {signingDisabledReason}
            </div>
          ) : null}
        </div>

        <div className="sticky bottom-0 flex items-center justify-end gap-2 border-t border-slate-200 bg-white px-5 py-4">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            variant="secondary"
            disabled={!episode || saving}
            isLoading={saving}
            onClick={async () => {
              if (!episode) {
                setError('Start pregnancy episode before saving encounter draft.');
                return;
              }

              setError(null);
              await onSubmit({
                action: 'SAVE_DRAFT',
                episode_id: episode.id,
                fundus_height: form.fundus_height || undefined,
                presentation_position: form.presentation_position || undefined,
                presenting_part: form.presenting_part || undefined,
                foetal_heart: form.foetal_heart || undefined,
                bp_systolic: form.bp_systolic ? Number(form.bp_systolic) : undefined,
                bp_diastolic: form.bp_diastolic ? Number(form.bp_diastolic) : undefined,
                urine: form.urine || undefined,
                weight_kg: form.weight_kg ? Number(form.weight_kg) : undefined,
                remarks: form.remarks || undefined,
                ref: form.ref || undefined,
                initial: form.initial || undefined,
              });
            }}
          >
            Save Draft
          </Button>
          <Button
            disabled={Boolean(signingDisabledReason) || saving}
            isLoading={saving}
            onClick={async () => {
              if (!episode || signingDisabledReason) {
                setError(signingDisabledReason || 'Unable to sign encounter.');
                return;
              }

              setError(null);
              await onSubmit({
                action: 'SIGN',
                episode_id: episode.id,
                fundus_height: form.fundus_height,
                presentation_position: form.presentation_position || undefined,
                presenting_part: form.presenting_part || undefined,
                foetal_heart: form.foetal_heart,
                bp_systolic: Number(form.bp_systolic),
                bp_diastolic: Number(form.bp_diastolic),
                urine: form.urine,
                weight_kg: Number(form.weight_kg),
                remarks: form.remarks,
                ref: form.ref || undefined,
                initial: form.initial,
              });
            }}
          >
            Sign Encounter
          </Button>
        </div>
      </div>
    </div>
  );
}
