/**
 * TypeScript types for negotiation events, state, and API responses.
 * Mirrors the backend event structure from backend/towow/core/events.py.
 */

// ============ Event Types ============

export type EventType =
  | 'formulation.ready'
  | 'resonance.activated'
  | 'offer.received'
  | 'barrier.complete'
  | 'center.tool_call'
  | 'plan.ready'
  | 'sub_negotiation.started'
  | 'execution.progress'   // V1 reserved
  | 'echo.received';       // V1 reserved

// ============ Event Data Shapes ============

export interface FormulationReadyData {
  [key: string]: unknown;
  raw_intent: string;
  formulated_text: string;
  enrichments: Record<string, unknown>;
  degraded?: boolean;
  degraded_reason?: string;
}

export interface ResonanceAgent {
  agent_id: string;
  display_name: string;
  resonance_score: number;
}

export interface ResonanceActivatedData {
  [key: string]: unknown;
  activated_count: number;
  agents: ResonanceAgent[];
  filtered_agents: ResonanceAgent[];
}

export interface OfferReceivedData {
  [key: string]: unknown;
  agent_id: string;
  display_name: string;
  content: string;
  capabilities: string[];
}

export interface BarrierCompleteData {
  [key: string]: unknown;
  total_participants: number;
  offers_received: number;
  exited_count: number;
}

export interface CenterToolCallData {
  [key: string]: unknown;
  tool_name: string;
  tool_args: Record<string, unknown>;
  round_number: number;
}

export interface PlanJsonParticipant {
  agent_id: string;
  display_name: string;
  role_in_plan: string;
}

export interface PlanJsonTask {
  id: string;
  title: string;
  description: string;
  assignee_id: string;
  prerequisites: string[];
  status: string;
}

export interface PlanJson {
  summary?: string;
  participants: PlanJsonParticipant[];
  tasks: PlanJsonTask[];
  topology?: {
    edges: Array<{ from: string; to: string }>;
  };
}

export interface PlanReadyData {
  [key: string]: unknown;
  plan_text: string;
  center_rounds: number;
  participating_agents: string[];
  plan_json: PlanJson;
}

export interface SubNegotiationStartedData {
  [key: string]: unknown;
  sub_negotiation_id: string;
  gap_description: string;
}

// ============ Uniform Event ============

export interface NegotiationEvent {
  event_type: EventType;
  negotiation_id: string;
  timestamp: string;
  event_id: string | null;
  data: Record<string, unknown>;
}

// ============ Typed Event Helpers ============

export interface FormulationReadyEvent extends NegotiationEvent {
  event_type: 'formulation.ready';
  data: FormulationReadyData;
}

export interface ResonanceActivatedEvent extends NegotiationEvent {
  event_type: 'resonance.activated';
  data: ResonanceActivatedData;
}

export interface OfferReceivedEvent extends NegotiationEvent {
  event_type: 'offer.received';
  data: OfferReceivedData;
}

export interface BarrierCompleteEvent extends NegotiationEvent {
  event_type: 'barrier.complete';
  data: BarrierCompleteData;
}

export interface CenterToolCallEvent extends NegotiationEvent {
  event_type: 'center.tool_call';
  data: CenterToolCallData;
}

export interface PlanReadyEvent extends NegotiationEvent {
  event_type: 'plan.ready';
  data: PlanReadyData;
}

export interface SubNegotiationStartedEvent extends NegotiationEvent {
  event_type: 'sub_negotiation.started';
  data: SubNegotiationStartedData;
}

// ============ Negotiation Phase ============

export type NegotiationPhase =
  | 'idle'
  | 'submitting'
  | 'formulating'
  | 'confirming'        // user sees formulation, decides to confirm/edit
  | 'resonating'
  | 'collecting_offers'
  | 'barrier_met'
  | 'synthesizing'
  | 'plan_ready'
  | 'error';

// ============ Negotiation State ============

export interface NegotiationState {
  phase: NegotiationPhase;
  negotiationId: string | null;
  formulation: FormulationReadyData | null;
  resonanceAgents: ResonanceAgent[];
  filteredAgents: ResonanceAgent[];
  offers: OfferReceivedData[];
  barrierInfo: BarrierCompleteData | null;
  centerActivities: CenterToolCallData[];
  plan: PlanReadyData | null;
  subNegotiations: SubNegotiationStartedData[];
  events: NegotiationEvent[];  // full event log
  error: string | null;
}

// ============ Reducer Actions ============

export type NegotiationAction =
  | { type: 'SUBMIT_DEMAND' }
  | { type: 'SET_NEGOTIATION_ID'; negotiationId: string }
  | { type: 'EVENT_RECEIVED'; event: NegotiationEvent }
  | { type: 'SET_PHASE'; phase: NegotiationPhase }
  | { type: 'SET_ERROR'; error: string }
  | { type: 'RESET' };

// ============ API Types ============

export interface SubmitDemandRequest {
  scene_id: string;
  user_id: string;
  intent: string;
  k_star?: number;
  min_score?: number;
}

export interface SubmitDemandResponse {
  negotiation_id: string;
}

export interface ConfirmFormulationRequest {
  confirmed_text: string;
}

export interface UserActionRequest {
  action: 'accept' | 'modify' | 'reject' | 'cancel';
  payload?: Record<string, unknown>;
}
