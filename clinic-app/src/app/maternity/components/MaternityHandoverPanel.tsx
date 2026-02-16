import { Button } from '@/shared/Button';
import { Doctor } from '@/domains/user/services/userService';
import { VisitResponse } from '@/shared/types';

interface MaternityHandoverPanelProps {
  selectedVisit: VisitResponse | null;
  assignableMidwives: Doctor[];
  selectedOwnerId: string;
  setSelectedOwnerId: (value: string) => void;
  loading: boolean;
  error: string | null;
  onReassign: () => Promise<void>;
}

export function MaternityHandoverPanel({
  selectedVisit,
  assignableMidwives,
  selectedOwnerId,
  setSelectedOwnerId,
  loading,
  error,
  onReassign,
}: MaternityHandoverPanelProps) {
  if (!selectedVisit) return null;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-base font-semibold text-slate-900">Reassign maternity owner</h3>
      <p className="mt-1 text-sm text-slate-600">Transfer care to another midwife for shift handover.</p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <select
          value={selectedOwnerId}
          onChange={(event) => setSelectedOwnerId(event.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          disabled={loading}
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
          variant="secondary"
          isLoading={loading}
          disabled={!selectedOwnerId || loading}
          onClick={() => {
            void onReassign();
          }}
        >
          Reassign
        </Button>
      </div>
      {error ? <p className="mt-2 text-xs text-rose-700">{error}</p> : null}
    </section>
  );
}
