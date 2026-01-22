# TASK-T06-gap-subnet

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T06-gap-subnet.md`
>
> * TASK_ID: TASK-T06
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-22

---

## 关联 Story

- **STORY-06**: 缺口识别与子网协作触发

---

## 任务描述

实现缺口识别（提示词 7）和递归判断（提示词 8）逻辑。当协商完成后，系统能够识别方案中的缺口，并判断是否需要触发子网协商。

### 当前问题

1. 缺口识别逻辑未实现
2. 递归判断逻辑未实现
3. 子网触发机制需要完善

### 改造目标

1. 实现提示词 7：缺口识别
2. 实现提示词 8：递归判断
3. 最多 1 层递归（MVP 简化）
4. 子网结果能够合并到主方案

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/services/gap_identification.py` | 新增缺口识别服务 |
| `towow/services/subnet_manager.py` | 新增子网管理服务 |
| `towow/openagents/agents/channel_admin.py` | 集成缺口识别和子网触发 |

### 关键代码改动

#### 1. 新增 gap_identification.py

```python
# towow/services/gap_identification.py

"""
缺口识别服务

提示词 7：分析方案是否覆盖需求的所有关键方面
"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Gap:
    """缺口数据结构"""
    gap_type: str           # 缺口类型（如：摄影师）
    importance: int         # 重要性 0-100
    reason: str             # 为什么重要
    suggested_tags: List[str]  # 建议的能力标签


class GapIdentificationService:
    """缺口识别服务"""

    def __init__(self, llm_service=None):
        self.llm = llm_service

    async def identify_gaps(
        self,
        demand: Dict[str, Any],
        proposal: Dict[str, Any],
        feedbacks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        识别方案中的缺口

        Args:
            demand: 需求信息
            proposal: 最终方案
            feedbacks: 参与者反馈

        Returns:
            {
                "is_complete": bool,
                "analysis": str,
                "gaps": List[Gap]
            }
        """
        if not self.llm:
            logger.warning("LLM 服务不可用，跳过缺口识别")
            return {"is_complete": True, "analysis": "无法分析", "gaps": []}

        prompt = self._build_gap_prompt(demand, proposal, feedbacks)

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system=self._get_gap_system_prompt(),
                fallback_key="gap_identify",
                max_tokens=2000,
                temperature=0.3
            )
            return self._parse_gap_response(response)
        except Exception as e:
            logger.error(f"缺口识别错误: {e}")
            return {"is_complete": True, "analysis": f"分析失败: {e}", "gaps": []}

    def _get_gap_system_prompt(self) -> str:
        return """你是 ToWow 的缺口分析系统。

分析协作方案是否完整覆盖了需求的关键方面。

分析维度：
1. 能力覆盖：需求所需的能力是否都有人承担
2. 资源覆盖：所需的资源是否齐备
3. 时间覆盖：时间安排是否完整
4. 风险覆盖：主要风险是否有应对措施

只识别真正重要的缺口（importance >= 60），不要过度分析。
以有效 JSON 格式输出。"""

    def _build_gap_prompt(
        self,
        demand: Dict[str, Any],
        proposal: Dict[str, Any],
        feedbacks: List[Dict[str, Any]]
    ) -> str:
        surface_demand = demand.get('surface_demand', '')
        capability_tags = demand.get('capability_tags', [])
        deep = demand.get('deep_understanding', {})

        return f"""
# 缺口识别任务

## 原始需求
{surface_demand}

### 需求分析
- **所需能力**: {', '.join(capability_tags) if capability_tags else '未指定'}
- **资源需求**: {json.dumps(deep.get('resource_requirements', []), ensure_ascii=False)}
- **规模**: {json.dumps(deep.get('scale', {}), ensure_ascii=False)}

## 当前方案
```json
{json.dumps(proposal, ensure_ascii=False, indent=2)}
```

## 参与者反馈中提到的问题
```json
{json.dumps([f.get('concerns', []) for f in feedbacks], ensure_ascii=False)}
```

## 分析任务

请分析这个方案是否完整覆盖了需求，识别出缺口。

## 输出要求

```json
{{
  "is_complete": true/false,
  "analysis": "分析说明（100字以内）",
  "gaps": [
    {{
      "gap_type": "缺口类型（如：摄影师）",
      "importance": 70,
      "reason": "为什么这个缺口重要",
      "suggested_tags": ["建议的能力标签"]
    }}
  ]
}}
```

注意：
- 只识别 importance >= 60 的重要缺口
- 如果方案基本完整，is_complete 应为 true
- gaps 列表可以为空
"""

    def _parse_gap_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{[\s\S]*\}', response)
                json_str = json_match.group() if json_match else "{}"

            data = json.loads(json_str)
            return {
                "is_complete": data.get("is_complete", True),
                "analysis": data.get("analysis", ""),
                "gaps": data.get("gaps", [])
            }
        except Exception as e:
            logger.error(f"解析缺口响应错误: {e}")
            return {"is_complete": True, "analysis": "", "gaps": []}
```

#### 2. 新增 subnet_manager.py

```python
# towow/services/subnet_manager.py

"""
子网管理服务

提示词 8：递归判断
决定是否需要触发子网协商
"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SubDemand:
    """子需求数据结构"""
    description: str
    capability_tags: List[str]
    priority: str  # high | medium | low


class SubnetManager:
    """子网管理服务"""

    # MVP 限制：最多 1 层递归
    MAX_RECURSION_DEPTH = 1

    def __init__(self, llm_service=None):
        self.llm = llm_service

    async def should_trigger_subnet(
        self,
        demand: Dict[str, Any],
        gaps: List[Dict[str, Any]],
        proposal: Dict[str, Any],
        current_depth: int = 0
    ) -> Dict[str, Any]:
        """
        判断是否需要触发子网

        Args:
            demand: 原始需求
            gaps: 识别出的缺口
            proposal: 当前方案
            current_depth: 当前递归深度

        Returns:
            {
                "should_recurse": bool,
                "reason": str,
                "sub_demands": List[SubDemand]
            }
        """
        # 检查递归深度限制
        if current_depth >= self.MAX_RECURSION_DEPTH:
            logger.info(f"已达到最大递归深度 {self.MAX_RECURSION_DEPTH}，不再递归")
            return {
                "should_recurse": False,
                "reason": "已达到最大递归深度",
                "sub_demands": []
            }

        # 检查是否有重要缺口
        important_gaps = [g for g in gaps if g.get("importance", 0) >= 60]
        if not important_gaps:
            return {
                "should_recurse": False,
                "reason": "无重要缺口",
                "sub_demands": []
            }

        if not self.llm:
            logger.warning("LLM 服务不可用，跳过递归判断")
            return {
                "should_recurse": False,
                "reason": "LLM 服务不可用",
                "sub_demands": []
            }

        prompt = self._build_recursion_prompt(demand, important_gaps, proposal)

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system=self._get_recursion_system_prompt(),
                fallback_key="recursion_decide",
                max_tokens=1500,
                temperature=0.3
            )
            return self._parse_recursion_response(response)
        except Exception as e:
            logger.error(f"递归判断错误: {e}")
            return {
                "should_recurse": False,
                "reason": f"判断失败: {e}",
                "sub_demands": []
            }

    def _get_recursion_system_prompt(self) -> str:
        return """你是 ToWow 的递归判断系统。

判断是否需要为方案缺口触发子网协商。

触发条件（三个都需要满足）：
1. 缺口解决后能提升需求满足度 20%+
2. 存在可能填补缺口的其他 Agent
3. 递归协商的成本效益合理（不超过主协商的 30%）

谨慎触发递归，只有在真正必要时才推荐。
以有效 JSON 格式输出。"""

    def _build_recursion_prompt(
        self,
        demand: Dict[str, Any],
        gaps: List[Dict[str, Any]],
        proposal: Dict[str, Any]
    ) -> str:
        return f"""
# 递归判断任务

## 原始需求
{demand.get('surface_demand', '')}

## 当前方案摘要
{proposal.get('summary', '无摘要')}

## 识别出的缺口
```json
{json.dumps(gaps, ensure_ascii=False, indent=2)}
```

## 判断任务

请评估是否需要为这些缺口触发子网协商。

### 评估维度
1. **满足度提升**：解决缺口能提升多少需求满足度？
2. **可行性**：是否可能找到填补缺口的 Agent？
3. **成本效益**：额外协商的成本是否值得？

## 输出要求

```json
{{
  "should_recurse": true/false,
  "analysis": {{
    "satisfaction_impact": "满足度提升分析",
    "feasibility": "可行性分析",
    "cost_benefit": "成本效益分析"
  }},
  "reason": "最终决定的理由（30字以内）",
  "sub_demands": [
    {{
      "description": "子需求描述",
      "capability_tags": ["需要的能力标签"],
      "priority": "high/medium/low",
      "gap_addressed": "解决哪个缺口"
    }}
  ]
}}
```

注意：
- 只有在三个条件都满足时才设置 should_recurse 为 true
- sub_demands 按 priority 排序，最多 3 个
"""

    def _parse_recursion_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{[\s\S]*\}', response)
                json_str = json_match.group() if json_match else "{}"

            data = json.loads(json_str)
            return {
                "should_recurse": data.get("should_recurse", False),
                "analysis": data.get("analysis", {}),
                "reason": data.get("reason", ""),
                "sub_demands": data.get("sub_demands", [])
            }
        except Exception as e:
            logger.error(f"解析递归判断响应错误: {e}")
            return {
                "should_recurse": False,
                "reason": "解析失败",
                "sub_demands": []
            }

    async def trigger_subnet(
        self,
        parent_channel_id: str,
        sub_demand: Dict[str, Any],
        coordinator
    ) -> Optional[str]:
        """
        触发子网协商

        Args:
            parent_channel_id: 父 Channel ID
            sub_demand: 子需求
            coordinator: Coordinator Agent

        Returns:
            子 Channel ID，失败返回 None
        """
        from uuid import uuid4

        sub_channel_id = f"sub-{uuid4().hex[:8]}"

        try:
            # 发送子网需求给 Coordinator
            await coordinator.send_to_agent("coordinator", {
                "type": "subnet_demand",
                "demand": {
                    "surface_demand": sub_demand.get("description"),
                    "capability_tags": sub_demand.get("capability_tags", []),
                    "deep_understanding": {
                        "type": "subnet",
                        "parent_channel": parent_channel_id
                    }
                },
                "parent_channel_id": parent_channel_id,
                "sub_channel_id": sub_channel_id,
                "recursion_depth": 1
            })

            logger.info(f"子网 {sub_channel_id} 已触发，父 Channel: {parent_channel_id}")
            return sub_channel_id

        except Exception as e:
            logger.error(f"触发子网失败: {e}")
            return None
```

#### 3. 集成到 ChannelAdmin

```python
# towow/openagents/agents/channel_admin.py

# 在 _finalize_channel() 方法中添加缺口识别和递归判断

async def _finalize_channel(self, state: ChannelState):
    """完成协商，并进行缺口识别"""
    state.status = ChannelStatus.FINALIZED

    # ... 现有的完成逻辑 ...

    # 缺口识别（仅主 Channel，非子网）
    if not state.is_subnet:
        await self._identify_and_handle_gaps(state)

async def _identify_and_handle_gaps(self, state: ChannelState):
    """识别缺口并处理"""
    from services.gap_identification import GapIdentificationService
    from services.subnet_manager import SubnetManager

    # 初始化服务
    gap_service = GapIdentificationService(llm_service=self.llm)
    subnet_manager = SubnetManager(llm_service=self.llm)

    # 收集反馈
    feedbacks = list(state.proposal_feedback.values())

    # 识别缺口
    gap_result = await gap_service.identify_gaps(
        demand=state.demand,
        proposal=state.current_proposal,
        feedbacks=feedbacks
    )

    self._logger.info(
        f"缺口识别完成: is_complete={gap_result['is_complete']}, "
        f"gaps={len(gap_result['gaps'])}"
    )

    # 发布缺口识别事件
    await self._publish_event("towow.gap.identified", {
        "channel_id": state.channel_id,
        "demand_id": state.demand_id,
        "is_complete": gap_result["is_complete"],
        "gaps": gap_result["gaps"],
        "analysis": gap_result["analysis"]
    })

    # 如果有缺口，判断是否需要递归
    if gap_result["gaps"]:
        recursion_result = await subnet_manager.should_trigger_subnet(
            demand=state.demand,
            gaps=gap_result["gaps"],
            proposal=state.current_proposal,
            current_depth=state.recursion_depth
        )

        if recursion_result["should_recurse"]:
            # 触发子网
            for sub_demand in recursion_result["sub_demands"][:1]:  # MVP 只触发一个
                from openagents.agents import get_coordinator
                coordinator = get_coordinator()
                if coordinator:
                    await subnet_manager.trigger_subnet(
                        parent_channel_id=state.channel_id,
                        sub_demand=sub_demand,
                        coordinator=coordinator
                    )

            # 发布子网触发事件
            await self._publish_event("towow.subnet.triggered", {
                "channel_id": state.channel_id,
                "demand_id": state.demand_id,
                "sub_demands": recursion_result["sub_demands"],
                "reason": recursion_result["reason"]
            })
```

---

## 接口契约

### 缺口识别输出

```python
gap_result: Dict = {
    "is_complete": bool,
    "analysis": str,
    "gaps": [
        {
            "gap_type": str,
            "importance": int,
            "reason": str,
            "suggested_tags": List[str]
        }
    ]
}
```

### 递归判断输出

```python
recursion_result: Dict = {
    "should_recurse": bool,
    "analysis": dict,
    "reason": str,
    "sub_demands": [
        {
            "description": str,
            "capability_tags": List[str],
            "priority": str
        }
    ]
}
```

---

## 依赖

### 硬依赖
- **T05**: 多轮协商逻辑（需要协商完成后触发）

### 接口依赖
- 无

### 被依赖
- **T08**: E2E 测试

---

## 验收标准

- [ ] **AC-1**: 协商完成后自动进行缺口识别
- [ ] **AC-2**: 缺口识别结果发布 `towow.gap.identified` 事件
- [ ] **AC-3**: 重要缺口（importance >= 60）触发递归判断
- [ ] **AC-4**: 递归深度限制为 1 层
- [ ] **AC-5**: 子网触发发布 `towow.subnet.triggered` 事件
- [ ] **AC-6**: LLM 不可用时优雅降级（不触发递归）

### 测试用例

```python
@pytest.mark.asyncio
async def test_gap_identification():
    """测试缺口识别"""
    service = GapIdentificationService(llm=mock_llm_service)

    result = await service.identify_gaps(
        demand={"surface_demand": "办AI聚会", "capability_tags": ["场地", "摄影"]},
        proposal={"assignments": [{"role": "场地提供者"}]},  # 缺少摄影
        feedbacks=[]
    )

    assert not result["is_complete"]
    assert len(result["gaps"]) > 0
    assert any("摄影" in g["gap_type"] for g in result["gaps"])

@pytest.mark.asyncio
async def test_recursion_depth_limit():
    """测试递归深度限制"""
    manager = SubnetManager(llm=mock_llm_service)

    result = await manager.should_trigger_subnet(
        demand={},
        gaps=[{"importance": 80}],
        proposal={},
        current_depth=1  # 已经是子网
    )

    assert not result["should_recurse"]
    assert "最大递归深度" in result["reason"]
```

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| 代码开发 | 2h |
| 提示词调优 | 0.5h |
| 单元测试 | 0.5h |
| **总计** | **3h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 过度触发子网 | 延迟增加 | 提高缺口重要性阈值，严格判断条件 |
| 子网协商失败 | 主方案不完整 | 子网失败不影响主方案 |
| LLM 分析不准确 | 缺口遗漏或误报 | 保守策略，宁缺毋滥 |

---

## 实现记录

*(开发完成后填写)*

---

## 测试记录

*(测试完成后填写)*
