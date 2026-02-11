'use client';

import { useState } from 'react';
import { PatientSearch } from '@/app/reception/components/patient/PatientSearch';
import { PatientRegistrationForm } from '@/app/reception/components/patient/PatientRegistrationForm';
import { DoctorSelection } from '@/app/reception/components/visit/DoctorSelection';
import { visitService } from '@/domains/visit/services/visitService';
import { PatientResponse } from '@/domains/patient/services/patientService';
import { Doctor } from '@/domains/user/services/userService';
import { VisitResponse } from '@/shared/types';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { PurposeOfUse, VisitServiceLine, UserRole } from '@/shared/enums';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';

interface StartVisitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (visitId: string) => void;
  onContinueVisit?: (visitId: string) => void;
}

type VisitStep = 'SELECT_PATIENT' | 'ASSIGN_DOCTOR' | 'CONFIRM';

export function StartVisitModal({
  isOpen,
  onClose,
  onSuccess,
  onContinueVisit,
}: StartVisitModalProps) {
  const [step, setStep] = useState<VisitStep>('SELECT_PATIENT');
  const [selectedPatient, setSelectedPatient] =
    useState<PatientResponse | null>(null);
  const [selectedDoctorId, setSelectedDoctorId] = useState<string>('');
  const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null);
  const [serviceLine, setServiceLine] = useState<VisitServiceLine>(
    VisitServiceLine.OPD
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRegistrationForm, setShowRegistrationForm] = useState(false);
  const [activeVisit, setActiveVisit] = useState<VisitResponse | null>(null);
  const [checkingActive, setCheckingActive] = useState(false);
  const [activeVisitError, setActiveVisitError] = useState<string | null>(null);

  const assignedRoleLabel =
    serviceLine === VisitServiceLine.ANC
      ? 'CHEW'
      : serviceLine === VisitServiceLine.MATERNITY
      ? 'Midwife'
      : 'Doctor';

  const handlePatientSelect = async (patient: PatientResponse | null) => {
    setSelectedPatient(patient);
    setActiveVisit(null);
    setActiveVisitError(null);
    if (!patient) {
      setStep('SELECT_PATIENT');
      return;
    }
    try {
      setCheckingActive(true);
      const existingVisit = await visitService.getActiveVisit(patient.id);
      if (existingVisit) {
        setActiveVisit(existingVisit);
        setStep('SELECT_PATIENT');
        setError(null);
        return;
      }
      setStep('ASSIGN_DOCTOR');
      setError(null);
    } catch (err) {
      setActiveVisitError(
        'Unable to verify active visits. You can still proceed.'
      );
      setStep('ASSIGN_DOCTOR');
    } finally {
      setCheckingActive(false);
    }
  };

  const handleDoctorSelect = (doctorId: string) => {
    setSelectedDoctorId(doctorId);
    if (doctorId) {
      setStep('CONFIRM');
    }
  };

  const handleSubmit = async () => {
    if (!selectedPatient || !selectedDoctorId) {
      setError('Please select both patient and doctor');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const visit = await visitService.startVisit({
        patient_id: selectedPatient.id,
        assigned_doctor_id: selectedDoctorId,
        service_line: serviceLine,
      });

      if (onSuccess) {
        onSuccess(visit.id);
      }

      resetForm();
      onClose();
    } catch (err: any) {
      console.error('Visit creation failed:', err);

      if (err.response?.status === 409) {
        setError(
          'This patient already has an active visit. Please complete or cancel it first.'
        );
      } else if (err.response?.status === 403) {
        setError('You do not have permission to start visits.');
      } else {
        setError(
          err.response?.data?.detail ||
            'Failed to start visit. Please try again.'
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setStep('SELECT_PATIENT');
    setSelectedPatient(null);
    setSelectedDoctorId('');
    setSelectedDoctor(null);
    setServiceLine(VisitServiceLine.OPD);
    setError(null);
    setShowRegistrationForm(false);
    setActiveVisit(null);
    setActiveVisitError(null);
    setCheckingActive(false);
  };

  const handleCancel = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Start New Visit
            </h2>
            <button
              onClick={handleCancel}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Close start visit"
            >
              ✕
            </button>
          </div>

          <div className="flex items-center justify-between mb-8">
            {['SELECT_PATIENT', 'ASSIGN_DOCTOR', 'CONFIRM'].map((s, index) => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    step === s
                      ? 'bg-blue-600 text-white'
                      : index <
                        ['SELECT_PATIENT', 'ASSIGN_DOCTOR', 'CONFIRM'].indexOf(
                          step
                        )
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {index + 1}
                </div>
                <span className="ml-2 text-sm font-medium">
                  {s === 'SELECT_PATIENT' && 'Select Patient'}
                  {s === 'ASSIGN_DOCTOR' && 'Assign Staff'}
                  {s === 'CONFIRM' && 'Confirm'}
                </span>
                {index < 2 && (
                  <div
                    className={`mx-4 h-0.5 w-12 ${
                      index <
                      ['SELECT_PATIENT', 'ASSIGN_DOCTOR', 'CONFIRM'].indexOf(
                        step
                      )
                        ? 'bg-green-600'
                        : 'bg-gray-300'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {step === 'SELECT_PATIENT' && (
            <div className="space-y-6">
              <Card title="1. Select Patient" titleClassName="text-[#0B4DA2]">
                {showRegistrationForm ? (
                  <div className="space-y-4">
                    <PatientRegistrationForm
                      compact
                      onSuccess={() => {
                        setShowRegistrationForm(false);
                      }}
                      onCancel={() => setShowRegistrationForm(false)}
                    />
                  </div>
                ) : (
                  <div className="space-y-6">
                    <PatientSearch
                      onSelectPatient={handlePatientSelect}
                      disabled={isSubmitting}
                      purposeOfUse={PurposeOfUse.OPERATIONS}
                      searchJustification="Start visit patient lookup"
                    />

                    {checkingActive && (
                      <div className="rounded-md border border-blue-100 bg-blue-50 p-3 text-sm text-blue-700">
                        Checking for active visits...
                      </div>
                    )}

                    {activeVisitError && (
                      <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
                        {activeVisitError}
                      </div>
                    )}

                    {activeVisit && (
                      <div className="rounded-md border border-amber-200 bg-amber-50 p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-semibold text-amber-900">
                              Active visit already exists for this patient
                            </p>
                            <p className="text-xs text-amber-700">
                              Started {new Date(activeVisit.created_at).toLocaleString()}
                            </p>
                          </div>
                          <VisitStatusBadge status={activeVisit.status} size="sm" />
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            variant="primary"
                            onClick={() => {
                              if (onContinueVisit) {
                                onContinueVisit(activeVisit.id);
                              }
                              handleCancel();
                            }}
                          >
                            Continue Visit
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => handlePatientSelect(null)}
                          >
                            Choose Different Patient
                          </Button>
                        </div>
                      </div>
                    )}

                    <div className="border-t pt-4">
                      <div className="text-center">
                        <p className="text-gray-600 mb-3">
                          Can't find the patient?
                        </p>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => setShowRegistrationForm(true)}
                        >
                          Register New Patient
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </Card>

              <div className="flex justify-between">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleCancel}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  onClick={() => {
                    if (selectedPatient) setStep('ASSIGN_DOCTOR');
                  }}
                  disabled={
                    !selectedPatient ||
                    isSubmitting ||
                    checkingActive ||
                    Boolean(activeVisit)
                  }
                >
                  Next: Assign Staff
                </Button>
              </div>
            </div>
          )}

          {step === 'ASSIGN_DOCTOR' && (
            <div className="space-y-6">
              <Card title="2. Assign Staff" titleClassName="text-[#0B4DA2]">
                <div className="space-y-6">
                  {selectedPatient && (
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-slate-900">
                          Selected Patient
                        </p>
                        <span className="text-xs text-slate-500">
                          Selected
                        </span>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Name
                          </div>
                          <div className="mt-1 font-semibold text-slate-900">
                            {selectedPatient.full_name}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Phone
                          </div>
                          <div className="mt-1 font-semibold text-slate-900">
                            {selectedPatient.phone_number}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Date of Birth
                          </div>
                          <div className="mt-1 font-semibold text-slate-900">
                            {selectedPatient.date_of_birth}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Gender
                          </div>
                          <div className="mt-1 font-semibold text-slate-900">
                            {selectedPatient.gender}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Service Line
                    </label>
                    <select
                      value={serviceLine}
                      onChange={(e) => {
                        setServiceLine(e.target.value as VisitServiceLine);
                        setSelectedDoctorId('');
                        setSelectedDoctor(null);
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value={VisitServiceLine.OPD}>Consultation (OPD)</option>
                      <option value={VisitServiceLine.ANC}>ANC</option>
                      <option value={VisitServiceLine.MATERNITY}>Maternity</option>
                    </select>
                    <p className="mt-1 text-xs text-gray-500">
                      Choose where this visit should be routed.
                    </p>
                  </div>

                  <DoctorSelection
                    value={selectedDoctorId}
                    onChange={handleDoctorSelect}
                    onSelectDoctor={setSelectedDoctor}
                    disabled={isSubmitting}
                    role={
                      serviceLine === VisitServiceLine.ANC
                        ? UserRole.CHEW
                        : serviceLine === VisitServiceLine.MATERNITY
                        ? UserRole.MIDWIFE
                        : UserRole.DOCTOR
                    }
                    label={
                      serviceLine === VisitServiceLine.ANC
                        ? 'Assign CHEW *'
                        : serviceLine === VisitServiceLine.MATERNITY
                        ? 'Assign Midwife *'
                        : 'Assign Doctor *'
                    }
                  />
                </div>
              </Card>

              <div className="flex justify-between">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setStep('SELECT_PATIENT')}
                  disabled={isSubmitting}
                >
                  ← Back
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  onClick={() => {
                    if (selectedDoctorId) setStep('CONFIRM');
                  }}
                  disabled={!selectedDoctorId || isSubmitting}
                >
                  Next: Confirm
                </Button>
              </div>
            </div>
          )}

          {step === 'CONFIRM' && (
            <div className="space-y-6">
              <Card title="3. Confirm Visit Details" titleClassName="text-[#0B4DA2]">
                <div className="space-y-6">
                  <div className="rounded-md border border-slate-200 bg-white p-4">
                    <h3 className="text-sm font-semibold text-slate-900 mb-3">
                      Patient Information
                    </h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Name
                        </div>
                        <p className="mt-1 font-semibold text-slate-900">
                          {selectedPatient?.full_name}
                        </p>
                      </div>
                      <div>
                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Phone
                        </div>
                        <p className="mt-1 font-semibold text-slate-900">
                          {selectedPatient?.phone_number}
                        </p>
                      </div>
                      <div>
                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Date of Birth
                        </div>
                        <p className="mt-1 font-semibold text-slate-900">
                          {selectedPatient?.date_of_birth}
                        </p>
                      </div>
                      <div>
                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Gender
                        </div>
                        <p className="mt-1 font-semibold text-slate-900">
                          {selectedPatient?.gender}
                        </p>
                      </div>
                      <div className="col-span-2">
                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Address
                        </div>
                        <p className="mt-1 font-semibold text-slate-900">
                          {selectedPatient?.address}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-md border border-slate-200 bg-white p-4">
                    <h3 className="text-sm font-semibold text-slate-900 mb-3">
                      Assigned {assignedRoleLabel}
                    </h3>
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                          <span className="text-blue-700 font-semibold">
                            {serviceLine === VisitServiceLine.OPD
                              ? 'DR'
                              : serviceLine === VisitServiceLine.ANC
                              ? 'CH'
                              : 'MW'}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-900">
                            {selectedDoctor?.full_name || 'Doctor selected'}
                          </p>
                          {selectedDoctor?.email && (
                            <p className="text-xs text-slate-500">
                              {selectedDoctor.email}
                            </p>
                          )}
                          {selectedDoctor?.specialty && (
                            <p className="text-xs text-slate-600">
                              {selectedDoctor.specialty}
                              {selectedDoctor.department
                                ? ` • ${selectedDoctor.department}`
                                : ''}
                            </p>
                          )}
                          {selectedDoctor?.room_label && (
                            <p className="text-xs text-slate-500">
                              Room: {selectedDoctor.room_label}
                            </p>
                          )}
                          {selectedDoctor?.availability_status && (
                            <p className="text-xs text-slate-500">
                              Status: {selectedDoctor.availability_status}
                            </p>
                          )}
                          <p className="text-xs text-slate-500">
                            ID: {selectedDoctorId.substring(0, 8)}...
                          </p>
                        </div>
                      </div>
                  </div>

                  <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
                    <p className="text-sm text-yellow-800">
                      <span className="font-medium">Important:</span> Starting a
                      visit initiates clinical care. This action creates a legal
                      medical record and assigns responsibility to the selected
                      doctor.
                    </p>
                  </div>
                </div>
              </Card>

              <div className="flex justify-between">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setStep('ASSIGN_DOCTOR')}
                  disabled={isSubmitting}
                >
                  ← Back
                </Button>
                <div className="flex space-x-3">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleCancel}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    variant="primary"
                    onClick={handleSubmit}
                    isLoading={isSubmitting}
                    disabled={isSubmitting}
                  >
                    Start Visit
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
