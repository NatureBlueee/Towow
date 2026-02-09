'use client';

import styles from './TeamBackground.module.css';

/**
 * Light glassmorphism background with animated gradient orbs.
 * Used as the shared background for all Team Matcher pages.
 */
export function TeamBackground() {
  return (
    <div className={styles.background}>
      <div className={styles.noiseOverlay} />
      <div className={`${styles.orb} ${styles.orbPrimary}`} />
      <div className={`${styles.orb} ${styles.orbSecondary}`} />
      <div className={`${styles.orb} ${styles.orbAccent}`} />
      {/* Grid lines for depth */}
      <div className={styles.gridLines} />
    </div>
  );
}
