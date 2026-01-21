# TASK-017：协商过程实时展示

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-017 |
| 所属Phase | Phase 5：前端开发 |
| 硬依赖 | TASK-015, TASK-018 |
| 接口依赖 | - |
| 可并行 | - |
| 预估工作量 | 1.5天 |
| 状态 | 待开始 |
| 关键路径 | YES |

---

## 任务描述

实现协商过程的实时展示页面，这是2000人现场演示的核心页面。需要实时展示：
- 协商时间线
- 当前方案
- 参与者回应状态

---

## 页面设计

### 布局示意

```
┌─────────────────────────────────────────────────────────────┐
│  需求：我想在北京办一场50人的AI主题聚会                       │
│  状态：协商中（第2轮）                                       │
├───────────────────────┬─────────────────────────────────────┤
│                       │                                     │
│   协商时间线           │         当前方案                    │
│                       │                                     │
│   * 需求已理解         │  ┌─────────────────────────────┐   │
│     12:00:05          │  │ 方案v2                       │   │
│                       │  │                             │   │
│   * 筛选完成           │  │ 时间：2月16日 14:00-17:00   │   │
│     12:00:08          │  │ 地点：朝阳区某会议室         │   │
│     邀请了15位候选人    │  │                             │   │
│                       │  │ 参与者：                     │   │
│   * 收到回应 (8/15)    │  │ - Bob - 场地提供            │   │
│     12:01:30          │  │ - Alice - 技术分享          │   │
│                       │  │ - Charlie - 活动策划        │   │
│   * 方案v1生成         │  │                             │   │
│     12:02:00          │  │ 待确认：是否需要下午茶？     │   │
│                       │  └─────────────────────────────┘   │
│   * 收到反馈           │                                     │
│     12:02:45          │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│     Bob: 时间需调整    │                                     │
│                       │         参与者回应                   │
│   o 方案调整中...      │                                     │
│                       │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐   │
│                       │  │ Bob │ │Alice│ │Charl│ │ ... │   │
│                       │  │  V  │ │  V  │ │ ... │ │     │   │
│                       │  └─────┘ └─────┘ └─────┘ └─────┘   │
│                       │                                     │
└───────────────────────┴─────────────────────────────────────┘
```

---

## 具体工作

### 1. 协商页面主组件

`src/features/negotiation/NegotiationPage.tsx`:

```tsx
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Row, Col, Typography, Tag, Timeline, Avatar, Spin, Result } from 'antd';
import {
  CheckCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  UserOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { motion, AnimatePresence } from 'framer-motion';
import { useSSE } from '../../hooks/useSSE';
import { TimelineEvent, Participant, Proposal, SSEEvent } from '../../types';
import { useDemandStore } from '../../stores/demandStore';
import './NegotiationPage.css';

const { Title, Text, Paragraph } = Typography;

export const NegotiationPage: React.FC = () => {
  const { demandId } = useParams<{ demandId: string }>();
  const { currentDemand } = useDemandStore();

  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [currentProposal, setCurrentProposal] = useState<Proposal | null>(null);
  const [status, setStatus] = useState<string>('processing');
  const [round, setRound] = useState(0);
  const [demandText, setDemandText] = useState('');

  // SSE连接
  const { connected, lastEvent, error, reconnect } = useSSE(
    `/api/events/stream/${demandId}`
  );

  // 初始化需求文本
  useEffect(() => {
    if (currentDemand) {
      setDemandText(currentDemand.understanding?.surface_demand || '');
    }
  }, [currentDemand]);

  // 处理SSE事件
  useEffect(() => {
    if (!lastEvent) return;

    const { event_type, payload } = lastEvent as SSEEvent;

    switch (event_type) {
      case 'towow.demand.understood':
        addTimelineEvent({
          id: payload.event_id,
          type: 'understand',
          timestamp: payload.timestamp,
          title: '需求已理解',
          description: payload.surface_demand,
          status: 'done',
        });
        setDemandText(payload.surface_demand);
        break;

      case 'towow.filter.completed':
        addTimelineEvent({
          id: payload.event_id,
          type: 'filter',
          timestamp: payload.timestamp,
          title: '筛选完成',
          description: `邀请了${payload.candidates?.length || 0}位候选人`,
          status: 'done',
        });
        setParticipants(
          payload.candidates?.map((c: any) => ({
            agent_id: c.agent_id,
            name: extractName(c.agent_id),
            status: 'pending',
          })) || []
        );
        break;

      case 'towow.offer.submitted':
        updateParticipant(payload.agent_id, {
          status: payload.decision === 'participate' ? 'accepted' : 'declined',
          contribution: payload.contribution,
          role: payload.role,
        });
        break;

      case 'towow.proposal.distributed':
        setCurrentProposal({
          version: payload.proposal_version,
          summary: payload.summary,
          assignments: payload.assignments,
          timeline: payload.timeline,
          open_questions: payload.open_questions,
          confidence: payload.confidence || 'medium',
        });
        setRound((r) => r + 1);
        addTimelineEvent({
          id: payload.event_id,
          type: 'proposal',
          timestamp: payload.timestamp,
          title: `方案v${payload.proposal_version}生成`,
          status: 'done',
        });
        break;

      case 'towow.proposal.feedback':
        updateParticipant(payload.agent_id, {
          status: payload.feedback_type === 'accept' ? 'accepted' : 'negotiating',
        });
        if (payload.feedback_type === 'negotiate') {
          addTimelineEvent({
            id: payload.event_id,
            type: 'feedback',
            timestamp: payload.timestamp,
            title: '收到反馈',
            description: `${extractName(payload.agent_id)}: ${payload.adjustment_request}`,
            status: 'done',
          });
        }
        break;

      case 'towow.proposal.finalized':
        setStatus('completed');
        addTimelineEvent({
          id: payload.event_id,
          type: 'finalized',
          timestamp: payload.timestamp,
          title: '方案确定！',
          status: 'done',
        });
        break;

      case 'towow.negotiation.failed':
        setStatus('failed');
        addTimelineEvent({
          id: payload.event_id,
          type: 'failed',
          timestamp: payload.timestamp,
          title: '协商失败',
          description: payload.reason,
          status: 'done',
        });
        break;
    }
  }, [lastEvent]);

  const addTimelineEvent = (event: TimelineEvent) => {
    setTimelineEvents((prev) => [...prev, event]);
  };

  const updateParticipant = (agentId: string, update: Partial<Participant>) => {
    setParticipants((prev) =>
      prev.map((p) => (p.agent_id === agentId ? { ...p, ...update } : p))
    );
  };

  const extractName = (agentId: string): string => {
    return agentId.replace('user_agent_', '').replace('demo_', '');
  };

  const getStatusTag = () => {
    switch (status) {
      case 'processing':
        return (
          <Tag icon={<SyncOutlined spin />} color="processing">
            协商中（第{round}轮）
          </Tag>
        );
      case 'completed':
        return (
          <Tag icon={<CheckCircleOutlined />} color="success">
            已完成
          </Tag>
        );
      case 'failed':
        return (
          <Tag icon={<ExclamationCircleOutlined />} color="error">
            协商失败
          </Tag>
        );
      default:
        return (
          <Tag icon={<ClockCircleOutlined />} color="default">
            等待中
          </Tag>
        );
    }
  };

  const getParticipantStatus = (participantStatus: string) => {
    switch (participantStatus) {
      case 'accepted':
        return { icon: 'V', color: '#52c41a' };
      case 'declined':
        return { icon: 'X', color: '#ff4d4f' };
      case 'negotiating':
        return { icon: '~', color: '#faad14' };
      default:
        return { icon: '...', color: '#d9d9d9' };
    }
  };

  if (error && !connected) {
    return (
      <div className="negotiation-page">
        <Result
          status="warning"
          title="连接断开"
          subTitle="正在尝试重新连接..."
          extra={
            <button onClick={reconnect}>重新连接</button>
          }
        />
      </div>
    );
  }

  return (
    <div className="negotiation-page">
      <Card className="header-card">
        <Title level={4}>需求：{demandText || '加载中...'}</Title>
        <div className="status-bar">
          {getStatusTag()}
          {!connected && <Tag color="orange">重连中...</Tag>}
        </div>
      </Card>

      <Row gutter={24} className="main-content">
        {/* 左侧：时间线 */}
        <Col span={8}>
          <Card title="协商时间线" className="timeline-card">
            <Timeline mode="left">
              <AnimatePresence>
                {timelineEvents.map((event, index) => (
                  <motion.div
                    key={event.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <Timeline.Item
                      color={
                        event.status === 'done'
                          ? 'green'
                          : event.status === 'active'
                          ? 'blue'
                          : 'gray'
                      }
                      label={formatTime(event.timestamp)}
                    >
                      <Text strong>{event.title}</Text>
                      {event.description && (
                        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                          {event.description}
                        </Paragraph>
                      )}
                    </Timeline.Item>
                  </motion.div>
                ))}
              </AnimatePresence>
              {status === 'processing' && (
                <Timeline.Item color="blue" dot={<SyncOutlined spin />}>
                  <Text type="secondary">处理中...</Text>
                </Timeline.Item>
              )}
            </Timeline>
          </Card>
        </Col>

        {/* 右侧：方案和参与者 */}
        <Col span={16}>
          {/* 当前方案 */}
          {currentProposal && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card
                title={`方案v${currentProposal.version}`}
                className="proposal-card"
              >
                <Paragraph>{currentProposal.summary}</Paragraph>
                {currentProposal.timeline && (
                  <Paragraph>
                    <Text strong>时间：</Text>
                    {currentProposal.timeline}
                  </Paragraph>
                )}
                <div className="assignments">
                  <Text strong>参与者分工：</Text>
                  {currentProposal.assignments.map((a, i) => (
                    <div key={i} className="assignment-item">
                      <Avatar size="small" icon={<UserOutlined />} />
                      <Text>
                        {extractName(a.agent_id)} - {a.role}
                      </Text>
                    </div>
                  ))}
                </div>
                {currentProposal.open_questions &&
                  currentProposal.open_questions.length > 0 && (
                    <div className="open-questions">
                      <Text type="secondary">
                        待确认：{currentProposal.open_questions.join('、')}
                      </Text>
                    </div>
                  )}
              </Card>
            </motion.div>
          )}

          {/* 参与者状态 */}
          <Card title="参与者回应" className="participants-card">
            <div className="participants-grid">
              <AnimatePresence>
                {participants.map((p, index) => {
                  const statusInfo = getParticipantStatus(p.status);
                  return (
                    <motion.div
                      key={p.agent_id}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: index * 0.05 }}
                      className="participant-item"
                    >
                      <Avatar style={{ backgroundColor: statusInfo.color }}>
                        {statusInfo.icon}
                      </Avatar>
                      <Text>{p.name}</Text>
                      {p.role && <Text type="secondary">{p.role}</Text>}
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// 辅助函数
function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}
```

### 2. 样式文件

`src/features/negotiation/NegotiationPage.css`:

```css
.negotiation-page {
  min-height: 100vh;
  padding: 24px;
  background: #f0f2f5;
}

.header-card {
  margin-bottom: 24px;
}

.header-card h4 {
  margin-bottom: 8px;
}

.status-bar {
  display: flex;
  gap: 8px;
}

.main-content {
  margin-top: 24px;
}

.timeline-card {
  height: calc(100vh - 200px);
  overflow-y: auto;
}

.proposal-card {
  margin-bottom: 24px;
}

.assignments {
  margin-top: 16px;
}

.assignment-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.open-questions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e8e8e8;
}

.participants-card {
  margin-top: 24px;
}

.participants-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 16px;
}

.participant-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}
```

### 3. SSE Hook

`src/hooks/useSSE.ts`:

```typescript
import { useState, useEffect, useCallback, useRef } from 'react';
import { SSEEvent } from '../types';

interface SSEHookResult {
  connected: boolean;
  lastEvent: SSEEvent | null;
  error: Error | null;
  reconnect: () => void;
}

export const useSSE = (url: string): SSEHookResult => {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const lastEventIdRef = useRef<string | null>(null);

  const connect = useCallback(() => {
    const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

    // 带上lastEventId实现断点续传
    let fullUrl = `${API_BASE}${url}`;
    if (lastEventIdRef.current) {
      fullUrl += `?last_event_id=${lastEventIdRef.current}`;
    }

    const eventSource = new EventSource(fullUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
      setReconnectCount(0);
      console.log('SSE connected');
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SSEEvent;
        // 记录最后的事件ID
        if (data.event_id) {
          lastEventIdRef.current = data.event_id;
        }
        setLastEvent(data);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    eventSource.onerror = () => {
      setConnected(false);
      setError(new Error('SSE connection error'));
      console.error('SSE error, reconnecting...');

      // 指数退避重连
      const delay = Math.min(1000 * Math.pow(2, reconnectCount), 30000);
      console.log(`Reconnecting in ${delay}ms...`);

      setTimeout(() => {
        if (eventSourceRef.current === eventSource) {
          setReconnectCount((c) => c + 1);
          connect();
        }
      }, delay);
    };

    return eventSource;
  }, [url, reconnectCount]);

  useEffect(() => {
    const eventSource = connect();

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [connect]);

  const reconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setReconnectCount(0);
    connect();
  }, [connect]);

  return { connected, lastEvent, error, reconnect };
};
```

---

## 接口契约

### SSE事件格式（TASK-018提供）

```typescript
interface SSEEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  payload: Record<string, any>;
}
```

### 事件类型列表

| 事件类型 | 说明 | payload主要字段 |
|---------|------|----------------|
| `towow.demand.understood` | 需求理解完成 | surface_demand |
| `towow.filter.completed` | 筛选完成 | candidates[] |
| `towow.offer.submitted` | 收到回应 | agent_id, decision, contribution |
| `towow.proposal.distributed` | 方案分发 | proposal_version, summary, assignments[] |
| `towow.proposal.feedback` | 收到反馈 | agent_id, feedback_type, adjustment_request |
| `towow.proposal.finalized` | 方案确定 | final_proposal |
| `towow.negotiation.failed` | 协商失败 | reason |

---

## 验收标准

- [ ] 页面正常显示
- [ ] SSE连接成功，状态指示正确
- [ ] 时间线实时更新，动画流畅
- [ ] 参与者状态实时更新
- [ ] 方案展示正确，格式美观
- [ ] 断线重连机制正常工作
- [ ] 协商完成/失败状态展示正确
- [ ] 适配大屏展示（字体、间距）

---

## 产出物

- `src/features/negotiation/NegotiationPage.tsx`
- `src/features/negotiation/NegotiationPage.css`
- `src/hooks/useSSE.ts`

---

**创建时间**: 2026-01-21
**来源**: supplement-03-frontend.md
**关键路径**: YES - 2000人演示核心页面

> Beads 任务ID：`towow-lab`
