# TASK-T01-demand-api-refactor

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T01-demand-api-refactor.md`
>
> * TASK_ID: TASK-T01
> * BEADS_ID: towow-0bk
> * 状态: DOING (待 review)
> * 创建日期: 2026-01-22

---

## 关联 Story

- **STORY-01**: 需求理解与深层洞察

---

## 任务描述

重构 `api/routers/demand.py`，移除硬编码的 `trigger_mock_negotiation()` 函数，改为调用真实的 Agent 协商流程。这是整个 Epic 的基础任务，后续所有 Agent 改造都依赖此任务完成。

### 当前问题

1. `trigger_mock_negotiation()` 使用硬编码的 Mock 数据模拟协商过程
2. 没有真正调用 `Coordinator` 启动协商流程
3. 事件发布使用固定延迟的模拟数据

### 改造目标

1. 调用 `Coordinator` 处理新需求
2. 真实触发 Agent 间的消息传递
3. 保留 Mock 模式作为演示/降级选项

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/api/routers/demand.py` | 重构 `submit_demand()` 和 `trigger_mock_negotiation()` |
| `towow/api/main.py` | 确保 Agent 初始化 |
| `towow/openagents/agents/__init__.py` | 导出 Agent 单例 |

### 关键代码改动

#### 1. demand.py 重构

```python
# towow/api/routers/demand.py

from openagents.agents import get_coordinator, get_channel_admin

@router.post("/submit")
async def submit_demand(request: DemandRequest):
    """
    提交新需求，触发真实协商流程
    """
    demand_id = f"d-{uuid4().hex[:8]}"

    # 获取 Coordinator 实例
    coordinator = get_coordinator()

    if not coordinator:
        # 降级：使用 Mock 模式
        return await trigger_mock_negotiation(demand_id, request)

    # 真实模式：调用 Coordinator 处理需求
    try:
        # 发送需求给 Coordinator
        await coordinator.send_to_agent("coordinator", {
            "type": "new_demand",
            "demand_id": demand_id,
            "user_id": request.user_id or "anonymous",
            "raw_input": request.raw_input
        })

        return {
            "demand_id": demand_id,
            "channel_id": f"collab-{demand_id[2:]}",
            "status": "processing",
            "message": "需求已提交，协商正在进行中"
        }
    except Exception as e:
        logger.error(f"协商启动失败: {e}")
        # 降级到 Mock 模式
        return await trigger_mock_negotiation(demand_id, request)


async def trigger_real_negotiation(demand_id: str, request: DemandRequest):
    """
    触发真实协商流程（新增）
    """
    coordinator = get_coordinator()

    # 构造需求消息
    demand_message = {
        "type": "new_demand",
        "demand_id": demand_id,
        "user_id": request.user_id or "anonymous",
        "raw_input": request.raw_input,
        "submitted_at": datetime.utcnow().isoformat()
    }

    # 通过直接调用处理（同进程）
    await coordinator._process_direct_demand(demand_message)

    return {
        "demand_id": demand_id,
        "channel_id": f"collab-{demand_id[2:]}",
        "status": "processing"
    }


async def trigger_mock_negotiation(demand_id: str, request: DemandRequest):
    """
    Mock 模式（保留用于演示/降级）
    标记为 deprecated，仅在真实模式不可用时使用
    """
    # ... 保留现有 Mock 逻辑 ...
```

#### 2. Agent 单例管理

```python
# towow/openagents/agents/__init__.py

from typing import Optional
from .coordinator import CoordinatorAgent
from .channel_admin import ChannelAdminAgent
from .user_agent import UserAgent

# 全局 Agent 实例
_coordinator: Optional[CoordinatorAgent] = None
_channel_admin: Optional[ChannelAdminAgent] = None
_user_agents: dict = {}

def init_agents(llm_service=None, secondme_service=None, db=None):
    """初始化所有 Agent"""
    global _coordinator, _channel_admin

    _coordinator = CoordinatorAgent(
        secondme_service=secondme_service,
        llm=llm_service,
        db=db
    )

    _channel_admin = ChannelAdminAgent(
        llm=llm_service,
        db=db
    )

    return _coordinator, _channel_admin

def get_coordinator() -> Optional[CoordinatorAgent]:
    return _coordinator

def get_channel_admin() -> Optional[ChannelAdminAgent]:
    return _channel_admin

def get_or_create_user_agent(
    user_id: str,
    profile: dict = None,
    llm_service=None,
    secondme_service=None
) -> UserAgent:
    """获取或创建 UserAgent"""
    if user_id not in _user_agents:
        _user_agents[user_id] = UserAgent(
            user_id=user_id,
            profile=profile or {},
            secondme_service=secondme_service,
            llm=llm_service
        )
    return _user_agents[user_id]
```

#### 3. main.py 初始化

```python
# towow/api/main.py

from openagents.agents import init_agents
from services.llm import init_llm_service_with_fallback

@app.on_event("startup")
async def startup_event():
    # 初始化 LLM 服务
    llm_service = init_llm_service_with_fallback(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model=os.getenv("LLM_MODEL", "claude-sonnet-4-5-20250929"),
        base_url=os.getenv("ANTHROPIC_BASE_URL")
    )

    # 初始化 Agent
    init_agents(llm_service=llm_service)

    logger.info("Agent 系统已初始化")
```

---

## 接口契约

### 输入

```python
class DemandRequest(BaseModel):
    raw_input: str          # 用户原始输入
    user_id: Optional[str]  # 用户 ID
```

### 输出

```python
class SubmitDemandResponse(BaseModel):
    demand_id: str          # d-abc12345
    channel_id: str         # collab-abc12345
    status: str             # processing | completed | failed
    message: Optional[str]  # 状态说明
    understanding: Optional[dict]  # 需求理解结果（可选）
```

---

## 依赖

### 硬依赖
- 无（起始任务）

### 接口依赖
- 无

### 被依赖
- T02: Coordinator 智能筛选
- T03: UserAgent 响应生成
- T04: ChannelAdmin 方案聚合
- T07: 前端修复（接口依赖）

---

## 验收标准

- [x] **AC-1**: `POST /api/v1/demand/submit` 成功返回 `demand_id` 和 `channel_id`
- [x] **AC-2**: 提交需求后，`Coordinator._process_direct_demand()` 被真实调用
- [x] **AC-3**: 事件 `towow.demand.understood` 被发布到事件总线
- [x] **AC-4**: LLM 服务不可用时，自动降级到 Mock 模式
- [x] **AC-5**: 日志中可见完整的调用链路

### 测试用例

```python
# tests/test_demand_api.py

@pytest.mark.asyncio
async def test_submit_demand_triggers_coordinator():
    """测试需求提交触发 Coordinator"""
    response = client.post("/api/v1/demand/submit", json={
        "raw_input": "我想办一场AI聚会",
        "user_id": "test_user"
    })

    assert response.status_code == 200
    data = response.json()
    assert "demand_id" in data
    assert data["status"] == "processing"

@pytest.mark.asyncio
async def test_submit_demand_fallback_to_mock():
    """测试 Coordinator 不可用时降级到 Mock"""
    # 模拟 Coordinator 不可用
    with patch("openagents.agents.get_coordinator", return_value=None):
        response = client.post("/api/v1/demand/submit", json={
            "raw_input": "测试需求"
        })

        assert response.status_code == 200
        # 验证走了 Mock 路径
```

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| 代码开发 | 1.5h |
| 单元测试 | 0.5h |
| **总计** | **2h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Agent 间消息传递不通 | 协商无法启动 | 添加详细日志，本地调试 |
| LLM 服务初始化失败 | 无法进入真实模式 | 保留完整的 Mock 降级路径 |

---

## 实现记录

### 实际修改的文件

| 文件 | 修改内容 |
|------|----------|
| `towow/openagents/agents/coordinator.py` | 增强 `_process_direct_demand()` 支持接收预先计算的 `understanding` 参数，避免重复 LLM 调用 |
| `towow/api/routers/demand.py` | 修改 `trigger_real_negotiation()` 传递 `understanding` 参数给 Coordinator |
| `towow/tests/test_coordinator.py` | 新增 `TestProcessDirectDemandT01` 测试类，6 个测试用例 |

### 核心改动说明

1. **`_process_direct_demand()` 增强**
   - 新增 `understanding` 参数支持
   - 当传入预先计算的 understanding 时，跳过 `_understand_demand()` 调用
   - 避免 demand.py 和 Coordinator 重复调用 LLM 进行需求理解

2. **调用链优化**
   ```
   submit_demand() -> _process_demand_async()
     -> trigger_real_demand_understanding() [调用 SecondMe，获取 understanding]
     -> trigger_real_negotiation(understanding) [传递 understanding]
       -> Coordinator._process_direct_demand(understanding) [直接使用，不重复调用]
   ```

3. **事件发布职责明确**
   - `demand.py` 不发布 `demand.understood` 事件
   - `Coordinator._process_direct_demand()` 负责发布该事件
   - 避免重复事件

### 遇到的问题

1. **重复 LLM 调用问题**
   - 原实现：demand.py 调用 SecondMe，Coordinator 又调用 SecondMe
   - 解决：demand.py 预先获取 understanding，传递给 Coordinator

2. **事件重复发布问题**
   - 原实现：demand.py 和 Coordinator 都可能发布 `demand.understood`
   - 解决：明确 Coordinator 为唯一发布者

### 解决方案

修改 `_process_direct_demand()` 签名和逻辑：

```python
async def _process_direct_demand(self, content: Dict):
    """处理通过直接消息发送的需求

    Args:
        content: 需求内容，包含:
            - raw_input: 原始输入
            - user_id: 用户ID
            - demand_id: 需求ID（可选）
            - understanding: 预先理解的结果（可选，如果提供则跳过理解步骤）
    """
    pre_understanding = content.get("understanding")

    if pre_understanding:
        # 直接使用预先计算的 understanding
        understanding = pre_understanding
    else:
        # 调用 SecondMe 理解需求
        understanding = await self._understand_demand(raw_input, user_id)
```

---

## 测试记录

### 测试结果

```
tests/test_coordinator.py::TestProcessDirectDemandT01 - 6 passed

测试用例：
1. test_process_direct_demand_with_pre_understanding - PASSED
   验证传入 understanding 时不调用 SecondMe
2. test_process_direct_demand_without_pre_understanding - PASSED
   验证未传入 understanding 时调用 SecondMe
3. test_process_direct_demand_publishes_demand_understood_event - PASSED
   验证 demand.understood 事件正确发布
4. test_process_direct_demand_triggers_smart_filter - PASSED
   验证智能筛选被正确调用
5. test_process_direct_demand_creates_channel - PASSED
   验证协商 Channel 被正确创建
6. test_process_direct_demand_no_candidates_fallback - PASSED
   验证无候选人时发布 filter.failed 事件
```

### 覆盖率

- 核心模块测试：120 passed
- 新增 T01 测试：6 passed
- 总测试通过率：100%
