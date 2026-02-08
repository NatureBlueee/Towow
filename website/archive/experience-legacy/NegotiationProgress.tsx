'use client';

import styles from './NegotiationProgress.module.css';

type NegotiationStatus = 'waiting' | 'in_progress' | 'completed' | 'failed';

interface NegotiationProgressProps {
  status: NegotiationStatus;
  currentRound?: number;
  totalRounds?: number;
}

const steps = [
  { key: 'waiting', label: '等待开始', icon: '1' },
  { key: 'in_progress', label: '协商中', icon: '2' },
  { key: 'completed', label: '已完成', icon: '3' },
];

function getStepStatus(
  stepKey: string,
  currentStatus: NegotiationStatus
): 'completed' | 'active' | 'pending' {
  const statusOrder = ['waiting', 'in_progress', 'completed'];
  const currentIndex = statusOrder.indexOf(currentStatus);
  const stepIndex = statusOrder.indexOf(stepKey);

  if (currentStatus === 'failed') {
    if (stepKey === 'completed') return 'pending';
    if (stepIndex < currentIndex) return 'completed';
    return 'active';
  }

  if (stepIndex < currentIndex) return 'completed';
  if (stepIndex === currentIndex) return 'active';
  return 'pending';
}

export function NegotiationProgress({
  status,
  currentRound,
  totalRounds,
}: NegotiationProgressProps) {
  return (
    <div className={styles.progress}>
      <div className={styles.steps}>
        {steps.map((step, index) => {
          const stepStatus = getStepStatus(step.key, status);
          const isLast = index === steps.length - 1;

          return (
            <div key={step.key} className={styles.stepWrapper}>
              <div
                className={`${styles.step} ${styles[stepStatus]} ${
                  status === 'failed' && step.key === 'in_progress'
                    ? styles.failed
                    : ''
                }`}
              >
                <div className={styles.stepIcon}>
                  {stepStatus === 'completed' ? (
                    <svg
                      className={styles.checkmark}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                    >
                      <path d="M5 12l5 5L19 7" />
                    </svg>
                  ) : (
                    <span>{step.icon}</span>
                  )}
                  {stepStatus === 'active' && status !== 'failed' && (
                    <span className={styles.pulse} />
                  )}
                </div>
                <span className={styles.stepLabel}>{step.label}</span>
              </div>
              {!isLast && (
                <div
                  className={`${styles.connector} ${
                    stepStatus === 'completed' ? styles.connectorActive : ''
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
      {status === 'in_progress' && currentRound && totalRounds && (
        <div className={styles.roundInfo}>
          <span className={styles.roundLabel}>
            第 {currentRound} / {totalRounds} 轮
          </span>
          <div className={styles.roundProgress}>
            <div
              className={styles.roundProgressBar}
              style={{
                width: `${(currentRound / totalRounds) * 100}%`,
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
