import { create } from 'zustand';
import type {
  NegotiationState,
  NegotiationStatus,
  Participant,
  Proposal,
  TimelineEvent,
} from '../types';

interface EventStore extends NegotiationState {
  setNegotiationId: (id: string | null) => void;
  setStatus: (status: NegotiationStatus) => void;
  setParticipants: (participants: Participant[]) => void;
  updateParticipant: (agentId: string, updates: Partial<Participant>) => void;
  addProposal: (proposal: Proposal) => void;
  updateProposal: (proposalId: string, updates: Partial<Proposal>) => void;
  addTimelineEvent: (event: TimelineEvent) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState: NegotiationState = {
  negotiationId: null,
  status: 'pending',
  participants: [],
  proposals: [],
  timeline: [],
  isLoading: false,
  error: null,
};

export const useEventStore = create<EventStore>((set) => ({
  ...initialState,

  setNegotiationId: (id) => set({ negotiationId: id }),

  setStatus: (status) => set({ status }),

  setParticipants: (participants) => set({ participants }),

  updateParticipant: (agentId, updates) =>
    set((state) => ({
      participants: state.participants.map((p) =>
        p.agent_id === agentId ? { ...p, ...updates } : p
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

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  reset: () => set(initialState),
}));
