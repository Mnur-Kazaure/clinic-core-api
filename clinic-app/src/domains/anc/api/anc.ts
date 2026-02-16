import {
  ancService,
  ANCEncounterResponse,
  ANCEncounterUpsert,
  ANCExportOptions,
  PregnancyEpisodeCreate,
  PregnancyEpisodeResponse,
  PreviousPregnancyCreate,
  PreviousPregnancyResponse,
} from '@/domains/anc/services/ancService';
import { VisitResponse } from '@/shared/types';

export interface AncVisitTimelineItem {
  visit: VisitResponse;
  encounter: ANCEncounterResponse | null;
}

export const ancApi = {
  getQueue: ancService.getQueue,
  getActiveEpisode: ancService.getActiveEpisode,
  createEpisode: ancService.createEpisode,
  listPreviousPregnancies: ancService.listPreviousPregnancies,
  addPreviousPregnancy: ancService.addPreviousPregnancy,
  getEncounter: ancService.getEncounter,
  upsertEncounter: ancService.upsertEncounter,
  exportEpisodePdf: ancService.exportEpisodePdf,
};

export type {
  ANCEncounterResponse,
  ANCEncounterUpsert,
  ANCExportOptions,
  PregnancyEpisodeCreate,
  PregnancyEpisodeResponse,
  PreviousPregnancyCreate,
  PreviousPregnancyResponse,
  VisitResponse,
};

export function calculateGestationalAgeWeeks(
  lmpDate?: string | null,
  referenceDate?: string | null
): number | null {
  if (!lmpDate) return null;

  const lmp = new Date(lmpDate);
  if (Number.isNaN(lmp.getTime())) return null;

  const reference = referenceDate ? new Date(referenceDate) : new Date();
  if (Number.isNaN(reference.getTime())) return null;

  const diffMs = reference.getTime() - lmp.getTime();
  if (diffMs < 0) return 0;

  const weeks = Math.floor(diffMs / (1000 * 60 * 60 * 24 * 7));
  return weeks;
}

export async function listEncounterTimeline(
  visits: VisitResponse[]
): Promise<AncVisitTimelineItem[]> {
  const timeline = await Promise.all(
    visits.map(async (visit) => {
      try {
        const encounter = await ancApi.getEncounter(visit.id);
        return { visit, encounter };
      } catch {
        return { visit, encounter: null };
      }
    })
  );

  return timeline.sort(
    (a, b) =>
      new Date(b.visit.created_at).getTime() - new Date(a.visit.created_at).getTime()
  );
}
