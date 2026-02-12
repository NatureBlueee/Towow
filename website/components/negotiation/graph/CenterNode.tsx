'use client';

import type { CenterNodeProps } from './types';
import styles from './CenterNode.module.css';

/**
 * CenterNode — the synthesizing hexagon that materializes after barrier.complete.
 *
 * CSS-only animations:
 *  - Entrance: 6 converging particles via @keyframes + hexagon scale-up
 *  - Synthesizing state: static glow filter (decorative pulsing glow REMOVED)
 *  - Labels: CSS delayed fade-in
 */

const SIDE = 35;

function hexPoints(cx: number, cy: number, size: number): string {
  const pts: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 6;
    const px = cx + size * Math.cos(angle);
    const py = cy + size * Math.sin(angle);
    pts.push(`${px.toFixed(2)},${py.toFixed(2)}`);
  }
  return pts.join(' ');
}

/** Six particle starting positions (directions around the hexagon). */
const PARTICLE_OFFSETS = [
  { dx: 0, dy: -80 },
  { dx: 70, dy: -40 },
  { dx: 70, dy: 40 },
  { dx: 0, dy: 80 },
  { dx: -70, dy: 40 },
  { dx: -70, dy: -40 },
];

export function CenterNode({
  x,
  y,
  visible,
  isSynthesizing,
  roundNumber,
  onClick,
}: CenterNodeProps) {
  const points = hexPoints(0, 0, SIDE);

  const className = [
    styles.centerGroup,
    visible ? styles.visible : styles.hidden,
  ].join(' ');

  return (
    <g
      className={className}
      style={{ transform: `translate(${x}px, ${y}px)` }}
      onClick={visible ? onClick : undefined}
      onKeyDown={visible ? (e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } } : undefined}
      role={visible ? 'button' : undefined}
      tabIndex={visible ? 0 : -1}
      aria-label={`Center node, round ${roundNumber}${isSynthesizing ? ', synthesizing' : ''}`}
      aria-hidden={!visible}
    >
      <defs>
        <radialGradient id="centerGrad" cx="40%" cy="35%" r="65%">
          <stop offset="0%" stopColor="#a78bfa" />
          <stop offset="100%" stopColor="#7c3aed" />
        </radialGradient>
        <filter id="centerGlow">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Converging particles — CSS @keyframes per particle */}
      {PARTICLE_OFFSETS.map((p, i) => (
        <circle
          key={`particle-${i}`}
          className={styles.particle}
          cx={0} cy={0} r={4}
          fill="#a78bfa"
          style={{
            '--start-x': `${p.dx}px`,
            '--start-y': `${p.dy}px`,
            animationDelay: `${i * 0.05}s`,
          } as React.CSSProperties}
        />
      ))}

      {/* Outer ring — static when synthesizing (decorative pulsing removed) */}
      <polygon
        points={hexPoints(0, 0, SIDE + 6)}
        fill="none"
        stroke="#8b5cf6"
        strokeWidth={2}
        strokeOpacity={isSynthesizing ? 0.5 : 0.25}
        className={styles.outerRing}
      />

      {/* Main hexagon */}
      <polygon
        points={points}
        fill="url(#centerGrad)"
        filter={isSynthesizing ? 'url(#centerGlow)' : undefined}
        className={styles.hexagon}
      />

      {/* Labels */}
      <text className={styles.centerLabel} x={0} y={-4}>
        Center
      </text>
      <text className={styles.roundLabel} x={0} y={12}>
        R{roundNumber}
      </text>
    </g>
  );
}
