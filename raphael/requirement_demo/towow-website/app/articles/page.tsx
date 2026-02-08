// app/articles/page.tsx
import Link from 'next/link';
import { getLocale, getTranslations } from 'next-intl/server';
import { getArticles } from '@/lib/articles';
import styles from './page.module.css';

// Extract excerpt from article content
function getExcerpt(article: ReturnType<typeof getArticles>[0]): string {
  if (article.sections.length === 0) return '';

  const firstContent = article.sections[0].content;
  const textContent = firstContent
    .replace(/<[^>]*>/g, '')
    .replace(/\s+/g, ' ')
    .trim();

  if (textContent.length > 100) {
    return textContent.slice(0, 100) + '...';
  }
  return textContent;
}

// Clean HTML tags from title
function cleanTitle(title: string): string {
  return title.replace(/<br\s*\/?>/gi, ' ').replace(/<[^>]*>/g, '');
}

export default async function ArticlesPage() {
  const locale = await getLocale();
  const t = await getTranslations('Articles');
  const tCommon = await getTranslations('Common');
  const articles = getArticles(locale);

  return (
    <main className={styles.page}>
      {/* Decorative Shapes */}
      <div className={styles.shapes}>
        <div className={styles.shape1} />
        <div className={styles.shape2} />
        <div className={styles.shape3} />
      </div>

      <div className={styles.container}>
        {/* Back Link */}
        <Link href="/" className={styles.backLink}>
          <i className="ri-arrow-left-line" />
          {tCommon('backToHome')}
        </Link>

        {/* Hero */}
        <header className={styles.hero}>
          <h1 className={styles.heroTitle}>{t('pageTitle')}</h1>
          <p className={styles.heroSubtitle}>
            {t('pageSubtitle')}
          </p>
        </header>

        {/* Articles Grid */}
        <div className={styles.articlesGrid}>
          {articles.map((article) => (
            <Link
              key={article.slug}
              href={`/articles/${article.slug}`}
              className={styles.articleCard}
            >
              <div className={styles.cardMeta}>
                <span>
                  <i className="ri-time-line" />
                  {t('readTime', { minutes: article.readingTime })}
                </span>
                <span className={styles.dot} />
                <span>{article.date}</span>
              </div>

              <h2 className={styles.cardTitle}>{cleanTitle(article.title)}</h2>

              <p className={styles.cardExcerpt}>{getExcerpt(article)}</p>

              <span className={styles.readMore}>
                {tCommon('readMore')}
                <i className="ri-arrow-right-line" />
              </span>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
