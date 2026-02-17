# Issue 006: Railway 部署后 Offer 生成全军超时

**日期**: 2026-02-13
**严重度**: 致命（协商流程完全不可用）
**影响范围**: App Store 协商 (`POST /store/api/negotiate`)
**环境**: Railway 生产部署（Docker + Python 3.12 + FastAPI）
**本地测试**: 250 测试全部通过，逻辑正确

## 症状

1. 用户提交需求 → 共振检测正常（9-15 个 Agent 被激活）
2. Offer 生成阶段 → **全部 Agent 超时（30s）**，无一成功
3. Center 综合以 0 个 Offer 运行 → 输出"暂无足够信息"
4. Railway 日志中 **看不到 `LLM call START`**（后来发现是日志级别问题，见下文）

典型日志：
```
WARNING  Agent agent_hackathon_001 timed out during offer generation (30s). adapter=AgentRegistry, offer_skill=OfferGenerationSkill
WARNING  Agent agent_hackathon_002 timed out during offer generation (30s). adapter=AgentRegistry, offer_skill=OfferGenerationSkill
... (所有 Agent 都超时)
WARNING  synthesis START: 0 participants, 0 offers, 0 exited, llm=ClaudePlatformClient
```

## 调用链路

Offer 生成的完整调用链：

```
engine._run_offers()                          # 并行启动，每个 Agent 30s 超时
  └→ offer_skill.execute(context)             # OfferGenerationSkill
       └→ adapter.chat(agent_id, messages)    # AgentRegistry (composite)
            └→ entry.adapter.chat(...)        # JSONFileAdapter (template agents)
                 └→ self._llm_client.chat()   # ClaudePlatformClient → Anthropic API
```

**断裂点未确定**——不知道链路在哪一环卡住。

## 背景时间线

| 时间 | 事件 |
|------|------|
| 之前 | 通过 packyapi 代理（5 个代理 key + base_url）工作正常 |
| 2026-02-12 | packyapi 代理返回 424 "no Claude account is available" |
| 同日 | 添加 424/5xx 重试逻辑 (commit 9217ae6) |
| 同日 | 用户切换到直接 Anthropic key (`sk-ant-api03-...`) |
| 同日 | 删除 Railway 环境变量 `TOWOW_ANTHROPIC_API_KEYS` 和 `TOWOW_ANTHROPIC_BASE_URL` |
| 同日 | 新增 `TOWOW_ANTHROPIC_API_KEY`（单 key，直连 Anthropic） |
| 切换后 | **所有 Agent 超时，无 LLM 日志可见** |

## 调查过程

### 1. 已排除的原因

| 假设 | 排除依据 |
|------|---------|
| 代码逻辑错误 | 250 测试通过，本地 mock 环境 Offer 流程正常 |
| API Key 无效 | 用户确认 Anthropic 额度充足 |
| `.env` 污染 Docker | `backend/.env` 在 `.gitignore` 中，不会进入 Docker 镜像 |
| `.env` 被 `load_dotenv()` 加载覆盖 | Docker 容器内无 `.env` 文件，`load_dotenv()` 无操作 |

### 2. 发现：日志级别盲区

**关键发现**：Railway 默认只显示 WARNING+ 级别日志。以下信息全部是 INFO 级别，在 Railway **完全不可见**：

- `LLM call START | key[0]...xxxx | model=xxx` — 是否发起了 LLM 调用
- `LLM call OK | ... | 3200ms` — LLM 调用是否成功
- `Store: ClaudePlatformClient initialized (1 key(s), base_url=default)` — 启动时加载了什么配置

这意味着：**我们根本不知道 LLM 调用是否真的发出了**。30s 超时可能是：
- (a) LLM 调用发出但目标 endpoint 无响应（网络/base_url 错误）
- (b) LLM 调用发出但 API key 无效导致长时间重试
- (c) LLM 调用根本没发出（`llm_client` 是 `None` 或 `MockLLMClient`）
- (d) 链路中某一环卡住了（如 `adapter.get_profile()` 异常阻塞）

### 3. 不确定事项（诊断日志部署后可确认）

| 问题 | 重要性 | 确认方式 |
|------|--------|---------|
| `store_llm_client` 类型是什么？ | 致命 | 启动日志 `Store LLM config:` |
| API key 实际加载了哪个？ | 致命 | 启动日志 key 后 4 位 |
| `base_url` 是 `api.anthropic.com` 还是 `packyapi.com`？ | 致命 | 启动日志 |
| `JSONFileAdapter._llm_client` 是什么类型？ | 高 | `JSONFileAdapter.chat:` 日志 |
| LLM HTTP 请求是否真的发出？ | 高 | `LLM call START` 日志 |
| 请求发出后多久超时？ | 中 | `LLM call OK/FAIL` 日志 |

### 4. 可能的根因场景

#### 场景 A：环境变量未正确切换（概率高）

`TowowConfig` 的 key 优先级：
```python
# config.py
def get_api_keys(self) -> list[str]:
    if self.anthropic_api_keys:       # ← 复数优先
        return [k.strip() for k in self.anthropic_api_keys.split(",")]
    if self.anthropic_api_key:        # ← 单数 fallback
        return [self.anthropic_api_key]
    return []
```

风险点：
- 如果 `TOWOW_ANTHROPIC_API_KEYS`（复数）在 Railway 中仍存在（即使为空字符串），`pydantic-settings` 会读取到空字符串 `""`，`bool("")` 为 `False` 所以会 fallback——但如果值是空格或换行符，行为不确定
- 如果 `TOWOW_ANTHROPIC_BASE_URL` 仍存在且值为 `https://www.packyapi.com`，所有请求仍会发往代理

#### 场景 B：MockLLMClient 被加载（概率中）

```python
# server.py _init_app_store()
if store_keys:
    llm_client = ClaudePlatformClient(api_key=store_keys, base_url=base_url)
else:
    llm_client = MockLLMClient()  # ← 硬编码模板，不调用 API
```

如果 `store_keys` 为空（因为环境变量问题），会 fallback 到 `MockLLMClient`。但 `MockLLMClient` 应该**立即返回**而非超时——除非 `MockLLMClient.chat()` 的返回格式不符合 `JSONFileAdapter` 的期望导致异常，而异常又被 `asyncio.wait_for` 的 timeout 吃掉了。

需要检查：`MockLLMClient.chat()` 的返回值是否兼容 `JSONFileAdapter.chat()` 中的 `result.get("content", "")` 调用。

#### 场景 C：Anthropic API 直连但网络不通（概率低）

Railway 容器到 `api.anthropic.com` 的 HTTPS 连接被防火墙或 DNS 阻断。不太可能但需要排除。

#### 场景 D：并发限制导致信号量饥饿（概率低）

`ClaudePlatformClient` 有 `asyncio.Semaphore(concurrency)` 控制。默认 `10 per key`，单 key = 10 并发。9 个 Agent 并行不应超过限制。但如果有其他请求占用了信号量……

## 已提交的修复

### commit 9217ae6 — 424/5xx 重试
- `ClaudePlatformClient`: 424/429/500/502/503/529 自动重试
- `ClaudeAdapter`: 同上

### commit 6d9faec — 启动诊断日志
- `server.py`: 启动时 WARNING 级别显示 key 配置和 source

### commit 8245496 — LLM 调用日志提升
- `llm_client.py`: `LLM call START/OK` 从 INFO→WARNING
- `json_adapter.py`: `chat()` 入口加 WARNING 日志（确认 llm_client 类型）
- `server.py`: `load_dotenv(override=False)` 防御性改进
- `.dockerignore`: 排除 `.env` 等敏感文件

## 验证步骤（部署 8245496 后）

### Step 1：检查启动日志

在 Railway logs 中搜索 `Store LLM config:`，确认：

```
Store LLM config: keys=['...xxxx'], base_url=api.anthropic.com (default), source=TOWOW_ANTHROPIC_API_KEY
```

- `keys` 应显示你的 Anthropic key 的后 4 位
- `base_url` 应为 `api.anthropic.com (default)`（不是 `packyapi.com`）
- `source` 应为 `TOWOW_ANTHROPIC_API_KEY`（单数）

**如果 `keys=['NONE']`**：环境变量未设置。
**如果 `base_url=https://www.packyapi.com`**：旧代理变量未删除。
**如果 `source=TOWOW_ANTHROPIC_API_KEYS`**：复数变量仍存在。

### Step 2：尝试协商，看日志

提交一次需求，在日志中搜索：

1. `JSONFileAdapter.chat:` — 确认 `llm_client` 类型
2. `LLM call START` — 确认 LLM 调用是否发出
3. `LLM call OK` 或 `LLM call FAIL` — 确认结果

### Step 3：根据日志判断

| 日志 | 结论 | 下一步 |
|------|------|--------|
| `llm_client=None` | key 未加载 | 检查 Railway 环境变量 |
| `llm_client=MockLLMClient` | key 未加载 | 检查 Railway 环境变量 |
| `llm_client=ClaudePlatformClient` + 无 `LLM call START` | 调用前卡住 | 检查 `offer_skill.execute` 逻辑 |
| `LLM call START` 出现 + 无 `OK/FAIL` | HTTP 请求发出但无响应 | base_url 错误或网络问题 |
| `LLM call START` + `FAIL` | API 返回错误 | 看具体错误码 |
| `LLM call START` + `OK` 但 offer 仍超时 | 返回值解析问题 | 检查 JSONFileAdapter 返回值处理 |

## Railway 环境变量检查清单

**必须存在**：
- `TOWOW_ANTHROPIC_API_KEY` = `sk-ant-api03-7Uixi4...`

**必须不存在**（删除，不是设为空）：
- `TOWOW_ANTHROPIC_API_KEYS`
- `TOWOW_ANTHROPIC_BASE_URL`

## 相关文件

| 文件 | 作用 |
|------|------|
| `backend/server.py:242-274` | App Store LLM 客户端初始化 |
| `backend/towow/infra/config.py` | `TowowConfig` + `get_api_keys()` |
| `backend/towow/infra/llm_client.py` | `ClaudePlatformClient`（平台侧 LLM） |
| `apps/shared/json_adapter.py` | `JSONFileAdapter`（template Agent 的 adapter） |
| `apps/app_store/backend/app.py:164-186` | `_load_sample_agents` 加载 Agent |
| `apps/app_store/backend/routers.py:513-616` | `negotiate` 端点 |
| `backend/towow/core/engine.py:547-645` | `_run_offers` 并行 Offer 生成 |
| `backend/towow/skills/offer.py` | `OfferGenerationSkill` |

## 技术栈

- **后端**: Python 3.12 + FastAPI + Uvicorn
- **LLM**: Anthropic Claude API (Sonnet 4.5) via `anthropic` SDK
- **部署**: Railway (Docker)
- **配置**: pydantic-settings（`TOWOW_` prefix 环境变量）
