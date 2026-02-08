'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import styles from './SignalVisualization.module.css';
import type { ProgressStage, OfferSummary } from '@/lib/team-matcher/types';

interface SignalVisualizationProps {
  stage: ProgressStage;
  offersCount: number;
  offerSummaries: OfferSummary[];
}

/**
 * Visual representation of the 3-stage matching process:
 * 1. Broadcasting - animated signal pulse rings
 * 2. Receiving - offer cards flying in
 * 3. Generating - synthesis animation
 */
export function SignalVisualization({
  stage,
  offersCount,
  offerSummaries,
}: SignalVisualizationProps) {
  const t = useTranslations('TeamMatcher.signal');
  const [visibleOffers, setVisibleOffers] = useState<number>(0);

  // Stagger offer visibility for fly-in animation
  useEffect(() => {
    if (stage === 'receiving' && offerSummaries.length > visibleOffers) {
      const timer = setTimeout(() => {
        setVisibleOffers((prev) => prev + 1);
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [stage, offerSummaries.length, visibleOffers]);

  return (
    <div className={styles.container}>
      {/* Central node */}
      <div className={styles.centerNode}>
        <div className={styles.centerIcon}>
          {stage === 'broadcasting' && <i className="ri-signal-tower-line" />}
          {stage === 'receiving' && <i className="ri-radar-line" />}
          {stage === 'generating' && <i className="ri-magic-line" />}
          {stage === 'complete' && <i className="ri-check-double-line" />}
        </div>
        {/* Pulse rings for broadcasting stage */}
        {stage === 'broadcasting' && (
          <>
            <div className={`${styles.pulseRing} ${styles.ring1}`} />
            <div className={`${styles.pulseRing} ${styles.ring2}`} />
            <div className={`${styles.pulseRing} ${styles.ring3}`} />
          </>
        )}
        {/* Glow effect for generating stage */}
        {stage === 'generating' && <div className={styles.generateGlow} />}
        {/* Success glow for complete */}
        {stage === 'complete' && <div className={styles.completeGlow} />}
      </div>

      {/* Stage text */}
      <div className={styles.stageInfo}>
        {stage === 'broadcasting' && (
          <>
            <h2 className={styles.stageTitle}>{t('broadcastingTitle')}</h2>
            <p className={styles.stageDesc}>{t('broadcastingDesc')}</p>
          </>
        )}
        {stage === 'receiving' && (
          <>
            <h2 className={styles.stageTitle}>
              <span className={styles.countHighlight}>{offersCount}</span>{' '}
              {t('receivingTitle', { count: offersCount })}
            </h2>
            <p className={styles.stageDesc}>{t('receivingDesc')}</p>
          </>
        )}
        {stage === 'generating' && (
          <>
            <h2 className={styles.stageTitle}>{t('generatingTitle')}</h2>
            <p className={styles.stageDesc}>
              {t('generatingDesc', { count: offersCount })}
            </p>
          </>
        )}
        {stage === 'complete' && (
          <>
            <h2 className={styles.stageTitle}>{t('completeTitle')}</h2>
            <p className={styles.stageDesc}>
              {t('completeDesc', { count: offersCount })}
            </p>
          </>
        )}
      </div>

      {/* Offer cards during receiving stage */}
      {(stage === 'receiving' || stage === 'generating' || stage === 'complete') &&
        offerSummaries.length > 0 && (
          <div className={styles.offerList}>
            {offerSummaries.map((offer, index) => (
              <div
                key={`${offer.agent_name}-${index}`}
                className={`${styles.offerCard} ${
                  index < visibleOffers ? styles.offerVisible : ''
                }`}
                style={{
                  animationDelay: `${index * 100}ms`,
                }}
              >
                <div className={styles.offerAvatar}>
                  {offer.agent_name.charAt(0)}
                </div>
                <div className={styles.offerContent}>
                  <span className={styles.offerName}>{offer.agent_name}</span>
                  <span className={styles.offerBrief}>{offer.brief}</span>
                </div>
                <div className={styles.offerSkills}>
                  {offer.skills.slice(0, 2).map((skill) => (
                    <span key={skill} className={styles.offerSkillTag}>
                      {skill}
                    </span>
                  ))}
                  {offer.skills.length > 2 && (
                    <span className={styles.offerSkillMore}>
                      +{offer.skills.length - 2}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

      {/* Progress bar */}
      <div className={styles.progressContainer}>
        <div className={styles.progressTrack}>
          <div
            className={styles.progressFill}
            style={{
              width:
                stage === 'broadcasting'
                  ? '25%'
                  : stage === 'receiving'
                  ? '55%'
                  : stage === 'generating'
                  ? '80%'
                  : '100%',
            }}
          />
        </div>
        <div className={styles.progressSteps}>
          <span
            className={`${styles.progressStep} ${
              stage === 'broadcasting' ? styles.progressStepActive : ''
            } ${
              ['receiving', 'generating', 'complete'].includes(stage)
                ? styles.progressStepDone
                : ''
            }`}
          >
            {t('stepBroadcast')}
          </span>
          <span
            className={`${styles.progressStep} ${
              stage === 'receiving' ? styles.progressStepActive : ''
            } ${
              ['generating', 'complete'].includes(stage)
                ? styles.progressStepDone
                : ''
            }`}
          >
            {t('stepResponse')}
          </span>
          <span
            className={`${styles.progressStep} ${
              stage === 'generating' ? styles.progressStepActive : ''
            } ${stage === 'complete' ? styles.progressStepDone : ''}`}
          >
            {t('stepGenerate')}
          </span>
          <span
            className={`${styles.progressStep} ${
              stage === 'complete' ? styles.progressStepActive : ''
            }`}
          >
            {t('stepComplete')}
          </span>
        </div>
      </div>
    </div>
  );
}
