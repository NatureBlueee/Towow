'use client';

import { useMemo } from 'react';
import { computeTopologyLayout as computeLayeredLayout, type TaskNode } from '@/lib/topology-layout';
import type { PlanViewProps } from './graph/types';
import type { PlanJsonTask } from '@/types/negotiation';
import styles from './PlanView.module.css';

/**
 * PlanView — displays the final negotiation plan with a structured
 * task topology, participant list, text summary, and action buttons.
 *
 * CSS-only animations:
 *  - Container: fade-in + slide-up entry
 *  - Task cards: scale-in with column-based stagger via --col custom property
 *  - Dependency edges: stroke-dashoffset draw animation
 *  - Actions: delayed fade-in + slide-up
 */

// ============ Layout Constants ============

const CARD_WIDTH = 160;
const CARD_HEIGHT = 80;
const COL_GAP = 60;
const ROW_GAP = 20;
const PADDING_X = 32;
const PADDING_Y = 24;

// ============ Layout Algorithm ============

interface TaskPosition {
  task: PlanJsonTask;
  col: number;
  row: number;
  x: number;
  y: number;
}

interface TopologyEdge {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
}

interface TopologyLayout {
  positions: TaskPosition[];
  edges: TopologyEdge[];
  width: number;
  height: number;
}

function computeTopologyLayout(tasks: PlanJsonTask[]): TopologyLayout {
  if (tasks.length === 0) {
    return { positions: [], edges: [], width: 0, height: 0 };
  }

  // Map PlanJsonTask → TaskNode for the shared library
  const taskNodes: TaskNode[] = tasks.map((t) => ({
    id: t.id,
    title: t.title,
    assigneeId: t.assignee_id || '',
    prerequisites: t.prerequisites || [],
  }));

  const result = computeLayeredLayout(
    taskNodes,
    CARD_WIDTH + COL_GAP,
    CARD_HEIGHT + ROW_GAP,
  );

  // Cycle detected — fall back to single-column layout
  if (!result) {
    const positions: TaskPosition[] = tasks.map((t, i) => ({
      task: t,
      col: 0,
      row: i,
      x: PADDING_X,
      y: PADDING_Y + i * (CARD_HEIGHT + ROW_GAP),
    }));
    const lastY = positions.length > 0
      ? positions[positions.length - 1].y + CARD_HEIGHT
      : 0;
    return {
      positions,
      edges: [],
      width: PADDING_X + CARD_WIDTH + PADDING_X,
      height: lastY + PADDING_Y,
    };
  }

  // Map LayoutNode → TaskPosition
  const taskMap = new Map<string, PlanJsonTask>();
  for (const t of tasks) taskMap.set(t.id, t);

  const positionMap = new Map<string, TaskPosition>();
  const positions: TaskPosition[] = result.nodes.map((node) => {
    const pos: TaskPosition = {
      task: taskMap.get(node.id)!,
      col: node.layer,
      row: Math.round(node.y / (CARD_HEIGHT + ROW_GAP)),
      x: node.x + PADDING_X,
      y: node.y + PADDING_Y,
    };
    positionMap.set(node.id, pos);
    return pos;
  });

  // Map LayoutEdge → TopologyEdge (pixel coordinates)
  const edges: TopologyEdge[] = result.edges
    .map((e) => {
      const from = positionMap.get(e.from);
      const to = positionMap.get(e.to);
      if (!from || !to) return null;
      return {
        fromX: from.x + CARD_WIDTH,
        fromY: from.y + CARD_HEIGHT / 2,
        toX: to.x,
        toY: to.y + CARD_HEIGHT / 2,
      };
    })
    .filter((e): e is TopologyEdge => e !== null);

  // Compute SVG dimensions
  let maxX = 0;
  let maxY = 0;
  for (const p of positions) {
    maxX = Math.max(maxX, p.x + CARD_WIDTH);
    maxY = Math.max(maxY, p.y + CARD_HEIGHT);
  }

  return {
    positions,
    edges,
    width: maxX + PADDING_X,
    height: maxY + PADDING_Y,
  };
}

// ============ Helper: Bezier curve path ============

function bezierPath(e: TopologyEdge): string {
  const dx = (e.toX - e.fromX) * 0.4;
  return `M ${e.fromX} ${e.fromY} C ${e.fromX + dx} ${e.fromY}, ${e.toX - dx} ${e.toY}, ${e.toX} ${e.toY}`;
}

// ============ Helper: Status class ============

function taskStatusClass(status: string): string {
  switch (status) {
    case 'pending':
      return styles.taskStatus_pending;
    case 'in_progress':
      return styles.taskStatus_in_progress;
    case 'completed':
      return styles.taskStatus_completed;
    default:
      return styles.taskStatus_default;
  }
}

// ============ Helper: Render plan text with basic formatting ============

function renderPlanText(text: string) {
  const lines = text.split('\n');
  return lines.map((line, i) => {
    const trimmed = line.trim();
    if (trimmed === '') {
      return <p key={i} className={styles.planTextSpacer} />;
    }
    if (/^[-*]\s/.test(trimmed) || /^\d+\.\s/.test(trimmed)) {
      const content = trimmed.replace(/^[-*]\s/, '').replace(/^\d+\.\s/, '');
      return (
        <p key={i} className={styles.planTextListItem}>{content}</p>
      );
    }
    return (
      <p key={i} className={styles.planTextParagraph}>{line}</p>
    );
  });
}

// ============ Main Component ============

export function PlanView({
  planText,
  planJson,
  onAccept,
  onReject,
  onTaskClick,
}: PlanViewProps) {
  const layout = useMemo(
    () => computeTopologyLayout(planJson.tasks || []),
    [planJson.tasks],
  );

  const hasTasks = layout.positions.length > 0;
  const hasParticipants = planJson.participants && planJson.participants.length > 0;

  return (
    <div className={styles.container}>
      {/* Summary */}
      {planJson.summary && (
        <p className={styles.summary}>{planJson.summary}</p>
      )}

      {/* Task Topology */}
      <div className={styles.topologySection}>
        <p className={styles.topologySectionTitle}>Task Topology</p>
        {hasTasks ? (
          <div className={styles.topologyWrapper}>
            <svg
              className={styles.topologySvg}
              width={layout.width}
              height={layout.height}
              viewBox={`0 0 ${layout.width} ${layout.height}`}
            >
              {/* Arrow marker definition */}
              <defs>
                <marker
                  id="planArrow"
                  viewBox="0 0 10 8"
                  refX="10"
                  refY="4"
                  markerWidth="8"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 4 L 0 8 Z" className={styles.depArrow} />
                </marker>
              </defs>

              {/* Dependency edges — CSS draw animation */}
              {layout.edges.map((e, i) => (
                <path
                  key={`edge-${i}`}
                  d={bezierPath(e)}
                  className={styles.depEdge}
                  markerEnd="url(#planArrow)"
                  pathLength={1}
                />
              ))}

              {/* Task cards using foreignObject — stagger via --col */}
              {layout.positions.map((pos) => (
                <foreignObject
                  key={pos.task.id}
                  className={styles.taskCardEntry}
                  x={pos.x}
                  y={pos.y}
                  width={CARD_WIDTH}
                  height={CARD_HEIGHT}
                  style={{ '--col': pos.col } as React.CSSProperties}
                >
                  <div
                    className={styles.taskCard}
                    onClick={() => onTaskClick(pos.task.id)}
                  >
                    <p className={styles.taskTitle}>{pos.task.title}</p>
                    <div className={styles.taskMeta}>
                      <span className={styles.taskAssignee}>
                        {pos.task.assignee_id || 'Unassigned'}
                      </span>
                      <span className={`${styles.taskStatus} ${taskStatusClass(pos.task.status)}`}>
                        {pos.task.status}
                      </span>
                    </div>
                  </div>
                </foreignObject>
              ))}
            </svg>
          </div>
        ) : (
          <div className={styles.emptyTasks}>No tasks defined</div>
        )}
      </div>

      {/* Participants */}
      {hasParticipants && (
        <div className={styles.participantsSection}>
          <p className={styles.participantsSectionTitle}>Participants</p>
          <div className={styles.participantList}>
            {planJson.participants.map((p) => (
              <div key={p.agent_id} className={styles.participantChip}>
                <span className={styles.participantName}>{p.display_name}</span>
                <span className={styles.participantRole}>{p.role_in_plan}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Plan Text */}
      {planText && (
        <div className={styles.planTextSection}>
          <p className={styles.planTextSectionTitle}>Plan Summary</p>
          <div className={styles.planTextBody}>
            {renderPlanText(planText)}
          </div>
        </div>
      )}

      {/* Action Buttons — only when handlers are provided */}
      {(onAccept || onReject) && (
        <div className={styles.actions}>
          {onReject && (
            <button className={styles.rejectButton} onClick={onReject}>
              Reject
            </button>
          )}
          {onAccept && (
            <button className={styles.acceptButton} onClick={onAccept}>
              Accept Plan
            </button>
          )}
        </div>
      )}
    </div>
  );
}
