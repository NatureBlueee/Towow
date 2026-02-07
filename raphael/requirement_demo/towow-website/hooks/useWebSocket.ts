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

interface UseWebSocketOptions {
  // 使用演示模式端点（不需要认证，用于本地开发跨域场景）
  demoMode?: boolean;
}

export function useWebSocket(agentId: string | null, options?: UseWebSocketOptions): UseWebSocketReturn {
  const { demoMode = false } = options || {};
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [messages, setMessages] = useState<NegotiationMessage[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const subscribedChannelsRef = useRef<Set<string>>(new Set());
  // Use ref to store connect function to avoid useEffect dependency issues
  const connectRef = useRef<(() => void) | null>(null);
  // Track if we're currently connecting to prevent duplicate connections
  const isConnectingRef = useRef(false);
  // Track the current agentId to detect changes
  const currentAgentIdRef = useRef<string | null>(null);
  // Store the connection timeout ID for cleanup
  const connectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  // Track if component is mounted to prevent state updates after unmount
  const isMountedRef = useRef(true);

  // Exponential backoff calculation
  const getRetryDelay = useCallback(() => {
    const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
    return delay;
  }, []);

  // Connect WebSocket
  const connect = useCallback(() => {
    // Prevent duplicate connections
    if (!agentId || isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Also check if WebSocket is in CONNECTING state
    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    // Don't connect if component is unmounted
    if (!isMountedRef.current) {
      return;
    }

    isConnectingRef.current = true;

    // 清除之前的错误状态
    if (isMountedRef.current) setError(null);

    // 设置连接状态
    if (retryCountRef.current > 0) {
      if (isMountedRef.current) setStatus('reconnecting');
    } else {
      if (isMountedRef.current) setStatus('connecting');
    }

    try {
      // 根据 demoMode 选择端点
      const wsPath = demoMode ? `/ws/demo/${agentId}` : `/ws/${agentId}`;
      const ws = new WebSocket(`${WS_BASE}${wsPath}`);

      ws.onopen = () => {
        isConnectingRef.current = false;
        if (isMountedRef.current) {
          setStatus('connected');
          setError(null);
          setRetryCount(0);
        }
        retryCountRef.current = 0;

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
            if (isMountedRef.current) {
              setMessages((prev) => [...prev, data.payload as NegotiationMessage]);
            }
          } else if (data.type === 'error') {
            if (isMountedRef.current) {
              setError({
                code: 'WEBSOCKET_ERROR',
                message: data.message || 'WebSocket 收到错误消息',
              });
            }
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = () => {
        if (isMountedRef.current) {
          setStatus('error');
          setError(WebSocketErrors.ERROR);
        }
      };

      ws.onclose = (event) => {
        wsRef.current = null;
        isConnectingRef.current = false;

        // 正常关闭
        if (event.code === 1000) {
          if (isMountedRef.current) setStatus('disconnected');
          return;
        }

        // 非正常关闭，尝试重连
        if (retryCountRef.current < MAX_RETRIES && isMountedRef.current) {
          setStatus('reconnecting');
          setError({
            code: 'WEBSOCKET_CLOSED',
            message: `连接已断开，正在尝试重连 (${retryCountRef.current + 1}/${MAX_RETRIES})...`,
          });

          const delay = getRetryDelay();
          retryCountRef.current += 1;
          setRetryCount(retryCountRef.current);
          retryTimeoutRef.current = setTimeout(connect, delay);
        } else if (isMountedRef.current) {
          setStatus('error');
          setError(WebSocketErrors.MAX_RETRIES);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      if (isMountedRef.current) {
        setStatus('error');
        setError({
          code: 'WEBSOCKET_ERROR',
          message: '无法建立 WebSocket 连接',
          details: { error: String(err) },
        });
      }
    }
  }, [agentId, demoMode, getRetryDelay]);

  // Keep connectRef in sync with connect function
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

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

    // 重置状态
    retryCountRef.current = 0;
    setRetryCount(0);
    setError(null);
    isConnectingRef.current = false;

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
  // Note: We use connectRef to avoid recreating the effect when connect changes
  useEffect(() => {
    isMountedRef.current = true;

    if (agentId) {
      // Check if agentId changed - if so, close existing connection first
      if (currentAgentIdRef.current && currentAgentIdRef.current !== agentId) {
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
        isConnectingRef.current = false;
      }
      currentAgentIdRef.current = agentId;

      // Clear any pending connection timeout
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
        connectionTimeoutRef.current = null;
      }

      // Use a delay to debounce rapid mount/unmount cycles (React Strict Mode)
      connectionTimeoutRef.current = setTimeout(() => {
        if (isMountedRef.current) {
          connectRef.current?.();
        }
      }, 50);
    }

    return () => {
      isMountedRef.current = false;
      // Clear the connection timeout on cleanup
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
        connectionTimeoutRef.current = null;
      }
    };
  }, [agentId]);

  // Cleanup on unmount only
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  // Reconnect when page becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && status === 'disconnected' && agentId) {
        retryCountRef.current = 0;
        setRetryCount(0);
        connectRef.current?.();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [status, agentId]);

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
