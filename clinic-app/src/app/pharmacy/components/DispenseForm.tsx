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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!quantity || quantity <= 0) {
      setError('Please enter a valid quantity');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      await pharmacyService.dispensePrescription(prescription.id, {
        pharmacist_id: pharmacistId,
        quantity: Number(quantity),
      });

      setSuccess(true);
      setQuantity('');

      if (onSuccess) {
        onSuccess();
      }

      setTimeout(() => {
        setSuccess(false);
      }, 2500);
    } catch (err: any) {
      console.error('Failed to dispense prescription:', err);
      if (err.response?.status === 409) {
        setError('Prescription is not available for dispensing');
      } else if (err.response?.status === 403) {
        setError('You do not have permission to dispense this prescription');
      } else {
        setError(err.response?.data?.detail || 'Failed to dispense prescription');
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
              Dispensed successfully.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
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
              {prescription.visit_id.substring(0, 12)}...
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
