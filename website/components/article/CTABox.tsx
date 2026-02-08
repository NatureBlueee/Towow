// components/article/CTABox.tsx
import { Button } from '@/components/ui/Button';
import styles from './CTABox.module.css';

interface CTABoxProps {
  title: string;
  description: string;
  buttonText: string;
  buttonHref: string;
  className?: string;
}

export function CTABox({
  title,
  description,
  buttonText,
  buttonHref,
  className,
}: CTABoxProps) {
  return (
    <div className={`${styles.box} ${className || ''}`}>
      {/* Decorative shape */}
      <div className={styles.decor} />

      <h3 className={styles.title}>{title}</h3>
      <p className={styles.description}>{description}</p>
      <Button variant="primary" href={buttonHref}>
        <span>{buttonText}</span>
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M16.172 11l-5.364-5.364 1.414-1.414L20 12l-7.778 7.778-1.414-1.414L16.172 13H4v-2h12.172z" />
        </svg>
      </Button>
    </div>
  );
}
