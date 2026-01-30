'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useExperienceContext } from '@/context/ExperienceContext';
import { useWebSocket } from './useWebSocket';
import {
  submitRequirement as submitRequirementApi,
  getRequirement,
  getNegotiationResult,
  NegotiationResult,
} from '@/lib/api/requirements';
import { RequirementInput, Requirement, NegotiationMessage } from '@/types/experience';
import { handleApiError, ApiError, NegotiationErrors } from '@/lib/errors';

export type NegotiationStatus = 'idle' | 'submitting' | 'waiting' | 'in_progress' | 'completed' | 'failed' | 'timeout';

// 协商超时时间（毫秒）
const NEGOTIATION_TIMEOUT = 5 * 60 * 1000; // 5 分钟

// 检测是否为本地开发环境（跨域场景）
const isLocalDevCrossOrigin = () => {
  if (typeof window === 'undefined') return false;
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080';
  const currentOrigin = window.location.origin;
  // 如果 WebSocket URL 和当前页面不在同一个端口，则为跨域
  return wsUrl.includes('localhost') && !wsUrl.includes(window.location.port);
};

export interface UseNegotiationReturn {
  submitRequirement: (data: RequirementInput) => Promise<string>;
  currentRequirement: Requirement | null;
  negotiationStatus: NegotiationStatus;
  messages: NegotiationMessage[];
  result: NegotiationResult | null;
  isLoading: boolean;
  error: ApiError | null;
  reset: () => void;
  wsStatus: string;
  wsError: ApiError | null;
  reconnectWs: () => void;
}

export function useNegotiation(): UseNegotiationReturn {
  const { state, dispatch } = useExperienceContext();
  const [negotiationStatus, setNegotiationStatus] = useState<NegotiationStatus>('idle');
  const [result, setResult] = useState<NegotiationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const lastSyncedIndexRef = useRef(0);
  // Use ref to track negotiation status to avoid callback recreation
  const negotiationStatusRef = useRef<NegotiationStatus>('idle');
  // Track synced message IDs to prevent duplicates even after reset
  const syncedMessageIdsRef = useRef<Set<string>>(new Set());

  const agentId = state.user?.agent_id || null;
  // 在本地开发跨域场景下使用演示模式（绕过 cookie 认证问题）
  const useDemoMode = isLocalDevCrossOrigin();
  // 使用 ref 存储稳定的演示 ID，避免每次渲染都生成新 ID
  const demoAgentIdRef = useRef<string | null>(null);
  if (useDemoMode && !demoAgentIdRef.current) {
    demoAgentIdRef.current = `demo_${Date.now()}`;
  }
  // 如果没有 agentId 但需要连接 WebSocket，使用稳定的演示 ID
  const wsAgentId = agentId || (useDemoMode ? demoAgentIdRef.current : null);
  const {
    messages,
    subscribe,
    unsubscribe,
    clearMessages,
    isConnected,
    status: wsStatus,
    error: wsError,
    reconnect: reconnectWs,
  } = useWebSocket(wsAgentId, { demoMode: useDemoMode });

  // Keep negotiationStatusRef in sync with state
  useEffect(() => {
    negotiationStatusRef.current = negotiationStatus;
  }, [negotiationStatus]);

  // 清除超时定时器
  const clearNegotiationTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // 设置协商超时 - use ref to avoid dependency on negotiationStatus
  const startNegotiationTimeout = useCallback(() => {
    clearNegotiationTimeout();
    startTimeRef.current = Date.now();

    timeoutRef.current = setTimeout(() => {
      // Use ref to get current status, avoiding stale closure
      const currentStatus = negotiationStatusRef.current;
      if (currentStatus === 'waiting' || currentStatus === 'in_progress') {
        setNegotiationStatus('timeout');
        setError(NegotiationErrors.TIMEOUT);
        dispatch({ type: 'SET_STATE', payload: 'ERROR' });
        dispatch({ type: 'SET_ERROR', payload: new Error(NegotiationErrors.TIMEOUT.message) });
      }
    }, NEGOTIATION_TIMEOUT);
  }, [clearNegotiationTimeout, dispatch]);

  // Subscribe to channel when requirement is created
  useEffect(() => {
    const channelId = state.currentRequirement?.channel_id;
    if (channelId && isConnected) {
      subscribe(channelId);
      return () => {
        unsubscribe(channelId);
      };
    }
  }, [state.currentRequirement?.channel_id, isConnected, subscribe, unsubscribe]);

  // Monitor messages for status changes
  // Use refs for callbacks to avoid unnecessary re-runs
  const startNegotiationTimeoutRef = useRef(startNegotiationTimeout);
  const clearNegotiationTimeoutRef = useRef(clearNegotiationTimeout);

  useEffect(() => {
    startNegotiationTimeoutRef.current = startNegotiationTimeout;
    clearNegotiationTimeoutRef.current = clearNegotiationTimeout;
  }, [startNegotiationTimeout, clearNegotiationTimeout]);

  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];

      if (lastMessage.message_type === 'system') {
        // 支持中英文关键词
        const content = lastMessage.content.toLowerCase();
        if (content.includes('started') || content.includes('begin') || content.includes('协商开始')) {
          setNegotiationStatus('in_progress');
          // 重置超时计时器
          startNegotiationTimeoutRef.current();
        } else if (content.includes('completed') || content.includes('finished') || content.includes('协商完成') || content.includes('✅')) {
          setNegotiationStatus('completed');
          clearNegotiationTimeoutRef.current();
          dispatch({ type: 'SET_STATE', payload: 'COMPLETED' });
        } else if (content.includes('failed') || content.includes('error') || content.includes('失败') || content.includes('错误')) {
          setNegotiationStatus('failed');
          clearNegotiationTimeoutRef.current();
          setError({
            code: 'NEGOTIATION_FAILED',
            message: lastMessage.content || '协商失败',
          });
        }
      }
    }
  }, [messages, dispatch]);

  // Fetch result when negotiation completes
  useEffect(() => {
    if (negotiationStatus === 'completed' && state.currentRequirement) {
      getNegotiationResult(state.currentRequirement.requirement_id)
        .then((res) => {
          if (res) {
            setResult(res);
          }
        })
        .catch((err) => {
          console.error('Failed to fetch negotiation result:', err);
          // 不影响完成状态，只记录错误
        });
    }
  }, [negotiationStatus, state.currentRequirement]);

  // 清理超时定时器
  useEffect(() => {
    return () => {
      clearNegotiationTimeout();
    };
  }, [clearNegotiationTimeout]);

  const submitRequirement = useCallback(
    async (data: RequirementInput): Promise<string> => {
      setIsLoading(true);
      setError(null);
      setNegotiationStatus('submitting');
      dispatch({ type: 'SET_STATE', payload: 'SUBMITTING' });

      try {
        const requirement = await submitRequirementApi(data, agentId || undefined);
        dispatch({ type: 'SET_REQUIREMENT', payload: requirement });
        setNegotiationStatus('waiting');
        dispatch({ type: 'SET_STATE', payload: 'NEGOTIATING' });

        // 开始超时计时
        startNegotiationTimeout();

        return requirement.requirement_id;
      } catch (err) {
        const apiError = handleApiError(err);
        setError(apiError);
        setNegotiationStatus('failed');
        dispatch({ type: 'SET_ERROR', payload: new Error(apiError.message) });
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [agentId, dispatch, startNegotiationTimeout]
  );

  const reset = useCallback(() => {
    clearNegotiationTimeout();
    setNegotiationStatus('idle');
    setResult(null);
    setError(null);
    setIsLoading(false);
    startTimeRef.current = null;
    lastSyncedIndexRef.current = 0;  // Reset sync index when clearing messages
    syncedMessageIdsRef.current.clear();  // Clear synced message IDs
    clearMessages();
    dispatch({ type: 'SET_REQUIREMENT', payload: null });
    dispatch({ type: 'CLEAR_MESSAGES' });
    dispatch({ type: 'SET_STATE', payload: 'READY' });
    dispatch({ type: 'SET_ERROR', payload: null });
  }, [clearMessages, dispatch, clearNegotiationTimeout]);

  // Sync messages to context - only add new messages
  useEffect(() => {
    // Only sync messages that haven't been synced yet
    const newMessages = messages.slice(lastSyncedIndexRef.current);
    newMessages.forEach((msg) => {
      // Double-check: skip if already synced (handles edge cases)
      if (!syncedMessageIdsRef.current.has(msg.message_id)) {
        syncedMessageIdsRef.current.add(msg.message_id);
        dispatch({ type: 'ADD_MESSAGE', payload: msg });
      }
    });
    lastSyncedIndexRef.current = messages.length;
  }, [messages, dispatch]);

  return {
    submitRequirement,
    currentRequirement: state.currentRequirement,
    negotiationStatus,
    messages: state.messages,
    result,
    isLoading,
    error,
    reset,
    wsStatus,
    wsError,
    reconnectWs,
  };
}
