# 技术方案补充02：事件类型定义

> ToWow系统的完整事件类型定义和消息格式规范

---

## 〇、设计文档事件映射

为保持与设计文档的一致性，下表展示设计文档事件名与技术方案事件名的对应关系：

| # | 设计文档事件 | 技术方案事件 | 说明 |
|---|-------------|-------------|------|
| 1 | `demand.broadcast` | `towow.demand.broadcast` | 需求广播 |
| 2 | `filter.completed` | `towow.filter.completed` | 筛选完成 |
| 3 | `channel.created` | `towow.channel.created` | Channel创建 |
| 4 | `offer.submitted` | `towow.offer.submitted` | Offer提交 |
| 5 | `plan.distributed` | `towow.proposal.distributed` | 方案分发（plan→proposal） |
| 6 | `agent.response` | `towow.proposal.feedback` | Agent反馈（语义映射） |
| 7 | `subnet.triggered` | `towow.subnet.triggered` | 子网触发 |
| 8 | `plan.finalized` | `towow.proposal.finalized` | 方案确定（plan→proposal） |

**命名规范说明**：
- 技术方案统一使用 `towow.` 前缀以避免与其他系统事件冲突
- 设计文档中的 `plan` 在技术方案中统一改为 `proposal`，语义更明确
- 设计文档中的 `agent.response` 在技术方案中细分为 `offer.submitted` 和 `proposal.feedback`

---

## 一、事件类型总览

ToWow系统定义8种核心事件类型，用于Agent间通信：

| 事件类型 | 触发者 | 接收者 | 说明 |
|---------|--------|--------|------|
| `demand.broadcast` | Coordinator | 全网络 | 需求广播 |
| `filter.completed` | Coordinator | 内部日志 | 筛选完成 |
| `channel.created` | Coordinator | ChannelAdmin | 协商Channel创建 |
| `offer.submitted` | UserAgent | ChannelAdmin | Agent提交offer |
| `proposal.distributed` | ChannelAdmin | 参与者 | 方案分发 |
| `agent.response` | UserAgent | ChannelAdmin | Agent反馈 |
| `subnet.triggered` | ChannelAdmin | Coordinator | 触发子网递归 |
| `plan.finalized` | ChannelAdmin | 全参与者 | 最终方案确定 |

---

## 二、事件定义（Python）

### 2.1 事件枚举

```python
"""
towow/events/types.py
事件类型定义
"""
from enum import Enum


class TowowEventType(Enum):
    """ToWow事件类型枚举"""

    # === 需求阶段 ===
    DEMAND_SUBMITTED = "towow.demand.submitted"        # 用户提交需求
    DEMAND_BROADCAST = "towow.demand.broadcast"        # 需求广播
    DEMAND_ACCEPTED = "towow.demand.accepted"          # 需求被接受处理
    DEMAND_REJECTED = "towow.demand.rejected"          # 需求被拒绝

    # === 筛选阶段 ===
    FILTER_STARTED = "towow.filter.started"            # 开始筛选
    FILTER_COMPLETED = "towow.filter.completed"        # 筛选完成

    # === Channel阶段 ===
    CHANNEL_CREATED = "towow.channel.created"          # Channel创建
    CHANNEL_INVITE_SENT = "towow.channel.invite_sent"  # 邀请已发送
    CHANNEL_CLOSED = "towow.channel.closed"            # Channel关闭

    # === Offer阶段 ===
    OFFER_REQUESTED = "towow.offer.requested"          # 请求offer
    OFFER_SUBMITTED = "towow.offer.submitted"          # offer已提交
    OFFER_TIMEOUT = "towow.offer.timeout"              # offer超时

    # === 方案阶段 ===
    PROPOSAL_AGGREGATING = "towow.proposal.aggregating"   # 正在聚合
    PROPOSAL_DISTRIBUTED = "towow.proposal.distributed"   # 方案已分发
    PROPOSAL_FEEDBACK = "towow.proposal.feedback"         # 收到反馈
    PROPOSAL_ADJUSTING = "towow.proposal.adjusting"       # 正在调整
    PROPOSAL_FINALIZED = "towow.proposal.finalized"       # 方案确定

    # === 递归阶段 ===
    GAP_IDENTIFIED = "towow.gap.identified"            # 识别到缺口
    SUBNET_TRIGGERED = "towow.subnet.triggered"        # 触发子网
    SUBNET_COMPLETED = "towow.subnet.completed"        # 子网完成

    # === 系统事件 ===
    AGENT_ONLINE = "towow.agent.online"                # Agent上线
    AGENT_OFFLINE = "towow.agent.offline"              # Agent下线
    ERROR_OCCURRED = "towow.error.occurred"            # 错误发生
```

### 2.2 事件Payload模型

```python
"""
towow/events/payloads.py
事件Payload定义
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


# === 基础模型 ===

class BasePayload(BaseModel):
    """基础Payload"""
    event_id: str = Field(..., description="事件唯一ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_agent: str = Field(..., description="发送者Agent ID")


# === 需求相关 ===

class DemandSubmittedPayload(BasePayload):
    """需求提交事件"""
    demand_id: str
    user_id: str
    raw_input: str
    surface_demand: Optional[str] = None
    deep_understanding: Optional[Dict[str, Any]] = None


class DemandBroadcastPayload(BasePayload):
    """需求广播事件"""
    demand_id: str
    requester_id: str
    surface_demand: str
    capability_tags: List[str] = []
    location_hint: Optional[str] = None
    urgency: str = "normal"  # low | normal | high


class DemandAcceptedPayload(BasePayload):
    """需求被接受事件"""
    demand_id: str
    channel_id: str
    candidate_count: int


# === 筛选相关 ===

class FilterCompletedPayload(BasePayload):
    """筛选完成事件"""
    demand_id: str
    total_agents: int
    candidates: List[Dict[str, Any]]  # [{agent_id, reason}]
    filter_duration_ms: int


# === Channel相关 ===

class ChannelCreatedPayload(BasePayload):
    """Channel创建事件"""
    channel_id: str
    demand_id: str
    invited_agents: List[str]
    parent_channel: Optional[str] = None  # 子网时有值
    recursion_depth: int = 0


class ChannelInviteSentPayload(BasePayload):
    """邀请发送事件"""
    channel_id: str
    agent_id: str
    demand_summary: str


# === Offer相关 ===

class OfferDecision(str, Enum):
    PARTICIPATE = "participate"
    DECLINE = "decline"
    NEED_MORE_INFO = "need_more_info"


class OfferSubmittedPayload(BasePayload):
    """Offer提交事件"""
    channel_id: str
    agent_id: str
    decision: OfferDecision
    contribution: Optional[str] = None
    conditions: List[str] = []
    reasoning: Optional[str] = None


# === 方案相关 ===

class Assignment(BaseModel):
    """分配项"""
    agent_id: str
    role: str
    responsibility: str
    conditions_accepted: bool = True
    notes: Optional[str] = None


class ProposalDistributedPayload(BasePayload):
    """方案分发事件"""
    channel_id: str
    proposal_version: int
    summary: str
    assignments: List[Assignment]
    timeline: Optional[str] = None
    open_questions: List[str] = []


class FeedbackType(str, Enum):
    ACCEPT = "accept"
    NEGOTIATE = "negotiate"
    WITHDRAW = "withdraw"


class ProposalFeedbackPayload(BasePayload):
    """方案反馈事件"""
    channel_id: str
    agent_id: str
    proposal_version: int
    feedback_type: FeedbackType
    adjustment_request: Optional[str] = None
    reasoning: Optional[str] = None


class ProposalFinalizedPayload(BasePayload):
    """方案确定事件"""
    channel_id: str
    demand_id: str
    final_proposal: Dict[str, Any]
    participants: List[str]
    negotiation_rounds: int
    total_duration_seconds: int


# === 递归相关 ===

class GapInfo(BaseModel):
    """缺口信息"""
    gap_type: str
    description: str
    importance: int  # 1-100
    suggested_capability: Optional[str] = None


class GapIdentifiedPayload(BasePayload):
    """缺口识别事件"""
    channel_id: str
    demand_id: str
    gaps: List[GapInfo]
    overall_completion: int  # 百分比


class SubnetTriggeredPayload(BasePayload):
    """子网触发事件"""
    parent_channel_id: str
    sub_channel_id: str
    sub_demand: Dict[str, Any]
    recursion_depth: int
    gap_being_addressed: str


class SubnetCompletedPayload(BasePayload):
    """子网完成事件"""
    parent_channel_id: str
    sub_channel_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None


# === 系统事件 ===

class AgentOnlinePayload(BasePayload):
    """Agent上线事件"""
    agent_id: str
    agent_type: str  # coordinator | channel_admin | user_agent
    capabilities: List[str] = []


class ErrorOccurredPayload(BasePayload):
    """错误事件"""
    error_code: str
    error_message: str
    context: Dict[str, Any] = {}
    recoverable: bool = True
```

### 2.3 事件工厂

```python
"""
towow/events/factory.py
事件创建工厂
"""
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime
from .types import TowowEventType
from .payloads import *


class EventFactory:
    """事件工厂"""

    @staticmethod
    def create_event(
        event_type: TowowEventType,
        source_agent: str,
        **payload_data
    ) -> Dict[str, Any]:
        """
        创建标准化事件

        Returns:
            {
                "event_type": "towow.xxx.xxx",
                "event_id": "uuid",
                "timestamp": "ISO8601",
                "source_agent": "agent_id",
                "payload": {...}
            }
        """
        return {
            "event_type": event_type.value,
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source_agent": source_agent,
            "payload": payload_data
        }

    # === 便捷方法 ===

    @classmethod
    def demand_broadcast(
        cls,
        source_agent: str,
        demand_id: str,
        requester_id: str,
        surface_demand: str,
        capability_tags: list = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建需求广播事件"""
        return cls.create_event(
            TowowEventType.DEMAND_BROADCAST,
            source_agent,
            demand_id=demand_id,
            requester_id=requester_id,
            surface_demand=surface_demand,
            capability_tags=capability_tags or [],
            **kwargs
        )

    @classmethod
    def offer_submitted(
        cls,
        source_agent: str,
        channel_id: str,
        agent_id: str,
        decision: str,
        contribution: str = None,
        conditions: list = None,
        reasoning: str = None
    ) -> Dict[str, Any]:
        """创建Offer提交事件"""
        return cls.create_event(
            TowowEventType.OFFER_SUBMITTED,
            source_agent,
            channel_id=channel_id,
            agent_id=agent_id,
            decision=decision,
            contribution=contribution,
            conditions=conditions or [],
            reasoning=reasoning
        )

    @classmethod
    def proposal_distributed(
        cls,
        source_agent: str,
        channel_id: str,
        proposal_version: int,
        summary: str,
        assignments: list,
        **kwargs
    ) -> Dict[str, Any]:
        """创建方案分发事件"""
        return cls.create_event(
            TowowEventType.PROPOSAL_DISTRIBUTED,
            source_agent,
            channel_id=channel_id,
            proposal_version=proposal_version,
            summary=summary,
            assignments=assignments,
            **kwargs
        )

    @classmethod
    def proposal_finalized(
        cls,
        source_agent: str,
        channel_id: str,
        demand_id: str,
        final_proposal: dict,
        participants: list,
        negotiation_rounds: int,
        total_duration_seconds: int
    ) -> Dict[str, Any]:
        """创建方案确定事件"""
        return cls.create_event(
            TowowEventType.PROPOSAL_FINALIZED,
            source_agent,
            channel_id=channel_id,
            demand_id=demand_id,
            final_proposal=final_proposal,
            participants=participants,
            negotiation_rounds=negotiation_rounds,
            total_duration_seconds=total_duration_seconds
        )

    @classmethod
    def gap_identified(
        cls,
        source_agent: str,
        channel_id: str,
        demand_id: str,
        gaps: list,
        overall_completion: int
    ) -> Dict[str, Any]:
        """创建缺口识别事件"""
        return cls.create_event(
            TowowEventType.GAP_IDENTIFIED,
            source_agent,
            channel_id=channel_id,
            demand_id=demand_id,
            gaps=gaps,
            overall_completion=overall_completion
        )

    @classmethod
    def subnet_triggered(
        cls,
        source_agent: str,
        parent_channel_id: str,
        sub_channel_id: str,
        sub_demand: dict,
        recursion_depth: int,
        gap_being_addressed: str
    ) -> Dict[str, Any]:
        """创建子网触发事件"""
        return cls.create_event(
            TowowEventType.SUBNET_TRIGGERED,
            source_agent,
            parent_channel_id=parent_channel_id,
            sub_channel_id=sub_channel_id,
            sub_demand=sub_demand,
            recursion_depth=recursion_depth,
            gap_being_addressed=gap_being_addressed
        )

    @classmethod
    def error_occurred(
        cls,
        source_agent: str,
        error_code: str,
        error_message: str,
        context: dict = None,
        recoverable: bool = True
    ) -> Dict[str, Any]:
        """创建错误事件"""
        return cls.create_event(
            TowowEventType.ERROR_OCCURRED,
            source_agent,
            error_code=error_code,
            error_message=error_message,
            context=context or {},
            recoverable=recoverable
        )
```

---

## 三、消息格式规范

### 3.1 Agent间直接消息格式

```json
{
  "type": "消息类型",
  "event_id": "uuid",
  "timestamp": "2026-01-21T12:00:00Z",
  "payload": {
    // 具体内容
  }
}
```

**消息类型列表**：

| type | 发送者 | 接收者 | 说明 |
|------|--------|--------|------|
| `new_demand` | UserAgent | Coordinator | 新需求 |
| `demand_accepted` | Coordinator | UserAgent | 需求已接受 |
| `demand_error` | Coordinator | UserAgent | 需求错误 |
| `collaboration_invite` | Coordinator | UserAgent | 协作邀请 |
| `proposal_review` | ChannelAdmin | UserAgent | 方案评审请求 |
| `proposal_finalized` | ChannelAdmin | UserAgent | 最终方案通知 |

### 3.2 Channel消息格式

```json
{
  "type": "消息类型",
  "event_id": "uuid",
  "timestamp": "2026-01-21T12:00:00Z",
  "sender": "agent_id",
  "payload": {
    // 具体内容
  }
}
```

**Channel消息类型列表**：

| type | 发送者 | 说明 |
|------|--------|------|
| `offer_response` | UserAgent | 回应邀请 |
| `proposal_feedback` | UserAgent | 方案反馈 |
| `proposal_update` | ChannelAdmin | 方案更新 |
| `negotiation_message` | Any | 协商讨论 |
| `compromise_proposal` | ChannelAdmin | 妥协方案 |
| `channel_closing` | ChannelAdmin | Channel即将关闭 |

### 3.3 具体消息示例

#### new_demand（新需求）

```json
{
  "type": "new_demand",
  "event_id": "evt_123456",
  "timestamp": "2026-01-21T12:00:00Z",
  "payload": {
    "demand": {
      "raw_input": "我想在北京办一场50人的AI主题聚会",
      "surface_demand": "在北京举办50人规模的AI主题聚会",
      "deep_understanding": {
        "motivation": "对AI技术感兴趣，想认识同行",
        "likely_preferences": ["轻松氛围", "技术分享"],
        "emotional_context": "期待、积极"
      },
      "uncertainties": ["具体日期未定", "是否需要赞助"],
      "confidence": "medium"
    }
  }
}
```

#### collaboration_invite（协作邀请）

```json
{
  "type": "collaboration_invite",
  "event_id": "evt_234567",
  "timestamp": "2026-01-21T12:05:00Z",
  "payload": {
    "channel": "collab-abc12345",
    "demand": {
      "surface_demand": "在北京举办50人规模的AI主题聚会",
      "capability_tags": ["场地", "分享嘉宾", "活动策划"],
      "location_hint": "北京"
    },
    "selection_reason": "您有场地资源，且对AI活动感兴趣",
    "message": "您被邀请参与协作，请查看需求并决定是否参与。"
  }
}
```

#### offer_response（Offer回应）

```json
{
  "type": "offer_response",
  "event_id": "evt_345678",
  "timestamp": "2026-01-21T12:10:00Z",
  "sender": "user_agent_bob",
  "payload": {
    "decision": "participate",
    "contribution": "可以提供朝阳区30人会议室，配有投影设备",
    "conditions": [
      "需要提前3天确认",
      "场地费用需要分摊（约500元）"
    ],
    "reasoning": "对AI聚会感兴趣，正好最近在关注这个领域"
  }
}
```

#### proposal_distributed（方案分发）

```json
{
  "type": "proposal_review",
  "event_id": "evt_456789",
  "timestamp": "2026-01-21T12:30:00Z",
  "payload": {
    "channel": "collab-abc12345",
    "proposal": {
      "summary": "2月15日在朝阳区举办30人AI聚会",
      "assignments": [
        {
          "agent_id": "user_agent_bob",
          "role": "场地提供者",
          "responsibility": "提供30人会议室，配有投影",
          "conditions_accepted": true,
          "notes": "费用500元由参与者分摊"
        },
        {
          "agent_id": "user_agent_alice",
          "role": "分享嘉宾",
          "responsibility": "做30分钟AI技术分享",
          "conditions_accepted": true,
          "notes": null
        }
      ],
      "timeline": "2月15日 14:00-17:00",
      "open_questions": ["是否需要下午茶？"],
      "confidence": "high"
    },
    "my_assignment": {
      "agent_id": "user_agent_bob",
      "role": "场地提供者",
      "responsibility": "提供30人会议室，配有投影",
      "conditions_accepted": true,
      "notes": "费用500元由参与者分摊"
    },
    "message": "请查看方案并提供反馈"
  }
}
```

#### proposal_feedback（方案反馈）

```json
{
  "type": "proposal_feedback",
  "event_id": "evt_567890",
  "timestamp": "2026-01-21T12:35:00Z",
  "sender": "user_agent_bob",
  "payload": {
    "feedback_type": "negotiate",
    "adjustment_request": "2月15日有其他安排，能否改到2月16日？",
    "reasoning": "时间冲突，但很想参与这次活动"
  }
}
```

#### proposal_finalized（最终方案）

```json
{
  "type": "proposal_finalized",
  "event_id": "evt_678901",
  "timestamp": "2026-01-21T13:00:00Z",
  "payload": {
    "channel": "collab-abc12345",
    "proposal": {
      "summary": "2月16日在朝阳区举办30人AI聚会",
      "assignments": [...],
      "timeline": "2月16日 14:00-17:00",
      "final": true
    },
    "my_assignment": {...},
    "message": "方案已确定，请按计划执行！",
    "stats": {
      "negotiation_rounds": 2,
      "total_duration_minutes": 60,
      "participants_count": 3
    }
  }
}
```

---

## 四、错误码定义

### 4.1 错误码格式

`TOWOW_[模块]_[序号]`

### 4.2 错误码列表

| 错误码 | 说明 | 可恢复 |
|--------|------|--------|
| **需求阶段** |||
| `TOWOW_DEMAND_001` | 需求解析失败 | 是 |
| `TOWOW_DEMAND_002` | 需求内容为空 | 是 |
| `TOWOW_DEMAND_003` | SecondMe服务不可用 | 是 |
| **筛选阶段** |||
| `TOWOW_FILTER_001` | 无可用Agent | 是 |
| `TOWOW_FILTER_002` | LLM筛选超时 | 是 |
| `TOWOW_FILTER_003` | 筛选结果解析失败 | 是 |
| **Channel阶段** |||
| `TOWOW_CHANNEL_001` | Channel创建失败 | 是 |
| `TOWOW_CHANNEL_002` | 邀请发送失败 | 是 |
| `TOWOW_CHANNEL_003` | Channel状态异常 | 否 |
| **方案阶段** |||
| `TOWOW_PROPOSAL_001` | 方案聚合失败 | 是 |
| `TOWOW_PROPOSAL_002` | 方案分发失败 | 是 |
| `TOWOW_PROPOSAL_003` | 反馈收集超时 | 是 |
| `TOWOW_PROPOSAL_004` | 达到最大协商轮次 | 是 |
| **递归阶段** |||
| `TOWOW_SUBNET_001` | 超过最大递归深度 | 否 |
| `TOWOW_SUBNET_002` | 子网创建失败 | 是 |
| **系统错误** |||
| `TOWOW_SYSTEM_001` | 数据库连接失败 | 是 |
| `TOWOW_SYSTEM_002` | OpenAgent连接失败 | 是 |
| `TOWOW_SYSTEM_003` | 内部错误 | 否 |

---

## 五、事件订阅与分发

### 5.1 事件总线

```python
"""
towow/events/bus.py
事件总线
"""
from typing import Dict, List, Callable, Any
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """
    事件总线

    支持：
    - 事件订阅
    - 事件发布
    - 通配符订阅（towow.*）
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def publish(self, event: Dict[str, Any]):
        """发布事件"""
        event_type = event.get("event_type", "")

        # 精确匹配的handler
        handlers = self._handlers.get(event_type, [])

        # 通配符匹配
        for pattern, pattern_handlers in self._handlers.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if event_type.startswith(prefix):
                    handlers.extend(pattern_handlers)

        if not handlers:
            logger.debug(f"No handlers for event: {event_type}")
            return

        # 并发执行所有handler
        tasks = [handler(event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 记录错误
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Handler error for {event_type}: {result}")


# 全局事件总线实例
event_bus = EventBus()
```

### 5.2 事件记录器（用于前端推送）

```python
"""
towow/events/recorder.py
事件记录器（用于实时推送）
"""
from typing import Dict, Any, List
from collections import deque
import asyncio


class EventRecorder:
    """
    事件记录器

    记录最近的事件，供前端轮询或WebSocket推送
    """

    def __init__(self, max_events: int = 1000):
        self._events: deque = deque(maxlen=max_events)
        self._subscribers: List[asyncio.Queue] = []

    async def record(self, event: Dict[str, Any]):
        """记录事件"""
        self._events.append(event)

        # 推送给所有订阅者
        for queue in self._subscribers:
            await queue.put(event)

    def get_recent(self, count: int = 50) -> List[Dict[str, Any]]:
        """获取最近的事件"""
        return list(self._events)[-count:]

    def get_by_channel(self, channel_id: str, count: int = 50) -> List[Dict[str, Any]]:
        """获取指定Channel的事件"""
        channel_events = [
            e for e in self._events
            if e.get("payload", {}).get("channel_id") == channel_id
               or e.get("payload", {}).get("channel") == channel_id
        ]
        return channel_events[-count:]

    def subscribe(self) -> asyncio.Queue:
        """订阅实时事件"""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """取消订阅"""
        if queue in self._subscribers:
            self._subscribers.remove(queue)


# 全局记录器实例
event_recorder = EventRecorder()
```

---

**文档版本**: v1.0
**创建时间**: 2026-01-21
**状态**: 补充完成
