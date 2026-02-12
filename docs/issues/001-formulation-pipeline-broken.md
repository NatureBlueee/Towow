# Issue 001: Formulation 数据管道断裂

**发现日期**: 2026-02-12
**影响范围**: V1 Engine formulation 阶段 + "通向惊喜"功能
**严重程度**: Critical — 核心价值主张失效
**状态**: 已诊断，待修复

---

## 现象

1. V1 negotiation 流程在 formulation 阶段不稳定，有时卡住无法通过
2. "通向惊喜"功能（基于用户 profile 丰富需求）完全无效
3. SecondMe 用户的分身在 V1 negotiation 中未被使用

## 根因分析

### 根因 1: profile_data 从未传给 formulation skill

**位置**: `backend/towow/core/engine.py:301-305`

Engine 传给 formulation skill 的 context 只有 `raw_intent`、`agent_id`、`adapter`，
没有 `profile_data`。而 formulation skill 的 `_build_prompt` 从 `context.get("profile_data", {})` 读取 profile，永远得到空字典。

LLM prompt 中永远出现 `"(no profile data)"`。

**对比**: Offer 阶段正确地先 `await adapter.get_profile()` 再传入 context（engine.py:446-458）。

### 根因 2: V1 Engine 永远使用 ClaudeAdapter，SecondMe 未接入

**位置**: `backend/server.py:127-136`

统一后端启动时创建的是 `ClaudeAdapter`（共享单例），绑定到 `app.state.adapter`。
V1 engine 的 `_run_negotiation()` 取的是 `state.adapter`——永远是 ClaudeAdapter。

SecondMe 用户的 adapter 注册在 App Store 的 `CompositeAdapter`（`state.store_composite`），
V1 engine 完全不知道它的存在。

**架构断裂**: 两个世界各管各的 adapter，无法互通。

### 根因 3: Formulation 无超时保护

**位置**: `backend/towow/core/engine.py:301`

Offer 生成有 `asyncio.wait_for(..., timeout=offer_timeout_s)` 保护。
Formulation 的 `formulation_skill.execute()` 没有超时，LLM 调用挂起时整个 negotiation 卡死。

### 根因 4: Lenient JSON parsing 把 LLM 错误当成需求文本

**位置**: `backend/towow/skills/formulation.py:134-137`

当 LLM 返回非 JSON（如 rate limit 错误消息），整段文本被当作 formulated_text。
后续 negotiation 基于一段错误消息去匹配 agent。

### 根因 5: 前端无 formulation 超时反馈

**位置**: `website/hooks/useNegotiationStream.ts`

WebSocket 等待 `formulation.ready` 事件时无超时机制。后端卡住时前端无限转圈，
用户无法重试或取消。

## 数据流对比

```
设计意图:
  用户意图 → [用户的 adapter 获取 profile] → [profile 注入 prompt] → LLM 丰富 → 确认 → 编码

实际发生:
  用户意图 → [共享 ClaudeAdapter, 无 profile] → [prompt 说 "no profile data"] → LLM 空洞响应 → 确认 → 编码
```

## 本质问题

这不是一个 bug，而是一个**架构层的遗漏**：

- Adapter 管理属于基础设施层，但目前被分裂在两个应用各自的初始化中
- V1 Engine（协议层）和 App Store（应用层）之间缺少统一的 adapter 基础设施
- 每个 agent 应该在注册时关联自己的 adapter，协议层操作时按 agent_id 路由

详见 Decision 文档: `docs/decisions/ADR-001-unified-adapter-registry.md`

## 教训

1. **类型对齐 ≠ 数据流通**: formulation skill 声明了 `profile_data` 参数，engine 声明了 adapter 参数，两边的类型都对，但数据没有真正流过中间环节
2. **单元测试的 mock 掩盖了真实问题**: 测试用 MockAdapter 直接返回 profile，绕过了 "engine 需要 fetch profile 再传给 skill" 这一步
3. **并行开发的接缝盲区**: V1 Engine 和 App Store 各自开发时都是通的，但接缝处（adapter 共享）没有人负责
4. **超时是基础设施**: 任何外部调用都必须有超时，不能依赖"通常很快"的假设
