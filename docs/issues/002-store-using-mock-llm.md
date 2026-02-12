# Issue 002: App Store 协商使用 MockLLMClient，API Key 未注入

**发现日期**: 2026-02-12
**影响范围**: App Store 所有协商流程
**严重程度**: Critical — 整个协商输出是假的
**状态**: 根因 1+2+3 已修复，根因 4 (SecondMe 不稳定) 属外部依赖
**关联**: ADR-001 (AgentRegistry), Issue 001

---

## 现象

1. 发起协商后方案几乎瞬间出来
2. 方案内容是通用模板，和具体需求完全无关
3. 用户配置的 API Key 仪表盘显示零调用
4. 只有 1 个 Agent（SecondMe 用户自己）产生共振
5. 响应收集为空或极差

## 根因分析

### 根因 1: Store LLM Client fallback 到 MockLLMClient（致命）

**位置**: `backend/server.py:200-211` (`_init_app_store`)

```python
store_keys = config.get_api_keys()
llm_client = None
if store_keys:
    llm_client = ClaudePlatformClient(api_key=store_keys, ...)
else:
    from apps.shared.mock_llm import MockLLMClient
    llm_client = MockLLMClient()  # ← 实际走了这条路
```

`config.get_api_keys()` 从环境变量 `TOWOW_ANTHROPIC_API_KEY` / `TOWOW_ANTHROPIC_API_KEYS` 读取。
`.env` 文件中没有这些变量 → 返回空列表 → fallback 到 MockLLMClient。

**MockLLMClient 行为** (`apps/shared/mock_llm.py:66-77`):
- Center 调用：直接返回硬编码模板（"基于所有参与者的响应分析..."）
- 普通 chat 调用：返回固定文本
- **用户看到的方案和模板一字不差**

**结果**:
- Formulation skill 调用 `adapter.chat()`（走 SecondMe/Claude adapter，不走 MockLLMClient）→ 可能正常
- Offer skill 调用 `adapter.chat()`（同上）→ 可能正常
- **Center skill 调用 `llm_client.chat()`（走 MockLLMClient）→ 返回假数据**
- 方案瞬间出来（无真实 LLM 调用），内容是废话模板

### 根因 2: store_agent_vectors 未为 sample agents 创建向量

**位置**: `backend/server.py:252`

```python
app.state.store_agent_vectors = {}  # 初始化为空
```

`_load_sample_agents()` 将 sample agents 注册到 AgentRegistry，但**没有编码向量**。
只有 SecondMe 用户通过 `_register_agent_from_secondme()` 连接时，向量才被添加到 `store_agent_vectors`。

**结果**: 共振检测的 `candidate_vectors` 几乎为空。
- Sample agents: 注册了但无向量 → 无法参与共振
- SecondMe 用户: 有向量 → 唯一参与者

### 根因 3: 需求提交者与自己产生共振

当 SecondMe 用户是唯一有向量的 agent 时，共振检测返回用户自己。
用户既是需求提交者，又是唯一响应者 — 自己匹配自己，无意义。

### 根因 4: SecondMe chat 不稳定（已知）

Offer 阶段调用 `SecondMeAdapter.chat()` 可能失败（502、超时等），导致 agent EXITED、0 offers。
但由于根因 1（MockLLMClient），Center 无论如何都返回模板，此问题被掩盖。

## 数据流对比

```
设计意图:
  需求 → Formulation(真实LLM) → 确认 → 编码 → 多Agent共振 → 多Offer → Center(真实LLM综合) → 方案

实际发生:
  需求 → Formulation(SecondMe?) → 自动确认 → 编码 → 仅自己共振 → 0-1 Offer → Center(MockLLMClient硬编码) → 模板
```

## 影响评估

| 组件 | 影响 |
|------|------|
| Center synthesis | 完全失效 — 用的是 Mock |
| Formulation | 可能正常（走 adapter，不走 llm_client） |
| Offer generation | 可能正常（走 adapter），但只有 1 个参与者 |
| 共振检测 | 形同虚设 — sample agents 无向量 |
| 前端展示 | 展示了假数据，用户看到垃圾方案 |

## 修复方向

### 紧急修复（解除 Mock）

1. **确保 `TOWOW_ANTHROPIC_API_KEY` 注入到运行环境**
   - 本地: 写入 `.env` 或启动命令
   - Railway: 确认环境变量已配置
   - 验证: 启动日志应显示 "ClaudePlatformClient" 而不是 "Mock LLM"

### 后续修复

2. **Sample agents 向量编码** — `_load_sample_agents` 后遍历编码，填充 `store_agent_vectors`
3. **排除需求提交者** — 共振检测应排除 `user_id == agent_id` 的情况
4. **移除或标记 MockLLMClient** — 生产环境不应有静默 fallback 到 Mock 的路径

## 修复记录

### 2026-02-12: 根因 1 修复 — API Key 注入 + 可观测性

**改动文件**: `backend/.env`, `backend/server.py`, `backend/towow/infra/llm_client.py`

1. **`.env` 添加 Key 和 Base URL**
   - `TOWOW_ANTHROPIC_API_KEYS=5个key逗号分隔`
   - `TOWOW_ANTHROPIC_BASE_URL=https://www.packyapi.com`（代理服务）

2. **Store 初始化日志** (`server.py`)
   - 用真实 LLM: `Store: ClaudePlatformClient initialized (N key(s), base_url=...)`
   - 用 Mock: `Store: ⚠️  Using MockLLMClient — ...` (WARNING 级别)

3. **每次 LLM 调用详细日志** (`llm_client.py`)
   - START: key 标识（尾4位）、model、messages 数、tools 数
   - OK: 耗时 ms、stop_reason、tool_calls 数、text 长度
   - FAIL/RATE_LIMITED: 耗时 ms、错误信息、自动换 key 重试

**验证**: Center 输出从硬编码模板变为真实 LLM 响应。

### 2026-02-12: 根因 2 修复 — Sample agents 向量编码

**改动文件**: `backend/server.py`

- 新增 `_encode_store_agent_vectors()` 异步函数
- 在 lifespan 中 `_init_app_store()` 之后调用
- 遍历 registry 所有 agent → 提取 profile 文本 → encoder.encode → 存入 `store_agent_vectors`
- 启动日志: `Store vectors: encoded N agents, skipped M (total T)`

**根因**: `app.py`（独立模式）有预编码逻辑(line 272-295)，但 `server.py`（统一服务模式）只有 `store_agent_vectors = {}` + "lazily" 注释，从未实际编码。

### 2026-02-12: 根因 3 修复 — 排除需求提交者自共振

**改动文件**: `backend/towow/core/engine.py`

- `_run_encoding()` 在调用 `resonance_detector.detect()` 前，从 `agent_vectors` 中排除 `session.demand.user_id`
- 排除后如果候选为空，跳过共振直接进入 OFFERING
- 改动在 engine 协议层（正确位置），不改 resonance detector（纯函数保持不变）

## 教训

1. **静默 fallback 是最危险的 bug**: MockLLMClient 作为开发工具本身没问题，但在生产路径上静默 fallback 且不告知用户，等于系统在"演戏"而非工作
2. **端到端验证必须包含 LLM 调用可观测性**: 启动时应明确 log "使用真实 LLM" vs "使用 Mock"，甚至在 API 响应中标记
3. **向量编码不能"后续再做"**: `store_agent_vectors = {}` + "populated lazily" 注释 = 永远不会被填充
4. **自己和自己匹配是设计盲区**: 需求提交者不应出现在共振结果中
