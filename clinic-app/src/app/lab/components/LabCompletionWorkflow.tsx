'use client';

import { useState } from 'react';
import { labService } from '@/domains/lab/services/labService';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';

interface LabCompletionWorkflowProps {
  requestId: string;
  visitId: string;
  testName: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

type CompletionStep = 'CONFIRM' | 'COMPLETE_LAB' | 'TRANSITION_VISIT' | 'DONE';

const COMPLETION_STEPS: CompletionStep[] = [
  'CONFIRM',
  'COMPLETE_LAB',
  'TRANSITION_VISIT',
  'DONE',
];

export function LabCompletionWorkflow({
  requestId,
  visitId,
  testName,
  onSuccess,
  onCancel,
}: LabCompletionWorkflowProps) {
  const [step, setStep] = useState<CompletionStep>('CONFIRM');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completionData, setCompletionData] = useState<any>(null);
  const [visitTransitioned, setVisitTransitioned] = useState(false);

  const handleCompleteLabRequest = async () => {
    try {
      setIsProcessing(true);
      setError(null);

      const result = await labService.completeRequest(requestId);
      setCompletionData(result);
      setStep('COMPLETE_LAB');

      if (result.visit_ready_for_transition) {
        setStep('TRANSITION_VISIT');
        await handleTransitionVisit();
      } else {
        setStep('DONE');
      }
    } catch (err: any) {
      console.error('Lab completion failed:', err);
      setError(err.response?.data?.detail || 'Failed to complete lab request');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTransitionVisit = async () => {
    try {
      setIsProcessing(true);
      setError(null);

      await labService.completeVisitLab(visitId);
      setVisitTransitioned(true);
      setStep('DONE');
    } catch (err: any) {
      console.error('Visit transition failed:', err);
      setError(err.response?.data?.detail || 'Failed to update visit status');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFinish = () => {
    if (onSuccess) {
      onSuccess();
    }
  };

  const resetWorkflow = () => {
    setStep('CONFIRM');
    setIsProcessing(false);
    setError(null);
    setCompletionData(null);
    setVisitTransitioned(false);
  };

  const completedIndex = COMPLETION_STEPS.indexOf(step);

  return (
    <Card
      title={`Complete Lab Workflow: ${testName}`}
      titleClassName="text-[#0B4DA2]"
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between mb-6">
          {COMPLETION_STEPS.map((currentStep, index) => (
            <div key={currentStep} className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  step === currentStep
                    ? 'bg-blue-600 text-white'
                    : index < completedIndex
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-200 text-gray-500'
                }`}
              >
                {index + 1}
              </div>
              <span className="ml-2 text-sm font-medium whitespace-nowrap">
                {currentStep === 'CONFIRM' && 'Confirm'}
                {currentStep === 'COMPLETE_LAB' && 'Complete Lab'}
                {currentStep === 'TRANSITION_VISIT' && 'Update Visit'}
                {currentStep === 'DONE' && 'Done'}
              </span>
              {index < COMPLETION_STEPS.length - 1 && (
                <div
                  className={`mx-4 h-0.5 w-8 ${
                    index < completedIndex ? 'bg-green-600' : 'bg-gray-300'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-600">{error}</p>
            <button
              onClick={resetWorkflow}
              className="mt-2 text-sm font-medium text-red-700 hover:text-red-800"
            >
              Start over
            </button>
          </div>
        )}

        {step === 'CONFIRM' && (
          <div className="space-y-6">
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-yellow-800 font-medium">Important Notice</p>
              <p className="text-yellow-700 text-sm mt-1">
                Completing this lab request will:
              </p>
              <ul className="list-disc pl-5 mt-2 text-sm text-yellow-700 space-y-1">
                <li>Mark the lab request as COMPLETED</li>
                <li>Set the completion timestamp</li>
                <li>Update the visit status to LAB_COMPLETED</li>
                <li>Make the visit available for next clinical steps</li>
              </ul>
            </div>

            <div className="p-4 border rounded-md">
              <h4 className="font-medium text-gray-900 mb-2">Details</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Test:</span>
                  <p className="font-medium">{testName}</p>
                </div>
                <div>
                  <span className="text-gray-600">Request ID:</span>
                  <p className="font-medium">{requestId.substring(0, 12)}...</p>
                </div>
                <div>
                  <span className="text-gray-600">Visit ID:</span>
                  <p className="font-medium">{visitId.substring(0, 12)}...</p>
                </div>
              </div>
            </div>

            <div className="flex justify-between pt-4">
              {onCancel && (
                <Button
                  variant="secondary"
                  onClick={onCancel}
                  disabled={isProcessing}
                >
                  Cancel
                </Button>
              )}
              <Button
                variant="primary"
                onClick={handleCompleteLabRequest}
                isLoading={isProcessing}
                disabled={isProcessing}
              >
                Start Completion
              </Button>
            </div>
          </div>
        )}

        {step === 'COMPLETE_LAB' && (
          <div className="space-y-6">
            <div className="p-4 bg-green-50 border border-green-200 rounded-md">
              <div className="flex items-center">
                <span className="text-green-500 mr-2">Done</span>
                <p className="text-green-800 font-medium">
                  Lab Request Completed
                </p>
              </div>
              {completionData && (
                <div className="mt-2 text-sm text-green-700">
                  <p>Status: {completionData.status}</p>
                  <p>
                    Completed at:{' '}
                    {new Date(completionData.completed_at).toLocaleString()}
                  </p>
                </div>
              )}
            </div>

            {completionData?.visit_ready_for_transition ? (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-blue-800 font-medium">
                  Ready to update visit status
                </p>
                <p className="text-blue-700 text-sm mt-1">
                  The visit can now be transitioned to LAB_COMPLETED status.
                </p>
              </div>
            ) : (
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-md">
                <p className="text-gray-700">
                  Visit does not require status update at this time.
                </p>
              </div>
            )}

            <div className="flex justify-between pt-4">
              {onCancel && (
                <Button
                  variant="secondary"
                  onClick={onCancel}
                  disabled={isProcessing}
                >
                  Close
                </Button>
              )}
              {completionData?.visit_ready_for_transition ? (
                <Button
                  variant="primary"
                  onClick={handleTransitionVisit}
                  isLoading={isProcessing}
                  disabled={isProcessing}
                >
                  Update Visit Status
                </Button>
              ) : (
                <Button variant="primary" onClick={handleFinish}>
                  Finish
                </Button>
              )}
            </div>
          </div>
        )}

        {step === 'TRANSITION_VISIT' && (
          <div className="space-y-6">
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
              <div className="flex items-center">
                <span className="text-blue-500 mr-2">Loading</span>
                <p className="text-blue-800 font-medium">
                  Updating Visit Status
                </p>
              </div>
              <p className="text-blue-700 text-sm mt-1">
                Transitioning visit to LAB_COMPLETED status...
              </p>
            </div>

            <div className="text-sm text-gray-600">
              <p>This will:</p>
              <ul className="list-disc pl-5 mt-1 space-y-1">
                <li>Update the visit status to LAB_COMPLETED</li>
                <li>Allow the visit to proceed to next clinical steps</li>
                <li>Create an audit trail entry</li>
              </ul>
            </div>

            {isProcessing ? (
              <div className="text-center py-4">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-600">Updating visit status...</p>
              </div>
            ) : (
              <div className="flex justify-between pt-4">
                <Button
                  variant="secondary"
                  onClick={() => setStep('COMPLETE_LAB')}
                  disabled={isProcessing}
                >
                  Back
                </Button>
                <Button
                  variant="primary"
                  onClick={handleTransitionVisit}
                  isLoading={isProcessing}
                  disabled={isProcessing}
                >
                  Complete Transition
                </Button>
              </div>
            )}
          </div>
        )}

        {step === 'DONE' && (
          <div className="space-y-6">
            <div className="text-center py-8">
              <div className="text-4xl mb-4">Done</div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                Workflow Complete
              </h3>
              <p className="text-gray-600">
                The lab request has been successfully processed.
              </p>
            </div>

            <div className="space-y-4">
              {completionData && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-md">
                  <h4 className="font-medium text-green-800 mb-2">
                    Lab Request
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-green-700">Status:</span>
                      <span className="ml-2 font-medium">
                        {completionData.status}
                      </span>
                    </div>
                    <div>
                      <span className="text-green-700">Completed:</span>
                      <span className="ml-2 font-medium">
                        {new Date(
                          completionData.completed_at
                        ).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {visitTransitioned && (
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
                  <h4 className="font-medium text-blue-800 mb-2">
                    Visit Updated
                  </h4>
                  <p className="text-sm text-blue-700">
                    Visit status transitioned to LAB_COMPLETED
                  </p>
                </div>
              )}
            </div>

            <div className="flex justify-between pt-4">
              <Button variant="secondary" onClick={resetWorkflow}>
                Process Another
              </Button>
              <Button variant="primary" onClick={handleFinish}>
                Finish
              </Button>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
