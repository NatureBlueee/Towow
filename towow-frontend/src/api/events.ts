import { createSSEConnection } from './client';
import type { SSEEvent } from '../types';

export type SSEEventHandler = (event: SSEEvent) => void;

export const createNegotiationEventSource = (
  negotiationId: string,
  onEvent: SSEEventHandler,
  onError?: (error: Event) => void
): EventSource => {
  const eventSource = createSSEConnection(`/api/v1/negotiations/${negotiationId}/events`);

  eventSource.onmessage = (event) => {
    try {
      const data: SSEEvent = JSON.parse(event.data);
      onEvent(data);
    } catch (e) {
      console.error('Failed to parse SSE event:', e);
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    onError?.(error);
  };

  return eventSource;
};
