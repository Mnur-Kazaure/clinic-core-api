'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  patientCreateSchema,
  PatientCreateFormData,
} from '@/domains/patient/schemas/patientSchema';
import { patientService } from '@/domains/patient/services/patientService';
import { Input } from '@/shared/Input';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';

interface PatientRegistrationFormProps {
  onSuccess?: (mrn?: string | null, patientName?: string | null) => void;
  onCancel?: () => void;
  compact?: boolean;
}

const OCCUPATION_OPTIONS = [
  'Under care',
  'Housewife',
  'Widow',
  'Divorcee',
  'Civil servant',
  'Public servant',
  'Farming',
  'Business',
  'Unknown',
  'Other',
] as const;

export function PatientRegistrationForm({
  onSuccess,
  onCancel,
  compact = false,
}: PatientRegistrationFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [issuedMrn, setIssuedMrn] = useState<string | null>(null);
  const [isProvisional, setIsProvisional] = useState(false);
  const [provisionalReason, setProvisionalReason] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    getValues,
  } = useForm<PatientCreateFormData>({
    resolver: zodResolver(patientCreateSchema),
    defaultValues: {
      gender: 'MALE',
    },
  });

  const onSubmit = async (data: PatientCreateFormData) => {
    try {
      setIsSubmitting(true);
      setSubmitError(null);

      const payload: Parameters<typeof patientService.createPatient>[0] = { ...data };
      if (isProvisional) {
        const trimmedReason = provisionalReason.trim();
        if (trimmedReason.length < 3) {
          setSubmitError('Reason for provisional registration is required.');
          return;
        }
        if (!payload.address.trim()) {
          payload.address = 'Unknown';
        }
        if (!payload.occupation.trim()) {
          payload.occupation = 'Unknown';
        }
        payload.identity_state = 'PROVISIONAL';
        payload.created_reason = trimmedReason;
      }

      const patient = await patientService.createPatient(payload);

      setSubmitSuccess(true);
      setIssuedMrn(patient.patient_mrn ?? null);
      reset();
      setIsProvisional(false);
      setProvisionalReason('');

      if (onSuccess) {
        onSuccess(patient.patient_mrn ?? null, patient.full_name ?? null);
      }

      setTimeout(() => {
        setSubmitSuccess(false);
        setIssuedMrn(null);
      }, 12000);
    } catch (error: unknown) {
      console.error('Patient registration failed:', error);
      const detail =
        typeof error === 'object' && error && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setSubmitError(detail || 'Failed to register patient. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleProvisionalToggle = (checked: boolean) => {
    setIsProvisional(checked);
    if (checked) {
      const address = getValues('address');
      const occupation = getValues('occupation');
      if (!address?.trim()) {
        setValue('address', 'Unknown', { shouldValidate: true });
      }
      if (!occupation?.trim()) {
        setValue('occupation', 'Unknown', { shouldValidate: true });
      }
    }
  };

  const fieldErrors = Object.values(errors)
    .map((error) => error?.message)
    .filter(Boolean) as string[];

  if (compact) {
    return (
      <Card
        title="Register New Patient"
        titleClassName="text-[#0B4DA2]"
        className="max-w-md"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {fieldErrors.length > 0 && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm font-medium text-red-700">
                Please fix {fieldErrors.length} field
                {fieldErrors.length !== 1 ? 's' : ''} below.
              </p>
            </div>
          )}
        {submitError && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{submitError}</p>
          </div>
        )}
        {submitSuccess && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-md">
            <p className="text-sm text-green-600">
              ✅ Patient registered successfully!
            </p>
            {issuedMrn && (
              <p className="text-xs text-green-700 mt-1">MRN: {issuedMrn}</p>
            )}
          </div>
        )}

        <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <label className="inline-flex items-center">
            <input
              type="checkbox"
              checked={isProvisional}
              onChange={(e) => handleProvisionalToggle(e.target.checked)}
              className="h-4 w-4 text-blue-600"
            />
            <span className="ml-2 text-sm text-slate-700">
              Provisional registration (unknown details)
            </span>
          </label>
          <p className="mt-1 text-xs text-slate-500">
            Use when address/occupation are unknown. You can update later.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Phone number is still required for follow-up.
          </p>
          {isProvisional && (
            <div className="mt-3 space-y-3">
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Reason for provisional registration
              </label>
              <input
                type="text"
                value={provisionalReason}
                onChange={(e) => setProvisionalReason(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Unconscious arrival"
              />
              <div className="flex flex-wrap gap-2">
                {[
                  'Unconscious arrival',
                  'No ID available',
                  'Child without guardian',
                  'Emergency admission',
                ].map((reason) => (
                  <button
                    key={reason}
                    type="button"
                    onClick={() => setProvisionalReason(reason)}
                    className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700 hover:border-blue-300 hover:text-blue-700"
                  >
                    {reason}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <Input
          label="Full Name *"
          {...register('full_name')}
          error={errors.full_name?.message}
          placeholder="John Doe"
          />

          <Input
            label="Date of Birth *"
            type="date"
            {...register('date_of_birth')}
            error={errors.date_of_birth?.message}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Gender *
            </label>
            <div className="flex space-x-4">
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  value="MALE"
                  {...register('gender')}
                  className="h-4 w-4 text-blue-600"
                />
                <span className="ml-2 text-gray-700">Male</span>
              </label>
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  value="FEMALE"
                  {...register('gender')}
                  className="h-4 w-4 text-blue-600"
                />
                <span className="ml-2 text-gray-700">Female</span>
              </label>
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  value="UNKNOWN"
                  {...register('gender')}
                  className="h-4 w-4 text-blue-600"
                />
                <span className="ml-2 text-gray-700">Unknown</span>
              </label>
            </div>
            {errors.gender && (
              <p className="mt-1 text-sm text-red-600">
                {errors.gender.message}
              </p>
            )}
          </div>

          <Input
            label="Phone Number *"
            {...register('phone_number')}
            error={errors.phone_number?.message}
            placeholder="+1234567890"
          />

          <Input
            label="Address *"
            {...register('address')}
            error={errors.address?.message}
            placeholder="123 Main Street, City"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Occupation *
            </label>
            <select
              {...register('occupation')}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              defaultValue=""
            >
              <option value="" disabled>
                Select occupation
              </option>
              {OCCUPATION_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            {errors.occupation && (
              <p className="mt-1 text-sm text-red-600">
                {errors.occupation.message}
              </p>
            )}
          </div>

          <div className="flex space-x-3 pt-4">
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              disabled={isSubmitting}
              className="flex-1"
            >
              Register Patient
            </Button>
            {onCancel && (
              <Button
                type="button"
                variant="secondary"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            )}
          </div>
        </form>
      </Card>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Patient Registration
        </h1>
        <p className="text-gray-600 mt-2">
          Register a new patient for the clinic
        </p>
      </div>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {fieldErrors.length > 0 && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="font-medium text-red-700">
                Please fix {fieldErrors.length} field
                {fieldErrors.length !== 1 ? 's' : ''} below.
              </p>
            </div>
          )}
          {submitError && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">{submitError}</p>
            </div>
          )}

          {submitSuccess && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-md">
              <p className="text-green-600 font-medium">
                ✅ Patient registered successfully!
              </p>
              <p className="text-green-600 text-sm mt-1">
                You can now start a visit for this patient.
              </p>
              {issuedMrn && (
                <p className="text-green-700 text-sm mt-2">
                  MRN: {issuedMrn}
                </p>
              )}
            </div>
          )}

          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <label className="inline-flex items-center">
              <input
                type="checkbox"
                checked={isProvisional}
                onChange={(e) => handleProvisionalToggle(e.target.checked)}
                className="h-4 w-4 text-blue-600"
              />
              <span className="ml-2 text-sm text-slate-700">
                Provisional registration (unknown details)
              </span>
            </label>
            <p className="mt-1 text-xs text-slate-500">
              Use when address/occupation are unknown. You can update later.
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Phone number is still required for follow-up.
            </p>
            {isProvisional && (
              <div className="mt-3 space-y-3">
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Reason for provisional registration
                </label>
                <input
                  type="text"
                  value={provisionalReason}
                  onChange={(e) => setProvisionalReason(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Unconscious arrival"
                />
                <div className="flex flex-wrap gap-2">
                  {[
                    'Unconscious arrival',
                    'No ID available',
                    'Child without guardian',
                    'Emergency admission',
                  ].map((reason) => (
                    <button
                      key={reason}
                      type="button"
                      onClick={() => setProvisionalReason(reason)}
                      className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700 hover:border-blue-300 hover:text-blue-700"
                    >
                      {reason}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Input
              label="Full Name *"
              {...register('full_name')}
              error={errors.full_name?.message}
              placeholder="John Doe"
            />

            <Input
              label="Date of Birth *"
              type="date"
              {...register('date_of_birth')}
              error={errors.date_of_birth?.message}
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Gender *
              </label>
              <div className="flex space-x-4">
                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    value="MALE"
                    {...register('gender')}
                    className="h-4 w-4 text-blue-600"
                  />
                  <span className="ml-2 text-gray-700">Male</span>
                </label>
                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    value="FEMALE"
                    {...register('gender')}
                    className="h-4 w-4 text-blue-600"
                  />
                  <span className="ml-2 text-gray-700">Female</span>
                </label>
                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    value="UNKNOWN"
                    {...register('gender')}
                    className="h-4 w-4 text-blue-600"
                  />
                  <span className="ml-2 text-gray-700">Unknown</span>
                </label>
              </div>
              {errors.gender && (
                <p className="mt-1 text-sm text-red-600">
                  {errors.gender.message}
                </p>
              )}
            </div>

            <Input
              label="Phone Number *"
              {...register('phone_number')}
              error={errors.phone_number?.message}
              placeholder="+1234567890"
            />

            <div className="md:col-span-2">
              <Input
                label="Address *"
                {...register('address')}
                error={errors.address?.message}
                placeholder="123 Main Street, City, State, ZIP"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Occupation *
              </label>
              <select
                {...register('occupation')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                defaultValue=""
              >
                <option value="" disabled>
                  Select occupation
                </option>
                {OCCUPATION_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              {errors.occupation && (
                <p className="mt-1 text-sm text-red-600">
                  {errors.occupation.message}
                </p>
              )}
            </div>
          </div>

          <div className="flex space-x-4 pt-6 border-t">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isSubmitting}
              disabled={isSubmitting}
              className="px-8"
            >
              Register Patient
            </Button>
            {onCancel && (
              <Button
                type="button"
                variant="secondary"
                size="lg"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              size="lg"
              onClick={() => reset()}
              disabled={isSubmitting}
            >
              Reset Form
            </Button>
          </div>

          <div className="text-sm text-gray-500 pt-4 border-t">
            <p className="font-medium">Note:</p>
            <ul className="list-disc pl-5 mt-1 space-y-1">
              <li>All fields marked with * are required</li>
              <li>Patient will be registered under your clinic</li>
              <li>You can start a visit immediately after registration</li>
            </ul>
          </div>
        </form>
      </Card>
    </div>
  );
}
