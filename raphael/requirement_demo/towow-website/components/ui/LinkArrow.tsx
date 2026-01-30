// components/ui/LinkArrow.tsx
import Link from 'next/link';
import styles from './LinkArrow.module.css';

interface LinkArrowProps {
  href: string;
  children: React.ReactNode;
  className?: string;
}

export function LinkArrow({ href, children, className }: LinkArrowProps) {
  return (
    <Link href={href} className={`${styles.linkArrow} ${className || ''}`}>
      <span className={styles.text}>{children}</span>
      <span className={styles.arrow}>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="5" y1="12" x2="19" y2="12" />
          <polyline points="12 5 19 12 12 19" />
        </svg>
      </span>
    </Link>
  );
}
