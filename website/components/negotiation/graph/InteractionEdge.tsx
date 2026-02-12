'use client';

import { useMemo, useId } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { InteractionEdgeProps } from './types';
import styles from './InteractionEdge.module.css';

/**
 * InteractionEdge — SVG edge for Center↔Agent or Agent↔Agent interactions.
 *
 * Three visual modes based on interactionType:
 * - ask_agent:       dashed purple line, pulse dot + question bubble
 * - discover:        dashed amber line, grows from midpoint outward
 * - task_assignment:  solid indigo line, shoots from center to agent
 */
export function InteractionEdge({
  id,
  fromX,
  fromY,
  toX,
  toY,
  interactionType,
  label,
  animate,
  onClick,
}: InteractionEdgeProps) {
  const uniqueId = useId();

  const midX = (fromX + toX) / 2;
  const midY = (fromY + toY) / 2;

  // Truncate label to 15 characters
  const truncatedLabel = useMemo(() => {
    if (!label) return '';
    return label.length > 15 ? label.slice(0, 15) + '...' : label;
  }, [label]);

  // Path definitions for animateMotion
  const forwardPathId = `interaction-fwd-${uniqueId}`;
  const returnPathId = `interaction-ret-${uniqueId}`;
  const forwardPathD = `M${fromX},${fromY} L${toX},${toY}`;
  const returnPathD = `M${toX},${toY} L${fromX},${fromY}`;

  // Discover: two half-paths from midpoint outward
  const discoverPathLeftId = `discover-left-${uniqueId}`;
  const discoverPathRightId = `discover-right-${uniqueId}`;

  // Estimate label width for foreignObject
  const labelWidth = 140;
  const labelHeight = 24;

  if (interactionType === 'ask_agent') {
    return <AskAgentEdge
      id={id}
      fromX={fromX}
      fromY={fromY}
      toX={toX}
      toY={toY}
      midX={midX}
      midY={midY}
      animate={animate}
      label={truncatedLabel}
      labelWidth={labelWidth}
      labelHeight={labelHeight}
      forwardPathId={forwardPathId}
      forwardPathD={forwardPathD}
      returnPathId={returnPathId}
      returnPathD={returnPathD}
      onClick={onClick}
    />;
  }

  if (interactionType === 'discover') {
    return <DiscoverEdge
      id={id}
      fromX={fromX}
      fromY={fromY}
      toX={toX}
      toY={toY}
      midX={midX}
      midY={midY}
      animate={animate}
      label={truncatedLabel}
      labelWidth={labelWidth}
      labelHeight={labelHeight}
      discoverPathLeftId={discoverPathLeftId}
      discoverPathRightId={discoverPathRightId}
      onClick={onClick}
    />;
  }

  // task_assignment
  return <TaskAssignmentEdge
    id={id}
    fromX={fromX}
    fromY={fromY}
    toX={toX}
    toY={toY}
    animate={animate}
    label={truncatedLabel}
    labelWidth={labelWidth}
    labelHeight={labelHeight}
    forwardPathId={forwardPathId}
    forwardPathD={forwardPathD}
    onClick={onClick}
  />;
}


// ============ ask_agent sub-component ============

interface AskAgentEdgeProps {
  id: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  midX: number;
  midY: number;
  animate: boolean;
  label: string;
  labelWidth: number;
  labelHeight: number;
  forwardPathId: string;
  forwardPathD: string;
  returnPathId: string;
  returnPathD: string;
  onClick?: () => void;
}

function AskAgentEdge({
  fromX,
  fromY,
  toX,
  toY,
  midX,
  midY,
  animate,
  label,
  labelWidth,
  labelHeight,
  forwardPathId,
  forwardPathD,
  returnPathId,
  returnPathD,
  onClick,
}: AskAgentEdgeProps) {
  const color = '#8b5cf6';

  return (
    <motion.g
      className={onClick ? styles.edgeGroupClickable : styles.edgeGroup}
      onClick={onClick}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Dashed purple line */}
      <motion.line
        className={styles.interactionLine}
        x1={fromX}
        y1={fromY}
        x2={toX}
        y2={toY}
        stroke={color}
        strokeWidth={1.5}
        strokeDasharray="6 4"
        strokeOpacity={0.7}
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
      />

      {/* Animated pulse dots */}
      <AnimatePresence>
        {animate && (
          <>
            {/* Hidden paths for animateMotion */}
            <path id={forwardPathId} d={forwardPathD} fill="none" stroke="none" />
            <path id={returnPathId} d={returnPathD} fill="none" stroke="none" />

            {/* Forward pulse: from → to */}
            <circle
              className={styles.pulsePoint}
              r={3}
              fill={color}
              opacity={0.9}
            >
              <animateMotion
                dur="0.6s"
                begin="0s"
                repeatCount="indefinite"
              >
                <mpath href={`#${forwardPathId}`} />
              </animateMotion>
            </circle>

            {/* Return pulse: to → from (offset start) */}
            <circle
              className={styles.pulsePoint}
              r={2.5}
              fill={color}
              opacity={0.6}
            >
              <animateMotion
                dur="0.6s"
                begin="0.3s"
                repeatCount="indefinite"
              >
                <mpath href={`#${returnPathId}`} />
              </animateMotion>
            </circle>

            {/* Label bubble at midpoint */}
            {label && (
              <motion.foreignObject
                className={styles.labelContainer}
                x={midX - labelWidth / 2}
                y={midY - labelHeight / 2 - 14}
                width={labelWidth}
                height={labelHeight}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{
                  delay: 0.2,
                  duration: 0.3,
                  ease: 'easeOut',
                }}
              >
                <div className={`${styles.labelBubble} ${styles.askLabel}`}>
                  {label}
                </div>
              </motion.foreignObject>
            )}
          </>
        )}
      </AnimatePresence>
    </motion.g>
  );
}


// ============ discover sub-component ============

interface DiscoverEdgeProps {
  id: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  midX: number;
  midY: number;
  animate: boolean;
  label: string;
  labelWidth: number;
  labelHeight: number;
  discoverPathLeftId: string;
  discoverPathRightId: string;
  onClick?: () => void;
}

function DiscoverEdge({
  fromX,
  fromY,
  toX,
  toY,
  midX,
  midY,
  animate,
  label,
  labelWidth,
  labelHeight,
  onClick,
}: DiscoverEdgeProps) {
  const color = '#f59e0b';

  return (
    <motion.g
      className={onClick ? styles.edgeGroupClickable : styles.edgeGroup}
      onClick={onClick}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Left half: midpoint → from */}
      <motion.line
        className={styles.interactionLine}
        x1={midX}
        y1={midY}
        x2={fromX}
        y2={fromY}
        stroke={color}
        strokeWidth={1.5}
        strokeDasharray="4 4"
        strokeOpacity={0.7}
        initial={{ pathLength: 0 }}
        animate={{ pathLength: animate ? 1 : 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      />

      {/* Right half: midpoint → to */}
      <motion.line
        className={styles.interactionLine}
        x1={midX}
        y1={midY}
        x2={toX}
        y2={toY}
        stroke={color}
        strokeWidth={1.5}
        strokeDasharray="4 4"
        strokeOpacity={0.7}
        initial={{ pathLength: 0 }}
        animate={{ pathLength: animate ? 1 : 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      />

      {/* Connection point at midpoint */}
      <motion.circle
        cx={midX}
        cy={midY}
        r={4}
        fill={color}
        fillOpacity={0.3}
        stroke={color}
        strokeWidth={1}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.3, delay: 0.2 }}
      />

      {/* Label at midpoint */}
      <AnimatePresence>
        {animate && label && (
          <motion.foreignObject
            className={styles.labelContainer}
            x={midX - labelWidth / 2}
            y={midY - labelHeight / 2 - 16}
            width={labelWidth}
            height={labelHeight}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ delay: 0.3, duration: 0.3 }}
          >
            <div className={`${styles.labelBubble} ${styles.discoverLabel}`}>
              {label}
            </div>
          </motion.foreignObject>
        )}
      </AnimatePresence>
    </motion.g>
  );
}


// ============ task_assignment sub-component ============

interface TaskAssignmentEdgeProps {
  id: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  animate: boolean;
  label: string;
  labelWidth: number;
  labelHeight: number;
  forwardPathId: string;
  forwardPathD: string;
  onClick?: () => void;
}

function TaskAssignmentEdge({
  fromX,
  fromY,
  toX,
  toY,
  animate,
  label,
  labelWidth,
  labelHeight,
  forwardPathId,
  forwardPathD,
  onClick,
}: TaskAssignmentEdgeProps) {
  const color = '#6366f1';

  return (
    <motion.g
      className={onClick ? styles.edgeGroupClickable : styles.edgeGroup}
      onClick={onClick}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Solid indigo line */}
      <motion.line
        className={styles.interactionLine}
        x1={fromX}
        y1={fromY}
        x2={toX}
        y2={toY}
        stroke={color}
        strokeWidth={1.5}
        strokeOpacity={0.65}
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      />

      {/* Animated pulse from Center → Agent */}
      <AnimatePresence>
        {animate && (
          <>
            <path id={forwardPathId} d={forwardPathD} fill="none" stroke="none" />
            <circle
              className={styles.pulsePoint}
              r={3}
              fill={color}
              opacity={0.85}
            >
              <animateMotion
                dur="0.8s"
                repeatCount="1"
                fill="freeze"
              >
                <mpath href={`#${forwardPathId}`} />
              </animateMotion>
            </circle>

            {/* Task label near the agent end */}
            {label && (
              <motion.foreignObject
                className={styles.labelContainer}
                x={toX - labelWidth / 2}
                y={toY + 18}
                width={labelWidth}
                height={labelHeight}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{ delay: 0.35, duration: 0.3 }}
              >
                <div className={`${styles.labelBubble} ${styles.taskLabel}`}>
                  {label}
                </div>
              </motion.foreignObject>
            )}
          </>
        )}
      </AnimatePresence>
    </motion.g>
  );
}
