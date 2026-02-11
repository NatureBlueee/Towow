'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { getStoreWebSocketUrl } from '@/lib/store-api';
import type { ApiError } from '@/lib/errors';

export interface StoreEvent {
  event_type: string;
  data: Record<string, unknown>;
  timestamp?: string;
}

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface UseStoreWebSocketReturn {
  status: ConnectionStatus;
  events: StoreEvent[];
  connect: (negId: string) => void;
  disconnect: () => void;
  clearEvents: () => void;
  error: ApiError | null;
}

const MAX_RETRIES = 5;

export function useStoreWebSocket(): UseStoreWebSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [events, setEvents] = useState<StoreEvent[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);
  const negIdRef = useRef<string | null>(null);

  const disconnect = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000);
      wsRef.current = null;
    }
    negIdRef.current = null;
    retryCountRef.current = 0;
    if (isMountedRef.current) {
      setStatus('disconnected');
    }
  }, []);

  const connect = useCallback((negId: string) => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    negIdRef.current = negId;
    retryCountRef.current = 0;
    setError(null);
    setStatus('connecting');

    const doConnect = () => {
      if (!isMountedRef.current || !negIdRef.current) return;

      const url = getStoreWebSocketUrl(negIdRef.current);
      const ws = new WebSocket(url);

      ws.onopen = () => {
        if (isMountedRef.current) {
          setStatus('connected');
          setError(null);
          retryCountRef.current = 0;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (isMountedRef.current) {
            setEvents((prev) => [...prev, data as StoreEvent]);
          }
        } catch {
          // Ignore non-JSON messages
        }
      };

      ws.onerror = () => {
        if (isMountedRef.current) {
          setStatus('error');
          setError({ code: 'WEBSOCKET_ERROR', message: 'WebSocket 连接错误' });
        }
      };

      ws.onclose = (event) => {
        wsRef.current = null;
        if (event.code === 1000 || !isMountedRef.current) {
          if (isMountedRef.current) setStatus('disconnected');
          return;
        }

        // Retry with exponential backoff
        if (retryCountRef.current < MAX_RETRIES && negIdRef.current) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 15000);
          retryCountRef.current += 1;
          retryTimeoutRef.current = setTimeout(doConnect, delay);
        } else if (isMountedRef.current) {
          setStatus('error');
          setError({ code: 'WEBSOCKET_MAX_RETRIES', message: '连接失败次数过多' });
        }
      };

      wsRef.current = ws;
    };

    doConnect();
  }, []);

  const clearEvents = useCallback(() => setEvents([]), []);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  return { status, events, connect, disconnect, clearEvents, error };
}
