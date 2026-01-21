# 技术方案补充04：递归子网与缺口识别

> 设计文档核心亮点：子网递归机制的详细实现

---

## 一、递归子网概述

### 1.1 什么是递归子网

当主协商Channel的方案存在缺口（如缺少摄影师、缺少特定技能的人）时，系统可以：
1. 识别缺口
2. 将缺口转化为子需求
3. 创建子Channel处理子需求
4. 子Channel的结果回传父Channel
5. 更新父Channel的方案

### 1.2 递归限制

| 限制 | 值 | 说明 |
|------|-----|------|
| 最大递归深度 | 2 | 最多创建2层子网 |
| 单层最大子网数 | 3 | 每个Channel最多创建3个子Channel |
| 子需求超时 | 180秒 | 子网协商超时时间 |

---

## 二、缺口识别（Gap Identification）

### 2.1 缺口识别时机

在方案初步聚合后，调用缺口识别提示词（提示词7）判断方案是否完整。

### 2.2 缺口类型

```python
class GapType(Enum):
    """缺口类型"""
    CAPABILITY_MISSING = "capability_missing"    # 缺少特定能力
    RESOURCE_SHORTAGE = "resource_shortage"      # 资源不足
    TIMELINE_CONFLICT = "timeline_conflict"      # 时间冲突
    BUDGET_GAP = "budget_gap"                    # 预算缺口
    LOCATION_MISMATCH = "location_mismatch"      # 地点不匹配
    QUALITY_CONCERN = "quality_concern"          # 质量担忧
```

### 2.3 缺口识别实现

```python
"""
towow/services/gap_identification.py
缺口识别服务
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Gap:
    """缺口信息"""
    gap_id: str
    gap_type: str
    description: str
    importance: int  # 1-100，越高越重要
    suggested_capability: Optional[str] = None
    can_be_resolved_by_subnet: bool = True


class GapIdentificationService:
    """缺口识别服务"""

    def __init__(self, llm_service, prompt_loader):
        self.llm = llm_service
        self.prompts = prompt_loader

    async def identify_gaps(
        self,
        demand: Dict[str, Any],
        proposal: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> List[Gap]:
        """
        识别方案缺口

        使用提示词7：缺口识别

        Args:
            demand: 原始需求
            proposal: 当前方案
            participants: 参与者列表

        Returns:
            缺口列表
        """
        prompt = f"""
你是ToWow的方案分析系统。

## 原始需求
{json.dumps(demand, ensure_ascii=False, indent=2)}

## 当前方案
{json.dumps(proposal, ensure_ascii=False, indent=2)}

## 参与者能力
{json.dumps(participants, ensure_ascii=False, indent=2)}

## 任务
分析当前方案，识别出所有缺口（未被满足的需求部分）。

## 缺口类型
- capability_missing: 缺少特定能力/技能的人
- resource_shortage: 资源数量不足（如场地太小）
- timeline_conflict: 时间安排有冲突
- budget_gap: 预算缺口
- location_mismatch: 地点不匹配
- quality_concern: 质量可能达不到预期

## 输出格式
```json
{{
  "overall_completion": 75,  // 方案完成度百分比
  "gaps": [
    {{
      "gap_id": "gap_001",
      "gap_type": "capability_missing",
      "description": "缺少专业摄影师记录活动",
      "importance": 60,
      "suggested_capability": "摄影/摄像",
      "can_be_resolved_by_subnet": true
    }}
  ],
  "analysis": "方案整体可行，主要缺口是..."
}}
```

注意：
- 只识别真正的缺口，不要过度分析
- importance评分要合理，不是所有缺口都重要
- 有些缺口（如预算问题）无法通过子网解决
"""

        response = await self.llm.complete(
            prompt=prompt,
            system="你是一个方案分析专家，擅长识别方案中的缺口和不足。"
        )

        return self._parse_gaps(response)

    def _parse_gaps(self, response: str) -> List[Gap]:
        """解析LLM响应为Gap列表"""
        import re
        import uuid

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                gaps = []
                for g in data.get("gaps", []):
                    gaps.append(Gap(
                        gap_id=g.get("gap_id", str(uuid.uuid4())[:8]),
                        gap_type=g.get("gap_type", "capability_missing"),
                        description=g.get("description", ""),
                        importance=g.get("importance", 50),
                        suggested_capability=g.get("suggested_capability"),
                        can_be_resolved_by_subnet=g.get("can_be_resolved_by_subnet", True)
                    ))
                return gaps
        except Exception as e:
            logger.error(f"Failed to parse gaps: {e}")

        return []

    async def should_trigger_subnet(
        self,
        gaps: List[Gap],
        recursion_depth: int,
        time_remaining_seconds: int
    ) -> List[Gap]:
        """
        判断是否应该触发子网

        使用提示词8：递归判断

        Returns:
            应该触发子网的缺口列表（可能为空）
        """
        if recursion_depth >= 2:
            logger.info("Max recursion depth reached, skipping subnet")
            return []

        if time_remaining_seconds < 60:
            logger.info("Not enough time for subnet")
            return []

        # 过滤可以通过子网解决的高重要性缺口
        eligible_gaps = [
            g for g in gaps
            if g.can_be_resolved_by_subnet and g.importance >= 50
        ]

        if not eligible_gaps:
            return []

        # 使用LLM判断是否值得
        prompt = f"""
你是ToWow的决策系统。

## 当前情况
- 递归深度: {recursion_depth}/2
- 剩余时间: {time_remaining_seconds}秒
- 可能的缺口:
{json.dumps([{"description": g.description, "importance": g.importance} for g in eligible_gaps], ensure_ascii=False, indent=2)}

## 任务
判断是否值得为这些缺口创建子网去寻找解决方案。

考虑因素：
1. 缺口的重要性
2. 剩余时间是否足够
3. 创建子网的成本（会增加复杂度和时间）
4. 即使子网失败，主方案是否仍可接受

## 输出格式
```json
{{
  "decision": "trigger" 或 "skip",
  "selected_gaps": ["gap_001", "gap_002"],  // 如果是trigger
  "reasoning": "决策理由"
}}
```
"""

        response = await self.llm.complete(
            prompt=prompt,
            system="你是一个决策系统，权衡成本和收益。"
        )

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                if data.get("decision") == "trigger":
                    selected_ids = set(data.get("selected_gaps", []))
                    return [g for g in eligible_gaps if g.gap_id in selected_ids]
        except Exception as e:
            logger.error(f"Failed to parse subnet decision: {e}")

        return []
```

---

## 三、递归子网实现

### 3.1 子网管理器

```python
"""
towow/services/subnet_manager.py
递归子网管理器
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging
from uuid import uuid4

from events.factory import EventFactory
from events.bus import event_bus
from services.gap_identification import Gap, GapIdentificationService

logger = logging.getLogger(__name__)


@dataclass
class SubnetInfo:
    """子网信息"""
    sub_channel_id: str
    parent_channel_id: str
    gap: Gap
    sub_demand: Dict[str, Any]
    recursion_depth: int
    created_at: datetime
    status: str  # "active" | "completed" | "timeout" | "failed"
    result: Optional[Dict[str, Any]] = None


class SubnetManager:
    """
    递归子网管理器

    职责：
    1. 创建子需求
    2. 创建子Channel
    3. 监控子网状态
    4. 聚合子网结果
    """

    MAX_DEPTH = 2
    MAX_SUBNETS_PER_CHANNEL = 3
    SUBNET_TIMEOUT = 180  # 3分钟

    def __init__(
        self,
        coordinator_agent,
        channel_admin_agent,
        gap_service: GapIdentificationService
    ):
        self.coordinator = coordinator_agent
        self.channel_admin = channel_admin_agent
        self.gap_service = gap_service
        self.active_subnets: Dict[str, SubnetInfo] = {}

    async def process_gaps(
        self,
        parent_channel_id: str,
        demand: Dict[str, Any],
        proposal: Dict[str, Any],
        participants: List[Dict[str, Any]],
        recursion_depth: int = 0
    ) -> List[SubnetInfo]:
        """
        处理方案缺口，决定是否创建子网

        Returns:
            创建的子网列表
        """
        # 1. 识别缺口
        gaps = await self.gap_service.identify_gaps(demand, proposal, participants)

        if not gaps:
            logger.info(f"No gaps identified for {parent_channel_id}")
            return []

        logger.info(f"Identified {len(gaps)} gaps for {parent_channel_id}")

        # 2. 判断是否触发子网
        time_remaining = self._estimate_time_remaining(parent_channel_id)
        gaps_to_resolve = await self.gap_service.should_trigger_subnet(
            gaps, recursion_depth, time_remaining
        )

        if not gaps_to_resolve:
            logger.info(f"No subnet triggered for {parent_channel_id}")
            return []

        # 3. 限制子网数量
        gaps_to_resolve = gaps_to_resolve[:self.MAX_SUBNETS_PER_CHANNEL]

        # 4. 创建子网
        created_subnets = []
        for gap in gaps_to_resolve:
            subnet = await self._create_subnet(
                parent_channel_id=parent_channel_id,
                parent_demand=demand,
                gap=gap,
                recursion_depth=recursion_depth + 1
            )
            if subnet:
                created_subnets.append(subnet)
                self.active_subnets[subnet.sub_channel_id] = subnet

        # 5. 启动超时监控
        for subnet in created_subnets:
            asyncio.create_task(self._monitor_subnet(subnet))

        return created_subnets

    async def _create_subnet(
        self,
        parent_channel_id: str,
        parent_demand: Dict[str, Any],
        gap: Gap,
        recursion_depth: int
    ) -> Optional[SubnetInfo]:
        """创建单个子网"""
        try:
            # 生成子Channel ID
            sub_channel_id = f"{parent_channel_id}_sub_{gap.gap_id}"

            # 构建子需求
            sub_demand = self._build_sub_demand(parent_demand, gap)

            # 发布子网触发事件
            event = EventFactory.subnet_triggered(
                source_agent="channel_admin",
                parent_channel_id=parent_channel_id,
                sub_channel_id=sub_channel_id,
                sub_demand=sub_demand,
                recursion_depth=recursion_depth,
                gap_being_addressed=gap.description
            )
            await event_bus.publish(event)

            # 通知Coordinator处理子需求
            await self.coordinator.send_to_agent("coordinator", {
                "type": "subnet_demand",
                "sub_channel_id": sub_channel_id,
                "parent_channel_id": parent_channel_id,
                "demand": sub_demand,
                "recursion_depth": recursion_depth,
                "gap": {
                    "gap_id": gap.gap_id,
                    "description": gap.description,
                    "suggested_capability": gap.suggested_capability
                }
            })

            subnet_info = SubnetInfo(
                sub_channel_id=sub_channel_id,
                parent_channel_id=parent_channel_id,
                gap=gap,
                sub_demand=sub_demand,
                recursion_depth=recursion_depth,
                created_at=datetime.utcnow(),
                status="active"
            )

            logger.info(f"Created subnet {sub_channel_id} for gap: {gap.description}")
            return subnet_info

        except Exception as e:
            logger.error(f"Failed to create subnet for gap {gap.gap_id}: {e}")
            return None

    def _build_sub_demand(self, parent_demand: Dict, gap: Gap) -> Dict[str, Any]:
        """
        根据缺口构建子需求

        关键：子需求要比父需求更聚焦
        """
        return {
            "raw_input": f"为'{parent_demand.get('surface_demand', '')}'寻找{gap.description}",
            "surface_demand": gap.description,
            "deep_understanding": {
                "parent_context": parent_demand.get("surface_demand"),
                "specific_need": gap.suggested_capability or gap.description,
                "priority": "high" if gap.importance >= 70 else "medium"
            },
            "capability_tags": [gap.suggested_capability] if gap.suggested_capability else [],
            "is_subnet": True,
            "parent_gap_id": gap.gap_id
        }

    async def _monitor_subnet(self, subnet: SubnetInfo):
        """监控子网状态和超时"""
        try:
            await asyncio.sleep(self.SUBNET_TIMEOUT)

            # 检查是否已完成
            if subnet.sub_channel_id in self.active_subnets:
                current = self.active_subnets[subnet.sub_channel_id]
                if current.status == "active":
                    # 超时
                    current.status = "timeout"
                    logger.warning(f"Subnet {subnet.sub_channel_id} timed out")

                    # 通知父Channel
                    await self._notify_parent_subnet_result(subnet, success=False)

        except Exception as e:
            logger.error(f"Error monitoring subnet {subnet.sub_channel_id}: {e}")

    async def handle_subnet_completed(
        self,
        sub_channel_id: str,
        result: Dict[str, Any],
        success: bool
    ):
        """
        处理子网完成

        由ChannelAdmin在子Channel完成时调用
        """
        if sub_channel_id not in self.active_subnets:
            logger.warning(f"Unknown subnet completed: {sub_channel_id}")
            return

        subnet = self.active_subnets[sub_channel_id]
        subnet.status = "completed" if success else "failed"
        subnet.result = result

        # 发布事件
        event = EventFactory.create_event(
            TowowEventType.SUBNET_COMPLETED,
            source_agent="channel_admin",
            parent_channel_id=subnet.parent_channel_id,
            sub_channel_id=sub_channel_id,
            success=success,
            result=result if success else None,
            failure_reason=result.get("failure_reason") if not success else None
        )
        await event_bus.publish(event)

        # 通知父Channel
        await self._notify_parent_subnet_result(subnet, success)

    async def _notify_parent_subnet_result(self, subnet: SubnetInfo, success: bool):
        """通知父Channel子网结果"""
        await self.channel_admin.post_to_channel(subnet.parent_channel_id, {
            "type": "subnet_result",
            "sub_channel_id": subnet.sub_channel_id,
            "gap_id": subnet.gap.gap_id,
            "success": success,
            "result": subnet.result if success else None,
            "gap_description": subnet.gap.description
        })

    def _estimate_time_remaining(self, channel_id: str) -> int:
        """估算剩余时间（秒）"""
        # 简化实现：假设总时间5分钟
        return 180

    async def get_subnet_status(self, parent_channel_id: str) -> List[Dict]:
        """获取某个Channel的所有子网状态"""
        return [
            {
                "sub_channel_id": s.sub_channel_id,
                "gap_description": s.gap.description,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "result": s.result
            }
            for s in self.active_subnets.values()
            if s.parent_channel_id == parent_channel_id
        ]
```

### 3.2 ChannelAdmin集成子网处理

```python
"""
towow/agents/channel_admin.py (补充部分)
ChannelAdmin的子网处理逻辑
"""

class ChannelAdminAgent(TowowBaseAgent):
    # ... 之前的代码 ...

    async def _trigger_aggregation(self, channel_id: str):
        """触发方案聚合（增加缺口识别）"""
        state = self.channel_states.get(channel_id)
        if not state:
            return

        state["status"] = ChannelStatus.AGGREGATING

        # 筛选愿意参与的人
        participants = {
            agent_id: resp
            for agent_id, resp in state["responses"].items()
            if resp["decision"] == "participate"
        }

        if not participants:
            await self._handle_no_participants(channel_id)
            return

        # 调用LLM聚合方案
        proposal = await self._llm_aggregate(
            demand=state["demand"],
            participants=participants
        )

        state["current_proposal"] = proposal
        state["proposal_version"] += 1

        # === 新增：缺口识别 ===
        if state.get("recursion_depth", 0) < 2:
            await self._process_gaps_and_subnets(channel_id, proposal, participants)

        state["status"] = ChannelStatus.FEEDBACK

        # 分发方案给参与者
        await self._distribute_proposal(channel_id, proposal, list(participants.keys()))

    async def _process_gaps_and_subnets(
        self,
        channel_id: str,
        proposal: Dict,
        participants: Dict
    ):
        """处理缺口和子网"""
        state = self.channel_states.get(channel_id)

        # 识别缺口
        gaps = await self.gap_service.identify_gaps(
            demand=state["demand"],
            proposal=proposal,
            participants=list(participants.values())
        )

        if gaps:
            # 记录缺口
            state["identified_gaps"] = gaps

            # 发布缺口识别事件
            from events.factory import EventFactory
            event = EventFactory.gap_identified(
                source_agent=self.client.agent_id,
                channel_id=channel_id,
                demand_id=state["demand"].get("demand_id", ""),
                gaps=[{
                    "gap_type": g.gap_type,
                    "description": g.description,
                    "importance": g.importance
                } for g in gaps],
                overall_completion=proposal.get("confidence_score", 70)
            )
            await event_bus.publish(event)

            # 判断是否触发子网
            created_subnets = await self.subnet_manager.process_gaps(
                parent_channel_id=channel_id,
                demand=state["demand"],
                proposal=proposal,
                participants=list(participants.values()),
                recursion_depth=state.get("recursion_depth", 0)
            )

            if created_subnets:
                state["active_subnets"] = [s.sub_channel_id for s in created_subnets]
                logger.info(f"Created {len(created_subnets)} subnets for {channel_id}")

    async def on_channel_post(self, context: ChannelMessageContext):
        """处理Channel消息（增加子网结果处理）"""
        message = context.message
        channel = context.channel
        msg_type = message.get("type", "unknown")

        # 原有处理
        if msg_type == "offer_response":
            await self._handle_offer_response(context, message, channel)
        elif msg_type == "proposal_feedback":
            await self._handle_proposal_feedback(context, message, channel)
        # 新增：子网结果处理
        elif msg_type == "subnet_result":
            await self._handle_subnet_result(context, message, channel)

    async def _handle_subnet_result(self, context, message: Dict, channel: str):
        """处理子网结果"""
        state = self.channel_states.get(channel)
        if not state:
            return

        sub_channel_id = message.get("sub_channel_id")
        success = message.get("success", False)
        result = message.get("result")
        gap_id = message.get("gap_id")

        logger.info(f"Subnet {sub_channel_id} completed: success={success}")

        # 更新子网状态
        if "subnet_results" not in state:
            state["subnet_results"] = {}
        state["subnet_results"][sub_channel_id] = {
            "success": success,
            "result": result,
            "gap_id": gap_id
        }

        # 检查是否所有子网都完成
        active_subnets = state.get("active_subnets", [])
        completed_subnets = set(state["subnet_results"].keys())

        if set(active_subnets).issubset(completed_subnets):
            # 所有子网完成，整合结果
            await self._integrate_subnet_results(channel)

    async def _integrate_subnet_results(self, channel_id: str):
        """整合子网结果到主方案"""
        state = self.channel_states.get(channel_id)
        subnet_results = state.get("subnet_results", {})

        successful_results = [
            r for r in subnet_results.values()
            if r["success"] and r.get("result")
        ]

        if not successful_results:
            logger.info(f"No successful subnet results for {channel_id}")
            return

        # 使用LLM整合子网结果
        current_proposal = state["current_proposal"]

        prompt = f"""
你是ToWow的方案整合系统。

## 当前主方案
{json.dumps(current_proposal, ensure_ascii=False, indent=2)}

## 子网解决的结果
{json.dumps(successful_results, ensure_ascii=False, indent=2)}

## 任务
将子网找到的资源/人员整合到主方案中，更新assignments。

## 输出格式
返回更新后的完整方案（与原方案格式相同）。
"""

        response = await self.llm_complete(
            prompt=prompt,
            system="你是一个方案整合专家。"
        )

        # 解析更新后的方案
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                updated_proposal = json.loads(json_match.group())
                state["current_proposal"] = updated_proposal
                state["proposal_version"] += 1

                # 重新分发更新后的方案
                participants = [a["agent_id"] for a in updated_proposal.get("assignments", [])]
                await self._distribute_proposal(channel_id, updated_proposal, participants)

                logger.info(f"Integrated subnet results into {channel_id}")

        except Exception as e:
            logger.error(f"Failed to integrate subnet results: {e}")
```

### 3.3 Coordinator处理子网需求

```python
"""
towow/agents/coordinator.py (补充部分)
Coordinator处理子网需求
"""

class CoordinatorAgent(TowowBaseAgent):
    # ... 之前的代码 ...

    async def on_startup(self):
        """启动时初始化"""
        self.active_demands = {}

        # 注册消息处理器
        self.register_handler("new_demand", self._handle_new_demand)
        self.register_handler("subnet_demand", self._handle_subnet_demand)  # 新增

        logger.info(f"CoordinatorAgent started: {self.client.agent_id}")

    async def _handle_subnet_demand(self, context, message: Dict):
        """处理子网需求"""
        sub_channel_id = message.get("sub_channel_id")
        parent_channel_id = message.get("parent_channel_id")
        demand = message.get("demand")
        recursion_depth = message.get("recursion_depth", 1)
        gap = message.get("gap", {})

        logger.info(f"Processing subnet demand for {sub_channel_id}, depth={recursion_depth}")

        try:
            # 1. 获取活跃Agent（排除父Channel已参与的）
            agent_profiles = await self._get_active_profiles()

            # TODO: 可以从父Channel获取已参与者列表，排除他们

            # 2. 针对缺口的聚焦筛选
            candidates = await self._focused_filter(
                demand=demand,
                profiles=agent_profiles,
                focus_capability=gap.get("suggested_capability")
            )

            if not candidates:
                logger.warning(f"No candidates found for subnet {sub_channel_id}")
                # 通知父Channel子网失败
                await self.post_to_channel(parent_channel_id, {
                    "type": "subnet_result",
                    "sub_channel_id": sub_channel_id,
                    "gap_id": gap.get("gap_id"),
                    "success": False,
                    "failure_reason": "no_candidates"
                })
                return

            # 3. 创建子Channel记录
            await self._create_collaboration_channel(
                channel_name=sub_channel_id,
                demand_id=demand.get("demand_id", sub_channel_id),
                candidates=candidates,
                parent_channel=parent_channel_id,
                recursion_depth=recursion_depth
            )

            # 4. 通知ChannelAdmin初始化子Channel
            await self.send_to_agent("channel_admin", {
                "type": "init_subnet_channel",
                "channel_id": sub_channel_id,
                "demand": demand,
                "candidates": candidates,
                "parent_channel_id": parent_channel_id,
                "recursion_depth": recursion_depth
            })

            # 5. 邀请候选人
            for agent_id in candidates:
                await self.send_to_agent(agent_id, {
                    "type": "collaboration_invite",
                    "channel": sub_channel_id,
                    "demand": demand,
                    "is_subnet": True,
                    "parent_context": f"这是'{parent_channel_id}'的子需求",
                    "message": f"您被邀请参与：{demand.get('surface_demand', '')}"
                })

            logger.info(f"Subnet {sub_channel_id} initiated with {len(candidates)} candidates")

        except Exception as e:
            logger.error(f"Error handling subnet demand: {e}")
            await self.post_to_channel(parent_channel_id, {
                "type": "subnet_result",
                "sub_channel_id": sub_channel_id,
                "gap_id": gap.get("gap_id"),
                "success": False,
                "failure_reason": str(e)
            })

    async def _focused_filter(
        self,
        demand: Dict,
        profiles: List[Dict],
        focus_capability: Optional[str]
    ) -> List[str]:
        """
        聚焦筛选：专门针对特定能力筛选

        与普通筛选不同，更注重精确匹配
        """
        if not profiles:
            return []

        focus_hint = f"\n\n特别关注具有'{focus_capability}'能力的人。" if focus_capability else ""

        prompt = f"""
你是ToWow的智能筛选系统。

## 子需求
{json.dumps(demand, ensure_ascii=False, indent=2)}

## 可用Agent列表
{json.dumps(profiles, ensure_ascii=False, indent=2)}

{focus_hint}

## 任务
这是一个子需求，请精准筛选最匹配的3-5个候选人。

注意：
- 宁缺毋滥，如果没有真正匹配的，可以返回空列表
- 优先选择能力精确匹配的人
- 最多返回5人

## 输出格式
```json
[
  {{"agent_id": "xxx", "reason": "选中理由"}}
]
```
"""

        response = await self.llm_complete(
            prompt=prompt,
            system="你是一个精准筛选系统。"
        )

        try:
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                candidates = json.loads(json_match.group())
                return [c["agent_id"] for c in candidates]
        except Exception as e:
            logger.error(f"Failed to parse focused filter response: {e}")

        return []
```

---

## 四、新增TASK

### TASK-019：递归子网实现

```markdown
# TASK-019：递归子网实现

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-019 |
| 所属Phase | Phase 3：提示词集成 |
| 依赖 | TASK-005, TASK-011 |
| 预估工作量 | 1天 |
| 状态 | 待开始 |

---

## 任务描述

实现递归子网机制，包括缺口识别、子网创建、结果整合。

---

## 具体工作

1. 实现 `GapIdentificationService` 缺口识别服务
2. 实现 `SubnetManager` 子网管理器
3. 在 `ChannelAdminAgent` 中集成缺口识别
4. 在 `CoordinatorAgent` 中增加子网需求处理
5. 实现子网结果整合逻辑

---

## 验收标准

- [ ] 方案聚合后能够识别缺口
- [ ] 缺口重要性评分合理
- [ ] 能够正确判断是否触发子网
- [ ] 子网可以正常创建和运行
- [ ] 子网结果能够整合到父方案
- [ ] 递归深度限制有效

---

## 产出物

- `services/gap_identification.py`
- `services/subnet_manager.py`
- ChannelAdmin、Coordinator的更新
```

---

**文档版本**: v1.0
**创建时间**: 2026-01-21
**状态**: 补充完成
