'use client';

import { useRouter } from 'next/navigation';
import styles from './TeamNav.module.css';

interface TeamNavProps {
  currentStep?: 'request' | 'progress' | 'proposals';
}

export function TeamNav({ currentStep = 'request' }: TeamNavProps) {
  const router = useRouter();

  return (
    <nav className={styles.nav}>
      <button
        className={styles.logoBtn}
        onClick={() => router.push('/')}
        aria-label="Return to home"
      >
        <i className="ri-arrow-left-line" />
        <span className={styles.logoText}>ToWow</span>
      </button>

      <div className={styles.steps}>
        <div className={`${styles.step} ${currentStep === 'request' ? styles.active : ''}`}>
          <span className={styles.stepDot} />
          <span className={styles.stepLabel}>发出信号</span>
        </div>
        <div className={styles.stepLine} />
        <div className={`${styles.step} ${currentStep === 'progress' ? styles.active : ''}`}>
          <span className={styles.stepDot} />
          <span className={styles.stepLabel}>等待共振</span>
        </div>
        <div className={styles.stepLine} />
        <div className={`${styles.step} ${currentStep === 'proposals' ? styles.active : ''}`}>
          <span className={styles.stepDot} />
          <span className={styles.stepLabel}>查看方案</span>
        </div>
      </div>

      <div className={styles.spacer} />
    </nav>
  );
}
