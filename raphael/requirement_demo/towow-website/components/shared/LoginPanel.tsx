'use client';

import { useTranslations } from 'next-intl';
import { ContentCard } from '@/components/ui/ContentCard';
import { Button } from '@/components/ui/Button';
import styles from './LoginPanel.module.css';

interface LoginPanelProps {
  onLoginClick: () => void;
  isLoading?: boolean;
}

export function LoginPanel({ onLoginClick, isLoading = false }: LoginPanelProps) {
  const t = useTranslations('Common');

  return (
    <ContentCard className={styles.loginPanel}>
      <div className={styles.icon}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2"/>
          <path d="M4 20C4 16.6863 7.58172 14 12 14C16.4183 14 20 16.6863 20 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </div>
      <h2 className={styles.title}>{t('loginTitle')}</h2>
      <p className={styles.description}>
        {t('loginDescription')}
      </p>
      <Button
        variant="primary"
        onClick={onLoginClick}
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <span className={styles.spinner} />
            {t('loggingIn')}
          </>
        ) : (
          t('loginWithSecondMe')
        )}
      </Button>
      <p className={styles.hint}>
        {t('loginHint')}
      </p>
    </ContentCard>
  );
}
