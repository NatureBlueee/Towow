'use client';

import { ContentCard } from '@/components/ui/ContentCard';
import { Button } from '@/components/ui/Button';
import styles from './ErrorPanel.module.css';

interface ErrorPanelProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  onReset?: () => void;
}

export function ErrorPanel({
  title = 'Something went wrong',
  message,
  onRetry,
  onReset,
}: ErrorPanelProps) {
  return (
    <ContentCard className={styles.errorPanel}>
      <div className={styles.icon}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      <h2 className={styles.title}>{title}</h2>
      <p className={styles.message}>{message}</p>

      <div className={styles.actions}>
        {onRetry && (
          <Button variant="primary" onClick={onRetry}>
            Retry
          </Button>
        )}
        {onReset && (
          <Button variant="outline" onClick={onReset}>
            Start Over
          </Button>
        )}
      </div>
    </ContentCard>
  );
}
