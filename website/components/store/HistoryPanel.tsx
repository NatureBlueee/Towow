'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { getHistory, getHistoryDetail } from '@/lib/store-api';
import type { HistoryItem, HistoryDetail } from '@/lib/store-api';
import { SCENES } from '@/lib/store-scenes';

interface HistoryPanelProps {
  isAuthenticated: boolean;
  /** When this transitions to 'completed', history auto-refreshes. */
  negotiationPhase?: string;
}

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  pending: '进行中',
  negotiating: '协商中',
  completed: '已完成',
  failed: '失败',
};

const STATUS_COLORS: Record<string, string> = {
  draft: '#B8B8B8',
  pending: '#F9A87C',
  negotiating: '#F9A87C',
  completed: '#8FD5A3',
  failed: '#E57373',
};

const MODE_LABELS: Record<string, string> = {
  manual: '手动输入',
  surprise: '通向惊喜',
  polish: '分身润色',
};

function formatTime(iso: string | null): string {
  if (!iso) return '';
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin} 分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} 小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay} 天前`;
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + '…';
}

function getSceneLabel(sceneId: string | null): { name: string; color: string } | null {
  if (!sceneId) return null;
  const scene = SCENES[sceneId];
  if (!scene) return { name: sceneId, color: '#B8B8B8' };
  return { name: scene.name, color: scene.primary };
}

/** Extract a one-line summary from plan_json when plan_output is missing. */
function planJsonSummary(planJson: Record<string, unknown> | null): string | null {
  if (!planJson) return null;
  const summary = planJson.summary as string | undefined;
  if (summary) return summary;
  const participants = planJson.participants as Array<{ display_name?: string }> | undefined;
  if (participants?.length) {
    return `${participants.length} 位参与者协作方案`;
  }
  return '方案已生成';
}

export function HistoryPanel({ isAuthenticated, negotiationPhase }: HistoryPanelProps) {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<HistoryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const prevPhaseRef = useRef(negotiationPhase);

  // Fetch ALL history (no scene filter)
  const fetchHistory = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      const data = await getHistory();
      setItems(data);
    } catch {
      // 401 or network error — silently ignore
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  // Initial load
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Auto-refresh when negotiation completes
  useEffect(() => {
    if (prevPhaseRef.current !== 'completed' && negotiationPhase === 'completed') {
      // Small delay to let DB write finish
      const timer = setTimeout(fetchHistory, 1500);
      return () => clearTimeout(timer);
    }
    prevPhaseRef.current = negotiationPhase;
  }, [negotiationPhase, fetchHistory]);

  const handleExpand = async (negId: string) => {
    if (expandedId === negId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(negId);
    setDetailLoading(true);
    try {
      const d = await getHistoryDetail(negId);
      setDetail(d);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  // Not authenticated — don't show
  if (!isAuthenticated) {
    return null;
  }

  return (
    <div style={{ padding: '8px 24px 16px' }}>
      {/* Header row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 10,
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: '#999',
            letterSpacing: 1,
          }}
        >
          MY HISTORY
        </div>
        {items.length > 0 && (
          <span style={{ fontSize: 12, color: '#CCC' }}>
            {items.length} 条记录
          </span>
        )}
      </div>

      <div
        style={{
          background: '#FFFFFF',
          borderRadius: 12,
          border: '1px solid #E8E4E0',
          overflow: 'hidden',
        }}
      >
        {/* Loading state */}
        {loading && items.length === 0 && (
          <div style={{ padding: '20px 16px', textAlign: 'center', color: '#B8B8B8', fontSize: 13 }}>
            加载历史记录...
          </div>
        )}

        {/* Empty state */}
        {!loading && items.length === 0 && (
          <div style={{ padding: '24px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 14, color: '#999', marginBottom: 4 }}>
              还没有历史记录
            </div>
            <div style={{ fontSize: 12, color: '#CCC' }}>
              提交需求后，你的协商记录会保存在这里
            </div>
          </div>
        )}

        {/* History list */}
        {items.map((item, idx) => (
          <div key={item.negotiation_id}>
            {idx > 0 && (
              <div style={{ height: 1, background: '#F0ECE8', margin: '0 16px' }} />
            )}

            {/* Summary row */}
            <button
              onClick={() => handleExpand(item.negotiation_id)}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 12,
                width: '100%',
                padding: '12px 16px',
                background: expandedId === item.negotiation_id ? '#FAFAF8' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background 0.15s',
              }}
            >
              {/* Status dot */}
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: STATUS_COLORS[item.status] || '#B8B8B8',
                  marginTop: 6,
                  flexShrink: 0,
                }}
              />

              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 14,
                    color: '#1A1A1A',
                    lineHeight: 1.4,
                    marginBottom: 4,
                  }}
                >
                  {truncate(item.demand_text || item.assist_output || '(无内容)', 80)}
                </div>
                <div
                  style={{
                    display: 'flex',
                    gap: 8,
                    alignItems: 'center',
                    flexWrap: 'wrap',
                  }}
                >
                  {/* Scene badge */}
                  {(() => {
                    const scene = getSceneLabel(item.scene_id);
                    if (!scene) return null;
                    return (
                      <span
                        style={{
                          fontSize: 11,
                          color: scene.color,
                          fontWeight: 600,
                          background: `${scene.color}18`,
                          padding: '1px 6px',
                          borderRadius: 4,
                        }}
                      >
                        {scene.name}
                      </span>
                    );
                  })()}
                  <span
                    style={{
                      fontSize: 11,
                      color: STATUS_COLORS[item.status] || '#999',
                      fontWeight: 500,
                    }}
                  >
                    {STATUS_LABELS[item.status] || item.status}
                  </span>
                  <span style={{ fontSize: 11, color: '#B8B8B8' }}>
                    {MODE_LABELS[item.demand_mode] || item.demand_mode}
                  </span>
                  {item.agent_count > 0 && (
                    <span style={{ fontSize: 11, color: '#B8B8B8' }}>
                      {item.agent_count} agents
                    </span>
                  )}
                  <span style={{ fontSize: 11, color: '#CCC' }}>
                    {formatTime(item.created_at)}
                  </span>
                </div>
              </div>

              {/* Expand indicator */}
              <div
                style={{
                  fontSize: 12,
                  color: '#CCC',
                  marginTop: 4,
                  transform: expandedId === item.negotiation_id ? 'rotate(90deg)' : 'none',
                  transition: 'transform 0.15s',
                }}
              >
                ›
              </div>
            </button>

            {/* Detail panel */}
            {expandedId === item.negotiation_id && (
              <div style={{ padding: '0 16px 12px 36px' }}>
                {detailLoading ? (
                  <div style={{ fontSize: 13, color: '#999', padding: '8px 0' }}>
                    加载中...
                  </div>
                ) : detail ? (
                  <div style={{ fontSize: 13, color: '#555', lineHeight: 1.6 }}>
                    {/* Assist output */}
                    {detail.assist_output && (
                      <div style={{ marginBottom: 10 }}>
                        <div style={{ fontWeight: 600, color: '#999', fontSize: 11, marginBottom: 4 }}>
                          分身输出
                        </div>
                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                          {detail.assist_output}
                        </div>
                      </div>
                    )}

                    {/* Formulated text */}
                    {detail.formulated_text && (
                      <div style={{ marginBottom: 10 }}>
                        <div style={{ fontWeight: 600, color: '#999', fontSize: 11, marginBottom: 4 }}>
                          丰富化需求
                        </div>
                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                          {detail.formulated_text}
                        </div>
                      </div>
                    )}

                    {/* Plan output — with plan_json fallback */}
                    {(detail.plan_output || detail.plan_json) && (
                      <div style={{ marginBottom: 10 }}>
                        <div style={{ fontWeight: 600, color: '#999', fontSize: 11, marginBottom: 4 }}>
                          方案
                        </div>
                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                          {detail.plan_output || planJsonSummary(detail.plan_json)}
                        </div>
                      </div>
                    )}

                    {/* Offers */}
                    {detail.offers.length > 0 && (
                      <div>
                        <div style={{ fontWeight: 600, color: '#999', fontSize: 11, marginBottom: 6 }}>
                          参与者响应 ({detail.offers.length})
                        </div>
                        {detail.offers.map((offer, oi) => (
                          <div
                            key={oi}
                            style={{
                              padding: '8px 12px',
                              marginBottom: 6,
                              background: '#F8F6F3',
                              borderRadius: 8,
                              fontSize: 13,
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                              <span style={{ fontWeight: 600, color: '#1A1A1A' }}>
                                {offer.agent_name || offer.agent_id}
                              </span>
                              <span style={{ color: '#8FD5A3', fontWeight: 600 }}>
                                {(offer.resonance_score * 100).toFixed(0)}%
                              </span>
                            </div>
                            {offer.offer_text && (
                              <div style={{ color: '#555', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                                {offer.offer_text}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Empty state for pending/draft */}
                    {!detail.plan_output && !detail.plan_json && !detail.assist_output && detail.offers.length === 0 && (
                      <div style={{ color: '#B8B8B8', fontSize: 12 }}>
                        协商尚未完成，暂无详情
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: '#E57373', padding: '8px 0' }}>
                    加载失败
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
