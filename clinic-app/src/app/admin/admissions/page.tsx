'use client';

import { useCallback, useEffect, useState } from 'react';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { Badge } from '@/shared/Badge';
import { Input } from '@/shared/Input';
import { bedService, Bed, Ward } from '@/domains/bed/services/bedService';
import {
  admissionRequestService,
  AdmissionRequest,
  AdmissionRequestStatus,
} from '@/domains/admission/services/admissionRequestService';

const statusLabels: Record<AdmissionRequestStatus, string> = {
  PENDING: 'Pending',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  CANCELLED: 'Cancelled',
};

const statusVariant: Record<AdmissionRequestStatus, 'warning' | 'success' | 'error' | 'ghost'> = {
  PENDING: 'warning',
  APPROVED: 'success',
  REJECTED: 'error',
  CANCELLED: 'ghost',
};

const maskId = (value: string) => `${value.slice(0, 8)}...`;
type BedActionMode = 'assign' | 'transfer';

export default function AdmissionRequestsPage() {
  const [requests, setRequests] = useState<AdmissionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<AdmissionRequestStatus>('PENDING');
  const [bedActionRequest, setBedActionRequest] = useState<AdmissionRequest | null>(null);
  const [bedActionMode, setBedActionMode] = useState<BedActionMode>('assign');
  const [bedActionModalOpen, setBedActionModalOpen] = useState(false);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [wards, setWards] = useState<Ward[]>([]);
  const [bedsLoading, setBedsLoading] = useState(false);
  const [bedActionError, setBedActionError] = useState<string | null>(null);
  const [bedActionReason, setBedActionReason] = useState('');
  const [selectedWard, setSelectedWard] = useState<string>('all');
  const [selectedBedId, setSelectedBedId] = useState('');
  const [bedActionSubmitting, setBedActionSubmitting] = useState(false);
  const [bedActionSuccess, setBedActionSuccess] = useState<string | null>(null);
  const listActionLocked = actionLoading !== null || bedActionSubmitting;

  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await admissionRequestService.listRequests(filter);
      setRequests(data);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setError(detail || 'Unable to load admission requests.');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  useEffect(() => {
    if (!bedActionSuccess) return;
    const timeout = window.setTimeout(() => setBedActionSuccess(null), 8000);
    return () => window.clearTimeout(timeout);
  }, [bedActionSuccess]);

  const loadBedsAndWards = useCallback(async (wardId?: string) => {
    try {
      setBedsLoading(true);
      setBedActionError(null);
      const [wardList, bedList] = await Promise.all([
        bedService.listWards(),
        bedService.listBeds({ availableOnly: true, wardId: wardId || undefined }),
      ]);
      setWards(wardList);
      setBeds(bedList);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setBedActionError(detail || 'Unable to load available beds.');
    } finally {
      setBedsLoading(false);
    }
  }, []);

  const openBedActionModal = async (
    request: AdmissionRequest,
    mode: BedActionMode
  ) => {
    setBedActionSuccess(null);
    setBedActionRequest(request);
    setBedActionMode(mode);
    setBedActionModalOpen(true);
    setBedActionReason('');
    setSelectedWard('all');
    setSelectedBedId('');
    await loadBedsAndWards();
  };

  const closeBedActionModal = () => {
    if (bedActionSubmitting) return;
    setBedActionModalOpen(false);
    setBedActionRequest(null);
    setBedActionError(null);
  };

  const handleSubmitBedAction = async () => {
    if (!bedActionRequest?.admission_id) {
      setBedActionError('Admission is not active yet. Approve the request first.');
      return;
    }
    if (!selectedBedId) {
      setBedActionError('Select an available bed to continue.');
      return;
    }
    if (bedActionMode === 'transfer' && bedActionReason.trim().length < 3) {
      setBedActionError('Transfer reason must be at least 3 characters.');
      return;
    }
    try {
      setBedActionSubmitting(true);
      setBedActionError(null);
      if (bedActionMode === 'assign') {
        await bedService.assignBed({
          admission_id: bedActionRequest.admission_id,
          bed_id: selectedBedId,
          reason: bedActionReason.trim() || undefined,
        });
      } else {
        await bedService.transferBed({
          admission_id: bedActionRequest.admission_id,
          to_bed_id: selectedBedId,
          reason: bedActionReason.trim(),
        });
      }
      await loadRequests();
      setBedActionSuccess(
        bedActionMode === 'assign'
          ? 'Bed assigned successfully.'
          : 'Bed transferred successfully.'
      );
      closeBedActionModal();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      const normalized = (detail || '').toLowerCase();

      if (normalized.includes('active bed assignment')) {
        setBedActionMode('transfer');
        setBedActionError(
          'This admission already has an active bed assignment. Use Transfer Bed.'
        );
        return;
      }
      if (normalized.includes('no active bed assignment')) {
        setBedActionMode('assign');
        setBedActionError(
          'No active bed assignment found. Use Assign Bed first.'
        );
        return;
      }
      if (normalized.includes('bed not available')) {
        await loadBedsAndWards(selectedWard === 'all' ? undefined : selectedWard);
        setBedActionError(
          'Selected bed is no longer available. Choose another bed.'
        );
        return;
      }

      setBedActionError(
        detail ||
          (bedActionMode === 'assign'
            ? 'Unable to assign bed.'
            : 'Unable to transfer bed.')
      );
    } finally {
      setBedActionSubmitting(false);
    }
  };

  const handleDecision = async (
    requestId: string,
    action: 'approve' | 'reject'
  ) => {
    const reason = prompt(
      action === 'approve'
        ? 'Approval reason (required):'
        : 'Rejection reason (required):'
    );
    if (!reason || reason.trim().length < 3) return;

    try {
      setActionLoading(requestId);
      if (action === 'approve') {
        await admissionRequestService.approveRequest(requestId, { reason });
      } else {
        await admissionRequestService.rejectRequest(requestId, { reason });
      }
      await loadRequests();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setError(detail || 'Action failed.');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
          Admission governance
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">
          Admission Requests
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Review doctor admission requests and approve or reject with audit
          reasons.
        </p>
      </section>

      <Card title="Requests Queue">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {(['PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'] as const).map(
              (status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  disabled={listActionLocked}
                  className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                    filter === status
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {statusLabels[status]}
                </button>
              )
            )}
          </div>

          {bedActionSuccess && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {bedActionSuccess}
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {loading ? (
            <div className="space-y-3">
              <div className="shimmer h-12 rounded"></div>
              <div className="shimmer h-12 rounded"></div>
            </div>
          ) : (
            <div className="space-y-3">
              {requests.length === 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                  No admission requests in this queue.
                </div>
              )}

              {requests.map((request) => (
                <div
                  key={request.id}
                  className="flex flex-col gap-3 rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-700 md:flex-row md:items-center md:justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-slate-900">
                        Patient {maskId(request.patient_id)}
                      </span>
                      <Badge variant={statusVariant[request.status]} size="sm">
                        {statusLabels[request.status]}
                      </Badge>
                      <Badge variant="outline" size="sm">
                        {request.admission_type}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-500">
                      Requested {new Date(request.requested_at).toLocaleString()}
                    </p>
                    <p className="text-xs text-slate-600">
                      Reason: {request.reason}
                    </p>
                  </div>

                  {request.status === 'PENDING' && (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleDecision(request.id, 'approve')}
                        isLoading={actionLoading === request.id}
                        disabled={listActionLocked}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDecision(request.id, 'reject')}
                        isLoading={actionLoading === request.id}
                        disabled={listActionLocked}
                      >
                        Reject
                      </Button>
                    </div>
                  )}

                  {request.status === 'APPROVED' && request.admission_id && (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => openBedActionModal(request, 'assign')}
                        disabled={listActionLocked}
                      >
                        Assign Bed
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openBedActionModal(request, 'transfer')}
                        disabled={listActionLocked}
                      >
                        Transfer Bed
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {bedActionModalOpen && bedActionRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-3xl rounded-2xl bg-white shadow-xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                  {bedActionMode === 'assign' ? 'Bed assignment' : 'Bed transfer'}
                </p>
                <h2 className="mt-1 text-xl font-semibold text-slate-900">
                  {bedActionMode === 'assign'
                    ? 'Assign bed for admission'
                    : 'Transfer bed for admission'}
                </h2>
                <p className="mt-1 text-sm text-slate-600">
                  Patient {maskId(bedActionRequest.patient_id)} • Admission{' '}
                  {bedActionRequest.admission_id
                    ? maskId(bedActionRequest.admission_id)
                    : 'Not created'}
                </p>
              </div>
              <button
                onClick={closeBedActionModal}
                disabled={bedActionSubmitting}
                className="text-2xl text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            </div>

              <div className="space-y-6 px-6 py-5">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                {bedActionMode === 'assign'
                  ? 'Use Assign Bed when the patient has no current bed.'
                  : 'Use Transfer Bed only when the patient already has an active bed assignment.'}
              </div>

              {bedActionError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {bedActionError}
                </div>
              )}

              <div className="flex flex-wrap items-center gap-3">
                <div className="min-w-[200px]">
                  <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Ward filter
                  </label>
                  <select
                    value={selectedWard}
                    disabled={bedsLoading || bedActionSubmitting}
                    onChange={async (event) => {
                      const next = event.target.value;
                      setSelectedWard(next);
                      setSelectedBedId('');
                      await loadBedsAndWards(next === 'all' ? undefined : next);
                    }}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
                  >
                    <option value="all">All wards</option>
                    {wards.map((ward) => (
                      <option key={ward.id} value={ward.id}>
                        {ward.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex-1">
                  <Input
                    label={
                      bedActionMode === 'assign'
                        ? 'Assignment note (optional)'
                        : 'Transfer reason *'
                    }
                    placeholder={
                      bedActionMode === 'assign'
                        ? 'Reason or placement note'
                        : 'Reason for transfer'
                    }
                    value={bedActionReason}
                    onChange={(event) => setBedActionReason(event.target.value)}
                  />
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-sm font-semibold text-slate-900">
                    Available beds
                  </p>
                  <span className="text-xs text-slate-500">
                    {bedsLoading ? 'Loading…' : `${beds.length} available`}
                  </span>
                </div>

                {bedsLoading ? (
                  <div className="space-y-3">
                    <div className="shimmer h-12 rounded-lg"></div>
                    <div className="shimmer h-12 rounded-lg"></div>
                  </div>
                ) : beds.length === 0 ? (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                    No available beds for the selected ward.
                  </div>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {beds.map((bed) => {
                      const ward = wards.find((item) => item.id === bed.ward_id);
                      const selected = selectedBedId === bed.id;
                      return (
                        <button
                          key={bed.id}
                          type="button"
                          disabled={bedActionSubmitting}
                          onClick={() => setSelectedBedId(bed.id)}
                          className={`flex items-center justify-between rounded-lg border px-4 py-3 text-left transition ${
                            selected
                              ? 'border-slate-900 bg-slate-900 text-white'
                              : 'border-slate-200 bg-white text-slate-700 hover:border-slate-400'
                          }`}
                        >
                          <div>
                            <p className="text-sm font-semibold">
                              Bed {bed.bed_label}
                            </p>
                            <p className={`text-xs ${selected ? 'text-white/80' : 'text-slate-500'}`}>
                              {ward?.name || 'Unassigned ward'}
                            </p>
                          </div>
                          <Badge variant={selected ? 'success' : 'outline'} size="sm">
                            Available
                          </Badge>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
              <p className="text-xs text-slate-500">
                {bedActionMode === 'assign'
                  ? 'Assignment will reserve the bed immediately.'
                  : 'Transfer will release current bed and reserve the new bed.'}
              </p>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={closeBedActionModal}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSubmitBedAction}
                  isLoading={bedActionSubmitting}
                  disabled={
                    bedActionSubmitting ||
                    !selectedBedId ||
                    (bedActionMode === 'transfer' && bedActionReason.trim().length < 3)
                  }
                >
                  {bedActionMode === 'assign' ? 'Assign Bed' : 'Transfer Bed'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
