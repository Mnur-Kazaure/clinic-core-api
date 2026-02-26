'use client';

import { useState } from 'react';
import {
  TriageAssessmentResponse,
  TriageDraftResponse,
  TriageFinalizeResponse,
  visitService,
} from '@/domains/visit/services/visitService';
import { Button } from '@/shared/Button';
import { PurposeOfUse, VisitStatus } from '@/shared/enums';
import type { VisitResponse } from '@/shared/types';
import { TriageAssessmentModal } from './TriageAssessmentModal';

interface QuickActionButtonsProps {
  visitId: string;
  currentStatus: string;
  visitVersion: number;
  allowedTransitions: string[];
  currentUserRole?: string | null;
  hiddenTransitions?: string[];
  onStatusChange?: (newStatus: string) => void;
  onVisitUpdated?: (visit: VisitResponse) => void;
  onReassign?: () => void;
}

type OutstandingWork = {
  pending_labs_count: number;
  unfulfilled_prescriptions_count: number;
};

type ApiErrorObject = Record<string, unknown> & {
  code?: string;
};

const OVERRIDE_REASON_LABELS: Record<string, string> = {
  PATIENT_LEFT: 'Patient left',
  REFERRED_OUT: 'Referred out',
  NO_LAB_REAGENTS: 'No lab reagents',
  DRUG_OUT_OF_STOCK_EXTERNAL_PURCHASE: 'Drug out of stock (external purchase)',
  EQUIPMENT_DOWN: 'Equipment down',
  AFTER_HOURS: 'After hours',
  PAYMENT_ISSUE: 'Payment issue',
  SYSTEM_OUTAGE: 'System outage',
  DOCUMENTATION_PENDING: 'Documentation pending',
  OTHER: 'Other (write note)',
};

export function QuickActionButtons({
  visitId,
  currentStatus,
  visitVersion,
  allowedTransitions,
  currentUserRole,
  hiddenTransitions = [],
  onStatusChange,
  onVisitUpdated,
  onReassign,
}: QuickActionButtonsProps) {
  const [isTransitioning, setIsTransitioning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showTriageModal, setShowTriageModal] = useState(false);
  const [activeTriageAssessment, setActiveTriageAssessment] =
    useState<TriageAssessmentResponse | null>(null);
  const [loadingTriage, setLoadingTriage] = useState(false);
  const [showCompleteConfirm, setShowCompleteConfirm] = useState(false);
  const [outstandingWork, setOutstandingWork] = useState<OutstandingWork | null>(null);
  const [overrideReasonCodes, setOverrideReasonCodes] = useState<string[]>([]);
  const [selectedOverrideReason, setSelectedOverrideReason] = useState<string>('PATIENT_LEFT');
  const [overrideReasonText, setOverrideReasonText] = useState<string>('');

  const transitionsToShow = allowedTransitions.filter(
    (status) => !hiddenTransitions.includes(status) && status !== VisitStatus.TRIAGED
  );
  const canUseTriageAction =
    ['CHEW', 'MIDWIFE', 'DOCTOR'].includes(currentUserRole || '') &&
    currentStatus === VisitStatus.REGISTERED;

  const parseApiDetail = (err: unknown): unknown => {
    if (!err || typeof err !== 'object' || !('response' in err)) {
      return null;
    }
    return (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  };

  const asApiErrorObject = (value: unknown): ApiErrorObject | null =>
    value && typeof value === 'object' ? (value as ApiErrorObject) : null;

  const handleOpenTriage = async () => {
    try {
      setLoadingTriage(true);
      setError(null);
      const existing = await visitService.getActiveTriage(visitId);
      setActiveTriageAssessment(existing);
      setShowTriageModal(true);
    } catch (err: unknown) {
      const detail = parseApiDetail(err);
      setError(
        typeof detail === 'string'
          ? detail
          : 'Unable to load triage context. Please refresh and retry.'
      );
    } finally {
      setLoadingTriage(false);
    }
  };

  const handleTriageDraftSaved = (response: TriageDraftResponse) => {
    setActiveTriageAssessment(response.triage_assessment);
  };

  const handleTriageSigned = async (response: TriageFinalizeResponse) => {
    setShowTriageModal(false);
    setActiveTriageAssessment(response.triage_assessment);
    try {
      const refreshed = await visitService.getVisit(visitId, {
        purpose_of_use:
          currentUserRole === 'DOCTOR'
            ? PurposeOfUse.TREATMENT
            : PurposeOfUse.OPERATIONS,
        justification: 'Refresh visit after triage assessment',
      });
      onVisitUpdated?.(refreshed);
      onStatusChange?.(refreshed.status);
    } catch {
      onStatusChange?.(response.visit_status);
    }
  };

  const handleTransition = async (toStatus: string) => {
    try {
      setIsTransitioning(toStatus);
      setError(null);

      const updated = await visitService.transitionVisit(visitId, {
        to_status: toStatus as VisitStatus,
        expected_version: visitVersion,
        mode: 'normal',
      });

      onVisitUpdated?.(updated);
      onStatusChange?.(updated.status);
    } catch (err: unknown) {
      console.error('Transition failed:', err);
      const detail = parseApiDetail(err);
      const detailObj = asApiErrorObject(detail);

      if (detailObj?.code === 'VERSION_CONFLICT') {
        setError('This visit was updated by someone else. Please refresh and try again.');
        return;
      }

      // Special-case: completion pre-check flow (outstanding work).
      if (toStatus === VisitStatus.COMPLETED && detailObj) {
        const code = detailObj.code;
        if (code === 'VISIT_HAS_OUTSTANDING_WORK') {
          const allowedOverride = Boolean(detailObj.allowed_override);
          if (!allowedOverride) {
            setError('Cannot complete visit: outstanding work must be resolved first.');
            return;
          }
          const outstanding = asApiErrorObject(detailObj.outstanding) || {};
          setOutstandingWork({
            pending_labs_count: Number(outstanding.pending_labs_count || 0),
            unfulfilled_prescriptions_count: Number(
              outstanding.unfulfilled_prescriptions_count || 0
            ),
          });
          const codes = Array.isArray(detailObj.override_reason_codes)
            ? (detailObj.override_reason_codes as string[])
            : [];
          setOverrideReasonCodes(codes);
          setSelectedOverrideReason(codes[0] || 'PATIENT_LEFT');
          setOverrideReasonText('');
          setShowCompleteConfirm(true);
          return;
        }
        if (code === 'VERSION_CONFLICT') {
          setError('This visit was updated by someone else. Please refresh and try again.');
          return;
        }
      }

      setError(
        typeof detail === 'string'
          ? detail
          : 'Failed to update status. Please refresh and try again.'
      );
    } finally {
      setIsTransitioning(null);
    }
  };

  const submitOverrideCompletion = async () => {
    if (!outstandingWork) return;
    if (!selectedOverrideReason) {
      setError('Select a reason to complete with outstanding work.');
      return;
    }
    if (selectedOverrideReason === 'OTHER' && overrideReasonText.trim().length < 10) {
      setError('Please provide at least 10 characters for OTHER.');
      return;
    }

    try {
      setIsTransitioning(VisitStatus.COMPLETED);
      setError(null);

      const updated = await visitService.transitionVisit(visitId, {
        to_status: VisitStatus.COMPLETED,
        expected_version: visitVersion,
        mode: 'override',
        override_reason_code: selectedOverrideReason,
        override_reason_text: selectedOverrideReason === 'OTHER' ? overrideReasonText.trim() : undefined,
      });

      setShowCompleteConfirm(false);
      setOutstandingWork(null);
      onVisitUpdated?.(updated);
      onStatusChange?.(updated.status);
    } catch (err: unknown) {
      console.error('Override completion failed:', err);
      const detail = parseApiDetail(err);
      const detailObj = asApiErrorObject(detail);
      if (detailObj?.code === 'VERSION_CONFLICT') {
        setError('This visit was updated by someone else. Please refresh and try again.');
        return;
      }
      setError(typeof detail === 'string' ? detail : 'Unable to complete visit. Please try again.');
    } finally {
      setIsTransitioning(null);
    }
  };

  const getStatusActionLabel = (status: string) => {
    const labels: Record<string, string> = {
      IN_CONSULTATION: 'Start Consultation',
      LAB_REQUESTED: 'Request Lab',
      LAB_COMPLETED: 'Complete Lab',
      PHARMACY_PENDING: 'Send to Pharmacy',
      COMPLETED: 'Complete Visit',
      CANCELLED: 'Cancel Visit',
    };
    return labels[status] || `Set to ${status}`;
  };

  const getButtonVariant = (status: string) => {
    if (status === 'CANCELLED') return 'danger';
    if (status === 'COMPLETED') return 'primary';
    return 'secondary';
  };

  if (transitionsToShow.length === 0 && !onReassign) {
    if (!canUseTriageAction) {
      return null;
    }
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {canUseTriageAction && (
          <Button
            variant="primary"
            size="sm"
            onClick={handleOpenTriage}
            disabled={isTransitioning !== null || loadingTriage}
            isLoading={loadingTriage}
          >
            {activeTriageAssessment ? 'Resume Triage' : 'Open Triage'}
          </Button>
        )}

        {transitionsToShow.map((status) => (
          <Button
            key={status}
            variant={getButtonVariant(status)}
            size="sm"
            onClick={() => handleTransition(status)}
            disabled={isTransitioning !== null}
            isLoading={isTransitioning === status}
          >
            {getStatusActionLabel(status)}
          </Button>
        ))}

        {onReassign && currentStatus === 'REGISTERED' && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onReassign}
            disabled={isTransitioning !== null}
          >
            Reassign Owner
          </Button>
        )}
      </div>

      <div className="text-xs text-gray-500">
        <p>
          ✅ Actions shown are authorized by backend based on your role and visit
          status
        </p>
        {canUseTriageAction && (
          <p>
            Triage must be saved through the triage workflow before consultation starts.
          </p>
        )}
        {transitionsToShow.length === 0 && (
          <p>No further actions available for this visit status</p>
        )}
      </div>

      <TriageAssessmentModal
        isOpen={showTriageModal}
        visitId={visitId}
        visitVersion={visitVersion}
        currentUserRole={currentUserRole}
        existingAssessment={activeTriageAssessment}
        onClose={() => setShowTriageModal(false)}
        onDraftSaved={handleTriageDraftSaved}
        onSigned={handleTriageSigned}
      />

      {showCompleteConfirm && outstandingWork && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
            <div className="flex items-start justify-between border-b px-5 py-4">
              <div>
                <div className="text-lg font-semibold text-slate-900">
                  Complete visit with outstanding items?
                </div>
                <div className="mt-1 text-sm text-slate-600">
                  This will mark the visit as <span className="font-medium">COMPLETED</span> without cancelling pending work.
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowCompleteConfirm(false)}
                className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 px-5 py-4">
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <div>Pending labs: <span className="font-semibold">{outstandingWork.pending_labs_count}</span></div>
                <div>Pending prescriptions: <span className="font-semibold">{outstandingWork.unfulfilled_prescriptions_count}</span></div>
              </div>

              <div>
                <div className="text-sm font-medium text-slate-700">Reason (required)</div>
                <div className="mt-2 space-y-2">
                  {(overrideReasonCodes.length ? overrideReasonCodes : Object.keys(OVERRIDE_REASON_LABELS)).map(
                    (code) => (
                      <label
                        key={code}
                        className="flex cursor-pointer items-start gap-2 rounded-md border border-slate-200 px-3 py-2 hover:bg-slate-50"
                      >
                        <input
                          type="radio"
                          name="overrideReason"
                          value={code}
                          checked={selectedOverrideReason === code}
                          onChange={(e) => setSelectedOverrideReason(e.target.value)}
                          className="mt-1"
                        />
                        <div className="text-sm text-slate-700">
                          {OVERRIDE_REASON_LABELS[code] || code}
                        </div>
                      </label>
                    )
                  )}
                </div>

                {selectedOverrideReason === 'OTHER' && (
                  <div className="mt-3">
                    <textarea
                      value={overrideReasonText}
                      onChange={(e) => setOverrideReasonText(e.target.value)}
                      rows={3}
                      className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
                      placeholder="Describe why you're completing the visit with pending items (min 10 chars)."
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t px-5 py-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowCompleteConfirm(false)}
                disabled={isTransitioning !== null}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={submitOverrideCompletion}
                disabled={isTransitioning !== null}
                isLoading={isTransitioning === VisitStatus.COMPLETED}
              >
                Complete Visit
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
