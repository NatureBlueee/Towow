// ============ Request/Response Types ============

export interface DemandSubmitRequest {
  user_input: string;
  context?: DemandContext;
}

export interface DemandContext {
  location?: string;
  budget_range?: {
    min?: number;
    max?: number;
    currency?: string;
  };
  time_constraints?: {
    start?: string;
    end?: string;
    flexible?: boolean;
  };
  preferences?: Record<string, unknown>;
}

export interface DemandSubmitResponse {
  negotiation_id: string;
  status: NegotiationStatus;
  parsed_demand: ParsedDemand;
  initial_participants: Participant[];
  message: string;
}

export interface ParsedDemand {
  intent: string;
  entities: Entity[];
  constraints: Constraint[];
  raw_text: string;
}

export interface Entity {
  type: string;
  value: string;
  confidence: number;
}

export interface Constraint {
  type: string;
  value: unknown;
  priority: 'must_have' | 'nice_to_have' | 'flexible';
}

// ============ ToWow Negotiation Status ============

export type NegotiationStatus =
  | 'pending'
  | 'connecting'
  | 'filtering'
  | 'collecting'
  | 'aggregating'
  | 'negotiating'
  | 'finalized'
  | 'failed'
  | 'in_progress'
  | 'awaiting_user'
  | 'completed'
  | 'cancelled';

// ============ ToWow Candidate Types ============

export interface Candidate {
  agent_id: string;
  reason: string;
  capabilities?: string[];
  response?: CandidateResponse;
}

export interface CandidateResponse {
  decision: 'participate' | 'decline' | 'conditional';
  contribution?: string;
  conditions?: string[];
}

// ============ ToWow Proposal Types ============

export interface ToWowProposal {
  summary: string;
  assignments: ProposalAssignment[];
  timeline?: string;
  confidence?: 'high' | 'medium' | 'low';
}

export interface ProposalAssignment {
  agent_id: string;
  role: string;
  responsibility: string;
}

// ============ Participant Types ============

export interface Participant {
  agent_id: string;
  agent_type: string;
  display_name: string;
  avatar?: string;
  status: 'active' | 'thinking' | 'waiting' | 'done';
  capabilities: string[];
}

// ============ Legacy Proposal Types (kept for compatibility) ============

export interface Proposal {
  id: string;
  agent_id: string;
  content: ProposalContent;
  score?: number;
  status: 'pending' | 'accepted' | 'rejected' | 'modified';
  created_at: string;
  updated_at?: string;
}

export interface ProposalContent {
  type: string;
  title: string;
  description: string;
  details: Record<string, unknown>;
  price?: {
    amount: number;
    currency: string;
    breakdown?: Record<string, number>;
  };
}

// ============ Timeline Types ============

export interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type: TimelineEventType;
  agent_id?: string;
  content: TimelineContent;
  metadata?: Record<string, unknown>;
}

export type TimelineEventType =
  | 'negotiation_started'
  | 'agent_joined'
  | 'agent_thinking'
  | 'agent_proposal'
  | 'agent_message'
  | 'user_feedback'
  | 'proposal_accepted'
  | 'proposal_rejected'
  | 'negotiation_completed'
  | 'error'
  // ToWow specific event types
  | 'towow.demand.understood'
  | 'towow.demand.broadcast'
  | 'towow.filter.completed'
  | 'towow.offer.submitted'
  | 'towow.proposal.distributed'
  | 'towow.proposal.feedback'
  | 'towow.proposal.finalized'
  | 'towow.negotiation.failed';

export interface TimelineContent {
  message?: string;
  proposal?: Proposal;
  thinking_step?: string;
  error?: string;
}

// ============ SSE Event Types ============

export interface SSEEvent {
  event_id?: string;
  event_type: string;
  negotiation_id: string;
  timestamp: string;
  data?: SSEEventData;
  payload?: ToWowEventPayload;
}

export type SSEEventData =
  | AgentThinkingData
  | AgentProposalData
  | AgentMessageData
  | StatusUpdateData
  | ErrorData;

export interface AgentThinkingData {
  agent_id: string;
  step: string;
  progress?: number;
}

export interface AgentProposalData {
  agent_id: string;
  proposal: Proposal;
}

export interface AgentMessageData {
  agent_id: string;
  message: string;
}

export interface StatusUpdateData {
  status: NegotiationStatus;
  message?: string;
}

export interface ErrorData {
  error_code: string;
  error_message: string;
}

// ============ ToWow Event Payload Types ============

export type ToWowEventPayload =
  | DemandUnderstoodPayload
  | FilterCompletedPayload
  | OfferSubmittedPayload
  | ProposalDistributedPayload
  | ProposalFeedbackPayload
  | ProposalFinalizedPayload
  | NegotiationFailedPayload;

export interface DemandUnderstoodPayload {
  parsed_intent: string;
  entities: Entity[];
}

export interface FilterCompletedPayload {
  candidates: Candidate[];
  total_found: number;
}

export interface OfferSubmittedPayload {
  agent_id: string;
  decision: 'participate' | 'decline' | 'conditional';
  contribution?: string;
  conditions?: string[];
}

export interface ProposalDistributedPayload {
  proposal: ToWowProposal;
  round: number;
}

export interface ProposalFeedbackPayload {
  agent_id: string;
  feedback: 'accept' | 'reject' | 'counter';
  reason?: string;
  counter_proposal?: Partial<ToWowProposal>;
}

export interface ProposalFinalizedPayload {
  proposal: ToWowProposal;
  accepted_by: string[];
}

export interface NegotiationFailedPayload {
  reason: string;
  last_proposal?: ToWowProposal;
}

// ============ UI State Types ============

export interface NegotiationState {
  negotiationId: string | null;
  status: NegotiationStatus;
  participants: Participant[];
  candidates: Candidate[];
  proposals: Proposal[];
  currentProposal: ToWowProposal | null;
  currentRound: number;
  timeline: TimelineEvent[];
  isLoading: boolean;
  error: string | null;
}

export interface DemandState {
  currentDemand: DemandSubmitRequest | null;
  parsedDemand: ParsedDemand | null;
  isSubmitting: boolean;
  submitError: string | null;
}
