# TASK-019：递归子网实现

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-019 |
| 所属Phase | Phase 6：递归子网 |
| 硬依赖 | TASK-005, TASK-011 |
| 接口依赖 | - |
| 可并行 | - |
| 预估工作量 | 1天 |
| 状态 | 待开始 |
| 优先级 | P1（增强功能，非MVP必需） |

---

## 任务描述

实现递归子网机制，包括缺口识别、子网创建、结果整合。当主协商Channel的方案存在缺口时，系统可以创建子Channel去寻找补充资源。

---

## 功能概述

### 递归子网流程

```
主Channel方案初步聚合
        ↓
    缺口识别（提示词7）
        ↓
    判断是否值得触发子网（提示词8）
        ↓
   [YES] 创建子Channel
        ↓
    子Channel独立协商
        ↓
    子网结果回传
        ↓
    整合到主方案
```

### 递归限制

| 限制 | 值 | 说明 |
|------|-----|------|
| 最大递归深度 | 2 | 最多创建2层子网 |
| 单层最大子网数 | 3 | 每个Channel最多创建3个子Channel |
| 子需求超时 | 180秒 | 子网协商超时时间 |

---

## 具体工作

### 1. 缺口类型定义

`towow/services/gap_types.py`:

```python
"""
缺口类型定义
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class GapType(Enum):
    """缺口类型"""
    CAPABILITY_MISSING = "capability_missing"    # 缺少特定能力
    RESOURCE_SHORTAGE = "resource_shortage"      # 资源不足
    TIMELINE_CONFLICT = "timeline_conflict"      # 时间冲突
    BUDGET_GAP = "budget_gap"                    # 预算缺口
    LOCATION_MISMATCH = "location_mismatch"      # 地点不匹配
    QUALITY_CONCERN = "quality_concern"          # 质量担忧


@dataclass
class Gap:
    """缺口信息"""
    gap_id: str
    gap_type: str
    description: str
    importance: int  # 1-100，越高越重要
    suggested_capability: Optional[str] = None
    can_be_resolved_by_subnet: bool = True
```

### 2. 缺口识别服务

`towow/services/gap_identification.py`:

```python
"""
缺口识别服务
"""
from typing import Dict, Any, List
import json
import re
import logging
from uuid import uuid4
from .gap_types import Gap

logger = logging.getLogger(__name__)


class GapIdentificationService:
    """缺口识别服务"""

    def __init__(self, llm_service):
        self.llm = llm_service

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
  "overall_completion": 75,
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
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                gaps = []
                for g in data.get("gaps", []):
                    gaps.append(Gap(
                        gap_id=g.get("gap_id", f"gap_{uuid4().hex[:6]}"),
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
        # 硬限制检查
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
  "selected_gaps": ["gap_001", "gap_002"],
  "reasoning": "决策理由"
}}
```
"""

        response = await self.llm.complete(
            prompt=prompt,
            system="你是一个决策系统，权衡成本和收益。"
        )

        try:
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

### 3. 子网管理器

`towow/services/subnet_manager.py`:

```python
"""
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
from .gap_types import Gap
from .gap_identification import GapIdentificationService

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

    def __init__(self, coordinator_agent, gap_service: GapIdentificationService):
        self.coordinator = coordinator_agent
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
        parent_demand: Dict,
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
            event = {
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": "towow.subnet.triggered",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "parent_channel_id": parent_channel_id,
                    "sub_channel_id": sub_channel_id,
                    "sub_demand": sub_demand,
                    "recursion_depth": recursion_depth,
                    "gap_being_addressed": gap.description
                }
            }
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
        """根据缺口构建子需求"""
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

                    # 发布超时事件
                    await event_bus.publish({
                        "event_id": f"evt-{uuid4().hex[:8]}",
                        "event_type": "towow.subnet.completed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "payload": {
                            "parent_channel_id": subnet.parent_channel_id,
                            "sub_channel_id": subnet.sub_channel_id,
                            "success": False,
                            "failure_reason": "timeout"
                        }
                    })

        except Exception as e:
            logger.error(f"Error monitoring subnet {subnet.sub_channel_id}: {e}")

    async def handle_subnet_completed(
        self,
        sub_channel_id: str,
        result: Dict[str, Any],
        success: bool
    ):
        """处理子网完成"""
        if sub_channel_id not in self.active_subnets:
            logger.warning(f"Unknown subnet completed: {sub_channel_id}")
            return

        subnet = self.active_subnets[sub_channel_id]
        subnet.status = "completed" if success else "failed"
        subnet.result = result

        # 发布完成事件
        await event_bus.publish({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.subnet.completed",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "parent_channel_id": subnet.parent_channel_id,
                "sub_channel_id": sub_channel_id,
                "success": success,
                "result": result if success else None,
                "failure_reason": result.get("failure_reason") if not success else None
            }
        })

    def _estimate_time_remaining(self, channel_id: str) -> int:
        """估算剩余时间（秒）"""
        # 简化实现：假设总时间5分钟
        return 180

    def get_subnet_status(self, parent_channel_id: str) -> List[Dict]:
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

---

## 验收标准

- [ ] 方案聚合后能够正确识别缺口
- [ ] 缺口重要性评分合理（50-100分为高重要性）
- [ ] 能够正确判断是否触发子网
- [ ] 子网可以正常创建和运行
- [ ] 子网结果能够正确回传
- [ ] 递归深度限制有效（最多2层）
- [ ] 子网超时机制正常工作
- [ ] 相关事件正确发布

---

## 产出物

- `towow/services/gap_types.py`
- `towow/services/gap_identification.py`
- `towow/services/subnet_manager.py`
- ChannelAdmin、Coordinator的子网相关更新

---

## 事件定义

| 事件类型 | 说明 | 关键payload |
|---------|------|------------|
| `towow.subnet.triggered` | 子网触发 | parent_channel_id, sub_channel_id, gap_being_addressed |
| `towow.subnet.completed` | 子网完成 | parent_channel_id, sub_channel_id, success, result |
| `towow.gap.identified` | 缺口识别 | channel_id, gaps[], overall_completion |

---

**创建时间**: 2026-01-21
**来源**: supplement-04-subnet.md
**优先级**: P1（增强功能）
