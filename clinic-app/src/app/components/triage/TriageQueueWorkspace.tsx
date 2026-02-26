'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { Badge } from '@/shared/Badge';
import { VisitResponse } from '@/shared/types';
import {
  TriageAssessmentResponse,
  TriageDraftResponse,
  TriageFinalizeResponse,
  visitService,
} from '@/domains/visit/services/visitService';
import { VisitServiceLine, UserRole } from '@/shared/enums';
import { TriageAssessmentModal } from '@/app/reception/components/visit/TriageAssessmentModal';

interface TriageQueueWorkspaceProps {
  triageRole: UserRole.CHEW | UserRole.MIDWIFE;
  onTriageCompleted?: (visitId: string) => void;
}

const SERVICE_LINE_LABELS: Record<VisitServiceLine, string> = {
  OPD: 'Outpatient',
  ANC: 'Antenatal',
  MATERNITY: 'Maternity/Labour',
};

const ACUITY_BADGE_VARIANT: Record<'CRITICAL' | 'URGENT' | 'ROUTINE', 'error' | 'warning' | 'success'> = {
  CRITICAL: 'error',
  URGENT: 'warning',
  ROUTINE: 'success',
};

const formatClock = (value?: string | null) => {
  if (!value) return '—';
  return new Date(value).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
};

export function TriageQueueWorkspace({ triageRole, onTriageCompleted }: TriageQueueWorkspaceProps) {
  const [queue, setQueue] = useState<VisitResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedVisit, setSelectedVisit] = useState<VisitResponse | null>(null);
  const [activeAssessment, setActiveAssessment] = useState<TriageAssessmentResponse | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [loadingModal, setLoadingModal] = useState(false);

  const queueTitle = triageRole === UserRole.CHEW ? 'CHEW Triage Queue' : 'Midwife Triage Queue';

  const loadQueue = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await visitService.getTriageQueue();
      setQueue(data);
    } catch (err: unknown) {
      console.error('Unable to load triage queue', err);
      setError('Unable to load triage queue. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const openAssessment = async (visit: VisitResponse) => {
    try {
      setLoadingModal(true);
      setError(null);
      setSelectedVisit(visit);
      const assessment = await visitService.getActiveTriage(visit.id);
      setActiveAssessment(assessment);
      setModalOpen(true);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Unable to open triage assessment.');
      setSelectedVisit(null);
    } finally {
      setLoadingModal(false);
    }
  };

  const waitingCounts = useMemo(() => {
    const counts = {
      total: queue.length,
      opd: 0,
      anc: 0,
      maternity: 0,
    };

    for (const visit of queue) {
      if (visit.service_line === VisitServiceLine.OPD) counts.opd += 1;
      if (visit.service_line === VisitServiceLine.ANC) counts.anc += 1;
      if (visit.service_line === VisitServiceLine.MATERNITY) counts.maternity += 1;
    }

    return counts;
  }, [queue]);

  const handleDraftSaved = (response: TriageDraftResponse) => {
    setActiveAssessment(response.triage_assessment);
    setSelectedVisit((prev) => {
      if (!prev || prev.id !== response.visit_id) {
        return prev;
      }
      return {
        ...prev,
        version: response.visit_version,
      };
    });

    setQueue((prev) =>
      prev.map((visit) =>
        visit.id === response.visit_id
          ? {
              ...visit,
              version: response.visit_version,
            }
          : visit
      )
    );
  };

  const handleSigned = (response: TriageFinalizeResponse) => {
    const completedVisitId = response.visit_id;
    setModalOpen(false);
    setSelectedVisit(null);
    setActiveAssessment(null);
    setQueue((prev) => prev.filter((visit) => visit.id !== completedVisitId));
    onTriageCompleted?.(completedVisitId);
  };

  return (
    <Card title={queueTitle} titleClassName="text-slate-900">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-xs uppercase tracking-wide text-slate-500">Pending triage</p>
            <p className="mt-1 text-lg font-semibold text-slate-900">{waitingCounts.total}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-xs uppercase tracking-wide text-slate-500">Outpatient</p>
            <p className="mt-1 text-lg font-semibold text-slate-900">{waitingCounts.opd}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-xs uppercase tracking-wide text-slate-500">Antenatal</p>
            <p className="mt-1 text-lg font-semibold text-slate-900">{waitingCounts.anc}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-xs uppercase tracking-wide text-slate-500">Maternity</p>
            <p className="mt-1 text-lg font-semibold text-slate-900">{waitingCounts.maternity}</p>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-600">
            Complete vital signs and sign triage before consultation handoff.
          </p>
          <Button size="sm" variant="secondary" onClick={loadQueue} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh queue'}
          </Button>
        </div>

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        )}

        {loading && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
            Loading triage queue…
          </div>
        )}

        {!loading && queue.length === 0 && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-8 text-center text-sm text-emerald-700">
            No patients are waiting for triage at this time.
          </div>
        )}

        {!loading && queue.length > 0 && (
          <div className="space-y-2">
            {queue.map((visit) => (
              <div
                key={visit.id}
                className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-slate-900">
                      {visit.patient_name ?? 'Unknown patient'}
                    </p>
                    <Badge variant="outline" size="sm">
                      {visit.service_line ? SERVICE_LINE_LABELS[visit.service_line] : 'Service line'}
                    </Badge>
                    {visit.triage_acuity && (
                      <Badge variant={ACUITY_BADGE_VARIANT[visit.triage_acuity]} size="sm">
                        {visit.triage_acuity}
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    MRN {visit.patient_mrn ?? '—'} • Arrival {formatClock(visit.created_at)}
                  </p>
                </div>

                <Button
                  size="sm"
                  onClick={() => openAssessment(visit)}
                  isLoading={loadingModal && selectedVisit?.id === visit.id}
                  disabled={loadingModal}
                >
                  Assess triage
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedVisit && (
        <TriageAssessmentModal
          isOpen={modalOpen}
          visitId={selectedVisit.id}
          visitVersion={selectedVisit.version}
          currentUserRole={triageRole}
          existingAssessment={activeAssessment}
          onClose={() => {
            setModalOpen(false);
            setSelectedVisit(null);
            setActiveAssessment(null);
          }}
          onDraftSaved={handleDraftSaved}
          onSigned={handleSigned}
        />
      )}
    </Card>
  );
}
