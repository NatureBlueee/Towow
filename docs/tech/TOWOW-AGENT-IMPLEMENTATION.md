# ToWow Agent 系统实现详解

**文档版本**: v1.0
**更新日期**: 2026-01-23
**目标读者**: OpenAgent 开发团队
**目的**: 说明 ToWow 项目中 Agent 系统的当前实现方式，寻求架构改进建议

---

## 📋 目录

1. [项目概述](#项目概述)
2. [当前实现方案](#当前实现方案)
3. [Agent 类型与职责](#agent-类型与职责)
4. [关键机制实现](#关键机制实现)
5. [技术挑战与问题](#技术挑战与问题)
6. [寻求的帮助](#寻求的帮助)

---

## 项目概述

### ToWow 是什么？

ToWow 是一个**大规模 AI Agent 协作平台**，目标是实现 **2000+ 个 Agent 同时在线**并进行智能协商。

**核心场景**:
```
用户发起需求 "想在北京办一场 AI 主题 Workshop"
  ↓
系统自动从 2000 个 Agent 中筛选出 10-15 个候选人
  ↓
这些 Agent 代表真实用户进行多轮协商
  ↓
自动聚合方案，处理反馈，达成共识
  ↓
如果能力有缺口，递归创建子协商（最多 2 层）
```

### 为什么需要 Agent 框架？

我们的核心需求：
- ✅ **Agent 间通信**: 需要 Coordinator、ChannelAdmin、UserAgent 三类 Agent 互相发送消息
- ✅ **Channel 管理**: 每个需求创建一个独立的协商 Channel，多个 Agent 在其中讨论
- ✅ **事件驱动**: 需求理解、筛选完成、方案生成等都通过事件广播
- ✅ **高并发**: 支持 2000 个 UserAgent 同时在线
- ✅ **生命周期管理**: Agent 的启动、关闭、健康检查

---

## 当前实现方案

### 实现概要

**现状**: 我们**没有完全使用 OpenAgent 框架**，而是自己实现了一套**轻量级的 Agent 基础设施**。

**原因**:
1. **学习曲线**: 团队对 OpenAgent 的 API 和概念不够熟悉
2. **快速迭代**: 需要在短时间内（7-10 天）完成 MVP 演示
3. **不确定性**: 不确定 OpenAgent 是否能满足我们的所有需求
4. **控制力**: 希望完全掌控底层实现，便于调试

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    ToWow 应用层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ FastAPI      │  │ Frontend     │  │ PostgreSQL   │      │
│  │ (REST API)   │  │ (React)      │  │ (Database)   │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
└─────────┼─────────────────────────────────────────────────┘
          │ 调用
┌─────────▼─────────────────────────────────────────────────┐
│            ToWow Agent 层（自己实现）                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Coordinator  │  │ ChannelAdmin │  │ UserAgent    │    │
│  │ Agent        │  │ Agent        │  │ (2000 实例)  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                  │                  │            │
│         └────────┬─────────┴──────────────────┘            │
│                  │                                         │
│         ┌────────▼─────────┐                              │
│         │  AgentRouter     │  ← 消息路由（自己实现）      │
│         │  (消息去重、分发) │                              │
│         └────────┬─────────┘                              │
│                  │                                         │
│         ┌────────▼─────────┐                              │
│         │ TowowBaseAgent   │  ← Agent 基类（自己实现）    │
│         │ (workspace、send)│                              │
│         └──────────────────┘                              │
└─────────────────────────────────────────────────────────┘
          │ (理想中应该在这里用 OpenAgent)
┌─────────▼─────────────────────────────────────────────────┐
│              OpenAgent 框架（未使用）                       │
│  - Agent 注册与发现                                        │
│  - WebSocket/gRPC 通信                                     │
│  - Channel 原生支持                                        │
│  - 事件订阅与分发                                          │
└───────────────────────────────────────────────────────────┘
```

### 关键代码文件

```
towow/openagents/
├── agents/
│   ├── base.py              # TowowBaseAgent - 自己实现的基类
│   ├── coordinator.py       # Coordinator Agent (23KB, 657 行)
│   ├── channel_admin.py     # ChannelAdmin Agent (77KB, 2000+ 行)
│   ├── user_agent.py        # UserAgent (37KB, 900+ 行)
│   ├── router.py            # AgentRouter - 消息路由器
│   └── factory.py           # AgentFactory - Agent 实例管理
└── launcher.py              # AgentLauncher - 生命周期管理
```

**代码量统计**:
- 核心 Agent 代码: ~140KB, 约 3500+ 行
- 测试代码: ~140KB, 8 个测试文件
- 总计: **23,000 行代码**

---

## Agent 类型与职责

### 1. Coordinator Agent (调度中枢)

**职责**:
- 接收新需求
- 调用 LLM 进行智能筛选（从 2000 人中选 3-15 人）
- 创建协商 Channel
- 通知 ChannelAdmin 开始管理

**关键实现**:

```python
class CoordinatorAgent(TowowBaseAgent):
    """
    调度中枢 - 单例 Agent
    """

    async def on_direct(self, ctx: EventContext):
        """接收直接消息（如新需求）"""
        content = ctx.incoming_event.payload.get("content", {})
        msg_type = content.get("type")

        if msg_type == "new_demand":
            # 1. 调用 LLM 理解需求
            understanding = await self._understand_demand(raw_input, user_id)

            # 2. 智能筛选候选人
            candidates = await self._smart_filter(demand_id, understanding)

            # 3. 创建 Channel 并通知 ChannelAdmin
            channel_id = f"collab-{demand_id[2:]}"
            await self.send_to_agent("channel_admin", {
                "type": "create_channel",
                "channel_id": channel_id,
                "candidates": candidates
            })
```

**智能筛选机制**:
```python
async def _smart_filter(self, demand_id: str, understanding: Dict) -> List[Dict]:
    """
    基于 LLM 进行智能筛选

    输入: 需求理解结果 + 2000 个 Agent 的 Profile
    输出: 3-15 个最匹配的候选人

    提示词包含:
    - 能力匹配优先
    - 地域相关性
    - 多样性互补
    - 规模适配
    """
    # 获取所有可用 Agent
    available_agents = await self._get_available_agents()  # 从数据库

    # 构建筛选提示词
    prompt = self._build_filter_prompt(understanding, available_agents)

    # 调用 LLM
    response = await self.llm.complete(
        prompt=prompt,
        system=self._get_filter_system_prompt(),
        max_tokens=4000,
        temperature=0.3
    )

    # 解析 JSON 响应
    candidates = self._parse_filter_response(response, available_agents)
    return candidates
```

### 2. ChannelAdmin Agent (协商管理者)

**职责**:
- 管理单个协商 Channel 的全生命周期
- 向候选 Agent 广播需求
- 收集响应（Offer）并聚合方案
- 处理多轮反馈（最多 5 轮）
- 识别能力缺口，触发子网递归

**状态机**:
```
CREATED → BROADCASTING → COLLECTING → AGGREGATING →
PROPOSAL_SENT → NEGOTIATING → FINALIZED/FAILED
```

**关键实现**:

```python
class ChannelAdminAgent(TowowBaseAgent):
    """
    Channel 管理者 - 每个需求一个实例
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.channels: Dict[str, ChannelState] = {}
        self._timeout_tasks: Dict[str, asyncio.Task] = {}

    async def start_managing(
        self,
        channel_id: str,
        demand: Dict,
        invited_agents: List[Dict],
        max_rounds: int = 5
    ):
        """开始管理一个 Channel"""
        # 1. 创建 Channel 状态
        state = ChannelState(
            channel_id=channel_id,
            demand=demand,
            candidates=invited_agents,
            max_rounds=max_rounds
        )
        self.channels[channel_id] = state

        # 2. 广播需求给候选人
        await self._broadcast_demand(state)

    async def _broadcast_demand(self, state: ChannelState):
        """向所有候选人广播需求"""
        for candidate in state.candidates:
            agent_id = candidate["agent_id"]
            await self.send_to_agent(agent_id, {
                "type": "demand_offer",
                "channel_id": state.channel_id,
                "demand": state.demand,
                "filter_reason": candidate.get("reason")
            })

        # 3. 启动收集超时
        timeout_task = asyncio.create_task(
            self._wait_for_responses(state.channel_id)
        )
        self._timeout_tasks[state.channel_id] = timeout_task

    async def handle_response(self, channel_id: str, agent_id: str, response: Dict):
        """处理 Agent 的响应"""
        state = self.channels[channel_id]
        state.responses[agent_id] = response

        # 如果收集完成，进入聚合阶段
        if len(state.responses) >= len(state.candidates) * 0.7:  # 70% 响应率
            await self._aggregate_offers(state)

    async def _aggregate_offers(self, state: ChannelState):
        """聚合所有 Offer 成为一个方案"""
        # 1. 调用 LLM 聚合
        proposal = await self._llm_aggregate(state)

        # 2. 分发方案给所有参与者
        await self._distribute_proposal(state, proposal)

        # 3. 等待反馈
        await self._wait_for_feedback(state)

    async def _llm_aggregate(self, state: ChannelState) -> Dict:
        """使用 LLM 聚合方案"""
        prompt = self._build_aggregate_prompt(state)
        response = await self.llm.complete(
            prompt=prompt,
            system="你是协商聚合专家，负责整合多个 Offer...",
            max_tokens=2000
        )
        return self._parse_proposal(response)

    async def _identify_gaps(self, state: ChannelState, proposal: Dict):
        """识别能力缺口"""
        # 使用 LLM 分析是否有未覆盖的能力
        gaps = await self._llm_identify_gaps(state, proposal)

        if gaps and state.recursion_depth < 2:  # 最多 2 层递归
            # 触发子网
            await self._trigger_subnet(state, gaps)
```

**幂等性控制**:
```python
@dataclass
class ChannelState:
    # 幂等性控制字段
    proposal_distributed: bool = False  # 方案是否已分发
    gaps_identified: bool = False       # 缺口是否已识别
    subnet_triggered: bool = False      # 子网是否已触发
    finalized_notified: bool = False    # 完成通知是否已发送
```

### 3. UserAgent (用户数字分身)

**职责**:
- 代表用户接收需求邀请
- 调用 SecondMe（或 LLM）生成响应
- 评估方案并提供反馈
- 自主决策是否参与

**关键实现**:

```python
class UserAgent(TowowBaseAgent):
    """
    用户数字分身 - 每个用户一个实例
    """

    def __init__(self, user_id: str, profile: Dict, secondme_service=None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.profile = profile
        self.secondme = secondme_service
        self.active_channels: Dict[str, Dict] = {}

    @property
    def agent_id(self) -> str:
        return f"user_agent_{self.user_id}"

    async def _handle_demand_offer(self, ctx, data: Dict):
        """处理需求邀请"""
        channel_id = data["channel_id"]
        demand = data["demand"]

        # 1. 生成响应
        response = await self._generate_response(demand, filter_reason)

        # 2. 发送给 ChannelAdmin
        await self.send_to_agent("channel_admin", {
            "type": "offer_response",
            "channel_id": channel_id,
            "agent_id": self.agent_id,
            **response
        })

    async def _generate_response(self, demand: Dict, filter_reason: str) -> Dict:
        """生成需求响应"""
        # 优先使用 SecondMe
        if self.secondme:
            return await self.secondme.generate_response(
                user_id=self.user_id,
                demand=demand,
                profile=self.profile
            )

        # 降级使用 LLM
        if self.llm:
            return await self._llm_generate_response(demand, filter_reason)

        # 最终降级：Mock 决策
        return self._mock_response(demand)
```

---

## 关键机制实现

### 1. Agent 基类（TowowBaseAgent）

**我们自己实现了一个基类**，模拟 OpenAgent 的接口：

```python
class TowowBaseAgent(ABC):
    """
    ToWow 基础 Agent 类

    提供独立的基类实现，不依赖外部 OpenAgent 包
    """

    def __init__(self, db=None, llm_service=None, agent_id=None, **kwargs):
        self.db = db
        self.llm = llm_service
        self._agent_id = agent_id
        self._workspace = _MockWorkspace(self)

    def workspace(self) -> _MockWorkspace:
        """获取 Workspace（模拟 OpenAgent 的 workspace() API）"""
        return self._workspace

    # 便捷方法
    async def send_to_agent(self, agent_id: str, data: Dict) -> Dict:
        """发送消息给指定 Agent"""
        ws = self.workspace()
        return await ws.agent(agent_id).send(data)

    async def post_to_channel(self, channel: str, data: Dict) -> Dict:
        """向 Channel 发送消息"""
        ws = self.workspace()
        return await ws.channel(channel).post(data)

    # 生命周期钩子
    async def on_startup(self):
        """Agent 启动时调用"""
        pass

    async def on_shutdown(self):
        """Agent 关闭时调用"""
        pass

    # 消息处理钩子（子类重写）
    async def on_direct(self, context: EventContext):
        """处理直接消息"""
        pass

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理 Channel 消息"""
        pass
```

**Mock Workspace**:
```python
class _MockWorkspace:
    """模拟 OpenAgent 的 workspace API"""

    def agent(self, agent_id: str) -> _MockAgentHandle:
        """获取 Agent 句柄"""
        return _MockAgentHandle(agent_id, self._agent)

    def channel(self, channel_name: str) -> _MockChannelHandle:
        """获取 Channel 句柄"""
        return _MockChannelHandle(channel_name, self._agent)
```

### 2. 消息路由（AgentRouter）

**核心问题**: `send_to_agent()` 如何真正把消息发给目标 Agent？

**我们的实现**:

```python
class AgentRouter:
    """
    Agent 消息路由器

    负责在 Agent 间路由消息，使用 AgentFactory 获取 Agent 实例
    """

    async def route_message(
        self,
        from_agent: str,
        to_agent: str,
        data: Dict
    ) -> Dict:
        """路由消息到目标 Agent"""

        # 1. 消息去重（防止重复处理）
        message_key = self._generate_message_key(from_agent, to_agent, data)
        if message_key in self._processing_messages:
            return {"status": "duplicate"}

        self._processing_messages.add(message_key)

        try:
            # 2. 获取 AgentFactory
            from . import get_agent_factory
            factory = get_agent_factory()

            # 3. 根据目标 ID 获取 Agent 实例
            target_agent = self._get_agent(factory, to_agent)

            # 4. 构造 EventContext 并调用 on_direct
            event = _DirectEvent(data)
            context = EventContext(incoming_event=event)

            # 5. 同步等待消息处理完成（避免并发问题）
            await target_agent.on_direct(context)

            return {"status": "delivered"}

        finally:
            self._processing_messages.discard(message_key)

    def _get_agent(self, factory, agent_id: str):
        """从 Factory 获取 Agent 实例"""
        if agent_id == "coordinator":
            return factory.get_coordinator()
        elif agent_id == "channel_admin":
            return factory.get_channel_admin()
        elif agent_id.startswith("user_agent_"):
            user_id = agent_id.replace("user_agent_", "")
            return factory.get_user_agent(user_id, profile)
```

**防重机制**:
```python
# 消息去重：记录正在处理的消息
self._processing_messages: set = set()

# 最近处理的消息ID（用于幂等性检查）
self._recent_message_ids: dict = {}  # message_key -> timestamp

def _generate_message_key(self, from_agent: str, to_agent: str, data: Dict) -> str:
    """生成消息唯一键"""
    msg_type = data.get("type", "unknown")
    channel_id = data.get("channel_id", "")
    return f"{from_agent}:{to_agent}:{msg_type}:{channel_id}"
```

### 3. Agent 实例管理（AgentFactory）

**问题**: 如何管理 2000 个 UserAgent 实例？

**我们的实现**:

```python
class AgentFactory:
    """
    Agent 工厂 - 单例模式

    负责创建和管理所有 Agent 实例
    """

    def __init__(self, db, llm_service, secondme_service):
        self.db = db
        self.llm = llm_service
        self.secondme = secondme_service

        # 单例 Agent
        self._coordinator: Optional[CoordinatorAgent] = None
        self._channel_admin: Optional[ChannelAdminAgent] = None

        # UserAgent 缓存（懒加载）
        self._user_agents: Dict[str, UserAgent] = {}

    def get_coordinator(self) -> CoordinatorAgent:
        """获取 Coordinator Agent（单例）"""
        if not self._coordinator:
            self._coordinator = CoordinatorAgent(
                db=self.db,
                llm_service=self.llm,
                secondme_service=self.secondme,
                agent_id="coordinator"
            )
        return self._coordinator

    def get_user_agent(self, user_id: str, profile: Dict) -> UserAgent:
        """获取 UserAgent（懒加载 + 缓存）"""
        agent_id = f"user_agent_{user_id}"

        if agent_id not in self._user_agents:
            self._user_agents[agent_id] = UserAgent(
                user_id=user_id,
                profile=profile,
                db=self.db,
                llm_service=self.llm,
                secondme_service=self.secondme
            )

        return self._user_agents[agent_id]
```

### 4. 生命周期管理（AgentLauncher）

```python
class AgentLauncher:
    """Agent 启动器，管理 Agent 的生命周期"""

    def __init__(self):
        self._agents: List[TowowBaseAgent] = []
        self._running = False

    def register(self, agent: TowowBaseAgent):
        """注册一个 Agent 实例"""
        self._agents.append(agent)
        return self

    async def start_all(self):
        """启动所有注册的 Agent"""
        self._running = True
        tasks = [agent.on_startup() for agent in self._agents]
        await asyncio.gather(*tasks)

    async def stop_all(self):
        """停止所有 Agent"""
        tasks = [agent.on_shutdown() for agent in self._agents]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._running = False
```

---

## 技术挑战与问题

### 1. 缺少真正的 Channel 管理

**现状**: 我们的 `post_to_channel()` 只是 Mock 实现，没有真正的 Channel 广播机制。

**问题**:
```python
async def post_to_channel(self, channel: str, data: Dict) -> Dict:
    """向 Channel 发送消息"""
    logger.debug(f"[Mock] Posting to #{channel}: {data}")
    return {"status": "mock_posted", "channel": channel}
    # ⚠️ 这里应该：
    # 1. 找到 Channel 的所有订阅者
    # 2. 向他们广播消息
    # 3. 返回广播结果
```

**影响**:
- ChannelAdmin 无法真正向候选人广播需求
- 只能通过 `send_to_agent()` 逐个发送（效率低）

### 2. Agent 注册与发现机制缺失

**现状**: 我们通过 `AgentFactory` 手动管理 Agent 实例。

**问题**:
- 无法动态发现哪些 Agent 在线
- `get_online_agents()` 返回空列表
- 无法实现真正的分布式 Agent 网络

**理想状态**:
```python
async def get_online_agents(self) -> List[str]:
    """获取在线 Agent 列表"""
    # ⚠️ 应该从 OpenAgent 网络获取
    # 而不是返回空列表
    return []
```

### 3. 消息路由性能问题

**现状**: 我们的 `AgentRouter` 是同步等待消息处理。

**问题**:
```python
# 同步等待消息处理完成
await target_agent.on_direct(context)
# ⚠️ 这会导致发送方阻塞，直到接收方处理完成
```

**影响**:
- 高并发场景下，消息处理会排队
- 无法实现真正的异步消息传递

**理想状态**: 消息投递后立即返回，接收方异步处理。

### 4. 事件总线未完全集成

**现状**: 我们有一个简单的 `event_bus`，但没有和 Agent 消息系统打通。

```python
async def _publish_event(self, event_type: str, payload: Dict):
    """发布事件到事件总线"""
    try:
        from events.bus import event_bus
        await event_bus.publish({
            "event_type": event_type,
            "payload": payload
        })
    except ImportError:
        self._logger.debug("事件总线不可用")
```

**问题**:
- Agent 内部事件 vs. 系统级事件 混乱
- 前端 SSE 推送依赖 `event_bus`，但 Agent 消息不经过它

### 5. 缺少健康检查与心跳

**现状**: 没有实现 Agent 的健康检查机制。

**问题**:
- 无法知道某个 Agent 是否卡死
- 没有超时机制（除了手动实现的 `asyncio.wait_for`）
- 无法实现故障恢复

### 6. 测试困难

**现状**: 因为是 Mock 实现，测试只能验证逻辑，无法测试真实通信。

**问题**:
```python
# 测试代码
response = await coordinator.send_to_agent("channel_admin", {
    "type": "create_channel"
})
# ⚠️ 这只是调用了 Mock，没有真正走网络
```

---

## 寻求的帮助

### 问题 1: 如何正确使用 OpenAgent？

**我们想知道**:
1. OpenAgent 的 `WorkerAgent` 基类应该如何使用？
2. 如何实现 Agent 间的直接消息发送？
3. Channel 的正确使用方式是什么？
4. 事件订阅机制如何工作？

**我们的疑惑**:
```python
# 假设我们继承 WorkerAgent
from openagents import WorkerAgent

class CoordinatorAgent(WorkerAgent):
    def __init__(self):
        super().__init__(agent_id="coordinator")

    async def on_message(self, message):
        # ⚠️ 问题：
        # 1. 如何向另一个 Agent 发送消息？
        # 2. 如何创建 Channel？
        # 3. 如何广播消息到 Channel？
        # 4. workspace() API 怎么用？
        pass
```

### 问题 2: OpenAgent 能否满足我们的需求？

**我们的核心需求**:
1. ✅ **2000 个 Agent 同时在线** - OpenAgent 是否支持？
2. ✅ **每个需求创建一个 Channel** - 动态创建 Channel 是否可行？
3. ✅ **Agent 间直接消息 + Channel 广播** - 两种通信方式如何配合？
4. ✅ **幂等性保证** - 消息去重机制是否内置？
5. ✅ **超时控制** - 如何实现 "等待响应最多 30 秒"？

### 问题 3: 迁移成本如何？

**当前代码量**:
- 自己实现的基础设施: ~2000 行（base.py, router.py, factory.py, launcher.py）
- 业务逻辑: ~3500 行（coordinator, channel_admin, user_agent）

**迁移问题**:
1. 如果切换到 OpenAgent，业务逻辑需要改多少？
2. 测试用例是否需要重写？
3. 是否有迁移指南或最佳实践？

### 问题 4: 性能与扩展性

**我们的疑问**:
1. OpenAgent 在 2000 个 Agent 场景下的性能如何？
2. 消息传递的延迟大概是多少？
3. 是否支持 Agent 的动态扩缩容？
4. 内存占用如何？（我们担心 2000 个 Agent 会不会爆内存）

---

## 总结

### 当前状态

✅ **已完成**:
- 三类 Agent 的业务逻辑实现
- 智能筛选、方案聚合、多轮协商
- 子网递归机制
- 基本的消息路由
- 完整的测试覆盖

❌ **缺失**:
- 真正的 Agent 通信机制（只有 Mock）
- Channel 广播功能
- Agent 注册与发现
- 健康检查与心跳
- 分布式部署能力

### 我们的困惑

**核心问题**: **我们应该继续自己实现底层，还是切换到 OpenAgent？**

**如果切换到 OpenAgent**:
- ✅ 优点: 省去底层通信实现，专注业务逻辑
- ❌ 缺点: 学习曲线，迁移成本，不确定是否满足需求

**如果继续自己实现**:
- ✅ 优点: 完全掌控，灵活调整
- ❌ 缺点: 需要实现 WebSocket/gRPC、Channel 管理、健康检查等（工作量巨大）

### 我们希望得到的建议

1. **架构建议**: 基于我们的需求，OpenAgent 是否是合适的选择？
2. **使用指导**: 如果用 OpenAgent，应该如何正确使用（最佳实践）？
3. **迁移方案**: 如何从当前实现迁移到 OpenAgent（分步指南）？
4. **性能评估**: OpenAgent 在大规模场景下的实际表现？

---

## 附录

### 相关文档

- **设计文档**: `ToWow-Design-MVP.md` - 产品设计和 MVP 范围
- **技术文档**: `docs/tech/TECH-TOWOW-MVP-v1.md` - 详细技术方案
- **测试指南**: `TESTING_GUIDE.md` - 测试策略和用例
- **OpenAgent 指南**: `OPENAGENTS_DEV_GUIDE.md` - OpenAgent 使用笔记

### 联系方式

如有任何问题或建议，请通过以下方式联系我们：
- GitHub Issues: [项目链接]
- 邮件: [联系邮箱]

---

**感谢 OpenAgent 团队的支持！**
我们期待您的反馈和建议。🙏
