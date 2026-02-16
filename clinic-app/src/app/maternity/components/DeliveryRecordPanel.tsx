import { useEffect, useState } from 'react';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import {
  MaternityDeliveryResponse,
  MaternityDeliveryUpsert,
} from '@/domains/maternity/services/maternityService';
import { VisitResponse } from '@/shared/types';
import { EmptyState } from '@/app/components/common/EmptyState';

interface DeliveryRecordPanelProps {
  selectedVisit: VisitResponse | null;
  delivery: MaternityDeliveryResponse | null;
  loading: boolean;
  onSave: (payload: MaternityDeliveryUpsert) => Promise<void>;
}

interface DeliveryFormState {
  delivered_at: string;
  mode_of_delivery: 'UNKNOWN' | 'SVD' | 'C_SECTION' | 'ASSISTED';
  outcome: 'UNKNOWN' | 'LIVE_BIRTH' | 'STILLBIRTH' | 'NEONATAL_DEATH';
  baby_sex: 'UNKNOWN' | 'MALE' | 'FEMALE';
  baby_weight_kg: string;
  apgar_1: string;
  apgar_5: string;
  maternal_complications: string;
  newborn_complications: string;
  notes: string;
}

const emptyForm = (): DeliveryFormState => ({
  delivered_at: '',
  mode_of_delivery: 'UNKNOWN',
  outcome: 'UNKNOWN',
  baby_sex: 'UNKNOWN',
  baby_weight_kg: '',
  apgar_1: '',
  apgar_5: '',
  maternal_complications: '',
  newborn_complications: '',
  notes: '',
});

function mapDeliveryToForm(delivery: MaternityDeliveryResponse | null): DeliveryFormState {
  if (!delivery) return emptyForm();
  return {
    delivered_at: delivery.delivered_at ?? '',
    mode_of_delivery: delivery.mode_of_delivery ?? 'UNKNOWN',
    outcome: delivery.outcome ?? 'UNKNOWN',
    baby_sex: delivery.baby_sex ?? 'UNKNOWN',
    baby_weight_kg: delivery.baby_weight_kg?.toString() ?? '',
    apgar_1: delivery.apgar_1?.toString() ?? '',
    apgar_5: delivery.apgar_5?.toString() ?? '',
    maternal_complications: delivery.maternal_complications ?? '',
    newborn_complications: delivery.newborn_complications ?? '',
    notes: delivery.notes ?? '',
  };
}

export function DeliveryRecordPanel({ selectedVisit, delivery, loading, onSave }: DeliveryRecordPanelProps) {
  const [form, setForm] = useState<DeliveryFormState>(emptyForm());

  useEffect(() => {
    setForm(mapDeliveryToForm(delivery));
  }, [delivery]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Delivery Record</h3>
          <p className="text-sm text-slate-600">Capture intrapartum outcomes and maternal/newborn complications.</p>
        </div>
      </div>

      {!selectedVisit ? (
        <div className="mt-4">
          <EmptyState
            title="No patient selected"
            description="Select a maternity visit from the queue to capture delivery details."
          />
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          {loading ? <p className="text-sm text-slate-600">Loading existing delivery record…</p> : null}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label="Delivered at"
              type="datetime-local"
              value={form.delivered_at}
              onChange={(event) => setForm((prev) => ({ ...prev, delivered_at: event.target.value }))}
            />

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Mode of delivery</label>
              <select
                value={form.mode_of_delivery}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, mode_of_delivery: event.target.value as DeliveryFormState['mode_of_delivery'] }))
                }
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="UNKNOWN">Unknown</option>
                <option value="SVD">SVD</option>
                <option value="C_SECTION">C-Section</option>
                <option value="ASSISTED">Assisted</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Outcome</label>
              <select
                value={form.outcome}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, outcome: event.target.value as DeliveryFormState['outcome'] }))
                }
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="UNKNOWN">Unknown</option>
                <option value="LIVE_BIRTH">Live birth</option>
                <option value="STILLBIRTH">Stillbirth</option>
                <option value="NEONATAL_DEATH">Neonatal death</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Baby sex</label>
              <select
                value={form.baby_sex}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, baby_sex: event.target.value as DeliveryFormState['baby_sex'] }))
                }
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="UNKNOWN">Unknown</option>
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
              </select>
            </div>

            <Input
              label="Baby weight (kg)"
              value={form.baby_weight_kg}
              onChange={(event) => setForm((prev) => ({ ...prev, baby_weight_kg: event.target.value }))}
            />
            <Input
              label="APGAR (1 minute)"
              value={form.apgar_1}
              onChange={(event) => setForm((prev) => ({ ...prev, apgar_1: event.target.value }))}
            />
            <Input
              label="APGAR (5 minutes)"
              value={form.apgar_5}
              onChange={(event) => setForm((prev) => ({ ...prev, apgar_5: event.target.value }))}
            />
            <Input
              label="Maternal complications"
              value={form.maternal_complications}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, maternal_complications: event.target.value }))
              }
            />
            <Input
              label="Newborn complications"
              value={form.newborn_complications}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, newborn_complications: event.target.value }))
              }
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Clinical notes</label>
            <textarea
              className="min-h-[96px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.notes}
              onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
            />
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                void onSave({
                  action: 'SAVE_DRAFT',
                  delivered_at: form.delivered_at || undefined,
                  mode_of_delivery: form.mode_of_delivery,
                  outcome: form.outcome,
                  baby_sex: form.baby_sex,
                  baby_weight_kg: form.baby_weight_kg ? Number(form.baby_weight_kg) : undefined,
                  apgar_1: form.apgar_1 ? Number(form.apgar_1) : undefined,
                  apgar_5: form.apgar_5 ? Number(form.apgar_5) : undefined,
                  maternal_complications: form.maternal_complications || undefined,
                  newborn_complications: form.newborn_complications || undefined,
                  notes: form.notes || undefined,
                });
              }}
            >
              Save Draft
            </Button>
            <Button
              onClick={() => {
                void onSave({
                  action: 'SIGN',
                  delivered_at: form.delivered_at || undefined,
                  mode_of_delivery: form.mode_of_delivery,
                  outcome: form.outcome,
                  baby_sex: form.baby_sex,
                  baby_weight_kg: form.baby_weight_kg ? Number(form.baby_weight_kg) : undefined,
                  apgar_1: form.apgar_1 ? Number(form.apgar_1) : undefined,
                  apgar_5: form.apgar_5 ? Number(form.apgar_5) : undefined,
                  maternal_complications: form.maternal_complications || undefined,
                  newborn_complications: form.newborn_complications || undefined,
                  notes: form.notes || undefined,
                });
              }}
            >
              Sign Delivery
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
