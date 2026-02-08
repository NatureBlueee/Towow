// app/experience/page.tsx
import { getTranslations } from 'next-intl/server';
import { AppGrid } from '@/components/experience-hub/AppGrid';
import { getActiveApps, getComingSoonApps } from '@/lib/apps/registry';
import styles from './experience.module.css';

export async function generateMetadata() {
  const t = await getTranslations('Experience');
  return {
    title: t('metaTitle'),
    description: t('metaDesc'),
  };
}

export default async function ExperiencePage() {
  const t = await getTranslations('Experience');
  const activeApps = getActiveApps();
  const comingSoonApps = getComingSoonApps();

  return (
    <div className={styles.container}>
      {/* Hero Section */}
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>
          {t.rich('heroTitle', {
            towow: () => <span className={styles.heroEn}>ToWow</span>,
          })}
        </h1>
        <p className={styles.heroSubtitle}>
          {t('heroSubtitle')}
        </p>
      </section>

      {/* Active Apps */}
      <section className={styles.section}>
        <AppGrid
          apps={activeApps}
          title={t('activeApps')}
          emptyMessage={t('noActiveApps')}
          columns={3}
          showComingSoonSeparately={false}
        />
      </section>

      {/* Coming Soon Apps */}
      {comingSoonApps.length > 0 && (
        <section className={styles.section}>
          <AppGrid
            apps={comingSoonApps}
            title=""
            emptyMessage=""
            columns={3}
            showComingSoonSeparately={true}
          />
        </section>
      )}

      {/* Call to Action */}
      <section className={styles.cta}>
        <div className={styles.ctaCard}>
          <h2 className={styles.ctaTitle}>{t('ctaTitle')}</h2>
          <p className={styles.ctaText}>
            {t('ctaText')}
          </p>
          <a
            href="/articles/join-us"
            className={styles.ctaButton}
          >
            {t('ctaButton')}
          </a>
        </div>
      </section>
    </div>
  );
}
