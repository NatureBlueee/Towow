'use client';

import type { ResonanceAgent } from '@/types/negotiation';
import styles from './ResonanceDisplay.module.css';

interface ResonanceDisplayProps {
  agents: ResonanceAgent[];
}

export function ResonanceDisplay({ agents }: ResonanceDisplayProps) {
  if (agents.length === 0) return null;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>
          Found {agents.length} relevant participant{agents.length !== 1 ? 's' : ''}
        </h3>
        <span className={styles.badge}>Resonance</span>
      </div>
      <div className={styles.agentList}>
        {agents.map((agent, i) => (
          <div
            key={agent.agent_id}
            className={styles.agentItem}
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className={styles.agentAvatar}>
              {agent.display_name.charAt(0)}
            </div>
            <div className={styles.agentInfo}>
              <span className={styles.agentName}>{agent.display_name}</span>
              <div className={styles.scoreBar}>
                <div
                  className={styles.scoreFill}
                  style={{ width: `${Math.round(agent.resonance_score * 100)}%` }}
                />
              </div>
            </div>
            <span className={styles.scoreValue}>
              {Math.round(agent.resonance_score * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
