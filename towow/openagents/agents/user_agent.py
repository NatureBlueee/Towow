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

v4 变更 (TASK-T03):
- 新增 response_type: "offer" | "negotiate" 响应类型区分
- 新增 NegotiationPoint 数据类，支持协商要点
- 新增 message_id 支持幂等处理
"""
from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from .base import TowowBaseAgent


# ============================================================================
# v4 数据类定义 - TASK-T03
# ============================================================================

@dataclass
class NegotiationPoint:
    """协商要点 - 当 response_type 为 negotiate 时使用."""

    aspect: str           # 协商方面（如：时间安排、角色分工、资源分配）
    current_value: str    # 当前值（方案中的现状）
    desired_value: str    # 期望值（希望调整为）
    reason: str           # 调整原因

    def to_dict(self) -> Dict[str, str]:
        """转换为字典."""
        return {
            "aspect": self.aspect,
            "current_value": self.current_value,
            "desired_value": self.desired_value,
            "reason": self.reason,
        }


@dataclass
class OfferResponse:
    """Agent 响应 - v4 完整响应结构."""

    offer_id: str
    agent_id: str
    display_name: str
    demand_id: str

    # [v4新增] 响应类型：offer（直接提交方案）或 negotiate（希望讨价还价）
    response_type: Literal["offer", "negotiate"]
    decision: Literal["participate", "decline", "conditional"]

    # 贡献与条件
    contribution: Optional[str] = None
    conditions: List[str] = field(default_factory=list)

    # [v4新增] 协商要点，negotiate 类型时填充
    negotiation_points: List[NegotiationPoint] = field(default_factory=list)

    # 理由与附加信息
    reasoning: str = ""
    decline_reason: Optional[str] = None
    confidence: int = 0  # 0-100 置信度
    enthusiasm_level: str = "medium"  # high/medium/low
    suggested_role: str = ""

    # [v4新增] 幂等ID，用于消息去重
    message_id: str = ""
    submitted_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于消息传递."""
        return {
            "offer_id": self.offer_id,
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "demand_id": self.demand_id,
            "response_type": self.response_type,
            "decision": self.decision,
            "contribution": self.contribution,
            "conditions": self.conditions,
            "negotiation_points": [p.to_dict() for p in self.negotiation_points],
            "reasoning": self.reasoning,
            "decline_reason": self.decline_reason,
            "confidence": self.confidence,
            "enthusiasm_level": self.enthusiasm_level,
            "suggested_role": self.suggested_role,
            "message_id": self.message_id,
            "timestamp": self.submitted_at,
        }

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
        # 幂等性控制：已处理的消息
        self._processed_messages: Dict[str, float] = {}  # message_key -> timestamp
        self._max_processed_messages = 500

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

        v4 更新：支持 response_type、negotiation_points、message_id，发布 SSE 事件

        Args:
            ctx: Channel message context.
            data: Message data containing demand information.
        """
        channel_id = data.get("channel_id", "")
        demand = data.get("demand", {})
        filter_reason = data.get("filter_reason", "")
        round_num = data.get("round", 1)  # [v4] 当前轮次
        match_score = data.get("match_score", 50)  # [v4] 匹配度

        self._logger.info(f"收到 Channel {channel_id} 的需求邀请 (轮次: {round_num})")

        # 记录参与信息
        self.active_channels[channel_id] = {
            "demand": demand,
            "status": "evaluating",
            "received_at": datetime.utcnow().isoformat(),
            "round": round_num,
        }

        # 调用SecondMe或LLM生成响应
        response = await self._generate_response(demand, filter_reason)

        # 确保 message_id 存在（v4 幂等支持）
        if "message_id" not in response:
            response["message_id"] = f"msg-{uuid4().hex[:12]}"

        # 更新状态
        self.active_channels[channel_id]["response"] = response
        self.active_channels[channel_id]["status"] = "responded"

        # 获取 display_name
        display_name = self.profile.get("name", self.user_id)

        # 发送响应给ChannelAdmin（v4 格式）
        await self.send_to_agent(
            "channel_admin",
            {
                "type": "offer_response",
                "channel_id": channel_id,
                "agent_id": self.agent_id,
                "display_name": display_name,
                "response_type": response.get("response_type", "offer"),  # [v4新增]
                "decision": response.get("decision", "participate"),
                "contribution": response.get("contribution"),
                "conditions": response.get("conditions", []),
                "reasoning": response.get("reasoning", ""),
                "decline_reason": response.get("decline_reason"),
                "negotiation_points": response.get("negotiation_points", []),  # [v4新增]
                "message_id": response.get("message_id", ""),  # [v4新增]
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # [v4新增] 发布 SSE 事件 towow.offer.submitted
        await self._emit_offer_submitted_event(
            channel_id=channel_id,
            demand=demand,
            response=response,
            display_name=display_name,
        )

    async def _emit_offer_submitted_event(
        self,
        channel_id: str,
        demand: Dict[str, Any],
        response: Dict[str, Any],
        display_name: str,
    ) -> None:
        """发布 towow.offer.submitted SSE 事件（v4 新增）.

        Args:
            channel_id: Channel ID
            demand: 需求信息
            response: 响应信息
            display_name: Agent 显示名称
        """
        from towow.events.bus import event_bus, Event

        # 汇总协商要点
        negotiation_summary = self._summarize_negotiation_points(
            response.get("negotiation_points", [])
        )

        event = Event.create(
            event_type="towow.offer.submitted",
            payload={
                "channel_id": channel_id,
                "demand_id": demand.get("demand_id", ""),
                "agent_id": self.agent_id,
                "display_name": display_name,
                "response_type": response.get("response_type", "offer"),
                "decision": response.get("decision", "participate"),
                "contribution": response.get("contribution"),
                "negotiation_summary": negotiation_summary,
            }
        )

        try:
            await event_bus.publish(event)
            self._logger.debug(f"已发布 SSE 事件: {event.event_type}")
        except Exception as e:
            self._logger.error(f"发布 SSE 事件失败: {e}")

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

        基于提示词 3：响应生成（TECH-v4 3.3.3）
        v4 变更：支持 response_type 区分 offer/negotiate，新增 negotiation_points

        Args:
            demand: The demand to respond to.
            filter_reason: Reason why this user was selected.

        Returns:
            Response containing decision, contribution, conditions, reasoning,
            decline_reason, confidence, enthusiasm_level, suggested_role,
            response_type, negotiation_points, and message_id.
        """
        # 生成幂等消息ID
        message_id = f"msg-{uuid4().hex[:12]}"

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
  "response_type": "offer | negotiate",
  "decision": "participate | decline | conditional",
  "contribution": "如果参与，具体说明你能贡献什么（详细描述，包含时间、资源等）",
  "conditions": ["如果是 conditional，列出每一个条件"],
  "reasoning": "你做出这个决定的理由（50字以内）",
  "decline_reason": "如果是 decline，说明原因",
  "confidence": 80,
  "enthusiasm_level": "high | medium | low",
  "suggested_role": "你建议自己在协作中承担的角色",
  "negotiation_points": [
    {{
      "aspect": "协商方面（如：时间安排、角色分工）",
      "current_value": "当前方案中的值",
      "desired_value": "你期望调整为的值",
      "reason": "希望调整的原因"
    }}
  ]
}}
```

## 响应类型说明

- **offer**: 直接提交你的方案，愿意按照当前需求参与
- **negotiate**: 你想讨价还价，有些地方希望调整，需要填写 negotiation_points

## 决策类型说明

- **participate**: 愿意参与，能够贡献
- **conditional**: 愿意参与，但有条件
- **decline**: 不参与（能力不匹配、时间冲突、兴趣不合等）

注意：
- 如果你完全同意需求，使用 response_type="offer"
- 如果你想参与但希望调整某些方面，使用 response_type="negotiate"，并填写 negotiation_points
- 请站在 {self.profile.get('name', self.user_id)} 的角度思考，基于其真实能力和偏好做出决策
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system=self._get_response_system_prompt(),
                fallback_key="response_generation",
                max_tokens=1500,
                temperature=0.5,
            )
            result = self._parse_response(response)
            # 注入 message_id（v4 幂等支持）
            result["message_id"] = message_id
            return result
        except Exception as e:
            self._logger.error(f"LLM 响应错误: {e}")
            return self._get_fallback_response(demand, message_id)

    def _get_response_system_prompt(self) -> str:
        """获取响应生成系统提示词.

        v4 更新：支持 response_type 和 negotiation_points
        """
        return """你是一个数字分身系统，代表用户做出合理的协作决策。

关键原则：
1. 基于用户档案做出符合用户性格和能力的决策
2. 不要过度承诺用户能力范围外的事情
3. 如果需求与用户能力不匹配，应该 decline
4. 如果部分匹配但有顾虑，使用 conditional
5. 如果想参与但希望调整某些方面，使用 response_type="negotiate" 并填写 negotiation_points
6. 始终以有效的 JSON 格式输出

响应类型选择：
- response_type="offer"：完全同意需求，直接提交方案
- response_type="negotiate"：想参与但希望调整某些方面，需要填写 negotiation_points"""

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
        v4 更新：支持 response_type 和 negotiation_points

        Args:
            response: Raw response string from LLM.

        Returns:
            Parsed response dictionary with all required fields including v4 fields.
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

            # [v4新增] 标准化响应类型
            response_type = data.get("response_type", "offer").lower().strip()
            if response_type not in ("offer", "negotiate"):
                response_type = "offer"

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

            # [v4新增] 解析协商要点
            negotiation_points = []
            raw_points = data.get("negotiation_points", [])
            if response_type == "negotiate" and raw_points:
                for p in raw_points:
                    if isinstance(p, dict):
                        negotiation_points.append({
                            "aspect": p.get("aspect", ""),
                            "current_value": p.get("current_value", ""),
                            "desired_value": p.get("desired_value", ""),
                            "reason": p.get("reason", ""),
                        })

            return {
                "response_type": response_type,  # [v4新增]
                "decision": decision,
                "contribution": data.get("contribution", ""),
                "conditions": data.get("conditions", []),
                "reasoning": data.get("reasoning", ""),
                "decline_reason": data.get("decline_reason", ""),
                "confidence": confidence,
                "enthusiasm_level": enthusiasm,
                "suggested_role": data.get("suggested_role", ""),
                "negotiation_points": negotiation_points,  # [v4新增]
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
        v4 更新：新增 response_type 和 negotiation_points 字段

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
                "response_type": "offer",  # [v4新增]
                "decision": "participate",
                "contribution": contribution,
                "conditions": [],
                "reasoning": "需求与我的能力匹配",
                "decline_reason": "",
                "confidence": 70,
                "enthusiasm_level": "medium",
                "suggested_role": suggested_role,
                "negotiation_points": [],  # [v4新增]
            }
        else:
            return {
                "response_type": "offer",  # [v4新增]
                "decision": "decline",
                "contribution": "",
                "conditions": [],
                "reasoning": "需求与我的能力不太匹配",
                "decline_reason": "当前能力与需求不匹配，无法提供有效贡献",
                "confidence": 60,
                "enthusiasm_level": "low",
                "suggested_role": "",
                "negotiation_points": [],  # [v4新增]
            }

    def _get_fallback_response(
        self,
        demand: Dict[str, Any],
        message_id: str
    ) -> Dict[str, Any]:
        """降级响应（v4 新增）.

        当 LLM 调用失败时使用此方法生成降级响应，包含 message_id。

        Args:
            demand: The demand to respond to.
            message_id: 幂等消息ID

        Returns:
            Fallback response with all required fields including message_id.
        """
        base_response = self._mock_response(demand)
        base_response["message_id"] = message_id
        return base_response

    def _summarize_negotiation_points(
        self,
        negotiation_points: List[Dict[str, str]]
    ) -> Optional[str]:
        """汇总协商要点（v4 新增）.

        Args:
            negotiation_points: 协商要点列表

        Returns:
            协商要点摘要字符串，无要点时返回 None
        """
        if not negotiation_points:
            return None
        return "; ".join([
            f"{p.get('aspect', '')}: 期望{p.get('desired_value', '')}"
            for p in negotiation_points
        ])

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
        """
        [v4优化] 使用LLM评估方案

        支持的反馈类型：
        - accept: 接受方案
        - reject: 拒绝方案
        - negotiate: 希望继续协商（需要提供调整请求）
        - withdraw: 退出协商（不再参与）

        Args:
            proposal: The proposal to evaluate.

        Returns:
            Feedback containing feedback_type, adjustment_request, reasoning,
            and negotiation_points (for negotiate type).
        """
        # 找到自己在方案中的角色
        my_assignment = None
        for assignment in proposal.get("assignments", []):
            if assignment.get("agent_id") == self.agent_id:
                my_assignment = assignment
                break

        assignment_json = (
            json.dumps(my_assignment, ensure_ascii=False, indent=2)
            if my_assignment
            else "未分配具体角色"
        )

        # 构建档案摘要
        profile_summary = self._build_profile_summary()

        # 获取当前轮次信息（从 active_channels 或 proposal）
        round_info = ""
        for channel_data in self.active_channels.values():
            if channel_data.get("proposal") == proposal:
                round_num = channel_data.get("round", 1)
                round_info = f"当前第 {round_num} 轮协商"
                break

        prompt = f"""
# 方案评审任务

## 你的身份
你是用户 **{self.profile.get('name', self.user_id)}** 的数字分身。
你需要代表用户评估这个协作方案，并决定如何响应。

## 你的档案
{profile_summary}

## 协作方案
```json
{json.dumps(proposal, ensure_ascii=False, indent=2)}
```

## 你在方案中的角色
```json
{assignment_json}
```

{round_info}

## 评估任务

请根据以下原则评估方案：

1. **角色匹配原则**：你的角色分配是否与你的能力匹配？
2. **条件满足原则**：你之前提出的条件是否被满足？
3. **公平性原则**：任务分配是否公平合理？
4. **可行性原则**：方案整体是否可执行？

## 输出格式

请以 JSON 格式输出你的反馈：

```json
{{
  "feedback_type": "accept | reject | negotiate | withdraw",
  "adjustment_request": "如果是 negotiate，详细说明希望如何调整",
  "reasoning": "你做出这个决定的理由（50字以内）",
  "concerns": ["如果有顾虑，列出每一条"],
  "negotiation_points": [
    {{
      "aspect": "需要调整的方面",
      "current_value": "当前方案中的值",
      "desired_value": "你期望的值",
      "reason": "调整原因"
    }}
  ],
  "satisfaction_score": 80
}}
```

## 反馈类型说明

- **accept**: 完全接受方案，愿意按照分配参与
- **reject**: 拒绝方案，不愿意按照当前分配参与（但仍在协商中）
- **negotiate**: 有条件地接受，希望调整某些方面后再确认
- **withdraw**: 退出协商，不再参与本次协作（永久退出）

## 决策建议

- 如果角色分配合理且条件被满足 → 使用 **accept**
- 如果角色分配不合理但可以调整 → 使用 **negotiate**
- 如果方案根本不可接受但想再看看调整 → 使用 **reject**
- 如果决定不再参与这次协作 → 使用 **withdraw**

注意：
- **withdraw** 是永久性的，一旦选择就不会再收到后续方案
- 尽量使用 **negotiate** 而非 **reject**，以促进协商进展
- 请站在 {self.profile.get('name', self.user_id)} 的角度思考
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system=self._get_feedback_system_prompt(),
                fallback_key="proposal_evaluation",
                max_tokens=1500,
                temperature=0.4
            )
            return self._parse_feedback_v4(response)
        except Exception as e:
            self._logger.error(f"LLM 评估错误: {e}")
            return self._mock_feedback(proposal)

    def _get_feedback_system_prompt(self) -> str:
        """[v4] 获取反馈评估系统提示词"""
        return """你是一个数字分身系统，代表用户评估协作方案。

关键原则：
1. 基于用户档案做出符合用户性格和能力的决策
2. 优先选择 accept 或 negotiate，促进协商进展
3. 只有在方案完全不可接受时才选择 reject
4. 只有在决定永久退出时才选择 withdraw
5. negotiate 时必须提供具体的 adjustment_request 和 negotiation_points
6. 始终以有效的 JSON 格式输出

反馈类型使用建议：
- accept: 方案可接受，同意参与
- negotiate: 方案基本可行，但需要调整某些方面
- reject: 方案当前不可接受，但愿意看调整后的方案
- withdraw: 决定不再参与本次协作（慎用）"""

    def _parse_feedback_v4(self, response: str) -> Dict[str, Any]:
        """
        [v4] 解析反馈响应

        支持 accept/reject/negotiate/withdraw 四种类型

        Args:
            response: Raw response string from LLM.

        Returns:
            Parsed feedback dictionary.
        """
        try:
            # 尝试提取 JSON 块
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    json_str = json_match.group()
                else:
                    self._logger.warning("未找到有效 JSON")
                    return self._mock_feedback({})

            data = json.loads(json_str)

            # 标准化反馈类型
            feedback_type = data.get("feedback_type", "accept").lower().strip()
            if feedback_type not in ("accept", "reject", "negotiate", "withdraw"):
                feedback_type = "accept"

            # 解析协商要点
            negotiation_points = []
            if feedback_type == "negotiate" and data.get("negotiation_points"):
                for point in data.get("negotiation_points", []):
                    if isinstance(point, dict):
                        negotiation_points.append({
                            "aspect": point.get("aspect", ""),
                            "current_value": point.get("current_value", ""),
                            "desired_value": point.get("desired_value", ""),
                            "reason": point.get("reason", "")
                        })

            return {
                "feedback_type": feedback_type,
                "adjustment_request": data.get("adjustment_request", ""),
                "reasoning": data.get("reasoning", ""),
                "concerns": data.get("concerns", []),
                "negotiation_points": negotiation_points,
                "satisfaction_score": data.get("satisfaction_score", 50)
            }

        except json.JSONDecodeError as e:
            self._logger.error(f"JSON 解析错误: {e}")
            return self._mock_feedback({})
        except Exception as e:
            self._logger.error(f"解析反馈错误: {e}")
            return self._mock_feedback({})

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
        - demand_offer: 需求offer（ChannelAdmin 广播）
        - negotiation_completed: 协商完成通知

        Args:
            ctx: Event context
        """
        import time

        payload = ctx.incoming_event.payload if hasattr(ctx, 'incoming_event') else {}
        content = payload.get("content", {})

        # 支持直接在 payload 中的消息格式
        data = content if isinstance(content, dict) else payload
        msg_type = data.get("type")
        channel_id = data.get("channel_id", "")

        # 生成消息唯一键用于幂等性检查
        message_key = f"{msg_type}:{channel_id}"
        current_time = time.time()

        # 清理过期的消息记录（超过 10 秒）
        expired_keys = [
            k for k, t in self._processed_messages.items()
            if current_time - t > 10.0
        ]
        for k in expired_keys:
            del self._processed_messages[k]

        # 幂等性检查：防止重复处理同一消息
        if message_key in self._processed_messages:
            self._logger.warning(f"[USER_AGENT] Duplicate message detected: {message_key}, skipping")
            return

        # 标记为已处理
        self._processed_messages[message_key] = current_time

        # 限制记录数量
        if len(self._processed_messages) > self._max_processed_messages:
            oldest_key = min(self._processed_messages, key=self._processed_messages.get)
            del self._processed_messages[oldest_key]

        self._logger.info(f"[USER_AGENT] on_direct received msg_type={msg_type}")

        if msg_type == "collaboration_invite":
            await self.handle_invite(
                channel_id=data.get("channel_id", ""),
                demand=data.get("demand", {}),
                filter_reason=data.get("filter_reason", "")
            )
        elif msg_type == "proposal_review":
            # 检查是否已经完成协商
            if channel_id in self.active_channels:
                status = self.active_channels[channel_id].get("status", "")
                if status in ("completed", "failed", "feedback_sent"):
                    self._logger.warning(
                        f"[USER_AGENT] Channel {channel_id} status={status}, ignoring proposal_review"
                    )
                    return
            await self.handle_proposal(
                channel_id=channel_id,
                proposal=data.get("proposal", {})
            )
        elif msg_type == "demand_offer":
            # ChannelAdmin 广播的需求邀请
            demand = data.get("demand", {})
            filter_reason = data.get("filter_reason", "")

            # 检查是否已经响应过
            if channel_id in self.active_channels:
                status = self.active_channels[channel_id].get("status", "")
                if status in ("responded", "completed", "failed"):
                    self._logger.warning(
                        f"[USER_AGENT] Channel {channel_id} status={status}, ignoring demand_offer"
                    )
                    return

            self._logger.info(f"[USER_AGENT] Handling demand_offer for channel={channel_id}")

            # 记录参与信息
            self.active_channels[channel_id] = {
                "demand": demand,
                "status": "evaluating",
                "received_at": datetime.utcnow().isoformat(),
            }

            # 生成响应
            response = await self._generate_response(demand, filter_reason)

            # 更新状态
            self.active_channels[channel_id]["response"] = response
            self.active_channels[channel_id]["status"] = "responded"

            self._logger.info(f"[USER_AGENT] Generated response: decision={response.get('decision')}")

            # 发送响应给 ChannelAdmin
            await self.send_to_agent(
                "channel_admin",
                {
                    "type": "offer_response",
                    "channel_id": channel_id,
                    "agent_id": self.agent_id,
                    "display_name": self.profile.get("name", self.user_id),
                    **response,
                },
            )
        elif msg_type == "negotiation_completed":
            # 协商完成通知
            channel_id = data.get("channel_id", "")
            success = data.get("success", False)
            self._logger.info(f"[USER_AGENT] Negotiation completed for channel={channel_id}, success={success}")
            if channel_id in self.active_channels:
                self.active_channels[channel_id]["status"] = "completed" if success else "failed"
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

