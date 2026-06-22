'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { consultationService } from '@/domains/consultation/services/consultationService';
import { followUpService, RecallIntervalUnit } from '@/domains/followup/services/followupService';
import { ConsultationResponse, RecallSuggestionDTO } from '@/shared/types';
import { jsonUtils } from '@/shared/utils/json';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';

interface ConsultationModalProps {
  visitId: string;
  visitSummary?: {
    patientName?: string | null;
    patientId?: string | null;
    status?: string | null;
    mrn?: string | null;
    intakeEmergencyFlag?: boolean | null;
    linkedFollowUpId?: string | null;
  };
  isOpen: boolean;
  onClose: () => void;
  onComplete?: (consultationId: string) => void;
  onConsultationReady?: (
    visitId: string,
    consultation: ConsultationResponse
  ) => void;
  existingConsultation?: ConsultationResponse | null;
}

type VitalsField = {
  label: string;
  key: string;
  unit?: string;
  placeholder?: string;
};

const VITALS_FIELDS: VitalsField[] = [
  { label: 'Blood Pressure', key: 'blood_pressure', placeholder: '120/80' },
  { label: 'Heart Rate', key: 'heart_rate', unit: 'bpm', placeholder: '72' },
  { label: 'Temperature', key: 'temperature', unit: 'C', placeholder: '36.6' },
  {
    label: 'Respiratory Rate',
    key: 'respiratory_rate',
    unit: 'breaths/min',
    placeholder: '16',
  },
  { label: 'Oxygen Saturation', key: 'spo2', unit: '%', placeholder: '98' },
  { label: 'Weight', key: 'weight', unit: 'kg', placeholder: '70' },
  { label: 'Height', key: 'height', unit: 'cm', placeholder: '175' },
  { label: 'BMI', key: 'bmi', placeholder: '22.9' },
];

export function ConsultationModal({
  visitId,
  visitSummary,
  isOpen,
  onClose,
  onComplete,
  onConsultationReady,
  existingConsultation,
}: ConsultationModalProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consultation, setConsultation] =
    useState<ConsultationResponse | null>(existingConsultation || null);

  const [vitals, setVitals] = useState<Record<string, string>>({});
  const [presentingComplaints, setPresentingComplaints] = useState('');
  const [diagnosis, setDiagnosis] = useState('');
  const [notes, setNotes] = useState('');
  const [doctorFullName, setDoctorFullName] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [recallSuggestions, setRecallSuggestions] = useState<RecallSuggestionDTO[]>([]);
  const [recallActionError, setRecallActionError] = useState<string | null>(null);
  const [recallActionSuccess, setRecallActionSuccess] = useState<string | null>(null);
  const [recallSubmittingId, setRecallSubmittingId] = useState<string | null>(null);
  const [adjustingSuggestionId, setAdjustingSuggestionId] = useState<string | null>(null);
  const [overrideIntervalValue, setOverrideIntervalValue] = useState<string>('');
  const [overrideIntervalUnit, setOverrideIntervalUnit] =
    useState<RecallIntervalUnit>('MONTHS');
  const canStartConsultation =
    !visitSummary?.status ||
    ['IN_CONSULTATION', 'LAB_REQUESTED', 'LAB_COMPLETED', 'PHARMACY_PENDING'].includes(
      visitSummary.status
    );
  const getErrorResponse = useCallback((err: unknown) => {
    if (typeof err !== 'object' || err === null) {
      return undefined;
    }
    if ('response' in err) {
      return (err as { response?: { status?: number; data?: { detail?: string } } })
        .response;
    }
    return undefined;
  }, []);

  const populateForm = useCallback((consultationData: ConsultationResponse) => {
    const parsedVitals = jsonUtils.parseVitals(consultationData.vitals) || {};
    setVitals(parsedVitals as Record<string, string>);

    setPresentingComplaints(consultationData.presenting_complaints || '');
    setDiagnosis(consultationData.diagnosis || '');
    setNotes(consultationData.notes || '');
    setDoctorFullName(consultationData.doctor_full_name || '');
    setIsCompleted(consultationData.completed_at !== null);
    setRecallSuggestions(consultationData.recall_suggestions || []);
    setIsDirty(false);
  }, []);

  const loadConsultation = useCallback(async () => {
    if (consultation && isDirty) {
      return;
    }
    if (existingConsultation) {
      setConsultation(existingConsultation);
      populateForm(existingConsultation);
      if (onConsultationReady) {
        onConsultationReady(visitId, existingConsultation);
      }
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data = await consultationService.getConsultationByVisit(visitId);
      if (data) {
        setConsultation(data);
        populateForm(data);
        if (onConsultationReady) {
          onConsultationReady(visitId, data);
        }
      }
    } catch (err: unknown) {
      const response = getErrorResponse(err);
      if (response?.status !== 404) {
        console.error('Failed to load consultation:', err);
        setError('Unable to load consultation data');
      }
      if (response?.status === 409) {
        setError('Visit must be in consultation before you can start notes.');
      }
    } finally {
      setLoading(false);
    }
  }, [
    consultation,
    isDirty,
    existingConsultation,
    getErrorResponse,
    onConsultationReady,
    populateForm,
    visitId,
  ]);

  const loadConsultationRef = useRef(loadConsultation);

  useEffect(() => {
    loadConsultationRef.current = loadConsultation;
  }, [loadConsultation]);

  useEffect(() => {
    if (isOpen && visitId) {
      loadConsultationRef.current();
    }
  }, [isOpen, visitId]);

  const handleVitalChange = (key: string, value: string) => {
    setVitals((prev) => ({
      ...prev,
      [key]: value,
    }));
    setIsDirty(true);
  };

  const getOrCreateConsultation = async () => {
    const existing = await consultationService.getConsultationByVisit(visitId);
    if (existing) {
      return existing;
    }

    try {
      return await consultationService.startConsultation(visitId);
    } catch (err: unknown) {
      const response = getErrorResponse(err);
      if (response?.status === 400 || response?.status === 409) {
        const retry = await consultationService.getConsultationByVisit(visitId);
        if (retry) {
          return retry;
        }
      }
      throw err;
    }
  };

  const handleSave = async (complete = false) => {
    try {
      setSaving(true);
      setError(null);

      if (complete) {
        const missingFields = [];
        if (!doctorFullName.trim()) missingFields.push('Doctor Full Name');
        if (!presentingComplaints.trim()) missingFields.push('Presenting Complaints');
        if (!diagnosis.trim()) missingFields.push('Diagnosis');
        if (!notes.trim()) missingFields.push('Clinical Notes');

        if (missingFields.length > 0) {
          setError(
            `Complete all required fields before finalizing: ${missingFields.join(
              ', '
            )}.`
          );
          return;
        }
      }

      const updateData = consultationService.prepareUpdateData({
        vitals,
        presenting_complaints: presentingComplaints,
        diagnosis,
        notes,
        doctor_full_name: doctorFullName,
      });

      if (consultation) {
        const updated = await consultationService.updateConsultation(
          consultation.id,
          updateData
        );

        setConsultation(updated);
        setIsDirty(false);

        if (complete) {
          const completed = await consultationService.completeConsultation(
            consultation.id,
            { linked_follow_up_id: visitSummary?.linkedFollowUpId || undefined }
          );
          setConsultation(completed);
          setIsCompleted(true);
          setRecallSuggestions(completed.recall_suggestions || []);
          setRecallActionError(null);
          setRecallActionSuccess(null);

          if (onComplete) {
            onComplete(completed.id);
          }
        }
      } else {
        const newConsultation = await getOrCreateConsultation();
        setConsultation(newConsultation);
        if (onConsultationReady) {
          onConsultationReady(visitId, newConsultation);
        }

        const updated = await consultationService.updateConsultation(
          newConsultation.id,
          updateData
        );
        setConsultation(updated);
        setIsDirty(false);

        if (complete) {
          const completed = await consultationService.completeConsultation(
            newConsultation.id,
            { linked_follow_up_id: visitSummary?.linkedFollowUpId || undefined }
          );
          setConsultation(completed);
          setIsCompleted(true);
          setRecallSuggestions(completed.recall_suggestions || []);
          setRecallActionError(null);
          setRecallActionSuccess(null);

          if (onComplete) {
            onComplete(completed.id);
          }
        }
      }
    } catch (err: unknown) {
      console.error('Failed to save consultation:', err);
      const response = getErrorResponse(err);
      if (response?.status === 403) {
        setError('You do not have permission to update this consultation');
      } else if (response?.status === 400) {
        setError(response?.data?.detail || 'Invalid consultation data');
      } else if (response?.status === 404) {
        setError('Consultation or visit not found');
      } else if (response?.status === 409) {
        setError('Cannot modify completed consultation');
      } else {
        setError('Failed to save consultation. Please try again.');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleStartConsultation = async () => {
    try {
      setSaving(true);
      setError(null);

      if (!canStartConsultation) {
        setError('Visit must be in consultation before you can start notes.');
        return;
      }

      const newConsultation = await getOrCreateConsultation();
      setConsultation(newConsultation);
      if (onConsultationReady) {
        onConsultationReady(visitId, newConsultation);
      }
    } catch (err: unknown) {
      console.error('Failed to start consultation:', err);
      const response = getErrorResponse(err);
      if (response?.status === 403) {
        setError('You do not have permission to start consultation');
      } else if (response?.status === 400) {
        setError(
          response?.data?.detail ||
            'Cannot start consultation for this visit status'
        );
      } else if (response?.status === 409) {
        setError('Visit must be in consultation before you can start notes.');
      } else if (response?.status === 404) {
        setError('Visit not found');
      } else {
        setError('Failed to start consultation. Please try again.');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    if (isDirty && !isCompleted && !saving) {
      const confirmClose = window.confirm(
        'You have unsaved changes. Close without saving?'
      );
      if (!confirmClose) {
        return;
      }
    }
    onClose();
  };

  const removeSuggestion = (conditionProfileId: string) => {
    setRecallSuggestions((prev) =>
      prev.filter((item) => item.condition_profile_id !== conditionProfileId)
    );
    if (adjustingSuggestionId === conditionProfileId) {
      setAdjustingSuggestionId(null);
    }
  };

  const handleStartRecall = async (
    suggestion: RecallSuggestionDTO,
    options?: { intervalValueOverride?: number; intervalUnitOverride?: RecallIntervalUnit }
  ) => {
    if (!visitSummary?.patientId) {
      setRecallActionError('Patient context is missing for recall creation.');
      return;
    }
    try {
      setRecallActionError(null);
      setRecallActionSuccess(null);
      setRecallSubmittingId(suggestion.condition_profile_id);
      await followUpService.createChronicRecall({
        patient_id: visitSummary.patientId,
        condition_profile_id: suggestion.condition_profile_id,
        origin_visit_id: visitId,
        interval_value_override: options?.intervalValueOverride,
        interval_unit_override: options?.intervalUnitOverride,
        justification: 'Consultation recall suggestion accepted',
      });
      removeSuggestion(suggestion.condition_profile_id);
      setRecallActionSuccess(`${suggestion.display_name} recall started.`);
      setOverrideIntervalValue('');
      setAdjustingSuggestionId(null);
    } catch (err: unknown) {
      const response = getErrorResponse(err);
      if (response?.status === 409) {
        setRecallActionError('An active recall already exists for this condition.');
        removeSuggestion(suggestion.condition_profile_id);
        return;
      }
      if (response?.status === 403) {
        setRecallActionError('Recall creation requires assigned active visit context.');
        return;
      }
      setRecallActionError('Unable to start recall. Please try again.');
    } finally {
      setRecallSubmittingId(null);
    }
  };

  const handleAdjustRecall = async (suggestion: RecallSuggestionDTO) => {
    const parsedValue = Number.parseInt(overrideIntervalValue, 10);
    if (!Number.isFinite(parsedValue) || parsedValue < 1) {
      setRecallActionError('Enter a valid interval value (minimum 1).');
      return;
    }
    await handleStartRecall(suggestion, {
      intervalValueOverride: parsedValue,
      intervalUnitOverride: overrideIntervalUnit,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
      <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 shadow-2xl">
        <div className="border-b border-slate-200 bg-white px-6 py-5">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0B4DA2]">
                Clinical Encounter Record
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-slate-950">
                {consultation ? 'Consultation' : 'Start Consultation'}
              </h2>
              <div className="mt-3 rounded-xl border border-blue-100 bg-[#F5FAFE] px-3 py-2 text-sm text-slate-700">
                <span className="font-semibold text-slate-950">
                  {visitSummary?.patientName || 'Unknown patient'}
                </span>
                <span className="text-slate-500">
                  {' '}
                  • Visit {visitId.substring(0, 12)}...
                </span>
                {visitSummary?.status && (
                  <span className="text-slate-500">
                    {' '}
                    • Status {visitSummary.status}
                  </span>
                )}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                {visitSummary?.mrn ? (
                  <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 font-semibold text-slate-700">
                    MRN {visitSummary.mrn}
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 font-semibold text-slate-500">
                    ID {visitId.substring(0, 6)}…{visitId.substring(visitId.length - 4)}
                  </span>
                )}
                {visitSummary?.intakeEmergencyFlag && (
                  <span className="inline-flex items-center rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 font-semibold text-rose-800">
                    Emergency flagged
                  </span>
                )}
              </div>
              {isCompleted && (
                <div className="mt-2 inline-flex items-center rounded-full border border-blue-100 bg-[#E6F4FB] px-2.5 py-0.5 text-xs font-semibold text-[#0B4DA2]">
                  Consultation completed (read-only)
                </div>
              )}
            </div>
            <button
              onClick={handleClose}
              className="text-2xl text-slate-400 hover:text-slate-600"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="p-6">

          {error && (
            <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 p-4">
              <p className="text-rose-700">{error}</p>
            </div>
          )}

          {loading && !consultation && (
            <div className="space-y-4">
              <div className="h-8 w-1/3 animate-pulse rounded bg-slate-200"></div>
              <div className="grid grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-200"></div>
                ))}
              </div>
            </div>
          )}

          {!consultation && !loading && (
            <Card>
              <div className="text-center py-8">
                <div className="mb-4 inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
                  Consultation
                </div>
                <h3 className="mb-2 text-lg font-semibold text-slate-950">
                  No Consultation Started
                </h3>
                <p className="mb-6 text-slate-600">
                  Start a consultation to record medical notes and vitals for
                  this patient.
                </p>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={handleStartConsultation}
                  isLoading={saving}
                  disabled={saving || !canStartConsultation}
                >
                  Start Consultation
                </Button>
                {!canStartConsultation && (
                  <p className="mt-3 text-xs text-amber-700">
                    Visit must be IN_CONSULTATION before you can start notes.
                  </p>
                )}
              </div>
            </Card>
          )}

          {consultation && (
            <div className="space-y-6">
              <Card title="Attending Clinician">
                  <Input
                    label="Doctor Full Name"
                    value={doctorFullName}
                    onChange={(e) => {
                      setDoctorFullName(e.target.value);
                      setIsDirty(true);
                    }}
                    placeholder="Enter full name for clinical record"
                    disabled={isCompleted || saving}
                  />
                </Card>

              <Card title="Vitals">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {VITALS_FIELDS.map((field) => (
                    <div key={field.key}>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {field.label}
                        {field.unit && (
                          <span className="text-gray-500 ml-1">
                            ({field.unit})
                          </span>
                        )}
                      </label>
                      <Input
                        value={vitals[field.key] || ''}
                        onChange={(e) =>
                          handleVitalChange(field.key, e.target.value)
                        }
                        placeholder={field.placeholder}
                        disabled={isCompleted || saving}
                      />
                    </div>
                  ))}
                </div>
              </Card>

              <Card title="Presenting Complaints">
                <textarea
                  value={presentingComplaints}
                  onChange={(e) => {
                    setPresentingComplaints(e.target.value);
                    setIsDirty(true);
                  }}
                  placeholder="Describe the patient's chief complaints, symptoms, and history..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-h-[100px]"
                  disabled={isCompleted || saving}
                />
              </Card>

              <Card title="Diagnosis">
                <textarea
                  value={diagnosis}
                  onChange={(e) => {
                    setDiagnosis(e.target.value);
                    setIsDirty(true);
                  }}
                  placeholder="Enter diagnosis, differential diagnosis, or clinical impression..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-h-[80px]"
                  disabled={isCompleted || saving}
                />
              </Card>

              <Card title="Clinical Notes">
                <textarea
                  value={notes}
                  onChange={(e) => {
                    setNotes(e.target.value);
                    setIsDirty(true);
                  }}
                  placeholder="Additional clinical notes, observations, or follow-up instructions..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-h-[120px]"
                  disabled={isCompleted || saving}
                />
              </Card>

              <div className="flex justify-between pt-6 border-t">
                <div className="flex space-x-3">
                  <Button
                    variant="secondary"
                    onClick={handleClose}
                    disabled={saving}
                  >
                    Close
                  </Button>
                  {!isCompleted && (
                    <Button
                      variant="primary"
                      onClick={() => handleSave(false)}
                      isLoading={saving}
                      disabled={saving}
                    >
                      Save Draft
                    </Button>
                  )}
                </div>

                {!isCompleted && (
                  <div className="flex flex-col items-end gap-2">
                    <span className="text-xs font-medium text-rose-700">
                      Completing locks this record: no edits, lab orders, or prescriptions.
                    </span>
                    <Button
                      variant="primary"
                      onClick={() => handleSave(true)}
                      isLoading={saving}
                      disabled={saving}
                    >
                      Complete Consultation
                    </Button>
                  </div>
                )}
              </div>

              {isCompleted && (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                  Consultation is completed and locked for edits.
                </div>
              )}

              {isCompleted && recallSuggestions.length > 0 && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-emerald-900">
                      Standing Recall Suggestions
                    </h3>
                    <span className="text-xs text-emerald-700">
                      Structured-first, fallback-aware
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-emerald-800">
                    Choose whether to start long-term recall for detected chronic conditions.
                  </p>

                  {recallActionError && (
                    <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                      {recallActionError}
                    </div>
                  )}
                  {recallActionSuccess && (
                    <div className="mt-3 rounded-md border border-emerald-300 bg-emerald-100 px-3 py-2 text-sm text-emerald-800">
                      {recallActionSuccess}
                    </div>
                  )}

                  <div className="mt-3 space-y-3">
                    {recallSuggestions.map((suggestion) => (
                      <div
                        key={suggestion.condition_profile_id}
                        className="rounded-md border border-emerald-200 bg-white p-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <p className="text-sm font-semibold text-slate-900">
                              Chronic condition detected: {suggestion.display_name}
                            </p>
                            <p className="text-xs text-slate-600">
                              Suggested interval: {suggestion.default_interval_value}{' '}
                              {suggestion.default_interval_unit.toLowerCase()} • Confidence{' '}
                              {suggestion.confidence}
                            </p>
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <Button
                              variant="primary"
                              size="sm"
                              isLoading={
                                recallSubmittingId === suggestion.condition_profile_id
                              }
                              disabled={saving || recallSubmittingId !== null}
                              onClick={() => handleStartRecall(suggestion)}
                            >
                              Start Recall
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              disabled={saving || recallSubmittingId !== null}
                              onClick={() => {
                                setRecallActionError(null);
                                setRecallActionSuccess(null);
                                setAdjustingSuggestionId((prev) =>
                                  prev === suggestion.condition_profile_id
                                    ? null
                                    : suggestion.condition_profile_id
                                );
                                setOverrideIntervalValue(
                                  String(suggestion.default_interval_value)
                                );
                                setOverrideIntervalUnit(suggestion.default_interval_unit);
                              }}
                            >
                              Adjust Interval
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              disabled={saving || recallSubmittingId !== null}
                              onClick={() => removeSuggestion(suggestion.condition_profile_id)}
                            >
                              Not Now
                            </Button>
                          </div>
                        </div>

                        {adjustingSuggestionId === suggestion.condition_profile_id && (
                          <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3">
                            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                              Adjust recall interval
                            </p>
                            <div className="mt-2 grid gap-2 sm:grid-cols-[120px_1fr_auto]">
                              <Input
                                value={overrideIntervalValue}
                                onChange={(event) =>
                                  setOverrideIntervalValue(event.target.value)
                                }
                                placeholder="Value"
                                disabled={recallSubmittingId !== null}
                              />
                              <select
                                value={overrideIntervalUnit}
                                disabled={recallSubmittingId !== null}
                                onChange={(event) =>
                                  setOverrideIntervalUnit(
                                    event.target.value as RecallIntervalUnit
                                  )
                                }
                                className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#0B4DA2]"
                              >
                                <option value="DAYS">Days</option>
                                <option value="WEEKS">Weeks</option>
                                <option value="MONTHS">Months</option>
                              </select>
                              <Button
                                variant="primary"
                                size="sm"
                                disabled={recallSubmittingId !== null}
                                onClick={() => handleAdjustRecall(suggestion)}
                              >
                                Confirm
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {consultation && (
                <div className="text-sm text-gray-500 pt-4 border-t">
                  <p>
                    <span className="font-medium">Consultation ID:</span>{' '}
                    {consultation.id.substring(0, 12)}...
                  </p>
                  <p>
                    <span className="font-medium">Doctor:</span>{' '}
                    {doctorFullName || '—'}
                  </p>
                  <p>
                    <span className="font-medium">Started:</span>{' '}
                    {new Date(consultation.started_at).toLocaleString()}
                  </p>
                  {consultation.completed_at && (
                    <p>
                      <span className="font-medium">Completed:</span>{' '}
                      {new Date(consultation.completed_at).toLocaleString()}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
