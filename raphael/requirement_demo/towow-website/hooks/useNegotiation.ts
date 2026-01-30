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

  const agentId = state.user?.agent_id || null;
  const {
    messages,
    subscribe,
    unsubscribe,
    clearMessages,
    isConnected,
    status: wsStatus,
    error: wsError,
    reconnect: reconnectWs,
  } = useWebSocket(agentId);

  // 清除超时定时器
  const clearNegotiationTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // 设置协商超时
  const startNegotiationTimeout = useCallback(() => {
    clearNegotiationTimeout();
    startTimeRef.current = Date.now();

    timeoutRef.current = setTimeout(() => {
      if (negotiationStatus === 'waiting' || negotiationStatus === 'in_progress') {
        setNegotiationStatus('timeout');
        setError(NegotiationErrors.TIMEOUT);
        dispatch({ type: 'SET_STATE', payload: 'ERROR' });
        dispatch({ type: 'SET_ERROR', payload: new Error(NegotiationErrors.TIMEOUT.message) });
      }
    }, NEGOTIATION_TIMEOUT);
  }, [clearNegotiationTimeout, negotiationStatus, dispatch]);

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
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];

      if (lastMessage.message_type === 'system') {
        // 支持中英文关键词
        const content = lastMessage.content.toLowerCase();
        if (content.includes('started') || content.includes('begin') || content.includes('协商开始')) {
          setNegotiationStatus('in_progress');
          // 重置超时计时器
          startNegotiationTimeout();
        } else if (content.includes('completed') || content.includes('finished') || content.includes('协商完成') || content.includes('✅')) {
          setNegotiationStatus('completed');
          clearNegotiationTimeout();
          dispatch({ type: 'SET_STATE', payload: 'COMPLETED' });
        } else if (content.includes('failed') || content.includes('error') || content.includes('失败') || content.includes('错误')) {
          setNegotiationStatus('failed');
          clearNegotiationTimeout();
          setError({
            code: 'NEGOTIATION_FAILED',
            message: lastMessage.content || '协商失败',
          });
        }
      }
    }
  }, [messages, dispatch, startNegotiationTimeout, clearNegotiationTimeout]);

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
    clearMessages();
    dispatch({ type: 'SET_REQUIREMENT', payload: null });
    dispatch({ type: 'CLEAR_MESSAGES' });
    dispatch({ type: 'SET_STATE', payload: 'READY' });
    dispatch({ type: 'SET_ERROR', payload: null });
  }, [clearMessages, dispatch, clearNegotiationTimeout]);

  // Sync messages to context
  useEffect(() => {
    messages.forEach((msg) => {
      dispatch({ type: 'ADD_MESSAGE', payload: msg });
    });
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
