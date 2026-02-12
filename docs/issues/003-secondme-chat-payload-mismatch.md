# Issue 003: SecondMe Chat API 请求参数名错误导致 assist-demand 始终 502

**发现日期**: 2026-02-12
**影响范围**: App Store "通向惊喜"功能（assist-demand）、所有经由 SecondMe chat_stream 的对话
**严重程度**: Critical — 核心交互功能完全不可用
**状态**: 已修复

---

## 现象

用户登录 SecondMe 成功后，点击"通向惊喜"按钮始终返回 502 Bad Gateway。

- 登录流程正常（OAuth2 授权 + token 交换 + Agent 注册 + profile 获取均正常）
- 仅 chat_stream 调用必定失败
- 此问题在 ADR-001 大重构之前就已存在，始终未查清

## 根因

### SecondMe Chat API 参数名不匹配

**位置**: `backend/oauth2_client.py:663-666`（修复前）

```python
# 错误代码
payload = {
    "messages": messages,        # ← 数组，OpenAI 格式
    "enableWebSearch": False,
}
```

SecondMe Chat API (`/gate/lab/api/secondme/chat/stream`) 期望的参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `message` | string | 单条消息文本（**不是** `messages` 数组） |
| `sessionId` | string (optional) | 会话 ID，用于上下文关联 |
| `systemPrompt` | string (optional) | 系统提示词 |
| `enableWebSearch` | boolean (optional) | 是否启用网络搜索 |

我们发送 `"messages": [{"role":"user","content":"text"}]`（OpenAI 多轮对话格式），
SecondMe 期望 `"message": "text"`（单条字符串）。

API 收不到 `message` 字段，返回错误或空内容 → 502。

### 为什么其他 SecondMe API 正常

同一 oauth2_client 的其他方法（`get_user_info`、`get_shades`、`get_softmemory`）都正常，
因为它们使用 GET 请求，参数在 URL/header 中，格式正确。只有 `chat_stream` 是 POST + JSON body，
参数名错了。

### 为什么之前两次修复未解决

| 时间 | Commit | 修了什么 | 为什么没解决 |
|------|--------|---------|-------------|
| 2026-02-11 | `aafec17` | SSE 解析格式（choices/delta）+ OAuth scope 加 chat | 解析和权限对了，但请求 payload 参数名仍然错 |
| 2026-02-11 | `37bd4d2` | Token 刷新（每次登录更新 adapter） | Token 对了，但请求 payload 参数名仍然错 |

三次修复分别对应三个独立的 failure mode：
1. 权限不足（scope 缺 chat）→ aafec17 修复
2. Token 过期（旧 adapter 残留）→ 37bd4d2 修复
3. **请求参数名错误（`messages` vs `message`）→ 本次修复**

## 修复

**文件**: `backend/oauth2_client.py` — `chat_stream()` 方法

从 `messages` 数组中提取最后一条 user 消息的 content，作为 `message` 字段发送：

```python
# 修复后
last_content = ""
for m in reversed(messages):
    if m.get("role") == "user" and m.get("content"):
        last_content = m["content"]
        break

payload = {
    "message": last_content,          # ← 单条字符串
    "enableWebSearch": enable_web_search,
}
```

函数签名不变（仍接受 `messages: list[dict]`），内部做格式转换。
对上层调用方（SecondMeAdapter、AgentRegistry、assist_demand handler）完全透明。

## 调查过程中的教训

### 教训 1: 外部 API 契约必须对照官方文档逐字段验证

`messages`（OpenAI 格式）和 `message`（SecondMe 格式）只差一个 `s`，
代码审查和类型检查都不会报错。这类"几乎正确"的 bug 只能通过**逐字段对照官方文档**发现。

### 教训 2: 多层错误掩盖根因

三个独立的 failure mode 叠加在同一条调用链上：
- 修了 scope → 仍然 502（因为还有 token 问题和参数问题）
- 修了 token → 仍然 502（因为还有参数问题）
- 每次修一层，掀开后面还有一层

当一个问题"修了还是不行"时，不应该怀疑修复本身，而应该**排查同一条链路上是否有多个独立的故障点**。

### 教训 3: 诊断手段要直达底层

前两次修复都是从"可能的原因"推理出的。本次修复是通过**直接查看 SecondMe API 文档**
确认请求参数格式后定位的。对外部 API 的问题，推理不如查文档+实测。

## 验证

- 221 测试全部通过（测试 mock 在 adapter 层，不受影响）
- 需要实际登录 SecondMe 并点击"通向惊喜"做端到端验证
- 诊断端点 `GET /store/api/debug/chat-test`（临时）可用于验证 chat 连通性

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/oauth2_client.py:630` | chat_stream 方法（修复点） |
| `backend/towow/adapters/secondme_adapter.py:146` | 调用 chat_stream 的 adapter |
| `apps/app_store/backend/routers.py:271` | assist_demand handler |
| SecondMe API 文档 | https://develop-docs.second.me/zh/docs/api-reference/secondme |
