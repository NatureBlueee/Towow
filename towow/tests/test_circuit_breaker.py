"""
熔断器测试 - TASK-T08

测试 LLMService 的熔断器机制，确保在 LLM 服务不可用时系统能够正确降级。

验收标准:
- AC-1: 连续 3 次 LLM 调用失败后，熔断器进入 OPEN 状态
- AC-2: 熔断状态下，直接返回降级响应，不发起 LLM 调用
- AC-3: 熔断 30 秒后，进入 HALF_OPEN 状态
- AC-4: HALF_OPEN 状态下成功一次，熔断器关闭
- AC-5: HALF_OPEN 状态下失败，重新进入 OPEN 状态
- AC-6: 所有 FALLBACK_RESPONSES 格式符合下游期望
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.llm import (
    CircuitBreaker,
    CircuitState,
    FALLBACK_RESPONSES,
    LLMService,
    LLMServiceWithFallback,
)


# ============================================================================
# CircuitBreaker 单元测试
# ============================================================================

class TestCircuitBreaker:
    """熔断器状态机测试"""

    def test_initial_state_is_closed(self):
        """测试熔断器初始状态为 CLOSED"""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_can_execute_when_closed(self):
        """测试 CLOSED 状态允许执行"""
        cb = CircuitBreaker()
        assert cb.can_execute() is True

    def test_record_success_resets_failure_count(self):
        """测试成功调用重置失败计数"""
        cb = CircuitBreaker()
        cb.failure_count = 2
        cb.record_success()
        assert cb.failure_count == 0

    def test_record_failure_increments_count(self):
        """测试失败调用增加计数"""
        cb = CircuitBreaker()
        cb.record_failure()
        assert cb.failure_count == 1
        cb.record_failure()
        assert cb.failure_count == 2

    def test_circuit_opens_after_threshold_failures(self):
        """AC-1: 连续 3 次失败后熔断器打开"""
        cb = CircuitBreaker(failure_threshold=3)

        # 模拟 3 次连续失败
        for i in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    def test_circuit_open_blocks_execution(self):
        """AC-2: 熔断状态下不允许执行"""
        cb = CircuitBreaker(failure_threshold=3)
        cb.state = CircuitState.OPEN
        cb.last_failure_time = time.time()

        assert cb.can_execute() is False

    def test_circuit_half_open_after_recovery_timeout(self):
        """AC-3: 恢复超时后进入 HALF_OPEN 状态"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
        cb.state = CircuitState.OPEN
        # 模拟 31 秒前的失败时间
        cb.last_failure_time = time.time() - 31

        # 调用 can_execute 应该触发状态转换
        result = cb.can_execute()

        assert result is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_closes_on_success_in_half_open(self):
        """AC-4: HALF_OPEN 状态下成功后关闭熔断器"""
        cb = CircuitBreaker()
        cb.state = CircuitState.HALF_OPEN

        cb.record_success()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_reopens_on_failure_in_half_open(self):
        """AC-5: HALF_OPEN 状态下失败后重新打开"""
        cb = CircuitBreaker()
        cb.state = CircuitState.HALF_OPEN

        cb.record_failure()

        assert cb.state == CircuitState.OPEN

    def test_half_open_limits_requests(self):
        """测试 HALF_OPEN 状态限制请求数"""
        cb = CircuitBreaker(half_open_max_calls=1)
        cb.state = CircuitState.HALF_OPEN
        cb.half_open_calls = 0

        # 第一次允许
        assert cb.can_execute() is True
        cb.half_open_calls = 1

        # 第二次拒绝
        assert cb.can_execute() is False

    def test_get_status_returns_correct_info(self):
        """测试获取状态返回正确信息"""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        cb.state = CircuitState.OPEN
        cb.failure_count = 5
        cb.last_failure_time = 12345.0

        status = cb.get_status()

        assert status["state"] == "open"
        assert status["failure_count"] == 5
        assert status["failure_threshold"] == 5
        assert status["recovery_timeout"] == 60.0
        assert status["last_failure_time"] == 12345.0


# ============================================================================
# LLMServiceWithFallback 集成测试
# ============================================================================

class TestLLMServiceWithFallback:
    """带降级能力的 LLM 服务测试"""

    @pytest.fixture
    def mock_llm_service(self):
        """创建 mock LLM 服务"""
        service = MagicMock(spec=LLMService)
        service.client = MagicMock()
        service.model = "test-model"
        return service

    @pytest.fixture
    def llm_with_fallback(self, mock_llm_service):
        """创建带降级能力的 LLM 服务"""
        return LLMServiceWithFallback(
            llm_service=mock_llm_service,
            timeout=5.0,
            circuit_breaker=CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=30.0
            )
        )

    @pytest.mark.asyncio
    async def test_successful_call_returns_result(self, llm_with_fallback, mock_llm_service):
        """测试成功调用返回正常结果"""
        mock_llm_service.complete = AsyncMock(return_value='{"result": "success"}')

        result = await llm_with_fallback.complete(
            prompt="test prompt",
            fallback_key="default"
        )

        assert result == '{"result": "success"}'
        assert llm_with_fallback.stats["success_count"] == 1
        assert llm_with_fallback.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_consecutive_failures(self, llm_with_fallback, mock_llm_service):
        """AC-1: 连续失败后熔断器打开"""
        mock_llm_service.complete = AsyncMock(side_effect=Exception("API Error"))

        # 连续 3 次调用失败
        for _ in range(3):
            await llm_with_fallback.complete(
                prompt="test prompt",
                fallback_key="default"
            )

        assert llm_with_fallback.circuit_breaker.state == CircuitState.OPEN
        assert llm_with_fallback.stats["failure_count"] == 3

    @pytest.mark.asyncio
    async def test_returns_fallback_when_circuit_open(self, llm_with_fallback, mock_llm_service):
        """AC-2: 熔断状态下直接返回降级响应"""
        # 手动设置熔断器为 OPEN 状态
        llm_with_fallback.circuit_breaker.state = CircuitState.OPEN
        llm_with_fallback.circuit_breaker.last_failure_time = time.time()

        result = await llm_with_fallback.complete(
            prompt="test prompt",
            fallback_key="default"
        )

        # 验证返回降级响应
        assert "status" in result or "fallback" in result
        assert llm_with_fallback.stats["circuit_open_count"] == 1
        assert llm_with_fallback.stats["fallback_count"] == 1
        # 验证没有调用实际 LLM
        mock_llm_service.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_half_open_allows_test_request(self, llm_with_fallback, mock_llm_service):
        """AC-3: HALF_OPEN 状态允许试探请求"""
        mock_llm_service.complete = AsyncMock(return_value='{"result": "recovered"}')

        # 设置为 OPEN 状态，但超过恢复时间
        llm_with_fallback.circuit_breaker.state = CircuitState.OPEN
        llm_with_fallback.circuit_breaker.last_failure_time = time.time() - 31

        result = await llm_with_fallback.complete(
            prompt="test prompt",
            fallback_key="default"
        )

        # 应该成功调用
        assert result == '{"result": "recovered"}'
        # 熔断器应该关闭
        assert llm_with_fallback.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_reopens_on_failure(self, llm_with_fallback, mock_llm_service):
        """AC-5: HALF_OPEN 状态失败后重新打开"""
        mock_llm_service.complete = AsyncMock(side_effect=Exception("Still failing"))

        # 设置为 HALF_OPEN 状态
        llm_with_fallback.circuit_breaker.state = CircuitState.HALF_OPEN

        await llm_with_fallback.complete(
            prompt="test prompt",
            fallback_key="default"
        )

        # 熔断器应该重新打开
        assert llm_with_fallback.circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_timeout_triggers_fallback(self, llm_with_fallback, mock_llm_service):
        """测试超时触发降级"""
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)
            return '{"result": "too slow"}'

        mock_llm_service.complete = slow_response
        llm_with_fallback.timeout = 0.1  # 设置很短的超时

        result = await llm_with_fallback.complete(
            prompt="test prompt",
            fallback_key="default"
        )

        # 应该返回降级响应
        assert "status" in result or "message" in result
        assert llm_with_fallback.stats["timeout_count"] == 1

    @pytest.mark.asyncio
    async def test_fallback_when_no_llm_service(self):
        """测试没有 LLM 服务时返回降级响应"""
        service = LLMServiceWithFallback(llm_service=None)

        result = await service.complete(
            prompt="test prompt",
            fallback_key="default"
        )

        assert "status" in result or "message" in result
        assert service.stats["fallback_count"] == 1

    @pytest.mark.asyncio
    async def test_complete_with_tools_fallback(self, llm_with_fallback, mock_llm_service):
        """测试工具调用的降级"""
        # 设置熔断器为 OPEN
        llm_with_fallback.circuit_breaker.state = CircuitState.OPEN
        llm_with_fallback.circuit_breaker.last_failure_time = time.time()

        result = await llm_with_fallback.complete_with_tools(
            prompt="test prompt",
            tools=[],
            fallback_key="default"
        )

        assert "content" in result
        assert "tool_calls" in result
        assert result["tool_calls"] == []

    def test_get_status(self, llm_with_fallback):
        """测试获取服务状态"""
        llm_with_fallback.stats["total_calls"] = 10
        llm_with_fallback.stats["success_count"] = 7

        status = llm_with_fallback.get_status()

        assert status["llm_configured"] is True
        assert status["timeout"] == 5.0
        assert "circuit_breaker" in status
        assert status["stats"]["total_calls"] == 10
        assert status["stats"]["success_count"] == 7

    def test_reset_stats(self, llm_with_fallback):
        """测试重置统计信息"""
        llm_with_fallback.stats["total_calls"] = 100
        llm_with_fallback.stats["failure_count"] = 50

        llm_with_fallback.reset_stats()

        assert llm_with_fallback.stats["total_calls"] == 0
        assert llm_with_fallback.stats["failure_count"] == 0

    def test_reset_circuit_breaker(self, llm_with_fallback):
        """测试重置熔断器"""
        llm_with_fallback.circuit_breaker.state = CircuitState.OPEN
        llm_with_fallback.circuit_breaker.failure_count = 5

        llm_with_fallback.reset_circuit_breaker()

        assert llm_with_fallback.circuit_breaker.state == CircuitState.CLOSED
        assert llm_with_fallback.circuit_breaker.failure_count == 0


# ============================================================================
# 降级响应格式测试
# ============================================================================

class TestFallbackResponses:
    """AC-6: 降级响应格式验证"""

    def test_all_fallback_responses_are_valid_json(self):
        """测试所有降级响应都是有效 JSON"""
        for key, response in FALLBACK_RESPONSES.items():
            try:
                parsed = json.loads(response)
                assert isinstance(parsed, dict), f"{key} should parse to dict"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON for fallback key '{key}': {e}")

    def test_coordinator_analyze_fallback_format(self):
        """测试协调器分析降级响应格式"""
        response = json.loads(FALLBACK_RESPONSES["coordinator_analyze"])

        assert "analysis" in response
        assert "key_requirements" in response
        assert isinstance(response["key_requirements"], list)
        assert "estimated_participants" in response
        assert "complexity" in response

    def test_coordinator_plan_fallback_format(self):
        """测试协调器计划降级响应格式"""
        response = json.loads(FALLBACK_RESPONSES["coordinator_plan"])

        assert "plan" in response
        assert "phases" in response
        assert isinstance(response["phases"], list)
        assert "estimated_rounds" in response

    def test_user_agent_evaluate_fallback_format(self):
        """测试用户代理评估降级响应格式"""
        response = json.loads(FALLBACK_RESPONSES["user_agent_evaluate"])

        assert "evaluation" in response
        assert "score" in response
        assert isinstance(response["score"], (int, float))
        assert "concerns" in response
        assert isinstance(response["concerns"], list)
        assert "suggestions" in response

    def test_user_agent_propose_fallback_format(self):
        """测试用户代理提案降级响应格式"""
        response = json.loads(FALLBACK_RESPONSES["user_agent_propose"])

        assert "proposal" in response
        assert "key_points" in response
        assert isinstance(response["key_points"], list)
        assert "confidence" in response

    def test_user_agent_respond_fallback_format(self):
        """测试用户代理响应降级响应格式"""
        response = json.loads(FALLBACK_RESPONSES["user_agent_respond"])

        assert "response" in response
        assert "agreement_level" in response
        assert response["agreement_level"] in ["agree", "disagree", "partial"]
        assert "conditions" in response

    def test_channel_admin_moderate_fallback_format(self):
        """测试频道管理员主持降级响应格式"""
        response = json.loads(FALLBACK_RESPONSES["channel_admin_moderate"])

        assert "action" in response
        assert response["action"] in ["continue", "pause", "end"]
        assert "summary" in response

    def test_gap_identify_fallback_format(self):
        """测试缺口识别降级响应格式"""
        response = json.loads(FALLBACK_RESPONSES["gap_identify"])

        assert "gaps" in response
        assert isinstance(response["gaps"], list)
        assert "severity" in response
        assert "recommendations" in response

    def test_default_fallback_format(self):
        """测试默认降级响应格式"""
        response = json.loads(FALLBACK_RESPONSES["default"])

        assert "status" in response
        assert response["status"] == "fallback"
        assert "message" in response


# ============================================================================
# 状态流转完整性测试
# ============================================================================

class TestCircuitBreakerStateTransitions:
    """熔断器状态流转完整性测试"""

    @pytest.mark.asyncio
    async def test_full_state_cycle(self):
        """测试完整的状态循环: CLOSED -> OPEN -> HALF_OPEN -> CLOSED"""
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.client = MagicMock()

        service = LLMServiceWithFallback(
            llm_service=mock_llm,
            timeout=5.0,
            circuit_breaker=CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=0.1  # 极短的恢复时间用于测试
            )
        )

        # 阶段 1: CLOSED - 连续失败触发熔断
        mock_llm.complete = AsyncMock(side_effect=Exception("Error"))
        for _ in range(3):
            await service.complete("test", fallback_key="default")

        assert service.circuit_breaker.state == CircuitState.OPEN

        # 阶段 2: OPEN - 请求被拒绝
        initial_call_count = mock_llm.complete.call_count
        await service.complete("test", fallback_key="default")
        assert mock_llm.complete.call_count == initial_call_count  # 没有新调用

        # 阶段 3: 等待恢复时间后进入 HALF_OPEN
        await asyncio.sleep(0.15)

        # 阶段 4: HALF_OPEN 成功 -> CLOSED
        mock_llm.complete = AsyncMock(return_value='{"status": "ok"}')
        result = await service.complete("test", fallback_key="default")

        assert result == '{"status": "ok"}'
        assert service.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        """测试 HALF_OPEN 失败后回到 OPEN"""
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.client = MagicMock()

        service = LLMServiceWithFallback(
            llm_service=mock_llm,
            timeout=5.0,
            circuit_breaker=CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=0.1
            )
        )

        # 进入 OPEN 状态
        mock_llm.complete = AsyncMock(side_effect=Exception("Error"))
        for _ in range(3):
            await service.complete("test", fallback_key="default")

        assert service.circuit_breaker.state == CircuitState.OPEN

        # 等待恢复，应自动进入 HALF_OPEN
        await asyncio.sleep(0.15)

        # 再次失败，应该回到 OPEN
        await service.complete("test", fallback_key="default")

        assert service.circuit_breaker.state == CircuitState.OPEN


# ============================================================================
# 边界条件测试
# ============================================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_circuit_breaker_with_zero_threshold(self):
        """测试失败阈值为 0 的情况（虽然不推荐）"""
        cb = CircuitBreaker(failure_threshold=0)
        # 阈值为 0 时，一次失败就应该触发
        cb.record_failure()
        # 由于 failure_count (1) >= threshold (0)，应该打开
        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_with_large_threshold(self):
        """测试大失败阈值"""
        cb = CircuitBreaker(failure_threshold=100)

        for _ in range(99):
            cb.record_failure()

        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_fallback_key_not_found(self):
        """测试降级 key 不存在时使用默认响应"""
        service = LLMServiceWithFallback(llm_service=None)

        fallback = service._get_fallback("nonexistent_key")

        # 应该返回默认响应
        parsed = json.loads(fallback)
        assert "status" in parsed or "message" in parsed

    @pytest.mark.asyncio
    async def test_concurrent_requests_during_circuit_open(self):
        """测试熔断期间的并发请求"""
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.client = MagicMock()

        service = LLMServiceWithFallback(
            llm_service=mock_llm,
            circuit_breaker=CircuitBreaker(failure_threshold=3)
        )

        # 设置熔断器为 OPEN
        service.circuit_breaker.state = CircuitState.OPEN
        service.circuit_breaker.last_failure_time = time.time()

        # 并发发送多个请求
        tasks = [
            service.complete("test", fallback_key="default")
            for _ in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # 所有请求都应该返回降级响应
        assert len(results) == 10
        for result in results:
            assert "status" in result or "message" in result

        # LLM 服务不应该被调用
        mock_llm.complete.assert_not_called()

        # 统计应该正确
        assert service.stats["circuit_open_count"] == 10
