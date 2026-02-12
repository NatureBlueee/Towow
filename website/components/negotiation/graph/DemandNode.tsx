'use client';

import type { DemandNodeProps } from './types';
import styles from './DemandNode.module.css';

/**
 * DemandNode — the central demand node in the negotiation graph.
 *
 * CSS-only animations:
 *  - Entry: keyframes demandEnter (scale 0→1)
 *  - Shrink: CSS transition when barrier_met+ (radius 45→25)
 *  - Decorative pulse REMOVED (was not protocol-mapped)
 */

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + '...';
}

function splitLines(text: string, maxPerLine: number): string[] {
  const truncated = truncate(text, 20);
  if (truncated.length <= maxPerLine) return [truncated];
  const mid = Math.ceil(truncated.length / 2);
  return [truncated.slice(0, mid), truncated.slice(mid)];
}

const SHRINK_PHASES = new Set(['barrier_met', 'synthesizing', 'plan_ready']);

export function DemandNode({ x, y, text, phase, onClick }: DemandNodeProps) {
  const shouldShrink = SHRINK_PHASES.has(phase);
  const radius = shouldShrink ? 25 : 45;
  const lines = splitLines(text, 10);

  const className = [
    styles.demandGroup,
    shouldShrink ? styles.shrunk : '',
  ].filter(Boolean).join(' ');

  return (
    <g
      className={className}
      style={{ transform: `translate(${x}px, ${y}px)` }}
      onClick={onClick}
      onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}
      role="button"
      tabIndex={0}
      aria-label={`Demand: ${text}`}
    >
      <defs>
        <radialGradient id="demandGrad" cx="40%" cy="35%" r="65%">
          <stop offset="0%" stopColor="#60a5fa" />
          <stop offset="100%" stopColor="#1d4ed8" />
        </radialGradient>
        <filter id="demandShadow">
          <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#1d4ed8" floodOpacity="0.3" />
        </filter>
      </defs>

      <circle
        cx={0} cy={0} r={radius + 6}
        fill="none" stroke="rgba(59, 130, 246, 0.2)" strokeWidth={2}
      />

      <circle
        cx={0} cy={0} r={radius}
        fill="url(#demandGrad)" filter="url(#demandShadow)"
        className={styles.mainCircle}
      />

      {!shouldShrink && (
        <text className={styles.label} x={0} y={lines.length > 1 ? -6 : 0}>
          {lines.map((line, i) => (
            <tspan
              key={i} x={0} dy={i === 0 ? 0 : 14}
              className={i > 0 ? styles.labelLine : undefined}
            >
              {line}
            </tspan>
          ))}
        </text>
      )}

      {shouldShrink && (
        <text className={styles.phaseLabel} x={0} y={0}>
          {'\u25CF'}
        </text>
      )}
    </g>
  );
}
