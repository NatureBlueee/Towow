import Link from 'next/link';
import Image from 'next/image';
import styles from './Footer.module.css';

interface FooterProps {
  variant?: 'home' | 'article';
}

export function Footer({ variant = 'home' }: FooterProps) {
  if (variant === 'article') {
    return (
      <footer className={styles.footerArticle}>
        <div className={styles.footerShape} />
        <div className={styles.footerLinks}>
          <Link href="/">返回首页</Link>
          <Link href="/experience-v2">体验 Demo</Link>
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
          ToWow，通向惊喜。
        </div>

        <div className={styles.footerMain}>
          <div className={styles.qrSection}>
            <div className={styles.qrCode}>
              <Image
                src="/微信图片_20260130164654_1683_1902.jpg"
                alt="微信群二维码"
                width={120}
                height={120}
                style={{ objectFit: 'cover' }}
              />
            </div>
            <span className={styles.qrText}>扫码加入社群</span>
          </div>

          <div className={styles.contactSection}>
            <div className={styles.contactTitle}>联系我们</div>
            <a href="mailto:hi@natureblueee.com" className={styles.contactEmail}>
              <i className="ri-mail-send-line" />
              <span>hi@natureblueee.com</span>
            </a>
            <Link href="/experience-v2" className={styles.demoLink}>
              <i className="ri-play-circle-line" />
              体验 Demo
            </Link>
            <span className={styles.demoHint}>早期概念演示，持续迭代中</span>
          </div>
        </div>

        <div className={styles.footerBottom}>
          &copy; {new Date().getFullYear()} ToWow Network. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
