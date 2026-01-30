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
  onSuccess?: (patientId: string) => void;
  onCancel?: () => void;
  compact?: boolean;
}

export function PatientRegistrationForm({
  onSuccess,
  onCancel,
  compact = false,
}: PatientRegistrationFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
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

      const patient = await patientService.createPatient(data);

      setSubmitSuccess(true);
      reset();

      if (onSuccess) {
        onSuccess(patient.id);
      }

      setTimeout(() => {
        setSubmitSuccess(false);
      }, 3000);
    } catch (error: any) {
      console.error('Patient registration failed:', error);
      setSubmitError(
        error.response?.data?.detail ||
          'Failed to register patient. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
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
            </div>
          )}

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

          <Input
            label="Occupation *"
            {...register('occupation')}
            error={errors.occupation?.message}
            placeholder="Engineer"
          />

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
            </div>
          )}

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
              <Input
                label="Occupation *"
                {...register('occupation')}
                error={errors.occupation?.message}
                placeholder="Engineer"
              />
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
