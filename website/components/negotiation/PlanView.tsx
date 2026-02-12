'use client';

import { useMemo } from 'react';
import { motion, type Variants } from 'framer-motion';
import { computeTopologyLayout as computeLayeredLayout, type TaskNode } from '@/lib/topology-layout';
import type { PlanViewProps } from './graph/types';
import type { PlanJsonTask } from '@/types/negotiation';
import styles from './PlanView.module.css';

/**
 * PlanView — displays the final negotiation plan with a structured
 * task topology, participant list, text summary, and action buttons.
 *
 * The task topology is rendered as an independent SVG element using a
 * layered layout algorithm: tasks with no prerequisites are placed in
 * column 0, tasks depending on column-0 tasks go to column 1, etc.
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
    // Detect list items (lines starting with - or * or a numbered list)
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

// ============ Animation Variants ============

const containerVariants: Variants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' },
  },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, scale: 0.85 },
  visible: (col: number) => ({
    opacity: 1,
    scale: 1,
    transition: {
      delay: 0.15 + col * 0.1,
      duration: 0.35,
      ease: 'easeOut',
    },
  }),
};

const edgeVariants: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: { delay: 0.3, duration: 0.6, ease: 'easeOut' },
  },
};

const actionVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { delay: 0.6, duration: 0.3, ease: 'easeOut' },
  },
};

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
    <motion.div
      className={styles.container}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
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

              {/* Dependency edges */}
              {layout.edges.map((e, i) => (
                <motion.path
                  key={`edge-${i}`}
                  d={bezierPath(e)}
                  className={styles.depEdge}
                  markerEnd="url(#planArrow)"
                  variants={edgeVariants}
                  initial="hidden"
                  animate="visible"
                />
              ))}

              {/* Task cards using foreignObject */}
              {layout.positions.map((pos) => (
                <motion.foreignObject
                  key={pos.task.id}
                  x={pos.x}
                  y={pos.y}
                  width={CARD_WIDTH}
                  height={CARD_HEIGHT}
                  variants={cardVariants}
                  custom={pos.col}
                  initial="hidden"
                  animate="visible"
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
                </motion.foreignObject>
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

      {/* Action Buttons */}
      <motion.div
        className={styles.actions}
        variants={actionVariants}
        initial="hidden"
        animate="visible"
      >
        <button className={styles.rejectButton} onClick={onReject}>
          Reject
        </button>
        <button className={styles.acceptButton} onClick={onAccept}>
          Accept Plan
        </button>
      </motion.div>
    </motion.div>
  );
}
