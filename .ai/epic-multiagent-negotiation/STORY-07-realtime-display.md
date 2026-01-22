# STORY-07: 实时展示

> **文档路径**: `.ai/epic-multiagent-negotiation/STORY-07-realtime-display.md`
>
> * EPIC_ID: E-001
> * STORY_ID: STORY-07
> * 优先级: P0
> * 状态: 可开发
> * 创建日期: 2026-01-22

---

## 用户故事

**作为**演示现场的观众
**我希望**实时看到 AI Agent 的协商过程，包括筛选、响应、讨价还价、方案调整
**以便**理解 ToWow 网络的涌现协作能力，感受"AI 在思考和讨论"

---

## 背景与动机

### 为什么实时展示很重要

MVP 的核心目标之一是：**观众能够实时看到协商过程（流式展示）**

不能等所有结果出来再显示，需要：
- 每一步都即时推送到前端
- 展示"AI 在思考"的过程
- 让观众感受协商的动态性

### 技术选型

使用 **SSE（Server-Sent Events）** 实现实时推送：
- 比 WebSocket 更简单，单向推送足够
- 原生浏览器支持，无需额外库
- 断线可自动重连

---

## 验收标准

### AC-1: 事件实时推送
**Given** 协商流程正在进行
**When** 每个阶段完成（筛选、响应、方案等）
**Then** 对应事件在 2 秒内推送到前端

### AC-2: 所有事件类型覆盖
**Given** 完整的协商流程
**When** 前端订阅 SSE
**Then** 能收到以下所有事件类型：
- demand.understood
- filter.completed
- channel.created
- offer.submitted
- proposal.distributed
- negotiation.bargain
- proposal.feedback
- agent.withdrawn
- gap.identified
- subnet.triggered
- proposal.finalized

### AC-3: 前端流式渲染
**Given** 收到 SSE 事件
**When** 前端处理事件
**Then**
- 事件按时间顺序追加到时间线
- 不同事件类型有不同的视觉样式
- 支持滚动查看历史事件

### AC-4: 断线重连
**Given** 网络短暂断开
**When** 网络恢复
**Then** SSE 自动重连，继续接收事件（不丢失）

### AC-5: 大屏展示友好
**Given** 演示场景需要大屏展示
**When** 在大屏幕上显示
**Then**
- 字体足够大，观众能看清
- 关键信息高亮显示
- 动画效果吸引注意力

---

## 技术要点

### SSE 服务端

- **实现位置**: `api/routers/events.py`
- **端点**: `GET /api/v1/events/stream?channel_id={channel_id}`
- **协议**: text/event-stream

### 依赖模块
- `events/recorder.py`: 事件记录器
- `events/integration.py`: 事件总线
- `api/routers/events.py`: SSE 端点

### 接口定义

**SSE 端点**:
```
GET /api/v1/events/stream?channel_id={channel_id}

Response Headers:
  Content-Type: text/event-stream
  Cache-Control: no-cache
  Connection: keep-alive
```

**SSE 事件格式**:
```
event: towow.offer.submitted
data: {"event_id":"evt-abc123","event_type":"towow.offer.submitted","timestamp":"2026-01-22T10:05:00Z","payload":{...}}

```

### 事件数据结构

```python
class SSEEvent(BaseModel):
    event_id: str               # 事件唯一 ID
    event_type: str             # 事件类型
    timestamp: str              # ISO 8601 时间戳
    payload: dict               # 事件负载
```

---

## SSE 事件清单

### 1. towow.demand.understood
**触发时机**: 需求理解完成
```json
{
  "event_type": "towow.demand.understood",
  "payload": {
    "demand_id": "d-abc12345",
    "channel_id": "collab-abc12345",
    "surface_demand": "想在北京办一场AI主题聚会",
    "capability_tags": ["场地提供", "演讲嘉宾", "活动策划"],
    "confidence": "high"
  }
}
```

### 2. towow.filter.completed
**触发时机**: 智能筛选完成
```json
{
  "event_type": "towow.filter.completed",
  "payload": {
    "demand_id": "d-abc12345",
    "channel_id": "collab-abc12345",
    "candidates": [
      {"agent_id": "agent_bob", "display_name": "Bob", "reason": "场地资源"},
      {"agent_id": "agent_alice", "display_name": "Alice", "reason": "技术分享"}
    ],
    "total_candidates": 15
  }
}
```

### 3. towow.channel.created
**触发时机**: 协商 Channel 创建
```json
{
  "event_type": "towow.channel.created",
  "payload": {
    "channel_id": "collab-abc12345",
    "demand_id": "d-abc12345",
    "invited_agents": ["agent_bob", "agent_alice", "agent_charlie"]
  }
}
```

### 4. towow.offer.submitted
**触发时机**: Agent 提交响应
```json
{
  "event_type": "towow.offer.submitted",
  "payload": {
    "channel_id": "collab-abc12345",
    "agent_id": "agent_bob",
    "display_name": "Bob",
    "decision": "participate",
    "contribution": "我可以提供30人的会议室...",
    "reasoning": "这个活动正好是我擅长的领域",
    "decline_reason": "",
    "round": 1
  }
}
```

### 5. towow.proposal.distributed
**触发时机**: 方案分发
```json
{
  "event_type": "towow.proposal.distributed",
  "payload": {
    "channel_id": "collab-abc12345",
    "demand_id": "d-abc12345",
    "proposal": {
      "summary": "关于'北京AI主题聚会'的协作方案",
      "objective": "组织一次高质量的技术交流活动",
      "assignments": [...]
    },
    "participants": ["agent_bob", "agent_alice", "agent_charlie"],
    "round": 1
  }
}
```

### 6. towow.negotiation.bargain
**触发时机**: 讨价还价请求
```json
{
  "event_type": "towow.negotiation.bargain",
  "payload": {
    "channel_id": "collab-abc12345",
    "agent_id": "agent_alice",
    "display_name": "Alice",
    "bargain_type": "condition",
    "content": "分享时长能否延长到45分钟？30分钟太紧凑了",
    "round": 1
  }
}
```

### 7. towow.proposal.feedback
**触发时机**: Agent 反馈方案
```json
{
  "event_type": "towow.proposal.feedback",
  "payload": {
    "channel_id": "collab-abc12345",
    "agent_id": "agent_bob",
    "display_name": "Bob",
    "feedback_type": "accept",
    "reasoning": "方案合理，角色分配符合我的能力",
    "round": 1
  }
}
```

### 8. towow.agent.withdrawn
**触发时机**: Agent 退出
```json
{
  "event_type": "towow.agent.withdrawn",
  "payload": {
    "channel_id": "collab-abc12345",
    "agent_id": "agent_charlie",
    "display_name": "Charlie",
    "reason": "非常抱歉，公司那边突然有个紧急项目...",
    "round": 1
  }
}
```

### 9. towow.gap.identified
**触发时机**: 缺口识别完成
```json
{
  "event_type": "towow.gap.identified",
  "payload": {
    "channel_id": "collab-abc12345",
    "is_complete": false,
    "gaps": [
      {"gap_type": "摄影师", "importance": 70, "reason": "需要记录活动内容"}
    ]
  }
}
```

### 10. towow.subnet.triggered
**触发时机**: 子网触发
```json
{
  "event_type": "towow.subnet.triggered",
  "payload": {
    "parent_channel_id": "collab-abc12345",
    "sub_channel_id": "collab-abc12345-sub-1",
    "sub_demand": {
      "description": "寻找摄影师，拍摄AI主题聚会",
      "capability_tags": ["摄影", "活动拍摄"]
    },
    "depth": 1
  }
}
```

### 11. towow.proposal.finalized
**触发时机**: 协商完成
```json
{
  "event_type": "towow.proposal.finalized",
  "payload": {
    "channel_id": "collab-abc12345",
    "demand_id": "d-abc12345",
    "status": "success",
    "final_proposal": {...},
    "total_rounds": 2,
    "participants_count": 3,
    "declined_count": 1,
    "withdrawn_count": 0,
    "summary": "经过2轮协商，3位参与者达成共识，1人婉拒"
  }
}
```

---

## 测试场景

| 场景 | 输入 | 预期输出 |
|------|------|----------|
| 正常订阅 | 连接 SSE 端点 | 收到 connection 成功事件 |
| 事件推送 | 后端触发 offer.submitted | 前端 2 秒内收到该事件 |
| 事件顺序 | 完整协商流程 | 事件按 timestamp 顺序排列 |
| 断线重连 | 网络断开 5 秒后恢复 | 自动重连，继续接收事件 |
| 多客户端 | 多个前端同时订阅 | 所有客户端都能收到相同事件 |

---

## 前端展示要求

### 事件时间线组件

```
┌─────────────────────────────────────────────────┐
│  协商进度                                        │
├─────────────────────────────────────────────────┤
│                                                 │
│  ⏱ 10:00:00  需求理解完成                       │
│  ├─ 表面需求：想在北京办一场AI主题聚会           │
│  └─ 能力标签：场地提供、演讲嘉宾、活动策划       │
│                                                 │
│  ⏱ 10:00:05  筛选完成                           │
│  └─ 找到 15 个候选人                            │
│                                                 │
│  ⏱ 10:00:10  Bob 响应                           │
│  ├─ 决策：参与                                  │
│  └─ "我可以提供30人的会议室..."                 │
│                                                 │
│  ⏱ 10:00:12  Alice 响应                         │
│  ├─ 决策：参与                                  │
│  └─ "我可以做AI技术分享..."                     │
│                                                 │
│  ⏱ 10:00:15  方案生成                           │
│  └─ [查看完整方案]                              │
│                                                 │
│  ⏱ 10:00:20  Alice 协商                         │
│  └─ "希望分享时间改为45分钟"                    │
│                                                 │
│  ⏱ 10:00:25  协商完成 ✅                        │
│  └─ 2轮协商，3人达成共识                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 事件类型视觉样式

| 事件类型 | 图标 | 颜色 | 说明 |
|----------|------|------|------|
| demand.understood | 💡 | 蓝色 | 需求理解 |
| filter.completed | 🔍 | 紫色 | 筛选完成 |
| offer.submitted (participate) | ✅ | 绿色 | 参与响应 |
| offer.submitted (decline) | ❌ | 灰色 | 拒绝响应 |
| offer.submitted (conditional) | ⚠️ | 黄色 | 有条件响应 |
| proposal.distributed | 📋 | 蓝色 | 方案分发 |
| negotiation.bargain | 💬 | 橙色 | 讨价还价 |
| proposal.feedback (accept) | 👍 | 绿色 | 接受方案 |
| proposal.feedback (negotiate) | 🔄 | 黄色 | 协商调整 |
| agent.withdrawn | 🚪 | 红色 | Agent 退出 |
| gap.identified | 🔎 | 紫色 | 缺口识别 |
| subnet.triggered | 🌐 | 蓝色 | 子网触发 |
| proposal.finalized (success) | 🎉 | 绿色 | 协商成功 |
| proposal.finalized (failed) | 😞 | 红色 | 协商失败 |

---

## UI 证据要求

- [ ] 事件时间线截图（显示多种事件类型）
- [ ] 实时推送效果录屏（展示事件逐个出现）
- [ ] 大屏展示效果截图
- [ ] 断线重连测试录屏

---

## OPEN 事项

| 编号 | 问题 | 状态 |
|------|------|------|
| OPEN-7.1 | 历史事件是否需要持久化 | 待确认：MVP 先只保留内存，重启丢失 |
| OPEN-7.2 | 是否需要支持按 demand_id 筛选事件 | 待确认：MVP 先支持 channel_id 筛选 |
| OPEN-7.3 | 大屏展示是否需要专门的"演示模式" | 待确认：可以做字体放大的样式切换 |

---

## 关联文档

- PRD: `./PRD-multiagent-negotiation-v3.md` (F7 章节)
- 技术方案: `/docs/tech/TECH-TOWOW-MVP-v1.md` (supplement-03)
- 前端实现: `towow-frontend/src/hooks/useSSE.ts`
- 后端实现: `towow/api/routers/events.py`
