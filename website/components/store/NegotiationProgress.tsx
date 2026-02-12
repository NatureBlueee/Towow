'use client';

import { useState, useRef, useEffect } from 'react';
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
  const [view, setView] = useState<ProgressView>('timeline');

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
          <ViewTab label="时间线" isActive={view === 'timeline'} onClick={() => setView('timeline')} />
          <ViewTab label="图谱" isActive={view === 'graph'} onClick={() => setView('graph')} />
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
        <RadialGraphView graphState={graphState} />
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

// ============ Radial Graph View ============

function RadialGraphView({ graphState }: { graphState: GraphState }) {
  const { agents, centerVisible, done } = graphState;
  const size = 300;
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 40;

  return (
    <div
      style={{
        position: 'relative',
        width: size,
        height: size,
        margin: '0 auto',
      }}
    >
      <style>{`
        @keyframes nodeAppear {
          from { transform: scale(0); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        @keyframes lineGrow {
          from { stroke-dashoffset: 200; }
          to { stroke-dashoffset: 0; }
        }
        @keyframes centerPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(212,184,217,0.4); }
          50% { box-shadow: 0 0 0 8px rgba(212,184,217,0); }
        }
      `}</style>
      {/* SVG lines */}
      <svg
        width={size}
        height={size}
        style={{ position: 'absolute', top: 0, left: 0 }}
      >
        {agents.map((agent, i) => {
          const angle = (2 * Math.PI * i) / agents.length - Math.PI / 2;
          const ax = cx + radius * Math.cos(angle);
          const ay = cy + radius * Math.sin(angle);
          return (
            <line
              key={`line-${agent.id}`}
              x1={cx}
              y1={cy}
              x2={ax}
              y2={ay}
              stroke={agent.active ? '#8FD5A3' : 'rgba(0,0,0,0.08)'}
              strokeWidth={agent.active ? 2 : 1}
              style={{
                strokeDasharray: 200,
                strokeDashoffset: 0,
                animation: `lineGrow 0.5s ease-out ${i * 0.05}s both`,
                transition: 'stroke 0.3s, stroke-width 0.3s',
              }}
            />
          );
        })}
        {/* Center-to-agent lines (when center visible) */}
        {centerVisible && agents.filter((a) => a.active).map((agent, i, arr) => {
          const origIdx = agents.indexOf(agent);
          const angle = (2 * Math.PI * origIdx) / agents.length - Math.PI / 2;
          const ax = cx + radius * Math.cos(angle);
          const ay = cy + radius * Math.sin(angle);
          const centerX = cx + 35;
          const centerY = cy - 35;
          return (
            <line
              key={`center-line-${agent.id}`}
              x1={centerX}
              y1={centerY}
              x2={ax}
              y2={ay}
              stroke="#D4B8D9"
              strokeWidth={1.5}
              strokeDasharray="4 2"
              style={{
                animation: `lineGrow 0.4s ease-out ${i * 0.08}s both`,
              }}
            />
          );
        })}
      </svg>

      {/* Demand node (center) */}
      <div
        style={{
          position: 'absolute',
          left: cx - 28,
          top: cy - 28,
          width: 56,
          height: 56,
          borderRadius: '50%',
          backgroundColor: done ? '#8FD5A3' : '#D4B8D9',
          color: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
          fontWeight: 600,
          zIndex: 2,
        }}
      >
        {done ? 'Done' : '需求'}
      </div>

      {/* Agent nodes */}
      {agents.map((agent, i) => {
        const angle = (2 * Math.PI * i) / agents.length - Math.PI / 2;
        const ax = cx + radius * Math.cos(angle);
        const ay = cy + radius * Math.sin(angle);
        const label = agent.name.length > 8 ? agent.name.substring(0, 7) + '..' : agent.name;
        return (
          <div
            key={agent.id}
            title={agent.name}
            style={{
              position: 'absolute',
              left: ax - 22,
              top: ay - 22,
              width: 44,
              height: 44,
              borderRadius: '50%',
              backgroundColor: agent.active ? '#F9A87C' : 'rgba(0,0,0,0.06)',
              color: agent.active ? '#fff' : '#999',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 11,
              fontWeight: 500,
              zIndex: 2,
              transition: 'background-color 0.3s, color 0.3s',
              animation: `nodeAppear 0.3s ease-out ${i * 0.05}s both`,
            }}
          >
            {label}
          </div>
        );
      })}

      {/* Center coordinator node */}
      {centerVisible && (
        <div
          style={{
            position: 'absolute',
            left: cx + 35 - 20,
            top: cy - 35 - 20,
            width: 40,
            height: 40,
            borderRadius: '50%',
            backgroundColor: '#D4B8D9',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 10,
            fontWeight: 600,
            zIndex: 2,
            border: '2px solid #fff',
            animation: 'nodeAppear 0.3s ease-out, centerPulse 2s ease-in-out infinite 0.3s',
          }}
        >
          Center
        </div>
      )}
    </div>
  );
}
