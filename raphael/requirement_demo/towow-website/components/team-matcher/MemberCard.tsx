'use client';

import styles from './MemberCard.module.css';
import type { TeamMember } from '@/lib/team-matcher/types';

interface MemberCardProps {
  member: TeamMember;
  index: number;
}

/**
 * Card showing a team member's info within a proposal.
 */
export function MemberCard({ member, index }: MemberCardProps) {
  // Generate a consistent avatar color based on name
  const colors = ['#6366F1', '#8B5CF6', '#06B6D4', '#F59E0B', '#10B981', '#F43F5E'];
  const colorIndex = member.agent_name
    .split('')
    .reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const avatarColor = colors[colorIndex % colors.length];

  return (
    <div
      className={styles.card}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className={styles.header}>
        <div
          className={styles.avatar}
          style={{ background: `linear-gradient(135deg, ${avatarColor}, ${avatarColor}80)` }}
        >
          {member.agent_name.charAt(0)}
        </div>
        <div className={styles.info}>
          <h4 className={styles.name}>{member.agent_name}</h4>
          <span className={styles.role}>{member.role}</span>
        </div>
      </div>

      <p className={styles.intro}>{member.brief_intro}</p>

      <div className={styles.skills}>
        {member.skills.slice(0, 4).map((skill) => (
          <span key={skill} className={styles.skillTag}>
            {skill}
          </span>
        ))}
        {member.skills.length > 4 && (
          <span className={styles.skillMore}>+{member.skills.length - 4}</span>
        )}
      </div>

      <div className={styles.matchReason}>
        <i className="ri-links-line" />
        <span>{member.match_reason}</span>
      </div>
    </div>
  );
}
