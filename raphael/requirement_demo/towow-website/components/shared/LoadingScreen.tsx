'use client';

import styles from './LoadingScreen.module.css';

interface LoadingScreenProps {
  message?: string;
}

export function LoadingScreen({ message = 'Loading...' }: LoadingScreenProps) {
  return (
    <div className={styles.loadingScreen}>
      <div className={styles.spinner}>
        <div className={styles.dot} />
        <div className={styles.dot} />
        <div className={styles.dot} />
      </div>
      <p className={styles.message}>{message}</p>
    </div>
  );
}
