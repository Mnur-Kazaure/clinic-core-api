'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { AncQueuePanel } from '@/app/anc/components/AncQueuePanel';
import { PregnancyOverviewSticky } from '@/app/anc/components/PregnancyOverviewSticky';
import { VisitTimeline } from '@/app/anc/components/VisitTimeline';
import { NewVisitDrawer } from '@/app/anc/components/NewVisitDrawer';
import { PreviousPregnanciesPanel } from '@/app/anc/components/PreviousPregnanciesPanel';
import { EpisodeDetailsPanel } from '@/app/anc/components/EpisodeDetailsPanel';
import { AncHandoverPanel } from '@/app/anc/components/AncHandoverPanel';
import { AncExportModal } from '@/app/anc/components/AncExportModal';
import { useAncQueue } from '@/domains/anc/hooks/useAncQueue';
import { useAncEpisode } from '@/domains/anc/hooks/useAncEpisode';
import { useAncVisits } from '@/domains/anc/hooks/useAncVisits';
import { PurposeOfUse, VisitServiceLine } from '@/shared/enums';
import { FollowUpListItem, followUpService } from '@/domains/followup/services/followupService';
import { userService, Doctor } from '@/domains/user/services/userService';
import { visitService } from '@/domains/visit/services/visitService';
import { ANCExportOptions, PregnancyEpisodeCreate } from '@/domains/anc/api/anc';
import { ancApi } from '@/domains/anc/api/anc';

export function AncDashboard() {
  const queueState = useAncQueue();
  const selectedPatientId = queueState.selectedVisit?.patient_id ?? null;

  const episodeState = useAncEpisode(selectedPatientId);
  const visitsState = useAncVisits({ queue: queueState.queue, patientId: selectedPatientId });

  const [newVisitDrawerOpen, setNewVisitDrawerOpen] = useState(false);

  const [assignableChews, setAssignableChews] = useState<Doctor[]>([]);
  const [assignableMidwives, setAssignableMidwives] = useState<Doctor[]>([]);
  const [selectedOwnerId, setSelectedOwnerId] = useState('');
  const [selectedMidwifeId, setSelectedMidwifeId] = useState('');
  const [reassignLoading, setReassignLoading] = useState(false);
  const [reassignError, setReassignError] = useState<string | null>(null);
  const [sendLoading, setSendLoading] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const [exportOpen, setExportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportPurpose, setExportPurpose] = useState<PurposeOfUse>(PurposeOfUse.TREATMENT);
  const [exportJustification, setExportJustification] = useState('');
  const [exportIncludePreviousPregnancies, setExportIncludePreviousPregnancies] = useState(true);
  const [exportIncludeEncounters, setExportIncludeEncounters] = useState(true);
  const [exportBlankRows, setExportBlankRows] = useState('0');
  const [followUps, setFollowUps] = useState<{
    overdue: FollowUpListItem[];
    today: FollowUpListItem[];
    upcoming: FollowUpListItem[];
  }>({
    overdue: [],
    today: [],
    upcoming: [],
  });
  const [followUpsLoading, setFollowUpsLoading] = useState(false);
  const [followUpsError, setFollowUpsError] = useState<string | null>(null);
  const [followUpSearch, setFollowUpSearch] = useState('');
  const [followUpActionError, setFollowUpActionError] = useState<string | null>(null);

  useEffect(() => {
    void queueState.refreshQueue();
  }, [queueState.refreshQueue]);

  useEffect(() => {
    void episodeState.refreshEpisode();
    void visitsState.refreshTimeline();
  }, [episodeState.refreshEpisode, visitsState.refreshTimeline]);

  useEffect(() => {
    let isMounted = true;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const loadFollowUps = async () => {
      try {
        setFollowUpsLoading(true);
        setFollowUpsError(null);
        const data = await followUpService.getMyFollowUps();
        if (!isMounted) return;
        const ancOnly = (items: FollowUpListItem[]) =>
          items.filter((item) => item.recommended_service_line === 'ANC');
        setFollowUps({
          overdue: ancOnly(data.overdue || []),
          today: ancOnly(data.today || []),
          upcoming: ancOnly(data.upcoming || []),
        });
      } catch {
        if (isMounted) {
          setFollowUpsError('Unable to load ANC follow-up worklist.');
        }
      } finally {
        if (isMounted) {
          setFollowUpsLoading(false);
        }
      }
    };

    void loadFollowUps();
    intervalId = setInterval(() => {
      void loadFollowUps();
    }, 60000);

    return () => {
      isMounted = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    const loadAssignableStaff = async () => {
      try {
        const staff = await userService.listAssignableStaff();
        const chews = staff.filter((member) => member.role === 'CHEW');
        const midwives = staff.filter((member) => member.role === 'MIDWIFE');
        setAssignableChews(chews);
        setAssignableMidwives(midwives);

        if (queueState.selectedVisit) {
          const chewFallback =
            chews.find((member) => member.id !== queueState.selectedVisit?.assigned_doctor_id)?.id ?? '';
          const midwifeFallback = midwives[0]?.id ?? '';
          setSelectedOwnerId(chewFallback);
          setSelectedMidwifeId(midwifeFallback);
        }
      } catch {
        setAssignableChews([]);
        setAssignableMidwives([]);
      }
    };

    void loadAssignableStaff();
  }, [queueState.selectedVisit?.id, queueState.selectedVisit?.assigned_doctor_id]);

  const selectedEncounter = queueState.selectedVisit
    ? visitsState.getEncounterForVisit(queueState.selectedVisit.id)
    : null;

  const handleSaveEpisode = async (payload: PregnancyEpisodeCreate) => {
    await episodeState.saveEpisode(payload);
    await visitsState.refreshTimeline();
  };

  const handleSaveEncounter = async (payload: Parameters<typeof visitsState.saveEncounter>[1]) => {
    if (!queueState.selectedVisit) return;

    const saved = await visitsState.saveEncounter(queueState.selectedVisit.id, payload);
    if (saved) {
      await visitsState.refreshTimeline();
      if (payload.action === 'SIGN') {
        setNewVisitDrawerOpen(false);
      }
    }
  };

  const handleAddPreviousPregnancy = async (
    payload: Parameters<typeof episodeState.addPreviousPregnancy>[0]
  ) => {
    await episodeState.addPreviousPregnancy(payload);
  };

  const filterFollowUps = (items: FollowUpListItem[]) => {
    const term = followUpSearch.trim().toLowerCase();
    if (!term) return items;
    return items.filter((item) => {
      const patientName = (item.patient_name || '').toLowerCase();
      const patientMrn = (item.patient_mrn || '').toLowerCase();
      const patientId = item.patient_id_canonical.toLowerCase();
      const reason = (item.reason || '').toLowerCase();
      return (
        patientName.includes(term) ||
        patientMrn.includes(term) ||
        patientId.includes(term) ||
        reason.includes(term)
      );
    });
  };

  const handleOpenFollowUpItem = (item: FollowUpListItem) => {
    setFollowUpActionError(null);
    if (!item.active_visit_id) {
      setFollowUpActionError(
        'No active linked visit yet. Ask reception to start a linked follow-up visit.'
      );
      return;
    }
    queueState.setSelectedVisitId(item.active_visit_id);
  };

  const handleReassignVisit = async () => {
    if (!queueState.selectedVisit || !selectedOwnerId || reassignLoading) return;

    try {
      setReassignLoading(true);
      setReassignError(null);
      const updated = await visitService.reassignOwner(queueState.selectedVisit.id, {
        assigned_doctor_id: selectedOwnerId,
        expected_version: queueState.selectedVisit.version,
        reason: 'ANC colleague handover',
      });
      await queueState.refreshQueue(updated.id);
    } catch (err: any) {
      setReassignError(err?.response?.data?.detail || 'Unable to reassign ANC owner.');
    } finally {
      setReassignLoading(false);
    }
  };

  const handleSendToMaternity = async () => {
    if (!queueState.selectedVisit || !selectedMidwifeId || sendLoading) return;

    try {
      setSendLoading(true);
      setSendError(null);
      const updated = await visitService.reassignOwner(queueState.selectedVisit.id, {
        assigned_doctor_id: selectedMidwifeId,
        expected_version: queueState.selectedVisit.version,
        service_line: VisitServiceLine.MATERNITY,
        reason: 'ANC handover to maternity',
      });
      await queueState.refreshQueue(updated.id);
    } catch (err: any) {
      setSendError(err?.response?.data?.detail || 'Unable to send visit to maternity.');
    } finally {
      setSendLoading(false);
    }
  };

  const handleExportPdf = async () => {
    if (!episodeState.episode || exporting) return;

    const trimmedJustification = exportJustification.trim();
    if (trimmedJustification.length < 2) {
      setExportError('Justification must be at least 2 characters.');
      return;
    }

    const options: ANCExportOptions = {
      purpose_of_use: exportPurpose,
      justification: trimmedJustification,
      include_previous_pregnancies: exportIncludePreviousPregnancies,
      include_encounters: exportIncludeEncounters,
      include_blank_rows: Number.isNaN(Number(exportBlankRows))
        ? 0
        : Math.max(0, Math.min(Number(exportBlankRows), 20)),
    };

    try {
      setExporting(true);
      setExportError(null);
      const pdfBlob = await ancApi.exportEpisodePdf(episodeState.episode.id, options);
      const blobUrl = window.URL.createObjectURL(pdfBlob);
      const opened = window.open(blobUrl, '_blank', 'noopener,noreferrer');
      if (!opened) {
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = `anc-export-${episodeState.episode.id}.pdf`;
        link.rel = 'noopener noreferrer';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60_000);
      setExportOpen(false);
    } catch (err: any) {
      const statusCode = err?.response?.status;
      if (statusCode === 403) {
        setExportError('Not authorized to export this ANC record.');
      } else if (statusCode === 400 || statusCode === 422) {
        const detail = err?.response?.data?.detail;
        setExportError(
          typeof detail === 'string' && detail.trim().length > 0
            ? detail
            : 'Validation failed. Check purpose and justification.'
        );
      } else {
        setExportError('Export failed. Retry.');
      }
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-4">
      <header className="rounded-2xl border border-slate-200 bg-gradient-to-r from-white via-blue-50/40 to-emerald-50/30 px-4 py-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">ANC Care Workspace</h1>
            <p className="mt-1 text-sm text-slate-600">
              Pregnancy journey view for baseline, monitoring encounters, and obstetric history.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              disabled={!episodeState.episode}
              onClick={() => {
                setExportError(null);
                setExportOpen(true);
              }}
            >
              Export PDF
            </Button>
            <Button
              size="sm"
              disabled={!queueState.selectedVisit}
              onClick={() => setNewVisitDrawerOpen(true)}
            >
              New visit
            </Button>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[320px_1fr]">
        <AncQueuePanel
          visits={queueState.filteredQueue}
          searchValue={queueState.search}
          selectedVisitId={queueState.selectedVisitId}
          loading={queueState.loading}
          error={queueState.error}
          onSearchChange={queueState.setSearch}
          onSelectVisit={queueState.setSelectedVisitId}
          onRefresh={() => {
            void queueState.refreshQueue();
          }}
        />

        <div className="space-y-4">
          <PregnancyOverviewSticky
            selectedVisit={queueState.selectedVisit}
            episode={episodeState.episode}
            onEditEpisode={() => {
              const detailsSection = document.getElementById('anc-episode-details');
              detailsSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }}
            actionSlot={
              <Button
                size="sm"
                variant="secondary"
                disabled={!queueState.selectedVisit}
                onClick={() => {
                  void visitsState.refreshTimeline();
                }}
              >
                Refresh data
              </Button>
            }
          />

          {episodeState.error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {episodeState.error}
            </div>
          ) : null}

          <AncHandoverPanel
            selectedVisit={queueState.selectedVisit}
            assignableChews={assignableChews}
            assignableMidwives={assignableMidwives}
            selectedOwnerId={selectedOwnerId}
            selectedMidwifeId={selectedMidwifeId}
            setSelectedOwnerId={setSelectedOwnerId}
            setSelectedMidwifeId={setSelectedMidwifeId}
            reassignLoading={reassignLoading}
            reassignError={reassignError}
            sendLoading={sendLoading}
            sendError={sendError}
            onReassign={handleReassignVisit}
            onSendToMaternity={handleSendToMaternity}
          />

          <section className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-slate-900">ANC Follow-Ups</p>
                <p className="text-xs text-slate-500">
                  Overdue, today, and upcoming follow-up obligations.
                </p>
              </div>
              <Button
                size="sm"
                variant="secondary"
                disabled={followUpsLoading}
                onClick={async () => {
                  try {
                    setFollowUpsLoading(true);
                    setFollowUpsError(null);
                    const data = await followUpService.getMyFollowUps();
                    const ancOnly = (items: FollowUpListItem[]) =>
                      items.filter((item) => item.recommended_service_line === 'ANC');
                    setFollowUps({
                      overdue: ancOnly(data.overdue || []),
                      today: ancOnly(data.today || []),
                      upcoming: ancOnly(data.upcoming || []),
                    });
                  } catch {
                    setFollowUpsError('Unable to load ANC follow-up worklist.');
                  } finally {
                    setFollowUpsLoading(false);
                  }
                }}
              >
                {followUpsLoading ? 'Refreshing…' : 'Refresh'}
              </Button>
            </div>

            <Input
              label="Quick Search"
              placeholder="Name, MRN, patient ID, reason..."
              value={followUpSearch}
              onChange={(event) => setFollowUpSearch(event.target.value)}
            />

            {followUpsError ? (
              <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {followUpsError}
              </div>
            ) : null}
            {followUpActionError ? (
              <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                {followUpActionError}
              </div>
            ) : null}

            <div className="mt-3 grid gap-3 md:grid-cols-3">
              {[
                { key: 'overdue', label: 'Overdue', items: filterFollowUps(followUps.overdue) },
                { key: 'today', label: 'Today', items: filterFollowUps(followUps.today) },
                {
                  key: 'upcoming',
                  label: 'Upcoming',
                  items: filterFollowUps(followUps.upcoming),
                },
              ].map((group) => (
                <div key={group.key} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                      {group.label}
                    </p>
                    <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-700">
                      {group.items.length}
                    </span>
                  </div>
                  {group.items.length === 0 ? (
                    <p className="text-xs text-slate-500">No follow-ups.</p>
                  ) : (
                    <div className="space-y-2">
                      {group.items.slice(0, 4).map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => handleOpenFollowUpItem(item)}
                          className="w-full rounded-md border border-slate-200 bg-white px-2 py-2 text-left hover:border-slate-300"
                        >
                          <p className="text-xs font-semibold text-slate-900">
                            {item.patient_name || 'Unknown patient'}
                          </p>
                          <p className="text-[11px] text-slate-500">
                            {item.patient_mrn
                              ? `MRN ${item.patient_mrn}`
                              : `ID ${item.patient_id_canonical.slice(0, 8)}...`}
                          </p>
                          <p className="mt-1 text-[11px] text-slate-600">{item.reason}</p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          <VisitTimeline
            timeline={visitsState.timeline}
            episode={episodeState.episode}
            loading={visitsState.loading || episodeState.loading}
            error={visitsState.error}
            onRefresh={() => {
              void visitsState.refreshTimeline();
            }}
          />

          <PreviousPregnanciesPanel
            rows={episodeState.previousPregnancies}
            disabled={!episodeState.episode}
            saving={episodeState.saving}
            onAdd={handleAddPreviousPregnancy}
          />

          <div id="anc-episode-details">
            <EpisodeDetailsPanel
              selectedPatientId={selectedPatientId}
              episode={episodeState.episode}
              saving={episodeState.saving}
              onSave={handleSaveEpisode}
            />
          </div>
        </div>
      </div>

      <NewVisitDrawer
        isOpen={newVisitDrawerOpen}
        visit={queueState.selectedVisit}
        episode={episodeState.episode}
        existingEncounter={selectedEncounter}
        saving={visitsState.saving}
        onClose={() => setNewVisitDrawerOpen(false)}
        onSubmit={handleSaveEncounter}
      />

      <AncExportModal
        open={exportOpen}
        exporting={exporting}
        error={exportError}
        purpose={exportPurpose}
        justification={exportJustification}
        includePreviousPregnancies={exportIncludePreviousPregnancies}
        includeEncounters={exportIncludeEncounters}
        blankRows={exportBlankRows}
        setPurpose={setExportPurpose}
        setJustification={setExportJustification}
        setIncludePreviousPregnancies={setExportIncludePreviousPregnancies}
        setIncludeEncounters={setExportIncludeEncounters}
        setBlankRows={setExportBlankRows}
        onClose={() => setExportOpen(false)}
        onSubmit={handleExportPdf}
      />
    </div>
  );
}
