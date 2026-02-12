'use client';

import { useMemo, useId } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ResonanceEdgeProps } from './types';
import styles from './ResonanceEdge.module.css';

/**
 * ResonanceEdge — SVG edge from the demand center to an agent node.
 *
 * Visual encoding:
 * - Line width scales with resonance score (1px at 0.5, 4px at 1.0)
 * - Hue maps score to green-red spectrum: HSL(score*120, 70%, 50%)
 * - hasOffer=true triggers a looping particle flowing agent→center
 * - isActive=false hides the edge (agent was filtered out)
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

  // Line width: linear interpolation, score 0.5→1px, score 1.0→4px
  // Clamp score to [0, 1] range for safety
  const clampedScore = Math.max(0, Math.min(1, score));
  const strokeWidth = useMemo(() => {
    const t = Math.max(0, (clampedScore - 0.5) / 0.5); // 0 at score=0.5, 1 at score=1.0
    return 1 + t * 3; // 1px to 4px
  }, [clampedScore]);

  // Color: HSL mapped by score. score=0→red(0), score=1→green(120)
  const hue = Math.round(clampedScore * 120);
  const baseColor = `hsl(${hue}, 70%, 50%)`;
  const offerColor = `hsl(${hue}, 80%, 40%)`; // darker when offer arrives

  const lineColor = hasOffer ? offerColor : baseColor;

  // Particle color matches the line but slightly brighter
  const particleColor = `hsl(${hue}, 85%, 60%)`;

  // Build a straight-line path string for animateMotion
  // Path goes from agent (to) toward center (from)
  const motionPathD = `M${toX},${toY} L${fromX},${fromY}`;

  return (
    <AnimatePresence>
      {isActive && (
        <motion.g
          className={onClick ? styles.edgeGroupClickable : styles.edgeGroup}
          onClick={onClick}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          {/* The resonance line */}
          <motion.line
            className={styles.resonanceLine}
            x1={fromX}
            y1={fromY}
            x2={toX}
            y2={toY}
            stroke={lineColor}
            strokeWidth={hasOffer ? strokeWidth + 0.5 : strokeWidth}
            strokeOpacity={0.7}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />

          {/* Offer particle — a dot that flows agent→center in a loop */}
          {hasOffer && (
            <>
              {/* Hidden path for animateMotion reference */}
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
        </motion.g>
      )}
    </AnimatePresence>
  );
}
