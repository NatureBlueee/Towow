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
  const isConnectingRef = useRef(false);

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
    console.log('[useSSE] disconnect called');
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
    if (!negotiationId) {
      console.log('[useSSE] connect called but no negotiationId');
      return;
    }

    // Prevent duplicate connections (React Strict Mode protection)
    if (isConnectingRef.current || eventSourceRef.current?.readyState === EventSource.OPEN) {
      console.log('[useSSE] Already connecting or connected, skipping');
      return;
    }
    isConnectingRef.current = true;

    console.log('[useSSE] Connecting to SSE for negotiationId:', negotiationId);

    // Reset manual disconnect flag
    isManualDisconnectRef.current = false;

    // Close existing connection
    if (eventSourceRef.current) {
      console.log('[useSSE] Closing existing connection');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Build URL with last_event_id for resume
    const url = new URL(`${API_BASE}/api/v1/events/negotiations/${negotiationId}/stream`);
    if (lastEventIdRef.current) {
      url.searchParams.set('last_event_id', lastEventIdRef.current);
    }

    console.log('[useSSE] Opening EventSource to:', url.toString());
    const eventSource = new EventSource(url.toString());
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('[useSSE] Connection opened for negotiationId:', negotiationId);
      isConnectingRef.current = false;
      setIsConnected(true);
      setError(null);
      setReconnectAttempts(0);
      onOpenRef.current?.();
    };

    eventSource.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);
        console.log('[useSSE] Event received:', data.event_type, 'event_id:', data.event_id);

        // Track last event ID for resume
        if (data.event_id) {
          lastEventIdRef.current = data.event_id;
        }

        onEventRef.current?.(data);
      } catch (err) {
        console.error('[useSSE] Failed to parse SSE event:', err, 'raw data:', event.data);
      }
    };

    eventSource.onerror = (err) => {
      console.error('[useSSE] Connection error for negotiationId:', negotiationId, err);
      isConnectingRef.current = false;
      setIsConnected(false);
      eventSource.close();
      eventSourceRef.current = null;

      // Don't reconnect if manually disconnected
      if (isManualDisconnectRef.current) {
        console.log('[useSSE] Manual disconnect, not reconnecting');
        return;
      }

      const error = new Error('SSE connection error');
      setError(error);
      onErrorRef.current?.(error);

      // Attempt reconnect with exponential backoff
      setReconnectAttempts((prev) => {
        const nextAttempts = prev + 1;
        if (nextAttempts <= maxReconnectAttemptsRef.current) {
          const delay = reconnectDelayRef.current * Math.min(Math.pow(2, prev), 10);
          console.log(`[useSSE] Reconnecting in ${delay}ms (attempt ${nextAttempts}/${maxReconnectAttemptsRef.current})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          console.error('[useSSE] Max reconnect attempts reached');
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
      isConnectingRef.current = false;
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
