'use client';

import { useState, useEffect } from 'react';
import type { AgentNodeProps } from './types';
import styles from './AgentNode.module.css';

/**
 * AgentNode — a resonance participant on the outer ring.
 *
 * CSS-only animations (no framer-motion):
 *  - Entry: keyframes nodeEnter (scale 0.6→1, opacity 0→1)
 *  - Filtered exit: CSS transition to opacity 0, scale 0.4
 *  - Offer pulse: keyframes offerPulse (scale 1→1.15→1)
 *  - Position: CSS transition on transform
 *  - Color: HSL 270→160 (purple→teal) mapped from score
 */

function truncateName(name: string): string {
  if (name.length <= 8) return name;
  return name.slice(0, 8) + '..';
}

/** Map score [0,1] to brand-aligned colour (purple → teal). */
function scoreToColor(score: number): string {
  const hue = Math.round(270 - score * 110);
  return `hsl(${hue}, 58%, 48%)`;
}

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

  const gradId = `agentGrad-${agentId}`;
  const baseColor = isFiltered ? '#9ca3af' : scoreToColor(score);
  const lightColor = isFiltered ? '#d1d5db' : scoreToColorLight(score);
  const displayText = truncateName(displayName);
  const scorePercent = Math.round(score * 100);

  const className = [
    styles.agentGroup,
    isFiltered ? styles.filtered : styles.visible,
    offerPulse ? styles.pulsing : '',
  ].filter(Boolean).join(' ');

  return (
    <g
      className={className}
      transform={`translate(${x}, ${y})`}
      onClick={isFiltered ? undefined : onClick}
      onKeyDown={isFiltered ? undefined : (e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}
      role={isFiltered ? undefined : 'button'}
      tabIndex={isFiltered ? -1 : 0}
      aria-label={`Agent: ${displayName}, score ${scorePercent}%${hasOffer ? ', offer received' : ''}${roleInPlan ? `, role: ${roleInPlan}` : ''}`}
      aria-hidden={isFiltered}
    >
      <defs>
        <radialGradient id={gradId} cx="38%" cy="32%" r="68%">
          <stop offset="0%" stopColor={lightColor} />
          <stop offset="100%" stopColor={baseColor} />
        </radialGradient>
      </defs>

      <circle cx={0} cy={0} r={RADIUS} fill={`url(#${gradId})`} />

      <circle
        cx={0} cy={0} r={RADIUS + 2}
        fill="none" stroke={baseColor}
        strokeWidth={1.5} strokeOpacity={0.3}
      />

      <text className={styles.nameText} x={0} y={-2} fill="#fff">
        {displayText}
      </text>

      <g className={styles.scoreBadge}>
        <rect x={-14} y={RADIUS + 4} width={28} height={16} rx={8} fill={baseColor} />
        <text className={styles.scoreText} x={0} y={RADIUS + 12}>
          {scorePercent}%
        </text>
      </g>

      {hasOffer && (
        <g>
          <circle cx={RADIUS - 4} cy={-RADIUS + 4} r={8} fill="#22c55e" />
          <text className={styles.checkmark} x={RADIUS - 4} y={-RADIUS + 5}>
            {'\u2713'}
          </text>
        </g>
      )}

      {roleInPlan && (
        <text className={styles.roleLabel} x={0} y={RADIUS + 28}>
          {roleInPlan}
        </text>
      )}
    </g>
  );
}
