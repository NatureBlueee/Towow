# 通爻工程参考文档

> 本文档是工程实现的统一标准。所有开发者（人类和 Agent）必须遵循。
> 可以修改，但修改后必须通知所有相关方并更新本文档。
> 本文档与 `ARCHITECTURE_DESIGN.md` 平级，一个定义"是什么"，一个定义"怎么做"。

---

## 1. 代码结构

```
backend/towow/               # V1 独立包（不修改 backend/app.py）
├── core/                     # 协议层
│   ├── models.py            # 核心数据模型（NegotiationSession, TraceChain 等）
│   ├── engine.py            # 编排引擎（状态机）
│   ├── events.py            # 事件定义（9 种，V1 实现 7 种）
│   ├── protocols.py         # 模块间 Protocol 定义（Encoder, Skill, etc.）
│   └── errors.py            # 统一异常层次
├── skills/                   # 能力层
│   ├── base_skill.py        # Skill 基类
│   ├── formulation.py       # DemandFormulationSkill
│   ├── offer.py             # OfferGenerationSkill
│   ├── center.py            # CenterCoordinatorSkill
│   ├── sub_negotiation.py   # SubNegotiationSkill
│   └── gap_recursion.py     # GapRecursionSkill
├── adapters/                 # ProfileDataSource 适配器
│   ├── claude_adapter.py    # Claude 默认通道
│   └── secondme_adapter.py  # SecondMe OAuth2 适配器
├── hdc/                      # 向量编码与共振
│   ├── encoder.py           # EmbeddingEncoder（V1: sentence-transformers）
│   └── resonance.py         # CosineResonanceDetector
├── infra/                    # 基础设施
│   ├── llm_client.py        # ClaudePlatformClient（tool-use）
│   ├── event_pusher.py      # WebSocketEventPusher
│   └── config.py            # TowowConfig（pydantic-settings, TOWOW_ 前缀）
└── api/                      # 应用层
    ├── app.py               # FastAPI 入口（端口 8081）
    ├── routes.py            # 5 REST + 1 WebSocket 端点
    └── schemas.py           # Pydantic 请求/响应模型
```

**原则**：
- 按四层架构组织：协议层（core/）、能力层（skills/）、基础设施层（infra/）、应用层（api/）
- adapters/ 和 hdc/ 是独立的功能模块，不属于某一层
- 每个文件职责单一
- 新文件创建前确认它属于哪个目录

---

## 2. 命名约定

| 元素 | 规则 | 例子 |
|------|------|------|
| 文件名 | snake_case | `negotiation_session.py` |
| 类名 | PascalCase | `NegotiationSession` |
| 函数/方法 | snake_case | `submit_demand()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_ROUNDS = 2` |
| 私有成员 | 前缀 `_` | `_current_state` |
| 接口/协议 | PascalCase，无前缀 | `Encoder`（不用 `IEncoder`） |
| 事件类型 | dot.separated | `formulation.ready` |
| API 端点 | kebab-case | `/api/team-requests` |

---

## 3. 类型注解

- 所有公开接口（函数签名、类属性）必须有类型注解
- 内部实现中的局部变量可以省略（类型推断即可）
- 使用 `typing` 模块：`Optional`, `List`, `Dict`, `Protocol` 等
- 复杂类型用 `TypeAlias` 或 `dataclass` / `TypedDict` 封装

---

## 4. 异步模式

- 所有 I/O 操作（LLM 调用、数据库读写、WebSocket 推送）用 `async/await`
- 并行任务用 `asyncio.gather()` （兼容 Python 3.9+；不用 TaskGroup）
- 超时用 `asyncio.wait_for(coro, timeout=...)`
- 不在异步上下文中使用阻塞调用

---

## 5. 错误处理

### 统一异常层次

```python
class TowowError(Exception):
    """通爻基础异常"""
    pass

class AdapterError(TowowError):
    """Adapter 调用失败（端侧 LLM 不可用等）"""
    pass

class LLMError(TowowError):
    """平台侧 LLM 调用失败"""
    pass

class SkillError(TowowError):
    """Skill 执行失败（输出格式错误、超时等）"""
    pass

class EngineError(TowowError):
    """编排引擎内部错误"""
    pass
```

### 处理原则

- **Agent 不可用**：标记为"退出"，不阻塞流程（Section 8.1）
- **LLM 调用失败**：重试最多 3 次，仍失败则降级或终止
- **格式解析失败**：记录原始输出，尝试宽松解析，实在不行报错
- **不吞掉异常**：所有异常要么处理、要么传播，不 `except: pass`

---

## 6. 事件格式

所有 9 种事件遵循统一的 JSON 结构：

```json
{
  "event_type": "formulation.ready",
  "negotiation_id": "neg_xxxxx",
  "timestamp": "2026-02-09T10:30:00Z",
  "data": {
    // 事件特定数据
  }
}
```

外层字段统一，`data` 字段因事件类型而异。具体每种事件的 `data` schema 在实施阶段定义并追加到本文档。

---

## 7. 模块接口模式

### 使用 Python Protocol 定义接口

```python
from typing import Protocol

class Encoder(Protocol):
    async def encode(self, text: str) -> Vector: ...
    async def batch_encode(self, texts: list[str]) -> list[Vector]: ...
```

### 接口放在模块的 base.py 或顶层

- `adapters/base.py` → `ProfileDataSource` Protocol
- `hdc/encoder.py` → `Encoder` Protocol（如果需要抽象）
- `skills/base.py` → `Skill` 基类

### 实现类遵循接口

- 实现类显式标注遵循的 Protocol
- 测试针对接口写，不针对实现写

---

## 8. 测试策略

### 目录结构

```
backend/tests/
├── core/
│   ├── test_engine.py
│   └── test_session.py
├── skills/
│   └── test_center.py
├── hdc/
│   └── test_encoder.py
└── conftest.py          # 共享 fixtures
```

### 测试原则

- **针对接口测**：测 Encoder 的行为，不测 SentenceTransformerEncoder 的内部
- **LLM 调用 mock**：测试中不真正调 LLM，mock 返回值测流程
- **状态机测核心路径**：正常流程、Agent 超时、Center 多轮、递归
- **事件测格式**：验证推送的事件符合统一 schema

---

## 9. 可复用代码清单

| 文件 | 复用方式 | 注意事项 |
|------|---------|---------|
| `websocket_manager.py` | 迁移到 `infra/`，直接使用 | 接口稳定，无需修改 |
| `database.py` | 迁移到 `infra/`，扩展新模型 | 保留现有模型，新增 NegotiationSession 等 |
| `oauth2_client.py` | 作为 `adapters/secondme.py` 的基础 | chat_stream() 是 SecondMe Adapter 的 LLM 调用通道 |

**不复用**：`app.py`（2600 行混杂）、`simulate_negotiation()`、`team_match_service.py`、`team_composition_engine.py`、`agent_manager.py`、`bridge_agent.py`

---

## 10. V1 工程决策

| 决策 | 结论 | 理由 |
|------|------|------|
| LLM 分界 | 端侧通过 Adapter；平台侧用 Claude API | 端侧计算原则 |
| 无自有 LLM 的用户 | 提供默认 LLM 通道 | 万能兜底 |
| 状态持久化 | 运行时内存为主，关键状态转换写数据库 | 性能 + 可恢复 |
| 代码复用 | 见上方清单 | — |
| V1 向量匹配 | 先用 embedding cosine similarity，不难则做 HDC | 快速验证 > 技术完美 |
| V1 执行阶段 | 跳过 WOWOK，只输出 plan 文本 | 先跑通协商闭环 |
| V1 Center 工具 | output_plan 必须；ask_agent、start_discovery 可选 | 增量复杂度 |

---

---

## 11. V1 实际实现决策（Phase 2 后补充）

| 决策 | 实际选择 | 理由 |
|------|---------|------|
| Embedding 模型 | `paraphrase-multilingual-MiniLM-L12-v2` (384 dim) | 多语言、速度快、维度合理 |
| 状态机 | 8 状态，所有非终态都可 → COMPLETED | 简洁 + 支持 cancel |
| Center Tool-Use | 5 工具 schema（output_plan 必须，其余 4 个可选） | 渐进复杂度 |
| API 端口 | 8081（独立于旧 app.py 的 8080） | 不改旧代码 |
| Python 兼容性 | asyncio.gather（不用 TaskGroup） | 兼容 Python 3.9+ |
| 前端路由 | `/negotiate`（旧版）+ `/negotiation`（新版） | 渐进迁移 |
| 环境变量前缀 | `TOWOW_` | 与旧系统隔离 |
| WebSocket channel | `negotiation:{id}` | 复用现有 WebSocketManager |

### 测试覆盖

| 层 | 文件 | 测试数 |
|----|------|--------|
| Core | test_models + test_events + test_engine | 51 |
| HDC | test_encoder + test_resonance | 31 |
| Adapters | test_claude + test_secondme | 14 |
| Skills | test_center + test_formulation + test_offer + test_sub_neg + test_gap | 43 |
| Infra | test_config + test_event_pusher + test_llm_client | 10 |
| API | test_routes | 17 |
| E2E | test_e2e | 6 |
| **Total** | | **172** |

### 前端组件

10 个协商 UI 组件 + TypeScript 类型定义 + WebSocket hook + REST API client:
- NegotiationPage, DemandInput, FormulationConfirm, ResonanceDisplay
- OfferCard, AgentPanel, CenterActivity, CenterPanel, EventTimeline, PlanResult

---

## 12. App Store API 契约

### 协商 API（已有）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/store/api/negotiate` | 发起协商 |
| GET | `/store/api/negotiate/{neg_id}` | 查询协商状态（内存 → DB fallback） |
| POST | `/store/api/negotiate/{neg_id}/confirm` | 确认 formulation |
| POST | `/store/api/assist-demand` | SecondMe 分身辅助需求（SSE） |
| GET | `/store/api/agents` | 网络中的 Agent 列表 |
| GET | `/store/api/scenes` | 场景列表 |
| GET | `/store/api/info` | 网络基本信息 |
| WS | `/store/ws/{neg_id}` | 协商事件推送 |

### 历史 API（ADR-007，2026-02-12 新增）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/store/api/history?scene_id=xxx` | 当前用户的协商历史列表（按时间倒序） | Cookie session |
| GET | `/store/api/history/{negotiation_id}` | 单次协商详情（含所有 Offer） | Cookie session + 归属校验 |

**History 列表响应 schema**:
```json
[{
  "negotiation_id": "neg_xxx",
  "user_id": "secondme_xxx",
  "scene_id": "hackathon",
  "demand_text": "用户原始输入",
  "demand_mode": "manual | surprise | polish",
  "assist_output": "分身生成的文本 | null",
  "formulated_text": "丰富化后的需求 | null",
  "status": "pending | negotiating | completed | failed | draft",
  "plan_output": "方案文本 | null",
  "agent_count": 5,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}]
```

**History 详情响应 schema**（在列表基础上增加）:
```json
{
  "...所有列表字段...",
  "plan_json": {},
  "center_rounds": 2,
  "scope": "scene:hackathon",
  "chain_ref": null,
  "offers": [{
    "agent_id": "agent_xxx",
    "agent_name": "Alice",
    "resonance_score": 0.85,
    "offer_text": "完整 Offer 内容",
    "confidence": 0.9,
    "agent_state": "offered | exited",
    "source": "SecondMe | Claude",
    "created_at": "ISO8601"
  }]
}
```

**持久化写入点**:
- `negotiate()` 创建时 → `save_negotiation(user_id=cookie_agent_id, status="pending")`
- `_run_negotiation()` 完成时 → `update_negotiation(status, plan_output, ...) + save_offers()`
- `assist_demand()` SSE 完成时 → `save_assist_output(user_id=cookie_agent_id, status="draft")`

---

## 更新日志

- 2026-02-09：初始版本，基于架构讨论确认的工程决策创建
- 2026-02-09：V1 Phase 2 完成后更新——实际代码结构、实现决策、测试覆盖
- 2026-02-12：新增 Section 12 — App Store API 契约 + 历史 API (ADR-007)
