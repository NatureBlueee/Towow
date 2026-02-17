# 文档索引 (Documentation Index)

通爻网络全部文档的导航地图。

---

## 主文档

| 文件 | 说明 |
|------|------|
| [ARCHITECTURE_DESIGN.md](ARCHITECTURE_DESIGN.md) | V1 架构设计 (13 sections, 107KB) |
| [ENGINEERING_REFERENCE.md](ENGINEERING_REFERENCE.md) | 工程标准——命名、错误处理、接口模式、事件格式 |

---

## 架构决策 (`decisions/`)

### ADR (Architecture Decision Records)

| ADR | 状态 | 主题 |
|-----|------|------|
| [ADR-001](decisions/ADR-001-unified-adapter-registry.md) | 已实施 | 统一 Adapter Registry |
| [ADR-002](decisions/ADR-002-mcp-entry-point.md) | 已批准 | MCP 作为独立入口 |
| [ADR-003](decisions/ADR-003-negotiation-graph-visualization.md) | 已实施 | 协商图可视化 |
| [ADR-004](decisions/ADR-004-bloom-filter-gate.md) | 搁置 | Bloom Filter 前置门 |
| [ADR-005](decisions/ADR-005-agent-exit-mechanism.md) | 搁置 | Agent 退出机制 |
| [ADR-006](decisions/ADR-006-data-layer-wowok-integration.md) | 已实施 | 数据层 WOWOK 集成 |
| [ADR-007](decisions/ADR-007-user-history-persistence.md) | 已实施 | 用户历史持久化 |
| [ADR-008](decisions/ADR-008-store-negotiation-display.md) | 已实施 | Store 协商展示 |
| [ADR-009](decisions/ADR-009-open-registration-playground.md) | 已实施 | 开放注册 Playground |
| [ADR-010](decisions/ADR-010-unified-entry-selector.md) | 已实施 | 统一入口选择器 |
| [ADR-011](decisions/ADR-011-v2-intent-field.md) | 已批准 | V2 Intent Field |
| [ADR-012](decisions/ADR-012-research-to-execution-pivot.md) | 已实施 | 研究到执行转向 |
| [ADR-013](decisions/ADR-013-post-experiment-decisions.md) | 已批准 | 实验后三组决策 |

### 实现方案 (PLAN) 和接口规格 (SPEC)

| 文件 | 关联 ADR |
|------|---------|
| [PLAN-001](decisions/PLAN-001-adapter-registry-implementation.md) | ADR-001 |
| [PLAN-002](decisions/PLAN-002-mcp-server.md) | ADR-002 |
| [SPEC-002](decisions/SPEC-002-mcp-interface-design.md) | ADR-002 接口设计 |
| [PLAN-003](decisions/PLAN-003-negotiation-graph-implementation.md) | ADR-003 |
| [PLAN-006](decisions/PLAN-006-app-store-graph-reuse.md) | ADR-006 |
| [PLAN-007](decisions/PLAN-007-user-history-persistence.md) | ADR-007 |
| [PLAN-008](decisions/PLAN-008-store-negotiation-display.md) | ADR-008 |
| [PLAN-009](decisions/PLAN-009-open-registration-playground.md) | ADR-009 |
| [PLAN-010](decisions/PLAN-010-unified-entry-selector.md) | ADR-010 |
| [PLAN-011](decisions/PLAN-011-v2-intent-field.md) | ADR-011 |
| [SPEC-011](decisions/SPEC-011-v2-intent-field-interface.md) | ADR-011 接口设计 |
| [EXEC-003](decisions/EXEC-003-parallel-development.md) | 并行开发编排 |

---

## 设计日志 (`design-logs/`)

思考过程的记录。不可变——决策一旦做出不修改原文。

| 编号 | 主题 | 核心洞察 |
|------|------|---------|
| [001](design-logs/DESIGN_LOG_001_PROJECTION_AND_SELF.md) | 投影与自我 | "自"在系统之外，系统中只有投影 |
| [002](design-logs/DESIGN_LOG_002_ECHO_AND_EXECUTION.md) | 回声与执行 | 执行信号回流改变存在本身 |
| [003](design-logs/DESIGN_LOG_003_PROJECTION_AS_FUNCTION.md) | 投影即函数 | Agent = 投影函数，不是有状态对象 |
| [004](design-logs/DESIGN_LOG_004_ECONOMIC_MODEL_AND_ECOSYSTEM.md) | 经济模型与生态 | 商业叙事、竞争分析、投资人 Q&A |
| [005](design-logs/DESIGN_LOG_005_SCENE_AS_PRODUCT.md) | 场景即产品 | 产品范式、API 边界 |
| [006](design-logs/DESIGN_LOG_006_CRYSTALLIZATION_PROTOCOL.md) | 结晶协议 | V2 协议从第一性原理重新推导 |

---

## 工程文档 (`engineering/`)

| 文件 | 说明 |
|------|------|
| [DEV_LOG_V1.md](engineering/DEV_LOG_V1.md) | V1 协商引擎全部决策和执行记录 |
| [DEV_LOG_V2.md](engineering/DEV_LOG_V2.md) | V2 意图场开发记录 |

---

## 研究与实验 (`research/`)

| 文件 | 说明 |
|------|------|
| [000](research/000-v2-field-experiment-review.md) | V2 Field 实验总览 |
| [001](research/001-intent-to-intent-encoding.md) | Intent 编码研究 |
| [002](research/002-experiment-skill-design.md) | 实验 Skill 设计 |
| [003](research/003-adr012-execution-results.md) | ADR-012 实验结果 (EXP-005~008) |

实验数据：`tests/field_poc/results/`

---

## V1 Skill Prompts (`prompts/`)

| 文件 | Skill |
|------|-------|
| [center_coordinator_v1.md](prompts/center_coordinator_v1.md) | Center 协调者 |
| [demand_formulation_v1.md](prompts/demand_formulation_v1.md) | 需求 Formulation |
| [offer_generation_v1.md](prompts/offer_generation_v1.md) | Offer 生成 |
| [gap_recursion_v1.md](prompts/gap_recursion_v1.md) | 缺口递归 |
| [sub_negotiation_v1.md](prompts/sub_negotiation_v1.md) | 子协商 |

---

## 开发指南 (`guides/`)

| 文件 | 说明 |
|------|------|
| [quickstart](guides/quickstart.md) | 快速上手（5 分钟跑通） |
| [v1-engine](guides/v1-engine.md) | V1 协商引擎开发指南 |
| [guide-001](guides/guide-001-projection-vs-essence.md) | 投影与本质 |

---

## 归档 (`archive/`)

历史产物，不再维护。保留供参考。

- `archive/tasks/` — 25 个旧任务文档
- `archive/promo/` — 推广材料
- `archive/features/` — 已合并的功能规格
- `archive/issues/` — 已解决的问题记录
- `archive/genome-v03.html` — Genome v0.3 HTML 版
- `archive/topology*.html` — 拓扑可视化
- `archive/arch-report.md`, `eng-report.md` — 审计报告
