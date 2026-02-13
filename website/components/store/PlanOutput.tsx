'use client';

import { useState, useCallback, useEffect } from 'react';
import type { StoreParticipant } from '@/lib/store-api';
import type { PlanJson, PlanJsonTask } from '@/types/negotiation';
import type { DetailPanelContentType } from '@/components/negotiation/graph/types';
import { parseOfferContent } from '@/lib/parse-offer-content';
import { PlanView } from '@/components/negotiation/PlanView';
import { DetailPanel } from '@/components/negotiation/DetailPanel';

/** Demo Machine on WOWOK testnet — single source of truth for chain URL */
export const DEMO_CHAIN_URL =
  'https://wowok.net/0x04f7e6667367aed84a90c4622a38b08ea791da625ad68f0ee2ac7fe043f8b370#0';

interface PlanOutputProps {
  planText: string | null;
  planJson?: Record<string, unknown> | null;
  participants: StoreParticipant[];
  planTemplate?: 'team' | 'default';
  chainUrl?: string | null;
}

/**
 * Ensure planJson is always valid for PlanView (ADR-003 compliance).
 *
 * When backend provides plan_json with tasks + prerequisites → use directly.
 * When backend data is missing/empty → construct from participants with
 * fan-out dependencies (first task → all others) to create visible topology edges.
 */
function ensurePlanJson(
  json: Record<string, unknown> | null | undefined,
  participants: StoreParticipant[],
): PlanJson {
  // Backend provided valid plan_json — use it directly
  if (
    json &&
    Array.isArray(json.tasks) &&
    json.tasks.length > 0 &&
    Array.isArray(json.participants)
  ) {
    return json as unknown as PlanJson;
  }

  // Construct plan from participants (last-resort frontend fallback)
  const replied = participants.filter((p) => p.offer_content);
  const allParticipants = replied.length > 0 ? replied : participants;

  const tasks: PlanJsonTask[] = allParticipants.map((p, i) => ({
    id: `task_${i + 1}`,
    title: `${p.display_name} 的贡献`,
    description: parseOfferContent(p.offer_content) || '',
    assignee_id: p.agent_id,
    // Honest fallback: parallel tasks (no fake dependencies)
    // Real dependencies come from LLM via plan_json
    prerequisites: [],
    status: 'pending',
  }));

  return {
    summary: '',
    participants: allParticipants.map((p) => ({
      agent_id: p.agent_id,
      display_name: p.display_name,
      role_in_plan: '参与者',
    })),
    tasks,
  };
}

const SOURCE_COLORS: Record<string, string> = {
  secondme: '#F9A87C',
  json_file: '#C4A0CA',
};

export function PlanOutput({
  planText,
  planJson,
  participants,
  planTemplate = 'default',
  chainUrl,
}: PlanOutputProps) {
  if (!planText && !planJson && participants.length === 0) return null;

  const validPlanJson = ensurePlanJson(planJson, participants);

  // ============ Detail Panel State (ADR-003 共识 6: 侧滑详情) ============

  const [detailPanel, setDetailPanel] = useState<{
    type: DetailPanelContentType;
    data: Record<string, unknown> | null;
  }>({ type: null, data: null });

  const handleTaskClick = useCallback(
    (taskId: string) => {
      const task = validPlanJson.tasks.find((t) => t.id === taskId);
      if (task) {
        setDetailPanel({
          type: 'task',
          data: task as unknown as Record<string, unknown>,
        });
      }
    },
    [validPlanJson.tasks],
  );

  const handleCloseDetail = useCallback(() => {
    setDetailPanel({ type: null, data: null });
  }, []);

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

      {/* PlanView: structured topology with dependency edges (ADR-003 共识 5) */}
      <PlanView
        planText={planText || ''}
        planJson={validPlanJson}
        onTaskClick={handleTaskClick}
      />

      {/* Chain on-chain preview — only when chainUrl is provided */}
      {chainUrl && <ChainPreview url={chainUrl} />}

      {/* DetailPanel: right-sliding task details (ADR-003 共识 6) */}
      <DetailPanel
        type={detailPanel.type}
        data={detailPanel.data}
        onClose={handleCloseDetail}
      />
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

// ============ Chain on-chain preview ============
// Three-state interaction: card → inline iframe → fullscreen
// Key: inline ↔ fullscreen shares ONE iframe (CSS only, no remount)

type ChainViewMode = 'card' | 'inline' | 'fullscreen';

function ChainPreview({ url }: { url: string }) {
  const [mode, setMode] = useState<ChainViewMode>('card');
  const isFullscreen = mode === 'fullscreen';

  // Lock body scroll when fullscreen
  useEffect(() => {
    if (!isFullscreen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [isFullscreen]);

  // Escape key exits fullscreen
  useEffect(() => {
    if (!isFullscreen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMode('inline');
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isFullscreen]);

  // ---- Card mode: compact trigger (no iframe loaded yet) ----
  if (mode === 'card') {
    return (
      <div
        onClick={() => setMode('inline')}
        style={{
          marginTop: 16,
          padding: '14px 18px',
          borderRadius: 10,
          border: '1px solid rgba(0,0,0,0.06)',
          backgroundColor: '#FAFBFC',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#F5F6F8';
          e.currentTarget.style.borderColor = 'rgba(0,0,0,0.12)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = '#FAFBFC';
          e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)';
        }}
      >
        <ChainIcon />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#333' }}>
            链上记录
          </div>
          <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>
            此方案已同步至区块链，点击查看链上内容
          </div>
        </div>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M6 4l4 4-4 4" stroke="#999" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    );
  }

  // ---- inline / fullscreen: single iframe, CSS-only switch ----
  return (
    <div
      style={isFullscreen ? {
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        backgroundColor: '#fff',
        display: 'flex',
        flexDirection: 'column' as const,
      } : {
        marginTop: 16,
      }}
    >
      {/* Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: isFullscreen ? '0 16px' : undefined,
          height: isFullscreen ? 48 : undefined,
          marginBottom: isFullscreen ? 0 : 8,
          borderBottom: isFullscreen ? '1px solid rgba(0,0,0,0.06)' : undefined,
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ChainIcon />
          <span style={{ fontSize: isFullscreen ? 14 : 13, fontWeight: 600, color: '#333' }}>
            链上记录
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {isFullscreen && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '6px 12px',
                borderRadius: 6,
                border: '1px solid rgba(0,0,0,0.08)',
                backgroundColor: '#fff',
                fontSize: 12,
                color: '#666',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <ExternalLinkIcon />
              新窗口打开
            </a>
          )}
          <button
            onClick={() => setMode(isFullscreen ? 'inline' : 'fullscreen')}
            style={{
              padding: isFullscreen ? '6px 12px' : '4px 10px',
              borderRadius: 6,
              border: '1px solid rgba(0,0,0,0.08)',
              backgroundColor: '#fff',
              fontSize: 12,
              color: '#666',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            {isFullscreen ? <CloseIcon /> : <ExpandIcon />}
            {isFullscreen ? '退出全屏' : '全屏'}
          </button>
          {!isFullscreen && (
            <button
              onClick={() => setMode('card')}
              style={{
                padding: '4px 10px',
                borderRadius: 6,
                border: '1px solid rgba(0,0,0,0.08)',
                backgroundColor: '#fff',
                fontSize: 12,
                color: '#666',
                cursor: 'pointer',
              }}
            >
              收起
            </button>
          )}
        </div>
      </div>

      {/* Single iframe — never remounts between inline ↔ fullscreen */}
      <div
        style={isFullscreen ? {
          flex: 1,
          display: 'flex',
        } : {
          borderRadius: 10,
          border: '1px solid rgba(0,0,0,0.08)',
          overflow: 'hidden',
          backgroundColor: '#fff',
        }}
      >
        <iframe
          src={url}
          title="链上记录"
          style={{
            width: '100%',
            height: isFullscreen ? '100%' : 420,
            flex: isFullscreen ? 1 : undefined,
            border: 'none',
            display: 'block',
          }}
          /* No sandbox — wowok.net needs localStorage for Sui wallet/chain state */
        />
      </div>
    </div>
  );
}

// ============ Inline SVG icons ============

function ChainIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path
        d="M7.5 10.5a3 3 0 004.243 0l2.25-2.25a3 3 0 00-4.243-4.243l-1.125 1.125"
        stroke="#8B5CF6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
      />
      <path
        d="M10.5 7.5a3 3 0 00-4.243 0L4.007 9.75a3 3 0 004.243 4.243l1.125-1.125"
        stroke="#8B5CF6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  );
}

function ExpandIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M9 1h4v4M5 13H1V9M13 1L8.5 5.5M1 13l4.5-4.5" stroke="#666" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M11 7.5v4a1.5 1.5 0 01-1.5 1.5h-7A1.5 1.5 0 011 11.5v-7A1.5 1.5 0 012.5 3H6.5M9 1h4v4M5.5 8.5L13 1" stroke="#666" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M1 1l12 12M13 1L1 13" stroke="#666" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
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
                  {parseOfferContent(p.offer_content)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
