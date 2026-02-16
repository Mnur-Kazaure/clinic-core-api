import { useEffect, useState } from 'react';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { EmptyState } from '@/app/components/common/EmptyState';
import { PregnancyEpisodeCreate, PregnancyEpisodeResponse } from '@/domains/anc/api/anc';

interface EpisodeDetailsPanelProps {
  selectedPatientId: string | null;
  episode: PregnancyEpisodeResponse | null;
  saving: boolean;
  onSave: (payload: PregnancyEpisodeCreate) => Promise<void>;
}

interface EpisodeFormState {
  lmp_date: string;
  edd_date: string;
  gravida: string;
  parity: string;
  booking_reg_no: string;
  past_medical_history: string;
  past_surgical_history: string;
  history_present_pregnancy: string;
  general_exam: string;
}

const emptyForm = (): EpisodeFormState => ({
  lmp_date: '',
  edd_date: '',
  gravida: '',
  parity: '',
  booking_reg_no: '',
  past_medical_history: '',
  past_surgical_history: '',
  history_present_pregnancy: '',
  general_exam: '',
});

function mapEpisodeToForm(episode: PregnancyEpisodeResponse | null): EpisodeFormState {
  if (!episode) return emptyForm();
  return {
    lmp_date: episode.lmp_date ?? '',
    edd_date: episode.edd_date ?? '',
    gravida: episode.gravida?.toString() ?? '',
    parity: episode.parity?.toString() ?? '',
    booking_reg_no: episode.booking_reg_no ?? '',
    past_medical_history: episode.past_medical_history ?? '',
    past_surgical_history: episode.past_surgical_history ?? '',
    history_present_pregnancy: episode.history_present_pregnancy ?? '',
    general_exam: episode.general_exam ?? '',
  };
}

export function EpisodeDetailsPanel({
  selectedPatientId,
  episode,
  saving,
  onSave,
}: EpisodeDetailsPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [form, setForm] = useState<EpisodeFormState>(emptyForm());

  useEffect(() => {
    setForm(mapEpisodeToForm(episode));
  }, [episode]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Episode Details</h3>
          <p className="text-sm text-slate-600">Baseline maternal history and examination notes.</p>
        </div>
        <button
          type="button"
          className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? 'Hide details' : 'Show details'}
        </button>
      </div>

      {!selectedPatientId ? (
        <div className="mt-4">
          <EmptyState
            title="No patient selected"
            description="Select a patient in the ANC queue to review or update episode details."
          />
        </div>
      ) : null}

      {selectedPatientId && expanded ? (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label="LMP"
              type="date"
              value={form.lmp_date}
              onChange={(event) => setForm((prev) => ({ ...prev, lmp_date: event.target.value }))}
            />
            <Input
              label="EDD"
              type="date"
              value={form.edd_date}
              onChange={(event) => setForm((prev) => ({ ...prev, edd_date: event.target.value }))}
            />
            <Input
              label="Gravida"
              value={form.gravida}
              onChange={(event) => setForm((prev) => ({ ...prev, gravida: event.target.value }))}
            />
            <Input
              label="Parity"
              value={form.parity}
              onChange={(event) => setForm((prev) => ({ ...prev, parity: event.target.value }))}
            />
            <Input
              label="Booking registration no"
              value={form.booking_reg_no}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, booking_reg_no: event.target.value }))
              }
            />
          </div>

          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Past medical history</label>
              <textarea
                className="min-h-[72px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={form.past_medical_history}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, past_medical_history: event.target.value }))
                }
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Past surgical history</label>
              <textarea
                className="min-h-[72px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={form.past_surgical_history}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, past_surgical_history: event.target.value }))
                }
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                History of present pregnancy
              </label>
              <textarea
                className="min-h-[72px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={form.history_present_pregnancy}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, history_present_pregnancy: event.target.value }))
                }
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                General examination (breasts, height, CVS, RS, pelvis, abdomen)
              </label>
              <textarea
                className="min-h-[96px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={form.general_exam}
                onChange={(event) => setForm((prev) => ({ ...prev, general_exam: event.target.value }))}
              />
            </div>
          </div>

          <div className="flex items-center justify-end">
            <Button
              isLoading={saving}
              onClick={async () => {
                await onSave({
                  lmp_date: form.lmp_date || undefined,
                  edd_date: form.edd_date || undefined,
                  gravida: form.gravida ? Number(form.gravida) : undefined,
                  parity: form.parity ? Number(form.parity) : undefined,
                  booking_reg_no: form.booking_reg_no || undefined,
                  past_medical_history: form.past_medical_history || undefined,
                  past_surgical_history: form.past_surgical_history || undefined,
                  history_present_pregnancy: form.history_present_pregnancy || undefined,
                  general_exam: form.general_exam || undefined,
                });
              }}
            >
              {episode ? 'Update episode' : 'Start episode'}
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
