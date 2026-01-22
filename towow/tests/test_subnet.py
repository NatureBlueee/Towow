"""
Tests for Gap Identification and Subnet Manager

测试递归子网机制的核心功能：
1. 缺口类型定义
2. 缺口识别服务
3. 子网管理器
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.gap_types import (
    GapType,
    GapSeverity,
    Gap,
    GapAnalysisResult
)
from services.gap_identification import GapIdentificationService
from services.subnet_manager import (
    SubnetStatus,
    SubnetInfo,
    SubnetResult,
    SubnetManager
)


# ==================== Gap Types Tests ====================

class TestGapType:
    """测试缺口类型枚举"""

    def test_gap_type_values(self):
        """测试缺口类型枚举值"""
        assert GapType.CAPABILITY.value == "capability"
        assert GapType.RESOURCE.value == "resource"
        assert GapType.PARTICIPANT.value == "participant"
        assert GapType.COVERAGE.value == "coverage"
        assert GapType.CONDITION.value == "condition"

    def test_gap_severity_values(self):
        """测试严重程度枚举值"""
        assert GapSeverity.CRITICAL.value == "critical"
        assert GapSeverity.HIGH.value == "high"
        assert GapSeverity.MEDIUM.value == "medium"
        assert GapSeverity.LOW.value == "low"


class TestGap:
    """测试 Gap 数据类"""

    def test_gap_creation(self):
        """测试缺口创建"""
        gap = Gap(
            gap_id="gap-001",
            gap_type=GapType.RESOURCE,
            severity=GapSeverity.HIGH,
            description="缺少场地资源",
            requirement="需要可容纳50人的场地",
            suggested_sub_demand="寻找能提供场地的协作者"
        )

        assert gap.gap_id == "gap-001"
        assert gap.gap_type == GapType.RESOURCE
        assert gap.severity == GapSeverity.HIGH
        assert gap.description == "缺少场地资源"
        assert gap.suggested_sub_demand is not None

    def test_gap_to_dict(self):
        """测试缺口转字典"""
        gap = Gap(
            gap_id="gap-001",
            gap_type=GapType.CAPABILITY,
            severity=GapSeverity.MEDIUM,
            description="测试缺口",
            requirement="测试需求"
        )

        data = gap.to_dict()

        assert data["gap_id"] == "gap-001"
        assert data["gap_type"] == "capability"
        assert data["severity"] == "medium"

    def test_gap_from_dict(self):
        """测试从字典创建缺口"""
        data = {
            "gap_id": "gap-002",
            "gap_type": "resource",
            "severity": "high",
            "description": "资源缺口",
            "requirement": "需要资源"
        }

        gap = Gap.from_dict(data)

        assert gap.gap_id == "gap-002"
        assert gap.gap_type == GapType.RESOURCE
        assert gap.severity == GapSeverity.HIGH

    def test_should_trigger_subnet_true(self):
        """测试应该触发子网的情况"""
        gap = Gap(
            gap_id="gap-001",
            gap_type=GapType.RESOURCE,
            severity=GapSeverity.CRITICAL,
            description="关键资源缺失",
            requirement="需要资源",
            suggested_sub_demand="寻找资源提供者"
        )

        assert gap.should_trigger_subnet() is True

    def test_should_trigger_subnet_false_low_severity(self):
        """测试低优先级不触发子网"""
        gap = Gap(
            gap_id="gap-001",
            gap_type=GapType.RESOURCE,
            severity=GapSeverity.LOW,
            description="次要资源缺失",
            requirement="需要资源",
            suggested_sub_demand="寻找资源提供者"
        )

        assert gap.should_trigger_subnet() is False

    def test_should_trigger_subnet_false_no_suggestion(self):
        """测试无建议子需求不触发子网"""
        gap = Gap(
            gap_id="gap-001",
            gap_type=GapType.RESOURCE,
            severity=GapSeverity.HIGH,
            description="资源缺失",
            requirement="需要资源",
            suggested_sub_demand=None
        )

        assert gap.should_trigger_subnet() is False


class TestGapAnalysisResult:
    """测试缺口分析结果"""

    def test_result_creation(self):
        """测试分析结果创建"""
        gaps = [
            Gap(
                gap_id="gap-001",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.HIGH,
                description="资源缺口",
                requirement="需要资源",
                suggested_sub_demand="寻找资源"
            ),
            Gap(
                gap_id="gap-002",
                gap_type=GapType.CAPABILITY,
                severity=GapSeverity.LOW,
                description="能力缺口",
                requirement="需要能力"
            )
        ]

        result = GapAnalysisResult(
            channel_id="ch-001",
            demand_id="d-001",
            proposal={"summary": "测试方案"},
            gaps=gaps
        )

        assert result.total_gaps == 2
        assert result.critical_gaps == 1  # HIGH counts as critical
        assert result.subnet_recommended is True

    def test_get_subnet_triggers(self):
        """测试获取触发子网的缺口"""
        gaps = [
            Gap(
                gap_id="gap-001",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.CRITICAL,
                description="关键缺口",
                requirement="需要",
                suggested_sub_demand="子需求1"
            ),
            Gap(
                gap_id="gap-002",
                gap_type=GapType.CAPABILITY,
                severity=GapSeverity.LOW,
                description="次要缺口",
                requirement="需要"
            )
        ]

        result = GapAnalysisResult(
            channel_id="ch-001",
            demand_id="d-001",
            proposal={},
            gaps=gaps
        )

        triggers = result.get_subnet_triggers()
        assert len(triggers) == 1
        assert triggers[0].gap_id == "gap-001"


# ==================== Gap Identification Service Tests ====================

class TestGapIdentificationService:
    """测试缺口识别服务"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return GapIdentificationService()

    @pytest.fixture
    def sample_demand(self):
        """示例需求"""
        return {
            "surface_demand": "组织一场技术分享活动",
            "deep_understanding": {
                "type": "event",
                "motivation": "知识分享",
                "scale": {"participants": 20},
                "resource_requirements": ["场地", "投影设备", "茶歇"]
            }
        }

    @pytest.fixture
    def sample_proposal(self):
        """示例方案"""
        return {
            "summary": "技术分享活动方案",
            "assignments": [
                {
                    "agent_id": "agent-001",
                    "role": "讲师",
                    "responsibility": "分享技术内容",
                    "conditions_addressed": []
                }
            ]
        }

    @pytest.fixture
    def sample_participants(self):
        """示例参与者"""
        return [
            {
                "agent_id": "agent-001",
                "decision": "participate",
                "capabilities": ["技术分享", "讲座"],
                "contribution": "提供技术分享"
            }
        ]

    @pytest.mark.asyncio
    async def test_identify_gaps_participant_count(self, service, sample_demand):
        """测试参与者数量缺口识别"""
        # 只有1个参与者，但需要20人规模
        participants = [
            {"agent_id": "agent-001", "decision": "participate"}
        ]
        proposal = {"assignments": []}

        result = await service.identify_gaps(
            demand=sample_demand,
            proposal=proposal,
            participants=participants,
            channel_id="ch-001",
            demand_id="d-001"
        )

        # 应该识别出参与者缺口
        participant_gaps = [
            g for g in result.gaps
            if g.gap_type == GapType.PARTICIPANT
        ]
        assert len(participant_gaps) >= 1

    @pytest.mark.asyncio
    async def test_identify_gaps_resource_coverage(
        self, service, sample_demand, sample_proposal
    ):
        """测试资源覆盖缺口识别"""
        # 参与者只提供技术分享，但需求还需要场地、设备、茶歇
        participants = [
            {
                "agent_id": "agent-001",
                "decision": "participate",
                "capabilities": ["技术分享"],
                "contribution": "技术分享"
            }
        ]

        result = await service.identify_gaps(
            demand=sample_demand,
            proposal=sample_proposal,
            participants=participants,
            channel_id="ch-001",
            demand_id="d-001"
        )

        # 应该识别出资源缺口（场地、投影设备、茶歇）
        resource_gaps = [
            g for g in result.gaps
            if g.gap_type == GapType.RESOURCE
        ]
        assert len(resource_gaps) >= 1

    @pytest.mark.asyncio
    async def test_identify_gaps_condition_unmet(self, service, sample_demand):
        """测试条件未满足缺口识别"""
        participants = [
            {
                "agent_id": "agent-001",
                "decision": "conditional",
                "conditions": ["需要报销交通费", "需要提供午餐"],
                "contribution": "技术分享"
            }
        ]
        proposal = {
            "assignments": [
                {
                    "agent_id": "agent-001",
                    "conditions_addressed": []  # 没有满足任何条件
                }
            ]
        }

        result = await service.identify_gaps(
            demand=sample_demand,
            proposal=proposal,
            participants=participants,
            channel_id="ch-001",
            demand_id="d-001"
        )

        # 应该识别出条件缺口
        condition_gaps = [
            g for g in result.gaps
            if g.gap_type == GapType.CONDITION
        ]
        assert len(condition_gaps) >= 1

    def test_should_trigger_subnet_respects_depth(self, service):
        """测试子网触发考虑递归深度"""
        gaps = [
            Gap(
                gap_id="gap-001",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.CRITICAL,
                description="关键缺口",
                requirement="需要",
                suggested_sub_demand="子需求"
            )
        ]
        result = GapAnalysisResult(
            channel_id="ch-001",
            demand_id="d-001",
            proposal={},
            gaps=gaps
        )

        # 深度0，应该触发
        assert service.should_trigger_subnet(result, recursion_depth=0, max_depth=2) is True

        # 深度2（等于最大深度），不应该触发
        assert service.should_trigger_subnet(result, recursion_depth=2, max_depth=2) is False

    def test_get_subnet_demands(self, service):
        """测试获取子网需求列表"""
        gaps = [
            Gap(
                gap_id="gap-001",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.CRITICAL,
                description="缺少场地",
                requirement="场地",
                suggested_sub_demand="寻找场地提供者"
            ),
            Gap(
                gap_id="gap-002",
                gap_type=GapType.CAPABILITY,
                severity=GapSeverity.HIGH,
                description="缺少设计师",
                requirement="设计能力",
                suggested_sub_demand="寻找设计师"
            ),
            Gap(
                gap_id="gap-003",
                gap_type=GapType.CONDITION,
                severity=GapSeverity.LOW,
                description="条件未满足",
                requirement="条件"
            )
        ]
        result = GapAnalysisResult(
            channel_id="ch-001",
            demand_id="d-001",
            proposal={},
            gaps=gaps
        )

        # 最多返回2个
        sub_demands = service.get_subnet_demands(result, max_subnets=2)

        assert len(sub_demands) == 2
        assert sub_demands[0]["gap_id"] == "gap-001"
        assert sub_demands[1]["gap_id"] == "gap-002"


# ==================== Subnet Manager Tests ====================

class TestSubnetInfo:
    """测试子网信息数据类"""

    def test_subnet_info_creation(self):
        """测试子网信息创建"""
        subnet = SubnetInfo(
            subnet_id="subnet-001",
            parent_channel_id="ch-001",
            parent_demand_id="d-001",
            gap_id="gap-001",
            sub_demand={"surface_demand": "子需求"},
            recursion_depth=1
        )

        assert subnet.subnet_id == "subnet-001"
        assert subnet.status == SubnetStatus.PENDING
        assert subnet.recursion_depth == 1
        assert subnet.is_active() is True
        assert subnet.is_finished() is False

    def test_subnet_info_status_transitions(self):
        """测试子网状态转换"""
        subnet = SubnetInfo(
            subnet_id="subnet-001",
            parent_channel_id="ch-001",
            parent_demand_id="d-001",
            gap_id="gap-001",
            sub_demand={},
            recursion_depth=1
        )

        # 初始状态
        assert subnet.is_active() is True

        # 完成状态
        subnet.status = SubnetStatus.COMPLETED
        assert subnet.is_active() is False
        assert subnet.is_finished() is True

    def test_subnet_info_to_dict(self):
        """测试子网信息转字典"""
        subnet = SubnetInfo(
            subnet_id="subnet-001",
            parent_channel_id="ch-001",
            parent_demand_id="d-001",
            gap_id="gap-001",
            sub_demand={"test": "data"},
            recursion_depth=1
        )

        data = subnet.to_dict()

        assert data["subnet_id"] == "subnet-001"
        assert data["status"] == "pending"
        assert data["recursion_depth"] == 1


class TestSubnetManager:
    """测试子网管理器"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return SubnetManager(
            max_depth=2,
            max_subnets=3,
            default_timeout=180
        )

    @pytest.fixture
    def sample_analysis_result(self):
        """示例缺口分析结果"""
        gaps = [
            Gap(
                gap_id="gap-001",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.CRITICAL,
                description="缺少场地",
                requirement="场地",
                suggested_sub_demand="寻找场地"
            )
        ]
        return GapAnalysisResult(
            channel_id="ch-001",
            demand_id="d-001",
            proposal={"summary": "测试方案"},
            gaps=gaps
        )

    @pytest.mark.asyncio
    async def test_process_gaps_creates_subnet(self, manager, sample_analysis_result):
        """测试处理缺口创建子网"""
        # 设置 mock 子网创建器
        async def mock_creator(demand, parent_id, depth):
            return f"subnet-ch-{depth}"

        manager.set_subnet_creator(mock_creator)

        subnets = await manager.process_gaps(sample_analysis_result, recursion_depth=0)

        assert len(subnets) == 1
        assert subnets[0].gap_id == "gap-001"
        assert subnets[0].recursion_depth == 1

    @pytest.mark.asyncio
    async def test_process_gaps_respects_max_depth(self, manager, sample_analysis_result):
        """测试处理缺口尊重最大深度"""
        # 深度已达到最大值
        subnets = await manager.process_gaps(sample_analysis_result, recursion_depth=2)

        assert len(subnets) == 0

    @pytest.mark.asyncio
    async def test_handle_subnet_completed_success(self, manager):
        """测试处理子网完成（成功）"""
        # 先创建一个子网
        subnet = SubnetInfo(
            subnet_id="subnet-001",
            parent_channel_id="ch-001",
            parent_demand_id="d-001",
            gap_id="gap-001",
            sub_demand={},
            recursion_depth=1,
            status=SubnetStatus.RUNNING,
            channel_id="subnet-ch-001"
        )
        manager._subnets[subnet.subnet_id] = subnet
        manager._parent_children["ch-001"] = [subnet.subnet_id]

        result = await manager.handle_subnet_completed(
            channel_id="subnet-ch-001",
            success=True,
            proposal={"summary": "子方案"},
            participants=["agent-001", "agent-002"]
        )

        assert result is not None
        assert result.success is True
        assert result.proposal == {"summary": "子方案"}
        assert subnet.status == SubnetStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_handle_subnet_completed_failure(self, manager):
        """测试处理子网完成（失败）"""
        subnet = SubnetInfo(
            subnet_id="subnet-001",
            parent_channel_id="ch-001",
            parent_demand_id="d-001",
            gap_id="gap-001",
            sub_demand={},
            recursion_depth=1,
            status=SubnetStatus.RUNNING,
            channel_id="subnet-ch-001"
        )
        manager._subnets[subnet.subnet_id] = subnet

        result = await manager.handle_subnet_completed(
            channel_id="subnet-ch-001",
            success=False,
            error="no_participants"
        )

        assert result is not None
        assert result.success is False
        assert result.error == "no_participants"
        assert subnet.status == SubnetStatus.FAILED

    def test_integrate_subnet_results(self, manager):
        """测试整合子网结果"""
        # 创建已完成的子网
        subnet = SubnetInfo(
            subnet_id="subnet-001",
            parent_channel_id="ch-001",
            parent_demand_id="d-001",
            gap_id="gap-001",
            sub_demand={},
            recursion_depth=1,
            status=SubnetStatus.COMPLETED,
            result={
                "success": True,
                "proposal": {
                    "assignments": [
                        {"agent_id": "agent-new", "role": "场地提供者"}
                    ]
                },
                "participants": ["agent-new"]
            }
        )
        manager._subnets[subnet.subnet_id] = subnet
        manager._parent_children["ch-001"] = [subnet.subnet_id]

        parent_proposal = {
            "summary": "父方案",
            "assignments": [
                {"agent_id": "agent-001", "role": "讲师"}
            ]
        }

        integrated = manager.integrate_subnet_results("ch-001", parent_proposal)

        # 检查整合结果
        assert "subnet_integration" in integrated
        assert integrated["subnet_integration"]["successful"] == 1
        assert len(integrated["assignments"]) == 2

    @pytest.mark.asyncio
    async def test_cancel_subnet(self, manager):
        """测试取消子网"""
        subnet = SubnetInfo(
            subnet_id="subnet-001",
            parent_channel_id="ch-001",
            parent_demand_id="d-001",
            gap_id="gap-001",
            sub_demand={},
            recursion_depth=1,
            status=SubnetStatus.RUNNING
        )
        manager._subnets[subnet.subnet_id] = subnet

        result = await manager.cancel_subnet("subnet-001", reason="test_cancel")

        assert result is True
        assert subnet.status == SubnetStatus.CANCELLED
        assert subnet.result["reason"] == "test_cancel"

    def test_get_statistics(self, manager):
        """测试获取统计信息"""
        # 添加一些子网
        for i in range(3):
            subnet = SubnetInfo(
                subnet_id=f"subnet-{i:03d}",
                parent_channel_id="ch-001",
                parent_demand_id="d-001",
                gap_id=f"gap-{i:03d}",
                sub_demand={},
                recursion_depth=1
            )
            manager._subnets[subnet.subnet_id] = subnet

        # 修改一些状态
        manager._subnets["subnet-000"].status = SubnetStatus.COMPLETED
        manager._subnets["subnet-001"].status = SubnetStatus.RUNNING

        stats = manager.get_statistics()

        assert stats["total_subnets"] == 3
        assert stats["active_subnets"] == 2  # PENDING and RUNNING
        assert stats["by_status"]["completed"] == 1
        assert stats["by_status"]["running"] == 1
        assert stats["max_depth_configured"] == 2

    def test_get_subnets_by_parent(self, manager):
        """测试按父 Channel 获取子网"""
        # 添加子网到不同父 Channel
        for i in range(2):
            subnet = SubnetInfo(
                subnet_id=f"subnet-a-{i}",
                parent_channel_id="ch-001",
                parent_demand_id="d-001",
                gap_id=f"gap-{i}",
                sub_demand={},
                recursion_depth=1
            )
            manager._subnets[subnet.subnet_id] = subnet

        for i in range(3):
            subnet = SubnetInfo(
                subnet_id=f"subnet-b-{i}",
                parent_channel_id="ch-002",
                parent_demand_id="d-002",
                gap_id=f"gap-{i}",
                sub_demand={},
                recursion_depth=1
            )
            manager._subnets[subnet.subnet_id] = subnet

        manager._parent_children["ch-001"] = ["subnet-a-0", "subnet-a-1"]
        manager._parent_children["ch-002"] = ["subnet-b-0", "subnet-b-1", "subnet-b-2"]

        ch1_subnets = manager.get_subnets_by_parent("ch-001")
        ch2_subnets = manager.get_subnets_by_parent("ch-002")

        assert len(ch1_subnets) == 2
        assert len(ch2_subnets) == 3


# ==================== Integration Tests ====================

class TestSubnetIntegration:
    """递归子网集成测试"""

    @pytest.mark.asyncio
    async def test_full_subnet_flow(self):
        """测试完整的子网流程"""
        # 1. 创建服务
        gap_service = GapIdentificationService()
        manager = SubnetManager(
            gap_service=gap_service,
            max_depth=2,
            max_subnets=3
        )

        # 2. 设置事件发布器
        published_events = []

        async def event_publisher(event_type, payload):
            published_events.append((event_type, payload))

        manager.set_event_publisher(event_publisher)

        # 3. 设置子网创建器
        created_channels = []

        async def subnet_creator(demand, parent_id, depth):
            channel_id = f"subnet-ch-{len(created_channels)}"
            created_channels.append({
                "channel_id": channel_id,
                "demand": demand,
                "depth": depth
            })
            return channel_id

        manager.set_subnet_creator(subnet_creator)

        # 4. 创建缺口分析结果
        gaps = [
            Gap(
                gap_id="gap-001",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.CRITICAL,
                description="缺少场地",
                requirement="场地",
                suggested_sub_demand="寻找能提供场地的协作者"
            )
        ]
        analysis = GapAnalysisResult(
            channel_id="main-ch-001",
            demand_id="d-001",
            proposal={"summary": "主方案"},
            gaps=gaps
        )

        # 5. 处理缺口
        subnets = await manager.process_gaps(analysis, recursion_depth=0)

        # 验证子网创建
        assert len(subnets) == 1
        assert len(created_channels) == 1

        # 6. 模拟子网完成
        await manager.handle_subnet_completed(
            channel_id=created_channels[0]["channel_id"],
            success=True,
            proposal={
                "summary": "子方案",
                "assignments": [
                    {"agent_id": "venue-agent", "role": "场地提供者"}
                ]
            },
            participants=["venue-agent"]
        )

        # 7. 整合结果
        integrated = manager.integrate_subnet_results(
            "main-ch-001",
            {"summary": "主方案", "assignments": []}
        )

        # 验证整合
        assert integrated["subnet_integration"]["successful"] == 1
        assert len(integrated["assignments"]) == 1
        assert integrated["assignments"][0]["source"] == "subnet"

        # 8. 验证事件发布
        event_types = [e[0] for e in published_events]
        assert "towow.subnet.created" in event_types
        assert "towow.subnet.started" in event_types
        assert "towow.subnet.completed" in event_types
