'use client';

import { useMemo, useId } from 'react';
import type { ResonanceEdgeProps } from './types';
import styles from './ResonanceEdge.module.css';

/**
 * ResonanceEdge — SVG edge from the demand center to an agent node.
 *
 * CSS-only animations:
 *  - Line draw: CSS stroke-dashoffset animation via pathLength="1"
 *  - Show/hide: CSS opacity transition (no unmount)
 *  - Offer particle: native SVG <animateMotion> (kept as-is)
 *
 * Color: HSL(270 - score*110) maps score to purple→teal brand palette.
 */
export function ResonanceEdge({
  fromX,
  fromY,
  toX,
  toY,
  score,
  isActive,
  hasOffer,
  onClick,
}: ResonanceEdgeProps) {
  const uniqueId = useId();
  const pathId = `resonance-path-${uniqueId}`;

  // Clamp score to [0, 1]
  const clampedScore = Math.max(0, Math.min(1, score));

  // Line width: score 0.5→1px, score 1.0→4px
  const strokeWidth = useMemo(() => {
    const t = Math.max(0, (clampedScore - 0.5) / 0.5);
    return 1 + t * 3;
  }, [clampedScore]);

  // Color: HSL 270→160 (purple→teal) brand-aligned
  const hue = Math.round(270 - clampedScore * 110);
  const baseColor = `hsl(${hue}, 70%, 50%)`;
  const offerColor = `hsl(${hue}, 80%, 40%)`;
  const lineColor = hasOffer ? offerColor : baseColor;
  const particleColor = `hsl(${hue}, 85%, 60%)`;

  // Path for animateMotion: agent → center
  const motionPathD = `M${toX},${toY} L${fromX},${fromY}`;

  const groupClass = [
    onClick ? styles.edgeGroupClickable : styles.edgeGroup,
    isActive ? styles.visible : styles.hidden,
  ].join(' ');

  return (
    <g className={groupClass} onClick={isActive ? onClick : undefined}>
      {/* The resonance line — CSS draw animation via pathLength */}
      <line
        className={styles.resonanceLine}
        x1={fromX}
        y1={fromY}
        x2={toX}
        y2={toY}
        stroke={lineColor}
        strokeWidth={hasOffer ? strokeWidth + 0.5 : strokeWidth}
        strokeOpacity={0.7}
        pathLength={1}
      />

      {/* Offer particle — native SVG animateMotion */}
      {hasOffer && (
        <>
          <path id={pathId} d={motionPathD} fill="none" stroke="none" />
          <circle
            className={styles.offerParticle}
            r={3}
            fill={particleColor}
            opacity={0.9}
          >
            <animateMotion
              dur="1.5s"
              repeatCount="indefinite"
              rotate="auto"
            >
              <mpath href={`#${pathId}`} />
            </animateMotion>
          </circle>
        </>
      )}
    </g>
  );
}
