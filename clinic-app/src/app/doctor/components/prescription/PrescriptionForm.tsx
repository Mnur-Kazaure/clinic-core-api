'use client';

import { useEffect, useState } from 'react';
import {
  pharmacyCatalogGovernanceService,
  PharmacyActiveCatalogItem,
} from '@/domains/pharmacy/services/pharmacyCatalogGovernanceService';
import { prescriptionService } from '@/domains/prescription/services/prescriptionService';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';

interface PrescriptionFormProps {
  visitId: string;
  consultationId: string;
  onSuccess?: (prescriptionId: string) => void;
  onCancel?: () => void;
  compact?: boolean;
}

const FREQUENCY_OPTIONS = [
  'Once daily',
  'Twice daily',
  'Three times daily',
  'Four times daily',
  'Every 6 hours',
  'Every 8 hours',
  'Every 12 hours',
  'As needed (PRN)',
  'Before meals',
  'After meals',
  'At bedtime',
];

const DURATION_OPTIONS = [
  '3 days',
  '5 days',
  '7 days',
  '10 days',
  '14 days',
  '21 days',
  '28 days',
  '30 days',
  '60 days',
  '90 days',
  'Until finished',
  'As directed',
];

export function PrescriptionForm({
  visitId,
  consultationId,
  onSuccess,
  onCancel,
  compact = false,
}: PrescriptionFormProps) {
  const [catalogItems, setCatalogItems] = useState<PharmacyActiveCatalogItem[]>([]);
  const [selectedCatalogItemId, setSelectedCatalogItemId] = useState('');
  const [dosage, setDosage] = useState('');
  const [frequency, setFrequency] = useState('');
  const [duration, setDuration] = useState('');
  const [instructions, setInstructions] = useState('');
  const [quantity, setQuantity] = useState<number | ''>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedCatalogItem =
    catalogItems.find((item) => item.id === selectedCatalogItemId) || null;

  useEffect(() => {
    let mounted = true;
    void pharmacyCatalogGovernanceService
      .listActiveCatalogItems()
      .then((items) => {
        if (mounted) {
          setCatalogItems(items);
        }
      })
      .catch(() => {
        if (mounted) {
          setError('Unable to load active pharmacy catalog items.');
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedCatalogItemId) {
      setError('Please select an active pharmacy catalog item');
      return;
    }

    if (!dosage) {
      setError('Please enter dosage');
      return;
    }

    if (!frequency) {
      setError('Please select frequency');
      return;
    }

    if (!duration) {
      setError('Please select duration');
      return;
    }

    const estimatedQuantity = Number(calculateQuantity() || 1);

    try {
      setIsSubmitting(true);
      setError(null);

      const prescription = await prescriptionService.issuePrescription({
        consultation_id: consultationId,
        pharmacy_catalog_item_id: selectedCatalogItemId,
        dosage,
        frequency,
        duration,
        quantity_prescribed: Number.isFinite(estimatedQuantity)
          ? estimatedQuantity
          : undefined,
        instructions: instructions || undefined,
      });

      if (onSuccess) {
        onSuccess(prescription.id);
      }

      setSelectedCatalogItemId('');
      setDosage('');
      setFrequency('');
      setDuration('');
      setInstructions('');
      setQuantity('');
    } catch (err: any) {
      console.error('Failed to issue prescription:', err);

      if (err.response?.status === 403) {
        setError('You do not have permission to issue prescriptions');
      } else if (err.response?.status === 400) {
        setError(err.response.data.detail || 'Invalid prescription data');
      } else if (err.response?.status === 404) {
        setError('Consultation not found or not accessible');
      } else if (err.response?.status === 409) {
        setError('Cannot issue prescription for completed consultation');
      } else {
        setError('Failed to issue prescription. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCatalogSelect = (itemId: string) => {
    setSelectedCatalogItemId(itemId);
    const item = catalogItems.find((row) => row.id === itemId) || null;
    if (item && !dosage) {
      setDosage(item.strength || item.display_name);
    }
  };

  const calculateQuantity = () => {
    if (!frequency || !duration || !dosage) return '';

    const freqMap: Record<string, number> = {
      'Once daily': 1,
      'Twice daily': 2,
      'Three times daily': 3,
      'Four times daily': 4,
      'Every 6 hours': 4,
      'Every 8 hours': 3,
      'Every 12 hours': 2,
      'As needed (PRN)': 1,
      'Before meals': 3,
      'After meals': 3,
      'At bedtime': 1,
    };

    const daysMap: Record<string, number> = {
      '3 days': 3,
      '5 days': 5,
      '7 days': 7,
      '10 days': 10,
      '14 days': 14,
      '21 days': 21,
      '28 days': 28,
      '30 days': 30,
      '60 days': 60,
      '90 days': 90,
      'Until finished': 7,
      'As directed': 7,
    };

    const dailyDoses = freqMap[frequency] || 1;
    const days = daysMap[duration] || 7;

    return dailyDoses * days;
  };

  if (compact) {
    return (
      <Card title="Issue Prescription">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Medication
            </label>
            <select
              value={selectedCatalogItemId}
              onChange={(e) => handleCatalogSelect(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isSubmitting}
            >
              <option value="">Select approved pharmacy catalog item...</option>
              {catalogItems.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.display_name}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-gray-500">
              Only CMD-approved and Accounts-priced items are available for prescribing.
            </p>
          </div>

          <Input
            label="Dosage"
            value={dosage}
            onChange={(e) => setDosage(e.target.value)}
            placeholder="e.g., 500mg, 10mg, 1 tablet"
            disabled={isSubmitting}
            error={!dosage && selectedCatalogItemId ? 'Dosage is required' : undefined}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Frequency
            </label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isSubmitting}
            >
              <option value="">Select frequency...</option>
              {FREQUENCY_OPTIONS.map((freq) => (
                <option key={freq} value={freq}>
                  {freq}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Duration
            </label>
            <select
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isSubmitting}
            >
              <option value="">Select duration...</option>
              {DURATION_OPTIONS.map((dur) => (
                <option key={dur} value={dur}>
                  {dur}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Instructions (Optional)
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g., Take with food, Avoid alcohol, Monitor blood pressure..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[80px]"
              disabled={isSubmitting}
            />
          </div>

          {frequency && duration && (
            <div className="p-3 bg-blue-50 rounded-md">
              <p className="text-sm text-blue-800">
                Estimated quantity:{' '}
                <span className="font-bold">{calculateQuantity()}</span> doses
              </p>
            </div>
          )}

          <div className="flex space-x-3 pt-4">
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              disabled={
                isSubmitting || !selectedCatalogItemId || !dosage || !frequency || !duration
              }
              className="flex-1"
            >
              Issue Prescription
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

          <div className="text-xs text-gray-500 pt-2">
            <p>Prescription will be sent to pharmacy for dispensing.</p>
            <p>Patient can collect medication after pharmacy processes.</p>
          </div>
        </form>
      </Card>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Issue Prescription
        </h1>
        <p className="text-gray-600 mt-2">
          Prescribe medication for patient treatment
        </p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          <div className="p-4 bg-blue-50 rounded-md">
            <h3 className="font-medium text-blue-800 mb-2">Patient Information</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Visit ID:</span>
                <p className="font-medium">{visitId.substring(0, 12)}...</p>
              </div>
              <div>
                <span className="text-gray-600">Consultation ID:</span>
                <p className="font-medium">
                  {consultationId.substring(0, 12)}...
                </p>
              </div>
              <div className="md:col-span-2">
                <span className="text-gray-600">Prescribing Doctor:</span>
                <p className="font-medium">You (Current Doctor)</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Select Medication
                </h3>

                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Approved Pharmacy Catalog Items
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {catalogItems.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => handleCatalogSelect(item.id)}
                        className={`
                          text-left p-4 rounded-md border text-sm transition-colors
                          ${
                            selectedCatalogItemId === item.id
                              ? 'bg-blue-50 border-blue-300 text-blue-700'
                              : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                          }
                          ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}
                        `}
                        disabled={isSubmitting}
                      >
                        <div className="font-medium">{item.display_name}</div>
                        <div className="text-gray-600 text-xs mt-1">
                          {item.classification} • Charge {item.currency} {(item.unit_price_minor / 100).toFixed(2)}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
                <p className="text-xs text-gray-500">
                  Prescribing is restricted to governed catalog items only.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Dosage
                  </label>
                  <Input
                    value={dosage}
                    onChange={(e) => setDosage(e.target.value)}
                    placeholder="e.g., 500mg, 10mg, 1 tablet"
                    disabled={isSubmitting}
                    error={!dosage && selectedCatalogItemId ? 'Required' : undefined}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Strength and form (mg, mcg, tablets, ml, etc.)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Frequency
                  </label>
                  <select
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={isSubmitting}
                  >
                    <option value="">Select frequency...</option>
                    {FREQUENCY_OPTIONS.map((freq) => (
                      <option key={freq} value={freq}>
                        {freq}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Duration
                  </label>
                  <select
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={isSubmitting}
                  >
                    <option value="">Select duration...</option>
                    {DURATION_OPTIONS.map((dur) => (
                      <option key={dur} value={dur}>
                        {dur}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Estimated Quantity
                  </label>
                  <div className="p-3 bg-gray-100 rounded-md">
                    <p className="text-lg font-bold text-gray-900">
                      {calculateQuantity() || '--'} doses
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Based on frequency and duration
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Special Instructions
                </h3>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="Enter any special instructions for the patient or pharmacist..."
                  className="w-full px-3 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[150px] font-mono text-sm"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="lg:pl-6 lg:border-l">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Prescription Preview
              </h3>

              <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4 shadow-sm">
                <div className="text-center mb-4">
                  <div className="text-2xl font-semibold text-gray-900 mb-1">
                    Rx
                  </div>
                  <h4 className="font-bold text-gray-900">
                    MEDICAL PRESCRIPTION
                  </h4>
                  <p className="text-sm text-gray-500">For Pharmacy Use</p>
                </div>

                <div className="space-y-3">
                  <div className="pb-3 border-b">
                    <span className="text-sm text-gray-600">Medication:</span>
                    <p className="font-bold text-lg text-gray-900">
                      {selectedCatalogItem?.display_name || '________________'}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-sm text-gray-600">Dosage:</span>
                      <p className="font-medium">{dosage || '______'}</p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">Frequency:</span>
                      <p className="font-medium">{frequency || '______'}</p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">Duration:</span>
                      <p className="font-medium">{duration || '______'}</p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">Quantity:</span>
                      <p className="font-medium">
                        {calculateQuantity() || '--'} doses
                      </p>
                    </div>
                  </div>

                  {instructions && (
                    <div className="pt-3 border-t">
                      <span className="text-sm text-gray-600">
                        Instructions:
                      </span>
                      <p className="text-sm text-gray-700 mt-1 whitespace-pre-line">
                        {instructions}
                      </p>
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t text-xs text-gray-500">
                  <p>Visit: {visitId.substring(0, 16)}...</p>
                  <p>Date: {new Date().toLocaleDateString()}</p>
                  <p className="mt-2">Doctor's Signature: ________________</p>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                  <h4 className="font-medium text-yellow-800 mb-2">
                    Prescribing Guidelines
                  </h4>
                  <ul className="text-sm text-yellow-700 space-y-1">
                    <li>• Verify patient allergies before prescribing</li>
                    <li>• Check for drug interactions</li>
                    <li>• Consider renal/hepatic function if applicable</li>
                    <li>• Document clinical indication</li>
                  </ul>
                </div>

                <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
                  <h4 className="font-medium text-blue-800 mb-2">
                    What Happens Next
                  </h4>
                  <ul className="text-sm text-blue-700 space-y-1">
                    <li>1. Prescription sent to pharmacy</li>
                    <li>2. Pharmacy verifies and dispenses</li>
                    <li>3. Patient collects medication</li>
                    <li>4. Prescription status updates to DISPENSED</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-between pt-6 border-t">
            <div className="flex space-x-3">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={isSubmitting}
                disabled={
                  isSubmitting || !selectedCatalogItemId || !dosage || !frequency || !duration
                }
              >
                Issue Prescription
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
            </div>

            <Button
              type="button"
              variant="secondary"
              size="lg"
              onClick={() => {
                setSelectedCatalogItemId('');
                setDosage('');
                setFrequency('');
                setDuration('');
                setInstructions('');
                setQuantity('');
              }}
              disabled={isSubmitting}
            >
              Clear Form
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
