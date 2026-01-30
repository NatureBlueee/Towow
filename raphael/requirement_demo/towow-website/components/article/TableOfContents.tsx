'use client';

// components/article/TableOfContents.tsx
import { useEffect, useState } from 'react';
import styles from './TableOfContents.module.css';

export interface TocItem {
  id: string;
  title: string;
}

interface TableOfContentsProps {
  items: TocItem[];
  className?: string;
}

export function TableOfContents({ items, className }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>(items[0]?.id || '');

  useEffect(() => {
    // Store element references for cleanup to avoid potential memory leaks
    const observedElements: Element[] = [];

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      {
        rootMargin: '-20% 0px -60% 0px',
        threshold: 0,
      }
    );

    // Observe all section elements
    items.forEach((item) => {
      const element = document.getElementById(item.id);
      if (element) {
        observer.observe(element);
        observedElements.push(element);
      }
    });

    return () => {
      // Use stored references for cleanup instead of querying DOM again
      observedElements.forEach((element) => {
        observer.unobserve(element);
      });
    };
  }, [items]);

  const handleClick = (
    e: React.MouseEvent<HTMLAnchorElement>,
    id: string
  ) => {
    e.preventDefault();
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveId(id);
    }
  };

  return (
    <nav className={`${styles.toc} ${className || ''}`}>
      <div className={styles.title}>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M11 4h10v2H11V4zm0 4h6v2h-6V8zm0 6h10v2H11v-2zm0 4h6v2h-6v-2zM3 4h6v6H3V4zm2 2v2h2V6H5zm-2 8h6v6H3v-6zm2 2v2h2v-2H5z" />
        </svg>
        <span>目录</span>
      </div>
      <ul className={styles.list}>
        <div className={styles.line} />
        {items.map((item) => (
          <li
            key={item.id}
            className={`${styles.item} ${
              activeId === item.id ? styles.active : ''
            }`}
          >
            <a
              href={`#${item.id}`}
              className={styles.link}
              onClick={(e) => handleClick(e, item.id)}
            >
              <div className={styles.marker} />
              <span>{item.title}</span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
