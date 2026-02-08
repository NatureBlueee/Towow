'use client';

import { useTranslations } from 'next-intl';
import { DemoStage, STAGES } from '../shared/types';
import styles from './StageIndicator.module.css';

interface StageIndicatorProps {
  currentStage: DemoStage;
  completedStages: DemoStage[];
  onStageClick?: (stage: DemoStage) => void;
}

export function StageIndicator({
  currentStage,
  completedStages,
  onStageClick,
}: StageIndicatorProps) {
  const t = useTranslations('DemandNegotiation.stages');
  const currentIndex = STAGES.findIndex((s) => s.id === currentStage);

  return (
    <nav className={styles.container} aria-label="Demo progress">
      <div className={styles.track}>
        {STAGES.map((stage, index) => {
          const isCompleted = completedStages.includes(stage.id);
          const isCurrent = stage.id === currentStage;
          const isClickable = isCompleted || isCurrent;

          return (
            <div key={stage.id} className={styles.stageWrapper}>
              {/* Connector line */}
              {index > 0 && (
                <div
                  className={`${styles.connector} ${
                    index <= currentIndex ? styles.connectorActive : ''
                  }`}
                  aria-hidden="true"
                />
              )}

              {/* Stage button */}
              <button
                className={`${styles.stage} ${
                  isCurrent ? styles.stageCurrent : ''
                } ${isCompleted ? styles.stageCompleted : ''}`}
                onClick={() => isClickable && onStageClick?.(stage.id)}
                disabled={!isClickable}
                aria-current={isCurrent ? 'step' : undefined}
                aria-label={`${t(stage.label)}: ${t(stage.description)}`}
              >
                <span className={styles.stageNumber}>
                  {isCompleted ? (
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    index + 1
                  )}
                </span>
                <span className={styles.stageLabel}>{t(stage.label)}</span>
              </button>
            </div>
          );
        })}
      </div>
    </nav>
  );
}
