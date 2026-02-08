'use client';

import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import styles from './LanguageToggle.module.css';

export function LanguageToggle() {
  const locale = useLocale();
  const router = useRouter();

  const toggleLocale = () => {
    const newLocale = locale === 'zh' ? 'en' : 'zh';
    document.cookie = `locale=${newLocale};path=/;max-age=31536000`;
    router.refresh();
  };

  return (
    <button
      className={styles.toggle}
      onClick={toggleLocale}
      aria-label={locale === 'zh' ? 'Switch to English' : '切换到中文'}
    >
      {locale === 'zh' ? 'EN' : '中'}
    </button>
  );
}
