'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { DashboardHero } from '@/app/components/DashboardHero';
import {
  getDashboardUserDisplayName,
  useDashboardUser,
} from '@/app/components/DashboardUserContext';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';
import { HOSPITAL_NAME } from '@/shared/constants/branding';
import {
  pharmacyCatalogGovernanceService,
  type PharmacyCatalogRegistryRow,
} from '@/domains/pharmacy/services/pharmacyCatalogGovernanceService';
import { pharmacyCmdService } from '@/domains/pharmacy/services/pharmacyCmdService';
import type { PharmacyRefillRequestResponse } from '@/domains/pharmacy/services/pharmacyService';

const ALL_FILTER = 'ALL';

function formatDateTime(value?: string | null) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleString();
}

function workflowLabel(value: string) {
  return value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function statusClass(status: string) {
  if (status === 'REJECTED') return 'border border-red-200 bg-red-50 text-red-700';
  if (status === 'AWAITING_CMD_APPROVAL') return 'border border-amber-200 bg-amber-50 text-amber-700';
  return 'border border-emerald-200 bg-emerald-50 text-emerald-700';
}

function priorityClass(value?: string | null) {
  if (value === 'EMERGENCY') return 'border border-red-200 bg-red-50 text-red-700';
  if (value === 'URGENT') return 'border border-amber-200 bg-amber-50 text-amber-700';
  return 'border border-slate-200 bg-slate-100 text-slate-700';
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <p className="mt-2 text-sm text-slate-600">{detail}</p>
    </div>
  );
}

function MetricTile({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-slate-900">{value}</p>
      {detail ? <p className="mt-2 text-sm text-slate-600">{detail}</p> : null}
    </div>
  );
}

export default function CmdPage() {
  const dashboardUser = useDashboardUser();
  const [requests, setRequests] = useState<PharmacyRefillRequestResponse[]>([]);
  const [catalogRequests, setCatalogRequests] = useState<PharmacyCatalogRegistryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>(ALL_FILTER);
  const [actingRequestId, setActingRequestId] = useState<string | null>(null);

  const loadRequests = useCallback(async (mode: 'initial' | 'refresh' = 'initial') => {
    try {
      if (mode === 'initial') {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);
      const [refillPayload, catalogPayload] = await Promise.all([
        pharmacyCmdService.getRefillRequests(),
        pharmacyCatalogGovernanceService.listCmdCatalogRequests(),
      ]);
      setRequests(refillPayload);
      setCatalogRequests(catalogPayload);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to load CMD approval requests.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadRequests('initial');
  }, [loadRequests]);

  useEffect(() => {
    if (!flashMessage) return;
    const timer = window.setTimeout(() => setFlashMessage(null), 4000);
    return () => window.clearTimeout(timer);
  }, [flashMessage]);

  const filteredRequests = useMemo(() => {
    const normalized = searchTerm.trim().toLowerCase();
    return requests.filter((request) => {
      const matchesStatus = statusFilter === ALL_FILTER || request.status === statusFilter;
      if (!matchesStatus) {
        return false;
      }
      if (!normalized) {
        return true;
      }
      return [
        request.requesting_unit_name,
        request.request_type,
        request.urgency,
        request.status,
        request.requested_by_name,
        ...request.items.map((item) => item.inventory_item_name),
      ]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(normalized));
    });
  }, [requests, searchTerm, statusFilter]);

  const pendingCount = useMemo(
    () => requests.filter((request) => request.status === 'AWAITING_CMD_APPROVAL').length,
    [requests]
  );
  const approvedCount = useMemo(
    () => requests.filter((request) => request.status === 'APPROVED').length,
    [requests]
  );
  const rejectedCount = useMemo(
    () => requests.filter((request) => request.status === 'REJECTED').length,
    [requests]
  );
  const pendingCatalogCount = useMemo(
    () =>
      catalogRequests.filter((item) => item.lifecycle_status === 'AWAITING_CMD_APPROVAL').length,
    [catalogRequests]
  );

  const handleDecision = async (
    requestId: string,
    decision: 'APPROVE' | 'REJECT'
  ) => {
    try {
      setActingRequestId(requestId);
      const updated = await pharmacyCmdService.reviewRefillRequest(requestId, { decision });
      setFlashMessage(
        `${updated.requesting_unit_name} request ${workflowLabel(updated.status)}.`
      );
      await loadRequests('refresh');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to complete CMD review.');
    } finally {
      setActingRequestId(null);
    }
  };

  const handleCatalogDecision = async (
    itemId: string,
    decision: 'APPROVE' | 'REJECT'
  ) => {
    try {
      setActingRequestId(itemId);
      const updated = await pharmacyCatalogGovernanceService.reviewCmdCatalogRequest(itemId, {
        decision,
      });
      setFlashMessage(
        `${updated.generic_name} catalog request ${workflowLabel(updated.lifecycle_status)}.`
      );
      await loadRequests('refresh');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to complete CMD catalog review.');
    } finally {
      setActingRequestId(null);
    }
  };

  return (
    <div className="space-y-6">
      <DashboardHero
        title="CMD Approval Workspace"
        subtitle={HOSPITAL_NAME}
        workspaceLabel="Department and unit supply requests awaiting CMD authority"
        monogram="C"
        variant="calm-light"
        accentLabel="Chief Medical Director"
        rightSlot={
          <>
            <div>
              <span className="font-semibold">Approver:</span>{' '}
              {getDashboardUserDisplayName(dashboardUser)}
            </div>
            <div>
              <span className="font-semibold">Role:</span> Chief Medical Director (CMD)
            </div>
          </>
        }
        actionsSlot={
          <Button variant="secondary" onClick={() => void loadRequests('refresh')} isLoading={refreshing}>
            Refresh Queue
          </Button>
        }
      />

      {flashMessage ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {flashMessage}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <MetricTile label="Awaiting CMD Approval" value={pendingCount} detail="Requests blocked until CMD decision" />
        <MetricTile label="Approved" value={approvedCount} detail="Released to HOD/store visibility" />
        <MetricTile label="Rejected" value={rejectedCount} detail="Requests not approved for store execution" />
        <MetricTile label="Catalog Queue" value={pendingCatalogCount} detail="New pharmacy items awaiting CMD governance" />
      </div>

      <Card>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_240px]">
          <Input
            label="Search requests"
            placeholder="Unit, request type, item, requester, or status"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
          />
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Status</label>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
            >
              <option value={ALL_FILTER}>All statuses</option>
              <option value="AWAITING_CMD_APPROVAL">Awaiting CMD approval</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
        </div>
      </Card>

      {loading ? (
        <Card title="Loading CMD Queue">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
            Loading departmental and store approval requests...
          </div>
        </Card>
      ) : (
        <Card title="Supply Approval Queue" titleClassName="text-slate-900">
          {!filteredRequests.length ? (
            <EmptyState
              title="No requests match this view"
              detail="Adjust the search term or status filter, or wait for new departmental requests."
            />
          ) : (
            <div className="space-y-4">
              {filteredRequests.map((request) => {
                const awaitingDecision = request.status === 'AWAITING_CMD_APPROVAL';
                return (
                  <div key={request.id} className="rounded-3xl border border-slate-200 bg-white p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-lg font-semibold text-slate-900">{request.requesting_unit_name}</p>
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClass(request.status)}`}>
                            {workflowLabel(request.status)}
                          </span>
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${priorityClass(request.urgency)}`}>
                            {request.urgency || 'ROUTINE'}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600">
                          {workflowLabel(request.request_type)} • Submitted {formatDateTime(request.requested_at)}
                        </p>
                        <p className="text-sm text-slate-600">
                          Requested by {request.requested_by_name || 'Unknown requester'}
                        </p>
                      </div>
                      {awaitingDecision ? (
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            onClick={() => void handleDecision(request.id, 'APPROVE')}
                            isLoading={actingRequestId === request.id}
                            disabled={Boolean(actingRequestId && actingRequestId !== request.id)}
                          >
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => void handleDecision(request.id, 'REJECT')}
                            isLoading={actingRequestId === request.id}
                            disabled={Boolean(actingRequestId && actingRequestId !== request.id)}
                          >
                            Reject
                          </Button>
                        </div>
                      ) : (
                        <p className="text-sm text-slate-500">Decision recorded</p>
                      )}
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      {request.items.map((item) => (
                        <div key={item.id} className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm">
                          <p className="font-medium text-slate-900">{item.inventory_item_name}</p>
                          <p className="mt-1 text-slate-600">Requested {item.requested_quantity}</p>
                          <p className="mt-1 text-slate-600">Approved {item.approved_quantity ?? 0}</p>
                          <p className="mt-1 text-slate-600">
                            Pending {(item.approved_quantity ?? item.requested_quantity) - item.received_quantity}
                          </p>
                        </div>
                      ))}
                    </div>
                    {request.requester_timeline.length ? (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {request.requester_timeline.map((step) => (
                          <span
                            key={`${request.id}-${step}`}
                            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700"
                          >
                            {step}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {loading ? null : (
        <Card title="Pharmacy Catalog Approval Queue" titleClassName="text-slate-900">
          {!catalogRequests.length ? (
            <EmptyState
              title="No catalog requests pending"
              detail="New medication and commodity requests from Pharmacy HOD will appear here for CMD review."
            />
          ) : (
            <div className="space-y-4">
              {catalogRequests.map((item) => {
                const awaitingDecision = item.lifecycle_status === 'AWAITING_CMD_APPROVAL';
                return (
                  <div key={item.id} className="rounded-3xl border border-slate-200 bg-white p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-lg font-semibold text-slate-900">
                            {item.generic_name}
                            {item.strength ? ` ${item.strength}` : ''}
                            {item.dosage_form ? ` ${item.dosage_form}` : ''}
                          </p>
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClass(item.lifecycle_status)}`}>
                            {workflowLabel(item.lifecycle_status)}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600">
                          {item.catalog_code} • {item.classification} • {item.tracking_mode}
                        </p>
                        <p className="text-sm text-slate-600">
                          Requested by {item.requested_by_name || 'Unknown requester'}
                        </p>
                        <p className="text-sm text-slate-600">{item.justification}</p>
                      </div>
                      {awaitingDecision ? (
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            onClick={() => void handleCatalogDecision(item.id, 'APPROVE')}
                            isLoading={actingRequestId === item.id}
                            disabled={Boolean(actingRequestId && actingRequestId !== item.id)}
                          >
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => void handleCatalogDecision(item.id, 'REJECT')}
                            isLoading={actingRequestId === item.id}
                            disabled={Boolean(actingRequestId && actingRequestId !== item.id)}
                          >
                            Reject
                          </Button>
                        </div>
                      ) : (
                        <p className="text-sm text-slate-500">Decision recorded</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
