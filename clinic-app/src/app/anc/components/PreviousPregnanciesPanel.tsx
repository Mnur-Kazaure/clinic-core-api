import { useState } from 'react';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { EmptyState } from '@/app/components/common/EmptyState';
import { PreviousPregnancyCreate, PreviousPregnancyResponse } from '@/domains/anc/api/anc';

interface PreviousPregnanciesPanelProps {
  rows: PreviousPregnancyResponse[];
  disabled: boolean;
  saving: boolean;
  onAdd: (payload: PreviousPregnancyCreate) => Promise<void>;
}

const initialFormState = {
  year: '',
  duration: '',
  antenatal_complications: '',
  labour: '',
  age_alive: '',
  age_dead: '',
  cause_of_death: '',
};

export function PreviousPregnanciesPanel({
  rows,
  disabled,
  saving,
  onAdd,
}: PreviousPregnanciesPanelProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(initialFormState);

  const resetForm = () => setForm(initialFormState);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Previous Pregnancies</h3>
          <p className="text-sm text-slate-600">Structured obstetric history from prior pregnancies.</p>
        </div>
        <Button
          size="sm"
          variant="secondary"
          disabled={disabled}
          onClick={() => setModalOpen(true)}
        >
          Add pregnancy
        </Button>
      </div>

      <div className="mt-4 hidden overflow-x-auto md:block">
        {rows.length === 0 ? (
          <EmptyState
            title="No previous pregnancies recorded"
            description="Add prior obstetric events to complete baseline risk context."
          />
        ) : (
          <table className="w-full table-auto text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="px-2 py-2">Year</th>
                <th className="px-2 py-2">Duration</th>
                <th className="px-2 py-2">Complications</th>
                <th className="px-2 py-2">Labour</th>
                <th className="px-2 py-2">Age Alive</th>
                <th className="px-2 py-2">Age Dead</th>
                <th className="px-2 py-2">Cause of Death</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-slate-100 text-slate-700">
                  <td className="px-2 py-2">{row.year ?? '—'}</td>
                  <td className="px-2 py-2">{row.duration || '—'}</td>
                  <td className="px-2 py-2">{row.antenatal_complications || '—'}</td>
                  <td className="px-2 py-2">{row.labour || '—'}</td>
                  <td className="px-2 py-2">{row.age_alive || '—'}</td>
                  <td className="px-2 py-2">{row.age_dead || '—'}</td>
                  <td className="px-2 py-2">{row.cause_of_death || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="mt-4 space-y-2 md:hidden">
        {rows.length === 0 ? (
          <EmptyState
            title="No previous pregnancies recorded"
            description="Add prior obstetric events to complete baseline risk context."
          />
        ) : (
          rows.map((row) => (
            <article key={row.id} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm">
              <p className="font-semibold text-slate-800">{row.year ?? 'Unknown year'}</p>
              <p className="mt-1 text-slate-600">Duration: {row.duration || '—'}</p>
              <p className="text-slate-600">Complications: {row.antenatal_complications || '—'}</p>
              <p className="text-slate-600">Labour: {row.labour || '—'}</p>
              <p className="text-slate-600">Age alive/dead: {row.age_alive || '—'} / {row.age_dead || '—'}</p>
              <p className="text-slate-600">Cause of death: {row.cause_of_death || '—'}</p>
            </article>
          ))
        )}
      </div>

      {modalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
          <div className="w-full max-w-3xl rounded-2xl bg-white shadow-2xl">
            <div className="border-b border-slate-200 px-5 py-4">
              <h4 className="text-lg font-semibold text-slate-900">Add previous pregnancy</h4>
            </div>
            <div className="grid grid-cols-1 gap-3 px-5 py-4 md:grid-cols-2">
              <Input
                label="Year"
                value={form.year}
                onChange={(event) => setForm((prev) => ({ ...prev, year: event.target.value }))}
              />
              <Input
                label="Duration"
                value={form.duration}
                onChange={(event) => setForm((prev) => ({ ...prev, duration: event.target.value }))}
              />
              <Input
                label="Antenatal complications"
                value={form.antenatal_complications}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, antenatal_complications: event.target.value }))
                }
              />
              <Input
                label="Labour"
                value={form.labour}
                onChange={(event) => setForm((prev) => ({ ...prev, labour: event.target.value }))}
              />
              <Input
                label="Age if alive"
                value={form.age_alive}
                onChange={(event) => setForm((prev) => ({ ...prev, age_alive: event.target.value }))}
              />
              <Input
                label="Age if dead"
                value={form.age_dead}
                onChange={(event) => setForm((prev) => ({ ...prev, age_dead: event.target.value }))}
              />
              <div className="md:col-span-2">
                <Input
                  label="Cause of death"
                  value={form.cause_of_death}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, cause_of_death: event.target.value }))
                  }
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <Button
                variant="secondary"
                onClick={() => {
                  setModalOpen(false);
                  resetForm();
                }}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button
                isLoading={saving}
                onClick={async () => {
                  await onAdd({
                    year: form.year ? Number(form.year) : undefined,
                    duration: form.duration || undefined,
                    antenatal_complications: form.antenatal_complications || undefined,
                    labour: form.labour || undefined,
                    age_alive: form.age_alive || undefined,
                    age_dead: form.age_dead || undefined,
                    cause_of_death: form.cause_of_death || undefined,
                  });
                  setModalOpen(false);
                  resetForm();
                }}
              >
                Save pregnancy
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
