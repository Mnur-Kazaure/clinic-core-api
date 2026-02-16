import { useCallback, useMemo, useState } from 'react';
import {
  ancApi,
  ANCEncounterResponse,
  ANCEncounterUpsert,
  AncVisitTimelineItem,
  listEncounterTimeline,
  VisitResponse,
} from '@/domains/anc/api/anc';

interface UseAncVisitsArgs {
  queue: VisitResponse[];
  patientId: string | null;
}

export function useAncVisits({ queue, patientId }: UseAncVisitsArgs) {
  const [timeline, setTimeline] = useState<AncVisitTimelineItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const patientVisits = useMemo(() => {
    if (!patientId) return [];
    return queue
      .filter((visit) => visit.patient_id === patientId)
      .sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
  }, [queue, patientId]);

  const refreshTimeline = useCallback(async () => {
    if (!patientId) {
      setTimeline([]);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await listEncounterTimeline(patientVisits);
      setTimeline(data);
    } catch {
      setError('Unable to load ANC visit timeline.');
      setTimeline([]);
    } finally {
      setLoading(false);
    }
  }, [patientId, patientVisits]);

  const saveEncounter = useCallback(
    async (visitId: string, payload: ANCEncounterUpsert) => {
      try {
        setSaving(true);
        setError(null);
        const updated = await ancApi.upsertEncounter(visitId, payload);
        setTimeline((prev) => {
          const existing = prev.find((item) => item.visit.id === visitId);
          if (existing) {
            return prev.map((item) =>
              item.visit.id === visitId ? { ...item, encounter: updated } : item
            );
          }

          const fallbackVisit = queue.find((visit) => visit.id === visitId);
          if (!fallbackVisit) {
            return prev;
          }

          return [{ visit: fallbackVisit, encounter: updated }, ...prev].sort(
            (a, b) =>
              new Date(b.visit.created_at).getTime() -
              new Date(a.visit.created_at).getTime()
          );
        });
        return updated;
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setError(detail || 'Unable to save ANC visit encounter.');
        return null;
      } finally {
        setSaving(false);
      }
    },
    [queue]
  );

  const getEncounterForVisit = useCallback(
    (visitId: string): ANCEncounterResponse | null =>
      timeline.find((item) => item.visit.id === visitId)?.encounter ?? null,
    [timeline]
  );

  return {
    patientVisits,
    timeline,
    loading,
    saving,
    error,
    setError,
    refreshTimeline,
    saveEncounter,
    getEncounterForVisit,
  };
}
