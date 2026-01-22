"""
UserAgent - 用户数字分身代理

职责：
1. 接收需求offer，调用SecondMe生成响应
2. 评估方案并提供反馈
3. 代表用户自主决策
4. 提交新需求给Coordinator

消息流转：
- 用户输入 → UserAgent.submit_demand() → SecondMe.understand_demand() → Coordinator
- Coordinator → UserAgent (collaboration_invite) → handle_invite() → SecondMe.generate_response()
- ChannelAdmin → UserAgent (proposal_review) → handle_proposal() → SecondMe.evaluate_proposal()
"""
from __future__ import annotations

import json
import logging
import random
import re
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from .base import TowowBaseAgent

logger = logging.getLogger(__name__)


class UserAgent(TowowBaseAgent):
    """
    UserAgent - 用户数字分身代理

    每个用户对应一个UserAgent实例，代表用户参与协商
    """

    AGENT_TYPE = "user_agent"

    def __init__(
        self,
        user_id: str,
        profile: Optional[Dict[str, Any]] = None,
        secondme_service: Any = None,
        **kwargs: Any,
    ):
        """Initialize the user agent.

        Args:
            user_id: The user this agent represents.
            profile: User profile containing capabilities and preferences.
            secondme_service: Optional SecondMe service for AI responses.
            **kwargs: Additional arguments passed to base class.
        """
        super().__init__(**kwargs)
        self.user_id = user_id
        self.profile = profile or {}
        self.secondme = secondme_service
        self.active_channels: Dict[str, Dict[str, Any]] = {}  # channel_id -> participation info

    @property
    def agent_id(self) -> str:
        """Agent ID."""
        return f"user_agent_{self.user_id}"

    async def on_channel_message(self, ctx: Any) -> None:
        """处理Channel消息.

        Args:
            ctx: Channel message context containing message data.
        """
        message = ctx.message if hasattr(ctx, "message") else {}
        data = message.get("data", {})
        msg_type = data.get("type")

        if msg_type == "demand_offer":
            await self._handle_demand_offer(ctx, data)
        elif msg_type == "proposal_review":
            await self._handle_proposal_review(ctx, data)

    async def _handle_demand_offer(
        self, ctx: Any, data: Dict[str, Any]
    ) -> None:
        """处理需求offer.

        Args:
            ctx: Channel message context.
            data: Message data containing demand information.
        """
        channel_id = data.get("channel_id", "")
        demand = data.get("demand", {})
        filter_reason = data.get("filter_reason", "")

        self._logger.info(f"Received demand offer for channel {channel_id}")

        # 记录参与信息
        self.active_channels[channel_id] = {
            "demand": demand,
            "status": "evaluating",
            "received_at": datetime.utcnow().isoformat(),
        }

        # 调用SecondMe生成响应
        response = await self._generate_response(demand, filter_reason)

        # 更新状态
        self.active_channels[channel_id]["response"] = response
        self.active_channels[channel_id]["status"] = "responded"

        # 发送响应给ChannelAdmin
        await self.send_to_agent(
            "channel_admin",
            {
                "type": "offer_response",
                "channel_id": channel_id,
                "agent_id": self.agent_id,
                **response,
            },
        )

    async def _generate_response(
        self, demand: Dict[str, Any], filter_reason: str
    ) -> Dict[str, Any]:
        """生成需求响应.

        Args:
            demand: The demand to respond to.
            filter_reason: Reason why this user was selected.

        Returns:
            Response containing decision, contribution, conditions, and reasoning.
        """
        # 优先使用SecondMe
        if self.secondme:
            try:
                return await self.secondme.generate_response(
                    user_id=self.user_id,
                    demand=demand,
                    profile=self.profile,
                    context={"filter_reason": filter_reason},
                )
            except Exception as e:
                self._logger.error(f"SecondMe error: {e}")

        # 使用LLM作为备选
        if self.llm:
            return await self._llm_generate_response(demand, filter_reason)

        # Mock响应
        return self._mock_response(demand)

    async def _llm_generate_response(
        self, demand: Dict[str, Any], filter_reason: str
    ) -> Dict[str, Any]:
        """使用LLM生成响应.

        Args:
            demand: The demand to respond to.
            filter_reason: Reason why this user was selected.

        Returns:
            Response containing decision, contribution, conditions, and reasoning.
        """
        prompt = f"""
## 你的身份
你是用户 {self.user_id} 的数字分身，需要代表用户回应一个协作需求。

## 用户档案
{json.dumps(self.profile, ensure_ascii=False, indent=2)}

## 收到的需求
{json.dumps(demand, ensure_ascii=False, indent=2)}

## 被筛选原因
{filter_reason}

## 任务
根据用户档案和需求，决定是否参与这个协作，并说明理由。

## 输出格式
```json
{{
  "decision": "participate" 或 "decline" 或 "conditional",
  "contribution": "如果参与，你能贡献什么",
  "conditions": ["如果是conditional，列出条件"],
  "reasoning": "决策理由"
}}
```

注意：
- 基于用户档案做出符合用户性格和能力的决策
- 不要过度承诺用户能力范围外的事情
- 如果需求与用户能力不匹配，应该decline
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是一个数字分身系统，代表用户做出合理的协作决策。",
                fallback_key="response_generation",
            )
            return self._parse_response(response)
        except Exception as e:
            self._logger.error(f"LLM response error: {e}")
            return self._mock_response(demand)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析响应.

        Args:
            response: Raw response string from LLM.

        Returns:
            Parsed response dictionary.
        """
        try:
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "decision": data.get("decision", "decline"),
                    "contribution": data.get("contribution", ""),
                    "conditions": data.get("conditions", []),
                    "reasoning": data.get("reasoning", ""),
                }
        except Exception as e:
            self._logger.error(f"Parse response error: {e}")
        return self._mock_response({})

    def _mock_response(self, demand: Dict[str, Any]) -> Dict[str, Any]:
        """Mock响应（演示用）.

        Args:
            demand: The demand to respond to.

        Returns:
            Mock response based on simple capability matching.
        """
        # 基于profile简单决策
        capabilities = self.profile.get("capabilities", [])
        demand_text = str(demand.get("surface_demand", ""))

        # 简单匹配
        has_match = any(cap.lower() in demand_text.lower() for cap in capabilities)

        if has_match:
            matched_caps = [cap for cap in capabilities[:2] if cap]
            contribution = f"可以提供 {', '.join(matched_caps)} 方面的支持" if matched_caps else "可以提供支持"
            return {
                "decision": "participate",
                "contribution": contribution,
                "conditions": [],
                "reasoning": "需求与我的能力匹配",
            }
        else:
            return {
                "decision": "decline",
                "contribution": "",
                "conditions": [],
                "reasoning": "需求与我的能力不太匹配",
            }

    async def _handle_proposal_review(
        self, ctx: Any, data: Dict[str, Any]
    ) -> None:
        """处理方案评审.

        Args:
            ctx: Channel message context.
            data: Message data containing proposal information.
        """
        channel_id = data.get("channel_id", "")
        proposal = data.get("proposal", {})

        self._logger.info(f"Reviewing proposal for channel {channel_id}")

        if channel_id not in self.active_channels:
            self._logger.warning(f"Unknown channel: {channel_id}")
            return

        # 评估方案
        feedback = await self._evaluate_proposal(proposal)

        # 更新状态
        self.active_channels[channel_id]["proposal"] = proposal
        self.active_channels[channel_id]["feedback"] = feedback

        # 发送反馈
        await self.send_to_agent(
            "channel_admin",
            {
                "type": "proposal_feedback",
                "channel_id": channel_id,
                "agent_id": self.agent_id,
                **feedback,
            },
        )

    async def _evaluate_proposal(
        self, proposal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估方案.

        Args:
            proposal: The proposal to evaluate.

        Returns:
            Feedback containing feedback_type, adjustment_request, and reasoning.
        """
        if self.secondme:
            try:
                return await self.secondme.evaluate_proposal(
                    user_id=self.user_id,
                    proposal=proposal,
                    profile=self.profile,
                )
            except Exception as e:
                self._logger.error(f"SecondMe evaluate error: {e}")

        if self.llm:
            return await self._llm_evaluate_proposal(proposal)

        return self._mock_feedback(proposal)

    async def _llm_evaluate_proposal(
        self, proposal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用LLM评估方案.

        Args:
            proposal: The proposal to evaluate.

        Returns:
            Feedback containing feedback_type, adjustment_request, and reasoning.
        """
        # 找到自己在方案中的角色
        my_assignment = None
        for assignment in proposal.get("assignments", []):
            if assignment.get("agent_id") == self.agent_id:
                my_assignment = assignment
                break

        assignment_json = (
            json.dumps(my_assignment, ensure_ascii=False)
            if my_assignment
            else "未分配具体角色"
        )

        prompt = f"""
## 你的身份
你是用户 {self.user_id} 的数字分身。

## 用户档案
{json.dumps(self.profile, ensure_ascii=False, indent=2)}

## 协作方案
{json.dumps(proposal, ensure_ascii=False, indent=2)}

## 你在方案中的角色
{assignment_json}

## 任务
评估这个方案是否可以接受。

## 输出格式
```json
{{
  "feedback_type": "accept" 或 "reject" 或 "negotiate",
  "adjustment_request": "如果是negotiate，说明希望如何调整",
  "reasoning": "评估理由"
}}
```
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是一个数字分身系统，代表用户评估协作方案。",
            )
            return self._parse_feedback(response)
        except Exception as e:
            self._logger.error(f"LLM evaluate error: {e}")
            return self._mock_feedback(proposal)

    def _parse_feedback(self, response: str) -> Dict[str, Any]:
        """解析反馈.

        Args:
            response: Raw response string from LLM.

        Returns:
            Parsed feedback dictionary.
        """
        try:
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "feedback_type": data.get("feedback_type", "accept"),
                    "adjustment_request": data.get("adjustment_request", ""),
                    "reasoning": data.get("reasoning", ""),
                }
        except Exception as e:
            self._logger.error(f"Parse feedback error: {e}")
        return self._mock_feedback({})

    def _mock_feedback(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Mock反馈（演示用）.

        Args:
            proposal: The proposal being evaluated (unused in mock).

        Returns:
            Mock feedback with 80% acceptance probability.
        """
        # 80%概率接受
        if random.random() < 0.8:
            return {
                "feedback_type": "accept",
                "adjustment_request": "",
                "reasoning": "方案合理，同意参与",
            }
        else:
            return {
                "feedback_type": "negotiate",
                "adjustment_request": "希望能调整一下时间安排",
                "reasoning": "整体可以，但时间上有点冲突",
            }

    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态.

        Returns:
            Agent status information.
        """
        return {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "active_channels": len(self.active_channels),
            "profile_loaded": bool(self.profile),
        }

    # ===== TASK-006 新增方法 =====

    async def submit_demand(self, raw_input: str) -> Dict[str, Any]:
        """提交新需求.

        流程：
        1. 调用 SecondMe 理解需求
        2. 构造需求消息发送给 Coordinator

        Args:
            raw_input: 用户原始需求输入

        Returns:
            {
                "demand_id": "d-xxx",
                "understanding": {...},
                "status": "submitted"
            }
        """
        demand_id = f"d-{uuid4().hex[:8]}"
        self._logger.info(f"User {self.user_id} submitting demand: {demand_id}")

        # 1. 调用 SecondMe 理解需求
        understanding = await self._understand_demand(raw_input)

        # 2. 发送给 Coordinator
        await self.send_to_agent(
            "coordinator",
            {
                "type": "new_demand",
                "demand_id": demand_id,
                "user_id": self.user_id,
                "raw_input": raw_input,
                "understanding": understanding,
                "submitted_at": datetime.utcnow().isoformat(),
            }
        )

        # 3. 记录提交的需求
        self.active_channels[demand_id] = {
            "type": "submitted_demand",
            "demand_id": demand_id,
            "raw_input": raw_input,
            "understanding": understanding,
            "status": "submitted",
            "submitted_at": datetime.utcnow().isoformat(),
        }

        return {
            "demand_id": demand_id,
            "understanding": understanding,
            "status": "submitted"
        }

    async def _understand_demand(self, raw_input: str) -> Dict[str, Any]:
        """调用 SecondMe 理解需求.

        Args:
            raw_input: 原始需求输入

        Returns:
            需求理解结果
        """
        if self.secondme:
            try:
                return await self.secondme.understand_demand(
                    raw_input=raw_input,
                    user_id=self.user_id
                )
            except Exception as e:
                self._logger.error(f"SecondMe understand_demand error: {e}")

        # 降级：返回基本结构
        return {
            "surface_demand": raw_input,
            "deep_understanding": {"motivation": "unknown"},
            "uncertainties": [],
            "confidence": "low"
        }

    async def handle_invite(
        self,
        channel_id: str,
        demand: Dict[str, Any],
        filter_reason: str = ""
    ) -> Dict[str, Any]:
        """处理协作邀请.

        当 Coordinator 筛选后，UserAgent 收到加入 Channel 的邀请。
        调用 SecondMe 决定是否参与。

        Args:
            channel_id: Channel ID
            demand: 需求信息
            filter_reason: 被筛选的原因

        Returns:
            {
                "decision": "participate/decline/conditional",
                "contribution": "贡献说明",
                "conditions": [...],
                "reasoning": "决策理由"
            }
        """
        self._logger.info(f"User {self.user_id} handling invite for channel {channel_id}")

        # 记录邀请
        self.active_channels[channel_id] = {
            "demand": demand,
            "status": "invited",
            "filter_reason": filter_reason,
            "received_at": datetime.utcnow().isoformat(),
        }

        # 调用 SecondMe 生成响应
        response = await self._generate_response(demand, filter_reason)

        # 更新状态
        self.active_channels[channel_id]["response"] = response
        self.active_channels[channel_id]["status"] = "responded"

        # 发送响应给 ChannelAdmin
        await self.send_to_agent(
            "channel_admin",
            {
                "type": "invite_response",
                "channel_id": channel_id,
                "agent_id": self.agent_id,
                "user_id": self.user_id,
                **response,
            },
        )

        return response

    async def handle_proposal(
        self,
        channel_id: str,
        proposal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理方案分配.

        当 ChannelAdmin 形成初步方案后，发送给各参与者评审。
        调用 SecondMe 评估方案并提供反馈。

        Args:
            channel_id: Channel ID
            proposal: 协作方案

        Returns:
            {
                "feedback_type": "accept/reject/negotiate",
                "adjustment_request": "调整请求",
                "reasoning": "评估理由"
            }
        """
        self._logger.info(f"User {self.user_id} handling proposal for channel {channel_id}")

        if channel_id not in self.active_channels:
            self._logger.warning(f"Unknown channel: {channel_id}, creating entry")
            self.active_channels[channel_id] = {
                "status": "proposal_received",
                "received_at": datetime.utcnow().isoformat(),
            }

        # 调用 SecondMe 评估方案
        feedback = await self._evaluate_proposal(proposal)

        # 更新状态
        self.active_channels[channel_id]["proposal"] = proposal
        self.active_channels[channel_id]["feedback"] = feedback
        self.active_channels[channel_id]["status"] = "feedback_sent"

        # 发送反馈给 ChannelAdmin
        await self.send_to_agent(
            "channel_admin",
            {
                "type": "proposal_feedback",
                "channel_id": channel_id,
                "agent_id": self.agent_id,
                "user_id": self.user_id,
                **feedback,
            },
        )

        return feedback

    async def on_direct(self, ctx: Any) -> None:
        """处理直接消息.

        支持的消息类型：
        - collaboration_invite: 协作邀请
        - proposal_review: 方案评审
        - demand_offer: 需求offer（兼容旧格式）

        Args:
            ctx: Event context
        """
        payload = ctx.incoming_event.payload if hasattr(ctx, 'incoming_event') else {}
        content = payload.get("content", {})
        msg_type = content.get("type")

        if msg_type == "collaboration_invite":
            await self.handle_invite(
                channel_id=content.get("channel_id", ""),
                demand=content.get("demand", {}),
                filter_reason=content.get("filter_reason", "")
            )
        elif msg_type == "proposal_review":
            await self.handle_proposal(
                channel_id=content.get("channel_id", ""),
                proposal=content.get("proposal", {})
            )
        elif msg_type == "demand_offer":
            # 兼容旧格式
            await self._handle_demand_offer(ctx, content)
        else:
            self._logger.debug(f"Unknown direct message type: {msg_type}")

