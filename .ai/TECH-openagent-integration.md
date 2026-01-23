# TECH: ToWow OpenAgents 框架集成技术方案

**文档版本**: v1.0
**状态**: DRAFT
**创建日期**: 2025-01-23
**作者**: tech

## 关联文档

- 迁移分析: `/worktree-openagent/.ai/MIGRATION-openagent-analysis.md`
- 任务拆解: `/worktree-openagent/.ai/TASK-openagent-migration.md`
- 现有代码: `/towow/openagents/agents/`

---

## 1. 技术决策与权衡

### 1.1 框架选型：OpenAgents vs 当前实现

| 维度 | 当前实现 | OpenAgents | 决策 |
|------|----------|------------|------|
| 消息路由 | 自研 AgentRouter，Mock 实现 | 原生多协议支持 (HTTP/gRPC/MCP) | **采用 OpenAgents** |
| 事件处理 | 手动分发 + EventBus | `@on_event()` 装饰器模式 | **采用 OpenAgents** |
| 状态管理 | 手写状态机 (ChannelStatus) | 无内置，需自定义 | **保留自研** |
| LLM 集成 | CircuitBreaker + Fallback | 无内置熔断 | **保留自研** |
| SSE 推送 | 自研 EventBus | 无内置 | **保留自研 + 桥接** |

**核心决策**: 采用 OpenAgents 作为底层通信框架，保留 ToWow 特有的业务逻辑层（状态机、熔断器、SSE）。

### 1.2 迁移策略：渐进式 vs 一步到位

```
[DECISION] 采用渐进式迁移（Strangler Fig Pattern）

理由：
1. 风险可控：每阶段可独立验证
2. 前端零改动：通过 SSE Bridge 保持兼容
3. 可回滚：双模式运行期间支持快速切换
4. 团队学习曲线：分阶段熟悉新框架
```

**迁移路径**:
```
Phase 1: 基础适配层 (TowowWorkerAgent)
    ↓
Phase 2: Coordinator 迁移
    ↓
Phase 3: ChannelAdmin + 状态机
    ↓
Phase 4: UserAgent + SSE 完整桥接
```

### 1.3 状态持久化：内存 vs 外部存储

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 内存状态 | 简单、低延迟 | 重启丢失、无法水平扩展 | MVP/单实例 |
| Redis | 高性能、支持过期 | 需要序列化、额外依赖 | 生产/多实例 |
| PostgreSQL | 持久化、可查询 | 延迟较高 | 审计/历史分析 |

**当前决策**:
```
[DECISION] Phase 1-3 保持内存状态
[OPEN] Phase 4 评估 Redis 持久化需求（取决于多实例部署计划）
```

### 1.4 LLM 调用：OpenAgents 原生 vs 保留自研

```
[DECISION] 保留自研 LLM 服务层

理由：
1. CircuitBreaker 已经稳定运行
2. FALLBACK_RESPONSES 是业务关键的降级策略
3. 统计监控已集成
4. OpenAgents 无内置熔断，迁移后仍需自研
```

**集成方式**: 在 `TowowWorkerAgent` 中注入 LLMService 实例。

---

## 2. 架构设计

### 2.1 目标架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ToWow Frontend                                │
│                    (SSE EventSource - 零改动)                            │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ SSE
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SSE Bridge Layer                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  TowowEventBridge                                                │   │
│  │  - OpenAgents Event ←→ ToWow SSE Event 转换                      │   │
│  │  - 订阅 OpenAgents 通道消息                                       │   │
│  │  - 发布到前端 EventBus                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    OpenAgents Runtime (Port 8700/8600/8800)             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ Coordinator │  │ChannelAdmin │  │  UserAgent  │  │  UserAgent  │   │
│  │   Agent     │  │   Agent     │  │   (Alice)   │  │   (Bob)     │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │
│         │                │                │                │          │
│         └────────────────┴────────────────┴────────────────┘          │
│                           │                                            │
│                  workspace().agent().send()                            │
│                  workspace().channel().post()                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Shared Services Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │   LLMService    │  │  CircuitBreaker │  │   EventBus      │        │
│  │  (with Fallback)│  │  (CLOSED/OPEN/  │  │ (SSE Publisher) │        │
│  │                 │  │   HALF_OPEN)    │  │                 │        │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件职责划分

| 组件 | 职责 | 继承关系 | 关键方法 |
|------|------|----------|----------|
| `TowowWorkerAgent` | 基类适配层 | `WorkerAgent` | `call_llm()`, `emit_sse()`, `get_state()` |
| `TowowCoordinator` | 需求理解、Agent 筛选、Channel 创建 | `TowowWorkerAgent` | `@on_event("towow.demand.*")` |
| `TowowChannelAdmin` | 状态机管理、协商流程、子网触发 | `TowowWorkerAgent` | `_transition_state()`, `_trigger_subnet()` |
| `TowowUserAgent` | 用户数字分身、响应生成 | `TowowWorkerAgent` | `@on_event("towow.invite")`, `@on_event("towow.proposal")` |
| `TowowEventBridge` | SSE 桥接 | 独立类 | `on_openagents_event()`, `emit_to_frontend()` |

### 2.3 数据流设计

#### 2.3.1 需求提交流程

```
用户提交需求
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend API: POST /api/demands                         │
│ → EventBus.emit("towow.demand.new", {demand_data})     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ TowowCoordinator.on_demand_new()                        │
│ 1. call_llm("理解需求") → demand_analysis               │
│ 2. call_llm("筛选 Agent") → filtered_agents             │
│ 3. workspace().channel().create(channel_config)         │
│ 4. emit_sse("channel.created", channel_info)           │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ TowowChannelAdmin.start_managing(channel_id)            │
│ → 状态: CREATED → BROADCASTING                          │
│ → 广播邀请到所有 filtered_agents                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ TowowUserAgent.on_invite()                              │
│ 1. call_llm("评估邀请") → decision                      │
│ 2. if accept: workspace().channel().post(proposal)      │
│ 3. emit_sse("agent.response", response_data)           │
└─────────────────────────────────────────────────────────┘
```

#### 2.3.2 协商状态机流程

```
                    ┌─────────────┐
                    │   CREATED   │
                    └──────┬──────┘
                           │ start_managing()
                           ▼
                    ┌─────────────┐
                    │ BROADCASTING│
                    └──────┬──────┘
                           │ 广播完成 / 超时
                           ▼
                    ┌─────────────┐
                    │ COLLECTING  │◄────────────────────┐
                    └──────┬──────┘                     │
                           │ 收集完成 / 超时             │
                           ▼                            │
                    ┌─────────────┐                     │
                    │ AGGREGATING │                     │
                    └──────┬──────┘                     │
                           │ 聚合完成                    │
                           ▼                            │
                    ┌─────────────────┐                 │
                    │ PROPOSAL_SENT   │                 │
                    └──────┬──────────┘                 │
                           │                            │
              ┌────────────┴────────────┐               │
              ▼                         ▼               │
       ┌─────────────┐          ┌─────────────┐        │
       │ NEGOTIATING │          │   有 GAP    │────────┘
       └──────┬──────┘          │ 触发子网    │  (递归)
              │                 └─────────────┘
              │ 所有反馈正向
              ▼
       ┌─────────────┐
       │  FINALIZED  │
       └─────────────┘
              │
              │ 失败 / 超时
              ▼
       ┌─────────────┐
       │   FAILED    │
       └─────────────┘
```

---

## 3. 详细技术方案

### 3.1 TowowWorkerAgent 基类

**文件路径**: `/towow/openagents/agents/base_v2.py`

```python
"""
TowowWorkerAgent - OpenAgents 适配基类

继承 OpenAgents WorkerAgent，注入 ToWow 特有能力：
1. LLM 调用（带熔断）
2. SSE 事件发射
3. 状态管理接口
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from openagents.agents.worker_agent import WorkerAgent

if TYPE_CHECKING:
    from ..services.llm import LLMService
    from ..events.bus import EventBus

logger = logging.getLogger(__name__)


class TowowWorkerAgent(WorkerAgent):
    """
    ToWow Agent 基类

    所有 ToWow Agent 继承此类，获得：
    - LLM 调用能力（带熔断器）
    - SSE 事件发射能力
    - 统一的日志和监控
    """

    def __init__(
        self,
        agent_id: str,
        llm_service: Optional["LLMService"] = None,
        event_bus: Optional["EventBus"] = None,
        **kwargs
    ):
        """
        初始化 TowowWorkerAgent

        Args:
            agent_id: Agent 唯一标识
            llm_service: LLM 服务实例（带熔断）
            event_bus: 事件总线（SSE 发布）
            **kwargs: 传递给 WorkerAgent 的参数
        """
        super().__init__(**kwargs)
        self._agent_id = agent_id
        self._llm_service = llm_service
        self._event_bus = event_bus
        self._state: Dict[str, Any] = {}

        logger.info("[%s] TowowWorkerAgent initialized", agent_id)

    @property
    def agent_id(self) -> str:
        """获取 Agent ID"""
        return self._agent_id

    # ========== LLM 调用（带熔断） ==========

    async def call_llm(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        fallback_key: Optional[str] = None
    ) -> str:
        """
        调用 LLM（通过熔断器）

        Args:
            prompt: 提示词
            context: 上下文数据（用于模板渲染）
            fallback_key: 降级响应键（熔断时使用）

        Returns:
            LLM 响应或降级响应
        """
        if not self._llm_service:
            logger.warning("[%s] LLM service not available", self._agent_id)
            return self._get_fallback_response(fallback_key)

        try:
            response = await self._llm_service.generate(
                prompt=prompt,
                context=context or {}
            )
            return response
        except Exception as e:
            logger.error("[%s] LLM call failed: %s", self._agent_id, str(e))
            return self._get_fallback_response(fallback_key)

    def _get_fallback_response(self, key: Optional[str]) -> str:
        """获取降级响应"""
        from ..services.llm import FALLBACK_RESPONSES
        if key and key in FALLBACK_RESPONSES:
            return FALLBACK_RESPONSES[key]
        return FALLBACK_RESPONSES.get("default", "服务暂时不可用，请稍后重试")

    # ========== SSE 事件发射 ==========

    def emit_sse(
        self,
        event_type: str,
        data: Dict[str, Any],
        channel_id: Optional[str] = None
    ) -> None:
        """
        发射 SSE 事件到前端

        Args:
            event_type: 事件类型（如 "agent.response"）
            data: 事件数据
            channel_id: 关联的 Channel ID
        """
        if not self._event_bus:
            logger.warning("[%s] EventBus not available for SSE", self._agent_id)
            return

        event_data = {
            "type": event_type,
            "agent_id": self._agent_id,
            "channel_id": channel_id,
            "data": data,
            "timestamp": self._get_timestamp()
        }

        # 发布到 EventBus，前端 SSE 连接会收到
        self._event_bus.emit(f"sse.{event_type}", event_data)
        logger.debug("[%s] SSE event emitted: %s", self._agent_id, event_type)

    def _get_timestamp(self) -> str:
        """获取 ISO 格式时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

    # ========== 状态管理 ==========

    def get_state(self, key: str, default: Any = None) -> Any:
        """获取状态值"""
        return self._state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """设置状态值"""
        self._state[key] = value
        logger.debug("[%s] State updated: %s = %s", self._agent_id, key, value)

    def clear_state(self) -> None:
        """清除所有状态"""
        self._state.clear()
        logger.debug("[%s] State cleared", self._agent_id)

    # ========== OpenAgents 生命周期钩子 ==========

    async def on_startup(self) -> None:
        """Agent 启动时调用"""
        logger.info("[%s] Agent starting up", self._agent_id)
        await super().on_startup()

    async def on_shutdown(self) -> None:
        """Agent 关闭时调用"""
        logger.info("[%s] Agent shutting down", self._agent_id)
        await super().on_shutdown()
```

### 3.2 TowowCoordinator

**文件路径**: `/towow/openagents/agents/coordinator_v2.py`

```python
"""
TowowCoordinator - 需求协调器

职责：
1. 接收用户需求
2. LLM 理解需求
3. 智能筛选 Agent
4. 创建协商 Channel
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from openagents.agents.worker_agent import on_event

from .base_v2 import TowowWorkerAgent

logger = logging.getLogger(__name__)


class TowowCoordinator(TowowWorkerAgent):
    """
    需求协调器 Agent

    处理流程：
    1. 接收 towow.demand.new 事件
    2. 调用 LLM 理解需求
    3. 调用 LLM 筛选合适的 Agent
    4. 创建 OpenAgents Channel 并通知 ChannelAdmin
    """

    def __init__(self, **kwargs):
        super().__init__(agent_id="coordinator", **kwargs)
        # 配置项
        self._max_candidates = 10  # 最大候选人数
        self._smart_filter_enabled = True  # 是否启用 LLM 筛选

    # ========== 事件处理器 ==========

    @on_event("towow.demand.new")
    async def on_demand_new(self, event: Any) -> None:
        """
        处理新需求

        Args:
            event: 包含需求数据的事件
        """
        demand_data = self._extract_demand_data(event)
        demand_id = demand_data.get("demand_id", "unknown")

        logger.info("[Coordinator] Processing new demand: %s", demand_id)

        try:
            # Step 1: 理解需求
            analysis = await self._understand_demand(demand_data)

            # Step 2: 筛选 Agent
            candidates = await self._filter_agents(demand_data, analysis)

            if not candidates:
                logger.warning("[Coordinator] No suitable agents found for demand: %s", demand_id)
                self.emit_sse("demand.failed", {
                    "demand_id": demand_id,
                    "reason": "no_suitable_agents"
                })
                return

            # Step 3: 创建 Channel
            channel_id = await self._create_channel(demand_data, candidates, analysis)

            logger.info("[Coordinator] Channel created: %s for demand: %s",
                       channel_id, demand_id)

            # 通知前端
            self.emit_sse("channel.created", {
                "demand_id": demand_id,
                "channel_id": channel_id,
                "candidates": [c["agent_id"] for c in candidates],
                "analysis": analysis
            })

            # 通知 ChannelAdmin 开始管理
            await self._notify_channel_admin(channel_id, demand_data, candidates)

        except Exception as e:
            logger.error("[Coordinator] Error processing demand %s: %s",
                        demand_id, str(e), exc_info=True)
            self.emit_sse("demand.failed", {
                "demand_id": demand_id,
                "reason": str(e)
            })

    @on_event("towow.demand.subnet")
    async def on_subnet_demand(self, event: Any) -> None:
        """
        处理子网需求（来自 ChannelAdmin 的 GAP 识别）

        Args:
            event: 包含子网需求数据的事件
        """
        subnet_data = self._extract_subnet_data(event)
        parent_channel = subnet_data.get("parent_channel_id")
        gap_description = subnet_data.get("gap_description")
        depth = subnet_data.get("depth", 0)

        logger.info("[Coordinator] Processing subnet demand for gap: %s (depth=%d)",
                   gap_description, depth)

        # 检查递归深度
        if depth >= 2:
            logger.warning("[Coordinator] Max subnet depth reached, skipping")
            return

        # 复用 on_demand_new 逻辑，标记为子网
        await self.on_demand_new({
            "payload": {
                "content": {
                    **subnet_data,
                    "is_subnet": True,
                    "parent_channel_id": parent_channel,
                    "depth": depth + 1
                }
            }
        })

    # ========== 内部方法 ==========

    async def _understand_demand(self, demand_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 理解需求

        Returns:
            需求分析结果
        """
        prompt = self._build_understand_prompt(demand_data)

        response = await self.call_llm(
            prompt=prompt,
            context={"demand": demand_data},
            fallback_key="demand_understanding"
        )

        return self._parse_analysis_response(response)

    async def _filter_agents(
        self,
        demand_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        筛选合适的 Agent

        Returns:
            筛选后的 Agent 列表
        """
        # 获取所有候选人
        all_candidates = self._get_all_candidates()

        if not self._smart_filter_enabled:
            return all_candidates[:self._max_candidates]

        # LLM 智能筛选
        prompt = self._build_filter_prompt(demand_data, analysis, all_candidates)

        response = await self.call_llm(
            prompt=prompt,
            context={
                "demand": demand_data,
                "analysis": analysis,
                "candidates": all_candidates
            },
            fallback_key="agent_filtering"
        )

        filtered = self._parse_filter_response(response, all_candidates)
        return filtered[:self._max_candidates]

    async def _create_channel(
        self,
        demand_data: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> str:
        """
        创建 OpenAgents Channel

        Returns:
            Channel ID
        """
        import uuid
        channel_id = f"channel_{uuid.uuid4().hex[:8]}"

        # 使用 OpenAgents workspace API 创建 channel
        # [VERIFIED] 基于 workspace.py:1120-1180
        channel_config = {
            "channel_id": channel_id,
            "demand_data": demand_data,
            "candidates": candidates,
            "analysis": analysis,
            "created_by": self._agent_id
        }

        # 调用 OpenAgents channel 创建
        # workspace().channel(channel_id).post(channel_config)
        await self.workspace().channel(channel_id).post(
            message_type="channel.init",
            content=channel_config
        )

        return channel_id

    async def _notify_channel_admin(
        self,
        channel_id: str,
        demand_data: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> None:
        """通知 ChannelAdmin 开始管理 Channel"""
        # [VERIFIED] 基于 workspace.py:890-950
        await self.workspace().agent("channel_admin").send(
            message_type="start_managing",
            content={
                "channel_id": channel_id,
                "demand_data": demand_data,
                "candidates": candidates
            }
        )

    def _extract_demand_data(self, event: Any) -> Dict[str, Any]:
        """从事件中提取需求数据"""
        if hasattr(event, "payload"):
            content = event.payload.get("content", {})
            if isinstance(content, dict):
                return content
        return {}

    def _extract_subnet_data(self, event: Any) -> Dict[str, Any]:
        """从事件中提取子网数据"""
        return self._extract_demand_data(event)

    def _get_all_candidates(self) -> List[Dict[str, Any]]:
        """获取所有候选 Agent"""
        try:
            from config import MOCK_CANDIDATES
            return MOCK_CANDIDATES
        except ImportError:
            logger.warning("[Coordinator] MOCK_CANDIDATES not available")
            return []

    def _build_understand_prompt(self, demand_data: Dict[str, Any]) -> str:
        """构建需求理解提示词"""
        return f"""
请分析以下用户需求，提取关键信息：

需求内容：{demand_data.get('content', '')}

请返回 JSON 格式的分析结果：
{{
    "summary": "需求摘要",
    "required_capabilities": ["能力1", "能力2"],
    "constraints": ["约束1", "约束2"],
    "priority": "high/medium/low"
}}
"""

    def _build_filter_prompt(
        self,
        demand_data: Dict[str, Any],
        analysis: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> str:
        """构建 Agent 筛选提示词"""
        candidates_str = "\n".join([
            f"- {c.get('display_name', c['agent_id'])}: {c.get('capabilities', [])}"
            for c in candidates
        ])

        return f"""
根据以下需求分析，从候选人中选择最合适的 Agent：

需求分析：{analysis}

候选人列表：
{candidates_str}

请返回最合适的 Agent ID 列表（JSON 数组格式）：
["agent_id_1", "agent_id_2", ...]
"""

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 分析响应"""
        import json
        try:
            # 尝试提取 JSON
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        # 降级：返回基础分析
        return {
            "summary": response[:200],
            "required_capabilities": [],
            "constraints": [],
            "priority": "medium"
        }

    def _parse_filter_response(
        self,
        response: str,
        all_candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """解析 LLM 筛选响应"""
        import json
        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                selected_ids = json.loads(response[start:end])
                return [
                    c for c in all_candidates
                    if c.get("agent_id") in selected_ids
                ]
        except json.JSONDecodeError:
            pass

        # 降级：返回所有候选人
        return all_candidates
```

### 3.3 TowowChannelAdmin（含状态机）

**文件路径**: `/towow/openagents/agents/channel_admin_v2.py`

```python
"""
TowowChannelAdmin - Channel 管理器（含状态机）

职责：
1. 管理 Channel 生命周期
2. 驱动协商状态机
3. 聚合提案、生成综合方案
4. 识别 GAP 并触发子网
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from openagents.agents.worker_agent import on_event

from .base_v2 import TowowWorkerAgent

logger = logging.getLogger(__name__)


class ChannelStatus(Enum):
    """Channel 状态枚举"""
    CREATED = "created"
    BROADCASTING = "broadcasting"
    COLLECTING = "collecting"
    AGGREGATING = "aggregating"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    FINALIZED = "finalized"
    FAILED = "failed"


# 状态转换规则
VALID_TRANSITIONS = {
    ChannelStatus.CREATED: {ChannelStatus.BROADCASTING, ChannelStatus.FAILED},
    ChannelStatus.BROADCASTING: {ChannelStatus.COLLECTING, ChannelStatus.FAILED},
    ChannelStatus.COLLECTING: {ChannelStatus.AGGREGATING, ChannelStatus.FAILED},
    ChannelStatus.AGGREGATING: {ChannelStatus.PROPOSAL_SENT, ChannelStatus.FAILED},
    ChannelStatus.PROPOSAL_SENT: {ChannelStatus.NEGOTIATING, ChannelStatus.COLLECTING, ChannelStatus.FAILED},
    ChannelStatus.NEGOTIATING: {ChannelStatus.FINALIZED, ChannelStatus.COLLECTING, ChannelStatus.FAILED},
    ChannelStatus.FINALIZED: set(),  # 终态
    ChannelStatus.FAILED: set(),  # 终态
}


@dataclass
class ChannelState:
    """
    Channel 状态数据

    包含协商过程中的所有状态信息
    """
    channel_id: str
    status: ChannelStatus = ChannelStatus.CREATED
    demand_data: Dict[str, Any] = field(default_factory=dict)
    candidates: List[Dict[str, Any]] = field(default_factory=list)

    # 响应收集
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # agent_id -> response
    expected_responses: Set[str] = field(default_factory=set)

    # 提案
    aggregated_proposal: Optional[Dict[str, Any]] = None
    feedback: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # agent_id -> feedback

    # 子网相关
    parent_channel_id: Optional[str] = None
    depth: int = 0
    subnet_ids: List[str] = field(default_factory=list)

    # 幂等性控制
    processed_message_ids: Set[str] = field(default_factory=set)

    # 超时配置（秒）
    broadcast_timeout: float = 30.0
    collect_timeout: float = 60.0
    negotiate_timeout: float = 120.0


class TowowChannelAdmin(TowowWorkerAgent):
    """
    Channel 管理器 Agent

    核心职责：
    1. 管理多个 Channel 的生命周期
    2. 驱动状态机转换
    3. 聚合提案、生成综合方案
    4. 识别 GAP 并触发子网递归
    """

    def __init__(self, **kwargs):
        super().__init__(agent_id="channel_admin", **kwargs)
        # channel_id -> ChannelState
        self._channels: Dict[str, ChannelState] = {}
        # 超时任务
        self._timeout_tasks: Dict[str, asyncio.Task] = {}

    # ========== 事件处理器 ==========

    @on_event("start_managing")
    async def on_start_managing(self, event: Any) -> None:
        """
        开始管理一个 Channel

        由 Coordinator 调用
        """
        data = self._extract_event_data(event)
        channel_id = data.get("channel_id")

        if not channel_id:
            logger.error("[ChannelAdmin] Missing channel_id in start_managing")
            return

        logger.info("[ChannelAdmin] Starting to manage channel: %s", channel_id)

        # 初始化 Channel 状态
        state = ChannelState(
            channel_id=channel_id,
            demand_data=data.get("demand_data", {}),
            candidates=data.get("candidates", []),
            expected_responses={c["agent_id"] for c in data.get("candidates", [])},
            parent_channel_id=data.get("parent_channel_id"),
            depth=data.get("depth", 0)
        )

        self._channels[channel_id] = state

        # 开始广播
        await self._broadcast_demand(channel_id)

    @on_event("towow.proposal.submitted")
    async def on_proposal_submitted(self, event: Any) -> None:
        """
        接收 Agent 提交的提案
        """
        data = self._extract_event_data(event)
        channel_id = data.get("channel_id")
        agent_id = data.get("agent_id")
        proposal = data.get("proposal")

        if not channel_id or channel_id not in self._channels:
            logger.warning("[ChannelAdmin] Unknown channel: %s", channel_id)
            return

        state = self._channels[channel_id]

        # 幂等性检查
        message_id = f"proposal_{agent_id}"
        if message_id in state.processed_message_ids:
            logger.debug("[ChannelAdmin] Duplicate proposal from %s", agent_id)
            return
        state.processed_message_ids.add(message_id)

        # 只在 COLLECTING 状态接收
        if state.status != ChannelStatus.COLLECTING:
            logger.warning("[ChannelAdmin] Proposal received in wrong state: %s", state.status)
            return

        # 记录响应
        state.responses[agent_id] = {
            "agent_id": agent_id,
            "proposal": proposal,
            "received_at": self._get_timestamp()
        }

        logger.info("[ChannelAdmin] Proposal received from %s (%d/%d)",
                   agent_id, len(state.responses), len(state.expected_responses))

        # 通知前端
        self.emit_sse("proposal.received", {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "progress": f"{len(state.responses)}/{len(state.expected_responses)}"
        }, channel_id=channel_id)

        # 检查是否收集完成
        if len(state.responses) >= len(state.expected_responses):
            await self._on_collect_complete(channel_id)

    @on_event("towow.feedback.submitted")
    async def on_feedback_submitted(self, event: Any) -> None:
        """
        接收 Agent 提交的反馈
        """
        data = self._extract_event_data(event)
        channel_id = data.get("channel_id")
        agent_id = data.get("agent_id")
        feedback = data.get("feedback")

        if not channel_id or channel_id not in self._channels:
            return

        state = self._channels[channel_id]

        # 只在 NEGOTIATING 状态接收
        if state.status != ChannelStatus.NEGOTIATING:
            return

        state.feedback[agent_id] = {
            "agent_id": agent_id,
            "feedback": feedback,
            "received_at": self._get_timestamp()
        }

        logger.info("[ChannelAdmin] Feedback received from %s", agent_id)

        # 检查是否所有反馈都收到
        if len(state.feedback) >= len(state.expected_responses):
            await self._evaluate_feedback(channel_id)

    # ========== 状态机驱动 ==========

    async def _transition_state(
        self,
        channel_id: str,
        new_status: ChannelStatus,
        reason: str = ""
    ) -> bool:
        """
        执行状态转换

        Args:
            channel_id: Channel ID
            new_status: 目标状态
            reason: 转换原因

        Returns:
            是否转换成功
        """
        state = self._channels.get(channel_id)
        if not state:
            return False

        old_status = state.status

        # 验证转换合法性
        if new_status not in VALID_TRANSITIONS.get(old_status, set()):
            logger.error("[ChannelAdmin] Invalid transition: %s -> %s",
                        old_status, new_status)
            return False

        # 执行转换
        state.status = new_status

        logger.info("[ChannelAdmin] Channel %s: %s -> %s (%s)",
                   channel_id, old_status.value, new_status.value, reason)

        # 通知前端
        self.emit_sse("channel.status_changed", {
            "channel_id": channel_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "reason": reason
        }, channel_id=channel_id)

        return True

    async def _broadcast_demand(self, channel_id: str) -> None:
        """
        广播需求到所有候选 Agent
        """
        state = self._channels.get(channel_id)
        if not state:
            return

        # 转换状态
        if not await self._transition_state(channel_id, ChannelStatus.BROADCASTING, "start_broadcast"):
            return

        # 广播邀请
        for candidate in state.candidates:
            agent_id = candidate["agent_id"]

            await self.workspace().agent(agent_id).send(
                message_type="towow.invite",
                content={
                    "channel_id": channel_id,
                    "demand_data": state.demand_data,
                    "invited_by": self._agent_id
                }
            )

            logger.debug("[ChannelAdmin] Invite sent to %s", agent_id)

        # 转换到收集状态
        await self._transition_state(channel_id, ChannelStatus.COLLECTING, "broadcast_complete")

        # 设置超时
        self._set_timeout(channel_id, state.collect_timeout, self._on_collect_timeout)

    async def _on_collect_complete(self, channel_id: str) -> None:
        """收集完成，开始聚合"""
        self._cancel_timeout(channel_id)

        if not await self._transition_state(channel_id, ChannelStatus.AGGREGATING, "collect_complete"):
            return

        await self._aggregate_proposals(channel_id)

    async def _on_collect_timeout(self, channel_id: str) -> None:
        """收集超时处理"""
        state = self._channels.get(channel_id)
        if not state or state.status != ChannelStatus.COLLECTING:
            return

        logger.warning("[ChannelAdmin] Collect timeout for channel %s", channel_id)

        # 如果有响应，继续聚合；否则失败
        if state.responses:
            await self._on_collect_complete(channel_id)
        else:
            await self._fail_channel(channel_id, "no_responses_timeout")

    async def _aggregate_proposals(self, channel_id: str) -> None:
        """
        聚合所有提案，生成综合方案
        """
        state = self._channels.get(channel_id)
        if not state:
            return

        logger.info("[ChannelAdmin] Aggregating %d proposals", len(state.responses))

        # 构建聚合提示词
        proposals_text = "\n\n".join([
            f"Agent {r['agent_id']}:\n{r['proposal']}"
            for r in state.responses.values()
        ])

        prompt = f"""
请综合以下各方提案，生成一个统一的解决方案：

原始需求：{state.demand_data.get('content', '')}

各方提案：
{proposals_text}

请返回 JSON 格式的综合方案：
{{
    "summary": "方案摘要",
    "details": "详细方案",
    "assignments": {{"agent_id": "分配任务"}},
    "gaps": ["识别到的能力缺口"]
}}
"""

        response = await self.call_llm(
            prompt=prompt,
            fallback_key="proposal_aggregation"
        )

        # 解析聚合结果
        state.aggregated_proposal = self._parse_aggregation_response(response)

        # 转换状态并分发方案
        await self._transition_state(channel_id, ChannelStatus.PROPOSAL_SENT, "aggregation_complete")
        await self._distribute_proposal(channel_id)

    async def _distribute_proposal(self, channel_id: str) -> None:
        """
        分发综合方案给所有参与者
        """
        state = self._channels.get(channel_id)
        if not state or not state.aggregated_proposal:
            return

        # 检查是否有 GAP
        gaps = state.aggregated_proposal.get("gaps", [])
        if gaps and state.depth < 2:
            await self._trigger_subnets(channel_id, gaps)
            return

        # 分发方案
        for agent_id in state.responses.keys():
            await self.workspace().agent(agent_id).send(
                message_type="towow.proposal.final",
                content={
                    "channel_id": channel_id,
                    "proposal": state.aggregated_proposal,
                    "your_assignment": state.aggregated_proposal.get("assignments", {}).get(agent_id)
                }
            )

        # 通知前端
        self.emit_sse("proposal.distributed", {
            "channel_id": channel_id,
            "proposal": state.aggregated_proposal
        }, channel_id=channel_id)

        # 转换到协商状态
        await self._transition_state(channel_id, ChannelStatus.NEGOTIATING, "proposal_distributed")

        # 设置协商超时
        self._set_timeout(channel_id, state.negotiate_timeout, self._on_negotiate_timeout)

    async def _trigger_subnets(self, channel_id: str, gaps: List[str]) -> None:
        """
        触发子网解决 GAP

        Args:
            channel_id: 父 Channel ID
            gaps: GAP 描述列表
        """
        state = self._channels.get(channel_id)
        if not state:
            return

        # 限制子网数量
        max_subnets = 3
        gaps_to_process = gaps[:max_subnets]

        logger.info("[ChannelAdmin] Triggering %d subnets for channel %s (depth=%d)",
                   len(gaps_to_process), channel_id, state.depth)

        for gap in gaps_to_process:
            # 通知 Coordinator 创建子网
            await self.workspace().agent("coordinator").send(
                message_type="towow.demand.subnet",
                content={
                    "parent_channel_id": channel_id,
                    "gap_description": gap,
                    "depth": state.depth + 1,
                    "original_demand": state.demand_data
                }
            )

        self.emit_sse("subnet.triggered", {
            "channel_id": channel_id,
            "gaps": gaps_to_process,
            "depth": state.depth + 1
        }, channel_id=channel_id)

    async def _evaluate_feedback(self, channel_id: str) -> None:
        """
        评估所有反馈，决定下一步
        """
        state = self._channels.get(channel_id)
        if not state:
            return

        self._cancel_timeout(channel_id)

        # 分析反馈
        positive_count = 0
        negative_feedback = []

        for agent_id, fb in state.feedback.items():
            feedback_data = fb.get("feedback", {})
            if feedback_data.get("accepted", False):
                positive_count += 1
            else:
                negative_feedback.append({
                    "agent_id": agent_id,
                    "reason": feedback_data.get("reason", "")
                })

        # 决策逻辑
        acceptance_rate = positive_count / len(state.feedback) if state.feedback else 0

        if acceptance_rate >= 0.8:  # 80% 以上接受
            await self._finalize_channel(channel_id)
        elif acceptance_rate >= 0.5:  # 50-80%，尝试重新协商
            await self._renegotiate(channel_id, negative_feedback)
        else:
            await self._fail_channel(channel_id, "low_acceptance_rate")

    async def _renegotiate(
        self,
        channel_id: str,
        negative_feedback: List[Dict[str, Any]]
    ) -> None:
        """
        重新协商
        """
        state = self._channels.get(channel_id)
        if not state:
            return

        logger.info("[ChannelAdmin] Renegotiating channel %s", channel_id)

        # 清除旧响应，回到收集状态
        state.responses.clear()
        state.feedback.clear()

        await self._transition_state(channel_id, ChannelStatus.COLLECTING, "renegotiate")

        # 重新广播，附带负面反馈
        for candidate in state.candidates:
            await self.workspace().agent(candidate["agent_id"]).send(
                message_type="towow.renegotiate",
                content={
                    "channel_id": channel_id,
                    "demand_data": state.demand_data,
                    "previous_proposal": state.aggregated_proposal,
                    "feedback_summary": negative_feedback
                }
            )

        self._set_timeout(channel_id, state.collect_timeout, self._on_collect_timeout)

    async def _finalize_channel(self, channel_id: str) -> None:
        """
        完成 Channel
        """
        if not await self._transition_state(channel_id, ChannelStatus.FINALIZED, "consensus_reached"):
            return

        state = self._channels[channel_id]

        self.emit_sse("channel.finalized", {
            "channel_id": channel_id,
            "final_proposal": state.aggregated_proposal,
            "participants": list(state.responses.keys())
        }, channel_id=channel_id)

        logger.info("[ChannelAdmin] Channel %s finalized successfully", channel_id)

        # 通知父 Channel（如果是子网）
        if state.parent_channel_id:
            await self._notify_parent_completed(channel_id)

    async def _fail_channel(self, channel_id: str, reason: str) -> None:
        """
        Channel 失败
        """
        if not await self._transition_state(channel_id, ChannelStatus.FAILED, reason):
            return

        self._cancel_timeout(channel_id)

        self.emit_sse("channel.failed", {
            "channel_id": channel_id,
            "reason": reason
        }, channel_id=channel_id)

        logger.warning("[ChannelAdmin] Channel %s failed: %s", channel_id, reason)

    async def _notify_parent_completed(self, channel_id: str) -> None:
        """通知父 Channel 子网完成"""
        state = self._channels.get(channel_id)
        if not state or not state.parent_channel_id:
            return

        # 发送子网完成通知
        await self.workspace().agent("channel_admin").send(
            message_type="subnet_completed",
            content={
                "parent_channel_id": state.parent_channel_id,
                "subnet_channel_id": channel_id,
                "result": state.aggregated_proposal
            }
        )

    async def _on_negotiate_timeout(self, channel_id: str) -> None:
        """协商超时"""
        state = self._channels.get(channel_id)
        if not state or state.status != ChannelStatus.NEGOTIATING:
            return

        # 使用已有反馈评估
        if state.feedback:
            await self._evaluate_feedback(channel_id)
        else:
            await self._fail_channel(channel_id, "negotiate_timeout")

    # ========== 工具方法 ==========

    def _extract_event_data(self, event: Any) -> Dict[str, Any]:
        """从事件中提取数据"""
        if hasattr(event, "payload"):
            content = event.payload.get("content", {})
            if isinstance(content, dict):
                return content
        return {}

    def _parse_aggregation_response(self, response: str) -> Dict[str, Any]:
        """解析聚合响应"""
        import json
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return {
            "summary": response[:500],
            "details": response,
            "assignments": {},
            "gaps": []
        }

    def _set_timeout(
        self,
        channel_id: str,
        timeout: float,
        callback
    ) -> None:
        """设置超时"""
        self._cancel_timeout(channel_id)

        async def timeout_task():
            await asyncio.sleep(timeout)
            await callback(channel_id)

        self._timeout_tasks[channel_id] = asyncio.create_task(timeout_task())

    def _cancel_timeout(self, channel_id: str) -> None:
        """取消超时"""
        task = self._timeout_tasks.pop(channel_id, None)
        if task and not task.done():
            task.cancel()
```

### 3.4 TowowUserAgent

**文件路径**: `/towow/openagents/agents/user_agent_v2.py`

```python
"""
TowowUserAgent - 用户数字分身

职责：
1. 接收协商邀请
2. 基于 Profile 生成响应
3. 提交提案和反馈
4. 支持讨价还价
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from openagents.agents.worker_agent import on_event

from .base_v2 import TowowWorkerAgent

logger = logging.getLogger(__name__)


class TowowUserAgent(TowowWorkerAgent):
    """
    用户数字分身 Agent

    代表用户参与协商，基于用户 Profile 自动生成响应
    """

    def __init__(
        self,
        user_id: str,
        profile: Dict[str, Any],
        **kwargs
    ):
        """
        初始化 UserAgent

        Args:
            user_id: 用户 ID
            profile: 用户 Profile（能力、偏好等）
        """
        super().__init__(agent_id=f"user_agent_{user_id}", **kwargs)
        self._user_id = user_id
        self._profile = profile

        # 参与的 Channel
        self._active_channels: Dict[str, Dict[str, Any]] = {}

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def profile(self) -> Dict[str, Any]:
        return self._profile

    # ========== 事件处理器 ==========

    @on_event("towow.invite")
    async def on_invite(self, event: Any) -> None:
        """
        处理协商邀请
        """
        data = self._extract_event_data(event)
        channel_id = data.get("channel_id")
        demand_data = data.get("demand_data", {})

        if not channel_id:
            return

        logger.info("[%s] Received invite for channel: %s", self._agent_id, channel_id)

        # 记录活跃 Channel
        self._active_channels[channel_id] = {
            "demand_data": demand_data,
            "status": "invited"
        }

        # 通知前端
        self.emit_sse("agent.invited", {
            "channel_id": channel_id,
            "demand_summary": demand_data.get("content", "")[:100]
        }, channel_id=channel_id)

        # 决定是否参与
        decision = await self._decide_participation(demand_data)

        if decision.get("participate", False):
            # 生成并提交提案
            proposal = await self._generate_proposal(demand_data)
            await self._submit_proposal(channel_id, proposal)
        else:
            # 拒绝参与
            await self._decline_invite(channel_id, decision.get("reason", ""))

    @on_event("towow.proposal.final")
    async def on_final_proposal(self, event: Any) -> None:
        """
        处理最终方案
        """
        data = self._extract_event_data(event)
        channel_id = data.get("channel_id")
        proposal = data.get("proposal", {})
        my_assignment = data.get("your_assignment")

        if not channel_id:
            return

        logger.info("[%s] Received final proposal for channel: %s",
                   self._agent_id, channel_id)

        # 通知前端
        self.emit_sse("proposal.received", {
            "channel_id": channel_id,
            "proposal_summary": proposal.get("summary", ""),
            "my_assignment": my_assignment
        }, channel_id=channel_id)

        # 评估方案
        evaluation = await self._evaluate_proposal(proposal, my_assignment)

        # 提交反馈
        await self._submit_feedback(channel_id, evaluation)

    @on_event("towow.renegotiate")
    async def on_renegotiate(self, event: Any) -> None:
        """
        处理重新协商请求
        """
        data = self._extract_event_data(event)
        channel_id = data.get("channel_id")
        demand_data = data.get("demand_data", {})
        previous_proposal = data.get("previous_proposal", {})
        feedback_summary = data.get("feedback_summary", [])

        logger.info("[%s] Renegotiation requested for channel: %s",
                   self._agent_id, channel_id)

        # 生成改进后的提案
        proposal = await self._generate_improved_proposal(
            demand_data, previous_proposal, feedback_summary
        )

        await self._submit_proposal(channel_id, proposal)

    # ========== 内部方法 ==========

    async def _decide_participation(
        self,
        demand_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        决定是否参与协商

        Returns:
            {"participate": bool, "reason": str}
        """
        prompt = f"""
你是一个 AI Agent，拥有以下能力和特点：
{self._format_profile()}

有人邀请你参与以下需求的协商：
{demand_data.get('content', '')}

请决定是否参与，返回 JSON：
{{
    "participate": true/false,
    "reason": "理由",
    "confidence": 0.0-1.0
}}
"""

        response = await self.call_llm(
            prompt=prompt,
            fallback_key="participation_decision"
        )

        return self._parse_decision_response(response)

    async def _generate_proposal(
        self,
        demand_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成提案
        """
        prompt = f"""
你是一个 AI Agent，拥有以下能力：
{self._format_profile()}

请针对以下需求生成你的提案：
{demand_data.get('content', '')}

请返回 JSON 格式的提案：
{{
    "approach": "你的方案",
    "timeline": "预计时间",
    "requirements": ["需要的资源/条件"],
    "concerns": ["潜在问题"]
}}
"""

        response = await self.call_llm(
            prompt=prompt,
            fallback_key="proposal_generation"
        )

        return self._parse_proposal_response(response)

    async def _generate_improved_proposal(
        self,
        demand_data: Dict[str, Any],
        previous_proposal: Dict[str, Any],
        feedback_summary: list
    ) -> Dict[str, Any]:
        """
        生成改进后的提案（基于反馈）
        """
        feedback_text = "\n".join([
            f"- {f.get('agent_id')}: {f.get('reason')}"
            for f in feedback_summary
        ])

        prompt = f"""
你是一个 AI Agent，拥有以下能力：
{self._format_profile()}

之前的方案收到了一些负面反馈：
{feedback_text}

请改进你的提案：
原需求：{demand_data.get('content', '')}
之前方案：{previous_proposal.get('summary', '')}

返回改进后的 JSON 提案。
"""

        response = await self.call_llm(
            prompt=prompt,
            fallback_key="proposal_improvement"
        )

        return self._parse_proposal_response(response)

    async def _evaluate_proposal(
        self,
        proposal: Dict[str, Any],
        my_assignment: Optional[str]
    ) -> Dict[str, Any]:
        """
        评估最终方案
        """
        prompt = f"""
你是一个 AI Agent，拥有以下能力：
{self._format_profile()}

请评估以下综合方案：
{proposal}

分配给你的任务：{my_assignment or '未分配'}

请返回你的评估（JSON）：
{{
    "accepted": true/false,
    "reason": "理由",
    "suggestions": ["改进建议"]
}}
"""

        response = await self.call_llm(
            prompt=prompt,
            fallback_key="proposal_evaluation"
        )

        return self._parse_evaluation_response(response)

    async def _submit_proposal(
        self,
        channel_id: str,
        proposal: Dict[str, Any]
    ) -> None:
        """提交提案"""
        await self.workspace().channel(channel_id).post(
            message_type="towow.proposal.submitted",
            content={
                "channel_id": channel_id,
                "agent_id": self._agent_id,
                "proposal": proposal
            }
        )

        self.emit_sse("proposal.submitted", {
            "channel_id": channel_id,
            "proposal_summary": proposal.get("approach", "")[:100]
        }, channel_id=channel_id)

        logger.info("[%s] Proposal submitted to channel: %s", self._agent_id, channel_id)

    async def _submit_feedback(
        self,
        channel_id: str,
        evaluation: Dict[str, Any]
    ) -> None:
        """提交反馈"""
        await self.workspace().channel(channel_id).post(
            message_type="towow.feedback.submitted",
            content={
                "channel_id": channel_id,
                "agent_id": self._agent_id,
                "feedback": evaluation
            }
        )

        self.emit_sse("feedback.submitted", {
            "channel_id": channel_id,
            "accepted": evaluation.get("accepted", False)
        }, channel_id=channel_id)

    async def _decline_invite(self, channel_id: str, reason: str) -> None:
        """拒绝邀请"""
        await self.workspace().channel(channel_id).post(
            message_type="towow.invite.declined",
            content={
                "channel_id": channel_id,
                "agent_id": self._agent_id,
                "reason": reason
            }
        )

        self.emit_sse("invite.declined", {
            "channel_id": channel_id,
            "reason": reason
        }, channel_id=channel_id)

    def _format_profile(self) -> str:
        """格式化 Profile 为文本"""
        return f"""
名称: {self._profile.get('name', self._user_id)}
能力: {', '.join(self._profile.get('capabilities', []))}
标签: {', '.join(self._profile.get('tags', []))}
描述: {self._profile.get('description', '')}
"""

    def _extract_event_data(self, event: Any) -> Dict[str, Any]:
        """从事件中提取数据"""
        if hasattr(event, "payload"):
            content = event.payload.get("content", {})
            if isinstance(content, dict):
                return content
        return {}

    def _parse_decision_response(self, response: str) -> Dict[str, Any]:
        """解析参与决策响应"""
        import json
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
        return {"participate": True, "reason": "default", "confidence": 0.5}

    def _parse_proposal_response(self, response: str) -> Dict[str, Any]:
        """解析提案响应"""
        import json
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
        return {"approach": response[:500], "timeline": "TBD", "requirements": [], "concerns": []}

    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """解析评估响应"""
        import json
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
        return {"accepted": True, "reason": "default", "suggestions": []}
```

### 3.5 SSE Event Bridge

**文件路径**: `/towow/openagents/bridges/sse_bridge.py`

```python
"""
TowowEventBridge - SSE 事件桥接层

职责：
1. 订阅 OpenAgents 事件
2. 转换为 ToWow SSE 格式
3. 发布到前端 EventBus
4. 保持前端零改动
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EventMapping:
    """事件映射配置"""
    openagents_pattern: str  # OpenAgents 事件模式
    sse_event_type: str  # ToWow SSE 事件类型
    transformer: Optional[Callable[[Dict], Dict]] = None  # 数据转换器


class TowowEventBridge:
    """
    SSE 事件桥接器

    将 OpenAgents 内部事件转换为前端 SSE 事件，
    保持前端代码零改动。
    """

    # 默认事件映射
    DEFAULT_MAPPINGS: List[EventMapping] = [
        # Channel 相关
        EventMapping(
            openagents_pattern="channel.init",
            sse_event_type="channel_created"
        ),
        EventMapping(
            openagents_pattern="channel.status_changed",
            sse_event_type="channel_status"
        ),
        EventMapping(
            openagents_pattern="channel.finalized",
            sse_event_type="channel_completed"
        ),
        EventMapping(
            openagents_pattern="channel.failed",
            sse_event_type="channel_failed"
        ),

        # Agent 响应相关
        EventMapping(
            openagents_pattern="towow.proposal.submitted",
            sse_event_type="agent_response",
            transformer=lambda d: {
                "agent_id": d.get("agent_id"),
                "channel_id": d.get("channel_id"),
                "response_type": "proposal",
                "content": d.get("proposal", {}).get("approach", "")
            }
        ),
        EventMapping(
            openagents_pattern="towow.feedback.submitted",
            sse_event_type="agent_feedback",
            transformer=lambda d: {
                "agent_id": d.get("agent_id"),
                "channel_id": d.get("channel_id"),
                "accepted": d.get("feedback", {}).get("accepted", False),
                "reason": d.get("feedback", {}).get("reason", "")
            }
        ),

        # 协商进度
        EventMapping(
            openagents_pattern="proposal.received",
            sse_event_type="negotiation_progress"
        ),
        EventMapping(
            openagents_pattern="proposal.distributed",
            sse_event_type="proposal_sent"
        ),

        # 子网相关
        EventMapping(
            openagents_pattern="subnet.triggered",
            sse_event_type="subnet_created"
        ),
    ]

    def __init__(self, event_bus: Any):
        """
        初始化桥接器

        Args:
            event_bus: ToWow EventBus 实例
        """
        self._event_bus = event_bus
        self._mappings: Dict[str, EventMapping] = {}
        self._active = False

        # 加载默认映射
        for mapping in self.DEFAULT_MAPPINGS:
            self._mappings[mapping.openagents_pattern] = mapping

        logger.info("[SSEBridge] Initialized with %d mappings", len(self._mappings))

    def start(self) -> None:
        """启动桥接"""
        self._active = True
        logger.info("[SSEBridge] Started")

    def stop(self) -> None:
        """停止桥接"""
        self._active = False
        logger.info("[SSEBridge] Stopped")

    def add_mapping(self, mapping: EventMapping) -> None:
        """添加自定义映射"""
        self._mappings[mapping.openagents_pattern] = mapping
        logger.debug("[SSEBridge] Added mapping: %s -> %s",
                    mapping.openagents_pattern, mapping.sse_event_type)

    def on_openagents_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        处理 OpenAgents 事件

        Args:
            event_type: OpenAgents 事件类型
            data: 事件数据
        """
        if not self._active:
            return

        # 查找匹配的映射
        mapping = self._find_mapping(event_type)
        if not mapping:
            logger.debug("[SSEBridge] No mapping for event: %s", event_type)
            return

        # 转换数据
        sse_data = self._transform_data(data, mapping)

        # 发布到前端
        self._emit_to_frontend(mapping.sse_event_type, sse_data)

    def _find_mapping(self, event_type: str) -> Optional[EventMapping]:
        """查找事件映射"""
        # 精确匹配
        if event_type in self._mappings:
            return self._mappings[event_type]

        # 模式匹配（支持通配符）
        for pattern, mapping in self._mappings.items():
            if self._match_pattern(pattern, event_type):
                return mapping

        return None

    def _match_pattern(self, pattern: str, event_type: str) -> bool:
        """模式匹配（简单通配符支持）"""
        if pattern == event_type:
            return True

        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_type.startswith(prefix)

        return False

    def _transform_data(
        self,
        data: Dict[str, Any],
        mapping: EventMapping
    ) -> Dict[str, Any]:
        """转换数据格式"""
        if mapping.transformer:
            return mapping.transformer(data)
        return data

    def _emit_to_frontend(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """发布到前端 EventBus"""
        # 构造 SSE 格式
        sse_event = {
            "event": event_type,
            "data": data,
            "timestamp": self._get_timestamp()
        }

        # 发布到 EventBus（前端 SSE 连接订阅）
        self._event_bus.emit(f"sse.{event_type}", sse_event)

        logger.debug("[SSEBridge] Emitted SSE event: %s", event_type)

    def _get_timestamp(self) -> str:
        """获取 ISO 格式时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# ========== 集成辅助函数 ==========

def setup_sse_bridge(event_bus: Any) -> TowowEventBridge:
    """
    设置 SSE 桥接

    在应用启动时调用
    """
    bridge = TowowEventBridge(event_bus)
    bridge.start()
    return bridge


def register_openagents_listener(bridge: TowowEventBridge) -> Callable:
    """
    创建 OpenAgents 事件监听器

    返回一个可以注册到 OpenAgents 的回调函数
    """
    def listener(event_type: str, data: Dict[str, Any]) -> None:
        bridge.on_openagents_event(event_type, data)

    return listener
```

### 3.6 子网递归实现

子网递归的核心逻辑已在 `TowowChannelAdmin._trigger_subnets()` 和 `TowowCoordinator.on_subnet_demand()` 中实现。

**关键约束**:

| 约束 | 值 | 实现位置 |
|------|-----|----------|
| 最大递归深度 | 2 层 | `ChannelState.depth` + `on_subnet_demand()` 检查 |
| 每层最大子网数 | 3 个 | `_trigger_subnets()` 中 `max_subnets = 3` |
| 子网超时 | 继承父 Channel 配置 | `ChannelState` 默认值 |

**递归流程**:

```
Layer 0 (主 Channel)
├── GAP 识别: ["缺少前端能力", "缺少测试能力"]
│
├── Layer 1 子网 A (前端能力)
│   ├── 筛选前端 Agent
│   ├── 协商
│   └── 完成 → 通知 Layer 0
│
├── Layer 1 子网 B (测试能力)
│   ├── GAP 识别: ["缺少自动化测试能力"]
│   │
│   └── Layer 2 子网 B-1 (自动化测试)
│       ├── 筛选
│       ├── 协商
│       └── 完成 → 通知 Layer 1 子网 B
│
└── 所有子网完成 → 继续主 Channel 协商
```

---

## 4. API 契约

### 4.1 Agent 间消息格式

#### 4.1.1 Direct Message（Agent 间直接通信）

```typescript
interface DirectMessage {
  message_type: string;  // 消息类型
  content: {
    channel_id?: string;
    agent_id?: string;
    [key: string]: any;
  };
  timestamp: string;  // ISO 8601
}
```

#### 4.1.2 Channel Post（Channel 内广播）

```typescript
interface ChannelPost {
  message_type: string;
  content: any;
  sender_id: string;
  channel_id: string;
  timestamp: string;
}
```

### 4.2 事件类型定义

#### 4.2.1 需求相关

| 事件类型 | 方向 | 数据结构 |
|----------|------|----------|
| `towow.demand.new` | Frontend → Coordinator | `{demand_id, content, user_id, metadata}` |
| `towow.demand.subnet` | ChannelAdmin → Coordinator | `{parent_channel_id, gap_description, depth}` |
| `demand.failed` | Coordinator → SSE | `{demand_id, reason}` |

#### 4.2.2 Channel 相关

| 事件类型 | 方向 | 数据结构 |
|----------|------|----------|
| `channel.created` | Coordinator → SSE | `{demand_id, channel_id, candidates, analysis}` |
| `channel.status_changed` | ChannelAdmin → SSE | `{channel_id, old_status, new_status, reason}` |
| `channel.finalized` | ChannelAdmin → SSE | `{channel_id, final_proposal, participants}` |
| `channel.failed` | ChannelAdmin → SSE | `{channel_id, reason}` |

#### 4.2.3 协商相关

| 事件类型 | 方向 | 数据结构 |
|----------|------|----------|
| `towow.invite` | ChannelAdmin → UserAgent | `{channel_id, demand_data, invited_by}` |
| `towow.proposal.submitted` | UserAgent → ChannelAdmin | `{channel_id, agent_id, proposal}` |
| `towow.proposal.final` | ChannelAdmin → UserAgent | `{channel_id, proposal, your_assignment}` |
| `towow.feedback.submitted` | UserAgent → ChannelAdmin | `{channel_id, agent_id, feedback}` |
| `towow.renegotiate` | ChannelAdmin → UserAgent | `{channel_id, previous_proposal, feedback_summary}` |

### 4.3 SSE 事件格式（前端兼容）

```typescript
// 前端 EventSource 接收格式
interface SSEEvent {
  event: string;  // 事件类型（与现有前端代码一致）
  data: {
    channel_id?: string;
    agent_id?: string;
    [key: string]: any;
  };
  timestamp: string;
}

// 示例：agent_response
{
  "event": "agent_response",
  "data": {
    "agent_id": "user_agent_alice",
    "channel_id": "channel_abc123",
    "response_type": "proposal",
    "content": "我建议..."
  },
  "timestamp": "2025-01-23T10:30:00Z"
}
```

---

## 5. 风险与预案

### 5.1 风险矩阵

| 风险 | 概率 | 影响 | 预案 |
|------|------|------|------|
| OpenAgents API 变更 | 中 | 高 | 适配层隔离；版本锁定 |
| 状态机死锁 | 低 | 高 | 超时机制；状态监控 |
| LLM 服务不可用 | 中 | 中 | 熔断 + Fallback 已有 |
| SSE 连接断开 | 中 | 中 | 前端重连机制已有 |
| 子网递归过深 | 低 | 中 | 深度限制（max=2） |
| 消息重复处理 | 中 | 低 | 幂等性检查已有 |

### 5.2 关键预案详情

#### 5.2.1 OpenAgents API 变更预案

```python
# 在 TowowWorkerAgent 中封装 workspace 调用
class TowowWorkerAgent(WorkerAgent):

    async def send_to_agent(self, agent_id: str, message_type: str, content: dict):
        """
        封装 Agent 间通信，隔离 OpenAgents API 变更

        如果 OpenAgents API 变更，只需修改此方法
        """
        try:
            # OpenAgents v1.x API
            await self.workspace().agent(agent_id).send(
                message_type=message_type,
                content=content
            )
        except AttributeError:
            # 降级到 v0.x API（如果存在）
            logger.warning("Using fallback API for agent communication")
            await self._legacy_send(agent_id, message_type, content)
```

#### 5.2.2 状态机死锁预案

```python
# 在 ChannelAdmin 中添加状态监控
class TowowChannelAdmin(TowowWorkerAgent):

    async def _check_stuck_channels(self) -> None:
        """
        定期检查卡住的 Channel

        每 30 秒执行一次
        """
        import time
        current_time = time.time()

        for channel_id, state in self._channels.items():
            # 检查是否超过最大生存时间（10 分钟）
            if current_time - state.created_at > 600:
                if state.status not in {ChannelStatus.FINALIZED, ChannelStatus.FAILED}:
                    logger.warning("Channel %s stuck in %s, forcing failure",
                                  channel_id, state.status)
                    await self._fail_channel(channel_id, "stuck_timeout")
```

---

## 6. 实施路线图

### 6.1 Phase 1: 基础适配层（1 周）

**目标**: 完成 TowowWorkerAgent 基类，验证与 OpenAgents 的基本集成。

| 任务 | 预估 | 验收标准 |
|------|------|----------|
| 实现 TowowWorkerAgent | 2d | 单元测试通过 |
| LLM 服务集成 | 1d | 熔断器工作正常 |
| SSE 发射能力 | 1d | 前端能收到事件 |
| 集成测试 | 1d | Agent 启动/关闭正常 |

**里程碑**: `TowowWorkerAgent` 可作为基类使用。

### 6.2 Phase 2: Coordinator 迁移（1 周）

**目标**: Coordinator 完全运行在 OpenAgents 上。

| 任务 | 预估 | 验收标准 |
|------|------|----------|
| 实现 TowowCoordinator | 2d | @on_event 装饰器工作 |
| 需求理解 LLM 调用 | 1d | 返回结构化分析 |
| Agent 筛选逻辑 | 1d | 筛选结果合理 |
| Channel 创建 | 1d | OpenAgents Channel 创建成功 |

**里程碑**: 需求提交后能创建 Channel 并通知 ChannelAdmin。

### 6.3 Phase 3: ChannelAdmin + 状态机（2 周）

**目标**: 状态机驱动的协商流程完整运行。

| 任务 | 预估 | 验收标准 |
|------|------|----------|
| 实现 TowowChannelAdmin | 3d | 状态转换正确 |
| 状态机测试 | 2d | 所有转换路径覆盖 |
| 提案聚合 | 2d | LLM 聚合结果合理 |
| 子网触发 | 2d | 递归深度控制正确 |
| 超时处理 | 1d | 超时后状态转换正确 |

**里程碑**: 完整的协商流程可运行（无前端）。

### 6.4 Phase 4: UserAgent + SSE 完整桥接（1 周）

**目标**: 端到端流程打通，前端零改动。

| 任务 | 预估 | 验收标准 |
|------|------|----------|
| 实现 TowowUserAgent | 2d | 响应邀请、提交提案正常 |
| SSE Bridge 完善 | 2d | 所有事件映射正确 |
| 端到端测试 | 1d | 前端 UI 正常更新 |

**里程碑**: 前端可正常使用新后端。

### 6.5 Phase 5: 清理与优化（1 周）

**目标**: 移除旧代码，优化性能。

| 任务 | 预估 | 验收标准 |
|------|------|----------|
| 移除旧 Agent 实现 | 1d | 代码清理完成 |
| 移除 AgentRouter | 0.5d | 不再使用 |
| 性能基准测试 | 1d | 响应时间 < 现有实现 |
| 文档更新 | 1d | README 更新 |
| 监控完善 | 1.5d | 关键指标可观测 |

**里程碑**: 迁移完成，旧代码移除。

---

## 7. 附录

### 7.1 文件路径汇总

| 新文件 | 路径 | 说明 |
|--------|------|------|
| TowowWorkerAgent | `/towow/openagents/agents/base_v2.py` | 基类适配层 |
| TowowCoordinator | `/towow/openagents/agents/coordinator_v2.py` | 需求协调器 |
| TowowChannelAdmin | `/towow/openagents/agents/channel_admin_v2.py` | Channel 管理器 |
| TowowUserAgent | `/towow/openagents/agents/user_agent_v2.py` | 用户数字分身 |
| TowowEventBridge | `/towow/openagents/bridges/sse_bridge.py` | SSE 桥接层 |

### 7.2 依赖版本

```toml
[dependencies]
openagents = ">=0.1.0"  # [ASSUMPTION] 需确认实际版本
python = ">=3.10"
```

### 7.3 未决项

| ID | 描述 | 负责人 | 截止日期 |
|----|------|--------|----------|
| [OPEN-1] | OpenAgents 生产部署配置 | TBD | Phase 5 前 |
| [OPEN-2] | Redis 状态持久化方案 | TBD | Phase 5 评估 |
| [OPEN-3] | 多实例部署下的 Channel 同步 | TBD | Phase 5 评估 |

---

**文档结束**

*Generated by tech skill*
