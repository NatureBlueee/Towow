// components/article/ArticleHero.tsx
import styles from './ArticleHero.module.css';

interface ArticleHeroProps {
  title: string;
  readingTime: number;
  date: string;
  decorImageRight?: string;
  decorImageLeft?: string;
  className?: string;
}

export function ArticleHero({
  title,
  readingTime,
  date,
  decorImageRight,
  decorImageLeft,
  className,
}: ArticleHeroProps) {
  return (
    <section className={`${styles.hero} ${className || ''}`}>
      {/* Background geometric shapes */}
      <div className={`${styles.shape} ${styles.shapeCircleLg}`} />
      <div className={`${styles.shape} ${styles.shapeSquareLime}`} />

      {/* Decorative images */}
      {decorImageRight && (
        <div
          className={styles.decorRight}
          style={{ backgroundImage: `url(${decorImageRight})` }}
        />
      )}
      {decorImageLeft && (
        <div
          className={styles.decorLeft}
          style={{ backgroundImage: `url(${decorImageLeft})` }}
        />
      )}

      {/* Title */}
      {/* SECURITY: Title content is from trusted static data files, not user input */}
      <h1
        className={styles.title}
        dangerouslySetInnerHTML={{ __html: title }}
      />

      {/* Meta info */}
      <div className={styles.meta}>
        <svg
          className={styles.metaIcon}
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 100-16 8 8 0 000 16zm1-8h4v2h-6V7h2v5z" />
        </svg>
        <span>
          阅读时长 {readingTime}分钟 · {date}
        </span>
      </div>
    </section>
  );
}
