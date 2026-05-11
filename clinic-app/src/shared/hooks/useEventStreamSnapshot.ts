'use client';

import { useEffect, useState } from 'react';

interface UseEventStreamSnapshotOptions<T> {
  enabled: boolean;
  url: string | null;
  eventName: string;
  errorMessage: string;
}

export function useEventStreamSnapshot<T>({
  enabled,
  url,
  eventName,
  errorMessage,
}: UseEventStreamSnapshotOptions<T>) {
  const [snapshot, setSnapshot] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || !url) {
      setSnapshot(null);
      setError(null);
      return;
    }

    if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') {
      return;
    }

    const stream = new window.EventSource(url, {
      withCredentials: true,
    });

    const handleSnapshot = (event: MessageEvent<string>) => {
      try {
        const next = JSON.parse(event.data) as T;
        setSnapshot(next);
        setError(null);
      } catch {
        setError(`Unable to parse ${errorMessage.toLowerCase()}`);
      }
    };

    stream.addEventListener(eventName, handleSnapshot as EventListener);
    stream.onerror = () => {
      setError((current) => current ?? errorMessage);
    };

    return () => {
      stream.removeEventListener(eventName, handleSnapshot as EventListener);
      stream.close();
    };
  }, [enabled, eventName, errorMessage, url]);

  return {
    snapshot,
    error,
  };
}
