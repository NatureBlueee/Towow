'use client';

import { useState, useEffect } from 'react';
import { StoreHeader } from '@/components/store/StoreHeader';
import { SceneTabs } from '@/components/store/SceneTabs';
import { DemandInput } from '@/components/store/DemandInput';
import { AgentScroll } from '@/components/store/AgentScroll';
import { NegotiationProgress } from '@/components/store/NegotiationProgress';
import { PlanOutput, DEMO_CHAIN_URL } from '@/components/store/PlanOutput';
import { DeveloperPanel } from '@/components/store/DeveloperPanel';
import { HistoryPanel } from '@/components/store/HistoryPanel';
import { useStoreNegotiation } from '@/hooks/useStoreNegotiation';
import { useStoreAuth } from '@/hooks/useStoreAuth';
import { getSceneConfig } from '@/lib/store-scenes';

export default function StorePage() {
  const [activeScene, setActiveScene] = useState<string | null>(null);
  const negotiation = useStoreNegotiation();
  const auth = useStoreAuth();

  // Token expired during negotiation → trigger logout
  useEffect(() => {
    if (negotiation.isAuthError) {
      auth.logout();
    }
  }, [negotiation.isAuthError, auth]);

  const scope = activeScene ? `scene:${activeScene}` : 'all';
  const scene = getSceneConfig(activeScene || 'hackathon');

  const handleSubmit = (intent: string) => {
    negotiation.submit(intent, scope, auth.user?.agent_id);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: activeScene ? scene.bg : '#F8F6F3',
        transition: 'background-color 0.3s ease',
      }}
    >
      <StoreHeader />

      {/* Hero */}
      <div style={{ padding: '48px 24px 24px', textAlign: 'center' }}>
        <h1
          style={{
            fontSize: 28,
            fontWeight: 700,
            marginBottom: 8,
            color: '#1A1A1A',
          }}
        >
          {activeScene ? scene.hero : '通爻网络'}
        </h1>
        <p style={{ fontSize: 15, color: '#666', maxWidth: 480, margin: '0 auto' }}>
          {activeScene
            ? scene.heroDesc
            : '描述你的需求，网络中的 Agent 会通过共振响应'}
        </p>
      </div>

      {/* Scene tabs */}
      <SceneTabs activeScene={activeScene} onSelect={setActiveScene} />

      {/* 1. Agent list */}
      <div style={{ marginBottom: 8 }}>
        <div
          style={{
            padding: '0 24px 8px',
            fontSize: 13,
            fontWeight: 600,
            color: '#999',
            letterSpacing: 1,
          }}
        >
          AGENTS
        </div>
        <AgentScroll scope={scope} cardTemplate={activeScene ? scene.cardTemplate : 'default'} />
      </div>

      {/* 2. Demand input */}
      <DemandInput
        sceneId={activeScene}
        onSubmit={handleSubmit}
        isSubmitting={negotiation.phase === 'submitting'}
        authSource={auth.authSource}
        onLoginRequest={auth.login}
        onAuthExpired={auth.logout}
      />

      {/* 3. Negotiation progress + Plan output (when active) */}
      {negotiation.phase !== 'idle' && (
        <div style={{ padding: '16px 24px' }}>
          <NegotiationProgress
            phase={negotiation.phase}
            participants={negotiation.participants}
            timeline={negotiation.timeline}
            error={negotiation.error}
            onReset={negotiation.reset}
            totalAgentCount={negotiation.negotiation?.agent_count}
          />
        </div>
      )}

      {(negotiation.planOutput || negotiation.planJson || negotiation.phase === 'completed') && (
        <div style={{ padding: '0 24px 16px' }}>
          <PlanOutput
            planText={negotiation.planOutput}
            planJson={negotiation.planJson}
            participants={negotiation.participants}
            planTemplate={activeScene ? scene.planTemplate : 'default'}
            chainUrl={DEMO_CHAIN_URL}
          />
        </div>
      )}

      {/* 4. History panel — always at bottom */}
      <HistoryPanel authSource={auth.authSource} negotiationPhase={negotiation.phase} />

      {/* Developer panel */}
      <DeveloperPanel
        negotiationId={negotiation.negotiationId}
        phase={negotiation.phase}
        engineState={negotiation.engineState}
        events={negotiation.events}
      />
    </div>
  );
}
