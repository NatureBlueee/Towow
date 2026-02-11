'use client';

import type { StoreParticipant } from '@/lib/store-api';
import { TopologyView, type TopologyViewProps } from './TopologyView';

interface PlanOutputProps {
  planText: string | null;
  planJson?: Record<string, unknown> | null;
  participants: StoreParticipant[];
  planTemplate?: 'team' | 'default';
}

/** Type-guard: check if planJson has the shape needed for TopologyView */
function isTopologyPlan(
  json: Record<string, unknown> | null | undefined,
): json is TopologyViewProps['planJson'] {
  if (!json) return false;
  const tasks = json.tasks;
  return Array.isArray(tasks) && tasks.length > 0 && Array.isArray(json.participants);
}

const SOURCE_COLORS: Record<string, string> = {
  secondme: '#F9A87C',
  json_file: '#C4A0CA',
};

export function PlanOutput({ planText, planJson, participants, planTemplate = 'default' }: PlanOutputProps) {
  if (!planText && !planJson) return null;

  return (
    <div
      style={{
        padding: '20px',
        borderRadius: 12,
        border: '1px solid rgba(0,0,0,0.06)',
        backgroundColor: '#fff',
      }}
    >
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
        协商方案
      </div>

      {/* Team lineup (hackathon template) or default participants */}
      {planTemplate === 'team' && participants.length > 0 ? (
        <TeamLineup participants={participants} />
      ) : (
        participants.length > 0 && (
          <ParticipantTags participants={participants} />
        )
      )}

      {/* Topology view or plain text fallback */}
      {isTopologyPlan(planJson) ? (
        <TopologyView planJson={planJson} />
      ) : (
        planText && (
          <div
            style={{
              padding: '16px',
              borderRadius: 8,
              backgroundColor: '#F8F6F3',
              fontSize: 14,
              lineHeight: 1.7,
              whiteSpace: 'pre-wrap',
            }}
          >
            {planText}
          </div>
        )
      )}
    </div>
  );
}

// ============ Default participant tags ============

function ParticipantTags({ participants }: { participants: StoreParticipant[] }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
        参与成员
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {participants.map((p) => {
          const sourceColor = p.source
            ? SOURCE_COLORS[p.source] || '#8FD5A3'
            : undefined;
          return (
            <div
              key={p.agent_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 6,
                backgroundColor: 'rgba(0,0,0,0.03)',
                fontSize: 13,
              }}
            >
              <span style={{ fontWeight: 500 }}>{p.display_name}</span>
              {p.source && (
                <span style={{ fontSize: 11, color: sourceColor, fontWeight: 500 }}>
                  {p.source}
                </span>
              )}
              {p.resonance_score > 0 && (
                <span style={{ fontSize: 11, color: '#999', fontFamily: 'monospace' }}>
                  {p.resonance_score.toFixed(3)}
                </span>
              )}
              {p.offer_content && (
                <span style={{ color: '#999', fontSize: 11 }}>已提案</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============ Hackathon team lineup ============
// Renders participants as a visual team roster with roles and contributions

function TeamLineup({ participants }: { participants: StoreParticipant[] }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
        团队阵容
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: 10,
        }}
      >
        {participants.map((p, i) => {
          const sourceColor = p.source
            ? SOURCE_COLORS[p.source] || '#8FD5A3'
            : '#8FD5A3';
          const initial = p.display_name.charAt(0).toUpperCase();
          const roleColors = ['#F9A87C', '#8FD5A3', '#D4B8D9', '#FFE4B5', '#B8D4E3'];
          const roleColor = roleColors[i % roleColors.length];

          return (
            <div
              key={p.agent_id}
              style={{
                padding: '12px',
                borderRadius: 10,
                border: '1px solid rgba(0,0,0,0.06)',
                backgroundColor: '#fff',
                borderLeft: `3px solid ${roleColor}`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    backgroundColor: roleColor,
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 14,
                    fontWeight: 600,
                    flexShrink: 0,
                  }}
                >
                  {initial}
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{p.display_name}</div>
                  <div style={{ fontSize: 11, color: sourceColor, fontWeight: 500 }}>
                    {p.source || 'agent'}
                  </div>
                </div>
              </div>

              {/* Resonance score as a compact bar */}
              {p.resonance_score > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <div
                    style={{
                      flex: 1,
                      height: 4,
                      borderRadius: 2,
                      backgroundColor: 'rgba(0,0,0,0.06)',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min(p.resonance_score * 100, 100)}%`,
                        height: '100%',
                        backgroundColor: roleColor,
                        borderRadius: 2,
                      }}
                    />
                  </div>
                  <span style={{ fontSize: 10, color: '#999', fontFamily: 'monospace' }}>
                    {(p.resonance_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}

              {/* Offer excerpt */}
              {p.offer_content && (
                <div
                  style={{
                    fontSize: 12,
                    color: '#666',
                    lineHeight: 1.4,
                    overflow: 'hidden',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                  }}
                >
                  {p.offer_content}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
