'use client';

import { useState } from 'react';
import { visitService } from '@/domains/visit/services/visitService';
import { Button } from '@/shared/Button';

interface QuickActionButtonsProps {
  visitId: string;
  currentStatus: string;
  allowedTransitions: string[];
  hiddenTransitions?: string[];
  onStatusChange?: (newStatus: string) => void;
  onReassign?: () => void;
}

export function QuickActionButtons({
  visitId,
  currentStatus,
  allowedTransitions,
  hiddenTransitions = [],
  onStatusChange,
  onReassign,
}: QuickActionButtonsProps) {
  const [isTransitioning, setIsTransitioning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const transitionsToShow = allowedTransitions.filter(
    (status) => !hiddenTransitions.includes(status)
  );

  const handleTransition = async (toStatus: string) => {
    try {
      setIsTransitioning(toStatus);
      setError(null);

      await visitService.transitionVisit(visitId, toStatus);

      if (onStatusChange) {
        onStatusChange(toStatus);
      }
    } catch (err: any) {
      console.error('Transition failed:', err);
      setError(err.response?.data?.detail || 'Failed to update status');
    } finally {
      setIsTransitioning(null);
    }
  };

  const getStatusActionLabel = (status: string) => {
    const labels: Record<string, string> = {
      TRIAGED: 'Mark as Triaged',
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
    return null;
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
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
            Reassign Doctor
          </Button>
        )}
      </div>

      <div className="text-xs text-gray-500">
        <p>
          ✅ Actions shown are authorized by backend based on your role and visit
          status
        </p>
        {transitionsToShow.length === 0 && (
          <p>No further actions available for this visit status</p>
        )}
      </div>
    </div>
  );
}
