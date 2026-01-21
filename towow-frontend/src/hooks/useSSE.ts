import { useEffect, useRef, useCallback } from 'react';
import { createNegotiationEventSource } from '../api/events';
import { useEventStore } from '../stores/eventStore';
import type { SSEEvent, TimelineEvent, Proposal } from '../types';

interface UseSSEOptions {
  onEvent?: (event: SSEEvent) => void;
  onError?: (error: Event) => void;
  autoConnect?: boolean;
}

export const useSSE = (negotiationId: string | null, options: UseSSEOptions = {}) => {
  const { onEvent, onError, autoConnect = true } = options;
  const eventSourceRef = useRef<EventSource | null>(null);
  const store = useEventStore();

  const handleEvent = useCallback(
    (event: SSEEvent) => {
      const timelineEvent: TimelineEvent = {
        id: `${event.event_type}-${Date.now()}`,
        timestamp: event.timestamp,
        event_type: event.event_type as TimelineEvent['event_type'],
        content: {},
      };

      switch (event.event_type) {
        case 'agent_thinking':
          if ('agent_id' in event.data && 'step' in event.data) {
            store.updateParticipant(event.data.agent_id, { status: 'thinking' });
            timelineEvent.agent_id = event.data.agent_id;
            timelineEvent.content.thinking_step = event.data.step;
          }
          break;

        case 'agent_proposal':
          if ('agent_id' in event.data && 'proposal' in event.data) {
            store.updateParticipant(event.data.agent_id, { status: 'active' });
            store.addProposal(event.data.proposal as Proposal);
            timelineEvent.agent_id = event.data.agent_id;
            timelineEvent.content.proposal = event.data.proposal as Proposal;
          }
          break;

        case 'agent_message':
          if ('agent_id' in event.data && 'message' in event.data) {
            timelineEvent.agent_id = event.data.agent_id;
            timelineEvent.content.message = event.data.message;
          }
          break;

        case 'status_update':
          if ('status' in event.data) {
            store.setStatus(event.data.status);
            if ('message' in event.data) {
              timelineEvent.content.message = event.data.message;
            }
          }
          break;

        case 'error':
          if ('error_message' in event.data) {
            store.setError(event.data.error_message);
            timelineEvent.content.error = event.data.error_message;
          }
          break;
      }

      store.addTimelineEvent(timelineEvent);
      onEvent?.(event);
    },
    [store, onEvent]
  );

  const connect = useCallback(() => {
    if (!negotiationId) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    eventSourceRef.current = createNegotiationEventSource(
      negotiationId,
      handleEvent,
      onError
    );
  }, [negotiationId, handleEvent, onError]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (autoConnect && negotiationId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, negotiationId, connect, disconnect]);

  return {
    connect,
    disconnect,
    isConnected: !!eventSourceRef.current,
  };
};
