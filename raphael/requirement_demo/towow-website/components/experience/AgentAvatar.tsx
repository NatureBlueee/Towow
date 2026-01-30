import styles from './AgentAvatar.module.css';

interface AgentAvatarProps {
  agentId: string;
  name: string;
  avatarUrl?: string;
  size?: 'sm' | 'md' | 'lg';
  showName?: boolean;
}

const sizeMap = {
  sm: 24,
  md: 32,
  lg: 48,
};

export function AgentAvatar({
  agentId,
  name,
  avatarUrl,
  size = 'md',
  showName = false,
}: AgentAvatarProps) {
  const initial = name.charAt(0).toUpperCase();
  const dimension = sizeMap[size];

  return (
    <div className={styles.container}>
      <div
        className={`${styles.avatar} ${styles[size]}`}
        style={{ width: dimension, height: dimension }}
      >
        {avatarUrl ? (
          <img src={avatarUrl} alt={name} className={styles.image} />
        ) : (
          <span className={styles.initial}>{initial}</span>
        )}
      </div>
      {showName && <span className={styles.name}>{name}</span>}
    </div>
  );
}
