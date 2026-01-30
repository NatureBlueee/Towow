'use client';

import { ContentCard } from '@/components/ui/ContentCard';
import { Button } from '@/components/ui/Button';
import styles from './ResultPanel.module.css';

interface Participant {
  agent_id: string;
  agent_name: string;
  contribution: string;
}

interface ResultPanelProps {
  status: 'completed' | 'failed' | 'timeout';
  summary: string;
  participants?: Participant[];
  finalProposal?: string;
  onReset: () => void;
}

export function ResultPanel({
  status,
  summary,
  participants = [],
  finalProposal,
  onReset,
}: ResultPanelProps) {
  const isSuccess = status === 'completed';

  return (
    <ContentCard className={styles.resultPanel}>
      <div className={`${styles.icon} ${isSuccess ? styles.success : styles.error}`}>
        {isSuccess ? (
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
            <path
              d="M9 12l2 2 4-4"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
          </svg>
        ) : (
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 8v4m0 4h.01"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
          </svg>
        )}
      </div>

      <h2 className={styles.title}>
        {isSuccess ? 'Negotiation Completed' : 'Negotiation Failed'}
      </h2>

      <p className={styles.summary}>{summary}</p>

      {finalProposal && (
        <div className={styles.proposal}>
          <h3 className={styles.proposalTitle}>Final Proposal</h3>
          <p className={styles.proposalContent}>{finalProposal}</p>
        </div>
      )}

      {participants.length > 0 && (
        <div className={styles.participants}>
          <h3 className={styles.participantsTitle}>Participants</h3>
          <ul className={styles.participantsList}>
            {participants.map((p) => (
              <li key={p.agent_id} className={styles.participant}>
                <span className={styles.participantName}>{p.agent_name}</span>
                <span className={styles.participantContribution}>{p.contribution}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Button variant="primary" onClick={onReset}>
        Start New Negotiation
      </Button>
    </ContentCard>
  );
}
