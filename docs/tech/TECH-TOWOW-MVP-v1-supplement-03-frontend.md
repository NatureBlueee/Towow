# 技术方案补充03：前端任务与实时推送

> 前端开发任务、实时推送机制、大屏展示设计

---

## 一、前端需求分析

### 1.1 核心需求（来自设计文档）

| 需求 | 优先级 | 说明 |
|------|--------|------|
| 需求提交界面 | P0 | 用户输入需求的入口 |
| 协商过程实时展示 | P0 | 2000人现场核心展示 |
| 最终方案展示 | P0 | 展示协作结果 |
| Agent状态展示 | P1 | 显示在线Agent数量等 |
| 大屏可视化 | P1 | 现场大屏展示 |

### 1.2 技术选型

| 项目 | 选型 | 理由 |
|------|------|------|
| 框架 | **React 18** | 生态成熟、团队熟悉 |
| UI库 | **Ant Design** | 组件丰富、快速开发 |
| 状态管理 | **Zustand** | 轻量、简单 |
| 实时通信 | **SSE** | 单向推送足够、比WebSocket简单 |
| 动画 | **Framer Motion** | 流畅的过渡动画 |

---

## 二、新增TASK文档

### TASK-015：前端项目初始化

```markdown
# TASK-015：前端项目初始化

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-015 |
| 所属Phase | Phase 4：演示准备 |
| 依赖 | - |
| 预估工作量 | 0.5天 |
| 状态 | 待开始 |

---

## 任务描述

初始化React前端项目，配置基础依赖和项目结构。

---

## 具体工作

### 1. 创建项目

```bash
npx create-react-app towow-frontend --template typescript
cd towow-frontend
```

### 2. 安装依赖

```bash
# UI组件
npm install antd @ant-design/icons

# 状态管理
npm install zustand

# 动画
npm install framer-motion

# HTTP请求
npm install axios

# 路由
npm install react-router-dom

# 工具
npm install dayjs lodash-es
npm install -D @types/lodash-es
```

### 3. 项目结构

```
towow-frontend/
├── src/
│   ├── api/                 # API调用
│   │   ├── client.ts
│   │   ├── demand.ts
│   │   └── events.ts
│   ├── components/          # 通用组件
│   │   ├── common/
│   │   └── layout/
│   ├── features/            # 功能模块
│   │   ├── demand/         # 需求提交
│   │   ├── negotiation/    # 协商展示
│   │   └── dashboard/      # 大屏展示
│   ├── hooks/               # 自定义Hooks
│   │   └── useSSE.ts
│   ├── stores/              # 状态管理
│   │   ├── demandStore.ts
│   │   └── eventStore.ts
│   ├── types/               # 类型定义
│   │   └── index.ts
│   ├── utils/               # 工具函数
│   ├── App.tsx
│   └── index.tsx
├── public/
└── package.json
```

### 4. 基础配置

```typescript
// src/api/client.ts
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// SSE连接
export const createSSEConnection = (endpoint: string): EventSource => {
  return new EventSource(`${API_BASE}${endpoint}`);
};
```

---

## 验收标准

- [ ] 项目可以正常启动（npm start）
- [ ] 依赖安装完成
- [ ] 目录结构创建完成
- [ ] 基础配置完成

---

## 产出物

- `towow-frontend/` 目录
- 项目基础结构
```

---

### TASK-016：需求提交页面

```markdown
# TASK-016：需求提交页面

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-016 |
| 所属Phase | Phase 4：演示准备 |
| 依赖 | TASK-015 |
| 预估工作量 | 1天 |
| 状态 | 待开始 |

---

## 任务描述

实现用户提交需求的页面，包括输入框、提交按钮、状态反馈。

---

## 页面设计

### 布局

```
┌─────────────────────────────────────────┐
│              ToWow 协作网络              │
│         让AI帮你找到合作伙伴             │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │                                 │   │
│  │   说说你想做什么...              │   │
│  │                                 │   │
│  │                                 │   │
│  └─────────────────────────────────┘   │
│                                         │
│              [ 发起协作 ]               │
│                                         │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│                                         │
│  💡 示例：                              │
│  • 我想在北京办一场AI主题聚会           │
│  • 找一个懂设计的人帮我做产品原型        │
│  • 组织一次周末徒步活动                 │
│                                         │
└─────────────────────────────────────────┘
```

### 实现代码

```tsx
// src/features/demand/DemandSubmitPage.tsx
import React, { useState } from 'react';
import { Input, Button, Card, Typography, Space, message } from 'antd';
import { SendOutlined, BulbOutlined } from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { demandApi } from '../../api/demand';
import { useDemandStore } from '../../stores/demandStore';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

const EXAMPLES = [
  '我想在北京办一场50人的AI主题聚会',
  '找一个懂AI的设计师帮我做产品原型',
  '组织一次周末在郊区的徒步活动',
];

export const DemandSubmitPage: React.FC = () => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setCurrentDemand } = useDemandStore();

  const handleSubmit = async () => {
    if (!input.trim()) {
      message.warning('请输入你的需求');
      return;
    }

    setLoading(true);
    try {
      const result = await demandApi.submit(input);
      setCurrentDemand(result);
      message.success('需求已提交，正在寻找合作伙伴...');
      navigate(`/negotiation/${result.demand_id}`);
    } catch (error) {
      message.error('提交失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleExampleClick = (example: string) => {
    setInput(example);
  };

  return (
    <div className="demand-submit-page">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Card className="submit-card">
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div className="header">
              <Title level={2}>ToWow 协作网络</Title>
              <Text type="secondary">让AI帮你找到合作伙伴</Text>
            </div>

            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="说说你想做什么..."
              autoSize={{ minRows: 4, maxRows: 8 }}
              maxLength={500}
              showCount
            />

            <Button
              type="primary"
              size="large"
              icon={<SendOutlined />}
              onClick={handleSubmit}
              loading={loading}
              block
            >
              发起协作
            </Button>

            <div className="examples">
              <Space>
                <BulbOutlined />
                <Text type="secondary">示例：</Text>
              </Space>
              <div className="example-list">
                {EXAMPLES.map((example, index) => (
                  <motion.div
                    key={index}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Button
                      type="text"
                      onClick={() => handleExampleClick(example)}
                    >
                      • {example}
                    </Button>
                  </motion.div>
                ))}
              </div>
            </div>
          </Space>
        </Card>
      </motion.div>
    </div>
  );
};
```

```typescript
// src/api/demand.ts
import { apiClient } from './client';

export interface DemandSubmitResult {
  demand_id: string;
  channel_id: string;
  status: string;
  understanding: {
    surface_demand: string;
    confidence: string;
  };
}

export const demandApi = {
  submit: async (rawInput: string): Promise<DemandSubmitResult> => {
    const response = await apiClient.post('/api/demand/submit', {
      raw_input: rawInput,
    });
    return response.data;
  },
};
```

---

## 验收标准

- [ ] 页面正常显示
- [ ] 可以输入需求文本
- [ ] 点击提交后调用API
- [ ] 提交成功后跳转到协商页面
- [ ] 示例点击可以填充输入框

---

## 产出物

- `DemandSubmitPage.tsx`
- `demand.ts` API封装
- 相关样式文件
```

---

### TASK-017：协商过程实时展示

```markdown
# TASK-017：协商过程实时展示

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-017 |
| 所属Phase | Phase 4：演示准备 |
| 依赖 | TASK-015, TASK-018 |
| 预估工作量 | 1.5天 |
| 状态 | 待开始 |

---

## 任务描述

实现协商过程的实时展示页面，这是2000人现场演示的核心页面。

---

## 页面设计

### 布局

```
┌─────────────────────────────────────────────────────────────┐
│  需求：我想在北京办一场50人的AI主题聚会                       │
│  状态：🔄 协商中（第2轮）                                    │
├───────────────────────┬─────────────────────────────────────┤
│                       │                                     │
│   协商时间线           │         当前方案                    │
│                       │                                     │
│   ● 需求已理解         │  ┌─────────────────────────────┐   │
│     12:00:05          │  │ 📋 方案v2                    │   │
│                       │  │                             │   │
│   ● 筛选完成           │  │ 时间：2月16日 14:00-17:00   │   │
│     12:00:08          │  │ 地点：朝阳区某会议室         │   │
│     邀请了15位候选人    │  │                             │   │
│                       │  │ 参与者：                     │   │
│   ● 收到回应 (8/15)    │  │ • Bob - 场地提供            │   │
│     12:01:30          │  │ • Alice - 技术分享          │   │
│                       │  │ • Charlie - 活动策划        │   │
│   ● 方案v1生成         │  │                             │   │
│     12:02:00          │  │ 待确认：是否需要下午茶？     │   │
│                       │  └─────────────────────────────┘   │
│   ● 收到反馈           │                                     │
│     12:02:45          │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│     Bob: 时间需调整    │                                     │
│                       │         参与者回应                   │
│   ○ 方案调整中...      │                                     │
│                       │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐   │
│                       │  │ Bob │ │Alice│ │Charl│ │ ... │   │
│                       │  │ ✓   │ │ ✓   │ │ ⏳  │ │     │   │
│                       │  └─────┘ └─────┘ └─────┘ └─────┘   │
│                       │                                     │
└───────────────────────┴─────────────────────────────────────┘
```

### 实现代码

```tsx
// src/features/negotiation/NegotiationPage.tsx
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Row, Col, Typography, Tag, Timeline, Avatar, Spin } from 'antd';
import {
  CheckCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  UserOutlined
} from '@ant-design/icons';
import { motion, AnimatePresence } from 'framer-motion';
import { useSSE } from '../../hooks/useSSE';
import { useEventStore } from '../../stores/eventStore';

const { Title, Text, Paragraph } = Typography;

interface TimelineEvent {
  id: string;
  type: string;
  timestamp: string;
  title: string;
  description?: string;
  status: 'done' | 'active' | 'pending';
}

interface Participant {
  agent_id: string;
  name: string;
  role?: string;
  status: 'pending' | 'accepted' | 'declined' | 'negotiating';
  contribution?: string;
}

interface Proposal {
  version: number;
  summary: string;
  assignments: Array<{
    agent_id: string;
    role: string;
    responsibility: string;
  }>;
  timeline?: string;
  open_questions?: string[];
}

export const NegotiationPage: React.FC = () => {
  const { demandId } = useParams<{ demandId: string }>();
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [currentProposal, setCurrentProposal] = useState<Proposal | null>(null);
  const [status, setStatus] = useState<string>('processing');
  const [round, setRound] = useState(0);

  // SSE连接
  const { connected, lastEvent } = useSSE(`/api/events/stream/${demandId}`);

  // 处理SSE事件
  useEffect(() => {
    if (!lastEvent) return;

    const { event_type, payload } = lastEvent;

    switch (event_type) {
      case 'towow.filter.completed':
        setTimelineEvents(prev => [...prev, {
          id: payload.event_id,
          type: 'filter',
          timestamp: payload.timestamp,
          title: '筛选完成',
          description: `邀请了${payload.candidates?.length || 0}位候选人`,
          status: 'done'
        }]);
        setParticipants(payload.candidates?.map((c: any) => ({
          agent_id: c.agent_id,
          name: c.agent_id.replace('user_agent_', ''),
          status: 'pending'
        })) || []);
        break;

      case 'towow.offer.submitted':
        setParticipants(prev => prev.map(p =>
          p.agent_id === payload.agent_id
            ? { ...p, status: payload.decision === 'participate' ? 'accepted' : 'declined', contribution: payload.contribution }
            : p
        ));
        break;

      case 'towow.proposal.distributed':
        setCurrentProposal({
          version: payload.proposal_version,
          summary: payload.summary,
          assignments: payload.assignments,
          timeline: payload.timeline,
          open_questions: payload.open_questions
        });
        setRound(r => r + 1);
        setTimelineEvents(prev => [...prev, {
          id: payload.event_id,
          type: 'proposal',
          timestamp: payload.timestamp,
          title: `方案v${payload.proposal_version}生成`,
          status: 'done'
        }]);
        break;

      case 'towow.proposal.feedback':
        setParticipants(prev => prev.map(p =>
          p.agent_id === payload.agent_id
            ? { ...p, status: payload.feedback_type === 'accept' ? 'accepted' : 'negotiating' }
            : p
        ));
        if (payload.feedback_type === 'negotiate') {
          setTimelineEvents(prev => [...prev, {
            id: payload.event_id,
            type: 'feedback',
            timestamp: payload.timestamp,
            title: '收到反馈',
            description: `${payload.agent_id.replace('user_agent_', '')}: ${payload.adjustment_request}`,
            status: 'done'
          }]);
        }
        break;

      case 'towow.proposal.finalized':
        setStatus('completed');
        setTimelineEvents(prev => [...prev, {
          id: payload.event_id,
          type: 'finalized',
          timestamp: payload.timestamp,
          title: '🎉 方案确定！',
          status: 'done'
        }]);
        break;
    }
  }, [lastEvent]);

  const getStatusTag = () => {
    switch (status) {
      case 'processing':
        return <Tag icon={<SyncOutlined spin />} color="processing">协商中（第{round}轮）</Tag>;
      case 'completed':
        return <Tag icon={<CheckCircleOutlined />} color="success">已完成</Tag>;
      default:
        return <Tag icon={<ClockCircleOutlined />} color="default">等待中</Tag>;
    }
  };

  const getParticipantStatus = (status: string) => {
    switch (status) {
      case 'accepted':
        return { icon: '✓', color: '#52c41a' };
      case 'declined':
        return { icon: '✗', color: '#ff4d4f' };
      case 'negotiating':
        return { icon: '⟳', color: '#faad14' };
      default:
        return { icon: '⏳', color: '#d9d9d9' };
    }
  };

  return (
    <div className="negotiation-page">
      <Card className="header-card">
        <Title level={4}>需求：我想在北京办一场50人的AI主题聚会</Title>
        <div className="status-bar">
          {getStatusTag()}
          {!connected && <Tag color="error">连接断开</Tag>}
        </div>
      </Card>

      <Row gutter={24}>
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
                      color={event.status === 'done' ? 'green' : event.status === 'active' ? 'blue' : 'gray'}
                      label={new Date(event.timestamp).toLocaleTimeString()}
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
              <Card title={`📋 方案v${currentProposal.version}`} className="proposal-card">
                <Paragraph>{currentProposal.summary}</Paragraph>
                {currentProposal.timeline && (
                  <Paragraph>
                    <Text strong>时间：</Text>{currentProposal.timeline}
                  </Paragraph>
                )}
                <div className="assignments">
                  <Text strong>参与者分工：</Text>
                  {currentProposal.assignments.map((a, i) => (
                    <div key={i} className="assignment-item">
                      <Avatar size="small" icon={<UserOutlined />} />
                      <Text>{a.agent_id.replace('user_agent_', '')} - {a.role}</Text>
                    </div>
                  ))}
                </div>
                {currentProposal.open_questions && currentProposal.open_questions.length > 0 && (
                  <div className="open-questions">
                    <Text type="secondary">待确认：{currentProposal.open_questions.join('、')}</Text>
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
                      <Avatar
                        style={{ backgroundColor: statusInfo.color }}
                      >
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
```

```typescript
// src/hooks/useSSE.ts
import { useState, useEffect, useCallback, useRef } from 'react';

interface SSEHookResult {
  connected: boolean;
  lastEvent: any;
  error: Error | null;
  reconnect: () => void;
}

export const useSSE = (url: string): SSEHookResult => {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const fullUrl = `${API_BASE}${url}`;

    const eventSource = new EventSource(fullUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
      console.log('SSE connected');
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastEvent(data);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    eventSource.onerror = (e) => {
      setConnected(false);
      setError(new Error('SSE connection error'));
      console.error('SSE error:', e);

      // 自动重连
      setTimeout(() => {
        if (eventSourceRef.current === eventSource) {
          connect();
        }
      }, 3000);
    };

    return eventSource;
  }, [url]);

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
    connect();
  }, [connect]);

  return { connected, lastEvent, error, reconnect };
};
```

---

## 验收标准

- [ ] 页面正常显示
- [ ] SSE连接成功
- [ ] 时间线实时更新
- [ ] 参与者状态实时更新
- [ ] 方案展示正确
- [ ] 动画流畅

---

## 产出物

- `NegotiationPage.tsx`
- `useSSE.ts` Hook
- 相关状态管理
- 样式文件
```

---

### TASK-018：实时推送服务（后端SSE）

```markdown
# TASK-018：实时推送服务

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-018 |
| 所属Phase | Phase 4：演示准备 |
| 依赖 | TASK-002 |
| 预估工作量 | 1天 |
| 状态 | 待开始 |

---

## 任务描述

实现后端SSE实时推送服务，将协商事件推送给前端。

---

## 技术方案

### 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Agent     │────▶│ EventBus    │────▶│ SSE Router  │
│   事件      │     │ 事件总线    │     │ 推送服务    │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   前端      │
                                        │   客户端    │
                                        └─────────────┘
```

### 实现代码

```python
"""
towow/api/routers/events.py
SSE事件推送路由
"""
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
import json
from events.recorder import event_recorder
from events.bus import event_bus

router = APIRouter(prefix="/api/events", tags=["events"])


async def event_generator(
    demand_id: str,
    request: Request
) -> AsyncGenerator[str, None]:
    """
    SSE事件生成器

    为特定demand_id生成事件流
    """
    # 订阅事件
    queue = event_recorder.subscribe()

    try:
        # 首先发送历史事件
        history = event_recorder.get_by_channel(f"collab-{demand_id[:8]}")
        for event in history:
            yield f"data: {json.dumps(event)}\n\n"

        # 持续发送新事件
        while True:
            # 检查客户端是否断开
            if await request.is_disconnected():
                break

            try:
                # 等待新事件（超时5秒发送心跳）
                event = await asyncio.wait_for(queue.get(), timeout=5.0)

                # 过滤只发送相关事件
                payload = event.get("payload", {})
                event_channel = payload.get("channel_id") or payload.get("channel")
                event_demand = payload.get("demand_id")

                if (event_channel and demand_id[:8] in event_channel) or \
                   (event_demand and event_demand == demand_id):
                    yield f"data: {json.dumps(event)}\n\n"

            except asyncio.TimeoutError:
                # 发送心跳
                yield f": heartbeat\n\n"

    finally:
        event_recorder.unsubscribe(queue)


@router.get("/stream/{demand_id}")
async def stream_events(demand_id: str, request: Request):
    """
    SSE事件流端点

    GET /api/events/stream/{demand_id}
    """
    return StreamingResponse(
        event_generator(demand_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        }
    )


@router.get("/recent/{demand_id}")
async def get_recent_events(demand_id: str, count: int = 50):
    """
    获取最近事件（轮询备用）

    GET /api/events/recent/{demand_id}?count=50
    """
    channel_id = f"collab-{demand_id[:8]}"
    events = event_recorder.get_by_channel(channel_id, count)
    return {"events": events, "count": len(events)}


# === 事件记录钩子 ===

async def record_towow_event(event: dict):
    """记录ToWow事件到recorder"""
    await event_recorder.record(event)


# 在应用启动时订阅所有towow事件
def setup_event_recording():
    """设置事件记录"""
    event_bus.subscribe("towow.*", record_towow_event)
```

```python
"""
towow/api/routers/demand.py
需求API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from events.factory import EventFactory
from events.bus import event_bus

router = APIRouter(prefix="/api/demand", tags=["demand"])


class DemandSubmitRequest(BaseModel):
    raw_input: str
    user_id: Optional[str] = "anonymous"


class DemandSubmitResponse(BaseModel):
    demand_id: str
    channel_id: str
    status: str
    understanding: Dict[str, Any]


@router.post("/submit", response_model=DemandSubmitResponse)
async def submit_demand(request: DemandSubmitRequest):
    """
    提交需求

    POST /api/demand/submit
    """
    from services.coordinator import coordinator_service

    try:
        # 1. 调用SecondMe理解需求
        understanding = await coordinator_service.understand_demand(
            user_id=request.user_id,
            raw_input=request.raw_input
        )

        # 2. 创建需求
        demand_id = await coordinator_service.create_demand(
            user_id=request.user_id,
            raw_input=request.raw_input,
            understanding=understanding
        )

        # 3. 发布事件
        event = EventFactory.demand_broadcast(
            source_agent="coordinator",
            demand_id=demand_id,
            requester_id=request.user_id,
            surface_demand=understanding.get("surface_demand", request.raw_input),
            capability_tags=[]
        )
        await event_bus.publish(event)

        # 4. 触发筛选流程（异步）
        asyncio.create_task(
            coordinator_service.start_filtering(demand_id)
        )

        return DemandSubmitResponse(
            demand_id=demand_id,
            channel_id=f"collab-{demand_id[:8]}",
            status="processing",
            understanding=understanding
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{demand_id}")
async def get_demand(demand_id: str):
    """
    获取需求详情

    GET /api/demand/{demand_id}
    """
    from services.coordinator import coordinator_service

    demand = await coordinator_service.get_demand(demand_id)
    if not demand:
        raise HTTPException(status_code=404, detail="Demand not found")

    return demand
```

---

## 验收标准

- [ ] SSE端点可以正常连接
- [ ] 事件可以实时推送
- [ ] 心跳机制正常工作
- [ ] 客户端断开后资源正确释放
- [ ] 历史事件可以正确获取

---

## 产出物

- `api/routers/events.py`
- `api/routers/demand.py`
- 事件记录集成
```

---

## 三、更新的任务依赖图

```
TASK-001 ─┬─ TASK-002 ─┬─ TASK-004 ─── TASK-009
          │            │
          │            ├─ TASK-005 ─── TASK-011
          │            │
          │            ├─ TASK-006 ─── TASK-010
          │            │
          │            └─ TASK-018 ←── [新增：实时推送]
          │                   │
          └─ TASK-003         │
                │             │
                └─ TASK-012   │
                              │
          TASK-007 ─── TASK-008
                              │
          TASK-015 ─┬─ TASK-016  [新增：前端初始化、需求提交]
                    │
                    └─ TASK-017 ← TASK-018  [新增：协商展示]
                              │
                              ↓
                         TASK-013 ─── TASK-014
```

---

## 四、端口和服务总结

| 服务 | 端口 | 说明 |
|------|------|------|
| OpenAgent HTTP | 8700 | Agent网络发现 |
| OpenAgent gRPC | 8600 | Agent连接 |
| ToWow API | 8000 | FastAPI后端 + SSE |
| 前端开发服务器 | 3000 | React开发模式 |
| PostgreSQL | 5432 | 数据库 |
| Nginx | 80/443 | 生产环境反向代理 |

---

**文档版本**: v1.0
**创建时间**: 2026-01-21
**状态**: 补充完成
