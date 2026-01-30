'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { WebSocketErrors, ApiError } from '@/lib/errors';

export interface NegotiationMessage {
  message_id: string;
  channel_id: string;
  sender_id: string;
  sender_name: string;
  message_type: 'text' | 'system' | 'action';
  content: string;
  timestamp: string;
}

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error' | 'reconnecting';

interface UseWebSocketReturn {
  isConnected: boolean;
  status: ConnectionStatus;
  messages: NegotiationMessage[];
  subscribe: (channelId: string) => void;
  unsubscribe: (channelId: string) => void;
  clearMessages: () => void;
  reconnect: () => void;
  error: ApiError | null;
  retryCount: number;
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080';
const MAX_RETRIES = 10;

export function useWebSocket(agentId: string | null): UseWebSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [messages, setMessages] = useState<NegotiationMessage[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const subscribedChannelsRef = useRef<Set<string>>(new Set());

  // Exponential backoff calculation
  const getRetryDelay = useCallback(() => {
    const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
    return delay;
  }, []);

  // Connect WebSocket
  const connect = useCallback(() => {
    if (!agentId || wsRef.current?.readyState === WebSocket.OPEN) return;

    // 清除之前的错误状态
    setError(null);

    // 设置连接状态
    if (retryCountRef.current > 0) {
      setStatus('reconnecting');
    } else {
      setStatus('connecting');
    }

    try {
      const ws = new WebSocket(`${WS_BASE}/ws/${agentId}`);

      ws.onopen = () => {
        setStatus('connected');
        setError(null);
        retryCountRef.current = 0;
        setRetryCount(0);

        // 重新订阅之前的频道
        subscribedChannelsRef.current.forEach((channelId) => {
          ws.send(JSON.stringify({
            action: 'subscribe',
            channel_id: channelId,
          }));
        });
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'message' && data.payload) {
            setMessages((prev) => [...prev, data.payload as NegotiationMessage]);
          } else if (data.type === 'error') {
            setError({
              code: 'WEBSOCKET_ERROR',
              message: data.message || 'WebSocket 收到错误消息',
            });
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = () => {
        setStatus('error');
        setError(WebSocketErrors.ERROR);
      };

      ws.onclose = (event) => {
        wsRef.current = null;

        // 正常关闭
        if (event.code === 1000) {
          setStatus('disconnected');
          return;
        }

        // 非正常关闭，尝试重连
        if (retryCountRef.current < MAX_RETRIES) {
          setStatus('reconnecting');
          setError({
            code: 'WEBSOCKET_CLOSED',
            message: `连接已断开，正在尝试重连 (${retryCountRef.current + 1}/${MAX_RETRIES})...`,
          });

          const delay = getRetryDelay();
          retryCountRef.current += 1;
          setRetryCount(retryCountRef.current);
          retryTimeoutRef.current = setTimeout(connect, delay);
        } else {
          setStatus('error');
          setError(WebSocketErrors.MAX_RETRIES);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      setStatus('error');
      setError({
        code: 'WEBSOCKET_ERROR',
        message: '无法建立 WebSocket 连接',
        details: { error: String(err) },
      });
    }
  }, [agentId, getRetryDelay]);

  // 手动重连
  const reconnect = useCallback(() => {
    // 清除现有连接和定时器
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // 重置重试计数
    retryCountRef.current = 0;
    setRetryCount(0);
    setError(null);

    // 重新连接
    connect();
  }, [connect]);

  // Subscribe to channel
  const subscribe = useCallback((channelId: string) => {
    subscribedChannelsRef.current.add(channelId);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        channel_id: channelId,
      }));
    }
  }, []);

  // Unsubscribe from channel
  const unsubscribe = useCallback((channelId: string) => {
    subscribedChannelsRef.current.delete(channelId);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'unsubscribe',
        channel_id: channelId,
      }));
    }
  }, []);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Connection management
  useEffect(() => {
    if (agentId) {
      connect();
    }

    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [agentId, connect]);

  // Reconnect when page becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && status === 'disconnected' && agentId) {
        retryCountRef.current = 0;
        setRetryCount(0);
        connect();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [status, agentId, connect]);

  // 网络状态监听
  useEffect(() => {
    const handleOnline = () => {
      if (status === 'error' || status === 'disconnected') {
        reconnect();
      }
    };

    const handleOffline = () => {
      setError({
        code: 'NETWORK_ERROR',
        message: '网络连接已断开，请检查网络设置',
      });
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [status, reconnect]);

  return {
    isConnected: status === 'connected',
    status,
    messages,
    subscribe,
    unsubscribe,
    clearMessages,
    reconnect,
    error,
    retryCount,
  };
}
