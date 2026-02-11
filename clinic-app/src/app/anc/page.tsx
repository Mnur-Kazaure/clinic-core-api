// clinic-app/src/app/anc/page.tsx
'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import {
  ancService,
  ANCEncounterResponse,
  PregnancyEpisodeResponse,
  PreviousPregnancyResponse,
} from '@/domains/anc/services/ancService';
import { VisitResponse } from '@/shared/types';
import { PurposeOfUse, VisitServiceLine } from '@/shared/enums';
import { userService, Doctor } from '@/domains/user/services/userService';
import { visitService } from '@/domains/visit/services/visitService';

const formatDate = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : '—';

const exportPurposeOptions: Array<{ value: PurposeOfUse; label: string }> = [
  { value: PurposeOfUse.TREATMENT, label: 'Treatment' },
  { value: PurposeOfUse.OPERATIONS, label: 'Operations' },
  { value: PurposeOfUse.EMERGENCY, label: 'Emergency' },
  { value: PurposeOfUse.AUDIT, label: 'Audit' },
  { value: PurposeOfUse.BILLING, label: 'Billing' },
  { value: PurposeOfUse.SECURITY, label: 'Security' },
];

export default function ANCPage() {
  const [queue, setQueue] = useState<VisitResponse[]>([]);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [selectedVisit, setSelectedVisit] = useState<VisitResponse | null>(null);

  const [episode, setEpisode] = useState<PregnancyEpisodeResponse | null>(null);
  const [episodeLoading, setEpisodeLoading] = useState(false);
  const [episodeError, setEpisodeError] = useState<string | null>(null);

  const [encounter, setEncounter] = useState<ANCEncounterResponse | null>(null);
  const [encounterSaving, setEncounterSaving] = useState(false);
  const [reassignLoading, setReassignLoading] = useState(false);
  const [reassignError, setReassignError] = useState<string | null>(null);
  const [showReassignPanel, setShowReassignPanel] = useState(false);
  const [assignableChews, setAssignableChews] = useState<Doctor[]>([]);
  const [assignableMidwives, setAssignableMidwives] = useState<Doctor[]>([]);
  const [selectedOwnerId, setSelectedOwnerId] = useState('');
  const [selectedMidwifeId, setSelectedMidwifeId] = useState('');
  const [sendLoading, setSendLoading] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [showSendPanel, setShowSendPanel] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportPurpose, setExportPurpose] = useState<PurposeOfUse>(
    PurposeOfUse.TREATMENT
  );
  const [exportJustification, setExportJustification] = useState('');
  const [exportIncludePreviousPregnancies, setExportIncludePreviousPregnancies] =
    useState(true);
  const [exportIncludeEncounters, setExportIncludeEncounters] = useState(true);
  const [exportBlankRows, setExportBlankRows] = useState('0');
  const [previousPregnancies, setPreviousPregnancies] = useState<PreviousPregnancyResponse[]>([]);
  const [prevForm, setPrevForm] = useState({
    year: '',
    duration: '',
    antenatal_complications: '',
    labour: '',
    age_alive: '',
    age_dead: '',
    cause_of_death: '',
  });

  const [episodeForm, setEpisodeForm] = useState({
    lmp_date: '',
    edd_date: '',
    gravida: '',
    parity: '',
    booking_reg_no: '',
    past_medical_history: '',
    past_surgical_history: '',
    history_present_pregnancy: '',
    general_exam: '',
  });

  const [encounterForm, setEncounterForm] = useState({
    fundus_height: '',
    presentation_position: '',
    presenting_part: '',
    foetal_heart: '',
    bp_systolic: '',
    bp_diastolic: '',
    urine: '',
    weight_kg: '',
    remarks: '',
    ref: '',
    initial: '',
  });

  const selectedPatientId = selectedVisit?.patient_id ?? null;

  const extractErrorDetail = (err: unknown, fallback: string) => {
    const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
      ?.data?.detail;
    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail;
    }
    return fallback;
  };

  const loadQueue = async (preserveVisitId?: string) => {
    try {
      setLoadingQueue(true);
      setQueueError(null);
      const data = await ancService.getQueue();
      setQueue(data);
      if (preserveVisitId) {
        const stillAssigned = data.find((v) => v.id === preserveVisitId) || null;
        setSelectedVisit(stillAssigned);
      }
    } catch (err: any) {
      console.error('ANC queue load failed', err);
      setQueueError('Unable to load ANC queue. Please try again.');
    } finally {
      setLoadingQueue(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  useEffect(() => {
    const loadEpisode = async () => {
      if (!selectedPatientId) {
        setEpisode(null);
        setEncounter(null);
        return;
      }
      try {
        setEpisodeLoading(true);
        setEpisodeError(null);
        const active = await ancService.getActiveEpisode(selectedPatientId);
        setEpisode(active);
        if (active) {
          setEpisodeForm({
            lmp_date: active.lmp_date ?? '',
            edd_date: active.edd_date ?? '',
            gravida: active.gravida?.toString() ?? '',
            parity: active.parity?.toString() ?? '',
            booking_reg_no: active.booking_reg_no ?? '',
            past_medical_history: active.past_medical_history ?? '',
            past_surgical_history: active.past_surgical_history ?? '',
            history_present_pregnancy: active.history_present_pregnancy ?? '',
            general_exam: active.general_exam ?? '',
          });
        }
        if (active) {
          const prev = await ancService.listPreviousPregnancies(active.id);
          setPreviousPregnancies(prev);
        } else {
          setPreviousPregnancies([]);
        }
        if (selectedVisit) {
          const enc = await ancService.getEncounter(selectedVisit.id);
          setEncounter(enc);
          if (enc) {
            setEncounterForm({
              fundus_height: enc.fundus_height ?? '',
              presentation_position: enc.presentation_position ?? '',
              presenting_part: enc.presenting_part ?? '',
              foetal_heart: enc.foetal_heart ?? '',
              bp_systolic: enc.bp_systolic?.toString() ?? '',
              bp_diastolic: enc.bp_diastolic?.toString() ?? '',
              urine: enc.urine ?? '',
              weight_kg: enc.weight_kg?.toString() ?? '',
              remarks: enc.remarks ?? '',
              ref: enc.ref ?? '',
              initial: enc.initial ?? '',
            });
          } else {
            setEncounterForm({
              fundus_height: '',
              presentation_position: '',
              presenting_part: '',
              foetal_heart: '',
              bp_systolic: '',
              bp_diastolic: '',
              urine: '',
              weight_kg: '',
              remarks: '',
              ref: '',
              initial: '',
            });
          }
        }
      } catch (err: unknown) {
        console.error('ANC episode load failed', err);
        setEpisodeError(
          extractErrorDetail(err, 'Unable to load ANC episode. Please try again.')
        );
      } finally {
        setEpisodeLoading(false);
      }
    };

    loadEpisode();
  }, [selectedPatientId, selectedVisit?.id]);

  useEffect(() => {
    const loadAssignableStaff = async () => {
      try {
        const staff = await userService.listAssignableStaff();
        const chews = staff.filter((member) => member.role === 'CHEW');
        const midwives = staff.filter((member) => member.role === 'MIDWIFE');
        setAssignableChews(chews);
        setAssignableMidwives(midwives);
        if (selectedVisit) {
          const chewFallback =
            chews.find((member) => member.id !== selectedVisit.assigned_doctor_id)
              ?.id ?? '';
          const midwifeFallback = midwives[0]?.id ?? '';
          setSelectedOwnerId(chewFallback);
          setSelectedMidwifeId(midwifeFallback);
        }
      } catch {
        setAssignableChews([]);
        setAssignableMidwives([]);
      }
    };
    loadAssignableStaff();
  }, [selectedVisit?.id, selectedVisit?.assigned_doctor_id]);

  useEffect(() => {
    if (!selectedVisit) {
      setShowReassignPanel(false);
      setReassignError(null);
      setShowSendPanel(false);
      setSendError(null);
      setShowExportModal(false);
      setExportError(null);
    }
  }, [selectedVisit]);

  useEffect(() => {
    if (!showExportModal) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !exporting) {
        setShowExportModal(false);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [showExportModal, exporting]);

  const handleAddPreviousPregnancy = async () => {
    if (!episode) return;
    const payload = {
      year: prevForm.year ? Number(prevForm.year) : undefined,
      duration: prevForm.duration || undefined,
      antenatal_complications: prevForm.antenatal_complications || undefined,
      labour: prevForm.labour || undefined,
      age_alive: prevForm.age_alive || undefined,
      age_dead: prevForm.age_dead || undefined,
      cause_of_death: prevForm.cause_of_death || undefined,
    };
    const created = await ancService.addPreviousPregnancy(episode.id, payload);
    setPreviousPregnancies((prev) => [created, ...prev]);
    setPrevForm({
      year: '',
      duration: '',
      antenatal_complications: '',
      labour: '',
      age_alive: '',
      age_dead: '',
      cause_of_death: '',
    });
  };

  const handleCreateEpisode = async () => {
    if (!selectedPatientId) return;
    try {
      setEpisodeLoading(true);
      const payload = {
        lmp_date: episodeForm.lmp_date || undefined,
        edd_date: episodeForm.edd_date || undefined,
        gravida: episodeForm.gravida ? Number(episodeForm.gravida) : undefined,
        parity: episodeForm.parity ? Number(episodeForm.parity) : undefined,
        booking_reg_no: episodeForm.booking_reg_no || undefined,
        past_medical_history: episodeForm.past_medical_history || undefined,
        past_surgical_history: episodeForm.past_surgical_history || undefined,
        history_present_pregnancy: episodeForm.history_present_pregnancy || undefined,
        general_exam: episodeForm.general_exam || undefined,
      };
      const created = await ancService.createEpisode(selectedPatientId, payload);
      setEpisode(created);
    } catch (err: any) {
      console.error('ANC episode create failed', err);
      setEpisodeError(err?.response?.data?.detail || 'Unable to create episode.');
    } finally {
      setEpisodeLoading(false);
    }
  };

  const handleSaveEncounter = async (action: 'SAVE_DRAFT' | 'SIGN') => {
    if (!selectedVisit || !episode) return;
    try {
      setEncounterSaving(true);
      const payload = {
        action,
        episode_id: episode.id,
        fundus_height: encounterForm.fundus_height || undefined,
        presentation_position: encounterForm.presentation_position || undefined,
        presenting_part: encounterForm.presenting_part || undefined,
        foetal_heart: encounterForm.foetal_heart || undefined,
        bp_systolic: encounterForm.bp_systolic ? Number(encounterForm.bp_systolic) : undefined,
        bp_diastolic: encounterForm.bp_diastolic ? Number(encounterForm.bp_diastolic) : undefined,
        urine: encounterForm.urine || undefined,
        weight_kg: encounterForm.weight_kg ? Number(encounterForm.weight_kg) : undefined,
        remarks: encounterForm.remarks || undefined,
        ref: encounterForm.ref || undefined,
        initial: encounterForm.initial || undefined,
      };
      const updated = await ancService.upsertEncounter(selectedVisit.id, payload);
      setEncounter(updated);
    } catch (err: any) {
      console.error('ANC encounter save failed', err);
    } finally {
      setEncounterSaving(false);
    }
  };

  const handleReassignVisit = async () => {
    if (!selectedVisit || !selectedOwnerId || reassignLoading) return;
    try {
      setReassignLoading(true);
      setReassignError(null);
      const updated = await visitService.reassignOwner(selectedVisit.id, {
        assigned_doctor_id: selectedOwnerId,
        expected_version: selectedVisit.version,
        reason: 'ANC colleague handover',
      });
      await loadQueue(updated.id);
      setSelectedVisit((prev) =>
        prev && prev.id === updated.id ? updated : prev
      );
      setShowReassignPanel(false);
    } catch (err: any) {
      setReassignError(
        err?.response?.data?.detail || 'Unable to reassign this ANC visit.'
      );
    } finally {
      setReassignLoading(false);
    }
  };

  const handleSendToMaternity = async () => {
    if (!selectedVisit || !selectedMidwifeId || sendLoading) return;
    try {
      setSendLoading(true);
      setSendError(null);
      const updated = await visitService.reassignOwner(selectedVisit.id, {
        assigned_doctor_id: selectedMidwifeId,
        expected_version: selectedVisit.version,
        service_line: VisitServiceLine.MATERNITY,
        reason: 'ANC handover to maternity',
      });
      await loadQueue(updated.id);
      setSelectedVisit((prev) =>
        prev && prev.id === updated.id ? updated : prev
      );
      setShowSendPanel(false);
    } catch (err: any) {
      setSendError(
        err?.response?.data?.detail || 'Unable to send this visit to maternity.'
      );
    } finally {
      setSendLoading(false);
    }
  };

  const handleExportPdf = async () => {
    if (!episode || exporting) return;

    const trimmedJustification = exportJustification.trim();
    if (trimmedJustification.length < 2) {
      setExportError('Justification must be at least 2 characters.');
      return;
    }

    try {
      setExporting(true);
      setExportError(null);
      const pdfBlob = await ancService.exportEpisodePdf(episode.id, {
        purpose_of_use: exportPurpose,
        justification: trimmedJustification,
        include_previous_pregnancies: exportIncludePreviousPregnancies,
        include_encounters: exportIncludeEncounters,
        include_blank_rows: Number.isNaN(Number(exportBlankRows))
          ? 0
          : Math.max(0, Math.min(Number(exportBlankRows), 20)),
      });
      const blobUrl = window.URL.createObjectURL(pdfBlob);
      const opened = window.open(blobUrl, '_blank', 'noopener,noreferrer');
      if (!opened) {
        setExportError('Popup blocked. Please allow popups and retry.');
        window.URL.revokeObjectURL(blobUrl);
        return;
      }
      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60_000);
      setShowExportModal(false);
    } catch (err: any) {
      const statusCode = err?.response?.status;
      if (statusCode === 403) {
        setExportError('Not authorized to export this ANC record.');
        return;
      }
      if (statusCode === 400 || statusCode === 422) {
        const detail = err?.response?.data?.detail;
        setExportError(
          typeof detail === 'string' && detail.trim().length > 0
            ? detail
            : 'Validation failed. Check purpose and justification.'
        );
        return;
      }
      setExportError('Export failed. Retry.');
    } finally {
      setExporting(false);
    }
  };

  const selectedHeader = useMemo(() => {
    if (!selectedVisit) return 'Select a patient from the queue';
    return `${selectedVisit.patient_name ?? 'Patient'} • MRN ${
      selectedVisit.patient_mrn ?? '—'
    }`;
  }, [selectedVisit]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">ANC Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">
            ANC queue, pregnancy episode header, and encounter entry.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={!episode}
            onClick={() => {
              setExportError(null);
              setShowExportModal(true);
            }}
          >
            Export PDF
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={!selectedVisit}
            onClick={() => {
              setReassignError(null);
              setShowReassignPanel((prev) => !prev);
            }}
          >
            {showReassignPanel ? 'Hide Reassignment' : 'Reassign Owner'}
          </Button>
          <Button
            size="sm"
            disabled={!selectedVisit}
            onClick={() => {
              setSendError(null);
              setShowSendPanel((prev) => !prev);
            }}
          >
            {showSendPanel ? 'Hide Send Panel' : 'Send to Maternity'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="ANC Queue" titleClassName="text-[#0B4DA2]">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-gray-500">{queue.length} patients</div>
            <Button size="sm" variant="secondary" onClick={loadQueue} disabled={loadingQueue}>
              {loadingQueue ? 'Refreshing...' : 'Refresh'}
            </Button>
          </div>
          {queueError && (
            <p className="text-sm text-red-600">{queueError}</p>
          )}
          {!queueError && queue.length === 0 && (
            <p className="text-sm text-gray-500">No ANC visits assigned.</p>
          )}
          <div className="space-y-2">
            {queue.map((visit) => (
              <button
                key={visit.id}
                onClick={() => setSelectedVisit(visit)}
                className={`w-full text-left p-3 rounded-lg border ${
                  selectedVisit?.id === visit.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="font-medium text-gray-900">
                  {visit.patient_name ?? 'Unknown patient'}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  MRN {visit.patient_mrn ?? '—'} • {visit.status}
                </div>
              </button>
            ))}
          </div>
        </Card>

        <div className="lg:col-span-2 space-y-6">
          {showSendPanel && (
            <Card title="Send Visit to Maternity" titleClassName="text-[#0B4DA2]">
              <div className="text-sm text-gray-600 mb-3">{selectedHeader}</div>
              {selectedVisit && (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                  <div className="mt-2 flex flex-col gap-2 md:flex-row md:items-center">
                    <select
                      value={selectedMidwifeId}
                      onChange={(e) => setSelectedMidwifeId(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm md:max-w-xs"
                      disabled={sendLoading}
                    >
                      <option value="">Select Midwife</option>
                      {assignableMidwives.map((member) => (
                        <option key={member.id} value={member.id}>
                          {member.full_name || member.email}
                        </option>
                      ))}
                    </select>
                    <Button
                      onClick={handleSendToMaternity}
                      disabled={!selectedMidwifeId || sendLoading}
                      isLoading={sendLoading}
                    >
                      Confirm Send
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => setShowSendPanel(false)}
                      disabled={sendLoading}
                    >
                      Cancel
                    </Button>
                  </div>
                  {sendError && (
                    <p className="mt-2 text-xs text-red-600">{sendError}</p>
                  )}
                </div>
              )}
            </Card>
          )}

          {showReassignPanel && (
            <Card title="Reassign ANC Owner" titleClassName="text-[#0B4DA2]">
              <div className="text-sm text-gray-600 mb-3">{selectedHeader}</div>
              {selectedVisit && (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                  <div className="text-xs text-slate-600">
                    Current owner:{' '}
                    <span className="font-medium text-slate-800">
                      {assignableChews.find(
                        (member) => member.id === selectedVisit.assigned_doctor_id
                      )?.full_name || 'Assigned CHEW'}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-col gap-2 md:flex-row md:items-center">
                    <select
                      value={selectedOwnerId}
                      onChange={(e) => setSelectedOwnerId(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm md:max-w-xs"
                      disabled={reassignLoading}
                    >
                      <option value="">Select CHEW</option>
                      {assignableChews.map((member) => (
                        <option key={member.id} value={member.id}>
                          {member.full_name || member.email}
                        </option>
                      ))}
                    </select>
                    <Button
                      variant="secondary"
                      onClick={handleReassignVisit}
                      disabled={!selectedOwnerId || reassignLoading}
                      isLoading={reassignLoading}
                    >
                      Reassign
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => setShowReassignPanel(false)}
                      disabled={reassignLoading}
                    >
                      Cancel
                    </Button>
                  </div>
                  {reassignError && (
                    <p className="mt-2 text-xs text-red-600">{reassignError}</p>
                  )}
                </div>
              )}
            </Card>
          )}

          <Card title="Episode" titleClassName="text-[#0B4DA2]">
            <div className="text-sm text-gray-600 mb-4">{selectedHeader}</div>
            {episodeError && <p className="text-sm text-red-600">{episodeError}</p>}
            {episodeLoading && <p className="text-sm text-gray-500">Loading episode...</p>}
            {!selectedVisit && (
              <p className="text-sm text-gray-500">Select a visit to manage ANC data.</p>
            )}
            {selectedVisit && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="LMP"
                  type="date"
                  value={episodeForm.lmp_date}
                  onChange={(e) =>
                    setEpisodeForm((prev) => ({ ...prev, lmp_date: e.target.value }))
                  }
                />
                <Input
                  label="EDD"
                  type="date"
                  value={episodeForm.edd_date}
                  onChange={(e) =>
                    setEpisodeForm((prev) => ({ ...prev, edd_date: e.target.value }))
                  }
                />
                <Input
                  label="Gravida"
                  value={episodeForm.gravida}
                  onChange={(e) =>
                    setEpisodeForm((prev) => ({ ...prev, gravida: e.target.value }))
                  }
                />
                <Input
                  label="Parity"
                  value={episodeForm.parity}
                  onChange={(e) =>
                    setEpisodeForm((prev) => ({ ...prev, parity: e.target.value }))
                  }
                />
                <Input
                  label="Booking Reg No"
                  value={episodeForm.booking_reg_no}
                  onChange={(e) =>
                    setEpisodeForm((prev) => ({ ...prev, booking_reg_no: e.target.value }))
                  }
                />
                <Input
                  label="Past Medical History"
                  value={episodeForm.past_medical_history}
                  onChange={(e) =>
                    setEpisodeForm((prev) => ({
                      ...prev,
                      past_medical_history: e.target.value,
                    }))
                  }
                />
                <Input
                  label="Past Surgical History"
                  value={episodeForm.past_surgical_history}
                  onChange={(e) =>
                    setEpisodeForm((prev) => ({
                      ...prev,
                      past_surgical_history: e.target.value,
                    }))
                  }
                />
                <Input
                  label="History of Present Pregnancy"
                  value={episodeForm.history_present_pregnancy}
                  onChange={(e) =>
                    setEpisodeForm((prev) => ({
                      ...prev,
                      history_present_pregnancy: e.target.value,
                    }))
                  }
                />
                <Input
                  label="General Exam"
                  value={episodeForm.general_exam}
                  onChange={(e) =>
                    setEpisodeForm((prev) => ({
                      ...prev,
                      general_exam: e.target.value,
                    }))
                  }
                />
              </div>
            )}
            {selectedVisit && (
              <div className="mt-4 flex items-center gap-3">
                <Button
                  onClick={handleCreateEpisode}
                  disabled={episodeLoading}
                >
                  {episode ? 'Update Episode' : 'Start Episode'}
                </Button>
                {episode && (
                  <span className="text-xs text-gray-500">
                    Active since {formatDate(episode.created_at)}
                  </span>
                )}
              </div>
            )}
          </Card>

          <Card title="ANC Encounter" titleClassName="text-[#0B4DA2]">
            {!selectedVisit && (
              <p className="text-sm text-gray-500">Select a visit to enter ANC encounter.</p>
            )}
            {selectedVisit && !episode && (
              <p className="text-sm text-gray-500">Start an episode to record encounters.</p>
            )}
            {selectedVisit && episode && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Fundus Height"
                    value={encounterForm.fundus_height}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({
                        ...prev,
                        fundus_height: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="Presentation / Position"
                    value={encounterForm.presentation_position}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({
                        ...prev,
                        presentation_position: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="Presenting Part"
                    value={encounterForm.presenting_part}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({
                        ...prev,
                        presenting_part: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="Foetal Heart"
                    value={encounterForm.foetal_heart}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({
                        ...prev,
                        foetal_heart: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="BP Systolic"
                    value={encounterForm.bp_systolic}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({
                        ...prev,
                        bp_systolic: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="BP Diastolic"
                    value={encounterForm.bp_diastolic}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({
                        ...prev,
                        bp_diastolic: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="Urine"
                    value={encounterForm.urine}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({ ...prev, urine: e.target.value }))
                    }
                  />
                  <Input
                    label="Weight (kg)"
                    value={encounterForm.weight_kg}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({
                        ...prev,
                        weight_kg: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="Remarks"
                    value={encounterForm.remarks}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({
                        ...prev,
                        remarks: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="Ref"
                    value={encounterForm.ref}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({ ...prev, ref: e.target.value }))
                    }
                  />
                  <Input
                    label="Initial"
                    value={encounterForm.initial}
                    onChange={(e) =>
                      setEncounterForm((prev) => ({
                        ...prev,
                        initial: e.target.value,
                      }))
                    }
                  />
                </div>
                <div className="flex items-center gap-3">
                  <Button
                    variant="secondary"
                    onClick={() => handleSaveEncounter('SAVE_DRAFT')}
                    disabled={encounterSaving}
                  >
                    Save Draft
                  </Button>
                  <Button
                    onClick={() => handleSaveEncounter('SIGN')}
                    disabled={encounterSaving}
                  >
                    Sign Encounter
                  </Button>
                  {encounter && (
                    <span className="text-xs text-gray-500">
                      Status: {encounter.record_status}
                    </span>
                  )}
                </div>
              </div>
            )}
          </Card>

          <Card title="Previous Pregnancies" titleClassName="text-[#0B4DA2]">
            {!episode && (
              <p className="text-sm text-gray-500">Start an episode to record history.</p>
            )}
            {episode && (
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <Input
                    label="Year"
                    value={prevForm.year}
                    onChange={(e) =>
                      setPrevForm((prev) => ({ ...prev, year: e.target.value }))
                    }
                  />
                  <Input
                    label="Duration"
                    value={prevForm.duration}
                    onChange={(e) =>
                      setPrevForm((prev) => ({ ...prev, duration: e.target.value }))
                    }
                  />
                  <Input
                    label="Complications"
                    value={prevForm.antenatal_complications}
                    onChange={(e) =>
                      setPrevForm((prev) => ({
                        ...prev,
                        antenatal_complications: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="Labour"
                    value={prevForm.labour}
                    onChange={(e) =>
                      setPrevForm((prev) => ({ ...prev, labour: e.target.value }))
                    }
                  />
                  <Input
                    label="Age Alive"
                    value={prevForm.age_alive}
                    onChange={(e) =>
                      setPrevForm((prev) => ({ ...prev, age_alive: e.target.value }))
                    }
                  />
                  <Input
                    label="Age Dead"
                    value={prevForm.age_dead}
                    onChange={(e) =>
                      setPrevForm((prev) => ({ ...prev, age_dead: e.target.value }))
                    }
                  />
                  <Input
                    label="Cause of Death"
                    value={prevForm.cause_of_death}
                    onChange={(e) =>
                      setPrevForm((prev) => ({ ...prev, cause_of_death: e.target.value }))
                    }
                  />
                </div>
                <Button onClick={handleAddPreviousPregnancy} variant="secondary">
                  Add Row
                </Button>
                <div className="space-y-2">
                  {previousPregnancies.length === 0 && (
                    <p className="text-sm text-gray-500">No previous pregnancies recorded.</p>
                  )}
                  {previousPregnancies.map((row) => (
                    <div key={row.id} className="p-3 border rounded-md text-sm text-gray-700">
                      <div className="font-medium text-gray-900">
                        {row.year || 'Year'} • {row.duration || 'Duration'}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Complications: {row.antenatal_complications || '—'} • Labour:{' '}
                        {row.labour || '—'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>

      {showExportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            className="w-full max-w-lg rounded-lg bg-white shadow-xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="anc-export-title"
          >
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 id="anc-export-title" className="text-lg font-semibold text-slate-900">
                Export ANC PDF
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                Purpose and justification are required for audit logging.
              </p>
            </div>
            <div className="space-y-4 px-5 py-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Purpose of Use
                </label>
                <select
                  value={exportPurpose}
                  onChange={(e) => setExportPurpose(e.target.value as PurposeOfUse)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  disabled={exporting}
                  autoFocus
                >
                  {exportPurposeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Justification
                </label>
                <textarea
                  value={exportJustification}
                  onChange={(e) => setExportJustification(e.target.value)}
                  className="min-h-[92px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  placeholder="Enter brief reason (min 2 characters)"
                  disabled={exporting}
                />
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={exportIncludePreviousPregnancies}
                    onChange={(e) =>
                      setExportIncludePreviousPregnancies(e.target.checked)
                    }
                    disabled={exporting}
                  />
                  Include previous pregnancies
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={exportIncludeEncounters}
                    onChange={(e) => setExportIncludeEncounters(e.target.checked)}
                    disabled={exporting}
                  />
                  Include encounters
                </label>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Blank rows (0-20)
                </label>
                <input
                  type="number"
                  min={0}
                  max={20}
                  value={exportBlankRows}
                  onChange={(e) => setExportBlankRows(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm sm:w-40"
                  disabled={exporting}
                />
              </div>

              {exportError && (
                <p className="text-sm text-red-600">{exportError}</p>
              )}
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <Button
                variant="secondary"
                onClick={() => setShowExportModal(false)}
                disabled={exporting}
              >
                Cancel
              </Button>
              <Button onClick={handleExportPdf} isLoading={exporting}>
                Generate PDF
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
