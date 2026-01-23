"""
T07: StateChecker 单元测试

测试状态检查与恢复机制的核心功能：
- AC-1: StateChecker 每 5 秒检查一次活跃 Channel
- AC-2: 卡在 COLLECTING 超过 120 秒触发恢复
- AC-3: 卡在 NEGOTIATING 超过 120 秒触发恢复
- AC-4: 恢复尝试最多 3 次，超过标记失败
- AC-5: 恢复操作是幂等的
- AC-6: 日志记录恢复尝试和结果
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# 设置测试环境
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.state_checker import (
    StateChecker,
    CheckResult,
    StateCheckResult,
    RecoveryAttempt,
    ChannelRecoveryState,
)
from openagents.agents.channel_admin import ChannelStatus, ChannelState


class MockChannelAdmin:
    """Mock ChannelAdmin 用于测试"""

    def __init__(self):
        self.channels = {}
        self._aggregate_proposals_called = []
        self._broadcast_demand_called = []
        self._evaluate_feedback_called = []
        self._distribute_proposal_called = []
        self._force_finalize_channel_called = []
        self._fail_channel_called = []

    def get_active_channels(self):
        """返回活跃 Channel 列表"""
        active_statuses = {
            ChannelStatus.CREATED,
            ChannelStatus.BROADCASTING,
            ChannelStatus.COLLECTING,
            ChannelStatus.AGGREGATING,
            ChannelStatus.PROPOSAL_SENT,
            ChannelStatus.NEGOTIATING,
        }
        return [
            cid for cid, state in self.channels.items()
            if state.status in active_statuses
        ]

    async def _aggregate_proposals(self, state):
        self._aggregate_proposals_called.append(state.channel_id)

    async def _broadcast_demand(self, state):
        self._broadcast_demand_called.append(state.channel_id)

    async def _evaluate_feedback(self, state):
        self._evaluate_feedback_called.append(state.channel_id)

    async def _distribute_proposal(self, state):
        self._distribute_proposal_called.append(state.channel_id)

    async def _force_finalize_channel(self, state):
        self._force_finalize_channel_called.append(state.channel_id)
        state.status = ChannelStatus.FORCE_FINALIZED

    async def _fail_channel(self, state, reason):
        self._fail_channel_called.append((state.channel_id, reason))
        state.status = ChannelStatus.FAILED

    def _get_fallback_proposal_v4(self, state, offers, negotiations):
        return {"summary": "fallback", "assignments": []}


def create_test_channel_state(
    channel_id: str,
    status: ChannelStatus = ChannelStatus.COLLECTING,
    created_at: datetime = None,
    responses: dict = None,
    candidates: list = None,
    proposal_feedback: dict = None,
) -> ChannelState:
    """创建测试用的 ChannelState"""
    if created_at is None:
        created_at = datetime.utcnow()

    state = ChannelState(
        channel_id=channel_id,
        demand_id=f"demand-{channel_id}",
        demand={"surface_demand": "test demand"},
        candidates=candidates or [{"agent_id": "agent1"}, {"agent_id": "agent2"}],
    )
    state.status = status
    state.created_at = created_at.isoformat()
    state.responses = responses or {}
    state.proposal_feedback = proposal_feedback or {}
    return state


class TestStateCheckerInit:
    """StateChecker 初始化测试"""

    def test_init_with_defaults(self):
        """测试默认配置初始化"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        assert checker.check_interval == 5
        assert checker.max_stuck_time == 120
        assert checker.max_recovery_attempts == 3
        assert checker._running is False

    def test_init_with_custom_config(self):
        """测试自定义配置初始化"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(
            mock_admin,
            check_interval=10,
            max_stuck_time=60,
            max_recovery_attempts=5
        )

        assert checker.check_interval == 10
        assert checker.max_stuck_time == 60
        assert checker.max_recovery_attempts == 5


class TestStateCheckerStartStop:
    """StateChecker 启动/停止测试"""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """测试启动和停止"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, check_interval=1)

        assert not checker.is_running

        await checker.start()
        assert checker.is_running

        # 等待一小段时间让检查循环运行
        await asyncio.sleep(0.1)

        await checker.stop()
        assert not checker.is_running

    @pytest.mark.asyncio
    async def test_double_start_ignored(self):
        """测试重复启动被忽略"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, check_interval=1)

        await checker.start()
        await checker.start()  # 应该被忽略

        assert checker.is_running

        await checker.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """测试未运行时停止"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        await checker.stop()  # 应该安全执行
        assert not checker.is_running


class TestCheckChannel:
    """Channel 检查测试"""

    @pytest.mark.asyncio
    async def test_healthy_channel(self):
        """测试健康状态的 Channel"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, max_stuck_time=120)

        # 创建一个刚刚创建的 Channel
        state = create_test_channel_state("ch-001", ChannelStatus.COLLECTING)
        mock_admin.channels["ch-001"] = state

        result = await checker.check_channel("ch-001")

        assert result.healthy is True
        assert result.channel_id == "ch-001"
        assert result.status == "collecting"

    @pytest.mark.asyncio
    async def test_stuck_in_collecting(self):
        """AC-2: 测试卡在 COLLECTING 状态"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, max_stuck_time=120)

        # 创建一个已经卡了很久的 Channel
        old_time = datetime.utcnow() - timedelta(seconds=200)
        state = create_test_channel_state(
            "ch-002",
            ChannelStatus.COLLECTING,
            created_at=old_time
        )
        mock_admin.channels["ch-002"] = state

        # 初始化恢复状态，并设置 last_status 以避免状态变更重置
        recovery_state = checker._get_or_create_recovery_state("ch-002")
        recovery_state.last_status = "collecting"  # 设置为当前状态
        recovery_state.last_status_change_time = old_time

        result = await checker.check_channel("ch-002")

        assert result.healthy is False
        assert result.reason == CheckResult.STUCK_IN_COLLECTING
        assert "stuck" in result.details.lower()
        assert result.stuck_duration_seconds > 120

    @pytest.mark.asyncio
    async def test_stuck_in_negotiating(self):
        """AC-3: 测试卡在 NEGOTIATING 状态"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, max_stuck_time=120)

        # 创建一个卡在 NEGOTIATING 的 Channel
        old_time = datetime.utcnow() - timedelta(seconds=200)
        state = create_test_channel_state(
            "ch-003",
            ChannelStatus.NEGOTIATING,
            created_at=old_time
        )
        mock_admin.channels["ch-003"] = state

        # 初始化恢复状态，并设置 last_status 以避免状态变更重置
        recovery_state = checker._get_or_create_recovery_state("ch-003")
        recovery_state.last_status = "negotiating"  # 设置为当前状态
        recovery_state.last_status_change_time = old_time

        result = await checker.check_channel("ch-003")

        assert result.healthy is False
        assert result.reason == CheckResult.STUCK_IN_NEGOTIATING

    @pytest.mark.asyncio
    async def test_missing_responses(self):
        """测试缺失响应检测"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, max_stuck_time=120)

        # 创建一个有候选人但没有响应的 Channel
        old_time = datetime.utcnow() - timedelta(seconds=70)  # > max_stuck_time / 2
        state = create_test_channel_state(
            "ch-004",
            ChannelStatus.COLLECTING,
            created_at=old_time,
            candidates=[{"agent_id": f"agent{i}"} for i in range(5)],
            responses={"agent1": {"decision": "participate"}}  # 只有 1/5 响应
        )
        mock_admin.channels["ch-004"] = state

        # 初始化恢复状态，并设置 last_status 以避免状态变更重置
        recovery_state = checker._get_or_create_recovery_state("ch-004")
        recovery_state.last_status = "collecting"  # 设置为当前状态
        recovery_state.last_status_change_time = old_time

        result = await checker.check_channel("ch-004")

        assert result.healthy is False
        assert result.reason == CheckResult.MISSING_RESPONSES
        assert "1/5" in result.details

    @pytest.mark.asyncio
    async def test_channel_not_found(self):
        """测试 Channel 不存在的情况"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        result = await checker.check_channel("non-existent")

        assert result.healthy is True
        assert "not found" in result.details.lower()


class TestRecoveryOperations:
    """恢复操作测试"""

    @pytest.mark.asyncio
    async def test_recover_stuck_collecting_with_responses(self):
        """测试恢复卡在 COLLECTING（有响应时执行聚合）"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        state = create_test_channel_state(
            "ch-005",
            ChannelStatus.COLLECTING,
            responses={"agent1": {"decision": "participate"}}
        )
        mock_admin.channels["ch-005"] = state

        result = StateCheckResult(
            healthy=False,
            reason=CheckResult.STUCK_IN_COLLECTING,
            channel_id="ch-005"
        )

        await checker._recover_stuck_collecting("ch-005", result)

        assert "ch-005" in mock_admin._aggregate_proposals_called

    @pytest.mark.asyncio
    async def test_recover_stuck_collecting_no_responses(self):
        """测试恢复卡在 COLLECTING（无响应时重新广播）"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        state = create_test_channel_state(
            "ch-006",
            ChannelStatus.COLLECTING,
            responses={}  # 无响应
        )
        mock_admin.channels["ch-006"] = state

        result = StateCheckResult(
            healthy=False,
            reason=CheckResult.STUCK_IN_COLLECTING,
            channel_id="ch-006"
        )

        await checker._recover_stuck_collecting("ch-006", result)

        assert "ch-006" in mock_admin._broadcast_demand_called

    @pytest.mark.asyncio
    async def test_recover_stuck_negotiating(self):
        """测试恢复卡在 NEGOTIATING（强制评估反馈）"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        state = create_test_channel_state(
            "ch-007",
            ChannelStatus.NEGOTIATING,
            proposal_feedback={"agent1": {"feedback_type": "accept"}}
        )
        mock_admin.channels["ch-007"] = state

        result = StateCheckResult(
            healthy=False,
            reason=CheckResult.STUCK_IN_NEGOTIATING,
            channel_id="ch-007"
        )

        await checker._recover_stuck_negotiating("ch-007", result)

        assert "ch-007" in mock_admin._evaluate_feedback_called


class TestMaxRecoveryAttempts:
    """AC-4: 最大恢复尝试次数测试"""

    @pytest.mark.asyncio
    async def test_max_recovery_attempts_exceeded(self):
        """测试超过最大恢复尝试次数后标记失败"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, max_recovery_attempts=3)

        state = create_test_channel_state("ch-008", ChannelStatus.COLLECTING)
        mock_admin.channels["ch-008"] = state

        # 模拟已经尝试了 3 次
        recovery_state = checker._get_or_create_recovery_state("ch-008")
        recovery_state.recovery_attempts = 3

        result = StateCheckResult(
            healthy=False,
            reason=CheckResult.STUCK_IN_COLLECTING,
            channel_id="ch-008"
        )

        await checker._handle_unhealthy_channel("ch-008", result)

        # 应该标记为失败而不是继续恢复
        assert len(mock_admin._fail_channel_called) == 1
        assert mock_admin._fail_channel_called[0][0] == "ch-008"
        assert "recovery_exhausted" in mock_admin._fail_channel_called[0][1]

    @pytest.mark.asyncio
    async def test_recovery_attempts_increment(self):
        """测试恢复尝试计数递增"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, max_recovery_attempts=5)

        state = create_test_channel_state(
            "ch-009",
            ChannelStatus.COLLECTING,
            responses={"agent1": {"decision": "participate"}}
        )
        mock_admin.channels["ch-009"] = state

        result = StateCheckResult(
            healthy=False,
            reason=CheckResult.STUCK_IN_COLLECTING,
            channel_id="ch-009"
        )

        # 第一次恢复
        await checker._handle_unhealthy_channel("ch-009", result)
        recovery_state = checker._recovery_states["ch-009"]
        assert recovery_state.recovery_attempts == 1

        # 第二次恢复
        await checker._handle_unhealthy_channel("ch-009", result)
        assert recovery_state.recovery_attempts == 2


class TestIdempotency:
    """AC-5: 幂等性测试"""

    @pytest.mark.asyncio
    async def test_status_change_resets_recovery_count(self):
        """测试状态变化重置恢复计数"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        # 创建 Channel
        state = create_test_channel_state("ch-010", ChannelStatus.COLLECTING)
        mock_admin.channels["ch-010"] = state

        # 设置恢复状态
        recovery_state = checker._get_or_create_recovery_state("ch-010")
        recovery_state.recovery_attempts = 2
        recovery_state.last_status = "collecting"

        # 检查一次（状态没变）
        await checker.check_channel("ch-010")
        assert recovery_state.recovery_attempts == 2  # 不变

        # 改变状态
        state.status = ChannelStatus.NEGOTIATING

        # 再次检查（状态变了）
        await checker.check_channel("ch-010")
        assert recovery_state.recovery_attempts == 0  # 重置
        assert recovery_state.last_status == "negotiating"

    @pytest.mark.asyncio
    async def test_recovery_history_recorded(self):
        """AC-6: 测试恢复历史记录"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        state = create_test_channel_state(
            "ch-011",
            ChannelStatus.COLLECTING,
            responses={"agent1": {"decision": "participate"}}
        )
        mock_admin.channels["ch-011"] = state

        result = StateCheckResult(
            healthy=False,
            reason=CheckResult.STUCK_IN_COLLECTING,
            suggested_action="aggregate_responses_or_rebroadcast",
            channel_id="ch-011"
        )

        await checker._handle_unhealthy_channel("ch-011", result)

        recovery_state = checker._recovery_states["ch-011"]
        assert len(recovery_state.recovery_history) == 1

        history_entry = recovery_state.recovery_history[0]
        assert history_entry.channel_id == "ch-011"
        assert history_entry.attempt_number == 1
        assert history_entry.reason == CheckResult.STUCK_IN_COLLECTING
        assert history_entry.success is True


class TestRecoveryStateManagement:
    """恢复状态管理测试"""

    def test_clear_recovery_state(self):
        """测试清理恢复状态"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        # 创建恢复状态
        checker._get_or_create_recovery_state("ch-012")
        assert "ch-012" in checker._recovery_states

        # 清理
        checker.clear_recovery_state("ch-012")
        assert "ch-012" not in checker._recovery_states

    def test_get_recovery_state_info(self):
        """测试获取恢复状态信息"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        # 创建恢复状态
        recovery_state = checker._get_or_create_recovery_state("ch-013")
        recovery_state.recovery_attempts = 2
        recovery_state.last_status = "collecting"

        # 获取信息
        info = checker.get_recovery_state("ch-013")
        assert info["channel_id"] == "ch-013"
        assert info["recovery_attempts"] == 2
        assert info["last_status"] == "collecting"

    def test_get_all_recovery_states(self):
        """测试获取所有恢复状态"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        checker._get_or_create_recovery_state("ch-014")
        checker._get_or_create_recovery_state("ch-015")

        all_states = checker.get_all_recovery_states()
        assert "ch-014" in all_states
        assert "ch-015" in all_states


class TestCheckLoop:
    """检查循环测试"""

    @pytest.mark.asyncio
    async def test_check_loop_processes_active_channels(self):
        """AC-1: 测试检查循环处理活跃 Channel"""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, check_interval=0.1, max_stuck_time=0.05)

        # 创建一个卡住的 Channel
        old_time = datetime.utcnow() - timedelta(seconds=1)
        state = create_test_channel_state(
            "ch-016",
            ChannelStatus.COLLECTING,
            created_at=old_time,
            responses={"agent1": {"decision": "participate"}}
        )
        mock_admin.channels["ch-016"] = state

        # 启动检查器
        await checker.start()

        # 等待检查循环运行
        await asyncio.sleep(0.3)

        await checker.stop()

        # 应该触发了恢复操作
        assert "ch-016" in mock_admin._aggregate_proposals_called
