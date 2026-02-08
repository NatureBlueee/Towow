// components/ui/NodeItem.tsx
import styles from './NodeItem.module.css';

interface NodeItemProps {
  icon: React.ReactNode;
  label: string;
  shape?: 'circle' | 'square';
  backgroundColor?: string;
  textColor?: string;
  className?: string;
  style?: React.CSSProperties;
}

export function NodeItem({
  icon,
  label,
  shape = 'circle',
  backgroundColor = '#fff',
  textColor = '#333',
  className,
  style,
}: NodeItemProps) {
  const nodeShapeClass = shape === 'circle' ? styles.nodeCircle : styles.nodeSquare;

  return (
    <div className={`${styles.nodeItem} ${className || ''}`} style={style}>
      <div
        className={`${styles.nodeShape} ${nodeShapeClass}`}
        style={{ backgroundColor, color: textColor }}
      >
        {icon}
      </div>
      <div className={styles.nodeText}>{label}</div>
    </div>
  );
}
