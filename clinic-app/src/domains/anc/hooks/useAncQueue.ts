import { useCallback, useMemo, useState } from 'react';
import { ancApi, VisitResponse } from '@/domains/anc/api/anc';

export function useAncQueue() {
  const [queue, setQueue] = useState<VisitResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedVisitId, setSelectedVisitId] = useState<string | null>(null);

  const refreshQueue = useCallback(async (preserveVisitId?: string | null) => {
    try {
      setLoading(true);
      setError(null);
      const data = await ancApi.getQueue();
      setQueue(data);
      setSelectedVisitId((previousId) => {
        const targetId = preserveVisitId ?? previousId;
        if (!targetId) {
          return data[0]?.id ?? null;
        }

        const stillExists = data.some((visit) => visit.id === targetId);
        return stillExists ? targetId : data[0]?.id ?? null;
      });
    } catch {
      setError('Unable to load ANC queue. Please retry.');
    } finally {
      setLoading(false);
    }
  }, []);

  const filteredQueue = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return queue;

    return queue.filter((visit) => {
      const patientName = (visit.patient_name ?? '').toLowerCase();
      const patientMrn = (visit.patient_mrn ?? '').toLowerCase();
      return patientName.includes(term) || patientMrn.includes(term);
    });
  }, [queue, search]);

  const selectedVisit = useMemo(
    () => queue.find((visit) => visit.id === selectedVisitId) ?? null,
    [queue, selectedVisitId]
  );

  return {
    queue,
    filteredQueue,
    loading,
    error,
    search,
    selectedVisit,
    selectedVisitId,
    setSearch,
    setSelectedVisitId,
    refreshQueue,
  };
}
