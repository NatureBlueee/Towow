'use client';

import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { DetailPanel } from '@/components/negotiation/DetailPanel';
import type { DetailPanelContentType } from '@/components/negotiation/graph/types';
import type { StoreParticipant } from '@/lib/store-api';
import type { TimelineEntry, NegotiationPhase } from '@/hooks/useStoreNegotiation';
import styles from './NegotiationProgress.module.css';

interface NegotiationProgressProps {
  phase: NegotiationPhase;
  participants: StoreParticipant[];
  timeline: TimelineEntry[];
  error: string | null;
  onReset: () => void;
  totalAgentCount?: number;
}

// ============ Phase Steps Config ============

const STEPS = [
  { key: 'formulating', label: '需求理解' },
  { key: 'resonating', label: '共振' },
  { key: 'offering', label: '响应收集' },
  { key: 'synthesizing', label: '协调' },
  { key: 'completed', label: '完成' },
] as const;

const PHASE_ORDER = [
  'submitting',
  'formulating',
  'resonating',
  'offering',
  'synthesizing',
  'completed',
] as const;

const PHASE_LABELS: Record<string, string> = {
  submitting: '提交中',
  formulating: '需求理解',
  resonating: '信号共振',
  offering: '方案生成',
  synthesizing: '综合协调',
  completed: '已完成',
  error: '出错',
};

const DOT_COLORS: Record<string, string> = {
  formulation: '#D4B8D9',
  resonance: '#8FD5A3',
  offer: '#F9A87C',
  barrier: '#FFE4B5',
  tool: '#B8D4E3',
  plan: '#8FD5A3',
};

const SOURCE_COLORS: Record<string, string> = {
  secondme: '#F9A87C',
  json_file: '#C4A0CA',
  default: '#8FD5A3',
};

// ============ Step Status Logic ============

function getStepStatus(
  stepKey: string,
  currentPhase: string,
): 'done' | 'active' | 'pending' {
  const stepIndex = PHASE_ORDER.indexOf(stepKey as (typeof PHASE_ORDER)[number]);
  const currentIndex = PHASE_ORDER.indexOf(
    currentPhase as (typeof PHASE_ORDER)[number],
  );
  if (currentIndex < 0 || stepIndex < 0) return 'pending';
  if (currentPhase === 'error') {
    // error: steps already passed stay done, current step becomes active (CSS marks it red)
    return stepIndex < currentIndex
      ? 'done'
      : stepIndex === currentIndex
        ? 'active'
        : 'pending';
  }
  if (stepIndex < currentIndex) return 'done';
  if (stepIndex === currentIndex) return 'active';
  return 'pending';
}

// ============ Score → Color Mapping ============

function scoreToColor(score: number): string {
  // HSL interpolation: score 0→1 maps hue 280→160 (gray-purple → brand green)
  const hue = 280 - score * 120;
  const saturation = 25 + score * 30; // 25% → 55%
  const lightness = 70 - score * 20; // 70% → 50%
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

// ============ Name Truncation ============

function truncateName(name: string, maxLen: number = 8): string {
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen) + '..';
}

// ============ Main Component ============

export function NegotiationProgress({
  phase,
  participants,
  timeline,
  error,
  onReset,
  totalAgentCount,
}: NegotiationProgressProps) {
  // ---- Detail Panel State ----
  const [detailPanel, setDetailPanel] = useState<{
    type: DetailPanelContentType;
    data: Record<string, unknown> | null;
  }>({ type: null, data: null });

  const handleAgentClick = useCallback((participant: StoreParticipant) => {
    setDetailPanel({
      type: 'agent',
      data: {
        agent_id: participant.agent_id,
        display_name: participant.display_name,
        resonance_score: participant.resonance_score,
        isFiltered: false,
        offerContent: participant.offer_content,
        capabilities: [],
        roleInPlan: undefined,
      },
    });
  }, []);

  const handleCloseDetail = useCallback(() => {
    setDetailPanel({ type: null, data: null });
  }, []);

  if (phase === 'idle') return null;

  return (
    <div className={styles.container}>
      <Header phase={phase} />
      {error && <ErrorBanner error={error} />}
      <PhaseSteps phase={phase} />
      {totalAgentCount && totalAgentCount > 0 && (
        <ResonanceBanner
          totalAgentCount={totalAgentCount}
          resonatedCount={participants.length}
          phase={phase}
        />
      )}
      <AgentGrid
        participants={participants}
        phase={phase}
        onAgentClick={handleAgentClick}
        totalAgentCount={totalAgentCount}
      />
      <ActivityFeed timeline={timeline} phase={phase} />
      {(phase === 'completed' || phase === 'error') && (
        <ResetButton onReset={onReset} />
      )}
      <DetailPanel
        type={detailPanel.type}
        data={detailPanel.data}
        onClose={handleCloseDetail}
      />
    </div>
  );
}

// ============ Header ============

function Header({ phase }: { phase: NegotiationPhase }) {
  const badgeClass =
    phase === 'completed'
      ? styles.statusBadgeCompleted
      : phase === 'error'
        ? styles.statusBadgeError
        : styles.statusBadgeActive;

  return (
    <div className={styles.header}>
      <div className={styles.headerLeft}>
        <span className={styles.headerTitle}>协商进度</span>
        <span className={`${styles.statusBadge} ${badgeClass}`}>
          {PHASE_LABELS[phase] || phase}
        </span>
      </div>
    </div>
  );
}

// ============ Error Banner ============

function ErrorBanner({ error }: { error: string }) {
  return <div className={styles.errorBanner}>{error}</div>;
}

// ============ Resonance Banner (群像 Crowd Visualization) ============

const DOT_CAP = 200;

function ResonanceBanner({
  totalAgentCount,
  resonatedCount,
  phase,
}: {
  totalAgentCount: number;
  resonatedCount: number;
  phase: NegotiationPhase;
}) {
  const displayCount = Math.min(totalAgentCount, DOT_CAP);
  const isScanning = phase === 'formulating' || phase === 'resonating';
  const hasResonated = resonatedCount > 0;

  // Scale resonated dot count proportionally when capped (preserve visual density accuracy)
  const scaledResonatedCount =
    totalAgentCount > DOT_CAP
      ? Math.max(1, Math.round((resonatedCount / totalAgentCount) * displayCount))
      : resonatedCount;

  // Evenly distribute resonated highlights across the dot cloud
  const resonatedSet = useMemo(() => {
    if (!hasResonated || displayCount === 0) return new Set<number>();
    const set = new Set<number>();
    const count = Math.min(scaledResonatedCount, displayCount);
    const step = displayCount / count;
    for (let i = 0; i < count; i++) {
      set.add(Math.round(i * step));
    }
    return set;
  }, [hasResonated, scaledResonatedCount, displayCount]);

  return (
    <div className={styles.resonanceBanner}>
      <div
        className={`${styles.dotCloud} ${isScanning ? styles.dotCloudScanning : ''} ${hasResonated ? styles.dotCloudResonated : ''}`}
      >
        {Array.from({ length: displayCount }, (_, i) => {
          const isLit = hasResonated && resonatedSet.has(i);
          return (
            <div
              key={i}
              className={`${styles.crowdDot} ${isLit ? styles.crowdDotLit : ''} ${hasResonated && !isLit ? styles.crowdDotFaded : ''}`}
              style={
                { animationDelay: `${(i * 0.06) % 2.5}s` } as React.CSSProperties
              }
            />
          );
        })}
      </div>
      <div className={styles.resonanceCaption}>
        {isScanning ? (
          <>
            扫描{' '}
            <span className={styles.captionNumber}>{totalAgentCount}</span> 个
            Agent 中...
          </>
        ) : hasResonated ? (
          <>
            从{' '}
            <span className={styles.captionNumber}>{totalAgentCount}</span> 个
            Agent 中共振出{' '}
            <span className={styles.captionNumberHighlight}>
              {resonatedCount}
            </span>{' '}
            个
          </>
        ) : (
          <>
            <span className={styles.captionNumber}>{totalAgentCount}</span> 个
            Agent 待扫描
          </>
        )}
      </div>
    </div>
  );
}

// ============ Phase Steps ============

function PhaseSteps({ phase }: { phase: NegotiationPhase }) {
  return (
    <div className={styles.phaseSteps}>
      {STEPS.map((step, i) => {
        const status = getStepStatus(step.key, phase);
        const isError = phase === 'error' && status === 'active';

        const dotClass =
          status === 'done'
            ? styles.stepDotDone
            : status === 'active'
              ? isError
                ? styles.stepDotError
                : styles.stepDotActive
              : styles.stepDot;

        const lineClass =
          status === 'done' ? styles.stepLineDone : styles.stepLine;

        const labelClass =
          status === 'done'
            ? styles.stepLabelDone
            : status === 'active'
              ? isError
                ? styles.stepLabelError
                : styles.stepLabelActive
              : styles.stepLabel;

        return (
          <div key={step.key} className={styles.stepWrapper}>
            <div className={styles.step}>
              <div className={dotClass}>
                {status === 'done' && (
                  <svg
                    width="10"
                    height="10"
                    viewBox="0 0 10 10"
                    fill="none"
                  >
                    <path
                      d="M2.5 5L4.5 7L7.5 3"
                      stroke="white"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </div>
              <span className={labelClass}>{step.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={lineClass} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ============ Agent Grid ============

function AgentGrid({
  participants,
  phase,
  onAgentClick,
  totalAgentCount,
}: {
  participants: StoreParticipant[];
  phase: NegotiationPhase;
  onAgentClick: (p: StoreParticipant) => void;
  totalAgentCount?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const DEFAULT_VISIBLE_COUNT = 12;

  // Track newly arrived offers for pulse animation
  const seenOffersRef = useRef<Set<string>>(new Set());
  const [pulsingIds, setPulsingIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const freshIds: string[] = [];
    for (const p of participants) {
      if (p.offer_content && !seenOffersRef.current.has(p.agent_id)) {
        freshIds.push(p.agent_id);
        seenOffersRef.current.add(p.agent_id);
      }
    }
    if (freshIds.length > 0) {
      setPulsingIds(new Set(freshIds));
      const timer = setTimeout(() => setPulsingIds(new Set()), 800);
      return () => clearTimeout(timer);
    }
  }, [participants]);

  const sorted = useMemo(
    () =>
      [...participants].sort((a, b) => b.resonance_score - a.resonance_score),
    [participants],
  );
  const visible = expanded ? sorted : sorted.slice(0, DEFAULT_VISIBLE_COUNT);

  if (participants.length === 0) return null;

  return (
    <div className={styles.agentSection}>
      <div className={styles.agentSectionHeader}>
        <span className={styles.agentSectionTitle}>
          共振 Agent ({participants.length})
        </span>
      </div>
      <div className={styles.agentGrid}>
        {visible.map((p, index) => {
          const hasOffer = !!p.offer_content;
          const color = scoreToColor(p.resonance_score);
          const percent = Math.round(p.resonance_score * 100);
          const isPulsing = pulsingIds.has(p.agent_id);

          return (
            <button
              key={p.agent_id}
              className={`${styles.agentCard}${isPulsing ? ` ${styles.agentCardPulse}` : ''}`}
              style={
                {
                  '--delay': `${index * 0.08}s`,
                  '--score-color': color,
                } as React.CSSProperties
              }
              onClick={() => onAgentClick(p)}
              type="button"
            >
              <div className={styles.agentName} title={p.display_name}>
                {truncateName(p.display_name)}
              </div>
              <div className={styles.agentScore} style={{ color }}>
                {percent}%
              </div>
              <div
                className={
                  hasOffer ? styles.agentStatusDone : styles.agentStatus
                }
              >
                {hasOffer ? '已回应' : '等待中'}
              </div>
            </button>
          );
        })}
      </div>
      {sorted.length > DEFAULT_VISIBLE_COUNT && (
        <button
          className={styles.expandButton}
          onClick={() => setExpanded((prev) => !prev)}
          type="button"
        >
          {expanded
            ? '收起'
            : `展开全部 (${sorted.length - DEFAULT_VISIBLE_COUNT} more)`}
        </button>
      )}
    </div>
  );
}

// ============ Activity Feed ============

function ActivityFeed({
  timeline,
  phase,
}: {
  timeline: TimelineEntry[];
  phase: NegotiationPhase;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showTools, setShowTools] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  const mainEvents = useMemo(
    () => timeline.filter((e) => e.dotType !== 'tool'),
    [timeline],
  );
  const toolEvents = useMemo(
    () => timeline.filter((e) => e.dotType === 'tool'),
    [timeline],
  );

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [timeline.length]);

  if (timeline.length === 0) {
    return (
      <div className={styles.activitySection}>
        <div className={styles.activityEmpty}>等待事件...</div>
      </div>
    );
  }

  // Compute expandedItems indices relative to the original timeline
  // for mainEvents: we need the original index for fullDetail toggling
  const mainWithIndex = timeline
    .map((entry, i) => ({ entry, originalIndex: i }))
    .filter(({ entry }) => entry.dotType !== 'tool');
  const toolWithIndex = timeline
    .map((entry, i) => ({ entry, originalIndex: i }))
    .filter(({ entry }) => entry.dotType === 'tool');

  return (
    <div className={styles.activitySection}>
      <div className={styles.activitySectionHeader}>
        <span className={styles.activitySectionTitle}>活动记录</span>
      </div>
      <div ref={scrollRef} className={styles.activityScroll}>
        {mainWithIndex.map(({ entry, originalIndex }, i) => (
          <ActivityItem
            key={originalIndex}
            entry={entry}
            isLast={
              i === mainWithIndex.length - 1 && toolWithIndex.length === 0
            }
            isExpanded={expandedItems.has(originalIndex)}
            onToggleExpand={() =>
              setExpandedItems((prev) => {
                const next = new Set(prev);
                if (next.has(originalIndex)) next.delete(originalIndex);
                else next.add(originalIndex);
                return next;
              })
            }
          />
        ))}

        {/* Tool calls — collapsible section */}
        {toolWithIndex.length > 0 && (
          <>
            <button
              className={styles.expandToggle}
              onClick={() => setShowTools((prev) => !prev)}
              type="button"
            >
              {showTools
                ? '收起工具调用'
                : `展开工具调用 (${toolWithIndex.length})`}
            </button>
            {showTools &&
              toolWithIndex.map(({ entry, originalIndex }, i) => (
                <ActivityItem
                  key={originalIndex}
                  entry={entry}
                  isLast={i === toolWithIndex.length - 1}
                  isExpanded={expandedItems.has(originalIndex)}
                  onToggleExpand={() =>
                    setExpandedItems((prev) => {
                      const next = new Set(prev);
                      if (next.has(originalIndex))
                        next.delete(originalIndex);
                      else next.add(originalIndex);
                      return next;
                    })
                  }
                />
              ))}
          </>
        )}
      </div>
    </div>
  );
}

// ============ Activity Item ============

function ActivityItem({
  entry,
  isLast,
  isExpanded,
  onToggleExpand,
}: {
  entry: TimelineEntry;
  isLast: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
}) {
  return (
    <div className={styles.activityItem}>
      {!isLast && <div className={styles.activityLine} />}
      <div
        className={styles.activityDot}
        style={
          {
            '--dot-color': DOT_COLORS[entry.dotType] || '#ccc',
          } as React.CSSProperties
        }
      />
      <div className={styles.activityContent}>
        <div className={styles.activityTitle}>{entry.title}</div>
        {entry.detail && (
          <div className={styles.activityDetail}>
            {isExpanded && entry.fullDetail ? entry.fullDetail : entry.detail}
            {entry.fullDetail && (
              <button
                className={styles.activityExpandBtn}
                onClick={onToggleExpand}
                type="button"
              >
                {isExpanded ? '收起' : '展开全部'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============ Reset Button ============

function ResetButton({ onReset }: { onReset: () => void }) {
  return (
    <div className={styles.resetRow}>
      <button className={styles.resetButton} onClick={onReset} type="button">
        重新开始
      </button>
    </div>
  );
}
