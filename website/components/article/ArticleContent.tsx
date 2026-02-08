// components/article/ArticleContent.tsx
import styles from './ArticleContent.module.css';

interface ArticleSection {
  id: string;
  title: string;
  content: string;
  isFirst?: boolean;
}

interface ArticleContentProps {
  sections: ArticleSection[];
  className?: string;
}

export function ArticleContent({ sections, className }: ArticleContentProps) {
  return (
    <article className={`${styles.article} ${className || ''}`}>
      {sections.map((section, index) => (
        <div key={section.id}>
          <section id={section.id} className={styles.section}>
            <h2 className={styles.heading}>{section.title}</h2>
            <div
              className={`${styles.content} ${
                section.isFirst || index === 0 ? styles.firstSection : ''
              }`}
              // SECURITY: Content is from trusted static data files, not user input
              dangerouslySetInnerHTML={{ __html: section.content }}
            />
          </section>
          {index < sections.length - 1 && (
            <div className={styles.divider}>
              <div className={`${styles.dividerShape} ${styles.circle}`} />
              <div className={`${styles.dividerShape} ${styles.square}`} />
              <div className={`${styles.dividerShape} ${styles.triangle}`} />
            </div>
          )}
        </div>
      ))}
    </article>
  );
}
