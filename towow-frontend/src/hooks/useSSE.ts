import { useEffect, useRef, useState, useCallback } from 'react';
import type { SSEEvent } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface UseSSEOptions {
  onEvent?: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
  autoConnect?: boolean;
}

export interface UseSSEReturn {
  isConnected: boolean;
  error: Error | null;
  connect: () => void;
  disconnect: () => void;
  reconnectAttempts: number;
}

export const useSSE = (
  negotiationId: string | null,
  options: UseSSEOptions = {}
): UseSSEReturn => {
  const {
    onEvent,
    onError,
    onOpen,
    onClose,
    reconnectDelay = 3000,
    maxReconnectAttempts = 10,
    autoConnect = true,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const lastEventIdRef = useRef<string | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isManualDisconnectRef = useRef(false);

  // Store callbacks in refs to avoid unnecessary reconnections
  const onEventRef = useRef(onEvent);
  const onErrorRef = useRef(onError);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const reconnectDelayRef = useRef(reconnectDelay);
  const maxReconnectAttemptsRef = useRef(maxReconnectAttempts);

  // Keep refs updated with latest callback values
  useEffect(() => {
    onEventRef.current = onEvent;
    onErrorRef.current = onError;
    onOpenRef.current = onOpen;
    onCloseRef.current = onClose;
    reconnectDelayRef.current = reconnectDelay;
    maxReconnectAttemptsRef.current = maxReconnectAttempts;
  });

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true;
    clearReconnectTimeout();

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setIsConnected(false);
    setReconnectAttempts(0);
    onCloseRef.current?.();
  }, [clearReconnectTimeout]);

  const connect = useCallback(() => {
    if (!negotiationId) return;

    // Reset manual disconnect flag
    isManualDisconnectRef.current = false;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Build URL with last_event_id for resume
    const url = new URL(`${API_BASE}/api/v1/events/negotiations/${negotiationId}/stream`);
    if (lastEventIdRef.current) {
      url.searchParams.set('last_event_id', lastEventIdRef.current);
    }

    const eventSource = new EventSource(url.toString());
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
      setReconnectAttempts(0);
      onOpenRef.current?.();
    };

    eventSource.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);

        // Track last event ID for resume
        if (data.event_id) {
          lastEventIdRef.current = data.event_id;
        }

        onEventRef.current?.(data);
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
      eventSourceRef.current = null;

      // Don't reconnect if manually disconnected
      if (isManualDisconnectRef.current) {
        return;
      }

      const err = new Error('SSE connection error');
      setError(err);
      onErrorRef.current?.(err);

      // Attempt reconnect with exponential backoff
      setReconnectAttempts((prev) => {
        const nextAttempts = prev + 1;
        if (nextAttempts <= maxReconnectAttemptsRef.current) {
          const delay = reconnectDelayRef.current * Math.min(Math.pow(2, prev), 10);
          console.log(`Reconnecting in ${delay}ms (attempt ${nextAttempts}/${maxReconnectAttemptsRef.current})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          console.error('Max reconnect attempts reached');
        }
        return nextAttempts;
      });
    };
  }, [negotiationId]);

  // Auto connect on mount or negotiationId change
  useEffect(() => {
    if (autoConnect && negotiationId) {
      connect();
    }

    return () => {
      clearReconnectTimeout();
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [autoConnect, negotiationId, connect, clearReconnectTimeout]);

  return {
    isConnected,
    error,
    connect,
    disconnect,
    reconnectAttempts,
  };
};
