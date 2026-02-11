'use client';

import { useEffect, useState } from 'react';
import { pharmacyService } from '@/domains/pharmacy/services/pharmacyService';
import { PrescriptionResponse } from '@/shared/types';
import { PrescriptionFulfillmentType, PrescriptionStatus } from '@/shared/enums';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';

type PrescriptionFilter = PrescriptionStatus | 'ALL';

interface PharmacyQueueProps {
  onSelectPrescription?: (prescription: PrescriptionResponse) => void;
  onDispensePrescription?: (prescription: PrescriptionResponse) => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function PharmacyQueue({
  onSelectPrescription,
  onDispensePrescription,
  autoRefresh = true,
  refreshInterval = 30000,
}: PharmacyQueueProps) {
  const [prescriptions, setPrescriptions] = useState<PrescriptionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] =
    useState<PrescriptionFilter>(PrescriptionStatus.ISSUED);
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
      const statusParam = statusFilter === 'ALL' ? undefined : statusFilter;
      const data = await pharmacyService.getPrescriptions(statusParam);
      setPrescriptions(data);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to load prescriptions:', err);
      setError('Unable to load prescriptions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPrescriptions();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(loadPrescriptions, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, statusFilter]);

  useEffect(() => {
    loadPrescriptions();
  }, [statusFilter]);

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
    const status = prescription.status;
    const config =
      {
        ISSUED: { color: 'bg-yellow-100 text-yellow-800', label: 'Issued' },
        DISPENSED: { color: 'bg-green-100 text-green-800', label: 'Dispensed' },
        CANCELLED: { color: 'bg-red-100 text-red-800', label: 'Cancelled' },
      }[status] || { color: 'bg-gray-100 text-gray-800', label: status };

    const label =
      status === PrescriptionStatus.DISPENSED &&
      prescription.fulfillment_type ===
        PrescriptionFulfillmentType.DISPENSED_EXTERNAL
        ? 'Dispensed (External)'
        : config.label;

    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}
      >
        {label}
      </span>
    );
  };

  if (loading && prescriptions.length === 0) {
    return (
      <Card title="Prescription Queue" titleClassName="text-[#0B4DA2]">
        <div className="space-y-4">
          <div className="animate-pulse h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  const filteredPrescriptions = prescriptions.filter(
    (prescription) => statusFilter === 'ALL' || prescription.status === statusFilter
  );

  return (
    <Card title="Prescription Queue" titleClassName="text-[#0B4DA2]">
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as PrescriptionFilter)
              }
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={PrescriptionStatus.ISSUED}>Issued</option>
              <option value={PrescriptionStatus.DISPENSED}>Dispensed</option>
              <option value={PrescriptionStatus.CANCELLED}>Cancelled</option>
              <option value="ALL">All</option>
            </select>

            <div className="text-sm text-gray-500">
              {filteredPrescriptions.length} prescription
              {filteredPrescriptions.length !== 1 ? 's' : ''}
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
              onClick={loadPrescriptions}
              disabled={loading}
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </Button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <div className="flex">
              <div className="flex-shrink-0">
                <span className="text-red-400">⚠</span>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-600">{error}</p>
                <button
                  onClick={loadPrescriptions}
                  className="mt-2 text-sm font-medium text-red-700 hover:text-red-800"
                >
                  Try again
                </button>
              </div>
            </div>
          </div>
        )}

        {!error && filteredPrescriptions.length === 0 && (
          <div className="text-center py-8">
            <div className="text-gray-400 mb-2">💊</div>
            <p className="text-gray-500">
              {statusFilter === PrescriptionStatus.ISSUED
                ? 'No issued prescriptions'
                : `No ${statusFilter.toLowerCase()} prescriptions`}
            </p>
          </div>
        )}

        {!error && filteredPrescriptions.length > 0 && (
          <div className="border rounded-lg divide-y">
            {filteredPrescriptions.map((prescription) => (
              <div
                key={prescription.id}
                className={`p-4 hover:bg-gray-50 transition-colors ${
                  onSelectPrescription ? 'cursor-pointer' : ''
                }`}
                onClick={() =>
                  onSelectPrescription && onSelectPrescription(prescription)
                }
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
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

                    <div className="text-xs text-gray-500 mt-1">
                      Prescribed by{' '}
                      {prescription.prescribed_by_name ||
                        maskId(prescription.prescribed_by)}
                      {prescription.prescribed_by_role
                        ? ` • ${prescription.prescribed_by_role}`
                        : ''}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">Dosage:</span>
                        <p className="font-medium text-gray-900">
                          {prescription.dosage}
                        </p>
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

                  {onSelectPrescription &&
                    prescription.status === PrescriptionStatus.ISSUED && (
                      <div className="ml-4">
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onDispensePrescription) {
                              onDispensePrescription(prescription);
                              return;
                            }
                            onSelectPrescription(prescription);
                          }}
                        >
                          Dispense
                        </Button>
                      </div>
                    )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
