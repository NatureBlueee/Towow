'use client';

/**
 * NegotiationGraph — core SVG container for the negotiation graph visualization.
 *
 * Responsibilities:
 *   1. Call computeLayout(state) to position nodes and edges
 *   2. Render SVG container (viewBox 0 0 800 600, responsive)
 *   3. Render real node/edge components (DemandNode, AgentNode, CenterNode, etc.)
 *   4. Animation queue: center.tool_call events enqueue and play sequentially
 *   5. Resonance wave ripple animation on resonance.activated
 *   6. Forward onNodeClick / onEdgeClick callbacks
 */

import React, { useMemo, useRef, useCallback, useEffect, useState } from 'react';
import { computeLayout } from './layout';
import { DemandNode } from './DemandNode';
import { AgentNode } from './AgentNode';
import { CenterNode } from './CenterNode';
import { ResonanceEdge } from './ResonanceEdge';
import { InteractionEdge } from './InteractionEdge';
import type {
  NegotiationGraphProps,
  NodePosition,
  EdgeDef,
  AnimationItem,
} from './types';
import {
  GRAPH_WIDTH,
  GRAPH_HEIGHT,
  DEMAND_X,
  DEMAND_Y,
} from './types';
import type {
  ResonanceAgent,
  OfferReceivedData,
  CenterToolCallData,
  PlanJsonTask,
} from '@/types/negotiation';
import styles from './NegotiationGraph.module.css';

// ============ Animation Queue Hook ============

function useAnimationQueue() {
  const queueRef = useRef<AnimationItem[]>([]);
  const [currentAnimation, setCurrentAnimation] = useState<AnimationItem | null>(null);
  const isPlayingRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      isPlayingRef.current = false;
      setCurrentAnimation(null);
      return;
    }

    isPlayingRef.current = true;
    const next = queueRef.current.shift()!;
    setCurrentAnimation(next);

    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      playNext();
    }, next.duration);
  }, []);

  const enqueue = useCallback(
    (item: AnimationItem) => {
      queueRef.current.push(item);
      if (!isPlayingRef.current) {
        playNext();
      }
    },
    [playNext],
  );

  const queueLength = queueRef.current.length + (currentAnimation ? 1 : 0);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return { currentAnimation, enqueue, queueLength };
}

// ============ Resonance Wave Ripple ============

function ResonanceWaveRipple({ active }: { active: boolean }) {
  if (!active) return null;

  return (
    <g aria-hidden="true">
      <circle cx={DEMAND_X} cy={DEMAND_Y} r={0} className={styles.resonanceWave} />
      <circle cx={DEMAND_X} cy={DEMAND_Y} r={0} className={styles.resonanceWave} />
      <circle cx={DEMAND_X} cy={DEMAND_Y} r={0} className={styles.resonanceWave} />
    </g>
  );
}

// ============ SVG Defs ============

function GraphDefs() {
  return (
    <defs>
      <marker
        id="arrowGreen"
        viewBox="0 0 10 10"
        refX={8}
        refY={5}
        markerWidth={6}
        markerHeight={6}
        orient="auto-start-reverse"
      >
        <path d="M 0 0 L 10 5 L 0 10 Z" fill="#10b981" />
      </marker>
    </defs>
  );
}

// ============ Task Node (simple, kept inline) ============

function TaskNode({
  node,
  title,
  onClick,
}: {
  node: NodePosition;
  title: string;
  onClick: () => void;
}) {
  const displayTitle = title.length > 10 ? title.slice(0, 8) + '...' : title;

  return (
    <g
      className={styles.taskNode}
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`Task: ${title}`}
    >
      <circle cx={node.x} cy={node.y} r={16} className={styles.taskCircle} />
      <text x={node.x} y={node.y} className={styles.taskLabel}>
        {displayTitle}
      </text>
    </g>
  );
}

// ============ Task Dependency Edge (simple, kept inline) ============

function TaskDependencyEdge({ edge }: { edge: EdgeDef }) {
  return (
    <line
      x1={edge.fromX}
      y1={edge.fromY}
      x2={edge.toX}
      y2={edge.toY}
      className={styles.taskDependencyEdge}
      markerEnd="url(#arrowGreen)"
    />
  );
}

// ============ Main Component ============

export default function NegotiationGraph({
  state,
  onNodeClick,
  onEdgeClick,
  onTaskClick,
}: NegotiationGraphProps) {
  const { currentAnimation, enqueue, queueLength } = useAnimationQueue();
  const prevActivityCountRef = useRef(0);

  // Compute layout
  const layout = useMemo(() => computeLayout(state), [state]);

  // Build quick-lookup maps
  const agentMap = useMemo(() => {
    const map = new Map<string, ResonanceAgent>();
    for (const agent of state.resonanceAgents) {
      map.set(agent.agent_id, agent);
    }
    for (const agent of state.filteredAgents) {
      map.set(agent.agent_id, agent);
    }
    return map;
  }, [state.resonanceAgents, state.filteredAgents]);

  const filteredAgentIds = useMemo(
    () => new Set(state.filteredAgents.map((a) => a.agent_id)),
    [state.filteredAgents],
  );

  const offersMap = useMemo(() => {
    const map = new Map<string, OfferReceivedData>();
    for (const offer of state.offers) {
      map.set(offer.agent_id, offer);
    }
    return map;
  }, [state.offers]);

  // Plan participants role map
  const participantRoleMap = useMemo(() => {
    const map = new Map<string, string>();
    if (state.plan?.plan_json?.participants) {
      for (const p of state.plan.plan_json.participants) {
        map.set(p.agent_id, p.role_in_plan);
      }
    }
    return map;
  }, [state.plan]);

  // Task lookup
  const taskMap = useMemo(() => {
    const map = new Map<string, PlanJsonTask>();
    if (state.plan?.plan_json?.tasks) {
      for (const task of state.plan.plan_json.tasks) {
        map.set(`task_${task.id}`, task);
      }
    }
    return map;
  }, [state.plan]);

  // Detect new center.tool_call events and enqueue animations
  useEffect(() => {
    const currentCount = state.centerActivities.length;
    if (currentCount > prevActivityCountRef.current) {
      const newActivities = state.centerActivities.slice(prevActivityCountRef.current);
      for (const activity of newActivities) {
        const animType = toolNameToAnimationType(activity.tool_name);
        enqueue({
          id: `anim_${activity.tool_name}_${activity.round_number}_${Date.now()}`,
          type: animType,
          data: { activity },
          duration: 1200,
        });
      }
    }
    prevActivityCountRef.current = currentCount;
  }, [state.centerActivities, enqueue]);

  // Determine states
  const showResonanceWave = state.phase === 'collecting_offers' && state.resonanceAgents.length > 0;
  const currentRound = state.centerActivities.length > 0
    ? state.centerActivities[state.centerActivities.length - 1].round_number
    : 0;
  const showCenter = state.phase === 'barrier_met' || state.phase === 'synthesizing' || state.phase === 'plan_ready';
  const isIdle = state.phase === 'idle';

  // Track which interaction edge index is currently animating
  const animatingEdgeIndex = useMemo(() => {
    if (!currentAnimation) return -1;
    const activity = currentAnimation.data.activity as CenterToolCallData | undefined;
    if (!activity) return -1;
    return state.centerActivities.indexOf(activity);
  }, [currentAnimation, state.centerActivities]);

  return (
    <div className={styles.graphContainer}>
      <svg
        className={styles.graphSvg}
        viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Negotiation graph visualization"
      >
        <GraphDefs />

        {/* Resonance wave ripple (behind everything) */}
        <ResonanceWaveRipple active={showResonanceWave} />

        {/* Edges layer (rendered below nodes) */}
        <g aria-label="Edges">
          {layout.edges.map((edge) => {
            if (edge.type === 'resonance') {
              const agentId = edge.to.replace('agent_', '');
              const agent = agentMap.get(agentId);
              const hasOffer = offersMap.has(agentId);
              return (
                <ResonanceEdge
                  key={edge.id}
                  fromX={edge.fromX}
                  fromY={edge.fromY}
                  toX={edge.toX}
                  toY={edge.toY}
                  score={agent?.resonance_score ?? 0.5}
                  isActive={!filteredAgentIds.has(agentId)}
                  hasOffer={hasOffer}
                  onClick={() => onEdgeClick(edge.id)}
                />
              );
            }

            if (edge.type === 'interaction') {
              const interactionEdges = layout.edges.filter((e) => e.type === 'interaction');
              const isLast = interactionEdges[interactionEdges.length - 1]?.id === edge.id;
              return (
                <InteractionEdge
                  key={edge.id}
                  id={edge.id}
                  fromX={edge.fromX}
                  fromY={edge.fromY}
                  toX={edge.toX}
                  toY={edge.toY}
                  interactionType={edge.interactionType ?? 'ask_agent'}
                  label={edge.label}
                  animate={isLast && state.phase === 'synthesizing'}
                  onClick={() => onEdgeClick(edge.id)}
                />
              );
            }

            if (edge.type === 'task_dependency') {
              return <TaskDependencyEdge key={edge.id} edge={edge} />;
            }

            return null;
          })}
        </g>

        {/* Nodes layer */}
        <g aria-label="Nodes">
          {layout.nodes.map((node) => {
            if (node.type === 'demand') {
              const demandText =
                state.formulation?.formulated_text ??
                state.formulation?.raw_intent ??
                '';
              return (
                <DemandNode
                  key={node.id}
                  x={node.x}
                  y={node.y}
                  text={demandText}
                  phase={state.phase}
                  onClick={() => onNodeClick('demand', node.id)}
                />
              );
            }

            if (node.type === 'agent') {
              const agentId = node.id.replace('agent_', '');
              const agent = agentMap.get(agentId);
              if (!agent) return null;
              const isFiltered = filteredAgentIds.has(agentId);
              const offer = offersMap.get(agentId);
              const role = participantRoleMap.get(agentId);
              return (
                <AgentNode
                  key={node.id}
                  x={node.x}
                  y={node.y}
                  agentId={agentId}
                  displayName={agent.display_name}
                  score={agent.resonance_score}
                  isFiltered={isFiltered}
                  hasOffer={!!offer}
                  offerContent={offer?.content}
                  roleInPlan={role}
                  onClick={() => onNodeClick('agent', agentId)}
                />
              );
            }

            if (node.type === 'center') {
              return (
                <CenterNode
                  key={node.id}
                  x={node.x}
                  y={node.y}
                  visible={showCenter}
                  isSynthesizing={state.phase === 'synthesizing'}
                  roundNumber={currentRound}
                  onClick={() => onNodeClick('center', node.id)}
                />
              );
            }

            if (node.type === 'task') {
              const task = taskMap.get(node.id);
              const taskId = node.id.replace('task_', '');
              return (
                <TaskNode
                  key={node.id}
                  node={node}
                  title={task?.title ?? taskId}
                  onClick={() => onTaskClick(taskId)}
                />
              );
            }

            return null;
          })}
        </g>

        {/* Empty state label */}
        {isIdle && (
          <text x={GRAPH_WIDTH / 2} y={GRAPH_HEIGHT / 2} className={styles.emptyLabel}>
            Submit a demand to start
          </text>
        )}
      </svg>

      {/* Animation queue indicator */}
      {queueLength > 0 && (
        <div className={styles.animationIndicator}>
          {currentAnimation
            ? `Playing: ${currentAnimation.type}`
            : `Queued: ${queueLength}`}
        </div>
      )}
    </div>
  );
}

// ============ Utility ============

function toolNameToAnimationType(
  toolName: string,
): AnimationItem['type'] {
  switch (toolName) {
    case 'ask_agent':
      return 'ask_agent';
    case 'discover_connections':
      return 'discover';
    case 'output_plan':
      return 'output_plan';
    case 'create_sub_demand':
      return 'sub_demand';
    default:
      return 'ask_agent';
  }
}
