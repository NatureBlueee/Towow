"""
Gap Identification Service - ToWow 缺口识别服务

负责分析协作方案，识别缺口，判断是否需要触发递归子网。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .gap_types import Gap, GapType, GapSeverity, GapAnalysisResult

logger = logging.getLogger(__name__)


class GapIdentificationService:
    """
    缺口识别服务

    分析协作方案，识别以下类型的缺口：
    1. 能力缺口 - 缺少必要技能
    2. 资源缺口 - 缺少必要资源
    3. 参与者缺口 - 参与人数不足
    4. 覆盖缺口 - 需求未完全覆盖
    5. 条件缺口 - 参与者条件无法满足
    """

    # H3 Fix: Load thresholds from shared config
    # Can be overridden by environment variables:
    # - TOWOW_MIN_PARTICIPANTS_THRESHOLD
    # - TOWOW_COVERAGE_THRESHOLD
    @property
    def MIN_PARTICIPANTS_THRESHOLD(self) -> int:
        """Minimum participants threshold, configurable via environment."""
        from config import MIN_PARTICIPANTS_THRESHOLD
        return MIN_PARTICIPANTS_THRESHOLD

    @property
    def COVERAGE_THRESHOLD(self) -> float:
        """Coverage threshold, configurable via environment."""
        from config import COVERAGE_THRESHOLD
        return COVERAGE_THRESHOLD

    def __init__(self, llm_service=None):
        """
        初始化缺口识别服务

        Args:
            llm_service: LLM 服务实例（可选，用于智能分析）
        """
        self.llm = llm_service
        self._logger = logger

    async def identify_gaps(
        self,
        demand: Dict[str, Any],
        proposal: Dict[str, Any],
        participants: List[Dict[str, Any]],
        channel_id: str = "",
        demand_id: str = ""
    ) -> GapAnalysisResult:
        """
        识别方案缺口

        Args:
            demand: 需求信息
            proposal: 当前方案
            participants: 参与者列表
            channel_id: Channel ID
            demand_id: 需求 ID

        Returns:
            GapAnalysisResult: 缺口分析结果
        """
        self._logger.info(f"Identifying gaps for demand {demand_id}")

        gaps: List[Gap] = []

        # 1. 基于规则的缺口识别
        rule_gaps = self._identify_by_rules(demand, proposal, participants)
        gaps.extend(rule_gaps)

        # 2. 基于 LLM 的智能缺口识别（如果可用）
        if self.llm:
            try:
                llm_gaps = await self._identify_by_llm(demand, proposal, participants)
                # 合并去重
                existing_ids = {g.gap_id for g in gaps}
                for gap in llm_gaps:
                    if gap.gap_id not in existing_ids:
                        gaps.append(gap)
            except Exception as e:
                self._logger.error(f"LLM gap identification failed: {e}")

        # 3. 构建分析结果
        result = GapAnalysisResult(
            channel_id=channel_id,
            demand_id=demand_id,
            proposal=proposal,
            gaps=gaps,
            analysis_summary=self._generate_summary(gaps)
        )

        self._logger.info(
            f"Gap analysis complete: {result.total_gaps} gaps found, "
            f"{result.critical_gaps} critical, subnet_recommended={result.subnet_recommended}"
        )

        return result

    def _identify_by_rules(
        self,
        demand: Dict[str, Any],
        proposal: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> List[Gap]:
        """
        基于规则识别缺口

        Args:
            demand: 需求信息
            proposal: 当前方案
            participants: 参与者列表

        Returns:
            识别出的缺口列表
        """
        gaps: List[Gap] = []

        # 规则1: 参与者数量检查
        participant_gap = self._check_participant_count(participants, demand)
        if participant_gap:
            gaps.append(participant_gap)

        # 规则2: 资源需求覆盖检查
        resource_gaps = self._check_resource_coverage(demand, proposal, participants)
        gaps.extend(resource_gaps)

        # 规则3: 条件满足检查
        condition_gaps = self._check_conditions(proposal, participants)
        gaps.extend(condition_gaps)

        # 规则4: 角色分配完整性检查
        assignment_gaps = self._check_assignments(demand, proposal)
        gaps.extend(assignment_gaps)

        return gaps

    def _check_participant_count(
        self,
        participants: List[Dict[str, Any]],
        demand: Dict[str, Any]
    ) -> Optional[Gap]:
        """检查参与者数量是否足够"""
        active_participants = [
            p for p in participants
            if p.get("decision") in ("participate", "conditional")
        ]

        # 从需求中获取期望的参与者数量
        deep = demand.get("deep_understanding", {})
        scale = deep.get("scale", {})
        expected_participants = scale.get("participants", self.MIN_PARTICIPANTS_THRESHOLD)

        if isinstance(expected_participants, str):
            # 尝试解析字符串格式的参与者数量（如 "5-10人"）
            match = re.search(r'(\d+)', expected_participants)
            expected_participants = int(match.group(1)) if match else self.MIN_PARTICIPANTS_THRESHOLD

        if len(active_participants) < expected_participants:
            return Gap(
                gap_id=f"gap-{uuid4().hex[:8]}",
                gap_type=GapType.PARTICIPANT,
                severity=GapSeverity.HIGH if len(active_participants) < 2 else GapSeverity.MEDIUM,
                description=f"参与者数量不足：当前 {len(active_participants)} 人，期望 {expected_participants} 人",
                requirement=f"需要至少 {expected_participants} 名参与者",
                suggested_sub_demand=f"寻找更多愿意参与的协作者（还需 {expected_participants - len(active_participants)} 人）",
                affected_aspects=["team_size", "collaboration_capacity"],
                potential_solutions=[
                    "扩大候选范围重新筛选",
                    "降低参与门槛",
                    "分阶段实施"
                ]
            )

        return None

    def _check_resource_coverage(
        self,
        demand: Dict[str, Any],
        proposal: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> List[Gap]:
        """检查资源需求覆盖情况"""
        gaps: List[Gap] = []

        # 获取需求中的资源需求
        deep = demand.get("deep_understanding", {})
        required_resources = deep.get("resource_requirements", [])

        if not required_resources:
            return gaps

        # 收集参与者提供的能力/贡献
        provided_capabilities = set()
        for p in participants:
            if p.get("decision") in ("participate", "conditional"):
                caps = p.get("capabilities", [])
                if isinstance(caps, list):
                    provided_capabilities.update(caps)
                contribution = p.get("contribution", "")
                if contribution:
                    provided_capabilities.add(contribution.lower())

        # 检查覆盖情况
        uncovered = []
        for resource in required_resources:
            resource_lower = resource.lower()
            # 简单的关键词匹配
            covered = any(
                resource_lower in cap.lower() or cap.lower() in resource_lower
                for cap in provided_capabilities
            )
            if not covered:
                uncovered.append(resource)

        # 为每个未覆盖的资源创建缺口
        for resource in uncovered:
            gaps.append(Gap(
                gap_id=f"gap-{uuid4().hex[:8]}",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.HIGH,
                description=f"资源需求未覆盖：{resource}",
                requirement=resource,
                suggested_sub_demand=f"寻找能够提供「{resource}」的协作者",
                affected_aspects=["resource_availability"],
                potential_solutions=[
                    f"寻找专门提供{resource}的Agent",
                    "考虑外部采购/租赁",
                    "调整方案以减少对该资源的依赖"
                ]
            ))

        return gaps

    def _check_conditions(
        self,
        proposal: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> List[Gap]:
        """检查参与者条件满足情况"""
        gaps: List[Gap] = []

        # 收集所有未满足的条件
        unmet_conditions = []
        for p in participants:
            if p.get("decision") == "conditional":
                conditions = p.get("conditions", [])
                agent_id = p.get("agent_id", "unknown")

                # 检查条件是否在方案中得到满足
                assignments = proposal.get("assignments", [])
                addressed = set()
                for assignment in assignments:
                    addressed.update(assignment.get("conditions_addressed", []))

                for condition in conditions:
                    if condition not in addressed:
                        unmet_conditions.append({
                            "agent_id": agent_id,
                            "condition": condition
                        })

        # 为未满足的条件创建缺口
        if unmet_conditions:
            condition_desc = "; ".join(
                f"{c['agent_id']}: {c['condition']}"
                for c in unmet_conditions[:3]  # 最多列出3个
            )
            if len(unmet_conditions) > 3:
                condition_desc += f" 等共 {len(unmet_conditions)} 个条件"

            gaps.append(Gap(
                gap_id=f"gap-{uuid4().hex[:8]}",
                gap_type=GapType.CONDITION,
                severity=GapSeverity.MEDIUM,
                description=f"参与者条件未满足：{condition_desc}",
                requirement="满足参与者提出的条件",
                suggested_sub_demand=None,  # 条件缺口通常不触发子网
                affected_aspects=["participant_satisfaction", "commitment"],
                potential_solutions=[
                    "协商调整条件",
                    "在方案中增加条件满足措施",
                    "寻找替代参与者"
                ],
                metadata={"unmet_conditions": unmet_conditions}
            ))

        return gaps

    def _check_assignments(
        self,
        demand: Dict[str, Any],
        proposal: Dict[str, Any]
    ) -> List[Gap]:
        """检查角色分配完整性"""
        gaps: List[Gap] = []

        assignments = proposal.get("assignments", [])

        # 检查是否有空角色或空职责
        empty_assignments = [
            a for a in assignments
            if not a.get("responsibility") or a.get("responsibility") == "待分配职责"
        ]

        if empty_assignments:
            gaps.append(Gap(
                gap_id=f"gap-{uuid4().hex[:8]}",
                gap_type=GapType.COVERAGE,
                severity=GapSeverity.MEDIUM,
                description=f"{len(empty_assignments)} 个角色职责未明确",
                requirement="所有参与者需要明确的职责分配",
                suggested_sub_demand=None,
                affected_aspects=["task_clarity", "accountability"],
                potential_solutions=[
                    "重新进行方案聚合",
                    "与参与者沟通明确职责"
                ]
            ))

        return gaps

    async def _identify_by_llm(
        self,
        demand: Dict[str, Any],
        proposal: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> List[Gap]:
        """
        使用 LLM 进行智能缺口识别

        Args:
            demand: 需求信息
            proposal: 当前方案
            participants: 参与者列表

        Returns:
            识别出的缺口列表
        """
        if not self.llm:
            return []

        surface_demand = demand.get("surface_demand", "")
        deep = demand.get("deep_understanding", {})

        prompt = f"""
# 协作方案缺口分析任务

你是ToWow协作平台的方案分析专家。请分析当前协作方案，识别其中的缺口和不足。

## 原始需求
{surface_demand}

## 需求深层理解
- 类型: {deep.get('type', 'unknown')}
- 动机: {deep.get('motivation', 'unknown')}
- 资源需求: {json.dumps(deep.get('resource_requirements', []), ensure_ascii=False)}
- 规模: {json.dumps(deep.get('scale', {}), ensure_ascii=False)}
- 时间线: {json.dumps(deep.get('timeline', {}), ensure_ascii=False)}

## 当前方案
```json
{json.dumps(proposal, ensure_ascii=False, indent=2)}
```

## 参与者情况
```json
{json.dumps(participants, ensure_ascii=False, indent=2)}
```

## 分析要求

请识别以下类型的缺口：
1. **能力缺口(capability)**: 缺少完成任务所需的技能或专业能力
2. **资源缺口(resource)**: 缺少必要的资源（场地、设备、资金等）
3. **参与者缺口(participant)**: 参与者数量或质量不足
4. **覆盖缺口(coverage)**: 某些需求维度未被方案覆盖
5. **条件缺口(condition)**: 参与者提出的条件无法满足

## 输出格式（JSON数组）

```json
[
  {{
    "gap_type": "capability|resource|participant|coverage|condition",
    "severity": "critical|high|medium|low",
    "description": "缺口描述",
    "requirement": "需要什么",
    "suggested_sub_demand": "建议的子需求描述（用于寻找能填补缺口的协作者）",
    "affected_aspects": ["受影响的方面"],
    "potential_solutions": ["潜在解决方案"]
  }}
]
```

注意：
- 只输出确实存在的缺口，不要凭空创造
- severity为critical或high的缺口才建议触发子网（提供suggested_sub_demand）
- 如果方案已经很完善，可以返回空数组 []
"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system="你是ToWow的方案分析专家，负责识别协作方案中的缺口。请以JSON数组格式输出分析结果。",
                fallback_key="gap_identification"
            )

            return self._parse_llm_gaps(response)
        except Exception as e:
            self._logger.error(f"LLM gap identification error: {e}")
            return []

    def _parse_llm_gaps(self, response: str) -> List[Gap]:
        """解析 LLM 返回的缺口列表"""
        try:
            # 尝试提取 JSON 数组
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())

                gaps = []
                for item in data:
                    try:
                        gap = Gap(
                            gap_id=f"gap-llm-{uuid4().hex[:8]}",
                            gap_type=GapType(item.get("gap_type", "coverage")),
                            severity=GapSeverity(item.get("severity", "medium")),
                            description=item.get("description", ""),
                            requirement=item.get("requirement", ""),
                            suggested_sub_demand=item.get("suggested_sub_demand"),
                            affected_aspects=item.get("affected_aspects", []),
                            potential_solutions=item.get("potential_solutions", [])
                        )
                        gaps.append(gap)
                    except (ValueError, KeyError) as e:
                        self._logger.warning(f"Failed to parse gap item: {e}")
                        continue

                return gaps
        except json.JSONDecodeError as e:
            self._logger.error(f"JSON parse error in LLM gaps: {e}")
        except Exception as e:
            self._logger.error(f"Parse LLM gaps error: {e}")

        return []

    def _generate_summary(self, gaps: List[Gap]) -> str:
        """生成缺口分析摘要"""
        if not gaps:
            return "方案完整，未发现明显缺口"

        critical_count = sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL)
        high_count = sum(1 for g in gaps if g.severity == GapSeverity.HIGH)

        type_counts = {}
        for gap in gaps:
            type_name = gap.gap_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        type_desc = "、".join(
            f"{t}({c})" for t, c in type_counts.items()
        )

        if critical_count > 0:
            return f"发现 {len(gaps)} 个缺口（{critical_count} 个关键），类型分布：{type_desc}，建议触发子网解决"
        elif high_count > 0:
            return f"发现 {len(gaps)} 个缺口（{high_count} 个高优先级），类型分布：{type_desc}"
        else:
            return f"发现 {len(gaps)} 个次要缺口，类型分布：{type_desc}"

    def should_trigger_subnet(
        self,
        analysis_result: GapAnalysisResult,
        recursion_depth: int = 0,
        max_depth: int = 2
    ) -> bool:
        """
        判断是否应该触发子网

        Args:
            analysis_result: 缺口分析结果
            recursion_depth: 当前递归深度
            max_depth: 最大递归深度

        Returns:
            是否应该触发子网
        """
        # 检查递归深度限制
        if recursion_depth >= max_depth:
            self._logger.info(
                f"Subnet not triggered: max depth reached ({recursion_depth}/{max_depth})"
            )
            return False

        # 检查是否有需要触发子网的缺口
        if not analysis_result.subnet_recommended:
            self._logger.info("Subnet not triggered: no gaps recommend subnet")
            return False

        # 检查关键缺口数量
        if analysis_result.critical_gaps == 0:
            self._logger.info("Subnet not triggered: no critical gaps")
            return False

        self._logger.info(
            f"Subnet trigger recommended: {analysis_result.critical_gaps} critical gaps"
        )
        return True

    def get_subnet_demands(
        self,
        analysis_result: GapAnalysisResult,
        max_subnets: int = 3
    ) -> List[Dict[str, Any]]:
        """
        获取子网需求列表

        Args:
            analysis_result: 缺口分析结果
            max_subnets: 单层最大子网数

        Returns:
            子网需求列表
        """
        triggers = analysis_result.get_subnet_triggers()

        # 限制子网数量
        triggers = triggers[:max_subnets]

        sub_demands = []
        for gap in triggers:
            sub_demand = {
                "gap_id": gap.gap_id,
                "surface_demand": gap.suggested_sub_demand,
                "deep_understanding": {
                    "type": "sub_demand",
                    "motivation": f"填补缺口：{gap.description}",
                    "parent_gap_type": gap.gap_type.value,
                    "requirement": gap.requirement
                },
                "metadata": {
                    "parent_demand_id": analysis_result.demand_id,
                    "parent_channel_id": analysis_result.channel_id,
                    "gap_severity": gap.severity.value
                }
            }
            sub_demands.append(sub_demand)

        return sub_demands
