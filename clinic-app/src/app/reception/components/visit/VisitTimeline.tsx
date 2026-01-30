'use client';

import { VisitTimelineEvent } from '@/domains/visit/services/visitService';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';

interface VisitTimelineProps {
  events: VisitTimelineEvent[];
  isLoading?: boolean;
}

export function VisitTimeline({ events, isLoading = false }: VisitTimelineProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="flex">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-gray-200 rounded-full"></div>
              </div>
              <div className="ml-4 flex-1">
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-3xl mb-2">📜</div>
        <p>No timeline events yet</p>
        <p className="text-sm mt-1">Status changes will appear here</p>
      </div>
    );
  }

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {events.map((event, index) => (
          <li key={event.id}>
            <div className="relative pb-8">
              {index !== events.length - 1 && (
                <span
                  className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"
                  aria-hidden="true"
                />
              )}
              <div className="relative flex items-start space-x-3">
                <div className="relative">
                  <div className="h-8 w-8 bg-gray-100 rounded-full flex items-center justify-center ring-8 ring-white">
                    <span className="text-gray-600 text-sm">
                      {event.from_status ? '🔄' : '🚀'}
                    </span>
                  </div>
                </div>

                <div className="min-w-0 flex-1">
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      {event.from_status && (
                        <>
                          <VisitStatusBadge status={event.from_status} size="sm" />
                          <span className="text-gray-400">→</span>
                        </>
                      )}
                      <VisitStatusBadge status={event.to_status} size="sm" />
                    </div>

                    <div className="text-sm text-gray-500 mt-1">
                      <span className="font-medium text-gray-900">
                        Changed by: {event.changed_by.substring(0, 8)}...
                      </span>
                      {' • '}
                      <time dateTime={event.created_at}>
                        {formatDateTime(event.created_at)}
                      </time>
                    </div>

                    {event.from_status && (
                      <div className="mt-2 text-xs text-gray-500 bg-gray-50 p-2 rounded">
                        Transition:{' '}
                        <span className="font-medium">{event.from_status}</span> →{' '}
                        <span className="font-medium">{event.to_status}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
