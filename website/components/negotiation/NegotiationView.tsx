'use client';

import type { NegotiationState } from '@/types/negotiation';
import { FormulationConfirm } from './FormulationConfirm';
import { ResonanceDisplay } from './ResonanceDisplay';
import { OfferCard } from './OfferCard';
import { CenterActivity } from './CenterActivity';
import { PlanResult } from './PlanResult';
import styles from './NegotiationView.module.css';

interface NegotiationViewProps {
  state: NegotiationState;
  onConfirmFormulation: (text: string) => void;
  onAcceptPlan?: () => void;
  onRejectPlan?: () => void;
}

/** Phase progress indicator */
function PhaseIndicator({ phase }: { phase: string }) {
  const phases = [
    { key: 'formulating', label: 'Formulating' },
    { key: 'resonating', label: 'Finding' },
    { key: 'collecting_offers', label: 'Collecting' },
    { key: 'synthesizing', label: 'Synthesizing' },
    { key: 'plan_ready', label: 'Plan' },
  ];

  const currentIdx = phases.findIndex(
    (p) => p.key === phase || (phase === 'confirming' && p.key === 'formulating')
      || (phase === 'barrier_met' && p.key === 'collecting_offers'),
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

export function NegotiationView({
  state,
  onConfirmFormulation,
  onAcceptPlan,
  onRejectPlan,
}: NegotiationViewProps) {
  const { phase, formulation, resonanceAgents, offers, centerActivities, plan, subNegotiations, error } = state;

  if (phase === 'idle' || phase === 'submitting') return null;

  return (
    <div className={styles.container}>
      {phase !== 'error' && (
        <PhaseIndicator phase={phase} />
      )}

      {/* Formulation ready — ask user to confirm */}
      {formulation && phase === 'confirming' && (
        <FormulationConfirm
          formulation={formulation}
          onConfirm={onConfirmFormulation}
        />
      )}

      {/* Formulation was confirmed — show it read-only */}
      {formulation && phase !== 'confirming' && phase !== 'formulating' && (
        <div className={styles.confirmedFormulation}>
          <span className={styles.confirmedLabel}>Demand confirmed</span>
          <p className={styles.confirmedText}>{formulation.formulated_text}</p>
        </div>
      )}

      {/* Resonance */}
      {resonanceAgents.length > 0 && (
        <ResonanceDisplay agents={resonanceAgents} />
      )}

      {/* Offers */}
      {offers.length > 0 && (
        <div className={styles.offersSection}>
          <h3 className={styles.sectionTitle}>
            Offers ({offers.length})
          </h3>
          <div className={styles.offersGrid}>
            {offers.map((offer, i) => (
              <OfferCard key={offer.agent_id} offer={offer} index={i} />
            ))}
          </div>
        </div>
      )}

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

      {/* Center activity */}
      {(centerActivities.length > 0 || phase === 'synthesizing') && (
        <CenterActivity
          activities={centerActivities}
          isSynthesizing={phase === 'synthesizing' || phase === 'barrier_met'}
        />
      )}

      {/* Plan */}
      {plan && (
        <PlanResult
          plan={plan}
          onAccept={onAcceptPlan}
          onReject={onRejectPlan}
        />
      )}

      {/* Error */}
      {phase === 'error' && error && (
        <div className={styles.errorBox}>
          <p>{error}</p>
        </div>
      )}
    </div>
  );
}
