# ToWow 产品全流程示例 - OpenAgent 迁移参考

> **目标读者**: OpenAgent 开发者
> **目的**: 展示 ToWow 多 Agent 协商平台的完整业务流程，便于迁移到 OpenAgent 框架

---

## 一、业务场景

### 场景描述

用户小明想找人帮他开发一个电商网站，他在 ToWow 平台提交需求：

```
"我想做一个电商网站，预算 5 万，2 个月内上线，需要支持微信支付"
```

系统需要：
1. 理解用户需求
2. 从候选人库中筛选合适的服务商
3. 让多个服务商 Agent 进行协商竞争
4. 聚合最优方案呈现给用户
5. 收集用户反馈，多轮协商直到达成一致

---

## 二、Agent 角色定义

### 2.1 系统级 Agent

| Agent | 职责 | OpenAgent 映射 |
|-------|------|----------------|
| **Coordinator** | 需求理解、候选人筛选、创建协商频道 | WorkerAgent + 自定义 Tool |
| **ChannelAdmin** | 管理协商频道、聚合方案、分发反馈、识别缺口 | WorkerAgent + State Machine |

### 2.2 动态 Agent（每个候选人一个）

| Agent | 职责 | OpenAgent 映射 |
|-------|------|----------------|
| **UserAgent** | 代表候选人生成报价、评估方案、提交反馈 | WorkerAgent（动态创建） |

### 2.3 Agent 数量

```
一次协商涉及的 Agent:
- 1 x Coordinator
- 1 x ChannelAdmin
- N x UserAgent (N = 筛选出的候选人数量，通常 5-10 个)
```

---

## 三、完整流程示例

### Step 0: 用户提交需求

**用户输入:**
```json
{
  "content": "我想做一个电商网站，预算 5 万，2 个月内上线，需要支持微信支付",
  "user_id": "user-xiaoming"
}
```

**系统响应:**
```json
{
  "demand_id": "d-abc123",
  "status": "processing",
  "message": "需求已提交，正在为您匹配服务商..."
}
```

---

### Step 1: Coordinator 理解需求

**Coordinator 调用 LLM 分析需求:**

```
Input: "我想做一个电商网站，预算 5 万，2 个月内上线，需要支持微信支付"

LLM Output:
{
  "demand_type": "software_development",
  "keywords": ["电商", "网站", "微信支付"],
  "constraints": {
    "budget": 50000,
    "deadline": "2 months",
    "payment": "wechat_pay"
  },
  "required_skills": ["web_development", "ecommerce", "payment_integration"]
}
```

**发出事件:** `towow.demand.understood`

---

### Step 2: Coordinator 筛选候选人

**Coordinator 查询候选人库:**

```sql
SELECT * FROM candidates
WHERE skills CONTAINS ('web_development', 'ecommerce')
AND available = true
ORDER BY rating DESC
LIMIT 10
```

**筛选结果:** 10 个候选人

| ID | 名称 | 技能 | 评分 |
|----|------|------|------|
| c-001 | 张工作室 | web, ecommerce, payment | 4.8 |
| c-002 | 李开发 | web, ecommerce | 4.6 |
| c-003 | 王团队 | fullstack, ecommerce | 4.5 |
| ... | ... | ... | ... |

**发出事件:** `towow.filter.completed`

```json
{
  "event_type": "towow.filter.completed",
  "payload": {
    "demand_id": "d-abc123",
    "candidate_count": 10,
    "candidates": ["c-001", "c-002", "c-003", ...]
  }
}
```

---

### Step 3: Coordinator 创建协商频道

**创建频道:**
```json
{
  "channel_id": "collab-abc123",
  "demand_id": "d-abc123",
  "participants": ["c-001", "c-002", ..., "c-010"],
  "status": "collecting_responses"
}
```

**为每个候选人创建 UserAgent:**

```python
for candidate in candidates:
    user_agent = UserAgent(
        agent_id=f"ua-{candidate.id}",
        candidate=candidate,
        channel_id="collab-abc123"
    )
    # 注册到 OpenAgent 网络
    network.register(user_agent)
```

**发出事件:** `towow.channel.created`

---

### Step 4: ChannelAdmin 广播需求

**ChannelAdmin 向所有 UserAgent 发送需求:**

```json
{
  "message_type": "demand_broadcast",
  "channel_id": "collab-abc123",
  "demand": {
    "content": "我想做一个电商网站...",
    "constraints": {
      "budget": 50000,
      "deadline": "2 months"
    }
  }
}
```

**发出事件:** `towow.demand.broadcast`

---

### Step 5: 每个 UserAgent 生成报价

**UserAgent (张工作室) 调用 LLM 生成报价:**

```
System Prompt:
你是张工作室的代理，专长：web开发、电商、支付集成，评分4.8。
请根据用户需求生成一个有竞争力的报价。

User Input:
需求：电商网站，预算5万，2个月，微信支付

LLM Output:
{
  "candidate_id": "c-001",
  "offer": {
    "price": 45000,
    "duration": "45天",
    "features": ["商品管理", "订单系统", "微信支付", "会员系统"],
    "highlights": "10年电商经验，已交付50+电商项目"
  }
}
```

**每个 UserAgent 独立生成报价，发出事件:** `towow.offer.submitted`

```
时间线:
T+0s:  UserAgent-001 调用 LLM...
T+2s:  towow.offer.submitted (c-001, 报价 45000)
T+3s:  towow.offer.submitted (c-002, 报价 48000)
T+4s:  towow.offer.submitted (c-003, 报价 42000)
...
T+15s: towow.offer.submitted (c-010, 报价 55000)
```

---

### Step 6: ChannelAdmin 聚合方案

**等待所有报价收集完成后，ChannelAdmin 调用 LLM 聚合:**

```
System Prompt:
你是协商频道管理员，请根据收到的10份报价，生成一个综合方案推荐给用户。

User Input:
报价列表:
- 张工作室: 45000元, 45天, 特点: 10年经验
- 李开发: 48000元, 50天, 特点: 快速响应
- 王团队: 42000元, 55天, 特点: 性价比高
...

LLM Output:
{
  "proposal": {
    "recommended": "c-001",
    "reason": "综合性价比最高，经验丰富且报价合理",
    "alternatives": ["c-003", "c-002"],
    "summary": "收到10份报价，价格区间42000-55000元，工期45-60天。推荐张工作室，报价45000元/45天，10年电商经验。"
  },
  "all_offers": [...],
  "round": 1
}
```

**发出事件:** `towow.aggregation.completed`

---

### Step 7: ChannelAdmin 分发方案给用户

**向用户展示聚合方案:**

```json
{
  "event_type": "towow.proposal.distributed",
  "payload": {
    "channel_id": "collab-abc123",
    "round": 1,
    "proposal": {
      "recommended": {
        "name": "张工作室",
        "price": 45000,
        "duration": "45天",
        "highlights": "10年电商经验"
      },
      "alternatives": [...],
      "summary": "收到10份报价..."
    }
  }
}
```

**用户在前端看到:**

```
===== 协商结果 (第1轮) =====

推荐方案: 张工作室
- 报价: ¥45,000
- 工期: 45天
- 亮点: 10年电商经验，已交付50+电商项目

备选方案:
1. 王团队 - ¥42,000 / 55天
2. 李开发 - ¥48,000 / 50天

[接受推荐] [提出反馈] [查看全部报价]
```

---

### Step 8: 用户提交反馈

**用户选择"提出反馈":**

```json
{
  "feedback_type": "counter_offer",
  "content": "价格可以接受，但希望工期能缩短到30天"
}
```

**发出事件:** `towow.feedback.submitted`

---

### Step 9: ChannelAdmin 识别缺口

**ChannelAdmin 分析反馈，识别缺口:**

```
用户反馈: 希望工期缩短到30天
当前最短工期: 45天
缺口: timeline (需要缩短15天)
```

**发出事件:** `towow.gap.identified`

```json
{
  "event_type": "towow.gap.identified",
  "payload": {
    "gap_type": "timeline",
    "current": "45天",
    "expected": "30天",
    "gap": "15天"
  }
}
```

---

### Step 10: ChannelAdmin 分发反馈给 UserAgent

**ChannelAdmin 向所有 UserAgent 分发用户反馈:**

```json
{
  "message_type": "proposal_review",
  "channel_id": "collab-abc123",
  "round": 2,
  "feedback": {
    "type": "counter_offer",
    "content": "希望工期缩短到30天"
  }
}
```

---

### Step 11: UserAgent 评估并更新报价

**UserAgent (张工作室) 调用 LLM 评估:**

```
System Prompt:
用户希望工期从45天缩短到30天。请评估是否可行，如果可行请更新报价。

LLM Output:
{
  "can_meet": true,
  "updated_offer": {
    "price": 52000,  // 加价7000元（加急费）
    "duration": "30天",
    "note": "可以30天交付，需要增加2名开发人员，加急费7000元"
  }
}
```

**发出事件:** `towow.offer.updated`

---

### Step 12: 多轮协商（重复 Step 6-11）

```
Round 2:
- 收集更新后的报价
- 聚合新方案
- 用户反馈: "加急费太高，能便宜点吗？"

Round 3:
- 张工作室: 50000元/30天（降价2000）
- 王团队: 48000元/35天
- 用户反馈: "接受张工作室的方案"

Round 4: 达成一致
```

---

### Step 13: 协商完成

**用户接受方案，ChannelAdmin 完成协商:**

```json
{
  "event_type": "towow.negotiation.finalized",
  "payload": {
    "channel_id": "collab-abc123",
    "total_rounds": 4,
    "final_result": {
      "selected_candidate": "c-001",
      "name": "张工作室",
      "final_price": 50000,
      "final_duration": "30天",
      "agreement": "电商网站开发，含商品管理、订单系统、微信支付、会员系统"
    }
  }
}
```

---

## 四、事件流总览

```
Timeline:

T+0s    [USER]        提交需求
        [COORDINATOR] → towow.demand.submitted

T+2s    [COORDINATOR] LLM 理解需求
        [COORDINATOR] → towow.demand.understood

T+3s    [COORDINATOR] 查询数据库筛选候选人
        [COORDINATOR] → towow.filter.completed (10 candidates)

T+4s    [COORDINATOR] 创建频道，注册 UserAgent
        [COORDINATOR] → towow.channel.created

T+5s    [CHANNEL_ADMIN] 广播需求
        [CHANNEL_ADMIN] → towow.demand.broadcast

T+7s    [USER_AGENT_001] LLM 生成报价
        [USER_AGENT_001] → towow.offer.submitted

T+8s    [USER_AGENT_002] LLM 生成报价
        [USER_AGENT_002] → towow.offer.submitted

...

T+20s   [USER_AGENT_010] LLM 生成报价
        [USER_AGENT_010] → towow.offer.submitted

T+22s   [CHANNEL_ADMIN] LLM 聚合方案
        [CHANNEL_ADMIN] → towow.aggregation.completed

T+23s   [CHANNEL_ADMIN] 分发方案给用户
        [CHANNEL_ADMIN] → towow.proposal.distributed

T+60s   [USER]        提交反馈
        [CHANNEL_ADMIN] → towow.feedback.submitted

T+62s   [CHANNEL_ADMIN] 识别缺口
        [CHANNEL_ADMIN] → towow.gap.identified

T+63s   [CHANNEL_ADMIN] 分发反馈给 UserAgent

T+65s   [USER_AGENT_*] 更新报价
        [USER_AGENT_*] → towow.offer.updated

... (多轮协商)

T+180s  [CHANNEL_ADMIN] 协商完成
        [CHANNEL_ADMIN] → towow.negotiation.finalized
```

---

## 五、OpenAgent 实现建议

### 5.1 网络配置 (network.yaml)

```yaml
name: towow-negotiation
description: ToWow Multi-Agent Negotiation Network

agents:
  - name: coordinator
    type: worker
    config:
      system_prompt: "你是需求协调者..."
      tools:
        - query_candidates
        - create_channel

  - name: channel_admin
    type: worker
    config:
      system_prompt: "你是协商频道管理员..."
      tools:
        - aggregate_proposals
        - identify_gaps

# UserAgent 动态创建，不在配置中定义

events:
  - towow.demand.submitted
  - towow.demand.understood
  - towow.filter.completed
  - towow.channel.created
  - towow.demand.broadcast
  - towow.offer.submitted
  - towow.aggregation.completed
  - towow.proposal.distributed
  - towow.feedback.submitted
  - towow.gap.identified
  - towow.offer.updated
  - towow.negotiation.finalized
```

### 5.2 Coordinator Agent (coordinator.py)

```python
from openagents import WorkerAgent, on_event

class Coordinator(WorkerAgent):

    @on_event("towow.demand.submitted")
    async def handle_demand(self, event):
        # 1. LLM 理解需求
        understanding = await self.llm.analyze(event.content)
        await self.publish("towow.demand.understood", understanding)

        # 2. 筛选候选人
        candidates = await self.tools.query_candidates(understanding.keywords)
        await self.publish("towow.filter.completed", {"candidates": candidates})

        # 3. 创建频道
        channel = await self.tools.create_channel(event.demand_id, candidates)
        await self.publish("towow.channel.created", channel)
```

### 5.3 ChannelAdmin Agent (channel_admin.py)

```python
from openagents import WorkerAgent, on_event

class ChannelAdmin(WorkerAgent):

    def __init__(self):
        self.channels = {}  # channel_id -> ChannelState

    @on_event("towow.channel.created")
    async def handle_channel_created(self, event):
        # 初始化频道状态
        self.channels[event.channel_id] = ChannelState(
            participants=event.participants,
            status="collecting_responses"
        )
        # 广播需求
        await self.broadcast_demand(event.channel_id, event.demand)

    @on_event("towow.offer.submitted")
    async def handle_offer(self, event):
        state = self.channels[event.channel_id]
        state.offers[event.candidate_id] = event.offer

        # 检查是否收集完成
        if len(state.offers) == len(state.participants):
            await self.aggregate_proposals(event.channel_id)

    async def aggregate_proposals(self, channel_id):
        state = self.channels[channel_id]
        # LLM 聚合
        proposal = await self.llm.aggregate(state.offers)
        await self.publish("towow.proposal.distributed", proposal)
```

### 5.4 UserAgent (user_agent.py)

```python
from openagents import WorkerAgent, on_message

class UserAgent(WorkerAgent):

    def __init__(self, candidate):
        self.candidate = candidate
        self.system_prompt = f"你是{candidate.name}的代理，专长：{candidate.skills}"

    @on_message("demand_broadcast")
    async def handle_demand(self, message):
        # LLM 生成报价
        offer = await self.llm.generate_offer(
            demand=message.demand,
            candidate=self.candidate
        )
        await self.publish("towow.offer.submitted", {
            "candidate_id": self.candidate.id,
            "offer": offer
        })

    @on_message("proposal_review")
    async def handle_feedback(self, message):
        # LLM 评估是否更新报价
        evaluation = await self.llm.evaluate_feedback(
            feedback=message.feedback,
            current_offer=self.current_offer
        )
        if evaluation.should_update:
            await self.publish("towow.offer.updated", evaluation.new_offer)
```

---

## 六、关键设计点

### 6.1 真实 LLM 调用（非 Mock）

```
重要：每个步骤都是真实的 LLM 调用，不是模拟！

- Coordinator.analyze() → 真实 LLM
- UserAgent.generate_offer() → 真实 LLM
- ChannelAdmin.aggregate() → 真实 LLM

LLM 调用本身需要时间（2-5秒），这就是自然的"阶段感"，不需要人为延迟。
```

### 6.2 事件驱动依赖

```
依赖关系通过事件自然表达：

demand.submitted
  → (Coordinator 处理)
  → filter.completed
  → (Coordinator 处理)
  → channel.created
  → (ChannelAdmin 处理)
  → demand.broadcast
  → (UserAgent 处理)
  → offer.submitted (多个)
  → (ChannelAdmin 等待全部)
  → aggregation.completed
  → ...

前一步完成自然触发后一步，不需要延迟或轮询。
```

### 6.3 动态 Agent 创建

```python
# 候选人数量不固定，UserAgent 需要动态创建
for candidate in filtered_candidates:
    agent = UserAgent(candidate)
    network.register(agent, lifetime="channel")  # 频道结束后自动注销
```

---

## 七、与现有代码的映射

| 现有代码 | OpenAgent 迁移 |
|----------|----------------|
| `towow/openagents/agents/coordinator.py` | `openagents/agents/coordinator.py` (继承 WorkerAgent) |
| `towow/openagents/agents/channel_admin.py` | `openagents/agents/channel_admin.py` (继承 WorkerAgent) |
| `towow/openagents/agents/user_agent.py` | `openagents/agents/user_agent.py` (继承 WorkerAgent) |
| `towow/openagents/agents/router.py` | **删除** (使用 OpenAgent 内置路由) |
| `towow/events/event_bus.py` | **删除** (使用 OpenAgent 内置事件系统) |
| `towow/config.py` 中的延迟配置 | **删除** (不需要延迟) |

---

## 八、总结

这个示例展示了 ToWow 产品的完整业务流程：

1. **3 类 Agent**: Coordinator, ChannelAdmin, UserAgent
2. **12 种事件**: 从 demand.submitted 到 negotiation.finalized
3. **多轮协商**: 支持用户反馈和多轮优化
4. **真实 LLM 调用**: 每个决策点都是真实的 LLM 调用
5. **事件驱动**: 依赖关系通过事件自然表达

迁移到 OpenAgent 后，可以利用框架内置的：
- Agent 生命周期管理
- 消息路由
- 事件系统
- Studio UI 监控
- 多协议支持

**下一步**: 参考 `openagents/llm.txt` 和 `openagents/demos/` 开始实现。
