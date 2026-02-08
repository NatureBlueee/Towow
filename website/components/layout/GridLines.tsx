import styles from './GridLines.module.css';

interface GridLinesProps {
  columns?: number;
}

export function GridLines({ columns = 12 }: GridLinesProps) {
  return (
    <div className={styles.gridLines}>
      {Array.from({ length: columns }).map((_, i) => (
        <div key={i} className={styles.line} />
      ))}
    </div>
  );
}
