# TECH-multiagent-negotiation-v3

> **文档路径**: `.ai/epic-multiagent-negotiation/TECH-multiagent-negotiation-v3.md`
>
> * EPIC_ID: E-001
> * 版本: v3
> * 状态: DRAFT
> * 创建日期: 2026-01-22
> * 最后更新: 2026-01-22

---

## 1. 变更概述

### 1.1 v3 相对于 v1/v2 的核心变更

| 变更项 | v1/v2 状态 | v3 状态 | 技术影响 |
|--------|-----------|---------|----------|
| 协商引擎 | `demand.py` 硬编码 Mock | **真实 LLM 驱动** | 重构 `trigger_mock_negotiation()` |
| 协商轮次 | 最多 5 轮 | **最多 3 轮** | 修改 `ChannelAdminAgent.MAX_NEGOTIATION_ROUNDS` |
| 递归层次 | 最多 2 层 | **最多 1 层** | 简化 `SubnetManager` |
| LLM 调用 | 仅框架代码 | **9 个提示词全面集成** | 新增 prompt templates |
| Agent 架构 | 有 LLM 支持但未启用 | **启用 LLM 决策** | 激活 `services/llm.py` 调用链 |

### 1.2 核心改造点

1. **demand.py 重构**: 移除硬编码的 `trigger_mock_negotiation()`，改为调用真实 Agent 流程
2. **Coordinator 智能筛选**: 激活 `_smart_filter()` 中的 LLM 调用
3. **UserAgent 响应生成**: 激活 `_llm_generate_response()` 和 `_llm_evaluate_proposal()`
4. **ChannelAdmin 方案聚合**: 激活 `_generate_proposal()` 和 `_adjust_proposal()`
5. **缺口识别与子网**: 新增缺口识别和递归判断逻辑
6. **前端修复**: 修复方案卡片消失、事件展示等问题

---

## 2. 架构设计

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React + Zustand)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ NegotiationPage │  │ EventTimeline │  │ ProposalCard │  │ CandidateList │ │
│  └───────┬──────┘  └───────┬──────┘  └───────┬──────┘  └───────┬──────┘ │
│          │                 │                 │                 │         │
│          └─────────────────┴─────────────────┴─────────────────┘         │
│                                    │                                      │
│                            SSE Stream (useSSE)                           │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Backend (FastAPI)                              │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    API Layer (api/routers/)                      │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │    │
│  │  │ demand.py    │  │ events.py    │  │ admin.py     │           │    │
│  │  │ POST /submit │  │ GET /stream  │  │ Agent管理     │           │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┘           │    │
│  └─────────┼─────────────────┼──────────────────────────────────────┘    │
│            │                 │                                           │
│            ▼                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Agent Layer (openagents/agents/)              │    │
│  │                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │                   Coordinator                             │   │    │
│  │  │  - 需求理解 (提示词1)                                      │   │    │
│  │  │  - 智能筛选 (提示词2)                                      │   │    │
│  │  │  - 创建 Channel                                           │   │    │
│  │  └──────────────────────────┬───────────────────────────────┘   │    │
│  │                             │                                    │    │
│  │              ┌──────────────┴──────────────┐                    │    │
│  │              ▼                              ▼                    │    │
│  │  ┌────────────────────┐        ┌────────────────────┐          │    │
│  │  │   ChannelAdmin     │        │   UserAgent (N个)   │          │    │
│  │  │  - 方案聚合 (提示词4) │        │  - 响应生成 (提示词3) │          │    │
│  │  │  - 方案调整 (提示词6) │        │  - 方案反馈 (提示词5) │          │    │
│  │  │  - 缺口识别 (提示词7) │        │  - 讨价还价          │          │    │
│  │  │  - 递归判断 (提示词8) │        │  - 退出协商          │          │    │
│  │  │  - 妥协方案 (提示词9) │        └────────────────────┘          │    │
│  │  └────────────────────┘                                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Service Layer (services/)                     │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │    │
│  │  │ llm.py       │  │ secondme*.py │  │ gap_*.py     │           │    │
│  │  │ LLM调用封装   │  │ SecondMe服务  │  │ 缺口识别      │           │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Event Layer (events/)                         │    │
│  │  ┌──────────────┐  ┌──────────────┐                             │    │
│  │  │ recorder.py  │  │ integration.py│                             │    │
│  │  │ 事件记录      │  │ 事件总线      │                             │    │
│  │  └──────────────┘  └──────────────┘                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件职责

| 组件 | 职责 | 关键文件 |
|------|------|----------|
| **API Layer** | HTTP 接口、请求路由 | `api/routers/demand.py`, `events.py` |
| **Coordinator** | 需求理解、智能筛选、创建 Channel | `openagents/agents/coordinator.py` |
| **ChannelAdmin** | 管理协商生命周期、聚合方案、多轮协商 | `openagents/agents/channel_admin.py` |
| **UserAgent** | 代表用户决策、生成响应、提供反馈 | `openagents/agents/user_agent.py` |
| **LLMService** | 封装 Claude API 调用、熔断降级 | `services/llm.py` |
| **EventRecorder** | 事件存储、SSE 推送 | `events/recorder.py` |

### 2.3 数据流

```
用户输入 → POST /api/v1/demand/submit
    │
    ├─1→ Coordinator._understand_demand() [提示词1]
    │        └→ SecondMe / LLM
    │
    ├─2→ Coordinator._smart_filter() [提示词2]
    │        └→ LLM → 返回 10-20 个候选人
    │
    ├─3→ ChannelAdmin._broadcast_demand()
    │        └→ 发送给每个 UserAgent
    │
    ├─4→ UserAgent._generate_response() [提示词3] (并行)
    │        └→ LLM → 返回 participate/decline/conditional
    │
    ├─5→ ChannelAdmin._aggregate_proposals() [提示词4]
    │        └→ LLM → 生成初步方案
    │
    ├─6→ ChannelAdmin._distribute_proposal()
    │        └→ 发送给参与者
    │
    ├─7→ UserAgent._evaluate_proposal() [提示词5] (并行)
    │        └→ LLM → 返回 accept/negotiate/withdraw
    │
    ├─8→ ChannelAdmin._adjust_proposal() [提示词6] (如有 negotiate)
    │        └→ LLM → 调整方案
    │
    ├─9→ [重复 6-8 最多 3 轮]
    │
    ├─10→ ChannelAdmin (协商完成后)
    │        └→ _identify_gaps() [提示词7]
    │        └→ _decide_recursion() [提示词8]
    │        └→ _generate_compromise() [提示词9] (如需要)
    │
    └─11→ 发布 towow.proposal.finalized 事件
             └→ SSE 推送到前端
```

---

## 3. 接口契约

### 3.1 API 接口

#### 3.1.1 POST /api/v1/demand/submit

**请求**:
```json
{
  "raw_input": "我想在北京办一场AI主题聚会，需要场地和嘉宾",
  "user_id": "user_alice"
}
```

**响应**:
```json
{
  "demand_id": "d-abc12345",
  "channel_id": "collab-abc12345",
  "status": "processing",
  "understanding": {
    "surface_demand": "想在北京办一场AI主题聚会",
    "deep_understanding": {
      "motivation": "上个月参加聚会后很兴奋，想当组织者",
      "likely_preferences": ["轻松氛围", "质量优先"]
    },
    "capability_tags": ["场地提供", "演讲嘉宾", "活动策划"],
    "context": {
      "location": "北京"
    },
    "confidence": "high"
  }
}
```

#### 3.1.2 GET /api/v1/events/negotiations/{demand_id}/stream

**协议**: Server-Sent Events (SSE)

**Headers**:
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**事件格式**:
```
data: {"event_id":"evt-abc123","event_type":"towow.offer.submitted","timestamp":"2026-01-22T10:05:00Z","payload":{...}}

```

### 3.2 Agent 间接口

#### 3.2.1 Coordinator 接口

**发送给 ChannelAdmin**:
```python
await self.send_to_agent("channel_admin", {
    "type": "create_channel",
    "demand_id": "d-abc12345",
    "channel_id": "collab-abc12345",
    "demand": {
        "surface_demand": "...",
        "deep_understanding": {...},
        "capability_tags": [...]
    },
    "candidates": [
        {"agent_id": "user_agent_bob", "reason": "场地资源", "relevance_score": 90}
    ]
})
```

#### 3.2.2 ChannelAdmin 接口

**发送给 UserAgent (邀请)**:
```python
await self.send_to_agent(agent_id, {
    "type": "demand_offer",
    "channel_id": "collab-abc12345",
    "demand_id": "d-abc12345",
    "demand": {...},
    "round": 1,
    "filter_reason": "场地资源",
    "match_score": 90
})
```

**发送给 UserAgent (方案评审)**:
```python
await self.send_to_agent(agent_id, {
    "type": "proposal_review",
    "channel_id": "collab-abc12345",
    "demand_id": "d-abc12345",
    "proposal": {...},
    "round": 1,
    "max_rounds": 3
})
```

#### 3.2.3 UserAgent 接口

**响应 (offer_response)**:
```python
await self.send_to_agent("channel_admin", {
    "type": "offer_response",
    "channel_id": "collab-abc12345",
    "agent_id": "user_agent_bob",
    "display_name": "Bob",
    "decision": "participate",  # participate | decline | conditional
    "contribution": "我可以提供30人的会议室...",
    "conditions": [],
    "reasoning": "这个活动正好是我擅长的领域"
})
```

**反馈 (proposal_feedback)**:
```python
await self.send_to_agent("channel_admin", {
    "type": "proposal_feedback",
    "channel_id": "collab-abc12345",
    "agent_id": "user_agent_bob",
    "feedback_type": "accept",  # accept | negotiate | withdraw
    "adjustment_request": "",
    "reasoning": "方案合理，同意参与"
})
```

### 3.3 LLM 调用接口

#### 3.3.1 提示词 1: 需求理解

**调用位置**: `services/secondme.py` 或 `Coordinator._understand_demand()`

**输入**:
```python
{
    "raw_input": "用户原始输入",
    "user_id": "用户ID",
    "user_context": {}  # 可选：用户历史、偏好
}
```

**输出**:
```python
{
    "surface_demand": "表面需求",
    "deep_understanding": {
        "motivation": "动机",
        "likely_preferences": ["偏好列表"],
        "emotional_context": "情绪上下文"
    },
    "capability_tags": ["能力标签"],
    "context": {
        "location": "地点",
        "expected_attendees": 50,
        "date": "日期",
        "budget": "预算"
    },
    "uncertainties": ["不确定点"],
    "confidence": "high|medium|low"
}
```

#### 3.3.2 提示词 2: 智能筛选

**调用位置**: `Coordinator._smart_filter()`

**输入**:
```python
{
    "demand": DemandUnderstanding,
    "all_agent_profiles": [AgentProfile]  # 所有活跃 Agent
}
```

**输出**:
```python
{
    "analysis": "筛选分析过程",
    "definitely_related": [
        {
            "agent_id": "xxx",
            "display_name": "Bob",
            "reason": "选择理由",
            "match_type": "explicit|inferred",
            "confidence": 0.9
        }
    ],
    "possibly_related": [...],
    "total_candidates": 15
}
```

#### 3.3.3 提示词 3: 响应生成

**调用位置**: `UserAgent._llm_generate_response()`

**输入**:
```python
{
    "agent_profile": AgentProfile,
    "demand": DemandUnderstanding,
    "filter_reason": "被筛选原因"
}
```

**输出**:
```python
{
    "decision": "participate|decline|conditional",
    "contribution": "贡献描述",
    "conditions": ["条件列表"],
    "reasoning": "决策理由",
    "decline_reason": "拒绝原因（如果 decline）",
    "confidence": 80
}
```

#### 3.3.4 提示词 4: 方案聚合

**调用位置**: `ChannelAdmin._generate_proposal()`

**输入**:
```python
{
    "demand": DemandUnderstanding,
    "offers": [AgentResponse]  # 所有收到的响应
}
```

**输出**:
```python
{
    "summary": "方案概述",
    "objective": "方案目标",
    "assignments": [
        {
            "agent_id": "xxx",
            "display_name": "Bob",
            "role": "场地提供者",
            "responsibility": "提供场地，负责茶歇",
            "dependencies": []
        }
    ],
    "timeline": {
        "start_date": "2026-02-15",
        "milestones": [...]
    },
    "rationale": "选择理由",
    "gaps": [],
    "confidence": "high|medium|low"
}
```

#### 3.3.5 提示词 5: 方案反馈

**调用位置**: `UserAgent._llm_evaluate_proposal()`

**输入**:
```python
{
    "agent_profile": AgentProfile,
    "proposal": Proposal,
    "my_assignment": Assignment
}
```

**输出**:
```python
{
    "feedback_type": "accept|negotiate|withdraw",
    "reasoning": "评估理由",
    "proposed_changes": {
        "field": "new_value",
        "reason": "调整原因"
    }
}
```

#### 3.3.6 提示词 6: 方案调整

**调用位置**: `ChannelAdmin._adjust_proposal()`

**输入**:
```python
{
    "demand": DemandUnderstanding,
    "current_proposal": Proposal,
    "feedbacks": [ProposalFeedback],
    "round": 2
}
```

**输出**:
```python
{
    # 调整后的 Proposal 结构
    "adjustment_summary": {
        "round": 2,
        "changes_made": [...],
        "requests_addressed": [...],
        "requests_declined": [...]
    }
}
```

#### 3.3.7 提示词 7: 缺口识别

**调用位置**: `services/gap_identification.py`

**输入**:
```python
{
    "demand": DemandUnderstanding,
    "final_proposal": Proposal,
    "agent_feedbacks": [ProposalFeedback]
}
```

**输出**:
```python
{
    "is_complete": False,
    "analysis": "分析过程",
    "gaps": [
        {
            "gap_type": "摄影师",
            "importance": 70,
            "reason": "需要记录活动内容",
            "suggested_capability_tags": ["摄影", "活动拍摄"]
        }
    ]
}
```

#### 3.3.8 提示词 8: 递归判断

**调用位置**: `services/subnet_manager.py`

**输入**:
```python
{
    "demand": DemandUnderstanding,
    "gaps": [Gap],
    "current_proposal": Proposal,
    "estimated_cost": {"tokens": 5000, "time_seconds": 30}
}
```

**输出**:
```python
{
    "should_recurse": True,
    "condition_1_met": True,
    "condition_1_analysis": "满足度分析",
    "condition_2_met": True,
    "condition_2_analysis": "利益相关方分析",
    "condition_3_met": True,
    "condition_3_analysis": "成本效益分析",
    "sub_demands": [
        {
            "description": "寻找摄影师",
            "capability_tags": ["摄影"],
            "priority": "high"
        }
    ]
}
```

#### 3.3.9 提示词 9: 妥协方案

**调用位置**: `ChannelAdmin._generate_compromise()`

**输入**:
```python
{
    "demand": DemandUnderstanding,
    "available_resources": [Assignment],
    "gaps": [Gap],
    "feedbacks": [ProposalFeedback]
}
```

**输出**:
```python
{
    "summary": "妥协方案概述",
    "type": "compromise",
    "assignments": [...],
    "compromises": [
        {
            "issue": "争议点",
            "resolution": "妥协方案",
            "rationale": "理由"
        }
    ],
    "unresolved": ["无法妥协的问题"],
    "suggestions": ["替代建议"],
    "confidence": "low|medium"
}
```

---

## 4. 数据结构

### 4.1 Demand（需求）

```python
@dataclass
class Demand:
    demand_id: str                    # d-abc12345
    requester_id: str                 # agent_alice
    raw_input: str                    # 用户原始输入
    surface_demand: str               # 表面需求
    deep_understanding: Dict          # 深层理解
    capability_tags: List[str]        # 能力标签
    context: Dict                     # 上下文（地点、时间、预算等）
    status: str                       # processing | completed | failed
    created_at: str                   # ISO 8601
```

### 4.2 Offer（响应）

```python
@dataclass
class Offer:
    offer_id: str                     # offer_001
    agent_id: str                     # agent_bob
    demand_id: str                    # d-abc12345
    decision: str                     # participate | decline | conditional
    contribution: str                 # 贡献描述
    conditions: List[str]             # 条件列表
    reasoning: str                    # 决策理由
    decline_reason: str               # 拒绝原因
    confidence: int                   # 0-100
    submitted_at: str                 # ISO 8601
```

### 4.3 Proposal（方案）

```python
@dataclass
class Proposal:
    proposal_id: str                  # prop_001
    demand_id: str                    # d-abc12345
    version: int                      # 1, 2, 3 (轮次)
    summary: str                      # 方案概述
    objective: str                    # 方案目标
    assignments: List[Assignment]     # 角色分配
    timeline: Timeline                # 时间线
    rationale: str                    # 选择理由
    gaps: List[str]                   # 识别的缺口
    confidence: str                   # high | medium | low
    created_at: str                   # ISO 8601

@dataclass
class Assignment:
    agent_id: str
    display_name: str
    role: str                         # 角色名称
    responsibility: str               # 具体职责
    dependencies: List[str]           # 依赖
    notes: str                        # 备注

@dataclass
class Timeline:
    start_date: str
    milestones: List[Milestone]

@dataclass
class Milestone:
    name: str
    date: str
    deliverable: str                  # 交付物
```

### 4.4 Gap（缺口）

```python
@dataclass
class Gap:
    gap_type: str                     # 摄影师
    importance: int                   # 0-100
    reason: str                       # 为什么重要
    suggested_capability_tags: List[str]  # 建议的能力标签
```

### 4.5 AgentProfile（Agent 简介）

```python
@dataclass
class AgentProfile:
    agent_id: str                     # user_agent_bob
    user_name: str                    # Bob
    profile_summary: str              # 200-500字自我介绍
    location: str                     # 北京
    tags: List[str]                   # 能力标签
    capabilities: Dict                # 详细能力
    interests: List[str]              # 兴趣领域
    availability: str                 # 时间可用性
```

#### 4.5.1 AgentProfile 初始化流程

**Mock Agent Profile 的初始化与维护：**

```python
# scripts/load_mock_profiles.py

# 1. Profile 来源
# - 从 data/mock_profiles.json 加载预定义的 Agent 配置
# - 每个 Agent 包含完整的能力描述、标签、兴趣等信息

# 2. 初始化流程
async def init_mock_agents():
    """初始化 Mock Agent Profiles"""
    profiles = load_profiles_from_file("data/mock_profiles.json")

    for profile in profiles:
        # 创建 UserAgent 实例
        agent = UserAgentFactory.create(profile)

        # 注册到 Agent Registry
        AgentRegistry.register(agent)

        # 初始化 Agent 状态
        agent.set_status("active")

    logger.info(f"已初始化 {len(profiles)} 个 Mock Agent")

# 3. Profile 格式
MOCK_PROFILE_SCHEMA = {
    "agent_id": str,           # 唯一标识，格式：user_agent_{name}
    "user_name": str,          # 显示名称
    "profile_summary": str,    # 200-500字自我介绍
    "location": str,           # 地理位置
    "tags": List[str],         # 能力标签（用于筛选）
    "capabilities": Dict,      # 详细能力描述
    "interests": List[str],    # 兴趣领域
    "availability": str        # 时间可用性
}

# 4. 运行时维护
# - Profile 在内存中维护，通过 AgentRegistry 访问
# - 支持热更新：通过 admin API 动态添加/修改 Agent
# - 演示模式：可快速加载/重置所有 Mock Agent
```

### 4.6 事件类型（Event Types）

SSE 推送的事件类型清单：

```python
# events/types.py

EVENT_TYPES = {
    # 需求处理阶段
    "towow.demand.understood": {
        "demand_id": str,
        "surface_demand": str,
        "capability_tags": List[str],
        "confidence": str  # high | medium | low
    },

    # 筛选阶段
    "towow.filter.completed": {
        "demand_id": str,
        "channel_id": str,
        "candidates_count": int,
        "candidates": List[{
            "agent_id": str,
            "display_name": str,
            "reason": str
        }]
    },

    # Channel 创建
    "towow.channel.created": {
        "channel_id": str,
        "demand_id": str,
        "participants_count": int
    },

    # 需求广播
    "towow.demand.broadcast": {
        "channel_id": str,
        "demand_id": str,
        "recipients_count": int
    },

    # 响应提交
    "towow.offer.submitted": {
        "channel_id": str,
        "demand_id": str,
        "agent_id": str,
        "display_name": str,
        "decision": str,  # participate | decline | conditional
        "contribution": str
    },

    # 方案聚合开始
    "towow.aggregation.started": {
        "channel_id": str,
        "demand_id": str,
        "offers_count": int
    },

    # 方案分发
    "towow.proposal.distributed": {
        "channel_id": str,
        "demand_id": str,
        "proposal": Proposal,
        "round": int
    },

    # 方案反馈
    "towow.proposal.feedback": {
        "channel_id": str,
        "demand_id": str,
        "agent_id": str,
        "feedback_type": str,  # accept | negotiate | withdraw
        "reasoning": str
    },

    # 反馈评估完成（新增）
    "towow.feedback.evaluated": {
        "channel_id": str,
        "accepts": int,          # 接受数量
        "rejects": int,          # 拒绝数量
        "negotiates": int,       # 协商数量
        "accept_rate": float,    # 接受率
        "round": int             # 当前轮次
    },

    # 新一轮协商
    "towow.negotiation.round_started": {
        "channel_id": str,
        "demand_id": str,
        "round": int,
        "max_rounds": int
    },

    # 协商成功完成
    "towow.proposal.finalized": {
        "channel_id": str,
        "demand_id": str,
        "final_proposal": Proposal,
        "participants_count": int,
        "rounds_taken": int
    },

    # 协商失败
    "towow.negotiation.failed": {
        "channel_id": str,
        "demand_id": str,
        "reason": str,
        "last_proposal": Proposal  # 可选
    },

    # Agent 退出
    "towow.agent.withdrawn": {
        "channel_id": str,
        "demand_id": str,
        "agent_id": str,
        "display_name": str,
        "reason": str
    },

    # 缺口识别
    "towow.gap.identified": {
        "channel_id": str,
        "demand_id": str,
        "gaps": List[Gap]
    },

    # 子网触发
    "towow.subnet.triggered": {
        "parent_channel_id": str,
        "parent_demand_id": str,
        "sub_demand_id": str,
        "sub_channel_id": str,
        "gap_type": str
    }
}
```

---

## 5. 状态机

### 5.1 协商状态流转

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Negotiation State Machine                     │
│                                                                      │
│   ┌──────────┐      ┌──────────────┐      ┌──────────────┐         │
│   │ CREATED  │─────▶│ BROADCASTING │─────▶│ COLLECTING   │         │
│   └──────────┘      └──────────────┘      └──────┬───────┘         │
│                                                   │                  │
│                                                   ▼                  │
│                                           ┌──────────────┐          │
│                                           │ AGGREGATING  │          │
│                                           └──────┬───────┘          │
│                                                   │                  │
│                                                   ▼                  │
│   ┌──────────┐      ┌──────────────┐      ┌──────────────┐         │
│   │ FINALIZED│◀─────│ NEGOTIATING  │◀─────│ PROPOSAL_SENT│         │
│   └──────────┘      └──────┬───────┘      └──────────────┘         │
│                             │                     ▲                  │
│                             │                     │                  │
│                             │      (round < 3)    │                  │
│                             └─────────────────────┘                  │
│                             │                                        │
│                             │ (round >= 3 || majority reject)        │
│                             ▼                                        │
│                        ┌──────────┐                                 │
│                        │  FAILED  │                                 │
│                        └──────────┘                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Channel 状态定义

```python
class ChannelStatus(Enum):
    CREATED = "created"           # Channel 已创建
    BROADCASTING = "broadcasting" # 正在广播需求
    COLLECTING = "collecting"     # 正在收集响应
    AGGREGATING = "aggregating"   # 正在聚合方案
    PROPOSAL_SENT = "proposal_sent"  # 方案已分发
    NEGOTIATING = "negotiating"   # 正在协商
    FINALIZED = "finalized"       # 协商成功完成
    FAILED = "failed"             # 协商失败
```

### 5.3 状态转换条件

| 当前状态 | 触发条件 | 下一状态 |
|----------|----------|----------|
| CREATED | 开始广播 | BROADCASTING |
| BROADCASTING | 广播完成 | COLLECTING |
| COLLECTING | 响应超时或全部收到 | AGGREGATING |
| AGGREGATING | 方案生成完成 | PROPOSAL_SENT |
| PROPOSAL_SENT | 方案分发完成 | NEGOTIATING |
| NEGOTIATING | 全员 accept | FINALIZED |
| NEGOTIATING | round < 3 && 有 negotiate | PROPOSAL_SENT (新一轮) |
| NEGOTIATING | round >= 3 || majority reject | FAILED 或 FINALIZED |

---

## 6. 错误处理

### 6.1 错误码定义

| 错误码 | 描述 | HTTP 状态码 |
|--------|------|-------------|
| `E001` | 需求格式错误 | 400 |
| `E002` | 需求 ID 不存在 | 404 |
| `E003` | LLM 服务不可用 | 503 |
| `E004` | LLM 调用超时 | 504 |
| `E005` | 无候选人匹配 | 200 (业务错误) |
| `E006` | 协商超时 | 200 (业务错误) |
| `E007` | Channel 不存在 | 404 |
| `E008` | Agent 不存在 | 404 |
| `E009` | 事件推送失败 | 500 |

### 6.2 降级策略

#### 6.2.1 LLM 调用失败降级

```python
# services/llm.py 中的 LLMServiceWithFallback 实现

# 1. 熔断器机制
- 连续 3 次失败后触发熔断
- 熔断后 30 秒内直接返回降级响应
- 30 秒后进入半开状态，允许 1 次试探

# 2. 超时控制
- 单次调用超时：10 秒
- 超时后返回预设降级响应

# 3. 预设降级响应
FALLBACK_RESPONSES = {
    "smart_filter": {...},          # 返回 mock 候选人
    "response_generation": {...},   # 返回 decline
    "proposal_aggregation": {...},  # 返回简化方案
    "proposal_adjustment": {...},   # 返回原方案
    "gap_identify": {...},          # 返回无缺口
    "default": {...}                # 通用降级
}
```

#### 6.2.2 Agent 响应超时降级

```python
# ChannelAdmin 中的超时处理

RESPONSE_TIMEOUT = 300   # 5 分钟
FEEDBACK_TIMEOUT = 120   # 2 分钟

# 响应超时：继续处理已收到的响应
# 反馈超时：视为 accept（默认接受）
```

#### 6.2.3 协商失败降级

```python
# 协商失败时的处理

if 无候选人:
    → 返回"未找到合适的协作者"建议

if 无参与者:
    → 生成妥协方案，给出替代建议

if 达到最大轮次仍有分歧:
    → 生成当前最佳方案，标记"部分共识"
```

---

## 7. 技术决策记录（ADR）

### ADR-001: 使用本地 Mock Agent 而非 OpenAgent Network

**状态**: 已决定

**背景**:
- OpenAgent 设计了 gRPC 跨网络协议
- 但真实的 A2A 协议尚未实现
- MVP 需要在 2026-02-01 前完成演示

**决策**:
在 MVP 阶段继续使用本地 Mock Agent 模式，所有 Agent 运行在同一进程内。

**理由**:
1. 聚焦 LLM 协商逻辑的验证
2. 避免分布式系统复杂性
3. 演示效果相同（用户看不出区别）
4. 为后续真实 A2A 协议预留接口

**影响**:
- Agent 间通信通过内存队列
- 无法演示跨网络能力
- 后续迁移成本较低（接口已设计）

### ADR-002: 简化到 3 轮协商

**状态**: 已决定

**背景**:
- 原设计最多 5 轮协商
- 每轮协商需要多次 LLM 调用
- 演示场景延迟敏感

**决策**:
MVP 阶段最多 3 轮协商。

**理由**:
1. 减少延迟（每轮约 10-20 秒）
2. 3 轮已足够展示协商能力
3. 超过 3 轮说明需求本身可能有问题
4. 用户体验更好

**影响**:
- `ChannelAdmin.MAX_NEGOTIATION_ROUNDS = 3`
- 复杂协商可能无法完全达成共识
- 通过妥协方案兜底

### ADR-003: 简化到 1 层递归

**状态**: 已决定

**背景**:
- 原设计最多 2 层递归
- 每层递归是一个完整协商流程
- 递归增加系统复杂度

**决策**:
MVP 阶段最多 1 层递归。

**理由**:
1. 1 层递归已能展示"递归协作"能力
2. 降低实现复杂度
3. 减少总延迟
4. 便于调试和测试

**影响**:
- 子网协商不再触发孙网
- 深度复杂需求可能无法完全满足
- 通过妥协方案兜底

### ADR-004: 智能筛选采用纯 LLM 方案

**状态**: 已决定

**背景**:
- 原设计是两层筛选：规则 SQL + LLM 语义
- Agent 数量约 100 个
- Claude 上下文窗口足够大

**决策**:
MVP 阶段采用纯 LLM 筛选，一步到位。

**理由**:
1. 简化实现，减少开发时间
2. 100 个 Agent，每人 500 字 ≈ 25K tokens，在 Claude 上下文范围内
3. 单次筛选约 3-5 秒，可接受
4. LLM 能做更智能的隐式推断

**影响**:
- 无需实现规则层
- 筛选成本较高（约 $0.1/次）
- Agent 数量增加时需要重新评估

### ADR-005: 前后端事件驱动架构

**状态**: 已决定

**背景**:
- 协商过程需要实时展示
- 传统轮询延迟高
- WebSocket 实现复杂

**决策**:
采用 SSE (Server-Sent Events) + 事件总线架构。

**理由**:
1. SSE 比 WebSocket 更简单
2. 原生浏览器支持，无需额外库
3. 单向推送足够（客户端只读）
4. 支持自动重连

**影响**:
- 后端通过 `event_recorder` 记录和推送事件
- 前端通过 `useSSE` hook 订阅
- 历史事件可回放

**SSE 重连配置**:

```typescript
// towow-frontend/src/hooks/useSSE.ts

// SSE 重连配置
const SSE_CONFIG = {
  MAX_RECONNECT_ATTEMPTS: 5,   // 最大重连次数
  RECONNECT_DELAY: 3000,       // 重连间隔 (ms)
  RECONNECT_BACKOFF: 1.5       // 重连退避系数
};

// 重连逻辑
// 1. 连接断开后，等待 RECONNECT_DELAY 毫秒后尝试重连
// 2. 每次重连失败，延迟时间乘以 RECONNECT_BACKOFF
// 3. 超过 MAX_RECONNECT_ATTEMPTS 次后停止重连，提示用户
// 4. 重连时带上 last_event_id 参数，避免事件丢失
```

---

## 8. 测试策略

### 8.1 单元测试

| 模块 | 测试重点 | 覆盖率目标 |
|------|----------|------------|
| `Coordinator._smart_filter` | 提示词格式、响应解析 | 80% |
| `UserAgent._generate_response` | 三种决策类型生成 | 80% |
| `ChannelAdmin._generate_proposal` | 方案结构完整性 | 80% |
| `LLMServiceWithFallback` | 熔断、超时、降级 | 90% |

### 8.2 集成测试

| 场景 | 验证点 |
|------|--------|
| 完整协商流程 | 需求提交 → 方案生成 → 协商完成 |
| 多轮协商 | negotiate 反馈 → 方案调整 → 重新分发 |
| Agent 退出 | 核心 Agent 退出 → 替补或失败 |
| 缺口识别 | 方案完成 → 缺口识别 → 子网触发 |

### 8.3 端到端测试

| 场景 | 预期结果 |
|------|----------|
| 正常流程 | 2-3 轮内达成共识 |
| 无候选人 | 返回失败提示 |
| LLM 超时 | 降级响应，流程继续 |
| 前端断线重连 | 重连后事件续传 |

---

## 9. 部署与监控

### 9.1 环境变量

```bash
# LLM 配置
ANTHROPIC_API_KEY=sk-xxx
ANTHROPIC_BASE_URL=https://api.anthropic.com  # 可选，支持代理
LLM_MODEL=claude-sonnet-4-5-20250929
LLM_TIMEOUT=10

# 熔断器配置
LLM_FAILURE_THRESHOLD=3
LLM_RECOVERY_TIMEOUT=30

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 9.2 监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `llm_call_total` | LLM 调用总数 | - |
| `llm_call_success_rate` | LLM 调用成功率 | < 90% |
| `llm_call_latency_p95` | LLM 调用 P95 延迟 | > 10s |
| `circuit_breaker_open` | 熔断器打开次数 | > 0 |
| `negotiation_success_rate` | 协商成功率 | < 70% |
| `sse_active_connections` | SSE 活跃连接数 | > 1000 |

### 9.3 日志规范

```python
# 关键日志点
logger.info(f"需求 {demand_id} 开始处理")
logger.info(f"智能筛选完成，找到 {len(candidates)} 个候选人")
logger.info(f"Channel {channel_id} 进入第 {round} 轮协商")
logger.warning(f"LLM 调用超时，使用降级响应")
logger.error(f"协商失败: {reason}")
```

---

## 10. 关联文档

| 文档类型 | 路径 |
|----------|------|
| PRD v3 | `.ai/epic-multiagent-negotiation/PRD-multiagent-negotiation-v3.md` |
| Story 文档 | `.ai/epic-multiagent-negotiation/STORY-*.md` |
| 任务依赖 | `.ai/epic-multiagent-negotiation/TASK-dependency-analysis.md` |
| 提示词清单 | `/docs/提示词清单.md` |
| 原技术方案 | `/docs/tech/TECH-TOWOW-MVP-v1.md` |

---

## 11. 变更记录

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v3 | 2026-01-22 | Claude | 初版，基于 PRD v3 和 7 个 Story 设计 |
