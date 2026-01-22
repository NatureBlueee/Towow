import React, { useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  DisconnectOutlined,
  CheckCircleOutlined,
  TeamOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useEventStore } from '../../stores/eventStore';
import { useSSE } from '../../hooks/useSSE';
import CandidateList from './CandidateList';
import ProposalCard from './ProposalCard';
import EventTimeline from './EventTimeline';
import StatusBadge from './StatusBadge';
import type { SSEEvent } from '../../types';

// Skeleton Components for loading states
const ContentSkeleton: React.FC = () => (
  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
    <div className="lg:col-span-4">
      <div className="card p-4">
        <div className="skeleton h-6 w-24 mb-4 rounded" />
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 mb-4">
            <div className="skeleton w-10 h-10 rounded-full" />
            <div className="flex-1">
              <div className="skeleton h-4 w-24 mb-2 rounded" />
              <div className="skeleton h-3 w-32 rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
    <div className="lg:col-span-4">
      <div className="card card-glass p-4">
        <div className="skeleton h-6 w-24 mb-4 rounded" />
        <div className="skeleton h-24 w-full mb-4 rounded-lg" />
        <div className="skeleton h-16 w-full rounded-lg" />
      </div>
    </div>
    <div className="lg:col-span-4">
      <div className="card p-4">
        <div className="skeleton h-6 w-24 mb-4 rounded" />
        {[...Array(4)].map((_, i) => (
          <div key={i} className="flex items-start gap-3 mb-4">
            <div className="skeleton w-3 h-3 rounded-full mt-1" />
            <div className="flex-1">
              <div className="skeleton h-4 w-28 mb-2 rounded" />
              <div className="skeleton h-3 w-20 rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export const NegotiationPage: React.FC = () => {
  const { negotiationId } = useParams<{ negotiationId: string }>();
  const navigate = useNavigate();

  const {
    status,
    candidates,
    currentProposal,
    currentRound,
    timeline,
    isLoading,
    error,
    setNegotiationId,
    handleSSEEvent,
    reset,
  } = useEventStore();

  // Memoize the event handler to prevent unnecessary reconnections
  const onSSEEvent = useCallback(
    (event: SSEEvent) => {
      handleSSEEvent(event);
    },
    [handleSSEEvent]
  );

  const onSSEError = useCallback((err: Error) => {
    console.error('SSE Error:', err);
  }, []);

  const { isConnected, connect, disconnect, reconnectAttempts } = useSSE(
    negotiationId || null,
    {
      onEvent: onSSEEvent,
      onError: onSSEError,
    }
  );

  useEffect(() => {
    if (negotiationId) {
      setNegotiationId(negotiationId);
    }

    return () => {
      // Clean up on unmount
      reset();
    };
  }, [negotiationId, setNegotiationId, reset]);

  // Calculate statistics
  const participatingCount = candidates.filter(
    (c) => c.response?.decision === 'participate'
  ).length;
  const pendingCount = candidates.filter((c) => !c.response).length;

  const getStatusDescription = () => {
    const descriptions: Record<string, string> = {
      pending: '正在初始化协商...',
      connecting: '正在连接协商网络...',
      filtering: 'AI 正在为您寻找合适的候选人...',
      collecting: '正在收集潜在协作者的响应...',
      aggregating: '正在生成最优协作方案...',
      negotiating: `协商进行中（第 ${currentRound} 轮）`,
      finalized: '协商已完成！您的协作方案已准备就绪。',
      failed: '很遗憾，协商未能达成一致。',
      in_progress: '协商正在进行中...',
      awaiting_user: '等待您的输入以继续...',
      completed: '协商已完成。',
      cancelled: '协商已取消。',
    };
    return descriptions[status] || '处理中...';
  };

  const getProgressPercent = () => {
    const stages: Record<string, number> = {
      pending: 0,
      connecting: 10,
      filtering: 30,
      collecting: 50,
      aggregating: 70,
      negotiating: 80,
      finalized: 100,
      completed: 100,
      failed: 100,
      cancelled: 100,
    };
    return stages[status] || 0;
  };

  const getProgressStatus = (): 'success' | 'error' | 'active' => {
    if (status === 'finalized' || status === 'completed') return 'success';
    if (status === 'failed') return 'error';
    return 'active';
  };

  const progressStatus = getProgressStatus();
  const progressPercent = getProgressPercent();

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      {/* Hero Header with Gradient */}
      <div
        className="relative overflow-hidden"
        style={{
          background: 'var(--gradient-hero)',
        }}
      >
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden">
          <div
            className="absolute -top-1/2 -right-1/4 w-96 h-96 rounded-full opacity-20"
            style={{ background: 'radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%)' }}
          />
          <div
            className="absolute -bottom-1/4 -left-1/4 w-80 h-80 rounded-full opacity-15"
            style={{ background: 'radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%)' }}
          />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Top Navigation */}
          <div className="flex items-center justify-between mb-6 animate-fade-in-down">
            <button
              onClick={() => navigate('/demand')}
              className="btn btn-ghost text-white/90 hover:text-white hover:bg-white/10"
            >
              <ArrowLeftOutlined />
              <span>返回</span>
            </button>

            <div className="flex items-center gap-3">
              <StatusBadge
                status={status}
                isConnected={isConnected}
                reconnectAttempts={reconnectAttempts}
              />
              <button
                onClick={isConnected ? disconnect : connect}
                className="btn btn-sm text-white/90 hover:text-white border border-white/20 hover:border-white/40 hover:bg-white/10"
              >
                {isConnected ? <DisconnectOutlined /> : <ReloadOutlined />}
                <span className="hidden sm:inline">{isConnected ? '断开' : '重连'}</span>
              </button>
            </div>
          </div>

          {/* Main Header Content */}
          <div className="animate-fade-in-up">
            <h1 className="text-white text-2xl sm:text-3xl font-bold mb-2">
              协商进行中
            </h1>
            <p className="text-white/80 text-sm sm:text-base mb-4">
              {getStatusDescription()}
            </p>

            {/* Negotiation ID */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-sm">
              <span className="text-white/60 text-xs">ID:</span>
              <code className="text-white/90 text-xs font-mono">{negotiationId}</code>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mt-6 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
            <div className="flex items-center justify-between text-white/60 text-xs mb-2">
              <span>进度</span>
              <span>{progressPercent}%</span>
            </div>
            <div className="h-2 bg-white/20 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${progressPercent}%`,
                  background: progressStatus === 'success'
                    ? 'var(--color-success)'
                    : progressStatus === 'error'
                    ? 'var(--color-error)'
                    : 'linear-gradient(90deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%)'
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-4 relative z-10">
          <div className="card bg-[var(--color-error-light)]/10 border-[var(--color-error)]/30 animate-fade-in-up">
            <div className="flex items-start gap-3 p-4">
              <div className="w-8 h-8 rounded-full bg-[var(--color-error)]/10 flex items-center justify-center flex-shrink-0">
                <span className="text-[var(--color-error)]">!</span>
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-[var(--color-error)] mb-1">错误</h4>
                <p className="text-sm text-[var(--color-text-secondary)]">{error}</p>
              </div>
              <button
                onClick={connect}
                className="btn btn-sm btn-primary"
              >
                重试
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Statistics Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 stagger-children">
          <div className="card p-4 animate-fade-in-up">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: 'var(--gradient-primary)', opacity: 0.9 }}
              >
                <TeamOutlined className="text-white text-lg" />
              </div>
              <div>
                <div className="text-xs text-[var(--color-text-tertiary)] mb-0.5">候选人</div>
                <div className="text-xl font-semibold text-[var(--color-text)]">{candidates.length}</div>
              </div>
            </div>
          </div>

          <div className="card p-4 animate-fade-in-up">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-[var(--color-success)]/10">
                <CheckCircleOutlined className="text-[var(--color-success)] text-lg" />
              </div>
              <div>
                <div className="text-xs text-[var(--color-text-tertiary)] mb-0.5">愿意参与</div>
                <div className="text-xl font-semibold text-[var(--color-success)]">{participatingCount}</div>
              </div>
            </div>
          </div>

          <div className="card p-4 animate-fade-in-up">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-[var(--color-warning)]/10">
                <ClockCircleOutlined className="text-[var(--color-warning)] text-lg" />
              </div>
              <div>
                <div className="text-xs text-[var(--color-text-tertiary)] mb-0.5">等待响应</div>
                <div className="text-xl font-semibold text-[var(--color-warning)]">{pendingCount}</div>
              </div>
            </div>
          </div>

          <div className="card p-4 animate-fade-in-up">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-[var(--color-secondary)]/10">
                <FileTextOutlined className="text-[var(--color-secondary)] text-lg" />
              </div>
              <div>
                <div className="text-xs text-[var(--color-text-tertiary)] mb-0.5">当前轮次</div>
                <div className="text-xl font-semibold text-[var(--color-text)]">{currentRound}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Three Column Layout */}
        {isLoading ? (
          <ContentSkeleton />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Candidates */}
            <div className="lg:col-span-4 animate-fade-in-up">
              <CandidateList candidates={candidates} events={timeline} />
            </div>

            {/* Center: Proposal */}
            <div className="lg:col-span-4 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
              <ProposalCard
                proposal={currentProposal}
                status={status}
                round={currentRound}
              />
            </div>

            {/* Right: Event Timeline */}
            <div className="lg:col-span-4 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              <EventTimeline events={timeline} maxHeight={500} />
            </div>
          </div>
        )}

        {/* Action Buttons for Finalized State */}
        {status === 'finalized' && currentProposal && (
          <div className="mt-8 animate-fade-in-up">
            <div className="card card-glass p-8 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-success)]/10 flex items-center justify-center">
                <CheckCircleOutlined className="text-[var(--color-success)] text-3xl" />
              </div>
              <h3 className="text-xl font-semibold text-[var(--color-text)] mb-2">
                协商完成！
              </h3>
              <p className="text-[var(--color-text-secondary)] mb-6 max-w-md mx-auto">
                您的协作方案已最终确定。您现在可以按照提议的安排继续推进。
              </p>
              <div className="flex flex-wrap items-center justify-center gap-3">
                <button className="btn btn-primary btn-lg">
                  接受并继续
                </button>
                <button className="btn btn-secondary btn-lg">
                  稍后处理
                </button>
                <button
                  className="btn btn-ghost btn-lg"
                  onClick={() => navigate('/demand')}
                >
                  开始新协商
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Failed State Actions */}
        {status === 'failed' && (
          <div className="mt-8 animate-fade-in-up">
            <div className="card p-8 text-center border-[var(--color-error)]/20">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-error)]/10 flex items-center justify-center">
                <span className="text-[var(--color-error)] text-3xl">!</span>
              </div>
              <h3 className="text-xl font-semibold text-[var(--color-error)] mb-2">
                协商未能完成
              </h3>
              <p className="text-[var(--color-text-secondary)] mb-6 max-w-md mx-auto">
                协商过程未能达成一致。您可以调整需求后重试。
              </p>
              <div className="flex flex-wrap items-center justify-center gap-3">
                <button
                  className="btn btn-primary btn-lg"
                  onClick={() => navigate('/demand')}
                >
                  重新尝试
                </button>
                <button className="btn btn-secondary btn-lg">
                  联系支持
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NegotiationPage;
