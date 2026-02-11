'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { consultationService } from '@/domains/consultation/services/consultationService';
import { ConsultationResponse } from '@/shared/types';
import { jsonUtils } from '@/shared/utils/json';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';

interface ConsultationModalProps {
  visitId: string;
  visitSummary?: {
    patientName?: string | null;
    status?: string | null;
    mrn?: string | null;
    intakeEmergencyFlag?: boolean | null;
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
            consultation.id
          );
          setConsultation(completed);
          setIsCompleted(true);

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
            newConsultation.id
          );
          setConsultation(completed);
          setIsCompleted(true);

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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                {consultation ? 'Consultation' : 'Start Consultation'}
              </h2>
              <div className="mt-2 rounded-md border border-blue-100 bg-[#F5FAFE] px-3 py-2 text-sm text-gray-700">
                <span className="font-medium text-gray-900">
                  {visitSummary?.patientName || 'Unknown patient'}
                </span>
                <span className="text-gray-500">
                  {' '}
                  • Visit {visitId.substring(0, 12)}...
                </span>
                {visitSummary?.status && (
                  <span className="text-gray-500">
                    {' '}
                    • Status {visitSummary.status}
                  </span>
                )}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-600">
                {visitSummary?.mrn ? (
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
                    MRN {visitSummary.mrn}
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-full bg-slate-50 px-2 py-0.5 font-medium text-slate-500">
                    ID {visitId.substring(0, 6)}…{visitId.substring(visitId.length - 4)}
                  </span>
                )}
                {visitSummary?.intakeEmergencyFlag && (
                  <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 font-medium text-red-800">
                    Emergency flagged
                  </span>
                )}
              </div>
              {isCompleted && (
                <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#E6F4FB] text-[#0B4DA2] mt-1">
                  Consultation completed (read-only)
                </div>
              )}
            </div>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ✕
            </button>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {loading && !consultation && (
            <div className="space-y-4">
              <div className="animate-pulse h-8 bg-gray-200 rounded w-1/3"></div>
              <div className="grid grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="animate-pulse h-20 bg-gray-200 rounded"></div>
                ))}
              </div>
            </div>
          )}

          {!consultation && !loading && (
            <Card>
              <div className="text-center py-8">
                <div className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-medium text-gray-700 mb-4">
                  Consultation
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No Consultation Started
                </h3>
                <p className="text-gray-600 mb-6">
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
                    <span className="text-xs text-red-600">
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
                <div className="rounded-md border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
                  Consultation is completed and locked for edits.
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
