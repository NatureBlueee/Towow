'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AgentNodeProps } from './types';
import styles from './AgentNode.module.css';

/**
 * AgentNode — a resonance participant on the outer ring.
 *
 * Visual mapping:
 *  - Circle colour is derived from the resonance score via HSL interpolation
 *    (0 = red / 0deg, 0.5 = yellow / 60deg, 1.0 = green / 120deg).
 *  - Filtered agents fade to grey and disappear with an exit animation.
 *  - Agents that have submitted an offer display a small checkmark badge.
 *  - If the agent has a role in the final plan, a label appears below the node.
 */

/** Truncate name to at most 8 characters. */
function truncateName(name: string): string {
  if (name.length <= 8) return name;
  return name.slice(0, 8) + '..';
}

/** Map score [0,1] to a brand-aligned colour (purple → teal → green). */
function scoreToColor(score: number): string {
  // Hue range: 270 (purple, low score) → 160 (teal/green, high score)
  const hue = Math.round(270 - score * 110);
  return `hsl(${hue}, 58%, 48%)`;
}

/** Slightly lighter version for the gradient highlight. */
function scoreToColorLight(score: number): string {
  const hue = Math.round(270 - score * 110);
  return `hsl(${hue}, 65%, 62%)`;
}

const RADIUS = 30;

export function AgentNode({
  x,
  y,
  agentId,
  displayName,
  score,
  isFiltered,
  hasOffer,
  offerContent,
  roleInPlan,
  onClick,
}: AgentNodeProps) {
  // Track previous hasOffer to detect "offer just arrived" pulse.
  const [prevHasOffer, setPrevHasOffer] = useState(hasOffer);
  const [offerPulse, setOfferPulse] = useState(false);

  useEffect(() => {
    if (hasOffer && !prevHasOffer) {
      setOfferPulse(true);
      const t = setTimeout(() => setOfferPulse(false), 400);
      setPrevHasOffer(true);
      return () => clearTimeout(t);
    }
    setPrevHasOffer(hasOffer);
  }, [hasOffer, prevHasOffer]);

  // Unique gradient id per agent to avoid collisions in SVG
  const gradId = `agentGrad-${agentId}`;
  const baseColor = isFiltered ? '#9ca3af' : scoreToColor(score);
  const lightColor = isFiltered ? '#d1d5db' : scoreToColorLight(score);

  const displayText = truncateName(displayName);
  const scorePercent = Math.round(score * 100);

  return (
    <AnimatePresence>
      {/* When isFiltered becomes true, the node animates out then unmounts */}
      {!isFiltered && (
        <motion.g
          key={agentId}
          className={styles.agentGroup}
          onClick={onClick}
          onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}
          role="button"
          tabIndex={0}
          aria-label={`Agent: ${displayName}, score ${scorePercent}%${hasOffer ? ', offer received' : ''}${roleInPlan ? `, role: ${roleInPlan}` : ''}`}
          initial={{ opacity: 0, scale: 0.6, x, y }}
          animate={{
            opacity: 1,
            scale: offerPulse ? [1, 1.15, 1] : 1,
            x,
            y,
          }}
          exit={{
            opacity: 0,
            scale: 0.4,
            transition: { duration: 0.6, ease: 'easeIn' },
          }}
          transition={{
            opacity: { duration: 0.3 },
            scale: offerPulse
              ? { duration: 0.3, ease: 'easeOut' }
              : { type: 'spring', stiffness: 300, damping: 22 },
            x: { duration: 0.3 },
            y: { duration: 0.3 },
          }}
        >
          {/* Gradient */}
          <defs>
            <radialGradient id={gradId} cx="38%" cy="32%" r="68%">
              <stop offset="0%" stopColor={lightColor} />
              <stop offset="100%" stopColor={baseColor} />
            </radialGradient>
          </defs>

          {/* Main circle */}
          <circle
            cx={0}
            cy={0}
            r={RADIUS}
            fill={`url(#${gradId})`}
          />

          {/* Outer ring highlight on hover (thin stroke) */}
          <circle
            cx={0}
            cy={0}
            r={RADIUS + 2}
            fill="none"
            stroke={baseColor}
            strokeWidth={1.5}
            strokeOpacity={0.3}
          />

          {/* Display name */}
          <text className={styles.nameText} x={0} y={-2} fill="#fff">
            {displayText}
          </text>

          {/* Score badge below the circle */}
          <g className={styles.scoreBadge}>
            <rect
              x={-14}
              y={RADIUS + 4}
              width={28}
              height={16}
              rx={8}
              fill={baseColor}
            />
            <text className={styles.scoreText} x={0} y={RADIUS + 12}>
              {scorePercent}%
            </text>
          </g>

          {/* Offer checkmark badge (top-right) */}
          {hasOffer && (
            <g>
              <circle cx={RADIUS - 4} cy={-RADIUS + 4} r={8} fill="#22c55e" />
              <text className={styles.checkmark} x={RADIUS - 4} y={-RADIUS + 5}>
                {'\u2713'}
              </text>
            </g>
          )}

          {/* Role-in-plan label (below score badge) */}
          {roleInPlan && (
            <text className={styles.roleLabel} x={0} y={RADIUS + 28}>
              {roleInPlan}
            </text>
          )}
        </motion.g>
      )}
    </AnimatePresence>
  );
}
