'use client';

import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/shared/Button';
import {
  maternityService,
  MaternityDeliveryResponse,
  PostnatalNoteResponse,
  FamilyPlanningEventResponse,
} from '@/domains/maternity/services/maternityService';
import { VisitResponse } from '@/shared/types';
import { userService, Doctor } from '@/domains/user/services/userService';
import { visitService } from '@/domains/visit/services/visitService';
import { MaternityQueuePanel } from '@/app/maternity/components/MaternityQueuePanel';
import { MaternityOverviewHeader } from '@/app/maternity/components/MaternityOverviewHeader';
import { MaternityHandoverPanel } from '@/app/maternity/components/MaternityHandoverPanel';
import { DeliveryRecordPanel } from '@/app/maternity/components/DeliveryRecordPanel';
import { PostnatalNotesPanel } from '@/app/maternity/components/PostnatalNotesPanel';
import { FamilyPlanningPanel } from '@/app/maternity/components/FamilyPlanningPanel';

export function MaternityDashboard() {
  const [queue, setQueue] = useState<VisitResponse[]>([]);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedVisitId, setSelectedVisitId] = useState<string | null>(null);

  const [delivery, setDelivery] = useState<MaternityDeliveryResponse | null>(null);
  const [deliveryLoading, setDeliveryLoading] = useState(false);
  const [postnatalNotes, setPostnatalNotes] = useState<PostnatalNoteResponse[]>([]);
  const [familyPlanningEvents, setFamilyPlanningEvents] = useState<FamilyPlanningEventResponse[]>([]);

  const [assignableMidwives, setAssignableMidwives] = useState<Doctor[]>([]);
  const [selectedOwnerId, setSelectedOwnerId] = useState('');
  const [reassignLoading, setReassignLoading] = useState(false);
  const [reassignError, setReassignError] = useState<string | null>(null);

  const selectedVisit = useMemo(
    () => queue.find((visit) => visit.id === selectedVisitId) ?? null,
    [queue, selectedVisitId]
  );

  const filteredQueue = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return queue;
    return queue.filter((visit) => {
      const patientName = (visit.patient_name ?? '').toLowerCase();
      const patientMrn = (visit.patient_mrn ?? '').toLowerCase();
      return patientName.includes(term) || patientMrn.includes(term);
    });
  }, [queue, search]);

  const loadQueue = async (preserveVisitId?: string | null) => {
    try {
      setLoadingQueue(true);
      setQueueError(null);
      const data = await maternityService.getQueue();
      setQueue(data);

      const targetId = preserveVisitId ?? selectedVisitId;
      if (!targetId) {
        setSelectedVisitId(data[0]?.id ?? null);
        return;
      }

      const stillExists = data.some((visit) => visit.id === targetId);
      setSelectedVisitId(stillExists ? targetId : data[0]?.id ?? null);
    } catch {
      setQueueError('Unable to load maternity queue. Please retry.');
    } finally {
      setLoadingQueue(false);
    }
  };

  useEffect(() => {
    void loadQueue();
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
        const [deliveryRecord, notes, events] = await Promise.all([
          maternityService.getDelivery(selectedVisit.id),
          maternityService.listPostnatalNotes(selectedVisit.id),
          maternityService.listFamilyPlanningEvents(selectedVisit.id),
        ]);
        setDelivery(deliveryRecord);
        setPostnatalNotes(notes);
        setFamilyPlanningEvents(events);
      } catch {
        setDelivery(null);
        setPostnatalNotes([]);
        setFamilyPlanningEvents([]);
      } finally {
        setDeliveryLoading(false);
      }
    };

    void loadWorkspace();
  }, [selectedVisit?.id]);

  useEffect(() => {
    const loadAssignableMidwives = async () => {
      try {
        const staff = await userService.listAssignableStaff();
        const midwives = staff.filter((member) => member.role === 'MIDWIFE');
        setAssignableMidwives(midwives);

        if (selectedVisit) {
          const fallback =
            midwives.find((member) => member.id !== selectedVisit.assigned_doctor_id)?.id ?? '';
          setSelectedOwnerId(fallback);
        }
      } catch {
        setAssignableMidwives([]);
      }
    };

    void loadAssignableMidwives();
  }, [selectedVisit?.id, selectedVisit?.assigned_doctor_id]);

  const handleSaveDelivery = async (payload: Parameters<typeof maternityService.upsertDelivery>[1]) => {
    if (!selectedVisit) return;
    const saved = await maternityService.upsertDelivery(selectedVisit.id, payload);
    setDelivery(saved);
  };

  const handleAddPostnatalNote = async (payload: { subject: 'MOTHER' | 'BABY'; note: string }) => {
    if (!selectedVisit) return;
    const note = await maternityService.addPostnatalNote(selectedVisit.id, payload);
    setPostnatalNotes((prev) => [note, ...prev]);
  };

  const handleAddFamilyPlanning = async (payload: {
    commodity: 'IMPLANT' | 'IUD' | 'INJECTABLE' | 'PILL' | 'CONDOM' | 'OTHER';
    notes?: string;
  }) => {
    if (!selectedVisit) return;
    const event = await maternityService.addFamilyPlanningEvent(selectedVisit.id, payload);
    setFamilyPlanningEvents((prev) => [event, ...prev]);
  };

  const handleReassignOwner = async () => {
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
    } catch (err: any) {
      setReassignError(err?.response?.data?.detail || 'Unable to reassign maternity owner.');
    } finally {
      setReassignLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <header className="rounded-2xl border border-slate-200 bg-gradient-to-r from-white via-emerald-50/40 to-blue-50/30 px-4 py-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Maternity Care Workspace</h1>
            <p className="mt-1 text-sm text-slate-600">
              Delivery, postnatal care, and family planning documentation in one workflow.
            </p>
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              void loadQueue(selectedVisitId);
            }}
            disabled={loadingQueue}
          >
            {loadingQueue ? 'Refreshing…' : 'Refresh queue'}
          </Button>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[320px_1fr]">
        <MaternityQueuePanel
          visits={filteredQueue}
          search={search}
          loading={loadingQueue}
          error={queueError}
          selectedVisitId={selectedVisitId}
          onSearchChange={setSearch}
          onSelectVisit={setSelectedVisitId}
          onRefresh={() => {
            void loadQueue(selectedVisitId);
          }}
        />

        <div className="space-y-4">
          <MaternityOverviewHeader
            selectedVisit={selectedVisit}
            delivery={delivery}
            actionSlot={
              <Button
                size="sm"
                variant="secondary"
                disabled={!selectedVisit}
                onClick={() => {
                  void loadQueue(selectedVisitId);
                }}
              >
                Sync
              </Button>
            }
          />

          <MaternityHandoverPanel
            selectedVisit={selectedVisit}
            assignableMidwives={assignableMidwives}
            selectedOwnerId={selectedOwnerId}
            setSelectedOwnerId={setSelectedOwnerId}
            loading={reassignLoading}
            error={reassignError}
            onReassign={handleReassignOwner}
          />

          <DeliveryRecordPanel
            selectedVisit={selectedVisit}
            delivery={delivery}
            loading={deliveryLoading}
            onSave={handleSaveDelivery}
          />

          <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">
            <PostnatalNotesPanel
              selectedVisit={selectedVisit}
              notes={postnatalNotes}
              onAdd={handleAddPostnatalNote}
            />
            <FamilyPlanningPanel
              selectedVisit={selectedVisit}
              events={familyPlanningEvents}
              onAdd={handleAddFamilyPlanning}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
