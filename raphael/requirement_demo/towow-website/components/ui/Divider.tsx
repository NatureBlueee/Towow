// components/ui/Divider.tsx
import styles from './Divider.module.css';

interface DividerProps {
  className?: string;
}

export function Divider({ className }: DividerProps) {
  return (
    <div className={`${styles.divider} ${className || ''}`}>
      <div className={`${styles.shape} ${styles.circle}`} />
      <div className={`${styles.shape} ${styles.square}`} />
      <div className={`${styles.shape} ${styles.triangle}`} />
    </div>
  );
}
