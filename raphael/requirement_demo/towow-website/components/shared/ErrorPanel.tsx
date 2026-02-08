'use client';

import { useTranslations } from 'next-intl';
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
  title,
  message,
  onRetry,
  onReset,
}: ErrorPanelProps) {
  const t = useTranslations('Common');

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

      <h2 className={styles.title}>{title || t('error')}</h2>
      <p className={styles.message}>{message}</p>

      <div className={styles.actions}>
        {onRetry && (
          <Button variant="primary" onClick={onRetry}>
            {t('retry')}
          </Button>
        )}
        {onReset && (
          <Button variant="outline" onClick={onReset}>
            {t('startOver')}
          </Button>
        )}
      </div>
    </ContentCard>
  );
}
