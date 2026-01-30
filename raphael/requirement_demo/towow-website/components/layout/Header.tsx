'use client';

import Link from 'next/link';
import styles from './Header.module.css';

interface HeaderProps {
  progress?: number;
}

export function Header({ progress = 0 }: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.headerLeft}>
        <Link href="/" className={styles.backLink}>
          <i className="ri-arrow-left-line" />
          <div className={styles.logoIcon}>
            <div className={styles.logoIconInner} />
          </div>
          <span>Back</span>
        </Link>
      </div>

      <div className={styles.headerLogo}>ToWow</div>

      <div className={styles.headerRight}>
        <button type="button" className={styles.btnOutline}>加入网络</button>
      </div>

      <div
        className={styles.progressBar}
        style={{ width: `${progress}%` }}
      />
    </header>
  );
}
