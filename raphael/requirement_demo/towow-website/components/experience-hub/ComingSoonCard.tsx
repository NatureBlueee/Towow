'use client';

import type { AppMetadata } from '@/lib/apps/types';
import styles from './ComingSoonCard.module.css';

interface ComingSoonCardProps {
  app: AppMetadata;
  className?: string;
}

export function ComingSoonCard({ app, className = '' }: ComingSoonCardProps) {
  return (
    <div className={`${styles.card} ${className}`}>
      {/* Coming Soon Badge */}
      <div className={styles.badge}>
        <span className={styles.badgeIcon}>🚀</span>
        即将推出
      </div>

      {/* Icon */}
      <div className={styles.iconWrapper}>
        <div className={styles.icon}>{app.icon}</div>
        <div className={styles.iconGlow} />
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

      {/* Notification Option */}
      <div className={styles.notifyWrapper}>
        <button className={styles.notifyButton} disabled>
          <span className={styles.notifyIcon}>🔔</span>
          通知我
        </button>
        <p className={styles.notifyHint}>敬请期待</p>
      </div>

      {/* Background Effect */}
      <div className={styles.bgEffect} />
    </div>
  );
}
