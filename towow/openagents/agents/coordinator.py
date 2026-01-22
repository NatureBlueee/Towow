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

        logger.info("[COORD] _process_direct_demand START demand_id=%s", demand_id)

        # 复用新需求处理逻辑
        logger.info("[COORD] Step 1: _understand_demand demand_id=%s", demand_id)
        understanding = await self._understand_demand(raw_input, user_id)
        logger.info("[COORD] Step 1 DONE: confidence=%s", understanding.get("confidence", "unknown"))

        self.active_demands[demand_id] = {
            "demand_id": demand_id,
            "raw_input": raw_input,
            "understanding": understanding,
            "status": "filtering",
            "created_at": datetime.utcnow().isoformat()
        }

        logger.info("[COORD] Publishing towow.demand.understood event demand_id=%s", demand_id)
        await self._publish_event("towow.demand.understood", {
            "demand_id": demand_id,
            "surface_demand": understanding.get("surface_demand"),
            "deep_understanding": understanding.get("deep_understanding"),
            "confidence": understanding.get("confidence", "medium")
        })

        logger.info("[COORD] Step 2: _smart_filter demand_id=%s", demand_id)
        candidates = await self._smart_filter(demand_id, understanding)
        logger.info("[COORD] Step 2 DONE: candidates_count=%d", len(candidates) if candidates else 0)

        if not candidates:
            logger.warning("[COORD] No candidates found for demand_id=%s", demand_id)
            await self._publish_event("towow.filter.failed", {
                "demand_id": demand_id,
                "reason": "no_candidates"
            })
            return

        channel_id = f"collab-{demand_id[2:]}"
        logger.info("[COORD] Step 3: _create_channel channel_id=%s, candidates=%d",
                    channel_id, len(candidates))
        await self._create_channel(demand_id, channel_id, understanding, candidates)
        logger.info("[COORD] _process_direct_demand COMPLETED demand_id=%s", demand_id)

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

        基于提示词 2：智能筛选
        从 Agent 池中筛选出 3-15 个高相关候选人

        Args:
            demand_id: 需求ID
            understanding: 需求理解结果

        Returns:
            候选Agent列表，每个包含：
            - agent_id: Agent ID
            - display_name: 显示名称
            - reason: 筛选理由
            - relevance_score: 相关性分数 (0-100)
            - expected_role: 预期角色
        """
        logger.info("[COORD] _smart_filter START demand_id=%s", demand_id)

        # 检查 LLM 服务
        if not self.llm:
            logger.warning("[COORD] LLM service unavailable, using mock filter")
            return self._mock_filter(understanding)

        # 获取所有可用Agent的能力（从数据库）
        logger.info("[COORD] Getting available agents from database")
        available_agents = await self._get_available_agents()
        logger.info("[COORD] Got %d available agents", len(available_agents) if available_agents else 0)

        if not available_agents:
            logger.warning("[COORD] No available agents, using mock data")
            return self._mock_filter(understanding)

        # 构建筛选提示词
        prompt = self._build_filter_prompt(understanding, available_agents)

        try:
            # 调用 LLM 进行智能筛选
            logger.info("[COORD] Calling LLM for smart filter")
            response = await self.llm.complete(
                prompt=prompt,
                system=self._get_filter_system_prompt(),
                fallback_key="smart_filter",
                max_tokens=4000,
                temperature=0.3  # 降低随机性，提高一致性
            )
            logger.info("[COORD] LLM response received, length=%d", len(response) if response else 0)

            # 解析响应
            candidates = self._parse_filter_response(response, available_agents)
            logger.info("[COORD] Parsed %d candidates from LLM response", len(candidates))

            if not candidates:
                logger.warning("[COORD] LLM filter returned no candidates, using mock")
                return self._mock_filter(understanding)

            logger.info("[COORD] _smart_filter DONE, found %d candidates", len(candidates))
            return candidates

        except Exception as e:
            logger.error("[COORD] _smart_filter FAILED: %s", str(e), exc_info=True)
            return self._mock_filter(understanding)

    def _get_filter_system_prompt(self) -> str:
        """获取筛选系统提示词"""
        return """你是 ToWow 协作平台的智能筛选系统。

你的任务是根据用户需求，从候选 Agent 池中筛选出最适合参与协作的人选。

筛选原则：
1. 能力匹配优先：Agent 的 capabilities 应与需求的资源需求匹配
2. 地域相关性：考虑 Agent 的 location 与需求地点的兼容性
3. 多样性互补：选择能力互补的组合，避免过于同质化
4. 规模适配：根据需求规模控制候选人数（小规模 3-5 人，中等 5-8 人，大规模 8-12 人）
5. 关键角色优先：确保核心能力（如场地、技术、组织）有人覆盖

重要：
- 候选人数量应在 3-15 人之间
- 优先选择 relevance_score >= 70 的候选人
- 始终以有效的 JSON 格式输出"""

    def _build_filter_prompt(
        self, understanding: Dict, agents: List[Dict]
    ) -> str:
        """
        构建智能筛选提示词

        基于 TECH 文档 3.3.2 节的提示词模板
        根据需求理解结果，从候选Agent池中筛选最匹配的参与者

        Args:
            understanding: 需求理解结果
            agents: 可用Agent列表

        Returns:
            提示词字符串
        """
        surface_demand = understanding.get('surface_demand', '')
        deep = understanding.get('deep_understanding', {})
        capability_tags = understanding.get('capability_tags', [])

        # 格式化 Agent 信息（限制每个 Agent 的信息量）
        agent_summaries = []
        for agent in agents[:50]:  # 最多处理 50 个 Agent
            summary = {
                "agent_id": agent.get("agent_id"),
                "display_name": agent.get("display_name", agent.get("agent_id")),
                "capabilities": agent.get("capabilities", [])[:5],  # 最多 5 个能力
                "location": agent.get("location", "未知"),
                "summary": (agent.get("description", "") or "")[:100]  # 限制描述长度
            }
            agent_summaries.append(summary)

        return f"""
# 智能筛选任务

## 需求信息

### 表面需求
{surface_demand}

### 深层理解
- **动机**: {deep.get('motivation', '未知')}
- **需求类型**: {deep.get('type', 'general')}
- **关键能力标签**: {', '.join(capability_tags) if capability_tags else '未指定'}
- **地点**: {deep.get('location', '未指定')}
- **规模**: {json.dumps(deep.get('scale', {}), ensure_ascii=False)}

### 不确定点
{json.dumps(understanding.get('uncertainties', []), ensure_ascii=False)}

## 候选 Agent 池（共 {len(agent_summaries)} 人）
```json
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}
```

## 输出要求

请以 JSON 格式输出筛选结果：

```json
{{
  "analysis": "简要分析筛选逻辑（50字以内）",
  "candidates": [
    {{
      "agent_id": "Agent 的 ID",
      "display_name": "Agent 显示名称",
      "reason": "选择该 Agent 的具体理由（30字以内）",
      "relevance_score": 85,
      "expected_role": "预期角色（如：场地提供者、技术顾问等）"
    }}
  ],
  "coverage": {{
    "covered": ["已覆盖的能力"],
    "uncovered": ["未覆盖的能力"]
  }}
}}
```
"""

    def _parse_filter_response(
        self, response: str, agents: List[Dict]
    ) -> List[Dict]:
        """
        解析筛选响应

        增强解析鲁棒性，处理各种格式问题

        Args:
            response: LLM响应文本
            agents: 可用Agent列表（用于验证）

        Returns:
            有效的候选Agent列表
        """
        try:
            # 尝试提取 JSON 块
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接匹配 JSON 对象
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group()
                else:
                    self._logger.warning("未找到有效 JSON")
                    return []

            data = json.loads(json_str)
            candidates = data.get("candidates", [])

            # 验证候选人 ID 存在
            valid_ids = {a.get("agent_id") for a in agents}
            valid_candidates = []

            for candidate in candidates:
                agent_id = candidate.get("agent_id")
                if agent_id in valid_ids:
                    # 补充显示名称（如果缺失）
                    if not candidate.get("display_name"):
                        for agent in agents:
                            if agent.get("agent_id") == agent_id:
                                candidate["display_name"] = agent.get(
                                    "display_name", agent_id
                                )
                                break
                    # 确保有 reason 字段
                    if not candidate.get("reason"):
                        candidate["reason"] = "符合需求"
                    # 确保有 relevance_score 字段
                    if not candidate.get("relevance_score"):
                        candidate["relevance_score"] = 70
                    valid_candidates.append(candidate)
                else:
                    self._logger.warning(f"无效的 agent_id: {agent_id}")

            # 按 relevance_score 排序
            valid_candidates.sort(
                key=lambda x: x.get("relevance_score", 0),
                reverse=True
            )

            return valid_candidates[:15]  # 最多返回 15 个

        except json.JSONDecodeError as e:
            self._logger.error(f"JSON 解析错误: {e}")
            return []
        except Exception as e:
            self._logger.error(f"解析筛选响应错误: {e}")
            return []

    def _mock_filter(self, understanding: Dict) -> List[Dict]:
        """
        Mock筛选（降级策略）

        当没有LLM服务、数据库不可用或 LLM 筛选失败时使用

        H1 Fix: Now uses shared mock candidates from config.py
        to ensure consistency across the system.

        Args:
            understanding: 需求理解结果

        Returns:
            模拟的候选Agent列表
        """
        # H1 Fix: Use shared mock candidates from config
        from config import filter_mock_candidates_by_tags, get_mock_candidates

        # 基于 capability_tags 进行简单的关键词匹配（降级逻辑）
        capability_tags = understanding.get('capability_tags', [])

        if capability_tags:
            return filter_mock_candidates_by_tags(capability_tags, max_results=10)

        # 默认返回前3个
        return get_mock_candidates(limit=3)

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
        logger.info("[COORD] _create_channel START channel_id=%s, candidates=%d",
                    channel_id, len(candidates))

        # 发布筛选完成事件
        logger.info("[COORD] Publishing towow.filter.completed event")
        await self._publish_event("towow.filter.completed", {
            "demand_id": demand_id,
            "channel_id": channel_id,
            "candidates": candidates
        })

        # 通知ChannelAdmin
        logger.info("[COORD] Sending create_channel message to ChannelAdmin")
        await self.send_to_agent("channel_admin", {
            "type": "create_channel",
            "demand_id": demand_id,
            "channel_id": channel_id,
            "demand": understanding,
            "candidates": candidates
        })
        logger.info("[COORD] create_channel message sent to ChannelAdmin")

        # 更新需求状态
        if demand_id in self.active_demands:
            self.active_demands[demand_id]["status"] = "negotiating"
            self.active_demands[demand_id]["channel_id"] = channel_id

        logger.info("[COORD] _create_channel DONE channel_id=%s", channel_id)

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
