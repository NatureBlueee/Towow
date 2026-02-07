'use client';

import { useRouter } from 'next/navigation';
import type { AppMetadata } from '@/lib/apps/types';
import styles from './AppCard.module.css';

interface AppCardProps {
  app: AppMetadata;
  className?: string;
}

export function AppCard({ app, className = '' }: AppCardProps) {
  const router = useRouter();

  const handleClick = () => {
    if (app.status === 'active' || app.status === 'beta') {
      router.push(app.path);
    }
  };

  const isClickable = app.status === 'active' || app.status === 'beta';

  return (
    <div
      className={`${styles.card} ${isClickable ? styles.clickable : ''} ${className}`}
      onClick={isClickable ? handleClick : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      } : undefined}
    >
      {/* Status Badge */}
      {app.status !== 'active' && (
        <div className={`${styles.statusBadge} ${styles[`status-${app.status}`]}`}>
          {app.status === 'beta' ? 'Beta' : app.status === 'coming-soon' ? '即将推出' : '已归档'}
        </div>
      )}

      {/* Featured Badge */}
      {app.featured && app.status === 'active' && (
        <div className={styles.featuredBadge}>
          <span className={styles.featuredIcon}>✨</span>
          推荐
        </div>
      )}

      {/* Icon */}
      <div className={styles.iconWrapper}>
        <div className={styles.icon}>{app.icon}</div>
      </div>

      {/* Content */}
      <div className={styles.content}>
        <h3 className={styles.title}>
          <span className={styles.titleEn}>{app.name}</span>
          {app.nameZh && <span className={styles.titleZh}>{app.nameZh}</span>}
        </h3>

        <p className={styles.description}>
          {app.descriptionZh || app.description}
        </p>

        {/* Tags */}
        {app.tags && app.tags.length > 0 && (
          <div className={styles.tags}>
            {app.tags.slice(0, 3).map((tag) => (
              <span key={tag} className={styles.tag}>
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className={styles.footer}>
        {app.author && (
          <div className={styles.author}>
            <span className={styles.authorIcon}>👤</span>
            {app.author}
          </div>
        )}
        {app.version && (
          <div className={styles.version}>v{app.version}</div>
        )}
      </div>

      {/* Hover Effect Overlay */}
      {isClickable && <div className={styles.hoverOverlay} />}
    </div>
  );
}
