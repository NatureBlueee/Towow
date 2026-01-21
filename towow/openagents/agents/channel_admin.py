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
    max_rounds: int = 3
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

    # 超时配置（秒）
    RESPONSE_TIMEOUT = 60  # 等待响应超时
    FEEDBACK_TIMEOUT = 30  # 等待反馈超时

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
            max_rounds=data.get("max_rounds", 3),
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
        """生成协作方案"""
        if not self.llm:
            self._logger.debug("No LLM service, using mock proposal")
            return self._mock_proposal(state, participants)

        prompt = f"""
## 需求信息
{json.dumps(state.demand, ensure_ascii=False, indent=2)}

## 参与者及其贡献
{json.dumps(participants, ensure_ascii=False, indent=2)}

## 当前协商轮次
第 {state.current_round} 轮（最多 {state.max_rounds} 轮）

## 任务
根据需求和参与者的贡献，生成一个协作方案。方案应该：
1. 明确每个参与者的角色和职责
2. 考虑参与者提出的条件
3. 给出时间安排建议
4. 列出成功标准和潜在风险

## 输出格式（JSON）
```json
{{
  "summary": "方案概述（一句话）",
  "assignments": [
    {{
      "agent_id": "agent-xxx",
      "role": "角色名称",
      "responsibility": "具体职责描述",
      "conditions_addressed": ["已处理的条件"]
    }}
  ],
  "timeline": "时间安排描述",
  "success_criteria": ["成功标准1", "成功标准2"],
  "risks": ["风险1", "风险2"],
  "confidence": "high/medium/low",
  "notes": "其他备注"
}}
```
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是ToWow的方案聚合系统，负责整合多方贡献形成可执行的协作方案。输出必须是有效的JSON格式。",
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
        """根据反馈调整方案"""
        prompt = f"""
## 当前方案
{json.dumps(state.current_proposal, ensure_ascii=False, indent=2)}

## 收到的反馈
{json.dumps(feedback, ensure_ascii=False, indent=2)}

## 任务
根据反馈调整方案，解决参与者的顾虑。

## 输出格式（JSON）
与原方案相同格式，但需要体现调整。
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是ToWow的方案调整系统，根据参与者反馈优化协作方案。",
                fallback_key="proposal_adjustment"
            )
            return self._parse_proposal(response)
        except Exception as e:
            self._logger.error(f"Proposal adjustment error: {e}")
            # 返回原方案
            return state.current_proposal or {}

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
