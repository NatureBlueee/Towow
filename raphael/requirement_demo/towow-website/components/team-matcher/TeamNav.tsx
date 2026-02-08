'use client';

import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import styles from './TeamNav.module.css';

interface TeamNavProps {
  currentStep?: 'request' | 'browse' | 'progress' | 'proposals';
}

export function TeamNav({ currentStep = 'request' }: TeamNavProps) {
  const router = useRouter();
  const t = useTranslations('TeamMatcher.nav');

  return (
    <nav className={styles.nav}>
      <button
        className={styles.logoBtn}
        onClick={() => router.push('/')}
        aria-label={t('returnHome')}
      >
        <i className="ri-arrow-left-line" />
        <span className={styles.logoText}>ToWow</span>
      </button>

      <div className={styles.steps}>
        <div className={`${styles.step} ${currentStep === 'request' ? styles.active : ''}`}>
          <span className={styles.stepDot} />
          <span className={styles.stepLabel}>{t('sendSignal')}</span>
        </div>
        <div className={styles.stepLine} />
        <div className={`${styles.step} ${currentStep === 'browse' ? styles.active : ''}`}>
          <span className={styles.stepDot} />
          <span className={styles.stepLabel}>{t('browseRequests')}</span>
        </div>
        <div className={styles.stepLine} />
        <div className={`${styles.step} ${currentStep === 'progress' ? styles.active : ''}`}>
          <span className={styles.stepDot} />
          <span className={styles.stepLabel}>{t('waitResonance')}</span>
        </div>
        <div className={styles.stepLine} />
        <div className={`${styles.step} ${currentStep === 'proposals' ? styles.active : ''}`}>
          <span className={styles.stepDot} />
          <span className={styles.stepLabel}>{t('viewProposals')}</span>
        </div>
      </div>

      <div className={styles.spacer} />
    </nav>
  );
}
