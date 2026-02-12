'use client';

import { motion } from 'framer-motion';
import type { DemandNodeProps } from './types';
import styles from './DemandNode.module.css';

/**
 * DemandNode — the central demand node in the negotiation graph.
 *
 * Displays the formulated demand text at the center of the SVG canvas.
 * Animates based on negotiation phase:
 *  - confirming: spring entrance from scale 0 -> 1
 *  - resonating+: gentle pulse loop
 *  - barrier_met+: shrinks to r=25 to make room for CenterNode
 */

/** Truncate text to maxLen characters, appending "..." if needed. */
function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + '...';
}

/** Split text into lines of roughly equal length for SVG <tspan> rendering. */
function splitLines(text: string, maxPerLine: number): string[] {
  const truncated = truncate(text, 20);
  if (truncated.length <= maxPerLine) return [truncated];
  // split at roughly the midpoint
  const mid = Math.ceil(truncated.length / 2);
  return [truncated.slice(0, mid), truncated.slice(mid)];
}

/** Phases where the demand node should shrink to give room for CenterNode. */
const SHRINK_PHASES = new Set(['barrier_met', 'synthesizing', 'plan_ready']);

/** Phases after confirming where the pulse animation plays. */
const PULSE_PHASES = new Set([
  'resonating',
  'collecting_offers',
  'barrier_met',
  'synthesizing',
  'plan_ready',
]);

export function DemandNode({ x, y, text, phase, onClick }: DemandNodeProps) {
  const shouldShrink = SHRINK_PHASES.has(phase);
  const shouldPulse = PULSE_PHASES.has(phase) && !shouldShrink;
  const radius = shouldShrink ? 25 : 45;

  const lines = splitLines(text, 10);

  return (
    <motion.g
      className={styles.demandGroup}
      onClick={onClick}
      onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}
      role="button"
      tabIndex={0}
      aria-label={`Demand: ${text}`}
      initial={{ scale: 0, x, y }}
      animate={{
        scale: shouldPulse ? [1, 1.05, 1] : 1,
        x,
        y,
      }}
      transition={
        shouldPulse
          ? { scale: { repeat: Infinity, duration: 2, ease: 'easeInOut' }, x: { duration: 0.3 }, y: { duration: 0.3 } }
          : { type: 'spring', stiffness: 260, damping: 20, duration: 0.5 }
      }
      style={{ originX: `${x}px`, originY: `${y}px` }}
    >
      {/* Gradient definition */}
      <defs>
        <radialGradient id="demandGrad" cx="40%" cy="35%" r="65%">
          <stop offset="0%" stopColor="#60a5fa" />
          <stop offset="100%" stopColor="#1d4ed8" />
        </radialGradient>
        <filter id="demandShadow">
          <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#1d4ed8" floodOpacity="0.3" />
        </filter>
      </defs>

      {/* Outer glow ring */}
      <circle
        cx={0}
        cy={0}
        r={radius + 6}
        fill="none"
        stroke="rgba(59, 130, 246, 0.2)"
        strokeWidth={2}
      />

      {/* Main circle */}
      <circle
        cx={0}
        cy={0}
        r={radius}
        fill="url(#demandGrad)"
        filter="url(#demandShadow)"
      />

      {/* Text content */}
      {!shouldShrink && (
        <text className={styles.label} x={0} y={lines.length > 1 ? -6 : 0}>
          {lines.map((line, i) => (
            <tspan
              key={i}
              x={0}
              dy={i === 0 ? 0 : 14}
              className={i > 0 ? styles.labelLine : undefined}
            >
              {line}
            </tspan>
          ))}
        </text>
      )}

      {/* Shrunk state: tiny dot icon */}
      {shouldShrink && (
        <text className={styles.phaseLabel} x={0} y={0}>
          {'\u25CF'}
        </text>
      )}
    </motion.g>
  );
}
