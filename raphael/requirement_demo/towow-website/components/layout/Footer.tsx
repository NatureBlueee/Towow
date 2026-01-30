import Link from 'next/link';
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
          {/* Demo 功能维护中，暂时隐藏入口 */}
          {/* <Link href="/experience">体验 Demo</Link> */}
          <a href="https://twitter.com" target="_blank" rel="noopener noreferrer">
            Twitter
          </a>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
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
              <span className={styles.qrPlaceholder}>微信群二维码</span>
            </div>
            <span className={styles.qrText}>扫码加入社群</span>
          </div>

          <div className={styles.contactSection}>
            <div className={styles.contactTitle}>联系我们</div>
            <a href="mailto:hi@towow.ai" className={styles.contactEmail}>
              <i className="ri-mail-send-line" />
              <span>hi@towow.ai</span>
            </a>
            <div className={styles.socialLinks}>
              <a href="https://twitter.com" target="_blank" rel="noopener noreferrer">
                <i className="ri-twitter-x-line" />
              </a>
              <a href="https://github.com" target="_blank" rel="noopener noreferrer">
                <i className="ri-github-line" />
              </a>
            </div>
            {/* Demo 功能维护中，暂时隐藏入口 */}
            {/* <Link href="/experience" className={styles.demoLink}>
              <i className="ri-play-circle-line" />
              体验 Demo
            </Link> */}
          </div>
        </div>

        <div className={styles.footerBottom}>
          &copy; {new Date().getFullYear()} ToWow Network. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
