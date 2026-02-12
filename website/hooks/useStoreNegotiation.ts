'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  startNegotiation,
  getNegotiation,
  type StoreNegotiation,
  type StoreParticipant,
} from '@/lib/store-api';
import { useStoreWebSocket, type StoreEvent } from './useStoreWebSocket';

export type NegotiationPhase =
  | 'idle'
  | 'submitting'
  | 'formulating'
  | 'resonating'
  | 'offering'
  | 'synthesizing'
  | 'completed'
  | 'error';

export interface TimelineEntry {
  title: string;
  detail: string;
  fullDetail?: string;
  dotType: 'formulation' | 'resonance' | 'offer' | 'barrier' | 'tool' | 'plan';
}

export interface GraphAgent {
  id: string;
  name: string;
  active: boolean;
}

export interface GraphState {
  agents: GraphAgent[];
  centerVisible: boolean;
  done: boolean;
}

export interface UseStoreNegotiationReturn {
  phase: NegotiationPhase;
  negotiationId: string | null;
  negotiation: StoreNegotiation | null;
  participants: StoreParticipant[];
  planOutput: string | null;
  planJson: Record<string, unknown> | null;
  events: StoreEvent[];
  timeline: TimelineEntry[];
  graphState: GraphState;
  engineState: string;
  error: string | null;
  isAuthError: boolean;
  submit: (intent: string, scope?: string, userId?: string) => Promise<void>;
  reset: () => void;
}

const STATE_TO_PHASE: Record<string, NegotiationPhase> = {
  CREATED: 'formulating',
  FORMULATING: 'formulating',
  FORMULATED: 'resonating',
  ENCODING: 'resonating',
  OFFERING: 'offering',
  BARRIER_WAITING: 'offering',
  SYNTHESIZING: 'synthesizing',
  COMPLETED: 'completed',
};

const POLL_INTERVAL = 2000;

function describeTool(name: string, args?: Record<string, unknown>): string {
  switch (name) {
    case 'ask_agent': return `追问 ${(args && args.agent_id) || '某位 Agent'}`;
    case 'start_discovery': return '发起探索性对话';
    case 'create_sub_demand': return '识别缺口，触发子协商';
    case 'identify_gap': return '分析能力缺口';
    case 'request_info': return '请求补充信息';
    default: return name;
  }
}

export function useStoreNegotiation(): UseStoreNegotiationReturn {
  const [phase, setPhase] = useState<NegotiationPhase>('idle');
  const [negotiationId, setNegotiationId] = useState<string | null>(null);
  const [negotiation, setNegotiation] = useState<StoreNegotiation | null>(null);
  const [planJson, setPlanJson] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAuthError, setIsAuthError] = useState(false);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [graphState, setGraphState] = useState<GraphState>({
    agents: [],
    centerVisible: false,
    done: false,
  });
  const [engineState, setEngineState] = useState<string>('CREATED');
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);
  const processedEventsRef = useRef(0);

  const ws = useStoreWebSocket();

  // Process incoming WS events into timeline + graph state
  useEffect(() => {
    const newEvents = ws.events.slice(processedEventsRef.current);
    if (newEvents.length === 0) return;
    processedEventsRef.current = ws.events.length;

    const newTimeline: TimelineEntry[] = [];

    for (const event of newEvents) {
      const type = event.event_type;
      const data = event.data || {};

      switch (type) {
        case 'formulation.ready':
          newTimeline.push({
            title: '需求理解',
            detail: (data.formulated_text as string) || (data.raw_intent as string) || '',
            dotType: 'formulation',
          });
          setEngineState('FORMULATED');
          setPhase('resonating');
          break;

        case 'resonance.activated': {
          const count = (data.activated_count as number) || 0;
          newTimeline.push({
            title: '共振激活',
            detail: `${count} 个 Agent 产生共振`,
            dotType: 'resonance',
          });
          setEngineState('OFFERING');
          setPhase('offering');

          setGraphState((prev) => {
            const agents = [...prev.agents];
            const eventAgents = data.agents as Array<{ agent_id?: string; display_name?: string }> | undefined;
            if (eventAgents) {
              for (const a of eventAgents) {
                const name = a.display_name || a.agent_id || '?';
                const id = a.agent_id || name;
                if (!agents.find((g) => g.id === id)) {
                  agents.push({ id, name, active: false });
                }
              }
            } else if (count > 0) {
              for (let i = agents.length; i < count; i++) {
                agents.push({ id: `agent_${i}`, name: `A${i + 1}`, active: false });
              }
            }
            return { ...prev, agents };
          });
          break;
        }

        case 'offer.received': {
          const name = (data.display_name as string) || (data.agent_id as string) || '';
          const fullContent = (data.content as string) || '';
          const preview = fullContent.substring(0, 200);
          newTimeline.push({
            title: `${name} 响应`,
            detail: preview + (fullContent.length > 200 ? '...' : ''),
            fullDetail: fullContent.length > 200 ? fullContent : undefined,
            dotType: 'offer',
          });

          const agentId = (data.agent_id as string) || name;
          setGraphState((prev) => {
            const agents = [...prev.agents];
            const found = agents.find((g) => g.id === agentId || g.name === name);
            if (found) {
              found.active = true;
            } else {
              agents.push({ id: agentId, name, active: true });
            }
            return { ...prev, agents };
          });
          break;
        }

        case 'barrier.complete':
          newTimeline.push({
            title: '响应收集完成',
            detail: `${(data.offers_received as number) || 0} 份响应，进入 Center 协调...`,
            dotType: 'barrier',
          });
          setEngineState('SYNTHESIZING');
          setPhase('synthesizing');
          setGraphState((prev) => ({ ...prev, centerVisible: true }));
          break;

        case 'center.tool_call':
          if ((data.tool_name as string) !== 'output_plan') {
            const desc = describeTool(
              data.tool_name as string,
              data.tool_args as Record<string, unknown> | undefined,
            );
            newTimeline.push({ title: `Center: ${desc}`, detail: '', dotType: 'tool' });
          }
          break;

        case 'plan.ready':
          newTimeline.push({
            title: '方案就绪',
            detail: '',
            dotType: 'plan',
          });
          setEngineState('COMPLETED');
          setPhase('completed');
          setGraphState((prev) => ({ ...prev, done: true }));
          if (data.plan_json && typeof data.plan_json === 'object') {
            setPlanJson(data.plan_json as Record<string, unknown>);
          }
          break;

        case 'sub_negotiation.started':
          newTimeline.push({
            title: '发现子需求',
            detail: `正在探索: ${(data.sub_demand as string) || ''}`,
            dotType: 'tool',
          });
          break;
      }
    }

    if (newTimeline.length > 0) {
      setTimeline((prev) => [...prev, ...newTimeline]);
    }
  }, [ws.events]);

  // Poll negotiation status
  const startPolling = useCallback((negId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);

    const poll = async () => {
      if (!isMountedRef.current) return;
      try {
        const data = await getNegotiation(negId);
        if (!isMountedRef.current) return;

        setNegotiation(data);

        // Only update phase from polling if no WS events have set it
        if (data.state === 'COMPLETED') {
          setPhase('completed');
          setEngineState('COMPLETED');
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes('401') || msg.includes('Unauthorized')) {
          setIsAuthError(true);
          setPhase('error');
          setError('登录已过期');
          if (pollRef.current) clearInterval(pollRef.current);
        }
        // Other polling errors are non-fatal
      }
    };

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL);
  }, []);

  const submit = useCallback(async (
    intent: string,
    scope = 'all',
    userId = 'app_store_user',
  ) => {
    setError(null);
    setIsAuthError(false);
    setPhase('submitting');
    setTimeline([]);
    setPlanJson(null);
    setGraphState({ agents: [], centerVisible: false, done: false });
    setEngineState('CREATED');
    processedEventsRef.current = 0;

    try {
      const result = await startNegotiation({ intent, scope, user_id: userId });
      if (!isMountedRef.current) return;

      setNegotiationId(result.negotiation_id);
      setNegotiation(result);
      setPhase(STATE_TO_PHASE[result.state] || 'formulating');
      setEngineState('FORMULATING');

      // Add initial timeline entry
      setTimeline([{
        title: '信号已广播',
        detail: `需求已发送到 ${result.agent_count} 个 Agent (scope: ${scope === 'all' ? '全网' : scope.replace('scene:', '')})`,
        dotType: 'formulation',
      }]);

      ws.connect(result.negotiation_id);
      startPolling(result.negotiation_id);
    } catch (err) {
      if (!isMountedRef.current) return;
      const msg = err instanceof Error ? err.message : String(err);
      setPhase('error');
      setError(msg);
      if (msg.includes('401') || msg.includes('Unauthorized')) {
        setIsAuthError(true);
      }
    }
  }, [ws, startPolling]);

  const reset = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    ws.disconnect();
    ws.clearEvents();
    processedEventsRef.current = 0;
    setPhase('idle');
    setNegotiationId(null);
    setNegotiation(null);
    setPlanJson(null);
    setError(null);
    setIsAuthError(false);
    setTimeline([]);
    setGraphState({ agents: [], centerVisible: false, done: false });
    setEngineState('CREATED');
  }, [ws]);

  // Cleanup
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return {
    phase,
    negotiationId,
    negotiation,
    participants: negotiation?.participants || [],
    planOutput: negotiation?.plan_output || null,
    planJson: planJson || negotiation?.plan_json || null,
    events: ws.events,
    timeline,
    graphState,
    engineState,
    error,
    isAuthError,
    submit,
    reset,
  };
}
