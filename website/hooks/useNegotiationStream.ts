'use client';

import { useReducer, useEffect, useRef, useCallback, useState } from 'react';
import type {
  NegotiationState,
  NegotiationAction,
  NegotiationEvent,
  FormulationReadyData,
  ResonanceActivatedData,
  OfferReceivedData,
  BarrierCompleteData,
  CenterToolCallData,
  PlanReadyData,
  SubNegotiationStartedData,
} from '@/types/negotiation';

// ============ Initial State ============

const initialState: NegotiationState = {
  phase: 'idle',
  negotiationId: null,
  formulation: null,
  resonanceAgents: [],
  filteredAgents: [],
  offers: [],
  barrierInfo: null,
  centerActivities: [],
  plan: null,
  subNegotiations: [],
  events: [],
  error: null,
};

// ============ Reducer ============

function negotiationReducer(
  state: NegotiationState,
  action: NegotiationAction,
): NegotiationState {
  switch (action.type) {
    case 'SUBMIT_DEMAND':
      return { ...initialState, phase: 'submitting' };

    case 'SET_NEGOTIATION_ID':
      return { ...state, negotiationId: action.negotiationId, phase: 'formulating' };

    case 'SET_PHASE':
      return { ...state, phase: action.phase };

    case 'SET_ERROR':
      return { ...state, phase: 'error', error: action.error };

    case 'RESET':
      return { ...initialState };

    case 'EVENT_RECEIVED': {
      const event = action.event;
      const newEvents = [...state.events, event];

      switch (event.event_type) {
        case 'formulation.ready': {
          const data = event.data as unknown as FormulationReadyData;
          return {
            ...state,
            events: newEvents,
            phase: 'confirming',
            formulation: data,
          };
        }

        case 'resonance.activated': {
          const data = event.data as unknown as ResonanceActivatedData;
          return {
            ...state,
            events: newEvents,
            phase: 'collecting_offers',
            resonanceAgents: data.agents,
            filteredAgents: data.filtered_agents || [],
          };
        }

        case 'offer.received': {
          const data = event.data as unknown as OfferReceivedData;
          return {
            ...state,
            events: newEvents,
            offers: [...state.offers, data],
          };
        }

        case 'barrier.complete': {
          const data = event.data as unknown as BarrierCompleteData;
          return {
            ...state,
            events: newEvents,
            phase: 'barrier_met',
            barrierInfo: data,
          };
        }

        case 'center.tool_call': {
          const data = event.data as unknown as CenterToolCallData;
          return {
            ...state,
            events: newEvents,
            phase: 'synthesizing',
            centerActivities: [...state.centerActivities, data],
          };
        }

        case 'plan.ready': {
          const data = event.data as unknown as PlanReadyData;
          return {
            ...state,
            events: newEvents,
            phase: 'plan_ready',
            plan: data,
          };
        }

        case 'sub_negotiation.started': {
          const data = event.data as unknown as SubNegotiationStartedData;
          return {
            ...state,
            events: newEvents,
            subNegotiations: [...state.subNegotiations, data],
          };
        }

        default:
          // Unknown event type — store but don't change phase
          return { ...state, events: newEvents };
      }
    }

    default:
      return state;
  }
}

// ============ WebSocket Config ============

const WS_BASE = process.env.NEXT_PUBLIC_NEGOTIATION_WS_URL || 'ws://localhost:8080/v1';
const MAX_RETRIES = 5;

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

// ============ Hook ============

export interface UseNegotiationStreamReturn {
  state: NegotiationState;
  connectionStatus: ConnectionStatus;
  dispatch: React.Dispatch<NegotiationAction>;
  connect: (negotiationId: string) => void;
  disconnect: () => void;
  reset: () => void;
  /** Inject a mock event (for development without backend) */
  injectEvent: (event: NegotiationEvent) => void;
}

export function useNegotiationStream(): UseNegotiationStreamReturn {
  const [state, dispatch] = useReducer(negotiationReducer, initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');

  const connectToWs = useCallback((negotiationId: string) => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

    retryCountRef.current = 0;
    setConnectionStatus('connecting');

    const doConnect = () => {
      if (!isMountedRef.current) return;

      try {
        const ws = new WebSocket(`${WS_BASE}/ws/negotiation/${negotiationId}`);

        ws.onopen = () => {
          if (!isMountedRef.current) return;
          retryCountRef.current = 0;
          setConnectionStatus('connected');
        };

        ws.onmessage = (evt) => {
          if (!isMountedRef.current) return;
          try {
            const event: NegotiationEvent = JSON.parse(evt.data);
            dispatch({ type: 'EVENT_RECEIVED', event });
          } catch {
            console.error('Failed to parse negotiation event:', evt.data);
          }
        };

        ws.onerror = () => {
          if (!isMountedRef.current) return;
          setConnectionStatus('error');
        };

        ws.onclose = (evt) => {
          wsRef.current = null;
          if (!isMountedRef.current) return;

          // Normal close
          if (evt.code === 1000) {
            setConnectionStatus('disconnected');
            return;
          }

          // Retry
          if (retryCountRef.current < MAX_RETRIES) {
            setConnectionStatus('reconnecting');
            const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 15000);
            retryCountRef.current += 1;
            retryTimeoutRef.current = setTimeout(doConnect, delay);
          } else {
            setConnectionStatus('error');
            dispatch({ type: 'SET_ERROR', error: 'WebSocket connection lost after max retries' });
          }
        };

        wsRef.current = ws;
      } catch {
        setConnectionStatus('error');
        dispatch({ type: 'SET_ERROR', error: 'Failed to create WebSocket connection' });
      }
    };

    doConnect();
  }, []);

  const disconnect = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000);
      wsRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, []);

  const reset = useCallback(() => {
    disconnect();
    dispatch({ type: 'RESET' });
  }, [disconnect]);

  const injectEvent = useCallback((event: NegotiationEvent) => {
    dispatch({ type: 'EVENT_RECEIVED', event });
  }, []);

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

  return {
    state,
    connectionStatus,
    dispatch,
    connect: connectToWs,
    disconnect,
    reset,
    injectEvent,
  };
}
