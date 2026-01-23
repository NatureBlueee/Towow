# TASK-T07-state-checker

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T07-state-checker.md`
>
> * TASK_ID: TASK-T07
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-23

---

## 关联 Story

- **STORY-05**: 多轮协商与状态管理

---

## 任务描述

实现状态检查与恢复机制（StateChecker），定期检查 Channel 状态，发现异常时触发恢复流程。根据 PRD v4 分析结论，**采用状态检查机制替代简单超时**，以应对网络波动和中间状态异常。

### 改造目标

1. 实现 StateChecker 定期检查 Channel 状态（每 5 秒）
2. 发现异常状态时触发恢复流程
3. 所有操作支持幂等（通过 message_id 去重）
4. 最多重试 3 次，超过则标记失败

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/services/state_checker.py` | 新建，实现状态检查逻辑 |
| `towow/openagents/agents/channel_admin.py` | 集成 StateChecker |
| `towow/config.py` | 添加状态检查配置 |

### 关键代码改动

#### 1. StateChecker 实现

```python
# towow/services/state_checker.py

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CheckResult(Enum):
    HEALTHY = "healthy"
    STUCK_IN_COLLECTING = "stuck_in_collecting"
    STUCK_IN_NEGOTIATING = "stuck_in_negotiating"
    MISSING_RESPONSES = "missing_responses"
    TIMEOUT = "timeout"

@dataclass
class StateCheckResult:
    """状态检查结果"""
    healthy: bool
    reason: Optional[CheckResult] = None
    details: Optional[str] = None
    suggested_action: Optional[str] = None

class StateChecker:
    """
    状态检查器

    [v4] 采用状态检查机制替代简单超时：
    1. 定期检查 Channel 状态（每 5 秒）
    2. 发现异常状态时触发恢复
    3. 幂等重试避免重复处理
    """

    CHECK_INTERVAL = 5           # 检查间隔（秒）
    MAX_STUCK_TIME = 120         # 卡住超时（秒）
    MAX_RECOVERY_ATTEMPTS = 3    # 最大恢复尝试次数

    def __init__(self, channel_admin=None):
        self.channel_admin = channel_admin
        self._running = False
        self._check_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动状态检查器"""
        if self._running:
            return

        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info("StateChecker 已启动")

    async def stop(self) -> None:
        """停止状态检查器"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("StateChecker 已停止")

    async def _check_loop(self) -> None:
        """检查循环"""
        while self._running:
            try:
                await self._check_all_channels()
            except Exception as e:
                logger.error(f"状态检查异常: {e}")

            await asyncio.sleep(self.CHECK_INTERVAL)

    async def _check_all_channels(self) -> None:
        """检查所有活跃的 Channel"""
        if not self.channel_admin:
            return

        active_channels = self.channel_admin.get_active_channels()

        for channel_id in active_channels:
            result = await self.check_channel(channel_id)
            if not result.healthy:
                await self._handle_unhealthy(channel_id, result)

    async def check_channel(self, channel_id: str) -> StateCheckResult:
        """
        检查单个 Channel 状态

        检查项：
        1. 是否卡在 COLLECTING 状态过久
        2. 是否卡在 NEGOTIATING 状态过久
        3. 是否有缺失的响应
        4. 是否超时
        """
        state = self.channel_admin._channels.get(channel_id)
        if not state:
            return StateCheckResult(healthy=True)

        now = datetime.utcnow()
        last_update = datetime.fromisoformat(state.last_updated_at)
        stuck_time = (now - last_update).total_seconds()

        # 检查 1: 卡在 COLLECTING
        if state.status == ChannelStatus.COLLECTING:
            if stuck_time > self.MAX_STUCK_TIME:
                return StateCheckResult(
                    healthy=False,
                    reason=CheckResult.STUCK_IN_COLLECTING,
                    details=f"卡在 COLLECTING 状态 {stuck_time:.0f} 秒",
                    suggested_action="继续处理已有响应或超时处理"
                )

        # 检查 2: 卡在 NEGOTIATING
        if state.status == ChannelStatus.NEGOTIATING:
            if stuck_time > self.MAX_STUCK_TIME:
                return StateCheckResult(
                    healthy=False,
                    reason=CheckResult.STUCK_IN_NEGOTIATING,
                    details=f"卡在 NEGOTIATING 状态 {stuck_time:.0f} 秒",
                    suggested_action="强制评估已有反馈"
                )

        # 检查 3: 缺失响应
        if state.status == ChannelStatus.COLLECTING:
            expected = state.expected_responses
            received = set(state.responses.keys())
            missing = expected - received

            if missing and stuck_time > 60:  # 等待 1 分钟后检查
                return StateCheckResult(
                    healthy=False,
                    reason=CheckResult.MISSING_RESPONSES,
                    details=f"缺失 {len(missing)} 个响应: {missing}",
                    suggested_action="继续处理已有响应"
                )

        # 检查 4: 总体超时
        created_at = datetime.fromisoformat(state.created_at)
        total_time = (now - created_at).total_seconds()

        if total_time > 600:  # 10 分钟总超时
            return StateCheckResult(
                healthy=False,
                reason=CheckResult.TIMEOUT,
                details=f"协商总时长 {total_time:.0f} 秒",
                suggested_action="强制终结或标记失败"
            )

        return StateCheckResult(healthy=True)

    async def _handle_unhealthy(
        self,
        channel_id: str,
        result: StateCheckResult
    ) -> None:
        """处理异常状态"""
        state = self.channel_admin._channels.get(channel_id)
        if not state:
            return

        # 检查重试次数
        if state.recovery_attempts >= self.MAX_RECOVERY_ATTEMPTS:
            logger.warning(
                f"Channel {channel_id} 超过最大恢复次数 ({self.MAX_RECOVERY_ATTEMPTS})，标记失败"
            )
            await self.channel_admin._fail_channel(
                channel_id,
                "max_recovery_attempts"
            )
            return

        # 增加重试计数
        state.recovery_attempts += 1
        logger.info(
            f"Channel {channel_id} 开始恢复尝试 {state.recovery_attempts}/{self.MAX_RECOVERY_ATTEMPTS}"
        )

        # 根据异常类型执行恢复
        if result.reason == CheckResult.STUCK_IN_COLLECTING:
            await self._recover_collecting(channel_id, state)
        elif result.reason == CheckResult.STUCK_IN_NEGOTIATING:
            await self._recover_negotiating(channel_id, state)
        elif result.reason == CheckResult.MISSING_RESPONSES:
            await self._recover_missing_responses(channel_id, state)
        elif result.reason == CheckResult.TIMEOUT:
            await self._recover_timeout(channel_id, state)

    async def _recover_collecting(self, channel_id: str, state) -> None:
        """恢复 COLLECTING 状态"""
        # 如果已有响应，继续处理
        if state.responses:
            logger.info(f"Channel {channel_id} 有 {len(state.responses)} 个响应，继续聚合")
            await self.channel_admin._aggregate_offers(channel_id)
        else:
            # 无响应，重新广播（幂等）
            logger.info(f"Channel {channel_id} 无响应，重新广播")
            await self.channel_admin._broadcast_demand(channel_id)

    async def _recover_negotiating(self, channel_id: str, state) -> None:
        """恢复 NEGOTIATING 状态"""
        # 强制评估已有反馈
        logger.info(f"Channel {channel_id} 强制评估反馈")
        await self.channel_admin.evaluate_feedback(channel_id)

    async def _recover_missing_responses(self, channel_id: str, state) -> None:
        """恢复缺失响应"""
        # 继续处理已有响应
        logger.info(f"Channel {channel_id} 处理部分响应")
        await self.channel_admin._aggregate_offers(channel_id)

    async def _recover_timeout(self, channel_id: str, state) -> None:
        """恢复超时"""
        # 根据当前状态决定
        if state.current_round >= state.max_rounds:
            # 已达最大轮次，强制终结
            await self.channel_admin._force_finalize_channel(channel_id)
        else:
            # 标记失败
            await self.channel_admin._fail_channel(channel_id, "timeout")
```

#### 2. 配置项

```python
# towow/config.py

class TimeoutConfig:
    """超时配置"""

    # 状态检查
    STATE_CHECK_INTERVAL = int(os.getenv("STATE_CHECK_INTERVAL", "5"))
    MAX_STUCK_TIME = int(os.getenv("MAX_STUCK_TIME", "120"))
    MAX_RECOVERY_ATTEMPTS = int(os.getenv("MAX_RECOVERY_ATTEMPTS", "3"))
```

#### 3. 集成到 ChannelAdmin

```python
# towow/openagents/agents/channel_admin.py

from services.state_checker import StateChecker

class ChannelAdminAgent:
    def __init__(self, llm=None, db=None):
        self.llm = llm
        self.db = db
        self._channels: Dict[str, ChannelState] = {}
        self.state_checker = StateChecker(channel_admin=self)

    async def start(self) -> None:
        """启动 ChannelAdmin"""
        await self.state_checker.start()

    async def stop(self) -> None:
        """停止 ChannelAdmin"""
        await self.state_checker.stop()

    def get_active_channels(self) -> List[str]:
        """获取活跃的 Channel 列表"""
        return [
            channel_id
            for channel_id, state in self._channels.items()
            if state.status not in [
                ChannelStatus.FINALIZED,
                ChannelStatus.FORCE_FINALIZED,
                ChannelStatus.FAILED
            ]
        ]
```

---

## 接口契约

### StateCheckResult

```python
@dataclass
class StateCheckResult:
    healthy: bool                          # 是否健康
    reason: Optional[CheckResult] = None   # 异常原因
    details: Optional[str] = None          # 详细描述
    suggested_action: Optional[str] = None # 建议操作
```

### 检查结果类型

```python
class CheckResult(Enum):
    HEALTHY = "healthy"
    STUCK_IN_COLLECTING = "stuck_in_collecting"
    STUCK_IN_NEGOTIATING = "stuck_in_negotiating"
    MISSING_RESPONSES = "missing_responses"
    TIMEOUT = "timeout"
```

---

## 依赖

### 硬依赖
- **T01**: demand.py 重构（需要 Agent 初始化）
- **T05**: 多轮协商逻辑（需要状态机基础）

### 接口依赖
- 无

### 被依赖
- **T10**: 端到端测试

---

## 验收标准

- [ ] **AC-1**: StateChecker 每 5 秒检查一次活跃 Channel
- [ ] **AC-2**: 卡在 COLLECTING 超过 120 秒触发恢复
- [ ] **AC-3**: 卡在 NEGOTIATING 超过 120 秒触发恢复
- [ ] **AC-4**: 恢复尝试最多 3 次，超过标记失败
- [ ] **AC-5**: 恢复操作是幂等的（不会重复处理）
- [ ] **AC-6**: 日志记录恢复尝试和结果

### 测试用例

```python
# tests/test_state_checker.py

@pytest.mark.asyncio
async def test_check_healthy_channel():
    """测试健康 Channel 检查"""
    checker = StateChecker(channel_admin=mock_admin)

    result = await checker.check_channel("healthy-channel")

    assert result.healthy is True

@pytest.mark.asyncio
async def test_detect_stuck_collecting():
    """测试检测卡在 COLLECTING 状态"""
    checker = StateChecker(channel_admin=mock_admin)

    # 模拟卡在 COLLECTING 超过 120 秒
    mock_admin._channels["stuck-channel"] = ChannelState(
        channel_id="stuck-channel",
        status=ChannelStatus.COLLECTING,
        last_updated_at=(datetime.utcnow() - timedelta(seconds=150)).isoformat()
    )

    result = await checker.check_channel("stuck-channel")

    assert result.healthy is False
    assert result.reason == CheckResult.STUCK_IN_COLLECTING

@pytest.mark.asyncio
async def test_recovery_attempts_limit():
    """测试恢复尝试次数限制"""
    checker = StateChecker(channel_admin=mock_admin)

    # 模拟已达最大重试次数
    mock_admin._channels["retry-channel"] = ChannelState(
        channel_id="retry-channel",
        status=ChannelStatus.COLLECTING,
        recovery_attempts=3,
        last_updated_at=(datetime.utcnow() - timedelta(seconds=150)).isoformat()
    )

    await checker._handle_unhealthy(
        "retry-channel",
        StateCheckResult(healthy=False, reason=CheckResult.STUCK_IN_COLLECTING)
    )

    # 验证标记为失败
    assert mock_admin._channels["retry-channel"].status == ChannelStatus.FAILED

@pytest.mark.asyncio
async def test_idempotent_recovery():
    """测试恢复操作幂等性"""
    checker = StateChecker(channel_admin=mock_admin)

    # 连续触发两次恢复
    await checker._recover_collecting("test-channel", mock_state)
    await checker._recover_collecting("test-channel", mock_state)

    # 验证只执行一次聚合
    assert mock_admin._aggregate_offers.call_count == 1  # 幂等
```

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| StateChecker 实现 | 2h |
| 恢复逻辑实现 | 1h |
| 集成到 ChannelAdmin | 0.5h |
| 单元测试 | 0.5h |
| **总计** | **4h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 检查过于频繁 | 性能开销 | 可配置检查间隔 |
| 恢复操作失败 | 状态不一致 | 幂等设计 + 日志追踪 |
| 误判健康状态 | 不必要的恢复 | 增加检查时间阈值 |

---

## 实现记录

*(开发完成后填写)*

### 实际修改的文件

### 遇到的问题

### 解决方案

---

## 测试记录

*(测试完成后填写)*

### 测试结果

### 覆盖率
