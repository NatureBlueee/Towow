import { create } from 'zustand';
import type {
  NegotiationState,
  NegotiationStatus,
  Participant,
  Proposal,
  TimelineEvent,
  Candidate,
  ToWowProposal,
  SSEEvent,
  ProposalAssignment,
  CandidateDecision,
  FeedbackResult,
  ForceFinalizationInfo,
} from '../types';

// ============ Runtime Type Validators ============

function isValidCandidate(obj: unknown): obj is Candidate {
  if (!obj || typeof obj !== 'object') return false;
  const candidate = obj as Record<string, unknown>;
  return (
    typeof candidate.agent_id === 'string' &&
    typeof candidate.reason === 'string'
  );
}

function validateCandidates(candidates: unknown): Candidate[] {
  if (!Array.isArray(candidates)) return [];
  return candidates.filter(isValidCandidate);
}

function isValidProposalAssignment(obj: unknown): obj is ProposalAssignment {
  if (!obj || typeof obj !== 'object') return false;
  const assignment = obj as Record<string, unknown>;
  return (
    typeof assignment.agent_id === 'string' &&
    typeof assignment.role === 'string' &&
    typeof assignment.responsibility === 'string'
  );
}

function isValidToWowProposal(obj: unknown): obj is ToWowProposal {
  if (!obj || typeof obj !== 'object') return false;
  const proposal = obj as Record<string, unknown>;
  if (typeof proposal.summary !== 'string') return false;
  if (!Array.isArray(proposal.assignments)) return false;
  return proposal.assignments.every(isValidProposalAssignment);
}

function validateToWowProposal(proposal: unknown): ToWowProposal | null {
  return isValidToWowProposal(proposal) ? proposal : null;
}

function isValidDecision(
  decision: unknown
): decision is CandidateDecision {
  return (
    decision === 'participate' ||
    decision === 'decline' ||
    decision === 'conditional' ||
    decision === 'withdrawn' ||
    decision === 'kicked'
  );
}

function isValidProposal(obj: unknown): obj is Proposal {
  if (!obj || typeof obj !== 'object') return false;
  const proposal = obj as Record<string, unknown>;
  return (
    typeof proposal.id === 'string' &&
    typeof proposal.agent_id === 'string' &&
    typeof proposal.content === 'object' &&
    proposal.content !== null
  );
}

// ============ Store Interface ============

interface EventStore extends NegotiationState {
  // Setters
  setNegotiationId: (id: string | null) => void;
  setStatus: (status: NegotiationStatus) => void;
  setParticipants: (participants: Participant[]) => void;
  setCandidates: (candidates: Candidate[]) => void;
  setCurrentProposal: (proposal: ToWowProposal | null) => void;
  setCurrentRound: (round: number) => void;
  setMaxRounds: (maxRounds: number) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;

  // v4 新增 setters
  setForceFinalized: (isForceFinalized: boolean, info?: ForceFinalizationInfo | null) => void;
  addFeedbackResult: (result: FeedbackResult) => void;

  // Updaters
  updateParticipant: (agentId: string, updates: Partial<Participant>) => void;
  updateCandidateResponse: (
    agentId: string,
    response: Candidate['response']
  ) => void;
  addProposal: (proposal: Proposal) => void;
  updateProposal: (proposalId: string, updates: Partial<Proposal>) => void;
  addTimelineEvent: (event: TimelineEvent) => void;

  // SSE Event Handler
  handleSSEEvent: (event: SSEEvent) => void;

  // Reset
  reset: () => void;
}

const initialState: NegotiationState = {
  negotiationId: null,
  status: 'pending',
  participants: [],
  candidates: [],
  proposals: [],
  currentProposal: null,
  currentRound: 0,
  maxRounds: 5,  // v4: 默认最大轮次为 5
  timeline: [],
  isLoading: false,
  error: null,
  // v4 新增字段
  isForceFinalized: false,
  forceFinalizationInfo: null,
  feedbackResults: [],
};

export const useEventStore = create<EventStore>((set) => ({
  ...initialState,

  setNegotiationId: (id) => set({ negotiationId: id }),

  setStatus: (status) => set({ status }),

  setParticipants: (participants) => set({ participants }),

  setCandidates: (candidates) => set({ candidates }),

  setCurrentProposal: (proposal) => set({ currentProposal: proposal }),

  setCurrentRound: (round) => set({ currentRound: round }),

  setMaxRounds: (maxRounds) => set({ maxRounds }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  // v4 新增 setters
  setForceFinalized: (isForceFinalized, info = null) => set({
    isForceFinalized,
    forceFinalizationInfo: info,
  }),

  addFeedbackResult: (result) =>
    set((state) => ({
      feedbackResults: [...state.feedbackResults, result],
    })),

  updateParticipant: (agentId, updates) =>
    set((state) => ({
      participants: state.participants.map((p) =>
        p.agent_id === agentId ? { ...p, ...updates } : p
      ),
    })),

  updateCandidateResponse: (agentId, response) =>
    set((state) => ({
      candidates: state.candidates.map((c) =>
        c.agent_id === agentId ? { ...c, response } : c
      ),
    })),

  addProposal: (proposal) =>
    set((state) => ({
      proposals: [...state.proposals, proposal],
    })),

  updateProposal: (proposalId, updates) =>
    set((state) => ({
      proposals: state.proposals.map((p) =>
        p.id === proposalId ? { ...p, ...updates } : p
      ),
    })),

  addTimelineEvent: (event) =>
    set((state) => ({
      timeline: [...state.timeline, event],
    })),

  handleSSEEvent: (event) => {
    console.log('[EventStore] handleSSEEvent called, event_type:', event.event_type);
    set((state) => {
      // Create new state object to accumulate all changes
      const newState: Partial<NegotiationState> = {};

      // Create timeline event
      const timelineEvent: TimelineEvent = {
        id: event.event_id || `${event.event_type}-${Date.now()}`,
        timestamp: event.timestamp,
        event_type: event.event_type as TimelineEvent['event_type'],
        content: {},
      };

      // Handle ToWow protocol events
      const payload = event.payload as Record<string, unknown> | undefined;
      console.log('[EventStore] Processing event:', event.event_type, 'payload:', payload);

      switch (event.event_type) {
        case 'towow.demand.understood':
          console.log('[EventStore] Demand understood, setting status to filtering');
          newState.status = 'filtering';
          timelineEvent.content.message =
            'Demand understood, filtering candidates...';
          break;

        case 'towow.demand.broadcast':
          console.log('[EventStore] Demand broadcast');
          timelineEvent.content.message = 'Demand broadcast to network';
          break;

        case 'towow.filter.completed': {
          const validatedCandidates = validateCandidates(payload?.candidates);
          console.log('[EventStore] Filter completed, candidates:', validatedCandidates.length);
          newState.status = 'collecting';
          newState.candidates = validatedCandidates;
          timelineEvent.content.message = `Found ${validatedCandidates.length} candidates`;
          break;
        }

        case 'towow.offer.submitted':
          if (payload?.agent_id && typeof payload.agent_id === 'string') {
            const agentId = payload.agent_id;
            const decision = payload.decision;

            if (isValidDecision(decision)) {
              const conditions = Array.isArray(payload.conditions)
                ? payload.conditions.filter(
                    (c): c is string => typeof c === 'string'
                  )
                : undefined;

              // M1 修复: 补充字段提取
              const enthusiasmLevel =
                payload.enthusiasm_level === 'high' ||
                payload.enthusiasm_level === 'medium' ||
                payload.enthusiasm_level === 'low'
                  ? payload.enthusiasm_level
                  : undefined;
              const suggestedRole =
                typeof payload.suggested_role === 'string'
                  ? payload.suggested_role
                  : undefined;
              const availabilityNote =
                typeof payload.availability_note === 'string'
                  ? payload.availability_note
                  : undefined;
              const matchAnalysis =
                typeof payload.match_analysis === 'string'
                  ? payload.match_analysis
                  : undefined;

              newState.candidates = state.candidates.map((c) =>
                c.agent_id === agentId
                  ? {
                      ...c,
                      response: {
                        decision,
                        contribution:
                          typeof payload.contribution === 'string'
                            ? payload.contribution
                            : undefined,
                        conditions,
                        // M1 修复: 添加新字段
                        enthusiasm_level: enthusiasmLevel,
                        suggested_role: suggestedRole,
                        availability_note: availabilityNote,
                        match_analysis: matchAnalysis,
                      },
                    }
                  : c
              );
            }

            timelineEvent.agent_id = agentId;
            timelineEvent.content.message = `Response from ${agentId.replace('user_agent_', '')}`;
          }
          break;

        case 'towow.proposal.distributed': {
          const validatedProposal = validateToWowProposal(payload?.proposal);
          const round =
            typeof payload?.round === 'number' ? payload.round : 1;

          console.log('[EventStore] Proposal distributed, round:', round, 'proposal valid:', !!validatedProposal);
          newState.status = 'negotiating';
          newState.currentProposal = validatedProposal;
          newState.currentRound = round;
          timelineEvent.content.message = `Proposal round ${round} distributed`;
          break;
        }

        case 'towow.proposal.feedback':
          if (payload?.agent_id && typeof payload.agent_id === 'string') {
            const agentId = payload.agent_id;
            console.log('[EventStore] Proposal feedback from:', agentId, 'type:', payload.feedback);
            timelineEvent.agent_id = agentId;
            timelineEvent.content.message = `Feedback: ${payload.feedback} from ${agentId.replace('user_agent_', '')}`;
          }
          break;

        case 'towow.proposal.finalized': {
          const validatedProposal = validateToWowProposal(payload?.proposal);
          console.log('[EventStore] Proposal finalized, setting status to finalized');
          newState.status = 'finalized';
          newState.currentProposal = validatedProposal;
          timelineEvent.content.message = 'Negotiation finalized';
          break;
        }

        case 'towow.negotiation.failed': {
          const reason =
            typeof payload?.reason === 'string'
              ? payload.reason
              : 'Negotiation failed';
          console.log('[EventStore] Negotiation failed:', reason);
          newState.status = 'failed';
          newState.error = reason;
          timelineEvent.content.message = reason;
          timelineEvent.content.error = reason;
          break;
        }

        // TASK-A3: 新增事件类型处理
        case 'towow.agent.withdrawn':
          if (payload?.agent_id && typeof payload.agent_id === 'string') {
            const agentId = payload.agent_id;
            const reason = typeof payload.reason === 'string' ? payload.reason : '主动退出';

            // 更新候选人状态
            newState.candidates = state.candidates.map((c) =>
              c.agent_id === agentId
                ? {
                    ...c,
                    response: {
                      ...c.response,
                      decision: 'withdrawn' as const,
                      withdrawn_reason: reason,
                      withdrawn_at: event.timestamp,
                    },
                  }
                : c
            );

            timelineEvent.agent_id = agentId;
            timelineEvent.content.message = `${agentId.replace('user_agent_', '')} 退出了协商: ${reason}`;
          }
          break;

        case 'towow.agent.kicked':
          if (payload?.agent_id && typeof payload.agent_id === 'string') {
            const agentId = payload.agent_id;
            const reason = typeof payload.reason === 'string' ? payload.reason : '被踢出';
            const kickedBy = typeof payload.kicked_by === 'string' ? payload.kicked_by : undefined;

            // 更新候选人状态
            newState.candidates = state.candidates.map((c) =>
              c.agent_id === agentId
                ? {
                    ...c,
                    response: {
                      ...c.response,
                      decision: 'kicked' as const,
                      kicked_reason: reason,
                      kicked_by: kickedBy,
                      kicked_at: event.timestamp,
                    },
                  }
                : c
            );

            timelineEvent.agent_id = agentId;
            timelineEvent.content.message = `${agentId.replace('user_agent_', '')} 被踢出协商: ${reason}`;
          }
          break;

        case 'towow.negotiation.bargain':
          if (payload?.agent_id && typeof payload.agent_id === 'string') {
            const agentId = payload.agent_id;
            const offer = typeof payload.offer === 'string' ? payload.offer : '';
            const originalPrice = payload.original_price;
            const newPrice = payload.new_price;

            timelineEvent.agent_id = agentId;
            if (originalPrice !== undefined && newPrice !== undefined) {
              timelineEvent.content.message = `${agentId.replace('user_agent_', '')} 发起讨价还价: ${originalPrice} -> ${newPrice}`;
            } else {
              timelineEvent.content.message = `${agentId.replace('user_agent_', '')} 发起讨价还价: ${offer}`;
            }
          }
          break;

        case 'towow.negotiation.counter_proposal':
          if (payload?.agent_id && typeof payload.agent_id === 'string') {
            const agentId = payload.agent_id;
            const counterProposal = validateToWowProposal(payload.counter_proposal);
            const reason = typeof payload.reason === 'string' ? payload.reason : '';

            timelineEvent.agent_id = agentId;
            if (counterProposal) {
              newState.currentProposal = counterProposal;
              timelineEvent.content.message = `${agentId.replace('user_agent_', '')} 提交了反提案: ${counterProposal.summary}`;
            } else {
              timelineEvent.content.message = `${agentId.replace('user_agent_', '')} 提交了反提案${reason ? `: ${reason}` : ''}`;
            }
          }
          break;

        // T07 新增事件类型处理
        case 'towow.feedback.evaluated': {
          // 支持两种格式：批量评估结果或单个 Agent 反馈
          const agentId = typeof payload?.agent_id === 'string' ? payload.agent_id : undefined;

          if (agentId) {
            // 单个 Agent 反馈评估
            const responseType = payload?.response_type === 'offer' || payload?.response_type === 'negotiate'
              ? payload.response_type
              : 'offer';
            const evaluation = payload?.evaluation === 'accept' || payload?.evaluation === 'reject' || payload?.evaluation === 'conditional'
              ? payload.evaluation
              : 'accept';

            // 添加到反馈结果列表
            const feedbackResult: FeedbackResult = {
              agent_id: agentId,
              response_type: responseType,
              evaluation: evaluation,
              timestamp: event.timestamp,
            };
            newState.feedbackResults = [...state.feedbackResults, feedbackResult];

            const displayName = agentId.replace('user_agent_', '');
            const evaluationText = evaluation === 'accept' ? '接受' : evaluation === 'reject' ? '拒绝' : '有条件接受';
            const typeText = responseType === 'offer' ? '报价' : '协商';
            timelineEvent.agent_id = agentId;
            timelineEvent.content.message = `${displayName} 的${typeText}反馈：${evaluationText}`;
          } else {
            // 批量评估结果（保持向后兼容）
            const accepts = typeof payload?.accepts === 'number' ? payload.accepts : 0;
            const rejects = typeof payload?.rejects === 'number' ? payload.rejects : 0;
            const negotiates = typeof payload?.negotiates === 'number' ? payload.negotiates : 0;
            const acceptRate = typeof payload?.accept_rate === 'number' ? payload.accept_rate : 0;
            const round = typeof payload?.round === 'number' ? payload.round : state.currentRound;

            newState.currentRound = round;
            timelineEvent.content.message = `反馈评估完成：${accepts} 接受，${rejects} 拒绝，${negotiates} 协商 (接受率 ${(acceptRate * 100).toFixed(0)}%)`;
          }
          break;
        }

        case 'towow.gap.identified': {
          const gaps = Array.isArray(payload?.gaps) ? payload.gaps : [];
          const gapTypes = gaps.map((g: { gap_type?: string }) => g.gap_type || '未知').join('、');
          timelineEvent.content.message = gaps.length > 0
            ? `识别到 ${gaps.length} 个缺口：${gapTypes}`
            : '未识别到缺口';
          break;
        }

        case 'towow.subnet.triggered': {
          const gapType = typeof payload?.gap_type === 'string' ? payload.gap_type : '未知';
          const subDemandId = typeof payload?.sub_demand_id === 'string' ? payload.sub_demand_id : '';
          timelineEvent.content.message = `子网协商已触发：${gapType}${subDemandId ? ` (${subDemandId})` : ''}`;
          break;
        }

        case 'towow.negotiation.round_started': {
          const round = typeof payload?.round === 'number' ? payload.round : 1;
          const maxRounds = typeof payload?.max_rounds === 'number' ? payload.max_rounds : 5;
          newState.currentRound = round;
          newState.maxRounds = maxRounds;  // v4: 更新最大轮次
          newState.status = 'negotiating';
          // v4: 第 5 轮显示"最终轮"
          const roundLabel = round === maxRounds ? '最终轮' : `第 ${round} 轮`;
          timelineEvent.content.message = `${roundLabel}协商开始 (${round}/${maxRounds})`;
          break;
        }

        // v4 新增: 强制终结事件
        case 'towow.negotiation.force_finalized': {
          const acceptedAgents = Array.isArray(payload?.accepted_agents) ? payload.accepted_agents : [];
          const pendingAgents = Array.isArray(payload?.pending_agents) ? payload.pending_agents : [];
          const compromiseProposal = validateToWowProposal(payload?.compromise_proposal);

          newState.status = 'finalized';
          newState.isForceFinalized = true;
          newState.currentProposal = compromiseProposal;
          newState.forceFinalizationInfo = {
            accepted_agents: acceptedAgents,
            pending_agents: pendingAgents,
            compromise_proposal: compromiseProposal,
            finalized_at: event.timestamp,
          };

          const acceptedCount = acceptedAgents.length;
          const pendingCount = pendingAgents.length;
          timelineEvent.content.message = `协商强制终结：${acceptedCount} 人接受，${pendingCount} 人未完全接受（已生成妥协方案）`;
          break;
        }

        // Handle legacy event types
        case 'agent_thinking':
          if (
            event.data &&
            'agent_id' in event.data &&
            'step' in event.data &&
            typeof event.data.agent_id === 'string'
          ) {
            const agentId = event.data.agent_id;
            newState.participants = state.participants.map((p) =>
              p.agent_id === agentId ? { ...p, status: 'thinking' } : p
            );
            timelineEvent.agent_id = agentId;
            timelineEvent.content.thinking_step = event.data.step;
          }
          break;

        case 'agent_proposal':
          if (
            event.data &&
            'agent_id' in event.data &&
            'proposal' in event.data &&
            typeof event.data.agent_id === 'string'
          ) {
            const agentId = event.data.agent_id;
            newState.participants = state.participants.map((p) =>
              p.agent_id === agentId ? { ...p, status: 'active' } : p
            );

            if (isValidProposal(event.data.proposal)) {
              newState.proposals = [...state.proposals, event.data.proposal];
              timelineEvent.content.proposal = event.data.proposal;
            }

            timelineEvent.agent_id = agentId;
          }
          break;

        case 'agent_message':
          if (
            event.data &&
            'agent_id' in event.data &&
            'message' in event.data &&
            typeof event.data.agent_id === 'string' &&
            typeof event.data.message === 'string'
          ) {
            timelineEvent.agent_id = event.data.agent_id;
            timelineEvent.content.message = event.data.message;
          }
          break;

        case 'status_update':
          if (event.data && 'status' in event.data) {
            newState.status = event.data.status;
            if ('message' in event.data && typeof event.data.message === 'string') {
              timelineEvent.content.message = event.data.message;
            }
          }
          break;

        case 'error':
          if (
            event.data &&
            'error_message' in event.data &&
            typeof event.data.error_message === 'string'
          ) {
            newState.error = event.data.error_message;
            timelineEvent.content.error = event.data.error_message;
          }
          break;
      }

      // Add timeline event - always include this in the single state update
      newState.timeline = [...state.timeline, timelineEvent];

      console.log('[EventStore] State update:', {
        event_type: event.event_type,
        newStatus: newState.status,
        candidatesCount: newState.candidates?.length,
        timelineLength: newState.timeline?.length
      });

      return newState;
    });
  },

  reset: () => set(initialState),
}));
