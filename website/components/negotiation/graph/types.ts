/**
 * Shared types for the negotiation graph visualization.
 * All graph components import from this file to ensure interface consistency.
 *
 * Layout: SVG viewBox 0 0 800 600, radial layout.
 * - Demand node: center (400, 300)
 * - Agent nodes: radius R=220 circle, starting from top (-PI/2)
 * - Center node: materializes at (400, 300) after barrier.complete
 * - Task nodes: inner ring R=120 during plan phase
 */

import type {
  NegotiationPhase,
  NegotiationState,
  ResonanceAgent,
  OfferReceivedData,
  CenterToolCallData,
  PlanJson,
  PlanJsonTask,
} from '@/types/negotiation';

// ============ Layout Types ============

export interface NodePosition {
  id: string;
  x: number;
  y: number;
  type: 'demand' | 'agent' | 'center' | 'task';
}

export interface EdgeDef {
  id: string;
  from: string; // node id
  to: string;   // node id
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  type: 'resonance' | 'interaction' | 'task_dependency';
  /** Interaction sub-type (only for type='interaction') */
  interactionType?: 'ask_agent' | 'discover' | 'task_assignment';
  /** Display label (question text, discovery reason, task name) */
  label?: string;
}

export interface LayoutResult {
  nodes: NodePosition[];
  edges: EdgeDef[];
}

// ============ Node Component Props ============

export interface DemandNodeProps {
  x: number;
  y: number;
  text: string;
  phase: NegotiationPhase;
  onClick: () => void;
}

export interface AgentNodeProps {
  x: number;
  y: number;
  agentId: string;
  displayName: string;
  score: number;
  isFiltered: boolean;
  hasOffer: boolean;
  offerContent?: string;
  roleInPlan?: string;
  onClick: () => void;
}

export interface CenterNodeProps {
  x: number;
  y: number;
  visible: boolean;
  isSynthesizing: boolean;
  roundNumber: number;
  onClick: () => void;
}

// ============ Edge Component Props ============

export interface ResonanceEdgeProps {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  score: number;
  isActive: boolean;
  hasOffer: boolean;
  onClick?: () => void;
}

export interface InteractionEdgeProps {
  id: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  interactionType: 'ask_agent' | 'discover' | 'task_assignment';
  label?: string;
  animate: boolean;
  onClick?: () => void;
}

// ============ Panel Props ============

export type DetailPanelContentType =
  | 'agent'
  | 'center'
  | 'demand'
  | 'task'
  | 'resonance_edge'
  | 'interaction_edge'
  | null;

export interface DetailPanelProps {
  type: DetailPanelContentType;
  data: Record<string, unknown> | null;
  onClose: () => void;
}

export interface PlanViewProps {
  planText: string;
  planJson: PlanJson;
  onAccept?: () => void;
  onReject?: () => void;
  onTaskClick: (taskId: string) => void;
}

// ============ Graph Container Props ============

export interface NegotiationGraphProps {
  state: NegotiationState;
  onNodeClick: (nodeType: 'demand' | 'agent' | 'center', id: string) => void;
  onEdgeClick: (edgeId: string) => void;
  onTaskClick: (taskId: string) => void;
}

// ============ Animation Queue ============

export interface AnimationItem {
  id: string;
  type: 'resonance_wave' | 'agent_appear' | 'agent_filter' | 'offer_arrive'
    | 'barrier_form' | 'center_appear' | 'ask_agent' | 'discover'
    | 'sub_demand' | 'output_plan' | 'plan_ready';
  data: Record<string, unknown>;
  duration: number; // ms
}

// ============ Layout Constants ============

export const GRAPH_WIDTH = 800;
export const GRAPH_HEIGHT = 600;

// Vertical flow layout — demand top, agents middle band, center lower
export const DEMAND_X = 400;
export const DEMAND_Y = 105;
export const AGENT_Y = 285;
export const AGENT_MIN_X = 130;
export const AGENT_MAX_X = 670;
export const CENTER_NODE_X = 400;
export const CENTER_NODE_Y = 465;
export const TASK_Y = 555;
export const TASK_MIN_X = 170;
export const TASK_MAX_X = 630;

// Legacy aliases (ResonanceWaveRipple ripples from demand position)
export const CENTER_X = DEMAND_X;
export const CENTER_Y = DEMAND_Y;
export const AGENT_RING_RADIUS = 220;
export const TASK_RING_RADIUS = 120;
export const START_ANGLE = -Math.PI / 2;
