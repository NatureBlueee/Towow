'use client';

import type { PlanReadyData } from '@/types/negotiation';
import styles from './PlanResult.module.css';

interface PlanResultProps {
  plan: PlanReadyData;
  onAccept?: () => void;
  onReject?: () => void;
}

export function PlanResult({ plan, onAccept, onReject }: PlanResultProps) {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>Plan Ready</h3>
        <span className={styles.badge}>
          {plan.center_rounds} round{plan.center_rounds !== 1 ? 's' : ''}
        </span>
      </div>

      <div className={styles.planBody}>
        {plan.plan_text.split('\n').map((line, i) => (
          <p key={i} className={line.trim() === '' ? styles.spacer : styles.line}>
            {line}
          </p>
        ))}
      </div>

      <div className={styles.participants}>
        <span className={styles.participantsLabel}>Participants:</span>
        <div className={styles.participantsList}>
          {plan.participating_agents.map((id) => (
            <span key={id} className={styles.participantTag}>{id}</span>
          ))}
        </div>
      </div>

      {(onAccept || onReject) && (
        <div className={styles.actions}>
          {onReject && (
            <button className={styles.rejectButton} onClick={onReject}>
              Reject
            </button>
          )}
          {onAccept && (
            <button className={styles.acceptButton} onClick={onAccept}>
              Accept Plan
            </button>
          )}
        </div>
      )}
    </div>
  );
}
