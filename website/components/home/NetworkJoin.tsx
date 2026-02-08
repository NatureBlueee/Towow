// components/home/NetworkJoin.tsx
import { NodeItem } from '@/components/ui/NodeItem';
import styles from './NetworkJoin.module.css';

interface NetworkNode {
  icon: React.ReactNode;
  label: string;
  position: {
    top?: string;
    left?: string;
    right?: string;
  };
  backgroundColor: string;
  textColor?: string;
  shape?: 'circle' | 'square';
  animationDuration: string;
  animationDelay: string;
}

interface NetworkJoinProps {
  title: string;
  description: string;
  nodes: NetworkNode[];
  id?: string;
}

export function NetworkJoin({ title, description, nodes, id }: NetworkJoinProps) {
  return (
    <section className={styles.section} id={id}>
      <div className={styles.gridWrapper}>
        {/* SVG Connection Lines */}
        <svg className={styles.connectionLines}>
          <line x1="50%" y1="85%" x2="20%" y2="30%" />
          <line x1="50%" y1="85%" x2="35%" y2="20%" />
          <line x1="50%" y1="85%" x2="50%" y2="15%" />
          <line x1="50%" y1="85%" x2="65%" y2="25%" />
          <line x1="50%" y1="85%" x2="80%" y2="35%" />
        </svg>

        {/* Center ToWow Node */}
        <div className={styles.centerNode}>
          <div className={styles.towowBox}>ToWow</div>
          <h2 className={styles.title}>{title}</h2>
          <p className={styles.description}>{description}</p>
        </div>

        {/* Floating Nodes */}
        <div className={styles.nodesContainer}>
          {nodes.map((node, index) => (
            <NodeItem
              key={index}
              icon={node.icon}
              label={node.label}
              shape={node.shape || 'circle'}
              backgroundColor={node.backgroundColor}
              textColor={node.textColor || '#333'}
              className={styles.floatingNode}
              style={{
                ...node.position,
                animationDuration: node.animationDuration,
                animationDelay: node.animationDelay,
              }}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
