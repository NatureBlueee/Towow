'use client';

import { useEffect, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import type { DetailPanelProps, DetailPanelContentType } from './graph/types';
import type { CenterToolCallData, PlanJsonTask } from '@/types/negotiation';
import { parseOfferContent } from '@/lib/parse-offer-content';
import styles from './DetailPanel.module.css';

/**
 * DetailPanel — right-sliding panel that displays detailed information
 * about a clicked graph element (agent, center, demand, task, edge).
 *
 * CSS-only animations:
 *  - Overlay: CSS opacity transition
 *  - Panel: CSS translateX transition (both entry and exit)
 *  - Last valid content preserved during exit via ref
 */

// ============ Type Icons ============

const TYPE_ICONS: Record<Exclude<DetailPanelContentType, null>, string> = {
  agent: '\u2726',          // four-pointed star
  center: '\u25C9',         // fisheye
  demand: '\u2738',         // heavy eight-pointed star
  task: '\u2611',           // ballot box with check
  resonance_edge: '\u223F', // sine wave
  interaction_edge: '\u21C4', // left right arrows
};

const TYPE_TITLES: Record<Exclude<DetailPanelContentType, null>, string> = {
  agent: '参与者详情',
  center: '协调活动',
  demand: '需求详情',
  task: '任务详情',
  resonance_edge: '共振连接',
  interaction_edge: '交互',
};

// ============ Helper: Format tool args ============

function formatToolArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args);
  if (entries.length === 0) return '(no arguments)';
  return entries
    .map(([k, v]) => {
      const val = typeof v === 'string' ? v : JSON.stringify(v);
      return `${k}: ${val}`;
    })
    .join('\n');
}

// ============ Helper: Readable interaction type ============

function readableInteractionType(type: string): string {
  switch (type) {
    case 'ask_agent':
      return 'Ask Agent';
    case 'discover':
      return 'Discover';
    case 'task_assignment':
      return 'Task Assignment';
    default:
      return type;
  }
}

// ============ Helper: Interaction icon class ============

function interactionIconClass(type: string): string {
  switch (type) {
    case 'ask_agent':
      return styles.interactionIcon_ask_agent;
    case 'discover':
      return styles.interactionIcon_discover;
    case 'task_assignment':
      return styles.interactionIcon_task_assignment;
    default:
      return styles.interactionIcon_ask_agent;
  }
}

// ============ Helper: Interaction icon character ============

function interactionIconChar(type: string): string {
  switch (type) {
    case 'ask_agent':
      return '?';
    case 'discover':
      return '\u2605'; // star
    case 'task_assignment':
      return '\u2192'; // right arrow
    default:
      return '\u2022';
  }
}

// ============ Helper: Status CSS class ============

function statusClass(status: string): string {
  switch (status) {
    case 'pending':
      return styles.statusTag_pending;
    case 'in_progress':
      return styles.statusTag_in_progress;
    case 'completed':
      return styles.statusTag_completed;
    default:
      return styles.statusTag_pending;
  }
}

// ============ Content Renderers ============

function AgentContent({ data }: { data: Record<string, unknown> }) {
  const displayName = (data.display_name as string) || 'Unknown Agent';
  const resonanceScore = (data.resonance_score as number) || 0;
  const offerContent = parseOfferContent(data.offerContent as string | undefined);
  const capabilities = (data.capabilities as string[]) || [];
  const roleInPlan = data.roleInPlan as string | undefined;
  const percent = Math.round(resonanceScore * 100);

  return (
    <>
      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>Agent Name</p>
        <p className={styles.sectionValue}>{displayName}</p>
      </div>

      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>Resonance Score</p>
        <div className={styles.scoreRow}>
          <div className={styles.scoreBarTrack}>
            <div
              className={styles.scoreBarFill}
              style={{ width: `${percent}%` }}
            />
          </div>
          <span className={styles.scoreLabel}>{percent}%</span>
        </div>
      </div>

      {offerContent && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>Offer</p>
          <div className={`${styles.textBlock} markdown-content`}>
            <ReactMarkdown>{offerContent}</ReactMarkdown>
          </div>
        </div>
      )}

      {capabilities.length > 0 && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>Capabilities</p>
          <div className={styles.tagList}>
            {capabilities.map((cap) => (
              <span key={cap} className={styles.tag}>{cap}</span>
            ))}
          </div>
        </div>
      )}

      {roleInPlan && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>Role in Plan</p>
          <span className={styles.roleTag}>{roleInPlan}</span>
        </div>
      )}
    </>
  );
}

function CenterContent({ data }: { data: Record<string, unknown> }) {
  const activities = (data.activities as CenterToolCallData[]) || [];
  const roundNumber = (data.roundNumber as number) || 0;

  return (
    <>
      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>Round</p>
        <p className={styles.sectionValue}>{roundNumber}</p>
      </div>

      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>Tool Calls ({activities.length})</p>
        {activities.length === 0 ? (
          <p className={styles.sectionValue}>No tool calls yet</p>
        ) : (
          activities.map((tc, i) => (
            <div key={i} className={styles.toolCallCard} style={{ marginTop: i > 0 ? 8 : 0 }}>
              <span className={styles.toolCallName}>{tc.tool_name}</span>
              <span className={styles.toolCallArgs}>{formatToolArgs(tc.tool_args)}</span>
              <span className={styles.toolCallRound}>Round {tc.round_number}</span>
            </div>
          ))
        )}
      </div>
    </>
  );
}

function DemandContent({ data }: { data: Record<string, unknown> }) {
  const rawIntent = (data.raw_intent as string) || '';
  const formulatedText = (data.formulated_text as string) || '';
  const enrichments = (data.enrichments as Record<string, unknown>) || {};

  const enrichmentEntries = Object.entries(enrichments);

  return (
    <>
      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>Original Intent</p>
        <p className={styles.textBlock}>{rawIntent}</p>
      </div>

      {formulatedText && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>Formulated Text</p>
          <p className={styles.textBlock}>{formulatedText}</p>
        </div>
      )}

      {enrichmentEntries.length > 0 && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>Enrichments</p>
          <div className={styles.enrichmentBlock}>
            {enrichmentEntries.map(([key, value]) => (
              <div key={key} className={styles.enrichmentRow}>
                <span className={styles.enrichmentKey}>{key}</span>
                <span className={styles.enrichmentValue}>
                  {Array.isArray(value)
                    ? value.join(', ')
                    : typeof value === 'string'
                      ? value
                      : JSON.stringify(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function statusLabel(status: string): string {
  switch (status) {
    case 'pending':
      return '待开始';
    case 'in_progress':
      return '进行中';
    case 'completed':
      return '已完成';
    default:
      return status;
  }
}

function TaskContent({ data }: { data: Record<string, unknown> }) {
  const task = data as unknown as PlanJsonTask;

  return (
    <>
      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>任务名称</p>
        <p className={styles.sectionValue}>{task.title || '未命名'}</p>
      </div>

      {task.description && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>任务描述</p>
          <p className={styles.textBlock}>{task.description}</p>
        </div>
      )}

      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>负责人</p>
        <p className={styles.sectionValue}>{task.assignee_id || '未分配'}</p>
      </div>

      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>状态</p>
        <span className={`${styles.statusTag} ${statusClass(task.status || 'pending')}`}>
          {statusLabel(task.status || 'pending')}
        </span>
      </div>

      {task.prerequisites && task.prerequisites.length > 0 && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>前置依赖</p>
          <ul className={styles.prereqList}>
            {task.prerequisites.map((prereq) => (
              <li key={prereq} className={styles.prereqItem}>{prereq}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function ResonanceEdgeContent({ data }: { data: Record<string, unknown> }) {
  const displayName = (data.display_name as string) || 'Unknown';
  const resonanceScore = (data.resonance_score as number) || 0;
  const percent = Math.round(resonanceScore * 100);

  return (
    <>
      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>Agent</p>
        <p className={styles.sectionValue}>{displayName}</p>
      </div>

      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>Resonance Score</p>
        <div className={styles.scoreRow}>
          <div className={styles.scoreBarTrack}>
            <div
              className={styles.scoreBarFill}
              style={{ width: `${percent}%` }}
            />
          </div>
          <span className={styles.scoreLabel}>{percent}%</span>
        </div>
      </div>
    </>
  );
}

function InteractionEdgeContent({ data }: { data: Record<string, unknown> }) {
  const interactionType = (data.interactionType as string) || 'unknown';
  const agentIds = (data.agentIds as string[]) || [];
  const question = data.question as string | undefined;
  const reason = data.reason as string | undefined;
  const label = data.label as string | undefined;

  return (
    <>
      <div className={styles.sectionBlock}>
        <p className={styles.sectionLabel}>Type</p>
        <div className={styles.interactionTypeRow}>
          <div className={`${styles.interactionIcon} ${interactionIconClass(interactionType)}`}>
            {interactionIconChar(interactionType)}
          </div>
          <span className={styles.interactionLabel}>
            {readableInteractionType(interactionType)}
          </span>
        </div>
      </div>

      {label && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>Label</p>
          <p className={styles.sectionValue}>{label}</p>
        </div>
      )}

      {agentIds.length > 0 && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>Participants</p>
          <div className={styles.tagList}>
            {agentIds.map((id) => (
              <span key={id} className={styles.tag}>{id}</span>
            ))}
          </div>
        </div>
      )}

      {question && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>Question</p>
          <p className={styles.textBlock}>{question}</p>
        </div>
      )}

      {reason && (
        <div className={styles.sectionBlock}>
          <p className={styles.sectionLabel}>Reason</p>
          <p className={styles.textBlock}>{reason}</p>
        </div>
      )}
    </>
  );
}

// ============ Content Router ============

function PanelContent({ type, data }: { type: Exclude<DetailPanelContentType, null>; data: Record<string, unknown> }) {
  switch (type) {
    case 'agent':
      return <AgentContent data={data} />;
    case 'center':
      return <CenterContent data={data} />;
    case 'demand':
      return <DemandContent data={data} />;
    case 'task':
      return <TaskContent data={data} />;
    case 'resonance_edge':
      return <ResonanceEdgeContent data={data} />;
    case 'interaction_edge':
      return <InteractionEdgeContent data={data} />;
  }
}

// ============ Main Component ============

export function DetailPanel({ type, data, onClose }: DetailPanelProps) {
  const isOpen = type !== null && data !== null;

  // Preserve last valid content during exit animation
  const lastTypeRef = useRef<Exclude<DetailPanelContentType, null>>('agent');
  const lastDataRef = useRef<Record<string, unknown>>({});
  if (type !== null && data !== null) {
    lastTypeRef.current = type;
    lastDataRef.current = data;
  }
  const displayType = type ?? lastTypeRef.current;
  const displayData = data ?? lastDataRef.current;

  // Close on Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  return (
    <>
      {/* Invisible overlay to catch outside clicks */}
      <div
        className={`${styles.overlay} ${isOpen ? styles.overlayVisible : ''}`}
        onClick={isOpen ? onClose : undefined}
      />

      {/* Sliding panel — CSS transition for both entry and exit */}
      <div className={`${styles.panel} ${isOpen ? styles.panelVisible : ''}`}>
        {/* Header */}
        <div className={styles.header}>
          <div className={`${styles.typeIcon} ${styles[`typeIcon_${displayType}`]}`}>
            {TYPE_ICONS[displayType]}
          </div>
          <h3 className={styles.headerTitle}>{TYPE_TITLES[displayType]}</h3>
          <button
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Close panel"
          >
            {'\u00D7'}
          </button>
        </div>

        {/* Scrollable content */}
        <div className={styles.content}>
          <PanelContent type={displayType} data={displayData} />
        </div>
      </div>
    </>
  );
}
