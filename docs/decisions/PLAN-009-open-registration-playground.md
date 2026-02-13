# PLAN-009: 开放注册 + Playground 实现方案

**关联**: ADR-009
**阶段**: ③ 接口设计 + ④ 实现方案（合并）
**修订**: v2 (2026-02-13) — 修复 3 个盲区，新增行为消费方验证

---

## 1. 接口设计（阶段 ③）

### 1.1 `POST /store/api/quick-register` — 开放注册

**语义**: 用户提交联络信息 + 任意文本，创建一个 Agent 并注册到网络。

| | 定义 |
|---|------|
| **输入** | `email: string` — 邮箱（email 和 phone 至少一个） |
| | `phone: string` — 手机号（可选） |
| | `display_name: string` — 显示名 |
| | `raw_text: string` — 任意文本（简历、自我介绍等） |
| | `subscribe: bool` — 是否订阅动态（默认 false） |
| | `scene_id: string` — 注册到哪个场景（可选，空则注册到所有已有场景） |
| **输出** | `agent_id: string` — 新创建的 Agent ID |
| | `display_name: string` |
| | `message: string` — 人类可读的确认信息 |
| **状态变化** | ① DB 写入 User 记录（永久） |
| | ② AgentRegistry 注册，adapter=default_adapter（内存） |
| | ③ Encoder.encode() 生成向量（内存） |
| | ④ 可立即参与后续协商的共振匹配 **和 Offer 生成** |
| **错误** | email/phone 都为空 → 400 |
| | raw_text 为空 → 400 |
| | email 已注册 → 409（返回已有 agent_id） |

**关键设计**：
- `raw_text` 不做 LLM 结构化，直接存储
- 向量化用 `Encoder.encode(raw_text)` 直接编码
- **`adapter=registry.default_adapter`**（用平台默认 ClaudeAdapter，不是 None）
  - 区别于 SecondMe 恢复用户的 adapter=None（见附录 A 根因分析）
- `source="playground"` 标识来源
- `scene_ids` 为空时，注册到所有已有场景（确保网络可见性）

### 1.2 前端 `/playground` 页面

**语义**: 零门槛体验通爻网络。

**用户流程**:
```
1. 填写：邮箱 + 显示名 + 勾选订阅
2. 粘贴：任意文本到大文本框
3. 选择场景（下拉，可选）
4. 点击"加入网络"
5. 看到确认：你的 Agent 已创建，agent_id 存入 localStorage
6. 出现需求输入框 → 填写需求 → 发起协商
7. 协商进度 + 结果展示（复用现有 NegotiationProgress 组件）
```

---

## 2. 变更链路（阶段 ④）

### 改动清单

| # | 文件 | 类型 | 改什么 | Skill |
|---|------|------|--------|-------|
| 1 | `backend/database.py` | 契约（DB schema） | User 表加字段 + 3 个 CRUD 函数 | `towow-dev` |
| 2 | `backend/towow/infra/agent_registry.py` | 实现 | `get_agent_info()` 提取字段列表加 `raw_text` | `towow-dev` |
| 3 | `apps/app_store/backend/routers.py` | 契约（API）+ 实现 | `POST /api/quick-register` + `_build_agent_summaries()` bio fallback | `towow-dev` |
| 4 | `backend/server.py` | 实现 | `_restore_playground_users()` + `_encode` 文本提取 fallback | `towow-dev` |
| 5 | curl 测试 | 验证 | 后端链路（注册 → AgentRegistry → 向量 → 协商） | — |
| 6 | `website/app/playground/page.tsx` | 新增 | Playground 页面（注册 + 协商一体） | `ui-ux-pro-max` |
| 7 | 端到端 + 重启验证 | 验证 | 注册 → 协商 → 重启 → 仍可见 | — |

### 不改的

| 模块 | 为什么不改 |
|------|-----------|
| AgentRegistry `register_agent()` | 现有接口完全够用 |
| Encoder | 现有 `encode(text: str)` 完全够用 |
| 协议层（engine, skills, models） | 不关心 Agent 来源 |
| App Store 现有页面 | SecondMe 登录流程保持不变 |
| `next.config.ts` | rewrite 已有 `/store/api/:path*`，新端点自动覆盖 |
| `website/app/store/api/[...path]/route.ts` | catch-all 代理已支持 POST 转发（需确认已提交 git） |

---

## 3. 每条变更的详细设计

### 3.1 database.py — User 表扩展

**新增字段**（所有 nullable，不影响现有 SecondMe 用户）：

```python
email = Column(String(256), nullable=True, unique=True, index=True)
phone = Column(String(32), nullable=True)
subscribe = Column(Boolean, default=False)
raw_profile_text = Column(Text, nullable=True)        # 原始粘贴文本
source = Column(String(32), default="secondme")       # secondme | playground | mcp
```

**新增函数**：

```python
def get_user_by_email(email: str) -> Optional[User]:
    """通过邮箱查找用户（quick-register 去重用）。"""

def create_playground_user(
    agent_id: str,
    display_name: str,
    email: str = None,
    phone: str = None,
    subscribe: bool = False,
    raw_profile_text: str = "",
) -> User:
    """创建 Playground 来源的用户。source="playground"。"""

def get_playground_users() -> List[User]:
    """获取所有 Playground 用户（启动时恢复用）。"""
```

**email unique 约束**：SQLite 允许多个 NULL unique，现有 SecondMe 用户 email=NULL 不冲突。

### 3.2 agent_registry.py — `get_agent_info()` 提取 `raw_text`

**当前**（第 223 行）：
```python
for key in ("skills", "bio", "role", "self_introduction", "interests",
             "experience", "shades", "memories"):
```

**改为**：
```python
for key in ("skills", "bio", "role", "self_introduction", "interests",
             "experience", "shades", "memories", "raw_text"):
```

这让 `_build_agent_summaries()` 和 `list_agents` 能看到 playground 用户的内容。

### 3.3 routers.py — `POST /api/quick-register` + bio fallback

**请求模型**：
```python
class QuickRegisterRequest(BaseModel):
    email: str = ""
    phone: str = ""
    display_name: str
    raw_text: str
    subscribe: bool = False
    scene_id: str = ""
```

**实现伪码**：
```python
@router.post("/api/quick-register")
async def quick_register(req: QuickRegisterRequest, request: Request):
    # 1. 验证
    if not req.email and not req.phone:
        raise HTTPException(400, "请提供邮箱或手机号")
    if not req.raw_text.strip():
        raise HTTPException(400, "请输入你的介绍内容")

    # 2. 邮箱去重（应用层快速检查）
    if req.email:
        existing = get_user_by_email(req.email)
        if existing:
            return JSONResponse(status_code=409, content={
                "error": "该邮箱已注册",
                "agent_id": existing.agent_id,
                "display_name": existing.display_name,
            })

    # 3. 生成 agent_id
    agent_id = generate_id("pg")  # pg = playground

    # 4. DB 持久化（catch IntegrityError 处理并发竞态）
    try:
        create_playground_user(
            agent_id=agent_id,
            display_name=req.display_name,
            email=req.email or None,
            phone=req.phone or None,
            subscribe=req.subscribe,
            raw_profile_text=req.raw_text,
        )
    except IntegrityError:
        # 并发竞态：两个请求同时通过了 get_user_by_email 检查
        existing = get_user_by_email(req.email)
        if existing:
            return JSONResponse(status_code=409, content={
                "error": "该邮箱已注册",
                "agent_id": existing.agent_id,
                "display_name": existing.display_name,
            })
        raise  # 非邮箱冲突的 IntegrityError，透传

    # 5. AgentRegistry 注册
    #    ⚠️ 用 default_adapter（ClaudeAdapter），不是 None
    #    原因：adapter=None 会导致 chat() 抛 AdapterError，
    #    该 Agent 永远无法生成 Offer（见附录 A）
    state = request.app.state
    registry = state.agent_registry

    # scene_ids：有指定则用指定，否则注册到所有已有场景
    if req.scene_id:
        scene_ids = [req.scene_id]
    else:
        scene_ids = [s["scene_id"] for s in state.store_scene_registry.list_scenes()]

    profile_data = {
        "raw_text": req.raw_text,
        "display_name": req.display_name,
        "source": "playground",
    }
    registry.register_agent(
        agent_id=agent_id,
        adapter=registry.default_adapter,  # ← 关键：不是 None
        source="playground",
        scene_ids=scene_ids,
        display_name=req.display_name,
        profile_data=profile_data,
    )

    # 6. 实时向量编码
    encoder = state.encoder
    if encoder:
        try:
            vec = await encoder.encode(req.raw_text)
            state.store_agent_vectors[agent_id] = vec
        except Exception as e:
            logger.warning("quick-register: 向量编码失败 %s: %s", agent_id, e)

    return {
        "agent_id": agent_id,
        "display_name": req.display_name,
        "message": f"你的 Agent 已创建，可以参与协商了",
    }
```

**`_build_agent_summaries()` bio fallback**（第 228 行）：

```python
# FROM:
bio = info.get("bio", "") or info.get("self_introduction", "")
# TO:
bio = info.get("bio", "") or info.get("self_introduction", "") or (info.get("raw_text", "") or "")[:100]
```

### 3.4 server.py — `_restore_playground_users()` + encode fallback

**位置**：在 `_init_app_store()` 末尾，`_restore_secondme_users()` 之后调用。

**逻辑**：
```python
def _restore_playground_users(registry) -> None:
    """启动时从 DB 恢复 Playground 用户到 AgentRegistry。

    与 _restore_secondme_users() 的关键区别：
    - SecondMe 恢复: adapter=None（token 过期，chat 不可用）
    - Playground 恢复: adapter=default_adapter（用平台 Claude，Offer 可用）
    """
    from database import get_playground_users

    users = get_playground_users()
    default_adapter = registry.default_adapter
    all_scene_ids = []  # 将在调用处传入

    for user in users:
        if user.agent_id in registry.all_agent_ids:
            continue
        profile_data = {
            "raw_text": user.raw_profile_text or "",
            "display_name": user.display_name,
            "source": "playground",
        }
        registry.register_agent(
            agent_id=user.agent_id,
            adapter=default_adapter,  # ← 关键：不是 None
            source="playground",
            scene_ids=list(all_scene_ids),
            display_name=user.display_name,
            profile_data=profile_data,
        )
    if users:
        logger.info("恢复 %d 个 Playground 用户 (adapter=%s)",
                     len(users), type(default_adapter).__name__ if default_adapter else "None")
```

**`_encode_store_agent_vectors()` 文本提取兼容**（432-443 行之后加）：

```python
# 现有字段提取之后，加 raw_text fallback：
if not text_parts:
    raw_text = profile.get("raw_text", "")
    if raw_text:
        text_parts.append(raw_text[:500])
```

### 3.5 前端 `/playground` 页面

**一个自包含页面**，内部两个状态：

**状态 A — 未注册**：
- 邮箱输入框
- 显示名输入框
- 文本粘贴大框（textarea，10 行高）
- 场景选择下拉（调用 `GET /store/api/scenes`，可选）
- 订阅 checkbox
- "加入网络" 按钮
- 调用 `POST /store/api/quick-register`
- 成功后 → `localStorage.setItem("playground_agent_id", agent_id)` → 切换到状态 B

**状态 B — 已注册，可协商**：
- 显示"你的 Agent: {display_name}"
- 需求输入框
- 场景选择（调用 `GET /store/api/scenes` 获取列表）
- "发起协商" 按钮
- 调用 `POST /store/api/negotiate`，`user_id` = localStorage 中的 `agent_id`
- 协商进度展示（复用 NegotiationProgress 组件 或简化版）

**页面加载时**：检查 `localStorage.playground_agent_id`，如有且服务端确认存在 → 直接进入状态 B。

---

## 4. 变更链路追踪清单

### 链路 1: 注册
```
前端 → POST /store/api/quick-register
  → 验证 email/phone + raw_text
  → DB: get_user_by_email() 去重（应用层快速检查）
  → DB: create_playground_user() 写入（catch IntegrityError 处理竞态）
  → AgentRegistry.register_agent(
      adapter=registry.default_adapter,  ← 不是 None
      source="playground",
      scene_ids=[所有已有场景],
      profile_data={"raw_text": ...}
    )
  → Encoder.encode(raw_text) → store_agent_vectors[agent_id]
  → 返回 agent_id
```

### 链路 2: Playground Agent 作为候选方参与他人协商
```
他人提交需求 → POST /store/api/negotiate
  → ResonanceDetector 匹配 store_agent_vectors
  → Playground Agent 被激活（有向量 + 在场景 scope 内）
  → Offer 生成：
      → AgentRegistry.get_profile(pg_agent_id) → {"raw_text": "...", ...}
      → AgentRegistry.chat(pg_agent_id) → default_adapter.chat() → Claude 生成 offer
         ✓ 不会抛 AdapterError（adapter 不是 None）
  → Plan 输出（Playground Agent 的 offer 参与 Center 综合）
```

### 链路 3: Playground 用户自己发起协商
```
前端 → POST /store/api/negotiate { intent, user_id=pg_agent_id, scope="scene:xxx" }
  → negotiate handler: persist_user_id = _get_agent_id_from_session() || req.user_id
     → 无 cookie → fallback 到 req.user_id (= pg_agent_id) ✓
  → 正常协商流程（其他 Agent 作为候选方）
```

### 链路 4: 服务器重启后恢复
```
lifespan 启动
  → _restore_secondme_users(registry)  — 现有，adapter=None
  → _restore_playground_users(registry) — 新增，adapter=default_adapter
  → _encode_store_agent_vectors()       — 现有 + raw_text fallback
  → Playground 用户重新在内存中可用，且能生成 Offer
```

### 降级路径
| 场景 | 行为 |
|------|------|
| Encoder 不可用 | 注册成功，无向量，不参与共振（日志 warning） |
| default_adapter 不可用 | 注册成功但 offer 生成失败 → EXITED（与 JSON 样板间行为一致） |
| DB 写入失败 | 返回 500（不降级——联络信息必须持久化） |
| DB 并发竞态 | IntegrityError → 返回 409 + 已有 agent_id |
| 重启时 DB 读取失败 | 日志 warning，Playground 用户暂不可用 |

---

## 5. 消费方验证清单

### 5.1 数据消费方（读 Agent 数据）

| 消费方 | 是否在 scope 内 | 处理 |
|--------|----------------|------|
| `get_agent_info()` | 在 scope（改动 #2） | 提取字段加 `raw_text` |
| `_build_agent_summaries()` | 在 scope（改动 #3） | bio fallback 到 `raw_text[:100]` |
| `_encode_store_agent_vectors()` | 在 scope（改动 #4） | 文本提取加 `raw_text` fallback |
| `list_agents` API | 自动覆盖 | `get_agent_info()` 改后自动生效 |
| `get_profile()` | 不需改 | `adapter!=None` → 用 adapter；adapter 是 ClaudeAdapter → 返回 `{"agent_id": id}`，再 fallback 到 `profile_data` (agent_registry.py:285-286) |

### 5.2 行为消费方（调用 Agent 能力）

| 消费方 | Agent 能力需求 | Playground Agent 是否满足 |
|--------|--------------|--------------------------|
| Offer 生成 (`offer.py:103`) | `adapter.chat()` | ✓ adapter=default_adapter，Claude 生成 |
| assist-demand (`routers.py:404`) | `adapter.chat_stream()` | N/A — assist-demand 要求 SecondMe 用户，playground 用户不走此路径 |
| negotiate (demand submit) | 无 — demand owner 不需要 chat | ✓ |

### 5.3 可见性消费方（scope 查询）

| 查询 | Playground Agent 是否可见 | 原因 |
|------|--------------------------|------|
| `get_agents_by_scope("all")` | ✓ | 所有 Agent 都在 |
| `get_agents_by_scope("scene:hackathon")` | ✓ | 注册时加入所有已有场景 |
| `/api/history` | ✗ — 不在 scope | 需要 session cookie，V1 不支持（可接受） |

---

## 6. 实现顺序

```
Step 1: database.py — User 表加字段 + 新增 CRUD 函数
Step 2: agent_registry.py — get_agent_info() 提取字段加 raw_text
Step 3: routers.py — _build_agent_summaries() bio fallback + POST /api/quick-register
Step 4: server.py — _restore_playground_users() + _encode 文本提取 fallback
Step 5: curl 测试后端链路（注册 → 确认 AgentRegistry → 确认向量 → 发起协商 → 确认 Offer 生成）
Step 6: playground/page.tsx — 前端页面
Step 7: 端到端验证（注册 → 协商 → 看到 Playground Agent 参与 + 生成 Offer）
Step 8: 重启验证（重启服务器 → Playground 用户仍在网络中 → 仍能生成 Offer）
```

---

## 7. 关键约束

1. **adapter=default_adapter**：Playground 用户用平台默认 ClaudeAdapter，不是 None（见附录 A）
2. **邮箱唯一性**：`email` 字段 `unique=True`，应用层去重 + DB 约束兜底（IntegrityError → 409）
3. **向量实时编码**：注册时立即 encode，不等 startup
4. **scene_ids 默认全量**：未指定场景时注册到所有已有场景，确保网络可见性
5. **profile_data 格式**：`{"raw_text": "...", "source": "playground", "display_name": "..."}`
6. **重启恢复**：`_restore_playground_users()` 用 default_adapter 恢复，不是 None
7. **History 不可用**：Playground 用户 V1 无 session cookie，看不了历史（后续扩展）
8. **前端 agent_id 存储**：`localStorage.playground_agent_id`，页面加载时恢复

---

## 附录 A：盲区根因分析

### 发现的盲区

| # | 盲区 | 严重度 | 修复 |
|---|------|--------|------|
| 1 | `adapter=None` → Agent 无法生成 Offer | 关键 | 改为 `registry.default_adapter` |
| 2 | 并发邮箱注册竞态 → 500 | 中等 | catch IntegrityError → 409 |
| 3 | 空 scene_ids → 场景协商中不可见 | 中等 | 默认注册到所有已有场景 |

### 共同的元模式

三个盲区共享同一个思维模式错误：

> **计划从"生产者"视角设计（注册用户），没有从"消费者"视角验证（网络如何使用这个 Agent）。**

"加入网络"是**双向契约**——用户加入网络，网络也承诺这个 Agent 是完整的参与者。计划只验证了用户侧（注册成功），没验证网络侧（参与完整性）。

### 逐个根因

**盲区 #1：同一语法 ≠ 同一语义**

`adapter=None` 在 SecondMe 恢复和 Playground 注册中含义完全不同：
- SecondMe 恢复：`adapter=None` = "你的专用 adapter 不可用了"（正确——应阻止 chat）
- Playground 注册：`adapter=None` = "你从来没有专用 adapter"（错误——应用默认 adapter）

计划复用了 `_restore_secondme_users()` 的模式，没有验证原模式的语义意图是否适用。

**盲区 #3：Optional 便利 vs 系统承诺**

`scene_id` 设为 optional 是给用户的便利（不强制选场景），但没有追问："不选场景时，agent 在网络中的可见性如何？"

### 新增验证维度（沉淀为流程改进）

原有的消费方验证只覆盖了"数据消费方"（谁在读数据）。新增两个维度：

| 验证维度 | 问什么 | 本次遗漏的例子 |
|----------|--------|---------------|
| **数据消费** | "能看到这个 Agent 的数据吗？" | — （已验证） |
| **行为消费** | "能调用这个 Agent 的能力吗？" | Offer 生成需要 chat()，adapter=None 必失败 |
| **可见性消费** | "在所有 scope 下都能找到这个 Agent 吗？" | 空 scene_ids → 场景查询不可见 |

### 教训

> **"接口接受" ≠ "语义完整"**：`register_agent()` 接受 `adapter=None` 不意味着网络会把这个 Agent 当成完整公民。验证公民权，不只验证注册。
>
> **复用模式必须验证语义**：同一行代码（`adapter=None`）在不同上下文中可能意味着完全不同的事。复用时必须问"原模式为什么这样？新场景的原因一样吗？"
>
> **Optional 字段需要缺席追踪**：每个 optional 字段为空时，沿所有下游消费方追问行为。Optional 是调用方的便利，不是系统的承诺。
