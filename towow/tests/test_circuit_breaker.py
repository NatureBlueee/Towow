"""
熔断器测试 - TASK-T09 (beads: towow-ql9)

测试 LLMService 的熔断器机制，确保在 LLM 服务不可用时系统能够正确降级。

熔断器配置:
- failure_threshold: 3     连续 3 次失败后触发熔断
- recovery_timeout: 30     熔断后 30 秒进入半开状态
- half_open_requests: 1    半开状态允许 1 次试探请求

熔断器状态机:
CLOSED (正常) -> 连续 3 次失败 -> OPEN (熔断) -> 30 秒后 -> HALF_OPEN (半开)
    -> 成功 -> CLOSED
    -> 失败 -> OPEN

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
    """AC-6: 降级响应格式验证

    验证所有降级响应格式符合下游期望：
    - smart_filter: 包含 candidates 数组（供 Coordinator._parse_filter_response 解析）
    - response_generation: 包含 decision, reasoning（供 UserAgent 响应生成）
    - proposal_aggregation: 包含 summary, assignments, confidence（供 ChannelAdmin 方案聚合）
    - gap_identification: 返回数组格式（供 GapIdentificationService._parse_llm_gaps 解析）
    """

    def test_all_fallback_responses_are_valid_json(self):
        """测试所有降级响应都是有效 JSON"""
        for key, response in FALLBACK_RESPONSES.items():
            try:
                parsed = json.loads(response)
                # gap_identification 返回数组，其他返回对象
                if key == "gap_identification":
                    assert isinstance(parsed, list), f"{key} should parse to list"
                else:
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
        """测试缺口识别降级响应格式（旧版兼容）"""
        response = json.loads(FALLBACK_RESPONSES["gap_identify"])

        assert "gaps" in response
        assert isinstance(response["gaps"], list)
        assert "severity" in response
        assert "recommendations" in response

    def test_gap_identification_fallback_format(self):
        """测试缺口识别降级响应格式（新版 - GapIdentificationService 使用）

        GapIdentificationService._parse_llm_gaps 期望接收 JSON 数组格式，
        降级时返回空数组表示没有发现缺口（安全的降级策略）。
        """
        response = json.loads(FALLBACK_RESPONSES["gap_identification"])

        # gap_identification 返回空数组，表示没有发现缺口
        assert isinstance(response, list)
        # 空数组是安全的降级策略
        assert len(response) == 0

    def test_default_fallback_format(self):
        """测试默认降级响应格式"""
        response = json.loads(FALLBACK_RESPONSES["default"])

        assert "status" in response
        assert response["status"] == "fallback"
        assert "message" in response

    # =========================================================================
    # 关键降级响应格式验证（下游系统依赖）
    # =========================================================================

    def test_smart_filter_format_for_coordinator(self):
        """测试 smart_filter 降级响应格式 - Coordinator._parse_filter_response 期望的格式

        关键字段验证：
        - candidates: 候选人列表（必需，供 _parse_filter_response 解析）
        - analysis: 分析说明（可选）
        - coverage: 覆盖情况（可选）

        每个 candidate 必须包含：
        - agent_id: Agent ID（必需，用于验证）
        - display_name: 显示名称
        - reason: 筛选理由
        - relevance_score: 相关性分数 (0-100)
        - expected_role: 预期角色
        """
        response = json.loads(FALLBACK_RESPONSES["smart_filter"])

        # 必须包含 candidates 字段
        assert "candidates" in response
        assert isinstance(response["candidates"], list)

        # 验证候选人格式
        for candidate in response["candidates"]:
            assert "agent_id" in candidate, "candidate must have agent_id"
            assert "display_name" in candidate, "candidate must have display_name"
            assert "reason" in candidate, "candidate must have reason"
            assert "relevance_score" in candidate, "candidate must have relevance_score"
            assert isinstance(candidate["relevance_score"], (int, float))
            assert 0 <= candidate["relevance_score"] <= 100
            assert "expected_role" in candidate, "candidate must have expected_role"

        # 可选字段
        if "analysis" in response:
            assert isinstance(response["analysis"], str)
        if "coverage" in response:
            assert isinstance(response["coverage"], dict)

    def test_response_generation_format_for_user_agent(self):
        """测试 response_generation 降级响应格式 - UserAgent._parse_response 期望的格式

        关键字段验证（必需）：
        - decision: participate | decline | conditional
        - reasoning: 决策理由

        可选字段：
        - contribution: 贡献说明
        - conditions: 条件列表
        - confidence: 置信度 (0-100)
        - enthusiasm_level: high | medium | low
        - suggested_role: 建议角色
        - decline_reason: 拒绝原因（decline 时）
        """
        response = json.loads(FALLBACK_RESPONSES["response_generation"])

        # 必需字段
        assert "decision" in response
        assert response["decision"] in ["participate", "decline", "conditional"]
        assert "reasoning" in response

        # 可选字段验证
        if "confidence" in response:
            assert isinstance(response["confidence"], (int, float))
            assert 0 <= response["confidence"] <= 100

        if "enthusiasm_level" in response:
            assert response["enthusiasm_level"] in ["high", "medium", "low"]

        if "conditions" in response:
            assert isinstance(response["conditions"], list)

    def test_proposal_aggregation_format_for_channel_admin(self):
        """测试 proposal_aggregation 降级响应格式 - ChannelAdmin._parse_proposal 期望的格式

        关键字段验证（必需）：
        - summary: 方案摘要
        - assignments: 角色分配列表
        - confidence: 方案置信度

        可选字段：
        - objective: 目标
        - timeline: 时间线
        - collaboration_model: 协作模式
        - success_criteria: 成功标准
        - risks: 风险列表
        - gaps: 识别的缺口
        - notes: 备注
        """
        response = json.loads(FALLBACK_RESPONSES["proposal_aggregation"])

        # 必需字段
        assert "summary" in response
        assert isinstance(response["summary"], str)

        assert "assignments" in response
        assert isinstance(response["assignments"], list)

        assert "confidence" in response
        # confidence 可以是字符串（high/medium/low）或数字
        assert response["confidence"] in ["high", "medium", "low"] or isinstance(
            response["confidence"], (int, float)
        )

        # 可选字段验证
        if "timeline" in response:
            assert isinstance(response["timeline"], dict)

        if "success_criteria" in response:
            assert isinstance(response["success_criteria"], list)

        if "risks" in response:
            assert isinstance(response["risks"], list)

        if "gaps" in response:
            assert isinstance(response["gaps"], list)


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


# ============================================================================
# 降级响应与下游代码集成测试
# ============================================================================

class TestFallbackResponseIntegration:
    """验证降级响应可以被下游代码正确解析"""

    def test_smart_filter_fallback_compatible_with_parse_filter_response(self):
        """验证 smart_filter 降级响应可以被 Coordinator._parse_filter_response 解析

        测试场景：熔断触发时，返回的降级响应格式必须能被下游正确解析。
        """
        import re

        fallback = FALLBACK_RESPONSES["smart_filter"]

        # 模拟 _parse_filter_response 的解析逻辑
        json_match = re.search(r'\{[\s\S]*\}', fallback)
        assert json_match is not None

        data = json.loads(json_match.group())
        candidates = data.get("candidates", [])

        # 验证候选人列表格式正确
        assert len(candidates) > 0

        # 验证每个候选人都有必要字段（_parse_filter_response 会检查这些）
        for candidate in candidates:
            assert "agent_id" in candidate
            assert "display_name" in candidate
            # relevance_score 和 reason 在解析时会有默认值补充

    def test_response_generation_fallback_compatible_with_parse_response(self):
        """验证 response_generation 降级响应可以被 UserAgent._parse_response 解析

        测试场景：用户代理生成响应时熔断，返回的降级响应必须符合预期格式。
        """
        import re

        fallback = FALLBACK_RESPONSES["response_generation"]

        # 模拟 _parse_response 的解析逻辑
        json_match = re.search(r'\{[\s\S]*\}', fallback)
        assert json_match is not None

        data = json.loads(json_match.group())

        # 验证必要字段
        decision = data.get("decision", "decline").lower().strip()
        assert decision in ("participate", "decline", "conditional")

        # 验证 reasoning 存在
        assert "reasoning" in data

        # 验证 confidence 格式
        confidence = data.get("confidence", 50)
        if isinstance(confidence, str):
            confidence = int(confidence)
        assert 0 <= confidence <= 100

    def test_proposal_aggregation_fallback_compatible_with_parse_proposal(self):
        """验证 proposal_aggregation 降级响应可以被 ChannelAdmin._parse_proposal 解析

        测试场景：方案聚合时熔断，返回的降级响应必须能够作为有效方案。
        """
        import re

        fallback = FALLBACK_RESPONSES["proposal_aggregation"]

        # 模拟 _parse_proposal 的解析逻辑
        json_match = re.search(r'\{[\s\S]*\}', fallback)
        assert json_match is not None

        data = json.loads(json_match.group())

        # 验证必要字段
        assert "summary" in data
        assert "assignments" in data
        assert isinstance(data["assignments"], list)

        # 验证 timeline 格式（如果存在）
        if "timeline" in data:
            timeline = data["timeline"]
            assert isinstance(timeline, dict)

    def test_gap_identification_fallback_compatible_with_parse_llm_gaps(self):
        """验证 gap_identification 降级响应可以被 GapIdentificationService._parse_llm_gaps 解析

        测试场景：缺口识别时熔断，返回的降级响应必须能被正确解析。
        空数组是安全的降级策略，表示没有发现缺口。
        """
        import re

        fallback = FALLBACK_RESPONSES["gap_identification"]

        # 模拟 _parse_llm_gaps 的解析逻辑
        json_match = re.search(r'\[[\s\S]*\]', fallback)
        assert json_match is not None

        data = json.loads(json_match.group())

        # 验证返回的是数组
        assert isinstance(data, list)

        # 空数组是有效的（表示没有缺口）
        # 如果有缺口，验证格式
        for item in data:
            assert isinstance(item, dict)
            # 每个 gap 应该有 gap_type 和 severity
            if "gap_type" in item:
                assert item["gap_type"] in [
                    "capability", "resource", "participant", "coverage", "condition"
                ]
            if "severity" in item:
                assert item["severity"] in ["critical", "high", "medium", "low"]


# ============================================================================
# 熔断器配置验证测试
# ============================================================================

class TestCircuitBreakerConfiguration:
    """验证熔断器配置符合任务要求"""

    def test_default_configuration_matches_task_requirements(self):
        """验证默认配置符合任务要求

        任务要求：
        - failure_threshold: 3 (连续 3 次失败后触发熔断)
        - recovery_timeout: 30 (熔断后 30 秒进入半开状态)
        - half_open_requests: 1 (半开状态允许 1 次试探请求)
        """
        cb = CircuitBreaker()

        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30.0
        assert cb.half_open_max_calls == 1

    def test_custom_configuration(self):
        """测试自定义配置"""
        cb = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_calls=2
        )

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60.0
        assert cb.half_open_max_calls == 2

    @pytest.mark.asyncio
    async def test_fallback_keys_used_in_actual_code(self):
        """验证代码中实际使用的 fallback_key 都有对应的降级响应

        检查以下 fallback_key 是否都有定义：
        - smart_filter (Coordinator)
        - response_generation (UserAgent)
        - proposal_aggregation (ChannelAdmin)
        - proposal_adjustment (ChannelAdmin)
        - gap_identification (GapIdentificationService)
        """
        required_keys = [
            "smart_filter",
            "response_generation",
            "proposal_aggregation",
            "proposal_adjustment",
            "gap_identification",
        ]

        for key in required_keys:
            assert key in FALLBACK_RESPONSES, f"Missing fallback for: {key}"
            # 验证是有效 JSON
            try:
                json.loads(FALLBACK_RESPONSES[key])
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON for fallback key: {key}")
