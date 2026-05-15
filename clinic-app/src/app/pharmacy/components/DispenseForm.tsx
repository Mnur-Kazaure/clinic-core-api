'use client';

import { useEffect, useMemo, useState } from 'react';
import { pharmacyService } from '@/domains/pharmacy/services/pharmacyService';
import { PrescriptionResponse } from '@/shared/types';
import {
  PharmacyExceptionAuthorizationType,
  PharmacyPrescriptionWorkflowStatus,
} from '@/shared/enums';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';

interface DispenseFormProps {
  prescription: PrescriptionResponse;
  pharmacistId: string;
  unitId?: string | null;
  onSuccess?: (message?: string) => void;
  onCancel?: () => void;
}

const reassignmentReasons = [
  { value: 'OUT_OF_STOCK', label: 'Out of stock' },
  { value: 'OVERLOAD', label: 'Unit overload' },
  { value: 'SPECIALIZED_UNIT', label: 'Specialized unit requirement' },
  { value: 'NHIS_ROUTING', label: 'NHIS / coverage routing' },
  { value: 'OTHER', label: 'Other documented reason' },
] as const;

function stockTone(status?: string | null) {
  switch (status) {
    case 'IN_STOCK':
      return 'border-emerald-200 bg-emerald-50 text-emerald-700';
    case 'LOW_STOCK':
      return 'border-amber-200 bg-amber-50 text-amber-700';
    default:
      return 'border-red-200 bg-red-50 text-red-700';
  }
}

function formatDateOnly(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleDateString();
}

function isActionableWorkflowStatus(status: PharmacyPrescriptionWorkflowStatus) {
  return (
    status === PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE ||
    status === PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED
  );
}

export function DispenseForm({
  prescription,
  pharmacistId,
  unitId,
  onSuccess,
  onCancel,
}: DispenseFormProps) {
  const availableLots = useMemo(
    () =>
      (prescription.available_stock_lots || []).filter(
        (lot) => !lot.blocked && lot.quantity_on_hand > 0
      ),
    [prescription.available_stock_lots]
  );

  const [quantity, setQuantity] = useState<number | ''>('');
  const [selectedLotId, setSelectedLotId] = useState<string>('');
  const [externalNote, setExternalNote] = useState('');
  const [reassignTargetId, setReassignTargetId] = useState('');
  const [reassignReason, setReassignReason] = useState<string>(
    reassignmentReasons[0].value
  );
  const [reassignNote, setReassignNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    setSelectedLotId(availableLots[0]?.id || '');
  }, [availableLots]);

  const selectedLot = availableLots.find((lot) => lot.id === selectedLotId) || null;
  const hasException =
    prescription.exception_authorization_type &&
    prescription.exception_authorization_type !==
      PharmacyExceptionAuthorizationType.NONE;

  const blockers = useMemo(() => {
    const issues: string[] = [];
    if (prescription.assigned_dispensing_unit_id && unitId && prescription.assigned_dispensing_unit_id !== unitId) {
      issues.push('This prescription is assigned to a different dispensing unit.');
    }
    if (
      !isActionableWorkflowStatus(prescription.workflow_status) &&
      !hasException
    ) {
      issues.push('Dispense is blocked until payment clearance or authorized exception.');
    }
    if (!availableLots.length) {
      if (prescription.local_stock_status === 'EXPIRED') {
        issues.push('All visible local stock batches are expired and blocked.');
      } else if (prescription.local_stock_status === 'UNMAPPED') {
        issues.push('Local stock mapping is missing for this medication.');
      } else {
        issues.push('No local unit stock is available for this prescription.');
      }
    }
    return issues;
  }, [
    availableLots.length,
    hasException,
    prescription.assigned_dispensing_unit_id,
    prescription.local_stock_status,
    prescription.workflow_status,
    unitId,
  ]);

  const canDispense = blockers.length === 0 && Boolean(selectedLotId);

  const clearFlash = () => {
    window.setTimeout(() => {
      setSuccessMessage(null);
    }, 2500);
  };

  const handleDispense = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!quantity || quantity <= 0) {
      setError('Enter a valid dispense quantity.');
      return;
    }
    if (!selectedLot) {
      setError('Select a valid local stock batch before dispensing.');
      return;
    }
    if (quantity > selectedLot.quantity_on_hand) {
      setError('Selected quantity exceeds the available quantity in the chosen batch.');
      return;
    }
    if (quantity > prescription.quantity_remaining) {
      setError('Selected quantity exceeds the remaining prescribed quantity.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setSuccessMessage(null);

      const response = await pharmacyService.dispensePrescription(prescription.id, {
        pharmacist_id: pharmacistId,
        quantity: Number(quantity),
        unit_id: unitId || undefined,
        stock_lot_id: selectedLot.id,
      });

      const message =
        response.quantity_remaining > 0
          ? `Partial dispense recorded — ${response.quantity_remaining} remaining.`
          : 'Dispense completed from local unit stock.';
      setSuccessMessage(message);
      clearFlash();
      onSuccess?.(message);
    } catch (err: any) {
      console.error('Failed to dispense prescription:', err);
      setError(
        err?.response?.data?.detail || 'Dispense could not be completed.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReassign = async () => {
    if (!reassignTargetId) {
      setError('Select a target dispensing unit for reassignment.');
      return;
    }
    if (!reassignReason) {
      setError('Choose a reassignment reason.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setSuccessMessage(null);

      await pharmacyService.reassignPrescription(prescription.id, {
        target_unit_id: reassignTargetId,
        reason: reassignReason,
        note: reassignNote.trim() || undefined,
      });

      const message = 'Reassignment recorded without changing readiness state.';
      setSuccessMessage(message);
      clearFlash();
      onSuccess?.(message);
    } catch (err: any) {
      console.error('Failed to reassign prescription:', err);
      setError(
        err?.response?.data?.detail || 'Reassignment could not be completed.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExternalFulfill = async () => {
    const note = externalNote.trim();
    if (note.length < 3) {
      setError('Enter a short external fulfillment note.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setSuccessMessage(null);

      await pharmacyService.fulfillPrescriptionExternal(prescription.id, {
        note,
      });

      const message = 'Prescription marked as externally fulfilled.';
      setSuccessMessage(message);
      clearFlash();
      onSuccess?.(message);
    } catch (err: any) {
      console.error('Failed to mark external fulfillment:', err);
      setError(
        err?.response?.data?.detail ||
          'External fulfillment could not be recorded.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card title={`Dispense Bench: ${prescription.drug_name}`}>
      <form
        onSubmit={handleDispense}
        className="space-y-6"
        data-testid="pharmacy-dispense-bench"
      >
        {error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}
        {successMessage ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {successMessage}
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1E4B8C]">
              Patient Context
            </p>
            <p className="mt-3 font-semibold text-slate-900">
              {prescription.patient_name || 'Unknown patient'}
            </p>
            <p className="mt-1 text-slate-600">
              {prescription.patient_mrn
                ? `MRN ${prescription.patient_mrn}`
                : 'MRN not available'}
              {prescription.source_department_name
                ? ` • ${prescription.source_department_name}`
                : ''}
            </p>
            <p className="mt-3 text-slate-600">
              Prescriber: {prescription.prescribed_by_name || 'Unassigned'}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1E4B8C]">
              Payment & Safety
            </p>
            <p className="mt-3 text-slate-900">
              Readiness:{' '}
              <span className="font-semibold">
                {prescription.workflow_status.replaceAll('_', ' ')}
              </span>
            </p>
            <p className="mt-1 text-slate-900">
              Payment:{' '}
              <span className="font-semibold">
                {prescription.payment_cleared
                  ? 'Payment cleared'
                  : hasException
                    ? 'Authorized exception'
                    : 'Awaiting Payment Clearance'}
              </span>
            </p>
            <p className="mt-1 text-slate-900">
              Source:{' '}
              <span className="font-semibold">
                {prescription.local_stock_source || 'Local Unit Stock'}
              </span>
            </p>
            <p className="mt-1 text-slate-900">
              Assigned Unit:{' '}
              <span className="font-semibold">
                {prescription.assigned_dispensing_unit_name || 'Unassigned'}
              </span>
            </p>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 p-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1E4B8C]">
                Local Stock Validation
              </p>
              <p className="mt-2 text-sm text-slate-600">
                Only local unit stock can be used for this dispense.
              </p>
            </div>
            <span
              className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${stockTone(
                prescription.local_stock_status
              )}`}
            >
              {(prescription.local_stock_status || 'UNMAPPED').replaceAll('_', ' ')}
            </span>
          </div>

          {blockers.length ? (
            <div className="mt-4 space-y-2 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {blockers.map((blocker) => (
                <p key={blocker}>{blocker}</p>
              ))}
            </div>
          ) : null}

          <div className="mt-4 grid gap-4 md:grid-cols-[1.2fr,0.8fr]">
            <div>
              <div className="mb-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Prescribed
                  </p>
                  <p className="mt-2 text-xl font-semibold text-slate-900">
                    {prescription.quantity_prescribed}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Dispensed
                  </p>
                  <p className="mt-2 text-xl font-semibold text-slate-900">
                    {prescription.quantity_dispensed_total}
                  </p>
                </div>
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">
                    Remaining
                  </p>
                  <p className="mt-2 text-xl font-semibold text-slate-900">
                    {prescription.quantity_remaining}
                  </p>
                </div>
              </div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Batch Selection
              </label>
              <select
                value={selectedLotId}
                onChange={(event) => setSelectedLotId(event.target.value)}
                data-testid="pharmacy-batch-select"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={!availableLots.length || isSubmitting}
              >
                <option value="">Select local stock batch</option>
                {availableLots.map((lot) => (
                  <option key={lot.id} value={lot.id}>
                    {lot.batch_number} • {lot.quantity_on_hand} available • Exp {formatDateOnly(lot.expiry_date)}
                  </option>
                ))}
              </select>
            </div>
            <Input
              label="Quantity Dispensed"
              type="number"
              min="1"
              max={
                selectedLot
                  ? Math.min(
                      selectedLot.quantity_on_hand,
                      prescription.quantity_remaining
                    )
                  : prescription.quantity_remaining || undefined
              }
              data-testid="pharmacy-dispense-quantity"
              value={quantity}
              onChange={(event) =>
                setQuantity(
                  event.target.value === '' ? '' : Number(event.target.value)
                )
              }
              disabled={!canDispense || isSubmitting}
            />
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1E4B8C]">
              Reassign Fulfillment
            </p>
            <p className="mt-2 text-sm text-slate-600">
              Reassignment changes fulfillment ownership only. It does not unlock payment or alter readiness state.
            </p>
            <div className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Target Unit
                </label>
                <select
                  value={reassignTargetId}
                  onChange={(event) => setReassignTargetId(event.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isSubmitting}
                >
                  <option value="">Select target unit</option>
                  {(prescription.reassignment_options || []).map((option) => (
                    <option key={option.unit_id} value={option.unit_id}>
                      {option.unit_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Reason
                </label>
                <select
                  value={reassignReason}
                  onChange={(event) => setReassignReason(event.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isSubmitting}
                >
                  {reassignmentReasons.map((reason) => (
                    <option key={reason.value} value={reason.value}>
                      {reason.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Note
                </label>
                <textarea
                  value={reassignNote}
                  onChange={(event) => setReassignNote(event.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Add the operational reason for reassignment."
                  disabled={isSubmitting}
                />
              </div>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void handleReassign()}
                disabled={isSubmitting}
                className="w-full"
              >
                Reassign Fulfillment
              </Button>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1E4B8C]">
              External Fulfillment
            </p>
            <p className="mt-2 text-sm text-slate-600">
              Use only when policy allows the patient to obtain the drug outside the clinic.
            </p>
            <div className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  External Note
                </label>
                <textarea
                  value={externalNote}
                  onChange={(event) => setExternalNote(event.target.value)}
                  rows={4}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Record why this prescription is being fulfilled externally."
                  disabled={isSubmitting}
                />
              </div>
              <Button
                type="button"
                variant="danger"
                onClick={() => void handleExternalFulfill()}
                disabled={isSubmitting}
                className="w-full"
              >
                Mark as Externally Fulfilled
              </Button>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-slate-200 pt-4">
          {onCancel ? (
            <Button type="button" variant="secondary" onClick={onCancel} disabled={isSubmitting}>
              Close Bench
            </Button>
          ) : null}
          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting}
            disabled={!canDispense || isSubmitting}
          >
            Dispense Medication
          </Button>
        </div>
      </form>
    </Card>
  );
}
