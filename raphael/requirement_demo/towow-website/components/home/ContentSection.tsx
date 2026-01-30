// components/home/ContentSection.tsx
import { ContentCard } from '@/components/ui/ContentCard';
import { LinkArrow } from '@/components/ui/LinkArrow';
import styles from './ContentSection.module.css';

interface ContentSectionProps {
  gridColumn: string;
  title: string;
  content: string;
  linkText: string;
  linkHref: string;
  textAlign?: 'left' | 'center' | 'right';
  children?: React.ReactNode;
}

export function ContentSection({
  gridColumn,
  title,
  content,
  linkText,
  linkHref,
  textAlign = 'left',
  children,
}: ContentSectionProps) {
  return (
    <section className={styles.section}>
      {/* Geometric Decorations */}
      {children && (
        <div className={styles.secVisual}>
          {children}
        </div>
      )}

      {/* Grid Content */}
      <div className={styles.gridWrapper}>
        <div
          className={styles.contentWrapper}
          style={{ gridColumn, textAlign }}
        >
          <ContentCard>
            {/* SECURITY: Content is from trusted static data files, not user input */}
            <h2
              className={styles.title}
              dangerouslySetInnerHTML={{ __html: title }}
            />
            <p
              className={styles.content}
              dangerouslySetInnerHTML={{ __html: content }}
            />
            <LinkArrow href={linkHref}>{linkText}</LinkArrow>
          </ContentCard>
        </div>
      </div>
    </section>
  );
}
