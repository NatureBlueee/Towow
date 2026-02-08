// components/article/RelatedArticles.tsx
import Link from 'next/link';
import { getTranslations } from 'next-intl/server';
import styles from './RelatedArticles.module.css';

export interface RelatedArticle {
  href: string;
  title: string;
  icon: 'handshake' | 'globe' | 'user' | 'lightbulb' | 'book';
}

interface RelatedArticlesProps {
  articles: RelatedArticle[];
  className?: string;
}

const iconPaths: Record<RelatedArticle['icon'], string> = {
  handshake:
    'M11.5 9.5V4a1.5 1.5 0 013 0v5.5a1.5 1.5 0 01-3 0zm-4 0V7a1.5 1.5 0 013 0v2.5a1.5 1.5 0 01-3 0zm-4 0V8a1.5 1.5 0 013 0v1.5a1.5 1.5 0 01-3 0zm12 0V6a1.5 1.5 0 013 0v3.5a1.5 1.5 0 01-3 0z',
  globe:
    'M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm-2.29-2.333A17.9 17.9 0 018.027 13H4.062a8.008 8.008 0 005.648 6.667zM10.03 13c.151 2.439.848 4.73 1.97 6.752A15.905 15.905 0 0013.97 13h-3.94zm9.908 0h-3.965a17.9 17.9 0 01-1.683 6.667A8.008 8.008 0 0019.938 13zM4.062 11h3.965A17.9 17.9 0 019.71 4.333 8.008 8.008 0 004.062 11zm5.969 0h3.938A15.905 15.905 0 0012 4.248 15.905 15.905 0 0010.03 11zm4.259-6.667A17.9 17.9 0 0115.973 11h3.965a8.008 8.008 0 00-5.648-6.667z',
  user: 'M12 14.5a5.25 5.25 0 100-10.5 5.25 5.25 0 000 10.5zm0-2.25a3 3 0 110-6 3 3 0 010 6zm7.5 8.25c0 .75-.75 1.5-1.5 1.5H6c-.75 0-1.5-.75-1.5-1.5 0-3.75 3-6.75 7.5-6.75s7.5 3 7.5 6.75z',
  lightbulb:
    'M12 18a6 6 0 110-12 6 6 0 010 12zm0-2a4 4 0 100-8 4 4 0 000 8zm-1 4h2v2h-2v-2zm0-16h2v2h-2V4zM4 11H2v2h2v-2zm18 0h-2v2h2v-2zM5.636 5.636l1.414 1.414-1.414 1.414-1.414-1.414 1.414-1.414zm12.728 0l1.414 1.414-1.414 1.414-1.414-1.414 1.414-1.414zM5.636 18.364l1.414-1.414 1.414 1.414-1.414 1.414-1.414-1.414zm12.728 0l1.414-1.414 1.414 1.414-1.414 1.414-1.414-1.414z',
  book: 'M21 4H7a2 2 0 00-2 2v12a2 2 0 002 2h14V4zM5 6a2 2 0 012-2h1v16H7a2 2 0 01-2-2V6zm4 0h10v12H9V6zm2 2v2h6V8h-6zm0 4v2h6v-2h-6z',
};

export async function RelatedArticles({ articles, className }: RelatedArticlesProps) {
  const t = await getTranslations('Articles');

  return (
    <section className={`${styles.section} ${className || ''}`}>
      <div className={styles.container}>
        <h4 className={styles.title}>{t('relatedArticles')}</h4>
        <div className={styles.list}>
          {articles.map((article, index) => (
            <Link key={index} href={article.href} className={styles.card}>
              <div className={styles.icon}>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d={iconPaths[article.icon]} />
                </svg>
              </div>
              <div className={styles.text}>{article.title}</div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
