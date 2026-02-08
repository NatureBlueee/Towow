'use client';

import type { CenterToolCallData, PlanReadyData } from '@/types/negotiation';
import styles from './CenterPanel.module.css';

interface CenterPanelProps {
  activities: CenterToolCallData[];
  plan: PlanReadyData | null;
  isSynthesizing: boolean;
  onAcceptPlan?: () => void;
  onRejectPlan?: () => void;
}

/** Human-readable description for Center tool calls. */
function describeToolCall(data: CenterToolCallData): string {
  const args = data.tool_args;
  switch (data.tool_name) {
    case 'ask_agent':
      return `Asking ${args.agent_id || 'an agent'}: "${args.question || '...'}"`;
    case 'discover_connections':
      return 'Discovering connections between participants';
    case 'evaluate_gap':
      return 'Evaluating capability gaps';
    case 'initiate_sub_negotiation':
      return 'Starting sub-negotiation for a missing capability';
    case 'output_plan':
      return 'Generating final plan';
    default:
      return `Running ${data.tool_name}`;
  }
}

export function CenterPanel({
  activities,
  plan,
  isSynthesizing,
  onAcceptPlan,
  onRejectPlan,
}: CenterPanelProps) {
  if (activities.length === 0 && !isSynthesizing && !plan) return null;

  return (
    <div className={styles.container}>
      {/* Synthesis progress */}
      {(activities.length > 0 || isSynthesizing) && (
        <div className={styles.synthesisSection}>
          <div className={styles.header}>
            <h3 className={styles.title}>Center Synthesis</h3>
            {isSynthesizing && !plan && <span className={styles.activeDot} />}
          </div>

          {activities.length > 0 && (
            <div className={styles.activityList}>
              {activities.map((activity, i) => (
                <div key={i} className={styles.activityItem}>
                  <span className={styles.round}>R{activity.round_number}</span>
                  <span className={styles.toolName}>{activity.tool_name}</span>
                  <span className={styles.description}>
                    {describeToolCall(activity)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {isSynthesizing && !plan && activities.length === 0 && (
            <div className={styles.waiting}>
              <span className={styles.spinner} />
              <span>Center is analyzing offers...</span>
            </div>
          )}
        </div>
      )}

      {/* Plan output */}
      {plan && (
        <div className={styles.planSection}>
          <div className={styles.planHeader}>
            <h3 className={styles.planTitle}>Plan Ready</h3>
            <span className={styles.roundsBadge}>
              {plan.center_rounds} round{plan.center_rounds !== 1 ? 's' : ''}
            </span>
          </div>

          <div className={styles.planBody}>
            {plan.plan_text.split('\n').map((line, i) => (
              <p key={i} className={line.trim() === '' ? styles.spacer : styles.planLine}>
                {line}
              </p>
            ))}
          </div>

          <div className={styles.participants}>
            <span className={styles.participantsLabel}>Participants:</span>
            <div className={styles.participantsList}>
              {plan.participating_agents.map((id) => (
                <span key={id} className={styles.participantTag}>
                  {id}
                </span>
              ))}
            </div>
          </div>

          {(onAcceptPlan || onRejectPlan) && (
            <div className={styles.actions}>
              {onRejectPlan && (
                <button className={styles.rejectButton} onClick={onRejectPlan}>
                  Reject
                </button>
              )}
              {onAcceptPlan && (
                <button className={styles.acceptButton} onClick={onAcceptPlan}>
                  Accept Plan
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
