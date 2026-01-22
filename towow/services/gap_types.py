"""
Gap Types - ToWow 递归子网缺口类型定义

定义方案缺口的类型和数据结构，用于子网触发决策。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class GapType(Enum):
    """
    缺口类型枚举

    定义协作方案中可能出现的缺口类型：
    - CAPABILITY: 能力缺口 - 缺少必要的技能或专业能力
    - RESOURCE: 资源缺口 - 缺少必要的资源（场地、设备等）
    - PARTICIPANT: 参与者缺口 - 参与者数量不足
    - COVERAGE: 覆盖缺口 - 某些需求维度未被覆盖
    - CONDITION: 条件缺口 - 参与者条件无法满足
    """
    CAPABILITY = "capability"      # 能力缺口
    RESOURCE = "resource"          # 资源缺口
    PARTICIPANT = "participant"    # 参与者缺口
    COVERAGE = "coverage"          # 覆盖缺口
    CONDITION = "condition"        # 条件缺口


class GapSeverity(Enum):
    """
    缺口严重程度枚举

    - CRITICAL: 关键缺口，必须解决才能继续
    - HIGH: 高优先级，强烈建议解决
    - MEDIUM: 中等优先级，建议解决
    - LOW: 低优先级，可选解决
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Gap:
    """
    缺口数据类

    描述协作方案中的一个缺口，包含类型、描述、建议的子需求等信息。

    Attributes:
        gap_id: 缺口唯一标识
        gap_type: 缺口类型
        severity: 严重程度
        description: 缺口描述
        requirement: 原始需求描述（缺少什么）
        suggested_sub_demand: 建议的子需求描述（用于触发子网）
        affected_aspects: 受影响的方案方面
        potential_solutions: 潜在解决方案列表
        metadata: 额外元数据
        created_at: 创建时间
    """
    gap_id: str
    gap_type: GapType
    severity: GapSeverity
    description: str
    requirement: str
    suggested_sub_demand: Optional[str] = None
    affected_aspects: List[str] = field(default_factory=list)
    potential_solutions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "requirement": self.requirement,
            "suggested_sub_demand": self.suggested_sub_demand,
            "affected_aspects": self.affected_aspects,
            "potential_solutions": self.potential_solutions,
            "metadata": self.metadata,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Gap":
        """从字典创建 Gap 实例"""
        return cls(
            gap_id=data["gap_id"],
            gap_type=GapType(data["gap_type"]),
            severity=GapSeverity(data.get("severity", "medium")),
            description=data["description"],
            requirement=data["requirement"],
            suggested_sub_demand=data.get("suggested_sub_demand"),
            affected_aspects=data.get("affected_aspects", []),
            potential_solutions=data.get("potential_solutions", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat())
        )

    def should_trigger_subnet(self) -> bool:
        """
        判断该缺口是否应该触发子网

        触发条件：
        1. 严重程度为 CRITICAL 或 HIGH
        2. 有建议的子需求描述

        Returns:
            是否应该触发子网
        """
        return (
            self.severity in (GapSeverity.CRITICAL, GapSeverity.HIGH) and
            self.suggested_sub_demand is not None and
            len(self.suggested_sub_demand.strip()) > 0
        )


@dataclass
class GapAnalysisResult:
    """
    缺口分析结果

    包含完整的缺口分析结果，用于决策是否触发子网。

    Attributes:
        channel_id: 相关的 Channel ID
        demand_id: 相关的需求 ID
        proposal: 被分析的方案
        gaps: 识别出的缺口列表
        total_gaps: 总缺口数
        critical_gaps: 关键缺口数
        subnet_recommended: 是否建议触发子网
        analysis_summary: 分析摘要
        analyzed_at: 分析时间
    """
    channel_id: str
    demand_id: str
    proposal: Dict[str, Any]
    gaps: List[Gap]
    total_gaps: int = 0
    critical_gaps: int = 0
    subnet_recommended: bool = False
    analysis_summary: str = ""
    analyzed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self):
        """初始化后计算统计信息"""
        self.total_gaps = len(self.gaps)
        self.critical_gaps = sum(
            1 for g in self.gaps
            if g.severity in (GapSeverity.CRITICAL, GapSeverity.HIGH)
        )
        self.subnet_recommended = any(g.should_trigger_subnet() for g in self.gaps)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "channel_id": self.channel_id,
            "demand_id": self.demand_id,
            "proposal": self.proposal,
            "gaps": [g.to_dict() for g in self.gaps],
            "total_gaps": self.total_gaps,
            "critical_gaps": self.critical_gaps,
            "subnet_recommended": self.subnet_recommended,
            "analysis_summary": self.analysis_summary,
            "analyzed_at": self.analyzed_at
        }

    def get_subnet_triggers(self) -> List[Gap]:
        """获取应该触发子网的缺口列表"""
        return [g for g in self.gaps if g.should_trigger_subnet()]
