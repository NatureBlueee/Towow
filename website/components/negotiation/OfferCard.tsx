'use client';

import type { OfferReceivedData } from '@/types/negotiation';
import styles from './OfferCard.module.css';

interface OfferCardProps {
  offer: OfferReceivedData;
  index: number;
}

const AVATAR_COLORS = ['#6366F1', '#8B5CF6', '#06B6D4', '#F59E0B', '#10B981', '#F43F5E'];

export function OfferCard({ offer, index }: OfferCardProps) {
  const colorIdx = offer.display_name
    .split('')
    .reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const avatarColor = AVATAR_COLORS[colorIdx % AVATAR_COLORS.length];

  return (
    <div
      className={styles.card}
      style={{ animationDelay: `${index * 120}ms` }}
    >
      <div className={styles.header}>
        <div
          className={styles.avatar}
          style={{ background: `linear-gradient(135deg, ${avatarColor}, ${avatarColor}80)` }}
        >
          {offer.display_name.charAt(0)}
        </div>
        <h4 className={styles.name}>{offer.display_name}</h4>
      </div>

      <p className={styles.content}>{offer.content}</p>

      {offer.capabilities.length > 0 && (
        <div className={styles.capabilities}>
          {offer.capabilities.map((cap) => (
            <span key={cap} className={styles.capTag}>{cap}</span>
          ))}
        </div>
      )}
    </div>
  );
}
