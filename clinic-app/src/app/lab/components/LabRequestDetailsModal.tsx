'use client';

import { useEffect, useState } from 'react';
import { labService, LabRequest, LabResult } from '@/domains/lab/services/labService';
import { visitService } from '@/domains/visit/services/visitService';
import { PurposeOfUse } from '@/shared/enums';
import { VisitResponse } from '@/shared/types';
import { LabResultForm } from './LabResultForm';
import { LabCompletionWorkflow } from './LabCompletionWorkflow';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';

interface LabRequestDetailsModalProps {
  request: LabRequest | null;
  technicianId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type DetailTab = 'details' | 'results' | 'completion';

export function LabRequestDetailsModal({
  request,
  technicianId,
  isOpen,
  onClose,
  onSuccess,
}: LabRequestDetailsModalProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>('details');
  const [results, setResults] = useState<LabResult[]>([]);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [resultsUpdatedAt, setResultsUpdatedAt] = useState<Date | null>(null);
  const [visitDetails, setVisitDetails] = useState<VisitResponse | null>(null);
  const [visitLoading, setVisitLoading] = useState(false);
  const [visitError, setVisitError] = useState<string | null>(null);

  useEffect(() => {
    if (request?.status === 'PENDING') {
      setActiveTab('results');
    } else {
      setActiveTab('details');
    }
  }, [request]);

  const loadResults = async (activeRequest: LabRequest) => {
    try {
      setResultsLoading(true);
      setResultsError(null);
      const data = await labService.getResults(activeRequest.id, {
        purpose_of_use: PurposeOfUse.TREATMENT,
        justification: 'Lab result review',
      });
      setResults(data);
      setResultsUpdatedAt(new Date());
    } catch (error: any) {
      console.error('Failed to load lab results:', error);
      setResultsError(
        error.response?.data?.detail || 'Failed to load lab results'
      );
    } finally {
      setResultsLoading(false);
    }
  };

  const loadVisit = async (activeRequest: LabRequest) => {
    try {
      setVisitLoading(true);
      setVisitError(null);
      const data = await visitService.getVisit(activeRequest.visit_id, {
        purpose_of_use: PurposeOfUse.TREATMENT,
        justification: 'Lab request review',
      });
      setVisitDetails(data);
    } catch (error: any) {
      console.error('Failed to load visit details:', error);
      setVisitError(
        error.response?.data?.detail || 'Failed to load visit details'
      );
    } finally {
      setVisitLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && request) {
      loadResults(request);
      loadVisit(request);
    }
  }, [isOpen, request]);

  if (!isOpen || !request) return null;

  const handleSuccess = () => {
    if (onSuccess) {
      onSuccess();
    }
    onClose();
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      PENDING: 'text-yellow-600 bg-yellow-100',
      COMPLETED: 'text-green-600 bg-green-100',
      CANCELLED: 'text-red-600 bg-red-100',
    };
    return colors[status] || 'text-gray-600 bg-gray-100';
  };

  const maskId = (value?: string | null) =>
    value ? `${value.substring(0, 6)}…${value.substring(value.length - 4)}` : '—';

  const patientName =
    visitDetails?.patient_name || request.patient_name || 'Unknown patient';
  const patientMrn = visitDetails?.patient_mrn || request.patient_mrn;
  const patientId = visitDetails?.patient_id || request.patient_id;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                Lab Request: {request.test_name}
              </h2>
              <div className="flex items-center space-x-4 mt-2">
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
                    request.status
                  )}`}
                >
                  {request.status}
                </span>
                <span className="text-sm text-gray-500">
                  Request ID: {maskId(request.id)}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-gray-600">
                <span className="font-medium text-gray-900">{patientName}</span>
                <span className="text-gray-400">•</span>
                <span>
                  {patientMrn ? `MRN ${patientMrn}` : `ID: ${maskId(patientId)}`}
                </span>
                {visitDetails?.intake_emergency_flag && (
                  <>
                    <span className="text-gray-400">•</span>
                    <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                      Emergency
                    </span>
                  </>
                )}
                {visitLoading && (
                  <>
                    <span className="text-gray-400">•</span>
                    <span>Loading visit…</span>
                  </>
                )}
              </div>
              {visitError && (
                <p className="mt-2 text-xs text-red-600">{visitError}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ✕
            </button>
          </div>

          <div className="border-b border-gray-200 mb-6">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('details')}
                className={`
                  py-2 px-1 border-b-2 font-medium text-sm
                  ${
                    activeTab === 'details'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                Details
              </button>
              {request.status === 'PENDING' && (
                <>
                  <button
                    onClick={() => setActiveTab('results')}
                    className={`
                      py-2 px-1 border-b-2 font-medium text-sm
                      ${
                        activeTab === 'results'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }
                    `}
                  >
                    Record Results
                  </button>
                  <button
                    onClick={() => setActiveTab('completion')}
                    className={`
                      py-2 px-1 border-b-2 font-medium text-sm
                      ${
                        activeTab === 'completion'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }
                    `}
                  >
                    Complete
                  </button>
                </>
              )}
            </nav>
          </div>

          {activeTab === 'details' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card title="Patient & Visit" titleClassName="text-[#0B4DA2]">
                  <dl className="space-y-3">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">
                        Patient
                      </dt>
                      <dd className="text-sm text-gray-900">{patientName}</dd>
                      <dd className="text-xs text-gray-500">
                        {patientMrn ? `MRN ${patientMrn}` : `ID: ${maskId(patientId)}`}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">
                        Visit ID
                      </dt>
                      <dd className="text-sm text-gray-900">
                        {maskId(request.visit_id)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">
                        Completed At
                      </dt>
                      <dd className="text-sm text-gray-900">
                        {request.completed_at
                          ? new Date(request.completed_at).toLocaleString()
                          : 'Not completed'}
                      </dd>
                    </div>
                    {visitDetails?.intake_emergency_flag && (
                      <div>
                        <dt className="text-sm font-medium text-gray-500">
                          Emergency Note
                        </dt>
                        <dd className="text-sm text-red-700">
                          {visitDetails.intake_emergency_reason || 'Flagged'}
                        </dd>
                      </div>
                    )}
                  </dl>
                </Card>

                <Card title="Request Summary" titleClassName="text-[#0B4DA2]">
                  <dl className="space-y-3">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">
                        Test Name
                      </dt>
                      <dd className="text-sm text-gray-900">
                        {request.test_name}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">
                        Status
                      </dt>
                      <dd>
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                            request.status
                          )}`}
                        >
                          {request.status}
                        </span>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">
                        Requested By
                      </dt>
                      <dd className="text-sm text-gray-900">
                        {request.requested_by_name
                          ? request.requested_by_name
                          : maskId(request.requested_by)}
                      </dd>
                      {request.requested_by_role && (
                        <dd className="text-xs text-gray-500">
                          {request.requested_by_role}
                        </dd>
                      )}
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">
                        Created
                      </dt>
                      <dd className="text-sm text-gray-900">
                        {new Date(request.created_at).toLocaleString()}
                      </dd>
                    </div>
                  </dl>
                </Card>
              </div>

              <Card title="Clinical Instructions" titleClassName="text-[#0B4DA2]">
                <div className="text-sm text-gray-700">
                  {request.special_instructions
                    ? request.special_instructions
                    : 'No special instructions provided.'}
                </div>
              </Card>

              <Card title="Result History" titleClassName="text-[#0B4DA2]">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm text-gray-500">
                    {resultsLoading
                      ? 'Refreshing...'
                      : resultsUpdatedAt
                      ? `Last updated ${resultsUpdatedAt.toLocaleTimeString()}`
                      : 'Latest results'}
                  </span>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => request && loadResults(request)}
                    disabled={resultsLoading}
                  >
                    {resultsLoading ? 'Loading...' : 'Refresh'}
                  </Button>
                </div>

                {resultsLoading && (
                  <div className="text-sm text-gray-500">Loading results...</div>
                )}
                {resultsError && (
                  <div className="text-sm text-red-600">{resultsError}</div>
                )}
                {!resultsLoading && !resultsError && results.length === 0 && (
                  <div className="text-sm text-gray-500">
                    No results recorded yet.
                  </div>
                )}
                {!resultsLoading && !resultsError && results.length > 0 && (
                  <div className="space-y-3">
                    {results.map((result) => (
                      <div
                        key={result.id}
                        className="border rounded-md p-3 text-sm"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-gray-900">
                            {result.result_value} {result.result_unit}
                          </span>
                          <span className="text-gray-500">
                            {new Date(result.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="text-gray-600 mt-1">
                          Reference range: {result.reference_range}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Technician: {result.technician_id.substring(0, 12)}...
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              <div className="flex justify-end space-x-3">
                {request.status === 'PENDING' && (
                  <Button
                    variant="primary"
                    onClick={() => setActiveTab('results')}
                  >
                    Record Results
                  </Button>
                )}
                <Button variant="secondary" onClick={onClose}>
                  Close
                </Button>
              </div>
            </div>
          )}

          {activeTab === 'results' && request.status === 'PENDING' && (
            <LabResultForm
              requestId={request.id}
              technicianId={technicianId}
              testName={request.test_name}
              onSuccess={() => {
                loadResults(request);
                setActiveTab('completion');
                if (onSuccess) onSuccess();
              }}
              onCancel={() => setActiveTab('details')}
            />
          )}

          {activeTab === 'completion' && request.status === 'PENDING' && (
            <LabCompletionWorkflow
              requestId={request.id}
              visitId={request.visit_id}
              testName={request.test_name}
              onSuccess={handleSuccess}
              onCancel={() => setActiveTab('results')}
            />
          )}
        </div>
      </div>
    </div>
  );
}
