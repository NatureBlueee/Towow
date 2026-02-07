'use client';

import { useState, useEffect, useCallback } from 'react';
import '@/styles/team-matcher.css';
import { TeamBackground } from '@/components/team-matcher/TeamBackground';
import { TeamNav } from '@/components/team-matcher/TeamNav';
import { TeamProposalCard } from '@/components/team-matcher/TeamProposalCard';
import { getTeamProposals } from '@/lib/team-matcher/api';
import type { TeamProposal } from '@/lib/team-matcher/types';
import styles from './ProposalsPage.module.css';

interface ProposalsPageClientProps {
  requestId: string;
}

export function ProposalsPageClient({ requestId }: ProposalsPageClientProps) {
  const [proposals, setProposals] = useState<TeamProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getTeamProposals(requestId);
        setProposals(data.proposals);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [requestId]);

  const handleSelect = useCallback((proposalId: string) => {
    setSelectedId(proposalId);
  }, []);

  return (
    <div className="team-matcher-root">
      <TeamBackground />
      <TeamNav currentStep="proposals" />
      <main className={styles.main}>
        {/* Page header */}
        <div className={styles.pageHeader}>
          <h1 className={styles.pageTitle}>团队方案</h1>
          <p className={styles.pageSubtitle}>
            基于收到的响应，为你生成了 {proposals.length} 种不同风格的团队组合
          </p>
        </div>

        {/* Loading skeleton */}
        {loading && (
          <div className={styles.skeletonGrid}>
            {[0, 1, 2].map((i) => (
              <div key={i} className={styles.skeleton}>
                <div className={styles.skeletonBadge} />
                <div className={styles.skeletonTitle} />
                <div className={styles.skeletonDesc} />
                <div className={styles.skeletonBar} />
                <div className={styles.skeletonBar} />
              </div>
            ))}
          </div>
        )}

        {/* Proposals grid */}
        {!loading && proposals.length > 0 && (
          <div className={styles.proposalsGrid}>
            {proposals.map((proposal, index) => (
              <TeamProposalCard
                key={proposal.proposal_id}
                proposal={proposal}
                index={index}
                onSelect={handleSelect}
              />
            ))}
          </div>
        )}

        {/* Selection confirmation */}
        {selectedId && (
          <div className={styles.selectionOverlay}>
            <div className={styles.selectionModal}>
              <div className={styles.selectionIcon}>
                <i className="ri-team-line" />
              </div>
              <h2 className={styles.selectionTitle}>团队已选择</h2>
              <p className={styles.selectionDesc}>
                你选择了
                <strong>
                  {proposals.find((p) => p.proposal_id === selectedId)?.proposal_label}
                </strong>
                方案。接下来可以开始协作了。
              </p>
              <div className={styles.selectionActions}>
                <button
                  className={styles.selectionBtnSecondary}
                  onClick={() => setSelectedId(null)}
                >
                  重新选择
                </button>
                <button className={styles.selectionBtnPrimary}>
                  <i className="ri-rocket-2-line" />
                  开始协作
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
