'use client';

import { useEffect, useRef } from 'react';
import type { NegotiationEvent } from '@/types/negotiation';
import styles from './EventTimeline.module.css';

interface EventTimelineProps {
  events: NegotiationEvent[];
}

/** Human-readable label for each event type. */
function eventLabel(type: string): string {
  switch (type) {
    case 'formulation.ready':
      return 'Formulation Ready';
    case 'resonance.activated':
      return 'Agents Matched';
    case 'offer.received':
      return 'Offer Received';
    case 'barrier.complete':
      return 'Barrier Complete';
    case 'center.tool_call':
      return 'Center Tool Call';
    case 'plan.ready':
      return 'Plan Ready';
    case 'sub_negotiation.started':
      return 'Sub-Negotiation';
    default:
      return type;
  }
}

/** CSS class suffix for the event type dot. */
function eventVariant(type: string): string {
  switch (type) {
    case 'formulation.ready':
      return styles.variantFormulation;
    case 'resonance.activated':
      return styles.variantResonance;
    case 'offer.received':
      return styles.variantOffer;
    case 'barrier.complete':
      return styles.variantBarrier;
    case 'center.tool_call':
      return styles.variantCenter;
    case 'plan.ready':
      return styles.variantPlan;
    case 'sub_negotiation.started':
      return styles.variantSubNeg;
    default:
      return styles.variantDefault;
  }
}

/** Extract a short summary from event data. */
function eventSummary(event: NegotiationEvent): string {
  const d = event.data;
  switch (event.event_type) {
    case 'formulation.ready':
      return truncate(String(d.formulated_text || d.raw_intent || ''), 80);
    case 'resonance.activated':
      return `${d.activated_count ?? 0} agent${(d.activated_count as number) !== 1 ? 's' : ''} matched`;
    case 'offer.received':
      return `${d.display_name || d.agent_id}: ${truncate(String(d.content || ''), 60)}`;
    case 'barrier.complete':
      return `${d.offers_received}/${d.total_participants} offers collected`;
    case 'center.tool_call':
      return `${d.tool_name} (round ${d.round_number})`;
    case 'plan.ready':
      return `Plan generated in ${d.center_rounds} round${(d.center_rounds as number) !== 1 ? 's' : ''}`;
    case 'sub_negotiation.started':
      return truncate(String(d.gap_description || ''), 80);
    default:
      return JSON.stringify(d).slice(0, 80);
  }
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '...' : s;
}

function formatTime(timestamp: string): string {
  try {
    const d = new Date(timestamp);
    return d.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '';
  }
}

export function EventTimeline({ events }: EventTimelineProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest event
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [events.length]);

  if (events.length === 0) return null;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>Event Log</h3>
        <span className={styles.count}>{events.length}</span>
      </div>
      <div className={styles.timeline}>
        {events.map((event, i) => (
          <div key={event.event_id || i} className={styles.item}>
            <div className={styles.rail}>
              <div className={`${styles.dot} ${eventVariant(event.event_type)}`} />
              {i < events.length - 1 && <div className={styles.line} />}
            </div>
            <div className={styles.content}>
              <div className={styles.itemHeader}>
                <span className={`${styles.label} ${eventVariant(event.event_type)}`}>
                  {eventLabel(event.event_type)}
                </span>
                <span className={styles.time}>{formatTime(event.timestamp)}</span>
              </div>
              <p className={styles.summary}>{eventSummary(event)}</p>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
