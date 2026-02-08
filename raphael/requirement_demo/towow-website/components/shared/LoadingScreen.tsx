'use client';

import { useTranslations } from 'next-intl';
import styles from './LoadingScreen.module.css';

interface LoadingScreenProps {
  message?: string;
}

export function LoadingScreen({ message }: LoadingScreenProps) {
  const t = useTranslations('Common');

  return (
    <div className={styles.loadingScreen}>
      <div className={styles.spinner}>
        <div className={styles.dot} />
        <div className={styles.dot} />
        <div className={styles.dot} />
      </div>
      <p className={styles.message}>{message || t('loading')}</p>
    </div>
  );
}
