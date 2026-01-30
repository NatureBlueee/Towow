'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import styles from './Header.module.css';

interface HeaderProps {
  progress?: number;
}

export function Header({ progress = 0 }: HeaderProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // 关闭菜单时恢复滚动
  useEffect(() => {
    if (isMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMenuOpen]);

  const handleLinkClick = () => {
    setIsMenuOpen(false);
  };

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
        <Link href="/experience" className={styles.btnOutline}>体验 Demo</Link>
      </div>

      {/* 汉堡菜单按钮 */}
      <button
        className={`${styles.menuButton} ${isMenuOpen ? styles.open : ''}`}
        onClick={() => setIsMenuOpen(!isMenuOpen)}
        aria-label={isMenuOpen ? '关闭菜单' : '打开菜单'}
        aria-expanded={isMenuOpen}
      >
        <div className={styles.menuIcon}>
          <span />
          <span />
          <span />
        </div>
      </button>

      {/* 移动端菜单 */}
      <nav className={`${styles.mobileMenu} ${isMenuOpen ? styles.open : ''}`}>
        <Link href="/" className={styles.mobileNavLink} onClick={handleLinkClick}>
          首页
        </Link>
        <Link href="/articles" className={styles.mobileNavLink} onClick={handleLinkClick}>
          文章
        </Link>
        <Link href="/experience" className={styles.mobileNavLink} onClick={handleLinkClick}>
          体验 Demo
        </Link>
      </nav>

      <div
        className={styles.progressBar}
        style={{ width: `${progress}%` }}
      />
    </header>
  );
}
