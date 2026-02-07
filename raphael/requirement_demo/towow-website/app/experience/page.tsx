// app/experience/page.tsx
import { AppGrid } from '@/components/experience-hub/AppGrid';
import { getActiveApps, getComingSoonApps } from '@/lib/apps/registry';
import styles from './experience.module.css';

export const metadata = {
  title: '应用目录 - ToWow 通爻',
  description: '探索通爻生态中的各种应用，体验响应范式的全新协作方式',
};

export default function ExperiencePage() {
  const activeApps = getActiveApps();
  const comingSoonApps = getComingSoonApps();

  return (
    <div className={styles.container}>
      {/* Hero Section */}
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>
          探索<span className={styles.heroEn}>通爻</span>应用
        </h1>
        <p className={styles.heroSubtitle}>
          每个应用都是响应范式的一次实验，发现意外的可能性
        </p>
      </section>

      {/* Active Apps */}
      <section className={styles.section}>
        <AppGrid
          apps={activeApps}
          title="活跃应用"
          emptyMessage="暂无活跃应用"
          columns={3}
          showComingSoonSeparately={false}
        />
      </section>

      {/* Coming Soon Apps */}
      {comingSoonApps.length > 0 && (
        <section className={styles.section}>
          <AppGrid
            apps={comingSoonApps}
            title=""
            emptyMessage=""
            columns={3}
            showComingSoonSeparately={true}
          />
        </section>
      )}

      {/* Call to Action */}
      <section className={styles.cta}>
        <div className={styles.ctaCard}>
          <h2 className={styles.ctaTitle}>有想法？</h2>
          <p className={styles.ctaText}>
            通爻是开放的协议，欢迎你构建自己的应用
          </p>
          <a
            href="/articles/join-us"
            className={styles.ctaButton}
          >
            加入共创
          </a>
        </div>
      </section>
    </div>
  );
}
