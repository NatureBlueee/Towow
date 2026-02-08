// components/home/Hero.tsx
import { Button } from '@/components/ui/Button';
import styles from './Hero.module.css';

interface HeroProps {
  title: React.ReactNode;
  subtitle: string;
  primaryButtonText: string;
  primaryButtonHref: string;
  outlineButtonText: string;
  outlineButtonHref: string;
}

export function Hero({
  title,
  subtitle,
  primaryButtonText,
  primaryButtonHref,
  outlineButtonText,
  outlineButtonHref,
}: HeroProps) {
  return (
    <section className={styles.hero}>
      {/* Background Animation */}
      <div className={styles.heroBgAnim}>
        <div className={styles.heroCircle} />
        <div className={styles.heroSquare} />
      </div>

      {/* Content */}
      <div className={styles.heroContent}>
        <h1 className={styles.heroTitle}>{title}</h1>
        <p className={styles.heroSubtitle}>{subtitle}</p>
        <div className={styles.heroButtons}>
          <Button variant="outline" href={outlineButtonHref}>
            {outlineButtonText}
          </Button>
          <Button variant="primary" href={primaryButtonHref}>
            {primaryButtonText}
          </Button>
        </div>
      </div>
    </section>
  );
}
