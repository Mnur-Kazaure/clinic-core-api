'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  labService,
  LabRequest,
  LabRequestWorkflowState,
  LabResult,
} from '@/domains/lab/services/labService';
import { visitService } from '@/domains/visit/services/visitService';
import { PurposeOfUse } from '@/shared/enums';
import { VisitResponse } from '@/shared/types';
import { LabResultForm } from './LabResultForm';
import { LabCompletionWorkflow } from './LabCompletionWorkflow';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { useDashboardUser } from '@/app/components/DashboardUserContext';

interface LabRequestDetailsModalProps {
  request: LabRequest | null;
  technicianId: string;
  selectedUnitId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type DetailTab = 'details' | 'results' | 'completion';

export function LabRequestDetailsModal({
  request,
  technicianId,
  selectedUnitId,
  isOpen,
  onClose,
  onSuccess,
}: LabRequestDetailsModalProps) {
  const dashboardUser = useDashboardUser();
  const [activeTab, setActiveTab] = useState<DetailTab>('details');
  const [results, setResults] = useState<LabResult[]>([]);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [resultsUpdatedAt, setResultsUpdatedAt] = useState<Date | null>(null);
  const [visitDetails, setVisitDetails] = useState<VisitResponse | null>(null);
  const [visitLoading, setVisitLoading] = useState(false);
  const [visitError, setVisitError] = useState<string | null>(null);
  const [workflowState, setWorkflowState] = useState<LabRequestWorkflowState | null>(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const getErrorDetail = (error: unknown): string | null => {
    if (typeof error !== 'object' || error === null || !('response' in error)) {
      return null;
    }
    return (error as { response?: { data?: { detail?: string } } }).response
      ?.data?.detail || null;
  };

  useEffect(() => {
    if (request?.status === 'PENDING' && !request.latest_result_status) {
      setActiveTab('results');
    } else {
      setActiveTab('details');
    }
  }, [request]);

  const loadResults = useCallback(async (activeRequest: LabRequest) => {
    try {
      setResultsLoading(true);
      setResultsError(null);
      const data = await labService.getResults(activeRequest.id, {
        purpose_of_use: PurposeOfUse.TREATMENT,
        justification: 'Lab result review',
        unit_id: selectedUnitId,
      });
      setResults(data);
      setResultsUpdatedAt(new Date());
    } catch (error: unknown) {
      console.error('Failed to load lab results:', error);
      setResultsError(getErrorDetail(error) || 'Failed to load lab results');
    } finally {
      setResultsLoading(false);
    }
  }, [selectedUnitId]);

  const loadVisit = useCallback(async (activeRequest: LabRequest) => {
    try {
      setVisitLoading(true);
      setVisitError(null);
      const data = await visitService.getVisit(activeRequest.visit_id, {
        purpose_of_use: PurposeOfUse.TREATMENT,
        justification: 'Lab request review',
      });
      setVisitDetails(data);
    } catch (error: unknown) {
      console.error('Failed to load visit details:', error);
      setVisitError(getErrorDetail(error) || 'Failed to load visit details');
    } finally {
      setVisitLoading(false);
    }
  }, []);

  const loadWorkflowState = useCallback(async (activeRequest: LabRequest) => {
    try {
      setWorkflowLoading(true);
      setWorkflowError(null);
      const data = await labService.getWorkflowState(activeRequest.id, selectedUnitId);
      setWorkflowState(data);
    } catch (error: unknown) {
      console.error('Failed to load lab workflow state:', error);
      setWorkflowError(getErrorDetail(error) || 'Failed to load workflow state');
    } finally {
      setWorkflowLoading(false);
    }
  }, [selectedUnitId]);

  useEffect(() => {
    if (isOpen && request) {
      loadResults(request);
      loadVisit(request);
      loadWorkflowState(request);
    }
  }, [isOpen, loadResults, loadVisit, loadWorkflowState, request]);

  if (!isOpen || !request) return null;

  const handleSuccess = () => {
    if (onSuccess) {
      onSuccess();
    }
    onClose();
  };

  const currentRole = dashboardUser?.role || null;
  const activeResultId = request.active_result_id || null;
  const latestResult = results.length > 0 ? results[results.length - 1] : null;
  const currentResult = results.find((row) => row.id === activeResultId) || latestResult;
  const canVerify =
    currentRole === 'LAB_SCIENTIST' || currentRole === 'LAB_SUPERVISOR';
  const canRelease = currentRole === 'LAB_SUPERVISOR';
  const canComplete = workflowState?.can_complete ?? request.latest_result_status === 'RELEASED';

  const reloadRequestContext = async () => {
    if (!request) return;
    await Promise.all([
      loadResults(request),
      loadWorkflowState(request),
    ]);
    if (onSuccess) {
      onSuccess();
    }
  };

  const copyValue = async (key: string, value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedKey(key);
      window.setTimeout(() => setCopiedKey((current) => (current === key ? null : current)), 1500);
    } catch (error) {
      console.error('Unable to copy value:', error);
    }
  };

  const handleVerifyResult = async () => {
    if (!currentResult) return;
    try {
      setActionLoading(true);
      setActionError(null);
      await labService.verifyResult(currentResult.id, selectedUnitId);
      await reloadRequestContext();
    } catch (error: unknown) {
      setActionError(getErrorDetail(error) || 'Unable to verify this result.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReleaseResult = async () => {
    if (!currentResult) return;
    try {
      setActionLoading(true);
      setActionError(null);
      await labService.releaseResult(currentResult.id, undefined, selectedUnitId);
      await reloadRequestContext();
    } catch (error: unknown) {
      const detail = getErrorDetail(error) || 'Unable to release this result.';
      if (
        canRelease &&
        detail.includes('QC failure blocks release')
      ) {
        const overrideReason = window.prompt(
          'QC override reason is required to release this result.'
        );
        if (overrideReason && overrideReason.trim().length >= 4) {
          try {
            await labService.releaseResult(
              currentResult.id,
              { qc_override_reason: overrideReason.trim() },
              selectedUnitId
            );
            await reloadRequestContext();
            return;
          } catch (overrideError: unknown) {
            setActionError(
              getErrorDetail(overrideError) || 'Unable to release this result with QC override.'
            );
            return;
          } finally {
            setActionLoading(false);
          }
        }
      }
      setActionError(detail);
    } finally {
      setActionLoading(false);
    }
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

  const chipToneClass = (tone: string) => {
    const tones: Record<string, string> = {
      success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
      warning: 'border-amber-200 bg-amber-50 text-amber-800',
      info: 'border-sky-200 bg-sky-50 text-sky-800',
      critical: 'border-rose-200 bg-rose-50 text-rose-800',
    };
    return tones[tone] || 'border-slate-200 bg-slate-50 text-slate-700';
  };

  const workflowChips = workflowState?.status_chips ?? [];
  const selectedUnitLabel = workflowState?.unit_name || request.target_unit_name || null;
  const copyButtonLabel = (key: string) => copiedKey === key ? 'Copied' : 'Copy';
  const requestIdLabel = maskId(request.id);
  const visitIdLabel = maskId(request.visit_id);

  const patientName =
    visitDetails?.patient_name || request.patient_name || 'Unknown patient';
  const patientMrn = visitDetails?.patient_mrn || request.patient_mrn;
  const patientId = visitDetails?.patient_id || request.patient_id;

  return (
    <div
      data-testid="lab-request-modal"
      className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2
                data-testid="lab-request-modal-title"
                className="text-2xl font-bold text-gray-900"
              >
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
              {(workflowChips.length > 0 || selectedUnitLabel) && (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {selectedUnitLabel && (
                    <span
                      data-testid="lab-selected-unit-chip"
                      className="inline-flex items-center rounded-full border border-[#0B4DA2]/15 bg-[#0B4DA2]/5 px-3 py-1 text-xs font-semibold text-[#0B4DA2]"
                    >
                      {selectedUnitLabel} bench
                    </span>
                  )}
                  {workflowChips.map((chip) => (
                    <span
                      key={chip.key}
                      data-testid={`lab-workflow-chip-${chip.key}`}
                      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${chipToneClass(chip.tone)}`}
                    >
                      {chip.label}: {chip.value}
                    </span>
                  ))}
                </div>
              )}
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
              {workflowError && (
                <p className="mt-2 text-xs text-red-600">{workflowError}</p>
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
                Request Details
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
                    Result Entry
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
                    Completion
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
                      <dd className="flex items-center gap-2 text-sm text-gray-900">
                        <span>{visitIdLabel}</span>
                        <button
                          type="button"
                          onClick={() => void copyValue('visit-id', request.visit_id)}
                          className="text-xs font-medium text-[#0B4DA2] hover:text-[#08386F]"
                        >
                          {copyButtonLabel('visit-id')}
                        </button>
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
                          <div>
                            <span className="font-medium text-gray-900">
                              {result.result_value}
                              {result.result_unit ? ` ${result.result_unit}` : ''}
                            </span>
                            {result.status && (
                              <div className="mt-1">
                                <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                                  {result.status.replaceAll('_', ' ')}
                                </span>
                              </div>
                            )}
                          </div>
                          <span className="text-gray-500">
                            {new Date(result.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="text-gray-600 mt-1">
                          Reference range: {result.reference_range || 'N/A'}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Technician: {result.technician_id.substring(0, 12)}...
                        </div>
                        {result.amendment_reason && (
                          <div className="mt-2 text-xs text-amber-700">
                            Amendment reason: {result.amendment_reason}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {actionError && (
                  <div className="mt-3 text-sm text-red-600">{actionError}</div>
                )}
                {request.status === 'PENDING' && currentResult && (
                  <div className="mt-4 flex flex-wrap gap-3">
                    {canVerify &&
                      ['DRAFT', 'SUBMITTED'].includes(currentResult.status || '') && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={handleVerifyResult}
                          disabled={actionLoading}
                        >
                          {actionLoading ? 'Working…' : 'Verify Result'}
                        </Button>
                      )}
                    {canRelease &&
                      ['SUBMITTED', 'VERIFIED'].includes(currentResult.status || '') && (
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={handleReleaseResult}
                          disabled={actionLoading}
                        >
                          {actionLoading ? 'Working…' : 'Release Result'}
                        </Button>
                      )}
                  </div>
                )}
              </Card>

              <div className="flex justify-end space-x-3">
                {request.status === 'PENDING' && (
                  <Button
                    variant="primary"
                    onClick={() => setActiveTab('results')}
                  >
                    Result Entry
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
              selectedUnitId={selectedUnitId}
              testName={request.test_name}
              workflowState={workflowState}
              onWorkflowRefresh={() => request && loadWorkflowState(request)}
              onSuccess={() => {
                void Promise.all([
                  loadResults(request),
                  loadWorkflowState(request),
                ]);
                setActiveTab('details');
                if (onSuccess) onSuccess();
              }}
              onCancel={() => setActiveTab('details')}
            />
          )}

          {activeTab === 'completion' && request.status === 'PENDING' && (
            <LabCompletionWorkflow
              requestId={request.id}
              visitId={request.visit_id}
              selectedUnitId={selectedUnitId}
              testName={request.test_name}
              workflowState={workflowState}
              requestIdLabel={requestIdLabel}
              visitIdLabel={visitIdLabel}
              onCopyValue={copyValue}
              workflowLoading={workflowLoading}
              onSuccess={handleSuccess}
              onCancel={() => setActiveTab('results')}
            />
          )}
        </div>
      </div>
    </div>
  );
}
