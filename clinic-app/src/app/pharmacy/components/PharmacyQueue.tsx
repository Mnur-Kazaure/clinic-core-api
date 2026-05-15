'use client';

import { useEffect, useState } from 'react';
import { pharmacyService } from '@/domains/pharmacy/services/pharmacyService';
import { PrescriptionResponse } from '@/shared/types';
import {
  PharmacyPrescriptionWorkflowStatus,
  PrescriptionFulfillmentType,
} from '@/shared/enums';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';

type PrescriptionFilter = PharmacyPrescriptionWorkflowStatus | 'ALL';

interface PharmacyQueueProps {
  unitId?: string | null;
  onSelectPrescription?: (prescription: PrescriptionResponse) => void;
  onDispensePrescription?: (prescription: PrescriptionResponse) => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function PharmacyQueue({
  unitId,
  onSelectPrescription,
  onDispensePrescription,
  autoRefresh = true,
  refreshInterval = 30000,
}: PharmacyQueueProps) {
  const [prescriptions, setPrescriptions] = useState<PrescriptionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<PrescriptionFilter>(
    PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE
  );
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const maskId = (value?: string | null) =>
    value ? `${value.slice(0, 8)}...` : '—';

  const getPatientDisplay = (prescription: PrescriptionResponse) => {
    if (prescription.patient_mrn) {
      return `MRN ${prescription.patient_mrn}`;
    }
    return `ID: ${maskId(prescription.patient_id)}`;
  };

  const loadPrescriptions = async () => {
    try {
      setLoading(true);
      setError(null);
      if (!unitId) {
        setPrescriptions([]);
        setLastUpdated(new Date());
        return;
      }
      const data = await pharmacyService.getPrescriptions({
        workflow_status: statusFilter === 'ALL' ? undefined : statusFilter,
        unit_id: unitId,
      });
      setPrescriptions(data);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to load prescriptions:', err);
      setError('Unable to load assigned prescriptions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPrescriptions();
  }, [unitId, statusFilter]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      void loadPrescriptions();
    }, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, unitId, statusFilter]);

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const getStatusBadge = (prescription: PrescriptionResponse) => {
    const status = prescription.workflow_status;
    const config =
      {
        ASSIGNED: { color: 'bg-sky-100 text-sky-800', label: 'Assigned' },
        AWAITING_PAYMENT_CLEARANCE: {
          color: 'bg-amber-100 text-amber-800',
          label: 'Awaiting Payment Clearance',
        },
        READY_TO_DISPENSE: {
          color: 'bg-emerald-100 text-emerald-800',
          label: 'Ready to Dispense',
        },
        PARTIALLY_DISPENSED: {
          color: 'bg-amber-100 text-amber-800',
          label: 'Partially Dispensed',
        },
        IN_DISPENSE: { color: 'bg-blue-100 text-blue-800', label: 'In Dispense' },
        DISPENSED: { color: 'bg-green-100 text-green-800', label: 'Dispensed' },
        REASSIGNED: { color: 'bg-violet-100 text-violet-800', label: 'Reassigned' },
        CANCELLED: { color: 'bg-red-100 text-red-800', label: 'Cancelled' },
        EXTERNALLY_FULFILLED: {
          color: 'bg-slate-100 text-slate-800',
          label: 'Externally Fulfilled',
        },
      }[status] || { color: 'bg-gray-100 text-gray-800', label: String(status) };

    const label =
      prescription.fulfillment_type === PrescriptionFulfillmentType.DISPENSED_EXTERNAL
        ? 'Externally Fulfilled'
        : config.label;

    return (
      <span
        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.color}`}
      >
        {label}
      </span>
    );
  };

  if (loading && prescriptions.length === 0) {
    return (
      <Card title="Assigned Prescriptions" titleClassName="text-[#0B4DA2]">
        <div className="space-y-4">
          <div className="h-8 w-1/3 animate-pulse rounded bg-gray-200" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded bg-gray-200" />
            ))}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Assigned Prescriptions" titleClassName="text-[#0B4DA2]">
      <div className="space-y-4">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="flex items-center space-x-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as PrescriptionFilter)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE}>
                Awaiting Payment Clearance
              </option>
              <option value={PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE}>
                Ready to Dispense
              </option>
              <option value={PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED}>
                Partially Dispensed
              </option>
              <option value={PharmacyPrescriptionWorkflowStatus.DISPENSED}>Dispensed</option>
              <option value={PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED}>
                Externally Fulfilled
              </option>
              <option value={PharmacyPrescriptionWorkflowStatus.CANCELLED}>Cancelled</option>
              <option value="ALL">All</option>
            </select>

            <div className="text-sm text-gray-500">
              {prescriptions.length} prescription{prescriptions.length !== 1 ? 's' : ''}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {lastUpdated && (
              <span className="text-sm text-gray-500">
                Updated {getTimeAgo(lastUpdated.toISOString())}
              </span>
            )}
            <Button
              size="sm"
              variant="secondary"
              onClick={() => void loadPrescriptions()}
              disabled={loading}
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </Button>
          </div>
        </div>

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <span className="text-red-400">⚠</span>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-600">{error}</p>
                <button
                  onClick={() => void loadPrescriptions()}
                  className="mt-2 text-sm font-medium text-red-700 hover:text-red-800"
                >
                  Try again
                </button>
              </div>
            </div>
          </div>
        )}

        {!error && prescriptions.length === 0 && (
          <div className="py-8 text-center">
            <div className="mb-2 text-gray-400">💊</div>
            <p className="text-gray-500">
              {unitId
                ? `No ${statusFilter === 'ALL' ? 'assigned' : statusFilter.toLowerCase().replaceAll('_', ' ')} prescriptions`
                : 'Select an assigned dispensing unit to view prescriptions'}
            </p>
          </div>
        )}

        {!error && prescriptions.length > 0 && (
          <div className="divide-y rounded-lg border">
            {prescriptions.map((prescription) => (
              <div
                key={prescription.id}
                className={`p-4 transition-colors hover:bg-gray-50 ${
                  onSelectPrescription ? 'cursor-pointer' : ''
                }`}
                onClick={() =>
                  onSelectPrescription && onSelectPrescription(prescription)
                }
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="mb-2 flex items-center space-x-3">
                      {getStatusBadge(prescription)}
                      <span className="text-sm font-medium text-gray-900">
                        {prescription.drug_name}
                      </span>
                    </div>

                    <div className="text-sm text-gray-700">
                      <span className="font-medium">
                        {prescription.patient_name || 'Unknown patient'}
                      </span>
                      <span className="text-gray-500">
                        {' '}
                        • {getPatientDisplay(prescription)}
                      </span>
                    </div>

                    <div className="mt-1 text-xs text-gray-500">
                      Prescribed by{' '}
                      {prescription.prescribed_by_name ||
                        maskId(prescription.prescribed_by)}
                      {prescription.prescribed_by_role
                        ? ` • ${prescription.prescribed_by_role}`
                        : ''}
                    </div>

                    <div className="mt-3 grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
                      <div>
                        <span className="text-gray-600">Payment:</span>
                        <p className="font-medium text-gray-900">
                          {prescription.payment_cleared
                            ? 'Cleared'
                            : 'Awaiting cashier clearance'}
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-600">Dispensing Unit:</span>
                        <p className="font-medium text-gray-900">
                          {prescription.assigned_dispensing_unit_name || 'Unassigned'}
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-600">Cashier Pay Point:</span>
                        <p className="font-medium text-gray-900">
                          {prescription.assigned_cashier_pay_point_name || 'Unassigned'}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
                      <div>
                        <span className="text-gray-600">Dosage:</span>
                        <p className="font-medium text-gray-900">{prescription.dosage}</p>
                      </div>
                      <div>
                        <span className="text-gray-600">Frequency:</span>
                        <p className="font-medium text-gray-900">
                          {prescription.frequency}
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-600">Issued:</span>
                        <p className="font-medium text-gray-900">
                          {getTimeAgo(prescription.issued_at)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center text-xs text-gray-500">
                      <span>
                        Prescription: {maskId(prescription.id)} • Visit:{' '}
                        {maskId(prescription.visit_id)}
                      </span>
                    </div>
                  </div>

                  <div className="ml-4 flex flex-col gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPrescription && onSelectPrescription(prescription);
                      }}
                    >
                      View
                    </Button>
                    {onDispensePrescription &&
                      prescription.workflow_status ===
                        PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE && (
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDispensePrescription(prescription);
                          }}
                        >
                          Dispense
                        </Button>
                      )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
