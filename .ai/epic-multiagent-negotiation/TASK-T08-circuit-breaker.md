# TASK-T08-circuit-breaker

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T08-circuit-breaker.md`
>
> * TASK_ID: TASK-T08
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-22

---

## 关联 Story

- **STORY-05**: 多轮协商与分歧处理（熔断器支持协商失败降级）
- **STORY-04**: 方案聚合与角色分配（熔断器保护 LLM 调用）

---

## 任务描述

验证和测试 LLMService 的熔断器机制，确保在 LLM 服务不可用时系统能够正确降级，保障协商流程的可用性。

### 改造目标

1. 验证熔断器配置正确生效
2. 测试所有降级响应格式符合下游期望
3. 确保熔断器与 LLMService 正确集成
4. 验证半开状态的试探机制

---

## 技术实现

### 熔断器配置（参考 TECH-v3.md 6.2.1 节）

```python
# services/llm.py 中的熔断器配置

CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 3,    # 连续 3 次失败后触发熔断
    "recovery_timeout": 30,    # 熔断后 30 秒进入半开状态
    "half_open_requests": 1    # 半开状态允许 1 次试探请求
}
```

### 修改/验证的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/services/llm.py` | 验证熔断器实现，补充测试接口 |
| `towow/tests/test_circuit_breaker.py` | 新增熔断器单元测试 |
| `towow/tests/test_llm_fallback.py` | 新增降级响应测试 |

### 关键代码验证

#### 1. 熔断器状态机

```python
# 预期的熔断器状态流转
CLOSED (正常)
    → 连续 3 次失败
    → OPEN (熔断)
    → 30 秒后
    → HALF_OPEN (半开)
    → 成功 → CLOSED
    → 失败 → OPEN
```

#### 2. 降级响应格式验证

```python
# services/llm.py 中的 FALLBACK_RESPONSES

FALLBACK_RESPONSES = {
    "smart_filter": {
        "analysis": "LLM 服务暂时不可用，返回 mock 候选人",
        "definitely_related": [],
        "possibly_related": [],
        "total_candidates": 0
    },
    "response_generation": {
        "decision": "decline",
        "contribution": "",
        "conditions": [],
        "reasoning": "LLM 服务暂时不可用",
        "decline_reason": "系统维护中",
        "confidence": 0
    },
    "proposal_aggregation": {
        "summary": "由于系统原因，暂时无法生成方案",
        "objective": "",
        "assignments": [],
        "timeline": None,
        "rationale": "LLM 服务暂时不可用",
        "gaps": [],
        "confidence": "low"
    },
    "proposal_adjustment": {
        # 返回原方案，不做调整
        "adjustment_summary": {
            "round": 0,
            "changes_made": [],
            "requests_addressed": [],
            "requests_declined": ["LLM 服务不可用，保持原方案"]
        }
    },
    "gap_identify": {
        "is_complete": True,
        "analysis": "LLM 服务暂时不可用，跳过缺口识别",
        "gaps": []
    },
    "default": {
        "error": "LLM 服务暂时不可用",
        "fallback": True
    }
}
```

#### 3. 测试用例

```python
# tests/test_circuit_breaker.py

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from services.llm import LLMServiceWithFallback, CIRCUIT_BREAKER_CONFIG

class TestCircuitBreaker:
    """熔断器测试"""

    @pytest.fixture
    def llm_service(self):
        return LLMServiceWithFallback()

    async def test_circuit_opens_after_failures(self, llm_service):
        """测试连续失败后熔断器打开"""
        with patch.object(llm_service, '_call_llm', side_effect=Exception("API Error")):
            # 连续调用，触发熔断
            for _ in range(CIRCUIT_BREAKER_CONFIG["failure_threshold"]):
                try:
                    await llm_service.call("smart_filter", {})
                except:
                    pass

            # 验证熔断器状态
            assert llm_service.circuit_state == "OPEN"

    async def test_circuit_returns_fallback_when_open(self, llm_service):
        """测试熔断状态下返回降级响应"""
        llm_service.circuit_state = "OPEN"
        llm_service.last_failure_time = asyncio.get_event_loop().time()

        result = await llm_service.call("smart_filter", {})

        assert result["fallback"] == True or "definitely_related" in result

    async def test_circuit_half_open_after_timeout(self, llm_service):
        """测试超时后进入半开状态"""
        llm_service.circuit_state = "OPEN"
        llm_service.last_failure_time = asyncio.get_event_loop().time() - 31  # 31 秒前

        # 下次调用应该进入半开状态
        assert llm_service._should_attempt_reset() == True

    async def test_circuit_closes_on_success_in_half_open(self, llm_service):
        """测试半开状态成功后关闭熔断器"""
        llm_service.circuit_state = "HALF_OPEN"

        with patch.object(llm_service, '_call_llm', return_value={"result": "success"}):
            await llm_service.call("smart_filter", {})

            assert llm_service.circuit_state == "CLOSED"

    async def test_circuit_reopens_on_failure_in_half_open(self, llm_service):
        """测试半开状态失败后重新打开熔断器"""
        llm_service.circuit_state = "HALF_OPEN"

        with patch.object(llm_service, '_call_llm', side_effect=Exception("API Error")):
            try:
                await llm_service.call("smart_filter", {})
            except:
                pass

            assert llm_service.circuit_state == "OPEN"


class TestFallbackResponses:
    """降级响应测试"""

    @pytest.fixture
    def llm_service(self):
        return LLMServiceWithFallback()

    async def test_smart_filter_fallback_format(self, llm_service):
        """测试智能筛选降级响应格式"""
        llm_service.circuit_state = "OPEN"
        llm_service.last_failure_time = asyncio.get_event_loop().time()

        result = await llm_service.call("smart_filter", {})

        # 验证必要字段
        assert "definitely_related" in result
        assert "possibly_related" in result
        assert "total_candidates" in result
        assert isinstance(result["definitely_related"], list)
        assert isinstance(result["possibly_related"], list)

    async def test_response_generation_fallback_format(self, llm_service):
        """测试响应生成降级响应格式"""
        llm_service.circuit_state = "OPEN"
        llm_service.last_failure_time = asyncio.get_event_loop().time()

        result = await llm_service.call("response_generation", {})

        # 验证必要字段
        assert "decision" in result
        assert result["decision"] in ["participate", "decline", "conditional"]
        assert "reasoning" in result

    async def test_proposal_aggregation_fallback_format(self, llm_service):
        """测试方案聚合降级响应格式"""
        llm_service.circuit_state = "OPEN"
        llm_service.last_failure_time = asyncio.get_event_loop().time()

        result = await llm_service.call("proposal_aggregation", {})

        # 验证必要字段
        assert "summary" in result
        assert "assignments" in result
        assert isinstance(result["assignments"], list)
        assert "confidence" in result

    async def test_gap_identify_fallback_format(self, llm_service):
        """测试缺口识别降级响应格式"""
        llm_service.circuit_state = "OPEN"
        llm_service.last_failure_time = asyncio.get_event_loop().time()

        result = await llm_service.call("gap_identify", {})

        # 验证必要字段
        assert "is_complete" in result
        assert "gaps" in result
        assert isinstance(result["gaps"], list)
```

---

## 接口契约

### LLMService 调用接口

```python
class LLMServiceWithFallback:
    async def call(
        self,
        prompt_type: str,  # smart_filter | response_generation | proposal_aggregation | ...
        params: dict
    ) -> dict:
        """
        调用 LLM，支持熔断和降级

        Returns:
            dict: LLM 响应或降级响应
        """
        pass
```

### 熔断器状态接口

```python
class CircuitBreaker:
    state: str  # CLOSED | OPEN | HALF_OPEN
    failure_count: int
    last_failure_time: float

    def record_success(self) -> None: ...
    def record_failure(self) -> None: ...
    def should_allow_request(self) -> bool: ...
```

---

## 依赖

### 硬依赖
- **T01**: demand.py 重构（需要调用入口存在）

### 接口依赖
- 无

### 被依赖
- **T09**: E2E 测试（需要熔断器正常工作）

---

## 验收标准

- [ ] **AC-1**: 连续 3 次 LLM 调用失败后，熔断器进入 OPEN 状态
- [ ] **AC-2**: 熔断状态下，直接返回降级响应，不发起 LLM 调用
- [ ] **AC-3**: 熔断 30 秒后，进入 HALF_OPEN 状态
- [ ] **AC-4**: HALF_OPEN 状态下成功一次，熔断器关闭
- [ ] **AC-5**: HALF_OPEN 状态下失败，重新进入 OPEN 状态
- [ ] **AC-6**: 所有 FALLBACK_RESPONSES 格式符合下游期望，不会导致解析错误

### 测试用例

```bash
# 运行熔断器测试
pytest tests/test_circuit_breaker.py -v

# 预期输出
# test_circuit_opens_after_failures PASSED
# test_circuit_returns_fallback_when_open PASSED
# test_circuit_half_open_after_timeout PASSED
# test_circuit_closes_on_success_in_half_open PASSED
# test_circuit_reopens_on_failure_in_half_open PASSED
# test_smart_filter_fallback_format PASSED
# test_response_generation_fallback_format PASSED
# test_proposal_aggregation_fallback_format PASSED
# test_gap_identify_fallback_format PASSED
```

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| 熔断器实现验证 | 1h |
| 降级响应格式验证 | 0.5h |
| 单元测试编写 | 1h |
| 集成测试 | 0.5h |
| **总计** | **3h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 降级响应格式不符合下游期望 | 协商流程中断 | 提前定义和验证所有响应格式 |
| 熔断器状态不同步 | 并发问题 | 使用线程安全的状态管理 |
| 半开状态试探失败过多 | 系统恢复慢 | 配置合理的恢复超时 |

---

## 实现记录

*(开发完成后填写)*

---

## 测试记录

*(测试完成后填写)*
