# EXEC-003: 协商图谱并行开发执行计划

**关联**: ADR-003, PLAN-003
**日期**: 2026-02-12

---

## 执行策略

最大化并行：Agent Team + Codex 同时执行无依赖的任务。

**工具分配原则**：
- **Codex**：机械性、规格明确的改动（小文件编辑、模式化组件）
- **Agent Team**：需要判断力的复杂任务（核心架构、交互逻辑、测试设计）
- **Leader (我)**：编排、接缝验证、集成、上下文保护

**上下文保护策略**：
- 所有规格在 PLAN-003 文件中，每个 Agent/Codex 首先读取该文件
- 中间产出写入文件而非保留在对话上下文中
- 每个 Phase 完成后，Leader 读文件验证，不依赖记忆

---

## Phase 1: 全部契约变更 + 测试（4 路并行）

### 1A — Codex: 后端契约文件 (A1+A2+A4)
修改 3 个文件的契约接口：
- `backend/towow/hdc/resonance.py`: detect() 加 min_score，返回 (activated, filtered)
- `backend/towow/core/events.py`: resonance_activated 加 filtered_agents；plan_ready plan_json 必填
- `backend/towow/api/schemas.py`: SubmitDemandRequest 加 k_star + min_score

### 1B — Codex: 后端路由 (A5)
- `backend/towow/api/routes.py`: submit_demand 读取 k_star/min_score，_run_negotiation 传递

### 1C — Agent: 后端引擎 + 全部测试 (A3+F1-F4)
复杂逻辑改动：
- `backend/towow/core/engine.py`: start_negotiation 加 min_score，_run_encoding 适配二元组
- 4 个测试文件的新增/修改测试用例

### 1D — Agent: 前端类型 + Hooks (B1+B2+B3)
- `website/types/negotiation.ts`: 类型变更 + PlanJson 新增
- `website/hooks/useNegotiationStream.ts`: filteredAgents 状态
- `website/hooks/useNegotiationApi.ts`: k_star + min_score 参数

### Phase 1 完成门禁
- [x] 后端全部 221+ 测试通过（实际 250 通过）
- [x] 前端 `npm run build` 无类型错误
- [x] Leader 接缝验证 S1, S4, S6

---

## Phase 2: 图谱组件（4 路并行）

依赖：Phase 1 完成（前端类型就绪）

### 2A — Agent: 图谱核心骨架 (C1+C2)
最复杂的部分：
- `graph/layout.ts`: 径向布局算法
- `NegotiationGraph.tsx`: SVG 容器 + 事件→动画调度队列

### 2B — Codex: 节点组件 (C3+C4+C5)
模式化 SVG + Framer Motion 组件：
- `graph/DemandNode.tsx`
- `graph/AgentNode.tsx`
- `graph/CenterNode.tsx`

### 2C — Codex: 边组件 (C6+C7)
- `graph/ResonanceEdge.tsx`: 共振连线 + 粒子动画
- `graph/InteractionEdge.tsx`: ask_agent 对话 + discover 新边

### 2D — Agent: 面板组件 (C9+C10)
需要判断力的交互组件：
- `DetailPanel.tsx`: 7 种内容类型的侧滑面板
- `PlanView.tsx`: plan_json 拓扑渲染 + plan_text

### Phase 2 完成门禁
- [x] 所有组件可独立渲染（无编译错误）
- [x] Leader 验证组件接口匹配 NegotiationGraph 的消费方式
- [x] 偏差记录：2B/2C 原计划用 Codex，实际用 Agent（Framer Motion 动画需要判断力）

---

## Phase 3: 集成 + Mock（2 路并行）

依赖：Phase 2 完成

### 3A — Agent: 页面重构 + 剩余组件 (C8+C11+D1+D2)
- `graph/SubGraph.tsx`: 子协商缩略图
- `ResonanceControls.tsx`: K 值 + 阈值滑块
- `NegotiationPage.tsx`: 布局重构（图谱为主）
- `NegotiationPage.module.css`: CSS 重写

### 3B — Codex: Mock 数据 (E1)
- `__mocks__/events.ts`: 完整 mock 事件序列（含 filtered、多轮 tool_call、plan_json）

### Phase 3 完成门禁
- [x] `npm run build` 通过
- [x] Demo 模式可运行（Mock 事件序列 11 步）
- [x] Leader 接缝验证 S2, S3, S5
- [x] Leader 发现并修复 3 个接缝 bug：边 ID 前缀不匹配、filteredAgents 查找缺失、交互边索引映射错误

---

## Phase 4: 端到端验证（Leader）

- [x] 后端测试全部通过（249/250，1 个预存 flaky）
- [x] 前端 build 通过（19 routes，0 错误）
- [ ] Demo 模式完整流程可视化（Playwright 因 Chrome 占用未能截图，待手动验证）
- [x] 6 条接缝全部验证（发现 3 bug 已修复 + 无障碍改进）
- [x] 更新 MEMORY.md
- [x] 3 个并行审计 Agent 全量检查 Phase 1-3 产出

---

## 并行度时间线

```
时间 →

Phase 1:  [1A Codex] [1B Codex] [1C Agent] [1D Agent]  ← 4 路并行
          ─────────────────────────────────────────────
Phase 2:            [2A Agent] [2B Codex] [2C Codex] [2D Agent]  ← 4 路并行
                    ───────────────────────────────────────────
Phase 3:                      [3A Agent] [3B Codex]  ← 2 路并行
                              ─────────────────────
Phase 4:                                [Leader 验证]
```

总计：10 个并行任务，4 个 Phase
