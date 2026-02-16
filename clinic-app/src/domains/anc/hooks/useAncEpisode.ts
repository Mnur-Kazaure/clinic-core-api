import { useCallback, useState } from 'react';
import {
  ancApi,
  PregnancyEpisodeCreate,
  PregnancyEpisodeResponse,
  PreviousPregnancyCreate,
  PreviousPregnancyResponse,
} from '@/domains/anc/api/anc';

export function useAncEpisode(patientId: string | null) {
  const [episode, setEpisode] = useState<PregnancyEpisodeResponse | null>(null);
  const [previousPregnancies, setPreviousPregnancies] = useState<PreviousPregnancyResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshEpisode = useCallback(async () => {
    if (!patientId) {
      setEpisode(null);
      setPreviousPregnancies([]);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const activeEpisode = await ancApi.getActiveEpisode(patientId);
      setEpisode(activeEpisode);

      if (!activeEpisode) {
        setPreviousPregnancies([]);
        return;
      }

      const history = await ancApi.listPreviousPregnancies(activeEpisode.id);
      setPreviousPregnancies(history);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Unable to load pregnancy episode.');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  const saveEpisode = useCallback(async (payload: PregnancyEpisodeCreate) => {
    if (!patientId) return null;

    try {
      setSaving(true);
      setError(null);
      const created = await ancApi.createEpisode(patientId, payload);
      setEpisode(created);
      const history = await ancApi.listPreviousPregnancies(created.id);
      setPreviousPregnancies(history);
      return created;
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Unable to save pregnancy episode.');
      return null;
    } finally {
      setSaving(false);
    }
  }, [patientId]);

  const addPreviousPregnancy = useCallback(async (payload: PreviousPregnancyCreate) => {
    if (!episode) return null;

    try {
      setSaving(true);
      setError(null);
      const created = await ancApi.addPreviousPregnancy(episode.id, payload);
      setPreviousPregnancies((prev) => [created, ...prev]);
      return created;
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Unable to save previous pregnancy.');
      return null;
    } finally {
      setSaving(false);
    }
  }, [episode]);

  return {
    episode,
    previousPregnancies,
    loading,
    saving,
    error,
    setError,
    refreshEpisode,
    saveEpisode,
    addPreviousPregnancy,
  };
}
