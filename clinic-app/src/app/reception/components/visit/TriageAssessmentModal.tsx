'use client';

import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import {
  ClinicalPriorityLevel,
  TriageAssessmentResponse,
  TriageComplaintSeverity,
  TriageDraftRequest,
  TriageDraftResponse,
  TriageFallbackReasonCode,
  TriageFinalizeAction,
  TriageFinalizeResponse,
  TriageMissingVitalReasonCode,
  visitService,
} from '@/domains/visit/services/visitService';

interface TriageAssessmentModalProps {
  isOpen: boolean;
  visitId: string;
  visitVersion: number;
  currentUserRole?: string | null;
  existingAssessment?: TriageAssessmentResponse | null;
  onClose: () => void;
  onDraftSaved?: (response: TriageDraftResponse) => void;
  onSigned: (response: TriageFinalizeResponse) => void;
}

type TriageFormState = {
  action: TriageFinalizeAction;
  acuity_level: ClinicalPriorityLevel;
  complaint_severity: TriageComplaintSeverity;
  chief_complaint: string;
  triage_note: string;
  danger_sign_codes: string;
  temp_c: string;
  pulse_bpm: string;
  rr_bpm: string;
  sbp_mmhg: string;
  dbp_mmhg: string;
  spo2_pct: string;
  missing_vitals_reason_code: '' | TriageMissingVitalReasonCode;
  fallback_reason_code: '' | TriageFallbackReasonCode;
  fallback_reason_text: string;
  referred_facility: string;
  referral_reason: string;
};

const RESPIRATORY_SIGNAL_TOKENS = ['RESP', 'BREATH', 'OXYGEN', 'SPO2', 'ASTHMA'];

const ACUITY_OPTIONS: Array<{ value: ClinicalPriorityLevel; label: string; help: string }> = [
  {
    value: 'CRITICAL',
    label: 'Emergency',
    help: 'Immediate clinician response required',
  },
  {
    value: 'URGENT',
    label: 'Urgent',
    help: 'High risk, prioritize in clinical queue',
  },
  {
    value: 'ROUTINE',
    label: 'Routine',
    help: 'Clinically stable, safe to wait',
  },
];

const COMPLAINT_SEVERITY_OPTIONS: TriageComplaintSeverity[] = [
  'MILD',
  'MODERATE',
  'SEVERE',
];

const MISSING_VITAL_REASON_OPTIONS: Array<{ value: TriageMissingVitalReasonCode; label: string }> = [
  { value: 'DEVICE_UNAVAILABLE', label: 'Device unavailable' },
  { value: 'PATIENT_UNSTABLE', label: 'Patient unstable' },
  { value: 'CLINICAL_JUDGMENT', label: 'Clinical judgment' },
  { value: 'REFUSED', label: 'Patient declined' },
];

const FALLBACK_REASON_OPTIONS: Array<{ value: TriageFallbackReasonCode; label: string }> = [
  { value: 'NO_TRIAGER_ON_DUTY', label: 'No triage nurse/CHEW on duty' },
  { value: 'MASS_CASUALTY', label: 'Mass casualty load' },
  { value: 'EMERGENCY_OVERRIDE', label: 'Emergency override' },
  { value: 'OTHER', label: 'Other documented reason' },
];

const emptyFormState: TriageFormState = {
  action: 'QUEUE_FOR_CONSULTATION',
  acuity_level: 'ROUTINE',
  complaint_severity: 'MILD',
  chief_complaint: '',
  triage_note: '',
  danger_sign_codes: '',
  temp_c: '',
  pulse_bpm: '',
  rr_bpm: '',
  sbp_mmhg: '',
  dbp_mmhg: '',
  spo2_pct: '',
  missing_vitals_reason_code: '',
  fallback_reason_code: '',
  fallback_reason_text: '',
  referred_facility: '',
  referral_reason: '',
};

const parseApiDetail = (err: unknown): unknown => {
  if (!err || typeof err !== 'object' || !('response' in err)) {
    return null;
  }
  return (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail ?? null;
};

const toNumber = (value: string): number | undefined => {
  const normalized = value.trim();
  if (!normalized) return undefined;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : undefined;
};

const toOptionalString = (value: string): string | undefined => {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : undefined;
};

export function TriageAssessmentModal({
  isOpen,
  visitId,
  visitVersion,
  currentUserRole,
  existingAssessment,
  onClose,
  onDraftSaved,
  onSigned,
}: TriageAssessmentModalProps) {
  const [form, setForm] = useState<TriageFormState>(emptyFormState);
  const [workingVersion, setWorkingVersion] = useState(visitVersion);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isSigning, setIsSigning] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusNote, setStatusNote] = useState<string | null>(null);

  const isDoctor = currentUserRole === 'DOCTOR';

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    setWorkingVersion(visitVersion);
    setStatusNote(null);
    setError(null);
    setHasUnsavedChanges(false);

    if (existingAssessment) {
      setForm({
        action: existingAssessment.triage_finalize_action,
        acuity_level: existingAssessment.acuity_level,
        complaint_severity: existingAssessment.complaint_severity,
        chief_complaint: existingAssessment.chief_complaint ?? '',
        triage_note: existingAssessment.triage_note ?? '',
        danger_sign_codes: (existingAssessment.danger_sign_codes ?? []).join(', '),
        temp_c: existingAssessment.temp_c === null ? '' : String(existingAssessment.temp_c),
        pulse_bpm: existingAssessment.pulse_bpm === null ? '' : String(existingAssessment.pulse_bpm),
        rr_bpm: existingAssessment.rr_bpm === null ? '' : String(existingAssessment.rr_bpm),
        sbp_mmhg: existingAssessment.sbp_mmhg === null ? '' : String(existingAssessment.sbp_mmhg),
        dbp_mmhg: existingAssessment.dbp_mmhg === null ? '' : String(existingAssessment.dbp_mmhg),
        spo2_pct: existingAssessment.spo2_pct === null ? '' : String(existingAssessment.spo2_pct),
        missing_vitals_reason_code: existingAssessment.missing_vitals_reason_code ?? '',
        fallback_reason_code: existingAssessment.fallback_reason_code ?? '',
        fallback_reason_text: existingAssessment.fallback_reason_text ?? '',
        referred_facility: existingAssessment.referred_facility ?? '',
        referral_reason: existingAssessment.referral_reason ?? '',
      });
      return;
    }

    setForm(emptyFormState);
  }, [existingAssessment, isOpen, visitVersion]);

  const dangerSignCodes = useMemo(
    () =>
      form.danger_sign_codes
        .split(/[\n,]/)
        .map((token) => token.trim().toUpperCase())
        .filter((token) => token.length > 0)
        .slice(0, 30),
    [form.danger_sign_codes]
  );

  const requiresSpo2 = useMemo(
    () =>
      dangerSignCodes.some((code) =>
        RESPIRATORY_SIGNAL_TOKENS.some((token) => code.includes(token))
      ),
    [dangerSignCodes]
  );

  const hasIncompleteCoreVitals =
    !form.temp_c.trim() ||
    !form.pulse_bpm.trim() ||
    !form.rr_bpm.trim() ||
    !form.sbp_mmhg.trim() ||
    !form.dbp_mmhg.trim();
  const hasIncompleteRequiredSpo2 = requiresSpo2 && !form.spo2_pct.trim();
  const missingVitalsReasonRequired = hasIncompleteCoreVitals || hasIncompleteRequiredSpo2;

  const updateForm = <K extends keyof TriageFormState>(key: K, value: TriageFormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setHasUnsavedChanges(true);
    setStatusNote(null);
    setError(null);
  };

  const validate = (): string | null => {
    if (form.chief_complaint.trim().length < 3) {
      return 'Chief complaint must be at least 3 characters.';
    }
    if (form.acuity_level === 'CRITICAL' && form.triage_note.trim().length < 5) {
      return 'Emergency triage requires a clinical note (minimum 5 characters).';
    }
    if (missingVitalsReasonRequired && !form.missing_vitals_reason_code) {
      return 'Select a reason for missing vital signs before saving.';
    }
    if (isDoctor && !form.fallback_reason_code) {
      return 'Doctor fallback triage requires a fallback reason code.';
    }
    if (
      isDoctor &&
      form.fallback_reason_code === 'OTHER' &&
      form.fallback_reason_text.trim().length < 15
    ) {
      return 'Fallback reason narrative must be at least 15 characters for OTHER.';
    }
    if (form.action === 'REFER_OUT_IMMEDIATE') {
      if (form.referred_facility.trim().length < 3) {
        return 'Referral facility is required when disposition is immediate referral.';
      }
      if (form.referral_reason.trim().length < 3) {
        return 'Referral clinical reason is required for immediate referral.';
      }
    }
    return null;
  };

  const buildDraftPayload = (): TriageDraftRequest => ({
    expected_version: workingVersion,
    action: form.action,
    acuity_level: form.acuity_level,
    chief_complaint: form.chief_complaint.trim(),
    complaint_severity: form.complaint_severity,
    triage_note: toOptionalString(form.triage_note),
    danger_sign_codes: dangerSignCodes,
    temp_c: toNumber(form.temp_c),
    pulse_bpm: toNumber(form.pulse_bpm),
    rr_bpm: toNumber(form.rr_bpm),
    sbp_mmhg: toNumber(form.sbp_mmhg),
    dbp_mmhg: toNumber(form.dbp_mmhg),
    spo2_pct: toNumber(form.spo2_pct),
    missing_vitals_reason_code: missingVitalsReasonRequired
      ? form.missing_vitals_reason_code || undefined
      : undefined,
    is_doctor_fallback: isDoctor,
    fallback_reason_code: isDoctor ? form.fallback_reason_code || undefined : undefined,
    fallback_reason_text: isDoctor ? toOptionalString(form.fallback_reason_text) : undefined,
    referred_facility:
      form.action === 'REFER_OUT_IMMEDIATE' ? toOptionalString(form.referred_facility) : undefined,
    referral_reason:
      form.action === 'REFER_OUT_IMMEDIATE' ? toOptionalString(form.referral_reason) : undefined,
  });

  const persistDraft = async (): Promise<TriageDraftResponse | null> => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return null;
    }

    const response = await visitService.saveTriageDraft(visitId, buildDraftPayload());
    setWorkingVersion(response.visit_version);
    setHasUnsavedChanges(false);
    setStatusNote('Draft triage assessment saved successfully.');
    onDraftSaved?.(response);
    return response;
  };

  const handleSaveDraft = async () => {
    try {
      setIsSavingDraft(true);
      setError(null);
      await persistDraft();
    } catch (err: unknown) {
      const detail = parseApiDetail(err);
      if (detail && typeof detail === 'object') {
        const code = (detail as { code?: string }).code;
        if (code === 'VERSION_CONFLICT') {
          setError('This visit changed while you were assessing triage. Refresh and retry.');
          return;
        }
        if (code === 'TRIAGE_ALREADY_SIGNED') {
          setError('Triage is already signed for this visit.');
          return;
        }
      }
      setError(typeof detail === 'string' ? detail : 'Unable to save triage draft.');
    } finally {
      setIsSavingDraft(false);
    }
  };

  const handleSign = async () => {
    try {
      setIsSigning(true);
      setError(null);

      let currentVersion = workingVersion;
      if (hasUnsavedChanges || !existingAssessment) {
        const draft = await persistDraft();
        if (!draft) {
          return;
        }
        currentVersion = draft.visit_version;
      }

      const signed = await visitService.signTriageAssessment(visitId, {
        expected_version: currentVersion,
      });
      onSigned(signed);
    } catch (err: unknown) {
      const detail = parseApiDetail(err);
      if (detail && typeof detail === 'object') {
        const code = (detail as { code?: string }).code;
        if (code === 'VERSION_CONFLICT') {
          setError('This visit changed while you were signing triage. Refresh and retry.');
          return;
        }
        if (code === 'TRIAGE_DRAFT_REQUIRED') {
          setError('Save a triage draft before signing.');
          return;
        }
        if (code === 'TRIAGE_ALREADY_SIGNED') {
          setError('Triage assessment is already signed for this visit.');
          return;
        }
      }
      setError(typeof detail === 'string' ? detail : 'Unable to sign triage assessment.');
    } finally {
      setIsSigning(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  const busy = isSavingDraft || isSigning;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-3 sm:p-6">
      <div className="max-h-[94vh] w-full max-w-5xl overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-xl">
        <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4 sm:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
              Clinical Triage Assessment
            </p>
            <h3 className="mt-1 text-xl font-semibold text-slate-900">Capture vital signs and acuity</h3>
            <p className="mt-1 text-sm text-slate-600">
              Complete triage documentation before the patient enters clinician consultation.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
            aria-label="Close triage assessment dialog"
          >
            ✕
          </button>
        </div>

        <div className="space-y-5 px-5 py-5 sm:px-6">
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
              {error}
            </div>
          )}
          {statusNote && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {statusNote}
            </div>
          )}

          <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Clinical disposition</label>
              <select
                value={form.action}
                onChange={(e) => updateForm('action', e.target.value as TriageFinalizeAction)}
                className="h-11 w-full rounded-xl border border-slate-300 px-3 text-sm text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
              >
                <option value="QUEUE_FOR_CONSULTATION">Queue for consultation</option>
                <option value="REFER_OUT_IMMEDIATE">Immediate referral out</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Chief complaint severity</label>
              <select
                value={form.complaint_severity}
                onChange={(e) =>
                  updateForm('complaint_severity', e.target.value as TriageComplaintSeverity)
                }
                className="h-11 w-full rounded-xl border border-slate-300 px-3 text-sm text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
              >
                {COMPLAINT_SEVERITY_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          </section>

          <section>
            <label className="mb-2 block text-sm font-medium text-slate-700">Clinical acuity</label>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-3" role="radiogroup" aria-label="Clinical acuity">
              {ACUITY_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className={`min-h-16 rounded-xl border px-3 py-3 text-sm transition ${
                    form.acuity_level === option.value
                      ? 'border-sky-500 bg-sky-50 text-sky-900'
                      : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="acuity_level"
                    value={option.value}
                    checked={form.acuity_level === option.value}
                    onChange={(e) =>
                      updateForm('acuity_level', e.target.value as ClinicalPriorityLevel)
                    }
                    className="mr-2"
                  />
                  <span className="font-semibold">{option.label}</span>
                  <span className="mt-1 block text-xs text-slate-500">{option.help}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Input
              label="Chief complaint"
              value={form.chief_complaint}
              onChange={(e) => updateForm('chief_complaint', e.target.value)}
              placeholder="Patient's main presenting complaint"
            />
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Danger signs</label>
              <textarea
                value={form.danger_sign_codes}
                onChange={(e) => updateForm('danger_sign_codes', e.target.value)}
                rows={2}
                placeholder="e.g. RESP_DISTRESS, BLEEDING, CONVULSION"
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
              />
            </div>
          </section>

          <section>
            <label className="mb-1 block text-sm font-medium text-slate-700">Clinical triage note</label>
            <textarea
              value={form.triage_note}
              onChange={(e) => updateForm('triage_note', e.target.value)}
              rows={3}
              placeholder="Document key observations informing acuity decision"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
            />
          </section>

          <section>
            <h4 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-600">Vital signs</h4>
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
              <Input
                label="Temperature (C)"
                value={form.temp_c}
                onChange={(e) => updateForm('temp_c', e.target.value)}
                placeholder="36.7"
              />
              <Input
                label="Pulse (bpm)"
                value={form.pulse_bpm}
                onChange={(e) => updateForm('pulse_bpm', e.target.value)}
                placeholder="72"
              />
              <Input
                label="Resp. rate"
                value={form.rr_bpm}
                onChange={(e) => updateForm('rr_bpm', e.target.value)}
                placeholder="18"
              />
              <Input
                label="Systolic BP"
                value={form.sbp_mmhg}
                onChange={(e) => updateForm('sbp_mmhg', e.target.value)}
                placeholder="120"
              />
              <Input
                label="Diastolic BP"
                value={form.dbp_mmhg}
                onChange={(e) => updateForm('dbp_mmhg', e.target.value)}
                placeholder="80"
              />
              <Input
                label="SpO2 (%)"
                value={form.spo2_pct}
                onChange={(e) => updateForm('spo2_pct', e.target.value)}
                placeholder="98"
              />
            </div>
            {missingVitalsReasonRequired && (
              <div className="mt-3">
                <label className="mb-1 block text-sm font-medium text-slate-700">Missing vitals reason</label>
                <select
                  value={form.missing_vitals_reason_code}
                  onChange={(e) =>
                    updateForm(
                      'missing_vitals_reason_code',
                      e.target.value as '' | TriageMissingVitalReasonCode
                    )
                  }
                  className="h-11 w-full rounded-xl border border-slate-300 px-3 text-sm text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
                >
                  <option value="">Select reason</option>
                  {MISSING_VITAL_REASON_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </section>

          {isDoctor && (
            <section className="rounded-xl border border-amber-200 bg-amber-50 p-3">
              <h4 className="text-sm font-semibold text-amber-900">Doctor fallback triage</h4>
              <p className="mt-1 text-xs text-amber-800">
                Use only when no triage nurse/CHEW is available. This action is audit-tracked.
              </p>
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-amber-900">Fallback reason</label>
                  <select
                    value={form.fallback_reason_code}
                    onChange={(e) =>
                      updateForm('fallback_reason_code', e.target.value as '' | TriageFallbackReasonCode)
                    }
                    className="h-11 w-full rounded-xl border border-amber-300 bg-white px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
                  >
                    <option value="">Select reason</option>
                    {FALLBACK_REASON_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                {form.fallback_reason_code === 'OTHER' && (
                  <div>
                    <label className="mb-1 block text-sm font-medium text-amber-900">Reason narrative</label>
                    <textarea
                      value={form.fallback_reason_text}
                      onChange={(e) => updateForm('fallback_reason_text', e.target.value)}
                      rows={2}
                      className="w-full rounded-xl border border-amber-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
                      placeholder="Document fallback context clearly"
                    />
                  </div>
                )}
              </div>
            </section>
          )}

          {form.action === 'REFER_OUT_IMMEDIATE' && (
            <section className="rounded-xl border border-sky-200 bg-sky-50 p-3">
              <h4 className="text-sm font-semibold text-sky-900">Referral handover details</h4>
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <Input
                  label="Referral facility"
                  value={form.referred_facility}
                  onChange={(e) => updateForm('referred_facility', e.target.value)}
                  placeholder="Receiving facility"
                />
                <div>
                  <label className="mb-1 block text-sm font-medium text-sky-900">Referral reason</label>
                  <textarea
                    value={form.referral_reason}
                    onChange={(e) => updateForm('referral_reason', e.target.value)}
                    rows={2}
                    className="w-full rounded-xl border border-sky-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
                    placeholder="Clinical reason for transfer/referral"
                  />
                </div>
              </div>
            </section>
          )}
        </div>

        <div className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end sm:px-6">
          <Button variant="secondary" size="sm" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleSaveDraft}
            disabled={busy}
            isLoading={isSavingDraft}
          >
            Save Draft
          </Button>
          <Button variant="primary" size="sm" onClick={handleSign} disabled={busy} isLoading={isSigning}>
            Sign & Complete Triage
          </Button>
        </div>
      </div>
    </div>
  );
}
