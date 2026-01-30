import { notFound } from 'next/navigation';
import { ArticlePageClient } from '@/components/article/ArticlePageClient';
import { ArticleHero } from '@/components/article/ArticleHero';
import { TableOfContents, TocItem } from '@/components/article/TableOfContents';
import { ArticleContent } from '@/components/article/ArticleContent';
import { CTABox } from '@/components/article/CTABox';
import { RelatedArticles, RelatedArticle } from '@/components/article/RelatedArticles';
import { Footer } from '@/components/layout/Footer';
import { getArticleBySlug, getAllArticleSlugs } from '@/lib/articles';
import styles from './page.module.css';

interface ArticlePageProps {
  params: Promise<{
    slug: string;
  }>;
}

// Generate static params for all articles
export async function generateStaticParams() {
  const slugs = getAllArticleSlugs();
  return slugs.map((slug) => ({
    slug,
  }));
}

// Generate metadata for each article
export async function generateMetadata({ params }: ArticlePageProps) {
  const { slug } = await params;
  const article = getArticleBySlug(slug);

  if (!article) {
    return {
      title: 'Article Not Found - ToWow',
    };
  }

  // Strip HTML tags from title for metadata
  const plainTitle = article.title.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

  return {
    title: `${plainTitle} - ToWow`,
    description: `阅读时长 ${article.readingTime}分钟`,
  };
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { slug } = await params;
  const article = getArticleBySlug(slug);

  if (!article) {
    notFound();
  }

  // Prepare TOC items from sections
  const tocItems: TocItem[] = article.sections.map((section) => ({
    id: section.id,
    title: section.title,
  }));

  // Prepare related articles data
  const relatedArticlesData: RelatedArticle[] = article.relatedArticles.map((related) => ({
    href: `/articles/${related.slug}`,
    title: related.title,
    icon: related.icon,
  }));

  return (
    <ArticlePageClient>
      <div className={styles.pageWrapper}>
        {/* Hero Section */}
        <ArticleHero
          title={article.title}
          readingTime={article.readingTime}
          date={article.date}
          decorImageRight={article.heroImages?.right}
          decorImageLeft={article.heroImages?.left}
        />

        {/* Three-column layout */}
        <div className={styles.container}>
          {/* Left Sidebar - Table of Contents */}
          <aside className={styles.sidebar}>
            <div className={styles.tocWrapper}>
              <TableOfContents items={tocItems} />
            </div>
          </aside>

          {/* Main Content */}
          <main className={styles.mainContent}>
            <ArticleContent sections={article.sections} />

            {/* CTA Box */}
            <div className={styles.ctaWrapper}>
              <CTABox
                title="准备好加入价值网络了吗？"
                description="ToWow正在构建Agent时代的开放协作网络，让价值自由流动。"
                buttonText="加入我们"
                buttonHref="/"
              />
            </div>
          </main>

          {/* Right Decorations */}
          <aside className={styles.rightDecor}>
            <div className={`${styles.parallaxShape} ${styles.pShape1}`} />
            <div className={`${styles.parallaxShape} ${styles.pShape2}`} />
            <div className={`${styles.parallaxShape} ${styles.pShape3}`} />
            <div className={`${styles.parallaxShape} ${styles.pShape4}`} />
          </aside>
        </div>

        {/* Related Articles */}
        <RelatedArticles articles={relatedArticlesData} />

        {/* Footer */}
        <Footer variant="article" />
      </div>
    </ArticlePageClient>
  );
}