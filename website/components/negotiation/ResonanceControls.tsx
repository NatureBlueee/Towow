'use client';

import styles from './ResonanceControls.module.css';

export interface ResonanceControlsProps {
  kStar: number;          // current K* value (integer, 1-50, default 10)
  minScore: number;       // minimum resonance score (0.0-1.0, default 0.5)
  onKStarChange: (k: number) => void;
  onMinScoreChange: (score: number) => void;
  disabled?: boolean;     // disable during active negotiation
}

/**
 * ResonanceControls — compact control panel with two sliders:
 *   - K* (number of agents to match, 1-50)
 *   - Min Score (minimum resonance threshold, 0.0-1.0)
 *
 * Displayed horizontally before demand submission to let users
 * tune resonance parameters. Disabled once a negotiation is active.
 */
export function ResonanceControls({
  kStar,
  minScore,
  onKStarChange,
  onMinScoreChange,
  disabled = false,
}: ResonanceControlsProps) {
  return (
    <div className={`${styles.container} ${disabled ? styles.disabled : ''}`}>
      {/* K* slider */}
      <div className={styles.sliderGroup}>
        <label className={styles.label} htmlFor="kstar-slider">
          K*
        </label>
        <input
          id="kstar-slider"
          type="range"
          className={styles.slider}
          min={1}
          max={50}
          step={1}
          value={kStar}
          onChange={(e) => onKStarChange(Number(e.target.value))}
          disabled={disabled}
        />
        <span className={styles.value}>{kStar}</span>
      </div>

      {/* Min Score slider */}
      <div className={styles.sliderGroup}>
        <label className={styles.label} htmlFor="minscore-slider">
          Min Score
        </label>
        <input
          id="minscore-slider"
          type="range"
          className={styles.slider}
          min={0}
          max={1}
          step={0.05}
          value={minScore}
          onChange={(e) => onMinScoreChange(Number(e.target.value))}
          disabled={disabled}
        />
        <span className={styles.value}>{minScore.toFixed(2)}</span>
      </div>
    </div>
  );
}
