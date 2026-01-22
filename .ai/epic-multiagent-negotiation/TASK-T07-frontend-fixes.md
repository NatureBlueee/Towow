# TASK-T07-frontend-fixes

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T07-frontend-fixes.md`
>
> * TASK_ID: TASK-T07
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-22

---

## 关联 Story

- **STORY-07**: 实时展示与事件驱动

---

## 任务描述

修复前端实时展示相关的问题，确保协商过程能够正确、实时地展示给用户。

### 当前问题

1. 方案卡片（ProposalCard）在协商完成后消失
2. 事件时间线（EventTimeline）展示不完整
3. 候选人列表（CandidateList）状态更新不及时
4. SSE 断线重连后事件丢失

### 改造目标

1. 修复方案卡片消失问题
2. 完善事件时间线展示
3. 优化候选人状态实时更新
4. 增强 SSE 断线重连机制

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow-frontend/src/features/negotiation/ProposalCard.tsx` | 修复方案卡片消失 |
| `towow-frontend/src/features/negotiation/EventTimeline.tsx` | 完善事件展示 |
| `towow-frontend/src/features/negotiation/CandidateList.tsx` | 优化状态更新 |
| `towow-frontend/src/hooks/useSSE.ts` | 增强断线重连 |
| `towow-frontend/src/stores/eventStore.ts` | 优化事件存储 |

### 关键代码改动

#### 1. 修复 ProposalCard 消失问题

```tsx
// towow-frontend/src/features/negotiation/ProposalCard.tsx

import React, { useEffect, useState } from 'react';
import { useEventStore } from '@/stores/eventStore';

interface ProposalCardProps {
  demandId: string;
}

export const ProposalCard: React.FC<ProposalCardProps> = ({ demandId }) => {
  const { events, getLatestProposal } = useEventStore();
  const [proposal, setProposal] = useState<any>(null);
  const [status, setStatus] = useState<'pending' | 'distributed' | 'finalized' | 'failed'>('pending');

  useEffect(() => {
    // 获取最新方案
    const latestProposal = getLatestProposal(demandId);
    if (latestProposal) {
      setProposal(latestProposal);
    }

    // 监听方案相关事件
    const proposalEvents = events.filter(e =>
      e.payload?.demand_id === demandId &&
      ['towow.proposal.distributed', 'towow.proposal.finalized', 'towow.negotiation.failed'].includes(e.event_type)
    );

    if (proposalEvents.length > 0) {
      const latest = proposalEvents[proposalEvents.length - 1];

      if (latest.event_type === 'towow.proposal.distributed') {
        setProposal(latest.payload.proposal);
        setStatus('distributed');
      } else if (latest.event_type === 'towow.proposal.finalized') {
        setProposal(latest.payload.final_proposal);
        setStatus('finalized');
      } else if (latest.event_type === 'towow.negotiation.failed') {
        setStatus('failed');
        // 保留最后的方案，不清空
      }
    }
  }, [events, demandId]);

  // 即使状态为 failed，也展示最后的方案
  if (!proposal) {
    return (
      <div className="proposal-card proposal-card--empty">
        <p>方案生成中...</p>
      </div>
    );
  }

  return (
    <div className={`proposal-card proposal-card--${status}`}>
      <div className="proposal-card__header">
        <h3>协作方案</h3>
        <StatusBadge status={status} />
      </div>

      <div className="proposal-card__summary">
        <p>{proposal.summary}</p>
      </div>

      {proposal.assignments && (
        <div className="proposal-card__assignments">
          <h4>角色分配</h4>
          <ul>
            {proposal.assignments.map((a: any, i: number) => (
              <li key={i}>
                <span className="role">{a.role}</span>
                <span className="name">{a.display_name}</span>
                <span className="responsibility">{a.responsibility}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {proposal.timeline && (
        <div className="proposal-card__timeline">
          <h4>时间安排</h4>
          <p>开始: {proposal.timeline.start_date}</p>
          {proposal.timeline.milestones?.map((m: any, i: number) => (
            <div key={i} className="milestone">
              <span>{m.name}</span>
              <span>{m.date}</span>
            </div>
          ))}
        </div>
      )}

      {status === 'finalized' && (
        <div className="proposal-card__success">
          协商成功完成
        </div>
      )}

      {status === 'failed' && (
        <div className="proposal-card__failed">
          协商未能达成共识，以上为最后方案
        </div>
      )}
    </div>
  );
};
```

#### 2. 完善 EventTimeline

```tsx
// towow-frontend/src/features/negotiation/EventTimeline.tsx

import React from 'react';
import { useEventStore } from '@/stores/eventStore';

interface EventTimelineProps {
  demandId: string;
}

// 事件类型到显示文本的映射
const EVENT_DISPLAY: Record<string, {
  title: string;
  icon: string;
  color: string;
}> = {
  'towow.demand.understood': {
    title: '需求已理解',
    icon: '🎯',
    color: 'blue'
  },
  'towow.filter.completed': {
    title: '候选人筛选完成',
    icon: '🔍',
    color: 'purple'
  },
  'towow.channel.created': {
    title: '协商频道已创建',
    icon: '📢',
    color: 'green'
  },
  'towow.demand.broadcast': {
    title: '需求已广播',
    icon: '📣',
    color: 'blue'
  },
  'towow.offer.submitted': {
    title: '收到响应',
    icon: '✋',
    color: 'teal'
  },
  'towow.aggregation.started': {
    title: '方案聚合中',
    icon: '🔄',
    color: 'orange'
  },
  'towow.proposal.distributed': {
    title: '方案已分发',
    icon: '📋',
    color: 'blue'
  },
  'towow.proposal.feedback': {
    title: '收到反馈',
    icon: '💬',
    color: 'purple'
  },
  'towow.negotiation.round_started': {
    title: '新一轮协商开始',
    icon: '🔄',
    color: 'orange'
  },
  'towow.proposal.finalized': {
    title: '方案已确定',
    icon: '✅',
    color: 'green'
  },
  'towow.negotiation.failed': {
    title: '协商失败',
    icon: '❌',
    color: 'red'
  },
  'towow.agent.withdrawn': {
    title: '参与者退出',
    icon: '👋',
    color: 'gray'
  },
  'towow.gap.identified': {
    title: '缺口已识别',
    icon: '🔎',
    color: 'yellow'
  },
  'towow.subnet.triggered': {
    title: '子网协商已触发',
    icon: '🌐',
    color: 'purple'
  }
};

export const EventTimeline: React.FC<EventTimelineProps> = ({ demandId }) => {
  const { events } = useEventStore();

  // 过滤当前需求的事件
  const relevantEvents = events.filter(e => {
    const payload = e.payload || {};
    return payload.demand_id === demandId ||
           payload.channel_id?.includes(demandId.slice(2, 10));
  });

  // 格式化时间
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // 生成事件描述
  const getEventDescription = (event: any): string => {
    const payload = event.payload || {};
    const eventType = event.event_type;

    switch (eventType) {
      case 'towow.offer.submitted':
        const decision = payload.decision === 'participate' ? '愿意参与' :
                        payload.decision === 'decline' ? '婉拒' : '有条件参与';
        return `${payload.display_name || payload.agent_id}: ${decision}`;

      case 'towow.proposal.feedback':
        const feedback = payload.feedback_type === 'accept' ? '接受方案' :
                        payload.feedback_type === 'negotiate' ? '希望调整' : '退出';
        return `${payload.agent_id}: ${feedback}`;

      case 'towow.negotiation.round_started':
        return `第 ${payload.round} 轮协商`;

      case 'towow.filter.completed':
        return `找到 ${payload.candidates_count || payload.candidates?.length} 位候选人`;

      case 'towow.proposal.finalized':
        return `${payload.participants_count} 位参与者达成共识`;

      case 'towow.negotiation.failed':
        return payload.reason || '协商未能达成共识';

      case 'towow.agent.withdrawn':
        return `${payload.display_name || payload.agent_id} 退出: ${payload.reason}`;

      default:
        return '';
    }
  };

  return (
    <div className="event-timeline">
      <h3>协商进度</h3>

      <div className="timeline-container">
        {relevantEvents.map((event, index) => {
          const display = EVENT_DISPLAY[event.event_type] || {
            title: event.event_type,
            icon: '📌',
            color: 'gray'
          };
          const description = getEventDescription(event);

          return (
            <div
              key={event.event_id || index}
              className={`timeline-item timeline-item--${display.color}`}
            >
              <div className="timeline-item__icon">{display.icon}</div>
              <div className="timeline-item__content">
                <div className="timeline-item__header">
                  <span className="title">{display.title}</span>
                  <span className="time">{formatTime(event.timestamp)}</span>
                </div>
                {description && (
                  <div className="timeline-item__description">
                    {description}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {relevantEvents.length === 0 && (
          <div className="timeline-empty">
            等待协商开始...
          </div>
        )}
      </div>
    </div>
  );
};
```

#### 3. 增强 useSSE

```tsx
// towow-frontend/src/hooks/useSSE.ts

import { useEffect, useRef, useCallback } from 'react';
import { useEventStore } from '@/stores/eventStore';

interface UseSSEOptions {
  demandId: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
}

export const useSSE = ({ demandId, onConnect, onDisconnect, onError }: UseSSEOptions) => {
  const { addEvent, setConnectionStatus } = useEventStore();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const lastEventIdRef = useRef<string | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000; // 3 秒

  const connect = useCallback(() => {
    // 清理现有连接
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // 构建 URL，支持断线重连
    let url = `/api/v1/events/negotiations/${demandId}/stream`;
    if (lastEventIdRef.current) {
      url += `?last_event_id=${lastEventIdRef.current}`;
    }

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnectionStatus('connected');
      reconnectAttemptsRef.current = 0;
      onConnect?.();
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // 记录最后的事件 ID
        if (data.event_id) {
          lastEventIdRef.current = data.event_id;
        }
        addEvent(data);
      } catch (e) {
        console.error('解析 SSE 消息失败:', e);
      }
    };

    eventSource.onerror = (error) => {
      setConnectionStatus('disconnected');
      onDisconnect?.();

      // 尝试重连
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current += 1;
        console.log(`SSE 连接断开，${RECONNECT_DELAY / 1000}秒后重试 (${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);

        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, RECONNECT_DELAY);
      } else {
        console.error('SSE 重连次数超限');
        onError?.(new Error('SSE 连接失败'));
      }
    };
  }, [demandId, addEvent, setConnectionStatus, onConnect, onDisconnect, onError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, [setConnectionStatus]);

  useEffect(() => {
    if (demandId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [demandId, connect, disconnect]);

  return {
    disconnect,
    reconnect: connect,
    isConnected: eventSourceRef.current?.readyState === EventSource.OPEN
  };
};
```

#### 4. 优化 eventStore

```tsx
// towow-frontend/src/stores/eventStore.ts

import { create } from 'zustand';

interface SSEEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  payload: Record<string, any>;
}

interface EventStore {
  events: SSEEvent[];
  connectionStatus: 'connecting' | 'connected' | 'disconnected';
  addEvent: (event: SSEEvent) => void;
  clearEvents: () => void;
  setConnectionStatus: (status: 'connecting' | 'connected' | 'disconnected') => void;
  getLatestProposal: (demandId: string) => any | null;
  getEventsByType: (eventType: string) => SSEEvent[];
}

export const useEventStore = create<EventStore>((set, get) => ({
  events: [],
  connectionStatus: 'disconnected',

  addEvent: (event) => {
    set((state) => {
      // 去重：检查 event_id 是否已存在
      if (state.events.some(e => e.event_id === event.event_id)) {
        return state;
      }
      return {
        events: [...state.events, event]
      };
    });
  },

  clearEvents: () => {
    set({ events: [] });
  },

  setConnectionStatus: (status) => {
    set({ connectionStatus: status });
  },

  getLatestProposal: (demandId) => {
    const events = get().events;

    // 查找最新的方案事件
    const proposalEvents = events
      .filter(e =>
        (e.event_type === 'towow.proposal.distributed' ||
         e.event_type === 'towow.proposal.finalized') &&
        (e.payload?.demand_id === demandId ||
         e.payload?.channel_id?.includes(demandId.slice(2, 10)))
      )
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    if (proposalEvents.length > 0) {
      const latest = proposalEvents[0];
      return latest.payload.final_proposal || latest.payload.proposal;
    }

    return null;
  },

  getEventsByType: (eventType) => {
    return get().events.filter(e => e.event_type === eventType);
  }
}));
```

---

## 接口契约

### SSE 事件格式

```typescript
interface SSEEvent {
  event_id: string;       // evt-abc12345
  event_type: string;     // towow.xxx.xxx
  timestamp: string;      // ISO 8601
  payload: {
    demand_id?: string;
    channel_id?: string;
    // ... 其他字段
  };
}
```

### 前端状态

```typescript
interface NegotiationState {
  status: 'pending' | 'filtering' | 'collecting' | 'aggregating' | 'negotiating' | 'finalized' | 'failed';
  candidates: Candidate[];
  proposal: Proposal | null;
  events: SSEEvent[];
  currentRound: number;
}
```

---

## 依赖

### 硬依赖
- 无

### 接口依赖
- **T01**: API 接口契约
- **T05**: 事件类型定义

### 被依赖
- **T08**: E2E 测试

---

## 验收标准

- [ ] **AC-1**: 方案卡片在协商完成后正常展示
- [ ] **AC-2**: 事件时间线展示所有关键事件
- [ ] **AC-3**: 候选人状态实时更新（参与/拒绝/退出）
- [ ] **AC-4**: SSE 断线后 3 秒内自动重连
- [ ] **AC-5**: 重连后不丢失历史事件
- [ ] **AC-6**: 支持 5 次重连尝试

### 测试用例

```typescript
// 手动测试场景

// 1. 方案卡片展示
// - 提交需求后，方案卡片显示"生成中"
// - 方案生成后，展示方案详情
// - 协商完成后，方案卡片保持展示

// 2. 事件时间线
// - 每个事件都有对应的图标和描述
// - 事件按时间顺序排列
// - 新事件实时添加

// 3. SSE 重连
// - 断开网络后，3秒内自动重连
// - 重连后历史事件不丢失
// - 5次重连失败后显示错误提示
```

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| ProposalCard 修复 | 1h |
| EventTimeline 完善 | 1h |
| useSSE 增强 | 0.5h |
| eventStore 优化 | 0.5h |
| **总计** | **3h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| SSE 兼容性问题 | 部分浏览器不支持 | 提供轮询降级方案 |
| 事件丢失 | 状态不一致 | 断线重连带 last_event_id |
| 状态同步延迟 | 用户体验差 | 添加 loading 状态提示 |

---

## 实现记录

*(开发完成后填写)*

---

## 测试记录

*(测试完成后填写)*
