'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { labService, LabResultCreate } from '@/domains/lab/services/labService';
import { Input } from '@/shared/Input';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';

const labResultSchema = z.object({
  result_value: z.string().trim().min(1, 'Result value is required'),
  result_unit: z.string().optional(),
  reference_range: z.string().optional(),
});

type LabResultFormData = z.infer<typeof labResultSchema>;

interface LabResultFormProps {
  requestId: string;
  technicianId: string;
  testName: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function LabResultForm({
  requestId,
  technicianId,
  testName,
  onSuccess,
  onCancel,
}: LabResultFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<LabResultFormData>({
    resolver: zodResolver(labResultSchema),
  });

  const isQualitativeTest = /hiv|hepatitis|hbsag|hcv|vdrl|pregnancy|mrdt|widal|h\.?\s*pylori|blood grouping|sickling|urinalysis|urine microscopy|stool microscopy|sputum afb/i.test(
    testName
  );

  const normalizeOptional = (value?: string) => {
    const trimmed = (value || '').trim();
    return trimmed.length > 0 ? trimmed : undefined;
  };

  const getErrorDetail = (err: unknown): string | null => {
    if (typeof err !== 'object' || err === null || !('response' in err)) {
      return null;
    }
    return (err as { response?: { data?: { detail?: string } } }).response?.data
      ?.detail || null;
  };

  const getStatusCode = (err: unknown): number | undefined => {
    if (typeof err !== 'object' || err === null || !('response' in err)) {
      return undefined;
    }
    return (err as { response?: { status?: number } }).response?.status;
  };

  const onSubmit = async (data: LabResultFormData) => {
    const normalizedUnit = normalizeOptional(data.result_unit);
    const normalizedReferenceRange = normalizeOptional(data.reference_range);
    if (!isQualitativeTest && (!normalizedUnit || !normalizedReferenceRange)) {
      setError('Unit and reference range are required for quantitative tests.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const payload: LabResultCreate = {
        result_value: data.result_value.trim(),
        result_unit: normalizedUnit,
        reference_range: normalizedReferenceRange,
        technician_id: technicianId,
      };

      await labService.recordResults(requestId, payload);

      setSuccess(true);
      reset();

      if (onSuccess) {
        onSuccess();
      }

      setTimeout(() => {
        setSuccess(false);
      }, 3000);
    } catch (err: unknown) {
      console.error('Failed to record results:', err);
      const statusCode = getStatusCode(err);
      const detail = getErrorDetail(err);

      if (statusCode === 409) {
        setError(
          'This lab request has already been completed. Cannot record new results.'
        );
      } else {
        setError(detail || 'Failed to record results. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const commonUnits = ['mg/dL', 'mmol/L', 'U/L', 'g/dL', 'cells/uL', 'IU/mL'];
  const commonRanges = [
    '3.5 - 6.1 mmol/L',
    '70 - 100 mg/dL',
    '0.5 - 1.2 mg/dL',
    '13.5 - 17.5 g/dL',
    '4.5 - 11.0 x10^3/uL',
    '0 - 5 mg/L',
  ];

  return (
    <Card
      title={`Record Results: ${testName}`}
      titleClassName="text-[#0B4DA2]"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {success && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-md">
            <p className="text-sm text-green-600">
              Results recorded successfully.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="Result Value"
            {...register('result_value')}
            error={errors.result_value?.message}
            placeholder="e.g., 5.2"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Unit {isQualitativeTest ? '(optional)' : '*'}
            </label>
            <select
              {...register('result_unit')}
              className={`
                w-full px-3 py-2 border rounded-md shadow-sm
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                border-gray-300
              `}
            >
              <option value="">{isQualitativeTest ? 'Not applicable' : 'Select unit'}</option>
              {commonUnits.map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Reference Range {isQualitativeTest ? '(optional)' : '*'}
          </label>
          <select
            {...register('reference_range')}
            className={`
              w-full px-3 py-2 border rounded-md shadow-sm
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              border-gray-300
            `}
          >
            <option value="">
              {isQualitativeTest
                ? 'Not applicable'
                : 'Select reference range'}
            </option>
            {commonRanges.map((range) => (
              <option key={range} value={range}>
                {range}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">
            {isQualitativeTest
              ? 'For qualitative tests, record value as Positive/Negative/Reactive/Non-reactive.'
              : 'Normal reference range for this test'}
          </p>
        </div>

        <div className="text-sm text-gray-500 bg-blue-50 p-3 rounded">
          <p className="font-medium">Note:</p>
          <ul className="list-disc pl-5 mt-1 space-y-1">
            <li>Recording results does NOT complete the lab request</li>
            <li>Complete the request separately after results are recorded</li>
            <li>Results cannot be modified after completion</li>
            <li>Technician ID: {technicianId.substring(0, 8)}...</li>
          </ul>
        </div>

        <div className="flex space-x-3 pt-4">
          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting}
            disabled={isSubmitting}
            className="flex-1"
          >
            Record Results
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
