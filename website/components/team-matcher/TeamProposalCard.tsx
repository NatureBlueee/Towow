'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import styles from './TeamProposalCard.module.css';
import { MemberCard } from './MemberCard';
import { CoverageBar } from './CoverageBar';
import type { TeamProposal } from '@/lib/team-matcher/types';

interface TeamProposalCardProps {
  proposal: TeamProposal;
  index: number;
  onSelect: (proposalId: string) => void;
}

const PROPOSAL_TYPE_ICONS: Record<TeamProposal['proposal_type'], { icon: string; color: string }> = {
  fast_validation: { icon: 'ri-rocket-2-line', color: '#10B981' },
  tech_depth: { icon: 'ri-code-box-line', color: '#6366F1' },
  cross_innovation: { icon: 'ri-lightbulb-flash-line', color: '#F59E0B' },
};

const PROPOSAL_TYPE_KEYS: Record<TeamProposal['proposal_type'], string> = {
  fast_validation: 'fastValidation',
  tech_depth: 'techDepth',
  cross_innovation: 'crossInnovation',
};

/**
 * A proposal card showing team composition, scores, and unexpected combinations.
 */
export function TeamProposalCard({ proposal, index, onSelect }: TeamProposalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const t = useTranslations('TeamMatcher.proposal');
  const typeKey = PROPOSAL_TYPE_KEYS[proposal.proposal_type];
  const { icon, color } = PROPOSAL_TYPE_ICONS[proposal.proposal_type];

  return (
    <div
      className={styles.card}
      style={{ animationDelay: `${index * 150}ms` }}
    >
      {/* Type badge */}
      <div className={styles.typeBadge} style={{ color }}>
        <i className={icon} />
        <span>{t(typeKey)}</span>
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
          {t('memberCount', { count: proposal.team_members.length })}
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
            <span>{t('unexpectedCombinations')}</span>
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
          <h4 className={styles.membersTitle}>{t('teamMembers')}</h4>
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
          {expanded ? t('collapse') : t('learnMore')}
        </button>
        <button
          className={styles.selectBtn}
          onClick={() => onSelect(proposal.proposal_id)}
        >
          <i className="ri-check-line" />
          {t('selectTeam')}
        </button>
      </div>
    </div>
  );
}
