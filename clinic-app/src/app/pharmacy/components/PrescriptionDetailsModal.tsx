'use client';

import { useState } from 'react';
import { pharmacyService } from '@/domains/pharmacy/services/pharmacyService';
import { PrescriptionResponse } from '@/shared/types';
import {
  PrescriptionFulfillmentType,
  PrescriptionStatus,
} from '@/shared/enums';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';

interface PrescriptionDetailsModalProps {
  prescription: PrescriptionResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onDispense?: (prescription: PrescriptionResponse) => void;
  onRefresh?: (prescription: PrescriptionResponse) => void;
}

export function PrescriptionDetailsModal({
  prescription,
  isOpen,
  onClose,
  onDispense,
  onRefresh,
}: PrescriptionDetailsModalProps) {
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  if (!isOpen || !prescription) return null;

  const maskId = (value?: string | null) =>
    value ? `${value.slice(0, 8)}...` : '—';

  const patientLabel = prescription.patient_mrn
    ? `MRN ${prescription.patient_mrn}`
    : `ID ${maskId(prescription.patient_id)}`;

  const handleRefresh = async () => {
    try {
      const refreshed = await pharmacyService.getPrescription(prescription.id);
      setLastUpdated(new Date());
      if (onRefresh) {
        onRefresh(refreshed);
      }
    } catch (error) {
      console.error('Failed to refresh prescription:', error);
    }
  };

  const statusBadge = {
    ISSUED: 'bg-yellow-100 text-yellow-800',
    DISPENSED: 'bg-green-100 text-green-800',
    CANCELLED: 'bg-red-100 text-red-800',
  }[prescription.status];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                Prescription: {prescription.drug_name}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {prescription.patient_name || 'Unknown patient'} • {patientLabel}
              </p>
              <div className="flex items-center space-x-4 mt-2">
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${statusBadge}`}
                >
                  {prescription.status}
                </span>
                <span className="text-sm text-gray-500">
                  ID: {maskId(prescription.id)}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card title="Medication Details" titleClassName="text-[#0B4DA2]">
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-gray-500">Drug</dt>
                  <dd className="text-gray-900 font-medium">
                    {prescription.drug_name}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Dosage</dt>
                  <dd className="text-gray-900">{prescription.dosage}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Frequency</dt>
                  <dd className="text-gray-900">{prescription.frequency}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Duration</dt>
                  <dd className="text-gray-900">{prescription.duration}</dd>
                </div>
                {prescription.instructions && (
                  <div>
                    <dt className="text-gray-500">Instructions</dt>
                    <dd className="text-gray-900">{prescription.instructions}</dd>
                  </div>
                )}
              </dl>
            </Card>

            <Card title="Visit & Audit" titleClassName="text-[#0B4DA2]">
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-gray-500">Visit ID</dt>
                  <dd className="text-gray-900">
                    {maskId(prescription.visit_id)}
                  </dd>
                </div>
                {prescription.status === PrescriptionStatus.DISPENSED &&
                  prescription.fulfillment_type && (
                    <div>
                      <dt className="text-gray-500">Fulfillment</dt>
                      <dd className="text-gray-900">
                        {prescription.fulfillment_type ===
                        PrescriptionFulfillmentType.DISPENSED_EXTERNAL
                          ? 'External'
                          : 'In-house'}
                      </dd>
                    </div>
                  )}
                <div>
                  <dt className="text-gray-500">Prescribed By</dt>
                  <dd className="text-gray-900">
                    {prescription.prescribed_by_name ||
                      maskId(prescription.prescribed_by)}
                    {prescription.prescribed_by_role
                      ? ` • ${prescription.prescribed_by_role}`
                      : ''}
                  </dd>
                </div>
                {prescription.dispensed_by && (
                  <div>
                    <dt className="text-gray-500">Dispensed By</dt>
                    <dd className="text-gray-900">
                      {prescription.dispensed_by_name ||
                        maskId(prescription.dispensed_by)}
                      {prescription.dispensed_by_role
                        ? ` • ${prescription.dispensed_by_role}`
                        : ''}
                    </dd>
                  </div>
                )}
                {prescription.fulfillment_type ===
                  PrescriptionFulfillmentType.DISPENSED_EXTERNAL &&
                  prescription.fulfillment_note && (
                    <div>
                      <dt className="text-gray-500">External Note</dt>
                      <dd className="text-gray-900">
                        {prescription.fulfillment_note}
                      </dd>
                    </div>
                  )}
              </dl>
            </Card>
          </div>

          <Card title="History" titleClassName="text-[#0B4DA2]">
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Issued</span>
                <span className="text-gray-900">
                  {new Date(prescription.issued_at).toLocaleString()}
                </span>
              </div>
              {prescription.dispensed_at && (
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Dispensed</span>
                  <span className="text-gray-900">
                    {new Date(prescription.dispensed_at).toLocaleString()}
                  </span>
                </div>
              )}
              {prescription.cancelled_at && (
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Cancelled</span>
                  <span className="text-gray-900">
                    {new Date(prescription.cancelled_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          </Card>

          <div className="flex items-center justify-end space-x-3 pt-4">
            {lastUpdated && (
              <span className="text-sm text-gray-500">
                Last updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <Button variant="secondary" onClick={handleRefresh}>
              Refresh
            </Button>
            {onDispense && prescription.status === PrescriptionStatus.ISSUED && (
              <Button
                variant="primary"
                onClick={() => onDispense(prescription)}
              >
                Dispense
              </Button>
            )}
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
