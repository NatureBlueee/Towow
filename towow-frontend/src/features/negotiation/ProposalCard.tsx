import React from 'react';
import type { ToWowProposal, NegotiationStatus, ProposalAssignment, ProposalTimeline } from '../../types';

interface ProposalCardProps {
  proposal: ToWowProposal | null;
  status: NegotiationStatus;
  round: number;
}

// Helper function to format timeline for display
const formatTimeline = (timeline: string | ProposalTimeline | undefined): string => {
  if (!timeline) return '';
  if (typeof timeline === 'string') return timeline;

  // Handle object timeline
  const parts: string[] = [];
  if (timeline.start_date) {
    parts.push(`开始: ${timeline.start_date}`);
  }
  if (timeline.end_date) {
    parts.push(`结束: ${timeline.end_date}`);
  }
  if (timeline.milestones && timeline.milestones.length > 0) {
    const milestoneNames = timeline.milestones.map(m => m.name).join('、');
    parts.push(`里程碑: ${milestoneNames}`);
  }
  return parts.join(' | ') || '时间待定';
};

// Helper function to format agent name for display
const formatAgentName = (agentId: string, displayName?: string): string => {
  if (displayName) return displayName;
  return agentId.replace('user_agent_', '').replace(/_/g, ' ').toUpperCase();
};

// Get initials for avatar
const getInitials = (name: string): string => {
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
};

// Get confidence percentage
const getConfidencePercent = (confidence?: string): number => {
  switch (confidence) {
    case 'high': return 90;
    case 'medium': return 60;
    case 'low': return 30;
    default: return 0;
  }
};

// Get confidence label
const getConfidenceLabel = (confidence?: string): string => {
  switch (confidence) {
    case 'high': return '高';
    case 'medium': return '中';
    case 'low': return '低';
    default: return '未知';
  }
};

// Get status indicator styles
const getStatusStyles = (status?: ProposalAssignment['status']): { className: string; label: string } => {
  switch (status) {
    case 'confirmed':
      return { className: 'tag-success', label: '已确认' };
    case 'conditional':
      return { className: 'tag-warning', label: '有条件' };
    case 'pending':
    default:
      return { className: 'tag-default', label: '待确认' };
  }
};

// Get avatar gradient based on index
const getAvatarGradient = (index: number): string => {
  const gradients = [
    'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    'linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%)',
    'linear-gradient(135deg, #ec4899 0%, #f43f5e 100%)',
    'linear-gradient(135deg, #22c55e 0%, #10b981 100%)',
    'linear-gradient(135deg, #f59e0b 0%, #f97316 100%)',
    'linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%)',
  ];
  return gradients[index % gradients.length];
};

// Empty state component
const EmptyState: React.FC<{ isFailed?: boolean }> = ({ isFailed }) => (
  <div className="card card-glass animate-fade-in">
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
      {/* Empty state illustration */}
      <div
        className="w-20 h-20 mb-4 flex items-center justify-center rounded-full"
        style={{
          background: isFailed
            ? 'rgba(239, 68, 68, 0.1)'
            : 'rgba(99, 102, 241, 0.1)'
        }}
      >
        {isFailed ? (
          <svg
            className="w-10 h-10"
            style={{ color: 'var(--color-error)' }}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        ) : (
          <svg
            className="w-10 h-10"
            style={{ color: 'var(--color-primary)' }}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        )}
      </div>

      <h4
        className="text-lg font-semibold mb-2"
        style={{ color: isFailed ? 'var(--color-error)' : 'var(--color-text)' }}
      >
        {isFailed ? '协商失败' : '暂无方案'}
      </h4>

      <p className="text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
        {isFailed
          ? '本次协商未能达成一致，请尝试调整需求后重试'
          : '协作方案正在生成中，请稍候...'
        }
      </p>
    </div>
  </div>
);

// Loading state component
const LoadingState: React.FC = () => (
  <div className="card card-glass animate-fade-in">
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
      {/* Animated loading indicator */}
      <div className="relative w-16 h-16 mb-4">
        <div
          className="absolute inset-0 rounded-full animate-pulse-glow"
          style={{
            background: 'var(--gradient-primary)',
            opacity: 0.2
          }}
        />
        <div
          className="absolute inset-2 rounded-full flex items-center justify-center"
          style={{ background: 'var(--color-card)' }}
        >
          <div
            className="w-6 h-6 rounded-full"
            style={{
              background: 'var(--gradient-primary)',
              animation: 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite'
            }}
          />
        </div>
      </div>

      <h4 className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
        正在生成方案
      </h4>

      <p className="text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
        AI 正在分析各方意见，制定最优协作方案...
      </p>
    </div>
  </div>
);

const ProposalCard: React.FC<ProposalCardProps> = ({ proposal, status, round }) => {
  const isLoading = !proposal && !['finalized', 'failed', 'completed', 'cancelled'].includes(status);
  const isFailed = status === 'failed';
  const isFinalized = status === 'finalized' || status === 'completed';

  // Show loading skeleton
  if (isLoading) {
    return <LoadingState />;
  }

  // Show empty state
  if (!proposal) {
    return <EmptyState isFailed={isFailed} />;
  }

  return (
    <div className={`card card-glass animate-fade-in-up ${isFinalized ? 'ring-2 ring-[var(--color-success)]' : ''}`}>
      {/* Header */}
      <div className="pb-4 mb-4 border-b border-[var(--color-border)]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {isFinalized && (
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(34, 197, 94, 0.1)' }}
              >
                <svg
                  className="w-4 h-4"
                  style={{ color: 'var(--color-success)' }}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
                  />
                </svg>
              </div>
            )}
            <h3
              className="text-lg font-semibold"
              style={{ color: isFinalized ? 'var(--color-success)' : 'var(--color-text)' }}
            >
              {isFinalized ? '最终方案' : '协作方案'}
            </h3>
          </div>

          {round > 0 && (
            <span className="tag tag-primary">
              第 {round} 轮
            </span>
          )}
        </div>

        <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
          {proposal.summary}
        </p>

        {/* Confidence Indicator */}
        {proposal.confidence && (
          <div className="mt-4">
            <div className="flex justify-between text-sm mb-2">
              <span style={{ color: 'var(--color-text-tertiary)' }}>方案信心度</span>
              <span
                className="font-medium"
                style={{
                  color: proposal.confidence === 'high'
                    ? 'var(--color-success)'
                    : proposal.confidence === 'medium'
                    ? 'var(--color-warning)'
                    : 'var(--color-error)'
                }}
              >
                {getConfidenceLabel(proposal.confidence)}
              </span>
            </div>
            <div
              className="h-2 rounded-full overflow-hidden"
              style={{ background: 'var(--color-bg-muted)' }}
            >
              <div
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${getConfidencePercent(proposal.confidence)}%`,
                  background: proposal.confidence === 'high'
                    ? 'linear-gradient(90deg, var(--color-success) 0%, var(--color-success-light) 100%)'
                    : proposal.confidence === 'medium'
                    ? 'linear-gradient(90deg, var(--color-warning) 0%, var(--color-warning-light) 100%)'
                    : 'linear-gradient(90deg, var(--color-error) 0%, var(--color-error-light) 100%)'
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Role Assignments */}
      {proposal.assignments && proposal.assignments.length > 0 && (
        <div className="mb-4">
          <h4
            className="text-sm font-medium mb-3"
            style={{ color: 'var(--color-text)' }}
          >
            角色分配
          </h4>

          <div className="space-y-2 stagger-children">
            {proposal.assignments.map((assignment, idx) => {
              const name = formatAgentName(assignment.agent_id, assignment.display_name);
              const statusStyles = getStatusStyles(assignment.status);

              return (
                <div
                  key={idx}
                  className="flex items-center gap-3 p-3 rounded-lg transition-all duration-200 hover:shadow-sm cursor-default"
                  style={{
                    background: 'var(--color-bg-subtle)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--color-bg-muted)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'var(--color-bg-subtle)';
                  }}
                >
                  {/* Avatar */}
                  <div
                    className="avatar avatar-md flex-shrink-0"
                    style={{
                      background: assignment.avatar
                        ? 'transparent'
                        : getAvatarGradient(idx)
                    }}
                  >
                    {assignment.avatar ? (
                      <img
                        src={assignment.avatar}
                        alt={name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <span>{getInitials(name)}</span>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className="font-medium truncate"
                        style={{ color: 'var(--color-text)' }}
                      >
                        {name}
                      </span>
                      <span className="tag tag-primary text-xs">
                        {assignment.role}
                      </span>
                      {assignment.status && (
                        <span className={`tag ${statusStyles.className} text-xs`}>
                          {statusStyles.label}
                        </span>
                      )}
                    </div>
                    <p
                      className="text-sm mt-1 truncate-2"
                      style={{ color: 'var(--color-text-tertiary)' }}
                    >
                      {assignment.responsibility}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Timeline */}
      {proposal.timeline && (
        <div
          className="flex items-start gap-3 p-3 rounded-lg mb-4"
          style={{ background: 'var(--color-bg-subtle)' }}
        >
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(59, 130, 246, 0.1)' }}
          >
            <svg
              className="w-4 h-4"
              style={{ color: 'var(--color-info)' }}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <span
              className="text-xs font-medium"
              style={{ color: 'var(--color-text-tertiary)' }}
            >
              时间规划
            </span>
            <p
              className="text-sm mt-0.5"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              {formatTimeline(proposal.timeline)}
            </p>
          </div>
        </div>
      )}

      {/* Success Criteria */}
      {proposal.success_criteria && proposal.success_criteria.length > 0 && (
        <div className="pt-4 border-t border-[var(--color-border)]">
          <h4
            className="text-sm font-medium mb-3"
            style={{ color: 'var(--color-text)' }}
          >
            成功标准
          </h4>
          <ul className="space-y-2">
            {proposal.success_criteria.map((criteria, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm"
              >
                <svg
                  className="w-4 h-4 mt-0.5 flex-shrink-0"
                  style={{ color: 'var(--color-success)' }}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                <span style={{ color: 'var(--color-text-secondary)' }}>
                  {criteria}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Finalized Status Banner */}
      {isFinalized && (
        <div
          className="mt-4 flex items-center justify-center gap-2 p-3 rounded-lg"
          style={{
            background: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid rgba(34, 197, 94, 0.2)'
          }}
        >
          <svg
            className="w-5 h-5"
            style={{ color: 'var(--color-success)' }}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span
            className="font-medium"
            style={{ color: 'var(--color-success)' }}
          >
            协商已完成
          </span>
        </div>
      )}
    </div>
  );
};

export default ProposalCard;
