"""
StateChecker - 状态检查与恢复机制

T07: 实现 StateChecker，定期检查 Channel 状态，发现异常时触发恢复流程。
采用状态检查机制替代简单超时。

核心职责：
1. 定期检查活跃 Channel 的状态
2. 发现异常状态（卡住、超时、缺失响应）
3. 触发恢复流程（重新广播、强制聚合、强制评估、终结）
4. 记录恢复尝试和结果
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from openagents.agents.channel_admin import ChannelAdminAgent, ChannelState

logger = logging.getLogger(__name__)


class CheckResult(Enum):
    """状态检查结果枚举"""
    HEALTHY = "healthy"
    STUCK_IN_COLLECTING = "stuck_in_collecting"
    STUCK_IN_NEGOTIATING = "stuck_in_negotiating"
    STUCK_IN_BROADCASTING = "stuck_in_broadcasting"
    STUCK_IN_AGGREGATING = "stuck_in_aggregating"
    STUCK_IN_PROPOSAL_SENT = "stuck_in_proposal_sent"
    MISSING_RESPONSES = "missing_responses"
    TIMEOUT = "timeout"
    NO_PROGRESS = "no_progress"


@dataclass
class StateCheckResult:
    """状态检查结果数据类"""
    healthy: bool
    reason: Optional[CheckResult] = None
    details: Optional[str] = None
    suggested_action: Optional[str] = None
    channel_id: Optional[str] = None
    status: Optional[str] = None
    stuck_duration_seconds: Optional[float] = None


@dataclass
class RecoveryAttempt:
    """恢复尝试记录"""
    channel_id: str
    attempt_number: int
    reason: CheckResult
    action: str
    timestamp: str
    success: bool = False
    error: Optional[str] = None


@dataclass
class ChannelRecoveryState:
    """Channel 恢复状态跟踪"""
    channel_id: str
    recovery_attempts: int = 0
    last_check_time: Optional[datetime] = None
    last_status: Optional[str] = None
    last_status_change_time: Optional[datetime] = None
    recovery_history: List[RecoveryAttempt] = field(default_factory=list)


class StateChecker:
    """
    状态检查器 - 定期检查 Channel 状态并触发恢复

    使用状态检查机制替代简单超时：
    - 定期检查所有活跃 Channel
    - 检测卡住状态（长时间停留在某个状态）
    - 检测缺失响应（应该有响应但没有）
    - 触发恢复操作（幂等性保证）
    - 记录恢复历史（可追溯）
    """

    # 默认配置
    DEFAULT_CHECK_INTERVAL = 5       # 检查间隔（秒）
    DEFAULT_MAX_STUCK_TIME = 120     # 卡住超时（秒）
    DEFAULT_MAX_RECOVERY_ATTEMPTS = 3  # 最大恢复尝试次数

    def __init__(
        self,
        channel_admin: "ChannelAdminAgent",
        check_interval: Optional[int] = None,
        max_stuck_time: Optional[int] = None,
        max_recovery_attempts: Optional[int] = None
    ):
        """
        初始化状态检查器

        Args:
            channel_admin: ChannelAdmin 实例，用于执行恢复操作
            check_interval: 检查间隔（秒），默认 5 秒
            max_stuck_time: 卡住超时（秒），默认 120 秒
            max_recovery_attempts: 最大恢复尝试次数，默认 3 次
        """
        self.channel_admin = channel_admin
        self._running = False
        self._check_task: Optional[asyncio.Task] = None

        # 从配置加载或使用默认值
        self.check_interval = check_interval or self._load_config_int(
            "STATE_CHECK_INTERVAL", self.DEFAULT_CHECK_INTERVAL
        )
        self.max_stuck_time = max_stuck_time or self._load_config_int(
            "STATE_MAX_STUCK_TIME", self.DEFAULT_MAX_STUCK_TIME
        )
        self.max_recovery_attempts = max_recovery_attempts or self._load_config_int(
            "STATE_MAX_RECOVERY_ATTEMPTS", self.DEFAULT_MAX_RECOVERY_ATTEMPTS
        )

        # Channel 恢复状态跟踪
        self._recovery_states: Dict[str, ChannelRecoveryState] = {}

        # 恢复操作回调（可扩展）
        self._recovery_handlers: Dict[CheckResult, Callable] = {
            CheckResult.STUCK_IN_COLLECTING: self._recover_stuck_collecting,
            CheckResult.STUCK_IN_NEGOTIATING: self._recover_stuck_negotiating,
            CheckResult.STUCK_IN_BROADCASTING: self._recover_stuck_broadcasting,
            CheckResult.STUCK_IN_AGGREGATING: self._recover_stuck_aggregating,
            CheckResult.STUCK_IN_PROPOSAL_SENT: self._recover_stuck_proposal_sent,
            CheckResult.MISSING_RESPONSES: self._recover_missing_responses,
            CheckResult.TIMEOUT: self._recover_timeout,
            CheckResult.NO_PROGRESS: self._recover_no_progress,
        }

        logger.info(
            f"StateChecker initialized: check_interval={self.check_interval}s, "
            f"max_stuck_time={self.max_stuck_time}s, "
            f"max_recovery_attempts={self.max_recovery_attempts}"
        )

    def _load_config_int(self, key: str, default: int) -> int:
        """从配置加载整数值"""
        try:
            from config import _get_env_int
            return _get_env_int(f"TOWOW_{key}", default)
        except ImportError:
            return default

    async def start(self) -> None:
        """启动状态检查器"""
        if self._running:
            logger.warning("StateChecker is already running")
            return

        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info(
            f"StateChecker started, checking every {self.check_interval} seconds"
        )

    async def stop(self) -> None:
        """停止状态检查器"""
        if not self._running:
            logger.warning("StateChecker is not running")
            return

        self._running = False
        if self._check_task and not self._check_task.done():
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

        logger.info("StateChecker stopped")

    async def _check_loop(self) -> None:
        """检查循环 - 定期检查所有活跃 Channel"""
        while self._running:
            try:
                await self._check_all_channels()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"StateChecker check loop error: {e}", exc_info=True)

            # 等待下一次检查
            await asyncio.sleep(self.check_interval)

    async def _check_all_channels(self) -> None:
        """检查所有活跃 Channel"""
        active_channel_ids = self.channel_admin.get_active_channels()

        if not active_channel_ids:
            return

        logger.debug(f"StateChecker checking {len(active_channel_ids)} active channels")

        for channel_id in active_channel_ids:
            try:
                result = await self.check_channel(channel_id)
                if not result.healthy:
                    await self._handle_unhealthy_channel(channel_id, result)
            except Exception as e:
                logger.error(
                    f"StateChecker error checking channel {channel_id}: {e}",
                    exc_info=True
                )

    async def check_channel(self, channel_id: str) -> StateCheckResult:
        """
        检查单个 Channel 的状态

        Args:
            channel_id: Channel ID

        Returns:
            StateCheckResult: 检查结果
        """
        if channel_id not in self.channel_admin.channels:
            return StateCheckResult(
                healthy=True,
                details="Channel not found (may have completed)",
                channel_id=channel_id
            )

        state = self.channel_admin.channels[channel_id]
        now = datetime.utcnow()

        # 获取或创建恢复状态跟踪
        recovery_state = self._get_or_create_recovery_state(channel_id)

        # 检测状态变化
        current_status = state.status.value
        if recovery_state.last_status != current_status:
            recovery_state.last_status = current_status
            recovery_state.last_status_change_time = now
            recovery_state.recovery_attempts = 0  # 状态变化重置恢复计数

        recovery_state.last_check_time = now

        # 计算状态停留时间
        status_change_time = recovery_state.last_status_change_time or datetime.fromisoformat(state.created_at)
        stuck_duration = (now - status_change_time).total_seconds()

        # 检查是否卡住
        from openagents.agents.channel_admin import ChannelStatus

        # 活跃状态的超时检查
        stuck_statuses = {
            ChannelStatus.BROADCASTING: CheckResult.STUCK_IN_BROADCASTING,
            ChannelStatus.COLLECTING: CheckResult.STUCK_IN_COLLECTING,
            ChannelStatus.AGGREGATING: CheckResult.STUCK_IN_AGGREGATING,
            ChannelStatus.PROPOSAL_SENT: CheckResult.STUCK_IN_PROPOSAL_SENT,
            ChannelStatus.NEGOTIATING: CheckResult.STUCK_IN_NEGOTIATING,
        }

        if state.status in stuck_statuses and stuck_duration > self.max_stuck_time:
            return StateCheckResult(
                healthy=False,
                reason=stuck_statuses[state.status],
                details=f"Channel stuck in {current_status} for {stuck_duration:.1f}s",
                suggested_action=self._get_suggested_action(stuck_statuses[state.status]),
                channel_id=channel_id,
                status=current_status,
                stuck_duration_seconds=stuck_duration
            )

        # 检查是否有响应缺失（COLLECTING 状态下）
        if state.status == ChannelStatus.COLLECTING:
            expected_responses = len(state.candidates)
            actual_responses = len(state.responses)
            if actual_responses < expected_responses and stuck_duration > self.max_stuck_time / 2:
                return StateCheckResult(
                    healthy=False,
                    reason=CheckResult.MISSING_RESPONSES,
                    details=f"Only {actual_responses}/{expected_responses} responses after {stuck_duration:.1f}s",
                    suggested_action="aggregate_with_partial_responses",
                    channel_id=channel_id,
                    status=current_status,
                    stuck_duration_seconds=stuck_duration
                )

        # 健康状态
        return StateCheckResult(
            healthy=True,
            channel_id=channel_id,
            status=current_status,
            stuck_duration_seconds=stuck_duration
        )

    def _get_suggested_action(self, reason: CheckResult) -> str:
        """根据检查结果获取建议的恢复操作"""
        actions = {
            CheckResult.STUCK_IN_BROADCASTING: "retry_broadcast",
            CheckResult.STUCK_IN_COLLECTING: "aggregate_responses_or_rebroadcast",
            CheckResult.STUCK_IN_AGGREGATING: "force_complete_aggregation",
            CheckResult.STUCK_IN_PROPOSAL_SENT: "resend_proposal",
            CheckResult.STUCK_IN_NEGOTIATING: "force_evaluate_feedback",
            CheckResult.MISSING_RESPONSES: "aggregate_partial_responses",
            CheckResult.TIMEOUT: "force_finalize_or_fail",
            CheckResult.NO_PROGRESS: "force_finalize_or_fail",
        }
        return actions.get(reason, "unknown")

    def _get_or_create_recovery_state(self, channel_id: str) -> ChannelRecoveryState:
        """获取或创建 Channel 的恢复状态跟踪"""
        if channel_id not in self._recovery_states:
            self._recovery_states[channel_id] = ChannelRecoveryState(
                channel_id=channel_id,
                last_status_change_time=datetime.utcnow()
            )
        return self._recovery_states[channel_id]

    async def _handle_unhealthy_channel(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """处理不健康的 Channel"""
        recovery_state = self._get_or_create_recovery_state(channel_id)

        # 检查是否超过最大恢复次数
        if recovery_state.recovery_attempts >= self.max_recovery_attempts:
            logger.warning(
                f"Channel {channel_id} exceeded max recovery attempts "
                f"({self.max_recovery_attempts}), marking as failed"
            )
            await self._mark_channel_failed(channel_id, result)
            return

        # 增加恢复尝试计数
        recovery_state.recovery_attempts += 1

        logger.info(
            f"StateChecker: Channel {channel_id} unhealthy ({result.reason.value}), "
            f"attempt {recovery_state.recovery_attempts}/{self.max_recovery_attempts}"
        )

        # 执行恢复操作
        await self._execute_recovery(channel_id, result, recovery_state)

    async def _execute_recovery(
        self,
        channel_id: str,
        result: StateCheckResult,
        recovery_state: ChannelRecoveryState
    ) -> None:
        """执行恢复操作"""
        if not result.reason:
            return

        handler = self._recovery_handlers.get(result.reason)
        if not handler:
            logger.warning(f"No recovery handler for {result.reason.value}")
            return

        attempt = RecoveryAttempt(
            channel_id=channel_id,
            attempt_number=recovery_state.recovery_attempts,
            reason=result.reason,
            action=result.suggested_action or "unknown",
            timestamp=datetime.utcnow().isoformat()
        )

        try:
            await handler(channel_id, result)
            attempt.success = True
            logger.info(
                f"StateChecker: Recovery for {channel_id} succeeded "
                f"({result.reason.value} -> {result.suggested_action})"
            )
        except Exception as e:
            attempt.success = False
            attempt.error = str(e)
            logger.error(
                f"StateChecker: Recovery for {channel_id} failed: {e}",
                exc_info=True
            )

        recovery_state.recovery_history.append(attempt)

    # ========== 恢复操作实现 ==========

    async def _recover_stuck_collecting(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """
        恢复卡在 COLLECTING 状态的 Channel

        策略：
        - 如果有响应，执行聚合
        - 如果无响应，重新广播
        """
        state = self.channel_admin.channels.get(channel_id)
        if not state:
            return

        if len(state.responses) > 0:
            # 有响应，执行聚合
            logger.info(
                f"StateChecker: Aggregating {len(state.responses)} responses "
                f"for stuck channel {channel_id}"
            )
            await self.channel_admin._aggregate_proposals(state)
        else:
            # 无响应，重新广播
            logger.info(
                f"StateChecker: Re-broadcasting demand for channel {channel_id} "
                f"(no responses)"
            )
            await self.channel_admin._broadcast_demand(state)

    async def _recover_stuck_negotiating(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """
        恢复卡在 NEGOTIATING 状态的 Channel

        策略：强制评估已有反馈
        """
        state = self.channel_admin.channels.get(channel_id)
        if not state:
            return

        logger.info(
            f"StateChecker: Force evaluating feedback for stuck channel {channel_id} "
            f"({len(state.proposal_feedback)} feedbacks)"
        )
        await self.channel_admin._evaluate_feedback(state)

    async def _recover_stuck_broadcasting(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """
        恢复卡在 BROADCASTING 状态的 Channel

        策略：重新广播需求
        """
        state = self.channel_admin.channels.get(channel_id)
        if not state:
            return

        logger.info(
            f"StateChecker: Re-broadcasting for stuck channel {channel_id}"
        )
        await self.channel_admin._broadcast_demand(state)

    async def _recover_stuck_aggregating(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """
        恢复卡在 AGGREGATING 状态的 Channel

        策略：强制完成聚合，使用降级方案
        """
        state = self.channel_admin.channels.get(channel_id)
        if not state:
            return

        logger.info(
            f"StateChecker: Force completing aggregation for channel {channel_id}"
        )

        # 使用降级方案
        from openagents.agents.channel_admin import ChannelStatus

        # 分类响应
        offers = []
        negotiations = []
        for aid, resp in state.responses.items():
            response_type = resp.get("response_type", "offer")
            decision = resp.get("decision")

            if decision == "decline":
                continue

            participant = {
                "agent_id": aid,
                "display_name": aid,
                "decision": decision,
                "contribution": resp.get("contribution"),
                "conditions": resp.get("conditions", []),
                "negotiation_points": resp.get("negotiation_points", [])
            }

            if response_type == "negotiate":
                negotiations.append(participant)
            else:
                offers.append(participant)

        # 生成降级方案
        state.current_proposal = self.channel_admin._get_fallback_proposal_v4(
            state, offers, negotiations
        )
        state.current_proposal["recovery_generated"] = True

        # 分发方案
        await self.channel_admin._distribute_proposal(state)

    async def _recover_stuck_proposal_sent(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """
        恢复卡在 PROPOSAL_SENT 状态的 Channel

        策略：重新分发方案（状态转换到 NEGOTIATING）
        """
        state = self.channel_admin.channels.get(channel_id)
        if not state:
            return

        logger.info(
            f"StateChecker: Re-distributing proposal for channel {channel_id}"
        )

        # 重置分发标记，允许重新分发
        state.proposal_distributed = False
        await self.channel_admin._distribute_proposal(state)

    async def _recover_missing_responses(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """
        恢复缺失响应的 Channel

        策略：处理部分响应，执行聚合
        """
        state = self.channel_admin.channels.get(channel_id)
        if not state:
            return

        logger.info(
            f"StateChecker: Aggregating partial responses for channel {channel_id} "
            f"({len(state.responses)}/{len(state.candidates)})"
        )
        await self.channel_admin._aggregate_proposals(state)

    async def _recover_timeout(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """
        恢复超时的 Channel

        策略：强制终结或标记失败
        """
        await self._force_finalize_or_fail(channel_id, result)

    async def _recover_no_progress(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """
        恢复无进展的 Channel

        策略：强制终结或标记失败
        """
        await self._force_finalize_or_fail(channel_id, result)

    async def _force_finalize_or_fail(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """强制终结或标记失败"""
        state = self.channel_admin.channels.get(channel_id)
        if not state:
            return

        # 检查是否有任何参与者
        participants = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]

        if participants:
            # 有参与者，强制终结
            logger.info(
                f"StateChecker: Force finalizing channel {channel_id} "
                f"({len(participants)} participants)"
            )
            await self.channel_admin._force_finalize_channel(state)
        else:
            # 无参与者，标记失败
            logger.info(
                f"StateChecker: Marking channel {channel_id} as failed (no participants)"
            )
            await self.channel_admin._fail_channel(state, "timeout_no_participants")

    async def _mark_channel_failed(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """标记 Channel 为失败（超过最大恢复次数）"""
        state = self.channel_admin.channels.get(channel_id)
        if not state:
            return

        logger.warning(
            f"StateChecker: Marking channel {channel_id} as failed "
            f"(exceeded max recovery attempts)"
        )
        await self.channel_admin._fail_channel(
            state,
            f"recovery_exhausted_{result.reason.value if result.reason else 'unknown'}"
        )

    # ========== 状态查询方法 ==========

    def get_recovery_state(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """获取 Channel 的恢复状态"""
        if channel_id not in self._recovery_states:
            return None

        rs = self._recovery_states[channel_id]
        return {
            "channel_id": rs.channel_id,
            "recovery_attempts": rs.recovery_attempts,
            "last_check_time": rs.last_check_time.isoformat() if rs.last_check_time else None,
            "last_status": rs.last_status,
            "last_status_change_time": (
                rs.last_status_change_time.isoformat()
                if rs.last_status_change_time else None
            ),
            "recovery_history": [
                {
                    "attempt_number": h.attempt_number,
                    "reason": h.reason.value,
                    "action": h.action,
                    "timestamp": h.timestamp,
                    "success": h.success,
                    "error": h.error
                }
                for h in rs.recovery_history
            ]
        }

    def get_all_recovery_states(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Channel 的恢复状态"""
        return {
            cid: self.get_recovery_state(cid)
            for cid in self._recovery_states
            if self.get_recovery_state(cid) is not None
        }

    def clear_recovery_state(self, channel_id: str) -> None:
        """清除 Channel 的恢复状态（Channel 完成后调用）"""
        if channel_id in self._recovery_states:
            del self._recovery_states[channel_id]
            logger.debug(f"StateChecker: Cleared recovery state for {channel_id}")

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running


# ========== 模块级便捷函数 ==========

_state_checker: Optional[StateChecker] = None


def init_state_checker(
    channel_admin: "ChannelAdminAgent",
    **kwargs
) -> StateChecker:
    """初始化状态检查器"""
    global _state_checker
    _state_checker = StateChecker(channel_admin, **kwargs)
    return _state_checker


def get_state_checker() -> Optional[StateChecker]:
    """获取状态检查器实例"""
    return _state_checker


async def start_state_checker() -> None:
    """启动状态检查器"""
    if _state_checker:
        await _state_checker.start()


async def stop_state_checker() -> None:
    """停止状态检查器"""
    if _state_checker:
        await _state_checker.stop()
