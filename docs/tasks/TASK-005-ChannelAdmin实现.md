# TASK-005：ChannelAdmin Agent实现

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-005 |
| 所属Phase | Phase 2：核心Agent |
| 依赖 | TASK-002, TASK-003 |
| 预估工作量 | 1.5天 |
| 状态 | 待开始 |

---

## 任务描述

实现Channel管理Agent，负责协商过程管理、方案聚合、冲突处理。

---

## 具体工作

### 1. ChannelAdmin核心实现

`openagents/agents/channel_admin.py`:

```python
from typing import Dict, Any, List, Optional
from .base import TowowBaseAgent
from database.connection import Database
from database.models import CollaborationChannel, AgentResponse
from services.llm import LLMService
from enum import Enum
import asyncio

class ChannelStatus(Enum):
    INVITING = "inviting"
    COLLECTING = "collecting"
    AGGREGATING = "aggregating"
    FEEDBACK = "feedback"
    ADJUSTING = "adjusting"
    COMPLETED = "completed"
    FAILED = "failed"

class ChannelAdminAgent(TowowBaseAgent):
    """Channel管理Agent"""

    MAX_NEGOTIATION_ROUNDS = 5
    RESPONSE_TIMEOUT = 300  # 5分钟超时

    def __init__(self, database: Database, llm_service: LLMService, **kwargs):
        super().__init__(agent_id="channel-admin", **kwargs)
        self.db = database
        self.llm = llm_service
        self.managed_channels: Dict[str, Dict] = {}

    async def on_channel_message(self, context):
        """处理Channel内的消息"""
        channel = context.channel
        message = context.message
        sender = context.sender

        if channel not in self.managed_channels:
            return  # 不是我们管理的Channel

        msg_type = message.get("type")

        if msg_type == "response":
            await self.handle_response(channel, sender, message)
        elif msg_type == "feedback":
            await self.handle_feedback(channel, sender, message)

    async def start_managing(
        self,
        channel_name: str,
        demand_id: str,
        demand: Dict,
        invited_agents: List[str]
    ):
        """开始管理一个协商Channel"""
        self.managed_channels[channel_name] = {
            "demand_id": demand_id,
            "demand": demand,
            "invited_agents": invited_agents,
            "responses": {},
            "status": ChannelStatus.COLLECTING,
            "current_proposal": None,
            "round": 0
        }

        # 设置超时
        asyncio.create_task(
            self._response_timeout(channel_name)
        )

        self.logger.info(f"Started managing channel {channel_name}")

    async def handle_response(
        self,
        channel: str,
        sender: str,
        message: Dict
    ):
        """处理Agent的回应"""
        channel_data = self.managed_channels.get(channel)
        if not channel_data:
            return

        # 存储回应
        channel_data["responses"][sender] = {
            "response_type": message.get("decision"),  # participate/decline/need_more_info
            "contribution": message.get("contribution"),
            "conditions": message.get("conditions", []),
            "reasoning": message.get("reasoning")
        }

        # 存储到数据库
        async with self.db.session() as session:
            response = AgentResponse(
                channel_id=channel,
                agent_id=sender,
                response_type=message.get("decision"),
                contribution=message.get("contribution"),
                conditions=message.get("conditions", []),
                reasoning=message.get("reasoning")
            )
            session.add(response)

        self.logger.info(f"Received response from {sender} in {channel}")

        # 检查是否收集完成
        await self._check_collection_complete(channel)

    async def _check_collection_complete(self, channel: str):
        """检查是否收集完所有回应"""
        channel_data = self.managed_channels.get(channel)
        if not channel_data:
            return

        invited = set(channel_data["invited_agents"])
        responded = set(channel_data["responses"].keys())

        # 所有人都回应了，或者参与者已经足够
        participants = [
            r for r in channel_data["responses"].values()
            if r["response_type"] == "participate"
        ]

        if responded == invited or len(participants) >= 3:
            await self.aggregate_proposal(channel)

    async def aggregate_proposal(self, channel: str):
        """聚合方案"""
        channel_data = self.managed_channels.get(channel)
        if not channel_data:
            return

        channel_data["status"] = ChannelStatus.AGGREGATING

        # 收集参与者
        participants = {
            agent_id: resp
            for agent_id, resp in channel_data["responses"].items()
            if resp["response_type"] == "participate"
        }

        if not participants:
            await self._handle_no_participants(channel)
            return

        # 调用LLM聚合方案
        proposal = await self._llm_aggregate(
            demand=channel_data["demand"],
            participants=participants
        )

        channel_data["current_proposal"] = proposal
        channel_data["status"] = ChannelStatus.FEEDBACK

        # 发送方案给参与者
        await self._broadcast_proposal(channel, proposal)

    async def _llm_aggregate(
        self,
        demand: Dict,
        participants: Dict[str, Dict]
    ) -> Dict:
        """使用LLM聚合方案"""

        participants_text = "\n\n".join([
            f"Agent: {agent_id}\n"
            f"贡献: {resp.get('contribution', '未说明')}\n"
            f"条件: {resp.get('conditions', [])}"
            for agent_id, resp in participants.items()
        ])

        prompt = f"""
## 需求

{demand.get('surface_demand', '')}

深层理解：{demand.get('deep_understanding', {})}

---

## 参与者回应

{participants_text}

---

## 任务

请将这些回应聚合成一个协作方案。

考虑：
1. 需求方的核心需求能否被满足
2. 每个参与者的角色分配是否合理
3. 如有冲突（如多人提供同一资源），选择最合适的

返回JSON格式：
```json
{{
  "proposal": {{
    "summary": "方案摘要",
    "assignments": [
      {{
        "agent_id": "xxx",
        "role": "场地提供者",
        "task": "提供30人活动场地",
        "conditions_accepted": ["场地费分担"]
      }}
    ],
    "unmet_needs": ["可能还需要..."],
    "conflicts_resolved": ["xxx和yyy都想提供场地，选择xxx因为..."]
  }}
}}
```
"""

        response = await self.llm.complete(
            prompt=prompt,
            system="你是一个协作方案聚合专家，负责将多方回应整合成可执行的方案。"
        )

        return self._parse_proposal(response)

    async def _broadcast_proposal(self, channel: str, proposal: Dict):
        """广播方案给参与者"""
        channel_data = self.managed_channels[channel]

        for agent_id, assignment in self._get_assignments(proposal):
            await self.send_direct(
                to=agent_id,
                content={
                    "type": "proposal",
                    "channel": channel,
                    "proposal": proposal,
                    "your_assignment": assignment
                }
            )

    async def handle_feedback(
        self,
        channel: str,
        sender: str,
        message: Dict
    ):
        """处理方案反馈"""
        channel_data = self.managed_channels.get(channel)
        if not channel_data:
            return

        feedback_type = message.get("feedback_type")  # accept/negotiate/withdraw

        if feedback_type == "accept":
            # 标记接受
            pass
        elif feedback_type == "negotiate":
            # 需要调整
            await self._handle_negotiation(channel, sender, message)
        elif feedback_type == "withdraw":
            # 退出
            await self._handle_withdrawal(channel, sender)

    async def _handle_negotiation(
        self,
        channel: str,
        sender: str,
        message: Dict
    ):
        """处理协商请求"""
        channel_data = self.managed_channels[channel]

        if channel_data["round"] >= self.MAX_NEGOTIATION_ROUNDS:
            # 超过最大轮次，生成妥协方案
            await self._generate_compromise(channel)
            return

        channel_data["round"] += 1
        channel_data["status"] = ChannelStatus.ADJUSTING

        # 调用LLM调整方案
        adjusted = await self._llm_adjust(
            channel_data["demand"],
            channel_data["current_proposal"],
            sender,
            message.get("adjustment_request")
        )

        channel_data["current_proposal"] = adjusted
        channel_data["status"] = ChannelStatus.FEEDBACK

        # 重新广播
        await self._broadcast_proposal(channel, adjusted)

    async def _generate_compromise(self, channel: str):
        """生成妥协方案"""
        channel_data = self.managed_channels[channel]

        # 调用LLM生成妥协方案
        # 使用提示词9：妥协方案生成
        pass

    async def _response_timeout(self, channel: str):
        """回应超时处理"""
        await asyncio.sleep(self.RESPONSE_TIMEOUT)

        channel_data = self.managed_channels.get(channel)
        if channel_data and channel_data["status"] == ChannelStatus.COLLECTING:
            self.logger.info(f"Response timeout for channel {channel}")
            await self.aggregate_proposal(channel)

    async def _handle_no_participants(self, channel: str):
        """处理无人参与的情况"""
        channel_data = self.managed_channels[channel]
        channel_data["status"] = ChannelStatus.FAILED

        # 通知发起者
        # 生成妥协/建议方案

    def _parse_proposal(self, response: str) -> Dict:
        """解析方案"""
        import json
        import re

        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result.get("proposal", {})
            except json.JSONDecodeError:
                pass

        return {"summary": "方案解析失败", "assignments": []}

    def _get_assignments(self, proposal: Dict):
        """获取分配列表"""
        assignments = proposal.get("assignments", [])
        for a in assignments:
            yield a.get("agent_id"), a
```

---

## 验收标准

- [ ] 能够管理协商Channel的生命周期
- [ ] 能够收集Agent回应
- [ ] 能够调用LLM聚合方案
- [ ] 能够处理反馈和调整
- [ ] 支持最多5轮协商
- [ ] 超时能正确触发聚合

---

## 产出物

- `openagents/agents/channel_admin.py` - ChannelAdmin Agent实现
- 状态机定义
- 单元测试

---

**创建时间**: 2026-01-21
