'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useTranslations } from 'next-intl';
import styles from './Footer.module.css';

interface FooterProps {
  variant?: 'home' | 'article';
}

export function Footer({ variant = 'home' }: FooterProps) {
  const t = useTranslations('Footer');

  if (variant === 'article') {
    return (
      <footer className={styles.footerArticle}>
        <div className={styles.footerShape} />
        <div className={styles.footerLinks}>
          <Link href="/">{t('backToHome')}</Link>
          <Link href="/experience">{t('exploreApps')}</Link>
        </div>
        <div className={styles.footerCopy}>
          &copy; {new Date().getFullYear()} ToWow Network. All rights reserved.
        </div>
      </footer>
    );
  }

  // Home variant
  return (
    <footer className={styles.footerHome}>
      <div className={styles.secVisual}>
        <div className={styles.shapeCircle} />
        <div className={styles.shapeSquare} />
      </div>

      <div className={styles.footerContent}>
        <div className={styles.footerTitle}>
          {t('slogan')}
        </div>

        <div className={styles.footerMain}>
          <div className={styles.qrSection}>
            <div className={styles.qrCode}>
              <Image
                src="/微信图片_20260130164654_1683_1902.jpg"
                alt={t('scanQR')}
                width={120}
                height={120}
                style={{ objectFit: 'cover' }}
              />
            </div>
            <span className={styles.qrText}>{t('scanQR')}</span>
          </div>

          <div className={styles.contactSection}>
            <div className={styles.contactTitle}>{t('contactTitle')}</div>
            <a href="mailto:hi@natureblueee.com" className={styles.contactEmail}>
              <i className="ri-mail-send-line" />
              <span>hi@natureblueee.com</span>
            </a>
            <Link href="/experience" className={styles.demoLink}>
              <i className="ri-play-circle-line" />
              {t('exploreApps')}
            </Link>
            <span className={styles.demoHint}>{t('appsHint')}</span>
          </div>
        </div>

        <div className={styles.footerBottom}>
          &copy; {new Date().getFullYear()} ToWow Network. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
