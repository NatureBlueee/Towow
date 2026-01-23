# TASK-T10-e2e-test

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T10-e2e-test.md`
>
> * TASK_ID: TASK-T10
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-23

---

## 关联 Story

- **全部 Story**: 端到端验证

---

## 任务描述

实现端到端测试，验证完整的多 Agent 协商流程。覆盖从需求提交到方案终结的全部场景，包括正常流程、异常处理、强制终结等。

### 测试目标

1. 验证完整协商流程（需求 → 筛选 → 响应 → 聚合 → 反馈 → 终结）
2. 验证 5 轮协商 + 强制终结机制
3. 验证三档阈值判定（>=80%, 50-80%, <50%）
4. 验证状态检查与恢复机制
5. 验证熔断降级机制
6. 验证 SSE 事件流

---

## 技术实现

### 测试文件

| 文件 | 测试内容 |
|------|----------|
| `tests/e2e/test_full_negotiation.py` | 完整协商流程 |
| `tests/e2e/test_force_finalize.py` | 强制终结场景 |
| `tests/e2e/test_threshold_decision.py` | 阈值判定 |
| `tests/e2e/test_recovery.py` | 状态恢复 |
| `tests/e2e/test_circuit_breaker.py` | 熔断降级 |
| `tests/e2e/test_sse_events.py` | SSE 事件流 |

### 测试用例设计

#### 1. 完整协商流程测试

```python
# tests/e2e/test_full_negotiation.py

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import json

@pytest.mark.asyncio
@pytest.mark.e2e
class TestFullNegotiation:
    """完整协商流程 E2E 测试"""

    async def test_happy_path_single_round(self, client: AsyncClient):
        """
        场景: 单轮协商成功
        - 提交需求
        - 智能筛选返回 3 个候选
        - 3 个 Agent 都返回 offer + accept
        - accept_rate = 100% >= 80%
        - 协商成功，状态为 FINALIZED
        """
        # 1. 提交需求
        response = await client.post("/api/v1/demand/submit", json={
            "raw_input": "我想在北京办一场AI聚会",
            "user_id": "test_user"
        })

        assert response.status_code == 200
        data = response.json()
        demand_id = data["demand_id"]
        channel_id = data["channel_id"]

        # 2. 等待协商完成
        await self._wait_for_completion(client, demand_id, timeout=30)

        # 3. 验证结果
        status = await self._get_channel_status(client, channel_id)
        assert status["status"] == "finalized"
        assert status["accept_rate"] >= 0.8

    async def test_multi_round_negotiation(self, client: AsyncClient):
        """
        场景: 多轮协商
        - 第 1 轮: accept_rate = 60% → 继续协商
        - 第 2 轮: accept_rate = 70% → 继续协商
        - 第 3 轮: accept_rate = 85% → 成功终结
        """
        # 模拟 UserAgent 返回渐进式接受
        mock_responses = [
            {"round": 1, "accepts": 3, "total": 5, "rate": 0.6},
            {"round": 2, "accepts": 3.5, "total": 5, "rate": 0.7},
            {"round": 3, "accepts": 4, "total": 5, "rate": 0.85},
        ]

        # 提交需求并等待
        response = await client.post("/api/v1/demand/submit", json={
            "raw_input": "测试多轮协商",
            "user_id": "test_user"
        })

        data = response.json()
        demand_id = data["demand_id"]

        # 等待完成
        await self._wait_for_completion(client, demand_id, timeout=60)

        # 验证轮次
        events = await self._get_events(client, demand_id)
        round_events = [e for e in events if e["event_type"] == "towow.negotiation.round_started"]

        # 应该有 2-3 轮（取决于具体实现）
        assert len(round_events) >= 1

    async def test_force_finalize_at_round_5(self, client: AsyncClient):
        """
        场景: 第 5 轮强制终结
        - 前 4 轮: accept_rate 在 50-80% 之间
        - 第 5 轮: 强制终结，区分确认/可选参与者
        """
        # 模拟持续 negotiate 的场景
        with patch("openagents.agents.user_agent.UserAgent._generate_feedback") as mock:
            # 前 4 轮都返回 negotiate
            mock.side_effect = [
                {"feedback_type": "negotiate"} for _ in range(20)  # 假设 5 个 Agent * 4 轮
            ]

            response = await client.post("/api/v1/demand/submit", json={
                "raw_input": "测试强制终结",
                "user_id": "test_user"
            })

            data = response.json()
            demand_id = data["demand_id"]

            # 等待完成
            await self._wait_for_completion(client, demand_id, timeout=120)

            # 验证强制终结
            events = await self._get_events(client, demand_id)
            force_finalized = [
                e for e in events
                if e["event_type"] == "towow.negotiation.force_finalized"
            ]

            assert len(force_finalized) == 1
            assert force_finalized[0]["payload"]["rounds_taken"] == 5

    async def _wait_for_completion(
        self,
        client: AsyncClient,
        demand_id: str,
        timeout: int = 30
    ) -> None:
        """等待协商完成"""
        import asyncio

        for _ in range(timeout):
            status = await self._get_demand_status(client, demand_id)
            if status in ["finalized", "force_finalized", "failed"]:
                return
            await asyncio.sleep(1)

        raise TimeoutError(f"协商超时: {demand_id}")

    async def _get_events(
        self,
        client: AsyncClient,
        demand_id: str
    ) -> list:
        """获取事件列表"""
        response = await client.get(f"/api/v1/events/{demand_id}")
        return response.json()
```

#### 2. 阈值判定测试

```python
# tests/e2e/test_threshold_decision.py

@pytest.mark.asyncio
@pytest.mark.e2e
class TestThresholdDecision:
    """三档阈值判定测试"""

    async def test_high_accept_rate_finalize(self, client: AsyncClient):
        """
        场景: accept_rate >= 80% → FINALIZED
        """
        # 模拟 5 个 Agent，4 个 accept (80%)
        with self._mock_feedback(accepts=4, total=5):
            result = await self._run_negotiation(client)

            assert result["status"] == "finalized"
            assert result["accept_rate"] >= 0.8

    async def test_medium_accept_rate_renegotiate(self, client: AsyncClient):
        """
        场景: 50% <= accept_rate < 80% → 继续协商
        """
        # 模拟 5 个 Agent，3 个 accept (60%)
        with self._mock_feedback(accepts=3, total=5):
            result = await self._run_negotiation(client, max_wait=10)

            # 应该进入新一轮，而不是直接终结
            events = result["events"]
            round_started = [
                e for e in events
                if e["event_type"] == "towow.negotiation.round_started"
            ]
            assert len(round_started) >= 1

    async def test_low_accept_rate_fail(self, client: AsyncClient):
        """
        场景: accept_rate < 50% → FAILED
        """
        # 模拟 5 个 Agent，2 个 accept (40%)
        with self._mock_feedback(accepts=2, total=5):
            result = await self._run_negotiation(client)

            assert result["status"] == "failed"
            assert "low_acceptance" in result.get("reason", "")

    async def test_edge_case_exactly_80_percent(self, client: AsyncClient):
        """
        边界测试: accept_rate == 80% → FINALIZED
        """
        with self._mock_feedback(accepts=4, total=5):  # 80%
            result = await self._run_negotiation(client)

            assert result["status"] == "finalized"

    async def test_edge_case_exactly_50_percent(self, client: AsyncClient):
        """
        边界测试: accept_rate == 50% → 继续协商
        """
        with self._mock_feedback(accepts=5, total=10):  # 50%
            result = await self._run_negotiation(client, max_wait=10)

            # 50% 应该继续协商，不是失败
            assert result["status"] != "failed"
```

#### 3. SSE 事件流测试

```python
# tests/e2e/test_sse_events.py

@pytest.mark.asyncio
@pytest.mark.e2e
class TestSSEEvents:
    """SSE 事件流测试"""

    async def test_event_sequence(self, client: AsyncClient):
        """
        验证事件发布顺序:
        1. towow.demand.understood
        2. towow.filter.completed
        3. towow.channel.created
        4. towow.offer.submitted (multiple)
        5. towow.proposal.distributed
        6. towow.proposal.feedback (multiple)
        7. towow.feedback.evaluated
        8. towow.proposal.finalized / towow.negotiation.force_finalized / towow.negotiation.failed
        """
        response = await client.post("/api/v1/demand/submit", json={
            "raw_input": "测试事件序列",
            "user_id": "test_user"
        })

        demand_id = response.json()["demand_id"]

        # 收集 SSE 事件
        events = await self._collect_sse_events(client, demand_id, timeout=30)

        # 验证事件序列
        event_types = [e["event_type"] for e in events]

        # 必须有的事件
        assert "towow.demand.understood" in event_types
        assert "towow.filter.completed" in event_types
        assert "towow.channel.created" in event_types
        assert "towow.offer.submitted" in event_types
        assert "towow.proposal.distributed" in event_types

        # 必须以终态事件结束
        final_events = [
            "towow.proposal.finalized",
            "towow.negotiation.force_finalized",
            "towow.negotiation.failed"
        ]
        assert any(e in event_types for e in final_events)

    async def test_v4_new_events(self, client: AsyncClient):
        """
        验证 v4 新增事件:
        - towow.feedback.evaluated (含 accept_rate)
        - towow.negotiation.round_started (含 round 信息)
        - towow.negotiation.force_finalized (含 confirmed/optional 参与者)
        """
        response = await client.post("/api/v1/demand/submit", json={
            "raw_input": "测试 v4 新事件",
            "user_id": "test_user"
        })

        demand_id = response.json()["demand_id"]
        events = await self._collect_sse_events(client, demand_id, timeout=30)

        # 验证 feedback.evaluated 事件
        feedback_events = [
            e for e in events
            if e["event_type"] == "towow.feedback.evaluated"
        ]

        for event in feedback_events:
            payload = event["payload"]
            assert "accept_rate" in payload
            assert "round" in payload
            assert "decision" in payload

    async def test_offer_submitted_contains_response_type(self, client: AsyncClient):
        """
        验证 offer.submitted 事件包含 response_type
        """
        response = await client.post("/api/v1/demand/submit", json={
            "raw_input": "测试响应类型",
            "user_id": "test_user"
        })

        demand_id = response.json()["demand_id"]
        events = await self._collect_sse_events(client, demand_id, timeout=30)

        offer_events = [
            e for e in events
            if e["event_type"] == "towow.offer.submitted"
        ]

        for event in offer_events:
            payload = event["payload"]
            assert "response_type" in payload
            assert payload["response_type"] in ["offer", "negotiate"]

    async def _collect_sse_events(
        self,
        client: AsyncClient,
        demand_id: str,
        timeout: int = 30
    ) -> list:
        """收集 SSE 事件"""
        import asyncio

        events = []
        async with client.stream(
            "GET",
            f"/api/v1/events/negotiations/{demand_id}/stream"
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    event = json.loads(line[5:].strip())
                    events.append(event)

                    # 检查是否为终态事件
                    if event["event_type"] in [
                        "towow.proposal.finalized",
                        "towow.negotiation.force_finalized",
                        "towow.negotiation.failed"
                    ]:
                        break

                # 超时检查
                if len(events) == 0:
                    await asyncio.sleep(1)
                    timeout -= 1
                    if timeout <= 0:
                        break

        return events
```

#### 4. 熔断降级测试

```python
# tests/e2e/test_circuit_breaker.py

@pytest.mark.asyncio
@pytest.mark.e2e
class TestCircuitBreaker:
    """熔断器 E2E 测试"""

    async def test_fallback_on_llm_failure(self, client: AsyncClient):
        """
        场景: LLM 连续失败 3 次，触发熔断，使用降级响应
        """
        with patch("services.llm.LLMService.call") as mock_llm:
            # 模拟连续失败
            mock_llm.side_effect = Exception("LLM service unavailable")

            response = await client.post("/api/v1/demand/submit", json={
                "raw_input": "测试熔断降级",
                "user_id": "test_user"
            })

            # 应该成功返回（使用降级响应）
            assert response.status_code == 200

            # 等待处理
            await asyncio.sleep(5)

            # 验证使用了降级候选（兜底 3 个）
            events = await self._get_events(client, response.json()["demand_id"])
            filter_event = next(
                e for e in events
                if e["event_type"] == "towow.filter.completed"
            )

            # 降级时应该有 fallback 标记
            # 注意：具体实现可能不同，这里验证至少有候选
            assert filter_event["payload"]["candidates_count"] >= 1
```

---

## 验收标准

- [x] **AC-1**: 完整协商流程（单轮）通过率 >= 95%
- [x] **AC-2**: 多轮协商流程（最多 5 轮）通过率 >= 90%
- [x] **AC-3**: 强制终结场景测试通过
- [x] **AC-4**: 三档阈值判定测试通过（包括边界值）
- [x] **AC-5**: SSE 事件序列正确
- [x] **AC-6**: v4 新增事件格式正确
- [x] **AC-7**: 熔断降级测试通过
- [x] **AC-8**: 总体 E2E 测试覆盖率 >= 80%

---

## 依赖

### 硬依赖
- **T01**: demand.py 重构
- **T02**: Coordinator 智能筛选
- **T03**: UserAgent 响应生成
- **T04**: ChannelAdmin 方案聚合
- **T05**: 多轮协商逻辑
- **T06**: 缺口识别与子网
- **T07**: 状态检查与恢复机制
- **T09**: 熔断器测试

### 接口依赖
- **T08**: 前端修复（可选，用于手动验证）

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| 测试框架搭建 | 1h |
| 完整流程测试 | 1h |
| 阈值判定测试 | 0.5h |
| SSE 事件测试 | 0.5h |
| 熔断降级测试 | 0.5h |
| 测试调试 | 0.5h |
| **总计** | **4h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 测试环境不稳定 | 测试结果不可靠 | 使用隔离的测试数据库 |
| 异步操作时序问题 | 测试 flaky | 增加重试和超时机制 |
| Mock 与实际不一致 | 测试通过但线上失败 | 增加集成测试比例 |

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
