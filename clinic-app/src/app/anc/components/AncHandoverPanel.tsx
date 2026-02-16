import { Button } from '@/shared/Button';
import { VisitResponse } from '@/shared/types';
import { Doctor } from '@/domains/user/services/userService';

interface AncHandoverPanelProps {
  selectedVisit: VisitResponse | null;
  assignableChews: Doctor[];
  assignableMidwives: Doctor[];
  selectedOwnerId: string;
  selectedMidwifeId: string;
  setSelectedOwnerId: (value: string) => void;
  setSelectedMidwifeId: (value: string) => void;
  reassignLoading: boolean;
  reassignError: string | null;
  sendLoading: boolean;
  sendError: string | null;
  onReassign: () => Promise<void>;
  onSendToMaternity: () => Promise<void>;
}

export function AncHandoverPanel({
  selectedVisit,
  assignableChews,
  assignableMidwives,
  selectedOwnerId,
  selectedMidwifeId,
  setSelectedOwnerId,
  setSelectedMidwifeId,
  reassignLoading,
  reassignError,
  sendLoading,
  sendError,
  onReassign,
  onSendToMaternity,
}: AncHandoverPanelProps) {
  if (!selectedVisit) return null;

  return (
    <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">Reassign ANC owner</h3>
        <p className="mt-1 text-sm text-slate-600">Hand over this patient to another CHEW.</p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
          <select
            value={selectedOwnerId}
            onChange={(event) => setSelectedOwnerId(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            disabled={reassignLoading}
          >
            <option value="">Select CHEW</option>
            {assignableChews.map((member) => (
              <option key={member.id} value={member.id}>
                {member.full_name || member.email}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            variant="secondary"
            isLoading={reassignLoading}
            disabled={!selectedOwnerId || reassignLoading}
            onClick={() => {
              void onReassign();
            }}
          >
            Reassign
          </Button>
        </div>
        {reassignError ? <p className="mt-2 text-xs text-rose-700">{reassignError}</p> : null}
      </article>

      <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">Send to maternity</h3>
        <p className="mt-1 text-sm text-slate-600">Transfer this visit to maternity workflow.</p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
          <select
            value={selectedMidwifeId}
            onChange={(event) => setSelectedMidwifeId(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            disabled={sendLoading}
          >
            <option value="">Select Midwife</option>
            {assignableMidwives.map((member) => (
              <option key={member.id} value={member.id}>
                {member.full_name || member.email}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            isLoading={sendLoading}
            disabled={!selectedMidwifeId || sendLoading}
            onClick={() => {
              void onSendToMaternity();
            }}
          >
            Send
          </Button>
        </div>
        {sendError ? <p className="mt-2 text-xs text-rose-700">{sendError}</p> : null}
      </article>
    </section>
  );
}
