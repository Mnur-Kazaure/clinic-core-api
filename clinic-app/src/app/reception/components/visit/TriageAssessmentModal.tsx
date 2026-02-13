'use client';

import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import {
  ClinicalPriorityLevel,
  TriageAssessmentResponse,
  TriageComplaintSeverity,
  TriageFallbackReasonCode,
  TriageFinalizeAction,
  TriageFinalizeResponse,
  TriageMissingVitalReasonCode,
  TriageSupersedeRequest,
  visitService,
} from '@/domains/visit/services/visitService';

interface TriageAssessmentModalProps {
  isOpen: boolean;
  visitId: string;
  visitVersion: number;
  mode: 'finalize' | 'supersede';
  currentUserRole?: string | null;
  existingAssessment?: TriageAssessmentResponse | null;
  onClose: () => void;
  onSuccess: (response: TriageFinalizeResponse) => void;
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
  correction_reason_code: string;
  correction_reason_text: string;
};

const RESPIRATORY_SIGNAL_TOKENS = ['RESP', 'BREATH', 'OXYGEN', 'SPO2', 'ASTHMA'];

const ACUITY_OPTIONS: Array<{ value: ClinicalPriorityLevel; label: string; help: string }> = [
  {
    value: 'CRITICAL',
    label: 'Critical',
    help: 'Immediate life-threatening risk',
  },
  {
    value: 'URGENT',
    label: 'Urgent',
    help: 'Needs clinician review soon',
  },
  {
    value: 'ROUTINE',
    label: 'Routine',
    help: 'Stable and can wait in queue',
  },
];

const COMPLAINT_SEVERITY_OPTIONS: TriageComplaintSeverity[] = [
  'MILD',
  'MODERATE',
  'SEVERE',
];

const MISSING_VITAL_REASON_OPTIONS: Array<{
  value: TriageMissingVitalReasonCode;
  label: string;
}> = [
  { value: 'DEVICE_UNAVAILABLE', label: 'Device unavailable' },
  { value: 'PATIENT_UNSTABLE', label: 'Patient unstable' },
  { value: 'CLINICAL_JUDGMENT', label: 'Clinical judgment' },
  { value: 'REFUSED', label: 'Patient refused' },
];

const FALLBACK_REASON_OPTIONS: Array<{ value: TriageFallbackReasonCode; label: string }> = [
  { value: 'NO_TRIAGER_ON_DUTY', label: 'No triager on duty' },
  { value: 'MASS_CASUALTY', label: 'Mass casualty' },
  { value: 'EMERGENCY_OVERRIDE', label: 'Emergency override' },
  { value: 'OTHER', label: 'Other' },
];

const CORRECTION_REASON_OPTIONS = [
  { value: 'VITALS_CORRECTION', label: 'Vitals correction' },
  { value: 'ACUITY_REASSESSMENT', label: 'Acuity reassessment' },
  { value: 'COMPLAINT_UPDATE', label: 'Complaint update' },
  { value: 'OTHER', label: 'Other' },
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
  correction_reason_code: 'VITALS_CORRECTION',
  correction_reason_text: '',
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
  mode,
  currentUserRole,
  existingAssessment,
  onClose,
  onSuccess,
}: TriageAssessmentModalProps) {
  const [form, setForm] = useState<TriageFormState>(emptyFormState);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isDoctor = currentUserRole === 'DOCTOR';
  const isSupersede = mode === 'supersede';

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    if (existingAssessment) {
      setForm({
        action: existingAssessment.triage_finalize_action,
        acuity_level: existingAssessment.acuity_level,
        complaint_severity: existingAssessment.complaint_severity,
        chief_complaint: existingAssessment.chief_complaint ?? '',
        triage_note: existingAssessment.triage_note ?? '',
        danger_sign_codes: (existingAssessment.danger_sign_codes ?? []).join(', '),
        temp_c:
          existingAssessment.temp_c === null
            ? ''
            : String(existingAssessment.temp_c),
        pulse_bpm:
          existingAssessment.pulse_bpm === null
            ? ''
            : String(existingAssessment.pulse_bpm),
        rr_bpm:
          existingAssessment.rr_bpm === null
            ? ''
            : String(existingAssessment.rr_bpm),
        sbp_mmhg:
          existingAssessment.sbp_mmhg === null
            ? ''
            : String(existingAssessment.sbp_mmhg),
        dbp_mmhg:
          existingAssessment.dbp_mmhg === null
            ? ''
            : String(existingAssessment.dbp_mmhg),
        spo2_pct:
          existingAssessment.spo2_pct === null
            ? ''
            : String(existingAssessment.spo2_pct),
        missing_vitals_reason_code:
          existingAssessment.missing_vitals_reason_code ?? '',
        fallback_reason_code: existingAssessment.fallback_reason_code ?? '',
        fallback_reason_text: existingAssessment.fallback_reason_text ?? '',
        referred_facility: existingAssessment.referred_facility ?? '',
        referral_reason: existingAssessment.referral_reason ?? '',
        correction_reason_code: 'VITALS_CORRECTION',
        correction_reason_text: '',
      });
    } else {
      setForm(emptyFormState);
    }
    setError(null);
  }, [existingAssessment, isOpen]);

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
  };

  const validate = (): string | null => {
    if (form.chief_complaint.trim().length < 3) {
      return 'Chief complaint must be at least 3 characters.';
    }
    if (form.acuity_level === 'CRITICAL' && form.triage_note.trim().length < 5) {
      return 'Critical triage requires a triage note (min 5 characters).';
    }
    if (missingVitalsReasonRequired && !form.missing_vitals_reason_code) {
      return 'Select a missing vitals reason when required vitals are incomplete.';
    }
    if (isDoctor && !form.fallback_reason_code) {
      return 'Doctor fallback triage requires a fallback reason.';
    }
    if (isDoctor && form.fallback_reason_code === 'OTHER' && form.fallback_reason_text.trim().length < 15) {
      return 'Fallback reason text must be at least 15 characters for OTHER.';
    }
    if (form.action === 'REFER_OUT_IMMEDIATE') {
      if (form.referred_facility.trim().length < 3) {
        return 'Referral facility is required for immediate referral.';
      }
      if (form.referral_reason.trim().length < 3) {
        return 'Referral reason is required for immediate referral.';
      }
    }
    if (isSupersede && form.correction_reason_code.trim().length < 2) {
      return 'Correction reason code is required when updating triage.';
    }
    return null;
  };

  const handleSubmit = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const payloadBase = {
        expected_version: visitVersion,
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
          form.action === 'REFER_OUT_IMMEDIATE'
            ? toOptionalString(form.referred_facility)
            : undefined,
        referral_reason:
          form.action === 'REFER_OUT_IMMEDIATE'
            ? toOptionalString(form.referral_reason)
            : undefined,
      };

      let response: TriageFinalizeResponse;
      if (isSupersede) {
        const supersedePayload: TriageSupersedeRequest = {
          ...payloadBase,
          correction_reason_code: form.correction_reason_code.trim(),
          correction_reason_text: toOptionalString(form.correction_reason_text),
        };
        response = await visitService.supersedeTriage(visitId, supersedePayload);
      } else {
        response = await visitService.finalizeTriage(visitId, payloadBase);
      }
      onSuccess(response);
    } catch (err: unknown) {
      const detail = parseApiDetail(err);
      if (detail && typeof detail === 'object') {
        const code = (detail as { code?: string }).code;
        if (code === 'VERSION_CONFLICT') {
          setError('This visit was updated by someone else. Refresh and try again.');
          return;
        }
        if (code === 'TRIAGE_ALREADY_EXISTS') {
          setError('A triage record already exists. Use Update Triage instead.');
          return;
        }
        if (code === 'TRIAGE_INVALID_VISIT_STATE') {
          setError('Triage is only allowed for registered or triaged visits.');
          return;
        }
      }
      setError(typeof detail === 'string' ? detail : 'Unable to save triage assessment.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white shadow-xl">
        <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
              Triage Assessment
            </p>
            <h3 className="mt-1 text-xl font-semibold text-slate-900">
              {isSupersede ? 'Update triage assessment' : 'Finalize triage assessment'}
            </h3>
            <p className="mt-1 text-sm text-slate-600">
              {isDoctor
                ? 'Doctor fallback triage is enabled and will be audited.'
                : 'Capture vitals and acuity before queueing for consultation.'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Close triage form"
          >
            ✕
          </button>
        </div>

        <div className="space-y-6 px-6 py-5">
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Action
              </label>
              <select
                value={form.action}
                onChange={(e) => updateForm('action', e.target.value as TriageFinalizeAction)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
              >
                <option value="QUEUE_FOR_CONSULTATION">Queue for consultation</option>
                <option value="REFER_OUT_IMMEDIATE">Refer out immediately</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Complaint severity
              </label>
              <select
                value={form.complaint_severity}
                onChange={(e) =>
                  updateForm('complaint_severity', e.target.value as TriageComplaintSeverity)
                }
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
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
            <label className="mb-2 block text-sm font-medium text-slate-700">
              Acuity level
            </label>
            <div className="grid gap-2 md:grid-cols-3">
              {ACUITY_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className={`cursor-pointer rounded-lg border px-3 py-2 text-sm ${
                    form.acuity_level === option.value
                      ? 'border-blue-500 bg-blue-50 text-blue-900'
                      : 'border-slate-200 bg-white text-slate-700'
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
                  <span className="font-medium">{option.label}</span>
                  <span className="ml-2 text-xs text-slate-500">{option.help}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Input
              label="Chief complaint"
              value={form.chief_complaint}
              onChange={(e) => updateForm('chief_complaint', e.target.value)}
              placeholder="Describe presenting complaint"
            />
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Danger sign codes
              </label>
              <textarea
                value={form.danger_sign_codes}
                onChange={(e) => updateForm('danger_sign_codes', e.target.value)}
                rows={2}
                placeholder="Comma-separated tokens, e.g. RESP_DISTRESS, BLEEDING"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
              />
            </div>
          </section>

          <section>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Triage note
            </label>
            <textarea
              value={form.triage_note}
              onChange={(e) => updateForm('triage_note', e.target.value)}
              rows={3}
              placeholder="Clinical note for triage decision"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
          </section>

          <section>
            <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
              Vitals
            </h4>
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
              <Input
                label="Temp (C)"
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
                label="Resp rate"
                value={form.rr_bpm}
                onChange={(e) => updateForm('rr_bpm', e.target.value)}
                placeholder="18"
              />
              <Input
                label="SBP (mmHg)"
                value={form.sbp_mmhg}
                onChange={(e) => updateForm('sbp_mmhg', e.target.value)}
                placeholder="120"
              />
              <Input
                label="DBP (mmHg)"
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
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Missing vitals reason
                </label>
                <select
                  value={form.missing_vitals_reason_code}
                  onChange={(e) =>
                    updateForm(
                      'missing_vitals_reason_code',
                      e.target.value as '' | TriageMissingVitalReasonCode
                    )
                  }
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
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
            <section className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <h4 className="text-sm font-semibold text-amber-900">Doctor fallback</h4>
              <p className="mt-1 text-xs text-amber-800">
                Doctor triage is fallback-only and requires explicit reason.
              </p>
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-amber-900">
                    Fallback reason
                  </label>
                  <select
                    value={form.fallback_reason_code}
                    onChange={(e) =>
                      updateForm(
                        'fallback_reason_code',
                        e.target.value as '' | TriageFallbackReasonCode
                      )
                    }
                    className="w-full rounded-md border border-amber-300 bg-white px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
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
                    <label className="mb-1 block text-sm font-medium text-amber-900">
                      Reason text
                    </label>
                    <textarea
                      value={form.fallback_reason_text}
                      onChange={(e) => updateForm('fallback_reason_text', e.target.value)}
                      rows={2}
                      className="w-full rounded-md border border-amber-300 bg-white px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                      placeholder="Explain fallback context (min 15 chars)"
                    />
                  </div>
                )}
              </div>
            </section>
          )}

          {form.action === 'REFER_OUT_IMMEDIATE' && (
            <section className="rounded-lg border border-rose-200 bg-rose-50 p-3">
              <h4 className="text-sm font-semibold text-rose-900">Referral details</h4>
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <Input
                  label="Referred facility"
                  value={form.referred_facility}
                  onChange={(e) => updateForm('referred_facility', e.target.value)}
                  placeholder="General Hospital ..."
                />
                <div>
                  <label className="mb-1 block text-sm font-medium text-rose-900">
                    Referral reason
                  </label>
                  <textarea
                    value={form.referral_reason}
                    onChange={(e) => updateForm('referral_reason', e.target.value)}
                    rows={2}
                    className="w-full rounded-md border border-rose-300 bg-white px-3 py-2 text-sm focus:border-rose-500 focus:outline-none"
                    placeholder="Clinical reason for immediate referral"
                  />
                </div>
              </div>
            </section>
          )}

          {isSupersede && (
            <section className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <h4 className="text-sm font-semibold text-slate-900">Correction details</h4>
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Correction reason code
                  </label>
                  <select
                    value={form.correction_reason_code}
                    onChange={(e) => updateForm('correction_reason_code', e.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
                  >
                    {CORRECTION_REASON_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Correction note (optional)
                  </label>
                  <textarea
                    value={form.correction_reason_text}
                    onChange={(e) => updateForm('correction_reason_text', e.target.value)}
                    rows={2}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
                    placeholder="Why this triage was superseded"
                  />
                </div>
              </div>
            </section>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4">
          <Button variant="secondary" size="sm" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={handleSubmit} isLoading={submitting}>
            {isSupersede ? 'Update Triage' : 'Finalize Triage'}
          </Button>
        </div>
      </div>
    </div>
  );
}
