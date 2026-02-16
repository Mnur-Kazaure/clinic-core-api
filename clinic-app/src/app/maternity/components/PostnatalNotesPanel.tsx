import { useState } from 'react';
import { Button } from '@/shared/Button';
import { EmptyState } from '@/app/components/common/EmptyState';
import { PostnatalNoteResponse } from '@/domains/maternity/services/maternityService';
import { VisitResponse } from '@/shared/types';

interface PostnatalNotesPanelProps {
  selectedVisit: VisitResponse | null;
  notes: PostnatalNoteResponse[];
  onAdd: (payload: { subject: 'MOTHER' | 'BABY'; note: string }) => Promise<void>;
}

export function PostnatalNotesPanel({ selectedVisit, notes, onAdd }: PostnatalNotesPanelProps) {
  const [subject, setSubject] = useState<'MOTHER' | 'BABY'>('MOTHER');
  const [noteText, setNoteText] = useState('');

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900">Postnatal Notes</h3>
      <p className="text-sm text-slate-600">Track maternal and newborn observations after delivery.</p>

      {!selectedVisit ? (
        <div className="mt-4">
          <EmptyState
            title="No patient selected"
            description="Select a maternity visit before documenting postnatal notes."
          />
        </div>
      ) : (
        <>
          <div className="mt-4 flex flex-col gap-2 md:flex-row md:items-start">
            <select
              value={subject}
              onChange={(event) => setSubject(event.target.value as 'MOTHER' | 'BABY')}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="MOTHER">Mother</option>
              <option value="BABY">Baby</option>
            </select>
            <textarea
              className="min-h-[78px] flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter postnatal note"
              value={noteText}
              onChange={(event) => setNoteText(event.target.value)}
            />
            <Button
              onClick={async () => {
                const trimmed = noteText.trim();
                if (!trimmed) return;
                await onAdd({ subject, note: trimmed });
                setNoteText('');
              }}
            >
              Add note
            </Button>
          </div>

          <div className="mt-4 space-y-2">
            {notes.length === 0 ? (
              <EmptyState
                title="No postnatal notes yet"
                description="Use this section to log maternal and newborn follow-up observations."
              />
            ) : (
              notes.map((note) => (
                <article key={note.id} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                      {note.subject}
                    </span>
                    <span className="text-xs text-slate-500">{new Date(note.added_at).toLocaleString()}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-800">{note.note}</p>
                </article>
              ))
            )}
          </div>
        </>
      )}
    </section>
  );
}
