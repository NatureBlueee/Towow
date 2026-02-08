'use client';

import type { ResonanceAgent, OfferReceivedData } from '@/types/negotiation';
import styles from './AgentPanel.module.css';

interface AgentPanelProps {
  agents: ResonanceAgent[];
  offers: OfferReceivedData[];
}

const AVATAR_COLORS = ['#6366F1', '#8B5CF6', '#06B6D4', '#F59E0B', '#10B981', '#F43F5E'];

function getAvatarColor(name: string): string {
  const hash = name.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

type AgentStatus = 'matched' | 'offered' | 'waiting';

function getAgentStatus(agentId: string, offers: OfferReceivedData[]): AgentStatus {
  const hasOffer = offers.some((o) => o.agent_id === agentId);
  return hasOffer ? 'offered' : 'waiting';
}

function statusLabel(status: AgentStatus): string {
  switch (status) {
    case 'offered':
      return 'Offered';
    case 'waiting':
      return 'Waiting';
    case 'matched':
      return 'Matched';
  }
}

export function AgentPanel({ agents, offers }: AgentPanelProps) {
  if (agents.length === 0) return null;

  // Build a lookup: agent_id -> offer
  const offerMap = new Map<string, OfferReceivedData>();
  for (const o of offers) {
    offerMap.set(o.agent_id, o);
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>Participants</h3>
        <span className={styles.count}>
          {offers.length}/{agents.length} responded
        </span>
      </div>

      <div className={styles.agentGrid}>
        {agents.map((agent, i) => {
          const status = getAgentStatus(agent.agent_id, offers);
          const offer = offerMap.get(agent.agent_id);
          const color = getAvatarColor(agent.display_name);

          return (
            <div
              key={agent.agent_id}
              className={`${styles.card} ${status === 'offered' ? styles.cardOffered : ''}`}
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className={styles.cardHeader}>
                <div
                  className={styles.avatar}
                  style={{
                    background: `linear-gradient(135deg, ${color}, ${color}80)`,
                  }}
                >
                  {agent.display_name.charAt(0)}
                </div>
                <div className={styles.nameBlock}>
                  <span className={styles.name}>{agent.display_name}</span>
                  <div className={styles.scoreLine}>
                    <div className={styles.scoreBar}>
                      <div
                        className={styles.scoreFill}
                        style={{ width: `${Math.round(agent.resonance_score * 100)}%` }}
                      />
                    </div>
                    <span className={styles.scoreValue}>
                      {Math.round(agent.resonance_score * 100)}%
                    </span>
                  </div>
                </div>
                <span className={`${styles.statusBadge} ${styles[`status_${status}`]}`}>
                  {statusLabel(status)}
                </span>
              </div>

              {/* Show offer content if available */}
              {offer && (
                <div className={styles.offerBody}>
                  <p className={styles.offerContent}>{offer.content}</p>
                  {offer.capabilities.length > 0 && (
                    <div className={styles.capabilities}>
                      {offer.capabilities.map((cap) => (
                        <span key={cap} className={styles.capTag}>
                          {cap}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
