import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  UserOutlined,
  InfoCircleOutlined,
  HistoryOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { Tooltip } from 'antd';
import type { Candidate, TimelineEvent, CandidateDecision, CandidateResponse } from '../../types';
import CandidateStatusBadge, { getCandidateStatusConfig } from './CandidateStatusBadge';
import { formatRelativeTime } from '../../utils/format';

interface CandidateListProps {
  candidates: Candidate[];
  events: TimelineEvent[];
}

interface CandidateWithMeta extends Candidate {
  // 计算后的响应信息
  computedResponse?: CandidateResponse;
  // 是否是新加入的候选人（用于动画）
  isNew?: boolean;
  // 是否正在退出（用于动画）
  isLeaving?: boolean;
  // 历史事件（按时间排序）
  history: HistoryItem[];
}

interface HistoryItem {
  timestamp: string;
  event_type: string;
  description: string;
  reason?: string;
}

// Skeleton for loading state
const CandidateListSkeleton: React.FC = () => (
  <div className="card">
    <div className="flex items-center justify-between mb-4">
      <div className="skeleton h-5 w-20 rounded" />
      <div className="skeleton h-5 w-8 rounded-full" />
    </div>
    <div className="space-y-3 stagger-children">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="p-3 rounded-xl bg-[var(--color-bg-subtle)]">
          <div className="flex items-start gap-3">
            <div className="skeleton w-10 h-10 rounded-full flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-2">
                <div className="skeleton h-4 w-24 rounded" />
                <div className="skeleton h-5 w-12 rounded-full" />
              </div>
              <div className="skeleton h-3 w-full rounded" />
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

/**
 * 获取事件描述
 */
function getEventDescription(eventType: string, metadata?: Record<string, unknown>): string {
  switch (eventType) {
    case 'towow.filter.completed':
      return '被筛选为候选人';
    case 'towow.offer.submitted':
      const decision = metadata?.decision as string;
      if (decision === 'participate') return '同意参与协商';
      if (decision === 'decline') return '拒绝参与协商';
      if (decision === 'conditional') return '有条件参与';
      return '提交了响应';
    case 'towow.agent.withdrawn':
      return '主动退出协商';
    case 'towow.agent.kicked':
      const kickedBy = metadata?.kicked_by as string;
      return kickedBy ? `被 ${kickedBy} 踢出` : '被踢出协商';
    case 'towow.negotiation.bargain':
      const bargainType = metadata?.bargain_type as string;
      if (bargainType === 'role_change') return '提出角色变更';
      if (bargainType === 'condition') return '提出新条件';
      if (bargainType === 'objection') return '提出异议';
      return '发起讨价还价';
    case 'towow.proposal.feedback':
      const feedback = metadata?.feedback as string;
      if (feedback === 'accept') return '接受方案';
      if (feedback === 'reject') return '拒绝方案';
      if (feedback === 'counter') return '提出反提案';
      return '反馈了方案';
    default:
      return eventType;
  }
}

/**
 * 悬停详情面板组件
 */
const DetailPanel: React.FC<{
  candidate: CandidateWithMeta;
  onClose: () => void;
}> = ({ candidate, onClose }) => {
  const response = candidate.computedResponse;
  const config = getCandidateStatusConfig(response?.decision);

  // 获取原因文本
  const getReasonText = (): string | null => {
    if (!response) return null;
    if (response.decline_reason) return response.decline_reason;
    if (response.withdrawn_reason) return response.withdrawn_reason;
    if (response.kicked_reason) return response.kicked_reason;
    return null;
  };

  const reasonText = getReasonText();

  return (
    <div
      className="absolute left-0 right-0 top-full mt-2 z-10 animate-fade-in-up"
      style={{ animationDuration: '150ms' }}
    >
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-lg p-4">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-[var(--color-text)]">详细信息</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            className="p-1 rounded-md hover:bg-[var(--color-bg-muted)] transition-colors"
          >
            <CloseOutlined className="text-[var(--color-text-muted)] text-xs" />
          </button>
        </div>

        {/* 原因展示 */}
        {reasonText && (
          <div className="mb-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <InfoCircleOutlined style={{ color: config.color, fontSize: '12px' }} />
              <span className="text-xs text-[var(--color-text-tertiary)]">
                {response?.decision === 'decline' && '拒绝原因'}
                {response?.decision === 'withdrawn' && '退出原因'}
                {response?.decision === 'kicked' && '踢出原因'}
              </span>
            </div>
            <p className="text-sm text-[var(--color-text-secondary)] bg-[var(--color-bg-subtle)] rounded-lg p-3">
              "{reasonText}"
            </p>
          </div>
        )}

        {/* 被踢出者信息 */}
        {response?.kicked_by && (
          <div className="mb-3 text-xs text-[var(--color-text-muted)]">
            操作者: {response.kicked_by}
          </div>
        )}

        {/* 时间戳 */}
        {(response?.responded_at || response?.withdrawn_at || response?.kicked_at) && (
          <div className="text-xs text-[var(--color-text-muted)]">
            时间: {formatRelativeTime(response.responded_at || response.withdrawn_at || response.kicked_at || '')}
          </div>
        )}

        {/* 历史记录 */}
        {candidate.history.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
            <div className="flex items-center gap-1.5 mb-2">
              <HistoryOutlined className="text-[var(--color-text-muted)] text-xs" />
              <span className="text-xs text-[var(--color-text-tertiary)]">历史记录</span>
            </div>
            <div className="space-y-2 max-h-32 overflow-y-auto custom-scrollbar">
              {candidate.history.slice(0, 5).map((item, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs">
                  <span className="text-[var(--color-text-muted)] whitespace-nowrap">
                    {formatRelativeTime(item.timestamp)}
                  </span>
                  <span className="text-[var(--color-text-secondary)]">
                    {item.description}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * 单个候选人卡片组件
 */
const CandidateCard: React.FC<{
  candidate: CandidateWithMeta;
  formatAgentName: (agentId: string) => string;
}> = ({ candidate, formatAgentName }) => {
  const [showDetail, setShowDetail] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const response = candidate.computedResponse;
  const decision = response?.decision;
  const config = getCandidateStatusConfig(decision);

  // 是否有原因需要显示
  const hasReason = !!(
    response?.decline_reason ||
    response?.withdrawn_reason ||
    response?.kicked_reason
  );

  // 获取简短的原因预览
  const getReasonPreview = (): string | null => {
    const reason = response?.decline_reason || response?.withdrawn_reason || response?.kicked_reason;
    if (!reason) return null;
    return reason.length > 30 ? reason.substring(0, 30) + '...' : reason;
  };

  // 点击外部关闭详情面板
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (cardRef.current && !cardRef.current.contains(event.target as Node)) {
        setShowDetail(false);
      }
    };

    if (showDetail) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showDetail]);

  // 动画类名
  const animationClass = candidate.isNew
    ? 'animate-slide-in-left'
    : candidate.isLeaving
      ? 'animate-fade-out'
      : '';

  return (
    <div
      ref={cardRef}
      className={`
        relative p-3 rounded-xl border-2 transition-all duration-300
        hover:shadow-md cursor-pointer
        ${animationClass}
      `}
      style={{
        borderColor: config.borderColor,
        backgroundColor: config.bgColor,
      }}
      onClick={() => {
        if (hasReason || candidate.history.length > 0) {
          setShowDetail(!showDetail);
        }
      }}
    >
      <div className="flex items-start gap-3">
        {/* 头像 */}
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-transform duration-200 hover:scale-105"
          style={{ backgroundColor: config.avatarBg }}
        >
          <UserOutlined className="text-white text-sm" />
        </div>

        {/* 内容 */}
        <div className="flex-1 min-w-0">
          {/* 名称 & 状态 */}
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="font-medium text-[var(--color-text)] truncate">
              {formatAgentName(candidate.agent_id)}
            </span>
            <CandidateStatusBadge decision={decision} size="md" />
          </div>

          {/* 推荐理由 */}
          <p className="text-xs text-[var(--color-text-tertiary)] mb-2 line-clamp-2">
            {candidate.reason}
          </p>

          {/* 拒绝/退出原因预览 */}
          {hasReason && (
            <Tooltip title="点击查看详情">
              <div
                className="mt-2 p-2 rounded-lg border-l-2 transition-colors hover:bg-[var(--color-bg-muted)]"
                style={{
                  backgroundColor: 'var(--color-bg-elevated)',
                  borderLeftColor: config.color,
                }}
              >
                <div className="flex items-start gap-1.5">
                  <InfoCircleOutlined
                    className="flex-shrink-0 mt-0.5"
                    style={{ color: config.color, fontSize: '12px' }}
                  />
                  <p className="text-xs text-[var(--color-text-secondary)] italic">
                    "{getReasonPreview()}"
                  </p>
                </div>
              </div>
            </Tooltip>
          )}

          {/* 贡献说明 */}
          {response?.contribution && (
            <div className="mt-2 p-2 rounded-lg bg-[var(--color-bg-elevated)] border-l-2 border-[var(--color-primary)]">
              <p className="text-xs text-[var(--color-text-secondary)] italic">
                "{response.contribution}"
              </p>
            </div>
          )}

          {/* 条件列表 */}
          {response?.conditions && response.conditions.length > 0 && (
            <div className="mt-2">
              <span className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">
                条件
              </span>
              <div className="flex flex-wrap gap-1 mt-1">
                {response.conditions.map((condition, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 text-[10px] rounded-full bg-[var(--color-bg-muted)] text-[var(--color-text-secondary)]"
                  >
                    {condition}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 历史记录指示器 */}
          {candidate.history.length > 1 && (
            <div className="mt-2 flex items-center gap-1 text-[10px] text-[var(--color-text-muted)]">
              <HistoryOutlined />
              <span>{candidate.history.length} 条历史记录</span>
            </div>
          )}
        </div>
      </div>

      {/* 详情面板 */}
      {showDetail && (
        <DetailPanel
          candidate={candidate}
          onClose={() => setShowDetail(false)}
        />
      )}
    </div>
  );
};

/**
 * 候选人列表组件
 * 展示所有候选人及其状态，支持状态变更动画和详情展示
 */
const CandidateList: React.FC<CandidateListProps> = ({ candidates, events }) => {
  // 记录之前的候选人列表，用于检测新增和离开
  const prevCandidatesRef = useRef<Set<string>>(new Set());
  const [newCandidates, setNewCandidates] = useState<Set<string>>(new Set());

  // 处理候选人数据，附加计算后的响应和历史
  const candidatesWithMeta: CandidateWithMeta[] = useMemo(() => {
    return candidates.map((candidate) => {
      // 从事件中提取该候选人的响应
      const computedResponse = extractResponseFromEvents(candidate.agent_id, events);

      // 提取历史记录
      const history = extractHistoryFromEvents(candidate.agent_id, events);

      // 合并原有响应和计算的响应
      const finalResponse = candidate.response || computedResponse;

      return {
        ...candidate,
        computedResponse: finalResponse,
        isNew: newCandidates.has(candidate.agent_id),
        history,
      };
    });
  }, [candidates, events, newCandidates]);

  // 检测新增候选人
  useEffect(() => {
    const currentIds = new Set(candidates.map(c => c.agent_id));
    const prevIds = prevCandidatesRef.current;

    const newIds = new Set<string>();
    currentIds.forEach(id => {
      if (!prevIds.has(id)) {
        newIds.add(id);
      }
    });

    if (newIds.size > 0) {
      setNewCandidates(newIds);
      // 300ms 后清除新增标记
      setTimeout(() => {
        setNewCandidates(new Set());
      }, 300);
    }

    prevCandidatesRef.current = currentIds;
  }, [candidates]);

  /**
   * 从事件中提取候选人响应
   */
  function extractResponseFromEvents(agentId: string, events: TimelineEvent[]): CandidateResponse | undefined {
    // 按时间倒序，找最新的状态
    const relevantEvents = events
      .filter(e => e.agent_id === agentId)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    for (const event of relevantEvents) {
      const metadata = event.metadata as Record<string, unknown> | undefined;

      // 被踢出
      if (event.event_type === 'towow.agent.kicked') {
        return {
          decision: 'kicked',
          kicked_reason: metadata?.reason as string,
          kicked_by: metadata?.kicked_by as string,
          kicked_at: event.timestamp,
        };
      }

      // 主动退出
      if (event.event_type === 'towow.agent.withdrawn') {
        return {
          decision: 'withdrawn',
          withdrawn_reason: metadata?.reason as string,
          withdrawn_at: event.timestamp,
        };
      }

      // 提交响应
      if (event.event_type === 'towow.offer.submitted' || event.event_type === 'agent_proposal') {
        if (metadata?.decision) {
          return {
            decision: metadata.decision as CandidateDecision,
            contribution: metadata.contribution as string | undefined,
            conditions: metadata.conditions as string[] | undefined,
            decline_reason: metadata.decline_reason as string | undefined,
            responded_at: event.timestamp,
          };
        }
      }
    }

    return undefined;
  }

  /**
   * 从事件中提取候选人历史
   */
  function extractHistoryFromEvents(agentId: string, events: TimelineEvent[]): HistoryItem[] {
    return events
      .filter(e => e.agent_id === agentId)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .map(e => ({
        timestamp: e.timestamp,
        event_type: e.event_type,
        description: getEventDescription(e.event_type, e.metadata),
        reason: (e.metadata as Record<string, unknown>)?.reason as string | undefined,
      }));
  }

  const formatAgentName = (agentId: string) => {
    return agentId.replace('user_agent_', '').replace(/_/g, ' ').toUpperCase();
  };

  // 统计各状态数量
  const statusCounts = useMemo(() => {
    const counts = {
      participate: 0,
      decline: 0,
      conditional: 0,
      withdrawn: 0,
      kicked: 0,
      pending: 0,
    };

    candidatesWithMeta.forEach(c => {
      const decision = c.computedResponse?.decision;
      if (decision && decision in counts) {
        counts[decision as keyof typeof counts]++;
      } else {
        counts.pending++;
      }
    });

    return counts;
  }, [candidatesWithMeta]);

  return (
    <div className="card h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-[var(--color-text)]">候选人</h3>
        <div className="flex items-center gap-2">
          {/* 状态统计 */}
          {statusCounts.participate > 0 && (
            <Tooltip title="已接受">
              <span className="tag tag-success text-[10px]">{statusCounts.participate}</span>
            </Tooltip>
          )}
          {statusCounts.decline > 0 && (
            <Tooltip title="已拒绝">
              <span className="tag tag-error text-[10px]">{statusCounts.decline}</span>
            </Tooltip>
          )}
          {statusCounts.withdrawn > 0 && (
            <Tooltip title="已退出">
              <span className="tag tag-default text-[10px]">{statusCounts.withdrawn}</span>
            </Tooltip>
          )}
          {statusCounts.pending > 0 && (
            <Tooltip title="待响应">
              <span className="tag tag-info text-[10px]">{statusCounts.pending}</span>
            </Tooltip>
          )}
          <span className="tag tag-primary">{candidates.length}</span>
        </div>
      </div>

      {/* Content */}
      {candidates.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-12 h-12 rounded-full bg-[var(--color-bg-muted)] flex items-center justify-center mb-3">
            <UserOutlined className="text-[var(--color-text-muted)] text-xl" />
          </div>
          <p className="text-sm text-[var(--color-text-tertiary)]">等待候选人...</p>
          <div className="mt-3 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse" />
            <span
              className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse"
              style={{ animationDelay: '0.2s' }}
            />
            <span
              className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse"
              style={{ animationDelay: '0.4s' }}
            />
          </div>
        </div>
      ) : (
        <div className="space-y-3 stagger-children">
          {candidatesWithMeta.map((candidate) => (
            <CandidateCard
              key={candidate.agent_id}
              candidate={candidate}
              formatAgentName={formatAgentName}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default CandidateList;
export { CandidateListSkeleton };
