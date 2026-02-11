'use client';

import { useState } from 'react';
import { pharmacyService } from '@/domains/pharmacy/services/pharmacyService';
import { PrescriptionResponse } from '@/shared/types';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';

interface DispenseFormProps {
  prescription: PrescriptionResponse;
  pharmacistId: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function DispenseForm({
  prescription,
  pharmacistId,
  onSuccess,
  onCancel,
}: DispenseFormProps) {
  const [quantity, setQuantity] = useState<number | ''>('');
  const [externalNote, setExternalNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const maskId = (value?: string | null) =>
    value ? `${value.slice(0, 8)}...` : '—';

  const patientLabel = prescription.patient_mrn
    ? `MRN ${prescription.patient_mrn}`
    : `ID ${maskId(prescription.patient_id)}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!quantity || quantity <= 0) {
      setError('Please enter a valid quantity');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setSuccessMessage(null);

      await pharmacyService.dispensePrescription(prescription.id, {
        pharmacist_id: pharmacistId,
        quantity: Number(quantity),
      });

      setSuccess(true);
      setSuccessMessage('Dispensed successfully.');
      setQuantity('');

      if (onSuccess) {
        onSuccess();
      }

      setTimeout(() => {
        setSuccess(false);
        setSuccessMessage(null);
      }, 2500);
    } catch (err: any) {
      console.error('Failed to dispense prescription:', err);
      if (err.response?.status === 409) {
        setError(
          err.response?.data?.detail ||
            'Prescription is not available for dispensing'
        );
      } else if (err.response?.status === 403) {
        setError('You do not have permission to dispense this prescription');
      } else {
        setError(err.response?.data?.detail || 'Failed to dispense prescription');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExternalFulfill = async () => {
    const note = externalNote.trim();
    if (note.length < 3) {
      setError('Please enter a short note (at least 3 characters).');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setSuccessMessage(null);

      await pharmacyService.fulfillPrescriptionExternal(prescription.id, {
        note,
      });

      setSuccess(true);
      setSuccessMessage('Marked as dispensed externally.');
      setExternalNote('');

      if (onSuccess) {
        onSuccess();
      }

      setTimeout(() => {
        setSuccess(false);
        setSuccessMessage(null);
      }, 2500);
    } catch (err: any) {
      console.error('Failed to mark external fulfillment:', err);
      if (err.response?.status === 409) {
        setError(
          err.response?.data?.detail || 'Prescription already fulfilled.'
        );
      } else if (err.response?.status === 403) {
        setError('You do not have permission to fulfill this prescription');
      } else {
        setError(
          err.response?.data?.detail || 'Failed to mark external fulfillment'
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card title={`Dispense: ${prescription.drug_name}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {success && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-md">
            <p className="text-sm text-green-600">
              {successMessage || 'Success.'}
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Patient:</span>
            <p className="font-medium text-gray-900">
              {prescription.patient_name || 'Unknown patient'} • {patientLabel}
            </p>
          </div>
          <div>
            <span className="text-gray-600">Prescribed By:</span>
            <p className="font-medium text-gray-900">
              {prescription.prescribed_by_name ||
                maskId(prescription.prescribed_by)}
            </p>
          </div>
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
            <span className="text-gray-600">Duration:</span>
            <p className="font-medium text-gray-900">{prescription.duration}</p>
          </div>
          <div>
            <span className="text-gray-600">Visit ID:</span>
            <p className="font-medium text-gray-900">
              {maskId(prescription.visit_id)}
            </p>
          </div>
        </div>

        {prescription.instructions && (
          <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
            <p className="font-medium text-gray-900 mb-1">Instructions</p>
            <p>{prescription.instructions}</p>
          </div>
        )}

        <Input
          label="Quantity Dispensed"
          type="number"
          min="1"
          value={quantity}
          onChange={(e) =>
            setQuantity(e.target.value === '' ? '' : Number(e.target.value))
          }
          placeholder="Enter quantity"
          disabled={isSubmitting}
        />

        <div className="pt-2 border-t">
          <p className="text-sm font-medium text-gray-900">
            Out of stock?
          </p>
          <p className="text-xs text-gray-600 mt-1">
            If the clinic does not have this medication, record that the patient
            will purchase it externally. This will still complete the visit when
            all prescriptions are fulfilled.
          </p>

          <div className="mt-3">
            <label className="block text-sm font-medium text-gray-700">
              Note
            </label>
            <textarea
              value={externalNote}
              onChange={(e) => setExternalNote(e.target.value)}
              placeholder="e.g., Out of stock; patient to buy outside"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              disabled={isSubmitting}
            />
          </div>

          <div className="mt-3">
            <Button
              type="button"
              variant="secondary"
              onClick={handleExternalFulfill}
              disabled={isSubmitting}
              className="w-full"
            >
              Mark as Dispensed Externally
            </Button>
          </div>
        </div>

        <div className="flex space-x-3 pt-2">
          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting}
            disabled={isSubmitting}
            className="flex-1"
          >
            Dispense Medication
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
