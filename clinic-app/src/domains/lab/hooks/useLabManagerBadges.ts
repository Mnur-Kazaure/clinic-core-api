'use client';

import { useCallback, useEffect, useState } from 'react';

import {
  LabManagerBadgeSectionKey,
  LabManagerBadgeSnapshot,
  labManagerService,
} from '@/domains/lab/services/labManagerService';

interface UseLabManagerBadgesOptions {
  enabled: boolean;
}

export function useLabManagerBadges({ enabled }: UseLabManagerBadgesOptions) {
  const [snapshot, setSnapshot] = useState<LabManagerBadgeSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled) {
      return null;
    }
    try {
      const next = await labManagerService.getBadges();
      setSnapshot(next);
      setError(null);
      return next;
    } catch (err) {
      setError('Unable to load laboratory governance badges.');
      return null;
    }
  }, [enabled]);

  const markViewed = useCallback(
    async (sectionKey: LabManagerBadgeSectionKey) => {
      if (!enabled) {
        return null;
      }
      try {
        const next = await labManagerService.markBadgeViewed(sectionKey);
        setSnapshot(next);
        setError(null);
        return next;
      } catch (err) {
        setError('Unable to update laboratory governance badge state.');
        return null;
      }
    },
    [enabled]
  );

  useEffect(() => {
    if (!enabled) {
      setSnapshot(null);
      return;
    }

    void refresh();

    if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') {
      return;
    }

    const stream = new window.EventSource(labManagerService.getBadgeStreamUrl(), {
      withCredentials: true,
    });

    const handleSnapshot = (event: MessageEvent<string>) => {
      try {
        const next = JSON.parse(event.data) as LabManagerBadgeSnapshot;
        setSnapshot(next);
        setError(null);
      } catch {
        setError('Unable to parse laboratory governance badge updates.');
      }
    };

    stream.addEventListener('badge_snapshot', handleSnapshot as EventListener);
    stream.onerror = () => {
      setError((current) => current ?? 'Live badge updates are temporarily unavailable.');
    };

    return () => {
      stream.removeEventListener('badge_snapshot', handleSnapshot as EventListener);
      stream.close();
    };
  }, [enabled, refresh]);

  return {
    snapshot,
    error,
    refresh,
    markViewed,
  };
}
