'use client';

import { use } from 'react';
import { SCENES } from '@/lib/store-scenes';
import { StoreHeader } from '@/components/store/StoreHeader';
import { DemandInput } from '@/components/store/DemandInput';
import { AgentScroll } from '@/components/store/AgentScroll';
import { NegotiationProgress } from '@/components/store/NegotiationProgress';
import { PlanOutput } from '@/components/store/PlanOutput';
import { DeveloperPanel } from '@/components/store/DeveloperPanel';
import { useStoreNegotiation } from '@/hooks/useStoreNegotiation';
import { useStoreAuth } from '@/hooks/useStoreAuth';

export default function ScenePage({
  params,
}: {
  params: Promise<{ scene: string }>;
}) {
  const { scene: sceneId } = use(params);
  const config = SCENES[sceneId];
  const negotiation = useStoreNegotiation();
  const auth = useStoreAuth();

  if (!config) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#F8F6F3' }}>
        <StoreHeader />
        <div style={{ padding: '80px 24px', textAlign: 'center' }}>
          <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 8 }}>
            场景不存在
          </h1>
          <p style={{ color: '#666' }}>
            <a href="/store/" style={{ color: '#D4B8D9' }}>返回 App Store</a>
          </p>
        </div>
      </div>
    );
  }

  const scope = `scene:${sceneId}`;

  const handleSubmit = (intent: string) => {
    negotiation.submit(intent, scope);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: config.bg,
      }}
    >
      <StoreHeader />

      {/* Scene hero */}
      <div style={{ padding: '48px 24px 24px', textAlign: 'center' }}>
        <h1
          style={{
            fontSize: 28,
            fontWeight: 700,
            marginBottom: 8,
            color: '#1A1A1A',
          }}
        >
          {config.hero}
        </h1>
        <p style={{ fontSize: 15, color: '#666', maxWidth: 480, margin: '0 auto' }}>
          {config.heroDesc}
        </p>
      </div>

      <DemandInput
        sceneId={sceneId}
        onSubmit={handleSubmit}
        isSubmitting={negotiation.phase === 'submitting'}
        isAuthenticated={auth.isAuthenticated}
        onLoginRequest={auth.login}
        onAuthExpired={auth.logout}
      />

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
        <AgentScroll scope={scope} cardTemplate={config.cardTemplate} />
      </div>

      {/* Negotiation progress */}
      {negotiation.phase !== 'idle' && (
        <div style={{ padding: '16px 24px' }}>
          <NegotiationProgress
            phase={negotiation.phase}
            participants={negotiation.participants}
            events={negotiation.events}
            timeline={negotiation.timeline}
            graphState={negotiation.graphState}
            error={negotiation.error}
            onReset={negotiation.reset}
          />
        </div>
      )}

      {/* Plan output */}
      {negotiation.planOutput && (
        <div style={{ padding: '0 24px 16px' }}>
          <PlanOutput
            planText={negotiation.planOutput}
            planJson={negotiation.planJson}
            participants={negotiation.participants}
            planTemplate={config.planTemplate}
          />
        </div>
      )}

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
