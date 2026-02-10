'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { LanguageToggle } from './LanguageToggle';
import styles from './Header.module.css';

interface HeaderProps {
  progress?: number;
}

export function Header({ progress = 0 }: HeaderProps) {
  const t = useTranslations('Header');
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

  // Escape 键关闭菜单
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMenuOpen) {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
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
          <span>{t('back')}</span>
        </Link>
      </div>

      <div className={styles.headerLogo}>ToWow</div>

      <div className={styles.headerRight}>
        <Link href="/articles" className={styles.btnOutline}>{t('articles')}</Link>
        <Link href="/journey" className={styles.btnOutline}>{t('journey')}</Link>
        <Link href="/contribute" className={styles.btnOutline}>{t('contribute')}</Link>
        <Link href="/store/" className={styles.btnOutline}>{t('apps')}</Link>
        <LanguageToggle />
      </div>

      {/* 汉堡菜单按钮 */}
      <button
        className={`${styles.menuButton} ${isMenuOpen ? styles.open : ''}`}
        onClick={() => setIsMenuOpen(!isMenuOpen)}
        aria-label={isMenuOpen ? t('closeMenu') : t('openMenu')}
        aria-expanded={isMenuOpen}
        aria-controls="mobile-menu"
      >
        <div className={styles.menuIcon}>
          <span />
          <span />
          <span />
        </div>
      </button>

      {/* 移动端菜单 */}
      <nav
        id="mobile-menu"
        className={`${styles.mobileMenu} ${isMenuOpen ? styles.open : ''}`}
      >
        <Link href="/" className={styles.mobileNavLink} onClick={handleLinkClick}>
          {t('home')}
        </Link>
        <Link href="/articles" className={styles.mobileNavLink} onClick={handleLinkClick}>
          {t('articles')}
        </Link>
        <Link href="/journey" className={styles.mobileNavLink} onClick={handleLinkClick}>
          {t('journey')}
        </Link>
        <Link href="/contribute" className={styles.mobileNavLink} onClick={handleLinkClick}>
          {t('contribute')}
        </Link>
        <Link href="/store/" className={styles.mobileNavLink} onClick={handleLinkClick}>
          {t('apps')}
        </Link>
        <LanguageToggle />
      </nav>

      <div
        className={styles.progressBar}
        style={{ width: `${progress}%` }}
      />
    </header>
  );
}
