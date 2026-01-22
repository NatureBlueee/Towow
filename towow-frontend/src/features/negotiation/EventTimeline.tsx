import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  LoadingOutlined,
  SearchOutlined,
  FilterOutlined,
  DownOutlined,
  UpOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import type { TimelineEvent } from '../../types';
import { formatRelativeTime } from '../../utils/format';

interface EventTimelineProps {
  events: TimelineEvent[];
  maxHeight?: number;
}

// ============ 事件图标配置 ============
interface EventConfig {
  icon: string;
  label: string;
  color: string;
  bgColor: string;
  category: 'demand' | 'negotiation' | 'participant' | 'proposal' | 'result' | 'system';
}

const EVENT_CONFIG: Record<string, EventConfig> = {
  // 需求相关
  'towow.demand.submitted': {
    icon: '📝',
    label: '需求提交',
    color: 'var(--color-primary)',
    bgColor: 'rgba(99, 102, 241, 0.1)',
    category: 'demand',
  },
  'towow.demand.understood': {
    icon: '💡',
    label: '需求已理解',
    color: 'var(--color-warning)',
    bgColor: 'rgba(245, 158, 11, 0.1)',
    category: 'demand',
  },
  'towow.demand.broadcast': {
    icon: '📢',
    label: '已广播到网络',
    color: 'var(--color-info)',
    bgColor: 'rgba(59, 130, 246, 0.1)',
    category: 'demand',
  },

  // 协商流程
  negotiation_started: {
    icon: '🚀',
    label: '协商开始',
    color: 'var(--color-primary)',
    bgColor: 'rgba(99, 102, 241, 0.1)',
    category: 'negotiation',
  },
  'towow.filter.completed': {
    icon: '🔍',
    label: '智能筛选完成',
    color: 'var(--color-info)',
    bgColor: 'rgba(59, 130, 246, 0.1)',
    category: 'negotiation',
  },

  // 参与者相关
  agent_joined: {
    icon: '👋',
    label: '参与者加入',
    color: 'var(--color-success)',
    bgColor: 'rgba(34, 197, 94, 0.1)',
    category: 'participant',
  },
  'towow.offer.submitted': {
    icon: '💬',
    label: '收到响应',
    color: 'var(--color-info)',
    bgColor: 'rgba(59, 130, 246, 0.1)',
    category: 'participant',
  },
  agent_message: {
    icon: '💬',
    label: '发言',
    color: 'var(--color-text-secondary)',
    bgColor: 'var(--color-bg-muted)',
    category: 'participant',
  },
  agent_thinking: {
    icon: '🤔',
    label: '思考中',
    color: 'var(--color-warning)',
    bgColor: 'rgba(245, 158, 11, 0.1)',
    category: 'participant',
  },
  'towow.agent.withdrawn': {
    icon: '🚪',
    label: '退出协商',
    color: 'var(--color-warning)',
    bgColor: 'rgba(245, 158, 11, 0.1)',
    category: 'participant',
  },
  'towow.agent.kicked': {
    icon: '⛔',
    label: '被踢出',
    color: 'var(--color-error)',
    bgColor: 'rgba(239, 68, 68, 0.1)',
    category: 'participant',
  },

  // 提案相关
  agent_proposal: {
    icon: '📋',
    label: '提案',
    color: 'var(--color-secondary)',
    bgColor: 'rgba(139, 92, 246, 0.1)',
    category: 'proposal',
  },
  'towow.proposal.distributed': {
    icon: '📋',
    label: '方案分发',
    color: 'var(--color-secondary)',
    bgColor: 'rgba(139, 92, 246, 0.1)',
    category: 'proposal',
  },
  'towow.proposal.feedback': {
    icon: '💬',
    label: '方案反馈',
    color: 'var(--color-info)',
    bgColor: 'rgba(59, 130, 246, 0.1)',
    category: 'proposal',
  },
  'towow.negotiation.counter_proposal': {
    icon: '🔄',
    label: '反提案',
    color: 'var(--color-secondary)',
    bgColor: 'rgba(139, 92, 246, 0.1)',
    category: 'proposal',
  },
  'towow.negotiation.bargain': {
    icon: '💰',
    label: '讨价还价',
    color: 'var(--color-warning)',
    bgColor: 'rgba(245, 158, 11, 0.1)',
    category: 'proposal',
  },

  // T07 新增事件类型
  'towow.feedback.evaluated': {
    icon: '📊',
    label: '反馈评估',
    color: 'var(--color-info)',
    bgColor: 'rgba(59, 130, 246, 0.1)',
    category: 'proposal',
  },
  'towow.gap.identified': {
    icon: '🔎',
    label: '缺口识别',
    color: 'var(--color-warning)',
    bgColor: 'rgba(245, 158, 11, 0.1)',
    category: 'negotiation',
  },
  'towow.subnet.triggered': {
    icon: '🌐',
    label: '子网触发',
    color: 'var(--color-secondary)',
    bgColor: 'rgba(139, 92, 246, 0.1)',
    category: 'negotiation',
  },
  'towow.negotiation.round_started': {
    icon: '🔄',
    label: '新一轮协商',
    color: 'var(--color-primary)',
    bgColor: 'rgba(99, 102, 241, 0.1)',
    category: 'negotiation',
  },

  // 结果相关
  proposal_accepted: {
    icon: '✅',
    label: '同意',
    color: 'var(--color-success)',
    bgColor: 'rgba(34, 197, 94, 0.1)',
    category: 'result',
  },
  proposal_rejected: {
    icon: '❌',
    label: '拒绝',
    color: 'var(--color-error)',
    bgColor: 'rgba(239, 68, 68, 0.1)',
    category: 'result',
  },
  'towow.proposal.finalized': {
    icon: '🎉',
    label: '协商完成',
    color: 'var(--color-success)',
    bgColor: 'rgba(34, 197, 94, 0.1)',
    category: 'result',
  },
  negotiation_completed: {
    icon: '🎉',
    label: '协商完成',
    color: 'var(--color-success)',
    bgColor: 'rgba(34, 197, 94, 0.1)',
    category: 'result',
  },
  'towow.negotiation.failed': {
    icon: '😞',
    label: '协商失败',
    color: 'var(--color-error)',
    bgColor: 'rgba(239, 68, 68, 0.1)',
    category: 'result',
  },

  // 系统事件
  user_feedback: {
    icon: '💬',
    label: '用户反馈',
    color: 'var(--color-primary)',
    bgColor: 'rgba(99, 102, 241, 0.1)',
    category: 'system',
  },
  status_update: {
    icon: '🔄',
    label: '状态更新',
    color: 'var(--color-info)',
    bgColor: 'rgba(59, 130, 246, 0.1)',
    category: 'system',
  },
  error: {
    icon: '⚠️',
    label: '错误',
    color: 'var(--color-error)',
    bgColor: 'rgba(239, 68, 68, 0.1)',
    category: 'system',
  },
};

// 事件分类标签
const CATEGORY_LABELS: Record<string, string> = {
  demand: '需求',
  negotiation: '协商',
  participant: '参与者',
  proposal: '提案',
  result: '结果',
  system: '系统',
};

// ============ 工具函数 ============
const getEventConfig = (eventType: string): EventConfig => {
  return (
    EVENT_CONFIG[eventType] || {
      icon: 'ℹ️',
      label: eventType.split('.').pop() || eventType,
      color: 'var(--color-text-muted)',
      bgColor: 'var(--color-bg-muted)',
      category: 'system',
    }
  );
};

const formatAgentName = (agentId?: string): string => {
  if (!agentId) return '';
  return agentId.replace('user_agent_', '').replace(/_/g, ' ').toUpperCase();
};

// ============ 子组件 ============

// Skeleton for loading state
const EventTimelineSkeleton: React.FC = () => (
  <div className="card">
    <div className="flex items-center justify-between mb-4">
      <div className="skeleton h-5 w-16 rounded" />
      <div className="skeleton h-5 w-8 rounded-full" />
    </div>
    <div className="space-y-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="flex items-start gap-3">
          <div className="skeleton w-8 h-8 rounded-full" />
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <div className="skeleton h-4 w-24 rounded" />
              <div className="skeleton h-3 w-12 rounded" />
            </div>
            <div className="skeleton h-3 w-full rounded mt-1" />
          </div>
        </div>
      ))}
    </div>
  </div>
);

// 单个事件项组件
interface EventItemProps {
  event: TimelineEvent;
  isExpanded: boolean;
  isNew: boolean;
  onToggle: () => void;
}

const EventItem: React.FC<EventItemProps> = ({ event, isExpanded, isNew, onToggle }) => {
  const config = getEventConfig(event.event_type);
  const hasDetails = !!(event.content?.message || event.content?.thinking_step || event.content?.error);

  return (
    <div
      className={`event-timeline-item relative flex items-start gap-3 pl-1 cursor-pointer group ${
        isNew ? 'event-timeline-item-new' : ''
      }`}
      onClick={hasDetails ? onToggle : undefined}
    >
      {/* 事件图标 */}
      <div
        className="event-icon w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-base relative z-10 ring-2 ring-[var(--color-card)] transition-transform duration-200 group-hover:scale-110"
        style={{ backgroundColor: config.bgColor }}
      >
        {config.icon}
      </div>

      {/* 内容 */}
      <div className="flex-1 min-w-0 pb-3">
        {/* 头部 */}
        <div className="flex items-center justify-between gap-2 mb-1">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="font-medium text-sm truncate"
              style={{ color: config.color }}
            >
              {config.label}
            </span>
            {event.agent_id && (
              <span className="inline-flex items-center px-2 py-0.5 text-[10px] rounded-full bg-[var(--color-bg-muted)] text-[var(--color-text-secondary)] truncate max-w-[100px]">
                {formatAgentName(event.agent_id)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <span className="text-[10px] text-[var(--color-text-muted)]">
              {formatRelativeTime(event.timestamp)}
            </span>
            {hasDetails && (
              <span className="text-[var(--color-text-muted)] text-xs opacity-0 group-hover:opacity-100 transition-opacity">
                {isExpanded ? <UpOutlined /> : <DownOutlined />}
              </span>
            )}
          </div>
        </div>

        {/* 详情内容（可折叠） */}
        {hasDetails && (
          <div
            className={`event-details overflow-hidden transition-all duration-200 ${
              isExpanded ? 'max-h-96 opacity-100 mt-2' : 'max-h-0 opacity-0'
            }`}
          >
            {/* 消息 */}
            {event.content?.message && (
              <div
                className={`p-2.5 rounded-lg text-xs border-l-2 ${
                  event.event_type.includes('error') || event.event_type.includes('failed')
                    ? 'bg-[var(--color-error)]/5 border-[var(--color-error)] text-[var(--color-error)]'
                    : 'bg-[var(--color-bg-subtle)] border-[var(--color-primary)] text-[var(--color-text-secondary)]'
                }`}
              >
                {event.content.message}
              </div>
            )}

            {/* 思考步骤 */}
            {event.content?.thinking_step && (
              <p className="text-xs text-[var(--color-text-tertiary)] italic pl-2 border-l-2 border-[var(--color-warning)]">
                {event.content.thinking_step}
              </p>
            )}

            {/* 错误 */}
            {event.content?.error && (
              <div className="p-2.5 rounded-lg text-xs bg-[var(--color-error)]/5 border border-[var(--color-error)]/20 text-[var(--color-error)]">
                {event.content.error}
              </div>
            )}
          </div>
        )}

        {/* 未展开时的摘要预览 */}
        {hasDetails && !isExpanded && event.content?.message && (
          <p className="text-xs text-[var(--color-text-tertiary)] truncate mt-0.5">
            {event.content.message}
          </p>
        )}
      </div>
    </div>
  );
};

// ============ 主组件 ============
const EventTimeline: React.FC<EventTimelineProps> = ({ events, maxHeight = 400 }) => {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set());
  const [newEventIds, setNewEventIds] = useState<Set<string>>(new Set());
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const prevEventsLengthRef = useRef(events.length);

  // 自动滚动到最新事件
  useEffect(() => {
    if (events.length > prevEventsLengthRef.current && scrollContainerRef.current) {
      // 新事件添加，标记为新
      const newIds = events
        .slice(prevEventsLengthRef.current)
        .map((e) => e.id);
      setNewEventIds((prev) => new Set([...prev, ...newIds]));

      // 滚动到顶部（最新事件）
      scrollContainerRef.current.scrollTo({
        top: 0,
        behavior: 'smooth',
      });

      // 3秒后移除新标记
      setTimeout(() => {
        setNewEventIds((prev) => {
          const next = new Set(prev);
          newIds.forEach((id) => next.delete(id));
          return next;
        });
      }, 3000);
    }
    prevEventsLengthRef.current = events.length;
  }, [events.length, events]);

  // 切换展开状态
  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  // 切换分类筛选
  const toggleCategory = useCallback((category: string) => {
    setSelectedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  }, []);

  // 清除所有筛选
  const clearFilters = useCallback(() => {
    setSelectedCategories(new Set());
    setSearchQuery('');
  }, []);

  // 筛选和搜索事件
  const filteredEvents = useMemo(() => {
    let result = [...events].reverse(); // 最新在上

    // 按分类筛选
    if (selectedCategories.size > 0) {
      result = result.filter((event) => {
        const config = getEventConfig(event.event_type);
        return selectedCategories.has(config.category);
      });
    }

    // 按搜索词筛选
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter((event) => {
        const config = getEventConfig(event.event_type);
        const agentName = formatAgentName(event.agent_id).toLowerCase();
        const message = event.content?.message?.toLowerCase() || '';
        return (
          config.label.toLowerCase().includes(query) ||
          agentName.includes(query) ||
          message.includes(query)
        );
      });
    }

    return result;
  }, [events, selectedCategories, searchQuery]);

  // 获取所有可用的分类
  const availableCategories = useMemo(() => {
    const categories = new Set<string>();
    events.forEach((event) => {
      const config = getEventConfig(event.event_type);
      categories.add(config.category);
    });
    return Array.from(categories);
  }, [events]);

  const hasActiveFilters = selectedCategories.size > 0 || searchQuery.trim();

  return (
    <div className="card h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-[var(--color-text)]">事件流</h3>
          <span className="tag tag-info text-xs">{events.length}</span>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`btn btn-ghost btn-sm p-1.5 ${showFilters ? 'text-[var(--color-primary)]' : ''}`}
          title="筛选与搜索"
        >
          <FilterOutlined />
        </button>
      </div>

      {/* 筛选与搜索区域 */}
      {showFilters && (
        <div className="mb-3 space-y-2 animate-fade-in-down">
          {/* 搜索框 */}
          <div className="relative">
            <SearchOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="搜索事件..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-9 pr-8 py-1.5 text-sm"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
              >
                <CloseOutlined className="text-xs" />
              </button>
            )}
          </div>

          {/* 分类筛选标签 */}
          <div className="flex flex-wrap gap-1.5">
            {availableCategories.map((category) => (
              <button
                key={category}
                onClick={() => toggleCategory(category)}
                className={`px-2 py-0.5 text-[10px] rounded-full transition-all ${
                  selectedCategories.has(category)
                    ? 'bg-[var(--color-primary)] text-white'
                    : 'bg-[var(--color-bg-muted)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-subtle)]'
                }`}
              >
                {CATEGORY_LABELS[category] || category}
              </button>
            ))}
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="px-2 py-0.5 text-[10px] rounded-full text-[var(--color-error)] hover:bg-[var(--color-error)]/10 transition-all"
              >
                清除筛选
              </button>
            )}
          </div>

          {/* 筛选结果提示 */}
          {hasActiveFilters && (
            <p className="text-[10px] text-[var(--color-text-tertiary)]">
              显示 {filteredEvents.length} / {events.length} 条事件
            </p>
          )}
        </div>
      )}

      {/* Content */}
      {events.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center flex-1">
          <div className="w-12 h-12 rounded-full bg-[var(--color-primary)]/10 flex items-center justify-center mb-3">
            <LoadingOutlined className="text-[var(--color-primary)] text-xl animate-spin" />
          </div>
          <p className="text-sm text-[var(--color-text-tertiary)]">等待事件...</p>
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center flex-1">
          <p className="text-sm text-[var(--color-text-tertiary)]">没有匹配的事件</p>
          <button
            onClick={clearFilters}
            className="mt-2 text-xs text-[var(--color-primary)] hover:underline"
          >
            清除筛选条件
          </button>
        </div>
      ) : (
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto custom-scrollbar pr-2 -mr-2"
          style={{ maxHeight }}
        >
          <div className="relative">
            {/* 时间线连接线 */}
            <div
              className="absolute left-[15px] top-4 bottom-4 w-[2px]"
              style={{ background: 'var(--color-border)' }}
            />

            {/* 事件列表 */}
            <div className="space-y-1">
              {filteredEvents.map((event) => (
                <EventItem
                  key={event.id}
                  event={event}
                  isExpanded={expandedIds.has(event.id)}
                  isNew={newEventIds.has(event.id)}
                  onToggle={() => toggleExpand(event.id)}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EventTimeline;
export { EventTimelineSkeleton };
