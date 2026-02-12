'use client';

import { useState, useCallback, useRef } from 'react';
import { useNegotiationStream } from '@/hooks/useNegotiationStream';
import { useNegotiationApi } from '@/hooks/useNegotiationApi';
import { DemandInput } from './DemandInput';
import { FormulationConfirm } from './FormulationConfirm';
import NegotiationGraph from './graph/NegotiationGraph';
import { DetailPanel } from './DetailPanel';
import { PlanView } from './PlanView';
import { ResonanceControls } from './ResonanceControls';
import { SubGraph } from './SubGraph';
import { EventTimeline } from './EventTimeline';
import { mockEventSequence } from './__mocks__/events';
import type { DetailPanelContentType } from './graph/types';
import styles from './NegotiationPage.module.css';

const DEFAULT_SCENE_ID = 'scene_default';
const DEFAULT_USER_ID = 'user_default';

/**
 * NegotiationPage is the main page-level component for the negotiation UI.
 * It orchestrates the full negotiation flow:
 *   demand input -> formulation confirm -> agent matching -> offers -> synthesis -> plan
 *
 * Graph-first layout: NegotiationGraph takes center stage, with all
 * supporting components arranged above and below it in a single column.
 * Agent and Center panels are removed — their data is now rendered
 * inside the graph as nodes. DetailPanel slides in from the right
 * when a graph element is clicked.
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

  // ============ Resonance Controls State ============

  const [kStar, setKStar] = useState(10);
  const [minScore, setMinScore] = useState(0.5);

  // ============ Detail Panel State ============

  const [detailPanel, setDetailPanel] = useState<{
    type: DetailPanelContentType;
    data: Record<string, unknown> | null;
  }>({ type: null, data: null });

  // ============ Timeline Collapsed State ============

  const [timelineOpen, setTimelineOpen] = useState(true);

  // ============ Handlers ============

  // Submit demand: call API with resonance parameters, get negotiation ID, connect WebSocket
  const handleSubmit = useCallback(
    async (intent: string) => {
      dispatch({ type: 'SUBMIT_DEMAND' });
      try {
        const negId = await api.submitDemand(
          DEFAULT_SCENE_ID,
          DEFAULT_USER_ID,
          intent,
          kStar,
          minScore,
        );
        dispatch({ type: 'SET_NEGOTIATION_ID', negotiationId: negId });
        connect(negId);
      } catch {
        dispatch({
          type: 'SET_ERROR',
          error: api.error || 'Failed to submit demand',
        });
      }
    },
    [api, dispatch, connect, kStar, minScore],
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
    setDetailPanel({ type: null, data: null });
  }, [reset]);

  // ============ Graph Interaction Handlers ============

  const handleNodeClick = useCallback(
    (nodeType: 'demand' | 'agent' | 'center', id: string) => {
      if (nodeType === 'demand') {
        setDetailPanel({
          type: 'demand',
          data: formulation
            ? {
                raw_intent: formulation.raw_intent,
                formulated_text: formulation.formulated_text,
                enrichments: formulation.enrichments,
              }
            : null,
        });
      } else if (nodeType === 'agent') {
        // Search both activated and filtered agents
        const agent =
          resonanceAgents.find((a) => a.agent_id === id) ||
          state.filteredAgents.find((a) => a.agent_id === id);
        const offer = offers.find((o) => o.agent_id === id);
        const planParticipant = plan?.plan_json?.participants?.find(
          (p) => p.agent_id === id,
        );
        const isFiltered = state.filteredAgents.some((a) => a.agent_id === id);
        setDetailPanel({
          type: 'agent',
          data: {
            agent_id: id,
            display_name: agent?.display_name || id,
            resonance_score: agent?.resonance_score || 0,
            isFiltered,
            offerContent: offer?.content,
            capabilities: offer?.capabilities || [],
            roleInPlan: planParticipant?.role_in_plan,
          },
        });
      } else if (nodeType === 'center') {
        const currentRound =
          centerActivities.length > 0
            ? centerActivities[centerActivities.length - 1].round_number
            : 0;
        setDetailPanel({
          type: 'center',
          data: {
            activities: centerActivities,
            roundNumber: currentRound,
          },
        });
      }
    },
    [formulation, resonanceAgents, state.filteredAgents, offers, plan, centerActivities],
  );

  const handleEdgeClick = useCallback((edgeId: string) => {
    // Edge IDs from layout.ts: res_{agent_id}, int_{index}, dep_{from}_{to}
    if (edgeId.startsWith('res_')) {
      const agentId = edgeId.replace('res_', '');
      const agent =
        resonanceAgents.find((a) => a.agent_id === agentId) ||
        state.filteredAgents.find((a) => a.agent_id === agentId);
      setDetailPanel({
        type: 'resonance_edge',
        data: {
          agent_id: agentId,
          display_name: agent?.display_name || agentId,
          resonance_score: agent?.resonance_score || 0,
        },
      });
    } else if (edgeId.startsWith('int_')) {
      // Edge IDs: int_{activityIdx} or int_{activityIdx}_{pairIdx} for discover
      const match = edgeId.match(/^int_(\d+)/);
      if (!match) return;
      const activityIdx = parseInt(match[1], 10);
      const activity = centerActivities[activityIdx];
      setDetailPanel({
        type: 'interaction_edge',
        data: {
          edgeId,
          interactionType: activity?.tool_name || 'ask_agent',
          toolArgs: activity?.tool_args || {},
          roundNumber: activity?.round_number || 0,
        },
      });
    }
  }, [resonanceAgents, state.filteredAgents, centerActivities]);

  const handleTaskClick = useCallback(
    (taskId: string) => {
      const task = plan?.plan_json?.tasks?.find((t) => t.id === taskId);
      if (task) {
        setDetailPanel({
          type: 'task',
          data: task as unknown as Record<string, unknown>,
        });
      }
    },
    [plan],
  );

  const handleCloseDetail = useCallback(() => {
    setDetailPanel({ type: null, data: null });
  }, []);

  // ============ Computed Flags ============

  const isSubmitting = phase === 'submitting' || api.loading;
  const showPhaseBar = phase !== 'idle' && phase !== 'submitting' && phase !== 'error';
  const showGraph = phase !== 'idle' && phase !== 'submitting';
  const showResonanceControls = phase === 'idle';
  const hasPlan = !!plan;

  return (
    <div className={styles.page}>
      {/* Header with title + controls + status */}
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
        {/* Step 1: Demand input (only in idle) */}
        {phase === 'idle' && (
          <DemandInput onSubmit={handleSubmit} disabled={isSubmitting} />
        )}

        {/* Resonance controls (only before submission) */}
        {showResonanceControls && (
          <ResonanceControls
            kStar={kStar}
            minScore={minScore}
            onKStarChange={setKStar}
            onMinScoreChange={setMinScore}
            disabled={isSubmitting || api.loading}
          />
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

        {/* Phase progress indicator */}
        {showPhaseBar && <PhaseIndicator phase={phase} />}

        {/* ============ Graph Area (center stage) ============ */}
        {showGraph && (
          <div className={styles.graphArea}>
            <NegotiationGraph
              state={state}
              onNodeClick={handleNodeClick}
              onEdgeClick={handleEdgeClick}
              onTaskClick={handleTaskClick}
            />
          </div>
        )}

        {/* ============ Plan View ============ */}
        {hasPlan && plan && (
          <div className={styles.planSection}>
            <PlanView
              planText={plan.plan_text}
              planJson={plan.plan_json}
              onAccept={handleAcceptPlan}
              onReject={handleRejectPlan}
              onTaskClick={handleTaskClick}
            />
          </div>
        )}

        {/* ============ Sub-Negotiation Grid ============ */}
        {subNegotiations.length > 0 && (
          <div className={styles.subGraphGrid}>
            {subNegotiations.map((sub) => (
              <SubGraph
                key={sub.sub_negotiation_id}
                subNegotiationId={sub.sub_negotiation_id}
                gapDescription={sub.gap_description}
                onClick={() => {
                  // Future: navigate to sub-negotiation view
                }}
              />
            ))}
          </div>
        )}

        {/* ============ Detail Panel (slides from right) ============ */}
        <DetailPanel
          type={detailPanel.type}
          data={detailPanel.data}
          onClose={handleCloseDetail}
        />

        {/* ============ Event Timeline (collapsible) ============ */}
        {events.length > 0 && (
          <div className={styles.timelineSection}>
            <button
              className={styles.timelineToggle}
              onClick={() => setTimelineOpen((prev) => !prev)}
              aria-expanded={timelineOpen}
            >
              <span className={styles.timelineToggleIcon}>
                {timelineOpen ? '\u25BE' : '\u25B8'}
              </span>
              <span>Event Log ({events.length})</span>
            </button>
            {timelineOpen && <EventTimeline events={events} />}
          </div>
        )}

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
