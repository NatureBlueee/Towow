# TASK-T09-e2e-test

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T09-e2e-test.md`
>
> * TASK_ID: TASK-T09
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-22

---

## 关联 Story

- **全部 Story**: 端到端测试覆盖所有协商流程

---

## 任务描述

编写端到端测试，验证从需求提交到协商完成的完整流程，确保系统在各种场景下正常工作。

### 测试目标

1. 完整协商流程验证
2. 失败场景处理
3. 缺口识别与子网触发
4. 熔断降级流程
5. 前后端数据一致性

---

## 技术实现

### 测试文件结构

```
towow/tests/e2e/
├── conftest.py           # 测试配置和 fixtures
├── test_happy_path.py    # 正常流程测试
├── test_failure_cases.py # 失败场景测试
├── test_subnet.py        # 子网协商测试
└── test_integration.py   # 前后端集成测试
```

### 测试数据准备

#### Mock Agent Profiles

```python
# tests/e2e/conftest.py

import pytest
from typing import List, Dict

@pytest.fixture
def mock_agent_profiles() -> List[Dict]:
    """测试用 Agent 配置"""
    return [
        {
            "agent_id": "user_agent_bob",
            "user_name": "Bob",
            "profile_summary": "场地资源提供者，有30人会议室...",
            "location": "北京",
            "tags": ["场地提供", "会议室", "茶歇服务"],
            "capabilities": {"venue_capacity": 30},
            "interests": ["技术交流", "创业"],
            "availability": "weekends"
        },
        {
            "agent_id": "user_agent_carol",
            "user_name": "Carol",
            "profile_summary": "AI领域专家，可做技术分享...",
            "location": "北京",
            "tags": ["演讲嘉宾", "AI专家", "技术分享"],
            "capabilities": {"speaking_topics": ["LLM", "Agent"]},
            "interests": ["AI", "开源"],
            "availability": "flexible"
        },
        {
            "agent_id": "user_agent_dave",
            "user_name": "Dave",
            "profile_summary": "活动策划经验丰富...",
            "location": "北京",
            "tags": ["活动策划", "项目管理"],
            "capabilities": {"event_experience": 5},
            "interests": ["社区运营"],
            "availability": "weekdays"
        }
    ]

@pytest.fixture
def test_demand() -> Dict:
    """测试用需求"""
    return {
        "raw_input": "我想在北京办一场AI主题的技术聚会，需要场地和演讲嘉宾",
        "user_id": "user_alice"
    }
```

### 关键测试用例

#### 1. 完整协商流程测试

```python
# tests/e2e/test_happy_path.py

import pytest
import asyncio
from httpx import AsyncClient
from typing import List

class TestHappyPath:
    """正常流程端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_negotiation_flow(
        self,
        async_client: AsyncClient,
        mock_agent_profiles: List,
        test_demand: dict
    ):
        """测试完整协商流程：提交需求 → 筛选 → 响应 → 方案 → 协商 → 完成"""

        # 1. 提交需求
        response = await async_client.post(
            "/api/v1/demand/submit",
            json=test_demand
        )
        assert response.status_code == 200
        data = response.json()
        demand_id = data["demand_id"]
        channel_id = data["channel_id"]

        assert data["status"] == "processing"
        assert "understanding" in data

        # 2. 等待协商完成（通过 SSE 监听）
        events = []
        async with async_client.stream(
            "GET",
            f"/api/v1/events/negotiations/{demand_id}/stream",
            timeout=60.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    event_data = json.loads(line[5:])
                    events.append(event_data)

                    # 检查是否完成
                    if event_data["event_type"] in [
                        "towow.proposal.finalized",
                        "towow.negotiation.failed"
                    ]:
                        break

        # 3. 验证事件序列
        event_types = [e["event_type"] for e in events]

        # 必须包含的事件
        assert "towow.demand.understood" in event_types
        assert "towow.filter.completed" in event_types
        assert "towow.offer.submitted" in event_types
        assert "towow.proposal.distributed" in event_types

        # 应该成功完成
        assert "towow.proposal.finalized" in event_types

    @pytest.mark.asyncio
    async def test_multi_round_negotiation(
        self,
        async_client: AsyncClient,
        mock_agent_profiles: List
    ):
        """测试多轮协商（有 negotiate 反馈的情况）"""

        # 提交一个容易引发协商的需求
        response = await async_client.post(
            "/api/v1/demand/submit",
            json={
                "raw_input": "我想办一个50人的聚会，需要场地、嘉宾和摄影",
                "user_id": "user_alice"
            }
        )
        demand_id = response.json()["demand_id"]

        # 收集事件
        events = await self._collect_events(async_client, demand_id, timeout=90)

        # 验证是否有多轮
        round_events = [e for e in events if e["event_type"] == "towow.negotiation.round_started"]

        # 至少进行了协商
        assert len(events) > 5

    async def _collect_events(
        self,
        client: AsyncClient,
        demand_id: str,
        timeout: float = 60.0
    ) -> List[dict]:
        """收集 SSE 事件"""
        events = []
        try:
            async with asyncio.timeout(timeout):
                async with client.stream(
                    "GET",
                    f"/api/v1/events/negotiations/{demand_id}/stream"
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            event_data = json.loads(line[5:])
                            events.append(event_data)

                            if event_data["event_type"] in [
                                "towow.proposal.finalized",
                                "towow.negotiation.failed"
                            ]:
                                break
        except asyncio.TimeoutError:
            pass
        return events
```

#### 2. 失败场景测试

```python
# tests/e2e/test_failure_cases.py

import pytest
from httpx import AsyncClient

class TestFailureCases:
    """失败场景测试"""

    @pytest.mark.asyncio
    async def test_no_candidates_found(self, async_client: AsyncClient):
        """测试无候选人匹配的情况"""

        # 提交一个无法匹配的需求
        response = await async_client.post(
            "/api/v1/demand/submit",
            json={
                "raw_input": "我需要在火星上建一个基地",
                "user_id": "user_alice"
            }
        )
        demand_id = response.json()["demand_id"]

        events = await self._collect_events(async_client, demand_id)

        # 应该有失败事件或空候选人
        event_types = [e["event_type"] for e in events]

        # 要么筛选完成但候选人为空
        filter_events = [e for e in events if e["event_type"] == "towow.filter.completed"]
        if filter_events:
            assert filter_events[0]["payload"]["candidates_count"] == 0 or \
                   "towow.negotiation.failed" in event_types

    @pytest.mark.asyncio
    async def test_all_agents_decline(self, async_client: AsyncClient):
        """测试所有 Agent 都拒绝的情况"""

        # 这个测试需要配置让所有 Agent 都拒绝
        # 可以通过 mock 或特殊的测试配置实现
        pass

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(
        self,
        async_client: AsyncClient,
        mock_llm_timeout
    ):
        """测试 LLM 超时降级"""

        response = await async_client.post(
            "/api/v1/demand/submit",
            json={
                "raw_input": "测试需求",
                "user_id": "user_alice"
            }
        )

        # 验证请求没有失败（降级生效）
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_circuit_breaker_fallback(
        self,
        async_client: AsyncClient,
        trigger_circuit_breaker  # fixture: 触发熔断器
    ):
        """测试熔断器降级"""

        # 熔断器打开后的请求
        response = await async_client.post(
            "/api/v1/demand/submit",
            json={
                "raw_input": "测试需求",
                "user_id": "user_alice"
            }
        )

        # 验证降级响应
        assert response.status_code == 200
        # 可能返回简化的处理结果
```

#### 3. 缺口与子网测试

```python
# tests/e2e/test_subnet.py

import pytest
from httpx import AsyncClient

class TestSubnetNegotiation:
    """缺口识别与子网协商测试"""

    @pytest.mark.asyncio
    async def test_gap_identification(self, async_client: AsyncClient):
        """测试缺口识别"""

        # 提交一个明确有缺口的需求
        response = await async_client.post(
            "/api/v1/demand/submit",
            json={
                "raw_input": "我需要场地、演讲嘉宾、摄影师和主持人来办一场活动",
                "user_id": "user_alice"
            }
        )
        demand_id = response.json()["demand_id"]

        events = await self._collect_events(async_client, demand_id, timeout=120)

        # 检查是否有缺口识别事件
        gap_events = [e for e in events if e["event_type"] == "towow.gap.identified"]

        # 如果识别到缺口
        if gap_events:
            gaps = gap_events[0]["payload"]["gaps"]
            assert isinstance(gaps, list)

    @pytest.mark.asyncio
    async def test_subnet_triggered(self, async_client: AsyncClient):
        """测试子网触发"""

        # 需要配置能触发子网的场景
        # ...
        pass
```

---

## 接口契约

### 测试 API

```python
# POST /api/v1/demand/submit
# 请求
{
    "raw_input": str,
    "user_id": str
}

# 响应
{
    "demand_id": str,
    "channel_id": str,
    "status": "processing" | "completed" | "failed",
    "understanding": {...}
}
```

### SSE 事件流

```
GET /api/v1/events/negotiations/{demand_id}/stream

# 事件格式
data: {"event_id": "...", "event_type": "towow.xxx", "timestamp": "...", "payload": {...}}
```

---

## 依赖

### 硬依赖
- **T01**: demand.py 重构（API 入口）
- **T05**: 多轮协商逻辑（核心流程）
- **T06**: 缺口识别与子网（子网测试）
- **T08**: 熔断器测试（降级测试）

### 接口依赖
- 无

### 被依赖
- 无（最终验证任务）

---

## 验收标准

- [ ] **AC-1**: 完整协商流程测试通过（Happy Path）
- [ ] **AC-2**: 多轮协商测试通过（最多 3 轮）
- [ ] **AC-3**: 无候选人场景正确处理
- [ ] **AC-4**: LLM 降级场景正确处理
- [ ] **AC-5**: 缺口识别功能正常
- [ ] **AC-6**: 所有 E2E 测试通过率 >= 80%

### 测试覆盖场景

| 场景 | 预期结果 | 状态 |
|------|----------|------|
| 正常 3 人协商 | 2-3 轮内达成共识 | TODO |
| 单人参与 | 生成单人方案 | TODO |
| 无候选人 | 返回失败提示 | TODO |
| 全员拒绝 | 生成妥协建议 | TODO |
| LLM 超时 | 降级响应，流程继续 | TODO |
| 熔断器打开 | 降级响应 | TODO |
| 缺口识别 | 识别出缺失角色 | TODO |
| 子网触发 | 正确递归 | TODO |

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| 测试框架搭建 | 0.5h |
| Happy Path 测试 | 1h |
| 失败场景测试 | 1h |
| 子网测试 | 1h |
| CI/CD 集成 | 0.5h |
| **总计** | **4h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 调用不稳定 | 测试结果不确定 | 使用 mock LLM 进行确定性测试 |
| 测试超时 | CI 失败 | 设置合理超时，分阶段测试 |
| 测试环境与生产不一致 | 漏测 | 使用 Docker 统一环境 |

---

## 实现记录

*(开发完成后填写)*

---

## 测试记录

*(测试完成后填写)*
