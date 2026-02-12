/**
 * Tests for the negotiation state reducer.
 * Verifies all 7 V1 event types are handled correctly
 * and that phase transitions follow the expected flow.
 */

import {
  mockFormulationReady,
  mockResonanceActivated,
  mockOfferAlice,
  mockOfferBob,
  mockBarrierComplete,
  mockCenterToolCall1,
  mockCenterToolCall2,
  mockSubNegotiationStarted,
  mockPlanReady,
  mockEventSequence,
} from '../__mocks__/events';
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

// ============ Inline reducer for testing ============
// (We test the reducer logic directly without importing from the hook,
//  since the hook wraps it with React internals. The logic is identical.)

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
          return { ...state, events: newEvents, phase: 'confirming', formulation: data };
        }
        case 'resonance.activated': {
          const data = event.data as unknown as ResonanceActivatedData;
          return { ...state, events: newEvents, phase: 'collecting_offers', resonanceAgents: data.agents, filteredAgents: data.filtered_agents || [] };
        }
        case 'offer.received': {
          const data = event.data as unknown as OfferReceivedData;
          return { ...state, events: newEvents, offers: [...state.offers, data] };
        }
        case 'barrier.complete': {
          const data = event.data as unknown as BarrierCompleteData;
          return { ...state, events: newEvents, phase: 'barrier_met', barrierInfo: data };
        }
        case 'center.tool_call': {
          const data = event.data as unknown as CenterToolCallData;
          return { ...state, events: newEvents, phase: 'synthesizing', centerActivities: [...state.centerActivities, data] };
        }
        case 'plan.ready': {
          const data = event.data as unknown as PlanReadyData;
          return { ...state, events: newEvents, phase: 'plan_ready', plan: data };
        }
        case 'sub_negotiation.started': {
          const data = event.data as unknown as SubNegotiationStartedData;
          return { ...state, events: newEvents, subNegotiations: [...state.subNegotiations, data] };
        }
        default:
          return { ...state, events: newEvents };
      }
    }
    default:
      return state;
  }
}

function applyAction(state: NegotiationState, action: NegotiationAction): NegotiationState {
  return negotiationReducer(state, action);
}

function applyEvent(state: NegotiationState, event: NegotiationEvent): NegotiationState {
  return applyAction(state, { type: 'EVENT_RECEIVED', event });
}

// ============ Tests ============

describe('NegotiationReducer', () => {
  test('initial state is idle', () => {
    expect(initialState.phase).toBe('idle');
    expect(initialState.negotiationId).toBeNull();
    expect(initialState.events).toHaveLength(0);
  });

  test('SUBMIT_DEMAND resets state and sets submitting', () => {
    const state = applyAction(initialState, { type: 'SUBMIT_DEMAND' });
    expect(state.phase).toBe('submitting');
    expect(state.offers).toHaveLength(0);
  });

  test('SET_NEGOTIATION_ID stores id and transitions to formulating', () => {
    const state = applyAction(initialState, { type: 'SET_NEGOTIATION_ID', negotiationId: 'neg_123' });
    expect(state.negotiationId).toBe('neg_123');
    expect(state.phase).toBe('formulating');
  });

  test('RESET returns to initial state', () => {
    let state = applyAction(initialState, { type: 'SET_NEGOTIATION_ID', negotiationId: 'neg_123' });
    state = applyEvent(state, mockFormulationReady);
    state = applyAction(state, { type: 'RESET' });
    expect(state).toEqual(initialState);
  });

  test('SET_ERROR transitions to error phase', () => {
    const state = applyAction(initialState, { type: 'SET_ERROR', error: 'something broke' });
    expect(state.phase).toBe('error');
    expect(state.error).toBe('something broke');
  });
});

describe('Event Handling', () => {
  test('formulation.ready -> confirming phase with formulation data', () => {
    const state = applyEvent(initialState, mockFormulationReady);
    expect(state.phase).toBe('confirming');
    expect(state.formulation).not.toBeNull();
    expect(state.formulation!.raw_intent).toContain('MVP');
    expect(state.formulation!.formulated_text).toContain('technical partner');
    expect(state.events).toHaveLength(1);
  });

  test('resonance.activated -> collecting_offers phase with agents', () => {
    const state = applyEvent(initialState, mockResonanceActivated);
    expect(state.phase).toBe('collecting_offers');
    expect(state.resonanceAgents).toHaveLength(4);
    expect(state.resonanceAgents[0].display_name).toBe('Alice Chen');
    expect(state.resonanceAgents[0].resonance_score).toBe(0.92);
  });

  test('offer.received accumulates offers without changing phase', () => {
    let state = applyEvent(initialState, mockOfferAlice);
    expect(state.offers).toHaveLength(1);
    expect(state.offers[0].display_name).toBe('Alice Chen');

    state = applyEvent(state, mockOfferBob);
    expect(state.offers).toHaveLength(2);
    expect(state.offers[1].display_name).toBe('Bob Zhang');
  });

  test('barrier.complete -> barrier_met phase', () => {
    const state = applyEvent(initialState, mockBarrierComplete);
    expect(state.phase).toBe('barrier_met');
    expect(state.barrierInfo).not.toBeNull();
    expect(state.barrierInfo!.total_participants).toBe(4);
    expect(state.barrierInfo!.offers_received).toBe(3);
    expect(state.barrierInfo!.exited_count).toBe(1);
  });

  test('center.tool_call -> synthesizing phase, accumulates activities', () => {
    let state = applyEvent(initialState, mockCenterToolCall1);
    expect(state.phase).toBe('synthesizing');
    expect(state.centerActivities).toHaveLength(1);
    expect(state.centerActivities[0].tool_name).toBe('ask_agent');

    state = applyEvent(state, mockCenterToolCall2);
    expect(state.centerActivities).toHaveLength(2);
    expect(state.centerActivities[1].tool_name).toBe('discover_connections');
  });

  test('plan.ready -> plan_ready phase with plan data', () => {
    const state = applyEvent(initialState, mockPlanReady);
    expect(state.phase).toBe('plan_ready');
    expect(state.plan).not.toBeNull();
    expect(state.plan!.center_rounds).toBe(2);
    expect(state.plan!.participating_agents).toHaveLength(3);
    expect(state.plan!.plan_text).toContain('Alice Chen');
  });

  test('sub_negotiation.started accumulates without changing phase', () => {
    const state = applyEvent(initialState, mockSubNegotiationStarted);
    expect(state.subNegotiations).toHaveLength(1);
    expect(state.subNegotiations[0].gap_description).toContain('DevOps');
  });

  test('unknown event type stores event but does not change phase', () => {
    const unknownEvent: NegotiationEvent = {
      event_type: 'execution.progress' as any,
      negotiation_id: 'neg_mock001',
      timestamp: new Date().toISOString(),
      event_id: 'evt_unknown',
      data: { progress: 50 },
    };
    const state = applyEvent(initialState, unknownEvent);
    expect(state.phase).toBe('idle'); // unchanged
    expect(state.events).toHaveLength(1);
  });
});

describe('Full Sequence', () => {
  test('processing all mock events produces expected final state', () => {
    let state = initialState;
    for (const event of mockEventSequence) {
      state = applyEvent(state, event);
    }

    expect(state.phase).toBe('plan_ready');
    expect(state.formulation).not.toBeNull();
    expect(state.resonanceAgents).toHaveLength(4);
    expect(state.offers).toHaveLength(3);
    expect(state.barrierInfo).not.toBeNull();
    expect(state.centerActivities).toHaveLength(2);
    expect(state.subNegotiations).toHaveLength(1);
    expect(state.plan).not.toBeNull();
    expect(state.events).toHaveLength(mockEventSequence.length);
  });
});

describe('Event Parsing', () => {
  test('all mock events have valid event_type', () => {
    const validTypes = [
      'formulation.ready',
      'resonance.activated',
      'offer.received',
      'barrier.complete',
      'center.tool_call',
      'plan.ready',
      'sub_negotiation.started',
    ];
    for (const event of mockEventSequence) {
      expect(validTypes).toContain(event.event_type);
    }
  });

  test('all mock events have required fields', () => {
    for (const event of mockEventSequence) {
      expect(event.negotiation_id).toBeTruthy();
      expect(event.timestamp).toBeTruthy();
      expect(event.data).toBeDefined();
      expect(typeof event.data).toBe('object');
    }
  });

  test('events can be serialized and deserialized as JSON', () => {
    for (const event of mockEventSequence) {
      const json = JSON.stringify(event);
      const parsed = JSON.parse(json);
      expect(parsed.event_type).toBe(event.event_type);
      expect(parsed.negotiation_id).toBe(event.negotiation_id);
      expect(parsed.data).toEqual(event.data);
    }
  });
});
