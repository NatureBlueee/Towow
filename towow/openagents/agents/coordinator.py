"""
Coordinator Agent - ToWow调度中枢

职责：
1. 接收新需求，调用SecondMe理解需求
2. 决定创建Channel并指派ChannelAdmin
3. 调用LLM进行智能筛选
4. 将筛选结果发送给ChannelAdmin
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .base import TowowBaseAgent, ChannelMessageContext, EventContext

logger = logging.getLogger(__name__)


class CoordinatorAgent(TowowBaseAgent):
    """
    Coordinator Agent

    ToWow系统的调度中枢，负责：
    - 需求接收与理解
    - 智能筛选候选Agent
    - 创建协商Channel
    """

    AGENT_TYPE = "coordinator"

    def __init__(self, secondme_service=None, **kwargs):
        """
        初始化Coordinator Agent

        Args:
            secondme_service: SecondMe服务实例（用于需求理解）
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self.secondme = secondme_service
        self.active_demands: Dict[str, Dict] = {}

    async def on_channel_message(self, ctx: ChannelMessageContext):
        """
        处理Channel消息

        根据消息类型分发到对应处理器
        """
        data = ctx.message.get("data", {})
        msg_type = data.get("type")

        if msg_type == "new_demand":
            await self._handle_new_demand(ctx, data)
        elif msg_type == "subnet_demand":
            await self._handle_subnet_demand(ctx, data)
        elif msg_type == "channel_completed":
            await self._handle_channel_completed(ctx, data)
        else:
            self._logger.debug(f"未知消息类型: {msg_type}")

    async def on_direct(self, ctx: EventContext):
        """
        处理直接消息

        支持通过直接消息发起新需求
        """
        payload = ctx.incoming_event.payload
        content = payload.get("content", {})
        msg_type = content.get("type")

        if msg_type == "new_demand":
            # 将直接消息转换为需求处理
            await self._process_direct_demand(content)
        else:
            self._logger.debug(f"收到直接消息: {content}")

    async def _process_direct_demand(self, content: Dict):
        """处理通过直接消息发送的需求"""
        raw_input = content.get("raw_input", "")
        user_id = content.get("user_id", "anonymous")
        demand_id = content.get("demand_id") or f"d-{uuid4().hex[:8]}"

        # 复用新需求处理逻辑
        understanding = await self._understand_demand(raw_input, user_id)

        self.active_demands[demand_id] = {
            "demand_id": demand_id,
            "raw_input": raw_input,
            "understanding": understanding,
            "status": "filtering",
            "created_at": datetime.utcnow().isoformat()
        }

        await self._publish_event("towow.demand.understood", {
            "demand_id": demand_id,
            "surface_demand": understanding.get("surface_demand"),
            "deep_understanding": understanding.get("deep_understanding"),
            "confidence": understanding.get("confidence", "medium")
        })

        candidates = await self._smart_filter(demand_id, understanding)

        if not candidates:
            self._logger.warning(f"需求 {demand_id} 未找到候选人")
            await self._publish_event("towow.filter.failed", {
                "demand_id": demand_id,
                "reason": "no_candidates"
            })
            return

        channel_id = f"collab-{demand_id[2:]}"
        await self._create_channel(demand_id, channel_id, understanding, candidates)

    async def _handle_new_demand(self, ctx: ChannelMessageContext, data: Dict):
        """
        处理新需求

        流程：
        1. 调用SecondMe理解需求
        2. 存储需求状态
        3. 发布需求理解事件
        4. 智能筛选候选Agent
        5. 创建协商Channel
        """
        raw_input = data.get("raw_input", "")
        user_id = data.get("user_id", "anonymous")
        demand_id = data.get("demand_id") or f"d-{uuid4().hex[:8]}"

        self._logger.info(f"正在处理新需求: {demand_id}")

        # 1. 调用SecondMe理解需求
        understanding = await self._understand_demand(raw_input, user_id)

        # 2. 存储需求
        self.active_demands[demand_id] = {
            "demand_id": demand_id,
            "raw_input": raw_input,
            "understanding": understanding,
            "status": "filtering",
            "created_at": datetime.utcnow().isoformat()
        }

        # 3. 发布需求理解事件
        await self._publish_event("towow.demand.understood", {
            "demand_id": demand_id,
            "surface_demand": understanding.get("surface_demand"),
            "deep_understanding": understanding.get("deep_understanding"),
            "confidence": understanding.get("confidence", "medium")
        })

        # 4. 智能筛选候选Agent
        candidates = await self._smart_filter(demand_id, understanding)

        if not candidates:
            self._logger.warning(f"需求 {demand_id} 未找到候选人")
            await self._publish_event("towow.filter.failed", {
                "demand_id": demand_id,
                "reason": "no_candidates"
            })
            return

        # 5. 创建协商Channel
        channel_id = f"collab-{demand_id[2:]}"
        await self._create_channel(demand_id, channel_id, understanding, candidates)

    async def _understand_demand(
        self, raw_input: str, user_id: str
    ) -> Dict[str, Any]:
        """
        调用SecondMe理解需求

        Args:
            raw_input: 用户原始输入
            user_id: 用户ID

        Returns:
            理解结果字典，包含：
            - surface_demand: 表面需求
            - deep_understanding: 深层理解
            - uncertainties: 不确定点
            - confidence: 置信度
        """
        if self.secondme:
            try:
                result = await self.secondme.understand_demand(raw_input, user_id)
                return result
            except Exception as e:
                self._logger.error(f"SecondMe 错误: {e}")

        # 降级：直接返回原始输入
        return {
            "surface_demand": raw_input,
            "deep_understanding": {"motivation": "unknown"},
            "uncertainties": [],
            "confidence": "low"
        }

    async def _smart_filter(
        self, demand_id: str, understanding: Dict
    ) -> List[Dict]:
        """
        智能筛选候选Agent

        Args:
            demand_id: 需求ID
            understanding: 需求理解结果

        Returns:
            候选Agent列表，每个包含：
            - agent_id: Agent ID
            - reason: 筛选理由
            - relevance_score: 相关性分数
        """
        if not self.llm:
            self._logger.warning("未配置 LLM 服务，使用模拟筛选")
            return self._mock_filter(understanding)

        # 获取所有可用Agent的能力（从数据库）
        available_agents = await self._get_available_agents()

        if not available_agents:
            self._logger.info("数据库中没有可用 Agent，使用模拟筛选")
            return self._mock_filter(understanding)

        # 构建筛选提示词
        prompt = self._build_filter_prompt(understanding, available_agents)

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是ToWow的智能筛选系统，负责为需求匹配最合适的Agent。",
                fallback_key="smart_filter"
            )
            return self._parse_filter_response(response, available_agents)
        except Exception as e:
            self._logger.error(f"LLM 筛选错误: {e}")
            return self._mock_filter(understanding)

    def _build_filter_prompt(
        self, understanding: Dict, agents: List[Dict]
    ) -> str:
        """
        构建智能筛选提示词

        基于提示词2：智能筛选
        根据需求理解结果，从候选Agent池中筛选最匹配的参与者

        Args:
            understanding: 需求理解结果
            agents: 可用Agent列表

        Returns:
            提示词字符串
        """
        surface_demand = understanding.get('surface_demand', '')
        deep = understanding.get('deep_understanding', {})

        return f"""
# 智能筛选任务

你是ToWow协作平台的智能筛选系统。你的任务是根据用户需求，从候选Agent池中筛选出最适合参与协作的人选。

## 需求信息

### 表面需求
{surface_demand}

### 深层理解
- **动机**: {deep.get('motivation', '未知')}
- **需求类型**: {deep.get('type', 'general')}
- **关键词**: {', '.join(deep.get('keywords', []))}
- **地点**: {deep.get('location', '未指定')}
- **规模**: {json.dumps(deep.get('scale', {}), ensure_ascii=False)}
- **时间线**: {json.dumps(deep.get('timeline', {}), ensure_ascii=False)}
- **资源需求**: {', '.join(deep.get('resource_requirements', []))}

### 不确定点
{json.dumps(understanding.get('uncertainties', []), ensure_ascii=False)}

## 候选Agent池
```json
{json.dumps(agents, ensure_ascii=False, indent=2)}
```

## 筛选原则

1. **能力匹配优先**：Agent的capabilities应与需求的资源需求匹配
2. **地域相关性**：考虑Agent的location与需求地点的兼容性
3. **多样性互补**：选择能力互补的组合，避免过于同质化
4. **规模适配**：根据需求规模控制候选人数（小规模3-5人，中等5-8人，大规模8-12人）
5. **关键角色优先**：确保核心能力（如场地、技术、组织）有人覆盖

## 筛选维度说明

对每个候选人，请评估：
- **直接匹配度**：能力与需求的直接相关程度（0-100）
- **间接价值**：可能带来的额外价值（资源、人脉等）
- **可用性风险**：基于其描述判断响应可能性

## 输出要求

请以JSON格式输出筛选结果：

```json
{{
  "candidates": [
    {{
      "agent_id": "Agent的ID",
      "reason": "选择该Agent的具体理由（30字以内）",
      "relevance_score": 85,
      "expected_role": "预期角色（如：场地提供者、技术顾问等）",
      "match_dimensions": {{
        "capability_match": 90,
        "location_fit": 80,
        "indirect_value": 70
      }}
    }}
  ],
  "filtering_logic": "整体筛选逻辑说明（描述为什么选择这个组合）",
  "coverage_analysis": {{
    "covered_requirements": ["已覆盖的资源需求"],
    "uncovered_requirements": ["未覆盖的资源需求"],
    "suggested_actions": ["建议采取的补充行动"]
  }}
}}
```

## 注意事项
- 候选人数量应在3-12人之间
- relevance_score越高表示匹配度越高
- 优先选择relevance_score >= 70的候选人
- 如果某个关键需求无人覆盖，请在coverage_analysis中说明
"""

    def _parse_filter_response(
        self, response: str, agents: List[Dict]
    ) -> List[Dict]:
        """
        解析筛选响应

        Args:
            response: LLM响应文本
            agents: 可用Agent列表（用于验证）

        Returns:
            有效的候选Agent列表
        """
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                candidates = data.get("candidates", [])
                # 验证agent_id存在
                valid_ids = {a["agent_id"] for a in agents}
                return [c for c in candidates if c.get("agent_id") in valid_ids]
        except Exception as e:
            self._logger.error(f"解析筛选响应错误: {e}")
        return []

    def _mock_filter(self, understanding: Dict) -> List[Dict]:
        """
        Mock筛选（演示用）

        当没有LLM服务或数据库时使用

        Args:
            understanding: 需求理解结果

        Returns:
            模拟的候选Agent列表
        """
        return [
            {
                "agent_id": "user_agent_bob",
                "reason": "场地资源",
                "relevance_score": 90
            },
            {
                "agent_id": "user_agent_alice",
                "reason": "技术分享能力",
                "relevance_score": 85
            },
            {
                "agent_id": "user_agent_charlie",
                "reason": "活动策划经验",
                "relevance_score": 80
            }
        ]

    async def _get_available_agents(self) -> List[Dict]:
        """
        获取可用Agent列表

        从数据库获取所有活跃的Agent Profile

        Returns:
            Agent信息列表
        """
        if self.db:
            try:
                from database.services import AgentProfileService
                service = AgentProfileService(self.db)
                profiles = await service.list_active()
                return [
                    {
                        "agent_id": p.id,
                        "display_name": p.name,
                        "capabilities": p.capabilities,
                        "description": p.description
                    }
                    for p in profiles
                ]
            except Exception as e:
                self._logger.error(f"数据库错误: {e}")
        return []

    async def _create_channel(
        self,
        demand_id: str,
        channel_id: str,
        understanding: Dict,
        candidates: List[Dict]
    ):
        """
        创建协商Channel

        Args:
            demand_id: 需求ID
            channel_id: Channel ID
            understanding: 需求理解结果
            candidates: 候选Agent列表
        """
        self._logger.info(
            f"正在创建协商 Channel {channel_id}，候选人数: {len(candidates)}"
        )

        # 发布筛选完成事件
        await self._publish_event("towow.filter.completed", {
            "demand_id": demand_id,
            "channel_id": channel_id,
            "candidates": candidates
        })

        # 通知ChannelAdmin
        await self.send_to_agent("channel_admin", {
            "type": "create_channel",
            "demand_id": demand_id,
            "channel_id": channel_id,
            "demand": understanding,
            "candidates": candidates
        })

        # 更新需求状态
        if demand_id in self.active_demands:
            self.active_demands[demand_id]["status"] = "negotiating"
            self.active_demands[demand_id]["channel_id"] = channel_id

    async def _handle_subnet_demand(
        self, ctx: ChannelMessageContext, data: Dict
    ):
        """
        处理子网需求

        子网需求用于递归协商场景

        Args:
            ctx: Channel消息上下文
            data: 消息数据
        """
        sub_demand = data.get("demand", {})
        parent_channel_id = data.get("parent_channel_id")
        recursion_depth = data.get("recursion_depth", 1)

        self._logger.info(f"正在处理子网需求，递归深度={recursion_depth}")

        # 简化处理：直接筛选并创建子Channel
        candidates = await self._smart_filter(
            data.get("sub_channel_id", ""),
            sub_demand
        )

        if candidates:
            await self.send_to_agent("channel_admin", {
                "type": "create_channel",
                "demand_id": data.get("sub_channel_id"),
                "channel_id": data.get("sub_channel_id"),
                "demand": sub_demand,
                "candidates": candidates,
                "is_subnet": True,
                "parent_channel_id": parent_channel_id,
                "recursion_depth": recursion_depth
            })

    async def _handle_channel_completed(
        self, ctx: ChannelMessageContext, data: Dict
    ):
        """
        处理Channel完成

        Args:
            ctx: Channel消息上下文
            data: 消息数据
        """
        demand_id = data.get("demand_id")
        success = data.get("success", False)
        proposal = data.get("proposal")

        if demand_id in self.active_demands:
            self.active_demands[demand_id]["status"] = (
                "completed" if success else "failed"
            )
            self.active_demands[demand_id]["final_proposal"] = proposal

        self._logger.info(f"需求 {demand_id} 已完成，成功={success}")

        # 发布完成事件
        await self._publish_event("towow.demand.completed", {
            "demand_id": demand_id,
            "success": success,
            "proposal": proposal
        })

    async def _publish_event(self, event_type: str, payload: Dict):
        """
        发布事件到事件总线

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
            self._logger.error(f"发布事件失败: {e}")

    def get_demand_status(self, demand_id: str) -> Optional[Dict]:
        """
        获取需求状态

        Args:
            demand_id: 需求ID

        Returns:
            需求状态字典，如果不存在返回None
        """
        return self.active_demands.get(demand_id)

    def list_active_demands(self) -> List[Dict]:
        """
        列出所有活跃需求

        Returns:
            活跃需求列表
        """
        return [
            demand for demand in self.active_demands.values()
            if demand.get("status") in ["filtering", "negotiating"]
        ]
