'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import {
  LabResultCreate,
  LabResultTemplate,
  LabResultTemplateField,
  LabSpecimen,
  LabRequestWorkflowState,
  labService,
} from '@/domains/lab/services/labService';
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
  selectedUnitId: string;
  testName: string;
  workflowState?: LabRequestWorkflowState | null;
  onWorkflowRefresh?: () => void;
  onSuccess?: () => void;
  onCancel?: () => void;
}

type EntryMode = 'loading' | 'structured' | 'legacy';

function isReadySpecimen(specimen: LabSpecimen): boolean {
  return ['RECEIVED', 'IN_PROCESS'].includes(specimen.status);
}

function extractErrorDetail(err: unknown): string | null {
  if (typeof err !== 'object' || err === null || !('response' in err)) {
    return null;
  }
  const detail = (err as { response?: { data?: { detail?: unknown } } }).response
    ?.data?.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object' && 'msg' in item) {
          const value = (item as { msg?: unknown }).msg;
          return typeof value === 'string' ? value : null;
        }
        return null;
      })
      .filter((value): value is string => Boolean(value))
      .join('; ');
  }
  return null;
}

function getStatusCode(err: unknown): number | undefined {
  if (typeof err !== 'object' || err === null || !('response' in err)) {
    return undefined;
  }
  return (err as { response?: { status?: number } }).response?.status;
}

function getOptions(field: LabResultTemplateField): string[] {
  if (Array.isArray(field.options_json)) {
    return field.options_json.filter((item): item is string => typeof item === 'string');
  }
  if (field.options_json && typeof field.options_json === 'object') {
    return Object.values(field.options_json).filter(
      (item): item is string => typeof item === 'string'
    );
  }
  return [];
}

export function LabResultForm({
  requestId,
  technicianId,
  selectedUnitId,
  testName,
  workflowState,
  onWorkflowRefresh,
  onSuccess,
  onCancel,
}: LabResultFormProps) {
  const [mode, setMode] = useState<EntryMode>('loading');
  const [template, setTemplate] = useState<LabResultTemplate | null>(null);
  const [specimens, setSpecimens] = useState<LabSpecimen[]>([]);
  const [structuredValues, setStructuredValues] = useState<Record<string, string>>({});
  const [specimenForm, setSpecimenForm] = useState({
    specimen_type: '',
    specimen_source: '',
    container_type: '',
    collection_site: '',
    print_label: true,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingTemplate, setIsLoadingTemplate] = useState(false);
  const [isRegisteringSpecimen, setIsRegisteringSpecimen] = useState(false);
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

  const loadStructuredContext = useCallback(async () => {
    try {
      setIsLoadingTemplate(true);
      setError(null);
      const [templateResponse, specimenResponse] = await Promise.all([
        labService.getResultTemplate(requestId, selectedUnitId),
        labService.getSpecimens(requestId, selectedUnitId),
      ]);
      setTemplate(templateResponse);
      setSpecimens(specimenResponse);
      setMode('structured');
    } catch (err: unknown) {
      const detail = extractErrorDetail(err);
      if (
        detail?.includes('No result template configured') ||
        getStatusCode(err) === 404 ||
        getStatusCode(err) === 409
      ) {
        setMode('legacy');
        return;
      }
      setError(detail || 'Unable to load lab result template.');
      setMode('legacy');
    } finally {
      setIsLoadingTemplate(false);
    }
  }, [requestId, selectedUnitId]);

  useEffect(() => {
    void loadStructuredContext();
  }, [loadStructuredContext]);

  useEffect(() => {
    const defaults = workflowState?.specimen_defaults;
    if (!defaults) {
      return;
    }
    setSpecimenForm((current) => ({
      ...current,
      specimen_type: current.specimen_type || defaults.specimen_type || '',
      specimen_source: current.specimen_source || defaults.specimen_source || '',
      container_type: current.container_type || defaults.container_type || '',
      collection_site: current.collection_site || defaults.collection_site || '',
    }));
  }, [workflowState]);

  const sortedFields = useMemo(
    () =>
      [...(template?.fields || [])].sort(
        (left, right) => left.display_order - right.display_order
      ),
    [template]
  );

  const hasReadySpecimen = useMemo(
    () => specimens.some((specimen) => isReadySpecimen(specimen)),
    [specimens]
  );

  const isQualitativeTest = /hiv|hepatitis|hbsag|hcv|vdrl|pregnancy|mrdt|widal|h\.?\s*pylori|blood grouping|sickling|urinalysis|urine microscopy|stool microscopy|sputum afb/i.test(
    testName
  );

  const normalizeOptional = (value?: string) => {
    const trimmed = (value || '').trim();
    return trimmed.length > 0 ? trimmed : undefined;
  };

  const setTransientSuccess = () => {
    setSuccess(true);
    setTimeout(() => {
      setSuccess(false);
    }, 3000);
  };

  const handleLegacySubmit = async (data: LabResultFormData) => {
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
      };

      await labService.recordResults(requestId, payload, selectedUnitId);
      reset();
      setTransientSuccess();
      onWorkflowRefresh?.();
      onSuccess?.();
    } catch (err: unknown) {
      const statusCode = getStatusCode(err);
      const detail = extractErrorDetail(err);
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

  const handleRegisterSpecimen = async () => {
    if (!specimenForm.specimen_type.trim() || !specimenForm.specimen_source.trim()) {
      setError('Specimen type and source are required before result entry.');
      return;
    }

    try {
      setIsRegisteringSpecimen(true);
      setError(null);
      await labService.createSpecimen(requestId, {
        specimen_type: specimenForm.specimen_type.trim(),
        specimen_source: specimenForm.specimen_source.trim(),
        container_type: normalizeOptional(specimenForm.container_type),
        collection_site: normalizeOptional(specimenForm.collection_site),
        status: 'RECEIVED',
        print_label: specimenForm.print_label,
      }, selectedUnitId);
      const refreshed = await labService.getSpecimens(requestId, selectedUnitId);
      setSpecimens(refreshed);
      onWorkflowRefresh?.();
    } catch (err: unknown) {
      setError(extractErrorDetail(err) || 'Unable to register specimen.');
    } finally {
      setIsRegisteringSpecimen(false);
    }
  };

  const handleStructuredSubmit = async () => {
    if (!template) return;
    if (!hasReadySpecimen) {
      setError('A received specimen is required before structured result entry.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const values = sortedFields.map((field) => {
        const rawValue = structuredValues[field.id] ?? '';
        const trimmed = rawValue.trim();

        if (field.is_required && trimmed.length === 0) {
          throw new Error(`${field.field_name} is required.`);
        }
        if (trimmed.length === 0) {
          return null;
        }

        if (field.field_type === 'NUMBER') {
          const parsed = Number(trimmed);
          if (Number.isNaN(parsed)) {
            throw new Error(`${field.field_name} must be a valid number.`);
          }
          return {
            template_field_id: field.id,
            value_number: parsed,
          };
        }

        if (field.field_type === 'BOOLEAN') {
          if (trimmed !== 'true' && trimmed !== 'false') {
            throw new Error(`${field.field_name} must be Yes or No.`);
          }
          return {
            template_field_id: field.id,
            value_boolean: trimmed === 'true',
          };
        }

        if (field.field_type === 'JSON') {
          try {
            return {
              template_field_id: field.id,
              value_json: JSON.parse(trimmed),
            };
          } catch {
            throw new Error(`${field.field_name} must contain valid JSON.`);
          }
        }

        return {
          template_field_id: field.id,
          value_string: trimmed,
        };
      });

      const filteredValues = values.filter(
        (value): value is NonNullable<(typeof values)[number]> => value !== null
      );
      if (filteredValues.length === 0) {
        throw new Error('At least one result value is required.');
      }

      await labService.recordStructuredResults(requestId, {
        values: filteredValues,
      }, selectedUnitId);

      setStructuredValues({});
      setTransientSuccess();
      onWorkflowRefresh?.();
      onSuccess?.();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(extractErrorDetail(err) || 'Failed to submit structured results.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderStructuredField = (field: LabResultTemplateField) => {
    const value = structuredValues[field.id] ?? '';
    const commonClassName =
      'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-[#0B4DA2] focus:ring-4 focus:ring-[#0B4DA2]/10';

    if (field.field_type === 'SELECT') {
      return (
        <select
          value={value}
          onChange={(event) =>
            setStructuredValues((current) => ({
              ...current,
              [field.id]: event.target.value,
            }))
          }
          className={commonClassName}
        >
          <option value="">Select an option</option>
          {getOptions(field).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    if (field.field_type === 'BOOLEAN') {
      return (
        <select
          value={value}
          onChange={(event) =>
            setStructuredValues((current) => ({
              ...current,
              [field.id]: event.target.value,
            }))
          }
          className={commonClassName}
        >
          <option value="">Select</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      );
    }

    if (field.field_type === 'TEXT' || field.field_type === 'JSON') {
      return (
        <textarea
          value={value}
          onChange={(event) =>
            setStructuredValues((current) => ({
              ...current,
              [field.id]: event.target.value,
            }))
          }
          rows={field.field_type === 'JSON' ? 4 : 3}
          className={commonClassName}
          placeholder={field.field_type === 'JSON' ? '{"value": "..."}' : 'Enter result'}
        />
      );
    }

    return (
      <input
        type={field.field_type === 'NUMBER' ? 'number' : 'text'}
        step={field.field_type === 'NUMBER' ? 'any' : undefined}
        value={value}
        onChange={(event) =>
          setStructuredValues((current) => ({
            ...current,
            [field.id]: event.target.value,
          }))
        }
        className={commonClassName}
        placeholder={field.unit ? `Enter result in ${field.unit}` : 'Enter result'}
      />
    );
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

  if (isLoadingTemplate && mode === 'loading') {
    return (
      <Card title={`Result Entry: ${testName}`} titleClassName="text-[#0B4DA2]">
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
          Loading result entry workflow…
        </div>
      </Card>
    );
  }

  return (
    <Card title={`Result Entry: ${testName}`} titleClassName="text-[#0B4DA2]">
      <div className="space-y-4">
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Results recorded successfully.
          </div>
        )}

        {mode === 'structured' && template && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{template.name}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Template {template.code} • v{template.version}
                  </p>
                  {template.description && (
                    <p className="mt-2 text-sm text-slate-600">{template.description}</p>
                  )}
                </div>
                <span
                  data-testid="lab-configured-template-badge"
                  className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700"
                >
                  Configured Template
                </span>
              </div>
            </div>

            <Card title="Specimen Gate" titleClassName="!text-[#0B4DA2]">
              <div className="mb-4 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
                <p className="font-medium">Specimen readiness</p>
                <ul className="mt-2 space-y-1 text-xs text-sky-800">
                  <li>Register the received specimen for this request.</li>
                  <li>Print the accession label if your bench workflow requires it.</li>
                  <li>Continue to structured result entry immediately after registration.</li>
                </ul>
              </div>

              {specimens.length > 0 && (
                <div className="mb-4 space-y-2">
                  {specimens.map((specimen) => (
                    <div
                      key={specimen.id}
                      className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
                    >
                      <p className="font-medium text-slate-900">
                        {specimen.accession_number} • {specimen.specimen_type}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Status: {specimen.status} • Source: {specimen.specimen_source}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {!hasReadySpecimen ? (
                <div className="space-y-4">
                  <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    A received specimen must be registered before structured result entry.
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <Input
                      label="Specimen Type *"
                      data-testid="lab-specimen-type-input"
                      value={specimenForm.specimen_type}
                      onChange={(event) =>
                        setSpecimenForm((current) => ({
                          ...current,
                          specimen_type: event.target.value,
                        }))
                      }
                      placeholder="e.g. Blood, Urine, Tissue"
                    />
                    <Input
                      label="Specimen Source *"
                      data-testid="lab-specimen-source-input"
                      value={specimenForm.specimen_source}
                      onChange={(event) =>
                        setSpecimenForm((current) => ({
                          ...current,
                          specimen_source: event.target.value,
                        }))
                      }
                      placeholder="e.g. blood, urine, tissue"
                    />
                    <Input
                      label="Container Type"
                      data-testid="lab-container-type-input"
                      value={specimenForm.container_type}
                      onChange={(event) =>
                        setSpecimenForm((current) => ({
                          ...current,
                          container_type: event.target.value,
                        }))
                      }
                      placeholder="e.g. EDTA tube"
                    />
                    <Input
                      label="Collection Site (optional)"
                      data-testid="lab-collection-site-input"
                      value={specimenForm.collection_site}
                      onChange={(event) =>
                        setSpecimenForm((current) => ({
                          ...current,
                          collection_site: event.target.value,
                        }))
                      }
                      placeholder="e.g. venous"
                    />
                  </div>
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={specimenForm.print_label}
                      onChange={(event) =>
                        setSpecimenForm((current) => ({
                          ...current,
                          print_label: event.target.checked,
                        }))
                      }
                      className="rounded border-slate-300 text-[#0B4DA2] focus:ring-[#0B4DA2]"
                    />
                    Print accession label event
                  </label>
                  <div className="flex gap-3">
                    <Button
                      type="button"
                      variant="primary"
                      isLoading={isRegisteringSpecimen}
                      disabled={isRegisteringSpecimen}
                      onClick={() => void handleRegisterSpecimen()}
                    >
                      Register Received Specimen
                    </Button>
                    {onCancel && (
                      <Button type="button" variant="secondary" onClick={onCancel}>
                        Cancel
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                  Received specimen confirmed. Structured result entry is enabled.
                </div>
              )}
            </Card>

            {hasReadySpecimen && (
              <>
                <div className="grid gap-4 md:grid-cols-2">
                  {sortedFields.map((field) => (
                    <div
                      key={field.id}
                      className={`space-y-2 rounded-xl border border-slate-200 bg-white p-4 ${
                        field.field_type === 'TEXT' || field.field_type === 'JSON'
                          ? 'md:col-span-2'
                          : ''
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <label className="text-sm font-medium text-slate-800">
                            {field.field_name}
                            {field.is_required ? ' *' : ''}
                          </label>
                          <p className="mt-1 text-xs text-slate-500">
                            {field.field_code}
                            {field.unit ? ` • ${field.unit}` : ''}
                          </p>
                        </div>
                        {(field.reference_range_text || field.reference_unit) && (
                          <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                            {field.reference_range_text ||
                              [field.reference_min, field.reference_max, field.reference_unit]
                                .filter(Boolean)
                                .join(' - ')}
                          </span>
                        )}
                      </div>
                      {renderStructuredField(field)}
                    </div>
                  ))}
                </div>

                <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
                  Structured entry is driven by the configured template for this request.
                </div>

                <div className="flex gap-3 pt-2">
                  <Button
                    type="button"
                    variant="primary"
                    isLoading={isSubmitting}
                    disabled={isSubmitting}
                    onClick={() => void handleStructuredSubmit()}
                  >
                    Submit Structured Results
                  </Button>
                  {onCancel && (
                    <Button type="button" variant="secondary" onClick={onCancel}>
                      Cancel
                    </Button>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {mode === 'legacy' && (
          <form onSubmit={handleSubmit(handleLegacySubmit)} className="space-y-4">
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              No configured result template was found for this request. Legacy result entry remains available for continuity.
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Input
                label="Result Value"
                {...register('result_value')}
                error={errors.result_value?.message}
                placeholder="e.g., 5.2"
              />

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Unit {isQualitativeTest ? '(optional)' : '*'}
                </label>
                <select
                  {...register('result_unit')}
                  className="w-full rounded-xl border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">
                    {isQualitativeTest ? 'Not applicable' : 'Select unit'}
                  </option>
                  {commonUnits.map((unit) => (
                    <option key={unit} value={unit}>
                      {unit}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Reference Range {isQualitativeTest ? '(optional)' : '*'}
              </label>
              <select
                {...register('reference_range')}
                className="w-full rounded-xl border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">
                  {isQualitativeTest ? 'Not applicable' : 'Select reference range'}
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

            <div className="rounded-xl bg-blue-50 p-3 text-sm text-gray-600">
              <p className="font-medium">Legacy continuity note</p>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                <li>Recording results does not complete the lab request.</li>
                <li>Complete the request separately after result recording.</li>
                <li>Technician ID: {technicianId.substring(0, 8)}…</li>
              </ul>
            </div>

            <div className="flex gap-3 pt-2">
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
        )}
      </div>
    </Card>
  );
}
