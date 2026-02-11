// clinic-app/src/app/maternity/page.tsx
'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import {
  maternityService,
  MaternityDeliveryResponse,
  PostnatalNoteResponse,
  FamilyPlanningEventResponse,
} from '@/domains/maternity/services/maternityService';
import { VisitResponse } from '@/shared/types';
import { userService, Doctor } from '@/domains/user/services/userService';
import { visitService } from '@/domains/visit/services/visitService';

const formatDate = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : '—';

export default function MaternityPage() {
  const [queue, setQueue] = useState<VisitResponse[]>([]);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [selectedVisit, setSelectedVisit] = useState<VisitResponse | null>(null);

  const [delivery, setDelivery] = useState<MaternityDeliveryResponse | null>(null);
  const [deliveryLoading, setDeliveryLoading] = useState(false);
  const [reassignLoading, setReassignLoading] = useState(false);
  const [reassignError, setReassignError] = useState<string | null>(null);
  const [showReassignPanel, setShowReassignPanel] = useState(false);
  const [assignableMidwives, setAssignableMidwives] = useState<Doctor[]>([]);
  const [selectedOwnerId, setSelectedOwnerId] = useState('');
  const [deliveryForm, setDeliveryForm] = useState({
    delivered_at: '',
    mode_of_delivery: 'UNKNOWN',
    outcome: 'UNKNOWN',
    baby_sex: 'UNKNOWN',
    baby_weight_kg: '',
    apgar_1: '',
    apgar_5: '',
    maternal_complications: '',
    newborn_complications: '',
    notes: '',
  });

  const [postnatalNotes, setPostnatalNotes] = useState<PostnatalNoteResponse[]>([]);
  const [postnatalSubject, setPostnatalSubject] = useState<'MOTHER' | 'BABY'>('MOTHER');
  const [postnatalNote, setPostnatalNote] = useState('');

  const [familyPlanningEvents, setFamilyPlanningEvents] = useState<FamilyPlanningEventResponse[]>([]);
  const [fpCommodity, setFpCommodity] = useState<'IMPLANT' | 'IUD' | 'INJECTABLE' | 'PILL' | 'CONDOM' | 'OTHER'>('IMPLANT');
  const [fpNotes, setFpNotes] = useState('');

  const loadQueue = async (preserveVisitId?: string) => {
    try {
      setLoadingQueue(true);
      setQueueError(null);
      const data = await maternityService.getQueue();
      setQueue(data);
      if (preserveVisitId) {
        const stillAssigned = data.find((v) => v.id === preserveVisitId) || null;
        setSelectedVisit(stillAssigned);
      }
    } catch (err: any) {
      console.error('Maternity queue load failed', err);
      setQueueError('Unable to load maternity queue. Please try again.');
    } finally {
      setLoadingQueue(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  useEffect(() => {
    const loadWorkspace = async () => {
      if (!selectedVisit) {
        setDelivery(null);
        setPostnatalNotes([]);
        setFamilyPlanningEvents([]);
        return;
      }
      try {
        setDeliveryLoading(true);
        const record = await maternityService.getDelivery(selectedVisit.id);
        setDelivery(record);
        if (record) {
          setDeliveryForm({
            delivered_at: record.delivered_at ?? '',
            mode_of_delivery: record.mode_of_delivery ?? 'UNKNOWN',
            outcome: record.outcome ?? 'UNKNOWN',
            baby_sex: record.baby_sex ?? 'UNKNOWN',
            baby_weight_kg: record.baby_weight_kg?.toString() ?? '',
            apgar_1: record.apgar_1?.toString() ?? '',
            apgar_5: record.apgar_5?.toString() ?? '',
            maternal_complications: record.maternal_complications ?? '',
            newborn_complications: record.newborn_complications ?? '',
            notes: record.notes ?? '',
          });
        }
        const notes = await maternityService.listPostnatalNotes(selectedVisit.id);
        setPostnatalNotes(notes);
        const events = await maternityService.listFamilyPlanningEvents(selectedVisit.id);
        setFamilyPlanningEvents(events);
      } catch (err) {
        console.error('Maternity workspace load failed', err);
      } finally {
        setDeliveryLoading(false);
      }
    };

    loadWorkspace();
  }, [selectedVisit?.id]);

  useEffect(() => {
    const loadAssignableMidwives = async () => {
      try {
        const staff = await userService.listAssignableStaff();
        const midwives = staff.filter((member) => member.role === 'MIDWIFE');
        setAssignableMidwives(midwives);
        if (selectedVisit) {
          const fallback =
            midwives.find((member) => member.id !== selectedVisit.assigned_doctor_id)
              ?.id ?? '';
          setSelectedOwnerId(fallback);
        }
      } catch {
        setAssignableMidwives([]);
      }
    };
    loadAssignableMidwives();
  }, [selectedVisit?.id, selectedVisit?.assigned_doctor_id]);

  useEffect(() => {
    if (!selectedVisit) {
      setShowReassignPanel(false);
      setReassignError(null);
    }
  }, [selectedVisit]);

  const handleSaveDelivery = async (action: 'SAVE_DRAFT' | 'SIGN') => {
    if (!selectedVisit) return;
    const payload = {
      action,
      delivered_at: deliveryForm.delivered_at || undefined,
      mode_of_delivery: deliveryForm.mode_of_delivery as any,
      outcome: deliveryForm.outcome as any,
      baby_sex: deliveryForm.baby_sex as any,
      baby_weight_kg: deliveryForm.baby_weight_kg ? Number(deliveryForm.baby_weight_kg) : undefined,
      apgar_1: deliveryForm.apgar_1 ? Number(deliveryForm.apgar_1) : undefined,
      apgar_5: deliveryForm.apgar_5 ? Number(deliveryForm.apgar_5) : undefined,
      maternal_complications: deliveryForm.maternal_complications || undefined,
      newborn_complications: deliveryForm.newborn_complications || undefined,
      notes: deliveryForm.notes || undefined,
    };
    const record = await maternityService.upsertDelivery(selectedVisit.id, payload);
    setDelivery(record);
  };

  const handleAddPostnatalNote = async () => {
    if (!selectedVisit || !postnatalNote.trim()) return;
    const note = await maternityService.addPostnatalNote(selectedVisit.id, {
      subject: postnatalSubject,
      note: postnatalNote.trim(),
    });
    setPostnatalNotes((prev) => [note, ...prev]);
    setPostnatalNote('');
  };

  const handleAddFamilyPlanning = async () => {
    if (!selectedVisit) return;
    const event = await maternityService.addFamilyPlanningEvent(selectedVisit.id, {
      commodity: fpCommodity,
      notes: fpNotes.trim() || undefined,
    });
    setFamilyPlanningEvents((prev) => [event, ...prev]);
    setFpNotes('');
  };

  const handleReassignVisit = async () => {
    if (!selectedVisit || !selectedOwnerId || reassignLoading) return;
    try {
      setReassignLoading(true);
      setReassignError(null);
      const updated = await visitService.reassignOwner(selectedVisit.id, {
        assigned_doctor_id: selectedOwnerId,
        expected_version: selectedVisit.version,
        reason: 'Maternity colleague handover',
      });
      await loadQueue(updated.id);
      setSelectedVisit((prev) =>
        prev && prev.id === updated.id ? updated : prev
      );
      setShowReassignPanel(false);
    } catch (err: any) {
      setReassignError(
        err?.response?.data?.detail ||
          'Unable to reassign this maternity visit.'
      );
    } finally {
      setReassignLoading(false);
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
          <h1 className="text-2xl font-semibold text-gray-900">Maternity Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">
            Delivery record, postnatal notes, and family planning events.
          </p>
        </div>
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
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Maternity Queue" titleClassName="text-[#0B4DA2]">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-gray-500">{queue.length} patients</div>
            <Button size="sm" variant="secondary" onClick={loadQueue} disabled={loadingQueue}>
              {loadingQueue ? 'Refreshing...' : 'Refresh'}
            </Button>
          </div>
          {queueError && <p className="text-sm text-red-600">{queueError}</p>}
          {!queueError && queue.length === 0 && (
            <p className="text-sm text-gray-500">No maternity visits assigned.</p>
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
          {showReassignPanel && (
            <Card title="Reassign Maternity Owner" titleClassName="text-[#0B4DA2]">
              <div className="text-sm text-gray-600 mb-3">{selectedHeader}</div>
              {selectedVisit && (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                  <div className="text-xs text-slate-600">
                    Current owner:{' '}
                    <span className="font-medium text-slate-800">
                      {assignableMidwives.find(
                        (member) => member.id === selectedVisit.assigned_doctor_id
                      )?.full_name || 'Assigned Midwife'}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-col gap-2 md:flex-row md:items-center">
                    <select
                      value={selectedOwnerId}
                      onChange={(e) => setSelectedOwnerId(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm md:max-w-xs"
                      disabled={reassignLoading}
                    >
                      <option value="">Select Midwife</option>
                      {assignableMidwives.map((member) => (
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

          <Card title="Delivery Record" titleClassName="text-[#0B4DA2]">
            <div className="text-sm text-gray-600 mb-4">{selectedHeader}</div>
            {deliveryLoading && <p className="text-sm text-gray-500">Loading delivery record...</p>}
            {!selectedVisit && (
              <p className="text-sm text-gray-500">Select a visit to capture delivery details.</p>
            )}
            {selectedVisit && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Delivered At"
                  type="datetime-local"
                  value={deliveryForm.delivered_at}
                  onChange={(e) =>
                    setDeliveryForm((prev) => ({ ...prev, delivered_at: e.target.value }))
                  }
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Mode of Delivery</label>
                  <select
                    value={deliveryForm.mode_of_delivery}
                    onChange={(e) =>
                      setDeliveryForm((prev) => ({ ...prev, mode_of_delivery: e.target.value }))
                    }
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="UNKNOWN">Unknown</option>
                    <option value="SVD">SVD</option>
                    <option value="C_SECTION">C-Section</option>
                    <option value="ASSISTED">Assisted</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Outcome</label>
                  <select
                    value={deliveryForm.outcome}
                    onChange={(e) =>
                      setDeliveryForm((prev) => ({ ...prev, outcome: e.target.value }))
                    }
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="UNKNOWN">Unknown</option>
                    <option value="LIVE_BIRTH">Live birth</option>
                    <option value="STILLBIRTH">Stillbirth</option>
                    <option value="NEONATAL_DEATH">Neonatal death</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Baby Sex</label>
                  <select
                    value={deliveryForm.baby_sex}
                    onChange={(e) =>
                      setDeliveryForm((prev) => ({ ...prev, baby_sex: e.target.value }))
                    }
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="UNKNOWN">Unknown</option>
                    <option value="MALE">Male</option>
                    <option value="FEMALE">Female</option>
                  </select>
                </div>
                <Input
                  label="Baby Weight (kg)"
                  value={deliveryForm.baby_weight_kg}
                  onChange={(e) =>
                    setDeliveryForm((prev) => ({ ...prev, baby_weight_kg: e.target.value }))
                  }
                />
                <Input
                  label="APGAR 1"
                  value={deliveryForm.apgar_1}
                  onChange={(e) =>
                    setDeliveryForm((prev) => ({ ...prev, apgar_1: e.target.value }))
                  }
                />
                <Input
                  label="APGAR 5"
                  value={deliveryForm.apgar_5}
                  onChange={(e) =>
                    setDeliveryForm((prev) => ({ ...prev, apgar_5: e.target.value }))
                  }
                />
                <Input
                  label="Maternal Complications"
                  value={deliveryForm.maternal_complications}
                  onChange={(e) =>
                    setDeliveryForm((prev) => ({
                      ...prev,
                      maternal_complications: e.target.value,
                    }))
                  }
                />
                <Input
                  label="Newborn Complications"
                  value={deliveryForm.newborn_complications}
                  onChange={(e) =>
                    setDeliveryForm((prev) => ({
                      ...prev,
                      newborn_complications: e.target.value,
                    }))
                  }
                />
                <Input
                  label="Notes"
                  value={deliveryForm.notes}
                  onChange={(e) =>
                    setDeliveryForm((prev) => ({ ...prev, notes: e.target.value }))
                  }
                />
              </div>
            )}
            {selectedVisit && (
              <div className="mt-4 flex items-center gap-3">
                <Button variant="secondary" onClick={() => handleSaveDelivery('SAVE_DRAFT')}>
                  Save Draft
                </Button>
                <Button onClick={() => handleSaveDelivery('SIGN')}>Sign Delivery</Button>
                {delivery && (
                  <span className="text-xs text-gray-500">
                    Status: {delivery.record_status}
                  </span>
                )}
              </div>
            )}
          </Card>

          <Card title="Postnatal Notes" titleClassName="text-[#0B4DA2]">
            {!selectedVisit && (
              <p className="text-sm text-gray-500">Select a visit to add postnatal notes.</p>
            )}
            {selectedVisit && (
              <div className="space-y-3">
                <div className="flex flex-col md:flex-row gap-3">
                  <select
                    value={postnatalSubject}
                    onChange={(e) => setPostnatalSubject(e.target.value as any)}
                    className="border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="MOTHER">Mother</option>
                    <option value="BABY">Baby</option>
                  </select>
                  <Input
                    label="Note"
                    value={postnatalNote}
                    onChange={(e) => setPostnatalNote(e.target.value)}
                  />
                  <Button onClick={handleAddPostnatalNote}>Add</Button>
                </div>
                <div className="space-y-2">
                  {postnatalNotes.length === 0 && (
                    <p className="text-sm text-gray-500">No notes recorded.</p>
                  )}
                  {postnatalNotes.map((note) => (
                    <div key={note.id} className="p-3 border rounded-md">
                      <div className="text-xs text-gray-500">
                        {note.subject} • {formatDate(note.added_at)}
                      </div>
                      <div className="text-sm text-gray-900 mt-1">{note.note}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          <Card title="Family Planning" titleClassName="text-[#0B4DA2]">
            {!selectedVisit && (
              <p className="text-sm text-gray-500">Select a visit to record family planning.</p>
            )}
            {selectedVisit && (
              <div className="space-y-3">
                <div className="flex flex-col md:flex-row gap-3">
                  <select
                    value={fpCommodity}
                    onChange={(e) => setFpCommodity(e.target.value as any)}
                    className="border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="IMPLANT">Implant</option>
                    <option value="IUD">IUD</option>
                    <option value="INJECTABLE">Injectable</option>
                    <option value="PILL">Pill</option>
                    <option value="CONDOM">Condom</option>
                    <option value="OTHER">Other</option>
                  </select>
                  <Input
                    label="Notes"
                    value={fpNotes}
                    onChange={(e) => setFpNotes(e.target.value)}
                  />
                  <Button onClick={handleAddFamilyPlanning}>Add</Button>
                </div>
                <div className="space-y-2">
                  {familyPlanningEvents.length === 0 && (
                    <p className="text-sm text-gray-500">No family planning events.</p>
                  )}
                  {familyPlanningEvents.map((event) => (
                    <div key={event.id} className="p-3 border rounded-md">
                      <div className="text-xs text-gray-500">
                        {event.commodity} • {formatDate(event.added_at)}
                      </div>
                      {event.notes && (
                        <div className="text-sm text-gray-900 mt-1">{event.notes}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
