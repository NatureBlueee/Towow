"""
ChannelAdmin Agent - 协商Channel管理者

职责：
1. 管理单个协商Channel的生命周期
2. 广播需求给候选Agent
3. 收集响应并聚合方案
4. 多轮协商直到达成共识
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .base import TowowBaseAgent, EventContext, ChannelMessageContext

logger = logging.getLogger(__name__)


class ChannelStatus(Enum):
    """Channel状态枚举"""
    CREATED = "created"
    BROADCASTING = "broadcasting"
    COLLECTING = "collecting"
    AGGREGATING = "aggregating"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    FINALIZED = "finalized"
    FAILED = "failed"


@dataclass
class ChannelState:
    """Channel状态数据类"""
    channel_id: str
    demand_id: str
    demand: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    status: ChannelStatus = ChannelStatus.CREATED
    current_round: int = 1
    max_rounds: int = 5  # 默认最多5轮协商
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    current_proposal: Optional[Dict[str, Any]] = None
    proposal_feedback: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_subnet: bool = False
    parent_channel_id: Optional[str] = None
    recursion_depth: int = 0


class ChannelAdminAgent(TowowBaseAgent):
    """
    ChannelAdmin Agent - 管理协商Channel的全生命周期

    状态机流程:
    CREATED -> BROADCASTING -> COLLECTING -> AGGREGATING ->
    PROPOSAL_SENT -> NEGOTIATING -> FINALIZED/FAILED

    支持多轮协商，直到达成共识或超过最大轮次。
    """

    AGENT_TYPE = "channel_admin"

    # 最大协商轮次
    MAX_NEGOTIATION_ROUNDS = 5

    # 超时配置（秒）
    RESPONSE_TIMEOUT = 300  # 5分钟等待响应超时
    FEEDBACK_TIMEOUT = 120  # 2分钟等待反馈超时

    def __init__(self, **kwargs):
        """初始化ChannelAdmin Agent"""
        super().__init__(**kwargs)
        self.channels: Dict[str, ChannelState] = {}
        self._timeout_tasks: Dict[str, asyncio.Task] = {}

    async def on_startup(self):
        """Agent启动时调用"""
        await super().on_startup()
        self._logger.info("ChannelAdmin Agent started, ready to manage channels")

    async def on_shutdown(self):
        """Agent关闭时调用"""
        # 取消所有超时任务
        for task in self._timeout_tasks.values():
            if not task.done():
                task.cancel()
        self._timeout_tasks.clear()
        await super().on_shutdown()

    # ========== 公共 API 方法 ==========

    async def start_managing(
        self,
        channel_name: str,
        demand_id: str,
        demand: Dict[str, Any],
        invited_agents: List[Dict[str, Any]],
        max_rounds: Optional[int] = None
    ) -> str:
        """
        开始管理一个协商Channel

        Args:
            channel_name: Channel名称（可选，为空则自动生成）
            demand_id: 需求ID
            demand: 需求信息
            invited_agents: 邀请的Agent列表，每项包含 agent_id 和可选的 reason/match_score
            max_rounds: 最大协商轮次（默认使用 MAX_NEGOTIATION_ROUNDS）

        Returns:
            channel_id: 创建的Channel ID
        """
        channel_id = channel_name or f"ch-{uuid4().hex[:8]}"

        if channel_id in self.channels:
            self._logger.warning(f"Channel {channel_id} already exists")
            return channel_id

        self._logger.info(f"Starting to manage channel {channel_id} for demand {demand_id}")

        # 创建Channel状态
        state = ChannelState(
            channel_id=channel_id,
            demand_id=demand_id,
            demand=demand,
            candidates=invited_agents,
            max_rounds=max_rounds or self.MAX_NEGOTIATION_ROUNDS
        )
        self.channels[channel_id] = state

        # 发布Channel创建事件
        await self._publish_event("towow.channel.created", {
            "channel_id": channel_id,
            "demand_id": demand_id,
            "candidates_count": len(invited_agents)
        })

        # 开始广播需求
        await self._broadcast_demand(state)

        return channel_id

    async def handle_response(
        self,
        channel_id: str,
        agent_id: str,
        decision: str,
        contribution: Optional[str] = None,
        conditions: Optional[List[str]] = None,
        reasoning: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        estimated_effort: Optional[str] = None
    ) -> bool:
        """
        处理Agent的回应

        Args:
            channel_id: Channel ID
            agent_id: Agent ID
            decision: 决定 (participate/decline/conditional)
            contribution: 贡献描述
            conditions: 条件列表
            reasoning: 理由
            capabilities: 能力列表
            estimated_effort: 预估工作量

        Returns:
            是否成功处理
        """
        data = {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "decision": decision,
            "contribution": contribution,
            "conditions": conditions or [],
            "reasoning": reasoning,
            "capabilities": capabilities or [],
            "estimated_effort": estimated_effort
        }
        await self._handle_offer_response(data)
        return True

    async def aggregate_proposal(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        聚合方案（公共API）

        Args:
            channel_id: Channel ID

        Returns:
            生成的方案，如果失败返回 None
        """
        if channel_id not in self.channels:
            self._logger.warning(f"Channel {channel_id} not found")
            return None

        state = self.channels[channel_id]
        await self._aggregate_proposals(state)
        return state.current_proposal

    async def handle_feedback(
        self,
        channel_id: str,
        agent_id: str,
        feedback_type: str,
        adjustment_request: Optional[str] = None,
        concerns: Optional[List[str]] = None
    ) -> bool:
        """
        处理方案反馈

        Args:
            channel_id: Channel ID
            agent_id: Agent ID
            feedback_type: 反馈类型 (accept/reject/negotiate)
            adjustment_request: 调整请求
            concerns: 顾虑列表

        Returns:
            是否成功处理
        """
        data = {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "feedback_type": feedback_type,
            "adjustment_request": adjustment_request,
            "concerns": concerns or []
        }
        await self._handle_proposal_feedback(data)
        return True

    # ========== 消息处理方法 ==========

    async def on_direct(self, context: EventContext):
        """处理直接消息"""
        await super().on_direct(context)
        payload = context.incoming_event.payload
        content = payload.get("content", {})

        # 支持直接在 payload 中的消息格式
        data = content if isinstance(content, dict) else payload
        msg_type = data.get("type")

        self._logger.debug(f"Received direct message type: {msg_type}")

        if msg_type == "create_channel":
            await self._handle_create_channel(data, context)
        elif msg_type == "offer_response":
            await self._handle_offer_response(data)
        elif msg_type == "proposal_feedback":
            await self._handle_proposal_feedback(data)
        elif msg_type == "get_status":
            await self._handle_get_status(data, context)
        else:
            self._logger.warning(f"Unknown message type: {msg_type}")

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel消息"""
        await super().on_channel_post(context)
        payload = context.incoming_event.payload
        content = payload.get("content", {})
        data = content if isinstance(content, dict) else payload
        msg_type = data.get("type")

        self._logger.debug(f"Received channel message type: {msg_type} in {context.channel}")

        if msg_type == "create_channel":
            await self._handle_create_channel(data, context)
        elif msg_type == "offer_response":
            await self._handle_offer_response(data)
        elif msg_type == "proposal_feedback":
            await self._handle_proposal_feedback(data)

    async def _handle_create_channel(
        self,
        data: Dict[str, Any],
        context: Optional[EventContext] = None
    ):
        """处理创建Channel请求"""
        channel_id = data.get("channel_id") or f"ch-{uuid4().hex[:8]}"
        demand_id = data.get("demand_id")

        if channel_id in self.channels:
            self._logger.warning(f"Channel {channel_id} already exists")
            if context:
                await context.reply({
                    "content": {
                        "type": "error",
                        "error": "channel_exists",
                        "channel_id": channel_id
                    }
                })
            return

        self._logger.info(f"Creating channel {channel_id} for demand {demand_id}")

        # 创建Channel状态
        state = ChannelState(
            channel_id=channel_id,
            demand_id=demand_id,
            demand=data.get("demand", {}),
            candidates=data.get("candidates", []),
            max_rounds=data.get("max_rounds", self.MAX_NEGOTIATION_ROUNDS),
            is_subnet=data.get("is_subnet", False),
            parent_channel_id=data.get("parent_channel_id"),
            recursion_depth=data.get("recursion_depth", 0)
        )
        self.channels[channel_id] = state

        # 发布Channel创建事件
        await self._publish_event("towow.channel.created", {
            "channel_id": channel_id,
            "demand_id": demand_id,
            "candidates_count": len(state.candidates),
            "is_subnet": state.is_subnet
        })

        # 回复确认
        if context:
            await context.reply({
                "content": {
                    "type": "channel_created",
                    "channel_id": channel_id,
                    "status": "created"
                }
            })

        # 开始广播
        await self._broadcast_demand(state)

    async def _broadcast_demand(self, state: ChannelState):
        """广播需求给候选Agent"""
        state.status = ChannelStatus.BROADCASTING

        candidate_ids = [c.get("agent_id") for c in state.candidates if c.get("agent_id")]
        self._logger.info(
            f"Broadcasting demand to {len(candidate_ids)} candidates for channel {state.channel_id}"
        )

        # 发布广播事件
        await self._publish_event("towow.demand.broadcast", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "candidates": candidate_ids,
            "round": state.current_round
        })

        # 发送给每个候选Agent
        for candidate in state.candidates:
            agent_id = candidate.get("agent_id")
            if not agent_id:
                continue

            try:
                await self.send_to_agent(agent_id, {
                    "type": "demand_offer",
                    "channel_id": state.channel_id,
                    "demand_id": state.demand_id,
                    "demand": state.demand,
                    "round": state.current_round,
                    "filter_reason": candidate.get("reason", ""),
                    "match_score": candidate.get("match_score", 0)
                })
                self._logger.debug(f"Sent demand offer to {agent_id}")
            except Exception as e:
                self._logger.error(f"Failed to send demand offer to {agent_id}: {e}")

        state.status = ChannelStatus.COLLECTING

        # 启动超时监控
        self._start_timeout_task(
            f"response_{state.channel_id}",
            self._wait_for_responses(state),
            self.RESPONSE_TIMEOUT
        )

    def _start_timeout_task(
        self,
        task_id: str,
        coro,
        timeout: float
    ):
        """启动超时任务"""
        # 取消已存在的同名任务
        if task_id in self._timeout_tasks:
            old_task = self._timeout_tasks[task_id]
            if not old_task.done():
                old_task.cancel()

        async def timeout_wrapper():
            await asyncio.sleep(timeout)
            await coro

        task = asyncio.create_task(timeout_wrapper())
        self._timeout_tasks[task_id] = task

    async def _wait_for_responses(self, state: ChannelState):
        """等待响应超时后继续处理"""
        # 检查是否还在收集状态
        if state.status == ChannelStatus.COLLECTING:
            responded = len(state.responses)
            total = len(state.candidates)
            self._logger.info(
                f"Response timeout for {state.channel_id}, "
                f"received {responded}/{total} responses"
            )
            await self._aggregate_proposals(state)

    async def _handle_offer_response(self, data: Dict[str, Any]):
        """处理Agent的offer响应"""
        channel_id = data.get("channel_id") or data.get("channel")
        agent_id = data.get("agent_id")

        if not channel_id or not agent_id:
            self._logger.warning("Missing channel_id or agent_id in offer_response")
            return

        if channel_id not in self.channels:
            self._logger.warning(f"Unknown channel: {channel_id}")
            return

        state = self.channels[channel_id]

        if state.status not in (ChannelStatus.COLLECTING, ChannelStatus.BROADCASTING):
            self._logger.warning(
                f"Cannot accept response for channel {channel_id} in status {state.status.value}"
            )
            return

        # 记录响应
        decision = data.get("decision", "decline")
        state.responses[agent_id] = {
            "decision": decision,  # participate/decline/conditional
            "contribution": data.get("contribution"),
            "conditions": data.get("conditions", []),
            "reasoning": data.get("reasoning"),
            "capabilities": data.get("capabilities", []),
            "estimated_effort": data.get("estimated_effort"),
            "received_at": datetime.utcnow().isoformat()
        }

        self._logger.info(
            f"Received response from {agent_id} for {channel_id}: {decision}"
        )

        # 发布响应事件
        await self._publish_event("towow.offer.submitted", {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "decision": decision,
            "contribution": data.get("contribution"),
            "round": state.current_round
        })

        # 检查是否收集完毕
        responded = len(state.responses)
        total = len(state.candidates)

        self._logger.debug(f"Responses collected: {responded}/{total}")

        if responded >= total:
            # 取消超时任务
            task_id = f"response_{state.channel_id}"
            if task_id in self._timeout_tasks:
                self._timeout_tasks[task_id].cancel()
                del self._timeout_tasks[task_id]

            await self._aggregate_proposals(state)

    async def _aggregate_proposals(self, state: ChannelState):
        """聚合响应，生成协作方案"""
        if state.status not in (ChannelStatus.COLLECTING, ChannelStatus.BROADCASTING):
            self._logger.debug(f"Skip aggregation, channel status: {state.status.value}")
            return

        state.status = ChannelStatus.AGGREGATING

        # 筛选愿意参与的Agent
        participants = [
            {"agent_id": aid, **resp}
            for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]

        if not participants:
            self._logger.warning(f"No participants for channel {state.channel_id}")
            await self._fail_channel(state, "no_participants")
            return

        self._logger.info(
            f"Aggregating proposals from {len(participants)} participants "
            f"for channel {state.channel_id}"
        )

        # 发布聚合开始事件
        await self._publish_event("towow.aggregation.started", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "participants_count": len(participants),
            "round": state.current_round
        })

        # 调用LLM聚合方案
        proposal = await self._generate_proposal(state, participants)
        state.current_proposal = proposal

        # 分发方案
        await self._distribute_proposal(state)

    async def _generate_proposal(
        self,
        state: ChannelState,
        participants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成协作方案

        基于提示词4：方案聚合
        整合多方贡献，形成结构化的协作方案

        Args:
            state: Channel状态
            participants: 参与者列表（包含其贡献和条件）

        Returns:
            结构化的协作方案
        """
        if not self.llm:
            self._logger.debug("No LLM service, using mock proposal")
            return self._mock_proposal(state, participants)

        demand = state.demand
        surface_demand = demand.get('surface_demand', '')
        deep = demand.get('deep_understanding', {})

        prompt = f"""
# 协作方案生成任务

你是ToWow协作平台的方案聚合系统。你的任务是整合各参与者的贡献和条件，生成一个可执行的协作方案。

## 需求背景

### 原始需求
{surface_demand}

### 需求分析
- **类型**: {deep.get('type', 'general')}
- **动机**: {deep.get('motivation', '未知')}
- **规模**: {json.dumps(deep.get('scale', {}), ensure_ascii=False)}
- **时间线**: {json.dumps(deep.get('timeline', {}), ensure_ascii=False)}
- **资源需求**: {json.dumps(deep.get('resource_requirements', []), ensure_ascii=False)}

## 参与者及其贡献

```json
{json.dumps(participants, ensure_ascii=False, indent=2)}
```

## 当前协商状态
- 当前轮次: 第 {state.current_round} 轮（最多 {state.max_rounds} 轮）
- 参与者数量: {len(participants)} 人

## 方案设计原则

1. **角色明确**：每个参与者都应有明确的角色和职责
2. **条件兼顾**：尽可能满足各参与者提出的条件
3. **时间合理**：考虑各方可用时间，给出合理的时间安排
4. **风险可控**：识别潜在风险并提供应对建议
5. **成功可衡量**：定义清晰的成功标准

## 输出要求

请生成一个结构化的协作方案（JSON格式）：

```json
{{
  "summary": "方案核心摘要（一句话描述这个方案做什么）",
  "objective": "方案目标（要达成的具体成果）",
  "assignments": [
    {{
      "agent_id": "参与者ID",
      "role": "角色名称",
      "responsibility": "具体职责描述（包含要做什么、产出什么）",
      "conditions_addressed": ["已满足的条件列表"],
      "estimated_effort": "预估投入（如：2小时/周、1天等）"
    }}
  ],
  "timeline": {{
    "start_date": "建议开始时间",
    "end_date": "预计完成时间",
    "milestones": [
      {{"name": "里程碑名称", "date": "时间点", "deliverable": "交付物"}}
    ]
  }},
  "collaboration_model": {{
    "communication_channel": "主要沟通方式",
    "meeting_frequency": "会议频率",
    "decision_mechanism": "决策机制"
  }},
  "success_criteria": [
    "成功标准1（可衡量的）",
    "成功标准2"
  ],
  "risks": [
    {{
      "risk": "风险描述",
      "probability": "high/medium/low",
      "mitigation": "应对措施"
    }}
  ],
  "dependencies": ["外部依赖项"],
  "confidence": "high/medium/low",
  "notes": "其他备注说明"
}}
```

## 注意事项
- 确保每个参与者都有明确分工
- 时间安排要考虑各方提出的时间约束
- 方案应该是可执行的，而非泛泛而谈
- 如果某些条件无法满足，在notes中说明原因和替代方案
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是ToWow的方案聚合系统，负责整合多方贡献形成可执行的协作方案。请始终以有效的JSON格式输出。",
                fallback_key="proposal_aggregation"
            )
            return self._parse_proposal(response)
        except Exception as e:
            self._logger.error(f"Proposal generation error: {e}")
            return self._mock_proposal(state, participants)

    def _parse_proposal(self, response: str) -> Dict[str, Any]:
        """解析LLM生成的方案"""
        try:
            # 尝试提取JSON块
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                return json.loads(json_match.group(1))

            # 尝试直接解析
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())

        except json.JSONDecodeError as e:
            self._logger.error(f"JSON parse error: {e}")
        except Exception as e:
            self._logger.error(f"Parse proposal error: {e}")

        return {
            "summary": "方案生成中",
            "assignments": [],
            "confidence": "low",
            "parse_error": True
        }

    def _mock_proposal(
        self,
        state: ChannelState,
        participants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成Mock方案（演示用）"""
        surface_demand = state.demand.get("surface_demand", "未知需求")

        return {
            "summary": f"关于'{surface_demand}'的协作方案",
            "assignments": [
                {
                    "agent_id": p["agent_id"],
                    "role": f"参与者-{i+1}",
                    "responsibility": p.get("contribution", "待分配职责"),
                    "conditions_addressed": p.get("conditions", [])
                }
                for i, p in enumerate(participants[:5])
            ],
            "timeline": "待确定",
            "success_criteria": ["需求被满足", "所有参与者达成共识"],
            "risks": ["方案可能需要多轮调整"],
            "confidence": "medium",
            "is_mock": True
        }

    async def _distribute_proposal(self, state: ChannelState):
        """分发方案给参与者"""
        state.status = ChannelStatus.PROPOSAL_SENT

        # 获取参与者列表
        participant_ids = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]

        self._logger.info(
            f"Distributing proposal to {len(participant_ids)} participants "
            f"for channel {state.channel_id}"
        )

        # 发布方案分发事件
        await self._publish_event("towow.proposal.distributed", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "proposal": state.current_proposal,
            "participants": participant_ids,
            "round": state.current_round
        })

        # 发送给每个参与者
        for agent_id in participant_ids:
            try:
                await self.send_to_agent(agent_id, {
                    "type": "proposal_review",
                    "channel_id": state.channel_id,
                    "demand_id": state.demand_id,
                    "proposal": state.current_proposal,
                    "round": state.current_round,
                    "max_rounds": state.max_rounds
                })
                self._logger.debug(f"Sent proposal to {agent_id}")
            except Exception as e:
                self._logger.error(f"Failed to send proposal to {agent_id}: {e}")

        state.status = ChannelStatus.NEGOTIATING

        # 启动反馈超时
        self._start_timeout_task(
            f"feedback_{state.channel_id}",
            self._wait_for_feedback(state),
            self.FEEDBACK_TIMEOUT
        )

    async def _wait_for_feedback(self, state: ChannelState):
        """等待反馈超时后继续"""
        if state.status == ChannelStatus.NEGOTIATING:
            feedback_count = len(state.proposal_feedback)
            self._logger.info(
                f"Feedback timeout for {state.channel_id}, "
                f"received {feedback_count} feedbacks"
            )
            await self._evaluate_feedback(state)

    async def _handle_proposal_feedback(self, data: Dict[str, Any]):
        """处理方案反馈"""
        channel_id = data.get("channel_id") or data.get("channel")
        agent_id = data.get("agent_id")

        if not channel_id or not agent_id:
            self._logger.warning("Missing channel_id or agent_id in proposal_feedback")
            return

        if channel_id not in self.channels:
            self._logger.warning(f"Unknown channel: {channel_id}")
            return

        state = self.channels[channel_id]

        if state.status != ChannelStatus.NEGOTIATING:
            self._logger.warning(
                f"Cannot accept feedback for channel {channel_id} "
                f"in status {state.status.value}"
            )
            return

        # 记录反馈
        feedback_type = data.get("feedback_type", "accept")
        state.proposal_feedback[agent_id] = {
            "feedback_type": feedback_type,  # accept/reject/negotiate
            "adjustment_request": data.get("adjustment_request"),
            "concerns": data.get("concerns", []),
            "received_at": datetime.utcnow().isoformat()
        }

        self._logger.info(
            f"Feedback from {agent_id} for {channel_id}: {feedback_type}"
        )

        # 发布反馈事件
        await self._publish_event("towow.proposal.feedback", {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "feedback_type": feedback_type,
            "round": state.current_round
        })

        # 检查是否收集完毕
        participants = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]

        if len(state.proposal_feedback) >= len(participants):
            # 取消超时任务
            task_id = f"feedback_{state.channel_id}"
            if task_id in self._timeout_tasks:
                self._timeout_tasks[task_id].cancel()
                del self._timeout_tasks[task_id]

            await self._evaluate_feedback(state)

    async def _evaluate_feedback(self, state: ChannelState):
        """评估反馈，决定下一步"""
        if state.status != ChannelStatus.NEGOTIATING:
            self._logger.debug(f"Skip evaluation, channel status: {state.status.value}")
            return

        # 统计反馈
        accepts = sum(
            1 for f in state.proposal_feedback.values()
            if f.get("feedback_type") == "accept"
        )
        rejects = sum(
            1 for f in state.proposal_feedback.values()
            if f.get("feedback_type") == "reject"
        )
        negotiates = sum(
            1 for f in state.proposal_feedback.values()
            if f.get("feedback_type") == "negotiate"
        )

        total = len(state.proposal_feedback)

        self._logger.info(
            f"Feedback evaluation for {state.channel_id}: "
            f"{accepts} accept, {rejects} reject, {negotiates} negotiate (total: {total})"
        )

        # 发布评估事件
        await self._publish_event("towow.feedback.evaluated", {
            "channel_id": state.channel_id,
            "accepts": accepts,
            "rejects": rejects,
            "negotiates": negotiates,
            "round": state.current_round
        })

        # 决策逻辑
        if total == 0:
            # 没有反馈，使用默认策略
            self._logger.warning(f"No feedback received for {state.channel_id}")
            if state.current_round < state.max_rounds:
                await self._next_round(state)
            else:
                await self._fail_channel(state, "no_feedback")
            return

        # 过半拒绝，协商失败
        if rejects > total / 2:
            await self._fail_channel(state, "majority_reject")
            return

        # 80%以上接受或全部接受，协商成功
        if accepts >= total * 0.8 or (accepts > 0 and negotiates == 0 and rejects == 0):
            await self._finalize_channel(state)
            return

        # 还有调整空间，进入下一轮
        if state.current_round < state.max_rounds:
            await self._next_round(state)
        else:
            # 达到最大轮次，根据情况决定
            if accepts >= rejects:
                await self._finalize_channel(state)
            else:
                await self._fail_channel(state, "max_rounds_reached")

    async def _next_round(self, state: ChannelState):
        """进入下一轮协商"""
        state.current_round += 1
        old_feedback = state.proposal_feedback.copy()
        state.proposal_feedback.clear()

        self._logger.info(
            f"Starting round {state.current_round} for channel {state.channel_id}"
        )

        # 发布新一轮事件
        await self._publish_event("towow.negotiation.round_started", {
            "channel_id": state.channel_id,
            "round": state.current_round,
            "max_rounds": state.max_rounds,
            "previous_feedback": old_feedback
        })

        # 根据反馈调整方案
        if self.llm:
            adjusted_proposal = await self._adjust_proposal(state, old_feedback)
            state.current_proposal = adjusted_proposal
        else:
            # 没有LLM，简单标记轮次
            if state.current_proposal:
                state.current_proposal["round"] = state.current_round
                state.current_proposal["adjusted"] = True

        # 重新分发
        await self._distribute_proposal(state)

    async def _adjust_proposal(
        self,
        state: ChannelState,
        feedback: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        根据反馈调整方案

        基于提示词5：方案调整
        根据参与者反馈优化协作方案

        Args:
            state: Channel状态
            feedback: 参与者反馈字典

        Returns:
            调整后的协作方案
        """
        current_proposal = state.current_proposal or {}
        demand = state.demand
        surface_demand = demand.get('surface_demand', '')

        # 分析反馈
        accept_count = sum(1 for f in feedback.values() if f.get('feedback_type') == 'accept')
        negotiate_count = sum(1 for f in feedback.values() if f.get('feedback_type') == 'negotiate')
        reject_count = sum(1 for f in feedback.values() if f.get('feedback_type') == 'reject')

        # 提取调整请求
        adjustment_requests = [
            {"agent_id": aid, "request": f.get('adjustment_request', ''), "concerns": f.get('concerns', [])}
            for aid, f in feedback.items()
            if f.get('adjustment_request') or f.get('concerns')
        ]

        prompt = f"""
# 方案调整任务

你是ToWow协作平台的方案调整系统。参与者已对当前方案给出反馈，你需要根据反馈优化方案。

## 原始需求
{surface_demand}

## 当前方案
```json
{json.dumps(current_proposal, ensure_ascii=False, indent=2)}
```

## 反馈汇总
- 接受: {accept_count} 人
- 希望调整: {negotiate_count} 人
- 拒绝: {reject_count} 人

## 具体调整请求
```json
{json.dumps(adjustment_requests, ensure_ascii=False, indent=2)}
```

## 完整反馈详情
```json
{json.dumps(feedback, ensure_ascii=False, indent=2)}
```

## 调整原则

1. **优先解决共性问题**：多人提出的问题优先处理
2. **平衡各方利益**：调整不应损害已接受方的利益
3. **保持方案可行**：调整后的方案仍应可执行
4. **透明说明变更**：清晰说明做了什么调整及原因
5. **避免过度妥协**：保持方案的核心价值

## 调整策略建议

根据反馈情况，建议采取以下策略：
{self._get_adjustment_strategy(accept_count, negotiate_count, reject_count, len(feedback))}

## 输出要求

请输出调整后的方案（保持与原方案相同的JSON结构），并在方案末尾添加调整说明：

```json
{{
  // ... 调整后的方案内容 ...
  "adjustment_summary": {{
    "round": {state.current_round},
    "changes_made": [
      {{"aspect": "调整的方面", "before": "调整前", "after": "调整后", "reason": "调整原因"}}
    ],
    "requests_addressed": ["已处理的调整请求"],
    "requests_declined": [
      {{"request": "未处理的请求", "reason": "未处理原因"}}
    ]
  }}
}}
```

请确保调整后的方案仍然是完整的、可执行的协作方案。
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是ToWow的方案调整系统，根据参与者反馈优化协作方案。请以有效的JSON格式输出调整后的完整方案。",
                fallback_key="proposal_adjustment"
            )
            return self._parse_proposal(response)
        except Exception as e:
            self._logger.error(f"Proposal adjustment error: {e}")
            # 返回原方案并标记调整失败
            adjusted = dict(current_proposal)
            adjusted["adjustment_failed"] = True
            adjusted["adjustment_error"] = str(e)
            return adjusted

    def _get_adjustment_strategy(
        self,
        accept_count: int,
        negotiate_count: int,
        reject_count: int,
        total: int
    ) -> str:
        """获取调整策略建议"""
        if total == 0:
            return "- 未收到反馈，建议保持方案不变或主动询问参与者意见"

        accept_ratio = accept_count / total
        negotiate_ratio = negotiate_count / total
        reject_ratio = reject_count / total

        strategies = []

        if accept_ratio >= 0.7:
            strategies.append("- 大多数人已接受，仅需微调以满足少数人的合理要求")
        elif accept_ratio >= 0.5:
            strategies.append("- 过半接受，重点关注negotiate方的具体诉求")
        else:
            strategies.append("- 接受率较低，需要较大幅度调整")

        if negotiate_ratio > 0:
            strategies.append("- 仔细分析调整请求，找出共性问题优先解决")

        if reject_ratio > 0.3:
            strategies.append("- 存在较多拒绝，可能需要重新考虑方案核心框架")
            strategies.append("- 建议主动沟通了解拒绝原因")

        return "\n".join(strategies) if strategies else "- 综合各方反馈，平衡调整"

    async def _finalize_channel(self, state: ChannelState):
        """完成协商"""
        state.status = ChannelStatus.FINALIZED

        self._logger.info(
            f"Channel {state.channel_id} finalized after {state.current_round} rounds"
        )

        # 发布完成事件
        await self._publish_event("towow.proposal.finalized", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "proposal": state.current_proposal,
            "participants": list(state.responses.keys()),
            "rounds": state.current_round,
            "finalized_at": datetime.utcnow().isoformat()
        })

        # 通知Coordinator
        await self.send_to_agent("coordinator", {
            "type": "channel_completed",
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "success": True,
            "proposal": state.current_proposal,
            "participants": [
                aid for aid, resp in state.responses.items()
                if resp.get("decision") in ("participate", "conditional")
            ],
            "rounds": state.current_round
        })

        # 通知所有参与者
        for agent_id in state.responses.keys():
            try:
                await self.send_to_agent(agent_id, {
                    "type": "negotiation_completed",
                    "channel_id": state.channel_id,
                    "success": True,
                    "proposal": state.current_proposal
                })
            except Exception as e:
                self._logger.error(f"Failed to notify {agent_id}: {e}")

    async def _fail_channel(self, state: ChannelState, reason: str):
        """协商失败"""
        state.status = ChannelStatus.FAILED

        self._logger.warning(
            f"Channel {state.channel_id} failed: {reason} (round {state.current_round})"
        )

        # 发布失败事件
        await self._publish_event("towow.negotiation.failed", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "reason": reason,
            "rounds": state.current_round,
            "responses_received": len(state.responses),
            "failed_at": datetime.utcnow().isoformat()
        })

        # 通知Coordinator
        await self.send_to_agent("coordinator", {
            "type": "channel_completed",
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "success": False,
            "failure_reason": reason,
            "rounds": state.current_round
        })

        # 通知所有参与者
        for agent_id in state.responses.keys():
            try:
                await self.send_to_agent(agent_id, {
                    "type": "negotiation_completed",
                    "channel_id": state.channel_id,
                    "success": False,
                    "reason": reason
                })
            except Exception as e:
                self._logger.error(f"Failed to notify {agent_id}: {e}")

    async def _handle_get_status(
        self,
        data: Dict[str, Any],
        context: EventContext
    ):
        """处理获取状态请求"""
        channel_id = data.get("channel_id")

        if channel_id:
            status = self.get_channel_status(channel_id)
            if status:
                await context.reply({"content": status})
            else:
                await context.reply({
                    "content": {
                        "error": "channel_not_found",
                        "channel_id": channel_id
                    }
                })
        else:
            # 返回所有Channel状态
            all_status = {
                cid: self.get_channel_status(cid)
                for cid in self.channels.keys()
            }
            await context.reply({"content": {"channels": all_status}})

    async def _publish_event(self, event_type: str, payload: Dict[str, Any]):
        """发布事件到事件总线"""
        try:
            from events.bus import event_bus
            await event_bus.publish({
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": payload
            })
        except ImportError:
            # 事件总线不可用，仅记录日志
            self._logger.debug(f"Event (no bus): {event_type} - {payload}")
        except Exception as e:
            self._logger.error(f"Failed to publish event {event_type}: {e}")

    def get_channel_status(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """获取Channel状态"""
        if channel_id not in self.channels:
            return None

        state = self.channels[channel_id]
        return {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "status": state.status.value,
            "current_round": state.current_round,
            "max_rounds": state.max_rounds,
            "candidates_count": len(state.candidates),
            "responses_count": len(state.responses),
            "participants": [
                aid for aid, resp in state.responses.items()
                if resp.get("decision") in ("participate", "conditional")
            ],
            "proposal": state.current_proposal,
            "created_at": state.created_at,
            "is_subnet": state.is_subnet
        }

    def get_all_channels(self) -> Dict[str, Dict[str, Any]]:
        """获取所有Channel状态"""
        return {
            cid: self.get_channel_status(cid)
            for cid in self.channels.keys()
        }

    def get_active_channels(self) -> List[str]:
        """获取活跃Channel列表"""
        active_statuses = {
            ChannelStatus.CREATED,
            ChannelStatus.BROADCASTING,
            ChannelStatus.COLLECTING,
            ChannelStatus.AGGREGATING,
            ChannelStatus.PROPOSAL_SENT,
            ChannelStatus.NEGOTIATING
        }
        return [
            cid for cid, state in self.channels.items()
            if state.status in active_statuses
        ]

    # ========== 兼容性方法 ==========

    async def on_channel_message(self, context: ChannelMessageContext) -> None:
        """
        处理Channel内的消息（兼容方法，映射到 on_channel_post）

        Args:
            context: Channel消息上下文
        """
        await self.on_channel_post(context)

    async def _generate_compromise(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        生成妥协方案（当达到最大协商轮次时使用）

        Args:
            channel_id: Channel ID

        Returns:
            妥协方案
        """
        if channel_id not in self.channels:
            return None

        state = self.channels[channel_id]

        if not self.llm:
            # 没有LLM，返回基于已有信息的简化方案
            return {
                "summary": "妥协方案（基于已有共识）",
                "type": "compromise",
                "accepted_assignments": [
                    {
                        "agent_id": aid,
                        "accepted": f.get("feedback_type") == "accept"
                    }
                    for aid, f in state.proposal_feedback.items()
                ],
                "original_proposal": state.current_proposal,
                "rounds_used": state.current_round,
                "note": "由于未能达成完全共识，此为妥协方案"
            }

        prompt = f"""
## 原始需求
{json.dumps(state.demand, ensure_ascii=False, indent=2)}

## 当前方案
{json.dumps(state.current_proposal, ensure_ascii=False, indent=2)}

## 历次反馈
{json.dumps(state.proposal_feedback, ensure_ascii=False, indent=2)}

## 参与者响应
{json.dumps(state.responses, ensure_ascii=False, indent=2)}

## 任务
已经进行了 {state.current_round} 轮协商，达到最大轮次 {state.max_rounds}。
请生成一个妥协方案，尽可能满足各方核心诉求。

妥协原则：
1. 优先保证需求方的核心需求
2. 对于有争议的部分，寻找折中点
3. 明确标注哪些部分是妥协的结果

## 输出格式（JSON）
```json
{{
  "summary": "妥协方案摘要",
  "type": "compromise",
  "assignments": [...],
  "compromises": [
    {{
      "issue": "争议点",
      "resolution": "妥协方案",
      "rationale": "理由"
    }}
  ],
  "unresolved": ["无法妥协的问题"],
  "confidence": "low/medium/high"
}}
```
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是ToWow的协商调解专家，负责在多轮协商未能达成共识时生成妥协方案。",
                fallback_key="compromise_generation"
            )
            return self._parse_proposal(response)
        except Exception as e:
            self._logger.error(f"Compromise generation error: {e}")
            return {
                "summary": "妥协方案生成失败",
                "type": "compromise",
                "error": str(e)
            }

    async def _handle_withdrawal(self, channel_id: str, agent_id: str) -> None:
        """
        处理Agent退出协商

        Args:
            channel_id: Channel ID
            agent_id: 退出的Agent ID
        """
        if channel_id not in self.channels:
            return

        state = self.channels[channel_id]

        # 更新响应状态
        if agent_id in state.responses:
            state.responses[agent_id]["decision"] = "withdrawn"
            state.responses[agent_id]["withdrawn_at"] = datetime.utcnow().isoformat()

        self._logger.info(f"Agent {agent_id} withdrew from channel {channel_id}")

        # 发布退出事件
        await self._publish_event("towow.agent.withdrawn", {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "round": state.current_round
        })

        # 检查是否还有足够的参与者
        remaining_participants = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]

        if len(remaining_participants) == 0:
            await self._fail_channel(state, "all_participants_withdrawn")

