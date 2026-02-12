'use client';

import styles from './SubGraph.module.css';

export interface SubGraphProps {
  subNegotiationId: string;
  gapDescription: string;
  onClick?: () => void;
}

/**
 * SubGraph — a compact thumbnail card representing a sub-negotiation.
 *
 * Shows a small symbolic SVG with connected dots, the gap description
 * (truncated to 2 lines), and a "Gap Found" badge. Clicking fires
 * the onClick callback for future expansion support.
 */
export function SubGraph({ subNegotiationId, gapDescription, onClick }: SubGraphProps) {
  return (
    <div
      className={styles.card}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      aria-label={`Sub-negotiation: ${gapDescription}`}
    >
      {/* Symbolic SVG thumbnail */}
      <div className={styles.thumbnail}>
        <svg
          className={styles.thumbnailSvg}
          viewBox="0 0 80 48"
          aria-hidden="true"
        >
          {/* Lines connecting dots */}
          <line x1="16" y1="14" x2="40" y2="24" className={styles.svgLine} />
          <line x1="16" y1="34" x2="40" y2="24" className={styles.svgLine} />
          <line x1="40" y1="24" x2="64" y2="14" className={styles.svgLine} />
          <line x1="40" y1="24" x2="64" y2="34" className={styles.svgLine} />

          {/* Dots */}
          <circle cx="16" cy="14" r="4" className={styles.svgDot} />
          <circle cx="16" cy="34" r="4" className={styles.svgDot} />
          <circle cx="40" cy="24" r="5" className={styles.svgDotCenter} />
          <circle cx="64" cy="14" r="4" className={styles.svgDot} />
          <circle cx="64" cy="34" r="4" className={styles.svgDot} />
        </svg>
      </div>

      {/* Text content */}
      <div className={styles.body}>
        <span className={styles.badge}>Gap Found</span>
        <p className={styles.description}>{gapDescription}</p>
        <span className={styles.idLabel}>{subNegotiationId}</span>
      </div>
    </div>
  );
}
