import { useState } from 'react';
import { Button } from '@/shared/Button';
import { EmptyState } from '@/app/components/common/EmptyState';
import { FamilyPlanningEventResponse } from '@/domains/maternity/services/maternityService';
import { VisitResponse } from '@/shared/types';

interface FamilyPlanningPanelProps {
  selectedVisit: VisitResponse | null;
  events: FamilyPlanningEventResponse[];
  onAdd: (payload: {
    commodity: 'IMPLANT' | 'IUD' | 'INJECTABLE' | 'PILL' | 'CONDOM' | 'OTHER';
    notes?: string;
  }) => Promise<void>;
}

export function FamilyPlanningPanel({ selectedVisit, events, onAdd }: FamilyPlanningPanelProps) {
  const [commodity, setCommodity] = useState<'IMPLANT' | 'IUD' | 'INJECTABLE' | 'PILL' | 'CONDOM' | 'OTHER'>('IMPLANT');
  const [notes, setNotes] = useState('');

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900">Family Planning</h3>
      <p className="text-sm text-slate-600">Record postpartum contraception counselling and commodities provided.</p>

      {!selectedVisit ? (
        <div className="mt-4">
          <EmptyState
            title="No patient selected"
            description="Select a maternity visit to document family planning support."
          />
        </div>
      ) : (
        <>
          <div className="mt-4 flex flex-col gap-2 md:flex-row md:items-start">
            <select
              value={commodity}
              onChange={(event) =>
                setCommodity(
                  event.target.value as
                    | 'IMPLANT'
                    | 'IUD'
                    | 'INJECTABLE'
                    | 'PILL'
                    | 'CONDOM'
                    | 'OTHER'
                )
              }
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="IMPLANT">Implant</option>
              <option value="IUD">IUD</option>
              <option value="INJECTABLE">Injectable</option>
              <option value="PILL">Pill</option>
              <option value="CONDOM">Condom</option>
              <option value="OTHER">Other</option>
            </select>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              className="min-h-[78px] flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Counselling or event notes"
            />
            <Button
              onClick={async () => {
                await onAdd({ commodity, notes: notes.trim() || undefined });
                setNotes('');
              }}
            >
              Add event
            </Button>
          </div>

          <div className="mt-4 space-y-2">
            {events.length === 0 ? (
              <EmptyState
                title="No family planning events"
                description="Document commodities and counselling to support postpartum continuity of care."
              />
            ) : (
              events.map((event) => (
                <article key={event.id} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                      {event.commodity}
                    </span>
                    <span className="text-xs text-slate-500">{new Date(event.added_at).toLocaleString()}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-800">{event.notes || 'No notes captured.'}</p>
                </article>
              ))
            )}
          </div>
        </>
      )}
    </section>
  );
}
