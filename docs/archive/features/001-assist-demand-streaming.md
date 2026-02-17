# Feature 001: "通向惊喜" 流式输出 + Markdown 渲染 + 智能需求生成

**日期**: 2026-02-12
**状态**: 已实现（V4 prompt + 数据管道修复 + Markdown 渲染）
**关联**: Issue 003 (SecondMe chat payload mismatch), Issue 002 (MockLLMClient)

---

## 功能概述

用户在 App Store 点击"通向惊喜"按钮后，SecondMe 分身利用三个信息源——用户 Profile、场景上下文、网络参与者——发现用户自己想不到的协作需求。文字以流式方式逐步出现，实时 Markdown 渲染。

## 改动清单

### 前端

| 文件 | 改动 | 类型 |
|------|------|------|
| `website/components/store/DemandInput.tsx` | 按钮加载态"捣乱中..." + 脉冲动画；Markdown 预览/编辑双模式；轻量 Markdown 渲染器 | 实现 |
| `website/lib/store-api.ts` | `assistDemandStream()` SSE 客户端 + buffer-based 解析器 | 契约消费方 |

### 后端

| 文件 | 改动 | 类型 |
|------|------|------|
| `apps/app_store/backend/routers.py` | `assist_demand` SSE StreamingResponse；60s 超时；防缓冲头 | **契约变更**（响应格式） |
| `apps/app_store/backend/routers.py` | `ASSIST_PROMPTS` V4：思维链 + 去模板 + 信息优势驱动 | 实现 |
| `apps/app_store/backend/routers.py` | `_build_agent_summaries()` 支持 JSON agent + SecondMe 两种画像格式 | 实现 |
| `backend/towow/infra/agent_registry.py` | `register_source()` 存储 profile_data | 数据管道修复 |
| `backend/towow/infra/agent_registry.py` | `get_agent_info()` 暴露 skills/bio/role/shades 等摘要字段 | 数据管道修复 |
| `backend/routers/auth.py` | `_register_agent_from_secondme()` 传 profile_data | 数据管道修复 |

---

## 全链路数据流

```
用户点击"通向惊喜"
│
├─ DemandInput.tsx: handleAssist('surprise')
│   setAssistLoading('surprise') → 按钮显示"捣乱中..." + 脉冲动画
│   setIsEditing(false) → 切换到 Markdown 预览模式
│
├─ store-api.ts: assistDemandStream()
│   fetch POST /store/api/assist-demand
│   headers: Content-Type: application/json
│   credentials: include (Cookie: towow_session=xxx)
│   body: { mode: "surprise", scene_id: "hackathon", raw_text: "" }
│
├─ Next.js rewrite: /store/api/* → ${BACKEND_URL}/store/api/*
│   (next.config.ts rewrites, dev server http-proxy / Vercel edge)
│
├─ routers.py: assist_demand()
│   1. _get_agent_id_from_session(request) → 从 Cookie 读 agent_id
│   2. composite.get_agent_info(agent_id) → 验证 agent 在网络中
│   3. _build_agent_summaries() → 构建网络参与者摘要（含 skills/bio/shades）
│   4. ASSIST_PROMPTS["surprise"].format() → 组装 system prompt（含网络信息）
│   5. 返回 StreamingResponse(_sse_generator())
│      headers: Cache-Control: no-cache, no-store
│               X-Accel-Buffering: no
│
├─ _sse_generator():
│   async with asyncio.timeout(60):
│     async for chunk in composite.chat_stream(agent_id, messages, system_prompt):
│       yield f"data: {chunk}\n\n"
│   yield "data: [DONE]\n\n"
│
├─ composite.chat_stream() → AgentRegistry 路由
│   entry = _agents[agent_id]
│   entry.adapter.chat_stream(messages, system_prompt)
│
├─ SecondMeAdapter.chat_stream()
│   self._client.chat_stream(messages, system_prompt)
│
├─ oauth2_client.chat_stream()
│   POST https://app.mindos.com/gate/lab/api/secondme/chat/stream
│   headers: Authorization: Bearer {access_token}
│   body: { "message": last_content, "systemPrompt": system_prompt }
│   ← SSE: data: {"choices":[{"delta":{"content":"..."}}]}
│   → yield content string
│
├─ 前端 ReadableStream 逐 chunk 接收
│   buffer-based SSE 解析（处理跨 chunk 拆分）
│   每个 data chunk → accumulated += chunk → onChunk(accumulated)
│
├─ DemandInput.tsx: setText(accumulated)
│   Markdown 预览模式：实时渲染 **加粗**、段落、列表
│
└─ 流结束: [DONE]
    setAssistLoading(null) → 按钮恢复为"通向惊喜"
    用户可点击预览区切换到编辑模式
```

## Agent Summaries 数据管道

### 问题诊断

`_build_agent_summaries()` 尝试获取 `skills`/`bio`，但 `get_agent_info()` 从未返回这些字段。

**根因**：两处注册入口都没有存储 profile_data：
1. `register_source()` —— 批量注册 JSON 样板间 Agent 时未传 profile_data
2. `_register_agent_from_secondme()` —— SecondMe 用户注册时未传 profile_data

**结果**：agent_summaries 只输出名字，SecondMe 分身无法知道网络中有谁能做什么。

### 修复（4 处）

| 位置 | 修复 |
|------|------|
| `agent_registry.py:register_source()` | 从 `adapter.profiles` 获取 profile_data 存到 AgentEntry |
| `auth.py:_register_agent_from_secondme()` | 传 `profile_data=profile` |
| `agent_registry.py:get_agent_info()` | 从 profile_data 提取 skills/bio/role/shades/interests 等摘要字段 |
| `routers.py:_build_agent_summaries()` | 支持两种画像格式：JSON agent（skills/role）+ SecondMe（shades/self_introduction） |

### 修复后 agent_summaries 示例

```
修前：- 张伟
修后：- 张伟（后端工程师），擅长 Python, Go, 分布式系统, Redis。5年后端开发经验，专注高并发系统设计...
```

---

## Prompt 设计

### 核心问题：分身比本人多看到了什么？

这是 V4 prompt 的设计基石。分身的信息优势来自三个源：

| 信息源 | 用户知道？ | 分身知道？ |
|--------|-----------|-----------|
| 用户自己的 Profile（经历、思维方式、盲区） | 部分（自我认知有盲区） | 全部（读过所有文字） |
| 场景上下文（什么机会） | 不知道 | 知道 |
| 网络中的人（谁在、能做什么） | 不知道 | 知道 |

**惊喜 = 用户的"自" × 用户不知道的（场景 + 网络中的人）→ 碰撞点**

这对齐了架构的核心概念：
- **投影操作**（Section 0.8）：用户的"自"通过（场景×网络）透镜投影出需求
- **未知关联**：通向惊喜 = 发现用户不知道存在的关联
- **需求 ≠ 要求**（Section 0.6）：分身发现的是真实张力，不是用户以为的解法

### Prompt 迭代历史

| 版本 | 问题 | 修正 |
|------|------|------|
| V1 | 机械模板（`## 我喜欢什么`），没读 V1 Skill Prompts | 读了所有 V1 Skill Prompts 后重写 |
| V2 | 对齐了哲学（需求≠要求），但字段语义仍在描述"这个人是谁" | 字段改为描述"这个协作要做什么" |
| V3 | 6 个固定字段模板，每个用户输出长得一样；SecondMe 实际输出验证通过 | 去模板化，改为思维链引导 |
| **V4（当前）** | — | **分步思维链 + 去模板 + 信息优势驱动 + 用用户的声音** |

### V4 Prompt 设计要点

**1. 明确信息优势**
```
你比他多看到两样东西：
1. 这个场景里有什么机会（他不知道）
2. 网络里有什么样的人（他不知道）
```

**2. 五步思维链（只输出最后一步）**
```
第一步：分析他 → 找到最独特的能力/经历/视角
第二步：扫描网络 → 谁的能力形成互补？
第三步：发现碰撞点 → 能力 × 机会 × 某个人
第四步：构造需求 → 做什么、各出什么、底线、时间
第五步：用他的声音说出来 → 适配用户的表达习惯
```

**3. 去模板化**
- 不再有 `**我要做什么**` 等固定字段
- 输出结构从内容生长，不是从模板填充
- 每个用户的输出风格不同（结构化 vs 口语化 vs 简洁 vs 细致）

**4. 负面约束**
- 不要描述"他是一个什么样的人"
- 不要编造没有的能力
- 只围绕一个碰撞点
- 不加任何前缀或后缀

### polish prompt 同步对齐

`ASSIST_PROMPTS["polish"]` V4 采用同样的分步思维链：
1. 理解真正的需求（vs 表面的要求）
2. 补充没说出来的背景
3. 区分硬性和柔性条件
4. 用他的方式重新表达

---

## Markdown 渲染

### 设计决策

V4 prompt 去模板化后，输出是自然段落+加粗+列表，需要渲染才好看。

**方案**：轻量级内置渲染器（不引入外部依赖），处理 `**加粗**`、段落、列表、换行。

### 双模式 UX

| 状态 | 显示 |
|------|------|
| 无内容 | textarea（可输入，显示 placeholder） |
| 编辑中（textarea focused） | textarea |
| 有内容 + 非编辑态 | **Markdown 预览**（可滚动，最大高度 400px） |
| 流式输出中 | **Markdown 预览**（实时渲染） |
| 点击预览区域 | 切换到编辑态（focus textarea） |
| 流式输出中点击 | 不响应（防止中断流式） |

### 渲染器支持

| Markdown 语法 | 渲染结果 |
|---------------|----------|
| `**文字**` | **加粗** |
| 空行分隔 | 段落 `<p>` |
| `- 项目` / `* 项目` | 无序列表 |
| `1) 项目` / `1. 项目` | 有序列表（渲染为 `<li>`） |
| 单个换行 | `<br>` |

---

## 降级路径

| 失败场景 | 后端行为 | 前端行为 |
|----------|----------|----------|
| SecondMe 60s 超时 | `TimeoutError` → `event: error` + `[DONE]` | 显示"分身响应超时，请重试" |
| SecondMe 返回空内容 | `event: error` + `[DONE]` | 显示"没有产出内容，请重试" |
| Stream 中途异常 | `event: error` + `[DONE]` | 显示"暂时无法响应，请稍后再试" |
| Cookie 过期 | HTTP 401 (在 SSE 之前) | 触发 `onAuthExpired()`，提示重新登录 |
| Next.js rewrite 缓冲 SSE | 未处理（理论风险） | 备选方案：Next.js API Route 做 SSE 代理 |

## 契约变更记录

### `POST /store/api/assist-demand` 响应格式变更

**Before**: `application/json`
```json
{"demand_text": "...", "mode": "surprise"}
```

**After**: `text/event-stream`
```
data: 文字内容\n\n
data: ...\n\n
event: error\n           ← 仅在出错时
data: 错误信息\n\n
data: [DONE]\n\n
```

**消费方**: 仅前端 `assistDemandStream()`，已同步更新。无其他消费方。

**响应头**:
- `Cache-Control: no-cache, no-store` — 防代理缓存
- `X-Accel-Buffering: no` — 告知反向代理不要缓冲

## 前置依赖

- **Issue 003 已修复**: SecondMe chat payload 参数名 `messages` → `message`
- **Auth 链路正常**: OAuth2 登录 → Cookie session → agent_id 映射

## 待验证

- [ ] Vercel 生产环境 Next.js rewrite 是否透传 SSE 流式
- [ ] V4 prompt 实际输出质量（碰撞点是否有意外感、声音是否像用户）
- [ ] Markdown 渲染在流式输出中途是否有闪烁/不完整的加粗标记

## 关键文件索引

| 文件 | 位置 | 说明 |
|------|------|------|
| `website/components/store/DemandInput.tsx` | `renderMarkdown()` | 轻量 Markdown 渲染器 |
| `website/components/store/DemandInput.tsx` | `handleAssist()` | 流式调用 + 模式切换 |
| `website/components/store/DemandInput.tsx` | `showPreview` | 预览/编辑双模式控制 |
| `website/lib/store-api.ts` | `assistDemandStream()` | SSE 客户端 + buffer 解析器 |
| `apps/app_store/backend/routers.py` | `ASSIST_PROMPTS` | V4 surprise + polish prompt |
| `apps/app_store/backend/routers.py` | `_build_agent_summaries()` | 双格式画像摘要 |
| `apps/app_store/backend/routers.py` | `assist_demand()` | SSE handler + 60s 超时 |
| `backend/towow/infra/agent_registry.py` | `register_source()` | 存储 profile_data |
| `backend/towow/infra/agent_registry.py` | `get_agent_info()` | 暴露画像摘要字段 |
| `backend/routers/auth.py` | `_register_agent_from_secondme()` | 传 profile_data |
| `backend/oauth2_client.py` | `chat_stream()` | SecondMe SSE 底层调用 |
