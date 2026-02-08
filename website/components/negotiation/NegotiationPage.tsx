'use client';

import { useCallback, useRef } from 'react';
import { useNegotiationStream } from '@/hooks/useNegotiationStream';
import { useNegotiationApi } from '@/hooks/useNegotiationApi';
import { DemandInput } from './DemandInput';
import { FormulationConfirm } from './FormulationConfirm';
import { AgentPanel } from './AgentPanel';
import { CenterPanel } from './CenterPanel';
import { EventTimeline } from './EventTimeline';
import { mockEventSequence } from './__mocks__/events';
import styles from './NegotiationPage.module.css';

const DEFAULT_SCENE_ID = 'scene_default';
const DEFAULT_USER_ID = 'user_default';

/**
 * NegotiationPage is the main page-level component for the negotiation UI.
 * It orchestrates the full negotiation flow:
 *   demand input -> formulation confirm -> agent matching -> offers -> synthesis -> plan
 *
 * Renders all sub-components and manages the connection between the
 * WebSocket event stream and the REST API actions.
 */
export function NegotiationPage() {
  const stream = useNegotiationStream();
  const api = useNegotiationApi();
  const mockTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const { state, dispatch, connect, injectEvent, reset, connectionStatus } = stream;
  const {
    phase,
    negotiationId,
    formulation,
    resonanceAgents,
    offers,
    centerActivities,
    plan,
    subNegotiations,
    events,
    error,
  } = state;

  // ============ Handlers ============

  // Submit demand: call API, get negotiation ID, connect WebSocket
  const handleSubmit = useCallback(
    async (intent: string) => {
      dispatch({ type: 'SUBMIT_DEMAND' });
      try {
        const negId = await api.submitDemand(DEFAULT_SCENE_ID, DEFAULT_USER_ID, intent);
        dispatch({ type: 'SET_NEGOTIATION_ID', negotiationId: negId });
        connect(negId);
      } catch {
        dispatch({
          type: 'SET_ERROR',
          error: api.error || 'Failed to submit demand',
        });
      }
    },
    [api, dispatch, connect],
  );

  // Confirm formulation
  const handleConfirmFormulation = useCallback(
    async (text: string) => {
      if (!negotiationId) return;
      try {
        await api.confirmFormulation(negotiationId, text);
        dispatch({ type: 'SET_PHASE', phase: 'resonating' });
      } catch {
        dispatch({
          type: 'SET_ERROR',
          error: api.error || 'Failed to confirm formulation',
        });
      }
    },
    [api, negotiationId, dispatch],
  );

  // Accept plan
  const handleAcceptPlan = useCallback(async () => {
    if (!negotiationId) return;
    try {
      await api.userAction(negotiationId, 'accept');
    } catch {
      // Plan acceptance error is non-critical
    }
  }, [api, negotiationId]);

  // Reject plan
  const handleRejectPlan = useCallback(async () => {
    if (!negotiationId) return;
    try {
      await api.userAction(negotiationId, 'reject');
    } catch {
      // Plan rejection error is non-critical
    }
  }, [api, negotiationId]);

  // Demo mode: inject mock events with staggered delays
  const handleDemo = useCallback(() => {
    mockTimersRef.current.forEach(clearTimeout);
    mockTimersRef.current = [];

    reset();
    dispatch({ type: 'SET_NEGOTIATION_ID', negotiationId: 'neg_mock001' });

    mockEventSequence.forEach((event, i) => {
      const timer = setTimeout(() => {
        injectEvent({ ...event, timestamp: new Date().toISOString() });
      }, (i + 1) * 1200);
      mockTimersRef.current.push(timer);
    });
  }, [reset, dispatch, injectEvent]);

  // Reset
  const handleReset = useCallback(() => {
    mockTimersRef.current.forEach(clearTimeout);
    mockTimersRef.current = [];
    reset();
  }, [reset]);

  const isSubmitting = phase === 'submitting' || api.loading;
  const showPhaseBar = phase !== 'idle' && phase !== 'submitting' && phase !== 'error';
  const isSynthesizing = phase === 'synthesizing' || phase === 'barrier_met';

  return (
    <div className={styles.page}>
      {/* Header with title + controls */}
      <header className={styles.header}>
        <h1 className={styles.title}>Negotiation</h1>
        <div className={styles.controls}>
          {connectionStatus !== 'disconnected' && (
            <span
              className={`${styles.statusDot} ${styles[connectionStatus]}`}
              title={connectionStatus}
            />
          )}
          <button className={styles.demoButton} onClick={handleDemo}>
            Demo
          </button>
          {phase !== 'idle' && (
            <button className={styles.resetButton} onClick={handleReset}>
              Reset
            </button>
          )}
        </div>
      </header>

      <main className={styles.main}>
        {/* Phase progress indicator */}
        {showPhaseBar && <PhaseIndicator phase={phase} />}

        {/* Step 1: Demand input (only in idle) */}
        {phase === 'idle' && (
          <DemandInput onSubmit={handleSubmit} disabled={isSubmitting} />
        )}

        {/* Loading state */}
        {isSubmitting && (
          <div className={styles.submitting}>
            <span className={styles.spinner} />
            <span>Submitting demand...</span>
          </div>
        )}

        {/* Step 2: Formulation confirm */}
        {formulation && phase === 'confirming' && (
          <FormulationConfirm
            formulation={formulation}
            onConfirm={handleConfirmFormulation}
          />
        )}

        {/* Confirmed formulation (read-only) */}
        {formulation && phase !== 'confirming' && phase !== 'formulating' && phase !== 'idle' && phase !== 'submitting' && (
          <div className={styles.confirmedFormulation}>
            <span className={styles.confirmedLabel}>Demand confirmed</span>
            <p className={styles.confirmedText}>{formulation.formulated_text}</p>
          </div>
        )}

        {/* Content layout: two columns on wider screens */}
        {(resonanceAgents.length > 0 || centerActivities.length > 0 || plan) && (
          <div className={styles.contentGrid}>
            {/* Left column: Agent panel */}
            <div className={styles.leftCol}>
              <AgentPanel agents={resonanceAgents} offers={offers} />

              {/* Sub-negotiations */}
              {subNegotiations.length > 0 && (
                <div className={styles.subNegSection}>
                  {subNegotiations.map((sub, i) => (
                    <div key={i} className={styles.subNegItem}>
                      <span className={styles.subNegBadge}>Gap Found</span>
                      <p className={styles.subNegDesc}>{sub.gap_description}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Right column: Center panel */}
            <div className={styles.rightCol}>
              <CenterPanel
                activities={centerActivities}
                plan={plan}
                isSynthesizing={isSynthesizing}
                onAcceptPlan={handleAcceptPlan}
                onRejectPlan={handleRejectPlan}
              />
            </div>
          </div>
        )}

        {/* Event timeline */}
        {events.length > 0 && <EventTimeline events={events} />}

        {/* Error */}
        {phase === 'error' && error && (
          <div className={styles.errorBox}>
            <p>{error}</p>
          </div>
        )}
      </main>
    </div>
  );
}

// ============ Phase Indicator ============

function PhaseIndicator({ phase }: { phase: string }) {
  const phases = [
    { key: 'formulating', label: 'Formulating' },
    { key: 'resonating', label: 'Finding' },
    { key: 'collecting_offers', label: 'Collecting' },
    { key: 'synthesizing', label: 'Synthesizing' },
    { key: 'plan_ready', label: 'Plan' },
  ];

  const currentIdx = phases.findIndex(
    (p) =>
      p.key === phase ||
      (phase === 'confirming' && p.key === 'formulating') ||
      (phase === 'barrier_met' && p.key === 'collecting_offers'),
  );

  return (
    <div className={styles.phaseBar}>
      {phases.map((p, i) => (
        <div
          key={p.key}
          className={`${styles.phaseStep} ${i <= currentIdx ? styles.phaseActive : ''} ${i === currentIdx ? styles.phaseCurrent : ''}`}
        >
          <div className={styles.phaseDot} />
          <span className={styles.phaseLabel}>{p.label}</span>
        </div>
      ))}
    </div>
  );
}
