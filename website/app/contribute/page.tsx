// app/contribute/page.tsx
import Link from 'next/link';
import { getTranslations, getLocale } from 'next-intl/server';
import { getContributeData } from '../../lib/contribute-data';
import styles from './contribute.module.css';

export async function generateMetadata() {
  const t = await getTranslations('Contribute');
  return {
    title: t('metaTitle'),
    description: t('metaDesc'),
  };
}

export default async function ContributePage() {
  const t = await getTranslations('Contribute');
  const locale = await getLocale();
  const tracks = getContributeData(locale);

  const totalTasks = tracks.reduce((sum, tr) => sum + tr.tasks.length, 0);
  const tier1Count = tracks.reduce(
    (sum, tr) => sum + tr.tasks.filter(task => task.tier === 1).length, 0
  );

  function tierLabel(tier: 1 | 2 | 'template') {
    if (tier === 1) return t('tier1');
    if (tier === 2) return t('tier2');
    return t('tierTemplate');
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t('pageTitle')}</h1>
        <p className={styles.subtitle}>
          {t('subtitle', { totalTasks, tier1Count })}
        </p>
      </header>

      {tracks.map((track) => (
        <section key={track.id} className={styles.track}>
          <div className={styles.trackHead}>
            <div className={styles.trackLabelRow}>
              <span className={styles.trackDot} style={{ background: track.color }} />
              <span className={styles.trackLabel}>{t('track')}</span>
            </div>
            <h2 className={styles.trackName}>{track.name}</h2>
            <div className={styles.trackMeta}>
              <p className={styles.trackMetaRow}>
                <span className={styles.fieldLabel}>{t('goal')}</span>
                {track.goal}
              </p>
              {track.dependency && (
                <p className={styles.trackMetaRow}>
                  <span className={styles.fieldLabel}>{t('dependency')}</span>
                  {track.dependency}
                </p>
              )}
            </div>
          </div>

          <div className={styles.taskGrid}>
            {track.tasks.map((task, index) => (
              <a
                key={index}
                href={task.prdUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.taskCard}
              >
                <div className={styles.cardTop}>
                  <span className={styles.taskNum}>{t('taskNum', { num: index + 1 })}</span>
                  <span className={`${styles.tier} ${
                    task.tier === 1 ? styles.tier1
                      : task.tier === 2 ? styles.tier2
                      : styles.tierTpl
                  }`}>
                    {tierLabel(task.tier)}
                  </span>
                </div>
                <h3 className={styles.taskName}>{task.name}</h3>
                <p className={styles.taskDesc}>{task.oneLiner}</p>
                <p className={styles.taskTarget}>
                  <span className={styles.fieldLabel}>{t('suitableFor')}</span>
                  {task.target}
                </p>
              </a>
            ))}
          </div>
        </section>
      ))}

      <section className={styles.howTo}>
        <h2 className={styles.howToTitle}>{t('howToTitle')}</h2>
        <p className={styles.howToText}>
          {t('howToText')}
        </p>
        <Link href="/articles/join-us" className={styles.ctaLink}>
          {t('joinCta')} &#8594;
        </Link>
      </section>
    </div>
  );
}
