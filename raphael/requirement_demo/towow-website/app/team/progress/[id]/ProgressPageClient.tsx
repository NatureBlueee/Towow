'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import '@/styles/team-matcher.css';
import { TeamBackground } from '@/components/team-matcher/TeamBackground';
import { TeamNav } from '@/components/team-matcher/TeamNav';
import { SignalVisualization } from '@/components/team-matcher/SignalVisualization';
import { getMockOffers } from '@/lib/team-matcher/api';
import type { ProgressStage, OfferSummary } from '@/lib/team-matcher/types';
import styles from './ProgressPage.module.css';

interface ProgressPageClientProps {
  requestId: string;
}

/**
 * Real-time progress page that simulates (or connects to) the matching process.
 * In demo/mock mode, it auto-advances through stages with mock offer data.
 * In production, it connects to WebSocket for real-time updates.
 */
export function ProgressPageClient({ requestId }: ProgressPageClientProps) {
  const router = useRouter();
  const [stage, setStage] = useState<ProgressStage>('broadcasting');
  const [offerSummaries, setOfferSummaries] = useState<OfferSummary[]>([]);
  const isMock = requestId.startsWith('mock-');
  const offerIndexRef = useRef(0);

  // Memoize mock data so it stays stable across renders
  const mockOfferSummaries = useMemo<OfferSummary[]>(
    () =>
      getMockOffers().map((offer) => ({
        agent_name: offer.agent_name,
        skills: offer.skills,
        brief: offer.offer_content,
        timestamp: offer.timestamp,
      })),
    []
  );

  // Mock: Auto-advance through stages for demo
  useEffect(() => {
    if (!isMock) return;

    // Stage 1: Broadcasting (3 seconds)
    const broadcastTimer = setTimeout(() => {
      setStage('receiving');
    }, 3000);

    return () => clearTimeout(broadcastTimer);
  }, [isMock]);

  // Mock: Drip-feed offers during receiving stage
  useEffect(() => {
    if (!isMock || stage !== 'receiving') return;

    offerIndexRef.current = 0;
    setOfferSummaries([]);

    const interval = setInterval(() => {
      if (offerIndexRef.current < mockOfferSummaries.length) {
        const idx = offerIndexRef.current;
        setOfferSummaries((prev) => [...prev, mockOfferSummaries[idx]]);
        offerIndexRef.current++;
      } else {
        clearInterval(interval);
        // Move to generating after all offers received
        setTimeout(() => setStage('generating'), 1500);
      }
    }, 800);

    return () => clearInterval(interval);
  }, [isMock, stage, mockOfferSummaries]);

  // Mock: generating -> complete
  useEffect(() => {
    if (!isMock || stage !== 'generating') return;

    const timer = setTimeout(() => {
      setStage('complete');
    }, 3000);

    return () => clearTimeout(timer);
  }, [isMock, stage]);

  // Navigate to proposals when complete
  const handleViewProposals = useCallback(() => {
    router.push(`/team/proposals/${requestId}`);
  }, [router, requestId]);

  return (
    <div className="team-matcher-root">
      <TeamBackground />
      <TeamNav currentStep="progress" />
      <main className={styles.main}>
        <SignalVisualization
          stage={stage}
          offersCount={offerSummaries.length}
          offerSummaries={offerSummaries}
        />

        {stage === 'complete' && (
          <button
            className={styles.viewBtn}
            onClick={handleViewProposals}
          >
            <i className="ri-team-line" />
            查看团队方案
            <i className="ri-arrow-right-line" />
          </button>
        )}
      </main>
    </div>
  );
}
