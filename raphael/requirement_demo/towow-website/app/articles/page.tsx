// app/articles/page.tsx
import Link from 'next/link';
import { articles } from '@/lib/articles';
import styles from './page.module.css';

// 从文章内容中提取摘要
function getExcerpt(article: (typeof articles)[0]): string {
  if (article.sections.length === 0) return '';

  // 从第一个 section 的 content 中提取纯文本
  const firstContent = article.sections[0].content;
  // 移除 HTML 标签
  const textContent = firstContent
    .replace(/<[^>]*>/g, '')
    .replace(/\s+/g, ' ')
    .trim();

  // 截取前 100 个字符
  if (textContent.length > 100) {
    return textContent.slice(0, 100) + '...';
  }
  return textContent;
}

// 清理标题中的 HTML 标签
function cleanTitle(title: string): string {
  return title.replace(/<br\s*\/?>/gi, ' ').replace(/<[^>]*>/g, '');
}

export default function ArticlesPage() {
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
          返回首页
        </Link>

        {/* Hero */}
        <header className={styles.hero}>
          <h1 className={styles.heroTitle}>我们的思考</h1>
          <p className={styles.heroSubtitle}>
            关于 Agent 网络、价值经济和开放协作的深度思考
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
                  {article.readingTime} 分钟阅读
                </span>
                <span className={styles.dot} />
                <span>{article.date}</span>
              </div>

              <h2 className={styles.cardTitle}>{cleanTitle(article.title)}</h2>

              <p className={styles.cardExcerpt}>{getExcerpt(article)}</p>

              <span className={styles.readMore}>
                阅读全文
                <i className="ri-arrow-right-line" />
              </span>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
