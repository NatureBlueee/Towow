# PLAN-007: 用户历史数据持久化

**日期**: 2026-02-12
**关联**: ADR-007
**目标**: 用户刷新页面后能看到所有历史需求和协商结果

---

## 现状分析

### 已有的持久化

| 机制 | 位置 | 能力 | 缺陷 |
|------|------|------|------|
| JSON 文件 | `data/negotiations/{neg_id}.json` | 按 neg_id 恢复单个协商 | **无法按用户列出所有协商** |
| SQLite legacy | `backend/database.py` | User/Requirement/ChannelMessage | **未使用**，schema 与当前需求不匹配 |
| Redis/内存 | `backend/session_store.py` | Auth session | 不存业务数据 |

### 数据写入点（要插入持久化逻辑的地方）

| 事件 | 当前代码位置 | 写入什么 |
|------|------------|---------|
| 用户提交需求 | `routers.py:negotiate()` L488 | 需求文本 + scene + user_id |
| "通向惊喜"完成 | `routers.py:assist_demand()` L341 → SSE 完成 | 生成的文本 |
| 协商完成 | `routers.py:_run_negotiation()` L713 → `_persist_session()` L662 | 方案 + participants + offers |

### 前端数据恢复点

| 页面 | 当前行为 | 期望行为 |
|------|---------|---------|
| `/store/[scene]` | 刷新后空白，phase='idle' | 刷新后展示历史列表 |
| `/store/[scene]` | 无法回顾过去的协商 | 可点击历史条目查看详情 |

---

## 变更清单

### 后端（4 个文件）

#### 1. `backend/database.py` — 重写 schema

**契约变更？否**（内部实现，无外部消费方）

删除 legacy 的 User/Requirement/ChannelMessage 表，替换为：

```python
class NegotiationHistory(Base):
    __tablename__ = "negotiation_history"

    id = Column(Integer, primary_key=True)
    negotiation_id = Column(String(64), unique=True, index=True)
    user_id = Column(String(64), index=True)       # agent_id
    scene_id = Column(String(64), index=True)
    demand_text = Column(Text)                      # 用户原始输入
    demand_mode = Column(String(20))                # "manual" | "surprise" | "polish"
    assist_output = Column(Text, nullable=True)     # "通向惊喜"生成的文本
    formulated_text = Column(Text, nullable=True)   # 丰富化后的需求
    status = Column(String(20), default="pending")  # pending | negotiating | completed | failed
    plan_output = Column(Text, nullable=True)       # 方案文本
    plan_json = Column(JSON, nullable=True)         # 方案结构化数据
    center_rounds = Column(Integer, default=0)
    scope = Column(String(64), default="all")
    agent_count = Column(Integer, default=0)        # 参与 Agent 数
    chain_ref = Column(String(128), nullable=True)  # 关联 ADR-006
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class NegotiationOffer(Base):
    __tablename__ = "negotiation_offers"

    id = Column(Integer, primary_key=True)
    negotiation_id = Column(String(64), ForeignKey("negotiation_history.negotiation_id"), index=True)
    agent_id = Column(String(64))
    agent_name = Column(String(100))
    resonance_score = Column(Float, default=0.0)
    offer_text = Column(Text)                       # 完整 Offer 内容
    confidence = Column(Float, nullable=True)
    agent_state = Column(String(20))                # offered | exited
    source = Column(String(20), nullable=True)      # SecondMe | Claude | ...
    created_at = Column(DateTime, default=datetime.now)
```

同时提供 CRUD 函数：
- `save_negotiation(history: NegotiationHistory) -> None`
- `save_offers(negotiation_id: str, offers: list[NegotiationOffer]) -> None`
- `get_user_history(user_id: str, scene_id: str = None) -> list[NegotiationHistory]`
- `get_negotiation_detail(negotiation_id: str) -> tuple[NegotiationHistory, list[NegotiationOffer]]`
- `update_negotiation_status(negotiation_id: str, **kwargs) -> None`

**注意**：
- 保留 `get_engine()` / `get_session()` 基础设施代码，只换 schema
- DB 路径不变：`data/app.db`
- `Base.metadata.create_all()` 自动建表

#### 2. `apps/app_store/backend/routers.py` — 三个写入点

**契约变更？是** — 新增 2 个 API endpoint

**写入点 A：`negotiate()` L488** — 协商创建时

在 `state.store_sessions[neg_id] = session` 之后，立刻写入一条 `status="pending"` 的历史记录：

```python
from database import save_negotiation, NegotiationHistory

history = NegotiationHistory(
    negotiation_id=neg_id,
    user_id=req.user_id,
    scene_id=scene_id or "network",
    demand_text=req.intent,
    demand_mode="manual",
    status="pending",
    scope=req.scope,
    agent_count=len(candidate_ids),
)
save_negotiation(history)
```

**写入点 B：`_run_negotiation()` L713** — 协商完成时

替换现有的 `_persist_session()` JSON 文件写入，改为写 DB：

```python
from database import update_negotiation_status, save_offers, NegotiationOffer

# 更新主记录
update_negotiation_status(
    session.negotiation_id,
    status="completed",  # or "failed"
    formulated_text=session.demand.formulated_text,
    plan_output=session.plan_output,
    plan_json=session.plan_json,
    center_rounds=session.center_rounds,
)

# 保存每条 Offer
offers = []
for p in session.participants:
    offers.append(NegotiationOffer(
        negotiation_id=session.negotiation_id,
        agent_id=p.agent_id,
        agent_name=p.display_name,
        resonance_score=p.resonance_score,
        offer_text=p.offer.content if p.offer else "",
        confidence=getattr(p.offer, "confidence", None) if p.offer else None,
        agent_state=p.state.value,
        source=agent_registry.get_agent_info(p.agent_id).get("source", "") if agent_registry else "",
    ))
save_offers(session.negotiation_id, offers)
```

**写入点 C：`assist_demand()` L341** — "通向惊喜"完成时

在 SSE 流完成后（`_sse_generator` yield `[DONE]` 之前），把累积文本写入 DB：

```python
# 在 assist_demand 中：创建一条 demand_mode="surprise"|"polish" 的记录
# 或更新已有记录的 assist_output 字段
```

需要注意：assist_demand 是 SSE StreamingResponse，写入时机在 generator 结束后。用一个 wrapper 在 generator 完成时触发 DB 写入。

**新增 endpoint D：`GET /store/api/history`**

```python
@router.get("/api/history")
async def get_history(request: Request, scene_id: str = ""):
    agent_id = await _get_agent_id_from_session(request)
    if not agent_id:
        raise HTTPException(401, "需要登录")

    history = get_user_history(agent_id, scene_id or None)
    return [h.to_dict() for h in history]
```

**新增 endpoint E：`GET /store/api/history/{negotiation_id}`**

```python
@router.get("/api/history/{negotiation_id}")
async def get_history_detail(negotiation_id: str, request: Request):
    agent_id = await _get_agent_id_from_session(request)
    if not agent_id:
        raise HTTPException(401, "需要登录")

    history, offers = get_negotiation_detail(negotiation_id)
    if not history or history.user_id != agent_id:
        raise HTTPException(404, "协商记录不存在")

    result = history.to_dict()
    result["offers"] = [o.to_dict() for o in offers]
    return result
```

#### 3. `backend/server.py` — DB 初始化

在 lifespan 中初始化数据库：

```python
from database import get_engine

# 在 lifespan 开头
get_engine()  # 自动创建表
```

#### 4. 清理：`_persist_session` / `_load_persisted_session`

DB 就绪后，这两个函数和 `_NEG_DATA_DIR` 可以删除。`get_negotiation()` endpoint 改为从 DB 读取（内存 miss → DB 查询，替代 JSON 文件加载）。

---

### 前端（3 个文件）

#### 5. `website/lib/store-api.ts` — 新增 API 调用

**契约变更？是** — 消费新增的 2 个 API

```typescript
export interface HistoryItem {
  negotiation_id: string;
  scene_id: string;
  demand_text: string;
  demand_mode: string;
  assist_output: string | null;
  status: string;
  plan_output: string | null;
  agent_count: number;
  created_at: string;
}

export interface HistoryDetail extends HistoryItem {
  formulated_text: string | null;
  plan_json: Record<string, unknown> | null;
  center_rounds: number;
  offers: OfferDetail[];
}

export interface OfferDetail {
  agent_id: string;
  agent_name: string;
  resonance_score: number;
  offer_text: string;
  confidence: number | null;
  agent_state: string;
}

export function getHistory(sceneId?: string): Promise<HistoryItem[]> { ... }
export function getHistoryDetail(negId: string): Promise<HistoryDetail> { ... }
```

#### 6. `website/components/store/HistoryPanel.tsx` — 新增组件

历史面板组件，展示在场景页侧边或下方：
- 按时间倒序展示所有历史条目
- 每条显示：需求文本（截断）、状态、时间、Agent 数
- 点击展开详情（含 Offer 列表）
- 当前正在进行的协商在最上方高亮

#### 7. `website/app/store/[scene]/page.tsx` 或对应页面组件

页面加载时调用 `getHistory(sceneId)` 填充历史面板。

---

## 变更链路追踪

### 链路 1：协商结果持久化

```
用户提交需求
  → routers.py:negotiate()
    → save_negotiation(status="pending")  ← 新增
  → _run_negotiation() 完成
    → update_negotiation_status(status="completed") + save_offers()  ← 替代 _persist_session()
```

```
□ 契约还是实现？ — 实现变更（DB 写入替代 JSON 文件，外部 API 不变）
□ 数据流通验证：negotiate() 有 user_id（从 request body）→ 写入 DB → history API 按 user_id 查询 ✓
□ 降级路径：DB 写入失败不应阻塞协商流程 → try/except + 日志告警
```

### 链路 2：assist-demand 结果持久化

```
用户点"通向惊喜"
  → routers.py:assist_demand() → SSE stream
    → stream 完成后 save_negotiation(demand_mode="surprise", assist_output=累积文本)  ← 新增
```

```
□ 契约还是实现？ — 实现变更（原有 SSE 契约不变，只是多了后置写入）
□ 数据流通验证：agent_id 从 Cookie session 获取 → 写入 DB ✓
□ 注意：assist_demand 的 user_id 来自 Cookie（不同于 negotiate 的 request body）
         → history API 也用 Cookie session 读 agent_id，所以一致 ✓
```

### 链路 3：前端历史加载

```
用户打开/刷新 /store/[scene]
  → page 组件 useEffect
    → getHistory(sceneId)
      → GET /store/api/history?scene_id=xxx
        → DB 查询 → 返回列表
  → 渲染 HistoryPanel
  → 点击某条
    → getHistoryDetail(negId)
      → GET /store/api/history/{negId}
        → DB 查询 → 返回详情 + Offers
```

```
□ 契约变更？ — 是（新增 2 个 API endpoint）
□ 消费方：仅前端 HistoryPanel，新增组件，无其他消费方
□ 降级路径：API 失败 → HistoryPanel 显示"暂无历史" → 不影响主流程
```

### 链路 4：`get_negotiation()` 恢复路径变更

```
前端轮询 GET /store/api/negotiate/{neg_id}
  → 当前：内存 miss → JSON 文件加载
  → 改为：内存 miss → DB 查询
```

```
□ 契约变更？ — 否（API 响应 schema 不变）
□ 消费方：前端 useStoreNegotiation 的轮询逻辑，不需要改
```

---

## 消费方验证

| 新增/变更 | 消费方 | 方案中有对应条目？ |
|----------|--------|-----------------|
| `GET /store/api/history` | 前端 HistoryPanel (新增) | ✓ store-api.ts + HistoryPanel.tsx |
| `GET /store/api/history/{neg_id}` | 前端 HistoryPanel (新增) | ✓ store-api.ts + HistoryPanel.tsx |
| DB 写入 (negotiate) | 无外部消费方 | — |
| DB 写入 (assist_demand) | 无外部消费方 | — |
| `get_negotiation()` 改用 DB | 前端轮询 (已有) | ✓ 响应 schema 不变，无需改前端 |
| 删除 `_persist_session` JSON | `_load_persisted_session` | ✓ 同步删除，改用 DB |

---

## 测试策略

| 测试 | 类型 | 覆盖 |
|------|------|------|
| `test_database.py` | 单元测试 | schema 建表 + CRUD 函数 |
| `test_history_api.py` | API 测试 | history 列表 + 详情 + 权限（只能看自己的） |
| `test_negotiation_persistence.py` | 集成测试 | negotiate → DB 写入 → history API 读取 |

---

## 实施顺序

```
Step 1: backend/database.py — 新 schema + CRUD（独立可测）
Step 2: backend/server.py — DB 初始化
Step 3: routers.py — negotiate() 写入 + _run_negotiation() 写入（替代 JSON）
Step 4: routers.py — assist_demand() 写入
Step 5: routers.py — 新增 history API endpoints
Step 6: 清理 _persist_session / _load_persisted_session / _NEG_DATA_DIR
Step 7: website/lib/store-api.ts — 新增 API 函数
Step 8: website/components/store/HistoryPanel.tsx — 新增组件
Step 9: 页面集成 HistoryPanel
Step 10: 测试
```

Step 1-6 纯后端，Step 7-9 纯前端，可以串行做也可以后端完成后前端跟上。

---

## Skill 调度

| Step | 文件 | Skill |
|------|------|-------|
| 1-6 | backend/ | `towow-dev` |
| 7-9 | website/ | `towow-dev` + `towow-eng-frontend` |
| 10 | tests/ | `towow-dev` |
