/**
 * Adapter: converts App Store's StoreEvent[] + phase into NegotiationState
 * for use with NegotiationGraph and DetailPanel.
 *
 * Pure function, no side effects. All data comes from WS events.
 */

import type {
  NegotiationState,
  NegotiationPhase,
  NegotiationEvent,
  FormulationReadyData,
  ResonanceAgent,
  OfferReceivedData,
  BarrierCompleteData,
  CenterToolCallData,
  PlanReadyData,
  SubNegotiationStartedData,
  EventType,
} from '@/types/negotiation';
import type { StoreEvent } from '@/hooks/useStoreWebSocket';

/**
 * Map Store's phase string to the canonical NegotiationPhase
 * used by NegotiationGraph. The Store has fewer phase values;
 * we infer the precise canonical phase from events.
 */
function mapPhase(storePhase: string, events: StoreEvent[]): NegotiationPhase {
  switch (storePhase) {
    case 'idle':
      return 'idle';
    case 'submitting':
      return 'submitting';
    case 'formulating': {
      const hasFormulation = events.some((e) => e.event_type === 'formulation.ready');
      return hasFormulation ? 'confirming' : 'formulating';
    }
    case 'resonating':
      return 'resonating';
    case 'offering':
      return 'collecting_offers';
    case 'synthesizing': {
      const hasCenterCall = events.some((e) => e.event_type === 'center.tool_call');
      return hasCenterCall ? 'synthesizing' : 'barrier_met';
    }
    case 'completed':
      return 'plan_ready';
    case 'error':
      return 'error';
    default:
      return 'idle';
  }
}

export function buildNegotiationState(
  events: StoreEvent[],
  storePhase: string,
): NegotiationState {
  let formulation: FormulationReadyData | null = null;
  const resonanceAgents: ResonanceAgent[] = [];
  const filteredAgents: ResonanceAgent[] = [];
  const offers: OfferReceivedData[] = [];
  let barrierInfo: BarrierCompleteData | null = null;
  const centerActivities: CenterToolCallData[] = [];
  let plan: PlanReadyData | null = null;
  const subNegotiations: SubNegotiationStartedData[] = [];
  const negotiationEvents: NegotiationEvent[] = [];

  for (const event of events) {
    const data = event.data || {};

    // Build NegotiationEvent for the events array
    negotiationEvents.push({
      event_type: event.event_type as EventType,
      negotiation_id: '',
      timestamp: event.timestamp || new Date().toISOString(),
      event_id: null,
      data,
    });

    switch (event.event_type) {
      case 'formulation.ready':
        formulation = {
          raw_intent: (data.raw_intent as string) || '',
          formulated_text: (data.formulated_text as string) || '',
          enrichments: (data.enrichments as Record<string, unknown>) || {},
          degraded: data.degraded as boolean | undefined,
          degraded_reason: data.degraded_reason as string | undefined,
        };
        break;

      case 'resonance.activated': {
        const agents = data.agents as
          | Array<{ agent_id: string; display_name: string; resonance_score: number }>
          | undefined;
        if (agents) {
          for (const a of agents) {
            resonanceAgents.push({
              agent_id: a.agent_id,
              display_name: a.display_name,
              resonance_score: a.resonance_score,
            });
          }
        }
        // filtered_agents may be absent from Store backend — default to empty
        const filtered = data.filtered_agents as
          | Array<{ agent_id: string; display_name: string; resonance_score: number }>
          | undefined;
        if (filtered) {
          for (const a of filtered) {
            filteredAgents.push({
              agent_id: a.agent_id,
              display_name: a.display_name,
              resonance_score: a.resonance_score,
            });
          }
        }
        break;
      }

      case 'offer.received':
        offers.push({
          agent_id: (data.agent_id as string) || '',
          display_name: (data.display_name as string) || '',
          content: (data.content as string) || '',
          capabilities: (data.capabilities as string[]) || [],
        });
        break;

      case 'barrier.complete':
        barrierInfo = {
          total_participants: (data.total_participants as number) || 0,
          offers_received: (data.offers_received as number) || 0,
          exited_count: (data.exited_count as number) || 0,
        };
        break;

      case 'center.tool_call':
        centerActivities.push({
          tool_name: (data.tool_name as string) || '',
          tool_args: (data.tool_args as Record<string, unknown>) || {},
          round_number: (data.round_number as number) || 0,
        });
        break;

      case 'plan.ready':
        plan = {
          plan_text: (data.plan_text as string) || '',
          center_rounds: (data.center_rounds as number) || 0,
          participating_agents: (data.participating_agents as string[]) || [],
          plan_json: (data.plan_json as PlanReadyData['plan_json']) || {
            participants: [],
            tasks: [],
          },
        };
        break;

      case 'sub_negotiation.started':
        subNegotiations.push({
          sub_negotiation_id: (data.sub_negotiation_id as string) || '',
          gap_description: (data.gap_description as string) || '',
        });
        break;
    }
  }

  return {
    phase: mapPhase(storePhase, events),
    negotiationId: null,
    formulation,
    resonanceAgents,
    filteredAgents,
    offers,
    barrierInfo,
    centerActivities,
    plan,
    subNegotiations,
    events: negotiationEvents,
    error: null,
  };
}
