'use client';

import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import NegotiationGraph from '@/components/negotiation/graph/NegotiationGraph';
import { DetailPanel } from '@/components/negotiation/DetailPanel';
import { buildNegotiationState } from '@/lib/store-negotiation-adapter';
import type { DetailPanelContentType } from '@/components/negotiation/graph/types';
import type { StoreParticipant } from '@/lib/store-api';
import type { StoreEvent } from '@/hooks/useStoreWebSocket';
import type { TimelineEntry, GraphState, NegotiationPhase } from '@/hooks/useStoreNegotiation';

interface NegotiationProgressProps {
  phase: NegotiationPhase;
  participants: StoreParticipant[];
  events: StoreEvent[];
  timeline: TimelineEntry[];
  graphState: GraphState;
  error: string | null;
  onReset: () => void;
}

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

type ProgressView = 'timeline' | 'graph';

export function NegotiationProgress({
  phase,
  participants,
  events,
  timeline,
  graphState,
  error,
  onReset,
}: NegotiationProgressProps) {
  const [view, setView] = useState<ProgressView>('graph');

  // ============ NegotiationGraph State ============

  const negotiationState = useMemo(
    () => buildNegotiationState(events, phase),
    [events, phase],
  );

  // ============ Detail Panel State ============

  const [detailPanel, setDetailPanel] = useState<{
    type: DetailPanelContentType;
    data: Record<string, unknown> | null;
  }>({ type: null, data: null });

  // ============ Graph Interaction Handlers ============

  const handleNodeClick = useCallback(
    (nodeType: 'demand' | 'agent' | 'center', id: string) => {
      const ns = negotiationState;
      if (nodeType === 'demand') {
        setDetailPanel({
          type: 'demand',
          data: ns.formulation
            ? {
                raw_intent: ns.formulation.raw_intent,
                formulated_text: ns.formulation.formulated_text,
                enrichments: ns.formulation.enrichments,
              }
            : null,
        });
      } else if (nodeType === 'agent') {
        const agent =
          ns.resonanceAgents.find((a) => a.agent_id === id) ||
          ns.filteredAgents.find((a) => a.agent_id === id);
        const offer = ns.offers.find((o) => o.agent_id === id);
        const planParticipant = ns.plan?.plan_json?.participants?.find(
          (p) => p.agent_id === id,
        );
        const isFiltered = ns.filteredAgents.some((a) => a.agent_id === id);
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
          ns.centerActivities.length > 0
            ? ns.centerActivities[ns.centerActivities.length - 1].round_number
            : 0;
        setDetailPanel({
          type: 'center',
          data: {
            activities: ns.centerActivities,
            roundNumber: currentRound,
          },
        });
      }
    },
    [negotiationState],
  );

  const handleEdgeClick = useCallback(
    (edgeId: string) => {
      const ns = negotiationState;
      if (edgeId.startsWith('res_')) {
        const agentId = edgeId.replace('res_', '');
        const agent =
          ns.resonanceAgents.find((a) => a.agent_id === agentId) ||
          ns.filteredAgents.find((a) => a.agent_id === agentId);
        setDetailPanel({
          type: 'resonance_edge',
          data: {
            agent_id: agentId,
            display_name: agent?.display_name || agentId,
            resonance_score: agent?.resonance_score || 0,
          },
        });
      } else if (edgeId.startsWith('int_')) {
        const match = edgeId.match(/^int_(\d+)/);
        if (!match) return;
        const activityIdx = parseInt(match[1], 10);
        const activity = ns.centerActivities[activityIdx];
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
    },
    [negotiationState],
  );

  const handleTaskClick = useCallback(
    (taskId: string) => {
      const task = negotiationState.plan?.plan_json?.tasks?.find(
        (t) => t.id === taskId,
      );
      if (task) {
        setDetailPanel({
          type: 'task',
          data: task as unknown as Record<string, unknown>,
        });
      }
    },
    [negotiationState],
  );

  const handleCloseDetail = useCallback(() => {
    setDetailPanel({ type: null, data: null });
  }, []);

  if (phase === 'idle') return null;

  return (
    <div
      style={{
        padding: '20px',
        borderRadius: 12,
        border: '1px solid rgba(0,0,0,0.06)',
        backgroundColor: '#fff',
      }}
    >
      {/* Header with view toggle */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>协商进度</span>
          <span
            style={{
              fontSize: 12,
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor:
                phase === 'completed' ? '#D4F4DD'
                : phase === 'error' ? '#FFE4E4'
                : '#FFF4E0',
              color:
                phase === 'completed' ? '#2D7A3F'
                : phase === 'error' ? '#CC3333'
                : '#B8860B',
            }}
          >
            {PHASE_LABELS[phase] || phase}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <ViewTab label="图谱" isActive={view === 'graph'} onClick={() => setView('graph')} />
          <ViewTab label="时间线" isActive={view === 'timeline'} onClick={() => setView('timeline')} />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            padding: '8px 12px',
            borderRadius: 6,
            backgroundColor: '#FFF0F0',
            color: '#CC3333',
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}

      {/* Content */}
      {view === 'timeline' ? (
        <TimelineView timeline={timeline} />
      ) : (
        <div style={{ width: '100%', maxWidth: 800, margin: '0 auto' }}>
          <NegotiationGraph
            state={negotiationState}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            onTaskClick={handleTaskClick}
          />
        </div>
      )}

      {/* Participants */}
      {participants.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
            参与者 ({participants.length})
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {participants.map((p) => (
              <span
                key={p.agent_id}
                style={{
                  fontSize: 12,
                  padding: '3px 8px',
                  borderRadius: 4,
                  backgroundColor: 'rgba(0,0,0,0.04)',
                  color: '#555',
                }}
              >
                {p.display_name}
                {p.resonance_score > 0 && (
                  <span style={{ color: '#999', marginLeft: 4 }}>
                    {(p.resonance_score * 100).toFixed(0)}%
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Reset */}
      {(phase === 'completed' || phase === 'error') && (
        <button
          onClick={onReset}
          style={{
            marginTop: 12,
            padding: '8px 16px',
            borderRadius: 6,
            border: '1px solid rgba(0,0,0,0.1)',
            backgroundColor: '#fff',
            color: '#333',
            fontSize: 13,
            cursor: 'pointer',
          }}
        >
          重新开始
        </button>
      )}

      {/* Detail Panel (fixed position, slides from right on node click) */}
      <DetailPanel
        type={detailPanel.type}
        data={detailPanel.data}
        onClose={handleCloseDetail}
      />
    </div>
  );
}

function ViewTab({ label, isActive, onClick }: { label: string; isActive: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        fontSize: 12,
        padding: '4px 10px',
        borderRadius: 4,
        border: isActive ? '1px solid #D4B8D9' : '1px solid rgba(0,0,0,0.08)',
        backgroundColor: isActive ? '#D4B8D918' : 'transparent',
        color: isActive ? '#D4B8D9' : '#999',
        cursor: 'pointer',
        fontWeight: isActive ? 600 : 400,
      }}
    >
      {label}
    </button>
  );
}

// ============ Timeline View ============

function TimelineView({ timeline }: { timeline: TimelineEntry[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [timeline.length]);

  if (timeline.length === 0) {
    return (
      <div style={{ fontSize: 13, color: '#999', padding: '16px 0' }}>
        等待事件...
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      style={{
        maxHeight: 300,
        overflowY: 'auto',
        paddingLeft: 16,
      }}
    >
      {timeline.map((entry, i) => (
        <div
          key={i}
          style={{
            display: 'flex',
            gap: 12,
            paddingBottom: 12,
            position: 'relative',
          }}
        >
          {/* Vertical line */}
          {i < timeline.length - 1 && (
            <div
              style={{
                position: 'absolute',
                left: 5,
                top: 16,
                bottom: 0,
                width: 1,
                backgroundColor: 'rgba(0,0,0,0.08)',
              }}
            />
          )}
          {/* Dot */}
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: DOT_COLORS[entry.dotType] || '#ccc',
              marginTop: 4,
              flexShrink: 0,
              position: 'relative',
              zIndex: 1,
            }}
          />
          {/* Content */}
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#333' }}>
              {entry.title}
            </div>
            {entry.detail && (
              <div
                style={{
                  fontSize: 12,
                  color: '#666',
                  marginTop: 2,
                  lineHeight: 1.5,
                  wordBreak: 'break-word',
                }}
              >
                {expandedItems.has(i) && entry.fullDetail ? entry.fullDetail : entry.detail}
                {entry.fullDetail && (
                  <button
                    onClick={() => setExpandedItems(prev => {
                      const next = new Set(prev);
                      if (next.has(i)) next.delete(i); else next.add(i);
                      return next;
                    })}
                    style={{
                      display: 'inline',
                      marginLeft: 4,
                      padding: 0,
                      border: 'none',
                      background: 'none',
                      color: '#D4B8D9',
                      fontSize: 12,
                      cursor: 'pointer',
                      textDecoration: 'underline',
                    }}
                  >
                    {expandedItems.has(i) ? '收起' : '展开全部'}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
