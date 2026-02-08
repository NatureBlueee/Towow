'use client';

import { useCallback, useRef } from 'react';
import { useNegotiationStream } from '@/hooks/useNegotiationStream';
import { useNegotiationApi } from '@/hooks/useNegotiationApi';
import { DemandInput } from '@/components/negotiation/DemandInput';
import { NegotiationView } from '@/components/negotiation/NegotiationView';
import { mockEventSequence } from '@/components/negotiation/__mocks__/events';
import styles from './NegotiatePage.module.css';

const DEFAULT_SCENE_ID = 'scene_default';
const DEFAULT_USER_ID = 'user_default';

export function NegotiatePage() {
  const stream = useNegotiationStream();
  const api = useNegotiationApi();
  const mockTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const { state, dispatch, connect, injectEvent, reset, connectionStatus } = stream;
  const { phase, negotiationId } = state;

  // Submit demand: call API, get negotiation ID, connect WebSocket
  const handleSubmit = useCallback(
    async (intent: string) => {
      dispatch({ type: 'SUBMIT_DEMAND' });
      try {
        const negId = await api.submitDemand(DEFAULT_SCENE_ID, DEFAULT_USER_ID, intent);
        dispatch({ type: 'SET_NEGOTIATION_ID', negotiationId: negId });
        connect(negId);
      } catch {
        dispatch({ type: 'SET_ERROR', error: api.error || 'Failed to submit demand' });
      }
    },
    [api, dispatch, connect],
  );

  // Confirm formulation: call API
  const handleConfirmFormulation = useCallback(
    async (text: string) => {
      if (!negotiationId) return;
      try {
        await api.confirmFormulation(negotiationId, text);
        dispatch({ type: 'SET_PHASE', phase: 'resonating' });
      } catch {
        dispatch({ type: 'SET_ERROR', error: api.error || 'Failed to confirm formulation' });
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

  // Demo mode: inject mock events one by one with delays
  const handleDemo = useCallback(() => {
    // Clear any existing timers
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

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Negotiate</h1>
        <div className={styles.controls}>
          {connectionStatus !== 'disconnected' && (
            <span className={`${styles.statusDot} ${styles[connectionStatus]}`} />
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
        {phase === 'idle' && (
          <DemandInput onSubmit={handleSubmit} disabled={isSubmitting} />
        )}

        {isSubmitting && (
          <div className={styles.submitting}>
            <span className={styles.spinner} />
            <span>Submitting demand...</span>
          </div>
        )}

        <NegotiationView
          state={state}
          onConfirmFormulation={handleConfirmFormulation}
          onAcceptPlan={handleAcceptPlan}
          onRejectPlan={handleRejectPlan}
        />
      </main>
    </div>
  );
}
