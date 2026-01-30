// components/ui/ContentCard.tsx
import styles from './ContentCard.module.css';

interface ContentCardProps {
  children: React.ReactNode;
  className?: string;
}

export function ContentCard({ children, className }: ContentCardProps) {
  return (
    <div className={`${styles.card} ${className || ''}`}>
      {children}
    </div>
  );
}
