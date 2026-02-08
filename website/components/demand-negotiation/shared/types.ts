// Experience V2 - Shared Types

export type DemoStage =
  | 'input'       // Stage 1: 需求输入
  | 'response'    // Stage 2: Agent响应
  | 'negotiation' // Stage 3: 协商过程
  | 'proposal'    // Stage 4: 方案展示
  | 'summary';    // Stage 5: 过程汇总

// Network Graph V2 Phases (within Stage 2)
export type NetworkPhase =
  | 'idle'        // Initial state
  | 'launch'      // Requirement shrinks and launches
  | 'broadcast'   // Waves scan outward
  | 'scan'        // Agents discovered
  | 'classify'    // Agents get colored (green/red/gray)
  | 'converge'    // Green agents form circle
  | 'respond'     // Agents show responses (user controlled)
  | 'negotiate'   // Information flows to center
  | 'filter'      // Some agents disconnected
  | 'deep'        // Peer-to-peer negotiation
  | 'proposal'    // Final arrangement
  | 'complete';   // Done

// Agent classification status
export type AgentStatus = 'willing' | 'notMatch' | 'observing' | 'filtered' | 'final';

// Extended Agent with status
export interface AgentWithStatus extends Agent {
  status: AgentStatus;
  position?: { x: number; y: number };
  response?: AgentResponse;
}

// Agent response types
export type ResponseType = 'competition' | 'offer' | 'suggestion';

export interface AgentResponse {
  type: ResponseType;
  title: string;
  content: string;
  conditions?: string[];
  price?: number;
}

export interface StageInfo {
  id: DemoStage;
  label: string;
  description: string;
}

// Stage label/description keys — looked up at render time via useTranslations('DemandNegotiation.stages')
export const STAGES: StageInfo[] = [
  { id: 'input', label: 'input', description: 'inputDesc' },
  { id: 'response', label: 'response', description: 'responseDesc' },
  { id: 'negotiation', label: 'negotiation', description: 'negotiationDesc' },
  { id: 'proposal', label: 'proposal', description: 'proposalDesc' },
  { id: 'summary', label: 'summary', description: 'summaryDesc' },
];

// Agent Types
export interface Agent {
  id: string;
  name: string;
  avatar?: string;
  role: string;
  description: string;
  skills: string[];
  initialResponse?: string;
  bio?: AgentBio; // SecondMe bio data
}

// Agent Bio from SecondMe
export interface AgentBio {
  summary: string;
  expertise: string[];
  experience: string;
  style: string;
}

// Network Graph Types
export interface NetworkNode {
  id: string;
  type: 'center' | 'agent';
  x: number;
  y: number;
  agent?: Agent;
}

export interface NetworkConnection {
  from: string;
  to: string;
  active?: boolean;
  speaking?: boolean;
}

// Event Card Types
export type EventCardType = 'insight' | 'transform' | 'combine' | 'confirm';

export interface EventCard {
  id: string;
  type: EventCardType;
  title: string;
  content: string;
  timestamp: number;
  agents?: string[]; // Agent IDs involved
  expanded?: boolean;
}

// Proposal Types
export interface ProposalStep {
  id: string;
  order: number;
  agentId: string;
  agentName: string;
  description: string;
  price?: number;
  duration?: string;
}

export interface Proposal {
  steps: ProposalStep[];
  totalCost: number;
  originalCost: number;
  participants: Agent[];
}

// Summary Types
export interface TimelineEvent {
  id: string;
  stage: DemoStage;
  timestamp: number;
  label: string;
}

export interface KeyInsight {
  type: 'insight' | 'transform' | 'discovery';
  title: string;
  content: string;
}

// Demo State
export interface DemoState {
  currentStage: DemoStage;
  requirement: string;
  agents: Agent[];
  events: EventCard[];
  proposal: Proposal | null;
  insights: KeyInsight[];
  isPlaying: boolean;
  playbackSpeed: number;
}

// Example Requirements
export interface ExampleRequirement {
  id: string;
  text: string;
  category: string;
}

// Example keys — looked up at render time via useTranslations('DemandNegotiation.input')
export const EXAMPLE_REQUIREMENTS: ExampleRequirement[] = [
  {
    id: '1',
    text: 'exampleStartupText',
    category: 'exampleStartup',
  },
  {
    id: '2',
    text: 'exampleMarketingText',
    category: 'exampleMarketing',
  },
  {
    id: '3',
    text: 'exampleEventText',
    category: 'exampleEvent',
  },
];
