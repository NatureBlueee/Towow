'use client';

import type { CenterToolCallData } from '@/types/negotiation';
import styles from './CenterActivity.module.css';

interface CenterActivityProps {
  activities: CenterToolCallData[];
  isSynthesizing: boolean;
}

/** Human-readable description for Center tool calls. */
function describeToolCall(data: CenterToolCallData): string {
  const args = data.tool_args;
  switch (data.tool_name) {
    case 'ask_agent':
      return `Asking ${args.agent_id || 'an agent'}: "${args.question || '...'}"`;
    case 'discover_connections':
      return `Discovering connections between participants`;
    case 'evaluate_gap':
      return `Evaluating capability gaps`;
    case 'initiate_sub_negotiation':
      return `Starting sub-negotiation for a missing capability`;
    case 'output_plan':
      return `Generating final plan`;
    default:
      return `Running ${data.tool_name}`;
  }
}

export function CenterActivity({ activities, isSynthesizing }: CenterActivityProps) {
  if (activities.length === 0 && !isSynthesizing) return null;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>Center is synthesizing</h3>
        {isSynthesizing && <span className={styles.dot} />}
      </div>
      <div className={styles.activityList}>
        {activities.map((activity, i) => (
          <div key={i} className={styles.activityItem}>
            <span className={styles.round}>R{activity.round_number}</span>
            <span className={styles.description}>
              {describeToolCall(activity)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
