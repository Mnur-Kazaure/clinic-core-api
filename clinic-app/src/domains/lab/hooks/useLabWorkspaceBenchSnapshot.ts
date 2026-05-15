'use client';

import { useCallback, useEffect, useState } from 'react';

import {
  LabWorkspaceBenchSnapshot,
  labService,
} from '@/domains/lab/services/labService';

interface UseLabWorkspaceBenchSnapshotOptions {
  enabled: boolean;
  unitId: string | null;
}

export function useLabWorkspaceBenchSnapshot({
  enabled,
  unitId,
}: UseLabWorkspaceBenchSnapshotOptions) {
  const [snapshot, setSnapshot] = useState<LabWorkspaceBenchSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled || !unitId) {
      return null;
    }
    try {
      const next = await labService.getWorkspaceBenchSnapshot(unitId);
      setSnapshot(next);
      setError(null);
      return next;
    } catch (err) {
      setError('Unable to load laboratory bench attention data.');
      return null;
    }
  }, [enabled, unitId]);

  useEffect(() => {
    if (!enabled || !unitId) {
      setSnapshot(null);
      setError(null);
      return;
    }

    void refresh();

    if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') {
      return;
    }

    const stream = new window.EventSource(labService.getWorkspaceBenchStreamUrl(unitId), {
      withCredentials: true,
    });

    const handleSnapshot = (event: MessageEvent<string>) => {
      try {
        const next = JSON.parse(event.data) as LabWorkspaceBenchSnapshot;
        setSnapshot(next);
        setError(null);
      } catch {
        setError('Unable to parse laboratory bench attention updates.');
      }
    };

    stream.addEventListener('bench_snapshot', handleSnapshot as EventListener);
    stream.onerror = () => {
      setError((current) => current ?? 'Live bench updates are temporarily unavailable.');
    };

    return () => {
      stream.removeEventListener('bench_snapshot', handleSnapshot as EventListener);
      stream.close();
    };
  }, [enabled, refresh, unitId]);

  return {
    snapshot,
    error,
    refresh,
  };
}
