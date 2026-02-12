/**
 * Mock events for all 7 V1 event types.
 * Used for frontend development without backend and for testing event parsing.
 */

import type { NegotiationEvent } from '@/types/negotiation';

const MOCK_NEGOTIATION_ID = 'neg_mock001';

export const mockFormulationReady: NegotiationEvent = {
  event_type: 'formulation.ready',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_001',
  data: {
    raw_intent: 'I need someone who can help me build an MVP for my startup idea',
    formulated_text:
      'Looking for a technical partner with full-stack development experience, ' +
      'capable of rapid prototyping and MVP delivery. Key requirements: ' +
      'React/Next.js frontend, Python backend, experience with AI integration, ' +
      'and willingness to iterate quickly based on user feedback.',
    enrichments: {
      detected_skills: ['full-stack', 'React', 'Python', 'AI', 'MVP'],
      intent_category: 'technical_collaboration',
    },
    degraded: false,
    degraded_reason: '',
  },
};

export const mockResonanceActivated: NegotiationEvent = {
  event_type: 'resonance.activated',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_002',
  data: {
    activated_count: 4,
    agents: [
      { agent_id: 'agent_alice', display_name: 'Alice Chen', resonance_score: 0.92 },
      { agent_id: 'agent_bob', display_name: 'Bob Zhang', resonance_score: 0.87 },
      { agent_id: 'agent_carol', display_name: 'Carol Li', resonance_score: 0.78 },
      { agent_id: 'agent_dave', display_name: 'Dave Wang', resonance_score: 0.71 },
    ],
    filtered_agents: [
      { agent_id: 'agent_eve', display_name: 'Eve Zhao', resonance_score: 0.42 },
      { agent_id: 'agent_frank', display_name: 'Frank Liu', resonance_score: 0.35 },
    ],
  },
};

export const mockOfferAlice: NegotiationEvent = {
  event_type: 'offer.received',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_003a',
  data: {
    agent_id: 'agent_alice',
    display_name: 'Alice Chen',
    content:
      'I have 5 years of full-stack experience with React and Python. ' +
      'I have shipped 3 MVPs in the past year, including an AI-powered analytics tool. ' +
      'I can commit 20 hours per week and am excited about rapid iteration.',
    capabilities: ['React', 'Next.js', 'Python', 'FastAPI', 'AI/ML Integration'],
  },
};

export const mockOfferBob: NegotiationEvent = {
  event_type: 'offer.received',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_003b',
  data: {
    agent_id: 'agent_bob',
    display_name: 'Bob Zhang',
    content:
      'Senior backend engineer with strong Python and infrastructure skills. ' +
      'I can help set up the backend architecture, CI/CD pipeline, and cloud deployment. ' +
      'Available full-time for the next 3 months.',
    capabilities: ['Python', 'AWS', 'Docker', 'PostgreSQL', 'CI/CD'],
  },
};

export const mockOfferCarol: NegotiationEvent = {
  event_type: 'offer.received',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_003c',
  data: {
    agent_id: 'agent_carol',
    display_name: 'Carol Li',
    content:
      'Product designer and frontend developer. I can handle both the UX design ' +
      'and frontend implementation. Experience with user research and rapid prototyping.',
    capabilities: ['UX Design', 'React', 'Figma', 'User Research', 'Prototyping'],
  },
};

export const mockBarrierComplete: NegotiationEvent = {
  event_type: 'barrier.complete',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_004',
  data: {
    total_participants: 4,
    offers_received: 3,
    exited_count: 1,
  },
};

export const mockCenterToolCall1: NegotiationEvent = {
  event_type: 'center.tool_call',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_005a',
  data: {
    tool_name: 'ask_agent',
    tool_args: {
      agent_id: 'agent_alice',
      question: 'Can you elaborate on your AI integration experience?',
    },
    round_number: 1,
  },
};

export const mockCenterToolCall2: NegotiationEvent = {
  event_type: 'center.tool_call',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_005b',
  data: {
    tool_name: 'discover_connections',
    tool_args: {
      agent_ids: ['agent_alice', 'agent_bob', 'agent_carol'],
      reason: 'Alice and Bob have complementary backend skills that could strengthen the architecture',
    },
    round_number: 1,
  },
};

export const mockCenterToolCall3: NegotiationEvent = {
  event_type: 'center.tool_call',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_005c',
  data: {
    tool_name: 'ask_agent',
    tool_args: {
      agent_id: 'agent_bob',
      question: 'What is your experience with cloud infrastructure and CI/CD?',
    },
    round_number: 2,
  },
};

export const mockCenterToolCallSubDemand: NegotiationEvent = {
  event_type: 'center.tool_call',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_005d',
  data: {
    tool_name: 'create_sub_demand',
    tool_args: {
      gap_description: 'No DevOps expertise found among current participants.',
      context: { parent_negotiation_id: MOCK_NEGOTIATION_ID },
    },
    round_number: 2,
  },
};

export const mockSubNegotiationStarted: NegotiationEvent = {
  event_type: 'sub_negotiation.started',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_006',
  data: {
    sub_negotiation_id: 'neg_sub001',
    gap_description: 'No DevOps expertise found among current participants. Searching for infrastructure specialist.',
  },
};

export const mockCenterToolCallOutputPlan: NegotiationEvent = {
  event_type: 'center.tool_call',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_005e',
  data: {
    tool_name: 'output_plan',
    tool_args: {
      plan_text:
        'Recommended team composition:\n\n' +
        '1. Alice Chen (Lead Developer)\n2. Bob Zhang (Backend/Infra)\n3. Carol Li (Design/Frontend)',
      plan_json: {
        participants: [
          { agent_id: 'agent_alice', display_name: 'Alice Chen', role_in_plan: 'Lead Developer' },
          { agent_id: 'agent_bob', display_name: 'Bob Zhang', role_in_plan: 'Backend/Infra' },
          { agent_id: 'agent_carol', display_name: 'Carol Li', role_in_plan: 'Design/Frontend' },
        ],
      },
    },
    round_number: 2,
  },
};

export const mockPlanReady: NegotiationEvent = {
  event_type: 'plan.ready',
  negotiation_id: MOCK_NEGOTIATION_ID,
  timestamp: new Date().toISOString(),
  event_id: 'evt_007',
  data: {
    plan_text:
      'Recommended team composition:\n\n' +
      '1. Alice Chen (Lead Developer) - Full-stack development and AI integration\n' +
      '2. Bob Zhang (Backend/Infra) - Backend architecture and cloud deployment\n' +
      '3. Carol Li (Design/Frontend) - UX design and frontend implementation\n\n' +
      'Suggested timeline:\n' +
      '- Week 1-2: Requirements refinement and architecture design\n' +
      '- Week 3-4: Core MVP development sprint\n' +
      '- Week 5-6: User testing and iteration\n\n' +
      'Key risk: DevOps gap identified. A sub-negotiation has been initiated ' +
      'to find infrastructure support.',
    center_rounds: 2,
    participating_agents: ['agent_alice', 'agent_bob', 'agent_carol'],
    plan_json: {
      summary: 'Three-person team for rapid MVP development with complementary skills.',
      participants: [
        { agent_id: 'agent_alice', display_name: 'Alice Chen', role_in_plan: 'Lead Developer' },
        { agent_id: 'agent_bob', display_name: 'Bob Zhang', role_in_plan: 'Backend/Infra' },
        { agent_id: 'agent_carol', display_name: 'Carol Li', role_in_plan: 'Design/Frontend' },
      ],
      tasks: [
        {
          id: 'task_1',
          title: 'Architecture Design',
          description: 'Design system architecture and API contracts',
          assignee_id: 'agent_alice',
          prerequisites: [],
          status: 'pending',
        },
        {
          id: 'task_2',
          title: 'UX Wireframes',
          description: 'Create wireframes and user flow diagrams',
          assignee_id: 'agent_carol',
          prerequisites: [],
          status: 'pending',
        },
        {
          id: 'task_3',
          title: 'Backend MVP',
          description: 'Implement core backend APIs and database schema',
          assignee_id: 'agent_bob',
          prerequisites: ['task_1'],
          status: 'pending',
        },
        {
          id: 'task_4',
          title: 'Frontend MVP',
          description: 'Implement frontend based on wireframes and API contracts',
          assignee_id: 'agent_carol',
          prerequisites: ['task_1', 'task_2'],
          status: 'pending',
        },
        {
          id: 'task_5',
          title: 'AI Integration',
          description: 'Integrate AI features into the MVP',
          assignee_id: 'agent_alice',
          prerequisites: ['task_3'],
          status: 'pending',
        },
        {
          id: 'task_6',
          title: 'Testing & Launch',
          description: 'End-to-end testing and deployment',
          assignee_id: 'agent_bob',
          prerequisites: ['task_4', 'task_5'],
          status: 'pending',
        },
      ],
      topology: {
        edges: [
          { from: 'task_1', to: 'task_3' },
          { from: 'task_1', to: 'task_4' },
          { from: 'task_2', to: 'task_4' },
          { from: 'task_3', to: 'task_5' },
          { from: 'task_4', to: 'task_6' },
          { from: 'task_5', to: 'task_6' },
        ],
      },
    },
  },
};

/**
 * All mock events in chronological order for simulating a full negotiation flow.
 */
export const mockEventSequence: NegotiationEvent[] = [
  mockFormulationReady,
  mockResonanceActivated,
  mockOfferAlice,
  mockOfferBob,
  mockOfferCarol,
  mockBarrierComplete,
  mockCenterToolCall1,
  mockCenterToolCall2,
  mockCenterToolCall3,
  mockCenterToolCallSubDemand,
  mockSubNegotiationStarted,
  mockCenterToolCallOutputPlan,
  mockPlanReady,
];
