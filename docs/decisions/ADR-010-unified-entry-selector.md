# ADR-010: 统一入口选择器

**日期**: 2026-02-13
**状态**: 已批准
**关联**: ADR-009 (开放注册), ADR-002 (MCP 独立入口)

## 背景

当前首页"进入通爻网络"直接跳转 SecondMe 登录。这有两个问题：

1. **入口单一**：没有 SecondMe 账号的用户无法进入（ADR-009 的 Playground 虽然解决了注册问题，但入口是独立页面，不在主流程中）
2. **无法展示宽度**：通爻网络支持多种接入方式（SecondMe、邮箱、MCP...），但用户感知不到

需要一个统一入口页面，让用户选择"怎么进入网络"。

## 核心判断

**入口是选择器，不是门卫。**

通爻网络的入口不是"证明你是谁"（传统登录），而是"你选择带多少东西进来"：
- SecondMe：带 AI 分身 + 丰富画像 + 专属 LLM 通道
- 邮箱/手机：带基本身份 + 自述文字 + 默认 LLM 通道
- MCP：带协议级接入能力 + 用户自有 LLM
- Google：带 Google 身份（未来）

## 选项分析

### 选项 A：新建独立入口页
- 新页面 `/enter`，用户从首页跳转到此
- 5 个入口卡片，选择后进入对应流程
- 优势：入口体验独立控制，不影响 Store 页面
- 劣势：多一次跳转

### 选项 B：Store 页面内嵌入口选择
- 未登录时，Store 页面展示入口选择器（替代当前的 SecondMe 登录提示）
- 登录后，入口选择器消失，展示正常 Store 内容
- 优势：少一次跳转，路由简单
- 劣势：Store 页面逻辑更复杂

## 决策

**选择 选项 A：独立入口页 `/enter`**

理由：
- 入口体验是品牌展示（展示宽度），值得一个独立页面
- Store 页面已经够复杂（协商、历史、Agent 列表），不应再塞入口逻辑
- 首页 CTA 从"进入通爻网络"→ `/enter` → 选择方式 → `/store`，流程自然

## 五个入口的实现深度

| 入口 | 按钮文案 | 点击行为 | 实现深度 |
|------|---------|---------|---------|
| SecondMe | "用 AI 分身登录" | 跳转 SecondMe OAuth | **完整**（已有） |
| 邮箱 | "用邮箱加入" | 展开邮箱注册表单（Playground 流程） | **完整**（复用 ADR-009 quick-register） |
| 手机号 | "用手机号加入" | 展开手机号注册表单 | **完整**（同一 API，phone 字段） |
| Google | "用 Google 登录" | Toast 提示"即将开放" | **占位**（按钮可点，有反馈） |
| MCP | "通过 MCP 连接" | 跳转 MCP 文档/下载页 | **引导**（外部链接） |

## 用户流程

```
首页 "进入通爻网络"
  → /enter（入口选择器）
    → SecondMe → OAuth → /store（已有流程）
    → 邮箱 → 表单 → quick-register → /store
    → 手机号 → 表单 → quick-register → /store
    → Google → Toast "即将开放"
    → MCP → 外部链接（文档/下载）
```

邮箱/手机注册成功后，agent_id 存入 localStorage（与 Playground 相同），跳转到 `/store`。Store 页面检测 localStorage 中的 agent_id，作为已登录用户展示。

## 对现有系统的影响

### 需要改的
1. **新页面** `/enter`（前端）
2. **首页 CTA** 从 `/store` 改为 `/enter`
3. **Store 页面** 新增 localStorage agent_id 检测（与 cookie session 并行）

### 不需要改的
- 后端 API（quick-register 已有，SecondMe OAuth 已有）
- AgentRegistry（ADR-009 已覆盖）
- 协商流程（不受入口方式影响）

## 核心原则

- **投影是基本操作 (0.8)**：每种登录方式是不同的投影透镜，给出不同丰度的"我"
- **本质与实现分离 (0.2)**：入口方式是应用层，不影响协议层
- **复杂性从简单规则生长 (0.7)**：所有非 SecondMe 入口都复用同一个 quick-register 模式

## 已知待解决

- Store 页面目前用 cookie session 判断登录状态（SecondMe）。新增 localStorage agent_id 后，两套身份机制需要共存。需要在 PLAN 阶段详细设计。
- Google OAuth 未来真正实现时，需要单独的 ADR。
- MCP 链接指向的文档/下载页尚不存在（依赖 ADR-002 实施）。
