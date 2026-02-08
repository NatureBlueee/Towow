'use client';

import styles from './Skeleton.module.css';

interface SkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  className?: string;
  animation?: 'shimmer' | 'pulse' | 'none';
}

export function Skeleton({
  variant = 'text',
  width,
  height,
  className = '',
  animation = 'shimmer',
}: SkeletonProps) {
  const style: React.CSSProperties = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  return (
    <div
      className={`${styles.skeleton} ${styles[variant]} ${styles[animation]} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}

interface SkeletonMessageProps {
  isCurrentUser?: boolean;
}

export function SkeletonMessage({ isCurrentUser = false }: SkeletonMessageProps) {
  return (
    <div
      className={`${styles.skeletonMessage} ${
        isCurrentUser ? styles.alignRight : ''
      }`}
    >
      <div className={styles.messageHeader}>
        <Skeleton variant="circular" width={24} height={24} />
        <Skeleton variant="text" width={80} height={14} />
        <Skeleton variant="text" width={40} height={12} />
      </div>
      <Skeleton variant="rounded" width="100%" height={60} />
    </div>
  );
}

export function SkeletonTimeline() {
  return (
    <div className={styles.skeletonTimeline}>
      <div className={styles.statusBarSkeleton}>
        <Skeleton variant="circular" width={8} height={8} />
        <Skeleton variant="text" width={80} height={14} />
      </div>
      <div className={styles.messageListSkeleton}>
        <SkeletonMessage />
        <SkeletonMessage isCurrentUser />
        <SkeletonMessage />
      </div>
    </div>
  );
}
