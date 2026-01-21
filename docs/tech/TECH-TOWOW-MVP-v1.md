# ToWow MVP 技术方案

> 基于OpenAgent框架的多Agent协作网络技术实现

**版本**: v1.1
**日期**: 2026-01-21
**目标**: 2月1日 2000人演示
**对齐检查**: 已完成（详见 ALIGNMENT-REPORT-v1.md）

---

## 〇、与设计文档对齐说明

本技术方案严格对齐 `ToWow-Design-MVP.md` 设计文档的核心要求：

### 10个MVP概念覆盖

| 概念 | 设计要求 | 技术实现 | 状态 |
|------|----------|----------|------|
| 1. 统一身份 | user_id + secondme_id 映射 | agent_profiles表增加字段 | OK |
| 2. Agent Card | PostgreSQL存简介 | agent_profiles表 | OK |
| 3. 三类Agent角色 | 中心管理员+Channel管理员+用户Agent | Coordinator+ChannelAdmin+UserAgent | OK |
| 4. Channel即协作室 | OpenAgent原生Channel | collaboration_channels表+OpenAgent | OK |
| 5. 需求广播 | OpenAgent事件 | towow.demand.broadcast | OK |
| 6. 智能筛选 | 直接LLM一步到位 | Coordinator._smart_filter() | OK |
| 7. Offer机制 | 核心流程 | offers表+offer消息 | OK |
| 8. 多轮协商 | 最多5轮 | max_rounds=5 | OK |
| 9. 三个Skills | 方案聚合+缺口识别+递归判断 | supplement-04实现 | OK |
| 10. 子网递归 | 最多2层 | MAX_DEPTH=2 | OK |

### 设计文档成功标准支撑

| 成功标准 | 技术支撑 |
|---------|---------|
| 100个真实用户发起/响应需求 | UserAgent + 需求提交页面 |
| 观众实时看到协商过程（流式） | SSE实时推送（supplement-03） |
| 至少一个触发子网递归的案例 | SubnetManager（supplement-04） |
| 2000人同时在线不崩溃 | 限流中间件（supplement-05） |

---

## 一、架构概览

### 1.1 系统定位

ToWow是一个基于OpenAgent框架的AI代理协作网络，核心功能是：
- 用户通过SecondMe（数字分身）发起需求
- 系统智能匹配网络中的其他Agent
- 多Agent协商形成合作方案

### 1.2 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      ToWow 系统架构                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐    ┌───────────────┐    ┌─────────────┐ │
│  │  SecondMe-1   │    │  SecondMe-2   │    │ SecondMe-N  │ │
│  │  (用户分身)   │    │  (用户分身)   │    │ (用户分身)  │ │
│  └───────┬───────┘    └───────┬───────┘    └──────┬──────┘ │
│          │                    │                   │        │
│          └────────────┬───────┴───────────────────┘        │
│                       ↓                                     │
│          ┌────────────────────────────┐                    │
│          │      OpenAgent 网络        │                    │
│          │  ┌──────────────────────┐  │                    │
│          │  │   中心调度Agent      │  │                    │
│          │  │   (Coordinator)      │  │                    │
│          │  └──────────────────────┘  │                    │
│          │  ┌──────────────────────┐  │                    │
│          │  │   Channel管理        │  │                    │
│          │  │   (协商空间)         │  │                    │
│          │  └──────────────────────┘  │                    │
│          └────────────────────────────┘                    │
│                       ↓                                     │
│          ┌────────────────────────────┐                    │
│          │      PostgreSQL            │                    │
│          │  - Agent简介存储           │                    │
│          │  - 协作记录               │                    │
│          └────────────────────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 核心角色

| 角色 | 实现方式 | 职责 |
|------|----------|------|
| **SecondMe** | 外部服务（API对接） | 用户的数字分身，理解用户需求，代表用户决策 |
| **Coordinator** | OpenAgent Agent | 中心调度，需求广播，智能筛选 |
| **ChannelAdmin** | OpenAgent Agent | 管理协商Channel，聚合方案，处理冲突 |
| **UserAgent** | OpenAgent Agent | 代表SecondMe在网络中的存在，转发消息 |

---

## 二、技术选型

### 2.1 核心框架

| 组件 | 选型 | 理由 |
|------|------|------|
| Agent框架 | **OpenAgent** | 事件驱动、Channel原生支持、内置状态管理 |
| 后端API | **FastAPI** | 高性能、异步支持、自动文档 |
| 数据库 | **PostgreSQL** | 成熟稳定、JSON支持好 |
| LLM | **Claude API** | 推理质量高、工具调用稳定 |

### 2.2 部署配置

**服务器配置**（已确认）：
- 单台服务器：阿里云 ecs.c7.2xlarge（8核16GB）或 c7.4xlarge（16核32GB）
- OpenAgent本地部署
- PostgreSQL本地安装
- **不需要Redis**（OpenAgent内置状态管理）

**端口分配**：
| 服务 | 端口 | 说明 |
|------|------|------|
| OpenAgent HTTP | 8700 | 网络发现、REST API |
| OpenAgent gRPC | 8600 | Agent连接（推荐） |
| ToWow API | 8000 | FastAPI后端 |
| PostgreSQL | 5432 | 本地数据库 |
| Nginx | 80/443 | 反向代理、SSL终止 |

### 2.3 OpenAgent关键API

基于OPENAGENTS_DEV_GUIDE.md，核心使用的API：

```python
# Agent连接
from openagents import Agent

class MyAgent(Agent):
    async def on_direct_message(self, context):
        # 处理直接消息
        pass

    async def on_channel_message(self, context):
        # 处理Channel消息
        pass

# 消息发送
await agent.send_direct(to="agent_id", text="message")
await agent.post_to_channel(channel="#channel_name", text="message")

# Channel操作
await agent.workspace().channel("#name").post(content)
channels = await agent.workspace().channels()  # 获取Channel列表
agents = await agent.workspace().agents()      # 获取在线Agent列表
```

---

## 三、数据模型

### 3.1 Agent简介（Agent Profile）

基于设计文档的Agent Card结构，结合心理学模型扩展：

```sql
CREATE TABLE agent_profiles (
    agent_id VARCHAR(64) PRIMARY KEY,

    -- 统一身份（对齐设计文档概念1）
    user_id VARCHAR(255),              -- ToWow全局用户ID
    secondme_id VARCHAR(255) UNIQUE,   -- SecondMe用户ID
    secondme_mcp_endpoint TEXT,        -- SecondMe MCP端点
    user_name VARCHAR(100) NOT NULL,

    -- 基础信息（对齐设计文档Agent Card）
    profile_summary TEXT,              -- 200-500字自我介绍（对应设计文档profile）
    location VARCHAR(100),             -- 地理位置
    tags JSONB,                        -- 能力标签（对齐设计文档）

    -- 能力与资源（扩展字段）
    capabilities JSONB,                -- 能提供什么（详细能力描述）
    interests JSONB,                   -- 感兴趣的领域
    recent_focus TEXT,                 -- 最近在做什么

    -- 协作风格（中等可观测）
    availability VARCHAR(50),          -- 时间可用性
    collaboration_style JSONB,         -- 合作风格偏好
    past_collaborations JSONB,         -- 过往协作记录

    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_active_at TIMESTAMP,
    active BOOLEAN DEFAULT true        -- 对齐设计文档active字段
);

-- 索引优化
CREATE INDEX idx_agent_user_id ON agent_profiles(user_id);
CREATE INDEX idx_agent_secondme_id ON agent_profiles(secondme_id);
CREATE INDEX idx_agent_location ON agent_profiles(location);
CREATE INDEX idx_agent_active ON agent_profiles(active);
CREATE INDEX idx_agent_capabilities ON agent_profiles USING GIN(capabilities);
CREATE INDEX idx_agent_tags ON agent_profiles USING GIN(tags);
```

### 3.2 需求记录（Demand）

```sql
CREATE TABLE demands (
    demand_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiator_agent_id VARCHAR(64) REFERENCES agent_profiles(agent_id),

    -- 需求内容（对齐设计文档Demand结构）
    raw_input TEXT NOT NULL,           -- 用户原始输入（对应设计文档description）
    surface_demand TEXT,               -- 表面需求
    deep_understanding JSONB,          -- SecondMe的深层理解（对应设计文档context）
    capability_tags JSONB,             -- 能力标签（对齐设计文档）

    -- 状态
    status VARCHAR(20) DEFAULT 'created',
    channel_id VARCHAR(100),           -- 关联的协商Channel

    -- 递归支持
    parent_demand_id UUID,             -- 如果是子需求
    depth INT DEFAULT 0,               -- 递归深度

    -- 时间
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_demand_status ON demands(status);
CREATE INDEX idx_demand_initiator ON demands(initiator_agent_id);
CREATE INDEX idx_demand_parent ON demands(parent_demand_id);
CREATE INDEX idx_demand_tags ON demands USING GIN(capability_tags);
```

### 3.3 协商Channel记录

```sql
CREATE TABLE collaboration_channels (
    channel_id VARCHAR(100) PRIMARY KEY,
    demand_id UUID REFERENCES demands(demand_id),

    -- 参与者
    invited_agents JSONB,              -- 被邀请的Agent列表
    responded_agents JSONB,            -- 已回应的Agent

    -- 方案
    current_proposal JSONB,            -- 当前方案
    proposal_version INT DEFAULT 0,

    -- 状态
    status VARCHAR(20) DEFAULT 'negotiating',
    negotiation_round INT DEFAULT 0,

    -- 递归信息
    parent_channel_id VARCHAR(100),    -- 父Channel（子网时有值）
    recursion_depth INT DEFAULT 0,

    -- 时间
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_channel_demand ON collaboration_channels(demand_id);
CREATE INDEX idx_channel_status ON collaboration_channels(status);
CREATE INDEX idx_channel_parent ON collaboration_channels(parent_channel_id);
```

### 3.4 Offer记录（对齐设计文档）

```sql
-- 对齐设计文档Offer数据结构
CREATE TABLE offers (
    offer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) REFERENCES agent_profiles(agent_id),
    demand_id UUID REFERENCES demands(demand_id),
    channel_id VARCHAR(100) REFERENCES collaboration_channels(channel_id),

    -- Offer内容（对齐设计文档）
    decision VARCHAR(20) NOT NULL,     -- participate | decline | need_more_info
    content TEXT,                      -- 贡献描述（对应设计文档content）
    structured_data JSONB,             -- 结构化数据（对齐设计文档）
    conditions JSONB,                  -- 条件列表
    confidence INTEGER DEFAULT 50,     -- 信心分数（对齐设计文档）
    reasoning TEXT,                    -- 决策理由

    -- 时间
    submitted_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_offer_demand ON offers(demand_id);
CREATE INDEX idx_offer_agent ON offers(agent_id);
CREATE INDEX idx_offer_channel ON offers(channel_id);
CREATE INDEX idx_offer_decision ON offers(decision);
```

### 3.5 协作历史记录

```sql
-- 用于归档完成的协作
CREATE TABLE collaboration_history (
    history_id SERIAL PRIMARY KEY,
    demand_id UUID REFERENCES demands(demand_id),
    channel_id VARCHAR(100),

    -- 参与者信息
    invited_agents JSONB,
    participants JSONB,

    -- 方案信息
    final_proposal JSONB,

    -- 统计
    negotiation_rounds INTEGER,
    subnets_count INTEGER DEFAULT 0,
    total_duration_seconds INTEGER,

    -- 状态
    status VARCHAR(20),                -- completed | failed | timeout

    -- 时间
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_history_demand ON collaboration_history(demand_id);
CREATE INDEX idx_history_status ON collaboration_history(status);
```

---

## 四、核心流程

### 4.1 需求发起流程

```
用户输入
    ↓
SecondMe（需求理解提示词）
    ↓
生成 {raw_input, surface_demand, deep_understanding}
    ↓
UserAgent 转发给 Coordinator
    ↓
Coordinator 广播到网络
```

**关键点**：
- SecondMe负责理解用户，输出结构化需求
- Coordinator只做调度，不做理解

### 4.2 智能筛选流程

```
Coordinator 收到需求
    ↓
查询 PostgreSQL 获取所有活跃Agent简介
    ↓
LLM筛选（智能筛选提示词）
    ↓
返回 10-20个候选Agent
    ↓
创建协商Channel，邀请候选人
```

**筛选逻辑**（基于心理学模型）：
1. **相关性判断**：能力、兴趣、关注点与需求的匹配
2. **状态评估**：可用性、当前负担
3. **历史参考**：过往协作风格

### 4.3 协商流程

```
Channel创建
    ↓
SecondMe代理各Agent决定是否参与（回应生成提示词）
    ↓
ChannelAdmin收集回应
    ↓
方案聚合（方案聚合提示词）
    ↓
分发方案给参与者
    ↓
SecondMe代理反馈（方案反馈提示词）
    ↓
[如有调整] 方案调整（方案调整提示词）
    ↓
[循环最多5轮]
    ↓
确定最终方案 或 生成妥协方案
```

### 4.4 递归与缺口填补

```
方案初步确定
    ↓
缺口识别（缺口识别提示词）
    ↓
[如果值得] 递归判断（递归判断提示词）
    ↓
创建子需求 → 回到4.1
```

---

## 五、Agent实现

> **重要提示**：本节代码示例使用正确的OpenAgent API。完整实现细节请参见 [supplement-01-openagent-api.md](./TECH-TOWOW-MVP-v1-supplement-01-openagent-api.md)

### 5.1 Coordinator Agent

```python
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.event_context import EventContext
from openagents.models.agent_config import AgentConfig
from typing import Dict, Any

class CoordinatorAgent(WorkerAgent):
    """中心调度Agent"""
    default_agent_id = "coordinator"

    async def on_startup(self):
        """启动时初始化"""
        self.active_demands = {}  # demand_id -> demand_info
        # 发送上线通知
        ws = self.workspace()
        await ws.channel("system").post({"type": "agent_online", "agent": "coordinator"})

    async def on_direct(self, context: EventContext):
        """处理来自UserAgent的需求"""
        message = context.incoming_event.payload.get('content', {})

        if message.get("type") == "new_demand":
            await self.handle_new_demand(message["demand"], context.source_id)

    async def handle_new_demand(self, demand: Dict[str, Any], requester_id: str):
        """处理新需求"""
        ws = self.workspace()

        # 1. 存储需求
        demand_id = await self.store_demand(demand)

        # 2. 获取所有活跃Agent简介
        agents = await self.get_active_agent_profiles()

        # 3. LLM筛选
        candidates = await self.smart_filter(demand, agents)

        # 4. 创建协商Channel
        channel_name = f"collab-{demand_id[:8]}"
        await self.create_collaboration_channel(
            channel_name,
            demand_id,
            candidates
        )

        # 5. 邀请候选人 - 使用正确的workspace API
        for agent_id in candidates:
            await ws.agent(agent_id).send({
                "type": "collaboration_invite",
                "channel": channel_name,
                "demand": demand
            })

        # 6. 通知发起者
        await ws.agent(requester_id).send({
            "type": "demand_accepted",
            "demand_id": demand_id,
            "channel": channel_name
        })

    async def smart_filter(self, demand: Dict, agents: list) -> list:
        """智能筛选候选Agent"""
        # 调用LLM进行筛选（详见supplement-01）
        pass
```

### 5.2 ChannelAdmin Agent

```python
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.event_context import ChannelMessageContext

class ChannelAdminAgent(WorkerAgent):
    """Channel管理Agent"""
    default_agent_id = "channel_admin"

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel内的消息"""
        message = context.incoming_event.payload.get('content', {})
        channel = context.channel
        sender = context.source_id

        if message.get("type") == "offer_response":
            await self.collect_response(channel, message, sender)
        elif message.get("type") == "proposal_feedback":
            await self.handle_feedback(channel, message, sender)

    async def collect_response(self, channel: str, response: Dict, sender: str):
        """收集回应"""
        ws = self.workspace()
        # 存储回应
        # 当收集足够或超时，触发方案聚合
        # 使用 ws.channel(channel).post() 发送聚合结果
        pass

    async def aggregate_proposal(self, channel: str):
        """聚合方案"""
        ws = self.workspace()
        # 调用LLM进行方案聚合
        # 使用 ws.channel(channel).post() 分发方案
        pass

    async def handle_feedback(self, channel: str, feedback: Dict, sender: str):
        """处理反馈"""
        # 根据反馈调整方案（详见supplement-01）
        pass
```

### 5.3 UserAgent

```python
from openagents.agents.worker_agent import WorkerAgent
from openagents.models.event_context import EventContext
import aiohttp

class UserAgent(WorkerAgent):
    """用户代理Agent"""

    def __init__(self, user_id: str, secondme_api_url: str, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.secondme_api = secondme_api_url

    async def on_direct(self, context: EventContext):
        """处理来自其他Agent的消息"""
        ws = self.workspace()
        message = context.incoming_event.payload.get('content', {})
        sender = context.source_id

        if message.get("type") == "collaboration_invite":
            # 转发给SecondMe决策
            response = await self.ask_secondme(
                prompt_type="response_generation",
                context=message
            )
            # 发送回应到Channel
            channel = message.get("channel")
            await ws.channel(channel).post({
                "type": "offer_response",
                "decision": response.get("decision"),
                "contribution": response.get("contribution"),
                "conditions": response.get("conditions", [])
            })

    async def ask_secondme(self, prompt_type: str, context: Dict) -> Dict:
        """调用SecondMe API"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.secondme_api}/generate",
                json={
                    "prompt_type": prompt_type,
                    "context": context
                }
            ) as resp:
                return await resp.json()
```

---

## 六、SecondMe对接

### 6.1 接口定义

**需求理解接口**：
```
POST /api/secondme/understand
Request:
{
    "user_id": "user_123",
    "raw_input": "我想在北京办一场AI聚会"
}

Response:
{
    "surface_demand": "想在北京办一场AI主题聚会",
    "deep_understanding": {
        "motivation": "上个月参加聚会后很兴奋，想当组织者",
        "likely_preferences": ["轻松氛围", "质量优先"],
        "emotional_context": "期待、有信心"
    },
    "uncertainties": ["规模未定", "是否需要分享环节"],
    "confidence": "medium"
}
```

**回应生成接口**：
```
POST /api/secondme/respond
Request:
{
    "user_id": "user_456",
    "collaboration_invite": {
        "demand": {...},
        "channel": "collab-abc123"
    }
}

Response:
{
    "decision": "participate",  // participate | decline | need_more_info
    "contribution": "可以提供30人的场地",
    "conditions": ["需要场地费用分担"],
    "reasoning": "基于用户对AI社区的兴趣..."
}
```

### 6.2 提示词集成

每个SecondMe接口对应一个提示词：
- `/understand` → 提示词1：需求理解
- `/respond` → 提示词3：回应生成
- `/feedback` → 提示词5：方案反馈

提示词存储在 `docs/prompts/` 目录，运行时加载。

---

## 七、开发任务拆分

### Phase 1：基础框架（3天）

| Task ID | 任务 | 依赖 | 产出 |
|---------|------|------|------|
| TASK-001 | 项目初始化 | - | 项目结构、依赖配置 |
| TASK-002 | OpenAgent连接 | TASK-001 | 基础Agent类、连接测试 |
| TASK-003 | 数据库初始化 | TASK-001 | PostgreSQL表结构、连接池 |

### Phase 2：核心Agent（5天）

| Task ID | 任务 | 依赖 | 产出 |
|---------|------|------|------|
| TASK-004 | Coordinator实现 | TASK-002 | 中心调度Agent |
| TASK-005 | ChannelAdmin实现 | TASK-002 | Channel管理Agent |
| TASK-006 | UserAgent实现 | TASK-002, TASK-007 | 用户代理Agent |
| TASK-007 | SecondMe Mock | TASK-001 | SecondMe模拟接口 |

### Phase 3：提示词集成（3天）

| Task ID | 任务 | 依赖 | 产出 |
|---------|------|------|------|
| TASK-008 | 需求理解集成 | TASK-007 | 提示词1实现 |
| TASK-009 | 智能筛选集成 | TASK-004 | 提示词2实现 |
| TASK-010 | 回应生成集成 | TASK-006 | 提示词3实现 |
| TASK-011 | 方案处理集成 | TASK-005 | 提示词4-6实现 |

### Phase 4：演示准备（2天）

| Task ID | 任务 | 依赖 | 产出 |
|---------|------|------|------|
| TASK-012 | 测试数据准备 | TASK-003 | 100个Mock Agent简介 |
| TASK-013 | 端到端测试 | 全部 | 完整流程测试 |
| TASK-014 | 部署配置 | 全部 | 生产环境部署 |

---

## 八、风险与应对

### 8.1 技术风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| OpenAgent不稳定 | 中 | 高 | 提前测试、准备降级方案 |
| LLM响应慢 | 中 | 中 | 超时设置、异步处理 |
| 2000人并发 | 低 | 高 | 压力测试、限流机制 |

### 8.2 业务风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 匹配质量差 | 中 | 高 | 提示词优化、人工兜底 |
| 协商时间过长 | 中 | 中 | 超时机制、妥协方案 |

---

## 九、附录

### 9.1 目录结构

```
towow/
├── openagents/              # OpenAgent相关代码
│   ├── agents/
│   │   ├── coordinator.py
│   │   ├── channel_admin.py
│   │   └── user_agent.py
│   └── config.py
├── api/                     # FastAPI后端
│   ├── main.py
│   ├── routers/
│   └── services/
├── database/
│   ├── models.py
│   └── migrations/
├── prompts/                 # 提示词存储
│   ├── demand_understanding.txt
│   ├── smart_filter.txt
│   └── ...
├── tests/
├── docs/
└── requirements.txt
```

### 9.2 关键依赖

```
openagents>=0.1.0
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
aiohttp>=3.8.0
anthropic>=0.20.0
pydantic>=2.0.0
```

---

## 十、补充文档索引

本技术方案包含以下补充文档，详细定义了各子系统的实现：

| 补充文档 | 内容 | 优先级 |
|---------|------|--------|
| [supplement-01-openagent-api.md](./TECH-TOWOW-MVP-v1-supplement-01-openagent-api.md) | OpenAgent API正确使用方式、Agent基类重写 | P0 |
| [supplement-02-events.md](./TECH-TOWOW-MVP-v1-supplement-02-events.md) | 事件类型定义、Payload模型、事件总线 | P1 |
| [supplement-03-frontend.md](./TECH-TOWOW-MVP-v1-supplement-03-frontend.md) | 前端架构、SSE实时推送、TASK-015~018 | P0 |
| [supplement-04-subnet.md](./TECH-TOWOW-MVP-v1-supplement-04-subnet.md) | 递归子网机制、缺口识别、TASK-019 | P1 |
| [supplement-05-fallback.md](./TECH-TOWOW-MVP-v1-supplement-05-fallback.md) | 降级预案、熔断器、限流、演示模式、TASK-020 | P1 |

### 10.1 重要修正说明

**OpenAgent API使用修正**（详见 supplement-01）：

本文档第五节的Agent实现代码示例存在API使用错误，正确的使用方式：

```python
# ❌ 错误写法（本文档原有示例）
from openagents import Agent
class MyAgent(Agent):
    async def on_direct_message(self, context): pass
    async def on_channel_message(self, context): pass
await agent.send_direct(to="agent_id", text="message")

# ✅ 正确写法（详见 supplement-01）
from openagents.agents.worker_agent import WorkerAgent
class MyAgent(WorkerAgent):
    async def on_direct(self, context: EventContext): pass
    async def on_channel_post(self, context: ChannelMessageContext): pass
await self.workspace().agent("agent_id").send(content)
```

### 10.2 任务全景

| 阶段 | 任务 | 来源 |
|------|------|------|
| Phase 1 | TASK-001~003 基础框架 | 主文档 |
| Phase 2 | TASK-004~007 核心Agent | 主文档 |
| Phase 3 | TASK-008~011 提示词集成 | 主文档 |
| Phase 4 | TASK-012~014 演示准备 | 主文档 |
| Phase 5 | TASK-015~018 前端开发 | supplement-03 |
| Phase 6 | TASK-019 递归子网 | supplement-04 |
| Phase 7 | TASK-020 降级与监控 | supplement-05 |

**总计**: 20个开发任务

### 10.3 任务依赖分析表

#### 依赖类型定义

| 类型 | 定义 | 规则 |
|------|------|------|
| **硬依赖** | 代码直接 import 了其他任务的模块 | 禁止 mock，必须等实现完成 |
| **接口依赖** | 只需要调用接口，不依赖具体实现 | 允许契约先行，可并行开发 |

#### 完整依赖矩阵

| TASK ID | 任务名称 | 硬依赖 | 接口依赖 | 可并行 | 关键路径 |
|---------|---------|--------|---------|--------|---------|
| TASK-001 | 项目初始化 | - | - | - | YES |
| TASK-002 | OpenAgent连接 | TASK-001 | - | - | YES |
| TASK-003 | 数据库初始化 | TASK-001 | - | TASK-002 | YES |
| TASK-004 | Coordinator实现 | TASK-002, TASK-003 | - | - | YES |
| TASK-005 | ChannelAdmin实现 | TASK-002, TASK-003 | TASK-004(协议) | - | YES |
| TASK-006 | UserAgent实现 | TASK-002 | TASK-007(SecondMe API) | - | - |
| TASK-007 | SecondMe Mock | TASK-001 | - | TASK-002~006 | - |
| TASK-008 | 需求理解集成 | TASK-007 | - | TASK-009~011 | - |
| TASK-009 | 智能筛选集成 | TASK-004, TASK-003 | - | TASK-008,010,011 | YES |
| TASK-010 | 回应生成集成 | TASK-006, TASK-007 | - | TASK-008,009,011 | - |
| TASK-011 | 方案处理集成 | TASK-005 | - | TASK-008~010 | YES |
| TASK-012 | 测试数据准备 | TASK-003 | - | TASK-004~011 | - |
| TASK-013 | 端到端测试 | TASK-008~012 | - | - | YES |
| TASK-014 | 部署配置 | TASK-013 | - | - | YES |
| TASK-015 | 前端项目初始化 | - | - | TASK-001~007 | - |
| TASK-016 | 需求提交页面 | TASK-015 | TASK-018(SSE API) | - | - |
| TASK-017 | 协商实时展示 | TASK-015, TASK-018 | - | - | YES |
| TASK-018 | 实时推送服务 | TASK-002 | - | TASK-015~017 | YES |
| TASK-019 | 递归子网实现 | TASK-005, TASK-011 | - | - | - |
| TASK-020 | 降级与监控 | TASK-013 | - | - | - |

#### 关键路径分析

```
关键路径（决定最短完成时间）:

TASK-001 → TASK-002 → TASK-004 → TASK-009 → TASK-013 → TASK-014
                ↓
           TASK-003 → TASK-005 → TASK-011 →↗
                ↓
           TASK-018 → TASK-017 →↗

并行开发窗口:
- TASK-002 完成后: TASK-003, TASK-015 可并行
- TASK-003 完成后: TASK-004~006, TASK-012 可并行
- TASK-015 完成后: TASK-016 可开始（接口依赖TASK-018）
- 后端前端可大部分并行开发
```

#### 接口契约（必须先定义）

以下接口契约必须在相关任务开始前定义完成：

| 接口 | 定义位置 | 依赖方 | 提供方 |
|------|---------|--------|--------|
| SecondMe API | TASK-007 | TASK-006, TASK-008, TASK-010 | SecondMe Mock |
| SSE Event Format | TASK-018 | TASK-016, TASK-017 | 实时推送服务 |
| Agent Message Protocol | TASK-002 | TASK-004~006 | TowowBaseAgent |
| DB Models | TASK-003 | TASK-004, TASK-005, TASK-009 | 数据库服务 |

#### 推荐开发顺序

**Week 1（基础框架）**:
- Day 1: TASK-001, TASK-015
- Day 2: TASK-002, TASK-003
- Day 3: TASK-007

**Week 2（核心Agent + 前端）**:
- Day 4: TASK-004, TASK-016
- Day 5: TASK-005, TASK-018
- Day 6: TASK-006, TASK-017

**Week 3（提示词集成）**:
- Day 7: TASK-008, TASK-009
- Day 8: TASK-010, TASK-011
- Day 9: TASK-012

**Week 4（集成测试与部署）**:
- Day 10: TASK-013
- Day 11: TASK-019, TASK-020
- Day 12: TASK-014

**总计**: 12个工作日（可压缩至10天）

---

**文档版本**: v1.2
**创建时间**: 2026-01-21
**最后更新**: 2026-01-21
**状态**: 技术方案完成（含5个补充文档）

### 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2026-01-21 | 初始版本 |
| v1.1 | 2026-01-21 | 添加补充文档索引 |
| v1.2 | 2026-01-21 | 修正OpenAgent API用法（第五节）；添加任务依赖分析表（10.3节） |
