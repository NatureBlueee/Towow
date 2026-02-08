'use client';

import { useTranslations } from 'next-intl';
import type { AppMetadata } from '@/lib/apps/types';
import { AppCard } from './AppCard';
import { ComingSoonCard } from './ComingSoonCard';
import styles from './AppGrid.module.css';

interface AppGridProps {
  apps: AppMetadata[];
  title?: string;
  emptyMessage?: string;
  columns?: 1 | 2 | 3 | 4;
  showComingSoonSeparately?: boolean;
}

export function AppGrid({
  apps,
  title,
  emptyMessage,
  columns = 3,
  showComingSoonSeparately = true,
}: AppGridProps) {
  const t = useTranslations('Common');

  // Split apps by status
  const activeApps = apps.filter(
    (app) => app.status === 'active' || app.status === 'beta'
  );
  const comingSoonApps = apps.filter((app) => app.status === 'coming-soon');

  const isEmpty = apps.length === 0;

  return (
    <div className={styles.container}>
      {/* Title */}
      {title && <h2 className={styles.title}>{title}</h2>}

      {/* Empty State */}
      {isEmpty && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>📦</div>
          <p className={styles.emptyText}>{emptyMessage || t('noApps')}</p>
        </div>
      )}

      {/* Active/Beta Apps Grid */}
      {!isEmpty && activeApps.length > 0 && (
        <div className={`${styles.grid} ${styles[`cols-${columns}`]}`}>
          {activeApps.map((app) => (
            <AppCard key={app.id} app={app} />
          ))}
        </div>
      )}

      {/* Coming Soon Section */}
      {!isEmpty && showComingSoonSeparately && comingSoonApps.length > 0 && (
        <div className={styles.comingSoonSection}>
          <h3 className={styles.comingSoonTitle}>{t('comingSoon')}</h3>
          <div className={`${styles.grid} ${styles[`cols-${columns}`]}`}>
            {comingSoonApps.map((app) => (
              <ComingSoonCard key={app.id} app={app} />
            ))}
          </div>
        </div>
      )}

      {/* If not separating, show all together */}
      {!isEmpty && !showComingSoonSeparately && comingSoonApps.length > 0 && (
        <div className={`${styles.grid} ${styles[`cols-${columns}`]}`}>
          {comingSoonApps.map((app) => (
            <ComingSoonCard key={app.id} app={app} />
          ))}
        </div>
      )}
    </div>
  );
}
