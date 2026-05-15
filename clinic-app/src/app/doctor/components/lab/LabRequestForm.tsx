'use client';

import { useEffect, useMemo, useState } from 'react';
import { labRequestService } from '@/domains/lab/services/labRequestService';
import {
  billingWorkflowService,
  ChargeItemPrice,
} from '@/domains/billing/services/billingWorkflowService';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';

interface LabRequestFormProps {
  visitId: string;
  consultationId: string;
  onSuccess?: (labRequestId: string) => void;
  onCancel?: () => void;
  compact?: boolean;
}

function formatMoney(amountMinor: number, currency: string): string {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amountMinor / 100);
}

export function LabRequestForm({
  visitId,
  consultationId,
  onSuccess,
  onCancel,
  compact = false,
}: LabRequestFormProps) {
  const [selectedCode, setSelectedCode] = useState('');
  const [instructions, setInstructions] = useState('');
  const [labTests, setLabTests] = useState<ChargeItemPrice[]>([]);
  const [isLoadingTests, setIsLoadingTests] = useState(true);
  const [testLoadError, setTestLoadError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadTests() {
      try {
        setIsLoadingTests(true);
        setTestLoadError(null);
        const items = await billingWorkflowService.listChargeItems('LAB_TEST');
        if (cancelled) {
          return;
        }
        setLabTests(items.filter((item) => item.active));
      } catch (err) {
        console.error('Failed to load configured lab tests:', err);
        if (!cancelled) {
          setTestLoadError(
            'Unable to load configured lab tests. Ask admin to verify laboratory configuration.'
          );
          setLabTests([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingTests(false);
        }
      }
    }

    loadTests();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedTest = useMemo(
    () => labTests.find((item) => item.code === selectedCode) || null,
    [labTests, selectedCode]
  );

  const testsByCategory = useMemo(() => {
    const grouped: Record<string, ChargeItemPrice[]> = {};
    for (const test of labTests) {
      if (!grouped[test.category]) {
        grouped[test.category] = [];
      }
      grouped[test.category].push(test);
    }
    for (const tests of Object.values(grouped)) {
      tests.sort((left, right) => {
        const leftOrder = left.display_order ?? Number.MAX_SAFE_INTEGER;
        const rightOrder = right.display_order ?? Number.MAX_SAFE_INTEGER;
        if (leftOrder !== rightOrder) {
          return leftOrder - rightOrder;
        }
        return left.name.localeCompare(right.name);
      });
    }
    return grouped;
  }, [labTests]);

  const extractErrorDetail = (err: unknown): string | null => {
    if (typeof err !== 'object' || err === null || !('response' in err)) {
      return null;
    }
    const response = (err as { response?: { data?: { detail?: string } } })
      .response;
    return response?.data?.detail || null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedTest) {
      setError('Please select a configured lab test.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const labRequest = await labRequestService.createLabRequest({
        visit_id: visitId,
        test_name: selectedTest.name,
        test_code: selectedTest.code,
        special_instructions: instructions || undefined,
      });

      if (onSuccess) {
        onSuccess(labRequest.id);
      }

      setSelectedCode('');
      setInstructions('');
    } catch (err: unknown) {
      console.error('Failed to create lab request:', err);
      const detail = extractErrorDetail(err);
      const statusCode =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { status?: number } }).response?.status
          : undefined;

      if (statusCode === 403) {
        setError('You do not have permission to request lab tests');
      } else if (statusCode === 422) {
        setError(detail || 'This test is missing a valid price configuration.');
      } else if (statusCode === 404) {
        setError('Visit not found or not accessible');
      } else {
        setError('Failed to create lab request. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (compact) {
    return (
      <Card title="Request Lab Test">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
          {testLoadError && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-md">
              <p className="text-sm text-amber-700">{testLoadError}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Select Test</label>
            <select
              value={selectedCode}
              onChange={(e) => setSelectedCode(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isSubmitting || isLoadingTests || labTests.length === 0}
            >
              <option value="">
                {isLoadingTests ? 'Loading tests...' : 'Select a test...'}
              </option>
              {Object.entries(testsByCategory).map(([category, tests]) => (
                <optgroup key={category} label={category}>
                  {tests.map((test) => (
                    <option key={test.code} value={test.code}>
                      {test.name} ({formatMoney(test.default_amount_minor, test.currency)})
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Special Instructions (Optional)
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Any special instructions for the lab..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[80px]"
              disabled={isSubmitting}
            />
          </div>

          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            {selectedTest
              ? `Charge: ${formatMoney(selectedTest.default_amount_minor, selectedTest.currency)}`
              : 'Select a test to view charge.'}
          </div>

          <div className="flex space-x-3 pt-4">
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              disabled={isSubmitting || !selectedTest || !!testLoadError}
              className="flex-1"
            >
              Request Lab Test
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
            <p>Billing item is created automatically for cashier payment.</p>
            <p>Lab receives this request only after payment verification.</p>
          </div>
        </form>
      </Card>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Request Lab Test</h1>
        <p className="text-gray-600 mt-2">
          Select a configured laboratory test to generate billing and route payment to cashier.
        </p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">{error}</p>
            </div>
          )}
          {testLoadError && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-md">
              <p className="text-amber-700">{testLoadError}</p>
            </div>
          )}

          <div className="p-4 bg-blue-50 rounded-md">
            <h3 className="font-medium text-blue-800 mb-2">Patient Information</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Visit ID:</span>
                <p className="font-medium">{visitId.substring(0, 12)}...</p>
              </div>
              <div>
                <span className="text-gray-600">Consultation ID:</span>
                <p className="font-medium">{consultationId.substring(0, 12)}...</p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Select Laboratory Test</h3>

            <div className="space-y-4">
              {isLoadingTests && (
                <p className="text-sm text-gray-500">Loading configured test catalog...</p>
              )}
              {!isLoadingTests && labTests.length === 0 && !testLoadError && (
                <p className="text-sm text-gray-500">
                  No active configured lab tests found. Ask admin to configure the laboratory catalog.
                </p>
              )}

              {Object.entries(testsByCategory).map(([category, tests]) => (
                <div key={category} className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                    {category}
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {tests.map((test) => {
                      const active = selectedCode === test.code;
                      return (
                        <button
                          key={test.code}
                          type="button"
                          onClick={() => setSelectedCode(test.code)}
                          className={`text-left p-3 rounded-md border text-sm transition-colors ${
                            active
                              ? 'bg-blue-50 border-blue-300 text-blue-700'
                              : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                          } ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
                          disabled={isSubmitting}
                        >
                          <div className="font-medium">{test.name}</div>
                          <div className="mt-1 text-xs text-slate-500">
                            {formatMoney(test.default_amount_minor, test.currency)}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Instructions</h3>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Special Instructions
              </label>
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Any special handling requirements, sample collection notes, or clinical context for the lab..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
                disabled={isSubmitting}
              />
            </div>

            <div className="md:pl-6 md:border-l">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Request Summary</h3>

              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div>
                  <span className="text-sm text-gray-600">Selected Test:</span>
                  <p className="font-medium">{selectedTest?.name || 'Not selected'}</p>
                </div>

                <div>
                  <span className="text-sm text-gray-600">Charge:</span>
                  <p className="font-medium">
                    {selectedTest
                      ? formatMoney(
                          selectedTest.default_amount_minor,
                          selectedTest.currency
                        )
                      : '—'}
                  </p>
                </div>

                <div>
                  <span className="text-sm text-gray-600">Instructions:</span>
                  <p className="text-sm text-gray-700 mt-1">
                    {instructions || 'No special instructions'}
                  </p>
                </div>
              </div>

              <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                <h4 className="font-medium text-yellow-800 mb-2">Workflow</h4>
                <ul className="text-sm text-yellow-700 space-y-1">
                  <li>• Request creates a pending billing item automatically</li>
                  <li>• Cashier must complete payment for this test</li>
                  <li>• Lab queue receives the request only after payment</li>
                </ul>
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
                disabled={isSubmitting || !selectedTest || !!testLoadError}
              >
                Submit Lab Request
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
                setSelectedCode('');
                setInstructions('');
              }}
              disabled={isSubmitting}
            >
              Reset Form
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
