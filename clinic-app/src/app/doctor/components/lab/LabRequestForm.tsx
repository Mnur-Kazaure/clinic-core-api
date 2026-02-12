'use client';

import { useState } from 'react';
import { labRequestService } from '@/domains/lab/services/labRequestService';
import { PHC_LAB_TEST_CATALOG } from '@/domains/lab/constants/labTestCatalog';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';

interface LabRequestFormProps {
  visitId: string;
  consultationId: string;
  onSuccess?: (labRequestId: string) => void;
  onCancel?: () => void;
  compact?: boolean;
}

const TESTS_BY_CATEGORY = PHC_LAB_TEST_CATALOG.reduce<
  Record<string, string[]>
>((acc, test) => {
  if (!acc[test.category]) {
    acc[test.category] = [];
  }
  acc[test.category].push(test.name);
  return acc;
}, {});

export function LabRequestForm({
  visitId,
  consultationId,
  onSuccess,
  onCancel,
  compact = false,
}: LabRequestFormProps) {
  const [testName, setTestName] = useState('');
  const [customTest, setCustomTest] = useState('');
  const [instructions, setInstructions] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extractErrorDetail = (err: unknown): string | null => {
    if (typeof err !== 'object' || err === null || !('response' in err)) {
      return null;
    }
    const response = (err as { response?: { data?: { detail?: string } } }).response;
    return response?.data?.detail || null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!testName && !customTest) {
      setError('Please select or enter a test name');
      return;
    }

    const finalTestName = testName || customTest;

    try {
      setIsSubmitting(true);
      setError(null);

      const labRequest = await labRequestService.createLabRequest({
        visit_id: visitId,
        test_name: finalTestName,
        special_instructions: instructions || undefined,
      });

      if (onSuccess) {
        onSuccess(labRequest.id);
      }

      setTestName('');
      setCustomTest('');
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
      } else if (statusCode === 400) {
        setError(detail || 'Invalid request');
      } else if (statusCode === 404) {
        setError('Visit not found or not accessible');
      } else {
        setError('Failed to create lab request. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTestSelect = (test: string) => {
    setTestName(test);
    setCustomTest('');
  };

  const handleCustomTestChange = (value: string) => {
    setCustomTest(value);
    if (value) {
      setTestName('');
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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Test
            </label>
            <div className="space-y-2">
              <select
                value={testName}
                onChange={(e) => handleTestSelect(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isSubmitting}
              >
                <option value="">Select a test...</option>
                {Object.entries(TESTS_BY_CATEGORY).map(([category, tests]) => (
                  <optgroup key={category} label={category}>
                    {tests.map((test) => (
                      <option key={test} value={test}>
                        {test}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>

              <div className="text-center text-sm text-gray-500">OR</div>

              <Input
                value={customTest}
                onChange={(e) => handleCustomTestChange(e.target.value)}
                placeholder="Enter custom test name..."
                disabled={isSubmitting}
              />
            </div>
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

          <div className="flex space-x-3 pt-4">
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              disabled={isSubmitting}
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
            <p>Request will be sent to the lab department for processing.</p>
            <p>Visit status will update to LAB_REQUESTED.</p>
          </div>
        </form>
      </Card>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Request Lab Test
        </h1>
        <p className="text-gray-600 mt-2">
          Order laboratory tests for patient assessment
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
            <div className="grid grid-cols-2 gap-4 text-sm">
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
            </div>
          </div>

          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Select Laboratory Test
            </h3>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                PHC Tests (Click to select)
              </label>
              <div className="space-y-4">
                {Object.entries(TESTS_BY_CATEGORY).map(([category, tests]) => (
                  <div key={category} className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                      {category}
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {tests.map((test) => (
                        <button
                          key={test}
                          type="button"
                          onClick={() => handleTestSelect(test)}
                          className={`
                            text-left p-3 rounded-md border text-sm transition-colors
                            ${
                              testName === test
                                ? 'bg-blue-50 border-blue-300 text-blue-700'
                                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                            }
                            ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}
                          `}
                          disabled={isSubmitting}
                        >
                          {test}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Custom Test Name
              </label>
              <Input
                value={customTest}
                onChange={(e) => handleCustomTestChange(e.target.value)}
                placeholder="Enter test name if not in list above..."
                disabled={isSubmitting}
              />
              <p className="text-xs text-gray-500 mt-1">
                Selected test:{' '}
                <span className="font-medium">
                  {testName || customTest || 'None'}
                </span>
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Instructions
              </h3>

              <div className="space-y-4">
                <div>
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
              </div>
            </div>

            <div className="md:pl-6 md:border-l">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Request Summary
              </h3>

              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div>
                  <span className="text-sm text-gray-600">Test Name:</span>
                  <p className="font-medium">
                    {testName || customTest || 'Not selected'}
                  </p>
                </div>

                <div>
                  <span className="text-sm text-gray-600">Visit ID:</span>
                  <p className="font-medium text-sm">
                    {visitId.substring(0, 16)}...
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
                <h4 className="font-medium text-yellow-800 mb-2">
                  Important Notes
                </h4>
                <ul className="text-sm text-yellow-700 space-y-1">
                  <li>• Lab requests are sent to the laboratory department</li>
                  <li>• Visit status updates to LAB_REQUESTED after ordering</li>
                  <li>• Results will be recorded in the patient&apos;s chart</li>
                  <li>• You can request multiple tests per consultation</li>
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
                disabled={isSubmitting || (!testName && !customTest)}
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
                setTestName('');
                setCustomTest('');
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
