'use client';

import { useState } from 'react';
import styles from './TeamProposalCard.module.css';
import { MemberCard } from './MemberCard';
import { CoverageBar } from './CoverageBar';
import type { TeamProposal } from '@/lib/team-matcher/types';
import { PROPOSAL_TYPE_CONFIG } from '@/lib/team-matcher/types';

interface TeamProposalCardProps {
  proposal: TeamProposal;
  index: number;
  onSelect: (proposalId: string) => void;
}

/**
 * A proposal card showing team composition, scores, and unexpected combinations.
 */
export function TeamProposalCard({ proposal, index, onSelect }: TeamProposalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const config = PROPOSAL_TYPE_CONFIG[proposal.proposal_type];

  return (
    <div
      className={styles.card}
      style={{ animationDelay: `${index * 150}ms` }}
    >
      {/* Type badge */}
      <div className={styles.typeBadge} style={{ color: config.color }}>
        <i className={config.icon} />
        <span>{config.label}</span>
      </div>

      {/* Header */}
      <div className={styles.header}>
        <h3 className={styles.title}>{proposal.proposal_label}</h3>
        <p className={styles.description}>{proposal.proposal_description}</p>
      </div>

      {/* Team members preview */}
      <div className={styles.membersPreview}>
        <div className={styles.avatarStack}>
          {proposal.team_members.map((member, i) => {
            const colors = ['#6366F1', '#8B5CF6', '#06B6D4', '#F59E0B', '#10B981', '#F43F5E'];
            const colorIndex = member.agent_name
              .split('')
              .reduce((sum, char) => sum + char.charCodeAt(0), 0);
            return (
              <div
                key={member.agent_id}
                className={styles.avatarStackItem}
                style={{
                  background: `linear-gradient(135deg, ${colors[colorIndex % colors.length]}, ${colors[colorIndex % colors.length]}80)`,
                  zIndex: proposal.team_members.length - i,
                }}
                title={member.agent_name}
              >
                {member.agent_name.charAt(0)}
              </div>
            );
          })}
        </div>
        <span className={styles.memberCount}>
          {proposal.team_members.length} 人团队
        </span>
      </div>

      {/* Coverage */}
      <CoverageBar
        coverage={proposal.role_coverage}
        coverageScore={proposal.coverage_score}
        synergyScore={proposal.synergy_score}
      />

      {/* Unexpected combinations */}
      {proposal.unexpected_combinations.length > 0 && (
        <div className={styles.unexpectedSection}>
          <div className={styles.unexpectedHeader}>
            <i className="ri-sparkling-2-line" />
            <span>意外组合</span>
          </div>
          {proposal.unexpected_combinations.map((combo, i) => (
            <p key={i} className={styles.unexpectedText}>
              {combo}
            </p>
          ))}
        </div>
      )}

      {/* Expandable detail */}
      {expanded && (
        <div className={styles.membersDetail}>
          <h4 className={styles.membersTitle}>团队成员</h4>
          <div className={styles.membersGrid}>
            {proposal.team_members.map((member, i) => (
              <MemberCard key={member.agent_id} member={member} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className={styles.actions}>
        <button
          className={styles.expandBtn}
          onClick={() => setExpanded(!expanded)}
        >
          <i className={expanded ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'} />
          {expanded ? '收起' : '了解更多'}
        </button>
        <button
          className={styles.selectBtn}
          onClick={() => onSelect(proposal.proposal_id)}
        >
          <i className="ri-check-line" />
          选择这个团队
        </button>
      </div>
    </div>
  );
}
