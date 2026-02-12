'use client';

import { motion, AnimatePresence } from 'framer-motion';
import type { CenterNodeProps } from './types';
import styles from './CenterNode.module.css';

/**
 * CenterNode — the synthesizing hexagon that materializes after barrier.complete.
 *
 * Visual behaviour:
 *  - Invisible until `visible` becomes true.
 *  - Entrance: six directional particles converge then coalesce into a hexagon.
 *  - While `isSynthesizing`, a pulsing glow filter animates around the shape.
 *  - Displays "Center" label and the current round number.
 */

/** Side length of the hexagon. */
const SIDE = 35;

/** Build hexagon points string for an SVG <polygon>. Flat-top orientation. */
function hexPoints(cx: number, cy: number, size: number): string {
  const pts: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 6; // flat-top: start at -30deg
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

  return (
    <AnimatePresence>
      {visible && (
        <motion.g
          key="center-node"
          className={styles.centerGroup}
          onClick={onClick}
          onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}
          role="button"
          tabIndex={0}
          aria-label={`Center node, round ${roundNumber}${isSynthesizing ? ', synthesizing' : ''}`}
          initial={{ x, y }}
          animate={{ x, y }}
          transition={{ duration: 0.3 }}
        >
          {/* Filters and gradients */}
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

          {/* Converging particles — animate from offset to origin then disappear */}
          {PARTICLE_OFFSETS.map((p, i) => (
            <motion.circle
              key={`particle-${i}`}
              cx={0}
              cy={0}
              r={4}
              fill="#a78bfa"
              initial={{ opacity: 0.9, translateX: p.dx, translateY: p.dy }}
              animate={{ opacity: 0, translateX: 0, translateY: 0 }}
              transition={{
                duration: 0.6,
                delay: i * 0.05,
                ease: 'easeIn',
              }}
            />
          ))}

          {/* Outer glow ring (pulsing when synthesizing) */}
          <motion.polygon
            points={hexPoints(0, 0, SIDE + 6)}
            fill="none"
            stroke="#8b5cf6"
            strokeWidth={2}
            strokeOpacity={0.25}
            animate={
              isSynthesizing
                ? { strokeOpacity: [0.15, 0.5, 0.15], scale: [1, 1.06, 1] }
                : { strokeOpacity: 0.25 }
            }
            transition={
              isSynthesizing
                ? { repeat: Infinity, duration: 1.6, ease: 'easeInOut' }
                : { duration: 0.3 }
            }
          />

          {/* Main hexagon */}
          <motion.polygon
            points={points}
            fill="url(#centerGrad)"
            filter={isSynthesizing ? 'url(#centerGlow)' : undefined}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{
              delay: 0.35,
              duration: 0.45,
              type: 'spring',
              stiffness: 260,
              damping: 18,
            }}
          />

          {/* "Center" label */}
          <motion.text
            className={styles.centerLabel}
            x={0}
            y={-4}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.3 }}
          >
            Center
          </motion.text>

          {/* Round number */}
          <motion.text
            className={styles.roundLabel}
            x={0}
            y={12}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.65, duration: 0.3 }}
          >
            R{roundNumber}
          </motion.text>
        </motion.g>
      )}
    </AnimatePresence>
  );
}
