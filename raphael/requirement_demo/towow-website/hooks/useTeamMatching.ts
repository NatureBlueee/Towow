'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { useTeamAuth } from '@/context/TeamAuthContext';
import { createTeamRequest, getTeamRequest, getTeamProposals } from '@/lib/team-matcher/api';
import type {
  TeamRequestFormData,
  TeamRequestDetail,
  TeamProposal,
  OfferSummary,
} from '@/lib/team-matcher/types';
import { handleApiError } from '@/lib/errors';

export type TeamMatchStatus =
  | 'idle'
  | 'submitting'
  | 'broadcasting'
  | 'receiving'
  | 'generating'
  | 'complete'
  | 'error';

/** Activity log entry for the progress page */
export interface ActivityLogEntry {
  time: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
}

export interface UseTeamMatchingReturn {
  submitRequest: (data: TeamRequestFormData & { user_id: string }) => Promise<string>;
  resumeRequest: (requestId: string) => Promise<void>;
  status: TeamMatchStatus;
  requestId: string | null;
  channelId: string | null;
  requestDetail: TeamRequestDetail | null;
  offers: OfferSummary[];
  llmProgress: string;
  proposals: TeamProposal[] | null;
  error: string | null;
  activityLog: ActivityLogEntry[];
  reset: () => void;
  wsStatus: string;
}

// Timeout: 5 minutes max for the entire matching process
const MATCHING_TIMEOUT = 5 * 60 * 1000;

// Detect local dev cross-origin scenario
const isLocalDevCrossOrigin = () => {
  if (typeof window === 'undefined') return false;
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080';
  return wsUrl.includes('localhost') && !wsUrl.includes(window.location.port);
};

export function useTeamMatching(agentId?: string | null): UseTeamMatchingReturn {
  // If no agentId is provided explicitly, try to get it from TeamAuthContext
  const teamAuth = useTeamAuth();
  const resolvedAgentId = agentId ?? teamAuth.user?.agent_id ?? null;

  const [status, setStatus] = useState<TeamMatchStatus>('idle');
  const [requestId, setRequestId] = useState<string | null>(null);
  const [channelId, setChannelId] = useState<string | null>(null);
  const [requestDetail, setRequestDetail] = useState<TeamRequestDetail | null>(null);
  const [offers, setOffers] = useState<OfferSummary[]>([]);
  const [llmProgress, setLlmProgress] = useState<string>('');
  const [proposals, setProposals] = useState<TeamProposal[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const statusRef = useRef<TeamMatchStatus>('idle');
  const isMountedRef = useRef(true);

  // Helper to add log entries
  const addLog = useCallback((message: string, type: ActivityLogEntry['type'] = 'info') => {
    if (!isMountedRef.current) return;
    setActivityLog((prev) => [
      ...prev,
      { time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }), message, type },
    ]);
  }, []);

  // WebSocket setup
  const useDemoMode = isLocalDevCrossOrigin();
  const demoAgentIdRef = useRef<string | null>(null);
  if (useDemoMode && !demoAgentIdRef.current) {
    demoAgentIdRef.current = `demo_team_${Date.now()}`;
  }
  const wsAgentId = resolvedAgentId || (useDemoMode ? demoAgentIdRef.current : null);

  const {
    messages,
    subscribe,
    unsubscribe,
    clearMessages,
    status: wsStatus,
    isConnected,
  } = useWebSocket(wsAgentId, { demoMode: useDemoMode });

  // Keep statusRef in sync
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  // Track mounted state
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Clear timeout helper
  const clearMatchingTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // Start timeout
  const startMatchingTimeout = useCallback(() => {
    clearMatchingTimeout();
    timeoutRef.current = setTimeout(() => {
      const currentStatus = statusRef.current;
      if (
        currentStatus === 'broadcasting' ||
        currentStatus === 'receiving' ||
        currentStatus === 'generating'
      ) {
        if (isMountedRef.current) {
          setStatus('error');
          setError('匹配超时，请重新提交请求');
        }
      }
    }, MATCHING_TIMEOUT);
  }, [clearMatchingTimeout]);

  // Subscribe to channel when channelId changes and WS is connected
  useEffect(() => {
    if (channelId && isConnected) {
      subscribe(channelId);
      return () => {
        unsubscribe(channelId);
      };
    }
  }, [channelId, isConnected, subscribe, unsubscribe]);

  // Process incoming WebSocket messages for team-specific events
  const processedIndexRef = useRef(0);

  useEffect(() => {
    if (messages.length <= processedIndexRef.current) return;

    const newMessages = messages.slice(processedIndexRef.current);
    processedIndexRef.current = messages.length;

    for (const msg of newMessages) {
      // Team matching messages come as system messages with structured content
      // or as raw JSON payloads. Try to parse the content as JSON first.
      let parsed: { type?: string; data?: Record<string, unknown> } | null = null;
      try {
        parsed = JSON.parse(msg.content);
      } catch {
        // Not JSON, check for keyword-based detection
        const content = msg.content.toLowerCase();
        if (content.includes('team_request_created') || content.includes('请求已创建')) {
          parsed = { type: 'team_request_created' };
        } else if (content.includes('signal_broadcasting') || content.includes('信号广播')) {
          parsed = { type: 'signal_broadcasting' };
        } else if (content.includes('offer_received') || content.includes('收到响应')) {
          parsed = { type: 'offer_received' };
        } else if (content.includes('matching_in_progress') || content.includes('匹配中')) {
          parsed = { type: 'matching_in_progress' };
        } else if (content.includes('proposals_ready') || content.includes('方案就绪')) {
          parsed = { type: 'proposals_ready' };
        } else if (content.includes('composition_progress')) {
          parsed = { type: 'composition_progress', data: { content: msg.content } };
        } else if (content.includes('composition_error') || content.includes('生成失败')) {
          parsed = { type: 'composition_error', data: { error: msg.content } };
        }
      }

      if (!parsed?.type) continue;
      if (!isMountedRef.current) break;

      switch (parsed.type) {
        case 'team_request_created':
        case 'signal_broadcasting':
          setStatus('broadcasting');
          addLog('信号广播中...', 'info');
          break;

        case 'offer_received': {
          setStatus('receiving');
          const data = parsed.data || {};
          const agentName = (data.agent_name as string) || '未知伙伴';
          const offerSummary: OfferSummary = {
            agent_name: agentName,
            skills: (data.skills as string[]) || [],
            brief: (data.offer_content as string) || (data.brief as string) || '',
            timestamp: (data.timestamp as string) || new Date().toISOString(),
          };
          setOffers((prev) => [...prev, offerSummary]);
          addLog(`${agentName} 响应了你的请求`, 'success');
          break;
        }

        case 'matching_in_progress':
          setStatus('generating');
          addLog('AI 开始组合团队方案...', 'info');
          break;

        case 'composition_progress': {
          const content = (parsed.data?.content as string) || '';
          if (content) {
            setLlmProgress((prev) => prev + content);
          }
          break;
        }

        case 'composition_error': {
          const errMsg = (parsed.data?.error as string) || '方案生成失败';
          setStatus('error');
          setError(errMsg);
          clearMatchingTimeout();
          break;
        }

        case 'proposals_ready': {
          setStatus('complete');
          clearMatchingTimeout();
          // Fetch the full proposals from API
          const reqId = requestId || (parsed.data?.request_id as string);
          if (reqId) {
            getTeamProposals(reqId)
              .then((res) => {
                if (isMountedRef.current) {
                  setProposals(res.proposals);
                }
              })
              .catch((err) => {
                console.error('Failed to fetch proposals:', err);
              });
          }
          break;
        }
      }
    }
  }, [messages, requestId, clearMatchingTimeout]);

  // Polling: periodically fetch request status to catch missed WebSocket events
  const startPolling = useCallback((reqId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      if (!isMountedRef.current) return;
      try {
        const data = await getTeamRequest(reqId);
        if (!isMountedRef.current) return;

        // Update request detail (includes offer_count)
        setRequestDetail(data);

        // Status-driven transitions — only move forward, never backward
        const currentStatus = statusRef.current;
        if (data.status === 'completed' && currentStatus !== 'complete') {
          setStatus('complete');
          addLog('方案已生成！', 'success');
          const result = await getTeamProposals(reqId);
          if (isMountedRef.current) setProposals(result.proposals);
          if (pollRef.current) clearInterval(pollRef.current);
        } else if (data.status === 'generating' && currentStatus !== 'generating' && currentStatus !== 'complete') {
          setStatus('generating');
          addLog('AI 正在组合团队方案...', 'info');
        } else if (data.status === 'collecting' && currentStatus === 'broadcasting') {
          setStatus('receiving');
        } else if (data.status === 'failed' && currentStatus !== 'error') {
          setStatus('error');
          setError('方案生成失败，请重试');
          addLog('方案生成失败', 'error');
          if (pollRef.current) clearInterval(pollRef.current);
        }

        // Update offer count from polling even if status unchanged
        if (data.offer_count > 0 && currentStatus === 'broadcasting') {
          setStatus('receiving');
          addLog(`已有 ${data.offer_count} 位伙伴响应`, 'success');
        }
      } catch {
        // Polling failure is non-fatal, just skip this cycle
      }
    }, 5000); // Poll every 5 seconds
  }, [addLog]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Submit a team matching request
  const submitRequest = useCallback(
    async (data: TeamRequestFormData & { user_id: string }): Promise<string> => {
      setStatus('submitting');
      setError(null);
      setOffers([]);
      setLlmProgress('');
      setProposals(null);

      try {
        const response = await createTeamRequest(data);
        const newRequestId = response.request_id;

        if (!isMountedRef.current) return newRequestId;

        setRequestId(newRequestId);
        addLog('请求已创建，信号正在广播', 'success');

        // Set up channel subscription and polling
        setChannelId(response.channel_id || newRequestId);
        setStatus('broadcasting');
        startMatchingTimeout();
        startPolling(newRequestId);

        // Fetch full request detail
        try {
          const detail = await getTeamRequest(newRequestId);
          if (isMountedRef.current) setRequestDetail(detail);
        } catch {
          // Non-fatal: detail fetch failed, polling will retry
        }

        return newRequestId;
      } catch (err) {
        if (isMountedRef.current) {
          const apiError = handleApiError(err);
          setStatus('error');
          setError(apiError.message);
        }
        throw err;
      }
    },
    [startMatchingTimeout]
  );

  // Resume tracking an existing request (e.g. after page navigation)
  const resumeRequest = useCallback(
    async (reqId: string) => {
      setStatus('broadcasting');
      setError(null);
      setRequestId(reqId);
      addLog('正在恢复请求状态...', 'info');

      try {
        const data = await getTeamRequest(reqId);

        if (!isMountedRef.current) return;

        // Store full request detail
        setRequestDetail(data);

        // Set channel for WebSocket subscription
        if (data.channel_id) {
          setChannelId(data.channel_id);
          addLog('WebSocket 频道已订阅', 'info');
        }

        // Map backend status to hook status
        const statusMap: Record<string, TeamMatchStatus> = {
          pending: 'broadcasting',
          collecting: 'receiving',
          generating: 'generating',
          completed: 'complete',
          failed: 'error',
        };
        const mappedStatus = statusMap[data.status] || 'broadcasting';
        setStatus(mappedStatus);

        // Log the current state
        if (data.offer_count > 0) {
          addLog(`已有 ${data.offer_count} 位伙伴响应`, 'success');
        } else {
          addLog('等待伙伴响应中...', 'info');
        }

        if (data.status === 'completed') {
          addLog('方案已就绪', 'success');
          const result = await getTeamProposals(reqId);
          if (isMountedRef.current) {
            setProposals(result.proposals);
          }
        } else if (data.status === 'failed') {
          setError('方案生成失败，请重试');
          addLog('方案生成失败', 'error');
        } else {
          // Start polling for in-progress requests
          startMatchingTimeout();
          startPolling(reqId);
        }
      } catch (err) {
        if (isMountedRef.current) {
          setStatus('error');
          const msg = err instanceof Error ? err.message : '无法获取请求状态';
          setError(msg);
          addLog(`错误: ${msg}`, 'error');
        }
      }
    },
    [startMatchingTimeout, startPolling, addLog]
  );

  // Reset all state
  const reset = useCallback(() => {
    clearMatchingTimeout();
    stopPolling();
    setStatus('idle');
    setRequestId(null);
    setChannelId(null);
    setRequestDetail(null);
    setOffers([]);
    setLlmProgress('');
    setProposals(null);
    setError(null);
    setActivityLog([]);
    processedIndexRef.current = 0;
    clearMessages();
  }, [clearMatchingTimeout, stopPolling, clearMessages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearMatchingTimeout();
      stopPolling();
    };
  }, [clearMatchingTimeout, stopPolling]);

  return {
    submitRequest,
    resumeRequest,
    status,
    requestId,
    channelId,
    requestDetail,
    offers,
    llmProgress,
    proposals,
    error,
    activityLog,
    reset,
    wsStatus,
  };
}
