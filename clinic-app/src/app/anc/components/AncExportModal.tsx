import { Dispatch, SetStateAction, useEffect } from 'react';
import { Button } from '@/shared/Button';
import { PurposeOfUse } from '@/shared/enums';

interface AncExportModalProps {
  open: boolean;
  exporting: boolean;
  error: string | null;
  purpose: PurposeOfUse;
  justification: string;
  includePreviousPregnancies: boolean;
  includeEncounters: boolean;
  blankRows: string;
  setPurpose: Dispatch<SetStateAction<PurposeOfUse>>;
  setJustification: Dispatch<SetStateAction<string>>;
  setIncludePreviousPregnancies: Dispatch<SetStateAction<boolean>>;
  setIncludeEncounters: Dispatch<SetStateAction<boolean>>;
  setBlankRows: Dispatch<SetStateAction<string>>;
  onClose: () => void;
  onSubmit: () => Promise<void>;
}

const purposeOptions: Array<{ value: PurposeOfUse; label: string }> = [
  { value: PurposeOfUse.TREATMENT, label: 'Treatment' },
  { value: PurposeOfUse.OPERATIONS, label: 'Operations' },
  { value: PurposeOfUse.EMERGENCY, label: 'Emergency' },
  { value: PurposeOfUse.AUDIT, label: 'Audit' },
  { value: PurposeOfUse.BILLING, label: 'Billing' },
  { value: PurposeOfUse.SECURITY, label: 'Security' },
];

export function AncExportModal({
  open,
  exporting,
  error,
  purpose,
  justification,
  includePreviousPregnancies,
  includeEncounters,
  blankRows,
  setPurpose,
  setJustification,
  setIncludePreviousPregnancies,
  setIncludeEncounters,
  setBlankRows,
  onClose,
  onSubmit,
}: AncExportModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !exporting) {
        onClose();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, exporting, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl" role="dialog" aria-modal="true">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-lg font-semibold text-slate-900">Export ANC PDF</h3>
          <p className="mt-1 text-sm text-slate-600">Purpose and justification are required for audit logging.</p>
        </div>

        <div className="space-y-4 px-5 py-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Purpose of use</label>
            <select
              value={purpose}
              onChange={(event) => setPurpose(event.target.value as PurposeOfUse)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              disabled={exporting}
            >
              {purposeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Justification</label>
            <textarea
              value={justification}
              onChange={(event) => setJustification(event.target.value)}
              className="min-h-[96px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Enter brief reason (minimum 2 characters)"
              disabled={exporting}
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={includePreviousPregnancies}
                onChange={(event) => setIncludePreviousPregnancies(event.target.checked)}
                disabled={exporting}
              />
              Include previous pregnancies
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={includeEncounters}
                onChange={(event) => setIncludeEncounters(event.target.checked)}
                disabled={exporting}
              />
              Include encounters
            </label>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Blank rows (0-20)</label>
            <input
              type="number"
              min={0}
              max={20}
              value={blankRows}
              onChange={(event) => setBlankRows(event.target.value)}
              className="w-36 rounded-md border border-slate-300 px-3 py-2 text-sm"
              disabled={exporting}
            />
          </div>

          {error ? <p className="text-sm text-rose-700">{error}</p> : null}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-5 py-4">
          <Button variant="secondary" disabled={exporting} onClick={onClose}>
            Cancel
          </Button>
          <Button isLoading={exporting} onClick={onSubmit}>
            Generate PDF
          </Button>
        </div>
      </div>
    </div>
  );
}
