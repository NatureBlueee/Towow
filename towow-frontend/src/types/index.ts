// ============ Request/Response Types ============

export interface DemandSubmitRequest {
  raw_input: string;          // 后端期望 raw_input 字段
  user_id?: string;           // 可选的用户ID
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
  demand_id: string;          // 后端返回 demand_id
  channel_id: string;         // 后端返回 channel_id
  status: string;
  understanding: {            // 后端返回 understanding 对象
    surface_demand: string;
    confidence: string;
  };
  // 兼容字段：前端可能还在使用 negotiation_id
  negotiation_id?: string;
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

/**
 * 候选人决策类型
 * - participate: 同意参与
 * - decline: 拒绝参与
 * - conditional: 有条件参与
 * - withdrawn: 主动退出（已加入后退出）
 * - kicked: 被踢出
 */
export type CandidateDecision = 'participate' | 'decline' | 'conditional' | 'withdrawn' | 'kicked';

export interface Candidate {
  agent_id: string;
  reason: string;
  capabilities?: string[];
  response?: CandidateResponse;
}

export interface CandidateResponse {
  decision: CandidateDecision;
  contribution?: string;
  conditions?: string[];
  // 拒绝/退出/被踢原因
  decline_reason?: string;
  withdrawn_reason?: string;
  kicked_reason?: string;
  kicked_by?: string;
  // 时间戳
  responded_at?: string;
  withdrawn_at?: string;
  kicked_at?: string;
  // M1 修复: 补充后端返回的字段
  enthusiasm_level?: 'high' | 'medium' | 'low';
  suggested_role?: string;
  availability_note?: string;
  match_analysis?: string;
}

// ============ ToWow Proposal Types ============

export interface ProposalTimeline {
  start_date?: string;
  end_date?: string;
  milestones?: Array<{
    name: string;
    date: string;
    deliverable?: string;
  }>;
}

export interface ToWowProposal {
  summary: string;
  assignments: ProposalAssignment[];
  timeline?: string | ProposalTimeline;
  confidence?: 'high' | 'medium' | 'low';
  success_criteria?: string[];
}

export interface ProposalAssignment {
  agent_id: string;
  role: string;
  responsibility: string;
  display_name?: string;
  avatar?: string;
  status?: 'confirmed' | 'pending' | 'conditional';
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
  | 'towow.demand.submitted'
  | 'towow.demand.broadcast'
  | 'towow.filter.completed'
  | 'towow.offer.submitted'
  | 'towow.proposal.distributed'
  | 'towow.proposal.feedback'
  | 'towow.proposal.finalized'
  | 'towow.negotiation.failed'
  // TASK-A3 新增事件类型
  | 'towow.agent.withdrawn'          // Agent主动退出
  | 'towow.agent.kicked'             // 被踢出协商
  | 'towow.negotiation.bargain'      // 讨价还价
  | 'towow.negotiation.counter_proposal';  // 反提案

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
  | NegotiationFailedPayload
  // M3 修复: 添加新增的 payload 类型
  | BargainPayload
  | CounterProposalPayload
  | WithdrawnPayload
  | KickedPayload;

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
  decision: CandidateDecision;
  contribution?: string;
  conditions?: string[];
  decline_reason?: string;
  // M1 修复: 补充后端返回的字段
  enthusiasm_level?: 'high' | 'medium' | 'low';
  suggested_role?: string;
  availability_note?: string;
  match_analysis?: string;
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

// M3 修复: 新增事件 payload 类型

// 讨价还价事件 payload
export interface BargainPayload {
  agent_id: string;
  agent_name?: string;
  offer?: string;
  original_terms?: Record<string, unknown>;
  new_terms?: Record<string, unknown>;
  original_price?: number;
  new_price?: number;
  demand_id?: string;
}

// 反提案事件 payload
export interface CounterProposalPayload {
  agent_id: string;
  agent_name?: string;
  counter_proposal?: ToWowProposal;
  reason?: string;
  demand_id?: string;
}

// 退出事件 payload
export interface WithdrawnPayload {
  agent_id: string;
  agent_name?: string;
  reason?: string;
  withdrawn_at?: string;
  demand_id?: string;
  channel_id?: string;
}

// 踢出事件 payload
export interface KickedPayload {
  agent_id: string;
  agent_name?: string;
  reason?: string;
  kicked_by?: string;
  kicked_at?: string;
  demand_id?: string;
  channel_id?: string;
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
