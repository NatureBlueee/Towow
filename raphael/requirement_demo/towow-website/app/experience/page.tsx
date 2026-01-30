import Link from 'next/link';
import styles from './page.module.css';

export const metadata = {
  title: 'ToWow Experience - Coming Soon',
  description: 'Experience AI Agent Collaboration Network',
};

export default function ExperiencePage() {
  return (
    <div className={styles.maintenanceContainer}>
      <div className={styles.maintenanceContent}>
        <div className={styles.maintenanceIcon}>
          <i className="ri-tools-line" />
        </div>
        <h1 className={styles.maintenanceTitle}>功能维护中</h1>
        <p className={styles.maintenanceDescription}>
          我们正在优化 Agent 协作体验，敬请期待。
        </p>
        <Link href="/" className={styles.backButton}>
          返回首页
        </Link>
      </div>
    </div>
  );
}
