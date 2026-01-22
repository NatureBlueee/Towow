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

        self._logger.info(f"收到 Channel {channel_id} 的需求邀请")

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
                self._logger.error(f"SecondMe 错误: {e}")

        # 使用LLM作为备选
        if self.llm:
            return await self._llm_generate_response(demand, filter_reason)

        # Mock响应
        return self._mock_response(demand)

    async def _llm_generate_response(
        self, demand: Dict[str, Any], filter_reason: str
    ) -> Dict[str, Any]:
        """使用LLM生成响应.

        基于提示词 3：响应生成（参考 TECH-v3.md 3.3.3）

        Args:
            demand: The demand to respond to.
            filter_reason: Reason why this user was selected.

        Returns:
            Response containing decision, contribution, conditions, reasoning,
            decline_reason, confidence, enthusiasm_level, and suggested_role.
        """
        # 构建更丰富的 Profile 描述
        profile_summary = self._build_profile_summary()

        # 构建需求摘要
        demand_summary = self._build_demand_summary(demand)

        prompt = f"""
# 协作邀请响应任务

## 你的身份
你是 **{self.profile.get('name', self.user_id)}** 的数字分身（AI Agent）。
你需要代表用户，根据其个人档案和能力，决定是否参与这个协作需求。

## 你的档案
{profile_summary}

## 收到的协作需求
{demand_summary}

## 你被筛选的原因
{filter_reason or "未说明"}

## 决策任务

请根据以下原则做出决策：

1. **能力匹配原则**：只承诺你档案中明确具备的能力
2. **真实性原则**：不要过度承诺，也不要过于谦虚
3. **条件明确原则**：如果有条件，必须明确说明
4. **理由清晰原则**：无论什么决定，都要给出清晰的理由

## 输出要求

请以 JSON 格式输出你的响应：

```json
{{
  "decision": "participate | decline | conditional",
  "contribution": "如果参与，具体说明你能贡献什么（详细描述，包含时间、资源等）",
  "conditions": ["如果是 conditional，列出每一个条件"],
  "reasoning": "你做出这个决定的理由（50字以内）",
  "decline_reason": "如果是 decline，说明原因",
  "confidence": 80,
  "enthusiasm_level": "high | medium | low",
  "suggested_role": "你建议自己在协作中承担的角色"
}}
```

## 决策类型说明

- **participate**: 愿意参与，能够贡献
- **conditional**: 愿意参与，但有条件
- **decline**: 不参与（能力不匹配、时间冲突、兴趣不合等）

注意：请站在 {self.profile.get('name', self.user_id)} 的角度思考，基于其真实能力和偏好做出决策。
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system=self._get_response_system_prompt(),
                fallback_key="response_generation",
                max_tokens=1000,
                temperature=0.5,
            )
            return self._parse_response(response)
        except Exception as e:
            self._logger.error(f"LLM 响应错误: {e}")
            return self._mock_response(demand)

    def _get_response_system_prompt(self) -> str:
        """获取响应生成系统提示词."""
        return """你是一个数字分身系统，代表用户做出合理的协作决策。

关键原则：
1. 基于用户档案做出符合用户性格和能力的决策
2. 不要过度承诺用户能力范围外的事情
3. 如果需求与用户能力不匹配，应该 decline
4. 如果部分匹配但有顾虑，使用 conditional
5. 始终以有效的 JSON 格式输出"""

    def _build_profile_summary(self) -> str:
        """构建 Profile 摘要."""
        name = self.profile.get("name", self.user_id)
        capabilities = self.profile.get("capabilities", [])
        interests = self.profile.get("interests", [])
        location = self.profile.get("location", "未知")
        availability = self.profile.get("availability", "未说明")
        description = self.profile.get("description", "")
        tags = self.profile.get("tags", [])

        # 处理 capabilities 可能是 dict 的情况
        if isinstance(capabilities, dict):
            cap_list = list(capabilities.keys())[:5]
        else:
            cap_list = capabilities[:5] if capabilities else []

        return f"""
- **姓名**: {name}
- **位置**: {location}
- **能力**: {', '.join(cap_list) if cap_list else '未说明'}
- **标签**: {', '.join(tags[:5]) if tags else '未说明'}
- **兴趣**: {', '.join(interests[:5]) if interests else '未说明'}
- **可用时间**: {availability}
- **简介**: {description[:200] if description else '未提供'}
"""

    def _build_demand_summary(self, demand: Dict[str, Any]) -> str:
        """构建需求摘要."""
        surface = demand.get("surface_demand", "未说明")
        deep = demand.get("deep_understanding", {})
        tags = demand.get("capability_tags", [])
        context = demand.get("context", {})

        return f"""
- **需求内容**: {surface}
- **需求类型**: {deep.get('type', '未知')}
- **所需能力**: {', '.join(tags) if tags else '未指定'}
- **地点**: {context.get('location', deep.get('location', '未指定'))}
- **动机**: {deep.get('motivation', '未知')}
- **预计人数**: {context.get('expected_attendees', '未指定')}
"""

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析响应.

        增强解析鲁棒性，支持所有必要字段。

        Args:
            response: Raw response string from LLM.

        Returns:
            Parsed response dictionary with all required fields.
        """
        try:
            # 尝试提取 JSON 块（支持 markdown code block）
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接匹配 JSON 对象
                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    json_str = json_match.group()
                else:
                    self._logger.warning("未找到有效 JSON")
                    return self._mock_response({})

            data = json.loads(json_str)

            # 标准化决策类型
            decision = data.get("decision", "decline").lower().strip()
            if decision not in ("participate", "decline", "conditional"):
                decision = "decline"

            # 标准化热情度
            enthusiasm = data.get("enthusiasm_level", "medium").lower().strip()
            if enthusiasm not in ("high", "medium", "low"):
                enthusiasm = "medium"

            # 处理 confidence，确保是有效数字
            confidence = data.get("confidence", 50)
            if isinstance(confidence, str):
                try:
                    confidence = int(confidence)
                except ValueError:
                    confidence = 50
            confidence = max(0, min(100, confidence))  # 限制在 0-100

            return {
                "decision": decision,
                "contribution": data.get("contribution", ""),
                "conditions": data.get("conditions", []),
                "reasoning": data.get("reasoning", ""),
                "decline_reason": data.get("decline_reason", ""),
                "confidence": confidence,
                "enthusiasm_level": enthusiasm,
                "suggested_role": data.get("suggested_role", ""),
            }

        except json.JSONDecodeError as e:
            self._logger.error(f"JSON 解析错误: {e}")
            return self._mock_response({})
        except Exception as e:
            self._logger.error(f"解析响应错误: {e}")
            return self._mock_response({})

    def _mock_response(self, demand: Dict[str, Any]) -> Dict[str, Any]:
        """Mock响应（降级/演示用）.

        当 LLM 调用失败时使用此方法生成中性响应。

        Args:
            demand: The demand to respond to.

        Returns:
            Mock response with all required fields based on simple capability matching.
        """
        # 基于profile简单决策
        capabilities = self.profile.get("capabilities", [])
        tags = self.profile.get("tags", [])
        demand_text = str(demand.get("surface_demand", ""))
        demand_tags = demand.get("capability_tags", [])

        # 处理 capabilities 可能是 dict 的情况
        if isinstance(capabilities, dict):
            cap_list = list(capabilities.keys())
        else:
            cap_list = capabilities if capabilities else []

        # 综合匹配：能力、标签和需求文本
        has_cap_match = any(
            cap.lower() in demand_text.lower() for cap in cap_list
        )
        has_tag_match = any(
            tag in demand_tags for tag in tags
        ) if tags and demand_tags else False

        has_match = has_cap_match or has_tag_match

        if has_match:
            matched_items = []
            for cap in cap_list[:2]:
                if cap and cap.lower() in demand_text.lower():
                    matched_items.append(cap)
            if not matched_items and cap_list:
                matched_items = cap_list[:2]

            contribution = (
                f"可以提供 {', '.join(matched_items)} 方面的支持"
                if matched_items
                else "可以提供相关支持"
            )
            suggested_role = matched_items[0] if matched_items else "参与者"

            return {
                "decision": "participate",
                "contribution": contribution,
                "conditions": [],
                "reasoning": "需求与我的能力匹配",
                "decline_reason": "",
                "confidence": 70,
                "enthusiasm_level": "medium",
                "suggested_role": suggested_role,
            }
        else:
            return {
                "decision": "decline",
                "contribution": "",
                "conditions": [],
                "reasoning": "需求与我的能力不太匹配",
                "decline_reason": "当前能力与需求不匹配，无法提供有效贡献",
                "confidence": 60,
                "enthusiasm_level": "low",
                "suggested_role": "",
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

        self._logger.info(f"正在评审 Channel {channel_id} 的方案")

        if channel_id not in self.active_channels:
            self._logger.warning(f"未知 Channel: {channel_id}")
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
                self._logger.error(f"SecondMe 评估错误: {e}")

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
            self._logger.error(f"LLM 评估错误: {e}")
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
            self._logger.error(f"解析反馈错误: {e}")
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
        self._logger.info(f"用户 {self.user_id} 正在提交需求: {demand_id}")

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
                self._logger.error(f"SecondMe 理解需求错误: {e}")

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
        self._logger.info(f"用户 {self.user_id} 正在处理 Channel {channel_id} 的协作邀请")

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
        self._logger.info(f"用户 {self.user_id} 正在处理 Channel {channel_id} 的方案")

        if channel_id not in self.active_channels:
            self._logger.warning(f"未知 Channel: {channel_id}，正在创建条目")
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
            self._logger.debug(f"未知直接消息类型: {msg_type}")

    # ===== 新增事件发射方法 =====

    async def withdraw(
        self,
        channel_id: str,
        reason: str = "因个人原因需要退出本次协作"
    ) -> Dict[str, Any]:
        """主动退出协商.

        当用户决定不再参与某个协商时调用此方法。
        会发布 towow.agent.withdrawn 事件。

        Args:
            channel_id: Channel ID
            reason: 退出原因

        Returns:
            {
                "success": True/False,
                "channel_id": channel_id,
                "reason": reason
            }
        """
        self._logger.info(f"用户 {self.user_id} 正在退出 Channel {channel_id}: {reason}")

        # 更新本地状态
        if channel_id in self.active_channels:
            self.active_channels[channel_id]["status"] = "withdrawn"
            self.active_channels[channel_id]["withdrawn_at"] = datetime.utcnow().isoformat()
            self.active_channels[channel_id]["withdrawal_reason"] = reason

        # 发布退出事件
        await self._publish_event("towow.agent.withdrawn", {
            "agent_id": self.agent_id,
            "agent_name": self.profile.get("name", self.user_id),
            "reason": reason,
            "demand_id": self.active_channels.get(channel_id, {}).get("demand", {}).get("demand_id"),
            "channel_id": channel_id,
            "withdrawn_at": datetime.utcnow().isoformat()
        })

        # 通知 ChannelAdmin
        await self.send_to_agent("channel_admin", {
            "type": "agent_withdrawn",
            "channel_id": channel_id,
            "agent_id": self.agent_id,
            "reason": reason
        })

        return {
            "success": True,
            "channel_id": channel_id,
            "reason": reason
        }

    async def bargain(
        self,
        channel_id: str,
        offer: str,
        original_terms: Optional[Dict[str, Any]] = None,
        new_terms: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发起讨价还价.

        当用户想要对方案中的某些条款进行协商时调用此方法。
        会发布 towow.negotiation.bargain 事件。

        Args:
            channel_id: Channel ID
            offer: 讨价还价的内容描述
            original_terms: 原始条款（可选）
            new_terms: 希望的新条款（可选）

        Returns:
            {
                "success": True/False,
                "channel_id": channel_id,
                "offer": offer
            }
        """
        self._logger.info(f"用户 {self.user_id} 在 Channel {channel_id} 发起讨价还价")

        demand_id = self.active_channels.get(channel_id, {}).get("demand", {}).get("demand_id")

        # 发布讨价还价事件
        await self._publish_event("towow.negotiation.bargain", {
            "agent_id": self.agent_id,
            "agent_name": self.profile.get("name", self.user_id),
            "offer": offer,
            "original_terms": original_terms or {},
            "new_terms": new_terms or {},
            "demand_id": demand_id,
            "channel_id": channel_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        # 通知 ChannelAdmin
        await self.send_to_agent("channel_admin", {
            "type": "bargain",
            "channel_id": channel_id,
            "agent_id": self.agent_id,
            "offer": offer,
            "original_terms": original_terms,
            "new_terms": new_terms
        })

        return {
            "success": True,
            "channel_id": channel_id,
            "offer": offer
        }

    async def submit_counter_proposal(
        self,
        channel_id: str,
        counter_proposal: Dict[str, Any],
        reason: str = ""
    ) -> Dict[str, Any]:
        """提交反提案.

        当用户对当前方案不满意，想要提出自己的替代方案时调用此方法。
        会发布 towow.negotiation.counter_proposal 事件。

        Args:
            channel_id: Channel ID
            counter_proposal: 反提案内容（应符合 ToWowProposal 结构）
            reason: 提交反提案的原因

        Returns:
            {
                "success": True/False,
                "channel_id": channel_id,
                "counter_proposal": counter_proposal
            }
        """
        self._logger.info(f"用户 {self.user_id} 在 Channel {channel_id} 提交反提案")

        demand_id = self.active_channels.get(channel_id, {}).get("demand", {}).get("demand_id")

        # 发布反提案事件
        await self._publish_event("towow.negotiation.counter_proposal", {
            "agent_id": self.agent_id,
            "agent_name": self.profile.get("name", self.user_id),
            "counter_proposal": counter_proposal,
            "reason": reason,
            "demand_id": demand_id,
            "channel_id": channel_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        # 通知 ChannelAdmin
        await self.send_to_agent("channel_admin", {
            "type": "counter_proposal",
            "channel_id": channel_id,
            "agent_id": self.agent_id,
            "counter_proposal": counter_proposal,
            "reason": reason
        })

        return {
            "success": True,
            "channel_id": channel_id,
            "counter_proposal": counter_proposal
        }

    async def _publish_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """发布事件到事件总线.

        Args:
            event_type: 事件类型
            payload: 事件负载
        """
        try:
            from events.bus import event_bus
            await event_bus.publish({
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": payload
            })
        except ImportError:
            self._logger.debug("事件总线不可用")
        except Exception as e:
            self._logger.error(f"发布事件 {event_type} 失败: {e}")

