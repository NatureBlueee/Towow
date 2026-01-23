/**
 * 协商过程实时展示页面
 *
 * 展示AI多方协商的实时进度和结果
 *
 * 设计特点:
 * - 深色渐变背景（与SubmitDemand风格呼应）
 * - 卡片式布局，毛玻璃效果
 * - 实时状态指示器
 * - 候选人卡片展示
 * - 时间线展示协商进程
 * - v4: 协商进度条、强制终结状态、反馈评估展示
 */
import React, { useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSSE } from '../hooks/useSSE';
import { useEventStore } from '../stores/eventStore';
import type { NegotiationStatus, Candidate, ToWowProposal, TimelineEvent, ProposalTimeline, FeedbackResult, ForceFinalizationInfo } from '../types';

// Helper function to format timeline for display
const formatTimeline = (timeline: string | ProposalTimeline | undefined): string => {
  if (!timeline) return '';
  if (typeof timeline === 'string') return timeline;

  const parts: string[] = [];
  if (timeline.start_date) parts.push(`开始: ${timeline.start_date}`);
  if (timeline.end_date) parts.push(`结束: ${timeline.end_date}`);
  if (timeline.milestones && timeline.milestones.length > 0) {
    const milestoneNames = timeline.milestones.map(m => m.name).join('、');
    parts.push(`里程碑: ${milestoneNames}`);
  }
  return parts.join(' | ') || '时间待定';
};

// 状态配置映射
const STATUS_CONFIG: Record<
  NegotiationStatus,
  { label: string; color: string; bgColor: string; icon: string }
> = {
  pending: { label: '准备中', color: 'text-gray-400', bgColor: 'bg-gray-500', icon: '⏳' },
  connecting: { label: '连接中', color: 'text-blue-400', bgColor: 'bg-blue-500', icon: '🔗' },
  filtering: { label: '筛选候选人', color: 'text-yellow-400', bgColor: 'bg-yellow-500', icon: '🔍' },
  collecting: { label: '收集响应', color: 'text-orange-400', bgColor: 'bg-orange-500', icon: '📥' },
  aggregating: { label: '聚合方案', color: 'text-purple-400', bgColor: 'bg-purple-500', icon: '🔄' },
  negotiating: { label: '协商进行中', color: 'text-indigo-400', bgColor: 'bg-indigo-500', icon: '💬' },
  finalized: { label: '协商完成', color: 'text-green-400', bgColor: 'bg-green-500', icon: '✅' },
  failed: { label: '协商失败', color: 'text-red-400', bgColor: 'bg-red-500', icon: '❌' },
  in_progress: { label: '进行中', color: 'text-blue-400', bgColor: 'bg-blue-500', icon: '▶️' },
  awaiting_user: { label: '等待用户', color: 'text-amber-400', bgColor: 'bg-amber-500', icon: '👤' },
  completed: { label: '已完成', color: 'text-green-400', bgColor: 'bg-green-500', icon: '🎉' },
  cancelled: { label: '已取消', color: 'text-gray-400', bgColor: 'bg-gray-500', icon: '🚫' },
};

// 状态指示器组件
const StatusIndicator: React.FC<{ status: NegotiationStatus }> = ({ status }) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const isActive = ['connecting', 'filtering', 'collecting', 'aggregating', 'negotiating', 'in_progress'].includes(status);

  return (
    <div className="flex items-center gap-3">
      <div className="relative">
        <span className="text-2xl">{config.icon}</span>
        {isActive && (
          <span className={`absolute -top-1 -right-1 w-3 h-3 ${config.bgColor} rounded-full animate-ping`} />
        )}
      </div>
      <div>
        <span className={`text-lg font-semibold ${config.color}`}>{config.label}</span>
        {isActive && (
          <div className="flex gap-1 mt-1">
            <span className={`w-2 h-2 ${config.bgColor} rounded-full animate-bounce`} style={{ animationDelay: '0ms' }} />
            <span className={`w-2 h-2 ${config.bgColor} rounded-full animate-bounce`} style={{ animationDelay: '150ms' }} />
            <span className={`w-2 h-2 ${config.bgColor} rounded-full animate-bounce`} style={{ animationDelay: '300ms' }} />
          </div>
        )}
      </div>
    </div>
  );
};

// v4: 协商进度条组件
const NegotiationProgressBar: React.FC<{
  currentRound: number;
  maxRounds: number;
  status: NegotiationStatus;
}> = ({ currentRound, maxRounds, status }) => {
  const isNegotiating = status === 'negotiating';
  const isFinalRound = currentRound === maxRounds;

  // 计算进度百分比
  const progress = maxRounds > 0 ? (currentRound / maxRounds) * 100 : 0;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-white/70 text-sm">协商进度</span>
          {isFinalRound && isNegotiating && (
            <span className="px-2 py-0.5 bg-orange-500/30 border border-orange-400/50 rounded text-orange-300 text-xs font-medium animate-pulse">
              最终轮
            </span>
          )}
        </div>
        <span className="text-white/90 text-sm font-medium">
          第 {currentRound} / {maxRounds} 轮
        </span>
      </div>

      {/* 进度条 */}
      <div className="relative h-2 bg-white/10 rounded-full overflow-hidden">
        <div
          className={`absolute left-0 top-0 h-full rounded-full transition-all duration-500 ${
            isFinalRound
              ? 'bg-gradient-to-r from-orange-500 to-red-500'
              : 'bg-gradient-to-r from-indigo-500 to-purple-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* 轮次标记 */}
      <div className="flex justify-between mt-1">
        {Array.from({ length: maxRounds }, (_, i) => i + 1).map((round) => (
          <div
            key={round}
            className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-all ${
              round < currentRound
                ? 'bg-green-500/30 text-green-300 border border-green-400/50'
                : round === currentRound
                ? 'bg-indigo-500/50 text-white border-2 border-indigo-400 animate-pulse'
                : 'bg-white/10 text-white/40 border border-white/20'
            }`}
          >
            {round}
          </div>
        ))}
      </div>
    </div>
  );
};

// v4: 强制终结警告卡片
const ForceFinalizationCard: React.FC<{
  info: ForceFinalizationInfo;
}> = ({ info }) => {
  const acceptedCount = info.accepted_agents.length;
  const pendingCount = info.pending_agents.length;

  return (
    <div className="bg-orange-500/10 backdrop-blur-sm rounded-xl border-2 border-orange-400/50 p-4 mb-4">
      <div className="flex items-start gap-3">
        <div className="text-2xl">&#9888;</div>
        <div className="flex-1">
          <h3 className="text-orange-300 font-semibold mb-1">协商强制终结</h3>
          <p className="text-white/70 text-sm mb-3">
            已达到最大协商轮次，系统自动生成妥协方案
          </p>

          <div className="flex gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-green-400 rounded-full" />
              <span className="text-green-300">{acceptedCount} 人接受</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-orange-400 rounded-full" />
              <span className="text-orange-300">{pendingCount} 人未完全接受</span>
            </div>
          </div>

          {pendingCount > 0 && (
            <div className="mt-3 p-2 bg-white/5 rounded-lg">
              <p className="text-white/50 text-xs mb-1">未完全接受的 Agent:</p>
              <div className="flex flex-wrap gap-1">
                {info.pending_agents.map((agentId) => (
                  <span
                    key={agentId}
                    className="px-2 py-0.5 bg-orange-500/20 rounded text-orange-200 text-xs"
                  >
                    {agentId.replace('user_agent_', '')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// v4: 反馈评估展示组件
const FeedbackResultsCard: React.FC<{
  results: FeedbackResult[];
}> = ({ results }) => {
  if (results.length === 0) return null;

  const evaluationConfig: Record<string, { color: string; bgColor: string; label: string }> = {
    accept: { color: 'text-green-300', bgColor: 'bg-green-500/20', label: '接受' },
    reject: { color: 'text-red-300', bgColor: 'bg-red-500/20', label: '拒绝' },
    conditional: { color: 'text-yellow-300', bgColor: 'bg-yellow-500/20', label: '有条件' },
  };

  const responseTypeConfig: Record<string, { icon: string; label: string }> = {
    offer: { icon: '&#128176;', label: '报价' },
    negotiate: { icon: '&#128172;', label: '协商' },
  };

  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 p-4 mb-4">
      <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
        <span className="text-lg">&#128200;</span>
        反馈评估结果
      </h3>

      <div className="space-y-2">
        {results.map((result, idx) => {
          const evalConfig = evaluationConfig[result.evaluation] || evaluationConfig.accept;
          const typeConfig = responseTypeConfig[result.response_type] || responseTypeConfig.offer;
          const displayName = result.agent_id.replace('user_agent_', '').replace(/_/g, ' ');

          return (
            <div
              key={`${result.agent_id}-${idx}`}
              className={`flex items-center justify-between p-2 rounded-lg ${evalConfig.bgColor}`}
            >
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white text-xs font-bold">
                  {displayName.charAt(0).toUpperCase()}
                </div>
                <div>
                  <span className="text-white text-sm capitalize">{displayName}</span>
                  <div className="flex items-center gap-1 text-white/50 text-xs">
                    <span dangerouslySetInnerHTML={{ __html: typeConfig.icon }} />
                    <span>{typeConfig.label}</span>
                  </div>
                </div>
              </div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${evalConfig.color}`}>
                {evalConfig.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* 统计摘要 */}
      <div className="mt-3 pt-3 border-t border-white/10 flex justify-around text-center">
        <div>
          <div className="text-green-400 text-lg font-bold">
            {results.filter((r) => r.evaluation === 'accept').length}
          </div>
          <div className="text-white/50 text-xs">接受</div>
        </div>
        <div>
          <div className="text-yellow-400 text-lg font-bold">
            {results.filter((r) => r.evaluation === 'conditional').length}
          </div>
          <div className="text-white/50 text-xs">有条件</div>
        </div>
        <div>
          <div className="text-red-400 text-lg font-bold">
            {results.filter((r) => r.evaluation === 'reject').length}
          </div>
          <div className="text-white/50 text-xs">拒绝</div>
        </div>
      </div>
    </div>
  );
};

// 候选人卡片组件
const CandidateCard: React.FC<{ candidate: Candidate }> = ({ candidate }) => {
  const displayName = candidate.agent_id.replace('user_agent_', '').replace(/_/g, ' ');
  const hasResponse = !!candidate.response;
  const decision = candidate.response?.decision;

  const decisionConfig: Record<string, { color: string; badge: string; badgeColor: string }> = {
    participate: { color: 'border-green-400 bg-green-400/10', badge: '已接受', badgeColor: 'bg-green-500' },
    decline: { color: 'border-red-400 bg-red-400/10', badge: '已拒绝', badgeColor: 'bg-red-500' },
    conditional: { color: 'border-yellow-400 bg-yellow-400/10', badge: '有条件', badgeColor: 'bg-yellow-500' },
    withdrawn: { color: 'border-gray-400 bg-gray-400/10', badge: '已退出', badgeColor: 'bg-gray-500' },
    kicked: { color: 'border-orange-400 bg-orange-400/10', badge: '被踢出', badgeColor: 'bg-orange-500' },
  };

  const config = decision && decisionConfig[decision]
    ? decisionConfig[decision]
    : { color: 'border-white/20 bg-white/5', badge: '待响应', badgeColor: 'bg-blue-500' };

  return (
    <div className={`rounded-xl border-2 ${config.color} p-4 transition-all duration-300 hover:scale-[1.02]`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-bold text-sm">
            {displayName.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="text-white font-medium capitalize">{displayName}</div>
            {candidate.capabilities && candidate.capabilities.length > 0 && (
              <div className="text-white/50 text-xs">
                {candidate.capabilities.slice(0, 2).join(', ')}
              </div>
            )}
          </div>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs text-white ${config.badgeColor}`}>
          {config.badge}
        </span>
      </div>

      <p className="text-white/70 text-sm mb-2">{candidate.reason}</p>

      {/* 拒绝/退出原因展示 */}
      {hasResponse && (candidate.response?.decline_reason || candidate.response?.withdrawn_reason || candidate.response?.kicked_reason) && (
        <div className="mt-3 p-3 bg-red-500/10 border border-red-400/30 rounded-lg">
          <p className="text-white/60 text-xs mb-1">
            {candidate.response?.decline_reason ? '拒绝原因' :
             candidate.response?.withdrawn_reason ? '退出原因' : '踢出原因'}:
          </p>
          <p className="text-red-300/90 text-sm italic">
            "{candidate.response?.decline_reason || candidate.response?.withdrawn_reason || candidate.response?.kicked_reason}"
          </p>
          {candidate.response?.kicked_by && (
            <p className="text-white/50 text-xs mt-1">操作者: {candidate.response.kicked_by}</p>
          )}
        </div>
      )}

      {hasResponse && candidate.response?.contribution && (
        <div className="mt-3 pt-3 border-t border-white/10">
          <p className="text-white/60 text-xs mb-1">贡献内容:</p>
          <p className="text-white/80 text-sm">{candidate.response.contribution}</p>
        </div>
      )}

      {hasResponse && candidate.response?.conditions && candidate.response.conditions.length > 0 && (
        <div className="mt-2">
          <p className="text-white/60 text-xs mb-1">条件:</p>
          <ul className="text-yellow-300/80 text-xs list-disc list-inside">
            {candidate.response.conditions.map((cond, idx) => (
              <li key={idx}>{cond}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

// 方案展示组件
const ProposalCard: React.FC<{ proposal: ToWowProposal; round?: number }> = ({ proposal, round }) => {
  const confidenceConfig = {
    high: { color: 'text-green-400', label: '高置信度' },
    medium: { color: 'text-yellow-400', label: '中置信度' },
    low: { color: 'text-red-400', label: '低置信度' },
  };

  const conf = proposal.confidence ? confidenceConfig[proposal.confidence] : null;

  return (
    <div className="bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">📋</span>
          <h3 className="text-white font-semibold text-lg">
            {round ? `第 ${round} 轮方案` : '最终方案'}
          </h3>
        </div>
        {conf && (
          <span className={`text-sm ${conf.color}`}>{conf.label}</span>
        )}
      </div>

      <p className="text-white/90 mb-4">{proposal.summary}</p>

      {proposal.timeline && (
        <div className="mb-4 p-3 bg-white/5 rounded-lg">
          <p className="text-white/60 text-xs mb-1">预计时间线</p>
          <p className="text-white/80 text-sm">{formatTimeline(proposal.timeline)}</p>
        </div>
      )}

      {proposal.assignments && proposal.assignments.length > 0 && (
        <div>
          <p className="text-white/60 text-sm mb-2">任务分配:</p>
          <div className="space-y-2">
            {proposal.assignments.map((assignment, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 bg-white/5 rounded-lg">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center text-white text-xs font-bold">
                  {assignment.agent_id.replace('user_agent_', '').charAt(0).toUpperCase()}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium text-sm capitalize">
                      {assignment.agent_id.replace('user_agent_', '').replace(/_/g, ' ')}
                    </span>
                    <span className="px-2 py-0.5 bg-indigo-500/30 rounded text-indigo-300 text-xs">
                      {assignment.role}
                    </span>
                  </div>
                  <p className="text-white/70 text-sm mt-1">{assignment.responsibility}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// 时间线事件组件
const TimelineItem: React.FC<{ event: TimelineEvent; isLast: boolean }> = ({ event, isLast }) => {
  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return '--:--:--';
    }
  };

  const isError = event.event_type === 'error' || event.event_type === 'towow.negotiation.failed';

  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={`w-3 h-3 rounded-full ${isError ? 'bg-red-400' : 'bg-indigo-400'}`} />
        {!isLast && <div className="w-0.5 flex-1 bg-white/20 mt-1" />}
      </div>
      <div className="flex-1 pb-4">
        <div className="flex items-center gap-2 text-xs text-white/50 mb-1">
          <span>{formatTime(event.timestamp)}</span>
          {event.agent_id && (
            <span className="px-1.5 py-0.5 bg-white/10 rounded text-white/70">
              {event.agent_id.replace('user_agent_', '')}
            </span>
          )}
        </div>
        <p className={`text-sm ${isError ? 'text-red-300' : 'text-white/80'}`}>
          {event.content.message || event.content.thinking_step || event.content.error || event.event_type}
        </p>
      </div>
    </div>
  );
};

// 主页面组件
const Negotiation: React.FC = () => {
  const { demandId } = useParams<{ demandId: string }>();
  const navigate = useNavigate();

  const {
    status,
    candidates,
    currentProposal,
    currentRound,
    maxRounds,
    timeline,
    error,
    isForceFinalized,
    forceFinalizationInfo,
    feedbackResults,
    handleSSEEvent,
    setNegotiationId,
    setStatus,
    reset,
  } = useEventStore();

  // SSE 事件处理
  const onSSEEvent = useCallback(
    (event: Parameters<typeof handleSSEEvent>[0]) => {
      handleSSEEvent(event);
    },
    [handleSSEEvent]
  );

  const onSSEOpen = useCallback(() => {
    setStatus('connecting');
  }, [setStatus]);

  const onSSEError = useCallback(
    (err: Error) => {
      console.error('SSE Error:', err);
    },
    []
  );

  // 使用 SSE hook
  const { isConnected, reconnectAttempts } = useSSE(demandId || null, {
    onEvent: onSSEEvent,
    onOpen: onSSEOpen,
    onError: onSSEError,
    autoConnect: true,
  });

  // 初始化
  useEffect(() => {
    if (demandId) {
      setNegotiationId(demandId);
      setStatus('connecting');
    }

    return () => {
      reset();
    };
  }, [demandId, setNegotiationId, setStatus, reset]);

  // 返回首页
  const handleBack = () => {
    navigate('/');
  };

  // 重新开始
  const handleRestart = () => {
    reset();
    navigate('/');
  };

  const isTerminal = ['finalized', 'completed', 'failed', 'cancelled'].includes(status);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* 顶部导航 */}
      <div className="sticky top-0 z-10 backdrop-blur-md bg-black/20 border-b border-white/10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 text-white/70 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span>返回</span>
          </button>

          <h1 className="text-xl font-bold text-white">ToWow</h1>

          <div className="flex items-center gap-2">
            {isConnected ? (
              <span className="flex items-center gap-1 text-green-400 text-sm">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                已连接
              </span>
            ) : (
              <span className="flex items-center gap-1 text-yellow-400 text-sm">
                <span className="w-2 h-2 bg-yellow-400 rounded-full" />
                {reconnectAttempts > 0 ? `重连中 (${reconnectAttempts})` : '断开'}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* 状态卡片 */}
        <div className="bg-white/10 backdrop-blur-sm rounded-2xl border border-white/20 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <StatusIndicator status={status} />
            <div className="text-right">
              <p className="text-white/50 text-xs">协商 ID</p>
              <p className="text-white/70 text-sm font-mono">{demandId?.slice(0, 12)}...</p>
            </div>
          </div>

          {/* v4: 协商进度条 - 在协商进行中或已完成时显示 */}
          {(status === 'negotiating' || isTerminal) && currentRound > 0 && (
            <div className="mt-4 pt-4 border-t border-white/10">
              <NegotiationProgressBar
                currentRound={currentRound}
                maxRounds={maxRounds}
                status={status}
              />
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-500/20 border border-red-400/30 rounded-lg">
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          )}
        </div>

        {/* v4: 强制终结警告 */}
        {isForceFinalized && forceFinalizationInfo && (
          <ForceFinalizationCard info={forceFinalizationInfo} />
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：候选人列表 + 方案 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 候选人列表 */}
            {candidates.length > 0 && (
              <div>
                <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <span className="text-xl">👥</span>
                  候选人 ({candidates.length})
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {candidates.map((candidate) => (
                    <CandidateCard key={candidate.agent_id} candidate={candidate} />
                  ))}
                </div>
              </div>
            )}

            {/* 当前方案 */}
            {currentProposal && (
              <div>
                <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <span className="text-xl">📋</span>
                  {isTerminal
                    ? isForceFinalized
                      ? '妥协方案'
                      : '最终方案'
                    : '当前方案'}
                  {isForceFinalized && (
                    <span className="px-2 py-0.5 bg-orange-500/30 rounded text-orange-300 text-xs">
                      部分 Agent 未完全接受
                    </span>
                  )}
                </h2>
                <ProposalCard proposal={currentProposal} round={isTerminal ? undefined : currentRound} />
              </div>
            )}

            {/* 空状态 */}
            {candidates.length === 0 && !currentProposal && !error && (
              <div className="bg-white/5 rounded-2xl border border-white/10 p-12 text-center">
                <div className="text-4xl mb-4">🔄</div>
                <p className="text-white/70">正在等待协商数据...</p>
                <p className="text-white/50 text-sm mt-2">AI正在分析你的需求并寻找合适的协作者</p>
              </div>
            )}
          </div>

          {/* 右侧：反馈评估 + 时间线 */}
          <div className="lg:col-span-1 space-y-6">
            {/* v4: 反馈评估展示 */}
            {feedbackResults.length > 0 && (
              <FeedbackResultsCard results={feedbackResults} />
            )}

            {/* 时间线 */}
            <div>
              <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                <span className="text-xl">📜</span>
                协商时间线
              </h2>
              <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 p-4 max-h-[600px] overflow-y-auto">
                {timeline.length > 0 ? (
                  <div>
                    {timeline.map((event, idx) => (
                      <TimelineItem
                        key={event.id}
                        event={event}
                        isLast={idx === timeline.length - 1}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-white/50">
                    <p>暂无事件</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 底部操作 */}
        {isTerminal && (
          <div className="mt-8 flex justify-center">
            <button
              onClick={handleRestart}
              className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold rounded-xl transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] shadow-lg"
            >
              开始新的协商
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Negotiation;
