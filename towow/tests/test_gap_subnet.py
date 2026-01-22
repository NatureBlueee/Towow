"""
缺口识别与子网触发测试

测试 T06 任务的核心功能：
1. 缺口识别正确工作
2. 子网触发正确
3. 递归深度限制生效
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.gap_identification import GapIdentificationService
from services.gap_types import Gap, GapType, GapSeverity, GapAnalysisResult
from services.subnet_manager import SubnetManager


class TestGapIdentification:
    """缺口识别服务测试"""

    def test_gap_should_trigger_subnet_high_severity(self):
        """测试：高严重度 + 有子需求建议 => 应该触发子网"""
        gap = Gap(
            gap_id="gap-001",
            gap_type=GapType.RESOURCE,
            severity=GapSeverity.HIGH,
            description="缺少摄影师",
            requirement="需要专业摄影师",
            suggested_sub_demand="寻找有摄影能力的协作者"
        )
        assert gap.should_trigger_subnet() is True

    def test_gap_should_trigger_subnet_critical_severity(self):
        """测试：关键严重度 + 有子需求建议 => 应该触发子网"""
        gap = Gap(
            gap_id="gap-002",
            gap_type=GapType.CAPABILITY,
            severity=GapSeverity.CRITICAL,
            description="缺少核心技能",
            requirement="需要AI专家",
            suggested_sub_demand="寻找AI领域专家"
        )
        assert gap.should_trigger_subnet() is True

    def test_gap_should_not_trigger_subnet_low_severity(self):
        """测试：低严重度 => 不应该触发子网"""
        gap = Gap(
            gap_id="gap-003",
            gap_type=GapType.COVERAGE,
            severity=GapSeverity.LOW,
            description="可选的额外覆盖",
            requirement="额外资源",
            suggested_sub_demand="可以寻找更多参与者"
        )
        assert gap.should_trigger_subnet() is False

    def test_gap_should_not_trigger_subnet_no_suggestion(self):
        """测试：没有子需求建议 => 不应该触发子网"""
        gap = Gap(
            gap_id="gap-004",
            gap_type=GapType.RESOURCE,
            severity=GapSeverity.HIGH,
            description="资源缺口",
            requirement="需要场地",
            suggested_sub_demand=None
        )
        assert gap.should_trigger_subnet() is False

    def test_gap_analysis_result_statistics(self):
        """测试：缺口分析结果统计正确"""
        gaps = [
            Gap(
                gap_id="gap-1",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.CRITICAL,
                description="关键缺口",
                requirement="req1",
                suggested_sub_demand="sub1"
            ),
            Gap(
                gap_id="gap-2",
                gap_type=GapType.CAPABILITY,
                severity=GapSeverity.HIGH,
                description="高优先级缺口",
                requirement="req2",
                suggested_sub_demand="sub2"
            ),
            Gap(
                gap_id="gap-3",
                gap_type=GapType.CONDITION,
                severity=GapSeverity.MEDIUM,
                description="中等缺口",
                requirement="req3",
                suggested_sub_demand=None
            ),
        ]

        result = GapAnalysisResult(
            channel_id="ch-001",
            demand_id="d-001",
            proposal={},
            gaps=gaps
        )

        assert result.total_gaps == 3
        assert result.critical_gaps == 2  # CRITICAL + HIGH
        assert result.subnet_recommended is True  # 有能触发子网的缺口

    @pytest.mark.asyncio
    async def test_identify_gaps_participant_count(self):
        """测试：参与者数量不足时识别缺口"""
        service = GapIdentificationService(llm_service=None)

        demand = {
            "surface_demand": "办一场50人的活动",
            "deep_understanding": {
                "scale": {"participants": 5}
            }
        }
        proposal = {}
        participants = [
            {"agent_id": "agent1", "decision": "participate"},
            {"agent_id": "agent2", "decision": "participate"}
        ]

        result = await service.identify_gaps(
            demand=demand,
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
        assert len(participant_gaps) > 0

    @pytest.mark.asyncio
    async def test_identify_gaps_resource_coverage(self):
        """测试：资源需求未覆盖时识别缺口"""
        service = GapIdentificationService(llm_service=None)

        demand = {
            "surface_demand": "办活动",
            "deep_understanding": {
                "resource_requirements": ["场地", "摄影师", "茶歇"]
            }
        }
        proposal = {}
        participants = [
            {
                "agent_id": "agent1",
                "decision": "participate",
                "contribution": "我可以提供场地",
                "capabilities": ["场地"]
            }
        ]

        result = await service.identify_gaps(
            demand=demand,
            proposal=proposal,
            participants=participants,
            channel_id="ch-001",
            demand_id="d-001"
        )

        # 应该识别出资源缺口（摄影师、茶歇未覆盖）
        resource_gaps = [
            g for g in result.gaps
            if g.gap_type == GapType.RESOURCE
        ]
        assert len(resource_gaps) >= 1


class TestSubnetManager:
    """子网管理器测试"""

    def test_max_recursion_depth_is_one(self):
        """测试：MVP 阶段最大递归深度为 1"""
        assert SubnetManager.MAX_RECURSION_DEPTH == 1

    def test_recursion_depth_limit_check(self):
        """测试：递归深度限制检查"""
        manager = SubnetManager(max_depth=1)

        # 创建一个建议触发子网的分析结果
        gaps = [
            Gap(
                gap_id="gap-1",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.CRITICAL,
                description="关键缺口",
                requirement="req",
                suggested_sub_demand="sub"
            )
        ]
        result = GapAnalysisResult(
            channel_id="ch-001",
            demand_id="d-001",
            proposal={},
            gaps=gaps
        )

        # 深度 0：应该触发
        service = GapIdentificationService()
        should_trigger = service.should_trigger_subnet(result, recursion_depth=0, max_depth=1)
        assert should_trigger is True

        # 深度 1：不应该触发（已达到最大深度）
        should_trigger = service.should_trigger_subnet(result, recursion_depth=1, max_depth=1)
        assert should_trigger is False

    def test_get_subnet_demands(self):
        """测试：获取子网需求列表"""
        service = GapIdentificationService()

        gaps = [
            Gap(
                gap_id="gap-1",
                gap_type=GapType.RESOURCE,
                severity=GapSeverity.CRITICAL,
                description="缺少摄影师",
                requirement="需要摄影",
                suggested_sub_demand="寻找摄影师"
            ),
            Gap(
                gap_id="gap-2",
                gap_type=GapType.CAPABILITY,
                severity=GapSeverity.HIGH,
                description="缺少主持人",
                requirement="需要主持",
                suggested_sub_demand="寻找主持人"
            ),
            Gap(
                gap_id="gap-3",
                gap_type=GapType.CONDITION,
                severity=GapSeverity.LOW,
                description="低优先级缺口",
                requirement="低优先级",
                suggested_sub_demand="可选"
            )
        ]
        result = GapAnalysisResult(
            channel_id="ch-001",
            demand_id="d-001",
            proposal={},
            gaps=gaps
        )

        # 获取子网需求（只有 CRITICAL/HIGH + 有建议的才会触发）
        sub_demands = service.get_subnet_demands(result, max_subnets=3)

        assert len(sub_demands) == 2  # 只有 gap-1 和 gap-2
        assert sub_demands[0]["gap_id"] == "gap-1"
        assert sub_demands[1]["gap_id"] == "gap-2"


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_gap_identification_flow(self):
        """测试：完整的缺口识别流程"""
        # 模拟一个需要触发子网的场景
        demand = {
            "surface_demand": "办一场AI主题聚会，需要场地和摄影",
            "capability_tags": ["场地", "摄影"],
            "deep_understanding": {
                "resource_requirements": ["场地", "摄影师"],
                "scale": {"participants": 3}
            }
        }

        proposal = {
            "summary": "AI聚会方案",
            "assignments": [
                {"agent_id": "agent1", "role": "场地提供者", "responsibility": "提供场地"}
            ]
        }

        participants = [
            {
                "agent_id": "agent1",
                "decision": "participate",
                "contribution": "我可以提供场地",
                "capabilities": ["场地"]
            }
        ]

        # 执行缺口识别
        service = GapIdentificationService(llm_service=None)
        result = await service.identify_gaps(
            demand=demand,
            proposal=proposal,
            participants=participants,
            channel_id="ch-001",
            demand_id="d-001"
        )

        # 验证识别出了摄影师缺口
        assert result.total_gaps >= 1

        # 验证应该触发子网
        resource_gaps = [g for g in result.gaps if g.gap_type == GapType.RESOURCE]
        assert len(resource_gaps) >= 1

        # 找到摄影师相关的缺口
        photography_gaps = [
            g for g in resource_gaps
            if "摄影" in g.description or "摄影" in g.requirement
        ]
        assert len(photography_gaps) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
