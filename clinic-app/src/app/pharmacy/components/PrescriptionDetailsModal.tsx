'use client';

import { useState } from 'react';
import { pharmacyService } from '@/domains/pharmacy/services/pharmacyService';
import { PrescriptionResponse } from '@/shared/types';
import {
  PharmacyExceptionAuthorizationType,
  PharmacyPrescriptionWorkflowStatus,
} from '@/shared/enums';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';

interface PrescriptionDetailsModalProps {
  prescription: PrescriptionResponse | null;
  unitId?: string | null;
  isOpen: boolean;
  onClose: () => void;
  onDispense?: (prescription: PrescriptionResponse) => void;
  onRefresh?: (prescription: PrescriptionResponse) => void;
}

function readinessBadge(status: PharmacyPrescriptionWorkflowStatus) {
  switch (status) {
    case PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE:
      return 'border border-emerald-200 bg-emerald-50 text-emerald-700';
    case PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED:
      return 'border border-amber-200 bg-amber-50 text-amber-700';
    case PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE:
      return 'border border-amber-200 bg-amber-50 text-amber-700';
    case PharmacyPrescriptionWorkflowStatus.IN_DISPENSE:
      return 'border border-blue-200 bg-blue-50 text-blue-700';
    case PharmacyPrescriptionWorkflowStatus.DISPENSED:
      return 'border border-green-200 bg-green-50 text-green-700';
    case PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED:
      return 'border border-slate-200 bg-slate-100 text-slate-700';
    default:
      return 'border border-slate-200 bg-slate-100 text-slate-700';
  }
}

function stockBadge(status?: string | null) {
  switch (status) {
    case 'IN_STOCK':
      return 'border border-emerald-200 bg-emerald-50 text-emerald-700';
    case 'LOW_STOCK':
      return 'border border-amber-200 bg-amber-50 text-amber-700';
    case 'OUT_OF_STOCK':
    case 'EXPIRED':
    case 'UNMAPPED':
      return 'border border-red-200 bg-red-50 text-red-700';
    default:
      return 'border border-slate-200 bg-slate-100 text-slate-700';
  }
}

function formatDateTime(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleString();
}

function formatDateOnly(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleDateString();
}

export function PrescriptionDetailsModal({
  prescription,
  unitId,
  isOpen,
  onClose,
  onDispense,
  onRefresh,
}: PrescriptionDetailsModalProps) {
  const [refreshing, setRefreshing] = useState(false);

  if (!isOpen || !prescription) return null;

  const canOpenBench =
    [
      PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
      PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
    ].includes(prescription.workflow_status) &&
    ['IN_STOCK', 'LOW_STOCK'].includes(
      prescription.local_stock_status || 'UNMAPPED'
    );

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      const refreshed = await pharmacyService.getPrescription(
        prescription.id,
        unitId || undefined
      );
      onRefresh?.(refreshed);
    } catch (error) {
      console.error('Failed to refresh prescription detail:', error);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-3xl bg-white shadow-2xl">
        <div className="border-b border-slate-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1E4B8C]">
                Dispensing Detail
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                {prescription.drug_name}
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                {prescription.patient_name || 'Unknown patient'}
                {prescription.patient_mrn ? ` • MRN ${prescription.patient_mrn}` : ''}
                {prescription.source_department_name
                  ? ` • ${prescription.source_department_name}`
                  : ''}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${readinessBadge(
                    prescription.workflow_status
                  )}`}
                >
                  {prescription.workflow_status.replaceAll('_', ' ')}
                </span>
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${stockBadge(
                    prescription.local_stock_status
                  )}`}
                >
                  {(prescription.local_stock_status || 'UNMAPPED').replaceAll('_', ' ')}
                </span>
                {prescription.priority ? (
                  <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                    {prescription.priority}
                  </span>
                ) : null}
                {prescription.exception_authorization_type &&
                prescription.exception_authorization_type !==
                  PharmacyExceptionAuthorizationType.NONE ? (
                  <span className="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700">
                    {prescription.exception_authorization_type.replaceAll('_', ' ')}
                  </span>
                ) : null}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-slate-200 px-3 py-1 text-sm text-slate-500 hover:bg-slate-50"
            >
              Close
            </button>
          </div>
        </div>

        <div className="space-y-6 px-6 py-6">
          <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
            <Card title="Patient & Visit Context" titleClassName="text-[#1E4B8C]">
              <dl className="grid gap-4 text-sm md:grid-cols-2">
                <div>
                  <dt className="text-slate-500">Patient</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.patient_name || 'Unknown patient'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">MRN</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.patient_mrn || 'Not available'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Source Department</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.source_department_name || 'Not mapped'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Prescriber</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.prescribed_by_name || 'Unassigned'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Issued</dt>
                  <dd className="font-medium text-slate-900">
                    {formatDateTime(prescription.issued_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Aging</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.aging_minutes ?? 0} minutes
                  </dd>
                </div>
              </dl>
            </Card>

            <Card title="Payment & Readiness" titleClassName="text-[#1E4B8C]">
              <dl className="space-y-4 text-sm">
                <div>
                  <dt className="text-slate-500">Payment State</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.payment_cleared
                      ? 'Payment cleared'
                      : prescription.exception_authorization_type &&
                          prescription.exception_authorization_type !==
                            PharmacyExceptionAuthorizationType.NONE
                        ? 'Authorized exception'
                        : 'Awaiting Payment Clearance'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Cashier Pay Point</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.assigned_cashier_pay_point_name || 'Unassigned'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Assigned Unit</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.assigned_dispensing_unit_name || 'Unassigned'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Local Stock Source</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.local_stock_source || 'Local Unit Stock'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Available Quantity</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.local_stock_available_quantity ?? 0}
                  </dd>
                </div>
              </dl>
            </Card>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
            <Card title="Prescription Item" titleClassName="text-[#1E4B8C]">
              <dl className="grid gap-4 text-sm md:grid-cols-2">
                <div>
                  <dt className="text-slate-500">Drug</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.drug_name}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Dosage</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.dosage}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Frequency</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.frequency}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Duration</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.duration}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Prescribed</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.quantity_prescribed}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Dispensed</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.quantity_dispensed_total}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Remaining</dt>
                  <dd className="font-medium text-slate-900">
                    {prescription.quantity_remaining}
                  </dd>
                </div>
              </dl>
              {prescription.instructions ? (
                <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                  <p className="font-medium text-slate-900">Instructions</p>
                  <p className="mt-2">{prescription.instructions}</p>
                </div>
              ) : null}
            </Card>

            <Card title="Batch & Expiry Visibility" titleClassName="text-[#1E4B8C]">
              {prescription.available_stock_lots?.length ? (
                <div className="space-y-3">
                  {prescription.available_stock_lots.map((lot) => (
                    <div
                      key={lot.id}
                      className={`rounded-2xl border px-4 py-3 text-sm ${
                        lot.blocked
                          ? 'border-red-200 bg-red-50'
                          : lot.low_stock
                            ? 'border-amber-200 bg-amber-50'
                            : 'border-slate-200 bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="font-medium text-slate-900">{lot.batch_number}</p>
                          <p className="text-slate-600">
                            Expiry: {formatDateOnly(lot.expiry_date)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold text-slate-900">
                            {lot.quantity_on_hand}
                          </p>
                          <p className="text-xs text-slate-500">
                            {lot.blocked
                              ? 'Blocked'
                              : lot.low_stock
                                ? 'Low stock'
                                : 'Available'}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-600">
                  No local stock lots are currently available for this prescription.
                </div>
              )}
            </Card>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-slate-200 px-6 py-4">
          <Button variant="secondary" onClick={() => void handleRefresh()} isLoading={refreshing}>
            Refresh Detail
          </Button>
          {onDispense ? (
            <Button
              variant="primary"
              onClick={() => onDispense(prescription)}
              disabled={!canOpenBench}
            >
              Open Dispense Bench
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
