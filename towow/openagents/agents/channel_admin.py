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
    FORCE_FINALIZED = "force_finalized"  # [v4新增] 强制终结状态
    FAILED = "failed"


@dataclass
class NegotiationPoint:
    """协商要点 - v4新增"""
    aspect: str           # 协商方面
    current_value: str = ""  # 当前值
    desired_value: str = ""  # 期望值
    reason: str = ""      # 原因


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
    # 幂等性控制字段
    proposal_distributed: bool = False  # 方案是否已分发
    gaps_identified: bool = False  # 缺口是否已识别
    subnet_triggered: bool = False  # 子网是否已触发
    finalized_notified: bool = False  # 完成通知是否已发送
    # [v4新增] 基于 message_id 的幂等控制
    processed_message_ids: set = field(default_factory=set)


class ChannelAdminAgent(TowowBaseAgent):
    """
    ChannelAdmin Agent - 管理协商Channel的全生命周期

    状态机流程:
    CREATED -> BROADCASTING -> COLLECTING -> AGGREGATING ->
    PROPOSAL_SENT -> NEGOTIATING -> FINALIZED/FAILED

    支持多轮协商，直到达成共识或超过最大轮次。
    """

    AGENT_TYPE = "channel_admin"

    # H2 Fix: Load MAX_NEGOTIATION_ROUNDS from shared config
    # Can be overridden by TOWOW_MAX_NEGOTIATION_ROUNDS environment variable
    @property
    def MAX_NEGOTIATION_ROUNDS(self) -> int:
        """Maximum negotiation rounds, configurable via environment."""
        from config import MAX_NEGOTIATION_ROUNDS
        return MAX_NEGOTIATION_ROUNDS

    # H2 Fix: Load timeouts from shared config
    @property
    def RESPONSE_TIMEOUT(self) -> int:
        """Response timeout in seconds, configurable via environment."""
        from config import RESPONSE_TIMEOUT
        return RESPONSE_TIMEOUT

    @property
    def FEEDBACK_TIMEOUT(self) -> int:
        """Feedback timeout in seconds, configurable via environment."""
        from config import FEEDBACK_TIMEOUT
        return FEEDBACK_TIMEOUT

    def __init__(self, **kwargs):
        """初始化ChannelAdmin Agent"""
        super().__init__(**kwargs)
        self.channels: Dict[str, ChannelState] = {}
        self._timeout_tasks: Dict[str, asyncio.Task] = {}
        # [T07] StateChecker 实例（延迟初始化）
        self._state_checker: Optional[Any] = None

    async def on_startup(self):
        """Agent启动时调用"""
        await super().on_startup()
        self._logger.info("ChannelAdmin Agent 已启动，准备管理协商 Channel")

        # [T07] 初始化并启动 StateChecker
        try:
            from config import STATE_CHECKER_ENABLED
            if STATE_CHECKER_ENABLED:
                from services.state_checker import StateChecker
                self._state_checker = StateChecker(self)
                await self._state_checker.start()
                self._logger.info("StateChecker 已启动")
        except ImportError as e:
            self._logger.warning(f"StateChecker 未初始化: {e}")
        except Exception as e:
            self._logger.error(f"StateChecker 启动失败: {e}")

    async def on_shutdown(self):
        """Agent关闭时调用"""
        # [T07] 停止 StateChecker
        if self._state_checker:
            try:
                await self._state_checker.stop()
                self._logger.info("StateChecker 已停止")
            except Exception as e:
                self._logger.error(f"StateChecker 停止失败: {e}")
            self._state_checker = None

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
            self._logger.warning(f"Channel {channel_id} 已存在")
            return channel_id

        self._logger.info(f"开始管理 Channel {channel_id}，需求: {demand_id}")

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
            self._logger.warning(f"Channel {channel_id} 未找到")
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

        logger.info("[CHANNEL_ADMIN] on_direct received msg_type=%s", msg_type)

        if msg_type == "create_channel":
            await self._handle_create_channel(data, context)
        elif msg_type == "offer_response":
            await self._handle_offer_response(data)
        elif msg_type == "proposal_feedback":
            await self._handle_proposal_feedback(data)
        elif msg_type == "get_status":
            await self._handle_get_status(data, context)
        elif msg_type == "agent_withdrawn":
            await self._handle_agent_withdrawn(data)
        elif msg_type == "bargain":
            await self._handle_bargain(data)
        elif msg_type == "counter_proposal":
            await self._handle_counter_proposal(data)
        elif msg_type == "kick_agent":
            await self._handle_kick_agent(data)
        else:
            logger.warning("[CHANNEL_ADMIN] Unknown message type: %s", msg_type)

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel消息"""
        await super().on_channel_post(context)
        payload = context.incoming_event.payload
        content = payload.get("content", {})
        data = content if isinstance(content, dict) else payload
        msg_type = data.get("type")

        self._logger.debug(f"在 {context.channel} 收到 Channel 消息类型: {msg_type}")

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

        logger.info("[CHANNEL_ADMIN] _handle_create_channel START channel_id=%s, demand_id=%s",
                    channel_id, demand_id)

        if channel_id in self.channels:
            logger.warning("[CHANNEL_ADMIN] Channel %s already exists", channel_id)
            if context:
                await context.reply({
                    "content": {
                        "type": "error",
                        "error": "channel_exists",
                        "channel_id": channel_id
                    }
                })
            return

        candidates = data.get("candidates", [])
        logger.info("[CHANNEL_ADMIN] Creating channel with %d candidates", len(candidates))

        # 创建Channel状态
        state = ChannelState(
            channel_id=channel_id,
            demand_id=demand_id,
            demand=data.get("demand", {}),
            candidates=candidates,
            max_rounds=data.get("max_rounds", self.MAX_NEGOTIATION_ROUNDS),
            is_subnet=data.get("is_subnet", False),
            parent_channel_id=data.get("parent_channel_id"),
            recursion_depth=data.get("recursion_depth", 0)
        )
        self.channels[channel_id] = state
        logger.info("[CHANNEL_ADMIN] Channel state created, status=%s", state.status.value)

        # 发布Channel创建事件
        logger.info("[CHANNEL_ADMIN] Publishing towow.channel.created event")
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
        logger.info("[CHANNEL_ADMIN] Starting broadcast for channel_id=%s", channel_id)
        await self._broadcast_demand(state)
        logger.info("[CHANNEL_ADMIN] _handle_create_channel DONE channel_id=%s", channel_id)

    async def _broadcast_demand(self, state: ChannelState):
        """广播需求给候选Agent"""
        state.status = ChannelStatus.BROADCASTING

        candidate_ids = [c.get("agent_id") for c in state.candidates if c.get("agent_id")]
        self._logger.info(
            f"正在向 {len(candidate_ids)} 个候选人广播需求，Channel: {state.channel_id}"
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
                self._logger.debug(f"已向 {agent_id} 发送需求邀请")
            except Exception as e:
                self._logger.error(f"向 {agent_id} 发送需求邀请失败: {e}")

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
                f"Channel {state.channel_id} 响应超时，"
                f"已收到 {responded}/{total} 个响应"
            )
            await self._aggregate_proposals(state)

    async def _handle_offer_response(self, data: Dict[str, Any]):
        """
        处理Agent的offer响应

        [v4] 增强功能：
        1. 基于 message_id 的幂等处理
        2. 区分 offer 和 negotiate 两种响应类型
        3. 解析 negotiation_points 协商要点
        """
        channel_id = data.get("channel_id") or data.get("channel")
        agent_id = data.get("agent_id")
        message_id = data.get("message_id")

        if not channel_id or not agent_id:
            self._logger.warning("offer_response 中缺少 channel_id 或 agent_id")
            return

        if channel_id not in self.channels:
            self._logger.warning(f"未知 Channel: {channel_id}")
            return

        state = self.channels[channel_id]

        if state.status not in (ChannelStatus.COLLECTING, ChannelStatus.BROADCASTING):
            self._logger.warning(
                f"Channel {channel_id} 当前状态 {state.status.value} 不接受响应"
            )
            return

        # [v4] 基于 message_id 的幂等检查（优先级高于 agent_id 检查）
        if message_id:
            if message_id in state.processed_message_ids:
                self._logger.info(
                    f"消息 {message_id} 已处理，忽略重复响应 (agent={agent_id})"
                )
                return
            # 记录已处理的消息ID
            state.processed_message_ids.add(message_id)

        # 幂等性检查：检查是否已收到该 agent 的响应（兜底检查）
        if agent_id in state.responses:
            self._logger.warning(
                f"已收到 {agent_id} 对 {channel_id} 的响应，忽略重复响应"
            )
            return

        # [v4] 解析响应类型和协商要点
        response_type = data.get("response_type", "offer")  # 默认为 offer
        decision = data.get("decision", "decline")

        # 解析协商要点（negotiate 类型时使用）
        negotiation_points = []
        if response_type == "negotiate" and data.get("negotiation_points"):
            for point in data.get("negotiation_points", []):
                if isinstance(point, dict):
                    negotiation_points.append({
                        "aspect": point.get("aspect", ""),
                        "current_value": point.get("current_value", ""),
                        "desired_value": point.get("desired_value", ""),
                        "reason": point.get("reason", "")
                    })

        # 记录响应
        state.responses[agent_id] = {
            "decision": decision,  # participate/decline/conditional
            "response_type": response_type,  # [v4] offer/negotiate
            "contribution": data.get("contribution"),
            "conditions": data.get("conditions", []),
            "reasoning": data.get("reasoning"),
            "decline_reason": data.get("decline_reason", ""),  # 拒绝原因
            "capabilities": data.get("capabilities", []),
            "estimated_effort": data.get("estimated_effort"),
            "negotiation_points": negotiation_points,  # [v4] 协商要点
            "confidence": data.get("confidence", 50),  # [v4] 置信度
            "message_id": message_id,  # [v4] 消息ID
            "received_at": datetime.utcnow().isoformat()
        }

        self._logger.info(
            f"收到 {agent_id} 对 {channel_id} 的响应: "
            f"type={response_type}, decision={decision}"
        )

        # 获取 agent 的显示名称
        display_name = data.get("display_name", agent_id)
        for candidate in state.candidates:
            if candidate.get("agent_id") == agent_id:
                display_name = candidate.get("display_name", display_name)
                break

        # [v4] 发布响应事件（包含 response_type）
        event_payload = {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "display_name": display_name,
            "response_type": response_type,
            "decision": decision,
            "contribution": data.get("contribution", ""),
            "reasoning": data.get("reasoning", ""),
            "decline_reason": data.get("decline_reason", ""),
            "conditions": data.get("conditions", []),
            "round": state.current_round,
            "timestamp": datetime.utcnow().isoformat()
        }

        # negotiate 类型时添加协商摘要
        if response_type == "negotiate" and negotiation_points:
            event_payload["negotiation_summary"] = "; ".join(
                f"{p['aspect']}: 期望 {p['desired_value']}"
                for p in negotiation_points if p.get("aspect")
            )

        await self._publish_event("towow.offer.submitted", event_payload)

        # 检查是否收集完毕
        responded = len(state.responses)
        total = len(state.candidates)

        self._logger.debug(f"已收集响应: {responded}/{total}")

        if responded >= total:
            # 取消超时任务
            task_id = f"response_{state.channel_id}"
            if task_id in self._timeout_tasks:
                self._timeout_tasks[task_id].cancel()
                del self._timeout_tasks[task_id]

            await self._aggregate_proposals(state)

    async def _aggregate_proposals(self, state: ChannelState):
        """
        聚合响应，生成协作方案

        [v4] 区分处理：
        - offer: 直接纳入方案
        - negotiate: 标注协商要点，可能影响角色分配
        """
        logger.info("[CHANNEL_ADMIN] _aggregate_proposals START channel_id=%s, status=%s",
                    state.channel_id, state.status.value)

        # 幂等性检查：只允许从 COLLECTING 或 BROADCASTING 状态进入
        if state.status not in (ChannelStatus.COLLECTING, ChannelStatus.BROADCASTING):
            logger.warning("[CHANNEL_ADMIN] Skipping aggregation, channel status=%s (not COLLECTING/BROADCASTING)",
                           state.status.value)
            return

        # 立即更新状态，防止并发调用
        state.status = ChannelStatus.AGGREGATING
        logger.info("[CHANNEL_ADMIN] Channel status changed to AGGREGATING")

        # [v4] 分类响应：区分 offer、negotiate 和 decline
        offers = []
        negotiations = []
        declines = []

        for aid, resp in state.responses.items():
            response_type = resp.get("response_type", "offer")
            decision = resp.get("decision")

            # 获取显示名称
            display_name = aid
            for candidate in state.candidates:
                if candidate.get("agent_id") == aid:
                    display_name = candidate.get("display_name", aid)
                    break

            participant_data = {
                "agent_id": aid,
                "display_name": display_name,
                "decision": decision,
                "contribution": resp.get("contribution"),
                "conditions": resp.get("conditions", []),
                "capabilities": resp.get("capabilities", []),
                "confidence": resp.get("confidence", 50),
                "negotiation_points": resp.get("negotiation_points", [])
            }

            if decision == "decline":
                declines.append(participant_data)
            elif response_type == "negotiate":
                negotiations.append(participant_data)
            else:  # offer
                offers.append(participant_data)

        logger.info(
            "[CHANNEL_ADMIN] Response classification: "
            f"offers={len(offers)}, negotiations={len(negotiations)}, declines={len(declines)}"
        )

        if not offers and not negotiations:
            logger.warning("[CHANNEL_ADMIN] No participants in channel_id=%s", state.channel_id)
            await self._fail_channel(state, "no_participants")
            return

        logger.info("[CHANNEL_ADMIN] Aggregating responses for channel_id=%s",
                    state.channel_id)

        # 发布聚合开始事件
        await self._publish_event("towow.aggregation.started", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "offers_count": len(offers),
            "negotiations_count": len(negotiations),
            "declines_count": len(declines),
            "round": state.current_round
        })

        # 调用LLM聚合方案
        logger.info("[CHANNEL_ADMIN] Generating proposal via LLM")
        proposal = await self._generate_proposal_v4(state, offers, negotiations, declines)
        state.current_proposal = proposal
        logger.info("[CHANNEL_ADMIN] Proposal generated, summary=%s",
                    proposal.get("summary", "")[:50] if proposal else "None")

        # 分发方案
        logger.info("[CHANNEL_ADMIN] Distributing proposal")
        await self._distribute_proposal(state)
        logger.info("[CHANNEL_ADMIN] _aggregate_proposals DONE channel_id=%s", state.channel_id)

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
        logger.info("[CHANNEL_ADMIN] _generate_proposal START channel_id=%s, participants=%d",
                    state.channel_id, len(participants))

        if not self.llm:
            logger.debug("[CHANNEL_ADMIN] No LLM service, using mock proposal")
            return self._mock_proposal(state, participants)

        # 构建提示词
        prompt = self._build_proposal_prompt(state, participants)

        try:
            logger.info("[CHANNEL_ADMIN] Calling LLM for proposal generation")
            response = await self.llm.complete(
                prompt=prompt,
                system=self._get_proposal_system_prompt(),
                fallback_key="proposal_aggregation",
                max_tokens=4000,
                temperature=0.4
            )
            logger.info("[CHANNEL_ADMIN] LLM response received, length=%d", len(response) if response else 0)

            proposal = self._parse_proposal(response)

            # 验证方案完整性
            proposal = self._validate_and_enhance_proposal(proposal, participants)

            logger.info("[CHANNEL_ADMIN] _generate_proposal DONE, assignments=%d",
                        len(proposal.get('assignments', [])))

            return proposal

        except Exception as e:
            logger.error("[CHANNEL_ADMIN] _generate_proposal FAILED: %s", str(e), exc_info=True)
            return self._mock_proposal(state, participants)

    def _get_proposal_system_prompt(self) -> str:
        """获取方案生成系统提示词"""
        return """你是 ToWow 协作平台的方案聚合系统。

你的任务是整合各参与者的贡献和条件，生成一个可执行的协作方案。

方案设计原则：
1. 角色明确：每个参与者都应有明确的角色和职责
2. 条件兼顾：尽可能满足各参与者提出的条件
3. 时间合理：考虑各方可用时间，给出合理的时间安排
4. 风险可控：识别潜在风险并提供应对建议
5. 成功可衡量：定义清晰的成功标准

始终以有效的 JSON 格式输出。"""

    def _build_proposal_prompt(
        self,
        state: ChannelState,
        participants: List[Dict[str, Any]]
    ) -> str:
        """构建方案生成提示词"""
        demand = state.demand
        surface_demand = demand.get('surface_demand', '未说明')
        deep = demand.get('deep_understanding', {})

        # 格式化参与者信息
        participant_details = []
        for p in participants:
            detail = {
                "agent_id": p.get("agent_id"),
                "display_name": p.get("display_name", p.get("agent_id")),
                "decision": p.get("decision"),
                "contribution": p.get("contribution", "未说明"),
                "conditions": p.get("conditions", []),
                "capabilities": p.get("capabilities", [])
            }
            participant_details.append(detail)

        return f"""
# 协作方案生成任务

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

共 {len(participants)} 位参与者：

```json
{json.dumps(participant_details, ensure_ascii=False, indent=2)}
```

## 当前协商状态
- 当前轮次: 第 {state.current_round} 轮（最多 {state.max_rounds} 轮）

## 输出要求

请生成一个结构化的协作方案（JSON 格式）：

```json
{{
  "summary": "方案核心摘要（一句话描述这个方案做什么）",
  "objective": "方案目标（要达成的具体成果）",
  "assignments": [
    {{
      "agent_id": "参与者 ID",
      "display_name": "参与者名称",
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
  "gaps": ["方案中可能存在的缺口"],
  "confidence": "high/medium/low",
  "notes": "其他备注说明"
}}
```

## 注意事项
- 确保每个参与者都有明确分工
- 时间安排要考虑各方提出的时间约束
- 方案应该是可执行的，而非泛泛而谈
- 如果某些条件无法满足，在 notes 中说明原因和替代方案
"""

    def _validate_and_enhance_proposal(
        self,
        proposal: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        验证并增强方案

        确保方案结构完整，补充缺失字段

        Args:
            proposal: LLM 生成的方案
            participants: 参与者列表

        Returns:
            验证并增强后的方案
        """
        # 确保 assignments 包含所有参与者
        assigned_ids = {a.get("agent_id") for a in proposal.get("assignments", [])}
        participant_ids = {p.get("agent_id") for p in participants}

        # 补充未分配的参与者
        for p in participants:
            if p.get("agent_id") not in assigned_ids:
                proposal.setdefault("assignments", []).append({
                    "agent_id": p.get("agent_id"),
                    "display_name": p.get("display_name", p.get("agent_id")),
                    "role": "待分配",
                    "responsibility": p.get("contribution", "待确定"),
                    "conditions_addressed": p.get("conditions", []),
                    "estimated_effort": "待评估"
                })

        # 为每个 assignment 补充 display_name（如果缺失）
        for assignment in proposal.get("assignments", []):
            if not assignment.get("display_name"):
                # 从参与者列表中查找
                agent_id = assignment.get("agent_id")
                for p in participants:
                    if p.get("agent_id") == agent_id:
                        assignment["display_name"] = p.get("display_name", agent_id)
                        break
                else:
                    assignment["display_name"] = agent_id

        # 确保必要字段存在
        proposal.setdefault("summary", "协作方案")
        proposal.setdefault("objective", "完成协作需求")
        proposal.setdefault("timeline", {
            "start_date": "待定",
            "end_date": "待定",
            "milestones": [{"name": "启动", "date": "待定", "deliverable": "项目启动"}]
        })

        # 确保 timeline 中有 milestones
        if "timeline" in proposal:
            if not proposal["timeline"].get("milestones"):
                proposal["timeline"]["milestones"] = [
                    {"name": "启动", "date": "待定", "deliverable": "项目启动"}
                ]

        proposal.setdefault("collaboration_model", {
            "communication_channel": "微信群",
            "meeting_frequency": "按需",
            "decision_mechanism": "协商一致"
        })
        proposal.setdefault("success_criteria", ["需求被满足", "参与者达成共识"])
        proposal.setdefault("risks", [])
        proposal.setdefault("gaps", [])
        proposal.setdefault("confidence", "medium")

        # 确保 success_criteria 至少有 2 个
        if len(proposal.get("success_criteria", [])) < 2:
            existing = proposal.get("success_criteria", [])
            defaults = ["需求被满足", "参与者达成共识", "按时完成交付"]
            for d in defaults:
                if d not in existing and len(existing) < 2:
                    existing.append(d)
            proposal["success_criteria"] = existing

        return proposal

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
            self._logger.error(f"JSON 解析错误: {e}")
        except Exception as e:
            self._logger.error(f"解析方案错误: {e}")

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

        # 构建完整的 assignments，包含 display_name
        assignments = []
        for i, p in enumerate(participants[:5]):
            assignments.append({
                "agent_id": p.get("agent_id"),
                "display_name": p.get("display_name", p.get("agent_id")),
                "role": f"参与者-{i+1}",
                "responsibility": p.get("contribution", "待分配职责"),
                "conditions_addressed": p.get("conditions", []),
                "estimated_effort": "待评估"
            })

        return {
            "summary": f"关于'{surface_demand}'的协作方案",
            "objective": f"完成 {surface_demand}",
            "assignments": assignments,
            "timeline": {
                "start_date": "待定",
                "end_date": "待定",
                "milestones": [
                    {"name": "启动会议", "date": "待定", "deliverable": "项目启动，明确分工"},
                    {"name": "执行阶段", "date": "待定", "deliverable": "各参与者完成各自任务"}
                ]
            },
            "collaboration_model": {
                "communication_channel": "微信群",
                "meeting_frequency": "按需",
                "decision_mechanism": "协商一致"
            },
            "success_criteria": [
                "需求被满足",
                "所有参与者达成共识",
                "按时完成交付"
            ],
            "risks": [
                {
                    "risk": "方案可能需要多轮调整",
                    "probability": "medium",
                    "mitigation": "保持沟通，及时调整"
                }
            ],
            "gaps": [],
            "confidence": "medium",
            "notes": "此为模拟方案，用于演示",
            "is_mock": True
        }

    # ========== [v4] 新增方法 ==========

    async def _generate_proposal_v4(
        self,
        state: ChannelState,
        offers: List[Dict[str, Any]],
        negotiations: List[Dict[str, Any]],
        declines: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        [v4] 生成协作方案 - 区分 offer 和 negotiate

        Args:
            state: Channel状态
            offers: offer 类型响应列表
            negotiations: negotiate 类型响应列表
            declines: decline 响应列表

        Returns:
            结构化的协作方案
        """
        logger.info(
            "[CHANNEL_ADMIN] _generate_proposal_v4 START channel_id=%s, "
            "offers=%d, negotiations=%d, declines=%d",
            state.channel_id, len(offers), len(negotiations), len(declines)
        )

        # 合并所有参与者（用于降级方案）
        all_participants = offers + negotiations

        if not self.llm:
            logger.debug("[CHANNEL_ADMIN] No LLM service, using fallback proposal")
            return self._get_fallback_proposal_v4(state, offers, negotiations)

        # 构建 v4 聚合提示词
        prompt = self._build_aggregation_prompt_v4(
            demand=state.demand,
            offers=offers,
            negotiations=negotiations,
            declines=declines,
            current_round=state.current_round,
            max_rounds=state.max_rounds
        )

        try:
            logger.info("[CHANNEL_ADMIN] Calling LLM for v4 proposal generation")
            response = await self.llm.complete(
                prompt=prompt,
                system=self._get_aggregation_system_prompt_v4(),
                fallback_key="proposal_aggregation",
                max_tokens=4000,
                temperature=0.4
            )
            logger.info(
                "[CHANNEL_ADMIN] LLM response received, length=%d",
                len(response) if response else 0
            )

            proposal = self._parse_proposal(response)

            # 验证方案完整性
            proposal = self._validate_and_enhance_proposal_v4(
                proposal, offers, negotiations
            )

            logger.info(
                "[CHANNEL_ADMIN] _generate_proposal_v4 DONE, assignments=%d",
                len(proposal.get('assignments', []))
            )

            return proposal

        except Exception as e:
            logger.error(
                "[CHANNEL_ADMIN] _generate_proposal_v4 FAILED: %s",
                str(e), exc_info=True
            )
            return self._get_fallback_proposal_v4(state, offers, negotiations)

    def _get_aggregation_system_prompt_v4(self) -> str:
        """[v4] 获取聚合系统提示词"""
        return """你是 ToWow 协作平台的方案聚合系统。

你的任务是根据参与者的响应，设计一个完整的协作方案。

## 响应类型说明
- **offer**: 参与者愿意直接贡献，可以直接分配角色
- **negotiate**: 参与者希望协商条件，需要考虑其诉求并尝试满足

## 方案设计原则
1. **角色明确**: 每个参与者都应有明确的角色和职责
2. **诉求兼顾**: 优先处理 negotiate 响应中的合理诉求
3. **分配公平**: 根据能力和贡献合理分配任务
4. **缺口识别**: 发现能力空白，标注需要填补的缺口
5. **可执行性**: 方案应具体可行，而非泛泛而谈

始终以有效的 JSON 格式输出。"""

    def _build_aggregation_prompt_v4(
        self,
        demand: Dict[str, Any],
        offers: List[Dict[str, Any]],
        negotiations: List[Dict[str, Any]],
        declines: List[Dict[str, Any]],
        current_round: int,
        max_rounds: int
    ) -> str:
        """
        [v4] 构建聚合提示词 - 区分 offer 和 negotiate

        Args:
            demand: 需求信息
            offers: offer 类型响应
            negotiations: negotiate 类型响应
            declines: decline 响应
            current_round: 当前轮次
            max_rounds: 最大轮次

        Returns:
            聚合提示词
        """
        surface_demand = demand.get('surface_demand', '未说明')
        deep = demand.get('deep_understanding', {})

        # 格式化 offer 响应
        offers_text = json.dumps([
            {
                "agent_id": o.get("agent_id"),
                "display_name": o.get("display_name"),
                "decision": o.get("decision"),
                "contribution": o.get("contribution"),
                "conditions": o.get("conditions", []),
                "confidence": o.get("confidence", 50)
            }
            for o in offers
        ], ensure_ascii=False, indent=2)

        # 格式化 negotiate 响应
        negotiations_text = json.dumps([
            {
                "agent_id": n.get("agent_id"),
                "display_name": n.get("display_name"),
                "decision": n.get("decision"),
                "contribution": n.get("contribution"),
                "negotiation_points": [
                    {
                        "aspect": p.get("aspect"),
                        "current_value": p.get("current_value"),
                        "desired_value": p.get("desired_value"),
                        "reason": p.get("reason")
                    }
                    for p in n.get("negotiation_points", [])
                ]
            }
            for n in negotiations
        ], ensure_ascii=False, indent=2)

        return f"""
# 协作方案聚合任务（v4）

## 需求信息
- **表面需求**: {surface_demand}
- **深层理解**: {json.dumps(deep, ensure_ascii=False)}
- **能力标签**: {demand.get('capability_tags', [])}

## 响应汇总

### 愿意参与的响应（offer 类型）- 共 {len(offers)} 人
{offers_text}

### 希望协商的响应（negotiate 类型）- 共 {len(negotiations)} 人
{negotiations_text}

### 拒绝参与
共 {len(declines)} 人拒绝参与

## 当前协商状态
- 当前轮次: 第 {current_round} 轮（最多 {max_rounds} 轮）

## 你的任务
1. 根据 **offer** 响应直接分配角色和职责
2. 分析 **negotiate** 响应中的协商要点，尽量满足合理诉求
3. 如果无法满足某些诉求，在 notes 中说明原因
4. 识别可能的缺口（能力不足的地方）
5. 生成完整的协作方案

## 输出格式 (JSON)
```json
{{
  "summary": "方案一句话描述",
  "objective": "协作目标",
  "assignments": [
    {{
      "agent_id": "agent_001",
      "display_name": "小王",
      "role": "场地负责人",
      "responsibility": "负责场地预订和布置",
      "dependencies": [],
      "is_confirmed": true,
      "notes": "需要确认具体时间"
    }}
  ],
  "timeline": {{
    "start_date": "2026-02-01",
    "end_date": "2026-02-15",
    "milestones": [
      {{"name": "场地确认", "date": "2026-02-03", "deliverable": "场地预订完成"}}
    ]
  }},
  "collaboration_model": {{
    "communication_channel": "微信群",
    "meeting_frequency": "每周一次",
    "decision_mechanism": "协商一致"
  }},
  "success_criteria": [
    "成功标准1（可衡量的）",
    "成功标准2"
  ],
  "rationale": "方案设计理由",
  "negotiation_handling": {{
    "addressed": [
      {{"agent_id": "xxx", "aspect": "时间", "resolution": "调整为周末"}}
    ],
    "declined": [
      {{"agent_id": "xxx", "aspect": "报酬", "reason": "超出预算"}}
    ]
  }},
  "gaps": [
    {{
      "capability": "活动主持",
      "description": "缺少主持人",
      "severity": "medium",
      "suggestion": "建议招募或外聘"
    }}
  ],
  "confidence": "high" | "medium" | "low"
}}
```

请返回 JSON 格式结果：
"""

    def _validate_and_enhance_proposal_v4(
        self,
        proposal: Dict[str, Any],
        offers: List[Dict[str, Any]],
        negotiations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        [v4] 验证并增强方案

        Args:
            proposal: LLM 生成的方案
            offers: offer 响应列表
            negotiations: negotiate 响应列表

        Returns:
            验证并增强后的方案
        """
        all_participants = offers + negotiations

        # 确保 assignments 包含所有参与者
        assigned_ids = {a.get("agent_id") for a in proposal.get("assignments", [])}

        # 补充未分配的参与者
        for p in all_participants:
            agent_id = p.get("agent_id")
            if agent_id not in assigned_ids:
                is_negotiate = p in negotiations
                proposal.setdefault("assignments", []).append({
                    "agent_id": agent_id,
                    "display_name": p.get("display_name", agent_id),
                    "role": "待分配",
                    "responsibility": p.get("contribution", "待确定"),
                    "dependencies": [],
                    "is_confirmed": not is_negotiate,  # negotiate 类型标记为未确认
                    "notes": "协商中" if is_negotiate else ""
                })

        # 为每个 assignment 补充 display_name（如果缺失）
        for assignment in proposal.get("assignments", []):
            if not assignment.get("display_name"):
                agent_id = assignment.get("agent_id")
                for p in all_participants:
                    if p.get("agent_id") == agent_id:
                        assignment["display_name"] = p.get("display_name", agent_id)
                        break
                else:
                    assignment["display_name"] = agent_id

        # 确保必要字段存在
        proposal.setdefault("summary", "协作方案")
        proposal.setdefault("objective", "完成协作需求")
        proposal.setdefault("timeline", {
            "start_date": "待定",
            "end_date": "待定",
            "milestones": [{"name": "启动", "date": "待定", "deliverable": "项目启动"}]
        })

        if "timeline" in proposal:
            if not proposal["timeline"].get("milestones"):
                proposal["timeline"]["milestones"] = [
                    {"name": "启动", "date": "待定", "deliverable": "项目启动"}
                ]

        proposal.setdefault("collaboration_model", {
            "communication_channel": "微信群",
            "meeting_frequency": "按需",
            "decision_mechanism": "协商一致"
        })
        proposal.setdefault("success_criteria", ["需求被满足", "参与者达成共识"])
        proposal.setdefault("risks", [])
        proposal.setdefault("gaps", [])
        proposal.setdefault("confidence", "medium")
        proposal.setdefault("rationale", "基于参与者贡献设计")

        # 确保 negotiation_handling 存在
        proposal.setdefault("negotiation_handling", {
            "addressed": [],
            "declined": []
        })

        return proposal

    def _get_fallback_proposal_v4(
        self,
        state: ChannelState,
        offers: List[Dict[str, Any]],
        negotiations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        [v4] 降级方案（LLM 失败时）

        简单合并所有 offer 和 negotiate 响应

        Args:
            state: Channel 状态
            offers: offer 响应列表
            negotiations: negotiate 响应列表

        Returns:
            降级方案
        """
        surface_demand = state.demand.get("surface_demand", "未知需求")

        assignments = []

        # 处理 offer 响应
        for i, o in enumerate(offers[:5]):
            assignments.append({
                "agent_id": o.get("agent_id"),
                "display_name": o.get("display_name", o.get("agent_id")),
                "role": f"参与者-{i+1}",
                "responsibility": o.get("contribution") or "待确认",
                "dependencies": [],
                "is_confirmed": True,
                "notes": ""
            })

        # 处理 negotiate 响应
        for i, n in enumerate(negotiations[:3]):
            negotiation_summary = ""
            if n.get("negotiation_points"):
                points = n.get("negotiation_points", [])
                negotiation_summary = "; ".join(
                    f"{p.get('aspect', '?')}: 期望{p.get('desired_value', '?')}"
                    for p in points[:2]
                )

            assignments.append({
                "agent_id": n.get("agent_id"),
                "display_name": n.get("display_name", n.get("agent_id")),
                "role": f"待协商参与者-{i+1}",
                "responsibility": n.get("contribution") or "待确认",
                "dependencies": [],
                "is_confirmed": False,  # negotiate 类型标记为未确认
                "notes": f"协商要点: {negotiation_summary}" if negotiation_summary else "待协商"
            })

        return {
            "summary": f"关于'{surface_demand}'的协作方案（降级响应）",
            "objective": f"完成 {surface_demand}",
            "assignments": assignments,
            "timeline": {
                "start_date": "待定",
                "end_date": "待定",
                "milestones": [
                    {"name": "启动", "date": "待定", "deliverable": "项目启动"}
                ]
            },
            "collaboration_model": {
                "communication_channel": "微信群",
                "meeting_frequency": "按需",
                "decision_mechanism": "协商一致"
            },
            "success_criteria": ["需求被满足", "参与者达成共识"],
            "rationale": "系统繁忙，使用降级方案",
            "negotiation_handling": {
                "addressed": [],
                "declined": []
            },
            "gaps": [],
            "confidence": "low",
            "notes": "此为降级响应，LLM服务暂时不可用",
            "is_fallback": True
        }

    async def _distribute_proposal(self, state: ChannelState):
        """
        分发方案给参与者

        [v4] 更新：
        - 同时分发给 offer 和 negotiate 类型的参与者
        - 在发送消息中包含该参与者的具体分配信息
        """
        # 幂等性检查：检查是否已分发过本轮方案
        if state.proposal_distributed and state.status == ChannelStatus.NEGOTIATING:
            logger.warning("[CHANNEL_ADMIN] Proposal already distributed for channel=%s round=%d, skipping",
                           state.channel_id, state.current_round)
            return

        state.status = ChannelStatus.PROPOSAL_SENT
        state.proposal_distributed = True  # 标记本轮已分发

        # [v4] 获取所有参与者（包括 negotiate 类型）
        participant_ids = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]

        self._logger.info(
            f"正在向 {len(participant_ids)} 个参与者分发方案，"
            f"Channel: {state.channel_id}"
        )

        # 构建 proposal ID（如果不存在）
        proposal = state.current_proposal or {}
        if "proposal_id" not in proposal:
            proposal["proposal_id"] = f"prop-{state.channel_id[:8]}-r{state.current_round}"

        # 获取 assignments 映射（agent_id -> assignment）
        assignments_map = {}
        for assignment in proposal.get("assignments", []):
            aid = assignment.get("agent_id")
            if aid:
                assignments_map[aid] = assignment

        # [v4] 发布方案分发事件（包含更多信息）
        await self._publish_event("towow.proposal.distributed", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "proposal_id": proposal.get("proposal_id"),
            "summary": proposal.get("summary", ""),
            "participants_count": len(participant_ids),
            "has_gaps": len(proposal.get("gaps", [])) > 0,
            "version": state.current_round,
            "round": state.current_round,
            "timestamp": datetime.utcnow().isoformat()
        })

        # [v4] 发送给每个参与者，包含其具体分配
        for agent_id in participant_ids:
            try:
                # 获取该参与者的分配信息
                your_assignment = assignments_map.get(agent_id)

                message = {
                    "type": "proposal_review",
                    "channel_id": state.channel_id,
                    "demand_id": state.demand_id,
                    "proposal": {
                        "proposal_id": proposal.get("proposal_id"),
                        "summary": proposal.get("summary"),
                        "objective": proposal.get("objective"),
                        "version": state.current_round,
                        "confidence": proposal.get("confidence", "medium"),
                        "assignments": proposal.get("assignments", []),
                        "timeline": proposal.get("timeline", {}),
                        "gaps": proposal.get("gaps", [])
                    },
                    "round": state.current_round,
                    "max_rounds": state.max_rounds
                }

                # 如果有该参与者的分配，添加到消息中
                if your_assignment:
                    message["your_assignment"] = {
                        "role": your_assignment.get("role", "待分配"),
                        "responsibility": your_assignment.get("responsibility", ""),
                        "dependencies": your_assignment.get("dependencies", []),
                        "is_confirmed": your_assignment.get("is_confirmed", True),
                        "notes": your_assignment.get("notes", "")
                    }

                await self.send_to_agent(agent_id, message)
                self._logger.debug(f"已向 {agent_id} 发送方案")
            except Exception as e:
                self._logger.error(f"向 {agent_id} 发送方案失败: {e}")

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
                f"Channel {state.channel_id} 反馈超时，"
                f"已收到 {feedback_count} 个反馈"
            )
            await self._evaluate_feedback(state)

    async def _handle_proposal_feedback(self, data: Dict[str, Any]):
        """处理方案反馈"""
        channel_id = data.get("channel_id") or data.get("channel")
        agent_id = data.get("agent_id")

        if not channel_id or not agent_id:
            self._logger.warning("proposal_feedback 中缺少 channel_id 或 agent_id")
            return

        if channel_id not in self.channels:
            self._logger.warning(f"未知 Channel: {channel_id}")
            return

        state = self.channels[channel_id]

        # 严格状态检查：只接受 NEGOTIATING 状态的反馈
        if state.status != ChannelStatus.NEGOTIATING:
            self._logger.warning(
                f"Channel {channel_id} 当前状态 {state.status.value} 不接受反馈 (需要 NEGOTIATING)"
            )
            return

        # 幂等性检查：检查是否已收到该 agent 的反馈
        if agent_id in state.proposal_feedback:
            self._logger.warning(
                f"已收到 {agent_id} 对 {channel_id} 的反馈，忽略重复反馈"
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
            f"收到 {agent_id} 对 {channel_id} 的反馈: {feedback_type}"
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
        """
        [v4] 评估反馈，决定下一步

        三档阈值决策逻辑：
        - >= 80% 接受 → FINALIZED（协商成功）
        - < 50% 接受（即 >= 50% 拒绝/退出）→ FAILED（协商失败）
        - 50%-80% 接受 且 round < max_rounds → 下一轮
        - 第 max_rounds 轮后 → 强制终结（FORCE_FINALIZED）

        支持的反馈类型：
        - accept: 接受方案
        - reject: 拒绝方案
        - withdraw: 退出协商
        - negotiate: 希望继续协商
        """
        # 从配置加载阈值
        from config import ACCEPT_THRESHOLD_HIGH, ACCEPT_THRESHOLD_LOW

        # 严格状态检查：防止重复评估
        if state.status != ChannelStatus.NEGOTIATING:
            self._logger.warning(f"跳过评估，Channel 状态: {state.status.value} (需要 NEGOTIATING)")
            return

        # 统计反馈
        total = len(state.proposal_feedback)
        if total == 0:
            self._logger.warning(f"Channel {state.channel_id} 未收到反馈")
            if state.current_round < state.max_rounds:
                await self._next_round(state)
            else:
                await self._fail_channel(state, "no_feedback")
            return

        # 分类统计（支持 withdraw 类型）
        accepts = sum(
            1 for f in state.proposal_feedback.values()
            if f.get("feedback_type") == "accept"
        )
        rejects = sum(
            1 for f in state.proposal_feedback.values()
            if f.get("feedback_type") == "reject"
        )
        withdraws = sum(
            1 for f in state.proposal_feedback.values()
            if f.get("feedback_type") == "withdraw"
        )
        negotiates = sum(
            1 for f in state.proposal_feedback.values()
            if f.get("feedback_type") == "negotiate"
        )

        # 计算比率
        accept_rate = accepts / total
        # reject + withdraw 都算作不接受
        reject_rate = (rejects + withdraws) / total

        self._logger.info(
            f"Channel {state.channel_id} 反馈评估 (轮次 {state.current_round}/{state.max_rounds}): "
            f"接受={accepts} ({accept_rate:.0%}), "
            f"拒绝={rejects}, 退出={withdraws} (合计拒绝率 {reject_rate:.0%}), "
            f"协商={negotiates} (共 {total} 人)"
        )

        # 决定决策结果
        decision = self._determine_decision(
            accept_rate=accept_rate,
            reject_rate=reject_rate,
            negotiates=negotiates,
            current_round=state.current_round,
            max_rounds=state.max_rounds,
            threshold_high=ACCEPT_THRESHOLD_HIGH,
            threshold_low=ACCEPT_THRESHOLD_LOW
        )

        # 发布评估事件（包含 decision）
        await self._publish_event("towow.feedback.evaluated", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "accepts": accepts,
            "rejects": rejects,
            "withdraws": withdraws,
            "negotiates": negotiates,
            "total": total,
            "accept_rate": accept_rate,
            "reject_rate": reject_rate,
            "decision": decision,
            "round": state.current_round,
            "max_rounds": state.max_rounds,
            "threshold_high": ACCEPT_THRESHOLD_HIGH,
            "threshold_low": ACCEPT_THRESHOLD_LOW
        })

        # 执行决策
        if decision == "finalized":
            self._logger.info(f"Channel {state.channel_id} 达到 {ACCEPT_THRESHOLD_HIGH:.0%} 接受率，协商成功")
            await self._finalize_channel(state)

        elif decision == "failed":
            self._logger.info(f"Channel {state.channel_id} 拒绝/退出率超过 {ACCEPT_THRESHOLD_LOW:.0%}，协商失败")
            await self._fail_channel(state, "majority_reject")

        elif decision == "force_finalized":
            self._logger.info(f"Channel {state.channel_id} 达到最大轮次 {state.max_rounds}，强制终结")
            await self._force_finalize_channel(state)

        elif decision == "next_round":
            self._logger.info(f"Channel {state.channel_id} 进入下一轮协商")
            await self._next_round(state)

        elif decision == "finalized_unanimous":
            self._logger.info(f"Channel {state.channel_id} 全员接受（{accepts}人），协商成功")
            await self._finalize_channel(state)

    def _determine_decision(
        self,
        accept_rate: float,
        reject_rate: float,
        negotiates: int,
        current_round: int,
        max_rounds: int,
        threshold_high: float,
        threshold_low: float
    ) -> str:
        """
        [v4] 根据反馈数据确定决策

        Args:
            accept_rate: 接受率
            reject_rate: 拒绝/退出率
            negotiates: 协商人数
            current_round: 当前轮次
            max_rounds: 最大轮次
            threshold_high: 高阈值（>=此值为成功）
            threshold_low: 低阈值（拒绝率>=此值为失败）

        Returns:
            决策类型: finalized | failed | force_finalized | next_round | finalized_unanimous
        """
        # 1. >= 80% 接受 → FINALIZED
        if accept_rate >= threshold_high:
            return "finalized"

        # 2. >= 50% 拒绝/退出 → FAILED
        if reject_rate >= threshold_low:
            return "failed"

        # 3. 全员接受（即使不足 80%，但无反对且无协商）→ FINALIZED
        if accept_rate > 0 and negotiates == 0 and reject_rate == 0:
            return "finalized_unanimous"

        # 4. 达到最大轮次 → 强制终结
        if current_round >= max_rounds:
            return "force_finalized"

        # 5. 50%-80% 接受 且 round < max_rounds → 下一轮
        return "next_round"

    async def _next_round(self, state: ChannelState):
        """进入下一轮协商"""
        state.current_round += 1
        old_feedback = state.proposal_feedback.copy()
        state.proposal_feedback.clear()
        state.proposal_distributed = False  # 重置分发标记，允许新一轮分发

        self._logger.info(
            f"Channel {state.channel_id} 进入第 {state.current_round} 轮协商"
        )

        # 发布新一轮事件
        await self._publish_event("towow.negotiation.round_started", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "round": state.current_round,
            "max_rounds": state.max_rounds,
            "previous_feedback_summary": {
                "accepts": sum(1 for f in old_feedback.values() if f.get("feedback_type") == "accept"),
                "rejects": sum(1 for f in old_feedback.values() if f.get("feedback_type") in ("reject", "withdraw")),
                "negotiates": sum(1 for f in old_feedback.values() if f.get("feedback_type") == "negotiate")
            }
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

        基于提示词 6：方案调整
        根据参与者反馈优化协作方案

        Args:
            state: Channel状态
            feedback: 参与者反馈字典

        Returns:
            调整后的协作方案
        """
        if not self.llm:
            # 没有 LLM，简单标记轮次
            adjusted = dict(state.current_proposal or {})
            adjusted["round"] = state.current_round
            adjusted["adjusted"] = True
            return adjusted

        current_proposal = state.current_proposal or {}

        # 分析反馈，按类型分组
        accept_feedbacks = []
        negotiate_feedbacks = []
        reject_feedbacks = []

        for agent_id, fb in feedback.items():
            fb_type = fb.get("feedback_type")
            fb_data = {
                "agent_id": agent_id,
                "adjustment_request": fb.get("adjustment_request", ""),
                "concerns": fb.get("concerns", []),
                "reasoning": fb.get("reasoning", "")
            }
            if fb_type == "accept":
                accept_feedbacks.append(fb_data)
            elif fb_type == "negotiate":
                negotiate_feedbacks.append(fb_data)
            else:  # reject / withdraw
                reject_feedbacks.append(fb_data)

        prompt = f"""
# 方案调整任务

## 原始需求
{state.demand.get('surface_demand', '未说明')}

## 当前方案（第 {state.current_round - 1} 轮）
```json
{json.dumps(current_proposal, ensure_ascii=False, indent=2)}
```

## 反馈汇总
- 接受: {len(accept_feedbacks)} 人
- 希望调整: {len(negotiate_feedbacks)} 人
- 拒绝/退出: {len(reject_feedbacks)} 人

## 调整请求详情

### 希望调整的反馈
```json
{json.dumps(negotiate_feedbacks, ensure_ascii=False, indent=2)}
```

### 拒绝/退出的反馈
```json
{json.dumps(reject_feedbacks, ensure_ascii=False, indent=2)}
```

## 调整原则

1. **优先解决共性问题**：多人提出的问题优先处理
2. **平衡各方利益**：调整不应损害已接受方的利益
3. **保持方案可行**：调整后的方案仍应可执行
4. **透明说明变更**：清晰说明做了什么调整及原因

## 输出要求

请输出调整后的完整方案（保持原方案 JSON 结构），并添加调整说明：

```json
{{
  "summary": "调整后的方案摘要",
  "objective": "方案目标",
  "assignments": [...],
  "timeline": {{...}},
  "success_criteria": [...],
  "risks": [...],
  "gaps": [...],
  "confidence": "high/medium/low",
  "adjustment_summary": {{
    "round": {state.current_round},
    "changes_made": [
      {{"aspect": "调整方面", "before": "调整前", "after": "调整后", "reason": "原因"}}
    ],
    "requests_addressed": ["已处理的请求"],
    "requests_declined": [
      {{"request": "未处理的请求", "reason": "原因"}}
    ]
  }}
}}
```
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是 ToWow 的方案调整系统。根据参与者反馈优化协作方案，以有效 JSON 格式输出。",
                fallback_key="proposal_adjustment",
                max_tokens=4000,
                temperature=0.4
            )
            adjusted = self._parse_proposal(response)
            adjusted["round"] = state.current_round
            return adjusted
        except Exception as e:
            self._logger.error(f"方案调整错误: {e}")
            adjusted = dict(current_proposal)
            adjusted["adjustment_failed"] = True
            adjusted["round"] = state.current_round
            return adjusted

    async def _finalize_channel(self, state: ChannelState):
        """完成协商，并进行缺口识别"""
        # 幂等性检查：防止重复完成
        if state.status == ChannelStatus.FINALIZED:
            self._logger.warning(f"Channel {state.channel_id} 已完成，跳过重复 finalize")
            return

        if state.finalized_notified:
            self._logger.warning(f"Channel {state.channel_id} 已发送完成通知，跳过")
            return

        state.status = ChannelStatus.FINALIZED
        state.finalized_notified = True  # 标记已发送完成通知

        # [T07] 清理 StateChecker 恢复状态
        if self._state_checker:
            self._state_checker.clear_recovery_state(state.channel_id)

        # 统计各类参与者数量
        confirmed_participants = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]
        declined_agents = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") == "decline"
        ]
        withdrawn_agents = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") == "withdrawn"
        ]

        self._logger.info(
            f"Channel {state.channel_id} 协商完成，共 {state.current_round} 轮，"
            f"{len(confirmed_participants)} 人参与"
        )

        # 缺口识别（仅主 Channel，非子网）
        if not state.is_subnet:
            await self._identify_and_handle_gaps(state)

        # 生成摘要
        summary = (
            f"经过{state.current_round}轮协商，"
            f"{len(confirmed_participants)}位参与者达成共识"
        )
        if declined_agents:
            summary += f"，{len(declined_agents)}人婉拒"
        if withdrawn_agents:
            summary += f"，{len(withdrawn_agents)}人中途退出"

        # 发布完成事件（完整统计信息）
        await self._publish_event("towow.proposal.finalized", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "status": "success",
            "final_proposal": state.current_proposal,
            "total_rounds": state.current_round,
            "participants_count": len(confirmed_participants),
            "declined_count": len(declined_agents),
            "withdrawn_count": len(withdrawn_agents),
            "participants": confirmed_participants,
            "summary": summary,
            "finalized_at": datetime.utcnow().isoformat()
        })

        # 通知Coordinator
        await self.send_to_agent("coordinator", {
            "type": "channel_completed",
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "success": True,
            "proposal": state.current_proposal,
            "participants": confirmed_participants,
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
                self._logger.error(f"通知 {agent_id} 失败: {e}")

    async def _force_finalize_channel(self, state: ChannelState):
        """
        [v4新增] 强制终结协商

        在达到最大轮次（第5轮）后，如果仍未达成共识，强制终结协商。
        区分已确认参与者（confirmed_participants）和可选参与者（optional_participants）。

        决策逻辑：
        - 接受方案的参与者 → confirmed_participants
        - negotiate 反馈的参与者 → optional_participants（可选参与）
        - reject/withdraw 的参与者 → 不纳入方案
        """
        # 幂等性检查
        if state.status in (ChannelStatus.FORCE_FINALIZED, ChannelStatus.FINALIZED):
            self._logger.warning(f"Channel {state.channel_id} 已终结，跳过重复 force_finalize")
            return

        if state.finalized_notified:
            self._logger.warning(f"Channel {state.channel_id} 已发送完成通知，跳过")
            return

        state.status = ChannelStatus.FORCE_FINALIZED
        state.finalized_notified = True

        # [T07] 清理 StateChecker 恢复状态
        if self._state_checker:
            self._state_checker.clear_recovery_state(state.channel_id)

        # 根据反馈类型分类参与者
        confirmed_participants = []  # 已确认参与
        optional_participants = []   # 可选参与（negotiate 类型）
        declined_agents = []         # 拒绝/退出

        for agent_id, feedback in state.proposal_feedback.items():
            feedback_type = feedback.get("feedback_type")
            if feedback_type == "accept":
                confirmed_participants.append(agent_id)
            elif feedback_type == "negotiate":
                optional_participants.append(agent_id)
            else:  # reject, withdraw
                declined_agents.append(agent_id)

        # 从 responses 中补充未给反馈但已参与的 agent
        for agent_id, resp in state.responses.items():
            if agent_id not in state.proposal_feedback:
                # 没有提供反馈的参与者，根据原始决策判断
                decision = resp.get("decision")
                if decision in ("participate", "conditional"):
                    # 默认归类为可选参与者
                    if agent_id not in optional_participants:
                        optional_participants.append(agent_id)

        self._logger.info(
            f"Channel {state.channel_id} 强制终结 (第 {state.current_round} 轮): "
            f"已确认={len(confirmed_participants)}, "
            f"可选={len(optional_participants)}, "
            f"退出={len(declined_agents)}"
        )

        # 生成强制终结的方案（带有分类标注）
        force_proposal = dict(state.current_proposal or {})
        force_proposal["force_finalized"] = True
        force_proposal["confirmed_participants"] = confirmed_participants
        force_proposal["optional_participants"] = optional_participants
        force_proposal["force_finalized_at"] = datetime.utcnow().isoformat()
        force_proposal["total_rounds"] = state.current_round

        # 更新 assignments 中的确认状态
        for assignment in force_proposal.get("assignments", []):
            agent_id = assignment.get("agent_id")
            if agent_id in confirmed_participants:
                assignment["is_confirmed"] = True
                assignment["participation_status"] = "confirmed"
            elif agent_id in optional_participants:
                assignment["is_confirmed"] = False
                assignment["participation_status"] = "optional"
            else:
                assignment["is_confirmed"] = False
                assignment["participation_status"] = "declined"

        state.current_proposal = force_proposal

        # 生成摘要
        summary = (
            f"经过 {state.current_round} 轮协商达到最大轮次，强制终结。"
            f"{len(confirmed_participants)} 人已确认参与"
        )
        if optional_participants:
            summary += f"，{len(optional_participants)} 人为可选参与"
        if declined_agents:
            summary += f"，{len(declined_agents)} 人已退出"

        # 发布强制终结事件
        await self._publish_event("towow.negotiation.force_finalized", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "status": "force_finalized",
            "total_rounds": state.current_round,
            "max_rounds": state.max_rounds,
            "confirmed_participants": confirmed_participants,
            "optional_participants": optional_participants,
            "declined_agents": declined_agents,
            "final_proposal": force_proposal,
            "summary": summary,
            "force_finalized_at": datetime.utcnow().isoformat()
        })

        # 缺口识别（仅主 Channel，非子网）
        if not state.is_subnet:
            await self._identify_and_handle_gaps(state)

        # 通知 Coordinator
        await self.send_to_agent("coordinator", {
            "type": "channel_completed",
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "success": True,  # 强制终结也算成功（有部分参与者）
            "force_finalized": True,
            "proposal": force_proposal,
            "confirmed_participants": confirmed_participants,
            "optional_participants": optional_participants,
            "rounds": state.current_round
        })

        # 通知所有参与者（带有各自的参与状态）
        for agent_id in state.responses.keys():
            try:
                participation_status = "confirmed"
                if agent_id in optional_participants:
                    participation_status = "optional"
                elif agent_id in declined_agents:
                    participation_status = "declined"

                await self.send_to_agent(agent_id, {
                    "type": "negotiation_completed",
                    "channel_id": state.channel_id,
                    "success": True,
                    "force_finalized": True,
                    "your_status": participation_status,
                    "proposal": force_proposal
                })
            except Exception as e:
                self._logger.error(f"通知 {agent_id} 失败: {e}")

    async def _fail_channel(self, state: ChannelState, reason: str):
        """协商失败"""
        state.status = ChannelStatus.FAILED

        # [T07] 清理 StateChecker 恢复状态
        if self._state_checker:
            self._state_checker.clear_recovery_state(state.channel_id)

        # 统计反馈情况
        accept_count = 0
        reject_count = 0
        for feedback in state.proposal_feedback.values():
            if feedback.get("feedback_type") == "accept":
                accept_count += 1
            elif feedback.get("feedback_type") == "reject":
                reject_count += 1

        # 生成失败原因的人性化描述
        reason_descriptions = {
            "no_participants": "没有候选人愿意参与",
            "majority_reject": "多数参与者拒绝了方案",
            "max_rounds_reached": "协商轮次已达上限，仍未达成共识",
            "no_feedback": "未收到参与者反馈",
            "all_participants_withdrawn": "所有参与者都已退出",
            "all_participants_removed": "所有参与者都已被移除"
        }
        human_reason = reason_descriptions.get(reason, reason)

        self._logger.warning(
            f"Channel {state.channel_id} 协商失败: {reason} (第 {state.current_round} 轮)"
        )

        # 发布失败事件（完整统计信息）
        await self._publish_event("towow.negotiation.failed", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "status": "failed",
            "reason": human_reason,
            "reason_code": reason,
            "total_rounds": state.current_round,
            "max_rounds": state.max_rounds,
            "final_accept_count": accept_count,
            "final_reject_count": reject_count,
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
                self._logger.error(f"通知 {agent_id} 失败: {e}")

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
            self._logger.debug(f"事件 (无总线): {event_type} - {payload}")
        except Exception as e:
            self._logger.error(f"发布事件 {event_type} 失败: {e}")

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

    # [T07] StateChecker 访问方法
    def get_state_checker(self) -> Optional[Any]:
        """获取 StateChecker 实例（用于测试和调试）"""
        return self._state_checker

    def get_state_checker_status(self) -> Dict[str, Any]:
        """获取 StateChecker 状态信息"""
        if not self._state_checker:
            return {"enabled": False, "running": False}
        return {
            "enabled": True,
            "running": self._state_checker.is_running,
            "check_interval": self._state_checker.check_interval,
            "max_stuck_time": self._state_checker.max_stuck_time,
            "max_recovery_attempts": self._state_checker.max_recovery_attempts,
            "recovery_states_count": len(self._state_checker._recovery_states),
            "active_channels_count": len(self.get_active_channels())
        }

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
            self._logger.error(f"妥协方案生成错误: {e}")
            return {
                "summary": "妥协方案生成失败",
                "type": "compromise",
                "error": str(e)
            }

    async def _handle_withdrawal(
        self,
        channel_id: str,
        agent_id: str,
        reason: str = "因个人原因需要退出本次协作",
        display_name: Optional[str] = None
    ) -> None:
        """
        处理Agent退出协商

        Args:
            channel_id: Channel ID
            agent_id: 退出的Agent ID
            reason: 退出原因
            display_name: Agent显示名称
        """
        if channel_id not in self.channels:
            return

        state = self.channels[channel_id]

        # 获取 agent 的显示名称
        if not display_name:
            # 尝试从候选人列表获取
            for candidate in state.candidates:
                if candidate.get("agent_id") == agent_id:
                    display_name = candidate.get("display_name", agent_id)
                    break
            if not display_name:
                display_name = agent_id

        # 更新响应状态
        if agent_id in state.responses:
            state.responses[agent_id]["decision"] = "withdrawn"
            state.responses[agent_id]["withdrawn_at"] = datetime.utcnow().isoformat()
            state.responses[agent_id]["withdrawal_reason"] = reason

        self._logger.info(f"Agent {agent_id} 退出 Channel {channel_id}: {reason}")

        # 发布退出事件（完整信息）
        await self._publish_event("towow.agent.withdrawn", {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "display_name": display_name,
            "reason": reason,
            "round": state.current_round,
            "timestamp": datetime.utcnow().isoformat()
        })

        # 检查是否还有足够的参与者
        remaining_participants = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]

        if len(remaining_participants) == 0:
            await self._fail_channel(state, "all_participants_withdrawn")

    async def _handle_kick(
        self,
        channel_id: str,
        agent_id: str,
        reason: str = "多次未响应，已自动移出协作",
        kicked_by: str = "system",
        display_name: Optional[str] = None
    ) -> None:
        """
        处理Agent被踢出

        Args:
            channel_id: Channel ID
            agent_id: 被踢出的Agent ID
            reason: 踢出原因
            kicked_by: 踢出者（system 或其他 agent_id）
            display_name: Agent显示名称
        """
        if channel_id not in self.channels:
            return

        state = self.channels[channel_id]

        # 获取 agent 的显示名称
        if not display_name:
            for candidate in state.candidates:
                if candidate.get("agent_id") == agent_id:
                    display_name = candidate.get("display_name", agent_id)
                    break
            if not display_name:
                display_name = agent_id

        # 更新响应状态
        if agent_id in state.responses:
            state.responses[agent_id]["decision"] = "kicked"
            state.responses[agent_id]["kicked_at"] = datetime.utcnow().isoformat()
            state.responses[agent_id]["kick_reason"] = reason
            state.responses[agent_id]["kicked_by"] = kicked_by

        self._logger.info(f"Agent {agent_id} 被踢出 Channel {channel_id}: {reason}")

        # 发布被踢出事件
        await self._publish_event("towow.agent.kicked", {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "display_name": display_name,
            "reason": reason,
            "kicked_by": kicked_by,
            "round": state.current_round,
            "timestamp": datetime.utcnow().isoformat()
        })

        # 检查是否还有足够的参与者
        remaining_participants = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]

        if len(remaining_participants) == 0:
            await self._fail_channel(state, "all_participants_removed")

    async def _publish_bargain_event(
        self,
        channel_id: str,
        agent_id: str,
        display_name: str,
        bargain_type: str,
        content: str
    ) -> None:
        """
        发布讨价还价事件

        Args:
            channel_id: Channel ID
            agent_id: Agent ID
            display_name: Agent显示名称
            bargain_type: 讨价还价类型 (role_change/condition/objection)
            content: 讨价还价内容
        """
        if channel_id not in self.channels:
            return

        state = self.channels[channel_id]

        await self._publish_event("towow.negotiation.bargain", {
            "channel_id": channel_id,
            "agent_id": agent_id,
            "display_name": display_name,
            "bargain_type": bargain_type,
            "content": content,
            "round": state.current_round,
            "timestamp": datetime.utcnow().isoformat()
        })

    # ========== 新增消息处理方法 ==========

    async def _handle_agent_withdrawn(self, data: Dict[str, Any]) -> None:
        """
        处理 Agent 主动退出消息

        Args:
            data: 消息数据，包含 channel_id, agent_id, reason
        """
        channel_id = data.get("channel_id")
        agent_id = data.get("agent_id")
        reason = data.get("reason", "因个人原因需要退出本次协作")

        if not channel_id or not agent_id:
            self._logger.warning("agent_withdrawn 消息缺少 channel_id 或 agent_id")
            return

        # 调用内部处理方法
        await self._handle_withdrawal(channel_id, agent_id, reason)

    async def _handle_bargain(self, data: Dict[str, Any]) -> None:
        """
        处理讨价还价消息

        Args:
            data: 消息数据，包含 channel_id, agent_id, offer, original_terms, new_terms
        """
        channel_id = data.get("channel_id")
        agent_id = data.get("agent_id")
        offer = data.get("offer", "")
        original_terms = data.get("original_terms", {})
        new_terms = data.get("new_terms", {})

        if not channel_id or not agent_id:
            self._logger.warning("bargain 消息缺少 channel_id 或 agent_id")
            return

        if channel_id not in self.channels:
            self._logger.warning(f"未知 Channel: {channel_id}")
            return

        state = self.channels[channel_id]

        # 获取 agent 的显示名称
        display_name = agent_id
        for candidate in state.candidates:
            if candidate.get("agent_id") == agent_id:
                display_name = candidate.get("display_name", agent_id)
                break

        self._logger.info(f"Agent {agent_id} 在 Channel {channel_id} 发起讨价还价: {offer}")

        # 发布讨价还价事件（使用更完整的 payload）
        await self._publish_event("towow.negotiation.bargain", {
            "channel_id": channel_id,
            "demand_id": state.demand_id,
            "agent_id": agent_id,
            "display_name": display_name,
            "offer": offer,
            "original_terms": original_terms,
            "new_terms": new_terms,
            "round": state.current_round,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def _handle_counter_proposal(self, data: Dict[str, Any]) -> None:
        """
        处理反提案消息

        Args:
            data: 消息数据，包含 channel_id, agent_id, counter_proposal, reason
        """
        channel_id = data.get("channel_id")
        agent_id = data.get("agent_id")
        counter_proposal = data.get("counter_proposal", {})
        reason = data.get("reason", "")

        if not channel_id or not agent_id:
            self._logger.warning("counter_proposal 消息缺少 channel_id 或 agent_id")
            return

        if channel_id not in self.channels:
            self._logger.warning(f"未知 Channel: {channel_id}")
            return

        state = self.channels[channel_id]

        # 获取 agent 的显示名称
        display_name = agent_id
        for candidate in state.candidates:
            if candidate.get("agent_id") == agent_id:
                display_name = candidate.get("display_name", agent_id)
                break

        self._logger.info(f"Agent {agent_id} 在 Channel {channel_id} 提交反提案")

        # 发布反提案事件
        await self._publish_event("towow.negotiation.counter_proposal", {
            "channel_id": channel_id,
            "demand_id": state.demand_id,
            "agent_id": agent_id,
            "display_name": display_name,
            "counter_proposal": counter_proposal,
            "reason": reason,
            "round": state.current_round,
            "timestamp": datetime.utcnow().isoformat()
        })

        # 可以选择是否将反提案作为当前方案的调整
        # 这里记录反提案供后续协商参考
        if agent_id in state.proposal_feedback:
            state.proposal_feedback[agent_id]["counter_proposal"] = counter_proposal
            state.proposal_feedback[agent_id]["counter_proposal_reason"] = reason

    async def _handle_kick_agent(self, data: Dict[str, Any]) -> None:
        """
        处理踢出 Agent 的消息

        Args:
            data: 消息数据，包含 channel_id, agent_id, reason, kicked_by
        """
        channel_id = data.get("channel_id")
        agent_id = data.get("agent_id")
        reason = data.get("reason", "多次未响应，已自动移出协作")
        kicked_by = data.get("kicked_by", "system")

        if not channel_id or not agent_id:
            self._logger.warning("kick_agent 消息缺少 channel_id 或 agent_id")
            return

        # 调用内部处理方法
        await self._handle_kick(channel_id, agent_id, reason, kicked_by)

    # ========== 公共 API 方法（供外部调用）==========

    async def withdraw_agent(
        self,
        channel_id: str,
        agent_id: str,
        reason: str = "因个人原因需要退出本次协作"
    ) -> bool:
        """
        处理 Agent 退出（公共 API）

        Args:
            channel_id: Channel ID
            agent_id: 退出的 Agent ID
            reason: 退出原因

        Returns:
            是否成功处理
        """
        await self._handle_withdrawal(channel_id, agent_id, reason)
        return True

    async def kick_agent(
        self,
        channel_id: str,
        agent_id: str,
        reason: str = "多次未响应，已自动移出协作",
        kicked_by: str = "system"
    ) -> bool:
        """
        踢出 Agent（公共 API）

        Args:
            channel_id: Channel ID
            agent_id: 被踢出的 Agent ID
            reason: 踢出原因
            kicked_by: 踢出者

        Returns:
            是否成功处理
        """
        await self._handle_kick(channel_id, agent_id, reason, kicked_by)
        return True

    async def publish_bargain(
        self,
        channel_id: str,
        agent_id: str,
        offer: str,
        original_terms: Optional[Dict[str, Any]] = None,
        new_terms: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发布讨价还价事件（公共 API）

        Args:
            channel_id: Channel ID
            agent_id: Agent ID
            offer: 讨价还价内容
            original_terms: 原始条款
            new_terms: 新条款

        Returns:
            是否成功处理
        """
        await self._handle_bargain({
            "channel_id": channel_id,
            "agent_id": agent_id,
            "offer": offer,
            "original_terms": original_terms or {},
            "new_terms": new_terms or {}
        })
        return True

    async def publish_counter_proposal(
        self,
        channel_id: str,
        agent_id: str,
        counter_proposal: Dict[str, Any],
        reason: str = ""
    ) -> bool:
        """
        发布反提案事件（公共 API）

        Args:
            channel_id: Channel ID
            agent_id: Agent ID
            counter_proposal: 反提案内容
            reason: 提交原因

        Returns:
            是否成功处理
        """
        await self._handle_counter_proposal({
            "channel_id": channel_id,
            "agent_id": agent_id,
            "counter_proposal": counter_proposal,
            "reason": reason
        })
        return True

    # ========== 缺口识别与子网触发 ==========

    async def _identify_and_handle_gaps(self, state: ChannelState):
        """
        识别缺口并处理

        基于提示词 7（缺口识别）和提示词 8（递归判断）实现。
        当协商完成后，分析方案是否存在缺口，并决定是否触发子网协商。

        Args:
            state: Channel 状态
        """
        # 幂等性检查：防止重复识别缺口
        if state.gaps_identified:
            self._logger.warning(f"Channel {state.channel_id} 缺口已识别，跳过")
            return

        state.gaps_identified = True  # 标记已识别

        try:
            from services.gap_identification import GapIdentificationService
            from services.subnet_manager import SubnetManager
        except ImportError:
            self._logger.warning("缺口识别服务不可用，跳过缺口分析")
            return

        # 初始化服务
        gap_service = GapIdentificationService(llm_service=self.llm)
        subnet_manager = SubnetManager(max_depth=1)  # MVP: 最多 1 层递归

        # 收集参与者信息（用于缺口分析）
        participants = []
        for agent_id, resp in state.responses.items():
            if resp.get("decision") in ("participate", "conditional"):
                participants.append({
                    "agent_id": agent_id,
                    "decision": resp.get("decision"),
                    "contribution": resp.get("contribution"),
                    "conditions": resp.get("conditions", []),
                    "capabilities": resp.get("capabilities", [])
                })

        # 识别缺口
        gap_result = await gap_service.identify_gaps(
            demand=state.demand,
            proposal=state.current_proposal or {},
            participants=participants,
            channel_id=state.channel_id,
            demand_id=state.demand_id
        )

        self._logger.info(
            f"缺口识别完成: total_gaps={gap_result.total_gaps}, "
            f"critical_gaps={gap_result.critical_gaps}, "
            f"subnet_recommended={gap_result.subnet_recommended}"
        )

        # 发布缺口识别事件
        await self._publish_event("towow.gap.identified", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "is_complete": gap_result.total_gaps == 0,
            "total_gaps": gap_result.total_gaps,
            "critical_gaps": gap_result.critical_gaps,
            "gaps": [g.to_dict() for g in gap_result.gaps],
            "analysis": gap_result.analysis_summary,
            "subnet_recommended": gap_result.subnet_recommended
        })

        # 如果有缺口且建议触发子网，进行递归判断
        if gap_result.subnet_recommended:
            await self._trigger_subnet_if_needed(
                state=state,
                gap_result=gap_result,
                subnet_manager=subnet_manager
            )

    async def _trigger_subnet_if_needed(
        self,
        state: ChannelState,
        gap_result,
        subnet_manager
    ):
        """
        根据缺口分析结果决定是否触发子网

        Args:
            state: Channel 状态
            gap_result: 缺口分析结果
            subnet_manager: 子网管理器
        """
        # 幂等性检查：防止重复触发子网
        if state.subnet_triggered:
            self._logger.warning(f"Channel {state.channel_id} 子网已触发，跳过")
            return

        # 检查递归深度限制
        if state.recursion_depth >= subnet_manager.max_depth:
            self._logger.info(
                f"已达到最大递归深度 {subnet_manager.max_depth}，不再触发子网"
            )
            return

        # 获取应该触发子网的缺口
        subnet_triggers = gap_result.get_subnet_triggers()
        if not subnet_triggers:
            self._logger.info("没有需要触发子网的缺口")
            return

        # 标记已触发子网（在实际触发前标记，防止并发）
        state.subnet_triggered = True

        # MVP: 只触发一个子网（最关键的缺口）
        gap = subnet_triggers[0]

        self._logger.info(
            f"触发子网解决缺口: {gap.gap_type.value} - {gap.description}"
        )

        # 构建子需求
        sub_demand = {
            "surface_demand": gap.suggested_sub_demand or f"寻找能够解决「{gap.description}」的协作者",
            "deep_understanding": {
                "type": "sub_demand",
                "motivation": f"填补缺口：{gap.description}",
                "parent_gap_type": gap.gap_type.value,
                "requirement": gap.requirement
            },
            "capability_tags": gap.affected_aspects,
            "metadata": {
                "parent_demand_id": state.demand_id,
                "parent_channel_id": state.channel_id,
                "gap_id": gap.gap_id,
                "gap_severity": gap.severity.value
            }
        }

        # 发布子网触发事件
        await self._publish_event("towow.subnet.triggered", {
            "channel_id": state.channel_id,
            "demand_id": state.demand_id,
            "gap_id": gap.gap_id,
            "gap_type": gap.gap_type.value,
            "gap_severity": gap.severity.value,
            "gap_description": gap.description,
            "sub_demand": sub_demand,
            "recursion_depth": state.recursion_depth + 1,
            "reason": f"缺口识别触发：{gap.gap_type.value} - {gap.description}"
        })

        # 通知 Coordinator 创建子网协商
        try:
            await self.send_to_agent("coordinator", {
                "type": "subnet_demand",
                "demand": sub_demand,
                "parent_channel_id": state.channel_id,
                "parent_demand_id": state.demand_id,
                "gap_id": gap.gap_id,
                "recursion_depth": state.recursion_depth + 1
            })
            self._logger.info(
                f"已通知 Coordinator 创建子网，父 Channel: {state.channel_id}"
            )
        except Exception as e:
            self._logger.error(f"通知 Coordinator 创建子网失败: {e}")


