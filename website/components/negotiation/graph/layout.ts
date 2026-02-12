/**
 * Vertical-flow layout algorithm for the negotiation graph.
 *
 * Pure computation — no React, no side effects.
 * Input: NegotiationState  ->  Output: LayoutResult (positioned nodes + edges)
 *
 * Layout structure (top → bottom):
 *   - Demand node: top center (400, 105)
 *   - Agent nodes: horizontal band at y=285, spread from x=130..670
 *   - Center node: lower center (400, 465), only after barrier_met
 *   - Task nodes: bottom band at y=555, spread from x=170..630
 */

import type {
  LayoutResult,
  NodePosition,
  EdgeDef,
} from './types';
import {
  DEMAND_X,
  DEMAND_Y,
  AGENT_Y,
  AGENT_MIN_X,
  AGENT_MAX_X,
  CENTER_NODE_X,
  CENTER_NODE_Y,
  TASK_Y,
  TASK_MIN_X,
  TASK_MAX_X,
} from './types';
import type {
  NegotiationState,
  ResonanceAgent,
  CenterToolCallData,
  PlanJson,
  PlanJsonTask,
} from '@/types/negotiation';

// ============ Helpers ============

/** Phases at which the Center node is visible. */
const CENTER_VISIBLE_PHASES = new Set([
  'barrier_met',
  'synthesizing',
  'plan_ready',
]);

/** Phases at which the plan/task layer is visible. */
const PLAN_VISIBLE_PHASES = new Set(['plan_ready']);

/**
 * Distribute items evenly across a horizontal band [minX, maxX].
 * Single item → centered. Two items → spread to edges.
 */
function spreadX(index: number, total: number, minX: number, maxX: number): number {
  if (total <= 1) return (minX + maxX) / 2;
  return minX + (maxX - minX) * index / (total - 1);
}

// ============ Agent Layout ============

interface AgentLayoutEntry {
  agent: ResonanceAgent;
  isFiltered: boolean;
  position: NodePosition;
}

/**
 * Build the unified list of agent nodes (activated + filtered)
 * and position them in a horizontal band.
 */
function layoutAgents(state: NegotiationState): AgentLayoutEntry[] {
  const activated = state.resonanceAgents ?? [];
  const filtered = state.filteredAgents ?? [];
  const totalAgents = activated.length + filtered.length;

  const entries: AgentLayoutEntry[] = [];

  const allAgents: Array<{ agent: ResonanceAgent; isFiltered: boolean }> = [
    ...activated.map((a) => ({ agent: a, isFiltered: false })),
    ...filtered.map((a) => ({ agent: a, isFiltered: true })),
  ];

  allAgents.forEach((item, index) => {
    entries.push({
      agent: item.agent,
      isFiltered: item.isFiltered,
      position: {
        id: `agent_${item.agent.agent_id}`,
        x: spreadX(index, totalAgents, AGENT_MIN_X, AGENT_MAX_X),
        y: AGENT_Y,
        type: 'agent',
      },
    });
  });

  return entries;
}

// ============ Task Layout ============

function layoutTasks(planJson: PlanJson): NodePosition[] {
  const tasks = planJson.tasks ?? [];
  if (tasks.length === 0) return [];

  return tasks.map((task: PlanJsonTask, index: number) => ({
    id: `task_${task.id}`,
    x: spreadX(index, tasks.length, TASK_MIN_X, TASK_MAX_X),
    y: TASK_Y,
    type: 'task' as const,
  }));
}

// ============ Edge Builders ============

/**
 * Resonance edges: demand -> each activated agent.
 * Filtered agents do NOT get resonance edges.
 */
function buildResonanceEdges(
  agentEntries: AgentLayoutEntry[],
  demandX: number,
  demandY: number,
): EdgeDef[] {
  return agentEntries
    .filter((e) => !e.isFiltered)
    .map((entry) => ({
      id: `res_${entry.agent.agent_id}`,
      from: 'demand',
      to: entry.position.id,
      fromX: demandX,
      fromY: demandY,
      toX: entry.position.x,
      toY: entry.position.y,
      type: 'resonance' as const,
    }));
}

/**
 * Interaction edges derived from center.tool_call activities.
 *
 * Supported tool_names:
 *   - ask_agent:            center -> agent
 *   - discover_connections: agent_a <-> agent_b (pairwise among agent_ids)
 *   - task_assignment:      center -> agent (from plan participants)
 */
function buildInteractionEdges(
  activities: CenterToolCallData[],
  nodeMap: Map<string, NodePosition>,
): EdgeDef[] {
  const edges: EdgeDef[] = [];

  for (let activityIdx = 0; activityIdx < activities.length; activityIdx++) {
    const activity = activities[activityIdx];
    const toolName = activity.tool_name;
    const args = activity.tool_args ?? {};

    if (toolName === 'ask_agent') {
      const agentId = args.agent_id as string | undefined;
      const question = args.question as string | undefined;
      if (!agentId) continue;

      const centerNode = nodeMap.get('center');
      const agentNode = nodeMap.get(`agent_${agentId}`);
      if (!centerNode || !agentNode) continue;

      edges.push({
        id: `int_${activityIdx}`,
        from: 'center',
        to: `agent_${agentId}`,
        fromX: centerNode.x,
        fromY: centerNode.y,
        toX: agentNode.x,
        toY: agentNode.y,
        type: 'interaction',
        interactionType: 'ask_agent',
        label: question,
      });
    } else if (toolName === 'discover_connections') {
      const agentIds = args.agent_ids as string[] | undefined;
      const reason = args.reason as string | undefined;
      if (!agentIds || agentIds.length < 2) continue;

      // Pairwise edges between discovered agents — all share the same activityIdx
      let pairIdx = 0;
      for (let i = 0; i < agentIds.length; i++) {
        for (let j = i + 1; j < agentIds.length; j++) {
          const nodeA = nodeMap.get(`agent_${agentIds[i]}`);
          const nodeB = nodeMap.get(`agent_${agentIds[j]}`);
          if (!nodeA || !nodeB) continue;

          edges.push({
            id: `int_${activityIdx}_${pairIdx++}`,
            from: nodeA.id,
            to: nodeB.id,
            fromX: nodeA.x,
            fromY: nodeA.y,
            toX: nodeB.x,
            toY: nodeB.y,
            type: 'interaction',
            interactionType: 'discover',
            label: reason,
          });
        }
      }
    } else if (toolName === 'task_assignment') {
      const agentId = args.agent_id as string | undefined;
      const taskName = args.task_name as string | undefined;
      if (!agentId) continue;

      const centerNode = nodeMap.get('center');
      const agentNode = nodeMap.get(`agent_${agentId}`);
      if (!centerNode || !agentNode) continue;

      edges.push({
        id: `int_${activityIdx}`,
        from: 'center',
        to: `agent_${agentId}`,
        fromX: centerNode.x,
        fromY: centerNode.y,
        toX: agentNode.x,
        toY: agentNode.y,
        type: 'interaction',
        interactionType: 'task_assignment',
        label: taskName,
      });
    } else if (toolName === 'output_plan') {
      // output_plan: Center assigns roles to participants → task_assignment edges
      const planJsonArg = args.plan_json as {
        participants?: Array<{ agent_id: string; role_in_plan?: string }>;
      } | undefined;
      const participants = planJsonArg?.participants ?? [];

      const centerNode = nodeMap.get('center');
      if (!centerNode || participants.length === 0) continue;

      let pairIdx = 0;
      for (const participant of participants) {
        const agentNode = nodeMap.get(`agent_${participant.agent_id}`);
        if (!agentNode) continue;

        edges.push({
          id: `int_${activityIdx}_${pairIdx++}`,
          from: 'center',
          to: `agent_${participant.agent_id}`,
          fromX: centerNode.x,
          fromY: centerNode.y,
          toX: agentNode.x,
          toY: agentNode.y,
          type: 'interaction',
          interactionType: 'task_assignment',
          label: participant.role_in_plan,
        });
      }
    } else if (toolName === 'create_sub_demand') {
      // create_sub_demand: triggers sub-negotiation, rendered by SubGraph outside SVG
      // No graph edges needed — animation queue provides visual feedback
      continue;
    }
  }

  return edges;
}

/**
 * Task dependency edges from plan_json.topology.
 */
function buildTaskDependencyEdges(
  planJson: PlanJson,
  nodeMap: Map<string, NodePosition>,
): EdgeDef[] {
  const topology = planJson.topology;
  if (!topology || !topology.edges) return [];

  const edges: EdgeDef[] = [];
  for (const edge of topology.edges) {
    const fromNode = nodeMap.get(`task_${edge.from}`);
    const toNode = nodeMap.get(`task_${edge.to}`);
    if (!fromNode || !toNode) continue;
    edges.push({
      id: `dep_${edge.from}_${edge.to}`,
      from: fromNode.id,
      to: toNode.id,
      fromX: fromNode.x,
      fromY: fromNode.y,
      toX: toNode.x,
      toY: toNode.y,
      type: 'task_dependency',
    });
  }
  return edges;
}

// ============ Main Layout Function ============

/**
 * Compute the full radial layout from the negotiation state.
 *
 * @param state - Current NegotiationState from useNegotiationStream
 * @returns LayoutResult with positioned nodes and edges
 */
export function computeLayout(state: NegotiationState): LayoutResult {
  const nodes: NodePosition[] = [];
  const edges: EdgeDef[] = [];

  // 1. Demand node — top center
  const demandNode: NodePosition = {
    id: 'demand',
    x: DEMAND_X,
    y: DEMAND_Y,
    type: 'demand',
  };
  nodes.push(demandNode);

  // 2. Agent nodes — horizontal band
  const agentEntries = layoutAgents(state);
  for (const entry of agentEntries) {
    nodes.push(entry.position);
  }

  // 3. Center node — lower center, only visible after barrier_met
  const showCenter = CENTER_VISIBLE_PHASES.has(state.phase);
  if (showCenter) {
    nodes.push({
      id: 'center',
      x: CENTER_NODE_X,
      y: CENTER_NODE_Y,
      type: 'center',
    });
  }

  // 4. Task nodes on inner ring — only when plan exists
  const showPlan = PLAN_VISIBLE_PHASES.has(state.phase);
  if (showPlan && state.plan?.plan_json) {
    const taskNodes = layoutTasks(state.plan.plan_json);
    nodes.push(...taskNodes);
  }

  // Build a lookup map for edge resolution
  const nodeMap = new Map<string, NodePosition>();
  for (const node of nodes) {
    nodeMap.set(node.id, node);
  }

  // 5. Resonance edges: demand -> activated agents
  edges.push(...buildResonanceEdges(agentEntries, demandNode.x, demandNode.y));

  // 6. Interaction edges from centerActivities
  if (showCenter) {
    edges.push(...buildInteractionEdges(state.centerActivities, nodeMap));
  }

  // 7. Task dependency edges from plan topology
  if (showPlan && state.plan?.plan_json) {
    edges.push(...buildTaskDependencyEdges(state.plan.plan_json, nodeMap));
  }

  return { nodes, edges };
}
