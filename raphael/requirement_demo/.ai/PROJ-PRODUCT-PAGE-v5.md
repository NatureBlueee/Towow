# PROJ-PRODUCT-PAGE-v5.md

## 文档元信息

| 字段 | 值 |
|------|-----|
| 文档ID | PROJ-PRODUCT-PAGE-v5 |
| 状态 | ACTIVE |
| 创建日期 | 2026-01-29 |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 项目概述

### 1.1 项目名称

ToWow 产品体验页开发

### 1.2 项目目标

为 ToWow 平台开发一个产品体验页，让用户能够：
1. 通过 SecondMe OAuth2 登录
2. 提交协作需求
3. 实时观看 Agent 协商过程
4. 体验多 Agent 实时协作能力

### 1.3 成功指标

- 用户可以完成完整的体验流程（登录 -> 提交 -> 查看协商 -> 查看结果）
- 页面加载时间 < 3s
- WebSocket 连接稳定，断线自动重连
- 无阻塞性 Bug

---

## 2. 范围说明

### 2.1 本期包含

| 功能 | 优先级 | 说明 |
|------|--------|------|
| SecondMe OAuth2 登录 | P0 | 用户认证入口 |
| 需求提交表单 | P0 | 标题 + 描述输入 |
| 协商过程实时展示 | P0 | WebSocket 消息流 |
| 协商结果展示 | P0 | 完成状态展示 |
| 错误处理 | P1 | 边界情况处理 |
| 动画优化 | P2 | 交互体验提升 |

### 2.2 本期不包含

- 用户注册流程（依赖 SecondMe）
- 历史需求管理
- Agent 配置管理
- 多语言支持
- 移动端适配（[TBD]）

### 2.3 Story -> Task 对齐表

| Story | Task | 优先级 | 本期纳入 |
|-------|------|--------|----------|
| 用户登录 | TASK-EXP-002, TASK-EXP-003 | P0 | Yes |
| 提交需求 | TASK-EXP-004 | P0 | Yes |
| 查看协商 | TASK-EXP-005, TASK-EXP-006, TASK-EXP-007, TASK-EXP-008 | P0/P1 | Yes |
| 页面框架 | TASK-EXP-001 | P0 | Yes |
| 页面集成 | TASK-EXP-009 | P0 | Yes |
| 错误处理 | TASK-EXP-010 | P1 | Yes |
| 动画优化 | TASK-EXP-011 | P2 | Yes |

---

## 3. 执行进度表

| TASK_ID | Beads ID | 任务名称 | 优先级 | 状态 | Owner | 预估 | 依赖 |
|---------|----------|----------|--------|------|-------|------|------|
| TASK-EXP-001 | towow-sv4 | 页面路由与布局 | P0 | TODO | [TBD] | 2h | - |
| TASK-EXP-002 | towow-7b6 | 认证 Context 与 Hooks | P0 | TODO | [TBD] | 4h | - |
| TASK-EXP-003 | towow-qzu | LoginPanel 组件 | P0 | TODO | [TBD] | 3h | EXP-002 |
| TASK-EXP-004 | towow-apq | RequirementForm 组件 | P0 | TODO | [TBD] | 4h | - |
| TASK-EXP-005 | towow-32d | WebSocket Hook | P0 | TODO | [TBD] | 4h | - |
| TASK-EXP-006 | towow-uk3 | MessageBubble 组件 | P1 | TODO | [TBD] | 2h | - |
| TASK-EXP-007 | towow-kdu | AgentAvatar 组件 | P1 | TODO | [TBD] | 1h | - |
| TASK-EXP-008 | towow-ns6 | NegotiationTimeline 组件 | P0 | TODO | [TBD] | 4h | EXP-005, EXP-006 |
| TASK-EXP-009 | towow-wvq | 页面集成与状态管理 | P0 | TODO | [TBD] | 4h | EXP-001~008 |
| TASK-EXP-010 | towow-28t | 错误处理与边界情况 | P1 | TODO | [TBD] | 3h | EXP-009 |
| TASK-EXP-011 | towow-bg4 | 动画与交互优化 | P2 | TODO | [TBD] | 3h | EXP-009 |

**总预估工时**：34h

---

## 4. 资源配置

| 角色 | 人数 | 投入时间 | 说明 |
|------|------|----------|------|
| 前端开发 | [TBD] | [TBD] | 主要开发 |
| 后端支持 | [TBD] | [TBD] | API 对接支持 |
| 设计支持 | [TBD] | [TBD] | UI 细节确认 |

---

## 5. 时间计划

### 5.1 目标上线时间

[TBD]

### 5.2 里程碑

| 里程碑 | 目标日期 | 包含任务 | 完成定义 |
|--------|----------|----------|----------|
| M1: 基础框架 | [TBD] | EXP-001, EXP-002, EXP-004, EXP-005, EXP-006, EXP-007 | 页面框架就绪，核心组件可用 |
| M2: 功能完成 | [TBD] | EXP-003, EXP-008, EXP-009 | 完整用户流程可走通 |
| M3: 优化上线 | [TBD] | EXP-010, EXP-011 | 错误处理完善，动画优化完成 |

---

## 6. 执行计划（并行策略）

### 6.1 第一批（可并行，无依赖）

可立即启动的任务：

| TASK_ID | Beads ID | 任务名称 | 预估 |
|---------|----------|----------|------|
| TASK-EXP-001 | towow-sv4 | 页面路由与布局 | 2h |
| TASK-EXP-002 | towow-7b6 | 认证 Context 与 Hooks | 4h |
| TASK-EXP-004 | towow-apq | RequirementForm 组件 | 4h |
| TASK-EXP-005 | towow-32d | WebSocket Hook | 4h |
| TASK-EXP-006 | towow-uk3 | MessageBubble 组件 | 2h |
| TASK-EXP-007 | towow-kdu | AgentAvatar 组件 | 1h |

**并行度**：6 个任务可同时进行

### 6.2 第二批（依赖第一批）

| TASK_ID | Beads ID | 任务名称 | 依赖 | 预估 |
|---------|----------|----------|------|------|
| TASK-EXP-003 | towow-qzu | LoginPanel 组件 | EXP-002 | 3h |
| TASK-EXP-008 | towow-ns6 | NegotiationTimeline 组件 | EXP-005, EXP-006 | 4h |

### 6.3 第三批（集成）

| TASK_ID | Beads ID | 任务名称 | 依赖 | 预估 |
|---------|----------|----------|------|------|
| TASK-EXP-009 | towow-wvq | 页面集成与状态管理 | EXP-001~008 | 4h |

### 6.4 第四批（优化）

| TASK_ID | Beads ID | 任务名称 | 依赖 | 预估 |
|---------|----------|----------|------|------|
| TASK-EXP-010 | towow-28t | 错误处理与边界情况 | EXP-009 | 3h |
| TASK-EXP-011 | towow-bg4 | 动画与交互优化 | EXP-009 | 3h |

---

## 7. 依赖关系图

```
第一批（可并行）：
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ EXP-001     │  │ EXP-002     │  │ EXP-004     │
│ 页面路由    │  │ 认证Context │  │ 需求表单    │
└─────────────┘  └──────┬──────┘  └─────────────┘
                       │
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ EXP-005     │  │ EXP-006     │  │ EXP-007     │
│ WebSocket   │  │ 消息气泡    │  │ Agent头像   │
└──────┬──────┘  └──────┬──────┘  └─────────────┘
       │                │
       └────────┬───────┘
                │
第二批（依赖第一批）：
┌─────────────┐  ┌─────────────┐
│ EXP-003     │  │ EXP-008     │
│ LoginPanel  │  │ Timeline    │
│ (依赖002)   │  │ (依赖005,006)│
└─────────────┘  └─────────────┘
                       │
第三批（集成）：        │
┌──────────────────────┴──────────────────────┐
│              EXP-009                         │
│         页面集成与状态管理                    │
│         (依赖 001-008)                       │
└──────────────────────┬──────────────────────┘
                       │
第四批（优化）：        │
       ┌───────────────┴───────────────┐
       │                               │
┌──────┴──────┐               ┌────────┴────────┐
│ EXP-010     │               │ EXP-011         │
│ 错误处理    │               │ 动画优化        │
└─────────────┘               └─────────────────┘
```

---

## 8. Gate 检查点

### 8.1 Gate A（进入实现前）- PASSED

- [x] TECH-PRODUCT-PAGE-v5.md 已完成
- [x] 任务拆解已完成（11 个 TASK）
- [x] 接口契约已定义
- [x] 组件设计已明确

### 8.2 Gate B（P0 Task 进入 DONE 前）

每个 P0 Task 完成前必须满足：
- [ ] 对应验收标准全部通过
- [ ] 无 TypeScript 编译错误
- [ ] 代码已 Review
- [ ] 测试用例已编写

### 8.3 Gate C（方向偏差时）

触发条件：
- 后端 API 接口变更
- WebSocket 协议变更
- 认证流程变更

触发后动作：
- 更新 TECH 文档
- 更新受影响的 TASK
- 重新评估里程碑

---

## 9. 风险与预案

| 风险 | 影响 | 概率 | 预案 |
|------|------|------|------|
| SecondMe OAuth2 服务不稳定 | 用户无法登录 | 中 | 添加重试机制，显示友好错误提示 |
| WebSocket 连接不稳定 | 消息丢失 | 中 | 实现重连机制，消息去重 |
| 后端 API 响应慢 | 用户体验差 | 低 | 添加 loading 状态，超时处理 |
| 协商过程过长 | 用户等待焦虑 | 中 | 显示进度指示，预估时间 |

---

## 10. 验收检查点

### 10.1 禁止 Mock 检查

- [ ] 前端是否调用真实后端 API？
- [ ] 后端是否返回真实数据结构？
- [ ] 是否进行了真数据端到端验证？

### 10.2 提交流程检查

每个 TASK 完成时：
1. 完成代码 + 更新 TASK 文档
2. 标记 beads 状态为 `DOING`
3. 请求 tech review
4. Review 通过后，执行 Git Commit（引用 TASK-ID）
5. 标记 beads 状态为 `DONE`

---

## 11. 变更记录

| 时间 | 变更内容 | 变更人 | 影响 |
|------|----------|--------|------|
| 2026-01-29 22:52 | 创建项目计划 | proj | 初始版本 |

---

## 附录：beads 命令速查

```bash
# 查看可开始的任务
bd ready -l PRODUCT-PAGE

# 查看所有任务
bd list -l PRODUCT-PAGE

# 查看任务详情
bd show <beads_id>

# 更新任务状态
bd update <beads_id> -s doing
bd update <beads_id> -s done

# 查看依赖关系
bd dep list <beads_id>
```

---

*文档版本：v5*
*最后更新：2026-01-29 22:52 CST*
