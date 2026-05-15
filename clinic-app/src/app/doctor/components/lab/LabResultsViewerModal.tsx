'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { PurposeOfUse } from '@/shared/enums';
import { VisitResponse } from '@/shared/types';
import {
  DoctorLabResultDetail,
  DoctorLabResultFieldValue,
  DoctorLabVisitResultSummary,
  DoctorPatientLabHistoryEntry,
  doctorLabService,
} from '@/domains/lab/services/doctorLabService';
import { LabRequest } from '@/domains/lab/services/labService';

interface LabResultsViewerModalProps {
  visit: VisitResponse | null;
  doctorFullName?: string | null;
  isOpen: boolean;
  onClose: () => void;
}

function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function formatFieldValue(value: DoctorLabResultFieldValue): string {
  if (value.value_number !== null && value.value_number !== undefined) {
    return `${value.value_number}${value.unit ? ` ${value.unit}` : ''}`;
  }
  if (value.value_boolean !== null && value.value_boolean !== undefined) {
    return value.value_boolean ? 'Yes' : 'No';
  }
  if (value.value_string !== null && value.value_string !== undefined) {
    return value.value_string;
  }
  if (value.value_json !== null && value.value_json !== undefined) {
    return JSON.stringify(value.value_json);
  }
  return '—';
}

function summarizeHistoryValues(values: DoctorLabResultFieldValue[]): string {
  return values
    .slice(0, 3)
    .map((value) => `${value.field_name}: ${formatFieldValue(value)}`)
    .join(' • ');
}

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function buildPrintableReportHtml(detail: DoctorLabResultDetail): string {
  const rows = detail.values
    .map(
      (value) => `
        <tr>
          <td>${escapeHtml(value.field_name)}</td>
          <td>${escapeHtml(formatFieldValue(value))}</td>
          <td>${escapeHtml(value.reference_range_text || '—')}</td>
          <td>${value.critical_flag ? 'Critical' : value.abnormal_flag ? 'Abnormal' : 'Normal'}</td>
        </tr>
      `
    )
    .join('');
  const specimenRows = detail.specimens
    .map(
      (specimen) => `
        <li>
          ${escapeHtml(specimen.accession_number)} • ${escapeHtml(specimen.specimen_type)} •
          Collected ${escapeHtml(formatDateTime(specimen.collected_at))} •
          Received ${escapeHtml(formatDateTime(specimen.received_at))}
        </li>
      `
    )
    .join('');
  const amendedBanner = detail.is_amended
    ? `
      <div class="banner">
        <strong>AMENDED REPORT</strong><br />
        Amendment time: ${escapeHtml(formatDateTime(detail.released_at))}<br />
        Amendment reason: ${escapeHtml(detail.amendment_reason || 'Not recorded')}
      </div>
    `
    : '';

  return `
    <!DOCTYPE html>
    <html>
      <head>
        <title>${escapeHtml(detail.test_name)} Report</title>
        <style>
          body { font-family: Arial, sans-serif; color: #0f172a; margin: 32px; }
          h1, h2, h3 { margin: 0; }
          .header { margin-bottom: 24px; }
          .banner { margin: 16px 0; padding: 12px; border: 1px solid #dc2626; background: #fef2f2; }
          .meta { margin: 12px 0 24px; font-size: 14px; line-height: 1.6; }
          table { width: 100%; border-collapse: collapse; margin-top: 12px; }
          th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: left; font-size: 14px; }
          th { background: #f8fafc; }
          .label { display: inline-block; margin-right: 8px; padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 999px; font-size: 12px; }
          .critical { border-color: #dc2626; color: #991b1b; }
          .abnormal { border-color: #f59e0b; color: #92400e; }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>Specialist Hospital Kazaure</h1>
          <p>Laboratory Diagnostic Report</p>
        </div>
        ${amendedBanner}
        <div class="meta">
          <div><strong>Patient:</strong> ${escapeHtml(detail.patient_name)}</div>
          <div><strong>MRN:</strong> ${escapeHtml(detail.patient_mrn || '—')}</div>
          <div><strong>Visit ID:</strong> ${escapeHtml(detail.visit_id)}</div>
          <div><strong>Test:</strong> ${escapeHtml(detail.test_name)}</div>
          <div><strong>Unit:</strong> ${escapeHtml(detail.unit_name || '—')}</div>
          <div><strong>Accession:</strong> ${escapeHtml(detail.accession_numbers.join(', ') || '—')}</div>
          <div><strong>Released:</strong> ${escapeHtml(formatDateTime(detail.released_at))}</div>
          <div><strong>Verified by:</strong> ${escapeHtml(detail.verified_by_name || '—')}</div>
        </div>
        <div>
          ${detail.has_critical ? '<span class="label critical">Critical Result</span>' : ''}
          ${!detail.has_critical && detail.has_abnormal ? '<span class="label abnormal">Abnormal Result</span>' : ''}
        </div>
        <table>
          <thead>
            <tr>
              <th>Analyte</th>
              <th>Result</th>
              <th>Reference</th>
              <th>Flag</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
        <h3 style="margin-top: 24px;">Specimen Trace</h3>
        <ul>${specimenRows || '<li>No specimen trace available.</li>'}</ul>
      </body>
    </html>
  `;
}

export function LabResultsViewerModal({
  visit,
  doctorFullName,
  isOpen,
  onClose,
}: LabResultsViewerModalProps) {
  const [visitResults, setVisitResults] = useState<DoctorLabVisitResultSummary[]>([]);
  const [labRequests, setLabRequests] = useState<LabRequest[]>([]);
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DoctorLabResultDetail | null>(null);
  const [history, setHistory] = useState<DoctorPatientLabHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getErrorDetail = (errorValue: unknown): string | null => {
    if (
      typeof errorValue !== 'object' ||
      errorValue === null ||
      !('response' in errorValue)
    ) {
      return null;
    }
    const detailValue = (
      errorValue as { response?: { data?: { detail?: unknown } } }
    ).response?.data?.detail;
    return typeof detailValue === 'string' ? detailValue : null;
  };

  const pendingRequests = useMemo(
    () => labRequests.filter((request) => request.status === 'PENDING'),
    [labRequests]
  );

  const stats = useMemo(
    () => ({
      pending: pendingRequests.length,
      released: visitResults.length,
      critical: visitResults.filter((result) => result.has_critical).length,
      amended: visitResults.filter((result) => result.is_amended).length,
    }),
    [pendingRequests.length, visitResults]
  );

  const loadDetail = useCallback(
    async (resultId: string) => {
      if (!visit) return;
      try {
        setDetailLoading(true);
        setError(null);
        const detailResponse = await doctorLabService.getVisitLabResultDetail(
          visit.id,
          resultId,
          {
            purpose_of_use: PurposeOfUse.TREATMENT,
            justification: 'Diagnostic result review',
          }
        );
        setDetail(detailResponse);
        setSelectedResultId(resultId);

        const testIdentifier = detailResponse.test_code || detailResponse.test_name;
        setHistoryLoading(true);
        const historyResponse = await doctorLabService.getPatientLabHistory(
          detailResponse.patient_id,
          testIdentifier,
          {
            purpose_of_use: PurposeOfUse.TREATMENT,
            justification: 'Longitudinal lab result review',
          }
        );
        setHistory(historyResponse);
      } catch (errorValue: unknown) {
        setError(getErrorDetail(errorValue) || 'Unable to load detailed lab result.');
      } finally {
        setDetailLoading(false);
        setHistoryLoading(false);
      }
    },
    [visit]
  );

  useEffect(() => {
    if (!isOpen || !visit) {
      setVisitResults([]);
      setLabRequests([]);
      setSelectedResultId(null);
      setDetail(null);
      setHistory([]);
      setError(null);
      return;
    }

    let isMounted = true;
    const currentVisit = visit;

    async function loadVisitResults() {
      try {
        setLoading(true);
        setError(null);
        const [summaryResponse, requestResponse] = await Promise.all([
          doctorLabService.getVisitLabResults(currentVisit.id, {
            purpose_of_use: PurposeOfUse.TREATMENT,
            justification: 'Visit lab result review',
          }),
          doctorLabService.getLabRequestsByVisit(currentVisit.id, {
            purpose_of_use: PurposeOfUse.TREATMENT,
            justification: 'Visit lab request review',
          }),
        ]);

        if (!isMounted) return;

        setVisitResults(summaryResponse);
        setLabRequests(requestResponse);

        if (summaryResponse.length > 0) {
          await loadDetail(summaryResponse[0].result_id);
        } else {
          setDetail(null);
          setSelectedResultId(null);
          setHistory([]);
        }
      } catch (errorValue: unknown) {
        if (!isMounted) return;
        setError(getErrorDetail(errorValue) || 'Unable to load lab results.');
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void loadVisitResults();

    return () => {
      isMounted = false;
    };
  }, [isOpen, loadDetail, visit]);

  if (!isOpen || !visit) return null;

  const handlePrint = () => {
    if (!detail || typeof window === 'undefined') return;
    const printWindow = window.open('', '_blank', 'noopener,noreferrer,width=980,height=720');
    if (!printWindow) return;
    printWindow.document.write(buildPrintableReportHtml(detail));
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-7xl overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 shadow-2xl">
        <div className="border-b border-slate-200 bg-white px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0B4DA2]">
                Diagnostic Results
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-slate-900">
                Visit Laboratory Results
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {visit.patient_name || 'Unknown patient'} •{' '}
                {visit.patient_mrn ? `MRN ${visit.patient_mrn}` : `Visit ${visit.id}`}
              </p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
                  Visit status: {visit.status}
                </span>
                {doctorFullName && (
                  <span className="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
                    Attending doctor: {doctorFullName}
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close lab results"
              className="text-2xl leading-none text-slate-400 hover:text-slate-600"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="grid gap-6 px-6 py-6 xl:grid-cols-[340px_minmax(0,1fr)]">
          <div className="space-y-4">
            <Card title="Visit Summary" titleClassName="!text-[#0B4DA2]">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-slate-200 bg-white p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Pending</p>
                  <p className="mt-1 text-2xl font-semibold text-slate-900">{stats.pending}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Released</p>
                  <p className="mt-1 text-2xl font-semibold text-slate-900">{stats.released}</p>
                </div>
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-3">
                  <p className="text-xs uppercase tracking-wide text-rose-700">Critical</p>
                  <p className="mt-1 text-2xl font-semibold text-rose-800">{stats.critical}</p>
                </div>
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
                  <p className="text-xs uppercase tracking-wide text-amber-700">Amended</p>
                  <p className="mt-1 text-2xl font-semibold text-amber-800">{stats.amended}</p>
                </div>
              </div>
            </Card>

            <Card title="Released Results" titleClassName="!text-[#0B4DA2]">
              {loading && (
                <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
                  Loading released results…
                </div>
              )}
              {!loading && visitResults.length === 0 && (
                <div className="space-y-3">
                  <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    {pendingRequests.length > 0
                      ? 'No released results yet. Lab work is still pending for this visit.'
                      : 'No laboratory result has been released for this visit.'}
                  </div>
                  {pendingRequests.length > 0 && (
                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Pending Requests
                      </p>
                      <div className="mt-3 space-y-2">
                        {pendingRequests.map((request) => (
                          <div
                            key={request.id}
                            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
                          >
                            <div className="font-medium text-slate-900">{request.test_name}</div>
                            <div className="mt-1 text-xs text-slate-500">
                              Requested {formatDateTime(request.created_at)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              {!loading && visitResults.length > 0 && (
                <div className="space-y-3">
                  {visitResults.map((result) => {
                    const isSelected = selectedResultId === result.result_id;
                    return (
                      <button
                        key={result.result_id}
                        type="button"
                        onClick={() => void loadDetail(result.result_id)}
                        className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                          isSelected
                            ? 'border-[#0B4DA2] bg-[#F5FAFE] shadow-sm'
                            : 'border-slate-200 bg-white hover:border-[#93c5fd] hover:bg-sky-50/50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-slate-900">
                              {result.test_name}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              Released {formatDateTime(result.released_at)}
                            </p>
                          </div>
                          <div className="flex flex-wrap justify-end gap-1">
                            {result.has_critical && (
                              <span className="rounded-full border border-rose-300 bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700">
                                ⚠ Critical
                              </span>
                            )}
                            {!result.has_critical && result.has_abnormal && (
                              <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                                Abnormal
                              </span>
                            )}
                            {result.is_amended && (
                              <span className="rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                                Amended
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                          <span>{result.unit_name || 'Unassigned unit'}</span>
                          <span>•</span>
                          <span>{result.specimen_count} specimen(s)</span>
                          {result.accession_numbers.length > 0 && (
                            <>
                              <span>•</span>
                              <span>{result.accession_numbers.join(', ')}</span>
                            </>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </Card>
          </div>

          <div className="space-y-4">
            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {detailLoading && (
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
                Loading result detail…
              </div>
            )}

            {!detailLoading && detail && (
              <>
                <Card title="Released Result Detail" titleClassName="!text-[#0B4DA2]">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h3 className="text-xl font-semibold text-slate-900">
                        {detail.test_name}
                      </h3>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {detail.state_labels.map((label) => (
                          <span
                            key={label}
                            className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                              label === 'Critical'
                                ? 'border border-rose-300 bg-rose-50 text-rose-700'
                                : label === 'Abnormal'
                                  ? 'border border-amber-300 bg-amber-50 text-amber-700'
                                  : 'border border-slate-200 bg-slate-100 text-slate-700'
                            }`}
                          >
                            {label === 'Critical' ? '⚠ ' : ''}
                            {label}
                          </span>
                        ))}
                      </div>
                      <div className="mt-3 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
                        <div>
                          <p className="text-xs uppercase tracking-wide text-slate-500">Patient</p>
                          <p className="font-medium text-slate-900">{detail.patient_name}</p>
                          <p>{detail.patient_mrn ? `MRN ${detail.patient_mrn}` : 'MRN not issued'}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-wide text-slate-500">Specimen</p>
                          <p>{detail.accession_numbers.join(', ') || 'No accession recorded'}</p>
                          <p>{detail.unit_name || 'Lab unit not assigned'}</p>
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <Button variant="secondary" onClick={handlePrint}>
                        Print Report
                      </Button>
                    </div>
                  </div>

                  <div className="mt-6 overflow-hidden rounded-xl border border-slate-200">
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead className="bg-slate-100 text-slate-600">
                        <tr>
                          <th className="px-4 py-3 text-left font-semibold">Analyte</th>
                          <th className="px-4 py-3 text-left font-semibold">Result</th>
                          <th className="px-4 py-3 text-left font-semibold">Reference</th>
                          <th className="px-4 py-3 text-left font-semibold">Indicator</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 bg-white">
                        {detail.values.map((value) => (
                          <tr key={`${detail.result_id}-${value.field_code}`}>
                            <td className="px-4 py-3 align-top">
                              <div className="font-medium text-slate-900">{value.field_name}</div>
                              <div className="text-xs text-slate-500">{value.field_code}</div>
                            </td>
                            <td className="px-4 py-3 align-top text-slate-900">
                              {formatFieldValue(value)}
                            </td>
                            <td className="px-4 py-3 align-top text-slate-600">
                              {value.reference_range_text || '—'}
                            </td>
                            <td className="px-4 py-3 align-top">
                              {value.critical_flag ? (
                                <span className="inline-flex items-center rounded-full border border-rose-300 bg-rose-50 px-2 py-0.5 text-xs font-semibold text-rose-700">
                                  ⚠ Critical Value
                                </span>
                              ) : value.abnormal_flag ? (
                                <span className="inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
                                  Abnormal
                                </span>
                              ) : (
                                <span className="inline-flex items-center rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                                  Normal
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>

                <div className="grid gap-4 xl:grid-cols-2">
                  <Card title="Verification & Release" titleClassName="!text-[#0B4DA2]">
                    <dl className="space-y-3 text-sm">
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Entered By</dt>
                        <dd className="text-slate-900">
                          {detail.entered_by_name || detail.entered_by || '—'} • {formatDateTime(detail.entered_at)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Verified By</dt>
                        <dd className="text-slate-900">
                          {detail.verified_by_name || detail.verified_by || '—'} • {formatDateTime(detail.verified_at)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Released By</dt>
                        <dd className="text-slate-900">
                          {detail.released_by_name || detail.released_by || '—'} • {formatDateTime(detail.released_at)}
                        </dd>
                      </div>
                      {detail.is_amended && (
                        <div>
                          <dt className="text-xs uppercase tracking-wide text-slate-500">Amendment</dt>
                          <dd className="text-slate-900">
                            {detail.amendment_reason || 'Amendment reason not recorded.'}
                          </dd>
                        </div>
                      )}
                    </dl>
                  </Card>

                  <Card title="Specimen Trace" titleClassName="!text-[#0B4DA2]">
                    <div className="space-y-3">
                      {detail.specimens.length === 0 && (
                        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                          No specimen trace available.
                        </div>
                      )}
                      {detail.specimens.map((specimen) => (
                        <div
                          key={specimen.specimen_id}
                          className="rounded-xl border border-slate-200 bg-white p-3 text-sm"
                        >
                          <div className="font-medium text-slate-900">
                            {specimen.accession_number}
                            {specimen.specimen_label_suffix
                              ? ` • ${specimen.specimen_label_suffix}`
                              : ''}
                          </div>
                          <div className="mt-2 grid gap-2 text-slate-600 sm:grid-cols-2">
                            <p>{specimen.specimen_type} • {specimen.specimen_source}</p>
                            <p>Status: {specimen.status}</p>
                            <p>Container: {specimen.container_type || '—'}</p>
                            <p>Site: {specimen.collection_site || '—'}</p>
                            <p>Collected: {formatDateTime(specimen.collected_at)}</p>
                            <p>Received: {formatDateTime(specimen.received_at)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <Card title="Critical Alerts" titleClassName="!text-[#0B4DA2]">
                    <div className="space-y-3">
                      {detail.alerts.length === 0 && (
                        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                          No active critical alert for this released result.
                        </div>
                      )}
                      {detail.alerts.map((alert) => (
                        <div
                          key={alert.alert_id}
                          className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm"
                        >
                          <div className="font-semibold text-rose-800">⚠ {alert.message}</div>
                          <div className="mt-2 text-rose-700">
                            <p>Severity: {alert.severity}</p>
                            <p>Status: {alert.status}</p>
                            <p>Created: {formatDateTime(alert.created_at)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>

                  <Card title="Amendment Chain" titleClassName="!text-[#0B4DA2]">
                    <div className="space-y-3">
                      {!detail.is_amended && detail.prior_versions.length === 0 && (
                        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                          This result has no prior released version.
                        </div>
                      )}
                      {detail.prior_versions.map((version) => (
                        <div
                          key={version.result_id}
                          className="rounded-xl border border-slate-200 bg-white p-3 text-sm"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-slate-900">
                              Version {version.result_id.slice(0, 8)}
                            </span>
                            {version.is_superseded && (
                              <span className="rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                                Superseded
                              </span>
                            )}
                          </div>
                          <p className="mt-2 text-slate-600">
                            Released {formatDateTime(version.released_at)}
                          </p>
                          {version.amendment_reason && (
                            <p className="mt-1 text-slate-600">
                              Reason: {version.amendment_reason}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>

                <Card title="Patient Lab History" titleClassName="!text-[#0B4DA2]">
                  {historyLoading && (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                      Loading longitudinal history…
                    </div>
                  )}
                  {!historyLoading && history.length === 0 && (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                      No prior released history found for this test.
                    </div>
                  )}
                  {!historyLoading && history.length > 0 && (
                    <div className="space-y-3">
                      {history.map((entry) => (
                        <div
                          key={entry.result_id}
                          className={`rounded-xl border p-3 text-sm ${
                            entry.result_id === detail.result_id
                              ? 'border-[#0B4DA2] bg-[#F5FAFE]'
                              : 'border-slate-200 bg-white'
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <p className="font-medium text-slate-900">
                                {formatDateTime(entry.released_at)}
                              </p>
                              <p className="mt-1 text-slate-600">
                                {summarizeHistoryValues(entry.values) || 'Result available'}
                              </p>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {entry.has_critical && (
                                <span className="rounded-full border border-rose-300 bg-rose-50 px-2 py-0.5 text-xs font-semibold text-rose-700">
                                  ⚠ Critical
                                </span>
                              )}
                              {!entry.has_critical && entry.has_abnormal && (
                                <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
                                  Abnormal
                                </span>
                              )}
                              {entry.is_amended && (
                                <span className="rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                                  Amended
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </>
            )}

            {!detailLoading && !detail && !loading && !error && (
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-5 text-sm text-slate-500">
                Select a released result to review the full diagnostic report.
              </div>
            )}

            <div className="flex justify-end">
              <Button variant="secondary" onClick={onClose}>
                Close
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
